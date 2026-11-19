"""Base pequena, curada, versionada; contexto completo sem busca vetorial."""
from dataclasses import dataclass
from datetime import date
import json
from pathlib import Path

from .errors import ValidationError

TOPICS = frozenset({"buracos", "calcadas", "iluminacao", "lixo", "alagamentos"})


@dataclass(frozen=True)
class Guidance:
    id: str
    topic: str
    text: str
    source_url: str
    source_title: str
    geographic_scope: str
    consulted_on: str
    kind: str


@dataclass(frozen=True)
class KnowledgeBase:
    version: str
    entries: tuple[Guidance, ...]

    @classmethod
    def load(cls, path: Path) -> "KnowledgeBase":
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if data["schema_version"] != 1 or not data["version"]:
                raise ValueError("schema")
            entries = tuple(Guidance(**row) for row in data["entries"])
            if not entries or len({e.id for e in entries}) != len(entries):
                raise ValueError("ids")
            if {e.topic for e in entries} != TOPICS:
                raise ValueError("topics")
            for entry in entries:
                if not all(isinstance(value, str) and value.strip() for value in vars(entry).values()):
                    raise ValueError("empty")
                date.fromisoformat(entry.consulted_on)
                if entry.kind not in {"official_guidance", "editorial_guidance"}:
                    raise ValueError("kind")
                if entry.kind == "official_guidance" and not entry.source_url.startswith("https://"):
                    raise ValueError("source")
            return cls(data["version"], entries)
        except (OSError, KeyError, TypeError, ValueError) as exc:
            raise ValidationError("A base de conhecimento está ausente ou inválida.") from exc

    def context(self) -> str:
        """Metadados acompanham a orientação; não há instruções municipais implícitas."""
        return "\n\n".join(
            f"[{e.id}] Tema: {e.topic}. {e.text}\n"
            f"Fonte: {e.source_title}; {e.source_url}; escopo: {e.geographic_scope}; "
            f"consulta: {e.consulted_on}; natureza: {e.kind}." for e in self.entries
        )
