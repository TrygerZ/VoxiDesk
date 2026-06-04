# 🎙️ VoxiDesk

[![Python](https://img.shields.io/badge/python-3.11+-blue?logo=python&logoColor=white)]()
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![faster-whisper](https://img.shields.io/badge/engine-faster--whisper-8A2BE2)]()
[![CUDA](https://img.shields.io/badge/CUDA-12.4-76B900?logo=nvidia&logoColor=white)]()

A modern desktop transcription application that converts audio/video files to text using **faster-whisper** (CTranslate2) — achieving **3-4x faster** performance than OpenAI Whisper. Built with **CustomTkinter** for a native-looking UI on Windows.

> **Note:** Multi-language transcription tool (15+ languages supported). Default language can be changed in Settings.

## ✨ Features

### Core
- ✅ **Audio/Video to Text** — Transcribe MP3, WAV, M4A, MP4, MKV, and more
- ✅ **Multiple Models** — Choose from tiny, base, small, medium, large
- ✅ **Multi-language** — 15+ languages supported (Indonesian default)
- ✅ **Batch Processing** — Queue multiple files for sequential transcription
- ✅ **Export Formats** — TXT, SRT, VTT auto-save
- ✅ **Dark/Light Mode** — Toggleable theme
- ✅ **Real-time Progress** — Live progress bar with **tok/s** (tokens per second) and ETA

### Enhancement
- ✅ **Transcription History** — Browse past results with details
- ✅ **Persistent Settings** — Preferences saved automatically
- ✅ **Cancel Transcription** — Graceful cancellation with partial results
- ✅ **CUDA Auto-detection** — Automatically uses GPU if available
- ✅ **Portable FFmpeg** — Detects bundled `ffmpeg/bin/` or system-installed FFmpeg
- ✅ **File Info** — Name, size, duration display

### Advanced
- ✅ 🔍 **Search Results** — Keyword search with match highlighting & navigation
- ✅ 📄 **PDF Export** — Professional PDF output (fpdf2, Unicode support)
- ✅ ⏱️ **Word-level Timestamps** — Toggle display on/off
- ✅ 📊 **Live Speed Stats** — Tokens per second from real segment callbacks
- ✅ 🖼️ **App Icon** — Custom .ico / .png included
- ✅ 📦 **PyInstaller Build** — Package as standalone `.exe`

## 📋 Prerequisites

- **Python 3.11** — Required for PyTorch CUDA wheels
- **FFmpeg** — Required for audio processing. [Download & setup](#-ffmpeg-setup) below.
- **NVIDIA GPU** (recommended, optional) — CUDA 12.4 support

## 🚀 Installation

### 1. Clone & Setup
```bash
git clone https://github.com/TrygerZ/VoxiDesk.git
cd VoxiDesk
py -3.11 -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. FFmpeg Setup

VoxiDesk requires FFmpeg for audio/video processing. Since the binary files are too large for GitHub, you need to download them manually:

| File | Source |
|------|--------|
| `ffmpeg.exe` | [Download FFmpeg](https://ffmpeg.org/download.html) (Windows builds: [gyan.dev](https://www.gyan.dev/ffmpeg/builds/) or [BtbN](https://github.com/BtbN/FFmpeg-Builds/releases)) |
| `ffprobe.exe` | Included in the same FFmpeg package |

**Quick setup (Windows):**
1. Download the latest FFmpeg release (e.g., `ffmpeg-release-full.7z`)
2. Extract `ffmpeg.exe`, `ffprobe.exe`, and the required DLLs into `ffmpeg/bin/`
3. Or simply place them anywhere and ensure they're in your system `PATH`

> **Note:** The `ffmpeg/bin/` folder should contain `ffmpeg.exe`, `ffprobe.exe`, and the required DLLs.
> The folder is kept in the repo but the binary files are excluded (too large for GitHub).

### 4. Run
```bash
python main.py
```

Or double-click `run.bat` (Windows).

## 📖 Usage Guide

1. **Select Files** — Drag & drop audio/video files, or click "Browse"
2. **Configure** — Choose model size, language, device, output formats
3. **Transcribe** — Click **"▶ Transcribe!"** to start
4. **Monitor** — Watch real-time progress with tok/s speed and ETA
5. **Review** — Preview text, search keywords, toggle timestamps, copy to clipboard
6. **Export** — Results auto-saved in selected folder and formats

### Keyboard Shortcuts
| Shortcut | Action |
|----------|--------|
| `Ctrl+C` | Copy selected text |
| `↑` / `↓` | Navigate search matches |

## 🏗️ Building Standalone Executable

```bash
pip install pyinstaller
pyinstaller build.spec
```

Output: `dist/VoxiDesk/`

> **Note:**
> - Ensure `assets/icons/app.ico` exists before building (run `python generate_icon.py` if missing).
> - The build script automatically bundles FFmpeg from `ffmpeg/bin/` — make sure those files are downloaded first.

## 🛠️ Tech Stack

| Component | Technology |
|-----------|-----------|
| GUI Framework | [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) 5.x |
| ML Engine | [faster-whisper](https://github.com/SYSTRAN/faster-whisper) 1.2.1 (CTranslate2) |
| Deep Learning | [PyTorch](https://pytorch.org/) (CUDA 12.4) |
| PDF Export | [fpdf2](https://github.com/py-pdf/fpdf2) |
| Image Processing | [Pillow](https://python-pillow.org/) |
| Drag & Drop | [tkinterdnd2](https://github.com/Eliav2/tkinterdnd2) |
| Build Tool | [PyInstaller](https://pyinstaller.org/) |

## 📁 Project Structure

```
VoxiDesk/
├── app/
│   ├── core/
│   │   ├── transcriber.py          # faster-whisper wrapper
│   │   ├── ffmpeg_checker.py       # FFmpeg detection (bundled/system)
│   │   ├── file_utils.py           # Audio duration via ffprobe
│   │   ├── export.py               # TXT/SRT/VTT export
│   │   └── device_checker.py       # CUDA/CPU detection
│   ├── ui/
│   │   ├── main_window.py          # Main window orchestrator
│   │   ├── progress_panel.py       # Progress bar + status display
│   │   ├── settings_panel.py       # Transcription settings
│   │   ├── preview_panel.py        # Result preview + search
│   │   ├── history_panel.py        # Transcription history
│   │   ├── file_drop_widget.py     # Drag & drop area
│   │   └── dialogs.py              # Dialog helpers
│   ├── worker/
│   │   └── transcription_worker.py # Background transcription thread
│   └── data/
│       ├── settings.py             # Settings persistence
│       └── history.py              # History storage (JSON)
├── ffmpeg/
│   └── bin/                        # FFmpeg binaries (download separately, see Installation)
├── assets/
│   ├── icons/                      # App icon files
│   └── fonts/                      # DejaVuSans fonts (PDF export)
├── venv/                           # Virtual environment (excluded from git)
├── main.py                         # Application entry point
├── run.bat                         # Windows launcher
├── build.spec                      # PyInstaller configuration
├── requirements.txt                # Python dependencies
├── generate_icon.py                # Icon generation script
├── LICENSE                         # MIT License (VoxiDesk source code)
├── LICENSE-FFmpeg.txt              # GPLv3 License (FFmpeg binaries)
└── README.md                       # This file
```

## 🚀 Performance

VoxiDesk leverages **faster-whisper** with CTranslate2 for significantly faster transcription:

| Model | RTX 4050 (estimated) | vs Real-time |
|-------|---------------------|--------------|
| Tiny  | ~67x real-time      | ⚡ Extreme |
| Base  | ~33x real-time      | ⚡ Very Fast |
| Small | ~20x real-time      | 🚀 Fast |
| Medium| ~8x real-time       | ✅ Good |
| Large | ~4x real-time       | ✅ Usable |

*Performance measured in tokens/second with real-time progress tracking.*

## 📄 License

This project is dual-licensed:

| Component | License | File |
|-----------|---------|------|
| VoxiDesk source code (Python) | **MIT** | [`LICENSE`](LICENSE) |
| FFmpeg binaries | **GPLv3** | [`LICENSE-FFmpeg.txt`](LICENSE-FFmpeg.txt) |

## 🤝 Contributing

Contributions are welcome! Feel free to open issues or submit pull requests.

