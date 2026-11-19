"""Evidencia de resiliencia: provoca falhas de proposito e mostra o que o robo faz.

Cada cenario roda o fluxo completo em uma pasta separada (saida/demo_falhas/).
O resultado vai para evidencias/falhas.md, com o trecho do log de cada cenario.
"""
import os
import shutil
from pathlib import Path

from . import config, fluxo

URL_FORA_DO_AR = "https://api-clima-fora-do-ar.invalid/v1/forecast"
CLIMA_RAPIDO = {"url": URL_FORA_DO_AR, "tentativas": 1, "espera": 0}
LOTE_BOM = "relatos_2026-11-18.csv"


class RespostaSemCampo:
    """Resposta HTTP 200 com JSON fora do formato esperado (simulada)."""
    status_code = 200

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return {"daily": {}}


def trecho_do_log(pasta: Path, palavras: tuple[str, ...]) -> list[str]:
    linhas = (pasta / "robo.log").read_text(encoding="utf-8").splitlines()
    return [linha for linha in linhas if any(p in linha for p in palavras)]


def preparar(base: Path, nome: str, com_lote: bool = True) -> tuple[Path, Path]:
    pasta = base / nome
    if pasta.exists():
        shutil.rmtree(pasta)
    entrada, saida = pasta / "entrada", pasta / "saida"
    entrada.mkdir(parents=True)
    if com_lote:
        shutil.copy(config.ENTRADA / LOTE_BOM, entrada / LOTE_BOM)
    return entrada, saida


def demonstrar(destino: Path | None = None) -> list[dict]:
    destino = destino or config.EVIDENCIAS
    destino.mkdir(parents=True, exist_ok=True)
    base = config.SAIDA / "demo_falhas"
    cenarios = []

    def registrar(titulo, falha, esperado, resumo, saida, palavras, observado):
        cenarios.append({"titulo": titulo, "falha": falha, "esperado": esperado, "resumo": resumo,
                         "log": trecho_do_log(saida, palavras), "observado": observado})

    # 1. Arquivo ausente
    entrada, saida = preparar(base, "1_arquivo_ausente", com_lote=False)
    r = fluxo.executar(entrada, saida, CLIMA_RAPIDO)
    registrar("Arquivo de entrada ausente", "A pasta de entrada esta vazia.",
              "Registrar o erro, nao criar nem alterar nada e encerrar com relatorio.",
              r, saida, ("Nenhum arquivo", "Fim."),
              f"Status: {r['status']}. Banco criado: {(saida / 'vivabairro.db').exists()}.")

    # 2. Arquivo corrompido e arquivo sem as colunas, junto com um lote bom
    entrada, saida = preparar(base, "2_arquivos_ruins")
    (entrada / "a_corrompido.csv").write_bytes(bytes(range(128, 256)) * 20)
    (entrada / "b_sem_colunas.csv").write_text("nome,valor\nteste,1\n", encoding="utf-8")
    r = fluxo.executar(entrada, saida, CLIMA_RAPIDO)
    registrar("Arquivo corrompido e arquivo sem as colunas obrigatorias",
              "Dois arquivos ruins chegam junto com um lote valido.",
              "Rejeitar os dois arquivos, registrar o motivo e processar o lote valido.",
              r, saida, ("Arquivo rejeitado", "Arquivo lido", "Banco:"),
              f"Arquivos rejeitados: {len(r['arquivos_rejeitados'])}. Arquivos lidos: {r['arquivos_lidos']}. "
              f"Relatos novos no banco: {r['novos']}.")

    # 3. Dados invalidos dentro do lote
    registrar("Linhas com dado invalido",
              "O lote tem descricao curta, descricao vazia, bairro vazio e data fora do formato.",
              "Nao gravar essas linhas no banco e manda-las para revisao humana com o motivo.",
              r, saida, ("Linha invalida", "repetido", "Revisao humana"),
              f"Linhas invalidas: {r['invalidas']}. Repetidas no lote: {r['repetidos_no_lote']}. "
              f"Linhas validas: {r['validas']}.")

    # 4. API fora do ar
    entrada, saida = preparar(base, "4_api_fora_do_ar")
    r = fluxo.executar(entrada, saida, {"url": URL_FORA_DO_AR, "tentativas": 3, "espera": 0.5})
    registrar("API de clima fora do ar",
              "O endereco da API nao responde (dominio inexistente).",
              "Tentar 3 vezes com espera crescente (0,5 s e 1 s), registrar e seguir sem o dado de chuva.",
              r, saida, ("API de clima", "Banco:", "Fim."),
              f"API de clima: {r['api_clima']}. Relatos novos no banco: {r['novos']}. Status: {r['status']}.")

    # 5. API responde, mas com JSON fora do formato (resposta simulada)
    entrada, saida = preparar(base, "5_api_resposta_invalida")
    r = fluxo.executar(entrada, saida, {"requisitar": lambda *a, **k: RespostaSemCampo(),
                                        "tentativas": 2, "espera": 0})
    registrar("API responde com dado invalido (resposta simulada)",
              "A API devolve HTTP 200, mas sem o campo precipitation_sum.",
              "Validar o JSON, tratar como falha e seguir sem o dado de chuva.",
              r, saida, ("API de clima", "Fim."),
              f"API de clima: {r['api_clima']}. Status: {r['status']}.")

    # 6. Servidor de e-mail invalido
    entrada, saida = preparar(base, "6_email_falha")
    antigos = {k: os.environ.get(k) for k in ("SMTP_HOST", "SMTP_PORT")}
    os.environ["SMTP_HOST"], os.environ["SMTP_PORT"] = "smtp-fora-do-ar.invalid", "587"
    try:
        r = fluxo.executar(entrada, saida, CLIMA_RAPIDO)
    finally:
        for chave, valor in antigos.items():
            if valor is None:
                os.environ.pop(chave, None)
            else:
                os.environ[chave] = valor
    registrar("Falha no envio do e-mail",
              "O servidor SMTP configurado nao existe.",
              "Registrar a falha e salvar o e-mail em arquivo .eml para envio manual.",
              r, saida, ("e-mail", "E-mail"),
              f"E-mail: {r['email']}. Arquivo salvo: {(saida / 'emails' / 'resumo.eml').exists()}.")

    # 7. Reexecucao com o mesmo lote (idempotencia)
    entrada, saida = preparar(base, "7_reexecucao")
    primeira = fluxo.executar(entrada, saida, CLIMA_RAPIDO)
    segunda = fluxo.executar(entrada, saida, CLIMA_RAPIDO)
    registrar("Mesmo lote processado duas vezes",
              "O robo e executado de novo sem que o lote tenha mudado.",
              "Nao duplicar relatos no banco.",
              segunda, saida, ("Banco:",),
              f"Primeira execucao: {primeira['novos']} novos. Segunda execucao: {segunda['novos']} novos "
              f"e {segunda['ja_existentes']} ja existentes.")

    linhas = ["# Casos de falha provocados e o que o robo fez", "",
              "Gerado por `python main.py falhas`. Cada cenario roda o fluxo completo em "
              "`saida/demo_falhas/`.", ""]
    for numero, c in enumerate(cenarios, start=1):
        linhas += [f"## {numero}. {c['titulo']}", "",
                   f"- Falha provocada: {c['falha']}",
                   f"- Comportamento esperado: {c['esperado']}",
                   f"- Observado: {c['observado']}", "",
                   "Trecho do log:", "", "```", *c["log"], "```", ""]
    (destino / "falhas.md").write_text("\n".join(linhas), encoding="utf-8")
    return cenarios
