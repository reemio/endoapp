#!/usr/bin/env powershell
Write-Host "Checking Python installation and packages..." -ForegroundColor Green

# Check Python installation
$pythonCmd = $null
try {
    python --version | Out-Null
    $pythonCmd = "python"
    Write-Host "Found: python" -ForegroundColor Green
} catch {
    try {
        python3 --version | Out-Null
        $pythonCmd = "python3"
        Write-Host "Found: python3" -ForegroundColor Green
    } catch {
        Write-Host "ERROR: Python not found. Please install Python or add it to PATH." -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }
}

# Show Python version
& $pythonCmd --version

# Check if PySide6 is installed
Write-Host "Checking PySide6..." -ForegroundColor Yellow
try {
    & $pythonCmd -c "import PySide6; print('PySide6 found:', PySide6.__version__)"
} catch {
    Write-Host "PySide6 not found. Installing required packages..." -ForegroundColor Yellow
    & $pythonCmd -m pip install PySide6 opencv-python numpy fpdf2 Pillow
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Failed to install packages" -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }
}

# Fix potential PDF library conflict
Write-Host "Fixing PDF library conflicts..." -ForegroundColor Yellow
& $pythonCmd -m pip uninstall -y pypdf 2>$null

Write-Host "Starting Endoscopy Reporting System..." -ForegroundColor Green
& $pythonCmd run.py

if ($LASTEXITCODE -ne 0) {
    Write-Host "Application exited with error code: $LASTEXITCODE" -ForegroundColor Red
    Read-Host "Press Enter to exit"
}