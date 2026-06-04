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

:: Copy CUDA DLL ke folder CTranslate2 (biar bisa detect GPU)
python -c "
import os, shutil, site
src = os.path.join(site.getsitepackages()[0], 'nvidia', 'cublas', 'bin')
dst = os.path.join(site.getsitepackages()[0], 'ctranslate2')
if os.path.exists(src):
    for f in os.listdir(src):
        if f.endswith('.dll'):
            shutil.copy2(os.path.join(src, f), os.path.join(dst, f))
    print('[INFO] CUDA DLLs copied to CTranslate2')
else:
    print('[INFO] CUDA not found - running on CPU')
" 2>nul

:: Jalankan aplikasi
echo [INFO] Starting application...
echo.
python main.py

:: Deaktivasi venv
deactivate
echo.
echo [INFO] Application closed.
pause

