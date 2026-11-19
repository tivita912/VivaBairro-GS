"""Audita o corpus STT e atualiza os resultados parciais. O modo padrão é offline."""

import argparse
from collections import Counter, defaultdict
from contextlib import contextmanager
import csv
from dataclasses import replace
from datetime import datetime, timezone
from hashlib import file_digest, sha256
from importlib.metadata import version
import json
from pathlib import Path
import platform
import shutil
from statistics import mean
import subprocess
from tempfile import NamedTemporaryFile, TemporaryDirectory
from time import perf_counter
from uuid import uuid4

import av

from evaluation.academic_metrics import chart, read
from src.api_config import APIConfig
from src.audio_input import prepare_audio
from src.config import Settings
from src.errors import ProviderError, ValidationError, VivaBairroError
from src.metrics import NORMALIZATION, normalize_reference, stt_scores
from src.privacy import Consent
from src.stt import OpenAISTT


ROOT = Path(__file__).resolve().parent
PARTICIPANTS = {"R": "Rafael", "G": "Gustavo", "T": "Thiago"}
PLAN = [f"{prefix}{n:02d}" for prefix, numbers in
        (("R", range(1, 8)), ("G", range(8, 15)), ("T", range(15, 21))) for n in numbers]
PLANNED_NOISE = {"R04", "R07", "G11", "G14", "T18"}
FORMATS = {".wav", ".mp3", ".m4a", ".mp4", ".webm", ".ogg", ".flac", ".opus"}
PRICE_MODEL = "gpt-transcribe"
PRICE_PER_MINUTE = 0.0045
PRICE_SOURCE = "https://developers.openai.com/api/docs/models/gpt-transcribe"
REVIEW_FIELDS = """sha256 audio_path sample_id identification_note preliminary_text preliminary_source
                   reference_text reference_reviewed_by noise_present noise_observation consent_id
                   consent_document external_audio_authorized review_completed""".split()
INVENTORY_FIELDS = """audio_path sha256 bytes container codec sample_rate channels duration_seconds
                      integrity app_compatible prepared_format prepared_seconds prepared_sha256
                      duplicate_count previous_sha256 whatsapp error""".split()
RESULT_FIELDS = """sample_id participant planned_noise status reference_status noise_present noise_observation
                   consent_id stt_status wer_status requested_model model_revision language environment_id
                   stt_seconds provider_audio_seconds wer substitutions deletions insertions reference_words
                   attempt attempt_recorded_sample_id error_code""".split()
MANIFEST_FIELDS = """sample_id data_origin speaker_id noise_present audio_path consent_id reference_text reference_reviewed_by
                     hypothesis_text transcription_completed model_id model_revision compute_type environment_id stt_seconds
                     recorded_on retention_until sharing_authorized notes audio_sha256 prepared_sha256 attempt_id
                     attempt_recorded_sample_id reference_status stt_status""".split()


def digest(path):
    with path.open("rb") as stream:
        return file_digest(stream, "sha256").hexdigest()


def atomic_write(path, write):
    with NamedTemporaryFile(mode="w", encoding="utf-8", newline="", dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        try:
            with stream:
                write(stream)
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)


def write_csv(path, fields, rows):
    def write(stream):
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    atomic_write(path, write)


def read_optional(path):
    return read(path) if path.exists() else []


@contextmanager
def prepared_audio(path, container, consent, settings, scratch):
    if path.suffix.lower() == ".opus" and container == "ogg":
        # .opus é uma extensão alternativa de Ogg Opus. Use o sufixo aceito pelo app.
        with TemporaryDirectory(dir=scratch) as folder:
            alias = Path(folder) / "input.ogg"
            shutil.copyfile(path, alias)
            with prepare_audio(alias, "upload", consent, settings, scratch) as audio:
                yield audio
    else:
        with prepare_audio(path, "upload", consent, settings, scratch) as audio:
            yield audio


