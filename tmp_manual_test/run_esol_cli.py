import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TMP = ROOT / "tmp_manual_test"
OUT = TMP / "esol_run"

log = (TMP / "esol_cli.log").open("w", encoding="utf-8")
started = time.perf_counter()
proc = subprocess.run(
    [sys.executable, "-m", "chembridge", str(TMP / "delaney-processed.csv"), "--out", str(OUT)],
    cwd=str(ROOT), stdout=log, stderr=subprocess.STDOUT,
)
elapsed = round(time.perf_counter() - started, 3)
log.close()

summary = {"elapsed_seconds": elapsed, "exit_code": proc.returncode}
(TMP / "esol_cli_result.json").write_text(json.dumps(summary), encoding="utf-8")
