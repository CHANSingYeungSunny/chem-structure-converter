# ChemBridge 本机工程验证与交付报告

日期：2026-11-07 至 2026-11-08（香港时间）｜执行环境：本机 Windows 11｜对应提示词：`prompts/DEEPSEEK_EXECUTION_PROMPT_zh.txt`

> **证据分层声明**：`evidence/environment.json`（Linux-6.18.57 / Python 3.12.14）、`evidence/test_run.txt`（`39 passed in 1.46s`）、`evidence/VALIDATION_SUMMARY.json` 是**上游交付时预置的 Linux 产物**，原档保留未改写。本报告中所有的 Windows 命令、输出与退出码都来自本机另存的 `evidence/windows_run_20261107/`，两者不混用。

---

## 1. 问题定义与边界

研究题目：自动侦测常见化学结构格式（`.mol`、`.csv` 等），转换成可用输出（图片、其他格式或计算性质）。

三个必须先厘清的定位：

1. **实际产品是 Torch Molecule Studio**，不等于 `liugangcode/torch-molecule` Python 套件；`chembridge_mvp` 是独立工程原型，**不是 Studio 原始码**。
2. 使用者为零基础、Windows、约 4 GB 显卡；本次全程 CPU + RDKit，**没有**索取／写入任何密钥，没有安装或训练大型模型，没有接真模型推论。
3. 本阶段目标是「把独立工具验证到可交付」，不是重写产品、不是公开部署、不是学术结果。

真实工作样本：使用者本次未提供实际上传档；依确认改以「PubChem 公开结构档 + 人工合成边界案例」建立验收表，**明确标注非使用者真实资料、不构成真实世界准确率**。

## 2. 支援矩阵（依实际 reader 核对，非只抄 README）

| 输入 | 状态 | 侦测依据 | 本次实测 |
|---|---|---|---|
| MOL V2000/V3000 | 已实作 | `V2000/V3000` + `M  END` 签章 | `misnamed.csv`（内容 MOL）→ 侦测 `mol`、1/0 |
| SDF/SD | 已实作 | `$$$$` 分隔、`ForwardSDMolSupplier` | 4 个 PubChem SDF + 2 个合成 SDF + gzip SDF（2 笔）+ metadata 保留 |
| CSV/TSV（含分号） | 已实作 | 分隔符 + 结构栏名 / 80% 启发式 | `molecules.csv` 5/0、`mixed_invalid.csv` 1/2、缺值、无效价态、盐／电荷／立体／同位素 |
| SMI/SMILES 文字 | 已实作 | 档名提示 / 首 token 试解析 | 上游合成范例 |
| InChI 文字 | 已实作 | `InChI=` 前缀 | `B15_inchi.txt` 1/0 |
| SELFIES 文字 | 已实作 | 档名提示，括号文字歧义会拒绝 | `B16_selfies.selfies` 1/0 |
| JSON | 已实作（专案 schema） | `{`/`[` 容器 | 上游测试覆盖；不代表任意供应商 JSON |
| 文字档 gzip | 已实作 | gzip magic，压缩／解压各 20 MiB 上限 | `B14_gzip.sdf.gz` 2/0 |
| MOL2 | **有限支援** | `@<TRIPOS>MOLECULE` | 仅 1 个标准 TRIPOS 水分子；不保证力场／部分电荷 |
| PDB | **实验性、预设拒绝** | `ATOM`/`HETATM`，需 `--allow-pdb` + CONECT + 单模型 | `B13` 未 opt-in 正确拒绝 |
| XYZ、CIF/mmCIF、CML、CDX/CDXML、PDBQT | 未支援 | `FORMATS` 无此 reader | `B12` XYZ 正确拒绝，未猜键级 |
| 结构图片、扫描 PDF、一般 Word/PDF 化学文件 | 未支援 | 二进位会被 `decode_bytes` 拒绝 | 需另一条结构辨识流程 |

`FORMATS`（`chembridge/io.py:17`）只有 10 种。README 的输入范围表与程式**大致一致**，但发现若干用语落差与未文件化的硬限制，详见 `evidence/windows_run_20261107/code_audit.md`：例如「前 20 笔非空值」实为前 20 个资料列、图片上限为 5000、AppTest 只显示前 12 张 PNG、`policy` 是写死常值而非旗标、`MAX_RECORDS=5000` 与 1000 原子上限未写在 README、PDB 预设拒绝属 exit 2。

## 3. 架构与真实资料流

主流程只有一个化学逻辑边界 `chembridge/pipeline.py:48 convert_file()`；CLI、UI、demo、测试、验收脚本都呼叫它，没有第二份化学逻辑。

