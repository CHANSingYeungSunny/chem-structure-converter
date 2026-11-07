"""Re-extract the starter guide PDF into a UTF-8 text evidence file.

Run from anywhere: python evidence/windows_run_20261107/extract_guide_text.py
Requires pypdf (already available in the system Python used for this audit).
"""
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[2]
PDF = ROOT / "docs" / "Engineering_Starter_Guide_zh.pdf"
OUT = Path(__file__).with_name("guide_extract.txt")

reader = PdfReader(str(PDF))
pages = [page.extract_text() or "" for page in reader.pages]
text = "\n\n".join(f"--- PAGE {i + 1} ---\n{body}" for i, body in enumerate(pages))
OUT.write_text(text, encoding="utf-8")
print(f"pages={len(pages)} chars={len(text)} output={OUT}")
