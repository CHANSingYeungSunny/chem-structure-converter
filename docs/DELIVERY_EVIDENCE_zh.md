# 交付 E：GitHub 仓库与干净 clone 重现证据

**状态：已完成。** 以下全部是 2026-11-08 本机真实命令的输出，不是预先填写的示例。

| 项目 | 真实结果 |
|---|---|
| repo URL | `https://github.com/CHANSingYeungSunny/chem-structure-converter` |
| visibility | `private`（`gh repo view` 回 `isPrivate: true`） |
| branch | `main` |
| 首次推送 commit SHA（也是干净 clone 验证用的 HEAD） | `abcefd444b1e1c0d1b614912964b86130107c4c7` |
| 建立远端 | `gh repo create CHANSingYeungSunny/chem-structure-converter --private --source . --remote origin` → 回传上述 URL |
| 推送 | `git push -u origin main` → `* [new branch] main -> main`，`branch 'main' set up to track 'origin/main'` |
| `gh repo view --json nameWithOwner,url,isPrivate` | `{"isPrivate":true,"nameWithOwner":"CHANSingYeungSunny/chem-structure-converter","url":"https://github.com/CHANSingYeungSunny/chem-structure-converter"}` |
| `git remote -v` | `origin https://github.com/CHANSingYeungSunny/chem-structure-converter.git (fetch)` 与 `(push)` |
| 本机 `git rev-parse HEAD` | `abcefd444b1e1c0d1b614912964b86130107c4c7` |
| `git ls-remote origin refs/heads/main` | `abcefd444b1e1c0d1b614912964b86130107c4c7	refs/heads/main` → **与本机 HEAD 一致** |
| 全新 clone 目录 | `c:/Users/Asus/Desktop/Chembridge/chem-structure-converter-check`（`gh repo clone ...`） |
| clone 后 `git rev-parse HEAD` | `abcefd444b1e1c0d1b614912964b86130107c4c7`（与远端一致） |
| clone 后建环境 | `py -3.12 --version` 回 `No suitable Python runtime found`（本机未注册 3.12）；改用 IDE 内建 3.12.14 运行时执行 `python -m venv --without-pip .venv` → `Python 3.12.14`；再以交付包内 `evidence/windows_run_20261107/bootstrap_venv.py` 用系统 Python 3.10 的 pip 搭配 `--target` 安装 48 个 cp312 wheel → `STAGE_EXIT_CODE=0`、`SITE_ITEMS=106` |
| clone 后 `run_demo.py`（经 `run_verification.py`） | `exit 0`：`molecules.csv` csv 5/0、`mixed_invalid.csv` csv 1/2、`misnamed.csv` mol 1/0 |
| clone 后 `pytest -q` | `46 passed in 39.31s`，`EXIT_CODE: 0` |
| clone 后 `first_steps.py` | `exit 0` |
| 未完成范围 | Torch Molecule Studio 整合、真实使用者上传样本验收、真模型推论、图片／PDF 辨识、跨浏览器与公开部署等，见 `docs/DELIVERY_REPORT_zh.md` 第 6 节 |

## 推送前检查（真实执行）

- `gh auth status` → 已登录 `CHANSingYeungSunny`（keyring，https）；`gh api user --jq .login` → `CHANSingYeungSunny`。账号符合预期，**未显示或写入任何 token**。
- `gh api repos/CHANSingYeungSunny/chem-structure-converter` → HTTP 404，名称未被占用，没有覆盖任何既有仓库。
- 父目录 `git rev-parse --show-toplevel` → `fatal: not a git repository`，确认不是不相关 repo 的子目录；新的本机 repo 建在含 `README.md` 的 `chembridge_mvp/`。
- 扫描无 `.env`、`*.pem`、`*.key`；`.gitignore` 排除 `.venv/`、`.tmp/`、`.pipcache/`、`.playwright-cli/`、`pip-*/`、`pytest-of-*/`、`runs/`、`*.log` 等。
- `git add` 只用明确交付路径，共 168 个档案；`git diff --cached --stat` → `168 files changed, 8814 insertions(+)`；`git diff --cached` 已检视 `tests/test_optional_ui.py` 与 `.gitignore` 的差异。staged 清单中的 `.png`／`.zip`／`pip_install.log` 都是刻意纳入的证据档。

## 关于「最终 commit SHA」

本证据档与 `docs/RETURN_RESULTS_FILLED_zh.md` 的第 11–13 项随**第二次提交**推送；上表所列的 `abcefd4...` 是首次推送、且被干净 clone 实际验证过的 commit。第二次提交后的最终 `HEAD` 由交付时的 `git rev-parse HEAD` 与 `git ls-remote origin refs/heads/main` 核对并在交付回报中给出，此处不预先填一个尚未存在的值。
