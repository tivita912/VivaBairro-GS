"""Estado backend e arquivos por sessão; nenhum segredo é guardado no estado Gradio."""
from dataclasses import dataclass, field
from pathlib import Path
import shutil
import tempfile
import threading
import time

from .api_runtime import CallBudget
from .config import Settings
from .conversation import Conversation
from .errors import ValidationError
from .privacy import Consent


def remove_owned(path: Path, root: Path):
    """Só remove filhos da raiz privada conhecida; nunca a raiz ou arquivos originais externos."""
    resolved, boundary = path.resolve(), root.resolve()
    if resolved == boundary or not resolved.is_relative_to(boundary) or path.is_symlink():
        raise ValidationError("Tentativa de limpeza fora da pasta temporária da aplicação.")
    if resolved.is_dir():
        shutil.rmtree(resolved)
    else:
        resolved.unlink(missing_ok=True)


@dataclass
class UserSession:
    settings: Settings
    root: Path
    consent: Consent = field(default_factory=Consent)
    conversation: Conversation = field(init=False)
    budget: CallBudget = field(init=False, repr=False)
    folder: Path = field(init=False, repr=False)
    last_touch: float = field(default_factory=time.monotonic)
    closed: bool = False
    metrics: dict = field(default_factory=dict)
    pending: dict = field(default_factory=dict, repr=False)
    lock: threading.RLock = field(default_factory=threading.RLock, repr=False)

    def __post_init__(self):
        self.conversation = Conversation(self.settings.history_turns)
        self.budget = CallBudget(self.settings.session_requests)
        self.root.mkdir(parents=True, exist_ok=True)
        self.folder = Path(tempfile.mkdtemp(prefix="session-", dir=self.root))

    def touch(self):
        self.last_touch = time.monotonic()

    def clear(self, revoke=False):
        with self.lock:
            self.conversation.clear()
            self.pending.clear()
            self.metrics.clear()
            if self.folder.exists():
                for path in self.folder.iterdir():
                    remove_owned(path, self.root)
            if revoke:
                self.consent = Consent()
            self.touch()

    def close(self):
        with self.lock:
            self.clear(revoke=True)
            remove_owned(self.folder, self.root)
            self.closed = True

    def history(self):
        return [{"role": role, "content": text} for question, answer in self.conversation.turns
                for role, text in (("user", question), ("assistant", answer))]
