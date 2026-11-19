"""Interface HTTP local para o controlador de voz existente."""
from contextlib import asynccontextmanager
from functools import partial
from pathlib import Path
from secrets import token_urlsafe
from tempfile import TemporaryDirectory
from threading import Lock
from time import perf_counter
from typing import Literal

from anyio import fail_after, to_thread
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, Response
from pydantic import BaseModel, StrictBool
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.requests import ClientDisconnect
from starlette.staticfiles import StaticFiles

from .api_config import APIConfig
from .config import PROJECT_ROOT, Settings
from .controller import VoiceController
from .errors import BudgetExceeded, ConsentRequired, ProviderError, VivaBairroError
from .knowledge import KnowledgeBase
from .privacy import NOTICE, NOTICE_VERSION
from .session import UserSession

WEB = PROJECT_ROOT / "web"
AudioFormat = Literal["wav", "mp3", "m4a", "mp4", "webm", "ogg", "flac"]
AudioSource = Literal["microphone", "upload"]


class ConsentForm(BaseModel):
    accepted: StrictBool
    external_audio: StrictBool
    external_text: StrictBool
    notice_version: str


def create_app(settings: Settings | None = None, *, pipeline_factory=None) -> FastAPI:
    settings = settings or Settings.load()
    try:
        config, config_error = APIConfig.load(), ""
    except VivaBairroError as exc:
        config, config_error = None, str(exc)
    available = config is not None or pipeline_factory is not None
    knowledge = KnowledgeBase.load(PROJECT_ROOT / "knowledge/urban_guidance.json")
    sessions: dict[str, UserSession] = {}
    registry_lock = Lock()
    turn_slot = Lock()

    @asynccontextmanager
    async def lifespan(app):
        with TemporaryDirectory(prefix="vivabairro-web-") as folder:
            app.state.controller = VoiceController(settings, Path(folder), config, config_error, pipeline_factory)
            app.state.controller.start_cleanup()
            try:
                yield
            finally:
                app.state.controller.close()
                sessions.clear()

    app = FastAPI(title="VivaBairro Voz", lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "testserver"])
    app.mount("/assets", StaticFiles(directory=WEB / "assets"), name="assets")

    @app.middleware("http")
    async def response_headers(request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "microphone=(self)"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; media-src 'self' blob:; object-src 'none'; "
            "base-uri 'none'; frame-ancestors 'none'; form-action 'self'"
        )
        if not request.url.path.startswith("/assets/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request, exc):
        return JSONResponse({"detail": "Confira os dados enviados e tente novamente."}, status_code=422)

    def active_session(request: Request) -> UserSession:
        token = request.headers.get("x-vivabairro-session", "")
        with registry_lock:
            session = sessions.get(token)
        if not session or session.closed:
            raise HTTPException(410, "A sessão expirou. Confirme novamente o consentimento.")
        return session

    def require_consent(session: UserSession):
        if session.closed:
            raise HTTPException(410, "A sessão expirou. Confirme novamente o consentimento.")
        try:
            session.consent.require(external=True, audio_external=True)
        except ConsentRequired as exc:
            raise HTTPException(403, str(exc)) from None

    @app.get("/")
    def index():
        return FileResponse(WEB / "index.html", media_type="text/html")

    @app.get("/api/info")
    def info():
        return {
            "available": available, "configuration_message": config_error if not available else "",
            "notice": NOTICE, "notice_version": NOTICE_VERSION,
            "max_audio_seconds": settings.max_audio_seconds, "max_audio_mb": settings.max_audio_mb,
            "retention_seconds": settings.retention_seconds,
            "topics": {e.topic: {"text": e.text, "source_title": e.source_title, "source_url": e.source_url}
                       for e in knowledge.entries},
        }

    @app.post("/api/consent")
    def authorize(form: ConsentForm, request: Request):
        if not available:
            raise HTTPException(503, config_error)
        if form.notice_version != NOTICE_VERSION or not (form.accepted and form.external_audio and form.external_text):
            raise HTTPException(403, "Leia o aviso vigente e confirme as três opções para continuar.")
        controller = request.app.state.controller
        token = request.headers.get("x-vivabairro-session", "")
        with registry_lock:
            for expired in [key for key, value in sessions.items() if value.closed]:
                sessions.pop(expired)
            session = sessions.get(token)
            if session is None:
                if len(sessions) >= 32:
                    raise HTTPException(429, "Há muitas sessões abertas. Tente novamente em alguns minutos.")
                token = token_urlsafe(32)
                sessions[token] = controller.authorize(None, True, True, True)
        if session is not None:
            with session.lock:
                if session.closed:
                    raise HTTPException(410, "A sessão expirou. Confirme novamente o consentimento.")
                controller.authorize(session, True, True, True)
        return {"session": token}

    @app.post("/api/clear")
    def clear(request: Request):
        session = active_session(request)
        with session.lock:
            if not session.closed:
                session.clear(revoke=True)
        return {"cleared": True}

    def run_turn(controller: VoiceController, session: UserSession, path: Path, source: str):
        with session.lock:
            require_consent(session)
            session.pending = {}
            session.metrics = {}
            try:
                result = controller.process(session, path, source)
            except VivaBairroError as exc:
                code = 429 if isinstance(exc, BudgetExceeded) else 502 if isinstance(exc, ProviderError) else 422
                return JSONResponse({"detail": str(exc), "error_code": exc.code if isinstance(exc, ProviderError) else None, **session.pending, "metrics": session.metrics,
                                     "history": session.history()}, status_code=code)
            except Exception:
                return JSONResponse({"detail": "Não foi possível concluir o atendimento. Tente novamente.",
                                     **session.pending, "metrics": session.metrics,
                                     "history": session.history()}, status_code=500)
            return {
                "transcription": result.transcription, "response": result.response, "speech_text": result.speech_text,
                "audio_url": "/api/audio/" + result.audio.path.name, "metrics": session.metrics,
                "history": session.history(),
            }

    @app.post("/api/turn")
    async def turn(request: Request, format: AudioFormat, source: AudioSource):
        started = perf_counter()
        session = active_session(request)
        require_consent(session)
        if request.headers.get("content-type") != "application/octet-stream":
            raise HTTPException(415, "Envie o áudio como arquivo.")
        if not turn_slot.acquire(blocking=False):
            raise HTTPException(429, "Já há um áudio em processamento. Aguarde e tente novamente.")
        controller = request.app.state.controller
        limit = settings.max_audio_mb * 1024 * 1024
        try:
            with TemporaryDirectory(prefix="upload-", dir=controller.root) as folder:
                path = Path(folder) / f"entrada.{format}"
                size = 0
                body_started = perf_counter()
                try:
                    with fail_after(settings.timeout_seconds):
                        with path.open("wb") as target:
                            async for chunk in request.stream():
                                size += len(chunk)
                                if size > limit:
                                    raise HTTPException(413, "O arquivo excede o limite de tamanho.")
                                target.write(chunk)
                except TimeoutError:
                    raise HTTPException(408, "O envio do áudio demorou demais. Tente novamente.") from None
                except ClientDisconnect:
                    raise HTTPException(400, "O envio do áudio foi interrompido.") from None
                if not size:
                    raise HTTPException(422, "Grave ou selecione um áudio antes de enviar.")
                body_ms = (perf_counter() - body_started) * 1000
                result = await to_thread.run_sync(partial(run_turn, controller, session, path, source))
                response = result if isinstance(result, JSONResponse) else JSONResponse(result)
                handler_ms = (perf_counter() - started) * 1000
                response.headers["Server-Timing"] = f"handler;dur={handler_ms:.3f}, body;dur={body_ms:.3f}"
                return response
        finally:
            turn_slot.release()

    @app.get("/api/audio/{name}")
    def audio(name: str, request: Request):
        started = perf_counter()
        session = active_session(request)
        with session.lock:
            require_consent(session)
            for candidate in session.folder.glob("turn-*/*.wav"):
                if candidate.name == name and candidate.is_file():
                    # Capture os bytes enquanto a sessão protege o arquivo de limpeza concorrente.
                    content = candidate.read_bytes()
                    timing = f"audio;dur={(perf_counter() - started) * 1000:.3f}"
                    return Response(content, media_type="audio/wav", headers={"Server-Timing": timing})
        raise HTTPException(404, "Este áudio não está mais disponível.")

    return app
