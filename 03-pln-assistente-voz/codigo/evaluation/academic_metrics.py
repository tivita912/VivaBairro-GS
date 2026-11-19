"""Apura evidências acadêmicas locais. Nenhuma função acessa provedores."""
import argparse
import csv
from html import escape
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean, median

from evaluation.score_stt import score_manifest
from src.errors import ValidationError
from src.metrics import percentage, rating_mean

ROOT = Path(__file__).resolve().parent
CATEGORIES = ("in_scope", "continuation", "out_of_scope")
STAGES = ("input", "stt", "context", "llm", "speech_text", "tts", "processing_total", "server_turn", "input_audio_duration",
          "request_body_receive", "turn_http", "audio_download", "player_prepare", "send_to_playing")


def read(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def real(rows):
    if any(row.get("data_origin") != "real" for row in rows):
        raise ValidationError("Resultados acadêmicos só aceitam linhas de origem real.")


def unique(rows, *fields):
    keys = [tuple(row.get(field, "").strip() for field in fields) for row in rows]
    if any(not all(key) for key in keys) or len(set(keys)) != len(keys):
        raise ValidationError("IDs ausentes ou duplicados: " + ", ".join(fields))


def number(value, minimum=0, maximum=math.inf):
    try:
        result = float(value)
    except (ValueError, TypeError):
        raise ValidationError("Valor numérico ausente ou inválido.") from None
    if not math.isfinite(result) or not minimum <= result <= maximum:
        raise ValidationError("Valor numérico fora do intervalo.")
    return result


def flag(value):
    if value not in {"true", "false"}:
        raise ValidationError("Use true ou false em julgamentos concluídos.")
    return value == "true"


def describe(values):
    if not values:
        return None
    return {"n": len(values), "mean": mean(values), "median": median(values),
            "min": min(values), "max": max(values)}


def assess_llm(catalog, rows):
    real(rows)
    unique(rows, "question_id")
    if len({row["run_id"] for row in rows}) != 1 or not rows[0]["run_id"]:
        raise ValidationError("Use uma execução por relatório de LLM.")
    questions = {r["question_id"]: r for r in catalog}
    if Counter(r["category"] for r in catalog) != dict(zip(CATEGORIES, (20, 5, 5))) or len(questions) != 30:
        raise ValidationError("O catálogo LLM precisa de 20 casos de domínio, 5 continuações e 5 recusas.")
    groups = {name: [] for name in CATEGORIES}
    refusals = []
    evaluators = Counter()
    skipped = Counter()
    for row in rows:
        case = questions.get(row["question_id"])
        if case is None:
            raise ValidationError("Caso LLM fora do catálogo.")
        if row["error_type"]:
            skipped["execution_failure"] += 1
            continue
        if row["review_status"] in {"pending", "ambiguous", ""}:
            skipped["not_reviewed"] += 1
            continue
        if row["review_status"] != "reviewed" or not all(row[k].strip() for k in (
                "actual_answer", "model_id", "model_revision", "prompt_version",
                "knowledge_version", "evaluator_id", "notes")):
            raise ValidationError("A revisão deve registrar resposta, configuração, avaliador e justificativa.")
        groups[case["category"]].append(flag(row["correct"]))
        evaluators["ia" if "IA_" in row["evaluator_id"].upper() else "humano" if row["evaluator_id"] in {"P01", "P02", "P03"} else "outro_identificado"] += 1
        if case["category"] == "out_of_scope":
            refusals.append(flag(row["refusal_appropriate"]))
    all_judgments = [judgment for group in groups.values() for judgment in group]
    return {"complete": len(all_judgments) == 30, "count_attempted": len(rows),
            "judgment_sources": dict(evaluators),
            "missing_cases": 30 - len(rows), "accuracy_denominator": len(all_judgments), "refusal_denominator": len(refusals),
            "accuracy_all_percent": percentage(all_judgments),
            "refusal_percent": percentage(refusals),
            "categories": {k: {"n": len(v), "correct_percent": percentage(v), "failures": v.count(False)}
                           for k, v in groups.items()}, "excluded_by_reason": dict(skipped)}


def assess_tts(samples, ratings, folder=ROOT):
    real(samples)
    unique(samples, "sample_id")
    unique(ratings, "sample_id", "evaluator_id")
    allowed = {row["sample_id"] for row in samples if row["status"] == "success"}
    expected = {f"T{n:02d}" for n in range(1, 11)}
    if any(row["status"] not in {"success", "failed"} or row["sample_id"] not in expected for row in samples):
        raise ValidationError("Sínteses devem usar T01–T10 e registrar sucesso ou falha.")
    for row in samples:
        if row["status"] == "success" and not all(row[k].strip() for k in (
                "text", "adapted_text", "voice_id", "provider", "provider_version", "audio_path")):
            raise ValidationError("Metadados TTS incompletos.")
        if row["status"] == "success":
            audio = Path(row["audio_path"])
            if not audio.is_absolute():
                audio = folder / audio
            if not audio.is_file() or not audio.stat().st_size:
                raise ValidationError("A amostra TTS declarada deve existir e conter áudio.")
    scores = defaultdict(list)
    for row in ratings:
        if row["sample_id"] not in allowed:
            raise ValidationError("Avaliação sem amostra TTS concluída.")
        scores[row["sample_id"]].append(tuple(int(number(row[k],1,5)) for k in (
            "clarity_1_to_5", "naturalness_1_to_5")))
        if any(not number(row[k],1,5).is_integer() for k in ("clarity_1_to_5", "naturalness_1_to_5")):
            raise ValidationError("Use notas inteiras de 1 a 5.")
    pairs = [pair for group in scores.values() for pair in group]
    return {
        "complete": len(allowed) == 10 and all(len(scores.get(key, [])) >= 3 for key in allowed),
        "synthesized": len(allowed), "ratings": len(ratings), "failed": len(samples)-len(allowed),
        "per_sample": {key: {"ratings": len(group), "clarity": rating_mean([pair[0] for pair in group]),
                             "naturalness": rating_mean([pair[1] for pair in group])}
                       for key, group in sorted(scores.items())},
        "overall": {"clarity": rating_mean([pair[0] for pair in pairs]),
                    "naturalness": rating_mean([pair[1] for pair in pairs])},
        "distribution": {"clarity": dict(Counter(pair[0] for pair in pairs)),
                         "naturalness": dict(Counter(pair[1] for pair in pairs))},
    }


def assess_e2e(rows):
    real(rows)
    unique(rows, "conversation_id", "turn_id")
    conversations = defaultdict(list)
    measured = []
    unmeasured = 0
    failures = 0
    for row in rows:
        if row["status"] not in {"success", "failed", "incomplete"} or not all(
            row[k].strip() for k in ("participant_id", "consent_id", "environment_id")
        ):
            raise ValidationError("Turno sem status, participante, autorização ou ambiente.")
        conversations[row["conversation_id"], row.get("collection_session_id", "")].append(row)
        if row["status"] == "failed":
            failures += 1
        elif (row["status"] == "success" and row.get("interactive_confirmed") == "true" and
              (int(row.get("logical_turn") or row["turn_id"]) == 1 or row.get("heard_previous_response") == "true") and
              row["playback_measurement"] == "player_event_proxy" and row["playback_start_seconds"]):
            boundary = {"microphone": "capture_start_to_playing", "upload": "file_selected_to_playing"}
            if boundary.get(row["input_source"]) != row["playback_boundary"]:
                raise ValidationError("Origem de latência de reprodução incompatível.")
            measured.append(row)
        else:
            unmeasured += 1
    sessions = set()
    timelines = {}
    for (key, collection), turns in conversations.items():
        valid = [r for r in measured if (r["conversation_id"], r.get("collection_session_id", "")) == (key, collection)]
        indices = sorted(int(r.get("logical_turn") or r["turn_id"]) for r in valid)
        if len({r["participant_id"] for r in turns}) == 1 and len(indices) >= 3 and indices == list(range(1, len(indices) + 1)):
            sessions.add(key)
        timelines[collection or key] = [{"turn":r["turn_id"],"source":r["input_source"],
                           "seconds":number(r["playback_start_seconds"])} for r in valid]
    results = {"complete": len(sessions) >= 10, "successful_sessions": len(sessions),
               "rows": len(rows), "failed_rows": failures, "without_playback": unmeasured,
               "per_stage_seconds": {stage: describe([number(r[stage+"_seconds"])
                                     for r in measured if r[stage+"_seconds"]]) for stage in STAGES},
               "by_source_seconds": {src: describe([number(r["playback_start_seconds"])
                                     for r in measured if r["input_source"] == src])
                                     for src in ("microphone","upload")},
               "scenarios": timelines}
    return results


def assess_comparison(rows):
    real(rows)
    active = [r for r in rows if not flag(r["warmup"]) and not flag(r["cold_start"])]
    if not active:
        return {"complete": False, "warmup_or_cold_rows": len(rows)}
    unique(active, "config_id", "sample_id", "run_index")
    design = {(r["component"], r["dataset_version"], r["environment_id"], r["quality_metric"]) for r in active}
    groups = defaultdict(dict)
    for r in active:
        groups[r["config_id"]][(r["sample_id"], r["run_index"])] = r
    if len(groups) != 2 or len(design) != 1 or not all(next(iter(design))):
        raise ValidationError("Use duas opções do mesmo componente, corpus, ambiente e métrica.")
    keys = [set(items) for items in groups.values()]
    if keys[0] != keys[1]:
        return {"complete": False, "paired": len(keys[0] & keys[1]), "unpaired": len(keys[0] ^ keys[1])}
    return {"complete": True, "n_pairs": len(keys[0]), "design": list(next(iter(design))),
            "warmup_or_cold_rows": len(rows)-len(active),
            "configurations": {
                key: {"quality": describe([number(r["quality_value"]) for r in group.values()]),
                      "seconds": describe([number(r["latency_seconds"]) for r in group.values()])}
                for key, group in groups.items()}}


def chart(path, title, unit, entries):
    if not entries:
        return
    width, height = 850, 105 + len(entries)*46
    peak = max(value for _, value in entries) or 1
    lines = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}">',
             '<rect width="100%" height="100%" fill="#f5f5ed"/>',
             f'<text x="29" y="38" fill="#142923" font-size="24" font-family="Segoe UI">{escape(title)}</text>']
    for i,(name,value) in enumerate(entries):
        y = 71+i*46
        length = 435*value/peak
        lines.extend([f'<text x="29" y="{y+18}" font-size="16" font-family="Segoe UI">{escape(name)}</text>',
                      f'<rect x="245" y="{y}" width="{length:.2f}" height="25" fill="#185440"/>',
                      f'<text x="705" y="{y+18}" font-size="16" font-family="Segoe UI">{value:.2f} {escape(unit)}</text>'])
    with path.open("x", encoding="utf-8") as output:
        output.write("\n".join(lines + ["</svg>"]))


