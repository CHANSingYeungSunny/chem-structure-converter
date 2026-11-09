# ChemBridge：化學結構格式偵測與轉換工程原型

目標：輸入常見的小分子結構檔案，自動辨認、驗證，輸出圖片、其他結構格式及性質表。

這是可獨立執行的 MVP v0.1.0，適合之後整合到 **Torch Molecule Studio**。它不是該 Studio 的原始碼，也尚未完成 Studio 整合。`liugangcode/torch-molecule` 是分子機器學習套件；本工具的格式處理由 RDKit 負責，預測模型透過獨立 adapter 日後接入。

## 先看哪裡

1. 零基礎先讀 `docs/Engineering_Starter_Guide_zh.pdf`，或可編輯 Word 同名檔。
2. 用下列命令執行 `scripts/first_steps.py`，理解「文字 → 分子圖 → 計算／畫圖」。
3. 執行 `scripts/run_demo.py`，打開輸出圖片、性質表及錯誤清單。
4. 看 `chembridge/io.py`、`chembridge/pipeline.py`，對照指南的核心程式。
5. 把 `prompts/DEEPSEEK_EXECUTION_PROMPT_zh.txt` 交給有檔案／終端機權限的 coding agent，繼續做驗收及 Studio 整合。

## Windows 安裝與執行

建議另建 **Python 3.12、64-bit** 環境，避免改動你之前的 Python 3.13 專案。先安裝 Python 3.12，再解壓到一般資料夾，例如 `C:\Projects\chembridge_mvp`。在此資料夾開啟 PowerShell，逐行執行：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-ui.txt
.\.venv\Scripts\python.exe scripts\first_steps.py
.\.venv\Scripts\python.exe scripts\run_demo.py
.\.venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1 --browser.gatherUsageStats false
```

瀏覽器開啟終端機顯示的本機地址（通常 `http://127.0.0.1:8501`），上傳 `examples/molecules.csv`，按「偵測並轉換」，然後下載結果 ZIP。完成首次安裝後也可雙擊 `start_windows.bat`。第一次安裝需要網路；轉換不需要 API 金鑰或 GPU。交付 ZIP 不含 Python、第三方安裝輪或虛擬環境。

不用網頁介面時，僅安裝 `requirements.txt`，執行 CLI：

```powershell
.\.venv\Scripts\python.exe -m chembridge examples\molecules.csv --out runs\first_run
.\.venv\Scripts\python.exe -m chembridge examples\mixed_invalid.csv --out runs\mixed_run
.\.venv\Scripts\python.exe -m chembridge examples\ambiguous_columns.csv --column smiles --out runs\chosen_run
```

每次 `--out` 必須是尚未存在的資料夾；這是避免覆蓋的設計。例子若已跑過，請換 `second_run` 等名稱。

macOS/Linux：`python3 -m venv .venv`，接著用 `.venv/bin/python` 執行同樣的 pip、demo 和 `-m chembridge` 命令。上游交付的 `39 passed` 與 `evidence/environment.json` 來自 Linux / Python 3.12；**本机 Windows 11 / Python 3.12.14 已另行实跑完成**（`46 passed in 32.49s`、三个 demo、真实浏览器上传／选栏／下载、23 笔验收表），证据在 `evidence/windows_run_20261107/` 与 `docs/DELIVERY_REPORT_zh.md`。`start_windows.bat` 未单独实测；本机以 `python -m streamlit run app.py` 启动成功。

## 輸入範圍

