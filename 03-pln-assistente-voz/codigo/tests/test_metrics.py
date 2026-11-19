import unittest

from src.errors import ValidationError
from src.metrics import LatencyTracker, percentage, rating_mean, stt_scores


class MetricTests(unittest.TestCase):
    def test_known_synthetic_word_error(self):
        result = stt_scores(["Há um buraco."], ["há dois buraco"])
        self.assertAlmostEqual(result["wer_corpus"], 1 / 3)

    def test_macro_differs_from_pooled(self):
        result = stt_scores(["a", "a b c"], ["x", "a b c"])
        self.assertEqual(result["wer_macro"], 0.5)
        self.assertEqual(result["wer_corpus"], 0.25)

    def test_empty_hypothesis_is_measured_failure(self):
        self.assertEqual(stt_scores(["fala de teste"], [""])["wer_corpus"], 1)

    def test_missing_data_and_empty_reference_rejected(self):
        for refs, hyps in [([], []), (["a"], []), ([""], ["a"])]:
            with self.assertRaises(ValidationError):
                stt_scores(refs, hyps)

    def test_unmeasured_is_none_not_perfect_score(self):
        self.assertIsNone(percentage([]))
        self.assertIsNone(rating_mean([]))
        self.assertEqual(percentage([True, False]), 50)

    def test_separate_rating_means_and_validation(self):
        self.assertEqual(rating_mean([1, 3, 5]), 3)
        for scores in [[0], [6], [float("nan")], [True]]:
            with self.assertRaises(ValidationError):
                rating_mean(scores)
        with self.assertRaises(ValidationError):
            percentage([None])

    def test_processing_is_not_playback_latency(self):
        ticks = iter([10.0, 11.0, 13.5, 15.0])
        tracker = LatencyTracker(clock=lambda: next(ticks))
        with tracker.measure("stt"):
            pass
        result = tracker.finish()
        self.assertEqual(result["stage_seconds"]["stt"], 2.5)
        self.assertEqual(result["processing_total_seconds"], 5)
        self.assertIsNone(result["playback_start_seconds"])
        self.assertEqual(tracker.finish(), result)

    def test_failed_stage_still_measured(self):
        tracker = LatencyTracker()
        with self.assertRaises(RuntimeError):
            with tracker.measure("llm"):
                raise RuntimeError("synthetic")
        self.assertIn("llm", tracker.stages)
        with self.assertRaises(ValidationError):
            with tracker.measure("llm"):
                pass
