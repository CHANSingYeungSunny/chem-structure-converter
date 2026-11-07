# 第一阶段：读码与宣称核对（本机 Windows，2026-11-07）

本文件是本机实际读码的结果，不是从 README 转抄，也不是 `evidence/` 内上游 Linux 预置证据的复述。核对方式：逐档读取原始码 + 用只读子代理跨档交叉比对 + 以 `pypdf` 提取工程指南全文（见 `guide_extract.txt`，由 `extract_guide_text.py` 产生）。

## 1. 实际读过的档案

- `README.md`、`docs/ENGINEERING_PLAN_zh.md`、`docs/SOURCES.md`、`docs/TORCH_MOLECULE_SOURCE_MAP_zh.md`、`docs/GITHUB_DELIVERY_zh.md`、`docs/Engineering_Starter_Guide_zh.pdf`（11 页）
- `chembridge/io.py`、`pipeline.py`、`__main__.py`、`model_adapter.py`、`__init__.py`
- `app.py`、`scripts/first_steps.py`、`scripts/run_demo.py`
- `tests/test_workflow.py`、`tests/test_optional_ui.py`、`tests/test_adapter.py`
- `pyproject.toml`、`requirements*.txt`、`start_windows.bat`、`.gitignore`、`PACKAGE_MANIFEST.json`
- `examples/` 14 个合成范例、`evidence/` 预置产物与 `evidence/actual_run_20261107/pip_install.log`

## 2. 真实函式链：输入 → 输出

主流程只有一个化学逻辑边界 `chembridge/pipeline.py:48 convert_file()`；CLI、UI、demo、测试都呼叫它，没有第二份化学逻辑。

| 环节 | 真实函式与位置 | 做的事 |
|---|---|---|
| CLI 入口 | `chembridge/__main__.py:9 main()` | 解析参数，21–23 呼叫 `convert_file`；24–26 捕捉 `InputError/OSError/ValueError` 回 2；28 依 `manifest["status"]` 回 0 或 1 |
| 套件 API | `chembridge/__init__.py:4` | 只汇出 `convert_file`，供 README 的 Studio 整合范例与 `scripts/run_demo.py:9` 使用 |
| UI 入口 | `app.py:33-34` | 上传档写入临时目录后呼叫同一个 `convert_file` |
| 教学脚本 | `scripts/first_steps.py` | 独立示范 `CCO` → Mol → 描述符 → 图片，**不呼叫** `convert_file` |
| ① 输入／解码／上限 | `pipeline.py:66` → `io.py:72 load_text()` → `io.py:53 decode_bytes()` | 20 MiB 压缩／解压双上限（`io.py:15,54,59,62`）、gzip magic、UTF-16 BOM 与 `utf-8-sig`；二进位（图片/PDF/CDX）直接 `InputError` |
| ② 格式侦测 | `pipeline.py:67` → `io.py:137 detect()`；辅助 `_hint:77`、`_lines:121`、`_cell_format:126`、`_valid:113`、`_parse_value:85` | 回传 `Detection(format, reason, method, suffix_hint, warnings)` |
| ③ 栏位选择／逐笔解析 | `pipeline.py:68` → `io.py:253 parse_records()`；表格再走 `io.py:200 _table_records()` | 分支 csv/tsv/json/sdf/mol2/mol/pdb/文字；`Record` 带 `raw`、`metadata`、`error` |
| ③a CSV 栏位 | `io.py:205-248 _table_records()` | `csv.Sniffer` 猜 `, ; \t`；已知结构栏名优先；`--column` 指定；多个候选栏 `raise InputError`；未知栏取前 20 个资料列、各栏非空格值达 80% 可解析且候选唯一才采用 |
| ④ 化学验证 | `io.py:85 _parse_value()` | `MolFromSmiles/MolFromInchi/SELFIES 解码/MolFromMolBlock/MolFromMol2Block/MolFromPDBBlock`；拒绝空分子、>1000 原子、wildcard；SDF 另经 `ForwardSDMolSupplier` |
| ⑤ 性质计算 | `pipeline.py:26 properties()`，于 87 呼叫；86 产生 canonical SMILES | 13 个 RDKit 描述符（分子式、分子量、精确质量、logP、TPSA、HBD/HBA、可旋转键、环数、重原子、电荷、片段数、QED） |
| ⑥ 输出档案 | `pipeline.py:69-172` | 防覆盖检查 → `original_input.bin` 备份 → 逐笔写 sdf/mol/inchi/selfies/png/svg → `molecules.json`、`properties.csv`、`molecules.smi/.inchi/.selfies` |
| ⑦ manifest／错误 | `pipeline.py:173-195` | `errors.json`、`export_errors.json`、`manifest.json`（侦测理由、计数、SHA-256、环境版本、policy、limitations、耗時） |
| ⑧ 结束码 | `chembridge/__main__.py:24-28` | 0 全成功；1 部分／全部记录失败（仍有报告）；2 输入／设定／档案层级错误 |
| ⑨ UI 显示／下载 | `app.py:46-61` | 格式与成功失败数、侦测理由与警告、前 12 张 PNG、性质表、错误清单、manifest、ZIP 下载 |
| ⑩ 模型边界 | `chembridge/model_adapter.py:10 predict_with_fitted_model()` | 独立介面，只被 `tests/test_adapter.py` 呼叫；主流程完全不呼叫，且没有内附模型权重 |

