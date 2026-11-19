import csv

from evaluation.score_stt import score_manifest
from evaluation.academic_metrics import assess_comparison, assess_llm, read, run
from src.config import PROJECT_ROOT
from src.errors import ValidationError
from tests.helpers import LocalFilesTest


class EvaluationTests(LocalFilesTest):
    def manifest(self, rows):
        path = self.folder / "synthetic.csv"
        fields = ["sample_id", "data_origin", "speaker_id", "noise_present", "reference_text",
                  "hypothesis_text", "transcription_completed", "consent_id", "model_id", "model_revision", "environment_id"]
        with path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
        return path

    def row(self):
        return dict(sample_id="SYNTHETIC-1", data_origin="synthetic_development", speaker_id="NOT_A_PERSON",
                    noise_present="false", reference_text="há um buraco", hypothesis_text="há dois buraco",
                    transcription_completed="true", consent_id="NOT_APPLICABLE_SYNTHETIC",
                    model_id="TEST_DOUBLE", model_revision="test", environment_id="unit-test")

    def test_blank_templates_cannot_produce_results(self):
        path = self.manifest([])
        with self.assertRaises(ValidationError):
            score_manifest(path)

    def test_synthetic_is_never_real_coverage(self):
        result = score_manifest(self.manifest([self.row()]))
        self.assertFalse(result["quantity_gate_met"])
        self.assertEqual(result["data_origin"], "synthetic_development")
        self.assertAlmostEqual(result["wer_corpus"], 1 / 3)

    def test_mixed_origins_and_duplicates_rejected(self):
        one = self.row()
        for second in [one, dict(one, sample_id="2", data_origin="real")]:
            with self.assertRaises(ValidationError):
                score_manifest(self.manifest([one, second]))

    def test_missing_transcription_is_not_automatic_zero(self):
        row = dict(self.row(), transcription_completed="false")
        with self.assertRaises(ValidationError):
            score_manifest(self.manifest([row]))

    def test_collection_tables_have_headers(self):
        for path in (PROJECT_ROOT / "evaluation").glob("*.csv"):
            with self.subTest(path=path.name):
                with path.open(encoding="utf-8", newline="") as stream:
                    reader = csv.DictReader(stream)
                    self.assertTrue(reader.fieldnames)

    def test_llm_catalog_counts_and_antecedents(self):
        rows = read(PROJECT_ROOT / "evaluation/llm_questions.csv")
        self.assertEqual(len(rows), 30)
        self.assertEqual(sum(r["category"] == "continuation" for r in rows), 5)
        self.assertEqual(sum(r["category"] == "out_of_scope" for r in rows), 5)
        by_id = {r["question_id"]: r for r in rows}
        for row in rows:
            if row["category"] == "continuation":
                self.assertEqual(by_id[row["previous_question_id"]]["question"], row["context"])

    def test_llm_counts_inconclusive_cases_outside_denominator(self):
        catalog = read(PROJECT_ROOT / "evaluation/llm_questions.csv")
        fixture = dict(question_id="Q26", run_id="UNIT", data_origin="real", review_status="reviewed",
                       actual_answer="Fixture de teste", model_id="fixture", model_revision="1", prompt_version="test",
                       knowledge_version="test", evaluator_id="fixture", notes="Teste de fórmula", correct="true",
                       refusal_appropriate="true", error_type="")
        result = assess_llm(catalog, [fixture, dict(fixture, question_id="Q27", error_type="timeout")])
        self.assertEqual(result["refusal_percent"], 100)
        self.assertEqual(result["categories"]["out_of_scope"]["n"], 1)
        self.assertEqual(result["excluded_by_reason"], {"execution_failure": 1})
        self.assertFalse(result["complete"])
        with self.assertRaises(ValidationError):
            assess_llm(catalog, [dict(fixture, data_origin="synthetic_development")])

    def test_comparison_requires_matched_case_and_run(self):
        fixture = dict(data_origin="real", component="llm", dataset_version="fixture", environment_id="fixture",
                       quality_metric="correct_binary", config_id="A", sample_id="Q01", run_index="1",
                       warmup="false", cold_start="false", quality_value="1", latency_seconds="0.2")
        second = dict(fixture, config_id="B", sample_id="Q02")
        self.assertFalse(assess_comparison([fixture, second])["complete"])
        paired = assess_comparison([fixture, dict(second, sample_id="Q01")])
        self.assertEqual(paired["n_pairs"], 1)

    def test_empty_academic_evidence_yields_null_metrics(self):
        names = ("stt_manifest", "llm_questions", "llm_ratings", "tts_samples",
                 "tts_ratings", "e2e_sessions", "model_comparison")
        for name in names:
            (self.folder / f"{name}.csv").write_text("id\n", encoding="utf-8")
        result = run(self.folder)
        self.assertTrue(all(result[key] is None for key in ("stt", "llm", "tts", "e2e", "comparison")))

    def test_tts_samples_without_human_ratings_export_cleanly(self):
        from evaluation.academic_metrics import assess_tts, export
        fixture_audio = self.folder / "tts_dummy_unit_test.wav"
        fixture_audio.write_bytes(b"unit-test-nonempty-file")
        fixture = dict(sample_id="T01", data_origin="real", status="success",
                       text="Teste", adapted_text="Teste", voice_id="dummy",
                       provider="unit_test", provider_version="fixture", audio_path=str(fixture_audio))
        assessed = assess_tts([fixture], [])
        self.assertFalse(assessed["complete"])
        self.assertEqual(assessed["ratings"], 0)
        self.assertEqual(assessed["per_sample"], {})
        result = dict(stt=None, llm=None, tts=assessed, e2e=None, comparison=None)
        destination = self.folder / "export_no_ratings"
        export(result, destination)
        self.assertTrue((destination / "metrics.json").is_file())
