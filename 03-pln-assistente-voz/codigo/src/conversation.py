"""Histórico por objeto de sessão, sem registro global ou persistência em disco."""
from dataclasses import dataclass, field
from pathlib import Path
from uuid import uuid4

from .errors import ValidationError
from .knowledge import KnowledgeBase
from .llm import Message


def checked_text(text: str, limit: int = 4000) -> str:
    if not isinstance(text, str) or not text.strip() or len(text) > limit:
        raise ValidationError(f"Informe um texto entre 1 e {limit} caracteres.")
    return text.strip()


@dataclass
class Conversation:
    max_turns: int = 6
    session_id: str = field(default_factory=lambda: str(uuid4()))
    _turns: list[tuple[str, str]] = field(default_factory=list, init=False, repr=False)

    def __post_init__(self) -> None:
        if not 1 <= self.max_turns <= 20:
            raise ValidationError("O histórico deve guardar entre 1 e 20 turnos.")

    @property
    def turns(self) -> tuple[tuple[str, str], ...]:
        return tuple(self._turns)

    def commit(self, user: str, assistant: str) -> None:
        # Ambos são validados antes de modificar a sessão.
        turn = checked_text(user), checked_text(assistant)
        self._turns.append(turn)
        self._turns[:] = self._turns[-self.max_turns:]

    def clear(self) -> None:
        self._turns.clear()
        self.session_id = str(uuid4())

    def messages(self, user: str, knowledge: KnowledgeBase, prompt_path: Path) -> tuple[Message, ...]:
        user = checked_text(user)
        try:
            prompt = checked_text(prompt_path.read_text(encoding="utf-8"), 16000)
        except OSError as exc:
            raise ValidationError("O system prompt não está disponível.") from exc
        messages = [Message("system", prompt + "\n\nBASE CURADA:\n" + knowledge.context())]
        for question, answer in self._turns:
            messages.extend((Message("user", question), Message("assistant", answer)))
        messages.append(Message("user", user))
        return tuple(messages)
