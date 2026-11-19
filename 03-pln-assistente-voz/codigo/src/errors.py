"""Erros públicos: mensagens seguras, sem texto pessoal ou caminhos de arquivos."""


class VivaBairroError(Exception):
    """Falha recuperável que a interface pode mostrar ao usuário."""


class ValidationError(VivaBairroError):
    """Entrada inválida ou fora dos limites acordados."""


class ConsentRequired(VivaBairroError):
    """A operação exige uma decisão explícita do usuário."""


class ComponentUnavailable(VivaBairroError):
    """Integração ausente; nunca deve produzir resposta simulada."""


class ProviderError(VivaBairroError):
    """Somente código e mensagem seguros; nunca o corpo da resposta do provedor."""

    MESSAGES = {
        "authentication": "A autenticação OpenAI falhou. Confira a configuração privada no computador.",
        "permission": "A conta não tem permissão para este recurso ou modelo.",
        "rate_limit": "A API atingiu um limite de uso ou saldo. Confira os limites da conta.",
        "timeout": "O serviço demorou além do limite. Você pode tentar novamente.",
        "network": "Não foi possível conectar à OpenAI. Confira a conexão com a internet.",
        "unavailable": "O serviço está indisponível no momento.",
        "invalid_request": "O modelo ou os parâmetros não foram aceitos pela API. Consulte o diagnóstico técnico.",
        "invalid_output": "O serviço retornou uma resposta incompleta ou incompatível.",
        "speech_mismatch": "O áudio foi descartado porque a transcrição da síntese divergiu do texto autorizado.",
    }

    def __init__(self, code: str, status: int | None = None):
        self.code = code if code in self.MESSAGES else "unavailable"
        self.status = status
        super().__init__(self.MESSAGES[self.code])


class BudgetExceeded(VivaBairroError):
    """Limite de chamadas atingido, inclusive tentativas que falharam."""
