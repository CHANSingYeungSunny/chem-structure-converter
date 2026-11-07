# torch-molecule：用這個專案學會看框架

本次核對上游 `https://github.com/liugangcode/torch-molecule` 的 main 快照：`e3466e386c18d449d6e6889446f1109551714efc`。查閱日期：2026-11-06（香港）。`main` 會變動；以下是這個快照的讀碼地圖。不是宣稱已讀完所有模型，亦未執行上游訓練。

## 三個角色

| 元件 | 角色 | 本題位置 |
|---|---|---|
| RDKit | 分子讀寫、圖結構、繪圖、描述符計算 | 第一版的核心引擎 |
| torch-molecule | Predictor／Encoder／Generator 模型與訓練介面 | 後續需要學習式預測時接入 |
| Torch Molecule Studio | 使用者操作與工作流程的應用層 | 真實程式尚未取得；需要核對實際 repo |

「學框架」不是先背模型名稱，而是跟著一筆資料走：結構文字 → 解析 → 分子圖 → 原子／鍵特徵 → 模型 → 預測值 → 附上目標與單位。

## 最小概念

SMILES `CCO` 表達乙醇的連接關係。RDKit 讀取後得到 Mol，內含原子及鍵；圖片只是這個圖的一種展示。CSV 則是多筆資料的容器，不能把任意 CSV 直接送進模型。

Predictor 把分子映射成目標，例如某個明確定義的溶解度。Encoder 把分子映射成向量，用於相似度或下游學習。Generator 產生分子候選。三者都不是「通用檔案轉換器」。

## 讀碼順序與對應問題

| 上游檔案／目錄 | 找甚麼 | 你要能回答 |
|---|---|---|
| `torch_molecule/__init__.py` | 對外匯出的類別 | 為何可以 `from torch_molecule import GNNMolecularPredictor`？ |
| `base/base.py` | `BaseModel`、參數、device、checkpoint、fitted 檢查 | 模型的設定與訓練權重有何分別？ |
| `base/predictor.py` | 預測模型共用介面 | `fit()` 和 `predict()` 各需要甚麼？ |
| `predictor/gnn/modeling_gnn.py` | 具體 `fit`、`predict`、資料轉換 | SMILES 如何進入 GNN？ |
| `utils/graph/graph_from_smiles.py` | 原子、雙向邊、鍵特徵 | 圖不是圖片；`edge_index` 儲存甚麼？ |
| `datasets/hub.py` | `load_dataset()`、目標與來源切分 | 資料從哪裡來？標籤是甚麼？ |
| `datasets/split.py` | random／scaffold／butina／size | 驗證集怎樣與訓練集分開？ |
| `encoder/`、`generator/`、`nn/` | 其他任務與神經網路元件 | 為何第一版不必改這些？ |

本次實際下載檢視了上表的 7 個 `.py` 檔（含 `__init__.py`）；其餘目錄只做結構定位。上游原始碼不複製入本包，請用 SOURCES.md 的固定 commit 連結閱讀。

## 圖資料怎麼建

在 `graph_from_smiles()`，字串先進入 `Chem.MolFromSmiles()`；程式走訪每個原子建立 node features，再走訪每條化學鍵。每條化學鍵加入兩個方向，例如 C0→C1 與 C1→C0，方便訊息傳遞。

輸出字典包含 `node_feat`、`edge_index`、`edge_feat`、`num_nodes`。若化學圖有 N 個原子與 E 條鍵，節點矩陣有 N 列；`edge_index` 形狀為 `[2, 2E]`。這不是把分子 PNG 丟進模型。

## 預測工作流程

1. 匯入有效結構；保留錯誤與來源 ID。
2. 定義目標、單位、標籤來源；確認不是把 RDKit 自己算的值當作新發現。
3. 在訓練前切分資料，並讓重複結構／相關測量留在同一組。
4. 用 train 訓練、validation 選參數，最後只用一次獨立 test 評估。
5. 保存 checkpoint、資料切分、環境、目標單位和訓練範圍。
6. 新分子轉為相同輸入格式後，才用正確 checkpoint 推論，並標示模型來源。

具體 GNN 的 `predict()` 在此快照回傳字典，應檢查其中 `prediction` 的維度。`model_adapter.py` 原樣保留預測回傳，沒有假設所有模型共用同一形狀，也沒有替你下載／訓練模型。

## 資料切分：初學者最容易誤解的地方

| 方法 | 白話 | 注意 |
|---|---|---|
| random | 隨機分資料列 | 重複分子可能跨集合，分數可能過度樂觀 |
| scaffold | 依分子骨架分組 | 較能檢查未見過骨架，但不等於所有結構洩漏都消失 |
| butina | 依指紋相似度聚類後分組 | 需理解相似度門檻與運算成本 |
| size | 依重原子數分開 | 檢查對較大／較小分子的外推 |

此快照的 `train_test_split()` 實際回傳 train 與 holdout **兩份**；若將 holdout 交給 `X_val/y_val` 選參數，它就是 validation，不應再把同一份當作未碰過的最終 test。原始 `groups` metadata 也不會自動決定列的分組，要自行核對。

格式轉換 MVP 不需要訓練／驗證／測試集。它需要的是：已知正確輸入、壞資料、歧義案例與轉換前後一致性檢查。只有加入學習式模型，才需要上述 ML 切分。

## 你現在要做到的程度

先能解釋 `scripts/first_steps.py` 的五個步驟，再能指出 `io.py` 的 detect/parse 與 `pipeline.py` 的計算／輸出，最後閱讀上游 graph_from_smiles。先不用安裝整套 torch-molecule 重型環境；等預測目標與 checkpoint 明確後，在另一個環境測試。
