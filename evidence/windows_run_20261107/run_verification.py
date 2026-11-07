"""Run the Windows verification commands and persist real evidence.

Execute with the project venv:
  .venv\\Scripts\\python.exe evidence\\windows_run_20261107\\run_verification.py

Every result written here is the real stdout/stderr/exit code of a subprocess.
"""
from __future__ import annotations

import importlib.metadata as md
import json
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PY = ROOT / ".venv" / "Scripts" / "python.exe"
RUNS = ROOT / "runs"

PACKAGES = ["rdkit", "selfies", "Pillow", "streamlit", "pytest",
            "numpy", "pandas", "pyarrow", "altair", "tornado"]


def run(name: str, args: list[str]) -> dict:
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    proc = subprocess.run(
        args, cwd=str(ROOT), env=env, capture_output=True,
        text=True, encoding="utf-8", errors="replace",
    )
    return {
        "name": name,
        "command": " ".join(args),
        "exit_code": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }


def main() -> None:
    before = {p.name for p in RUNS.glob("demo_*")} if RUNS.exists() else set()

    results = [
        run("first_steps", [str(PY), "scripts/first_steps.py"]),
        run("run_demo", [str(PY), "scripts/run_demo.py"]),
        run("pytest", [str(PY), "-m", "pytest", "-q"]),
    ]

    packages = {}
    for name in PACKAGES:
        try:
            packages[name] = md.version(name)
        except md.PackageNotFoundError:
            packages[name] = None

    environment = {
        "captured_utc": datetime.now(timezone.utc).isoformat(),
        "os": platform.platform(),
        "python": sys.version,
        "python_executable": sys.executable,
        "packages": packages,
        "installation_method": (
            "System Python 3.10 pip with --target and cp312 wheel tags, because "
            ".venv\\Scripts\\python.exe -m pip install hangs on this machine. "
            "See bootstrap_install.txt for the real log."
        ),
    }
    (HERE / "environment.json").write_text(
        json.dumps(environment, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = ["# 本機 Windows 實跑命令與結果", "",
             f"擷取時間（UTC）：{environment['captured_utc']}",
             f"OS：{environment['os']}", f"Python：{sys.version.split()[0]}", ""]
    for item in results:
        lines += [f"## {item['name']}", "",
                  "```", f"COMMAND: {item['command']}", "```", "",
                  "stdout:", "```", item["stdout"].rstrip() or "(empty)", "```", "",
                  "stderr:", "```", item["stderr"].rstrip() or "(empty)", "```", "",
                  f"EXIT_CODE: {item['exit_code']}", ""]
    (HERE / "commands_and_results.md").write_text("\n".join(lines), encoding="utf-8")

    pytest_result = next(r for r in results if r["name"] == "pytest")
    (HERE / "pytest.txt").write_text(
        f"COMMAND: {pytest_result['command']}\n"
        f"{pytest_result['stdout']}"
        f"EXIT_CODE: {pytest_result['exit_code']}\n",
        encoding="utf-8")

    demo_dirs = sorted(
        (p for p in RUNS.glob("demo_*") if p.name not in before),
        key=lambda p: p.stat().st_mtime,
    )
    demo = {"demo_root": str(demo_dirs[-1]) if demo_dirs else None, "jobs": []}
    if demo_dirs:
        for name in ("molecules", "mixed_invalid", "misnamed"):
            manifest_path = demo_dirs[-1] / name / "manifest.json"
            if manifest_path.exists():
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                demo["jobs"].append({
                    "input": name,
                    "detected_format": manifest["detection"]["format"],
                    "detection_reason": manifest["detection"]["reason"],
                    "detection_method": manifest["detection"]["method"],
                    "suffix_hint": manifest["detection"]["suffix_hint"],
                    "warnings": manifest["detection"]["warnings"],
                    "source_records": manifest["source_records"],
                    "converted_records": manifest["converted_records"],
                    "failed_records": manifest["failed_records"],
                    "export_errors": manifest["export_errors"],
                    "status": manifest["status"],
                    "elapsed_seconds": manifest["elapsed_seconds"],
                    "environment": manifest["environment"],
                })
    (HERE / "demo_manifests.json").write_text(
        json.dumps(demo, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({
        "environment": environment["os"],
        "python": sys.version.split()[0],
        "commands": [{"name": r["name"], "exit_code": r["exit_code"]} for r in results],
        "demo_root": demo["demo_root"],
        "demo_jobs": [(j["input"], j["detected_format"],
                       j["converted_records"], j["failed_records"]) for j in demo["jobs"]],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