def inspect(path, root, settings, scratch):
    name = path.relative_to(root).as_posix()
    row = dict(audio_path=name, app_compatible="false", whatsapp="indeterminado")
    try:
        row.update(bytes=path.stat().st_size, sha256=digest(path))
        if not row["bytes"]:
            return dict(row, integrity="VAZIO")
        if path.suffix.lower() not in FORMATS:
            return dict(row, integrity="EXTENSAO_NAO_SUPORTADA")
        with path.open("rb") as stream, av.open(stream, options={"err_detect": "explode"}) as container:
            if not container.streams.audio:
                return dict(row, integrity="SEM_FAIXA_DE_AUDIO")
            track = container.streams.audio[0]
            container_name = container.format.name
            row.update(container=container_name, codec=track.codec_context.name,
                       sample_rate=track.rate, channels=track.channels)
            if container_name == "ogg" and row["codec"] == "opus" and path.name.lower().startswith("whatsapp ptt "):
                row["whatsapp"] = "provável mensagem de voz"
            duration = sum(frame.samples / frame.sample_rate for frame in container.decode(audio=0))
            declared = float(track.duration * track.time_base) if track.duration and track.time_base else 0
            row["duration_seconds"] = f"{duration:.6f}"
            # A duração declarada pode incluir o atraso e o preenchimento do codec.
            if not duration or (declared and duration + 0.25 < declared):
                return dict(row, integrity="AUDIO_INCOMPLETO")
        row["integrity"] = "VALIDO"
        # Escopo local do inventário. A autorização de cada participante é conferida antes do envio.
        with prepared_audio(path, row["container"], Consent.grant(), settings, scratch) as audio:
            row.update(app_compatible="true",
                       prepared_format=f"WAV PCM s16le {audio.sample_rate} Hz {audio.channels} canal(is)",
                       prepared_seconds=f"{audio.duration_seconds:.6f}", prepared_sha256=digest(audio.path))
        if digest(path) != row["sha256"]:
            return dict(row, integrity="ALTERADO_DURANTE_A_LEITURA", app_compatible="false")
    except (OSError, av.error.FFmpegError, ValueError) as error:
        row.update(integrity="ERRO_DE_LEITURA_OU_DECODIFICACAO", error=type(error).__name__)
    except VivaBairroError as error:
        row["error"] = str(error)
    return row


def audit(root, output, settings, scratch):
    path = output / "stt_inventario_audio.csv"
    previous = {row["audio_path"]: row for row in read_optional(path)}
    audio = root / "audio"
    if not audio.is_dir():
        raise ValidationError("A pasta evaluation/audio está indisponível.")
    rows = [inspect(p, root, settings, scratch) for p in sorted(audio.rglob("*"))
            if p.is_file() and not p.is_symlink() and p.resolve().is_relative_to(audio.resolve())]
    hashes = Counter(r["sha256"] for r in rows if r.get("sha256"))
    for row in rows:
        before = previous.get(row["audio_path"], {})
        current = row.get("sha256", "")
        row["duplicate_count"] = hashes[current] if current else ""
        row["previous_sha256"] = (before.get("sha256", "") if current != before.get("sha256")
                                  else before.get("previous_sha256", ""))
    write_csv(path, INVENTORY_FIELDS, rows)
    return rows


def review_rows(path, inventory):
    rows = read_optional(path)
    by_hash = {row["sha256"]: row for row in rows}
    if len(by_hash) != len(rows) or any(not row.get("sha256") for row in rows):
        raise ValidationError("Use um único registro de revisão por SHA-256.")
    for audio in inventory:
        key = audio.get("sha256")
        if key and audio["integrity"] == "VALIDO" and key not in by_hash:
            by_hash[key] = dict(sha256=key, audio_path=audio["audio_path"])
    for row in by_hash.values():
        if row.get("sample_id") and (row["sample_id"] not in PLAN or not row.get("identification_note", "").strip()):
            raise ValidationError("Confirme os IDs a partir do conteúdo e preencha identification_note.")
        if row.get("noise_present", "") not in {"", "true", "false"}:
            raise ValidationError("Use true, false ou vazio para a presença de ruído.")
        if row.get("noise_present") and not row.get("noise_observation", "").strip():
            raise ValidationError("Descreva a observação do ruído antes de classificá-lo.")
        if row.get("review_completed") == "true" and not (row.get("sample_id") and
                row.get("reference_reviewed_by", "").strip() and normalize_reference(row.get("reference_text", ""))):
            raise ValidationError("A revisão concluída precisa de ID confirmado, referência e revisor.")
    if len(by_hash) != len(rows) or not path.exists():
        write_csv(path, REVIEW_FIELDS, by_hash.values())
    return by_hash


