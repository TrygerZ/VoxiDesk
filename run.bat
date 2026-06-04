@echo off
cd /d "%~dp0"
title VoxiDesk v3.0

echo ========================================
echo            VoxiDesk v3.0
echo ========================================
echo.

:: Cek venv
if not exist "venv\Scripts\activate.bat" (
    echo [ERROR] Virtual environment not found.
    echo.
    echo Run: py -3.11 -m venv venv
    echo.
    pause
    exit /b 1
)

:: Aktivasi venv
call "venv\Scripts\activate.bat"

:: Cek dependencies
python -c "import customtkinter" 2>nul
if errorlevel 1 (
    echo [ERROR] Dependencies not installed.
    echo.
    echo Run: pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

:: Jalankan aplikasi
echo [INFO] Starting application...
echo.
python main.py

:: Deaktivasi venv
deactivate
echo.
echo [INFO] Application closed.
pause

