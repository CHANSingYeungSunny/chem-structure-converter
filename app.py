"""Optional local UI. Launch: python -m streamlit run app.py"""
import io
import json
import tempfile
import zipfile
from pathlib import Path

import streamlit as st

from chembridge.io import FORMATS
from chembridge.pipeline import DEFAULT_OUTPUTS, convert_file

st.set_page_config(page_title="ChemBridge 分子格式轉換", layout="wide")
st.title("ChemBridge 分子格式轉換")
st.write("上傳結構檔案，查看偵測結果、結構圖、性質及錯誤清單，再下載轉換結果。")
st.caption("本機小分子工程原型。PDB 僅實驗性支援；圖片與 PDF 的結構辨識尚未支援。")
upload = st.file_uploader("選擇分子結構檔案（支援內容偵測，毋須正確副檔名）")
with st.expander("格式、表格欄位與輸出設定"):
    selected = st.selectbox("輸入格式", ["auto", *sorted(FORMATS)])
    column = st.text_input("CSV/TSV 分子欄位名稱（留空自動偵測）")
    rep = st.selectbox("該欄位的表示方式", ["auto", "smiles", "inchi", "selfies", "mol"])
    formats = st.multiselect("輸出格式", list(DEFAULT_OUTPUTS), default=list(DEFAULT_OUTPUTS))
    limit = st.number_input("最多繪製多少個分子", 0, 5000, 100)
    allow_pdb = st.checkbox("允許實驗性 PDB 匯入（需 CONECT；必須人工核對化學結構）")
if st.button("偵測並轉換", disabled=upload is None):
    st.session_state.pop("result", None)
    try:
        with tempfile.TemporaryDirectory(prefix="chembridge_") as tmp:
            root = Path(tmp)
            source = root / Path(upload.name.replace("\\", "/")).name
            source.write_bytes(upload.getvalue())
            out = root / "converted"
            manifest = convert_file(source, out, input_format=selected, column=column or None,
                                    column_format=rep, outputs=formats, image_limit=int(limit), allow_pdb=allow_pdb)
            data = json.loads((out / "molecules.json").read_text()) if (out / "molecules.json").exists() else None
            errors = json.loads((out / "errors.json").read_text())
            image_data = [p.read_bytes() for p in sorted((out / "images").glob("*.png"))[:12]]
            buffer = io.BytesIO()
            with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
                for file in sorted(out.rglob("*")):
                    if file.is_file():
                        archive.write(file, str(file.relative_to(out)))
            st.session_state["result"] = (manifest, data, errors, image_data, buffer.getvalue())
    except Exception as exc:
        st.error(str(exc))
if "result" in st.session_state:
    manifest, data, errors, image_data, zip_bytes = st.session_state["result"]
    st.write(f"格式：{manifest['detection']['format']}；成功：{manifest['converted_records']}；失敗：{manifest['failed_records']}")
    st.info(manifest["detection"]["reason"])
    for warning in manifest["detection"]["warnings"]:
        st.warning(warning)
    if image_data:
        st.image(image_data, width=240)
    if data:
        st.dataframe([{"name": m["name"], "smiles": m["smiles"], **m["properties"]} for m in data["molecules"]])
    if errors:
        st.warning("部分資料未能轉換；原文及原因已保存在 errors.json。")
        st.json(errors)
    with st.expander("執行紀錄"):
        st.json(manifest)
    st.download_button("下載全部結果 ZIP", zip_bytes, "chembridge_results.zip", "application/zip")
