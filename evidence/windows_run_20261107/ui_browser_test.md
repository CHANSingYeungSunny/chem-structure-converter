# 本机界面真实浏览器操作证据（2026-11-07/08，Windows 11）

## 环境与启动方式

- OS：`Windows-11-10.0.26200-SP0`；Python `3.12.14`；`streamlit 1.51.0`；`rdkit 2025.9.4`
- 启动：`start_streamlit.py` 以完全脱离终端的方式执行
  `.venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501 --server.headless true --browser.gatherUsageStats false`
- 服务证据：`streamlit_server.txt` 显示 `URL: http://127.0.0.1:8501`；`/_stcore/health` 回 `ok`
- 浏览器工具：`playwright-cli`（`@playwright/cli` 0.1.18，Node v20.17.0），真实 Chromium 由该工具管理
- 结束：`playwright-cli close` → `Browser 'default' closed`；`taskkill /T /F` 终止 Streamlit 程序树（PID 18332 / 32244 / 24580）

## 真实浏览器操作（不是 AppTest）

操作方式：以 Playwright 对真实页面的 `input[type=file]` 呼叫 `setInputFiles`，再以 `getByRole('button')` 点击「偵測並轉換」；栏位选择用 `getByRole('textbox')` 的 `fill`。

补充说明：`playwright-cli upload` 需要档案选择器的 modal state，而 Streamlit 的 `Choose File` 按钮（快照 `e41`）被拖放区 SVG 图层拦截点击，故改用 `setInputFiles`。这仍是对真实浏览器档案输入设档，不是 mock 或注入 session_state。

| # | 上传样本 | 界面显示 | 结构图／性质／错误 | ZIP 下载 |
|---|---|---|---|---|
| 1 | `molecules.csv` | `格式：csv；成功：5；失敗：0`；侦测理由 `Delimited table; structure column must be resolved.` | 5 张结构图、性质资料表工具列、执行纪录展开器 | 实际下载 `chembridge_results.zip`（79,410 B）→ `downloaded_molecules.zip`；内含 25 档、`manifest.json`、`properties.csv`、`errors.json`、10 个图档（5 PNG + 5 SVG） |
| 2 | `mixed_invalid.csv` | `格式：csv；成功：1；失敗：2`；警告 `部分資料未能轉換；原文及原因已保存在 errors.json。` | 1 张结构图、性质表、错误清单 JSON（含 `record_index`、`name`、`error`、`raw`、`metadata`） | 实际下载 → `downloaded_mixed_invalid.zip`；`errors.json` 2 笔，索引 `[3, 4]`，原文 `['INVALID', '']`；`manifest` 为 `1 / 2 / partial` |
| 3 | `misnamed.csv`（内容是 MOL，副档名是 .csv） | `格式：mol；成功：1；失敗：0`；侦测理由 `MDL version marker and M END.`；警告 `Filename suggests csv, but content suggests mol; content takes priority.` | 1 张结构图、性质表、执行纪录、ZIP 按钮 | 按钮存在（本次未重复下载） |
| 4 | `ambiguous_columns.csv`，**不选栏** | 错误 `Multiple structure columns: smiles, inchi. Select --column (and optionally --column-format).`；**没有产生假成功结果** | 无结果区块 | 无 |
| 5 | `ambiguous_columns.csv`，展开「格式、表格欄位與輸出設定」后在「CSV/TSV 分子欄位名稱」填 `smiles` | `格式：csv；成功：1；失敗：0` | 1 张结构图、性质表、执行纪录、ZIP 按钮 | 按钮存在（本次未重复下载） |

### 视觉证据（真实截图）

| 档案 | 大小 | 对应案例 |
|---|---|---|
| `ui_molecules.png` | 82,593 B | 5 个分子成功 |
| `ui_mixed_invalid.png` | 56,555 B | 混合坏资料与错误清单 |
| `ui_misnamed.png` | 49,934 B | 错副档名侦测为 MOL 与警告 |
| `ui_ambiguous_smiles.png` | 51,570 B | 指定 smiles 栏后成功 |

### 页面快照证据

`ui_snapshot_initial.txt`（未上传、按钮 disabled）、`ui_snapshot_uploaded.txt`（已上传、按钮启用）、`ui_snapshot_result_molecules.txt` / `ui_snapshot_result_molecules_full.txt`、`ui_snapshot_result_mixed_invalid.txt`、`ui_snapshot_ambiguous_no_column.txt`、`ui_snapshot_settings_open.txt`、`ui_snapshot_ambiguous_column_smiles.txt`、`ui_snapshot_result_misnamed.txt`。

### 关键结论

- 图片、性质表、错误清单、侦测理由/警告、执行纪录、ZIP 下载按钮都在真实浏览器出现并可操作。
- 混合坏资料的成功记录与失败记录同时保留，失败的原文与来源 metadata 没有被静默删除。
- 两个结构栏位不默默自选；明确指定 `smiles` 后成功。
- 错副档名以内容签章优先，并在界面显示警告。

## 程式测试（与真实操作分开）

- `tests/test_optional_ui.py` 的 Streamlit **AppTest** 使用假 `session_state["result"]` 注入，只验证标题与 dataframe 出现；它不是真实上传/下载。
- 本机首次 `pytest -q` 为 `1 failed, 38 passed`（AppTest 第二次 `run()` 预设 3 秒超时）；原始失败证据在 `pytest_before_fix.txt`、`commands_and_results_before_fix.md`。
- 以 `diagnose_apptest.py` 实测第二次 `run(timeout=30)` 耗时 5.21 秒且无异常，据此把测试两次 `run` 明确设为 `timeout=30`；修改前原文保存在 `test_optional_ui_before_fix.py.txt`。修复后 `39 passed in 26.93s`。

## 未测项目（不冒充已完成）

- `agent-browser` 在本机未安装（`where.exe agent-browser` 无结果），本次未强行安装以避免改动全域 npm 环境；独立视觉核对由 `playwright-cli` 的截图完成。
- 只测了 `playwright-cli` 预设的 Chromium；未做跨浏览器（Firefox/WebKit/Edge）核对。
- 未测大于 200 MB 的上传、多使用者并发、公开部署、身份验证、工作伫列与 timeout。
- 未测在另一台机器开启下载后的 ZIP；本次是在同一台 Windows 上以 `zipfile` 验证内容。
- 未测真实浏览器中的 PDB 实验性汇入与 MOL2 上传。
