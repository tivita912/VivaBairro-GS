"""Tema 4 - E-mail automatizado.

Monta o resumo do dia para a equipe de zeladoria. Com SMTP configurado no .env,
envia. Sem SMTP, ou se o envio falhar, salva o e-mail em arquivo .eml (caminho seguro).
"""
import smtplib
import ssl
from email.message import EmailMessage
from pathlib import Path

import pandas as pd

from . import config
from .logs import obter


def montar(fila: pd.DataFrame, por_categoria: dict, por_prioridade: dict, resumo: dict) -> EmailMessage:
    cfg = config.config_email()
    linhas = [
        "Resumo automatico do VivaBairro (prototipo academico, dados sinteticos).",
        "",
        f"Relatos na base: {len(fila)}",
        f"Novos nesta execucao: {resumo['novos']}",
        f"Aguardando revisao humana: {resumo['para_revisao']} relato(s) e {resumo['invalidas']} linha(s) invalida(s)",
        f"API de clima: {resumo['api_clima']}",
        "",
        "Por prioridade:",
    ]
    linhas += [f"  - {nome}: {total}" for nome, total in por_prioridade.items()]
    linhas += ["", "Por categoria:"]
    linhas += [f"  - {nome}: {total}" for nome, total in por_categoria.items()]
    linhas += ["", "Primeiros da fila (prioridade alta):"]
    altas = fila[fila["prioridade"] == "alta"].head(10)
    if altas.empty:
        linhas.append("  (nenhum)")
    for _, r in altas.iterrows():
        linhas.append(f"  - [{r['bairro']}] {r['categoria']}: {r['descricao'][:90]}")
    linhas += ["", "A fila completa esta em saida/fila_priorizada.csv.",
               "Toda prioridade e uma sugestao do robo e deve ser conferida por uma pessoa."]
    mensagem = EmailMessage()
    mensagem["Subject"] = f"VivaBairro - resumo de relatos ({resumo['fim'][:10]})"
    mensagem["From"] = cfg["remetente"]
    mensagem["To"] = cfg["destino"]
    mensagem.set_content("\n".join(linhas), charset="utf-8", cte="8bit")
    return mensagem


def salvar(mensagem: EmailMessage, pasta: Path, nome: str) -> Path:
    pasta.mkdir(parents=True, exist_ok=True)
    destino = pasta / nome
    destino.write_bytes(mensagem.as_bytes())
    return destino


def enviar_ou_salvar(mensagem: EmailMessage, pasta: Path, nome: str = "resumo.eml") -> str:
    """Devolve o que aconteceu: 'enviado', 'salvo em arquivo (sem SMTP)' ou 'falha no envio, salvo em arquivo'."""
    log = obter()
    cfg = config.config_email()
    arquivo = salvar(mensagem, pasta, nome)
    if not cfg["host"]:
        log.info("SMTP nao configurado. E-mail salvo em %s", arquivo.name)
        return "salvo em arquivo (sem SMTP)"
    try:
        with smtplib.SMTP(cfg["host"], cfg["porta"], timeout=10) as servidor:
            servidor.starttls(context=ssl.create_default_context())
            if cfg["usuario"]:
                servidor.login(cfg["usuario"], cfg["senha"])
            servidor.send_message(mensagem)
        log.info("E-mail enviado para %s", cfg["destino"])
        return "enviado"
    except (smtplib.SMTPException, OSError) as falha:
        log.error("Falha no envio do e-mail (%s). Caminho seguro: copia salva em %s",
                  type(falha).__name__, arquivo.name)
        return "falha no envio, salvo em arquivo"
