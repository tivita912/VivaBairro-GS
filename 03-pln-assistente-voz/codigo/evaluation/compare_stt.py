"""Compara gpt-transcribe já executado e Whisper local em pares com referência humana."""

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import platform
import re
import subprocess
from tempfile import TemporaryDirectory
from time import perf_counter

from evaluation.academic_metrics import describe
from evaluation.run_stt import ROOT, atomic_write, digest, prepared_audio, read
from src.config import Settings
from src.errors import ValidationError, VivaBairroError
from src.metrics import stt_scores
from src.privacy import Consent

ENGINE_SHA = "111bd344b7bf0356818f2795a525cb5240ed0a99028fa9f3f1c68b4ff5b17b91"
MODEL_SHA = "422f1ae452ade6f30a004d7e5c6a43195e4433bc370bf23fac9cc591f01a8898"
ENGINE_RELEASE = "whisper.cpp v1.8.6 Windows x64 CPU"
MODEL_NAME = "Whisper base multilíngue Q5_1"


def local_environment():
    cpu = platform.processor()
    if os.name == "nt":
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0") as key:
                cpu = winreg.QueryValueEx(key, "ProcessorNameString")[0].strip()
        except OSError:
            pass
    return dict(os=platform.platform(), cpu=cpu, logical_cpus=os.cpu_count(), threads=6, backend="CPU")


