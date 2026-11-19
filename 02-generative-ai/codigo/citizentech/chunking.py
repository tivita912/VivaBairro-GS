"""Chunking reproduzivel, com preservacao de metadados da fonte."""
from __future__ import annotations
import json
import re
import unicodedata
from datetime import date
from urllib.parse import urlsplit
from pathlib import Path

STOPWORDS = set("a o os as um uma uns umas e ou de do da dos das no na nos nas em para por com que qual quais como onde quanto quando porque por que sera ser sao esta estou eu voce vc meu minha seu sua tem ter tenho posso pode preciso fazer quero sobre mais menos sem isso isto ja ao aos pelo pela pelos pelas cada se foi a minha meu mesmo muita muito este essa esse esses essas ainda".split())


SYNONYMS = {
    'passeio': ['calcada'], 'luminaria': ['lampada'], 'lampada': ['luminaria'],
    'bueiro': ['drenagem', 'boca', 'lobo'], 'cratera': ['buraco', 'asfalto'],
    'entulho': ['residuos', 'descarte'], 'cadeirante': ['acessibilidade', 'calcada'],
}
def fold(text: str) -> str:
    return unicodedata.normalize('NFKD', text.lower()).encode('ascii', 'ignore').decode('ascii')


def tokenize(text: str, expand: bool=False) -> list[str]:
    words = [w for w in re.findall(r'[a-z0-9]+', fold(text)) if len(w) > 1 and w not in STOPWORDS]
    if expand:
        words += [v for w in words for v in SYNONYMS.get(w, [])]
    return words


def load_corpus(path: str | Path) -> list[dict]:
    with open(path, encoding='utf-8') as file:
        docs = json.load(file)
    if not isinstance(docs, list) or not docs:
        raise ValueError('Corpus vazio ou inválido')
    ids, urls = set(), set()
    for doc in docs:
        required = ('id', 'title', 'url', 'consulted_on', 'origin', 'sections')
        if any(not doc.get(key) for key in required):
            raise ValueError('Fonte sem metadados obrigatorios: ' + str(doc.get('id')))
        endpoint = urlsplit(doc['url'])
        municipal = {'prefeitura.sp.gov.br', 'sp156.prefeitura.sp.gov.br'}
        if endpoint.scheme != 'https' or endpoint.netloc not in municipal:
            raise ValueError('Fonte fora do dominio permitido: ' + doc['url'])
        if not re.fullmatch(r'F[0-9]{2}', doc['id']) or doc['id'] in ids or doc['url'] in urls:
            raise ValueError('Fonte duplicada ou com ID inválido: ' + doc['id'])
        date.fromisoformat(doc['consulted_on'])
        if any(not section.get('heading') or not section.get('text', '').strip() for section in doc['sections']):
            raise ValueError('Seção sem título ou conteúdo: ' + doc['id'])
        ids.add(doc['id'])
        urls.add(doc['url'])
    return docs


def windows(words: list[str], size: int, overlap: int) -> list[str]:
    if size < 15 or overlap < 0 or overlap >= size:
        raise ValueError('Configuracao invalida de chunking')
    if not words:
        return []
    result = []
    stride = size - overlap
    for start in range(0, len(words), stride):
        part = words[start:start+size]
        if not part:
            break
        result.append(' '.join(part))
        if start + size >= len(words):
            break
    return result


def chunk_corpus(docs: list[dict], strategy: str='structure', size: int=65, overlap: int=10) -> list[dict]:
    """structure: nao mistura secoes; fixed: janelas fixas por documento."""
    if strategy not in ('structure', 'fixed'):
        raise ValueError('Estrategia desconhecida')
    chunks = []
    for doc in docs:
        units = [(sec['heading'], sec['text']) for sec in doc['sections']] if strategy == 'structure' else [('Documento completo', ' '.join(f"{s['heading']}. {s['text']}" for s in doc['sections']))]
        for section_index, (heading, content) in enumerate(units):
            for part_index, part in enumerate(windows(content.split(), size, overlap)):
                chunks.append({'id': f"{doc['id']}-S{section_index+1:02d}-C{part_index+1:02d}",
                               'doc_id': doc['id'], 'title': doc['title'], 'heading': heading,
                               'url': doc['url'], 'origin': doc['origin'], 'consulted_on': doc['consulted_on'],
                               'last_modified': doc.get('last_modified'), 'domain': doc.get('domain'),
                               'municipality': doc.get('municipality'), 'limitations': doc.get('limitations'),
                               'text': part, 'word_count': len(part.split()),
                               'word_start': part_index * (size - overlap),
                               'overlap_words': overlap if part_index else 0})
    return chunks
