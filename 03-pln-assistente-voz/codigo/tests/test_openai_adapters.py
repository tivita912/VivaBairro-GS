"""Doubles explícitos de SDK/transportes; esta suíte nunca chama a rede."""
import asyncio
import base64
from dataclasses import replace
from types import SimpleNamespace as NS
from unittest.mock import Mock
import wave

from src.api_config import APIConfig
from src.api_runtime import APIRuntime, CallBudget
from src.config import Settings
from src.errors import ProviderError, ValidationError, BudgetExceeded
from src.llm import OpenAILLM, Message
from src.stt import OpenAISTT
from src.tts import OpenAIRealtimeTTS
from src.audio_input import inspect_wav
from src.privacy import Consent
from tests.helpers import LocalFilesTest


class FakeClient:
    def __init__(self):
        self.transcribe = Mock(return_value=NS(text="Há um buraco.", languages=[NS(code="pt")], usage={"seconds": 1}))
        self.generate = Mock(return_value=NS(status="completed", output_text="Descreva o local aproximado.",
                                              model="gpt-6-luna", usage={"input_tokens": 10, "output_tokens": 5}))
        self.audio = NS(transcriptions=NS(create=self.transcribe))
        self.responses = NS(create=self.generate)

    def __enter__(self): return self
    def __exit__(self, *args): pass