def run(exe, model):
    if digest(exe) != ENGINE_SHA or digest(model) != MODEL_SHA:
        raise ValidationError("Binário ou pesos diferentes dos ativos registrados para a comparação.")
    probe = subprocess.run([str(exe), "--help"], capture_output=True, encoding="utf-8", errors="replace", timeout=30)
    if "--no-gpu" not in (probe.stdout + probe.stderr):
        raise ValidationError("O executável registrado não iniciou corretamente.")
    output = ROOT / "results"
    audit = {r["sha256"]: r for r in read(output / "stt_inventario_audio.csv")}
    manifest = read(ROOT / "stt_manifest.csv")
    cloud = [r for r in manifest if r["transcription_completed"] == "true" and r["model_id"] == "gpt-transcribe"]
    eligible = [r for r in cloud if r["reference_status"] == "VERIFICADA" and r["reference_reviewed_by"]]
    local_env = local_environment()
    local_env_id = sha256(json.dumps(local_env, sort_keys=True).encode()).hexdigest()[:12]
    completed = []
    failures = []
    settings = Settings.load()
    local = output / "stt_whisper_formal"
    if eligible:
        local.mkdir(exist_ok=True)
    for row in eligible:
        original = ROOT / row["audio_path"]
        source_sha, wav_sha = row["audio_sha256"], row["prepared_sha256"]
        if digest(original) != source_sha:
            failures.append(dict(sample_id=row["sample_id"], error="original_alterado"))
            continue
        entry = local / f"{source_sha}-{wav_sha}-{local_env_id}.json"
        if entry.exists():
            result = json.loads(entry.read_text(encoding="utf-8"))
        else:
            try:
                with TemporaryDirectory(prefix="vivabairro-comparacao-") as folder:
                    with prepared_audio(original, audit[source_sha]["container"], Consent.grant(), settings, Path(folder)) as audio:
                        if digest(audio.path) != wav_sha:
                            raise ValidationError("O WAV preparado diverge da entrada da API.")
                        started = perf_counter()
                        proc = subprocess.run([str(exe), "-m", str(model), "-l", "pt", "-ng", "-t", "6", "-nt", "-bs", "1",
                                               "-bo", "1", "-nf", "-otxt", "-f", str(audio.path)],
                                              capture_output=True, encoding="utf-8", errors="replace", check=True, timeout=90)
                        wall = perf_counter() - started
                        timings = {name: float(ms) / 1000 for name, ms in re.findall(
                            r"whisper_print_timings:\s+(load|mel|encode|decode|batchd|prompt|sample|total) time\s*=\s*([\d.]+)\s+ms", proc.stderr)}
                        if not {"load", "encode", "total"}.issubset(timings):
                            raise ValidationError("Tempos de inferência ausentes na saída do Whisper.")
                        hypothesis = audio.path.with_suffix(".wav.txt").read_text(encoding="utf-8").strip()
                        result = dict(hypothesis=hypothesis, local_wall_seconds=wall, load_seconds=timings["load"],
                                      whisper_seconds=timings, engine_sha=ENGINE_SHA, model_sha=MODEL_SHA,
                                      local_environment=local_env)
                        atomic_write(entry, lambda s: json.dump(result, s, ensure_ascii=False, indent=2))
            except (OSError, subprocess.SubprocessError, VivaBairroError) as error:
                failures.append(dict(sample_id=row["sample_id"], error=type(error).__name__))
                continue
        completed.append((row, result))

    groups = []
    configurations = sorted({(r["environment_id"], r["model_revision"]) for r, _ in completed})
    for env, revision in configurations:
        subset = [(r, b) for r, b in completed if (r["environment_id"], r["model_revision"]) == (env, revision)]
        refs = [r["reference_text"] for r, _ in subset]
        groups.append(dict(environment_id_A=env, revision_A=revision,
                           pairs=[dict(sample_id=r["sample_id"], sha256=r["audio_sha256"], call_id=r["attempt_id"],
                                       reference_sha256=sha256(r["reference_text"].encode()).hexdigest(),
                                       remote_seconds=float(r["stt_seconds"]), local_wall_seconds=b["local_wall_seconds"],
                                       local_load_seconds=b["load_seconds"], local_inference_seconds=b["whisper_seconds"]["total"] - b["load_seconds"])
                                  for r, b in subset],
                           A=stt_scores(refs, [r["hypothesis_text"] for r, _ in subset]),
                           B=stt_scores(refs, [b["hypothesis"] for _, b in subset]),
                           remote=describe([float(r["stt_seconds"]) for r, _ in subset]),
                           local_wall=describe([b["local_wall_seconds"] for _, b in subset]),
                           local_load=describe([b["load_seconds"] for _, b in subset]),
                           local_inference=describe([b["whisper_seconds"]["total"] - b["load_seconds"] for _, b in subset])))
    pooled = {}
    if completed and len({revision for _, revision in configurations}) == 1:
        refs = [r["reference_text"] for r, _ in completed]
        pooled = dict(A=stt_scores(refs, [r["hypothesis_text"] for r, _ in completed]),
                      B=stt_scores(refs, [b["hypothesis"] for _, b in completed]))
    summary = dict(A="gpt-transcribe", B=MODEL_NAME, engine=ENGINE_RELEASE, engine_sha256=ENGINE_SHA, model_sha256=MODEL_SHA,
                   model_license="MIT", engine_license="MIT", local_environment=local_env,
                   available=True, complete=bool(pooled) and len(completed) == 20 and
                   len({r["speaker_id"] for r, _ in completed}) >= 3 and sum(r["noise_present"] == "true" for r, _ in completed) >= 5,
                   remote_completed=len(cloud), eligible=len(eligible), pairs=len(completed), failures=failures, groups=groups,
                   corpus_wer=pooled,
                   notes="A inclui envio e rede. O relógio externo de B inclui início do processo, leitura, inferência e encerramento. "
                         "O tempo interno sem carga usa o relatório do Whisper e inclui processamento do sinal. Sem medir inferência no servidor.")
    atomic_write(output / "stt_comparacao.json", lambda s: json.dump(summary, s, ensure_ascii=False, indent=2))
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("whisper_cli", type=lambda p: Path(p).resolve())
    parser.add_argument("weights", type=lambda p: Path(p).resolve())
    args = parser.parse_args()
    try:
        summary = run(args.whisper_cli, args.weights)
        print(f"Whisper local disponível. {summary['pairs']} pares avaliados, {summary['remote_completed']} transcrições remotas preservadas.")
    except (OSError, subprocess.SubprocessError, VivaBairroError) as error:
        parser.exit(1, f"Comparação indisponível: {error}\n")


if __name__ == "__main__":
    main()
