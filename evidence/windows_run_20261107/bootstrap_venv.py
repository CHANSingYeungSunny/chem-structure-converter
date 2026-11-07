"""Bootstrap the Python 3.12 venv without invoking its broken pip launcher.

Why: on this Windows machine `.venv\\Scripts\\python.exe -m pip install ...`
hangs (CPU spin, no output, no downloads). The system Python 3.10 pip works,
so it installs official cp312 wheels straight into the venv's site-packages
via --target plus cross-version wheel tags. No venv interpreter is launched.

Usage:
  python bootstrap_venv.py            -> start detached worker, returns at once
  python bootstrap_venv.py --work     -> run inside the detached worker
"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SITE = ROOT / ".venv" / "Lib" / "site-packages"
LOG = HERE / "bootstrap_install.txt"
EXIT = HERE / "bootstrap_exit.txt"
PY310 = r"C:\Users\Asus\AppData\Local\Programs\Python\Python310\python.exe"


def build_env():
    env = dict(os.environ)
    for key in ("PIP_CACHE_DIR", "PIP_TARGET", "PIP_PREFIX", "PIP_TEMP_DIR",
                "PYTHONPATH", "PYTHONHOME"):
        env.pop(key, None)
    system_temp = tempfile.gettempdir().rstrip("\\/")
    env["TEMP"] = system_temp
    env["TMP"] = system_temp
    env["PYTHONUNBUFFERED"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    return env, system_temp


def work():
    env, system_temp = build_env()
    common = [
        PY310, "-u", "-m", "pip", "install",
        "--disable-pip-version-check", "--progress-bar", "off",
        "--only-binary=:all:", "--platform", "win_amd64",
        "--python-version", "3.12", "--implementation", "cp", "--abi", "cp312",
        "--target", str(SITE),
    ]
    stages = [
        ("stage1_selfies_probe",
         common + ["--no-deps", "selfies==2.2.0"]),
        ("stage2_full_requirements",
         common + ["-r", str(ROOT / "requirements-ui.txt"),
                   "-r", str(ROOT / "requirements-dev.txt")]),
    ]
    last_code = 0
    with LOG.open("w", encoding="utf-8") as log:
        log.write("PY310: " + PY310 + "\n")
        log.write("TARGET: " + str(SITE) + "\n")
        log.write("TEMP: " + system_temp + "\n")
        log.flush()
        for name, args in stages:
            log.write("\n=== " + name + " ===\n")
            log.write("COMMAND: " + " ".join(args) + "\n")
            log.flush()
            proc = subprocess.Popen(
                args, cwd=str(ROOT), env=env,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding="utf-8", errors="replace", bufsize=1,
            )
            for line in proc.stdout:
                log.write(line)
                log.flush()
            last_code = proc.wait()
            log.write(f"STAGE_EXIT_CODE={last_code}\n")
            log.flush()
    EXIT.write_text(f"{last_code}\n", encoding="utf-8")


def launch():
    flags = (
        subprocess.DETACHED_PROCESS
        | subprocess.CREATE_NEW_PROCESS_GROUP
        | getattr(subprocess, "CREATE_NO_WINDOW", 0)
    )
    proc = subprocess.Popen(
        [sys.executable, str(Path(__file__).resolve()), "--work"],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=flags,
        close_fds=True,
        cwd=str(HERE.parents[1]),
    )
    print(f"STARTED_PID={proc.pid}")
    print("RETURNING_IMMEDIATELY=1")


if __name__ == "__main__":
    if "--work" in sys.argv:
        work()
    else:
        launch()