`FORMATS`（`io.py:17`）只有 10 种：`mol, sdf, csv, tsv, smiles, inchi, selfies, json, mol2, pdb`。XYZ／CIF／CML／CDX／PDBQT、结构图片／PDF 确实没有 reader。

## 3. `detect()` 的优先顺序（`io.py:137-197`）

1. 使用者 `--input-format` 强制指定（141–144），完全不看内容。
2. 档名只当「提示」`_hint()`（77–82），`.gz` 先去掉、`smi/sd/sf` 别名。
3. 内容签章**优先于可能误导的副档名**：TRIPOS → mol2、ATOM/HETATM → pdb、`$$$$` → sdf、V2000/V3000 + `M  END` → mol、`{`/`[` 开头的合法 JSON → json。
4. 表格判断：第一非空列含 `\t , ;` 且不是 `InChI=` 开头，且（有已知结构栏名 或 档名像表格 或 多栏）→ csv/tsv。
5. 文字：`InChI=` 前缀、`.selfies`/`.smiles` 档名提示、其他已知档名提示；最后才用首个 token 试解析 SMILES/SELFIES，两者都可解析或都不可解析就 `InputError` 要求明确指定。
6. 档名与内容冲突时加 warning（193–195），`method` 标为 `signature` 或 `heuristic`。

歧义／结构性错误一律抛 `InputError` → CLI exit 2，且**不会建立输出目录**（因为防覆盖检查 `pipeline.py:69` 在 `parse_records` 之后）。逐笔错误则保留在 `Record.error` → `errors.json`，成功记录不删除。

## 4. 文件宣称核对结果

**大致一致**：支援矩阵（含 gzip、MOL2 有限、PDB 需 `--allow-pdb` + CONECT + 单模型）、两个候选结构栏拒绝自选、JSON 每笔只能一个顶层结构栏、输出档案清单、`--out` 防覆盖、CLI exit 0/1/2、13 个性质栏位、manifest 的 policy 与 limitations、canonical SMILES 与资讯损失说明，都能在程式找到对应实作。

**发现的落差／文件未写明的硬限制**（不是 bug，是报告要写清的边界）：

| 项目 | 实际情况 |
|---|---|
| README:66「前 20 笔非空值」 | `io.py:229` 是 `rows[1:21]` = 前 20 个**资料列**；分母是该栏在这 20 列中的非空格数，可能少于 20；80% 门槛一致 |
| README:48 SMI 标头只写 `smiles` | `io.py:318` 也接受首行单 token `inchi`／`selfies` |
| README:72 图片上限 | `pipeline.py:64` 上界是 5000；`drawn` 计数是「处理过的成功记录数」，png/svg 共用，输出失败仍消耗配额；`app.py:37` 只显示前 12 张 PNG |
| README:70–80 输出清单 | `original_input.bin`、`errors.json`、`export_errors.json`、`manifest.json` **无条件写入**，不受 `--outputs` 影响；其余才依条件产生 |
| README:74 逐行表示档 | `pipeline.py:170 if value:` 会略过产生失败的分子 |
| README:79「转换政策」 | `pipeline.py:186-188` 的 policy 是写死在 manifest 的常值，不是可切换旗标；唯一会变化学处理的是 `--allow-pdb` |
| README 未提的硬限制 | `MAX_RECORDS=5000`、单分子 1000 原子上限、拒绝 wildcard/query 原子、重复栏名拒绝、栏宽不符逐笔报错、坏 JSON 拒绝改判为 SMILES、忽略 `#` 注解行、`pyproject.toml:17` 另有 `chembridge` console script、`--input-format smi` 会被 argparse 拒绝（别名只作用于档名） |
| README:82 `mixed_invalid.csv` 预期 exit 1 | `scripts/run_demo.py:12` 只断言成功／失败数；CLI exit 1 是由测试里等效的 `mixed.smi` 验证，本次会直接对 `mixed_invalid.csv` 实跑确认 |
| PDB 预设拒绝 | 拒绝点在 `io.py:305-311 parse_records`，属 `InputError` → **exit 2**，README 未写是哪一个码 |

