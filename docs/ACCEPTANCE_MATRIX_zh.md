# 第三阶段：格式验收矩阵说明（2026-11-08，本机 Windows）

> **这不是真实世界准确率报告。** 本表 23 个档案来自 PubChem 公开资料与人工合成边界案例，**不是使用者实际上传的真实工作资料**，也不代表任何真实上传分布。固定单元测试 `46 passed` 只是回归检查，与本表任何比率无关。

## 1. 资料来源、版本与分母

| 项目 | 内容 |
|---|---|
| 产生时间 | 2026-11-08（香港时间），由 `evidence/windows_run_20261107/build_acceptance.py` 产生 |
| 环境 | `Windows-11-10.0.26200-SP0` / Python `3.12.14` / `rdkit 2025.9.4` / `selfies 2.2.0`（模块自报 2.1.1）/ ChemBridge `0.1.0` |
| 化学逻辑边界 | 所有案例都经 `chembridge.pipeline.convert_file`，没有第二份化学逻辑 |
| 总分母 | **23 个档案**（以档案为单位，不是分子数） |
| 公开来源 | 4 个 PubChem 2D SDF：CID 702 ethanol、1983 caffeine、2244 aspirin、3672 ibuprofen，取得日期 2026-11-08，来源与授权说明见 `examples/acceptance/SOURCES.md` |
| 人工合成边界 | 16 个，产生在 `examples/acceptance/boundary/`：错副档名、缺结构栏、多结构栏、缺值、无效价态、盐／电荷、立体化学、同位素、3D 座标、SDF metadata、MOL2、XYZ、PDB 未 opt-in、gzip、InChI、SELFIES |
| 上游合成范例 | 3 个：`molecules.csv`、`mixed_invalid.csv`、`ambiguous_columns.csv`（指定 `smiles`） |
| 逐案原始结果 | `evidence/windows_run_20261107/acceptance_results.json` |
| 逐案试算表 | `evidence/acceptance_matrix.xlsx`（三个工作表：逐案结果／汇总／说明与限制） |
| 本次输出 | 刻意不含 PNG/SVG，聚焦化学图往返；图片证据另见 demo 产物与真实浏览器截图 |

## 2. 评估维度、分母与排除规则

| 维度 | 分母 | 通过 | 结果 | 定义与排除 |
|---|---|---|---|---|
| 格式识别 | 22 | 22 | 100% | 比对 `detect()` 的 `format` 与人工标注。排除 1 笔 `B12_xyz_unsupported.xyz`：该文件预期就是「无法判定格式」，不列入分母 |
| 拒绝／歧义 | 4 | 4 | 100% | 只计预期应拒绝的档案（缺结构栏、两个结构栏、XYZ、PDB 未 opt-in），实际抛 `InputError` 且不建立输出目录才算正确 |
| 读取成功 | 19 | 19 | 100% | 只计预期接受／部分成功的档案，成功数与失败数**都**须符合人工标注 |
| 误接受 | 23 | 0 | 0 件 | 预期拒绝却接受，或预期坏资料被静默当成成功，记为 1 |
| 输入→输出化学图一致 | 17 | 17 | 100% | 以**独立 RDKit reader** 从原始档算 InChIKey 集合，与输出 `mol/*.mol` 回读的 InChIKey 集合比对；不是原始档逐位元相同，也不是字串相同。排除 6 笔：4 笔拒绝、1 笔无成功分子（无效价态）、1 笔 gzip（独立 reader 无法直接解析） |
| metadata 保留 | 6 | 6 | 100% | 只计含 SDF 属性的样本（4 个 PubChem + 2 个合成 SDF）；gzip SDF 不列入 |
| 3D 座标保留 | 1 | 1 | 100% | 只计含 3D conformer 的合成 SDF，检查输出 MOL 回读后 `Is3D()` 仍为真 |
| 耗时 | 23 | — | p50 0.0533s / p95 0.0794s（min 0.0157 / max 0.0946） | 取 `manifest.elapsed_seconds`；本机单机、无并发、样本都很小 |

所有比率的分母都是**该维度适用的档案数**；不适用者记 `NA` 并排除，不以 0 充当通过或失败。多笔 SDF 的分子数另计（`molecules.sdf` 含 2 笔），不混成独立格式档数。

## 3. 值得注意的个案