```
CLI(__main__.py:9) / UI(app.py:33) / demo(run_demo.py:15)
        └─> convert_file()  [pipeline.py:48]
              ├─ load_text → decode_bytes   [io.py:72, 53]  解码 / gzip / 20 MiB / BOM
              ├─ detect                    [io.py:137]      内容签章优先于副档名
              ├─ parse_records → _table_records [io.py:253, 200] 选栏 / 逐笔验证
              ├─ properties                [pipeline.py:26] 13 个 RDKit 描述符
              ├─ 输出 molecules.json / properties.csv / mol / sdf / png / svg / smi / inchi / selfies
              └─ errors.json / export_errors.json / manifest.json / original_input.bin
        └─> __main__.py:28  exit 0 (complete) / 1 (partial, 仍有报告) / 2 (InputError)
```

`model_adapter.py:10 predict_with_fitted_model()` 独立存在，只被 `tests/test_adapter.py` 的 fake predictor 呼叫，主流程完全不呼叫，也没有内附权重。

## 4. 关键程式片段与白话解说

### 4.1 先读懂分子，才能算与画

```python
# scripts/first_steps.py（教学用，不进主链）
mol = Chem.MolFromSmiles("CCO")
assert mol is not None
print(Descriptors.MolWt(mol))
Draw.MolToImage(mol).save("ethanol.png")
```

白话：`CCO` 只是文字；`MolFromSmiles` 把它变成电脑内的原子／键图，`assert` 确认没解析失败，之后分子量、氢键供体、结构图都是从这个图算／画出来的。`convert_file` 里的正式版本是 `io.py:85 _parse_value()`，对 SMILES/InChI/SELFIES/MOL/MOL2/PDB 分别呼叫对应 reader，并拒绝空分子、>1000 原子与 wildcard 原子。

### 4.2 两个结构栏不默默选

```python
# chembridge/io.py:224-226
elif len(named) > 1:
    raise InputError("Multiple structure columns: "
        + ", ".join(h for h, _ in named)
        + ". Select --column (and optionally --column-format).")
```

白话：CSV 只是容器。`_table_records()` 先认已知栏名，若有两个候选就要求人指定，不猜第一个。未知栏名才取前 20 个资料列、以该栏非空格值达 80% 可解析率找唯一候选（`io.py:229-236`）；这是工程规则，不是模型信心。

### 4.3 坏资料去哪里

```python
# chembridge/pipeline.py:79-82
if record.error:
    errors.append({"record_index": record.index, "name": record.name,
                   "error": record.error, "raw": record.raw, "metadata": record.metadata})
    continue
```

白话：逐笔错误写进 `errors.json`（含原文、原因、来源 metadata），成功记录继续处理；结构性错误（档案读不懂、栏位歧义）则抛 `InputError`、不建立输出目录。混合资料 CLI 回 `1` 是「部分失败但报告已产生」，不是失败要掩盖。

### 4.4 不覆盖旧结果

```python
# chembridge/pipeline.py:69-70
if output_dir.exists():
    raise InputError("Output directory already exists; choose a new directory to avoid overwriting results.")
```

白话：每次 `--out` 必须是新目录。本机实测重跑同一目录回 exit 2，且原 `manifest.json` 位元组不变（`cli_exit_codes.md` 有前后 SHA-256 比对）。

### 4.5 性质不是药效

`pipeline.py:26 properties()` 的 13 个数值全部来自 RDKit 描述符／估计（分子式、分子量、精确质量、logP、TPSA、HBD/HBA、可旋转键、环数、重原子、电荷、片段数、QED）。manifest 的 `policy` 明写 `neutralize/strip_salts/tautomer_standardize/deduplicate = False`、`ml_prediction = False`。这些不是实验测量、毒性安全、药效或 torch-molecule 预测。

## 5. 真实命令与结果

### 5.1 环境修复（本机真实障碍）

