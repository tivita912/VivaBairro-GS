"""Fluxo do robo, de ponta a ponta:

arquivos de entrada -> validacao (Pandas) -> IA (categoria e prioridade) -> API de clima
-> banco SQLite -> fila priorizada + lista de revisao humana -> e-mail -> relatorio.
"""
import json
import time
from datetime import datetime
from pathlib import Path

import pandas as pd

from . import banco, classificador, clima, config, email_resumo, leitura, logs

COLUNAS_REVISAO = ["origem", "arquivo", "linha", "data", "bairro", "descricao", "motivo",
                   "categoria_sugerida", "prioridade_sugerida", "confianca"]


def agora() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def resumo_vazio(inicio: str) -> dict:
    return {
        "status": "concluido", "inicio": inicio, "fim": inicio, "duracao_s": 0.0,
        "arquivos_lidos": 0, "arquivos_rejeitados": [], "linhas_lidas": 0, "validas": 0,
        "invalidas": 0, "repetidos_no_lote": 0, "novos": 0, "ja_existentes": 0,
        "para_revisao": 0, "dados_pessoais_mascarados": 0, "api_clima": "nao consultada",
        "prioridades_alteradas_pela_chuva": 0, "email": "nao gerado",
    }


def tratar_relatos(validos: pd.DataFrame, opcoes_clima: dict, resumo: dict) -> pd.DataFrame:
    """Aplica a IA e o dado de chuva aos relatos validos."""
    log = logs.obter()
    modelo = classificador.treinar()
    previsoes = classificador.classificar(modelo, validos["descricao"].tolist())
    validos["categoria"] = [categoria for categoria, _ in previsoes]
    validos["confianca"] = [confianca for _, confianca in previsoes]
    regras = [classificador.prioridade_por_regras(texto) for texto in validos["descricao"]]
    validos["prioridade"] = [prioridade for prioridade, _ in regras]
    validos["motivo_prioridade"] = [motivo for _, motivo in regras]
    log.info("IA aplicada a %d relato(s): categoria por NLP, prioridade por regras.", len(validos))

    chuvas = clima.chuva_por_bairro(validos["bairro"].tolist(), **opcoes_clima)
    consultas_ok = sum(1 for c in chuvas.values() if c.ok)
    if consultas_ok == len(chuvas):
        resumo["api_clima"] = f"ok ({len(chuvas)} bairro(s) consultado(s))"
    elif consultas_ok:
        resumo["api_clima"] = f"parcial ({consultas_ok} de {len(chuvas)} bairro(s))"
    else:
        resumo["api_clima"] = "indisponivel (robo seguiu sem o dado de chuva)"
    validos["chuva_mm"] = [chuvas[b].mm if chuvas[b].ok else None for b in validos["bairro"]]

    alteradas = 0
    for indice, r in validos.iterrows():
        chuva = r["chuva_mm"]
        if (r["categoria"] == "Drenagem e alagamentos" and pd.notna(chuva)
                and chuva >= config.CHUVA_FORTE_MM and r["prioridade"] != "alta"):
            validos.at[indice, "prioridade"] = classificador.subir_prioridade(r["prioridade"])
            validos.at[indice, "motivo_prioridade"] = (
                f"{r['motivo_prioridade']}; chuva prevista de {chuva:.1f} mm")
            alteradas += 1
    resumo["prioridades_alteradas_pela_chuva"] = alteradas
    validos["precisa_revisao"] = validos["confianca"] < config.LIMIAR_CONFIANCA
    return validos


def montar_revisao(validos: pd.DataFrame, invalidos: pd.DataFrame) -> pd.DataFrame:
    """Tudo o que o robo nao resolve sozinho vai para uma pessoa conferir."""
    partes = []
    if not invalidos.empty:
        parte = invalidos[["arquivo", "linha", "data", "bairro", "descricao", "motivo"]].copy()
        parte.insert(0, "origem", "linha invalida")
        partes.append(parte)
    if not validos.empty and validos["precisa_revisao"].any():
        duvidosos = validos[validos["precisa_revisao"]]
        parte = duvidosos[["arquivo", "linha", "data", "bairro", "descricao"]].copy()
        parte.insert(0, "origem", "baixa confianca da IA")
        parte["motivo"] = "confianca abaixo de " + str(config.LIMIAR_CONFIANCA)
        parte["categoria_sugerida"] = duvidosos["categoria"]
        parte["prioridade_sugerida"] = duvidosos["prioridade"]
        parte["confianca"] = duvidosos["confianca"].round(2)
        partes.append(parte)
    if not partes:
        return pd.DataFrame(columns=COLUNAS_REVISAO)
    return pd.concat(partes, ignore_index=True).reindex(columns=COLUNAS_REVISAO)


