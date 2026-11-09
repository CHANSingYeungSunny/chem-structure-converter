# ChemBridge

输入小分子结构档，自动判定格式、逐笔验证，输出结构图、其他化学格式与性质表。化学解析由 RDKit 负责，不需要 API 密钥或 GPU。

## 安装

需要 Python 3.12（64-bit）。在专案根目录开启 PowerShell：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-ui.txt
```

- 只用命令列、不开网页界面：改装 `-r requirements.txt` 即可。
- macOS / Linux：`python3 -m venv .venv`，之后把 `.venv\Scripts\python.exe` 换成 `.venv/bin/python`。
- 第一次安装需要网络；转换本身不需要。

## 跑两个例子

仓库内附两份公开资料集（MoleculeNet），可直接拿来跑：

**1. ESOL，1,128 笔，全部成功**

```powershell
.\.venv\Scripts\python.exe -m chembridge tmp_manual_test\delaney-processed.csv --out runs\esol_run
```

**2. BBBP，2,050 笔，其中有坏资料**

```powershell
.\.venv\Scripts\python.exe -m chembridge tmp_manual_test\BBBP.csv --out runs\bbbp_run
```

BBBP 的结果是 `partial`（部分成功，CLI 退出码 1），这是设计结果、不是错误：11 笔无法解析的资料连同原文与列号留在 `errors.json`，其余 2,039 笔照常输出。

每次 `--out` 都要给一个**还不存在的目录**，避免覆盖旧结果。跑完看该目录里的 `manifest.json`（判定理由、成功／失败数）和 `properties.csv`（性质表）。大档约需 1–2 分钟。

### 网页界面（可选）

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1
```

开 `http://127.0.0.1:8501`，上传上面任一个 CSV，按「偵測並轉換」，可下载结果 ZIP。

## 输入范围

支持 MOL、SDF、CSV/TSV、SMILES／InChI／SELFIES 文字、JSON，以及这些文字档的 gzip；MOL2 有限支持，PDB 需 `--allow-pdb`。不支持 XYZ、CIF、CML、CDX、PDBQT、结构图片与 PDF。

表格必须有真正的结构栏（`smiles`、`inchi`、`molblock` 等）；只有名称或分子式的表格无法还原结构。若有两个候选结构栏，要用 `--column smiles` 指定。

## 输出

`--out` 目录里会有 `manifest.json`、`molecules.json`、`properties.csv`、`errors.json`、`export_errors.json`、`images/*.png|svg`（预设最多 100 张）、`mol/*.mol`、`molecules.sdf`、`molecules.smi|inchi|selfies`，以及原档备份 `original_input.bin`。

只要部分输出可加 `--outputs csv,json,png`，调整图片数用 `--image-limit 20`。退出码：0 全成功、1 部分失败、2 输入或设定错误。

性质是 RDKit 计算值，不是实验测量或药效预测；转档可能丢失座标与属性，不宣称无损转换。
