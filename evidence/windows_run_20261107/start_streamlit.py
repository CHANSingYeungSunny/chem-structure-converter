"""Start the local Streamlit UI detached for real-browser acceptance testing."""
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PY = ROOT / ".venv" / "Scripts" / "python.exe"
LOG = HERE / "streamlit_server.txt"
PID = HERE / "streamlit_pid.txt"

args = [str(PY), "-m", "streamlit", "run", "app.py",
        "--server.address", "127.0.0.1", "--server.port", "8501",
        "--server.headless", "true",
        "--browser.gatherUsageStats", "false"]

flags = (
    subprocess.DETACHED_PROCESS
    | subprocess.CREATE_NEW_PROCESS_GROUP
    | getattr(subprocess, "CREATE_NO_WINDOW", 0)
)

handle = LOG.open("wb")
proc = subprocess.Popen(
    args, cwd=str(ROOT), stdin=subprocess.DEVNULL,
    stdout=handle, stderr=subprocess.STDOUT,
    creationflags=flags, close_fds=True,
)
PID.write_text(str(proc.pid), encoding="utf-8")
print("STARTED_PID=" + str(proc.pid))
print("URL=http://127.0.0.1:8501")
