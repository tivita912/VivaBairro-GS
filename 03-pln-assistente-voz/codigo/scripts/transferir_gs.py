"""Cria e restaura pacotes separados de código e evidências com inventário SHA-256."""

import argparse
import csv
from hashlib import sha256
from io import StringIO
import json
from pathlib import Path, PurePosixPath
import posixpath
import re
import shutil
from tempfile import TemporaryDirectory
from zipfile import ZIP_DEFLATED, ZipFile

from evaluation.run_stt import digest, read_optional
from src.config import PROJECT_ROOT
from src.errors import ValidationError

VIDEO = "docs/video/editorial_v2/vivabairro_video_final_narrado.mp4"
PRIVATE_CSV = {"stt_manifest.csv", "llm_ratings.csv", "tts_samples.csv", "tts_ratings.csv", "e2e_sessions.csv"}
INDEX = "SHA256.json"


def code_files(root):
    paths = [root / name for name in ("app.py", "README.md", "requirements.txt", "requirements-academic.txt",
                                      "config.example.env", ".gitignore", "vivabairro.css", "iniciar_avaliacao_gs.ps1",
                                      "instalar_gs.ps1", "preparar_whisper.ps1")]
    for directory in ("src", "web", "tests", "knowledge", "prompts", "scripts", "evaluation"):
        paths.extend(p for p in (root / directory).iterdir() if p.is_file() and p.name not in PRIVATE_CSV)
    paths.extend(p for p in (root / "web/assets").iterdir() if p.is_file())
    paths.extend(root / name for name in ("docs/architecture.md", "docs/dependencies.md", "docs/checklist.md", "docs/consent_template.md",
                 "docs/web_interface.md", "docs/manual_voice_test.md",
                 "docs/academic/GUIA_GUSTAVO.md", "docs/academic/CHECKLIST_ENTREGA_FINAL.md", "docs/academic/metodologia.md",
                 "docs/academic/resultados.md", "docs/academic/revisao_final.md", "docs/academic/AUDITORIA_LLM.md",
                 "docs/academic/ORIENTACOES_DO_PROFESSOR.md", "docs/academic/ESTADO_ATUAL_E_PENDENCIAS.md",
                 "docs/academic/GUIA_OPERACIONAL_COMPLETO.md", "docs/academic/PRONTIDAO_ATUAL.md",
                 "docs/academic/ENUNCIADO_OFICIAL_GS_2TIAPY.pdf",
                 "docs/academic/relatorio_global_solution_preliminar_STT13_20261117.pdf",
                 "evaluation/results/README.md", "evaluation/consents/README.md"))
    result = {}
    for path in paths:
        if not path.is_file() or path.is_symlink() or not path.resolve().is_relative_to(root):
            raise ValidationError(f"Arquivo de código indisponível: {path.name}")
        if path.name == "metodologia.md":
            result[path.relative_to(root).as_posix()] = re.sub(r" · RM \d{6}", "", path.read_text(encoding="utf-8")).encode()
        else:
            result[path.relative_to(root).as_posix()] = path
    for name, value in list(result.items()):
        if not name.endswith(".md"):
            continue
        content = value.read_text(encoding="utf-8-sig") if isinstance(value, Path) else value.decode()
        def replace_link(match):
            label, href = match.groups()
            target = posixpath.normpath(posixpath.join(posixpath.dirname(name), href.split("#", 1)[0]))
            if ":" in href or href.startswith("#") or target in result:
                return match[0]
            return label + " (na cópia de trabalho da equipe)"
        result[name] = re.sub(r"\[([^\]\n]+)\]\(([^\s)]+)\)", replace_link, content).encode("utf-8")
    return result


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def filtered_csv(path, keep, transform=None):
    with path.open(encoding="utf-8-sig", newline="") as raw:
        reader = csv.DictReader(raw)
        stream = StringIO(newline="")
        writer = csv.DictWriter(stream, reader.fieldnames)
        writer.writeheader()
        for row in reader:
            if keep(row):
                writer.writerow(transform(row) if transform else row)
    return stream.getvalue().encode("utf-8")


def checked_scope(root, file):
    scope = {"stt": {}, "e2e": {}, "video": ""}
    if not file:
        return scope
    scope.update(json.loads(file.read_text(encoding="utf-8-sig")))
    if scope.get("confirmado") is not True or not str(scope.get("destinatario", "")).strip():
        raise ValidationError("Registre o destinatário e confira o escopo de compartilhamento.")
    for term in [*scope["stt"].values(), *scope["e2e"].values(), *([scope["video"]] if scope["video"] else [])]:
        path = root / "evaluation/consents" / term
        if not path.is_file() or not path.stat().st_size or path.name == "README.md":
            raise ValidationError("A declaração de compartilhamento aponta para um comprovante indisponível.")
    return scope


