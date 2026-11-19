from src.audio_input import inspect_wav, prepare_audio
from src.config import Settings
from src.errors import ConsentRequired, ValidationError
from src.privacy import Consent
from tests.helpers import LocalFilesTest


class AudioTests(LocalFilesTest):
    def test_both_origins_share_same_format(self):
        path = self.wav()
        for source in ("upload", "microphone"):
            audio = inspect_wav(path, source, Consent.grant(), Settings())
            self.assertEqual(audio.sample_rate, 16000)
            self.assertAlmostEqual(audio.duration_seconds, 0.02)

    def test_consent_before_file_access(self):
        with self.assertRaises(ConsentRequired):
            inspect_wav(self.folder / "missing", "upload", Consent(), Settings())

    def test_invalid_header(self):
        path = self.folder / "wrong.wav"
        path.write_text("not audio")
        with self.assertRaises(ValidationError):
            inspect_wav(path, "upload", Consent.grant(), Settings())

    def test_limits_empty_duration_format_and_origin(self):
        for duration, width, source in [(0, 2, "upload"), (1.1, 2, "upload"),
                                        (0.02, 1, "upload"), (0.02, 2, "remote")]:
            with self.subTest(duration=duration, width=width, source=source):
                with self.assertRaises(ValidationError):
                    inspect_wav(self.wav(duration, width=width), source, Consent.grant(),
                                Settings(max_audio_seconds=1))

    def test_truncated_content_rejected(self):
        path = self.wav()
        path.write_bytes(path.read_bytes()[:-10])
        with self.assertRaises(ValidationError):
            inspect_wav(path, "upload", Consent.grant(), Settings())

    def test_cleanup_success_and_original_preserved(self):
        original = self.wav()
        original_bytes = original.read_bytes()
        with prepare_audio(original, "upload", Consent.grant(), Settings(), self.folder / "runtime") as audio:
            copy = audio.path
            self.assertTrue(copy.exists())
            self.assertNotEqual(copy, original)
        self.assertFalse(copy.exists())
        self.assertEqual(original.read_bytes(), original_bytes)

    def test_cleanup_on_provider_failure(self):
        original = self.wav()
        with self.assertRaises(RuntimeError):
            with prepare_audio(original, "upload", Consent.grant(), Settings(), self.folder / "runtime") as audio:
                copy = audio.path
                raise RuntimeError("synthetic provider failure")
        self.assertFalse(copy.exists())
        self.assertTrue(original.exists())

    def compressed(self, seconds=0.02):
        import av
        import numpy as np
        path = self.folder / "synthetic.flac"
        with av.open(str(path), "w", format="flac") as container:
            stream = container.add_stream("flac", rate=16000)
            stream.layout = "mono"
            frame = av.AudioFrame.from_ndarray(np.zeros((1, int(16000 * seconds)), dtype=np.int16), format="s16", layout="mono")
            frame.sample_rate = 16000
            for packet in stream.encode(frame): container.mux(packet)
            for packet in stream.encode(None): container.mux(packet)
        return path

    def test_compressed_audio_decodes_to_common_contract(self):
        path = self.compressed()
        with prepare_audio(path, "upload", Consent.grant(), Settings(), self.folder / "runtime") as audio:
            self.assertEqual(audio.path.suffix, ".wav")
            self.assertEqual(audio.sample_rate, 16000)
            self.assertAlmostEqual(audio.duration_seconds, 0.02)
        self.assertTrue(path.exists())

    def test_duration_limit_applies_to_decoded_audio(self):
        with self.assertRaises(ValidationError):
            with prepare_audio(self.compressed(1.1), "upload", Consent.grant(), Settings(max_audio_seconds=1), self.folder / "runtime"):
                pass
        self.assertEqual(list((self.folder / "runtime").iterdir()), [])