| 輸入 | 本版狀態 | 偵測／限制 |
|---|---|---|
| MOL，V2000/V3000 | 已實作及範例測試 | 版本標記、M END；單一分子 |
| SDF/SD | 已實作及範例測試 | $$$$ 分隔；逐筆錯誤保留；保留可讀 SD 屬性 |
| CSV/TSV（含分號分隔） | 已實作及範例測試 | 必須有欄名；辨認 SMILES/InChI/SELFIES/molblock 欄 |
| SMI/SMILES | 已實作及範例測試 | 每行 `SMILES 可選名稱`；可有第一行單一 `smiles` 標頭 |
| InChI 文字 | 已實作及範例測試 | `InChI=` 前綴；每行一筆 |
| SELFIES 文字 | 已實作及範例測試 | 建議 `.selfies` 或明確指定，避免與括號 SMILES 混淆 |
| JSON | 已實作及範例測試 | 見下列專案 schema；不代表任意供應商 JSON 都支援 |
| 上述文字的 gzip | 已實作及範例測試 | gzip magic；壓縮及解壓後各有 20 MiB 上限 |
| MOL2 | 有限支援／合成範例測試 | 依 RDKit 相容原子型別；不保證保留力場／部分電荷資訊 |
| PDB | 實驗性／預設拒絕 | 需 `--allow-pdb`、CONECT、單模型；鍵級仍需核對；非蛋白質工具 |
| XYZ、CIF/mmCIF、CML、CDX/CDXML、PDBQT | 尚未支援 | 下一階段依需求評估 Open Babel 或專用 reader |
| 結構圖片、掃描 PDF、一般 Word/PDF 化學文件 | 尚未支援 | 需要結構辨識或文件抽取；不是普通檔案互轉 |

CSV 是容器，不是分子表示。例如 `id,name,SMILES` 中只有 SMILES 欄能建構分子。表格只有分子式、化合物名稱或 CAS 編號，不能唯一還原結構，本版會要求提供真正的結構資料。兩個候選結構欄位會拒絕自選；請加 `--column 欄位名稱`，必要時加 `--column-format smiles`。

輸入 JSON 可以是單一物件、物件陣列，或 `{"molecules": [...]}`。**每筆只能有一個**頂層結構欄位 `smiles`、`inchi`、`selfies`、`molblock`：

```json
{"molecules": [{"name": "ethanol", "smiles": "CCO", "supplier": "demo"}]}
```

其他欄位保存在輸出 JSON 的 `metadata`。CSV 優先採用已知結構欄名；未知欄名會用前 20 筆非空值做啟發式取樣，必須只有一個欄達到 80% 可解析率。這不是機率信心，也不保證未知表格都能辨認；不確定時明確指定欄位。

## 輸出與讀取方法

| 輸出 | 用途 |
|---|---|
| `images/m00001.png`、`.svg` | 2D 結構圖；預設最多前 100 個成功分子 |
| `mol/m00001.mol`、`molecules.sdf` | 給其他化學工具讀取；有座標則保留，無座標則生成 2D |
| `molecules.smi/.inchi/.selfies` | 每行一筆分子表示及內部 ID |
| `properties.csv` | 分子式、分子量、精確質量、RDKit logP、TPSA、HBD/HBA、可旋轉鍵、環數、重原子、電荷、片段數、QED |
| `molecules.json` | 成功分子的表示、性質、來源 metadata、警告與輸出路徑，可再次匯入 |
| `errors.json` | 失敗的來源記錄索引、原文、原因、metadata；CSV 索引含標頭 |
| `export_errors.json` | 已讀懂分子，但某個輸出格式失敗的原因 |
| `manifest.json` | 格式偵測理由、警告、計數、版本、輸入 SHA-256、耗時、轉換政策 |
| `original_input.bin` | 完整原始輸入備份；原檔名在 manifest 中 |

只需要部分輸出：`--outputs csv,json,png`。需要更多圖片：`--image-limit 500`。成功與否請看 manifest，不要只看資料夾出現。CLI 退出碼：0=全部成功；1=部分／全部記錄失敗或輸出失敗（仍有報告）；2=輸入、設定或檔案層級錯誤。`mixed_invalid.csv` 預期退出 1，這代表正確報告兩筆壞資料。

