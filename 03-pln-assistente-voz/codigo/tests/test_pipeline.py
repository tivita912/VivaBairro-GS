"""Integração de contratos com doubles EXPLÍCITOS; não testa modelos nem voz real."""
from pathlib import Path

from src.config import PROJECT_ROOT, Settings
from src.conversation import Conversation
from src.errors import ConsentRequired, ValidationError
from src.knowledge import KnowledgeBase
from src.llm import LLMResponse
from src.pipeline import VoicePipeline
from src.privacy import Consent, private_workspace
from src.speech_text import SpeechText
from src.stt import Transcription
from src.tts import SynthesizedAudio
from tests.helpers import LocalFilesTest


class SyntheticSTT:
    calls = 0

    def transcribe(self, audio):
        self.calls += 1
        self.last_path = audio.path
        return Transcription("Há uma calçada danificada.", "pt", "TEST_DOUBLE", "synthetic-v1")


class SyntheticLLM:
    def __init__(self, stt):
        self.stt = stt

    def generate(self, messages):
        assert not self.stt.last_path.exists(), "A cópia deve ser apagada antes do LLM"
        self.messages = messages
        return LLMResponse("Descreva o obstáculo observado.", "TEST_DOUBLE", "synthetic-v1")


class SyntheticSpeech:
    def adapt(self, text):
        return SpeechText(text)


class SyntheticTTS:
    sends_text_externally = False

    def synthesize(self, text, output_dir):
        path = output_dir / "synthetic-not-playable.bin"
        path.write_bytes(b"TEST ONLY - NOT AUDIO")
        return SynthesizedAudio(path, "application/octet-stream", "TEST_DOUBLE", "synthetic")


class PipelineTests(LocalFilesTest):
    def setUp(self):
        super().setUp()
        self.stt = SyntheticSTT()
        self.llm = SyntheticLLM(self.stt)
        self.pipeline = VoicePipeline(self.stt, self.llm, SyntheticSpeech(), SyntheticTTS(),
            KnowledgeBase.load(PROJECT_ROOT / "knowledge/urban_guidance.json"),
            PROJECT_ROOT / "prompts/system_v1.txt", Settings())
        self.session = Conversation()
        self.original = self.wav()
        self.output = self.folder / "output"
        self.output.mkdir()

    def run_turn(self, consent=None):
        return self.pipeline.run(self.original, "upload", self.session, consent or Consent.grant(),
                                 self.folder / "input", self.output)

    def test_contract_sequence_and_followup_context(self):
        first = self.run_turn()
        self.assertTrue(first.audio.path.exists())
        self.assertIsNone(first.metrics["playback_start_seconds"])
        self.run_turn()
        self.assertEqual(len(self.session.turns), 2)
        self.assertEqual(len(self.llm.messages), 4)
        self.assertTrue(self.original.exists())

    def test_external_consent_checked_before_stt(self):
        self.pipeline.tts.sends_text_externally = True
        with self.assertRaises(ConsentRequired):
            self.run_turn()
        self.assertEqual(self.stt.calls, 0)

    def test_no_consent_no_work(self):
        with self.assertRaises(ConsentRequired):
            self.run_turn(Consent())
        self.assertEqual(self.stt.calls, 0)

    def test_llm_failure_leaves_history_clean(self):
        class FailingLLM:
            def generate(self, messages):
                raise RuntimeError("synthetic provider failure")
        self.pipeline.llm = FailingLLM()
        with self.assertRaises(RuntimeError):
            self.run_turn()
        self.assertFalse(self.stt.last_path.exists())
        self.assertEqual(self.session.turns, ())

    def test_provider_cannot_return_unowned_path(self):
        original = self.original
        class OutsideTTS(SyntheticTTS):
            def synthesize(self, text, output_dir):
                return SynthesizedAudio(original, "audio/wav", "TEST_DOUBLE", "synthetic")
        self.pipeline.tts = OutsideTTS()
        with self.assertRaises(ValidationError):
            self.run_turn()
        self.assertTrue(self.original.exists())
        self.assertEqual(self.session.turns, ())

    def test_output_lifetime_owned_by_caller(self):
        with private_workspace(self.folder / "private_outputs", Consent.grant()) as output:
            result = self.pipeline.run(self.original, "upload", self.session, Consent.grant(),
                                       self.folder / "input", output)
            path = result.audio.path
            self.assertTrue(path.exists())
        self.assertFalse(path.exists())
