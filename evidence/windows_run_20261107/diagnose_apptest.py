"""Diagnose the Windows AppTest timeout with an explicit longer timeout."""
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from streamlit.testing.v1 import AppTest

APP = ROOT / "app.py"
MANIFEST = {"detection": {"format": "smiles", "reason": "test fixture", "warnings": []},
            "converted_records": 1, "failed_records": 0}
DATA = {"molecules": [{"name": "ethanol", "smiles": "CCO", "properties": {"hbd": 1}}]}

app = AppTest.from_file(str(APP)).run(timeout=30)
print("first_run_exception", [str(e) for e in app.exception])
print("first_run_title", app.title[0].value)

app.session_state["result"] = (MANIFEST, DATA, [], [], b"test zip fixture")
started = time.time()
app.run(timeout=30)
print("second_run_elapsed_seconds", round(time.time() - started, 2))
print("second_run_exception", [str(e) for e in app.exception])
print("dataframe_count", len(app.dataframe))
print("json_count", len(app.json))
