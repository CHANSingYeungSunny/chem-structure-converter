# 可带回 ChatGPT 的执行摘要（依 `prompts/RETURN_RESULTS_TO_CHATGPT_zh.txt` 逐项填答）

> 本摘要**不含任何金钥、access token、个人资料或 email**。上游 Linux 预置证据与本机 Windows 实跑结果分开陈述；固定测试通过率、验收表比率都不等于真实世界准确率、实验药效或模型推论。

## 1. 作业系统／Python／RDKit／SELFIES／Streamlit 版本

本机实跑（**真正测过**）：`Windows-11-10.0.26200-SP0`／Python `3.12.14`／`rdkit 2025.9.4`／`selfies 2.2.0`（pip distribution；模块自报 `2.1.1`，两者都记录在 manifest）／`streamlit 1.51.0`／`pytest 8.4.2`／`Pillow 12.3.0`／`numpy 2.2.6`。
上游交付预置（**非本机**）：`Linux-6.18.57` / Python 3.12.14，见 `evidence/environment.json`。
本机系统另有 Python 3.9、3.10 与 IDE 内建 3.12.14 运行时，**均未改动**。

## 2. 实际执行命令及退出码

| 命令 | 退出码 |
|---|---|
| 系统 Python 3.10 pip + `--target` 跨版本安装 48 个 cp312 wheel（`bootstrap_venv.py`） | `FINAL_EXIT_CODE=0`（完整日志 `bootstrap_install.txt`） |
| `.venv\Scripts\python.exe scripts\first_steps.py` | 0 |
| `.venv\Scripts\python.exe scripts\run_demo.py` | 0 |
| `.venv\Scripts\python.exe -m pytest -q` | 0（修复后） |
| CLI 六条边界命令（`run_cli_checks.py`） | `0, 1, 0, 2, 0, 2` |
| Streamlit `http://127.0.0.1:8501/_stcore/health` | `ok` |

**曾失败并保留证据**：首次 `pytest -q` = `1 failed, 38 passed`（AppTest 3 秒超时）；`.venv\Scripts\python.exe -m pip install` 在本机 CPU 空转、无输出、无网路、无落盘（已终止并改走绕道）。原始输出在 `pytest_before_fix.txt`、`commands_and_results_before_fix.md`、`pip_install.txt`。

## 3. pytest 摘要（通过／失败／跳过）

修复后：**46 passed / 0 failed / 0 skipped，in 32.49s**（`evidence/windows_run_20261107/pytest.txt`）。
修复前：38 passed / 1 failed / 0 skipped。新增 7 个回归测试来自 `tests/test_acceptance_regressions.py`。
上游预置的 `39 passed in 1.46s` 是 Linux 产物，不是本机结果。

## 4. 三个 demo 的 manifest 及成功／失败数

| 输入 | 侦测格式 | 成功／失败 | status |
|---|---|---|---|
| `molecules.csv` | csv | 5 / 0 | complete |
| `mixed_invalid.csv` | csv | 1 / 2 | partial（CLI exit 1，设计结果） |
| `misnamed.csv` | **mol**（档名是 .csv） | 1 / 0 | complete，含副档名冲突警告 |

逐笔 manifest 摘录在 `demo_manifests.json`；`source_records = converted + failed` 可对帐，`original_input.bin` 与输入位元组相同。

## 5. 本机界面是否实际上载／选栏／下载成功

**是，真实浏览器（Chromium，经 `playwright-cli`）实测，不是 AppTest**：上传 `molecules.csv`／`mixed_invalid.csv`／`misnamed.csv`／`ambiguous_columns.csv`，展开设定填入 `smiles` 后转换成功；看到结构图、性质表、错误清单、侦测理由与警告、执行纪录；实际下载两个 `chembridge_results.zip`（79,410 B 与 11,274 B）并以 `zipfile` 验证内容（25 档／13 档、`errors.json` 2 笔含原文）。四张截图与八份页面快照留存。详见 `ui_browser_test.md`。
**程式测试**另计：`tests/test_optional_ui.py` 的 AppTest 用假 `session_state` 注入，只验证标题与 dataframe。
**未测**：跨浏览器、`agent-browser` 通道（未安装）、`start_windows.bat`、大档上传、公开部署。

## 6. 真实工作样本来源、格式与失败案例

**没有使用者真实上传档**（本次确认改以公开＋合成样本，明确标注「非使用者真实资料、不构成真实世界准确率」）：4 个 PubChem 公开 2D SDF（CID 702/1983/2244/3672）、16 个合成边界、3 个上游合成范例，共 23 个档案。来源与授权见 `examples/acceptance/SOURCES.md`。
覆盖：错副档名、缺栏、多分子栏、缺值、无效价态、盐／电荷、立体化学、同位素、3D 座标、SDF metadata、MOL2、gzip、InChI/SELFIES、XYZ、PDB 未 opt-in。
失败案例：`B02` 缺结构栏、`B03` 多结构栏、`B12` XYZ、`B13` PDB 未 opt-in 都正确拒绝；`B05` 五价碳被 RDKit 拒绝并记入 `errors.json`；`B04`／`E02` 混合坏资料的原文与 metadata 保留。
分母与排除规则见 `docs/ACCEPTANCE_MATRIX_zh.md`；比率只适用于这 23 笔，不是真实世界准确率。

## 7. 程式改动档案与原因