def run(folder):
    tables = {name: (read(path) if (path := folder / f"{name}.csv").exists() else []) for name in (
        "stt_manifest", "llm_questions", "llm_ratings", "tts_samples", "tts_ratings", "e2e_sessions", "model_comparison")}
    if tables["stt_manifest"]:
        real(tables["stt_manifest"])
    human = folder / "results/llm_revisao_humana.csv"
    if human.is_file():
        reviewed = read(human)
        original = {r["question_id"]: (r["run_id"], r["actual_answer"]) for r in tables["llm_ratings"]}
        if any(original.get(r["question_id"]) != (r["run_id"], r["actual_answer"]) or r["evaluator_id"] not in {"P01", "P02", "P03"}
               for r in reviewed) or not reviewed:
            raise ValidationError("Revisão humana LLM sem vínculo com as respostas originais.")
    else:
        reviewed = tables["llm_ratings"]
    if tables["tts_ratings"] and not tables["tts_samples"]:
        raise ValidationError("Notas TTS encontradas sem amostras sintetizadas.")
    comparison_path = folder / "results/stt_comparacao.json"
    comparison = (json.loads(comparison_path.read_text(encoding="utf-8")) if comparison_path.is_file()
                  else assess_comparison(tables["model_comparison"]) if tables["model_comparison"] else None)
    result = {
        "rows": {name: len(rows) for name,rows in tables.items()},
        "stt": score_manifest(folder/"stt_manifest.csv") if tables["stt_manifest"] else None,
        "llm": assess_llm(tables["llm_questions"], reviewed) if reviewed else None,
        "tts": assess_tts(tables["tts_samples"], tables["tts_ratings"], folder) if tables["tts_samples"] else None,
        "e2e": assess_e2e(tables["e2e_sessions"]) if tables["e2e_sessions"] else None,
        "comparison": comparison,
    }
    return result


