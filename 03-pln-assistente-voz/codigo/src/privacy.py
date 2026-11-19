"""Consentimento em memória e temporários sob responsabilidade do aplicativo."""
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Iterator

from .errors import ConsentRequired, ValidationError

NOTICE_VERSION = "2.0-openai"
NOTICE = (
    "Este assistente acadêmico envia sua gravação à OpenAI para transcrição. "
    "A transcrição, o histórico limitado e as orientações da base são enviados para gerar a resposta. "
    "O texto da resposta é enviado à OpenAI Realtime para produzir uma voz sintética. "
    "O serviço usa internet e pode gerar custos para o responsável pela chave. "
    "Não informe nome, CPF, telefone ou endereço residencial completo. "
    "As cópias locais da entrada são removidas após a transcrição; áudio de saída e histórico "
    "são mantidos temporariamente para reprodução e continuidade. Use Limpar conversa ao terminar. "
    "A exclusão local não exclui registros do provedor: store=false não garante retenção zero. "
    "O projeto não registra solicitações oficiais nem gera protocolos."
)


@dataclass(frozen=True)
class Consent:
    accepted: bool = False
    external_text: bool = False
    notice_version: str = NOTICE_VERSION
    accepted_at: str | None = None
    external_audio: bool = False

    @classmethod
    def grant(cls, *, external_text: bool = False, external_audio: bool = False) -> "Consent":
        return cls(True, external_text, NOTICE_VERSION, datetime.now(timezone.utc).isoformat(), external_audio)

    def require(self, *, external: bool = False, audio_external: bool = False) -> None:
        if not self.accepted or self.notice_version != NOTICE_VERSION or not self.accepted_at:
            raise ConsentRequired("Leia o aviso e confirme o consentimento antes de continuar.")
        if external and not self.external_text:
            raise ConsentRequired("O envio de texto ao serviço externo não foi autorizado.")
        if audio_external and not self.external_audio:
            raise ConsentRequired("O envio de áudio à OpenAI não foi autorizado.")


@contextmanager
def private_workspace(root: Path, consent: Consent) -> Iterator[Path]:
    """Remove apenas o diretório temporário criado aqui, inclusive em falhas.

    Não apaga uploads originais. Não promete apagamento seguro de SSD, backups
    ou sincronização OneDrive. root deve ser uma pasta privada do projeto.
    """
    consent.require()
    if root.is_symlink():
        raise ValidationError("A pasta temporária não pode ser um link simbólico.")
    root.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix="turn-", dir=root) as temporary:
        yield Path(temporary)
