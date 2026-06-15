# Changelog

All notable changes to VoxiDesk are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.1.0] — 2026-06-15

### Added

- **Thread safety**: `threading.Lock` untuk semua operasi model lifecycle di `Transcriber` (load, transcribe, unload) — mencegah race condition saat akses concurrent
- **Worker lifecycle**: State machine eksplisit (IDLE → LOADING → TRANSCRIBING → EXPORTING → CLEANUP → IDLE) dengan sinyal `worker_done` sebagai titik keputusan tunggal setelah worker selesai
- **Auto-save settings**: Pengaturan tersimpan otomatis saat ada perubahan dengan debounce 500ms — tidak perlu nunggu aplikasi ditutup
- **Theme 3-state cycle**: System → Light → Dark → System (sebelumnya hanya Dark ↔ Light)
- **Async duration probing**: Durasi file diprobbing di thread terpisah agar UI tidak freeze saat memproses banyak file
- **Single instance lock**: Hanya satu instance VoxiDesk yang bisa berjalan — menggunakan socket-based lock + PID file
- **Schema versioning**: `__version__` field di root JSON untuk settings dan history — memudahkan migrasi di masa depan
- **Backup rotation**: Timestamp-based backup (`.json.bak.YYYYMMDDHHMMSS`) sebelum setiap write — backup korup tidak menimpa backup valid
- **Magic bytes validation**: Validasi header file untuk format audio/video umum (MP3, WAV, FLAC, OGG, MKV, MP4/M4A/MOV) — tidak hanya mengandalkan ekstensi
- **Max file size**: Batas ukuran file 500MB dengan pesan error yang user-friendly
- **NaN/Inf guard**: Validasi nilai `math.isnan()` / `math.isinf()` pada output ffprobe dan `format_duration()` — mencegah crash akibat data korup
- **Platform-aware extension**: Deteksi ekstensi binary berdasarkan platform (`.exe` untuk Windows, kosong untuk Linux/macOS)
- **WM_DELETE_WINDOW handler**: Semua dialog (`show_error`, `show_info`, `show_about`) bisa ditutup dengan tombol X tanpa masalah fokus
- **Log bounded**: Progress log dibatasi 500 baris — baris lama di-trim untuk mencegah memory leak
- **Dialog modal**: History clear dialog menggunakan `transient()` + `grab_set()` — mencegah interaksi dengan window lain sebelum dialog ditutup
- **GPU cache cleanup**: `unload_model()` memanggil `torch.cuda.empty_cache()` setelah `gc.collect()` untuk memastikan VRAM benar-benar dibebaskan
- **Export fallback**: Jika PDF export gagal (misal font issue), worker mencoba export ulang tanpa format PDF dan melanjutkan format lainnya

### Fixed

- **Race condition worker batch**: Worker lama sekarang di-join dengan timeout 10s sebelum worker baru dimulai — mencegah dua model Whisper aktif bersamaan yang bisa menyebabkan OOM/CUDA error
- **Cancel flow tidak responsif**: Cancel dikirim dari worker sendiri (bukan thread terpisah), dengan pengecekan `cancel_flag` sebelum dan sesudah `load_model()` — cancel merespon dalam ≤5 detik bahkan saat loading model
- **Status ganda cancel**: `_on_complete` now checks `is_cancelling` di awal — mencegah "✅ File done!" dan "⏹ Cancelled" muncul bersamaan
- **UI freeze saat probing**: Durasi file diprobbing di thread background dengan update via `after(0, ...)` di main thread
- **Window geometry menyusut**: `_save_settings()` menggunakan `toplevel.winfo_width()` (root window), bukan `self.winfo_width()` (CTkFrame) — geometri tidak menyusut setelah restart
- **Device menu tidak sinkron**: `_pending_device` flag menyimpan device dari `load_from_settings()`, diaplikasikan di `_on_devices_loaded()` setelah async scan selesai
- **Drag-drop parser tidak robust**: Handle format braced `{path}` (Windows) dan fallback `re.split` (Linux/macOS)
- **History detail crash**: Helper `_fmt_duration()` aman terhadap nilai non-numeric — mengembalikan `"-"` jika gagal
- **Copy All button stuck**: Tombol reset ke "📋 Copy All" setelah 1.5 detik — tidak stuck di "✅ Copied!"
- **Duplicate file case-sensitive**: Perbandingan menggunakan `path.resolve()` untuk case-insensitive di Windows
- **Error setelah cancel ditelan**: Error selama cancel tetap di-log via `logging.warning()` dan ditampilkan di progress panel
- **Queue error handling**: `_poll_queues` menggunakan `logging.exception()` instead of `print()`, menangkap TclError secara spesifik
- **Theme toggle tidak kembali ke System**: Cycle 3 state (System → Light → Dark → System) — sebelumnya hanya Dark ↔ Light
- **Callback safety**: `on_segment()` dipanggil dalam `try/except` — callback failure tidak menghentikan transkripsi
- **Pengecekan winfo_exists**: `_on_devices_loaded()` guard `if not self.winfo_exists(): return` — mencegah update UI setelah widget di-destroy
- **GPU name mismatch**: Log warning jika jumlah GPU terdeteksi tidak cocok dengan CUDA count
- **"vi" di PDF blocklist**: Vietnamese dihapus dari `unsupported_pdf_fonts` karena menggunakan Latin script yang didukung DejaVuSans