def draft_references(path, inventory, reviews, settings, scratch, root, engine, model):
    engine, model = Path(engine).resolve(strict=True), Path(model).resolve(strict=True)
    source = f"{engine.name} SHA-256 {digest(engine)} / {model.name} SHA-256 {digest(model)} / pt / CPU / não verificada"
    consent = Consent.grant()
    for row in inventory:
        review = reviews.get(row.get("sha256"), {})
        if row["app_compatible"] != "true" or review.get("preliminary_text") or review.get("reference_reviewed_by"):
            continue
        with prepared_audio(root / row["audio_path"], row["container"], consent, settings, scratch) as audio:
            if digest(audio.path) != row["prepared_sha256"]:
                print("Rascunho pendente para um arquivo que mudou durante o preparo.")
                continue
            command = [str(engine), "-m", str(model), "-l", "pt", "-ng", "-t", "6", "-nt", "-bs", "1", "-bo", "1",
                       "-nf", "-np", "-otxt", "-f", str(audio.path)]
            target = audio.path.with_suffix(".wav.txt")
            try:
                subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True, timeout=60)
                review["preliminary_text"] = target.read_text(encoding="utf-8").strip()
            except (OSError, subprocess.SubprocessError):
                print("Um rascunho local falhou. Consulte o arquivo de revisão.")
                continue
            review["preliminary_source"] = source
            write_csv(path, REVIEW_FIELDS, reviews.values())


def has_consent(root, review):
    if not review.get("consent_id", "").strip() or review.get("external_audio_authorized") != "true":
        return False
    if not review.get("consent_document", "").strip():
        return False
    document = (root / "consents" / review["consent_document"]).resolve()
    try:
        return document.is_file() and document.stat().st_size > 0 and document != root / "consents/README.md"
    except OSError:
        return False


def environment(settings):
    details = dict(os=platform.platform(), cpu=platform.processor(), python=platform.python_version(),
                   openai=version("openai"), av=av.__version__, jiwer=version("jiwer"),
                   timeout_seconds=settings.timeout_seconds, retries=0)
    suffix = sha256(json.dumps(details, sort_keys=True).encode()).hexdigest()[:12]
    return f"stt-{suffix}", details


def attempt_key(row):
    # O ambiente e o WAV da chamada continuam registrados. A troca de computador não autoriza repetir o envio.
    return tuple(row[field] for field in ("sha256", "consent_id", "requested_model"))


def build_results(root, inventory, reviews, attempts, model, env_id, reserved=()):
    audio_by_hash = defaultdict(list)
    for audio in inventory:
        if audio.get("sha256"):
            audio_by_hash[audio["sha256"]].append(audio)
    by_id = defaultdict(list)
    replaced_ids = set()
    replacements = {r.get("previous_sha256") for r in inventory if r.get("previous_sha256")}
    paths = {a["audio_path"] for a in inventory}
    replacements.update(r["sha256"] for r in reviews.values() if r.get("audio_path") in paths
                        and r["sha256"] not in audio_by_hash)
    for key, review in reviews.items():
        if not (sample_id := review.get("sample_id")):
            continue
        options = audio_by_hash[key]
        if options:
            audio = next((a for a in options if a["audio_path"] == review["audio_path"]), options[0])
            by_id[sample_id].append((audio, review))
        elif key in replacements:
            replaced_ids.add(sample_id)

    results = []
    for sample_id in PLAN:
        row = dict(sample_id=sample_id, participant=PARTICIPANTS[sample_id[0]],
                   planned_noise=str(sample_id in PLANNED_NOISE).lower(), status="PENDENTE",
                   reference_status="PENDENTE", stt_status="PENDENTE", wer_status="PENDENTE")
        results.append(row)
        matches = by_id[sample_id]
        if len(matches) != 1:
            if matches:
                row["status"] = "IDENTIFICACAO_AMBIGUA"
            elif sample_id in replaced_ids:
                row["status"] = "ARQUIVO_ALTERADO_REVISAR"
            continue
        audio, review = matches[0]
        reference = review.get("reference_text", "")
        verified = (review.get("review_completed") == "true" and
                    review.get("reference_reviewed_by", "").strip() and normalize_reference(reference))
        consent = has_consent(root, review)
        row.update(audio, status="RECEBIDO", requested_model=model, environment_id=env_id,
                   reference_status="VERIFICADA" if verified else "PENDENTE", reference=reference if verified else "",
                   noise_present=review.get("noise_present", ""), noise_observation=review.get("noise_observation", ""),
                   consent_id=review.get("consent_id", ""), stt_status="PENDENTE_CONSENTIMENTO", external_eligible=consent,
                   inventory_prepared_sha256=audio.get("prepared_sha256", ""))
        if audio.get("app_compatible") != "true":
            row["stt_status"] = "AUDIO_INCOMPATIVEL"
        elif previous := attempts.get(attempt_key(row)):
            row.update(stt_status=previous["stt_status"], attempt=previous["attempt"],
                       attempt_recorded_sample_id=previous["sample_id"], environment_id=previous["environment_id"],
                       prepared_sha256=previous["prepared_sha256"],
                       model_revision=previous.get("model_revision", ""), language=previous.get("language", ""),
                       stt_seconds=previous.get("stt_seconds", ""), error_code=previous.get("error_code", ""),
                       provider_audio_seconds=previous.get("usage", {}).get("seconds", ""), hypothesis=previous.get("hypothesis", ""))
        elif (audio["sha256"], model) in reserved or any(
                original == audio["sha256"] and requested == model and saved.get("stt_status") == "TRANSCRITO"
                for (original, _, requested), saved in attempts.items()):
            row["stt_status"] = "PENDENTE_RESTAURAR_HISTORICO"
        elif consent:
            row["stt_status"] = "PENDENTE_AUTORIZACAO_API"
    return results