def evidence_files(root, scope, include_video=True):
    e = root / "evaluation"
    out = e / "results"
    result = {}

    def add(path):
        if not path.is_file() or path.is_symlink() or not path.resolve().is_relative_to(root):
            raise ValidationError(f"Evidência indisponível: {path.name}")
        result[path.relative_to(root).as_posix()] = path

    for name in ("llm_ratings.csv", "tts_samples.csv", "tts_ratings.csv"):
        if (e / name).exists():
            add(e / name)
    for directory in ("llm_rodadas", "tts_rodadas"):
        for path in sorted((out / directory).glob("*/*")):
            if path.suffix in {".json", ".wav"}:
                add(path)
    for name in ("llm_ratings_antes_da_avaliacao_por_ia.csv", "llm_triagem_assistente.csv", "llm_triagem_assistente.md",
                 "llm_revisao_humana.csv", "llm_revisao_para_preencher.csv", "kit_tts_avaliadores.zip", "tts_verificacao_tecnica.json",
                 "verificacao_transferencia_final.json"):
        if (out / name).exists():
            add(out / name)

    manifest = read_optional(e / "stt_manifest.csv")
    by_id = {r["sample_id"]: r for r in manifest}
    if len(by_id) != len(manifest) or not set(scope["stt"]).issubset(by_id):
        raise ValidationError("O escopo STT contém IDs ausentes ou conflitantes.")
    selected = {by_id[key]["audio_sha256"] for key in scope["stt"]}
    reserved = []
    for path in (out / "stt_historico").glob("*.json"):
        record = json.loads(path.read_text(encoding="utf-8-sig"))
        if record["stt_status"] == "TRANSCRITO":
            reserved.append((record["sha256"], record["requested_model"]))
        if record["sha256"] in selected:
            add(path)
    result["evaluation/results/stt_reserva_historica.json"] = json_bytes(sorted(set(reserved)))
    if selected:
        for row in manifest:
            if row["audio_sha256"] in selected:
                path = e / row["audio_path"]
                if not path.resolve().is_relative_to(e / "audio") or digest(path) != row["audio_sha256"]:
                    raise ValidationError("O original STT diverge da evidência registrada.")
                add(path)
        result["evaluation/stt_manifest.csv"] = filtered_csv(e / "stt_manifest.csv", lambda r: r["audio_sha256"] in selected)
        result["evaluation/results/stt_referencias_revisao.csv"] = filtered_csv(
            out / "stt_referencias_revisao.csv", lambda r: r["sha256"] in selected,
            lambda r: dict(r, consent_document="", external_audio_authorized=""))
        for path in (out / "stt_whisper_formal").glob("*.json"):
            if path.name.split("-")[0] in selected:
                add(path)
        if len(selected) == len(manifest) and (out / "stt_comparacao.json").is_file():
            add(out / "stt_comparacao.json")
        if len(selected) == len(manifest):
            for name in ("stt_correcao_ids_2026-11-16.csv", "stt_relatorio_parcial.md"):
                if (out / name).is_file():
                    add(out / name)

    sessions = read_optional(e / "e2e_sessions.csv")
    if not set(scope["e2e"]).issubset({r["conversation_id"] for r in sessions}):
        raise ValidationError("O escopo E2E contém um cenário ausente.")
    if scope["e2e"]:
        result["evaluation/e2e_sessions.csv"] = filtered_csv(e / "e2e_sessions.csv", lambda r: r["conversation_id"] in scope["e2e"])
        for row in sessions:
            if row["conversation_id"] not in scope["e2e"] or not row.get("audio_evidence_path"):
                continue
            path = e / row["audio_evidence_path"]
            if not path.resolve().is_relative_to(out) or digest(path) != row["audio_sha256"]:
                raise ValidationError("Um WAV E2E diverge do registro.")
            add(path)
    if scope["video"] and include_video:
        add(root / VIDEO)
    result["evaluation/results/estado_transferencia.json"] = json_bytes(dict(
        stt_origem=len(manifest), stt_transcritos_origem=sum(r["transcription_completed"] == "true" for r in manifest),
        stt_incluidos=sorted(scope["stt"]), stt_retidos=sorted(set(by_id) - set(scope["stt"])),
        e2e_incluidos=sorted(scope["e2e"]), video_incluido=VIDEO in result,
        nota="Termos individuais permanecem com o responsável. O resumo da origem não conta como corpus restaurado."))
    return result


