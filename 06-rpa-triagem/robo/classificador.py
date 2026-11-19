"""IA do robo: NLP classico para a categoria e regras para a prioridade.

Categoria: TF-IDF + Regressao Logistica (scikit-learn), treinado em relatos sinteticos.
Prioridade: regras escritas pelo grupo, seguindo o criterio descrito no README.
Nao usa LLM, entao roda offline, de graca e sem enviar texto do cidadao a nenhuma API.
"""
from pathlib import Path

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from . import config
from .leitura import sem_acento

# Risco imediato a integridade fisica ou bloqueio de passagem de quem tem mobilidade reduzida.
TERMOS_ALTA = [
    "ferid", "machuc", "acident", "caiu", "cair", "queda", "tropec", "risco", "perig",
    "cadeirante", "cadeira de rodas", "nao consegue passar", "impede a passagem",
    "fio exposto", "fio solto", "fio desencapado", "choque", "alagad", "enchente",
    "transbord", "invadi", "desab", "cratera", "afund", "assalt", "crianca", "idos",
]
# Incomodo sem risco: problema pequeno, estetico ou sem urgencia.
TERMOS_BAIXA = [
    "pequen", "estetic", "sem urgencia", "nao e urgente", "nao atrapalha", "quando puderem",
    "apagada pelo tempo", "desbotad", "pichac", "pintura", "feio", "so um pouco",
]


def treinar(caminho: Path | None = None) -> Pipeline:
    dados = pd.read_csv(caminho or config.TREINO, dtype=str, encoding="utf-8")
    modelo = Pipeline([
        ("tfidf", TfidfVectorizer(preprocessor=sem_acento, ngram_range=(1, 2), sublinear_tf=True)),
        ("clf", LogisticRegression(max_iter=1000, C=10.0)),
    ])
    modelo.fit(dados["descricao"], dados["categoria"])
    return modelo


def classificar(modelo: Pipeline, textos: list[str]) -> list[tuple[str, float]]:
    """Devolve (categoria, confianca) para cada texto. Confianca = maior probabilidade."""
    if not textos:
        return []
    probabilidades = modelo.predict_proba(textos)
    classes = modelo.classes_
    return [(str(classes[p.argmax()]), float(p.max())) for p in probabilidades]


def prioridade_por_regras(texto: str) -> tuple[str, str]:
    """Devolve (prioridade, motivo). O motivo fica guardado para a revisao humana conferir."""
    limpo = sem_acento(texto)
    for termo in TERMOS_ALTA:
        if termo in limpo:
            return "alta", f"termo de risco: {termo}"
    for termo in TERMOS_BAIXA:
        if termo in limpo:
            return "baixa", f"termo de baixa urgencia: {termo}"
    return "media", "sem termo de risco nem de baixa urgencia"


def subir_prioridade(prioridade: str) -> str:
    return {"baixa": "media", "media": "alta", "alta": "alta"}[prioridade]