def export_manifest(root, rows, reviews):
    manifest = []
    for row in rows:
        if not row.get("sha256"):
            continue
        review = reviews[row["sha256"]]
        manifest.append(dict(row, data_origin="real", speaker_id=row["participant"],
                             audio_sha256=row["sha256"], model_id=row["requested_model"], compute_type="api",
                             reference_text=row["reference"], hypothesis_text=row.get("hypothesis", ""),
                             reference_reviewed_by=review.get("reference_reviewed_by", "") if row["reference"] else "",
                             transcription_completed=str(row["stt_status"] == "TRANSCRITO").lower(),
                             attempt_id=row.get("attempt", ""), notes=review.get("identification_note", "")))
    write_csv(root / "stt_manifest.csv", MANIFEST_FIELDS, manifest)


def transcribe(root, output, rows, model, settings, details, scratch, args):
    from src.api_runtime import APIRuntime, CallBudget

    retry = {"FALHA", "EM_ANDAMENTO"} if args.repetir_falhas else set()
    selected = set(args.ids or PLAN)
    pending = [r for r in rows if r["sample_id"] in selected and r.get("external_eligible") and
               r["stt_status"] in {"PENDENTE_AUTORIZACAO_API"} | retry]
    if not pending:
        return
    config = APIConfig.load()
    if config.stt_model != model:
        raise ValidationError("O modelo privado diverge do modelo da rodada. Confira o modelo e o custo antes de autorizar.")
    runtime = APIRuntime(config, settings, CallBudget(args.autorizar_api))
    backend = OpenAISTT(runtime)
    for row in pending[:args.autorizar_api]:
        path = root / row["audio_path"]
        consent = Consent.grant(external_audio=True)
        consent.require(audio_external=True)
        try:
            with prepared_audio(path, row["container"], consent, settings, scratch) as audio:
                prepared_sha = digest(audio.path)
                if digest(path) != row["sha256"] or prepared_sha != row["inventory_prepared_sha256"]:
                    print(f"{row['sample_id']}: arquivo alterado após auditoria")
                    continue
                stamp = datetime.now(timezone.utc).isoformat()
                attempt = f"{stamp.replace(':', '')}-{uuid4().hex}"
                evidence = {k: row[k] for k in ("sample_id", "audio_path", "sha256", "prepared_sha256",
                                                "requested_model", "environment_id", "consent_id")}
                evidence.update(prepared_sha256=prepared_sha, environment_id=details["id"])
                evidence.update(attempt=attempt, started_utc=stamp, stt_status="EM_ANDAMENTO", environment=details)
                evidence_path = output / "stt_historico" / f"{attempt}.json"
                atomic_write(evidence_path, lambda s: json.dump(evidence, s, ensure_ascii=False, indent=2))
                started = perf_counter()
                try:
                    result = backend.transcribe(audio)
                    evidence.update(stt_status="TRANSCRITO", hypothesis=result.text, language=result.language,
                                    model_revision=result.model_revision, usage=result.usage)
                except VivaBairroError as error:
                    code = error.code if isinstance(error, ProviderError) else type(error).__name__
                    evidence.update(stt_status="FALHA", error_code=code)
                evidence["stt_seconds"] = perf_counter() - started
                atomic_write(evidence_path, lambda s: json.dump(evidence, s, ensure_ascii=False, indent=2))
                print(f"{row['sample_id']}: {evidence['stt_status']}")
        except (ValidationError, FileNotFoundError):
            print(f"{row['sample_id']}: preparação falhou antes da chamada")