- 起始状态：`.venv` 是 Python 3.12.14 / pip 26.2.1，但五个依赖全部未安装；`evidence/actual_run_20261107/pip_install.log` 记录上次把暂存目录指到专案内 `.tmp` 造成 `[Errno 13] Permission denied`。
- 诊断：PyPI 可连（HTTP 200，0.27 秒）、无残留程序、无可用 wheel 快取；但 `.venv\Scripts\python.exe -m pip install` 会 CPU 空转（观察到 118 秒、无输出、无网路连线、无落盘）。系统 Python 3.9/3.10 保持不动。
- 解法：以**系统 Python 3.10 的正常 pip** 搭配 `--target .venv\Lib\site-packages` 与跨版本标签（`--platform win_amd64 --python-version 3.12 --implementation cp --abi cp312 --only-binary=:all:`），把官方 cp312 wheel 直接装进 venv，全程不呼叫坏掉的 venv 启动器。
- 真实日志：`evidence/windows_run_20261107/bootstrap_install.txt` → `stage1_selfies_probe` `STAGE_EXIT_CODE=0`；`stage2_full_requirements` 成功安装 48 个套件、`STAGE_EXIT_CODE=0`、`FINAL_EXIT_CODE=0`。日志中 `openxlab 0.1.3 requires packaging~=24.0` 的冲突警告来自**系统 Python 3.10 既有套件**的完整解析器提示，venv 内没有 `openxlab`，不影响本次环境。
- 装完验证：`python 3.12.14`、`Windows-11-10.0.26200-SP0`、`rdkit 2025.9.4`、`selfies 2.2.0`（模块自报 2.1.1）、`Pillow 12.3.0`、`streamlit 1.51.0`、`pytest 8.4.2`，`Chem.MolFromSmiles("CCO")` 得到 3 个原子。

### 5.2 三个实跑命令

| 命令 | 退出码 | 真实输出 |
|---|---|---|
| `.venv\Scripts\python.exe scripts\first_steps.py` | 0 | 产生 `learning_output/` 与乙醇图片 |
| `.venv\Scripts\python.exe scripts\run_demo.py` | 0 | 三个 job：`molecules.csv` csv 5/0；`mixed_invalid.csv` csv 1/2；`misnamed.csv` mol 1/0 |
| `.venv\Scripts\python.exe -m pytest -q` | 0 | `46 passed in 32.49s` |

证据：`evidence/windows_run_20261107/commands_and_results.md`、`pytest.txt`、`demo_manifests.json`、`environment.json`。

**发现的真实问题与修复**：首次 pytest 为 `1 failed, 38 passed`，失败是 `tests/test_optional_ui.py` 的 Streamlit AppTest 第二次 `app.run()` 在预设 3 秒超时。以 `diagnose_apptest.py` 实测 `run(timeout=30)` 需 5.21 秒且无异常、`dataframe_count=1`，判定为 Windows 上测试执行绪启动较慢，**不是产品缺陷**。修改前原文隔离保存在 `test_optional_ui_before_fix.py.txt`，失败输出保存在 `pytest_before_fix.txt`；修复是把两次 `run` 明确设为 `timeout=30`，并在 `tests/test_acceptance_regressions.py` 新增 7 个以真实 CLI 与范例档为依据的回归测试（结束码、歧义拒绝、坏资料保留、防覆盖、错副档名）。修复后 `39 → 46 passed`。

### 5.3 CLI 边界复验

`run_cli_checks.py` 的真实退出码序列：`0, 1, 0, 2, 0, 2`（`molecules` / `mixed_invalid` / `misnamed` / 歧义不选栏 / 指定 `smiles` / 同一 `--out` 重跑），`manifest_unchanged: true`。详见 `evidence/windows_run_20261107/cli_exit_codes.md`。

### 5.4 真实浏览器 UI 实测

以 `playwright-cli`（真实 Chromium）开启 `http://127.0.0.1:8501`（`/_stcore/health` 回 `ok`），实际上传、点选、下载：

| 样本 | 界面 | 下载 |
|---|---|---|
| `molecules.csv` | `格式：csv；成功：5；失敗：0`、5 张结构图、性质表 | `chembridge_results.zip` 79,410 B，25 档，含 manifest/properties/errors/10 图档 |
| `mixed_invalid.csv` | `成功：1；失敗：2`、警告与错误清单 JSON | ZIP 11,274 B；`errors.json` 2 笔，索引 `[3,4]`，原文 `INVALID`／空值；manifest `partial` |
| `misnamed.csv` | `格式：mol；成功：1；失敗：0`，副档名冲突警告 | ZIP 按钮存在 |
| `ambiguous_columns.csv` 不选栏 | `Multiple structure columns: smiles, inchi. Select --column...`，无假成功 | — |
| 同上，展开设定填 `smiles` | `格式：csv；成功：1；失敗：0` | ZIP 按钮存在 |

四张截图与八份页面快照都在 `evidence/windows_run_20261107/`；完整区分「真实操作／AppTest 程式测试／未测项目」见 `ui_browser_test.md`。`agent-browser` 本机未安装，未强行安装以免更动全域 npm 环境，此通道记为未使用。

### 5.5 验收矩阵

