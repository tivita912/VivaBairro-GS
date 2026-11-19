"""Contrato substituível de STT. Nenhum modelo é carregado na fundação."""
from dataclasses import dataclass, field
from typing import Protocol

from .audio_input import AudioInput
from .errors import ComponentUnavailable


@dataclass(frozen=True)
class Transcription:
    text: str
    language: str
    model_id: str
    model_revision: str
    usage: dict = field(default_factory=dict)


class STTBackend(Protocol):
    def transcribe(self, audio: AudioInput) -> Transcription:
        """Retorna pt; silêncio deve falhar explicitamente, sem inventar texto."""
        ...


class UnconfiguredSTT:
    def transcribe(self, audio: AudioInput) -> Transcription:
        raise ComponentUnavailable("STT ainda não integrado. Nenhuma transcrição foi gerada.")


class OpenAISTT:
    sends_audio_externally = True

    def __init__(self, runtime):
        self.runtime = runtime

    def transcribe(self, audio: AudioInput) -> Transcription:
        from .api_runtime import numeric_usage
        from .conversation import checked_text
        from .errors import ValidationError
        model = self.runtime.config.stt_model
        def operation():
            with self.runtime.client_factory(**self.runtime.client_kwargs()) as client:
                with audio.path.open("rb") as stream:
                    return client.audio.transcriptions.create(model=model, file=stream,
                        languages=["pt"], response_format="json")
        response = self.runtime.call("stt", model, operation)
        languages = [getattr(item, "code", "") for item in (getattr(response, "languages", None) or [])]
        if "pt" not in languages and "pt-BR" not in languages:
            raise ValidationError("Não foi possível reconhecer fala em português com confiança. Grave novamente.")
        return Transcription(checked_text(response.text), "pt", model,
                             getattr(response, "model", None) or "alias; revisão não informada pela API",
                             numeric_usage(getattr(response, "usage", None)))