def escrever_relatorio(resumo: dict, saida: Path) -> None:
    saida.mkdir(parents=True, exist_ok=True)
    (saida / "relatorio_execucao.json").write_text(
        json.dumps(resumo, ensure_ascii=False, indent=2), encoding="utf-8")
    rejeitados = "; ".join(f"{r['arquivo']} ({r['motivo']})" for r in resumo["arquivos_rejeitados"]) or "nenhum"
    linhas = [
        "# Relatorio de execucao do robo VivaBairro", "",
        "| Item | Valor |", "| --- | --- |",
        f"| Status | {resumo['status']} |",
        f"| Inicio | {resumo['inicio']} |",
        f"| Fim | {resumo['fim']} |",
        f"| Duracao (s) | {resumo['duracao_s']} |",
        f"| Arquivos lidos | {resumo['arquivos_lidos']} |",
        f"| Arquivos rejeitados | {rejeitados} |",
        f"| Linhas lidas | {resumo['linhas_lidas']} |",
        f"| Linhas validas | {resumo['validas']} |",
        f"| Linhas invalidas (revisao humana) | {resumo['invalidas']} |",
        f"| Repetidas dentro do lote | {resumo['repetidos_no_lote']} |",
        f"| Relatos novos no banco | {resumo['novos']} |",
        f"| Relatos que ja estavam no banco | {resumo['ja_existentes']} |",
        f"| Relatos com baixa confianca (revisao humana) | {resumo['para_revisao']} |",
        f"| Relatos com dado pessoal mascarado | {resumo['dados_pessoais_mascarados']} |",
        f"| API de clima | {resumo['api_clima']} |",
        f"| Prioridades alteradas pela chuva | {resumo['prioridades_alteradas_pela_chuva']} |",
        f"| E-mail | {resumo['email']} |", "",
    ]
    (saida / "relatorio_execucao.md").write_text("\n".join(linhas), encoding="utf-8")


def executar(entrada: Path | None = None, saida: Path | None = None,
             opcoes_clima: dict | None = None) -> dict:
    entrada = entrada or config.ENTRADA
    saida = saida or config.SAIDA
    opcoes_clima = opcoes_clima or {}
    saida.mkdir(parents=True, exist_ok=True)
    log = logs.configurar(saida / "robo.log")
    cronometro = time.perf_counter()
    resumo = resumo_vazio(agora())
    log.info("Inicio. Entrada: %s", config.relativo(entrada))
    try:
        arquivos = leitura.listar_arquivos(entrada)
        if not arquivos:
            log.error("Nenhum arquivo .csv em %s. Caminho seguro: nada e alterado e o robo "
                      "encerra com relatorio.", config.relativo(entrada))
            resumo["status"] = "sem arquivo de entrada"
        else:
            validos, invalidos, rejeitados = leitura.carregar_lotes(entrada)
            repetidos = int(validos.attrs.get("repetidos_no_lote", 0))
            resumo.update({
                "arquivos_lidos": len(arquivos) - len(rejeitados),
                "arquivos_rejeitados": rejeitados,
                "linhas_lidas": len(validos) + len(invalidos) + repetidos,
                "validas": len(validos), "invalidas": len(invalidos),
                "repetidos_no_lote": repetidos,
            })
            if not validos.empty:
                resumo["dados_pessoais_mascarados"] = int(validos["dado_pessoal_mascarado"].sum())
                validos = tratar_relatos(validos, opcoes_clima, resumo)
                resumo["para_revisao"] = int(validos["precisa_revisao"].sum())
            conexao = banco.conectar(saida / "vivabairro.db")
            try:
                if not validos.empty:
                    novos, existentes = banco.inserir_relatos(conexao, validos, agora())
                    resumo["novos"], resumo["ja_existentes"] = novos, existentes
                    log.info("Banco: %d relato(s) novo(s), %d ja existente(s).", novos, existentes)
                fila = banco.fila(conexao)
                fila.to_csv(saida / "fila_priorizada.csv", index=False, encoding="utf-8")
                revisao = montar_revisao(validos, invalidos)
                revisao.to_csv(saida / "revisao_humana.csv", index=False, encoding="utf-8")
                log.info("Fila priorizada: %d relato(s). Revisao humana: %d item(ns).",
                         len(fila), len(revisao))
                resumo["fim"] = agora()
                mensagem = email_resumo.montar(
                    fila, banco.contagem(conexao, "categoria"),
                    banco.contagem(conexao, "prioridade"), resumo)
                resumo["email"] = email_resumo.enviar_ou_salvar(mensagem, saida / "emails")
                resumo["fim"] = agora()
                resumo["duracao_s"] = round(time.perf_counter() - cronometro, 2)
                banco.registrar_execucao(conexao, resumo)
            finally:
                conexao.close()
            if rejeitados and not resumo["arquivos_lidos"]:
                resumo["status"] = "nenhum arquivo aproveitavel"
    except Exception:  # falha nao prevista: registra e encerra com relatorio
        log.exception("Falha nao prevista. O robo encerra com relatorio.")
        resumo["status"] = "falha nao prevista (ver log)"
    resumo["fim"] = agora()
    resumo["duracao_s"] = round(time.perf_counter() - cronometro, 2)
    escrever_relatorio(resumo, saida)
    log.info("Fim. Status: %s. Relatorio em %s", resumo["status"],
             config.relativo(saida / "relatorio_execucao.md"))
    return resumo
