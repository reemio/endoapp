@echo off
echo Checking Python installation and packages...

REM Check if python is available
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python not found in PATH. Trying python3...
    python3 --version >nul 2>&1
    if %errorlevel% neq 0 (
        echo ERROR: Python not found. Please install Python or add it to PATH.
        pause
        exit /b 1
    )
    set PYTHON_CMD=python3
) else (
    set PYTHON_CMD=python
)

echo Using: %PYTHON_CMD%
%PYTHON_CMD% --version

REM Check if PySide6 is installed
echo Checking PySide6...
%PYTHON_CMD% -c "import PySide6; print('PySide6 found:', PySide6.__version__)" 2>nul
if %errorlevel% neq 0 (
    echo PySide6 not found. Installing required packages...
    %PYTHON_CMD% -m pip install PySide6 opencv-python numpy fpdf2 Pillow
    if %errorlevel% neq 0 (
        echo ERROR: Failed to install packages
        pause
        exit /b 1
    )
)

REM Fix potential PDF library conflict
echo Fixing PDF library conflicts...
%PYTHON_CMD% -m pip uninstall -y pypdf >nul 2>&1

echo Starting Endoscopy Reporting System...

REM Use Device 1 for USB capture devices (change to 0 for webcam)
set PREFERRED_CAMERA_ID=1

%PYTHON_CMD% run.py
if %errorlevel% neq 0 (
    echo Application exited with error code: %errorlevel%
    pause
)