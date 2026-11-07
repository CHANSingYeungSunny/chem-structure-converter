"""Focused Streamlit AppTest coverage for the V1 unknown-upload section.

This is programmatic UI verification (Streamlit AppTest), NOT a real browser
test. No browser automation is claimed here.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("streamlit") is None,
    reason="Optional UI dependency not installed")

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app.py"
MOL = (ROOT / "examples" / "ethanol.mol").read_bytes()
INCHI = "InChI=1S/C2H6O/c1-2-3/h3H,2H2,1H3"


def _new_app():
    from streamlit.testing.v1 import AppTest
    return AppTest.from_file(str(APP)).run(timeout=30)


def _upload(app, data: bytes, name: str):
    app.session_state["v1_bytes"] = data
    app.session_state["v1_name"] = name
    app.run(timeout=30)
    assert not app.exception
    return app


def _text(app) -> str:
    return "\n".join(
        [m.value for m in app.markdown]
        + [e.value for e in app.error]
        + [w.value for w in app.warning]
    )


def test_v1_ui_success_csv_shows_format_counts_and_results():
    app = _upload(_new_app(), b"id,smiles\n1,CCO\n2,CCN\n", "molecules.csv")
    text = _text(app)
    assert "success" in text
    assert "csv" in text
    assert "成功 2" in text
    assert "CCO" in text and "CCN" in text


def test_v1_ui_partial_success_shows_failed_row_and_raw_value():
    app = _upload(_new_app(), b"id,smiles\n1,CCO\n2,INVALID\n", "mixed.csv")
    text = _text(app)
    assert "partial_success" in text
    assert "成功 1" in text
    assert "第 3 列" in text
    assert "INVALID" in text
    assert "CCO" in text  # successful record preserved


def test_v1_ui_multiple_fields_offers_selection_and_resumes_without_reupload():
    data = f'name,smiles,inchi\nethanol,CCO,"{INCHI}"\n'.encode()
    app = _upload(_new_app(), data, "two_columns.csv")
    text = _text(app)
    assert "requires_user_input" in text
    assert "MULTIPLE_STRUCTURE_FIELDS" in text
    assert "smiles" in text and "inchi" in text
    selectors = [s for s in app.selectbox if s.label == "選擇分子結構欄位"]
    assert len(selectors) == 1
    assert set(selectors[0].options) == {"smiles", "inchi"}
    assert any(b.label == "使用此欄位重新檢查" for b in app.button)

    # Click the real resume button; the file must NOT be uploaded again.
    original_bytes = app.session_state["v1_bytes"]
    resume_button = next(b for b in app.button if b.label == "使用此欄位重新檢查")
    app = resume_button.click().run(timeout=30)
    assert not app.exception
    assert app.session_state["v1_bytes"] == original_bytes
    assert "success" in _text(app)
    assert "使用欄位" in _text(app)
    assert "smiles" in _text(app)

    # A later rerun keeps the selection through st.session_state.
    app.run(timeout=30)
    assert not app.exception
    assert "success" in _text(app)
    assert "smiles" in _text(app)


def test_v1_ui_extension_mismatch_shows_warning_and_preserves_filename():
    app = _upload(_new_app(), MOL, "mislabelled.csv")
    text = _text(app)
    assert "success" in text
    assert "mol" in text
    assert "EXTENSION_CONTENT_MISMATCH" in text
    assert "mislabelled.csv" in text
    assert "副檔名 csv" in text


@pytest.mark.parametrize("data,name,code", [
    (b"", "empty.csv", "EMPTY_OR_UNREADABLE_FILE"),
    (b"this is not chemistry at all\n", "notes.txt", "UNSUPPORTED_OR_UNKNOWN_FORMAT"),
])
def test_v1_ui_empty_or_unsupported_shows_concise_error(data, name, code):
    app = _upload(_new_app(), data, name)
    text = _text(app)
    assert code in text
    assert "Traceback" not in text
    assert "File \"" not in text
    assert not app.exception
