@echo off
setlocal
cd /d "%~dp0"
call start.bat --setup-only
if errorlevel 1 exit /b 1
echo Installing optional AI packages. This may download several GB.
".venv\Scripts\python.exe" -m pip install -r requirements-ai.txt
if errorlevel 1 goto error
echo AI packages installed. Start the app and select AI mode.
echo Models download on the first AI question and require Hugging Face access.
pause
exit /b 0
:error
echo Installation failed. Basic local retrieval still works with start.bat.
pause
exit /b 1
