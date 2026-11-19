"""Defesas basicas: nenhuma credencial persistida; documentacao e input sao nao confiaveis."""
from __future__ import annotations
import re
from .chunking import fold

DIRECT_INJECTION = [
    re.compile(r'(ignore|desconsidere|desobedeca|substitua).{0,100}(instrucoes|regras|prompt|sistema)', re.I),
    re.compile(r'(revele|mostre|exiba|imprima|retorne|vaze).{0,90}(prompt|system|segredo|token|chave|api.key|credencial)', re.I),
    re.compile(r'(password|senha secreta|token secreto|api.key).{0,50}(mostre|revele|imprima)', re.I),
]
SECRET_REGEX = re.compile(r'\b\d{3}[. ]?\d{3}[. ]?\d{3}[- ]?\d{2}\b')
PRIVATE_MARKERS = re.compile(r'(?i)\b[\w.+-]+@[\w.-]+\.[a-z]{2,}\b|\b(?:api[_ -]?key|senha|token)\s*=\s*\S+')
SUSPICIOUS_EVIDENCE = re.compile(r'(ignore|desconsidere|obede[cç]a).{0,100}(instru[cç][oõ]es|prompt|sistema)|<\|?system\|?>|BEGIN SYSTEM PROMPT|API_KEY\s*=', re.I)


def assess_query(query: str) -> str | None:
    # Nao imprimir ou registrar o conteudo da consulta.
    norm = fold(' '.join(query.split()))
    if any(p.search(norm) for p in DIRECT_INJECTION):
        return 'Não posso revelar instruções internas, credenciais ou chaves. Posso orientar sobre os serviços públicos documentados.'
    if contains_sensitive(query):
        return 'Não envie CPF ou outros dados pessoais aqui. Para sua segurança, refaça a pergunta sem dados identificáveis.'
    if len(query.strip()) < 8:
        return 'Sua pergunta está muito curta. Informe qual serviço público digital deseja consultar, sem dados pessoais.'
    return None


def contains_sensitive(text: str) -> bool:
    return bool(SECRET_REGEX.search(text) or PRIVATE_MARKERS.search(text))


def sanitize_evidence(chunks: list[dict]) -> tuple[list[dict], int]:
    clean, removed = [], 0
    for chunk in chunks:
        # Linhas do corpus nunca se tornam instrucoes para o modelo.
        fields = ' '.join(chunk.get(key, '') for key in ('title', 'heading', 'text'))
        if SUSPICIOUS_EVIDENCE.search(' '.join(fields.split())) or contains_sensitive(fields):
            removed += 1
            continue
        clean.append(chunk)
    return clean, removed