def history(output):
    attempts = {}
    for path in sorted((output / "stt_historico").glob("*.json")):
        row = json.loads(path.read_text(encoding="utf-8"))
        key = attempt_key(row)
        if attempts.get(key, {}).get("stt_status") != "TRANSCRITO":
            attempts[key] = row
    return attempts


def score_results(rows):
    groups = defaultdict(list)
    for row in rows:
        if row["stt_status"] == "TRANSCRITO":
            groups[row["requested_model"], row["model_revision"], row["environment_id"]].append(row)
    scores = {}
    for config, subset in groups.items():
        measured = [r for r in subset if r["reference_status"] == "VERIFICADA"]
        totals = {"latency": [(r["sample_id"], r["stt_seconds"]) for r in subset], "scores": {},
                  "provider_audio_seconds": [r["provider_audio_seconds"] for r in subset
                                             if isinstance(r.get("provider_audio_seconds"), (int, float))]}
        strata = {"Corpus": measured}
        for participant in PARTICIPANTS.values():
            strata[participant] = [r for r in measured if r["participant"] == participant]
        for flag, label in (("true", "Com ruído"), ("false", "Limpo")):
            strata[label] = [r for r in measured if r["noise_present"] == flag]
        for label, samples in strata.items():
            if samples:
                totals["scores"][label] = stt_scores([r["reference"] for r in samples], [r["hypothesis"] for r in samples])
        if measured:
            corpus = totals["scores"]["Corpus"]
            for row, wer, counts in zip(measured, corpus["wer_per_sample"], corpus["word_errors_per_sample"]):
                row.update(counts, wer_status="CALCULADO", wer=wer)
        scores[config] = totals
    return scores


def make_charts(output, scores, rows):
    made = []
    names = ("stt_wer_gravacao", "stt_wer_participante", "stt_wer_ruido", "stt_latencia")
    for index, data in enumerate(scores.values(), 1):
        score = data["scores"]
        latency = data["latency"]
        ids = {key for key, _ in latency}
        spec = (("WER por gravação", "%", [(r["sample_id"], 100 * r["wer"]) for r in rows
                                            if r["sample_id"] in ids and "wer" in r]),
                ("WER por participante", "%", [(p, 100 * score[p]["wer_corpus"]) for p in PARTICIPANTS.values() if p in score]),
                ("WER por presença de ruído", "%", [(p, 100 * score[p]["wer_corpus"]) for p in ("Limpo", "Com ruído")]
                 if {"Limpo", "Com ruído"}.issubset(score) else []),
                ("Latência STT por gravação", "s", latency))
        for name, (title, unit, entries) in zip(names, spec):
            if entries:
                file = f"{name}_{index}.svg"
                temp = output / f".stt-chart-{uuid4().hex}.tmp"
                try:
                    chart(temp, f"{title} · configuração {index}", unit, entries)
                    temp.replace(output / file)
                finally:
                    temp.unlink(missing_ok=True)
                made.append((file, f"{title} · configuração {index}"))
    current = {file for file, _ in made}
    for name in names:
        for path in output.glob(f"{name}_[0-9]*.svg"):
            if path.name not in current:
                path.unlink()
    return made


