"""Valida a coleta e prepara uma nova pasta de relatório ou entrega, sempre offline."""

import argparse
import json
from pathlib import Path
import shutil
from uuid import uuid4

from evaluation.academic_metrics import export
from scripts.gs_preflight import inspect, summarize
from scripts.transferir_gs import VIDEO, checked_scope, code_files, evidence_files, make_archive
from src.config import PROJECT_ROOT
from src.errors import ValidationError


def render(pdf, destination):
    import pymupdf

    destination.mkdir()
    with pymupdf.open(pdf) as doc:
        if len(doc) < 6:
            raise ValidationError("O PDF está incompleto.")
        pages = [page.get_text() for page in doc]
        if not all(rm in pages[0] for rm in ("562286", "563978", "561932")):
            raise ValidationError("O PDF não contém a identificação completa.")
        for index, page in enumerate(doc, 1):
            if len(pages[index - 1].strip()) < 100:
                raise ValidationError(f"Página {index} sem conteúdo suficiente para revisão.")
            if any(float(word[0]) < 15 or float(word[2]) > page.rect.width - 15 or float(word[3]) > page.rect.height - 10
                   for word in page.get_text("words")):
                raise ValidationError(f"Página {index} contém texto fora da margem de verificação.")
            page.get_pixmap(dpi=110).save(destination / f"pagina-{index:02d}.png")


def pending(info, args, scope):
    issues = [key for key, ok in info["gates"].items() if not ok] + info["problemas"]
    if not args.edicao or not args.edicao.strip():
        issues.append("Edição acadêmica confirmada pelo docente")
    if not args.decisao or not args.decisao.is_file() or not args.decisao.read_text(encoding="utf-8-sig").strip():
        issues.append("Justificativa da configuração escolhida com os resultados A/B")
    if len(scope["stt"]) != 20 or len(scope["e2e"]) != 10 or not scope["video"]:
        issues.append("Escopo específico para compartilhar originais STT, evidências E2E e MP4 com o destinatário")
    return issues


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--preliminar", action="store_true")
    parser.add_argument("--saida", type=Path)
    parser.add_argument("--edicao")
    parser.add_argument("--escopo", type=Path)
    parser.add_argument("--decisao", type=Path, help="Texto UTF-8 da decisão STT a partir dos resultados A/B")
    args = parser.parse_args()
    try:
        info, metrics = inspect()
        scope = checked_scope(PROJECT_ROOT, args.escopo)
        issues = pending(info, args, scope)
        print(summarize(info))
        for issue in issues:
            print("Pendente", issue)
        if args.dry_run:
            print("A finalização prepara evidências, gráficos, PDF renderizado e um diretório de entrega.")
            return 0
        if issues and not args.preliminar:
            print("A entrega final está bloqueada.")
            return 2
        if not args.saida:
            raise ValidationError("Indique uma nova pasta com --saida.")
        target = args.saida.resolve()
        if target.exists() or info["problemas"]:
            raise ValidationError("Use uma pasta nova e corrija divergências de evidência antes de gerar o PDF.")
        from scripts.build_academic_report import build
        stage = target.with_name(".gs-staging-" + uuid4().hex)
        stage.mkdir(parents=True)
        metrics.update(preflight=info)
        export(metrics, stage / "metricas")
        basename = "relatorio_global_solution_preliminar.pdf" if args.preliminar else "relatorio_global_solution_final.pdf"
        pdf = stage / basename
        decision = args.decisao.read_text(encoding="utf-8-sig") if args.decisao else ""
        build(pdf, stage / "metricas/metrics.json", args.edicao, not args.preliminar, decision=decision)
        render(pdf, stage / "paginas_pdf")
        (stage / "preflight.json").write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
        if not args.preliminar:
            make_archive(stage / "VivaBairro_GS_Codigo.zip", code_files(PROJECT_ROOT), "codigo")
            make_archive(stage / "VivaBairro_GS_Material_Restrito.zip", evidence_files(PROJECT_ROOT, scope, include_video=False), "evidencias")
            shutil.copyfile(PROJECT_ROOT / VIDEO, stage / Path(VIDEO).name)
            links = [basename, Path(VIDEO).name, "VivaBairro_GS_Codigo.zip", "VivaBairro_GS_Material_Restrito.zip", "metricas/metrics.json"]
            (stage / "ABRIR_ENTREGA.md").write_text("# VivaBairro Voz\n\n" + "\n".join(f"- [{name}]({name})" for name in links)
                + "\n\nConfira as páginas renderizadas e compartilhe somente esta pasta em acesso restrito ao destinatário aprovado.\n", encoding="utf-8")
            if not all((stage / name).is_file() for name in links):
                raise ValidationError("Há um link de entrega sem arquivo correspondente.")
        stage.rename(target)
        print(target)
        return 0
    except (OSError, ValueError, KeyError, ValidationError, ImportError) as error:
        print(f"Finalização indisponível: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
