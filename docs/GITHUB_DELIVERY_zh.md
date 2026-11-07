# 建立新 GitHub 倉庫並推送

新倉庫建議名稱：**chem-structure-converter**。應用名稱仍為 ChemBridge。此步是工程交付的一部分；以下命令由有 GitHub 存取的本機執行者完成，文件存在不代表遠端已建立。

## 先核對環境與登入

安裝 Git 和 GitHub CLI（gh），在 PowerShell 執行：

```powershell
git --version
gh --version
gh auth status
gh api user --jq .login
```

預期帳號為 `CHANSingYeungSunny`，以實際登入核對。未登入時使用 `gh auth login` 的互動瀏覽器流程；不要在提示詞、README 或聊天貼上 access token。若登入成另一帳號，先釐清目標，不可默默推到另一帳號。

新解壓專案應位於獨立目錄。先執行 `git rev-parse --show-toplevel`；新專案尚未初始化時出現「not a git repository」是正常的。如果回傳其他專案根目錄，先移出該目錄，避免將不相關工作納入本次提交。

## 建立本機提交

在含 README.md 的 chembridge_mvp 根目錄執行。先確認測試和 demo 已通過，再建立 repo：

```powershell
git init
git branch -M main
git add .gitignore README.md pyproject.toml requirements*.txt
git add chembridge app.py start_windows.bat scripts tests examples docs prompts evidence
git diff --cached --stat
git diff --cached
```

檢查 staged files，確認沒有 .env、密鑰、.venv、私人資料或使用者上傳檔。evidence 只能納入適合分享的合成範例與驗證報告。若 Git 要求 author identity，使用本人真實 Git 設定；不要編造使用者名稱或電子郵件。

```powershell
git commit -m "Add chemical structure detection and conversion MVP"
```

## 建立新遠端與推送

先檢查 `CHANSingYeungSunny/chem-structure-converter` 是否已存在；存在時核對用途，不可覆寫不相關 repo。若不可用，可用日期尾綴建立新 repo，後續命令都要同步改名。

下面預設建立 private repo。已有明確公開要求時，將 `--private` 改為 `--public`。

```powershell
gh repo create CHANSingYeungSunny/chem-structure-converter --private --source . --remote origin
git push -u origin main
gh repo view --json nameWithOwner,url,isPrivate
git rev-parse HEAD
git ls-remote origin refs/heads/main
```

本機 HEAD 與遠端 main 的 SHA 應一致；記錄命令真實結果。GitHub CLI 建立成功並不自動代表 push 成功。

## 從全新 clone 驗證

在另一個新目錄執行。實際 repo 若換名，請同步更改：

```powershell
gh repo clone CHANSingYeungSunny/chem-structure-converter chem-structure-converter-check
cd chem-structure-converter-check
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-ui.txt -r requirements-dev.txt
.\.venv\Scripts\python.exe scripts\run_demo.py
.\.venv\Scripts\python.exe -m pytest -q
git rev-parse HEAD
```

交付時回傳：真實 repo URL、visibility、main 的 SHA、push 狀態、全新 clone 的 OS／版本／demo／測試結果，以及仍未完成的 Studio 整合項目。沒有 GitHub 登入時，標記遠端步驟為未完成；不要杜撰網址。

官方指令來源：

- https://cli.github.com/manual/gh_repo_create
- https://cli.github.com/manual/gh_auth_login
- https://cli.github.com/manual/gh_repo_clone
