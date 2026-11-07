"""Build the acceptance set, run convert_file, and write the matrix workbook.

Run with the project venv:
  .venv\\Scripts\\python.exe evidence\\windows_run_20261107\\build_acceptance.py

All samples are public PubChem SDFs or synthetic boundary files. They are NOT
real user uploads; no real-world accuracy may be inferred from this matrix.
"""
from __future__ import annotations

import csv
import gzip
import io
import json
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
from rdkit import Chem
from rdkit.Chem import AllChem

from chembridge import convert_file
from chembridge.io import InputError, detect, load_text

ACC = ROOT / "examples" / "acceptance"
BOUND = ACC / "boundary"
EX = ROOT / "examples"
RUN = ROOT / "runs" / ("acceptance_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
OUTPUTS = "csv,json,mol,sdf,smi,inchi,selfies"
NA = "NA"


def make_samples() -> None:
    BOUND.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(EX / "misnamed.csv", BOUND / "B01_wrong_extension.csv")
    (BOUND / "B02_missing_structure_column.csv").write_text(
        "id,name\n1,water\n2,ethanol\n", encoding="utf-8")
    shutil.copyfile(EX / "ambiguous_columns.csv", BOUND / "B03_multiple_structure_columns.csv")
    (BOUND / "B04_missing_value.csv").write_text(
        "id,smiles\nA,CCO\nB,\nC,INVALID\n", encoding="utf-8")
    (BOUND / "B05_invalid_valence.csv").write_text(
        "id,smiles\n1,C(C)(C)(C)(C)C\n", encoding="utf-8")
    (BOUND / "B06_salt_charge.csv").write_text(
        "id,smiles\n1,[Na+].[Cl-]\n", encoding="utf-8")
    (BOUND / "B07_stereo.csv").write_text(
        "id,smiles\n1,C[C@H](O)CC\n", encoding="utf-8")
    (BOUND / "B08_isotope.csv").write_text(
        "id,smiles\n1,[13CH4]\n", encoding="utf-8")

    m3d = Chem.AddHs(Chem.MolFromSmiles("CC(C)Cc1ccc(cc1)C(C)C(=O)O"))
    AllChem.EmbedMolecule(m3d, randomSeed=0xF00D)
    AllChem.MMFFOptimizeMolecule(m3d)
    m3d.SetProp("SOURCE", "synthetic 3D")
    writer = Chem.SDWriter(str(BOUND / "B09_3d_coords.sdf"))
    writer.write(m3d)
    writer.close()

    meta = Chem.MolFromSmiles("CCO")
    meta.SetProp("SOURCE", "synthetic acceptance case")
    writer = Chem.SDWriter(str(BOUND / "B10_sdf_metadata.sdf"))
    writer.write(meta)
    writer.close()

    shutil.copyfile(EX / "water.mol2", BOUND / "B11_mol2_tripos.mol2")
    (BOUND / "B12_xyz_unsupported.xyz").write_text(
        "3\nwater\nO 0.0 0.0 0.0\nH 0.76 0.0 0.0\nH -0.76 0.0 0.0\n", encoding="utf-8")
    (BOUND / "B13_pdb_no_optin.pdb").write_text(
        "HETATM    1  O1  UNL     1       0.000   0.000   0.000  1.00  0.00           O\n"
        "CONECT    1\nEND\n", encoding="utf-8")
    (BOUND / "B14_gzip.sdf.gz").write_bytes(gzip.compress((EX / "molecules.sdf").read_bytes()))
    shutil.copyfile(EX / "molecules.inchi", BOUND / "B15_inchi.txt")
    shutil.copyfile(EX / "molecules.selfies", BOUND / "B16_selfies.selfies")


def case(cid, file, source, category, fmt, outcome, ok, bad, features, column=None):
    return {"id": cid, "file": file, "source": source, "category": category,
            "expected_format": fmt, "expected_outcome": outcome,
            "expected_ok": ok, "expected_bad": bad,
            "features": features, "column": column}


CASES = [
    case("P01", "examples/acceptance/pubchem_cid_702_2d.sdf", "PubChem CID 702 (ethanol)", "public", "sdf", "accept", 1, 0, {"metadata": 1}),
    case("P02", "examples/acceptance/pubchem_cid_1983_2d.sdf", "PubChem CID 1983 (caffeine)", "public", "sdf", "accept", 1, 0, {"metadata": 1}),
    case("P03", "examples/acceptance/pubchem_cid_2244_2d.sdf", "PubChem CID 2244 (aspirin)", "public", "sdf", "accept", 1, 0, {"metadata": 1}),
    case("P04", "examples/acceptance/pubchem_cid_3672_2d.sdf", "PubChem CID 3672 (ibuprofen)", "public", "sdf", "accept", 1, 0, {"metadata": 1}),
    case("B01", "examples/acceptance/boundary/B01_wrong_extension.csv", "合成：MOL 内容配上 .csv 档名", "boundary", "mol", "accept", 1, 0, {}),
    case("B02", "examples/acceptance/boundary/B02_missing_structure_column.csv", "合成：表格无结构栏", "boundary", "csv", "reject", None, None, {}),
    case("B03", "examples/acceptance/boundary/B03_multiple_structure_columns.csv", "合成：两个结构栏", "boundary", "csv", "reject", None, None, {}),
    case("B04", "examples/acceptance/boundary/B04_missing_value.csv", "合成：缺值与坏字串", "boundary", "csv", "partial", 1, 2, {}),
    case("B05", "examples/acceptance/boundary/B05_invalid_valence.csv", "合成：五价碳无效价态", "boundary", "csv", "partial", 0, 1, {}),
    case("B06", "examples/acceptance/boundary/B06_salt_charge.csv", "合成：盐与形式电荷", "boundary", "csv", "accept", 1, 0, {"charge": 1, "fragments": 1}),
    case("B07", "examples/acceptance/boundary/B07_stereo.csv", "合成：立体化学", "boundary", "csv", "accept", 1, 0, {"stereo": 1}),
    case("B08", "examples/acceptance/boundary/B08_isotope.csv", "合成：同位素", "boundary", "csv", "accept", 1, 0, {"isotope": 1}),
    case("B09", "examples/acceptance/boundary/B09_3d_coords.sdf", "合成：RDKit 生成 3D 座标", "boundary", "sdf", "accept", 1, 0, {"coords3d": 1, "metadata": 1}),
    case("B10", "examples/acceptance/boundary/B10_sdf_metadata.sdf", "合成：SDF SOURCE 属性", "boundary", "sdf", "accept", 1, 0, {"metadata": 1}),
    case("B11", "examples/acceptance/boundary/B11_mol2_tripos.mol2", "合成：标准 TRIPOS MOL2 水分子", "boundary", "mol2", "accept", 1, 0, {}),
    case("B12", "examples/acceptance/boundary/B12_xyz_unsupported.xyz", "合成：不支援的 XYZ", "boundary", "reject", "reject", None, None, {}),
    case("B13", "examples/acceptance/boundary/B13_pdb_no_optin.pdb", "合成：PDB 未显式允许", "boundary", "pdb", "reject", None, None, {}),
    case("B14", "examples/acceptance/boundary/B14_gzip.sdf.gz", "合成：上游 SDF 的 gzip 版本", "boundary", "sdf", "accept", 2, 0, {"metadata": 1}),
    case("B15", "examples/acceptance/boundary/B15_inchi.txt", "合成：上游 InChI 文字", "boundary", "inchi", "accept", 1, 0, {}),
    case("B16", "examples/acceptance/boundary/B16_selfies.selfies", "合成：上游 SELFIES 文字", "boundary", "selfies", "accept", 1, 0, {}),
    case("E01", "examples/molecules.csv", "上游合成范例：5 分子 CSV", "project", "csv", "accept", 5, 0, {}),
    case("E02", "examples/mixed_invalid.csv", "上游合成范例：混合坏资料", "project", "csv", "partial", 1, 2, {}),
    case("E03", "examples/ambiguous_columns.csv", "上游合成范例：指定 smiles 栏", "project", "csv", "accept", 1, 0, {}, "smiles"),
]


def reference_keys(path: Path, fmt: str, column=None):
    """Independently parse the ORIGINAL input with RDKit (not via chembridge)."""
    if str(path).endswith(".gz"):
        return None, "gzip 输入未由独立 reader 解析"
    text = load_text(path)
    keys = []
    if fmt in ("csv", "tsv"):
        first = next((ln for ln in text.splitlines() if ln.strip()), "")
        delim = "\t" if "\t" in first else ";" if ";" in first else ","
        rows = list(csv.reader(io.StringIO(text), delimiter=delim))
        header = [h.strip().lower() for h in rows[0]]
        idx = header.index(column.lower()) if column else next(
            (i for i, h in enumerate(header) if h in ("smiles", "canonicalsmiles", "isomericsmiles")), None)
        if idx is None:
            return None, "无法独立判定结构栏"
        for row in rows[1:]:
            value = row[idx].strip() if len(row) > idx else ""
            mol = Chem.MolFromSmiles(value) if value else None
            if mol:
                keys.append(Chem.MolToInchiKey(mol))
    elif fmt == "sdf":
        for mol in Chem.SDMolSupplier(str(path), removeHs=True):
            if mol:
                keys.append(Chem.MolToInchiKey(mol))
    elif fmt == "mol":
        mol = Chem.MolFromMolBlock(text, removeHs=True)
        if mol:
            keys.append(Chem.MolToInchiKey(mol))
    elif fmt == "inchi":
        for line in text.splitlines():
            token = line.strip().split()[0] if line.strip() else ""
            mol = Chem.MolFromInchi(token) if token.startswith("InChI=") else None
            if mol:
                keys.append(Chem.MolToInchiKey(mol))
    elif fmt == "mol2":
        mol = Chem.MolFromMol2Block(text, removeHs=True)
        if mol:
            keys.append(Chem.MolToInchiKey(mol))
    elif fmt == "selfies":
        import selfies as sf
        for line in text.splitlines():
            token = line.strip().split()[0] if line.strip() else ""
            try:
                mol = Chem.MolFromSmiles(sf.decoder(token)) if token.startswith("[") else None
            except Exception:
                mol = None
            if mol:
                keys.append(Chem.MolToInchiKey(mol))
    else:
        return None, f"格式 {fmt} 未纳入独立 reader"
    return (sorted(keys) or None), ""


def readback_keys(out_dir: Path):
    keys = []
    for path in sorted((out_dir / "mol").glob("*.mol")):
        mol = Chem.MolFromMolFile(str(path), removeHs=True)
        if mol:
            keys.append(Chem.MolToInchiKey(mol))
    return sorted(keys) or None


def sdf_features(path: Path, out_dir: Path, features: dict):
    metadata = NA
    coords = NA
    if str(path).endswith(".gz") or not path.suffix == ".sdf":
        return metadata, coords
    supplier = Chem.SDMolSupplier(str(path), removeHs=False)
    if not len(supplier) or supplier[0] is None:
        return metadata, coords
    mol = supplier[0]
    if features.get("metadata"):
        props = {k for k in mol.GetPropsAsDict() if not k.startswith("_")}
        data = json.loads((out_dir / "molecules.json").read_text(encoding="utf-8"))
        out_meta = set(data["molecules"][0].get("metadata", {}))
        metadata = 1 if props and props & out_meta else 0
    if features.get("coords3d") and mol.GetNumConformers() and mol.GetConformer().Is3D():
        back = Chem.MolFromMolFile(str(out_dir / "mol" / "m00001.mol"), removeHs=False)
        coords = 1 if back and back.GetNumConformers() and back.GetConformer().Is3D() else 0
    return metadata, coords


def evaluate(item: dict) -> dict:
    path = ROOT / item["file"]
    out_dir = RUN / item["id"]
    rejected, error = False, ""
    manifest = None
    started = time.perf_counter()
    try:
        kwargs = {"outputs": OUTPUTS}
        if item["column"]:
            kwargs["column"] = item["column"]
        manifest = convert_file(path, out_dir, **kwargs)
    except InputError as exc:
        rejected, error = True, str(exc)
    except Exception as exc:
        rejected, error = True, f"{type(exc).__name__}: {exc}"
    wall = round(time.perf_counter() - started, 4)

    try:
        det = detect(load_text(path), path.name)
        detected, method, warnings = det.format, det.method, det.warnings
    except InputError as exc:
        detected, method, warnings = "detect_rejected", "signature", [str(exc)]

    fmt = item["expected_format"]
    outcome = item["expected_outcome"]
    ok = manifest["converted_records"] if manifest else 0
    bad = manifest["failed_records"] if manifest else 0
    status = manifest["status"] if manifest else "rejected"

    format_correct = NA if fmt == "reject" else int(detected == fmt)
    refusal_correct = NA if outcome != "reject" else int(rejected)
    read_success = NA if outcome == "reject" else int(
        ok == item["expected_ok"] and bad == item["expected_bad"] and not rejected)
    false_accept = 1 if (outcome == "reject" and not rejected) else (
        1 if (item["expected_bad"] and bad < item["expected_bad"]) else 0)

    roundtrip, exclusion = NA, ""
    metadata_ret, coords_ret = NA, NA
    if manifest and ok > 0:
        ref, why = reference_keys(path, detected if detected != "detect_rejected" else fmt, item["column"])
        back = readback_keys(out_dir)
        if ref is None or back is None:
            exclusion = why or "无输出 MOL 可回读"
        else:
            roundtrip = int(ref == back)
        metadata_ret, coords_ret = sdf_features(path, out_dir, item["features"])
    else:
        exclusion = "拒绝或无成功分子，不列入往返／保留维度分母"

    return {
        "id": item["id"], "file": item["file"], "source": item["source"],
        "category": item["category"], "expected_format": fmt,
        "expected_outcome": outcome, "expected_ok": item["expected_ok"],
        "expected_bad": item["expected_bad"], "features": item["features"],
        "detected_format": detected, "detection_method": method,
        "warnings": warnings, "outcome": "reject" if rejected else status,
        "converted": ok, "failed": bad,
        "source_records": manifest["source_records"] if manifest else None,
        "error": error,
        "elapsed_seconds": manifest["elapsed_seconds"] if manifest else wall,
        "format_correct": format_correct, "refusal_correct": refusal_correct,
        "read_success": read_success, "false_accept": false_accept,
        "roundtrip": roundtrip, "metadata_retained": metadata_ret,
        "coords_retained": coords_ret, "exclusion": exclusion,
    }


def write_workbook(results: list[dict], path: Path) -> None:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "逐案结果"
    headers = ["案例ID", "档案", "来源", "来源类别", "预期格式", "预期结果",
               "预期成功数", "预期失败数", "实际侦测格式", "侦测方法", "实际结果",
               "实际成功数", "实际失败数", "格式识别正确", "拒绝正确", "读取成功",
               "误接受", "输入→输出化学图一致", "metadata 保留", "3D 座标保留",
               "耗时(秒)", "排除／备注", "警告"]
    ws.append(headers)
    for r in results:
        ws.append([r["id"], r["file"], r["source"], r["category"],
                   r["expected_format"], r["expected_outcome"],
                   r["expected_ok"] if r["expected_ok"] is not None else NA,
                   r["expected_bad"] if r["expected_bad"] is not None else NA,
                   r["detected_format"], r["detection_method"], r["outcome"],
                   r["converted"], r["failed"],
                   r["format_correct"], r["refusal_correct"], r["read_success"],
                   r["false_accept"], r["roundtrip"], r["metadata_retained"],
                   r["coords_retained"], r["elapsed_seconds"],
                   r["exclusion"] or "-", "; ".join(r["warnings"]) or "-"])

    header_fill = PatternFill("solid", start_color="D9E2F3")
    for cell in ws[1]:
        cell.font = Font(name="Arial", bold=True)
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    for row in ws.iter_rows(min_row=2):
        for cell in row:
            cell.font = Font(name="Arial")
    widths = [10, 46, 34, 12, 12, 12, 12, 12, 16, 12, 12, 12, 12,
              14, 12, 12, 10, 20, 16, 16, 12, 44, 50]
    for idx, width in enumerate(widths, 1):
        ws.column_dimensions[openpyxl.utils.get_column_letter(idx)].width = width
    ws.freeze_panes = "A2"

    last = len(results) + 1
    summary = wb.create_sheet("汇总")
    summary.append(["维度", "分母", "通过数", "比率／结果", "说明"])
    dimensions = [
        ("格式识别正确率", "N", f"=COUNT('逐案结果'!N2:N{last})",
         f"=SUM('逐案结果'!N2:N{last})",
         f'=IF(COUNT(\'逐案结果\'!N2:N{last})=0,"NA",SUM(\'逐案结果\'!N2:N{last})/COUNT(\'逐案结果\'!N2:N{last}))',
         "只计预期格式可判定的档案；预期拒绝格式不明者记 NA 排除"),
        ("拒绝／歧义正确率", "O", f"=COUNT('逐案结果'!O2:O{last})",
         f"=SUM('逐案结果'!O2:O{last})",
         f'=IF(COUNT(\'逐案结果\'!O2:O{last})=0,"NA",SUM(\'逐案结果\'!O2:O{last})/COUNT(\'逐案结果\'!O2:O{last}))',
         "只计预期应拒绝的档案"),
        ("读取成功率", "P", f"=COUNT('逐案结果'!P2:P{last})",
         f"=SUM('逐案结果'!P2:P{last})",
         f'=IF(COUNT(\'逐案结果\'!P2:P{last})=0,"NA",SUM(\'逐案结果\'!P2:P{last})/COUNT(\'逐案结果\'!P2:P{last}))',
         "只计预期接受的档案；成功数与失败数都须符合人工标注"),
        ("误接受数", "Q", f"=COUNT('逐案结果'!Q2:Q{last})",
         f"=SUM('逐案结果'!Q2:Q{last})",
         f"=SUM('逐案结果'!Q2:Q{last})",
         "越低越好；预期拒绝却接受，或预期坏资料被当成成功"),
        ("输入→输出化学图一致率", "R", f"=COUNT('逐案结果'!R2:R{last})",
         f"=SUM('逐案结果'!R2:R{last})",
         f'=IF(COUNT(\'逐案结果\'!R2:R{last})=0,"NA",SUM(\'逐案结果\'!R2:R{last})/COUNT(\'逐案结果\'!R2:R{last}))',
         "以独立 RDKit reader 的 InChIKey 比对输出 MOL；不可独立解析者排除"),
        ("metadata 保留率", "S", f"=COUNT('逐案结果'!S2:S{last})",
         f"=SUM('逐案结果'!S2:S{last})",
         f'=IF(COUNT(\'逐案结果\'!S2:S{last})=0,"NA",SUM(\'逐案结果\'!S2:S{last})/COUNT(\'逐案结果\'!S2:S{last}))',
         "只计含 SDF 属性的样本"),
        ("3D 座标保留率", "T", f"=COUNT('逐案结果'!T2:T{last})",
         f"=SUM('逐案结果'!T2:T{last})",
         f'=IF(COUNT(\'逐案结果\'!T2:T{last})=0,"NA",SUM(\'逐案结果\'!T2:T{last})/COUNT(\'逐案结果\'!T2:T{last}))',
         "只计含 3D conformer 的样本"),
    ]
    for name, _, denom, passed, ratio, note in dimensions:
        summary.append([name, denom, passed, ratio, note])
    summary.append(["耗时 p50 (秒)", f"=COUNT('逐案结果'!U2:U{last})", NA,
                    f"=MEDIAN('逐案结果'!U2:U{last})", "manifest.elapsed_seconds"])
    summary.append(["耗时 p95 (秒)", f"=COUNT('逐案结果'!U2:U{last})", NA,
                    f"=PERCENTILE('逐案结果'!U2:U{last},0.95)", "manifest.elapsed_seconds"])
    for cell in summary[1]:
        cell.font = Font(name="Arial", bold=True)
        cell.fill = header_fill
    for row in summary.iter_rows(min_row=2):
        for cell in row:
            cell.font = Font(name="Arial")
    for col, width in zip("ABCDE", [26, 14, 14, 18, 66]):
        summary.column_dimensions[col].width = width

    notes = wb.create_sheet("说明与限制")
    lines = [
        ["ChemBridge 验收表 — 重要声明"],
        [""],
        ["本表档案不是使用者实际上传的真实工作资料，来自公开资料库与人工合成边界案例。"],
        ["不得据此宣称真实世界格式辨识准确率、误接受率或化学保真率，也不代表真实上传分布。"],
        [""],
        [f"产生时间(UTC)：{datetime.now(timezone.utc).isoformat()}"],
        [f"OS：Windows 11 / Python 3.12.14 / rdkit 2025.9.4 / selfies 2.2.0"],
        [f"工具版本：ChemBridge 0.1.0；convert_file 为唯一化学逻辑边界"],
        [f"样本总数（分母）：{len(results)} 个档案；公开 PubChem {sum(1 for r in results if r['category']=='public')} 个、"
         f"合成边界 {sum(1 for r in results if r['category']=='boundary')} 个、上游合成范例 {sum(1 for r in results if r['category']=='project')} 个"],
        [""],
        ["分母与排除规则"],
        ["1. 每笔以「档案」为分母单位；多笔 SDF 的分子数另计，不混为独立格式档数。"],
        ["2. 预期拒绝的样本不计入读取成功率；预期接受的样本不计入拒绝率；不适用维度记 NA 且不计入该维度分母。"],
        ["3. 往返一致性以独立 RDKit reader 从原始档算 InChIKey，与输出 mol/*.mol 回读的 InChIKey 比对；"],
        ["   不是原始档逐位元相同，也不是字串相同。gzip / 无法独立解析的格式记 NA 排除。"],
        ["4. 验收输出刻意不含 PNG/SVG（聚焦化学图往返），图片证据另见 demo 与真实浏览器截图。"],
        ["5. 固定单元测试 46 passed 只是回归检查，与本表任何比率无关，不得混用。"],
        ["6. 不含私人资料、使用者上传档、实验测量值或任何模型预测值。"],
        [""],
        ["资讯损失与未评估范围"],
        ["- 标准 InChIKey 可能正规化互变异构／质子化状态，一致性不等于完整化学身分保真。"],
        ["- SMILES/InChI/SELFIES 不保存 3D 座标；SDF/MOL 只在本表所列样本验证座标保留。"],
        ["- MOL2 仅验证一个标准 TRIPOS 水分子，不能推论各供应商 MOL2、力场或部分电荷资讯保留。"],
        ["- XYZ/PDBQT/CIF/CML/CDX/结构图片/扫描 PDF 仍未支援；PDB 仅在显式允许且需人工核键级时实验性读取。"],
        ["- 未评估大于 20 MiB／5000 笔的上限行为、任意供应商 JSON schema、大分子与蛋白质。"],
        [""],
        ["公式重算限制"],
        ["- 本机无 LibreOffice，xlsx 技能的 recalc.py 在 Windows 因 socket.AF_UNIX 不存在而无法执行，公式快取值未重算。"],
        ["- 汇总页比率／分母为 Excel 公式，以 Excel 开启时自动重算为准；独立核对值见 docs/ACCEPTANCE_MATRIX_zh.md。"],
    ]
    for line in lines:
        notes.append(line)
    notes["A1"].font = Font(name="Arial", bold=True, size=13)
    for row in notes.iter_rows(min_row=2):
        for cell in row:
            cell.font = Font(name="Arial")
    notes.column_dimensions["A"].width = 110
    wb.save(path)


def main() -> None:
    make_samples()
    results = [evaluate(item) for item in CASES]
    (HERE / "acceptance_results.json").write_text(
        json.dumps({"generated_utc": datetime.now(timezone.utc).isoformat(),
                    "run_root": str(RUN), "cases": results},
                   ensure_ascii=False, indent=2), encoding="utf-8")
    write_workbook(results, ROOT / "evidence" / "acceptance_matrix.xlsx")
    counts = {key: sum(1 for r in results if r[key] == 1)
              for key in ("format_correct", "refusal_correct", "read_success",
                          "false_accept", "roundtrip", "metadata_retained", "coords_retained")}
    print("ACCEPTANCE_OK " + json.dumps({
        "cases": len(results), "counts": counts,
        "xlsx": str(ROOT / "evidence" / "acceptance_matrix.xlsx"),
        "run_root": str(RUN),
    }))


if __name__ == "__main__":
    main()
