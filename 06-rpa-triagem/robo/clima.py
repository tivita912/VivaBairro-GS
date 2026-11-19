"""Tema 2 - Integracao com API (Open-Meteo, publica e sem chave).

Busca a chuva prevista para o dia no bairro. Se chover forte, relatos de drenagem
sobem de prioridade. A chamada tem timeout, novas tentativas com espera crescente
e um caminho seguro: se a API falhar, o robo segue sem o dado de chuva.
"""
import time
from dataclasses import dataclass

import requests

from . import config
from .leitura import sem_acento
from .logs import obter


@dataclass
class Chuva:
    ok: bool
    mm: float | None
    tentativas: int
    erro: str = ""


def coordenadas(bairro: str) -> tuple[tuple[float, float], bool]:
    """Devolve as coordenadas do bairro e se ele foi encontrado na tabela."""
    chave = sem_acento(bairro)
    if chave in config.BAIRROS:
        return config.BAIRROS[chave], True
    return config.COORDENADAS_PADRAO, False


def extrair_mm(resposta: dict) -> float:
    """Valida o JSON da API. Formato inesperado vira erro tratado."""
    valores = resposta["daily"]["precipitation_sum"]
    valor = valores[0]
    if valor is None:
        raise ValueError("precipitation_sum vazio")
    mm = float(valor)
    if mm < 0 or mm > 1000:
        raise ValueError(f"precipitation_sum fora do esperado: {mm}")
    return mm


def buscar_chuva(lat: float, lon: float, *, url: str | None = None, tentativas: int | None = None,
                 timeout: float | None = None, espera: float | None = None,
                 requisitar=requests.get, dormir=time.sleep) -> Chuva:
    log = obter()
    url = url or config.URL_CLIMA
    tentativas = tentativas or config.CLIMA_TENTATIVAS
    timeout = timeout or config.CLIMA_TIMEOUT_S
    espera = config.CLIMA_ESPERA_S if espera is None else espera
    parametros = {
        "latitude": lat, "longitude": lon, "daily": "precipitation_sum",
        "forecast_days": 1, "timezone": "America/Sao_Paulo",
    }
    erro = ""
    for numero in range(1, tentativas + 1):
        try:
            resposta = requisitar(url, params=parametros, timeout=timeout)
            resposta.raise_for_status()
            return Chuva(ok=True, mm=extrair_mm(resposta.json()), tentativas=numero)
        except (requests.RequestException, ValueError, KeyError, IndexError, TypeError) as falha:
            erro = f"{type(falha).__name__}"
            log.warning("API de clima falhou (tentativa %d de %d): %s", numero, tentativas, erro)
            if numero < tentativas:
                dormir(espera * (2 ** (numero - 1)))
    return Chuva(ok=False, mm=None, tentativas=tentativas, erro=erro)


def chuva_por_bairro(bairros: list[str], **opcoes) -> dict[str, Chuva]:
    """Uma chamada por coordenada diferente. Depois de uma falha total, nao insiste nas demais."""
    log = obter()
    por_coordenada: dict[tuple[float, float], Chuva] = {}
    resultado: dict[str, Chuva] = {}
    api_fora = False
    for bairro in sorted(set(bairros)):
        ponto, conhecido = coordenadas(bairro)
        if not conhecido:
            log.warning("Bairro fora da tabela de coordenadas: %s. Usando o centro da cidade.", bairro)
        if ponto not in por_coordenada:
            if api_fora:
                por_coordenada[ponto] = Chuva(ok=False, mm=None, tentativas=0, erro="API indisponivel")
            else:
                por_coordenada[ponto] = buscar_chuva(*ponto, **opcoes)
                if not por_coordenada[ponto].ok:
                    api_fora = True
                    log.error("API de clima indisponivel. Caminho seguro: o robo segue sem o dado "
                              "de chuva e nao altera prioridades.")
        resultado[bairro] = por_coordenada[ponto]
    return resultado