def export(result, destination):
    destination.mkdir(parents=True, exist_ok=False)
    (destination/"metrics.json").write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    if stt := result["stt"]:
        for key,label in (("by_speaker","WER por participante"), ("by_noise","WER por presença de ruído")):
            names = {"true": "Com ruído", "false": "Limpo"}
            chart(destination/f"stt_{key}.svg",label,"%", [(names.get(k,k),v["wer_corpus"]*100)
                  for k,v in stt[key].items()])
    if llm := result["llm"]:
        chart(destination/"llm.svg","Acerto por categoria","%",
              [(k,v["correct_percent"]) for k,v in llm["categories"].items() if v["correct_percent"] is not None])
    if tts := result["tts"]:
        for key,label in (("clarity","Clareza"),("naturalness","Naturalidade")):
            chart(destination/f"tts_{key}.svg",f"{label} por amostra","/ 5",
                  [(k,v[key]) for k,v in tts["per_sample"].items()])
    if e2e := result["e2e"]:
        chart(destination/"e2e_etapas.svg","Latência média por etapa","s",
              [(k,v["mean"]) for k,v in e2e["per_stage_seconds"].items() if v])
    if (comparison := result["comparison"]) and comparison.get("groups"):
        for i, group in enumerate(comparison["groups"], 1):
            chart(destination/f"stt_comparacao_wer_{i}.svg", "WER no conjunto pareado", "%",
                  [(label, 100 * group[label]["wer_corpus"]) for label in ("A", "B")])
    elif comparison and comparison["complete"] and "configurations" in comparison:
        for key,unit in (("quality",""),("seconds","s")):
            chart(destination/f"comparacao_{key}.svg",f"Comparação pareada · {key}",unit,
                  [(k,v[key]["mean"]) for k,v in comparison["configurations"].items()])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dados", type=Path, default=ROOT)
    parser.add_argument("--saida", type=Path, required=True, help="Nova pasta para o resultado")
    args = parser.parse_args()
    try:
        export(run(args.dados),args.saida)
    except (ValidationError, OSError, KeyError, TypeError) as failure:
        parser.exit(1,f"Avaliação não concluída: {failure}\n")
    print(f"Resultado local: {args.saida}")


if __name__ == "__main__":
    main()
