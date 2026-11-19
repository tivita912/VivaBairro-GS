"""Validação local de WAV PCM. Captura e conversão de outros formatos: etapa 02."""
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
import shutil
from typing import Iterator, Literal
import wave

from .config import Settings
from .errors import ValidationError
from .privacy import Consent, private_workspace


@dataclass(frozen=True)
class AudioInput:
    path: Path
    source: Literal["microphone", "upload"]
    sample_rate: int
    channels: int
    duration_seconds: float


def inspect_wav(path: Path, source: str, consent: Consent, settings: Settings) -> AudioInput:
    """Valida conteúdo, tamanho, duração e PCM; não modifica o arquivo original."""
    consent.require()  # Antes de acessar o arquivo.
    if source not in {"microphone", "upload"}:
        raise ValidationError("A origem deve ser microfone ou upload.")
    try:
        if path.is_symlink() or not path.is_file() or path.suffix.lower() != ".wav":
            raise ValidationError("Selecione um arquivo WAV PCM válido.")
        if not 0 < path.stat().st_size <= settings.max_audio_mb * 1024 * 1024:
            raise ValidationError("O áudio excede o limite de tamanho ou está vazio.")
        with wave.open(str(path), "rb") as audio:
            frames, rate, channels, width = (audio.getnframes(), audio.getframerate(),
                                            audio.getnchannels(), audio.getsampwidth())
            if rate not in {8000, 16000, 22050, 24000, 44100, 48000} or channels not in {1, 2}:
                raise ValidationError("Use WAV mono ou estéreo entre 8 e 48 kHz nas taxas suportadas.")
            if width != 2 or audio.getcomptype() != "NONE":
                raise ValidationError("Nesta etapa, use WAV PCM de 16 bits.")
            duration = frames / rate
            if not 0 < duration <= settings.max_audio_seconds:
                raise ValidationError("A duração do áudio está fora do limite configurado.")
            if len(audio.readframes(frames)) != frames * channels * width:
                raise ValidationError("O arquivo de áudio está incompleto.")
    except (OSError, EOFError, wave.Error) as exc:
        raise ValidationError("Não foi possível ler o áudio WAV.") from exc
    return AudioInput(path.resolve(), source, rate, channels, duration)


@contextmanager
def prepare_audio(path: Path, source: str, consent: Consent, settings: Settings,
                  runtime_root: Path) -> Iterator[AudioInput]:
    """Copia para área transitória; o chamador deve sair do bloco logo após STT."""
    consent.require()
    if source not in {"microphone", "upload"}:
        raise ValidationError("A origem deve ser microfone ou upload.")
    if path.suffix.lower() == ".wav":
        original = inspect_wav(path, source, consent, settings)
    else:
        original = None
        if (path.is_symlink() or not path.is_file() or
            path.suffix.lower() not in {".mp3", ".m4a", ".mp4", ".webm", ".ogg", ".flac"}):
            raise ValidationError("Use WAV PCM, MP3, M4A, MP4, WebM, OGG ou FLAC.")
        if not 0 < path.stat().st_size <= settings.max_audio_mb * 1024 * 1024:
            raise ValidationError("O arquivo excede o limite de tamanho ou está vazio.")
    with private_workspace(runtime_root, consent) as folder:
        target = folder / "input.wav"
        try:
            if original:
                shutil.copyfile(original.path, target)
            else:
                decode_to_wav(path, target, settings)
        except OSError as exc:
            raise ValidationError("Não foi possível preparar o áudio temporário.") from exc
        yield inspect_wav(target, source, consent, settings)


def decode_to_wav(source: Path, target: Path, settings: Settings) -> None:
    """PyAV com leitura limitada por amostras decodificadas, não só metadados."""
    import av
    import time
    started = time.monotonic()
    total = 0
    try:
        # Arquivo aberto localmente: o decodificador não recebe uma URL.
        with source.open("rb") as file, av.open(file, mode="r") as container:
            if not container.streams.audio:
                raise ValidationError("O arquivo não contém uma faixa de áudio.")
            resampler = av.AudioResampler(format="s16", layout="mono", rate=16000)
            with wave.open(str(target), "wb") as output:
                output.setnchannels(1)
                output.setsampwidth(2)
                output.setframerate(16000)
                def write_frames(frames):
                    nonlocal total
                    for frame in frames:
                        total += frame.samples
                        if total > settings.max_audio_seconds * 16000:
                            raise ValidationError("A duração do áudio excede o limite configurado.")
                        output.writeframes(frame.to_ndarray().tobytes())
                for frame in container.decode(audio=0):
                    if time.monotonic() - started > settings.timeout_seconds:
                        raise ValidationError("A conversão de áudio excedeu o tempo permitido.")
                    write_frames(resampler.resample(frame))
                write_frames(resampler.resample(None))
        if total == 0:
            raise ValidationError("O arquivo não contém áudio decodificável.")
    except (av.error.FFmpegError, OSError, ValueError):
        raise ValidationError("Não foi possível decodificar este arquivo de áudio.") from None
