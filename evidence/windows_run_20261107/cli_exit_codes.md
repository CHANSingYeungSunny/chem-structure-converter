# CLI 边界复验（本机 Windows 真实命令）

执行时间：2026-11-08T00:13:34.874208
输出根目录：`C:\Users\Asus\Desktop\Chembridge\chembridge_mvp\runs\cli_checks_20261108_001321`

说明：`mixed_invalid.csv` 的 exit 1 是设计结果（仍有完整报告），**未改成假成功**。

## molecules.csv（全部成功）

```
C:\Users\Asus\Desktop\Chembridge\chembridge_mvp\.venv\Scripts\python.exe -m chembridge C:\Users\Asus\Desktop\Chembridge\chembridge_mvp\examples\molecules.csv --out C:\Users\Asus\Desktop\Chembridge\chembridge_mvp\runs\cli_checks_20261108_001321\molecules
```

EXIT_CODE: 0

stdout（节录）：
```
{
  "schema": "chembridge.run.v1",
  "tool_version": "0.1.0",
  "status": "complete",
  "created_utc": "2026-11-07T16:13:23.408933+00:00",
  "input_name": "molecules.csv",
  "input_sha256": "8f6f514d71bae76198cf04670c316aa9b730c79726271c5d5c4c984d893d9a4c",
  "detection": {
    "format": "csv",
    "reason": "Delimited table; structure column must be resolved.",
    "method": "signature",
    "suffix_hint": "csv",
    "warnings": []
  },
  "source_records": 5,
  "converted_records": 5,
  "failed_records": 0,
  "export_errors": 0,
  "elapsed_seconds": 0.7421,
  "requested_outputs": [
    "csv",
```

stderr：
```
(empty)
```

manifest 关键栏位：
```json
{"format": "csv", "method": "signature", "suffix_hint": "csv", "warnings": [], "source_records": 5, "converted_records": 5, "failed_records": 0, "status": "complete"}
```

`errors.json` 笔数：0；索引：[]；原文：[]

## mixed_invalid.csv（部分失败）

```
C:\Users\Asus\Desktop\Chembridge\chembridge_mvp\.venv\Scripts\python.exe -m chembridge C:\Users\Asus\Desktop\Chembridge\chembridge_mvp\examples\mixed_invalid.csv --out C:\Users\Asus\Desktop\Chembridge\chembridge_mvp\runs\cli_checks_20261108_001321\mixed_invalid
```

EXIT_CODE: 1

stdout（节录）：
```
{
  "schema": "chembridge.run.v1",
  "tool_version": "0.1.0",
  "status": "partial",
  "created_utc": "2026-11-07T16:13:28.225271+00:00",
  "input_name": "mixed_invalid.csv",
  "input_sha256": "3ac4ae3bbf99ca5b941eb62dde43bfe96a5c97406297589776a33a7c07f3afd3",
  "detection": {
    "format": "csv",
    "reason": "Delimited table; structure column must be resolved.",
    "method": "signature",
    "suffix_hint": "csv",
    "warnings": []
  },
  "source_records": 3,
  "converted_records": 1,
  "failed_records": 2,
  "export_errors": 0,
  "elapsed_seconds": 0.692,
  "requested_outputs": [
    "csv
```

stderr：
```
(empty)
```

manifest 关键栏位：
```json
{"format": "csv", "method": "signature", "suffix_hint": "csv", "warnings": [], "source_records": 3, "converted_records": 1, "failed_records": 2, "status": "partial"}
```

`errors.json` 笔数：2；索引：[3, 4]；原文：['INVALID', '']

## misnamed.csv（错副档名）

```
C:\Users\Asus\Desktop\Chembridge\chembridge_mvp\.venv\Scripts\python.exe -m chembridge C:\Users\Asus\Desktop\Chembridge\chembridge_mvp\examples\misnamed.csv --out C:\Users\Asus\Desktop\Chembridge\chembridge_mvp\runs\cli_checks_20261108_001321\misnamed
```

EXIT_CODE: 0

stdout（节录）：
```
{
  "schema": "chembridge.run.v1",
  "tool_version": "0.1.0",
  "status": "complete",
  "created_utc": "2026-11-07T16:13:30.244312+00:00",
  "input_name": "misnamed.csv",
  "input_sha256": "25845271a46e0d8e2f38c3587c4c2dbfedfdccc373c77115921c16885ba793db",
  "detection": {
    "format": "mol",
    "reason": "MDL version marker and M  END.",
    "method": "signature",
    "suffix_hint": "csv",
    "warnings": [
      "Filename suggests csv, but content suggests mol; content takes priority."
    ]
  },
  "source_records": 1,
  "converted_records": 1,
  "failed_records": 0,
  "export_errors": 0,

```

