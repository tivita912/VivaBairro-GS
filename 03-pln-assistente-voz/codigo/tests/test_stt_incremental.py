"""Exercita o fluxo incremental com arquivos temporários e provedor isolado."""

from argparse import Namespace
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
import wave

from evaluation.run_stt import REVIEW_FIELDS, read, run, score_results, write_csv
from evaluation.score_stt import score_manifest
from src.api_config import APIConfig
from src.stt import Transcription


class IncrementalSTTTests(unittest.TestCase):
    def setUp(self):
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.output = self.root / "results"
        self.audio = self.root / "audio"
        self.audio.mkdir()
        self.review = self.output / "stt_referencias_revisao.csv"

    @staticmethod
    def write_wav(path, amplitude):
        with wave.open(str(path), "wb") as stream:
            stream.setparams((1, 2, 16000, 0, "NONE", "not compressed"))
            stream.writeframes(amplitude.to_bytes(2, "little", signed=True) * 1600)

    def run_batch(self, calls=None, ids=None):
        with redirect_stdout(StringIO()):
            run(self.root, Namespace(modelo="gpt-transcribe", autorizar_api=calls, ids=ids,
                                     repetir_falhas=False, rascunhos_local=None))
        return {r["sample_id"]: r for r in read(self.output / "stt_resultados_parciais.csv")}

    def test_import_uses_one_review_per_hash_and_flags_replacement(self):
        original = self.audio / "original.wav"
        self.write_wav(original, 100)
        self.run_batch()
        review = read(self.review)[0]
        review.update(sample_id="R01", identification_note="Teste por conteúdo")
        write_csv(self.review, REVIEW_FIELDS, [review])
        self.write_wav(self.audio / "copia.wav", 100)
        with patch.object(APIConfig, "load") as config:
            result = self.run_batch(1)
            config.assert_not_called()
        self.assertEqual(result["R01"]["stt_status"], "PENDENTE_CONSENTIMENTO")
        self.assertEqual(result["R01"]["duplicate_count"], "2")
        self.assertEqual(len(read(self.review)), 1)
        (self.audio / "copia.wav").unlink()
        self.write_wav(original, 200)
        self.assertEqual(self.run_batch()["R01"]["status"], "ARQUIVO_ALTERADO_REVISAR")
        repeated = self.run_batch()
        self.assertEqual(repeated["R01"]["status"], "ARQUIVO_ALTERADO_REVISAR")
        self.assertEqual(len(read(self.review)), 2)
        self.assertTrue(all(repeated["G08"][field] == "PENDENTE" for field in ("status", "wer_status")))

    def test_success_is_preserved_when_another_original_arrives(self):
        self.write_wav(self.audio / "primeiro.wav", 100)
        self.run_batch()
        consent = self.root / "consents"
        consent.mkdir()
        (consent / "fixture.txt").write_text("Termo de teste unitário", encoding="utf-8")

        def confirm(mapping):
            reviews = read(self.review)
            for row in reviews:
                row.update(sample_id=mapping[row["audio_path"]], identification_note="Teste por conteúdo",
                           consent_id="fixture", consent_document="fixture.txt", external_audio_authorized="true")
            write_csv(self.review, REVIEW_FIELDS, reviews)

        with patch.object(APIConfig, "load", return_value=APIConfig("fixture")), patch(
            "evaluation.run_stt.OpenAISTT.transcribe", return_value=Transcription("Texto de teste", "pt", "gpt-transcribe", "fixture")
        ) as transcribe:
            confirm({"audio/primeiro.wav": "R01"})
            first = self.run_batch(1)["R01"]
            self.assertEqual(first["stt_status"], "TRANSCRITO")
            self.assertEqual(first["wer_status"], "PENDENTE")
            partial_score = score_manifest(self.root / "stt_manifest.csv")
            self.assertIsNone(partial_score["wer_corpus"])
            self.assertEqual(partial_score["transcribed"], 1)
            confirm({"audio/primeiro.wav": "R02"})
            relabeled = self.run_batch(1)["R02"]
            self.assertEqual(relabeled["attempt"], first["attempt"])
            self.assertEqual(relabeled["attempt_recorded_sample_id"], "R01")
            self.write_wav(self.audio / "segundo.wav", 200)
            self.run_batch()
            confirm({"audio/primeiro.wav": "R01", "audio/segundo.wav": "G08"})
            self.assertEqual(self.run_batch(1, ["R01"])["G08"]["stt_status"], "PENDENTE_AUTORIZACAO_API")
            current = self.run_batch(1, ["G08"])
            self.assertEqual(current["R01"]["attempt"], first["attempt"])
            self.assertEqual(current["G08"]["stt_status"], "TRANSCRITO")
            self.run_batch(2)
            self.assertEqual(transcribe.call_count, 2)

    def test_wer_is_weighted_and_excludes_unreviewed_references(self):
        config = dict(stt_status="TRANSCRITO", requested_model="fixture", model_revision="1",
                      environment_id="test", stt_seconds=1.0, reference_status="VERIFICADA", participant="Rafael")
        rows = [dict(config, sample_id="R01", reference="Boa", hypothesis="Outra", noise_present="true"),
                dict(config, sample_id="R02", reference="A rua está boa!", hypothesis="a rua está boa", noise_present="false"),
                dict(config, sample_id="R03", reference_status="PENDENTE", reference="A escola", hypothesis="Uma praça")]
        result = next(iter(score_results(rows).values()))["scores"]
        self.assertAlmostEqual(result["Corpus"]["wer_corpus"], 1 / 5)
        self.assertEqual(result["Com ruído"]["wer_corpus"], 1)
        self.assertEqual(result["Limpo"]["wer_corpus"], 0)
        self.assertNotIn("wer", rows[2])