def make_archive(target, files, kind):
    index = {name: digest(value) if isinstance(value, Path) else sha256(value).hexdigest() for name, value in sorted(files.items())}
    with ZipFile(target, "x", compression=ZIP_DEFLATED) as bundle:
        for name, value in sorted(files.items()):
            if isinstance(value, Path):
                bundle.write(value, name)
            else:
                bundle.writestr(name, value)
        bundle.writestr(INDEX, json_bytes(dict(kind=kind, sha256=index)))
    with target.with_suffix(".zip.sha256").open("x", encoding="ascii") as sidecar:
        sidecar.write(f"{digest(target)}  {target.name}\n")


def safe_destination(root, name):
    relative = PurePosixPath(name)
    if (relative.is_absolute() or len(relative.parts) < 2 or relative.parts[0] not in {"evaluation", "docs"} or
            any(part in {".", ".."} or ":" in part or "\\" in part or part.startswith(".") or
                part.lower() in {"secrets", "__pycache__", "consents"} for part in relative.parts)):
        raise ValidationError("Caminho não permitido no pacote privado.")
    if relative.parts[0] == "docs" and name != VIDEO:
        raise ValidationError("Caminho de documentação não permitido no pacote privado.")
    if relative.parts[0] == "evaluation" and relative.parts[1] not in {"audio", "results", *PRIVATE_CSV}:
        raise ValidationError("Arquivo fora da área de evidências.")
    dest = root.joinpath(*relative.parts)
    if not dest.resolve().is_relative_to(root):
        raise ValidationError("O destino sai da raiz autorizada.")
    return dest


def restore(package, expected, root=PROJECT_ROOT, dry_run=False):
    if not re.fullmatch(r"[a-fA-F0-9]{64}", expected) or digest(package) != expected.lower():
        raise ValidationError("O SHA-256 do ZIP não confere.")
    if not (root / "app.py").is_file():
        raise ValidationError("Extraia primeiro o pacote de código.")
    with ZipFile(package) as bundle:
        names = bundle.namelist()
        meta = json.loads(bundle.read(INDEX))
        hashes = meta["sha256"]
        if meta["kind"] != "evidencias" or len(names) != len(set(n.casefold() for n in names)) or set(names) != {*hashes, INDEX}:
            raise ValidationError("Conteúdo do ZIP diverge do índice.")
        conflicts = []
        items = []
        with TemporaryDirectory(prefix="vivabairro-restaurar-") as temp:
            for index, (name, hash_value) in enumerate(hashes.items()):
                dest = safe_destination(root, name)
                staged = Path(temp) / str(index)
                with bundle.open(name) as src, staged.open("wb") as out:
                    shutil.copyfileobj(src, out)
                if digest(staged) != hash_value:
                    raise ValidationError(f"Evidência corrompida: {name}")
                if dest.exists():
                    if not dest.is_file() or digest(dest) != hash_value:
                        conflicts.append(name)
                else:
                    items.append((staged, dest))
            if conflicts:
                raise ValidationError("Conflitos preservados: " + ", ".join(conflicts[:12]))
            if not dry_run:
                for staged, dest in items:
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    with staged.open("rb") as src, dest.open("xb") as out:
                        shutil.copyfileobj(src, out)
            return len(items), len(hashes) - len(items)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    create = sub.add_parser("criar")
    create.add_argument("--saida", type=Path, required=True)
    create.add_argument("--escopo", type=Path)
    use = sub.add_parser("restaurar")
    use.add_argument("zip", type=Path)
    use.add_argument("--sha256", required=True)
    use.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    try:
        if args.action == "criar":
            scope = checked_scope(PROJECT_ROOT, args.escopo)
            evidence = evidence_files(PROJECT_ROOT, scope)
            code = code_files(PROJECT_ROOT)
            args.saida.mkdir(parents=True, exist_ok=False)
            make_archive(args.saida / "VivaBairro_GS_Codigo.zip", code, "codigo")
            make_archive(args.saida / "VivaBairro_GS_Evidencias_Privadas.zip", evidence, "evidencias")
        else:
            new, same = restore(args.zip, args.sha256, dry_run=args.dry_run)
            print(f"{new} novos, {same} idênticos, zero conflitos. Simulação: {args.dry_run}.")
    except (OSError, ValueError, KeyError, ValidationError) as error:
        parser.exit(1, f"Transferência interrompida: {error}\n")


if __name__ == "__main__":
    main()
