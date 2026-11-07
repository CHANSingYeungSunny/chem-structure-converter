# 验收样本来源说明（2026-11-08）

> **重要声明**：本目录的档案**不是使用者实际上传的真实工作资料**。它们来自公开资料库与人工合成边界案例，只用于本机工程验收与回归检查。**不得据此宣称真实世界格式辨识准确率、误接受率或化学保真率**，也不代表任何真实上传分布。

## A. 公开来源结构档（PubChem PUG REST，NLM/NIH）

取得方式：本机以 `urllib` 呼叫 PubChem PUG REST，取得日期 2026-11-08（香港时间）。PubChem 资料为美国国家医学图书馆公开资料，依其公开政策可自由取用；此处仅保存 2D SDF 供格式读取验证，不重新发布为资料集。

| 档案 | CID | 化合物 | 来源 URL |
|---|---|---|---|
| `pubchem_cid_702_2d.sdf` | 702 | Ethanol | `https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/702/SDF?record_type=2d` |
| `pubchem_cid_1983_2d.sdf` | 1983 | Caffeine | `https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/1983/SDF?record_type=2d` |
| `pubchem_cid_2244_2d.sdf` | 2244 | Aspirin | `https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/2244/SDF?record_type=2d` |
| `pubchem_cid_3672_2d.sdf` | 3672 | Ibuprofen | `https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/3672/SDF?record_type=2d` |

这些是**单笔 2D SDF**，含 PubChem 的 SDF 属性栏位；不含 3D 座标，也不代表多笔 SDF、供应商 SDF 或实验座标档的复杂度。

## B. 人工合成边界案例

由 `evidence/windows_run_20261107/build_acceptance.py` 产生在 `boundary/` 子目录，每笔都有人工标注的预期结果与排除规则（见 `evidence/acceptance_matrix.xlsx` 与 `docs/ACCEPTANCE_MATRIX_zh.md`）。涵盖：

- 错副档名、缺结构栏、多个结构栏、缺值、无效价态、坏资料混合
- 盐／电荷、立体化学、同位素、多片段
- 3D 座标、SDF metadata、gzip
- 两种不同写法的 MOL2
- 不支援格式（XYZ）、PDB 未显式允许时的拒绝
- InChI／SELFIES 文字

## C. 专案原有合成范例

`../`（`examples/` 根目录）原有的 14 个档案全部是上游交付的合成小档（数十至数千位元组），用于三个 demo 与固定单元测试，同样**不是真实工作资料**。

## D. 排除规则

1. 不纳入任何私人资料、使用者上传档、实验测量值或模型预测值。
2. 不把「固定单元测试通过率」写成格式辨识准确率；39→46 个测试只代表回归检查。
3. 每笔样本以「档案」为分母单位；多笔 SDF 内的分子数另计，不混为独立格式档数。
4. 往返一致性以 RDKit `InChIKey`／canonical SMILES 比对化学图，不以原始档案逐位元相同或字串相同为准。
5. 对「预期拒绝」的样本不计算读取成功率；对「预期接受」的样本不计算拒绝率；不适用的维度记为 `NA`，不列入该维度分母。
