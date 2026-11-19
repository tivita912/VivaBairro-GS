"""Pré-voo reproduzível da avaliação, sem rede ou transcrição."""

import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import wave

import av

from evaluation import academic_metrics
from evaluation.preparar_kit_tts import verify_samples
from evaluation.run_stt import PLAN, atomic_write, digest, history, read_optional
from scripts.transferir_gs import VIDEO
from src.config import PROJECT_ROOT
from src.errors import ValidationError

VIDEO_SHA = "0619e9224da931a5204d8fda2be6bba2e360d98e771c9612662b973539953687"


def inspect(root=PROJECT_ROOT):
    e = root / "evaluation"
    result = e / "results"
    manifest = read_optional(e / "stt_manifest.csv")
    review = {r["sha256"]: r for r in read_optional(result / "stt_referencias_revisao.csv")}
    labels = {r["sample_id"] for r in manifest}
    attempts = {r["attempt"]: r for r in history(result).values()}
    problems = []
    recorded = [r for r in manifest if r.get("transcription_completed") == "true"]
    checks = {}
    observed = set()
    for row in manifest:
        path = (e / row["audio_path"]).resolve()
        sha = row.get("audio_sha256")
        key = row["sample_id"]
        if not path.is_relative_to(e / "audio") or not path.is_file() or digest(path) != sha or sha in observed:
            problems.append(f"{key}: original ausente, duplicado ou divergente.")
        observed.add(sha)
        linked = review.get(sha, {})
        if linked.get("sample_id") != key:
            problems.append(f"{key}: vínculo com revisão não confere.")
        if row.get("reference_status") == "VERIFICADA" and (
                linked.get("review_completed") != "true" or
                any(linked.get(field) != row[field] for field in ("reference_text", "reference_reviewed_by", "noise_present"))):
            problems.append(f"{key}: referência ou ruído diverge da revisão.")
        if row["transcription_completed"] == "true":
            attempt = attempts.get(row.get("attempt_id"), {})
            expected = {"sha256": sha, "hypothesis": row["hypothesis_text"], "prepared_sha256": row["prepared_sha256"],
                        "requested_model": row["model_id"], "consent_id": row["consent_id"], "stt_status": "TRANSCRITO"}
            if not row["consent_id"] or any(attempt.get(field) != value for field, value in expected.items()):
                problems.append(f"{key}: histórico da chamada não confere.")
    checks["integridade_stt"] = not problems and bool(manifest)
    try:
        metrics = academic_metrics.run(e)
    except (OSError, ValueError, KeyError, TypeError, ValidationError) as error:
        problems.append(f"Apuração: {error}")
        metrics = dict.fromkeys(("stt", "llm", "tts", "e2e", "comparison"))
    stt, llm, tts, e2e, comp = (metrics[key] or {} for key in ("stt", "llm", "tts", "e2e", "comparison"))
    checks["stt_20_vozes_3_ruidos_5_wer"] = checks["integridade_stt"] and labels == set(PLAN) and bool(stt.get("quantity_gate_met"))
    checks["llm_30_com_avaliador_identificado"] = bool(llm.get("complete")) and sum(
        llm.get("judgment_sources", {}).get(key, 0) for key in ("ia", "humano")) == 30
    checks["tts_10_e_tres_avaliadores"] = False
    synth = []
    if (e / "tts_samples.csv").is_file() and read_optional(e / "tts_samples.csv"):
        try:
            synth = verify_samples(e)
            hashes = {r["sample_id"]:r["sha256"] for r in synth}
            ratings = read_optional(e / "tts_ratings.csv")
            checks["tts_10_e_tres_avaliadores"] = bool(tts.get("complete")) and all(
                r["evaluator_id"] in {"P01", "P02", "P03"} and r.get("audio_sha256") == hashes.get(r["sample_id"])
                for r in ratings)
        except (OSError, ValueError, KeyError, wave.Error, ValidationError) as error:
            problems.append(f"TTS: {error}")
    checks["e2e_10_sessoes_interativas_medidas"] = bool(e2e.get("complete"))
    for row in read_optional(e / "e2e_sessions.csv"):
        if row["status"] != "success":
            continue
        path = (e / row["audio_evidence_path"]).resolve()
        required = ("input_audio_duration_seconds", "stt_seconds", "llm_seconds", "speech_text_seconds",
                    "tts_seconds", "processing_total_seconds", "playback_start_seconds")
        if not path.is_relative_to(result) or not path.is_file() or digest(path) != row.get("audio_sha256") or any(
                not row.get(key, "").strip() for key in required):
            problems.append(f"{row['conversation_id']}/{row['turn_id']}: WAV ou tempos ausentes.")
            checks["e2e_10_sessoes_interativas_medidas"] = False
    pairs = [pair for group in comp.get("groups", []) for pair in group["pairs"]]
    expected_pairs = {(r["sample_id"], r["audio_sha256"], r["attempt_id"], r.get("reference_text")) for r in recorded
                      if r.get("reference_status") == "VERIFICADA"}
    from hashlib import sha256
    fingerprints = {(sid, sha, attempt, sha256(ref.encode()).hexdigest()) for sid, sha, attempt, ref in expected_pairs}
    checks["comparacao_duas_configuracoes"] = bool(comp.get("complete")) and len(pairs) == len(fingerprints) == 20 and {
        (p["sample_id"], p["sha256"], p["call_id"], p.get("reference_sha256")) for p in pairs} == fingerprints
    video = root / VIDEO
    duration = None
    intact = video.is_file() and digest(video) == VIDEO_SHA
    if intact:
        with av.open(str(video)) as media:
            if media.duration and media.streams.audio and media.streams.video:
                duration = round(media.duration / av.time_base, 3)
    checks["video_ate_5_minutos"] = bool(duration and duration <= 300)
    essential = ["README.md", "requirements.txt", "app.py", "src/web.py", "evaluation/llm_questions.csv",
                 "evaluation/roteiros_stt.md", "evaluation/tts_prompts.csv", "docs/academic/metodologia.md"]
    checks["arquivos_obrigatorios"] = all((root / path).is_file() for path in essential)
    return dict(generated=datetime.now(timezone(timedelta(hours=-3))).isoformat(),
                stt=dict(recebidos=len(manifest), transcritos=len(recorded), referencias_verificadas=stt.get("human_references", 0),
                         ruidos_confirmados=stt.get("coverage", {}).get("noisy_samples", 0),
                         ids_ausentes=[key for key in PLAN if key not in labels]),
                llm=dict(casos_executados=llm.get("count_attempted", 0), julgamento=llm.get("judgment_sources", {}),
                         adequacao=llm.get("accuracy_all_percent"), recusas=llm.get("refusal_percent")),
                tts=dict(sinteses_reais=len(synth), avaliacoes_reais=tts.get("ratings", 0)),
                e2e=dict(conversas_medidas=e2e.get("successful_sessions", 0)), comparison=dict(pares=len(pairs)),
                video=dict(duracao_s=duration, sha256_valido=intact), gates=checks, problemas=problems), metrics