class AdapterTests(LocalFilesTest):
    def setUp(self):
        super().setUp()
        self.client = FakeClient()
        self.factory = Mock(return_value=self.client)
        self.runtime = APIRuntime(APIConfig("offline-test-value-not-a-credential"), Settings(),
                                 CallBudget(12), client_factory=self.factory)

    def test_stt_uses_languages_pt_and_closes_file(self):
        audio = inspect_wav(self.wav(), "upload", Consent.grant(), Settings())
        result = OpenAISTT(self.runtime).transcribe(audio)
        kwargs = self.client.transcribe.call_args.kwargs
        self.assertEqual(kwargs["languages"], ["pt"])
        self.assertNotIn("language", kwargs)
        self.assertTrue(kwargs["file"].closed)
        self.assertEqual(result.language, "pt")
        self.assertEqual(self.runtime.budget.used, 1)

    def test_stt_does_not_label_unknown_language_as_portuguese(self):
        self.client.transcribe.return_value.languages = []
        with self.assertRaises(ValidationError):
            OpenAISTT(self.runtime).transcribe(inspect_wav(self.wav(), "upload", Consent.grant(), Settings()))

    def test_llm_uses_responses_no_server_storage_and_full_history(self):
        messages = [Message("system", "REGRAS"), Message("user", "Buraco"),
                    Message("assistant", "Onde?"), Message("user", "Na praça")]
        output = OpenAILLM(self.runtime).generate(messages)
        kwargs = self.client.generate.call_args.kwargs
        self.assertFalse(kwargs["store"])
        self.assertEqual(kwargs["instructions"], "REGRAS")
        self.assertEqual(len(kwargs["input"]), 3)
        self.assertEqual(kwargs["reasoning"], {"effort": "none"})
        self.assertEqual(output.usage["input_tokens"], 10)
        self.assertEqual(self.factory.call_args.kwargs["max_retries"], 0)
        self.assertEqual(self.factory.call_args.kwargs["base_url"], "https://api.openai.com/v1")

    def test_incomplete_llm_output_is_not_spoken(self):
        self.client.generate.return_value.status = "incomplete"
        with self.assertRaises(ProviderError):
            OpenAILLM(self.runtime).generate([Message("system", "r"), Message("user", "p")])

    def test_limits_prevent_long_response_without_truncating_warning(self):
        self.client.generate.return_value.output_text = "x" * 901
        with self.assertRaises(ValidationError):
            OpenAILLM(self.runtime).generate([Message("system", "r"), Message("user", "p")])

    def test_missing_system_does_not_spend(self):
        with self.assertRaises(ValidationError):
            OpenAILLM(self.runtime).generate([Message("user", "p")])
        self.assertEqual(self.runtime.budget.used, 0)

    def test_tts_discards_changed_content_without_creating_file(self):
        class ChangedTTS(OpenAIRealtimeTTS):
            async def _generate(self, text):
                return b"\0\0" * 240, "Outro conteúdo.", {}, "test"
        with self.assertRaises(ProviderError) as error:
            ChangedTTS(self.runtime).synthesize("Texto autorizado.", self.folder)
        self.assertEqual(error.exception.code, "speech_mismatch")
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_tts_writes_valid_pcm_after_transcript_check(self):
        class LiteralTTS(OpenAIRealtimeTTS):
            async def _generate(self, text):
                return b"\0\0" * 240, "texto autorizado!", {"output_tokens": 8}, "test"
        audio = LiteralTTS(self.runtime).synthesize("Texto autorizado.", self.folder)
        with wave.open(str(audio.path), "rb") as file:
            self.assertEqual(file.getframerate(), 24000)
            self.assertEqual(file.getnframes(), 240)
        self.assertTrue(audio.transcript_verified)

    def test_realtime_protocol_events_and_explicit_zero_reconnect(self):
        sent = {}
        events = iter([
            NS(type="session.created", session=NS(model="test-realtime")),
            NS(type="session.updated", session=NS(model="test-realtime")),
            NS(type="response.output_audio.delta", delta=base64.b64encode(b"\0\0" * 100).decode()),
            NS(type="response.output_audio_transcript.done", transcript="Leia tudo."),
            NS(type="response.done", response=NS(status="completed", usage={"output_tokens": 10})),
        ])
        class Connection:
            async def __aenter__(self): return self
            async def __aexit__(self, *args): pass
            async def recv(self): return next(events)
            async def update(self, **kwargs): sent["session"] = kwargs
            async def create(self, **kwargs): sent["response"] = kwargs
            def __init__(self):
                self.session = NS(update=self.update)
                self.response = NS(create=self.create)
        class Client:
            async def __aenter__(self): return self
            async def __aexit__(self, *args): pass
            def connect(self, **kwargs):
                sent["connect"] = kwargs
                return Connection()
            def __init__(self, **kwargs): self.realtime = NS(connect=self.connect)
        self.runtime.async_client_factory = Client
        data, transcript, usage, model = asyncio.run(OpenAIRealtimeTTS(self.runtime)._generate("Leia tudo."))
        self.assertEqual(len(data), 200)
        self.assertEqual(model, "test-realtime")
        self.assertEqual(sent["connect"]["max_retries"], 0)
        self.assertEqual(sent["response"]["response"]["input"], [])
        self.assertEqual(sent["response"]["response"]["conversation"], "none")
        self.assertIn("Leia tudo.", sent["response"]["response"]["instructions"])

    def test_timeout_is_sanitized_and_budgeted(self):
        def failure(): raise TimeoutError("SENSITIVE_CONTENT_MUST_NOT_ESCAPE")
        with self.assertRaises(ProviderError) as error:
            self.runtime.call("tts", "test", failure)
        self.assertEqual(error.exception.code, "timeout")
        self.assertNotIn("SENSITIVE", str(error.exception) + str(self.runtime.records))
        self.assertEqual(self.runtime.budget.used, 1)

    def test_retry_is_explicit_and_every_attempt_counts(self):
        self.runtime.settings = replace(Settings(), retries=1)
        call = Mock(side_effect=[TimeoutError(), "ok"])
        self.assertEqual(self.runtime.call("llm", "test", call), "ok")
        self.assertEqual(self.runtime.budget.used, 2)

    def test_no_retry_beyond_budget(self):
        self.runtime.settings = replace(Settings(), retries=2)
        self.runtime.budget.limit = 1
        with self.assertRaises(BudgetExceeded):
            self.runtime.call("llm", "test", Mock(side_effect=TimeoutError()))
        self.assertEqual(self.runtime.budget.used, 1)
