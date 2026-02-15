# Gulama Bot — Windows Install Script
# Usage: irm https://gulama.ai/install.ps1 | iex
# Or:    .\scripts\install.ps1

$ErrorActionPreference = "Stop"
$GULAMA_VERSION = "0.1.0"
$MIN_PYTHON = "3.12"
$VENV_DIR = "$env:APPDATA\gulama\venv"

function Write-Info($msg) { Write-Host "[INFO] $msg" -ForegroundColor Cyan }
function Write-Ok($msg) { Write-Host "[OK] $msg" -ForegroundColor Green }
function Write-Warn($msg) { Write-Host "[WARN] $msg" -ForegroundColor Yellow }
function Write-Err($msg) { Write-Host "[ERROR] $msg" -ForegroundColor Red; exit 1 }

Write-Host ""
Write-Host "======================================" -ForegroundColor Green
Write-Host "   Gulama Bot Installer v$GULAMA_VERSION" -ForegroundColor Green
Write-Host "   Secure AI Agent Platform" -ForegroundColor Green
Write-Host "======================================" -ForegroundColor Green
Write-Host ""

# --- Check Python ---
$pythonCmd = $null
foreach ($cmd in @("python3", "python", "py")) {
    try {
        $version = & $cmd -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
        if ($version) {
            $parts = $version.Split(".")
            if ([int]$parts[0] -ge 3 -and [int]$parts[1] -ge 12) {
                $pythonCmd = $cmd
                Write-Ok "Python $version found"
                break
            }
        }
    } catch {
        continue
    }
}

if (-not $pythonCmd) {
    Write-Err "Python >= $MIN_PYTHON required. Install from https://python.org or: winget install Python.Python.3.12"
}

# --- Create virtual environment ---
Write-Info "Creating virtual environment at $VENV_DIR..."
$parentDir = Split-Path -Parent $VENV_DIR
if (-not (Test-Path $parentDir)) {
    New-Item -ItemType Directory -Path $parentDir -Force | Out-Null
}

& $pythonCmd -m venv $VENV_DIR
if ($LASTEXITCODE -ne 0) {
    Write-Err "Failed to create virtual environment"
}
Write-Ok "Virtual environment created"

# --- Activate and install ---
$activateScript = Join-Path $VENV_DIR "Scripts\Activate.ps1"
if (-not (Test-Path $activateScript)) {
    Write-Err "Virtual environment activation script not found"
}
. $activateScript

Write-Info "Installing Gulama..."
pip install --upgrade pip --quiet 2>$null
try {
    pip install gulama --quiet 2>$null
    Write-Ok "Gulama installed from PyPI"
} catch {
    if (Test-Path "pyproject.toml") {
        Write-Info "Installing from source..."
        pip install -e ".[dev]" --quiet
        Write-Ok "Gulama installed from source"
    } else {
        Write-Err "Could not install gulama. Package not yet published to PyPI."
    }
}

# --- Add to PATH ---
$venvBin = Join-Path $VENV_DIR "Scripts"
$currentPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($currentPath -notlike "*gulama*") {
    [Environment]::SetEnvironmentVariable(
        "Path",
        "$venvBin;$currentPath",
        "User"
    )
    Write-Info "Added $venvBin to user PATH"
}

# --- Verify ---
$gulamaPath = Join-Path $venvBin "gulama.exe"
if (Test-Path $gulamaPath) {
    Write-Ok "Gulama installed successfully!"
} else {
    Write-Warn "Gulama installed but gulama.exe not found at $gulamaPath"
}

Write-Host ""
Write-Host "Installation complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:"
Write-Host "  1. Open a NEW terminal (to pick up PATH changes)"
Write-Host "  2. Run initial setup:  gulama setup"
Write-Host "  3. Start chatting:     gulama chat"
Write-Host "  4. Start the server:   gulama start"
Write-Host ""
Write-Host "For Docker:  docker compose up -d"
Write-Host "For help:    gulama --help"
Write-Host ""