def summarize(info):
    stt, llm, tts, e2e = (info[k] for k in ("stt", "llm", "tts", "e2e"))
    return (f"STT {stt['recebidos']}/20, {stt['transcritos']} transcritos e {stt['referencias_verificadas']} revisados. "
            f"LLM {llm['casos_executados']}/30. TTS {tts['sinteses_reais']}/10 e {tts['avaliacoes_reais']}/30 notas. "
            f"E2E {e2e['conversas_medidas']}/10. Comparação {info['comparison']['pares']}/20 pares.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    info, _ = inspect()
    print(summarize(info))
    pending = [label for label, ok in info["gates"].items() if not ok]
    for item in [*pending, *info["problemas"]]:
        print("Pendente", item)
    if not args.dry_run:
        out = PROJECT_ROOT / "evaluation/results"
        out.mkdir(parents=True, exist_ok=True)
        atomic_write(out / "gs_prontidao.json", lambda s: json.dump(info, s, ensure_ascii=False, indent=2))
        report = PROJECT_ROOT / "docs/academic/PRONTIDAO_ATUAL.md"
        lines = ["# Estado verificável do VivaBairro Voz", "", summarize(info), "",
                 *[f"- [{'x' if ok else ' '}] {key}" for key, ok in info["gates"].items()], "",
                 *[f"- {p}" for p in info["problemas"]], "",
                 "A conferência automática complementa a revisão humana de consentimentos e a inspeção da entrega.", ""]
        atomic_write(report, lambda s: s.write("\n".join(lines)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
