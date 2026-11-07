# 3–5 分钟示范脚本（给零基础使用者）

目标：用三个案例说明「输入 → 侦测 → 选栏 → 解析 → 验证 → 计算 → 输出」每一段结果来自哪段程式，并说明坏资料去哪里。所有命令在 `chembridge_mvp` 根目录、用 `.venv\Scripts\python.exe` 执行。每次 `--out` 都要换一个**尚未存在**的目录名。

> 先讲一句定位（约 20 秒）：这是独立的本机小分子格式转换工具，不是 Torch Molecule Studio；转换只靠 RDKit，不需要 API 金钥、GPU 或模型。

---

## 案例一：全部成功（约 90 秒）

```powershell
.\.venv\Scripts\python.exe -m chembridge examples\molecules.csv --out runs\demo_ok
```

**预期**：控制台印出 `manifest.json` 内容，退出码 `0`；`detection.format = csv`、`converted_records = 5`、`failed_records = 0`、`status = complete`。

依序打开给观众看：

| 打开 | 会看到 | 结果来自哪段程式 |
|---|---|---|
| `runs\demo_ok\manifest.json` | `detection.reason = "Delimited table; structure column must be resolved."`、输入 SHA-256、环境版本、policy、`limitations` | `chembridge/io.py:137 detect()` 判定表格；`chembridge/pipeline.py:176-194` 组装 manifest |
| `runs\demo_ok\properties.csv` | 5 列、分子式、分子量、logP、TPSA、HBD/HBA、QED 等 13 栏 | `chembridge/pipeline.py:26 properties()`，由 RDKit `Descriptors/Crippen/Lipinski/QED/rdMolDescriptors` 计算 |
| `runs\demo_ok\images\m00001.png` | 乙醇 2D 结构图 | `chembridge/pipeline.py:126-139`，在**副本** `depiction` 上画，不改原始分子 |
| `runs\demo_ok\molecules.sdf` / `mol\m00001.mol` | 可给其他化学工具读取的结构档 | `chembridge/pipeline.py:105-117`，无座标才生成 2D 并加警告 |
| `runs\demo_ok\molecules.json` | 成功分子的 SMILES、性质、来源 metadata、警告、输出路径 | `chembridge/pipeline.py:97-99, 152-153` |
| `runs\demo_ok\original_input.bin` | 与输入档完全相同的位元组 | `chembridge/pipeline.py:72-73`，防篡改／可追溯 |

**白话重点**：CSV 只是容器，程式先在 `chembridge/io.py:200 _table_records()` 找出真正的 SMILES 栏，再对每一列呼叫 `Chem.MolFromSmiles`（`io.py:85 _parse_value()`）。先建出分子图，才能算性质、画图；不是直接把文字画成图。

---

## 案例二：混合坏资料（约 90 秒）

```powershell
.\.venv\Scripts\python.exe -m chembridge examples\mixed_invalid.csv --out runs\demo_mixed
echo $LASTEXITCODE
```

**预期**：退出码 **`1`**，但资料夹仍完整产生。`converted_records = 1`、`failed_records = 2`、`status = partial`。

> 一定要讲：**exit 1 不是 bug，是设计结果**。它表示「部分记录失败，但报告已产生」，不能改成假成功。对应 `chembridge/__main__.py:28` 的 `return 0 if manifest["status"] == "complete" else 1`。

打开：

| 打开 | 会看到 | 结果来自哪段程式 |
|---|---|---|
| `runs\demo_mixed\errors.json` | 2 笔失败：`record_index 3` 原文 `INVALID`、`record_index 4` 原文空值，各自带 `error` 原因与来源 `metadata`（含 `id`、`smiles`、`note`） | `io.py:253 parse_records()` 把逐笔错误写进 `Record.error`；`pipeline.py:79-82, 173` 汇出 |
| `runs\demo_mixed\molecules.json` | 仍保留 1 笔成功分子 | `pipeline.py:147`，成功记录不因其他笔失败被删除 |
| `runs\demo_mixed\manifest.json` | `source_records = 3 = converted(1) + failed(2)` | `pipeline.py:180-182`，来源笔数可对帐 |

**白话重点**：坏资料不会被偷偷丢掉。结构性错误（档案读不懂、栏位歧义）会抛 `InputError` → exit 2；逐笔错误则保留原文与原因。这个区别来自 `chembridge/io.py:25 InputError` 与 `pipeline.py:69-70` 的检查顺序。

---

## 案例三：歧义栏位（约 90 秒）

先**不指定**栏位：

```powershell
.\.venv\Scripts\python.exe -m chembridge examples\ambiguous_columns.csv --out runs\demo_reject
echo $LASTEXITCODE
```

**预期**：退出码 `2`，stderr 显示 `ERROR: Multiple structure columns: smiles, inchi. Select --column (and optionally --column-format).`，而且 `runs\demo_reject` **不会被建立**。

再明确指定：

```powershell
.\.venv\Scripts\python.exe -m chembridge examples\ambiguous_columns.csv --column smiles --out runs\demo_choose
echo $LASTEXITCODE
```

**预期**：退出码 `0`，`converted_records = 1`、`failed_records = 0`。

| 结果 | 来自哪段程式 |
|---|---|
| 两个已知结构栏就拒绝自选 | `chembridge/io.py:224-226`，`raise InputError("Multiple structure columns: ...")` |
| 指定 `--column smiles` 后采用该栏 | `chembridge/io.py:217-221` |
| 未知栏名才用前 20 列、80% 可解析率取样 | `chembridge/io.py:229-236`，这是工程规则，**不是模型信心** |
| 拒绝时不建立输出目录 | `convert_file` 先 `load_text → detect → parse_records`（`pipeline.py:66-68`），防覆盖检查 `pipeline.py:69-70` 在其后 |

**白话重点**：`name,smiles,inchi` 里有两个候选结构栏，程式不会猜你要哪一个，而是要求你指定。这就是「拒绝／歧义」比「硬猜」更安全的地方。

---

## 收尾（约 30 秒）

- 再跑一次 `--out runs\demo_ok` 会被拒绝（`exit 2`、`already exists`），原 `manifest.json` 位元组不变 → `pipeline.py:69-70`。
- 把 `misnamed.csv`（内容是 MOL、档名是 .csv）跑一次，会侦测成 `mol` 并在 manifest 加 `Filename suggests csv, but content suggests mol` 警告 → `io.py:147-155, 193-195`。
- **资讯损失提醒**：SMILES/InChI/SELFIES 不保存 3D 座标；InChI 可能正规化部分资讯；RDKit logP、QED 是计算／估计值，不是实验药效或模型预测。原始档备份与 JSON metadata 有助追溯，但不能称为普遍无损转换。

## 可核对的真实证据

- `evidence/windows_run_20261107/commands_and_results.md`、`pytest.txt`（`46 passed`）
- `evidence/windows_run_20261107/cli_exit_codes.md`（六条 CLI 命令与退出码 `0,1,0,2,0,2`）
- `evidence/windows_run_20261107/ui_browser_test.md`（真实浏览器上传／选栏／ZIP 下载与截图）
- `evidence/acceptance_matrix.xlsx`、`docs/ACCEPTANCE_MATRIX_zh.md`（23 笔样本，明确标注非真实用户资料）
