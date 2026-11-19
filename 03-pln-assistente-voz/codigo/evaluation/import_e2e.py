"""Importa captura manual de um turno real de upload e preserva tentativas anteriores."""

import argparse
import csv
from datetime import date
import json
import math
from pathlib import Path
import wave

from evaluation.run_stt import ROOT, digest, has_consent, read, write_csv
from src.errors import ValidationError

EXTRA = ["collection_session_id", "logical_turn", "audio_sha256", "interactive_confirmed", "heard_previous_response"]
STAGES = ("input", "stt", "context", "llm", "speech_text", "tts")
SCENARIOS = {f"C{i:02d}" for i in range(1, 11)}


def import_capture(path, root=ROOT):
    with path.open(encoding="utf-8-sig") as stream:
        capture = json.load(stream)
    metrics = capture["metrics"]
    status = capture["status"]
    if capture["conversation_id"] not in SCENARIOS or status not in {"success", "failed", "incomplete"}:
        raise ValidationError("Informe C01–C10 e o estado real do turno.")
    for key in ("logical_turn", "turn_id"):
        if type(capture[key]) is not int or capture[key] < 1:
            raise ValidationError("Cada turno e tentativa precisa de um índice inteiro positivo.")
    date.fromisoformat(capture["recorded_on"])
    if not all(capture[k].strip() for k in ("participant_id", "collection_session_id", "environment_id")):
        raise ValidationError("Informe participante, sessão de coleta e ambiente.")
    if capture.get("consent_scope_confirmed") is not True or not has_consent(root, dict(capture, external_audio_authorized="true")):
        raise ValidationError("Informe um documento de consentimento para este fluxo externo.")
    source = metrics.get("input_source") or capture.get("input_source", "upload")
    boundary = {"upload": "file_selected_to_playing", "microphone": "capture_start_to_playing"}.get(source)
    if not boundary or metrics.get("playback_boundary") not in {None, boundary}:
        raise ValidationError("A origem da gravação diverge dos marcos de reprodução.")
    if source == "upload" and any(metrics.get(k) is not None for k in ("question_started_at", "capture_seconds", "capture_finalize_seconds", "question_end_to_playing_seconds")):
        raise ValidationError("Upload não mede a gravação original nem o fim da captura no WhatsApp.")
    path_csv = root / "e2e_sessions.csv"
    schema = path_csv if path_csv.exists() else root / "e2e_sessions.schema.csv"
    with schema.open(encoding="utf-8-sig", newline="") as stream:
        fields = list(csv.DictReader(stream).fieldnames)
    fields += [key for key in EXTRA if key not in fields]
    row = {k: capture.get(k, "") for k in fields}
    row.update(data_origin="real", input_source=source, transcription=capture.get("transcription", ""),
               response_text=capture.get("response", ""))
    for field in ("interactive_confirmed", "heard_previous_response"):
        row[field] = str(capture.get(field) is True).lower()
    for key in fields:
        if key in {"playback_boundary", "playback_measurement"} and metrics.get(key):
            row[key] = metrics[key]
        elif key.endswith("_seconds"):
            value = metrics.get("stage_seconds", {}).get(key.removesuffix("_seconds")) if key.removesuffix("_seconds") in STAGES else metrics.get(key)
            if value is not None and (type(value) not in {int, float} or not math.isfinite(value) or value < 0):
                raise ValidationError("Uma duração do navegador ou servidor é inválida.")
            row[key] = "" if value is None else value
    if status == "success" and (metrics.get("failed") or not row["transcription"].strip() or not row["response_text"].strip() or
            row["playback_measurement"] != "player_event_proxy" or row["playback_boundary"] != boundary or
            row["playback_start_seconds"] == "" or
            not row["audio_evidence_path"]):
        raise ValidationError("Sucesso exige textos, áudio real salvo e evento playing. Registre uma coleta incompleta se faltar evidência.")
    if status == "success" and (row["interactive_confirmed"] != "true" or
            (capture["logical_turn"] > 1 and row["heard_previous_response"] != "true")):
        raise ValidationError("Confirme a interação real e a escuta anterior antes de contar o turno acadêmico.")
    if status != "success" and not row["notes"].strip():
        raise ValidationError("Descreva a falha ou lacuna observada no turno.")
    if row["audio_evidence_path"]:
        audio = (root / row["audio_evidence_path"]).resolve()
        if not audio.is_relative_to(root / "results") or not audio.is_file():
            raise ValidationError("Salve o WAV de resposta na área privada evaluation/results/.")
        with wave.open(str(audio), "rb") as wav:
            if not wav.getnframes():
                raise ValidationError("O WAV de resposta está vazio.")
        row.update(audio_evidence_path=audio.relative_to(root).as_posix(), audio_sha256=digest(audio))
    existing = read(path_csv) if path_csv.exists() else []
    for prior in existing:
        if prior.get("collection_session_id") == row["collection_session_id"] and prior["conversation_id"] != row["conversation_id"]:
            raise ValidationError("Cada cenário precisa de uma sessão de navegador própria.")
        if prior["conversation_id"] == row["conversation_id"] and prior["turn_id"] == str(row["turn_id"]):
            if all(str(row.get(k, "")) == (prior.get(k) or "") for k in fields):
                return False
            raise ValidationError("Esse índice de tentativa já tem outra evidência. Preserve a linha e use um novo índice.")
    write_csv(path_csv, fields, [*existing, row])
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("captura", type=Path)
    args = parser.parse_args()
    try:
        print("Turno importado." if import_capture(args.captura) else "Turno já importado.")
    except (OSError, ValueError, KeyError, TypeError, wave.Error, ValidationError) as error:
        parser.exit(1, f"Captura inválida: {error}\n")


if __name__ == "__main__":
    main()
