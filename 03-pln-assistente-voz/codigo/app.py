"""VivaBairro Voz: interface local com backend OpenAI e consentimento prévio."""
import argparse
import json
from pathlib import Path
import sys

from src.config import PROJECT_ROOT, Settings
from src.errors import VivaBairroError
from src.knowledge import KnowledgeBase


def diagnose(settings: Settings) -> dict:
    from src.api_config import APIConfig
    base = KnowledgeBase.load(PROJECT_ROOT / "knowledge/urban_guidance.json")
    if not (PROJECT_ROOT / "prompts/system_v1.txt").read_text(encoding="utf-8").strip():
        raise VivaBairroError("O system prompt está vazio.")
    try:
        api = APIConfig.load().public_status()
    except VivaBairroError as exc:
        api = {"key_configured": False, "diagnostic": str(exc)}
    return {"stage": "02-openai", "knowledge_version": base.version,
            "knowledge_entries": len(base.entries), "system_prompt": "v1.0",
            "history_turns": settings.history_turns, "api": api,
            "adapters": "OpenAI STT, Responses e Realtime implementados",
            "speech_adaptation": "normalização conservadora pt-BR",
            "voice_end_to_end": "not_tested", "network_calls_in_this_check": 0}


def main() -> int:
    parser = argparse.ArgumentParser(description="VivaBairro Voz — OpenAI")
    parser.add_argument("--check", action="store_true", help="Diagnóstico local sem chamadas de API")
    parser.add_argument("--env-file", type=Path, help="Somente limites VIVABAIRRO_; não é o arquivo de segredos")
    args = parser.parse_args()
    try:
        settings = Settings.load(args.env_file)
        if args.check:
            print(json.dumps(diagnose(settings), ensure_ascii=False, indent=2))
        else:
            import uvicorn
            from src.web import create_app

            uvicorn.run(create_app(settings), host="127.0.0.1", port=settings.port, access_log=False)
        return 0
    except (VivaBairroError, ImportError, OSError) as exc:
        print(str(exc) if isinstance(exc, VivaBairroError) else "Não foi possível iniciar. Confira dependências, configuração e porta.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
