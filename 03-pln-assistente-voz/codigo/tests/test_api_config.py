import os
from unittest.mock import patch

from src.api_config import APIConfig
from src.api_runtime import CallBudget, safe_provider_error, numeric_usage
from src.errors import ComponentUnavailable, ValidationError, BudgetExceeded
from tests.helpers import LocalFilesTest


class APIConfigTests(LocalFilesTest):
    def test_reads_localappdata_without_overwriting_or_exposing_secret(self):
        folder = self.folder / "VivaBairroVoz"
        folder.mkdir()
        path = folder / ".env"
        content = "OPENAI_API_KEY=offline-test-value-not-a-credential\nOPENAI_TTS_VOICE=marin\n"
        path.write_text(content, encoding="utf-8")
        with patch.dict(os.environ, {"LOCALAPPDATA": str(self.folder)}, clear=True):
            config = APIConfig.load()
            self.assertNotIn("OPENAI_API_KEY", os.environ)
        self.assertEqual(path.read_text(encoding="utf-8"), content)
        self.assertNotIn(config.api_key, repr(config))
        self.assertNotIn(config.api_key, str(config.public_status()))

    def test_missing_and_placeholder_keys_fail_safely(self):
        path = self.folder / ".env"
        with self.assertRaises(ComponentUnavailable):
            APIConfig.load(path)
        path.write_text("OPENAI_API_KEY=COLE_SUA_CHAVE_AQUI")
        with self.assertRaises(ComponentUnavailable):
            APIConfig.load(path)

    def test_model_identifier_cannot_leak_key_as_model(self):
        path = self.folder / ".env"
        path.write_text("OPENAI_API_KEY=offline-test-value-not-a-credential\nOPENAI_LLM_MODEL=sk-not-a-real-key")
        with self.assertRaises(ValidationError) as error:
            APIConfig.load(path)
        self.assertNotIn("sk-", str(error.exception))

    def test_budget_persists_and_does_not_allow_extra_attempt(self):
        path = self.folder / "ledger.json"
        budget = CallBudget(1, ledger=path)
        budget.take()
        restored = CallBudget(1, ledger=path)
        with self.assertRaises(BudgetExceeded): restored.take()
        self.assertEqual(restored.used, 1)

    def test_http_errors_never_expose_response_body(self):
        for status, expected in [(401, "authentication"), (403, "permission"), (429, "rate_limit"), (404, "invalid_request")]:
            error = RuntimeError("PRIVATE_TEST_STRING")
            error.status_code = status
            safe = safe_provider_error(error)
            self.assertEqual(safe.code, expected)
            self.assertNotIn("PRIVATE_TEST_STRING", str(safe))

    def test_usage_filters_out_text(self):
        self.assertEqual(numeric_usage({"input_tokens": 7, "prompt": "PRIVATE_TEST_STRING", "details": {"audio_tokens": 2}}),
                         {"input_tokens": 7, "details": {"audio_tokens": 2}})
