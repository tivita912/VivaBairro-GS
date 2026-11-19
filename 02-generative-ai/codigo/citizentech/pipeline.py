"""Configuração compartilhada do corpus, índice e provedor."""
from __future__ import annotations

import os
from pathlib import Path

from .chunking import chunk_corpus, load_corpus
from .generator import DEFAULT_MODELS
from .retrieval import Retriever

ROOT = Path(__file__).resolve().parents[1]


class RAGIndex:
    def __init__(self, corpus_path=None, strategy='structure', chunk_size=65, overlap=10,
                 retriever='hybrid', top_k=4, provider=None, model=None):
        self.docs = load_corpus(corpus_path or ROOT/'corpus/fontes.json')
        self.chunks = chunk_corpus(self.docs,strategy,chunk_size,overlap)
        self.retriever = Retriever(self.chunks,retriever)
        self.top_k = top_k
        self.provider = provider or os.getenv('GENERATOR_PROVIDER','baseline')
        if self.provider not in {'baseline',*DEFAULT_MODELS}:
            raise ValueError('GENERATOR_PROVIDER inválido.')
        self.model = None if self.provider == 'baseline' else (
            model or os.getenv('GENERATOR_MODEL') or DEFAULT_MODELS[self.provider]
        )

