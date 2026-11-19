"""Registra saídas reais de verificações locais, separadas da avaliação acadêmica."""
import argparse
from datetime import datetime, timezone, timedelta
from importlib.metadata import version
import json
import os
from pathlib import Path
import platform
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ui", action="store_true", help="Inclui inicialização HTTP local")
    parser.add_argument("--evidence", type=Path, help="Grava o registro em um novo arquivo e preserva o histórico")
    args = parser.parse_args()
    commands = [
        ["-m", "pip", "check"],
        ["-m", "compileall", "-q", "app.py", "src", "tests", "evaluation", "scripts"],
        ["app.py", "--check"],
        ["-m", "unittest", "discover", "-s", "tests", "-v"],
    ]
    if args.ui:
        commands.append(["scripts/smoke_ui.py"])
    environment = dict(os.environ, PYTHONUTF8="1")
    results = []
    for command in commands:
        run = subprocess.run([sys.executable, *command], cwd=ROOT, env=environment,
                             capture_output=True, text=True, encoding="utf-8", timeout=120)
        results.append({"command": ["python", *command], "exit_code": run.returncode,
                        "stdout": run.stdout, "stderr": run.stderr})
        print(f"{'PASS' if run.returncode == 0 else 'FAIL'}: python {' '.join(command)}")
    evidence = {
        "recorded_at_sao_paulo": datetime.now(timezone(timedelta(hours=-3))).isoformat(),
        "python": platform.python_version(), "platform": platform.platform(),
        "packages": {name: version(name) for name in ("fastapi", "uvicorn", "httpx", "jiwer", "openai", "python-dotenv", "av")},
        "scope": "Custom web UI offline checks; no paid calls or academic voice evaluation",
        "checks": results,
    }
    target = args.evidence or ROOT / "docs/web_validation_evidence.json"
    with target.open("x" if args.evidence else "w", encoding="utf-8") as stream:
        stream.write(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n")
    return int(any(result["exit_code"] for result in results))


if __name__ == "__main__":
    raise SystemExit(main())