def report(output, inventory, rows, scores, graphs, model, details, review_path, reviews):
    def cell(value):
        return str(value or "—").replace("|", "\\|").replace("\n", " ")

    def table_row(*cells):
        return "| " + " | ".join(cell(item) for item in cells) + " |"

    lines = ["# Avaliação parcial de STT · VivaBairro Voz", "",
             "## Corpus recebido", ""]
    prepared = {r["sha256"]: float(r["prepared_seconds"]) for r in inventory if r["app_compatible"] == "true"}
    matched = {r["audio_path"] for r in rows if r.get("audio_path")}
    compatible = sum(r["app_compatible"] == "true" for r in inventory)
    transcribed = sum(r["stt_status"] == "TRANSCRITO" for r in rows)
    verified = sum(r["reference_status"] == "VERIFICADA" for r in rows)
    noisy = sum(r.get("noise_present") == "true" and r.get("app_compatible") == "true" for r in rows)
    clean = sum(r.get("noise_present") == "false" and r.get("app_compatible") == "true" for r in rows)
    duplicate_groups = {r["sha256"] for r in inventory if isinstance(r["duplicate_count"], int) and r["duplicate_count"] > 1}
    whatsapp = sum(r["whatsapp"] == "provável mensagem de voz" for r in inventory)
    received = Counter(r["participant"] for r in rows if r.get("audio_path"))
    participant_counts = ", ".join(f"{name} {received[name]}" for name in PARTICIPANTS.values())
    pending = ", ".join(r["sample_id"] for r in rows if r["status"] != "RECEBIDO") or "nenhum ID"
    errors = [r for r in rows if r["stt_status"] in {"FALHA", "EM_ANDAMENTO"}]
    blocked = sum(r["stt_status"] == "PENDENTE_CONSENTIMENTO" for r in rows)
    ready = [r for r in rows if r["stt_status"] == "PENDENTE_AUTORIZACAO_API"]
    drafts = sum(bool(r.get("preliminary_text")) for r in reviews.values() if r["sha256"] in prepared)
    lines += [f"- {len(inventory)} arquivos encontrados, {compatible} preparados e validados localmente, "
              f"{len(duplicate_groups)} grupos de duplicatas SHA-256, {sum(r['integrity'] == 'VAZIO' for r in inventory)} vazios "
              f"e {sum(r['integrity'] in {'ERRO_DE_LEITURA_OU_DECODIFICACAO', 'AUDIO_INCOMPLETO'} for r in inventory)} com falha de leitura ou integridade.",
              f"- {len(received)} participantes vinculados a roteiros ({participant_counts}) e {len(matched)} vínculos arquivo–ID.",
              f"- {transcribed} transcrições do VivaBairro, {verified} referências humanas verificadas. "
              f"{noisy} com ruído confirmado, {clean} confirmadas limpas e {len(prepared)-noisy-clean} com classificação pendente. "
              "A triagem por energia e frequência nas pausas não separa de forma confiável ambiente, fala e artefatos do dispositivo.",
              f"- {drafts} rascunhos offline no arquivo de revisão. Eles servem para conferir o conteúdo e continuam sem revisão humana.",
              f"- {whatsapp} prováveis mensagens de voz do WhatsApp, identificadas pelo nome e por Ogg/Opus. "
              "Opus e AAC usam compressão com perdas. A conversão para WAV preserva o conteúdo temporal decodificado, "
              "com reamostragem a 16 kHz e conversão para mono nas entradas comprimidas, sem ajuste de velocidade ou redução de ruído. "
              "O WAV não recupera informação descartada na codificação. A gravação anterior à compressão seria necessária para medir seu efeito isoladamente.",
              "- O inventário registra o SHA-256 do original e do WAV preparado. As cópias de áudio são temporárias.", "",
              f"[Inventário completo](stt_inventario_audio.csv) · [Resultados por ID](stt_resultados_parciais.csv) · [Revisão humana]({review_path.name})", "",
              "| ID | Participante | Arquivo encontrado | Formato e codec | Duração (s) | Situação |",
              "| --- | --- | --- | --- | ---: | --- |"]
    for row in rows:
        path = row.get("audio_path", "")
        status = row["stt_status"] if path else row["status"]
        lines.append(table_row(row["sample_id"], row["participant"], path,
                               f"{Path(path).suffix.lower()} / {row.get('codec', '—')}" if path else "",
                               row.get("duration_seconds"), status))
    if unmatched := [r for r in inventory if r["audio_path"] not in matched]:
        lines += ["", "### Arquivos sem vínculo confirmado", "",
                  "| Arquivo | Formato e codec | Duração (s) | Integridade | Observação |", "| --- | --- | ---: | --- | --- |"]
        lines += [table_row(r["audio_path"], f"{Path(r['audio_path']).suffix.lower()} / {r.get('codec', '—')}",
                            r.get("duration_seconds"), r["integrity"],
                            reviews.get(r.get("sha256"), {}).get("identification_note")) for r in unmatched]

    lines += ["", "## Resultados e limitações", "",
              f"STT configurado para `{model}`, com `languages=[\"pt\"]` e retorno JSON. SDK OpenAI {details['openai']}, "
              f"PyAV {details['av']}, Python {details['python']} e jiwer {details['jiwer']}. "
              f"Timeout de {details['timeout_seconds']} s e zero retentativas automáticas. "
              "O serviço informa a revisão quando disponível. A latência mede `OpenAISTT.transcribe`, após preparar o WAV.", "",
              f"Normalização fixada em `{NORMALIZATION}`. O WER agregado é `Σ(S + D + I) / ΣN`. "
              "Somente pares com referência humana revisada entram no WER. A condição acústica desconhecida fica fora dos estratos de ruído. "
              "As seis chamadas iniciais antecederam a revisão humana. Use a página de escuta sem consultar hipóteses ou rascunhos.", "",
              "[Página de revisão cega](stt_revisao.html) · [Manifesto acadêmico privado](../stt_manifest.csv)", ""]
    if not scores:
        lines += ["WER individual, agregado, por participante e por ruído, além da latência de STT, estão pendentes.", ""]
    for index, (config, result) in enumerate(scores.items(), 1):
        latencies = [seconds for _, seconds in result["latency"]]
        lines += [f"### Configuração {index} · {' / '.join(config)}", "",
                  f"Latência média {mean(latencies):.3f} s em {len(latencies)} transcrições. "
                  f"Tempos entre {min(latencies):.3f} s e {max(latencies):.3f} s.", ""]
        usage = result["provider_audio_seconds"]
        if config[0] == PRICE_MODEL and len(usage) == len(latencies):
            lines += [f"A API informou {sum(usage):g} s de uso para estas transcrições. "
                      f"O valor estimado pela tarifa pública é US$ {sum(usage) * PRICE_PER_MINUTE / 60:.5f}.", ""]
        if result["scores"]:
            lines += ["| Estrato | Amostras | Palavras | S | D | I | WER |", "| --- | ---: | ---: | ---: | ---: | ---: | ---: |"]
            for label, value in result["scores"].items():
                counts = value["word_errors"]
                lines.append(table_row(label, value["samples"], counts["reference_words"], str(counts["substitutions"]),
                                       str(counts["deletions"]), str(counts["insertions"]), f"{value['wer_corpus']:.2%}"))
        else:
            lines.append("WER pendente de referência humana verificada.")
        lines.append("")
    lines += [f"- [{title}]({file})" for file, title in graphs] or ["Gráficos pendentes de medições válidas."]
    lines += ["", "## Pendências de coleta e execução", "", f"- Aguardam arquivo ou identificação os IDs {pending}.",
              f"- {blocked} arquivos vinculados aguardam consentimento documentado para envio à OpenAI. "
              f"{len(ready)} arquivos estão elegíveis para uma rodada autorizada.",
              f"- {len(errors)} tentativas com falha ou interrupção nesta configuração."]
    lines += [f"  - {r['sample_id']} · {r['stt_status']} · {r.get('error_code') or 'sem retorno registrado'}" for r in errors]
    if ready:
        lines += ["- A fila elegível inclui " + ", ".join(r["sample_id"] for r in ready) + "."]
    if model == PRICE_MODEL:
        seconds = sum(prepared.values())
        ready_seconds = sum(float(r["prepared_seconds"]) for r in ready)
        lines += [f"- A estimativa para uma chamada por original compatível e distinto é de {len(prepared)} chamadas, "
                  f"{seconds:.2f} s e US$ {seconds * PRICE_PER_MINUTE / 60:.5f}. "
                  f"A fila atualmente elegível corresponde a {len(ready)} chamadas e US$ {ready_seconds * PRICE_PER_MINUTE / 60:.5f}. "
                  f"[Tarifa pública de US$ {PRICE_PER_MINUTE:.4f}/min]({PRICE_SOURCE})."]
    lines += ["", "## Conclusão provisória", "",
              "A avaliação acadêmica exige 20 gravações, três vozes e cinco gravações com ruído de fundo. "
              "A cobertura e os estratos devem ser conferidos com a coleta completa e as observações da escuta.",
              "", "O procedimento de importação, revisão e reexecução está no [guia de avaliação](../README.md#fluxo-incremental-do-corpus-stt).", ""]
    atomic_write(output / "stt_relatorio_parcial.md", lambda s: s.write("\n".join(lines)))


