"""Tema 3 - Banco de dados SQL (SQLite).

Guarda os relatos tratados e o historico de execucoes. O id do relato e chave
primaria, entao rodar o robo duas vezes com o mesmo lote nao duplica nada.
"""
import sqlite3
from pathlib import Path

import pandas as pd

ESQUEMA = """
CREATE TABLE IF NOT EXISTS relatos (
    id TEXT PRIMARY KEY,
    data TEXT NOT NULL,
    bairro TEXT NOT NULL,
    descricao TEXT NOT NULL,
    categoria TEXT NOT NULL,
    confianca REAL NOT NULL,
    prioridade TEXT NOT NULL,
    motivo_prioridade TEXT NOT NULL,
    chuva_mm REAL,
    precisa_revisao INTEGER NOT NULL,
    registrado_em TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS execucoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    inicio TEXT NOT NULL,
    fim TEXT NOT NULL,
    linhas_lidas INTEGER, validas INTEGER, invalidas INTEGER,
    novos INTEGER, ja_existentes INTEGER, para_revisao INTEGER,
    api_clima TEXT, email TEXT
);
"""

ORDEM_FILA = """
SELECT id, data, bairro, categoria, prioridade, motivo_prioridade,
       ROUND(confianca, 2) AS confianca, chuva_mm, precisa_revisao, descricao
FROM relatos
ORDER BY CASE prioridade WHEN 'alta' THEN 0 WHEN 'media' THEN 1 ELSE 2 END,
         data ASC, confianca DESC
"""


def conectar(caminho: Path) -> sqlite3.Connection:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    conexao = sqlite3.connect(caminho)
    conexao.executescript(ESQUEMA)
    return conexao


def inserir_relatos(conexao: sqlite3.Connection, relatos: pd.DataFrame, agora: str) -> tuple[int, int]:
    """Insere so o que ainda nao existe. Devolve (novos, ja_existentes)."""
    novos = 0
    with conexao:
        for _, r in relatos.iterrows():
            cursor = conexao.execute(
                "INSERT OR IGNORE INTO relatos VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (r["id"], r["data"], r["bairro"], r["descricao"], r["categoria"], float(r["confianca"]),
                 r["prioridade"], r["motivo_prioridade"],
                 None if pd.isna(r["chuva_mm"]) else float(r["chuva_mm"]),
                 int(bool(r["precisa_revisao"])), agora),
            )
            novos += cursor.rowcount
    return novos, len(relatos) - novos


def registrar_execucao(conexao: sqlite3.Connection, resumo: dict) -> None:
    with conexao:
        conexao.execute(
            "INSERT INTO execucoes (inicio, fim, linhas_lidas, validas, invalidas, novos, "
            "ja_existentes, para_revisao, api_clima, email) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (resumo["inicio"], resumo["fim"], resumo["linhas_lidas"], resumo["validas"],
             resumo["invalidas"], resumo["novos"], resumo["ja_existentes"], resumo["para_revisao"],
             resumo["api_clima"], resumo["email"]),
        )


def fila(conexao: sqlite3.Connection) -> pd.DataFrame:
    return pd.read_sql_query(ORDEM_FILA, conexao)


def contagem(conexao: sqlite3.Connection, coluna: str) -> dict[str, int]:
    if coluna not in {"categoria", "prioridade", "bairro"}:
        raise ValueError("coluna nao permitida")
    linhas = conexao.execute(
        f"SELECT {coluna}, COUNT(*) FROM relatos GROUP BY {coluna} ORDER BY COUNT(*) DESC"
    ).fetchall()
    return {nome: total for nome, total in linhas}
