import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import wave

from evaluation.importar_gustavo import ingest
from evaluation.importar_notas_tts import FIELDS, merge
from evaluation.run_stt import attempt_key, build_results, digest, write_csv
from scripts.transferir_gs import make_archive, restore
from src.errors import ValidationError


class HandoffTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name)

    def test_preserves_paid_stt_on_another_machine(self):
        audio = dict(sha256="original", prepared_sha256="wav-new", audio_path="audio/original.wav", app_compatible="true")
        review = dict(sample_id="R01", sha256="original", audio_path=audio["audio_path"], consent_id="historical-consent")
        saved = dict(sha256="original", prepared_sha256="wav-old", requested_model="gpt-transcribe",
                     consent_id="historical-consent", environment_id="old", stt_status="TRANSCRITO",
                     attempt="original-attempt", sample_id="R02", hypothesis="fixture")
        args = self.root, [audio], {"original": review}, {attempt_key(saved): saved}, "gpt-transcribe", "new"
        chosen = build_results(*args)[0]
        self.assertEqual((chosen["stt_status"], chosen["environment_id"], chosen["prepared_sha256"]), ("TRANSCRITO", "old", "wav-old"))
        self.assertFalse(chosen["external_eligible"])
        reserved = build_results(*args[:3], {}, *args[4:], reserved={("original", "gpt-transcribe")})[0]
        self.assertEqual(reserved["stt_status"], "PENDENTE_RESTAURAR_HISTORICO")

    def test_ingest_without_guessing_id_is_idempotent(self):
        src = self.root / "incoming"
        src.mkdir()
        e = self.root / "evaluation"
        source = src / "fixture.wav"
        with wave.open(str(source), "wb") as out:
            out.setparams((1, 2, 16000, 0, "NONE", "not compressed"))
            out.writeframes(bytes(3200))
        self.assertEqual(ingest(src, e), (1, []))
        self.assertEqual(digest(source), digest(e / "audio/Gustavo/fixture.wav"))
        self.assertEqual(ingest(src, e), (0, ["fixture.wav"]))
        (src / "corrupt.ogg").write_bytes(b"fixture invalid")
        with self.assertRaises(ValidationError):
            ingest(src, e)
        self.assertFalse((e / "audio/Gustavo/corrupt.ogg").exists())
        with self.assertRaises(ValidationError):
            ingest(src / "missing", e)

    def test_transfer_preserves_identical_and_conflicting_files(self):
        (self.root / "app.py").write_bytes(b"fixture")
        archive = self.root / "pack.zip"
        make_archive(archive, {"evaluation/tts_ratings.csv": b"fixture evidence"}, "evidencias")
        self.assertEqual(restore(archive, digest(archive), self.root, dry_run=True), (1, 0))
        target = self.root / "evaluation/tts_ratings.csv"
        self.assertFalse(target.exists())
        self.assertEqual(restore(archive, digest(archive), self.root), (1, 0))
        self.assertEqual(restore(archive, digest(archive), self.root), (0, 1))
        target.write_bytes(b"newer fixture evidence")
        with self.assertRaises(ValidationError):
            restore(archive, digest(archive), self.root)
        self.assertEqual(target.read_bytes(), b"newer fixture evidence")

    def test_tts_rating_merge_does_not_overwrite(self):
        ids = [f"T{n:02d}" for n in range(1, 11)]
        source = self.root / "test.csv"
        rows = [dict(sample_id=sid, evaluator_id="P01", clarity_1_to_5="4", naturalness_1_to_5="5",
                     evaluated_on="2026-11-17", notes="fixture", audio_sha256=sid) for sid in ids]
        write_csv(source, FIELDS, rows)
        with patch("evaluation.importar_notas_tts.verify_samples", return_value=[dict(sample_id=i, sha256=i) for i in ids]):
            self.assertEqual(merge([source], self.root), 10)
            self.assertEqual(merge([source], self.root), 10)
            target = self.root / "tts_ratings.csv"
            old = target.read_bytes()
            rows[0]["clarity_1_to_5"] = "3"
            write_csv(source, FIELDS, rows)
            with self.assertRaises(ValidationError):
                merge([source], self.root)
            self.assertEqual(target.read_bytes(), old)
