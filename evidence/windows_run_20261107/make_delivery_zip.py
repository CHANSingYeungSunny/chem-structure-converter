"""Build delivery A: a reproducible ZIP of the project without local state.

Run with any Python 3.x:
  python evidence/windows_run_20261107/make_delivery_zip.py
"""
from __future__ import annotations

import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT.parent / "chem-structure-converter-delivery.zip"
PREFIX = "chembridge_mvp"

TOP_LEVEL = [
    "README.md", ".gitignore", "pyproject.toml", "PACKAGE_MANIFEST.json",
    "requirements.txt", "requirements-ui.txt", "requirements-dev.txt",
    "start_windows.bat", "app.py",
    "chembridge", "scripts", "tests", "examples", "docs", "prompts", "evidence",
]
SKIP_PARTS = {"__pycache__", ".pytest_cache", "runs", ".venv", ".git",
              ".tmp", ".pipcache", ".playwright-cli", "build", "dist"}
SKIP_SUFFIXES = {".pyc", ".pyo"}


def main() -> None:
    files = []
    for name in TOP_LEVEL:
        source = ROOT / name
        if source.is_file():
            files.append(source)
        elif source.is_dir():
            files.extend(p for p in source.rglob("*") if p.is_file())
    files = [p for p in files
             if not (set(p.relative_to(ROOT).parts) & SKIP_PARTS)
             and p.suffix not in SKIP_SUFFIXES]
    files = sorted(set(files))

    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, f"{PREFIX}/{path.relative_to(ROOT).as_posix()}")
    print(f"ZIP_FILES={len(files)} ZIP_BYTES={OUT.stat().st_size} OUTPUT={OUT}")


if __name__ == "__main__":
    main()
