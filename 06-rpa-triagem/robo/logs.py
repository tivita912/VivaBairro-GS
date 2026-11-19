"""Log do robo: tudo vai para o console e para um arquivo em UTF-8."""
import logging
from pathlib import Path

NOME = "robo"
FORMATO = "%(asctime)s | %(levelname)-7s | %(message)s"


def configurar(arquivo: Path) -> logging.Logger:
    arquivo.parent.mkdir(parents=True, exist_ok=True)
    log = logging.getLogger(NOME)
    log.setLevel(logging.INFO)
    for antigo in list(log.handlers):
        antigo.close()
        log.removeHandler(antigo)
    formato = logging.Formatter(FORMATO, datefmt="%Y-%m-%d %H:%M:%S")
    para_arquivo = logging.FileHandler(arquivo, mode="w", encoding="utf-8")
    para_arquivo.setFormatter(formato)
    para_console = logging.StreamHandler()
    para_console.setFormatter(formato)
    log.addHandler(para_arquivo)
    log.addHandler(para_console)
    log.propagate = False
    return log


def obter() -> logging.Logger:
    return logging.getLogger(NOME)
