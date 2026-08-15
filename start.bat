@echo off
setlocal EnableExtensions
cd /d "%~dp0"
chcp 65001 >nul 2>&1
set "PYTHONUTF8=1"

if not exist "config\config.ini" (
    echo [ERROR] config\config.ini was not found.
    echo Copy config\config.ini.example to config\config.ini and configure it.
    pause
    exit /b 1
)

set "PYTHON_CMD=.venv\Scripts\python.exe"
if not exist "%PYTHON_CMD%" (
    set "BOOTSTRAP_PY="
    where py >nul 2>&1
    if not errorlevel 1 set "BOOTSTRAP_PY=py -3.14"
    if not defined BOOTSTRAP_PY (
        where python >nul 2>&1
        if not errorlevel 1 set "BOOTSTRAP_PY=python"
    )
    if not defined BOOTSTRAP_PY (
        echo [ERROR] Python 3.14 or newer was not found.
        pause
        exit /b 1
    )
    echo [SETUP] Creating local .venv...
    %BOOTSTRAP_PY% -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Could not create .venv.
        pause
        exit /b 1
    )
)

"%PYTHON_CMD%" -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 14) else 1)" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] .venv uses Python older than 3.14.
    echo [ACTION] Recreate .venv with Python 3.14 or newer.
    pause
    exit /b 1
)

echo [SETUP] Updating pip, setuptools and wheel in .venv...
"%PYTHON_CMD%" -m pip install --quiet --upgrade "pip==26.1.2" "setuptools==84.0.0" "wheel==0.48.0"
if errorlevel 1 (
    echo [ERROR] Could not update Python tools in .venv.
    pause
    exit /b 1
)

if exist "requirements.txt" (
    echo [SETUP] Installing dependencies into .venv...
    set "PIP_DISABLE_PIP_VERSION_CHECK=1"
    "%PYTHON_CMD%" -m pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] Dependency installation failed.
        pause
        exit /b 1
    )
)

"%PYTHON_CMD%" "HourBooster.py" %*
set "EXIT_CODE=%ERRORLEVEL%"
pause
endlocal & exit /b %EXIT_CODE%
