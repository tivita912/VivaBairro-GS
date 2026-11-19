"""Valida ou executa uma rodada formal LLM/TTS com orçamento explícito e evidência por caso."""

import argparse
from collections import Counter
from dataclasses import replace
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import re
from time import perf_counter

from evaluation.run_stt import ROOT, atomic_write, digest, environment, read, read_optional, write_csv
from src.api_config import APIConfig
from src.config import PROJECT_ROOT, Settings
from src.conversation import Conversation
from src.errors import ProviderError, ValidationError, VivaBairroError
from src.knowledge import KnowledgeBase
from src.llm import OpenAILLM
from src.speech_text import PortugueseSpeechAdapter
from src.tts import OpenAIRealtimeTTS

PROMPT = PROJECT_ROOT / "prompts/system_v1.txt"
BASE = PROJECT_ROOT / "knowledge/urban_guidance.json"
LLM_MODEL = "gpt-6-luna"
TTS_MODEL = "gpt-realtime-2.1-mini"
TTS_VOICE = "marin"
LLM_FIELDS = """run_id question_id model_id model_revision prompt_version knowledge_version actual_answer correct
                refusal_appropriate evaluator_id llm_seconds error_type notes data_origin review_status history_case_id""".split()
TTS_FIELDS = """run_id sample_id text adapted_text voice_id provider provider_version audio_path tts_seconds environment_id
                synthesized_on data_origin status notes model_id audio_sha256""".split()
JUDGMENTS = {"correct", "refusal_appropriate", "evaluator_id", "notes", "review_status"}


def catalog(component):
    path = ROOT / ("llm_questions.csv" if component == "llm" else "tts_prompts.csv")
    rows = read(path)
    key = "question_id" if component == "llm" else "sample_id"
    prefix, count = ("Q", 30) if component == "llm" else ("T", 10)
    if [r[key] for r in rows] != [f"{prefix}{n:02d}" for n in range(1, count + 1)]:
        raise ValidationError("IDs duplicados, fora de ordem ou ausentes no catálogo.")
    if component == "llm":
        expected = ["in_scope"] * 20 + ["continuation"] * 5 + ["out_of_scope"] * 5
        if [r["category"] for r in rows] != expected:
            raise ValidationError("Esperado 20 domínio, 5 continuações, 5 fora do escopo.")
        for row, parent in zip(rows[20:25], (rows[i] for i in (0, 4, 8, 12, 16))):
            if (row["previous_question_id"], row["context"], row["conversation_id"], row["turn_index"]) != (
                    parent["question_id"], parent["question"], parent["conversation_id"], "2"):
                raise ValidationError("Uma continuação diverge do antecedente registrado.")
        if any(not all(r[field].strip() for field in ("question", "expected_answer", "required_elements", "forbidden_elements")) for r in rows):
            raise ValidationError("O catálogo LLM precisa dos critérios humanos antes da execução.")
    elif any(not r["text"].strip() for r in rows):
        raise ValidationError("Uma amostra de TTS não contém texto.")
    return path, rows, key


def design(component, path, settings):
    env_id, env = environment(settings)
    result = dict(component=component, sdk=env["openai"], dataset_sha256=digest(path),
                  environment_id=env_id, environment=env, model=LLM_MODEL if component == "llm" else TTS_MODEL)
    if component == "llm":
        result.update(prompt_sha256=digest(PROMPT), knowledge_sha256=digest(BASE),
                      knowledge_version=KnowledgeBase.load(BASE).version,
                      max_output_tokens=settings.max_output_tokens, max_response_chars=settings.max_response_chars)
    else:
        result.update(adapter_sha256=digest(PROJECT_ROOT / "src/speech_text.py"), voice=TTS_VOICE,
                      tts_max_tokens=settings.tts_max_tokens)
    result["design_id"] = sha256(json.dumps(result, sort_keys=True).encode()).hexdigest()[:16]
    return result


def estimate(component, n, settings):
    if component == "llm":
        return n * (8000 * 0.10 + settings.max_output_tokens * 0.50) / 1_000_000
    return n * (2000 * 0.60 + settings.tts_max_tokens * 20) / 1_000_000


