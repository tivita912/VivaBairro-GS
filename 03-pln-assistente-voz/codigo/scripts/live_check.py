"""Verificações explicitamente pagas, com orçamento persistente e dados de desenvolvimento."""
import argparse
from dataclasses import replace
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.api_config import APIConfig
from src.api_runtime import APIRuntime, CallBudget
from src.config import Settings
from src.errors import VivaBairroError


def main():
    parser = argparse.ArgumentParser(description="Chamadas reais somente mediante --run")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--auth-only", action="store_true")
    parser.add_argument("--audio-only", action="store_true", help="Reverifica apenas a falha de áudio com texto sintético já registrado")
    args = parser.parse_args()
    if not args.run:
        print("Nenhuma chamada executada. Use --run para autorizar os testes reais limitados.")
        return 0
    settings = replace(Settings.load(), retries=0)
    folder = ROOT / ".runtime"
    folder.mkdir(exist_ok=True)
    lock = folder / "live_check.lock"
    try:
        lock_file = lock.open("x")
    except FileExistsError:
        print("Outra verificação está em execução ou há uma trava de execução interrompida. Nenhuma chamada realizada.")
        return 1
    evidence_path = ROOT / "docs/stage02_live.json"
    evidence = json.loads(evidence_path.read_text(encoding="utf-8")) if evidence_path.exists() else {"runs": []}
    run = {"recorded_at": datetime.now(timezone.utc).isoformat(),
           "kind": "technical_development_not_academic_evaluation"}
    runtime = None
    try:
        config = APIConfig.load()
        budget = CallBudget(settings.auto_test_calls, ledger=folder / "live_budget.json")
        runtime = APIRuntime(config, settings, budget)
        budget.require_capacity(2 if args.audio_only else 1 if args.auth_only else 6)
        run["configuration"] = config.public_status()
        if args.audio_only:
            previous = [r["components"]["llm_turn_1"]["answer"] for r in evidence["runs"]
                        if r.get("components", {}).get("llm_turn_1", {}).get("ok")]
            if not previous:
                raise VivaBairroError("Não há texto de desenvolvimento previamente registrado para esta verificação.")
            run["components"] = run_audio(runtime, previous[-1])
        else:
            run["authentication"] = runtime.authenticate()
            print("Autenticação: OK. Disponibilidade efetiva será verificada por componente.")
        if not args.auth_only and not args.audio_only:
            run["components"] = run_components(runtime)
        run["ok"] = all(item.get("ok", True) for item in run.get("components", {}).values())
    except VivaBairroError as exc:
        run["ok"] = False
        run["safe_error"] = str(exc)
        run["error_code"] = getattr(exc, "code", "configuration_or_budget")
        print("Verificação interrompida: " + str(exc))
    except Exception:
        run["ok"] = False
        run["safe_error"] = "Falha técnica local. Nenhum corpo de erro do provedor foi registrado."
        print(run["safe_error"])
    finally:
        if runtime:
            run["request_attempts_total"] = runtime.budget.used
            run["requests"] = runtime.records
        evidence["runs"].append(run)
        evidence_path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        lock_file.close()
        lock.unlink()
    return int(not run["ok"])


def run_components(runtime):
    from src.conversation import Conversation
    from src.knowledge import KnowledgeBase
    from src.llm import OpenAILLM
    results = {}
    conversation = Conversation()
    knowledge = KnowledgeBase.load(ROOT / "knowledge/urban_guidance.json")
    llm = OpenAILLM(runtime)
    questions = ["Há uma calçada quebrada perto de uma praça e dificulta a passagem de cadeirantes. Como descrevo isso?",
                 "E onde eu faço isso?",
                 "Escreva uma receita de bolo de chocolate."]
    first_answer = None
    for index, question in enumerate(questions, 1):
        try:
            messages = conversation.messages(question, knowledge, ROOT / "prompts/system_v1.txt")
            answer = llm.generate(messages)
            conversation.commit(question, answer.text)
            first_answer = first_answer or answer.text
            results[f"llm_turn_{index}"] = {"ok": True, "input_origin": "synthetic_development_text",
                "question": question, "answer": answer.text, "model_reported": answer.model_revision,
                "usage": answer.usage, "messages_sent": len(messages), "human_accuracy_rating": None}
            print(f"LLM turno {index}: resposta real recebida.")
        except VivaBairroError as exc:
            results[f"llm_turn_{index}"] = {"ok": False, "safe_error": str(exc)}
            print(f"LLM turno {index}: " + str(exc))
            break  # Não chama continuações sem o contexto anterior.
    if first_answer:
        results.update(run_audio(runtime, first_answer))
    results["human_voice_e2e"] = {"status": "pending_authorized_human_recordings", "ok": True,
                                   "criterion_met": False}
    return results


def run_audio(runtime, first_answer):
    from src.tts import OpenAIRealtimeTTS
    from src.stt import OpenAISTT
    from src.audio_input import prepare_audio
    from src.privacy import Consent
    from tempfile import TemporaryDirectory
    import wave
    class DevelopmentObservedTTS(OpenAIRealtimeTTS):
        last_transcript = None
        async def _generate(self, text):
            result = await super()._generate(text)
            self.last_transcript = result[1]
            return result
    tts = DevelopmentObservedTTS(runtime)
    results = {}
    with TemporaryDirectory(prefix="vivabairro-voicecheck-") as folder:
        directory = Path(folder)
        try:
            audio = tts.synthesize(first_answer, directory)
            with wave.open(str(audio.path), "rb") as stream:
                duration = stream.getnframes() / stream.getframerate()
            results["tts"] = {"ok": True, "audio_origin": "OpenAI_synthetic_not_human",
                "duration_seconds": duration, "bytes": audio.path.stat().st_size,
                "model_reported": audio.model_revision, "voice": audio.voice_id,
                "transcript_verified": audio.transcript_verified, "usage": audio.usage,
                "listened_by_human": False, "retained": False}
            print("TTS: WAV real gerado; transcrição da síntese confere com o texto.")
            consent = Consent.grant(external_audio=True, external_text=True)
            with prepare_audio(audio.path, "upload", consent, runtime.settings, directory / "stt") as prepared:
                transcription = OpenAISTT(runtime).transcribe(prepared)
            results["stt_synthetic_roundtrip"] = {"ok": True, "audio_origin": "synthetic_not_academic_corpus",
                "text": transcription.text, "usage": transcription.usage,
                "model_reported": transcription.model_revision}
            print("STT: transcrição real de áudio sintético recebida; não conta como gravação humana.")
        except VivaBairroError as exc:
            stage = "stt_synthetic_roundtrip" if "tts" in results else "tts"
            results[stage] = {"ok": False, "safe_error": str(exc), "error_code": getattr(exc, "code", "validation"),
                "synthetic_expected_text": first_answer, "synthetic_returned_transcript": tts.last_transcript}
            print(stage + ": " + str(exc))
    return results


if __name__ == "__main__":
    raise SystemExit(main())
