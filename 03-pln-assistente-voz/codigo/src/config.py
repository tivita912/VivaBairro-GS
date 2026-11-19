"""Configuração pequena e explícita. Não altera o ambiente global."""
from dataclasses import dataclass
import os
from pathlib import Path

from .errors import ValidationError

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PREFIX = "VIVABAIRRO_"


@dataclass(frozen=True)
class Settings:
    port: int = 7860
    max_audio_seconds: int = 60
    max_audio_mb: int = 10
    history_turns: int = 6
    session_requests: int = 30
    max_output_tokens: int = 300
    max_response_chars: int = 900
    timeout_seconds: int = 45
    retries: int = 0
    auto_test_calls: int = 12
    retention_seconds: int = 600
    tts_max_tokens: int = 1500

    @classmethod
    def load(cls, env_file: Path | None = None) -> "Settings":
        values = {}
        if env_file:
            try:
                for line in env_file.read_text(encoding="utf-8-sig").splitlines():
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    key, sep, value = line.partition("=")
                    if not sep or not key.strip().startswith(PREFIX):
                        raise ValidationError("Use linhas VIVABAIRRO_CHAVE=valor no arquivo de configuração.")
                    values[key.strip()] = value.strip()
            except OSError as exc:
                raise ValidationError("Não foi possível ler a configuração.") from exc
        values.update({k: v for k, v in os.environ.items() if k.startswith(PREFIX)})
        bounds = {"port": (1024, 65535), "max_audio_seconds": (1, 300),
                  "max_audio_mb": (1, 24), "history_turns": (1, 20),
                  "session_requests": (3, 120), "max_output_tokens": (80, 800),
                  "max_response_chars": (100, 2000), "timeout_seconds": (5, 90),
                  "retries": (0, 2), "auto_test_calls": (0, 12),
                  "retention_seconds": (60, 1800), "tts_max_tokens": (200, 3000)}
        allowed = {PREFIX + name.upper() for name in bounds}
        if values.keys() - allowed:
            raise ValidationError("Há uma chave de configuração desconhecida.")
        result = {}
        for name, (low, high) in bounds.items():
            try:
                value = int(values.get(PREFIX + name.upper(), getattr(cls(), name)))
            except ValueError as exc:
                raise ValidationError("As configurações devem ser números inteiros.") from exc
            if not low <= value <= high:
                raise ValidationError(f"Configuração {name} fora do intervalo {low} a {high}.")
            result[name] = value
        return cls(**result)
