"""Confere a série TTS e gera um ZIP offline a partir das sínteses existentes."""

import argparse
import json
from pathlib import Path
import wave
import zipfile

from evaluation.run_stt import ROOT, digest, read
from src.errors import ValidationError

IDS = {f"T{i:02d}" for i in range(1, 11)}


def verify_samples(root=ROOT):
    rows = read(root / "tts_samples.csv")
    if len(rows) != len(IDS) or {r["sample_id"] for r in rows} != IDS:
        raise ValidationError("A série TTS precisa conter T01 a T10 uma vez cada.")
    seen = set()
    samples = []
    for r in sorted(rows, key=lambda row: row["sample_id"]):
        sample = r["sample_id"]
        path = (root / r["audio_path"]).resolve()
        if r["status"] != "success" or r["data_origin"] != "real" or not path.is_relative_to(root / "results"):
            raise ValidationError(f"{sample}: síntese ou caminho inválido.")
        sha = digest(path)
        if sha in seen or sha != r["audio_sha256"]:
            raise ValidationError(f"{sample}: SHA-256 duplicado ou divergente.")
        seen.add(sha)
        with wave.open(str(path), "rb") as audio:
            channels, rate, width, count = (audio.getnchannels(), audio.getframerate(), audio.getsampwidth(), audio.getnframes())
            if (channels, rate, width) != (1, 24000, 2) or not count or len(audio.readframes(count)) != count * 2:
                raise ValidationError(f"{sample}: WAV PCM incompleto ou fora do formato do TTS.")
        evidence = json.loads(path.with_suffix(".json").read_text(encoding="utf-8"))
        fields = ("sample_id", "status", "text", "adapted_text", "audio_sha256", "voice_id", "model_id")
        if any(evidence.get(field) != r[field] for field in fields):
            raise ValidationError(f"{sample}: texto ou hash diverge do registro da síntese.")
        samples.append(dict(sample_id=sample, path=path, sha256=sha, duration_seconds=count / rate,
                            channels=channels, sample_rate=rate, format="WAV PCM16LE"))
    return samples


def make_kit(target, root=ROOT):
    verified = verify_samples(root)
    form = (root / "avaliar_tts_offline.html").read_text(encoding="utf-8")
    hashes = {sample["sample_id"]: sample["sha256"] for sample in verified}
    form = form.replace("/*__TTS_HASHES__*/ {}", json.dumps(hashes))
    instructions = ("VivaBairro Voz - Avaliação humana de TTS\n\n"
                    "Extraia todos os arquivos. Abra avaliar_tts.html no navegador, ouça T01 a T10, "
                    "dê duas notas de 1 a 5 por áudio e exporte o CSV. Envie o CSV por WhatsApp à equipe.\n"
                    "Use P01 (Thiago), P02 (Rafael) ou P03 (Gustavo). Faça a escuta individualmente.\n"
                    "O ZIP funciona offline, sem Python. Não altere os WAVs.\n")
    target.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(target, "x", compression=zipfile.ZIP_DEFLATED) as bundle:
        for item in verified:
            bundle.write(item["path"], item["sample_id"] + ".wav")
        bundle.writestr("avaliar_tts.html", form.encode("utf-8"))
        bundle.writestr("LEIA-ME.txt", instructions.encode("utf-8"))
        bundle.writestr("SHA256.json", json.dumps(hashes, indent=2))
    return verified


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--saida", type=Path, default=ROOT / "results/kit_tts_avaliadores.zip")
    args = parser.parse_args()
    try:
        for sample in make_kit(args.saida):
            print(f"{sample['sample_id']} {sample['duration_seconds']:.2f} s {sample['sha256']}")
        print(args.saida)
    except (OSError, ValueError, wave.Error, ValidationError) as error:
        parser.exit(1, f"Kit indisponível: {error}\n")


if __name__ == "__main__":
    main()
