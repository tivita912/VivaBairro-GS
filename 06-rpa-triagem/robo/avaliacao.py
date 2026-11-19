"""Evidencia de validacao: mede a IA do robo no conjunto de teste rotulado.

O conjunto de teste (dados/teste_rotulado.csv) tem 60 relatos sinteticos escritos a mao,
com outra redacao que nao a dos dados de treino. O resultado vai para evidencias/avaliacao.md.
"""
from pathlib import Path

import pandas as pd
from sklearn.metrics import accuracy_score, confusion_matrix, precision_recall_fscore_support

from . import classificador, config


def tabela(df: pd.DataFrame) -> list[str]:
    linhas = ["| " + " | ".join(str(c) for c in df.columns) + " |",
              "| " + " | ".join("---" for _ in df.columns) + " |"]
    for _, r in df.iterrows():
        linhas.append("| " + " | ".join(str(v).replace("|", "/") for v in r.tolist()) + " |")
    return linhas


def avaliar(destino: Path | None = None) -> dict:
    destino = destino or config.EVIDENCIAS
    destino.mkdir(parents=True, exist_ok=True)
    teste = pd.read_csv(config.TESTE, dtype=str, encoding="utf-8")
    treino = pd.read_csv(config.TREINO, dtype=str, encoding="utf-8")
    modelo = classificador.treinar()
    previsoes = classificador.classificar(modelo, teste["descricao"].tolist())
    teste["categoria_robo"] = [c for c, _ in previsoes]
    teste["revisao_humana"] = [p < config.LIMIAR_CONFIANCA for _, p in previsoes]
    teste["confianca"] = [round(p, 2) for _, p in previsoes]
    regras = [classificador.prioridade_por_regras(t) for t in teste["descricao"]]
    teste["prioridade_robo"] = [p for p, _ in regras]
    teste["motivo_prioridade"] = [m for _, m in regras]
    teste["categoria_certa"] = teste["categoria"] == teste["categoria_robo"]
    teste["prioridade_certa"] = teste["prioridade"] == teste["prioridade_robo"]
    teste.to_csv(destino / "avaliacao_predicoes.csv", index=False, encoding="utf-8")

    total = len(teste)
    acertos_cat = int(teste["categoria_certa"].sum())
    acertos_pri = int(teste["prioridade_certa"].sum())
    precisao, revocacao, _, suporte = precision_recall_fscore_support(
        teste["categoria"], teste["categoria_robo"], labels=config.CATEGORIAS, zero_division=0)
    por_classe = pd.DataFrame({
        "Categoria": config.CATEGORIAS, "Relatos": suporte,
        "Precisao": [f"{v:.2f}" for v in precisao], "Revocacao": [f"{v:.2f}" for v in revocacao],
    })
    matriz = pd.DataFrame(
        confusion_matrix(teste["categoria"], teste["categoria_robo"], labels=config.CATEGORIAS),
        columns=[f"Robo: {c}" for c in config.CATEGORIAS])
    matriz.insert(0, "Real", config.CATEGORIAS)
    matriz_pri = pd.DataFrame(
        confusion_matrix(teste["prioridade"], teste["prioridade_robo"], labels=config.PRIORIDADES),
        columns=[f"Robo: {p}" for p in config.PRIORIDADES])
    matriz_pri.insert(0, "Real", config.PRIORIDADES)

    automaticos = teste[~teste["revisao_humana"]]
    revisados = teste[teste["revisao_humana"]]
    altas = teste[teste["prioridade"] == "alta"]
    altas_achadas = int((altas["prioridade_robo"] == "alta").sum())

    def taxa(parte: pd.DataFrame) -> str:
        if parte.empty:
            return "sem relatos"
        certos = int(parte["categoria_certa"].sum())
        return f"{certos} de {len(parte)} ({100 * certos / len(parte):.1f}%)"

    erros_cat = teste[~teste["categoria_certa"]][
        ["descricao", "categoria", "categoria_robo", "confianca", "revisao_humana"]]
    erros_pri = teste[~teste["prioridade_certa"]][
        ["descricao", "prioridade", "prioridade_robo", "motivo_prioridade"]]

    linhas = [
        "# Avaliacao da IA do robo no conjunto de teste rotulado", "",
        f"- Treino: {len(treino)} relatos sinteticos gerados por combinacao de trechos (scripts/gerar_treino.py).",
        f"- Teste: {total} relatos sinteticos escritos a mao, 10 por categoria, com categoria e prioridade rotuladas.",
        "- Nenhum relato de teste foi usado no treino. Nenhum dado real de cidadao foi usado.", "",
        "## Categoria (NLP: TF-IDF + Regressao Logistica)", "",
        f"Acertos: **{acertos_cat} de {total} ({100 * accuracy_score(teste['categoria'], teste['categoria_robo']):.1f}%)**", "",
        *tabela(por_classe), "", "Matriz de confusao (linhas = categoria real):", "", *tabela(matriz), "",
        f"## Revisao humana (confianca abaixo de {config.LIMIAR_CONFIANCA})", "",
        f"- Relatos aceitos automaticamente: {len(automaticos)}. Categoria certa em {taxa(automaticos)}.",
        f"- Relatos enviados para revisao humana: {len(revisados)}. Categoria certa em {taxa(revisados)}.",
        f"- Erros de categoria que a revisao humana pega: {int((~revisados['categoria_certa']).sum())} de {total - acertos_cat}.", "",
        "## Prioridade (regras)", "",
        f"Acertos: **{acertos_pri} de {total} ({100 * acertos_pri / total:.1f}%)**", "",
        f"Relatos de prioridade alta encontrados pelo robo: {altas_achadas} de {len(altas)}.", "",
        "Matriz de confusao (linhas = prioridade real):", "", *tabela(matriz_pri), "",
        "## Erros de categoria", "", *(tabela(erros_cat) if not erros_cat.empty else ["Nenhum."]), "",
        "## Erros de prioridade", "", *(tabela(erros_pri) if not erros_pri.empty else ["Nenhum."]), "",
    ]
    (destino / "avaliacao.md").write_text("\n".join(linhas), encoding="utf-8")
    return {
        "total": total, "acertos_categoria": acertos_cat, "acertos_prioridade": acertos_pri,
        "aceitos": len(automaticos), "aceitos_certos": int(automaticos["categoria_certa"].sum()),
        "revisao": len(revisados), "altas": len(altas), "altas_achadas": altas_achadas,
    }
