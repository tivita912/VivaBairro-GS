"""Orquestração preparada por injeção de dependências; sem adaptadores reais."""
from contextlib import ExitStack
from dataclasses import dataclass, field
from pathlib import Path

from .audio_input import prepare_audio
from .config import Settings
from .conversation import Conversation, checked_text
from .errors import ValidationError
from .knowledge import KnowledgeBase
from .llm import LLMBackend
from .metrics import LatencyTracker
from .privacy import Consent
from .speech_text import SpeechAdapter
from .stt import STTBackend
from .tts import SynthesizedAudio, TTSBackend


@dataclass(frozen=True)
class TurnResult:
    transcription: str
    response: str
    speech_text: str
    audio: SynthesizedAudio
    metrics: dict
    warnings: tuple[str, ...] = ()
    models: dict = field(default_factory=dict)
    usage: dict = field(default_factory=dict)


@dataclass
class VoicePipeline:
    stt: STTBackend
    llm: LLMBackend
    speech: SpeechAdapter
    tts: TTSBackend
    knowledge: KnowledgeBase
    prompt_path: Path
    settings: Settings

    def run(self, audio_path: Path, source: str, session: Conversation,
            consent: Consent, input_root: Path, output_dir: Path, on_progress=None) -> TurnResult:
        """Chamador fornece output_dir privado e gerencia seu tempo de vida.

        Um turno por sessão por vez. A futura UI deve serializar eventos da mesma
        sessão. Nenhum estado de usuário fica nos adaptadores compartilhados.
        """
        consent.require(external=self.tts.sends_text_externally or getattr(self.llm, "sends_text_externally", False),
                        audio_external=getattr(self.stt, "sends_audio_externally", False))
        progress = on_progress or (lambda stage, value: None)
        tracker = LatencyTracker()
        # Apenas a cópia transitória é excluída, logo após transcrição ou falha.
        with ExitStack() as stack:
            with tracker.measure("input"):
                audio = stack.enter_context(prepare_audio(audio_path, source, consent, self.settings, input_root))
            with tracker.measure("stt"):
                transcription = self.stt.transcribe(audio)
                if transcription.language not in {"pt", "pt-BR"}:
                    raise ValidationError("A transcrição deve estar em português.")
                user = checked_text(transcription.text)
        progress("transcription", user)
        with tracker.measure("context"):
            messages = session.messages(user, self.knowledge, self.prompt_path)
        with tracker.measure("llm"):
            generated = self.llm.generate(messages)
            response = checked_text(generated.text)
        progress("response", response)
        with tracker.measure("speech_text"):
            adapted = self.speech.adapt(response)
            spoken = checked_text(adapted.text)
        progress("speech_text", spoken)
        with tracker.measure("tts"):
            synthesized = self.tts.synthesize(spoken, output_dir)
            resolved = synthesized.path.resolve()
            if not resolved.is_relative_to(output_dir.resolve()) or not resolved.is_file():
                raise ValidationError("O sintetizador não retornou áudio na pasta do turno.")
            if resolved.stat().st_size == 0:
                raise ValidationError("O sintetizador retornou um arquivo vazio.")
        timing = tracker.finish()
        timing["input_audio_duration_seconds"] = audio.duration_seconds
        session.commit(user, response)  # Falhas não deixam turnos incompletos.
        return TurnResult(user, response, spoken, synthesized, timing, adapted.warnings,
            {"stt": {"requested": transcription.model_id, "reported": transcription.model_revision},
             "llm": {"requested": generated.model_id, "reported": generated.model_revision},
             "tts": {"requested": synthesized.model_id, "reported": synthesized.model_revision}},
            {"stt": transcription.usage, "llm": generated.usage, "tts": synthesized.usage})