23 个档案（4 个 PubChem 公开 2D SDF + 16 个合成边界 + 3 个上游合成范例），逐案结果 `evidence/windows_run_20261107/acceptance_results.json`，试算表 `evidence/acceptance_matrix.xlsx`，说明 `docs/ACCEPTANCE_MATRIX_zh.md`。独立计算：格式识别 `22/22`（1 笔预期格式不明排除）、拒绝／歧义 `4/4`、读取成功 `19/19`、误接受 `0/23`、输入→输出化学图一致 `17/17`（6 笔排除）、metadata 保留 `6/6`、3D 座标保留 `1/1`；耗时 p50 `0.0533s`、p95 `0.0794s`。**这些是工程验收，不是真实世界准确率。**

## 6. 已完成 / 未完成

**已完成**：读码核对与文件落差清单；本机 3.12 环境修复与依赖安装；三个实跑命令与 46 个测试；CLI 结束码与防覆盖复验；真实浏览器上传／选栏／性质／错误／ZIP 下载；一个真实缺陷的诊断、隔离修复与 7 个回归测试；23 笔人工标注验收表与资讯损失评估；中文报告、示范脚本、13 项摘要；证据完整留存。

**未完成 / 明确标注**：
- **Torch Molecule Studio 整合：未完成**（见第 9 节）。
- 真实使用者上传资料验收：无真实样本，改以公开＋合成样本，已声明不代表真实分布。
- 真 torch-molecule 模型训练／推论：未执行，也没有权重、目标、单位、checkpoint。
- 图片／扫描 PDF 结构辨识、XYZ/CIF/CML/CDX/PDBQT 支援、Open Babel 整合：未做。
- 跨浏览器核对、大于 200 MB 上传、多使用者、公开部署、工作伫列、身份验证、timeout：未测。
- `agent-browser` 通道、`start_windows.bat` 单独实测：未测。
- 验收表 Excel 公式快取值：本机无 LibreOffice、`recalc.py` 在 Windows 因 `socket.AF_UNIX` 不存在无法执行，公式以 Excel 开启自动重算为准，独立核对值写在报告与说明文件中。

## 7. 资讯损失

- SMILES／InChI／SELFIES 不保存 3D 座标；标准 InChI 可能正规化互变异构／质子化资讯。
- Canonical SMILES 受 RDKit 版本影响，不等于完整化学身分标准化；本工具不去盐、不中和、不去重复、不做互变异构标准化。
- SDF/MOL 输出在无座标时会生成 2D 并加警告；有座标则保留（本次仅 1 个 3D 样本验证）。
- MOL2 仅验证 1 个标准 TRIPOS 水分子，不保证力场／部分电荷／原子型别资讯。
- 表格／逐行输出（`properties.csv`、`molecules.smi` 等）只保留部分栏位；完整 metadata 在 `molecules.json` 与 `original_input.bin`。
- 验收表的「化学图一致」以独立 RDKit InChIKey 比对，不是原始档逐位元相同，也不是字串相同。

## 8. 下一步

1. **优先收集使用者实际会上传的档案与格式分布**，重新建立人工标注验收集；现有 23 笔只能当回归基准（依 `docs/ENGINEERING_PLAN_zh.md` 建议，每个主要格式至少 100 个真实档或依实际分布取样）。
2. 依实际缺口选下一个格式：XYZ 若支援必须把「键级不明」标示为推论并要求人工核对；图片／PDF 需另一条结构辨识流程；引入 Open Babel 前先核对官方格式清单与各格式资讯损失，不宣称支援所有档案。
3. 取得真正 Studio 源码后再做整合（第 9 节）。
4. 若将来要接模型，先定义预测目标、单位、标签来源、正确 checkpoint 与适用范围，且训练／验证／测试独立切分。

## 9. Studio 整合状态：未完成（依提示词第 14 条）

**没有找到任何可证明是 Torch Molecule Studio 的原始码、remote、README 或启动入口。** 证据（`evidence/windows_run_20261107/code_audit.md` 第 6 节）：工作区只有 `ChemBridge_Engineering_Starter_v0_1_0.zip`、`chembridge_mvp/`、`diagnostics/` 与指南 docx/pdf；全工作区搜 `*studio*` 为 0 个档案、`*torch*` 只有 `docs/TORCH_MOLECULE_SOURCE_MAP_zh.md`；11 个 `.py` 全在 `chembridge_mvp`，没有 Studio 前后端、上传路由或启动入口；没有 `.git` 与 remote；`docs/TORCH_MOLECULE_SOURCE_MAP_zh.md:11` 明写「真實程式尚未取得」；`docs/SOURCES.md` 只有上游 `liugangcode/torch-molecule` 固定 commit 的 URL，不是本档案案。