def run(root, args):
    output = root / "results"
    output.mkdir(exist_ok=True)
    lock = output / ".stt_em_execucao"
    try:
        lock.mkdir()
    except FileExistsError:
        raise ValidationError("Já existe uma execução STT em curso ou interrompida. Confira o bloqueio no guia.") from None
    try:
        (output / "stt_historico").mkdir(exist_ok=True)
        settings = replace(Settings.load(), retries=0)
        env_id, details = environment(settings)
        with TemporaryDirectory(prefix="vivabairro-stt-") as folder:
            scratch = Path(folder)
            inventory = audit(root, output, settings, scratch)
            review_path = output / "stt_referencias_revisao.csv"
            reviews = review_rows(review_path, inventory)
            if getattr(args, "importar_revisao", None):
                from evaluation.stt_review import import_review
                import_review(args.importar_revisao, reviews)
                write_csv(review_path, REVIEW_FIELDS, reviews.values())
                reviews = review_rows(review_path, inventory)
            if args.rascunhos_local:
                draft_references(review_path, inventory, reviews, settings, scratch, root, *args.rascunhos_local)
            reserve = output / "stt_reserva_historica.json"
            reserved = {tuple(item) for item in json.loads(reserve.read_text(encoding="utf-8"))} if reserve.exists() else set()
            rows = build_results(root, inventory, reviews, history(output), args.modelo, env_id, reserved)
            if args.autorizar_api:
                transcribe(root, output, rows, args.modelo, settings, dict(details, id=env_id), scratch, args)
                rows = build_results(root, inventory, reviews, history(output), args.modelo, env_id, reserved)
        scores = score_results(rows)
        graphs = make_charts(output, scores, rows)
        write_csv(output / "stt_resultados_parciais.csv", RESULT_FIELDS + INVENTORY_FIELDS, rows)
        export_manifest(root, rows, reviews)
        from evaluation.stt_review import export_review
        export_review(output, inventory, reviews, PLAN)
        report(output, inventory, rows, scores, graphs, args.modelo, details, review_path, reviews)
        print(f"{len(inventory)} arquivos inventariados e {len(rows)} IDs atualizados em {output.name}/.")
    finally:
        lock.rmdir()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--modelo", default=APIConfig.stt_model, help="Modelo configurado para a rodada")
    parser.add_argument("--autorizar-api", type=int, metavar="N", help="Autoriza até N chamadas pagas nesta rodada")
    parser.add_argument("--ids", nargs="+", choices=PLAN, metavar="ID", help="Restringe a rodada paga aos IDs informados")
    parser.add_argument("--repetir-falhas", action="store_true", help="Inclui tentativas falhas ou interrompidas")
    parser.add_argument("--rascunhos-local", nargs=2, metavar=("WHISPER_CLI", "MODELO"),
                        help="Preenche rascunhos de referência com um whisper.cpp instalado localmente")
    parser.add_argument("--importar-revisao", type=Path, metavar="JSON", help="Importa as revisões exportadas pela página de escuta")
    args = parser.parse_args()
    if args.autorizar_api is not None and not 1 <= args.autorizar_api <= len(PLAN):
        parser.error(f"--autorizar-api aceita de 1 a {len(PLAN)} chamadas por rodada")
    if (args.repetir_falhas or args.ids) and not args.autorizar_api:
        parser.error("--repetir-falhas e --ids exigem --autorizar-api")
    if args.rascunhos_local and args.autorizar_api:
        parser.error("Produza rascunhos locais antes da rodada paga")
    try:
        run(ROOT, args)
    except (VivaBairroError, OSError) as error:
        print(f"Avaliação interrompida: {error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
