# 官方來源與閱讀優先次序

查閱日期：2026-11-06（香港）。先讀官方使用流程，再讀基礎論文；此清單不是 2026 年前沿趨勢綜述。

1. **RDKit Getting Started in Python**
   https://www.rdkit.org/docs/GettingStartedInPython.html
   先看 Reading, Drawing, and Writing Molecules。讀完要能自己從 CCO 產生 Mol、檢查 None、畫圖、寫 MOL/SDF。
2. **RDKit molecular file API**
   https://www.rdkit.org/docs/source/rdkit.Chem.rdmolfiles.html
   查 MolFromSmiles/MolFromMolBlock/MolFromMol2Block/MolFromPDBBlock/SDWriter 的實際參數與限制。文件可能較本包固定的 RDKit 2025.09.4 新；本包採用已實測功能。
3. **torch-molecule repository and official docs**
   https://github.com/liugangcode/torch-molecule
   https://liugangcode.github.io/torch-molecule/
   三類模型與 sklearn 風格 API；本包未訓練該套件模型。
4. **Open Babel command-line documentation**
   https://openbabel.org/docs/Command-line_tools/babel.html
   比較既有格式互轉能力及明確指定 input/output 的方式。下一階段候選依賴，尚未在本工具中安裝或整合。
5. **O'Boyle et al. (2011). Open Babel: An open chemical toolbox.**
   DOI: 10.1186/1758-2946-3-33
   https://pmc.ncbi.nlm.nih.gov/articles/PMC3198950/
   基礎閱讀：為何格式很多、不同格式承載資訊不同，以及工程中既有轉換工具的定位。
6. **Lo et al. (2023). Recent advances in the Self-Referencing Embedding Strings (SELFIES) library.**
   DOI: 10.1039/D3DD00044C
   https://arxiv.org/abs/2302.03620
   基礎閱讀：SELFIES 語法、語義限制、版本特性。可解碼不代表與使用者原意相符或具有藥效。
7. **Bickerton et al. (2012). Quantifying the chemical beauty of drugs.**
   DOI: 10.1038/nchem.1243
   https://pubmed.ncbi.nlm.nih.gov/22270643/
   性質背景閱讀：QED 用來描述 drug-likeness，不是有效性或安全性證明。
8. **SELFIES official source**
   https://github.com/aspuru-guzik-group/selfies
   本包固定 pip distribution 2.2.0；其模組自報 2.1.1，manifest 同時記錄，避免混淆。

## 本次上游原始碼核對

固定 commit：`e3466e386c18d449d6e6889446f1109551714efc`。

以下連結可直接查閱讀碼地圖對應的程式：

- https://github.com/liugangcode/torch-molecule/blob/e3466e386c18d449d6e6889446f1109551714efc/torch_molecule/__init__.py
- https://github.com/liugangcode/torch-molecule/blob/e3466e386c18d449d6e6889446f1109551714efc/torch_molecule/base/base.py
- https://github.com/liugangcode/torch-molecule/blob/e3466e386c18d449d6e6889446f1109551714efc/torch_molecule/base/predictor.py
- https://github.com/liugangcode/torch-molecule/blob/e3466e386c18d449d6e6889446f1109551714efc/torch_molecule/predictor/gnn/modeling_gnn.py
- https://github.com/liugangcode/torch-molecule/blob/e3466e386c18d449d6e6889446f1109551714efc/torch_molecule/utils/graph/graph_from_smiles.py
- https://github.com/liugangcode/torch-molecule/blob/e3466e386c18d449d6e6889446f1109551714efc/torch_molecule/datasets/hub.py
- https://github.com/liugangcode/torch-molecule/blob/e3466e386c18d449d6e6889446f1109551714efc/torch_molecule/datasets/split.py

原始碼查閱用於核對介面及教學說明，不是上游所有模型的重現結果。本包由 RDKit/SELFIES API 組成自己的工程流程；未複製上游框架原碼。
