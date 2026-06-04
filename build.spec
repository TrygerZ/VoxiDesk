# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller build script for VoxiDesk.
Build: pyinstaller build.spec

Requires:
    pip install pyinstaller
"""

import os
import sys
from pathlib import Path


# ─── Paths ────────────────────────────────────────
ROOT_DIR = Path.cwd()
APP_DIR = ROOT_DIR / "app"
ASSETS_DIR = ROOT_DIR / "assets"
FFMPEG_DIR = ROOT_DIR / "ffmpeg"

# ─── Collect all app modules ──────────────────────
a = Analysis(
    ['main.py'],
    pathex=[str(ROOT_DIR)],
    binaries=[],
    datas=[
        # Include assets (icons, fonts)
        (str(ASSETS_DIR / "icons"), "assets/icons"),
        (str(ASSETS_DIR / "fonts"), "assets/fonts"),
    ],
    hiddenimports=[
        'customtkinter',
        'PIL._tkinter_finder',
        'faster_whisper',
        'torch',
        'numpy',
        'tiktoken',
    ],
    hookspath=[],
    hooksconfig={},
    excludes=[
        'matplotlib',
        'scipy',
        'jupyter',
        'jupyter_client',
        'ipython',
        'notebook',
        'tkinter.test',
        'unittest',
        'distutils',
        'setuptools',
        'pip',
        'tensorboard',
        'pydoc',
        'test',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

# ─── Add FFmpeg binaries ──────────────────────────
if FFMPEG_DIR.exists():
    ffmpeg_bin = FFMPEG_DIR / "bin"
    if ffmpeg_bin.exists():
        for f in ffmpeg_bin.iterdir():
            if f.is_file() and f.suffix.lower() in ('.exe', '.dll'):
                a.binaries += [(f.name, str(f), 'BINARY')]
                print(f"  Added FFmpeg binary: {f.name}")

# ─── PyInstaller EXE ──────────────────────────────
pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='VoxiDesk',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ASSETS_DIR / "icons" / "app.ico"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='VoxiDesk',
)
