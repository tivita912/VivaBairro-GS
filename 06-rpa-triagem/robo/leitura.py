"""Tema 1 - Tratamento de arquivos e dados com Pandas.

Le os lotes de relatos em CSV, rejeita arquivo quebrado sem parar o robo,
valida linha por linha, mascara dados pessoais e gera um id estavel por relato.
"""
import hashlib
import re
import unicodedata
from datetime import datetime
from pathlib import Path

import pandas as pd

from . import config
from .logs import obter

EXTENSOES = {".csv"}

PADROES_PESSOAIS = [
    (re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b"), "[CPF REMOVIDO]"),
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"), "[E-MAIL REMOVIDO]"),
    (re.compile(r"(?:\+?55\s?)?\(?\d{2}\)?\s?9?\d{4}[-\s]?\d{4}\b"), "[TELEFONE REMOVIDO]"),
]


class ArquivoInvalido(Exception):
    """O arquivo existe, mas nao da para usar (corrompido, vazio ou sem as colunas)."""


def sem_acento(texto: str) -> str:
    normal = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in normal if not unicodedata.combining(c)).casefold().strip()


def listar_arquivos(pasta: Path) -> list[Path]:
    """Devolve os arquivos de entrada. Pasta ausente ou vazia devolve lista vazia."""
    if not pasta.exists() or not pasta.is_dir():
        return []
    return sorted(p for p in pasta.iterdir() if p.is_file() and p.suffix.lower() in EXTENSOES)


def ler_arquivo(caminho: Path) -> pd.DataFrame:
    try:
        df = pd.read_csv(caminho, dtype=str, encoding="utf-8", keep_default_na=False)
    except Exception as erro:  # qualquer falha de leitura vira um erro tratado
        raise ArquivoInvalido(f"nao foi possivel ler ({type(erro).__name__})") from erro
    df.columns = [str(c).strip().lower() for c in df.columns]
    faltando = [c for c in config.COLUNAS_OBRIGATORIAS if c not in df.columns]
    if faltando:
        raise ArquivoInvalido(f"colunas ausentes: {', '.join(faltando)}")
    if df.empty:
        raise ArquivoInvalido("arquivo sem linhas")
    df = df[config.COLUNAS_OBRIGATORIAS].fillna("").astype(str)
    for coluna in config.COLUNAS_OBRIGATORIAS:
        df[coluna] = df[coluna].str.strip()
    df["arquivo"] = caminho.name
    df["linha"] = range(2, len(df) + 2)  # linha 1 e o cabecalho
    return df


def mascarar_dados_pessoais(texto: str) -> tuple[str, bool]:
    """Troca CPF, e-mail e telefone por um marcador antes de guardar o relato."""
    limpo = texto
    for padrao, marcador in PADROES_PESSOAIS:
        limpo = padrao.sub(marcador, limpo)
    return limpo, limpo != texto


def motivo_invalido(linha: pd.Series) -> str:
    """Devolve o motivo da rejeicao, ou texto vazio se a linha for valida."""
    try:
        datetime.strptime(linha["data"], "%Y-%m-%d")
    except ValueError:
        return "data ausente ou fora do formato AAAA-MM-DD"
    if not (config.BAIRRO_MIN <= len(linha["bairro"]) <= config.BAIRRO_MAX):
        return "bairro ausente ou com tamanho invalido"
    tamanho = len(linha["descricao"])
    if tamanho < config.DESCRICAO_MIN:
        return f"descricao com menos de {config.DESCRICAO_MIN} caracteres"
    if tamanho > config.DESCRICAO_MAX:
        return f"descricao com mais de {config.DESCRICAO_MAX} caracteres"
    if any(ord(c) < 32 and c not in "\n\t" for c in linha["bairro"] + linha["descricao"]):
        return "texto com caracteres de controle"
    return ""


def gerar_id(data: str, bairro: str, descricao: str) -> str:
    base = f"{data}|{sem_acento(bairro)}|{sem_acento(descricao)}"
    return hashlib.sha256(base.encode("utf-8")).hexdigest()[:16]


def validar(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Separa linhas validas das invalidas. As invalidas saem com o motivo."""
    df = df.copy()
    df["motivo"] = [motivo_invalido(linha) for _, linha in df.iterrows()]
    invalidos = df[df["motivo"] != ""].copy()
    validos = df[df["motivo"] == ""].drop(columns=["motivo"]).copy()
    if validos.empty:
        validos["dado_pessoal_mascarado"] = pd.Series(dtype=bool)
        validos["id"] = pd.Series(dtype=str)
        return validos, invalidos
    mascarados = validos["descricao"].map(mascarar_dados_pessoais)
    validos["descricao"] = [texto for texto, _ in mascarados]
    validos["dado_pessoal_mascarado"] = [mudou for _, mudou in mascarados]
    validos["id"] = [
        gerar_id(d, b, t) for d, b, t in zip(validos["data"], validos["bairro"], validos["descricao"])
    ]
    return validos, invalidos


def carregar_lotes(pasta: Path) -> tuple[pd.DataFrame, pd.DataFrame, list[dict]]:
    """Le todos os arquivos da pasta. Um arquivo ruim e registrado e o robo segue para o proximo."""
    log = obter()
    lidos, rejeitados = [], []
    for caminho in listar_arquivos(pasta):
        try:
            df = ler_arquivo(caminho)
        except ArquivoInvalido as erro:
            log.error("Arquivo rejeitado: %s (%s). O robo segue para o proximo.", caminho.name, erro)
            rejeitados.append({"arquivo": caminho.name, "motivo": str(erro)})
            continue
        log.info("Arquivo lido: %s (%d linhas)", caminho.name, len(df))
        lidos.append(df)
    if not lidos:
        vazio = pd.DataFrame(columns=config.COLUNAS_OBRIGATORIAS + ["arquivo", "linha"])
        validos, invalidos = validar(vazio)
        return validos, invalidos, rejeitados
    validos, invalidos = validar(pd.concat(lidos, ignore_index=True))
    repetidos = int(validos.duplicated(subset="id").sum())
    if repetidos:
        log.warning("%d relato(s) repetido(s) dentro do lote foram ignorados.", repetidos)
        validos = validos.drop_duplicates(subset="id").copy()
    validos.attrs["repetidos_no_lote"] = repetidos
    for _, linha in invalidos.iterrows():
        log.warning("Linha invalida: %s linha %s (%s). Vai para revisao humana.",
                    linha["arquivo"], linha["linha"], linha["motivo"])
    return validos, invalidos, rejeitados
