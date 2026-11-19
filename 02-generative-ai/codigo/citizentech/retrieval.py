"""BM25 ou hibrido BM25 + LSA (embedding denso local)."""
from __future__ import annotations
from collections import Counter, defaultdict
import math

import numpy as np
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize
from .chunking import tokenize


MIN_BM25 = 1.6
MIN_DENSE = 0.35
LEXICAL_WEIGHT = 0.78
PER_DOC = 2


class Retriever:
    def __init__(self, chunks: list[dict], mode: str='hybrid'):
        if mode not in ('bm25', 'dense', 'hybrid'):
            raise ValueError('Retriever desconhecido')
        if not chunks:
            raise ValueError('Nenhum chunk')
        self.chunks, self.mode = chunks, mode
        self.tokens = [tokenize(c['title'] + ' ' + c['heading'] + ' ' + c['text']) for c in chunks]
        self.tf = [Counter(x) for x in self.tokens]
        self.avglen = sum(map(len, self.tokens))/len(self.tokens)
        self.df = Counter(word for tokens in self.tokens for word in set(tokens))
        # LSA produz vetores densos treinados apenas no corpus atual; NAO e embedding de transformer.
        self.vectorizer, self.svd, self.dense = None, None, None
        if mode != 'bm25' and len(chunks) > 2:
            self.vectorizer = TfidfVectorizer(strip_accents='unicode', lowercase=True,
                                               analyzer='char_wb', ngram_range=(3,5), min_df=1, sublinear_tf=True)
            matrix = self.vectorizer.fit_transform(c['title'] + ' ' + c['heading'] + ' ' + c['text'] for c in chunks)
            components = min(24, matrix.shape[0]-1, matrix.shape[1]-1)
            if components >= 2:
                self.svd = TruncatedSVD(n_components=components, n_iter=7, random_state=42)
                self.dense = normalize(self.svd.fit_transform(matrix))

    def score_bm25(self, query: str) -> np.ndarray:
        query_tokens = sorted(set(tokenize(query, expand=True)))
        n = len(self.chunks)
        scores = np.zeros(n, dtype=float)
        k1, b = 1.5, 0.75
        for word in query_tokens:
            df = self.df.get(word, 0)
            if not df:
                continue
            idf = math.log(1 + (n-df+0.5)/(df+0.5))
            for i, tf in enumerate(self.tf):
                f = tf.get(word, 0)
                if f:
                    scores[i] += idf * f*(k1+1)/(f+k1*(1-b+b*len(self.tokens[i])/self.avglen))
        return scores

    def score_dense(self, query: str) -> np.ndarray:
        if self.dense is None:
            return np.zeros(len(self.chunks))
        q = self.svd.transform(self.vectorizer.transform([query]))
        q = normalize(q)
        return (self.dense @ q[0]).clip(-1, 1)

    def retrieve(self, query: str, top_k: int = 4, domain: str | None = None,
                 min_bm25: float = MIN_BM25, doc_id: str | None = None) -> list[dict]:
        if top_k < 1:
            return []
        lexical = self.score_bm25(query)
        dense = self.score_dense(query)
        relevance, threshold = (dense, MIN_DENSE) if self.mode == 'dense' else (lexical, min_bm25)
        candidates = [
            i for i, chunk in enumerate(self.chunks)
            if (not domain or chunk['domain'] == domain)
            and (not doc_id or chunk['doc_id'] == doc_id)
            and relevance[i] >= threshold
        ]
        if not candidates:
            return []
        max_lex = max(lexical[i] for i in candidates) or 1
        def score(i: int) -> float:
            normalized_bm = lexical[i] / max_lex
            if self.mode == 'dense':
                return float(dense[i])
            if self.mode == 'bm25':
                return float(normalized_bm)
            return float(LEXICAL_WEIGHT * normalized_bm + (1 - LEXICAL_WEIGHT) * max(dense[i], 0))
        ranked = sorted(candidates, key=lambda i: (-score(i), self.chunks[i]['id']))
        per_doc = defaultdict(int)
        result = []
        for idx in ranked:
            chunk = self.chunks[idx]
            if per_doc[chunk['doc_id']] >= PER_DOC:
                continue
            per_doc[chunk['doc_id']] += 1
            result.append({'rank':len(result)+1,'score':round(score(idx),4),
                           'bm25':round(float(lexical[idx]),4), 'dense':round(float(dense[idx]),4),
                           **chunk})
            if len(result)>=top_k:
                break
        return result
