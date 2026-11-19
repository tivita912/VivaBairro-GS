"""Instrumentos de medição. Ausência de evidência é None, nunca zero inventado."""
from contextlib import contextmanager
from dataclasses import dataclass, field
import math
import re
from statistics import mean
import time
from typing import Callable, Iterator, Sequence
import unicodedata

from .errors import ValidationError

STAGES = frozenset({"input", "stt", "context", "llm", "speech_text", "tts"})
NORMALIZATION = "pt_v1: NFC, minúsculas, pontuação por espaço, espaços colapsados; acentos e números preservados"


@dataclass
class LatencyTracker:
    """Relógio monotônico do servidor. Não mede início de reprodução no navegador."""
    clock: Callable[[], float] = time.perf_counter
    stages: dict[str, float] = field(default_factory=dict, init=False)
    _started: float = field(init=False, repr=False)
    _total: float | None = field(default=None, init=False)

    def __post_init__(self) -> None:
        self._started = self.clock()

    @contextmanager
    def measure(self, stage: str) -> Iterator[None]:
        if stage not in STAGES or stage in self.stages or self._total is not None:
            raise ValidationError("Etapa de medição inválida, repetida ou já encerrada.")
        started = self.clock()
        try:
            yield
        finally:
            self.stages[stage] = self.clock() - started

    def finish(self) -> dict:
        if self._total is None:
            self._total = self.clock() - self._started
        return {
            "stage_seconds": dict(self.stages),
            "processing_total_seconds": self._total,
            "playback_start_seconds": None,
            "playback_measurement": "not_instrumented",
            "processing_boundary": "handler_start_to_audio_ready",
        }


def normalize_reference(text: str) -> str:
    text = unicodedata.normalize("NFC", text).lower()
    text = "".join(" " if unicodedata.category(c).startswith("P") else c for c in text)
    return re.sub(r"\s+", " ", text).strip()


def stt_scores(references: Sequence[str], hypotheses: Sequence[str]) -> dict:
    if not references or len(references) != len(hypotheses):
        raise ValidationError("Forneça pares de referência e transcrição, em quantidades iguais.")
    from jiwer import process_words

    refs = [normalize_reference(s) for s in references]
    hyps = [normalize_reference(s) for s in hypotheses]
    if any(not s for s in refs):
        raise ValidationError("Referência vazia: avalie silêncio separadamente do corpus WER.")
    def counts(result):
        return {
            "substitutions": result.substitutions,
            "deletions": result.deletions,
            "insertions": result.insertions,
            "reference_words": result.hits + result.substitutions + result.deletions,
        }

    pairs = [process_words(r, h) for r, h in zip(refs, hyps)]
    individual = [pair.wer for pair in pairs]
    corpus = process_words(refs, hyps)
    return {"samples": len(refs), "wer_per_sample": individual,
            "wer_macro": mean(individual), "wer_corpus": corpus.wer,
            "word_errors": counts(corpus), "word_errors_per_sample": [counts(pair) for pair in pairs],
            "normalization": NORMALIZATION}


def percentage(values: Sequence[bool]) -> float | None:
    if any(type(value) is not bool for value in values):
        raise ValidationError("Avaliações devem ser booleanas; exclua as ainda não avaliadas.")
    return 100 * sum(values) / len(values) if values else None


def rating_mean(values: Sequence[float]) -> float | None:
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or
           not math.isfinite(v) or not 1 <= v <= 5 for v in values):
        raise ValidationError("As notas devem estar entre 1 e 5.")
    return mean(values) if values else None
