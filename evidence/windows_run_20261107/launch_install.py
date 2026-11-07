"""Start install_worker.py fully detached so this command returns immediately.

Detached process + DEVNULL handles are required: otherwise the calling tool
keeps waiting on inherited stdout/stderr pipes and appears to hang.
"""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORKER = HERE / "install_worker.py"

flags = (
    subprocess.DETACHED_PROCESS
    | subprocess.CREATE_NEW_PROCESS_GROUP
    | getattr(subprocess, "CREATE_NO_WINDOW", 0)
)

proc = subprocess.Popen(
    [sys.executable, str(WORKER)],
    stdin=subprocess.DEVNULL,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
    creationflags=flags,
    close_fds=True,
    cwd=str(HERE.parents[1]),
)

print(f"STARTED_PID={proc.pid}")
print("RETURNING_IMMEDIATELY=1")
