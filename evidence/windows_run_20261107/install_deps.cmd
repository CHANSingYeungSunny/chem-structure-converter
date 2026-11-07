@echo off
REM Background installer used for the Windows verification run.
REM Logs full pip output and its exit code next to this script.
cd /d "%~dp0..\.."
set "LOGDIR=%~dp0"
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check --progress-bar off -r requirements-ui.txt -r requirements-dev.txt > "%LOGDIR%pip_install.txt" 2>&1
echo %ERRORLEVEL% > "%LOGDIR%pip_exit_code.txt"
