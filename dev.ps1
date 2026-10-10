# ============================================================
#  StudyLoop development entry point (Windows PowerShell)
#  Creates the Python venv if missing, then starts backend +
#  frontend, each in its own window.
# ============================================================
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Py = Join-Path $Root ".venv\Scripts\python.exe"

if (-not (Test-Path $Py)) {
    Write-Host "[dev] Creating virtual environment with uv..." -ForegroundColor Cyan
    if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
        Write-Host "[dev] ERROR: uv is required. See https://docs.astral.sh/uv/" -ForegroundColor Red
        exit 1
    }
    Push-Location $Root
    uv venv .venv
    if ($LASTEXITCODE -ne 0) { Pop-Location; Write-Host "[dev] ERROR: uv venv failed" -ForegroundColor Red; exit 1 }
    Write-Host "[dev] Installing backend dependencies..."
    uv pip install --python ".venv\Scripts\python.exe" -r "backend\requirements.txt"
    if ($LASTEXITCODE -ne 0) { Pop-Location; Write-Host "[dev] ERROR: dependency install failed" -ForegroundColor Red; exit 1 }
    Pop-Location
}

Write-Host "[dev] Starting backend on http://127.0.0.1:8000 ..."
Start-Process -FilePath $Py `
    -ArgumentList @("-m", "uvicorn", "src.main:app", "--reload", "--host", "127.0.0.1", "--port", "8000") `
    -WorkingDirectory (Join-Path $Root "backend")

Write-Host "[dev] Starting frontend on http://127.0.0.1:3000 ..."
Start-Process -FilePath "npm.cmd" `
    -ArgumentList @("run", "dev") `
    -WorkingDirectory (Join-Path $Root "frontend")

Write-Host "[dev] Both started.  Backend: http://127.0.0.1:8000   Frontend: http://127.0.0.1:3000" -ForegroundColor Green
Write-Host "[dev] The two service windows stay open; close them to stop each service."