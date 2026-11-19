"""Agrega os CSVs do formulário offline, preservando os julgamentos já aceitos."""

import argparse
from datetime import date
from pathlib import Path
import wave

from evaluation.academic_metrics import assess_tts, chart
from evaluation.preparar_kit_tts import verify_samples
from evaluation.run_stt import ROOT, read_optional, write_csv
from src.errors import ValidationError

FIELDS = "sample_id evaluator_id clarity_1_to_5 naturalness_1_to_5 evaluated_on notes audio_sha256".split()


def merge(paths, root=ROOT):
    target = root / "tts_ratings.csv"
    hashes = {r["sample_id"]: r["sha256"] for r in verify_samples(root)}
    lock = root / ".tts_importando"
    with lock.open("x", encoding="utf-8"):
        pass
    try:
        rows = {}
        for path in [target, *paths]:
            items = read_optional(path) if path == target or path.is_file() else None
            if items is None:
                raise FileNotFoundError(path)
            if path != target and (len(items) != 10 or {r.get("sample_id") for r in items} != set(hashes)
                                   or len({r.get("evaluator_id") for r in items}) != 1):
                raise ValidationError("Cada ficha precisa de dez amostras e um único avaliador.")
            for row in items:
                if set(row) != set(FIELDS) or any(not isinstance(row[k], str) for k in FIELDS):
                    raise ValidationError("Use as colunas exportadas pelo formulário do ZIP.")
                sid, person = row["sample_id"], row["evaluator_id"]
                if person not in {"P01", "P02", "P03"} or hashes.get(sid) != row["audio_sha256"]:
                    raise ValidationError("Avaliador inválido ou amostra de outro kit.")
                if any(row[k] not in "12345" or len(row[k]) != 1 for k in ("clarity_1_to_5", "naturalness_1_to_5")):
                    raise ValidationError("Preencha duas notas inteiras de 1 a 5.")
                try:
                    if date.fromisoformat(row["evaluated_on"]).isoformat() != row["evaluated_on"]:
                        raise ValueError
                except ValueError as error:
                    raise ValidationError("Use data válida no formato AAAA-MM-DD.") from error
                key = sid, person
                if key in rows and rows[key] != row:
                    raise ValidationError(f"Conflito em {sid}/{person}. A planilha anterior foi preservada.")
                rows[key] = row
        if list(rows.values()) != read_optional(target):
            write_csv(target, FIELDS, [rows[key] for key in sorted(rows)])
        return len(rows)
    finally:
        lock.unlink()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", nargs="+", type=Path)
    parser.add_argument("--graficos", type=Path, help="Nova pasta para gráficos de clareza e naturalidade")
    args = parser.parse_args()
    try:
        n = merge(args.csv)
        scores = assess_tts(read_optional(ROOT / "tts_samples.csv"), read_optional(ROOT / "tts_ratings.csv"))
        if args.graficos and n:
            args.graficos.mkdir(parents=True, exist_ok=False)
            for key, label in (("clarity", "Clareza"), ("naturalness", "Naturalidade")):
                chart(args.graficos / f"tts_{key}.svg", label, "/ 5", [(sid, row[key]) for sid, row in scores["per_sample"].items()])
        print(f"{n}/30 julgamentos | clareza {scores['overall']['clarity']} | naturalidade {scores['overall']['naturalness']}")
    except (OSError, ValueError, wave.Error, ValidationError) as error:
        parser.exit(1, f"Importação indisponível: {error}\n")


if __name__ == "__main__":
    main()
