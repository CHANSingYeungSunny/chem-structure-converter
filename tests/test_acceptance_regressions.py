"""Regressions derived from the Windows 2026-11-07/08 acceptance run.

Unlike the inline-string fixtures in test_workflow.py, these call the real CLI
with the shipped example files and assert exit codes, manifest counts, byte
preservation and refusal semantics end to end.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"


def cli(out_dir: Path, input_name: str, *extra: str):
    command = [sys.executable, "-m", "chembridge",
               str(EXAMPLES / input_name), "--out", str(out_dir), *extra]
    return subprocess.run(command, cwd=str(ROOT), capture_output=True,
                          text=True, encoding="utf-8", errors="replace")


@pytest.mark.parametrize(
    "input_name, exit_code, fmt, ok, bad",
    [
        ("molecules.csv", 0, "csv", 5, 0),
        ("mixed_invalid.csv", 1, "csv", 1, 2),
        ("misnamed.csv", 0, "mol", 1, 0),
    ],
)
def test_demo_cli_exit_codes_and_manifest(tmp_path, input_name, exit_code, fmt, ok, bad):
    out = tmp_path / ("out_" + input_name.replace(".", "_"))
    proc = cli(out, input_name)
    assert proc.returncode == exit_code, proc.stderr
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["detection"]["format"] == fmt
    assert manifest["converted_records"] == ok
    assert manifest["failed_records"] == bad
    assert manifest["source_records"] == ok + bad
    assert (out / "original_input.bin").read_bytes() == (EXAMPLES / input_name).read_bytes()


def test_wrong_extension_is_detected_from_content_with_warning(tmp_path):
    out = tmp_path / "out_misnamed"
    assert cli(out, "misnamed.csv").returncode == 0
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["detection"]["suffix_hint"] == "csv"
    assert any("Filename suggests csv" in w for w in manifest["detection"]["warnings"])


def test_ambiguous_column_requires_explicit_choice(tmp_path):
    out_reject = tmp_path / "out_reject"
    rejected = cli(out_reject, "ambiguous_columns.csv")
    assert rejected.returncode == 2
    assert "Multiple structure columns" in rejected.stderr
    assert not out_reject.exists()

    out_ok = tmp_path / "out_ok"
    accepted = cli(out_ok, "ambiguous_columns.csv", "--column", "smiles")
    assert accepted.returncode == 0, accepted.stderr
    manifest = json.loads((out_ok / "manifest.json").read_text(encoding="utf-8"))
    assert (manifest["converted_records"], manifest["failed_records"]) == (1, 0)


def test_bad_records_are_reported_not_silently_dropped(tmp_path):
    out = tmp_path / "out_mixed"
    assert cli(out, "mixed_invalid.csv").returncode == 1
    errors = json.loads((out / "errors.json").read_text(encoding="utf-8"))
    assert len(errors) == 2
    assert "INVALID" in [item["raw"] for item in errors]
    assert all({"record_index", "raw", "error", "metadata"} <= set(item) for item in errors)
    molecules = json.loads((out / "molecules.json").read_text(encoding="utf-8"))
    assert len(molecules["molecules"]) == 1
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "partial"
    assert manifest["source_records"] == manifest["converted_records"] + manifest["failed_records"]


def test_existing_output_directory_is_never_overwritten(tmp_path):
    out = tmp_path / "out_once"
    assert cli(out, "molecules.csv").returncode == 0
    before = (out / "manifest.json").read_bytes()
    second = cli(out, "molecules.csv")
    assert second.returncode == 2
    assert "already exists" in second.stderr
    assert (out / "manifest.json").read_bytes() == before
