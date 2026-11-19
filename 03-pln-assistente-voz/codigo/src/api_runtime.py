"""Limites de chamadas, SDK oficial e tradução segura de falhas."""
from dataclasses import dataclass, field
import json
import logging
from pathlib import Path
import threading
import time
from typing import Callable

import openai

from .api_config import APIConfig
from .config import Settings
from .errors import BudgetExceeded, ProviderError


@dataclass
class CallBudget:
    limit: int
    used: int = 0
    ledger: Path | None = None
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)

    def __post_init__(self):
        if self.ledger and self.ledger.exists():
            self.used = int(json.loads(self.ledger.read_text(encoding="utf-8"))["attempts"])

    def require_capacity(self, count: int = 1):
        if self.used + count > self.limit:
            raise BudgetExceeded("O limite de chamadas desta sessão ou verificação foi atingido. Limpar a conversa não reinicia o contador.")

    def take(self):
        with self._lock:
            self.require_capacity()
            self.used += 1
            if self.ledger:
                self.ledger.parent.mkdir(parents=True, exist_ok=True)
                self.ledger.write_text(json.dumps({"attempts": self.used, "limit": self.limit}), encoding="utf-8")


def safe_provider_error(exc: Exception) -> ProviderError:
    if isinstance(exc, ProviderError):
        return exc
    status = getattr(exc, "status_code", None)
    if status is None:
        status = getattr(getattr(exc, "response", None), "status_code", None)
    if status == 401:
        code = "authentication"
    elif status == 403:
        code = "permission"
    elif status == 429:
        code = "rate_limit"
    elif status in {400, 404, 422}:
        code = "invalid_request"
    elif isinstance(exc, (TimeoutError, openai.APITimeoutError)):
        code = "timeout"
    elif isinstance(exc, (openai.APIConnectionError, ConnectionError, OSError)):
        code = "network"
    else:
        code = "unavailable"
    return ProviderError(code, status if isinstance(status, int) else None)


def numeric_usage(value) -> dict:
    """Permite apenas consumo numérico e subcampos; nenhum corpo/prompt/transcrição."""
    if hasattr(value, "model_dump"):
        value = value.model_dump()
    if not isinstance(value, dict):
        return {}
    result = {}
    for key, item in value.items():
        if isinstance(item, (int, float)) and not isinstance(item, bool):
            result[key] = item
        elif isinstance(item, dict):
            result[key] = numeric_usage(item)
    return result


class APIRuntime:
    def __init__(self, config: APIConfig, settings: Settings, budget: CallBudget,
                 client_factory=openai.OpenAI, async_client_factory=openai.AsyncOpenAI):
        self.config, self.settings, self.budget = config, settings, budget
        self.client_factory, self.async_client_factory = client_factory, async_client_factory
        self.records: list[dict] = []
        # Bibliotecas de transporte não devem emitir headers/corpos mesmo se debug externo estiver ativo.
        for name in ("openai", "httpx", "httpx2", "httpcore", "httpcore2", "websockets", "dotenv.main"):
            logging.getLogger(name).setLevel(logging.CRITICAL)

    def client_kwargs(self):
        return {"api_key": self.config.api_key, "base_url": "https://api.openai.com/v1",
                "websocket_base_url": "wss://api.openai.com/v1",
                "timeout": self.settings.timeout_seconds, "max_retries": 0}

    def call(self, component: str, model: str, operation: Callable):
        for attempt in range(self.settings.retries + 1):
            self.budget.take()  # SDK retries/reconnect estão desativados, cada tentativa conta.
            started = time.perf_counter()
            try:
                result = operation()
            except BudgetExceeded:
                raise
            except Exception as exc:
                error = safe_provider_error(exc)
                self.records.append({"component": component, "model": model, "ok": False,
                                     "seconds": time.perf_counter() - started,
                                     "error_code": error.code, "http_status": error.status})
                if attempt < self.settings.retries and error.code in {"network", "timeout", "rate_limit", "unavailable"}:
                    time.sleep(min(2 ** attempt, 2))
                    continue
                raise error from None
            self.records.append({"component": component, "model": model, "ok": True,
                                 "seconds": time.perf_counter() - started})
            return result

    def authenticate(self) -> dict:
        def operation():
            with self.client_factory(**self.client_kwargs()) as client:
                # Uma requisição sem conteúdo pessoal e sem inferência paga.
                page = client.models.list()
                return {item.id for item in page.data}
        available = self.call("authentication", "models.list", operation)
        return {"authenticated": True, "listed": {model: model in available for model in
                (self.config.stt_model, self.config.llm_model, self.config.tts_model)},
                "limitation": "Listagem não comprova permissão efetiva em cada endpoint."}
