"""Calcula WER de um manifesto preenchido, sem confundir fixtures com evidência."""
import argparse
import csv
import json
from pathlib import Path
from statistics import mean, median

from src.errors import ValidationError
from src.metrics import stt_scores


def score_manifest(path: Path) -> dict:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    if not rows:
        raise ValidationError("O manifesto está vazio. Grave e transcreva as amostras antes de calcular WER.")
    required = {"sample_id", "data_origin", "speaker_id", "noise_present", "reference_text",
                "hypothesis_text", "transcription_completed", "consent_id", "model_id", "model_revision", "environment_id"}
    if not required.issubset(rows[0]):
        raise ValidationError("O manifesto não contém todas as colunas obrigatórias.")
    if len({r["sample_id"] for r in rows}) != len(rows):
        raise ValidationError("Use uma configuração por manifesto e IDs de amostra únicos.")
    origins = {r["data_origin"] for r in rows}
    if len(origins) != 1 or not origins.issubset({"real", "synthetic_development"}):
        raise ValidationError("Não misture evidência real com dados sintéticos de desenvolvimento.")
    partial_schema = "reference_status" in rows[0]
    received = len(rows)
    completed = sum(r["transcription_completed"] == "true" for r in rows)
    verified = sum(r.get("reference_status") == "VERIFICADA" for r in rows)
    measured = [r for r in rows if r["transcription_completed"] == "true" and r.get("stt_seconds")]
    latency = {}
    for speaker in sorted({r["speaker_id"] for r in measured}):
        latency[speaker] = {}
        for env in sorted({r["environment_id"] for r in measured if r["speaker_id"] == speaker}):
            values = [float(r["stt_seconds"]) for r in measured if (r["speaker_id"], r["environment_id"]) == (speaker, env)]
            latency[speaker][env] = dict(n=len(values), mean=mean(values), median=median(values), min=min(values), max=max(values))
    if partial_schema:
        rows = [r for r in rows if r.get("reference_status") == "VERIFICADA" and r["transcription_completed"] == "true"]
        if not rows:
            return {"sample_ids": [], "data_origin": next(iter(origins)), "samples": 0, "wer_corpus": None,
                    "by_speaker": {}, "by_noise": {}, "coverage": {"samples": 0, "speakers": 0, "noisy_samples": 0},
                    "quantity_gate_met": False, "received": received, "transcribed": completed,
                    "human_references": verified, "latency_by_speaker_and_environment": latency,
                    "limitation": "WER aguarda pares com referência humana revisada."}
    for row in rows:
        optional = {"hypothesis_text", "noise_present"} if partial_schema else {"hypothesis_text"}
        noise_values = {"", "true", "false"} if partial_schema else {"true", "false"}
        if (any(not row.get(k, "").strip() for k in required - optional) or
                row["noise_present"] not in noise_values or row["transcription_completed"] != "true"):
            raise ValidationError("Complete os metadados e use true/false nos campos booleanos.")
        if row["data_origin"] == "real" and not row.get("reference_reviewed_by", "").strip():
            raise ValidationError("Referências reais precisam de revisão humana registrada.")
    configurations = {(r["model_id"], r["model_revision"]) for r in rows}
    if len(configurations) != 1:
        raise ValidationError("O WER agregado exige o mesmo modelo e a mesma revisão informada.")

    def scores(subset):
        return stt_scores([r["reference_text"] for r in subset], [r["hypothesis_text"] for r in subset])

    result = scores(rows)
    result["sample_ids"] = [r["sample_id"] for r in rows]
    result["data_origin"] = next(iter(origins))
    result["by_speaker"] = {speaker: scores([r for r in rows if r["speaker_id"] == speaker])
                            for speaker in sorted({r["speaker_id"] for r in rows})}
    result["by_noise"] = {noise: scores([r for r in rows if r["noise_present"] == noise])
                          for noise in sorted({r["noise_present"] for r in rows} - {""})}
    result["coverage"] = {"samples": len(rows), "speakers": len(result["by_speaker"]),
                          "noisy_samples": sum(r["noise_present"] == "true" for r in rows)}
    result["quantity_gate_met"] = (origins == {"real"} and len(rows) >= 20 and
                                   result["coverage"]["speakers"] >= 3 and result["coverage"]["noisy_samples"] >= 5)
    result["limitation"] = "Metadados declarados; não verifica autenticidade, consentimento assinado ou existência dos áudios."
    if partial_schema:
        result.update(received=received, transcribed=completed, human_references=verified,
                      latency_by_speaker_and_environment=latency,
                      environments=sorted({r["environment_id"] for r in rows}),
                      model_revision=next(iter(configurations))[1])
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="WER real ou de desenvolvimento, sempre identificado")
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        result = score_manifest(args.manifest)
        serialized = json.dumps(result, ensure_ascii=False, indent=2)
        if args.output:
            # Não sobrescreve evidência anterior.
            with args.output.open("x", encoding="utf-8") as stream:
                stream.write(serialized + "\n")
        else:
            print(serialized)
        return 0
    except (ValidationError, OSError) as exc:
        print(f"Avaliação não concluída: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
