"""Optional local UI. Launch: python -m streamlit run app.py"""
import io
import json
import tempfile
import zipfile
from pathlib import Path

import streamlit as st

from chembridge.io import FORMATS
from chembridge.pipeline import DEFAULT_OUTPUTS, convert_file
from chembridge.upload_workflow import process_upload

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

st.divider()
st.subheader("未知上傳檢查（V1：MOL / SDF / CSV / 純 SMILES）")
v1_upload = st.file_uploader("上傳待檢查檔案（以內容判斷，不信任副檔名）", key="v1_upload")
if v1_upload is not None:
    st.session_state["v1_bytes"] = v1_upload.getvalue()
    st.session_state["v1_name"] = v1_upload.name
    st.session_state.pop("v1_field", None)
    st.session_state.pop("v1_format", None)
if "v1_bytes" in st.session_state:
    v1_result = process_upload(
        st.session_state["v1_bytes"], st.session_state["v1_name"],
        selected_field=st.session_state.get("v1_field"),
        selected_format=st.session_state.get("v1_format"),
    )
    if v1_result.status == "requires_user_input":
        if v1_result.candidate_fields:
            v1_field = st.selectbox("選擇分子結構欄位", v1_result.candidate_fields)
            if st.button("使用此欄位重新檢查"):
                st.session_state["v1_field"] = v1_field
                v1_result = process_upload(
                    st.session_state["v1_bytes"], st.session_state["v1_name"],
                    selected_field=v1_field)
        elif v1_result.candidate_formats:
            v1_format = st.selectbox("選擇檔案格式", v1_result.candidate_formats)
            if st.button("使用此格式重新檢查"):
                st.session_state["v1_format"] = v1_format
                v1_result = process_upload(
                    st.session_state["v1_bytes"], st.session_state["v1_name"],
                    selected_format=v1_format)
        st.info("請選擇後按「重新檢查」；上傳內容已保留，不需重新上傳。")

    st.write(f"原始檔名：{v1_result.original_filename}"
             f"（副檔名 {v1_result.original_extension or '無'}）")
    st.write(f"狀態：{v1_result.status}；格式：{v1_result.detected_format or '未判定'}；"
             f"成功 {v1_result.successful_records}／失敗 {v1_result.failed_records}／"
             f"略過 {v1_result.skipped_records}／總計 {v1_result.total_records}")
    if v1_result.code:
        st.write(f"代碼：{v1_result.code}；{v1_result.message}")
    if v1_result.selected_structure_field:
        st.write(f"使用欄位：{v1_result.selected_structure_field}")
    if v1_result.candidate_fields:
        st.write(f"候選欄位：{', '.join(v1_result.candidate_fields)}")
    if v1_result.candidate_formats:
        st.write(f"候選格式：{', '.join(v1_result.candidate_formats)}")
    if v1_result.successful_results:
        st.write("成功結構：" + ", ".join(
            m.canonical_smiles for m in v1_result.successful_results))
    if v1_result.failed_record_details:
        st.write("失敗記錄：" + "；".join(
            f"第 {d.source_record_number} 列（{d.raw_structure_value!r}）：{d.message}"
            for d in v1_result.failed_record_details))
    if v1_result.status == "failed":
        st.error(f"{v1_result.code}: {v1_result.message}")
    for warning in v1_result.warnings:
        st.warning(warning)
    st.json(v1_result.to_dict())