### Security

- **Argument injection prevention** (`file_utils.py`): Menggunakan `Path.resolve()` + separator `--` sebelum file path di ffprobe subprocess — file bernama seperti `-v.mp3` tidak diinterpretasi sebagai flag
- **Path traversal prevention** (`transcription_worker.py`): Stem dibersihkan dari `..`, `/`, `\\`; resolved path divalidasi tetap berada di dalam `output_dir`
- **Global PATH mutation dihapus** (`ffmpeg_checker.py`): Tidak ada modifikasi `os.environ["PATH"]` — path absolut dikembalikan untuk digunakan langsung di subprocess. Mutasi PATH terbatas di worker thread (diperlukan oleh `faster_whisper`)
- **Error disclosure prevention** (`transcription_worker.py`): Traceback lengkap hanya di-log secara internal — `result_queue` hanya membawa `{"message": generic_msg}` tanpa key `"detail"` atau internal paths
- **Information disclosure di UI** (`main_window.py`): `show_error()` dipanggil tanpa parameter `detail` — pesan error bersifat generik, tidak mengekspos path sistem atau stack trace
- **File validation** (`file_drop_widget.py`): Magic bytes validation + max file size 500MB — mencegah file non-media atau file oversized diproses
- **Binary integrity**: Platform-aware extension dan prioritaskan FFmpeg sistem > bundled (bundled sebagai fallback)

### Changed

- Worker thread berubah dari `daemon=True` menjadi `daemon=False` — memastikan cleanup lengkap (unload model, free CUDA memory) sebelum thread berakhir
- `_on_complete` hanya increment `batch_index`, tidak langsung memanggil `_process_next_file()` — pemanggilan ditunda ke `_handle_worker_done()` setelah worker benar-benar cleanup
- `on_close` join timeout ditingkatkan dari 2s menjadi 30s + `gc.collect()` setelah join
- `get_all()` dan `get_recent()` di `AppSettings` dan `HistoryManager` mengembalikan `copy.deepcopy()` — mencegah modifikasi internal dari luar
- Prioritas FFmpeg: sistem terlebih dahulu, bundled sebagai fallback (sebelumnya bundled shadowing sistem)

### Removed

- `cancel_thread` terpisah — cancel sekarang langsung memanggil `worker.cancel()` dari main thread
- Per-path `transcriber.unload_model()` di `TranscriptionWorker.run()` — dikonsolidasi ke `finally` block

---

## [3.0.0] — Initial Release

- Release awal VoxiDesk dengan fitur transkripsi audio/video menggunakan faster-whisper
- Dukungan CUDA acceleration, multi-model, multi-language, batch processing, export TXT/SRT/VTT/PDF
- Dark dan light themes, real-time progress, transcription history, search dengan highlighting
