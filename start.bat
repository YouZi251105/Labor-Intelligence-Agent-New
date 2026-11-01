@echo off
setlocal EnableExtensions
title Labor Intelligence Agent

cd /d "%~dp0"

echo.
echo ==========================================
echo   Labor Intelligence Agent
echo   Project Launcher
echo ==========================================
echo.

where python >nul 2>&1
if errorlevel 1 goto missing_python

where node >nul 2>&1
if errorlevel 1 goto missing_node

where npm >nul 2>&1
if errorlevel 1 goto missing_npm

if not exist "%~dp0backend\.venv\Scripts\python.exe" (
    echo [1/3] Creating Python virtual environment...
    python -m venv "%~dp0backend\.venv"
    if errorlevel 1 goto backend_setup_failed
)

if not exist "%~dp0backend\.venv\.lia-deps-installed" (
    echo [2/3] Installing backend dependencies. First run may take several minutes...
    pushd "%~dp0backend"
    ".venv\Scripts\python.exe" -m pip install --upgrade pip
    if errorlevel 1 goto backend_setup_failed
    ".venv\Scripts\python.exe" -m pip install -e ".[dev]"
    if errorlevel 1 (
        echo Editable package install failed. Retrying with requirements-dev.txt...
        ".venv\Scripts\python.exe" -m pip install -r requirements-dev.txt
        if errorlevel 1 goto backend_setup_failed
    )
    type nul > ".venv\.lia-deps-installed"
    popd
) else (
    echo [2/3] Backend dependencies are ready.
)

if not exist "%~dp0frontend\node_modules" (
    echo [3/3] Installing frontend dependencies. First run may take several minutes...
    pushd "%~dp0frontend"
    call npm install --no-audit --no-fund
    if errorlevel 1 goto frontend_setup_failed
    popd
) else (
    echo [3/3] Frontend dependencies are ready.
)

powershell -NoProfile -Command "if (Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue) { exit 0 } else { exit 1 }"
if errorlevel 1 (
    echo Starting backend: http://127.0.0.1:8000
    start "Labor Backend" /D "%~dp0backend" cmd /k "set PYTHONUTF8=1&& .venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000"
) else (
    echo Backend port 8000 is already running.
)

powershell -NoProfile -Command "if (Get-NetTCPConnection -LocalPort 5173 -State Listen -ErrorAction SilentlyContinue) { exit 0 } else { exit 1 }"
if errorlevel 1 (
    echo Starting frontend: http://127.0.0.1:5173
    start "Labor Frontend" /D "%~dp0frontend" cmd /k "npm run dev -- --host 127.0.0.1"
) else (
    echo Frontend port 5173 is already running.
)

echo.
echo Waiting for services...
powershell -NoProfile -Command "Start-Sleep -Seconds 4"
start "" "http://127.0.0.1:5173/"

echo.
echo Launcher finished.
echo Frontend: http://127.0.0.1:5173/
echo API docs: http://127.0.0.1:8000/docs
echo.
pause
exit /b 0

:missing_python
echo [ERROR] Python was not found. Install Python 3.13 or a compatible version.
echo Download: https://www.python.org/downloads/
goto failed

:missing_node
echo [ERROR] Node.js was not found. Install Node.js 24 or a compatible version.
echo Download: https://nodejs.org/
goto failed

:missing_npm
echo [ERROR] npm was not found. Reinstall Node.js.
goto failed

:backend_setup_failed
echo.
echo [ERROR] Backend setup failed.
echo Run manually in the backend directory:
echo .\.venv\Scripts\python -m pip install -e ".[dev,quality]"
goto failed

:frontend_setup_failed
echo.
echo [ERROR] Frontend setup failed.
echo Run manually in the frontend directory:
echo npm install --no-audit --no-fund
goto failed

:failed
echo.
pause
exit /b 1