**欠缺的资料**：真正 Studio 的 repo URL 或 ZIP（含其 `remote`、`README`、启动入口、前后端框架、上传路由与资料契约）。**为何需要它**：整合必须在真实路由／框架／资料契约上加「上传 → 预览 → 选栏 → 转换 → 下载」，后端要重用 `convert_file`、每个 job 用隔离目录、输出结构化错误与 manifest；没有源码就无法确认这些入口，也不能凭空杜撰档案路径或宣称已整合。`README.md:97-102` 的 `convert_file` 范例只是**可整合的界面建议**，不是已完成整合。本次没有新增任何声称「已整合」的档案或路径。

## 10. 证据清单

| 证据 | 路径 |
|---|---|
| 读码核对与文件落差 | `evidence/windows_run_20261107/code_audit.md` |
| 指南 PDF 全文与提取脚本 | `evidence/windows_run_20261107/guide_extract.txt`、`extract_guide_text.py` |
| 安装日志（含失败尝试与成功绕道） | `pip_install.txt`、`bootstrap_install.txt`、`bootstrap_venv.py`、`install_deps.cmd`、`install_worker.py`、`launch_install.py` |
| 环境与版本 | `environment.json` |
| 三个实跑命令与输出 | `commands_and_results.md`、`commands_and_results_before_fix.md`、`pytest.txt`、`pytest_before_fix.txt`、`demo_manifests.json` |
| CLI 边界复验 | `cli_exit_codes.md`、`run_cli_checks.py` |
| UI 实测 | `ui_browser_test.md`、四张 `ui_*.png`、八份 `ui_snapshot_*.txt`、两个 `downloaded_*.zip` |
| 回归测试与修复前原文 | `tests/test_acceptance_regressions.py`、`test_optional_ui_before_fix.py.txt`、`diagnose_apptest.py` |
| 验收样本与来源 | `examples/acceptance/SOURCES.md`、`boundary/`、`acceptance_results.json`、`build_acceptance.py` |
| 验收表与说明 | `evidence/acceptance_matrix.xlsx`、`docs/ACCEPTANCE_MATRIX_zh.md` |
| 交付文件 | `docs/DEMO_SCRIPT_zh.md`、`docs/RETURN_RESULTS_FILLED_zh.md`、`docs/DELIVERY_EVIDENCE_zh.md` |

## 11. 核心修改差异

- `tests/test_optional_ui.py`：两处 `app.run()` 改为 `run(timeout=30)`，附本机实测量测依据（唯一的产品测试修改）。
- `tests/test_acceptance_regressions.py`：**新增** 7 个真实 CLI 回归案例。
- `.gitignore`：新增 `.tmp/`、`.pipcache/`、`.playwright-cli/` 忽略规则。
- `README.md`：更正「Windows 尚未实测」「GitHub 推送尚未完成」等过时宣称，补本机实跑结果、可重跑脚本与环境绕道说明。
- 新增 `docs/` 四份交付文件、`evidence/windows_run_20261107/` 全部本机证据、`examples/acceptance/` 验收样本。
- **`chembridge/` 核心逻辑、`requirements*.txt`、`pyproject.toml`、`PACKAGE_MANIFEST.json`、`scripts/`、`app.py` 均未改动**。
- 由于 README 已更新，其 SHA-256 与上游 `PACKAGE_MANIFEST.json` 记录的原始值不再一致；该清单保留作为「上游原始交付」的比对基准，未改写。

---

## 附录：完整提示词保留声明

两份提示词原档**原样保留、未删改**于交付包：

| 档案 | 上游 `PACKAGE_MANIFEST.json` 记录的 SHA-256 | 字节 |
|---|---|---|
| `prompts/DEEPSEEK_EXECUTION_PROMPT_zh.txt` | `8ae4b4ccaef5b4480e54b7b49e35c1574a70ab5d299d4faa054f592ad953f5d7` | 6,938 |
| `prompts/RETURN_RESULTS_TO_CHATGPT_zh.txt` | `515b8b6530081c3d63958d95dd48204531e640a14ca4ca90b4836d79fee75c2f` | 1,038 |

`DEEPSEEK_EXECUTION_PROMPT_zh.txt` 共 20 条指示（五阶段：读码核对、实际执行、真实工作资料验收、Studio 整合、GitHub 建立与推送）与交付 A–E；`RETURN_RESULTS_TO_CHATGPT_zh.txt` 为 13 项回传模板，并要求先审核证据一致性、指出下一个最重要的改进，且不得把 fixture／RDKit 描述符／fake adapter 当成真实准确率、实验药效或真正推论。本报告与 `docs/RETURN_RESULTS_FILLED_zh.md` 即依该模板逐项填答。
