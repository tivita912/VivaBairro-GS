"""Coordenação de sessões sem segredos no frontend e sem logs de relatos."""
from pathlib import Path
import threading
import time
from uuid import uuid4

from .api_config import APIConfig
from .api_runtime import APIRuntime
from .config import PROJECT_ROOT, Settings
from .errors import ComponentUnavailable, VivaBairroError, ValidationError
from .knowledge import KnowledgeBase
from .llm import OpenAILLM
from .pipeline import VoicePipeline
from .privacy import Consent
from .session import UserSession, remove_owned
from .speech_text import PortugueseSpeechAdapter
from .stt import OpenAISTT
from .tts import OpenAIRealtimeTTS


class VoiceController:
    def __init__(self, settings: Settings, runtime_root: Path, config: APIConfig | None,
                 config_error: str = "", pipeline_factory=None):
        self.settings, self.root = settings, runtime_root
        self._config, self.config_error = config, config_error
        self.pipeline_factory = pipeline_factory
        self._sessions: list[UserSession] = []
        self._registry_lock = threading.Lock()
        self._stop = threading.Event()
        self._sweeper = None

    def new_session(self):
        session = UserSession(self.settings, self.root / "sessions")
        with self._registry_lock:
            self._sessions.append(session)
        return session

    def start_cleanup(self):
        if self._sweeper:
            return
        def sweep():
            while not self._stop.wait(10):
                with self._registry_lock:
                    sessions = list(self._sessions)
                for session in sessions:
                    if time.monotonic() - session.last_touch > self.settings.retention_seconds:
                        if session.lock.acquire(blocking=False):
                            try:
                                if not session.closed:
                                    session.close()
                            finally:
                                session.lock.release()
                with self._registry_lock:
                    self._sessions[:] = [s for s in self._sessions if not s.closed]
        self._sweeper = threading.Thread(target=sweep, daemon=True, name="vivabairro-cleanup")
        self._sweeper.start()

    def close(self):
        self._stop.set()
        if self._sweeper:
            self._sweeper.join(timeout=2)
        with self._registry_lock:
            for session in self._sessions:
                if not session.closed:
                    session.close()
            self._sessions.clear()

    def authorize(self, session, accepted, audio_external, text_external):
        if session is None or session.closed:
            session = self.new_session()
        with session.lock:
            if accepted and audio_external and text_external:
                session.consent = Consent.grant(external_text=True, external_audio=True)
                session.touch()
            else:
                session.clear(revoke=True)
        return session

    def pipeline(self, session):
        if self.pipeline_factory:
            return self.pipeline_factory(session)
        if self._config is None:
            raise ComponentUnavailable(self.config_error or "A configuração privada da OpenAI não está disponível.")
        runtime = APIRuntime(self._config, self.settings, session.budget)
        pipeline = VoicePipeline(OpenAISTT(runtime), OpenAILLM(runtime), PortugueseSpeechAdapter(),
            OpenAIRealtimeTTS(runtime), KnowledgeBase.load(PROJECT_ROOT / "knowledge/urban_guidance.json"),
            PROJECT_ROOT / "prompts/system_v1.txt", self.settings)
        return pipeline, runtime

    def process(self, session, path, source):
        if session is None or session.closed:
            raise ValidationError("A sessão expirou. Confirme novamente o consentimento.")
        with session.lock:
            session.consent.require(external=True, audio_external=True)
            session.budget.require_capacity(3)
            if not path:
                raise ValidationError("Grave um áudio ou selecione um arquivo antes de enviar.")
            path = Path(path)
            if not path.resolve().is_relative_to(self.root.resolve()) or path.is_symlink():
                raise ValidationError("O áudio deve vir da área de upload desta aplicação.")
            session.touch()
            session.pending = {}
            session.metrics = {}
            # O áudio anterior deixa de ser servido ao começar novo turno.
            for previous in session.folder.iterdir():
                remove_owned(previous, self.root)
            output = session.folder / ("turn-" + str(uuid4()))
            output.mkdir()
            runtime = None
            started = time.perf_counter()
            def progress(stage, value):
                session.pending[stage] = value
                if stage == "transcription":
                    remove_owned(path, self.root)  # Remove upload do Gradio logo após STT.
            try:
                pipeline, runtime = self.pipeline(session)
                result = pipeline.run(path, source, session.conversation, session.consent,
                                      session.folder / "input", output, on_progress=progress)
                session.metrics = dict(result.metrics, usage=result.usage, models=result.models,
                    session_request_attempts=session.budget.used, warnings=list(result.warnings),
                    playback_measurement="not_instrumented", cost_charged=None)
                return result
            except Exception:
                remove_owned(output, self.root)
                session.metrics = {"failed": True, "elapsed_to_failure_seconds": time.perf_counter() - started,
                                   "playback_start_seconds": None, "session_request_attempts": session.budget.used}
                raise
            finally:
                remove_owned(path, self.root)
                if runtime:
                    session.metrics["request_metadata"] = runtime.records
                session.touch()

    def discard_upload(self, value):
        if value:
            path = Path(value)
            if path.exists() and path.resolve().is_relative_to(self.root.resolve()) and not path.is_symlink():
                remove_owned(path, self.root)
