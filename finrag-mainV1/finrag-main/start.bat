@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" goto check
where py >nul 2>nul
if errorlevel 1 goto use_python
py -3 -m venv .venv
if errorlevel 1 goto error
goto check
:use_python
python -m venv .venv
if errorlevel 1 goto error
:check
".venv\Scripts\python.exe" -c "import sys; assert sys.version_info >= (3,10), 'Python 3.10 or newer is required'"
if errorlevel 1 goto error
".venv\Scripts\python.exe" -c "import streamlit, pypdf, docx, requests, dotenv; from packaging.version import Version; assert Version(streamlit.__version__) >= Version('1.40')" >nul 2>nul
if not errorlevel 1 goto run
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto error
:run
if /i "%~1"=="--setup-only" exit /b 0
echo Starting Finland Travel Assistant at http://127.0.0.1:8501
echo Keep this window open. Press Ctrl+C to stop.
".venv\Scripts\python.exe" -X utf8 -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501 --server.headless false --browser.gatherUsageStats false
if errorlevel 1 goto error
exit /b 0
:error
echo.
echo Startup failed. Check the error above and see README.md.
pause
exit /b 1
