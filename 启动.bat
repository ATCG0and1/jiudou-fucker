@echo off
cd /d "%~dp0"
chcp 65001 >nul 2>&1
title Jiudou Auto Answer

echo.
echo ===========================================
echo   Jiudou Auto Answer Tool
echo ===========================================
echo.

:: ====== Step 0: Find Python ======
set PYCMD=
python --version >nul 2>&1 && set PYCMD=python
if not defined PYCMD py --version >nul 2>&1 && set PYCMD=py
if not defined PYCMD python3 --version >nul 2>&1 && set PYCMD=python3

if not defined PYCMD (
    echo [ERROR] Python not found. Install Python 3.8+
    echo Download: https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)
echo Python: %PYCMD%

:: ====== Step 1: Create venv (first time only) ======
set VENV=%~dp0.venv
if not exist "%VENV%\Scripts\python.exe" (
    echo.
    echo [1/3] Creating virtual environment...
    %PYCMD% -m venv "%VENV%"
    if %errorlevel% neq 0 (
        echo Failed to create venv, using system Python...
        set VENV_PYTHON=%PYCMD%
    ) else (
        echo Done.
    )
) else (
    echo Venv already exists.
)
if exist "%VENV%\Scripts\python.exe" set VENV_PYTHON=%VENV%\Scripts\python.exe
if not defined VENV_PYTHON set VENV_PYTHON=%PYCMD%

:: ====== Step 2: Install dependencies ======
echo.
echo [2/3] Installing dependencies (mirror, ~5MB)...
"%VENV_PYTHON%" -m pip install requests playwright -i https://pypi.tuna.tsinghua.edu.cn/simple -q 2>nul
if %errorlevel% neq 0 (
    "%VENV_PYTHON%" -m pip install requests playwright -i https://mirrors.aliyun.com/pypi/simple -q 2>nul
    if %errorlevel% neq 0 (
        "%VENV_PYTHON%" -m pip install requests playwright -q 2>nul
    )
)
echo Done.

:: ====== Step 3: Skip Chromium download (use system Chrome) ======
echo.
echo [3/3] Ready. (using system Chrome/Edge, no 150MB download)
echo.

:: ====== Run ======
echo Starting... Browser will open shortly.
echo Login to jiudou123.com, then press Enter in this window.
echo ===========================================
echo.

"%VENV_PYTHON%" "%~dp0jiudou_auto.py"

echo.
echo Script finished. You can close this window.
pause