def execute(component, cases, key, destination, runtime, spec, retry=False):
    by_id = {row[key]: row for row in cases}
    llm = OpenAILLM(runtime) if component == "llm" else None
    kb = KnowledgeBase.load(BASE) if component == "llm" else None
    tts = OpenAIRealtimeTTS(runtime) if component == "tts" else None
    adapter = PortugueseSpeechAdapter() if tts else None
    for case in cases:
        case_id = case[key]
        record = destination / f"{case_id}.json"
        if runtime.budget.used >= runtime.budget.limit:
            continue
        if record.exists():
            previous_state = json.loads(record.read_text(encoding="utf-8"))["status"]
            if not retry or previous_state not in {"failed", "running"}:
                continue
        parent = case.get("previous_question_id", "")
        session = Conversation(runtime.settings.history_turns) if llm else None
        if parent:
            previous = destination / f"{parent}.json"
            if not previous.exists():
                continue
            precedent = json.loads(previous.read_text(encoding="utf-8"))
            if precedent["status"] != "success":
                continue
            session.commit(by_id[parent]["question"], precedent["actual_answer"])
        now = datetime.now(timezone.utc).isoformat()
        if record.exists():
            archive_id = now.replace(":", "")
            record.rename(destination / f"{case_id}-anterior-{archive_id}.json")
            partial_audio = destination / f"{case_id}.wav"
            if tts and partial_audio.exists():
                partial_audio.rename(destination / f"{case_id}-anterior-{archive_id}.wav")
        result = dict(status="running", design_id=spec["design_id"], run_id=spec["design_id"], timestamp=now, data_origin="real",
                      model_id=spec["model"], environment_id=spec["environment_id"], **{key: case_id})
        # Um caso iniciado exige reconciliação manual após interrupção, para evitar cobrar novamente.
        try:
            with record.open("x", encoding="utf-8") as stream:
                json.dump(result, stream, ensure_ascii=False)
        except FileExistsError:
            continue
        started = perf_counter()
        try:
            if llm:
                result.update(run_id=spec["design_id"], history_case_id=parent, prompt_version=spec["prompt_sha256"],
                              knowledge_version=spec["knowledge_version"], review_status="pending")
                answer = llm.generate(session.messages(case["question"], kb, PROMPT))
                result.update(actual_answer=answer.text, model_revision=answer.model_revision, usage=answer.usage)
            else:
                adapted = adapter.adapt(case["text"])
                result.update(text=case["text"], adapted_text=adapted.text, notes=" ".join(adapted.warnings), synthesized_on=now)
                audio = tts.synthesize(adapted.text, destination)
                target = destination / f"{case_id}.wav"
                audio.path.rename(target)
                result.update(voice_id=audio.voice_id, provider=audio.provider, provider_version=audio.model_revision,
                              audio_path=target.relative_to(ROOT).as_posix(), audio_sha256=digest(target), usage=audio.usage)
            result.update(status="success", error_type="")
        except VivaBairroError as error:
            result.update(status="failed", error_type=error.code if isinstance(error, ProviderError) else type(error).__name__)
        result[component + "_seconds"] = perf_counter() - started
        atomic_write(record, lambda s: json.dump(result, s, ensure_ascii=False, indent=2))


def canonical_rows(component, key, spec):
    canonical = ROOT / ("llm_ratings.csv" if component == "llm" else "tts_samples.csv")
    previous = {row[key]: row for row in read_optional(canonical)}
    if any(r.get("run_id") != spec["design_id"] for r in previous.values()):
        raise ValidationError("A planilha contém outra rodada. Preserve a planilha e o histórico antes de trocar de desenho.")
    return canonical, previous


def export(component, destination, cases, key, spec):
    fields = LLM_FIELDS if component == "llm" else TTS_FIELDS
    canonical, previous = canonical_rows(component, key, spec)
    rows = []
    for case in cases:
        record = destination / f"{case[key]}.json"
        if record.exists():
            result = json.loads(record.read_text(encoding="utf-8"))
            if result["status"] == "running":
                continue
            existing = previous.pop(case[key], {})
            if component == "llm" and existing.get("actual_answer") == result.get("actual_answer"):
                result.update({field: existing[field] for field in JUDGMENTS if field in existing})
            rows.append(result)
    write_csv(canonical, fields, rows + list(previous.values()))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("component", choices=("llm", "tts"))
    parser.add_argument("--autorizar-api", type=int, metavar="N", help="Teto de chamadas desta rodada, após autorização de custo")
    parser.add_argument("--exportar", action="store_true", help="Atualiza a planilha a partir de resultados já gravados")
    parser.add_argument("--repetir-falhas", action="store_true", help="Repete falhas ou interrupções com o novo teto autorizado")
    args = parser.parse_args()
    if args.repetir_falhas and args.autorizar_api is None:
        parser.error("--repetir-falhas exige --autorizar-api")
    try:
        component = args.component
        path, cases, key = catalog(component)
        settings = replace(Settings.load(), retries=0)
        spec = design(component, path, settings)
        destination = ROOT / "results" / f"{component}_rodadas" / spec["design_id"]
        pending = [r for r in cases if not (destination / f"{r[key]}.json").exists()]
        print(json.dumps(dict(model=spec["model"], voice=spec.get("voice"), pending=len(pending),
                              cost_scenario_usd=round(estimate(component, len(pending), settings), 5),
                              design=spec["design_id"], categories=dict(Counter(r.get("category", "tts") for r in cases))),
                         ensure_ascii=False))
        if args.autorizar_api is not None:
            if not 1 <= args.autorizar_api <= len(cases):
                raise ValidationError("Teto de chamadas fora do tamanho do catálogo.")
            canonical_rows(component, key, spec)
            from src.api_runtime import APIRuntime, CallBudget
            config = APIConfig.load()
            if getattr(config, component + "_model") != spec["model"] or (component == "tts" and config.tts_voice != spec["voice"]):
                raise ValidationError("Modelo ou voz diverge do preflight de custo.")
            destination.mkdir(parents=True, exist_ok=True)
            meta = destination / "design.json"
            if not meta.exists():
                atomic_write(meta, lambda s: json.dump(spec, s, ensure_ascii=False, indent=2))
            execute(component, cases, key, destination, APIRuntime(config, settings, CallBudget(args.autorizar_api)), spec,
                    retry=args.repetir_falhas)
        if args.exportar or args.autorizar_api:
            export(component, destination, cases, key, spec)
    except (OSError, VivaBairroError) as error:
        parser.exit(1, f"Rodada interrompida: {error}\n")


if __name__ == "__main__":
    main()
