from io import BytesIO
from uuid import uuid4
from unittest.mock import patch
import wave

from fastapi.testclient import TestClient

from app import diagnose
from src.api_config import APIConfig
from src.config import PROJECT_ROOT, Settings
from src.errors import ComponentUnavailable, ProviderError
from src.knowledge import KnowledgeBase
from src.pipeline import VoicePipeline
from src.privacy import NOTICE_VERSION
from src.tts import SynthesizedAudio
from src.web import create_app
from tests.helpers import LocalFilesTest
from tests.test_pipeline import SyntheticLLM, SyntheticSpeech, SyntheticSTT


class TestWavTTS:
    sends_text_externally = False

    def synthesize(self, text, output_dir):
        path = output_dir / f"{uuid4()}.wav"
        with wave.open(str(path), "wb") as audio:
            audio.setparams((1, 2, 24000, 0, "NONE", "not compressed"))
            audio.writeframes(b"\x00\x00" * 240)
        return SynthesizedAudio(path, "audio/wav", "TEST_DOUBLE", "synthetic")


class AppTests(LocalFilesTest):
    def setUp(self):
        super().setUp()
        self.settings = Settings(max_audio_mb=1)
        self.stt = SyntheticSTT()
        self.llm = SyntheticLLM(self.stt)
        self.tts = TestWavTTS()
        self.base = KnowledgeBase.load(PROJECT_ROOT / "knowledge/urban_guidance.json")
        with patch.object(APIConfig, "load", return_value=APIConfig("offline-test-value-not-a-credential")):
            self.app = create_app(self.settings, pipeline_factory=self.pipeline_factory)
        self.client = self.enterContext(TestClient(self.app))

    def pipeline_factory(self, session):
        return VoicePipeline(self.stt, self.llm, SyntheticSpeech(), self.tts, self.base,
                             PROJECT_ROOT / "prompts/system_v1.txt", self.settings), None

    def authorize(self, headers=None, **changes):
        choices = dict(accepted=True, external_audio=True, external_text=True, notice_version=NOTICE_VERSION)
        response = self.client.post("/api/consent", json=choices | changes, headers=headers)
        return response

    def upload(self, headers=None, content=None, source="upload"):
        return self.client.post(f"/api/turn?format=wav&source={source}",
                                content=self.wav().read_bytes() if content is None else content,
                                headers={"Content-Type": "application/octet-stream"} | (headers or {}))

    def test_diagnostic_does_not_claim_voice_success(self):
        report = diagnose(Settings())
        self.assertEqual(report["knowledge_entries"], 5)
        self.assertEqual(report["voice_end_to_end"], "not_tested")

    def test_renders_voice_flow_and_assets(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        for marker in ('lang="pt-BR"', 'id="capture-controls" hidden', 'id="consent-form"',
                       'id="transcription"', 'id="answer-audio"', 'id="history"', 'id="metrics"',
                       'id="retry"', 'id="clear"'):
            self.assertIn(marker, response.text)
        self.assertEqual(response.text.count('type="checkbox"'), 3)
        self.assertNotIn("checked", response.text)
        self.assertEqual(response.headers["cache-control"], "no-store")
        for asset in ("site.css", "site.js", "latency.mjs", "bairro.webp", "icon.svg"):
            self.assertEqual(self.client.get("/assets/" + asset).status_code, 200)
        self.assertIn("javascript", self.client.get("/assets/latency.mjs").headers["content-type"])
        info = self.client.get("/api/info")
        self.assertEqual(len(info.json()["topics"]), 5)
        self.assertNotIn("offline-test-value-not-a-credential", info.text)

    def test_consent_checks_each_choice_and_notice_version(self):
        for option in ("accepted", "external_audio", "external_text"):
            self.assertEqual(self.authorize(**{option: False}).status_code, 403)
        self.assertEqual(self.authorize(notice_version="older").status_code, 403)
        self.assertEqual(self.authorize(accepted="true").status_code, 422)
        self.assertEqual(self.upload().status_code, 410)
        self.assertEqual(self.stt.calls, 0)

    def test_upload_uses_pipeline_and_audio_belongs_to_the_session(self):
        first = {"X-VivaBairro-Session": self.authorize().json()["session"]}
        second = {"X-VivaBairro-Session": self.authorize().json()["session"]}
        turn = self.upload(first, source="microphone")
        self.assertEqual(turn.status_code, 200, turn.text)
        data = turn.json()
        self.assertTrue(data["transcription"])
        self.assertTrue(data["response"])
        self.assertEqual(len(data["history"]), 2)
        self.assertIn("stt", data["metrics"]["stage_seconds"])
        self.assertGreater(data["metrics"]["input_audio_duration_seconds"], 0)
        self.assertIn("handler;dur=", turn.headers["server-timing"])
        self.assertIn("body;dur=", turn.headers["server-timing"])
        self.assertIsNone(data["metrics"]["playback_start_seconds"])
        self.assertEqual(self.client.get(data["audio_url"], headers=second).status_code, 404)
        self.assertEqual(self.client.get(data["audio_url"]).status_code, 410)
        playback = self.client.get(data["audio_url"], headers=first)
        self.assertEqual(playback.status_code, 200)
        self.assertEqual(playback.headers["cache-control"], "no-store")
        self.assertIn("audio;dur=", playback.headers["server-timing"])
        with wave.open(BytesIO(playback.content), "rb") as audio:
            self.assertGreater(audio.getnframes(), 0)
        followup = self.upload(first).json()
        self.assertEqual(len(followup["history"]), 4)
        self.assertEqual(self.client.get(data["audio_url"], headers=first).status_code, 404)
        self.assertEqual(len(self.upload(second).json()["history"]), 2)

    def test_clear_revokes_audio_and_preserves_session_identity(self):
        token = self.authorize().json()["session"]
        headers = {"X-VivaBairro-Session": token}
        url = self.upload(headers).json()["audio_url"]
        self.assertEqual(self.client.post("/api/clear", headers=headers).status_code, 200)
        self.assertEqual(self.client.get(url, headers=headers).status_code, 403)
        self.assertEqual(self.upload(headers).status_code, 403)
        self.assertEqual(self.authorize(headers).json()["session"], token)
        self.assertEqual(self.client.get(url, headers=headers).status_code, 404)
        self.assertEqual(len(self.upload(headers).json()["history"]), 2)

    def test_upload_limit_discards_temporary_file(self):
        headers = {"X-VivaBairro-Session": self.authorize().json()["session"]}
        self.assertEqual(self.upload(headers, b"0" * (1024 * 1024 + 1)).status_code, 413)
        self.assertEqual(list(self.app.state.controller.root.glob("upload-*")), [])
        self.assertEqual(self.stt.calls, 0)

    def test_late_failure_keeps_text_and_leaves_no_audio_or_history(self):
        def fail(text, output):
            raise ProviderError("timeout")

        self.tts.synthesize = fail
        headers = {"X-VivaBairro-Session": self.authorize().json()["session"]}
        response = self.upload(headers)
        self.assertEqual(response.status_code, 502)
        data = response.json()
        self.assertTrue(data["transcription"])
        self.assertTrue(data["response"])
        self.assertEqual(data["history"], [])
        self.assertNotIn("audio_url", data)
        self.assertEqual(list(self.app.state.controller.root.rglob("*.wav")), [])

    def test_stt_network_failure_is_identified_without_leaking_secrets(self):
        def fail(audio):
            raise ProviderError("network")
        self.stt.transcribe = fail
        headers = {"X-VivaBairro-Session": self.authorize().json()["session"]}
        response = self.upload(headers)
        self.assertEqual(response.status_code, 502)
        data = response.json()
        self.assertEqual(data["error_code"], "network")
        self.assertNotIn("transcription", data)
        self.assertEqual(data["history"], [])
        self.assertNotIn("offline-test-value-not-a-credential", response.text)
        script = self.client.get("/assets/site.js").text
        self.assertIn("retryable && !data.transcription && selected", script)
        self.assertIn("Reenviar poderá consumir uma nova chamada", script)

    def test_missing_configuration_disables_consent(self):
        with patch.object(APIConfig, "load", side_effect=ComponentUnavailable("Configuração indisponível.")):
            app = create_app(self.settings)
        with TestClient(app) as client:
            self.assertFalse(client.get("/api/info").json()["available"])
            response = client.post("/api/consent", json=dict(accepted=True, external_audio=True,
                                   external_text=True, notice_version=NOTICE_VERSION))
            self.assertEqual(response.status_code, 503)
