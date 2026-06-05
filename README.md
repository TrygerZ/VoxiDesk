# 🎙️ VoxiDesk

[![Python](https://img.shields.io/badge/python-3.14+-blue?logo=python&logoColor=white)]()
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![faster-whisper](https://img.shields.io/badge/engine-faster--whisper-8A2BE2)]()
[![CUDA](https://img.shields.io/badge/CUDA-12-76B900?logo=nvidia&logoColor=white)]()

VoxiDesk is a desktop application that transcribes audio and video files into text. It uses **faster-whisper** with CTranslate2 to run 3-4x faster than the original OpenAI Whisper, with support for both CPU and NVIDIA GPU (CUDA) acceleration.

## ✨ Features

- 🎬 Transcribe audio and video files — MP3, WAV, M4A, MP4, MKV, AVI, and more
- 🧠 Multiple model sizes — from tiny (fast) to large (most accurate)
- 🌍 Multi-language support — 15+ languages, Indonesian set as default
- 📂 Batch processing — queue multiple files for sequential transcription
- 💾 Export to TXT, SRT, VTT, and PDF
- 🌓 Dark and light themes
- 📊 Real-time progress with tokens per second and ETA
- 🔍 Search results with keyword highlighting and navigation
- ⏱️ Word-level timestamps toggle
- 📜 Transcription history with persistent storage
- ⚡ CUDA auto-detection — uses GPU if available, falls back to CPU
- 🎯 GPU acceleration via CTranslate2 without PyTorch

## 📋 Prerequisites

- Python 3.14 or newer
- FFmpeg (required for audio processing)
- NVIDIA GPU with CUDA (optional, recommended for faster transcription)

## 🚀 Installation

### 1. Clone and prepare
```bash
git clone https://github.com/TrygerZ/VoxiDesk.git
cd VoxiDesk
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. FFmpeg setup

VoxiDesk needs FFmpeg to process audio and video files. Download the latest build for your system:

- [ffmpeg.org](https://ffmpeg.org/download.html)
- Windows builds: [gyan.dev](https://www.gyan.dev/ffmpeg/builds/) or [BtbN](https://github.com/BtbN/FFmpeg-Builds/releases)

Extract **all contents** from the `bin/` folder of the FFmpeg build into `ffmpeg/bin/`:
- `ffmpeg.exe`, `ffprobe.exe`, `ffplay.exe`
- All required DLLs (`avcodec-*.dll`, `avformat-*.dll`, `avutil-*.dll`, `avfilter-*.dll`, `avdevice-*.dll`, `swresample-*.dll`, `swscale-*.dll`)

Or install FFmpeg globally and make sure it is in your system PATH.

### 4. Run
```bash
python main.py
```

Or double-click `run.bat` on Windows.

## 📖 Usage

1. Drop audio or video files into the selection area, or click Browse.
2. Choose the model size, language, processing device, and output formats.
3. Click **Transcribe** to start.
4. Watch the progress bar, speed, and estimated time remaining.
5. Review the transcription in the preview panel. Use search to find specific text.
6. Results are saved automatically to your chosen output folder.

## Performance

VoxiDesk uses faster-whisper with CTranslate2, which runs significantly faster than the original OpenAI Whisper. GPU acceleration via CUDA provides an additional speed boost.

| Model | RTX 4050 (estimated) | vs Real-time |
|-------|---------------------|--------------|
| Tiny  | ~67x                | ⚡ Extreme |
| Base  | ~33x                | ⚡ Very Fast |
| Small | ~20x                | 🚀 Fast |
| Medium| ~8x                 | ✅ Good |
| Large | ~4x                 | ✅ Usable |

## 🛠️ Tech Stack

- **GUI:** CustomTkinter 5.x
- **Engine:** faster-whisper 1.2.1 with CTranslate2
- **PDF export:** fpdf2
- **Image processing:** Pillow
- **Drag and drop:** tkinterdnd2

## 📁 Project Structure

```
VoxiDesk/
├── app/
│   ├── core/
│   │   ├── transcriber.py         # faster-whisper wrapper
│   │   ├── ffmpeg_checker.py      # FFmpeg detection
│   │   ├── file_utils.py          # Audio duration via ffprobe
│   │   ├── export.py              # TXT, SRT, VTT, PDF export
│   │   └── device_checker.py      # CUDA and CPU detection
│   ├── ui/
│   │   ├── main_window.py         # Main application window
│   │   ├── progress_panel.py      # Progress bar and logs
│   │   ├── settings_panel.py      # Transcription settings
│   │   ├── preview_panel.py       # Result viewer and search
│   │   ├── history_panel.py       # Transcription history
│   │   ├── file_drop_widget.py    # File selection area
│   │   └── dialogs.py             # Dialog helpers
│   ├── worker/
│   │   └── transcription_worker.py # Background processing thread
│   └── data/
│       ├── settings.py            # Settings persistence
│       └── history.py             # History storage
├── ffmpeg/bin/                    # FFmpeg binaries (download separately)
├── assets/
│   ├── icons/                     # App icons
│   └── fonts/                     # Fonts for PDF export
├── main.py                        # Entry point
├── run.bat                        # Windows launcher
├── requirements.txt               # Python dependencies
├── LICENSE                        # MIT License (VoxiDesk)
├── LICENSE-FFmpeg.txt             # GPLv3 License (FFmpeg)
└── README.md
```

## 📄 License

This project is dual-licensed:
- **VoxiDesk source code** (Python) — MIT License. See [LICENSE](LICENSE).
- **FFmpeg binaries** — GPLv3 License. See [LICENSE-FFmpeg.txt](LICENSE-FFmpeg.txt).

