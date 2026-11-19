"""Tipos comuns de mensagens e contrato do modelo de linguagem."""
from dataclasses import dataclass, field
from typing import Literal, Protocol, Sequence

from .errors import ComponentUnavailable


@dataclass(frozen=True)
class Message:
    role: Literal["system", "user", "assistant"]
    content: str


@dataclass(frozen=True)
class LLMResponse:
    text: str
    model_id: str
    model_revision: str
    usage: dict = field(default_factory=dict)


class LLMBackend(Protocol):
    def generate(self, messages: Sequence[Message]) -> LLMResponse:
        """O adaptador aplica o chat template, limites de tokens e timeout."""
        ...


class UnconfiguredLLM:
    def generate(self, messages: Sequence[Message]) -> LLMResponse:
        raise ComponentUnavailable("LLM ainda não integrado. Nenhuma resposta de IA foi gerada.")


class OpenAILLM:
    sends_text_externally = True

    def __init__(self, runtime):
        self.runtime = runtime

    def generate(self, messages: Sequence[Message]) -> LLMResponse:
        from .api_runtime import numeric_usage
        from .conversation import checked_text
        from .errors import ProviderError, ValidationError
        if not messages or messages[0].role != "system":
            raise ValidationError("A conversa precisa do system prompt versionado.")
        model = self.runtime.config.llm_model
        def operation():
            with self.runtime.client_factory(**self.runtime.client_kwargs()) as client:
                return client.responses.create(model=model, instructions=messages[0].content,
                    input=[{"role": m.role, "content": m.content} for m in messages[1:]],
                    store=False, reasoning={"effort": "none"},
                    max_output_tokens=self.runtime.settings.max_output_tokens)
        response = self.runtime.call("llm", model, operation)
        if response.status != "completed":
            raise ProviderError("invalid_output")
        text = checked_text(response.output_text, self.runtime.settings.max_response_chars)
        return LLMResponse(text, model, response.model, numeric_usage(response.usage))