| 档案 | 原因 |
|---|---|
| `tests/test_optional_ui.py` | 本机实测 AppTest 第二次 `run` 需 5.21 秒，预设 3 秒造成假失败 → 明确设 `timeout=30`；修改前原文隔离保存在 `test_optional_ui_before_fix.py.txt` |
| `tests/test_acceptance_regressions.py`（新增） | 7 个以真实 CLI／范例档为依据的回归：结束码、歧义拒绝、坏资料保留、防覆盖、错副档名 |
| `.gitignore` | 新增 `.tmp/`、`.pipcache/`、`.playwright-cli/` 忽略规则 |
| `README.md` | 更正「Windows 尚未实测」「GitHub 推送尚未完成」等过时宣称，补本机结果与可重跑脚本 |
| `docs/` 四份、`evidence/windows_run_20261107/`、`examples/acceptance/` | 交付文件、本机证据与验收样本 |

**`chembridge/` 核心逻辑、`requirements*.txt`、`pyproject.toml`、`app.py`、`scripts/` 均未改动**。README 更新后其 SHA-256 与上游 `PACKAGE_MANIFEST.json` 的原始值不再一致，该清单保留为上游基准。

## 8. 真正 Torch Molecule Studio repo／ZIP 及已确认入口

**没有。** 工作区只有工程起步包与 `chembridge_mvp`；搜 `*studio*` 为 0 个档案，11 个 `.py` 全在 `chembridge_mvp`，没有 Studio 前后端、上传路由、启动入口或 remote；`docs/TORCH_MOLECULE_SOURCE_MAP_zh.md:11` 自承「真實程式尚未取得」。`docs/SOURCES.md` 只有上游 `liugangcode/torch-molecule` 固定 commit 的 URL，那是 Python 套件，**不是 Studio**。

## 9. 已完成整合的实际路径／流程，或仍欠缺资料

**整合状态：未完成。** 没有新增任何声称「已整合」的路径或流程。`README.md:97-102` 与 `chembridge/model_adapter.py` 只是可整合的界面建议。
仍需：真正 Studio 的 repo URL 或 ZIP，以及其 `remote`、`README`、启动入口、前后端框架、上传路由与资料契约。有了之后才能在真实路由上加「上传 → 预览 → 选栏 → 转换 → 下载」，后端重用 `convert_file`、每个 job 隔离目录、输出结构化错误与 manifest；公开部署前另需工作伫列、timeout、身份验证、档案隔离与负载限制。

## 10. 我能解释的核心函式与目前不懂之处

**能解释**（白话与行号见 `docs/DELIVERY_REPORT_zh.md` 第 4 节与 `DEMO_SCRIPT_zh.md`）：`io.py:53 decode_bytes` / `:72 load_text`（解码、gzip、20 MiB 上限）；`io.py:137 detect`（内容签章优先于副档名）；`io.py:200 _table_records`（选栏、两个候选拒绝、80% 启发式）；`io.py:85 _parse_value` / `:253 parse_records`（逐笔建分子、坏资料保留原文）；`pipeline.py:26 properties`（13 个 RDKit 描述符）；`pipeline.py:48 convert_file`（防覆盖、输出、manifest）；`__main__.py:28`（exit 0/1/2）；`app.py`（上传→预览→ZIP）。

**仍不懂／尚未验证**：真正 Studio 的框架与资料契约；各供应商 SDF/MOL2/PDB 的真实差异与键级真值；XYZ／PDB 键级推论该如何在输出中正确标示信心；图片／PDF 结构辨识的可靠流程；`torch-molecule` 真模型的预测目标、单位、checkpoint 与适用范围；本机 venv pip 启动器空转的底层原因（已绕过，未根治）。

## 11. 新 GitHub repo URL／visibility／branch／commit SHA

**待第五阶段完成后填入，不预先编造。** 见 `docs/DELIVERY_EVIDENCE_zh.md`。

## 12. git push 及远端 SHA 核对结果

**待第五阶段完成后填入**（`gh repo view`、`git remote -v`、`git ls-remote` 与本机 `HEAD` 比对）。见 `docs/DELIVERY_EVIDENCE_zh.md`。

## 13. 从全新 clone 建环境、跑 demo／pytest 的真实结果

**待第五阶段完成后填入**（全新目录 clone、依 README 建环境、跑 demo 与 pytest，不得以原工作区结果冒充）。见 `docs/DELIVERY_EVIDENCE_zh.md`。

---

## 真正测过 vs 未测（分开列）

**真正测过**：本机 3.12 环境安装与版本、三个实跑命令、46 个测试、CLI 六条结束码与防覆盖、真实浏览器上传／选栏／性质／结构图／错误／ZIP 下载及内容、23 笔验收表各维度、PDF 指南全文、Studio 源码搜寻、`gh` 登录账号与仓库名可用性核对。

**只有程式测试**：Streamlit AppTest（假 session_state）、`model_adapter` 的 fake predictor、固定合成 fixtures。

**未测**：Studio 整合、真模型推论、真实使用者上传分布、图片/PDF 辨识、跨浏览器、大档与多使用者、公开部署、`start_windows.bat`、`agent-browser`、Excel 公式快取值重算（无 LibreOffice）。

## 下一个最重要的改进

**先收集使用者实际会上传的档案与格式分布，建立真正的「人工标注验收集」，再据以重新评估格式识别／拒绝／误接受与下一个该支援的格式。** 理由：目前所有比率都建立在 23 个公开＋合成档案上，且 `46 passed` 只是回归检查；没有真实分布，就无法判断该优先补 XYZ、MOL2 还是其他格式，也无法把「误接受率」说成真实世界指标。这比先改程式、先接 Open Babel 或先接模型都更重要。

其次（但依赖外部资料）是取得真正 Studio 的 repo／ZIP，才能把整合从「界面建议」变成可验证的流程；在两者到位之前，不应宣称支援更多格式、不宣称真实准确率，也不应把 RDKit 描述符或 fake predictor 当成实验药效／模型推论。
