"""Exporta as 30 respostas para revisão humana independente e reimporta os julgamentos."""

import argparse
from pathlib import Path

from evaluation.academic_metrics import assess_llm, read
from evaluation.run_stt import ROOT, write_csv
from src.errors import ValidationError

DECISIONS = ("correct", "refusal_appropriate", "evaluator_id", "notes")


def prepare(root, path):
    catalog = read(root / "llm_questions.csv")
    results = {r["question_id"]: r for r in read(root / "llm_ratings.csv")}
    if len(results) != 30 or any(not r.get("actual_answer") or r.get("error_type") for r in results.values()):
        raise ValidationError("As 30 respostas originais são necessárias para montar a revisão.")
    rows = [dict(r, actual_answer=results[r["question_id"]]["actual_answer"], **dict.fromkeys(DECISIONS, "")) for r in catalog]
    if path.exists():
        raise FileExistsError(path)
    # O questionário usa reviewed_by; a resposta da IA não é copiada nos campos de decisão.
    write_csv(path, list(rows[0]), rows)


def import_review(root, path):
    catalog = read(root / "llm_questions.csv")
    source = {r["question_id"]: r for r in read(root / "llm_ratings.csv")}
    review = read(path)
    if len(review) != 30 or {r.get("question_id") for r in review} != set(source):
        raise ValidationError("A revisão precisa cobrir os 30 casos.")
    rows = []
    for judge in review:
        old = source[judge["question_id"]]
        if judge.get("evaluator_id") not in {"P01", "P02", "P03"} or judge["actual_answer"] != old["actual_answer"]:
            raise ValidationError("Informe um avaliador humano do grupo e preserve a resposta literal.")
        rows.append(dict(old, **{field: judge[field] for field in DECISIONS}, review_status="reviewed"))
    if not assess_llm(catalog, rows)["complete"]:
        raise ValidationError("Os julgamentos humanos estão incompletos.")
    out = root / "results/llm_revisao_humana.csv"
    if out.exists() and read(out) != rows:
        raise ValidationError("Já há outra revisão humana. Preserve-a antes de substituir a revisão selecionada.")
    if not out.exists():
        write_csv(out, list(rows[0]), rows)
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("acao", choices=("exportar", "importar"))
    parser.add_argument("csv", type=Path)
    args = parser.parse_args()
    try:
        if args.acao == "exportar":
            prepare(ROOT, args.csv)
        else:
            print(import_review(ROOT, args.csv))
    except (OSError, KeyError, ValidationError) as error:
        parser.exit(1, f"Revisão indisponível: {error}\n")


if __name__ == "__main__":
    main()