stderr：
```
(empty)
```

manifest 关键栏位：
```json
{"format": "mol", "method": "signature", "suffix_hint": "csv", "warnings": ["Filename suggests csv, but content suggests mol; content takes priority."], "source_records": 1, "converted_records": 1, "failed_records": 0, "status": "complete"}
```

`errors.json` 笔数：0；索引：[]；原文：[]

## ambiguous_columns.csv 不选栏

```
C:\Users\Asus\Desktop\Chembridge\chembridge_mvp\.venv\Scripts\python.exe -m chembridge C:\Users\Asus\Desktop\Chembridge\chembridge_mvp\examples\ambiguous_columns.csv --out C:\Users\Asus\Desktop\Chembridge\chembridge_mvp\runs\cli_checks_20261108_001321\ambiguous_reject
```

EXIT_CODE: 2

stdout（节录）：
```
(empty)
```

stderr：
```
ERROR: Multiple structure columns: smiles, inchi. Select --column (and optionally --column-format).
```

## ambiguous_columns.csv --column smiles

```
C:\Users\Asus\Desktop\Chembridge\chembridge_mvp\.venv\Scripts\python.exe -m chembridge C:\Users\Asus\Desktop\Chembridge\chembridge_mvp\examples\ambiguous_columns.csv --out C:\Users\Asus\Desktop\Chembridge\chembridge_mvp\runs\cli_checks_20261108_001321\ambiguous_ok --column smiles
```

EXIT_CODE: 0

stdout（节录）：
```
{
  "schema": "chembridge.run.v1",
  "tool_version": "0.1.0",
  "status": "complete",
  "created_utc": "2026-11-07T16:13:33.352667+00:00",
  "input_name": "ambiguous_columns.csv",
  "input_sha256": "f7c072d8a6c7d7329243afa8a89d613504c8a2de49b1cf65dc7fe1a0260b8b89",
  "detection": {
    "format": "csv",
    "reason": "Delimited table; structure column must be resolved.",
    "method": "signature",
    "suffix_hint": "csv",
    "warnings": []
  },
  "source_records": 1,
  "converted_records": 1,
  "failed_records": 0,
  "export_errors": 0,
  "elapsed_seconds": 0.2752,
  "requested_outputs": [
  
```

stderr：
```
(empty)
```

manifest 关键栏位：
```json
{"format": "csv", "method": "signature", "suffix_hint": "csv", "warnings": [], "source_records": 1, "converted_records": 1, "failed_records": 0, "status": "complete"}
```

`errors.json` 笔数：0；索引：[]；原文：[]

## 同一 --out 重跑（防覆盖）

```
C:\Users\Asus\Desktop\Chembridge\chembridge_mvp\.venv\Scripts\python.exe -m chembridge C:\Users\Asus\Desktop\Chembridge\chembridge_mvp\examples\molecules.csv --out C:\Users\Asus\Desktop\Chembridge\chembridge_mvp\runs\cli_checks_20261108_001321\molecules
```

EXIT_CODE: 2

stdout（节录）：
```
(empty)
```

stderr：
```
ERROR: Output directory already exists; choose a new directory to avoid overwriting results.
```

manifest 关键栏位：
```json
{"format": "csv", "method": "signature", "suffix_hint": "csv", "warnings": [], "source_records": 5, "converted_records": 5, "failed_records": 0, "status": "complete"}
```

`errors.json` 笔数：0；索引：[]；原文：[]

## 防覆盖前后比对

`runs/.../molecules/manifest.json` SHA-256（重跑前）：`d045a6d7c10058647dc70fa699c647505c131eb3a31dd0537727a8269ad03407`

SHA-256（重跑后）：`d045a6d7c10058647dc70fa699c647505c131eb3a31dd0537727a8269ad03407`

是否相同：True

## 结论

- `molecules.csv` → 0（5/0）；`mixed_invalid.csv` → 1（1/2，partial）；`misnamed.csv` → 0（侦测 mol，1/0）。
- 歧义栏不选 → 2 且不建立输出目录；指定 `--column smiles` → 0（1/0）。
- 同一 `--out` 重跑 → 2，且原 manifest 位元组未变。
- 坏资料原文与 metadata 保留在 `errors.json`，成功记录未被删除。