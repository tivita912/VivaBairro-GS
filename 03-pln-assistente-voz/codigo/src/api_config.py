"""Leitura backend da configuração privada. Nunca carrega segredos no ambiente global."""
from dataclasses import dataclass, field
import os
from pathlib import Path
import re

from dotenv import dotenv_values

from .errors import ComponentUnavailable, ValidationError


@dataclass(frozen=True, repr=False)
class APIConfig:
    api_key: str = field(repr=False)
    stt_model: str = "gpt-transcribe"
    llm_model: str = "gpt-6-luna"
    tts_model: str = "gpt-realtime-2.1-mini"
    tts_voice: str = "marin"

    def __repr__(self):
        return "APIConfig(<configuração privada>)"

    @classmethod
    def load(cls, path: Path | None = None) -> "APIConfig":
        if path is None:
            try:
                path = Path(os.environ["LOCALAPPDATA"]) / "VivaBairroVoz" / ".env"
            except KeyError:
                raise ComponentUnavailable("LOCALAPPDATA não está definido. Esta configuração é para execução Windows.") from None
        if not path.is_file():
            raise ComponentUnavailable("Configuração privada não encontrada em LOCALAPPDATA/VivaBairroVoz/.env.")
        try:
            # Interpolação desativada: nenhum valor de outra variável é copiado.
            values = dotenv_values(path, encoding="utf-8-sig", interpolate=False)
        except (OSError, UnicodeError):
            raise ComponentUnavailable("Não foi possível ler a configuração privada.") from None
        key = values.get("OPENAI_API_KEY") or ""
        if len(key) < 20 or any(c.isspace() for c in key) or "COLE_SUA" in key:
            raise ComponentUnavailable("A chave OpenAI está ausente ou ainda contém um marcador de preenchimento.")
        models = {}
        for name in ("stt_model", "llm_model", "tts_model", "tts_voice"):
            value = values.get("OPENAI_" + name.upper()) or getattr(cls, name)
            if not re.fullmatch(r"[a-z0-9][a-z0-9.-]{1,79}", value) or value.startswith("sk-"):
                raise ValidationError("Há um identificador de modelo ou voz inválido na configuração privada.")
            models[name] = value
        return cls(api_key=key, **models)

    def public_status(self) -> dict:
        return {"key_configured": bool(self.api_key), "stt_model": self.stt_model,
                "llm_model": self.llm_model, "tts_model": self.tts_model, "tts_voice": self.tts_voice}