`docs/Engineering_Starter_Guide_zh.pdf` 第 4 页与第 6 页列出的 `io.py detect/parse_records/_table_records`、`pipeline.py properties/convert_file`、`__main__.py` 与 `app.py` 共用核心流程，与实际函式一致；第 4 页的「两个候选栏不默默选掉」片段对应 `io.py:224-226`。指南第 2 页写 `py -3.12 -m venv .venv`，但本机 `py -0p` 没有注册 3.12（见环境证据），需如实记录偏差。

## 5. 测试与证据现况

- `evidence/test_run.txt`（`39 passed in 1.46s`）与 `evidence/environment.json`（Linux-6.18.57 / Python 3.12.14）是**上游 Linux 预置产物**，不是本机 Windows 执行记录。
- `tests/` 共 39 项：`test_workflow.py` 37 项（含参数化格式变体、防覆盖、CLI 结束码、立体／电荷／同位素／盐／3D 座标往返）、`test_optional_ui.py` 1 项（Streamlit **AppTest**，且用假 `session_state` 注入结果）、`test_adapter.py` 1 项（**fake predictor**）。
- `examples/` 全是数十至数百位元组的合成档；MOL2 与 PDB 测试资料甚至直接写在测试档里。README:93、指南与 `docs/ENGINEERING_PLAN_zh.md:32` 都自承：固定范例只是回归检查，不代表真实世界格式辨识准确率或完整化学保真率。
- `evidence/VALIDATION_SUMMARY.json` 的 `not_completed` 明列 Windows 原机执行、真实浏览器上传下载、真实资料验收、Studio 整合、真模型推论、GitHub push；其 `github_plan.status` 写「无 gh 能力」与本机 `gh` 已登录 `CHANSingYeungSunny` **不符**，报告中须更正，原档不改写。

## 6. Torch Molecule Studio 源码搜寻结论

**没有找到任何可证明是 Studio 的原始码、remote、README 或启动入口。**

- 工作区根只有 `ChemBridge_Engineering_Starter_v0_1_0.zip`、`chembridge_mvp/`、`diagnostics/`、指南 docx/pdf；唯一 ZIP 名称是本工程起步包。
- 全工作区搜 `*studio*` 为 0 个档案；`*torch*` 只有 `docs/TORCH_MOLECULE_SOURCE_MAP_zh.md`（文件）。共 11 个 `.py`，全在 `chembridge_mvp`，没有 Studio 前后端、上传路由或启动入口。
- 没有 `.git` 目录、没有 remote 设定。`docs/TORCH_MOLECULE_SOURCE_MAP_zh.md:11` 原文写「真實程式尚未取得；需要核對實際 repo」；`docs/SOURCES.md:34-48` 只记录上游 `liugangcode/torch-molecule` 固定 commit 的 **URL 连结**，不是本档案案。
- 依提示词第 14 条：本次把 Studio 整合标为**未完成**，只列出欠缺的 repo/ZIP 与为何整合需要它，不新增任何声称「已整合」的档案或路径。

## 7. 结论

没有发现「宣称已實作但完全没写」的格式；主要问题是文件用语精确度、多项未文件化的硬限制，以及所有验证都还停留在合成固定范例与上游 Linux 环境。接下来必须以本机 Windows 真实执行补齐证据，且不得改写上游证据。
