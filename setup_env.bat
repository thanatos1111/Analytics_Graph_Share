@echo off
setlocal
cd /d "%~dp0"

echo Setting up environment for Analytics Graph Share...
echo Installing dependencies to system Python...
echo.

pip install -r requirements.txt
if errorlevel 1 (
    echo Failed to install requirements. Ensure Python and pip are on PATH.
    exit /b 1
)

echo.
echo Setup complete. Run start_app.bat to launch the app.
exit /b 0