性質是依輸入結構計算／估計的數值，不等於實驗測量、毒性安全、藥效或 torch-molecule 模型預測。鹽、電荷和互變異構體不會自動標準化；重複分子也保留。Canonical SMILES 不等於完整化學身分標準化，且可能受 RDKit 版本影響。轉換到不同格式可能失去座標、屬性、原子順序等資訊；本版不宣稱普遍無損轉換。

## 驗證

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
```

UI 測試在未安裝 Streamlit 時會跳過；裝了 `requirements-ui.txt` 則執行。`evidence/` 頂層是**上游 Linux 預置產物**（`environment.json`、`test_run.txt` 的 `39 passed`），不是本机 Windows 实跑；本机结果另存于 `evidence/windows_run_20261107/`。这些是小型固定范例的工程验证，不能当成真实世界格式辨识准确率或完整化学保真率。

本机可重跑的验证脚本（都用 `.venv\Scripts\python.exe` 执行）：

```powershell
.\.venv\Scripts\python.exe evidence\windows_run_20261107\run_verification.py       # first_steps / run_demo / pytest
.\.venv\Scripts\python.exe evidence\windows_run_20261107\run_cli_checks.py         # CLI 结束码与防覆盖
.\.venv\Scripts\python.exe evidence\windows_run_20261107\build_acceptance.py       # 23 笔验收表与 xlsx
```

本机实跑结果：`46 passed in 32.49s`；三个 demo 为 `5/0`、`1/2`、`1/0（侦测 mol）`；CLI 结束码 `0,1,0,2,0,2`；真实浏览器上传／选栏／ZIP 下载成功；详见 `docs/DELIVERY_REPORT_zh.md`。

> 本机环境备注：这台 Windows 上 `.venv\Scripts\python.exe -m pip install` 会异常空转，因此安装改用系统 Python 3.10 的 pip 搭配 `--target` 与 cp312 wheel 标签，把官方 wheel 直接装进 venv 的 `site-packages`；完整日志在 `evidence/windows_run_20261107/bootstrap_install.txt`。系统 Python 3.9／3.10 没有因此被修改。

## Torch Molecule Studio 整合界面

```python
from chembridge import convert_file
manifest = convert_file("uploaded_file.sdf", "a_new_job_directory", outputs="json,csv,png,sdf")
```

Studio 的後端可先將上傳檔存入獨立 job 目錄，再呼叫此函式，顯示 manifest／錯誤／圖像並提供下載。正式服務仍需工作佇列、timeout、權限隔離、上傳檔驗證和大資料串流處理。本地 MVP 不等於可直接公開部署的多使用者服務。

`chembridge/model_adapter.py` 接受**呼叫者已訓練或正確載入的 predictor**，將成功記錄的 SMILES 依 ID 順序送入 `predict()`，並要求目標、單位和 checkpoint ID。此處只有介面與 fake predictor 測試，未執行真正 torch-molecule 模型推論，也沒有內附模型權重。

請先取得真正 Studio 的 repo／ZIP，再用提示詞做整合。不要把第三方 torch-molecule fork 或舊 benchmark 專案當作 Studio 原始碼。

## 進一步學習

`docs/TORCH_MOLECULE_SOURCE_MAP_zh.md`：套件結構與讀碼順序。

`docs/ENGINEERING_PLAN_zh.md`：七日進度、交付驗收、研究延伸。

`docs/GITHUB_DELIVERY_zh.md`：建立新倉庫 **chem-structure-converter**、git push，以及從全新 clone 驗證的具體步驟。實際 repo URL、visibility、branch、commit SHA、push 核對與乾淨 clone 重現結果見 `docs/DELIVERY_EVIDENCE_zh.md`；該檔在推送完成後才填入真實值，未填即代表該步驟未完成。

`docs/SOURCES.md`：官方文件、基礎論文、已檢視的上游 commit。

本包是完整的入門工程原型交付，尚未涵蓋任意化學文件、完整 Studio 整合、機器學習模型、或學術發表結果。
