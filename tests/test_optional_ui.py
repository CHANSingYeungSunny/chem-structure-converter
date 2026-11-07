import importlib.util
from pathlib import Path

import pytest


@pytest.mark.skipif(importlib.util.find_spec("streamlit") is None, reason="Optional UI dependency not installed")
def test_ui_initial_and_result_views():
    from streamlit.testing.v1 import AppTest

    # Windows 11 / Python 3.12.14 / streamlit 1.51.0: the second AppTest run
    # takes ~5.2 s here, so the 3 s default produced a spurious timeout.
    # Measured with evidence/windows_run_20261107/diagnose_apptest.py.
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py")).run(timeout=30)
    assert not app.exception
    assert app.title[0].value == "ChemBridge 分子格式轉換"
    manifest = {"detection": {"format": "smiles", "reason": "test fixture", "warnings": []},
                "converted_records": 1, "failed_records": 0}
    data = {"molecules": [{"name": "ethanol", "smiles": "CCO", "properties": {"hbd": 1}}]}
    app.session_state["result"] = (manifest, data, [], [], b"test zip fixture")
    app.run(timeout=30)
    assert not app.exception
    assert len(app.dataframe) == 1
