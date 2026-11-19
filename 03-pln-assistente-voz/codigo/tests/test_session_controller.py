from dataclasses import replace

from src.config import Settings, PROJECT_ROOT
from src.controller import VoiceController
from src.errors import ConsentRequired, BudgetExceeded, ValidationError, ProviderError
from src.knowledge import KnowledgeBase
from src.pipeline import VoicePipeline
from src.privacy import Consent
from src.session import remove_owned
from tests.helpers import LocalFilesTest
from tests.test_pipeline import SyntheticSTT, SyntheticLLM, SyntheticSpeech, SyntheticTTS


class SessionTests(LocalFilesTest):
    def setUp(self):
        super().setUp()
        self.settings = Settings()
        self.stt = SyntheticSTT()
        self.llm = SyntheticLLM(self.stt)
        self.tts = SyntheticTTS()
        def pipeline_factory(session):
            return VoicePipeline(self.stt, self.llm, SyntheticSpeech(), self.tts,
                KnowledgeBase.load(PROJECT_ROOT / "knowledge/urban_guidance.json"),
                PROJECT_ROOT / "prompts/system_v1.txt", self.settings), None
        self.controller = VoiceController(self.settings, self.folder, None, pipeline_factory=pipeline_factory)
        self.addCleanup(self.controller.close)
        self.session = self.controller.new_session()

    def authorize(self):
        self.controller.authorize(self.session, True, True, True)

    def test_no_consent_means_no_stt(self):
        with self.assertRaises(ConsentRequired):
            self.controller.process(self.session, self.wav(), "microphone")
        self.assertEqual(self.stt.calls, 0)

    def test_separate_audio_consent_is_required_by_pipeline(self):
        self.stt.sends_audio_externally = True
        pipeline, _ = self.controller.pipeline(self.session)
        with self.assertRaises(ConsentRequired):
            pipeline.run(self.wav(), "upload", self.session.conversation, Consent.grant(external_text=True),
                         self.folder / "inputs", self.folder)
        self.assertEqual(self.stt.calls, 0)

    def test_clear_removes_audio_history_and_consent_but_not_usage(self):
        self.authorize()
        self.session.budget.take()
        result = self.controller.process(self.session, self.wav(), "microphone")
        path = result.audio.path
        self.assertTrue(path.exists())
        self.session.clear(revoke=True)
        self.assertFalse(path.exists())
        self.assertEqual(self.session.conversation.turns, ())
        self.assertFalse(self.session.consent.accepted)
        self.assertEqual(self.session.budget.used, 1)

    def test_original_upload_copy_is_removed_after_processing(self):
        self.authorize()
        path = self.wav()
        self.controller.process(self.session, path, "upload")
        self.assertFalse(path.exists())

    def test_tts_failure_keeps_transcription_visible_without_history_commit(self):
        self.authorize()
        self.tts.synthesize = lambda *args: (_ for _ in ()).throw(ProviderError("timeout"))
        with self.assertRaises(ProviderError):
            self.controller.process(self.session, self.wav(), "upload")
        self.assertTrue(self.session.pending["transcription"])
        self.assertTrue(self.session.pending["response"])
        self.assertEqual(self.session.conversation.turns, ())
        self.assertTrue(self.session.metrics["failed"])

    def test_two_sessions_have_separate_history_and_files(self):
        second = self.controller.new_session()
        self.authorize()
        self.controller.process(self.session, self.wav(), "upload")
        self.assertEqual(second.conversation.turns, ())
        self.assertNotEqual(second.folder, self.session.folder)

    def test_reserve_entire_turn_before_spending(self):
        self.authorize()
        self.session.budget.used = self.session.budget.limit - 2
        with self.assertRaises(BudgetExceeded):
            self.controller.process(self.session, self.wav(), "upload")
        self.assertEqual(self.stt.calls, 0)

    def test_cleanup_cannot_remove_root_or_external_original(self):
        with self.assertRaises(ValidationError): remove_owned(self.folder, self.folder)
        with self.assertRaises(ValidationError): remove_owned(self.folder.parent / "outside.wav", self.folder)

    def test_expired_session_requires_new_consent(self):
        self.authorize()
        self.session.close()
        with self.assertRaises(ValidationError):
            self.controller.process(self.session, self.wav(), "upload")

    def test_revocation_blocks_all_external_operations(self):
        self.authorize()
        self.controller.authorize(self.session, True, False, True)
        with self.assertRaises(ConsentRequired):
            self.controller.process(self.session, self.wav(), "upload")
