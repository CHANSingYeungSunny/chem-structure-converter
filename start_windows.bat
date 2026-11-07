@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  py -3.12 -m venv .venv
  if errorlevel 1 goto failure
)
.venv\Scripts\python.exe -m pip install -r requirements-ui.txt
if errorlevel 1 goto failure
.venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1 --browser.gatherUsageStats false
if errorlevel 1 goto failure
goto end
:failure
echo Setup or startup failed. Install Python 3.12 and read README.md.
pause
:end
endlocal
