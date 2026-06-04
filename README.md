# 🎙️ VoxiDesk

[![Python](https://img.shields.io/badge/python-3.11+-blue?logo=python&logoColor=white)]()
[![License](https://img.shields.io/badge/license-MIT-green)]()
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
- ✅ **Bundled FFmpeg** — Fully portable, no system install required
- ✅ **CUDA Auto-detection** — Automatically uses GPU if available
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
- **FFmpeg** — Bundled in `ffmpeg/bin/` (included in repo)
- **NVIDIA GPU** (recommended, optional) — CUDA 12.4 support

## 🚀 Installation

### 1. Clone & Setup
```bash
git clone https://github.com/yourusername/voxidesk.git
cd voxidesk
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

### 3. Generate App Icon (Optional)
```bash
python generate_icon.py
```

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

> **Note:** Ensure `assets/icons/app.ico` exists before building.

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
│   └── bin/                        # Bundled FFmpeg (portable)
├── assets/
│   └── icons/                      # App icon files
├── venv/                           # Virtual environment
├── main.py                         # Application entry point
├── run.bat                         # Windows launcher
├── build.spec                      # PyInstaller configuration
├── requirements.txt                # Python dependencies
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

## 🤝 Contributing

Contributions are welcome! Feel free to open issues or submit pull requests.