- `B01`（MOL 内容配 `.csv` 档名）：侦测 `mol`，并产生 `Filename suggests csv, but content suggests mol; content takes priority.` 警告 → 内容签章优先于副档名。
- `B02`／`B03`：缺结构栏、两个结构栏都被拒绝，没有默默选第一栏，也没有产生输出目录。
- `B05`（`C(C)(C)(C)(C)C` 五价碳）：RDKit 拒绝，记录进 `errors.json`，没有误接受。
- `B04`／`E02`（缺值与混合坏资料）：成功与失败记录同时保留，原文与来源 metadata 未删除。
- `B06`/`B07`/`B08`（盐／电荷、立体、同位素）：canonical SMILES 与 InChIKey 往返一致；但工具不做去盐、中和或互变异构标准化，policy 在 manifest 里明确写死 `neutralize: False` 等。
- `B12` XYZ：`detect()` 抛 `Unknown or ambiguous text format. Use --input-format explicitly.` → 正确拒绝，**没有把只有元素与座标的 XYZ 猜成确定结构**。
- `B13` PDB：即使有 `CONECT`，未加 `--allow-pdb` 仍拒绝；这是设计上的显式 opt-in。
- PubChem 四个 2D SDF：SDF 属性进入 `molecules.json` 的 `metadata`，输出 MOL 回读的化学图一致。

## 4. 资讯损失与未评估范围

- 标准 InChI／InChIKey 可能正规化互变异构、质子化等细节；化学图一致**不等于**完整化学身分保真或普遍无损转换。
- SMILES／InChI／SELFIES 不保存 3D 座标；本次只对 1 个 3D SDF 验证 MOL 座标保留，不能推论任意座标档。
- MOL2 只验证 1 个标准 TRIPOS 水分子，不能推论各供应商 MOL2、力场参数或部分电荷资讯保留。
- 验收刻意不含 PNG/SVG，且未评估 `--outputs` 子集、`image_limit` 边界、export error 路径。
- 未评估大于 20 MiB／5000 笔上限、任意供应商 JSON schema、大分子／蛋白质、多模型 PDB、不同来源 PDBQT。
- 仍未支援：XYZ、CIF/mmCIF、CML、CDX/CDXML、PDBQT、结构图片、扫描 PDF、一般 Word/PDF 化学文件。
- 本表不含私人资料、使用者上传档、实验测量值或任何模型预测值；RDKit 描述符不是实验药效，`model_adapter` 的 fake predictor 不是真模型推论。

## 5. 公式重算限制（如实记载）

`evidence/acceptance_matrix.xlsx` 的「汇总」页使用 Excel 公式（`COUNT` / `SUM` / `MEDIAN` / `PERCENTILE`）计算比率。本机没有 LibreOffice，且 xlsx 技能随附的 `recalc.py` 在 Windows 上因 `socket.AF_UNIX` 不存在而无法执行，因此**公式的快取值未在本机重算**；以 Excel 开启时自动重算为准。本文件第 2 节的数值由 Python 独立计算，可作为交叉核对，两者口径一致。活页簿本身没有 `#REF!` / `#DIV/0!` 等公式错误（分母为 0 时公式回传 `NA`）。

## 6. 下一个格式的取舍（基于本表缺口，非使用者真实需求）

提示词要求「针对实际缺口选下一个格式」。由于**没有使用者真实上传分布**，这里只能列出基于本表的候选，不能冒充已确认的优先顺序：

1. **XYZ**：本表唯一被明确拒绝的常见座标格式。若下一阶段要支援，必须把「只有元素与座标、键级不明」标示为**推论**，输出中明确警告并要求人工核对，不能默默猜成确定结构；也不该把推得的键级当原始真值。
2. **MOL2 多样性**：目前只有一个合成水分子，需先补不同供应商／原子型别／电荷栏位的真实档案，并建立可读写能力与资讯损失对照表。
3. **图片／扫描 PDF**：这是**另一条结构辨识流程**（先抽取结构，再经 RDKit 验证），不是普通档案互转；不能把文字 OCR 等同分子图辨识，本阶段不纳入格式转换路线。
4. **Open Babel**：`docs/SOURCES.md` 已列官方文件连结，但本次**未安装、未整合、未核对官方格式清单**，因此不宣称支援它所列的任何格式。若引入，须先逐格式核对可读写、键级／立体／座标／电荷承载能力与资讯损失，并在输出中标注推断项目。

在真正选定下一个格式之前，仍需收集使用者实际会上传的档案与分布，重新建立人工标注验收集；本表的 23 笔只能当工程回归基准。
