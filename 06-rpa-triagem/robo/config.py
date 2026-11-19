"""Caminhos, constantes e leitura das variaveis de ambiente do robo."""
import os
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DADOS = RAIZ / "dados"
ENTRADA = DADOS / "entrada"
TREINO = DADOS / "treino_relatos.csv"
TESTE = DADOS / "teste_rotulado.csv"
SAIDA = RAIZ / "saida"
EVIDENCIAS = RAIZ / "evidencias"

COLUNAS_OBRIGATORIAS = ["data", "bairro", "descricao"]
CATEGORIAS = [
    "Vias e buracos",
    "Calçadas e acessibilidade",
    "Iluminação pública",
    "Lixo e limpeza",
    "Drenagem e alagamentos",
    "Outros",
]
PRIORIDADES = ["alta", "media", "baixa"]

# Mesmos limites do contrato RelatoEntrada do front-end do VivaBairro.
BAIRRO_MIN, BAIRRO_MAX = 2, 60
DESCRICAO_MIN, DESCRICAO_MAX = 30, 900

# Abaixo deste valor o robo nao confia na propria classificacao e manda para revisao humana.
LIMIAR_CONFIANCA = 0.40

# Clima (Open-Meteo, API publica e sem chave).
URL_CLIMA = "https://api.open-meteo.com/v1/forecast"
CLIMA_TIMEOUT_S = 5
CLIMA_TENTATIVAS = 3
CLIMA_ESPERA_S = 1.0
CHUVA_FORTE_MM = 10.0  # limite escolhido pelo grupo para subir a prioridade de drenagem

# Coordenadas aproximadas do centro de alguns distritos de Sao Paulo.
# O robo envia para a API apenas estes numeros, nunca o texto do relato.
COORDENADAS_PADRAO = (-23.55, -46.63)
BAIRROS = {
    "se": (-23.55, -46.63),
    "lapa": (-23.52, -46.70),
    "pinheiros": (-23.56, -46.69),
    "itaquera": (-23.54, -46.45),
    "santo amaro": (-23.65, -46.71),
    "capao redondo": (-23.67, -46.78),
    "tucuruvi": (-23.48, -46.60),
    "mooca": (-23.56, -46.60),
    "butanta": (-23.57, -46.72),
    "vila mariana": (-23.59, -46.63),
    "penha": (-23.53, -46.54),
    "jabaquara": (-23.65, -46.64),
    "santana": (-23.50, -46.63),
    "grajau": (-23.77, -46.70),
    "sao miguel paulista": (-23.49, -46.44),
}


def relativo(caminho: Path) -> str:
    """Caminho relativo a raiz do projeto, para o log nao expor pastas do computador."""
    try:
        return Path(caminho).resolve().relative_to(RAIZ).as_posix()
    except ValueError:
        return Path(caminho).name


def carregar_env(caminho: Path | None = None) -> None:
    """Le um arquivo .env simples (CHAVE=valor) sem sobrescrever o que ja esta no ambiente."""
    caminho = caminho or (RAIZ / ".env")
    if not caminho.exists():
        return
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        chave, valor = linha.split("=", 1)
        os.environ.setdefault(chave.strip(), valor.strip().strip('"').strip("'"))


def config_email() -> dict:
    """Credenciais de e-mail vem so do ambiente. Sem elas o robo salva o e-mail em arquivo."""
    return {
        "host": os.environ.get("SMTP_HOST", ""),
        "porta": int(os.environ.get("SMTP_PORT", "587") or 587),
        "usuario": os.environ.get("SMTP_USER", ""),
        "senha": os.environ.get("SMTP_PASSWORD", ""),
        "remetente": os.environ.get("EMAIL_REMETENTE", "robo@vivabairro.invalid"),
        "destino": os.environ.get("EMAIL_DESTINO", "zeladoria@vivabairro.invalid"),
    }
