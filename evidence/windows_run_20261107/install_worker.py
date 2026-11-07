"""Background pip worker for the Windows verification run.

Streams pip output line-by-line into pip_install.txt, then writes the real
process exit code to pip_exit_code.txt. Uses the system temp directory so the
earlier project-local .tmp permission failure cannot recur.
"""
import os
import subprocess
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PY = ROOT / ".venv" / "Scripts" / "python.exe"
LOG = HERE / "pip_install.txt"
EXIT = HERE / "pip_exit_code.txt"

args = [
    str(PY), "-u", "-m", "pip", "install",
    "--disable-pip-version-check", "--progress-bar", "off",
    "-r", str(ROOT / "requirements-ui.txt"),
    "-r", str(ROOT / "requirements-dev.txt"),
]

env = dict(os.environ)
for key in ("PIP_CACHE_DIR", "PIP_TARGET", "PIP_PREFIX", "PIP_TEMP_DIR"):
    env.pop(key, None)
system_temp = tempfile.gettempdir().rstrip("\\/")
env["TEMP"] = system_temp
env["TMP"] = system_temp
env["PYTHONUNBUFFERED"] = "1"
env["PYTHONIOENCODING"] = "utf-8"

with LOG.open("w", encoding="utf-8") as log:
    log.write("COMMAND: " + " ".join(args) + "\n")
    log.write("TEMP: " + system_temp + "\n")
    log.flush()
    proc = subprocess.Popen(
        args,
        cwd=str(ROOT),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
    )
    for line in proc.stdout:
        log.write(line)
        log.flush()
    code = proc.wait()
    log.write(f"EXIT_CODE={code}\n")

EXIT.write_text(f"{code}\n", encoding="utf-8")
