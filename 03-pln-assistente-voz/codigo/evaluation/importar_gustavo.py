"""Copia e audita originais de Gustavo. A associação aos IDs é feita por escuta."""

import argparse
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory

from evaluation.run_stt import FORMATS, ROOT, digest, inspect, run
from src.config import Settings
from src.errors import ValidationError


def ingest(source, root=ROOT):
    destination = root / "audio/Gustavo"
    if not source.is_dir() or source.is_symlink():
        raise ValidationError("Informe uma pasta de gravações local.")
    if destination.is_symlink() or (root / "audio").is_symlink():
        raise ValidationError("O destino do corpus não pode ser um link.")
    files = sorted(p for p in source.iterdir() if p.is_file() and not p.is_symlink())
    if not files or any(p.suffix.lower() not in FORMATS for p in files):
        raise ValidationError("Separe as gravações compatíveis dos outros arquivos antes de importar.")
    existing = {digest(p): p for p in (root / "audio").rglob("*") if p.is_file() and not p.is_symlink()}
    copied = []
    skipped = []
    settings = Settings.load()
    with TemporaryDirectory(prefix="vivabairro-importar-") as temporary:
        for path in files:
            info = inspect(path, source, settings, Path(temporary))
            if info["integrity"] != "VALIDO" or info["app_compatible"] != "true":
                raise ValidationError(f"{path.name}: áudio recusado pelo validador.")
            sha = info["sha256"]
            target = destination / path.name
            if target.exists() and (target.is_symlink() or digest(target) != sha):
                raise ValidationError(f"{path.name}: o destino já contém outro original. Renomeie o arquivo recebido.")
            if sha in existing:
                skipped.append(path.name)
                continue
            existing[sha] = target
            copied.append((path, target, sha))
    if copied:
        destination.mkdir(parents=True, exist_ok=True)
    for path, target, sha in copied:
        with path.open("rb") as src, target.open("xb") as out:
            try:
                shutil.copyfileobj(src, out)
            except OSError:
                out.close()
                target.unlink()
                raise
        if digest(target) != sha:
            target.unlink()
            raise ValidationError(f"{path.name}: o original de origem mudou durante a cópia.")
    return len(copied), skipped


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pasta", type=Path)
    args = parser.parse_args()
    try:
        count, skipped = ingest(args.pasta.resolve())
        print(f"{count} novos originais; {len(skipped)} duplicados por SHA-256 ignorados.")
        run(ROOT, argparse.Namespace(modelo="gpt-transcribe", autorizar_api=None, ids=None, repetir_falhas=False,
                                     rascunhos_local=None, importar_revisao=None))
    except (OSError, ValidationError) as error:
        parser.exit(1, f"Importação interrompida: {error}\n")


if __name__ == "__main__":
    main()
