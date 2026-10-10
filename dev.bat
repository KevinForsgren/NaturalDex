@echo off
REM ============================================================
REM  StudyLoop development entry point (Windows CMD)
REM  Creates the Python venv if missing, then starts backend +
REM  frontend, each in its own window.
REM ============================================================
setlocal
set "ROOT=%~dp0"
set "PY=%ROOT%.venv\Scripts\python.exe"

REM Ensure the virtual environment exists.
if not exist "%PY%" (
  echo [dev] Creating virtual environment with uv...
  where uv >nul 2>nul
  if errorlevel 1 (
    echo [dev] ERROR: uv is required. See https://docs.astral.sh/uv/
    exit /b 1
  )
  pushd "%ROOT%"
  uv venv .venv
  if errorlevel 1 ( popd & echo [dev] ERROR: uv venv failed & exit /b 1 )
  echo [dev] Installing backend dependencies...
  uv pip install --python .venv\Scripts\python.exe -r backend\requirements.txt
  popd
)

echo [dev] Starting backend on http://127.0.0.1:8000 ...
start "StudyLoop backend" cmd /k ""cd /d "%ROOT%backend" && "%PY%" -m uvicorn src.main:app --reload --host 127.0.0.1 --port 8000""

echo [dev] Starting frontend on http://127.0.0.1:3000 ...
start "StudyLoop frontend" cmd /k ""cd /d "%ROOT%frontend" && npm run dev""

echo [dev] Both started.  Backend: http://127.0.0.1:8000   Frontend: http://127.0.0.1:3000
echo [dev] The two service windows stay open; close them to stop each service.
pause >nul
endlocal