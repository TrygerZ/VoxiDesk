"""Export transcription results to TXT, SRT, VTT, PDF formats."""

import datetime
from pathlib import Path


def _get_assets_dir() -> Path:
    """Get assets directory path."""
    return Path(__file__).resolve().parent.parent.parent / "assets"


def format_timestamp(seconds: float, srt: bool = True) -> str:
    """Format seconds to SRT (hh:mm:ss,ms) or VTT (hh:mm:ss.ms) timestamp."""
    if seconds < 0:
        seconds = 0
    td = datetime.timedelta(seconds=float(seconds))
    hours, remainder = divmod(td.seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    millis = int(td.microseconds / 1000)
    hours += td.days * 24
    if srt:
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
    else:
        ms = f"{millis:03d}"
        return f"{hours:02d}:{minutes:02d}:{secs:02d}.{ms}"


def write_txt(out_path: Path, text: str):
    """Write transcription result to TXT file."""
    out_path.write_text(text.strip() + "\n", encoding="utf-8")


def write_srt(out_path: Path, segments: list):
    """Write transcription segments to SRT file."""
    lines = []
    for i, seg in enumerate(segments, start=1):
        start = format_timestamp(seg["start"], srt=True)
        end = format_timestamp(seg["end"], srt=True)
        text = seg.get("text", "").strip()
        if not text:
            continue
        lines.append(str(i))
        lines.append(f"{start} --> {end}")
        lines.append(text)
        lines.append("")
    out_path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")


def write_vtt(out_path: Path, segments: list):
    """Write transcription segments to VTT file."""
    lines = ["WEBVTT", ""]
    for seg in segments:
        start = format_timestamp(seg["start"], srt=False)
        end = format_timestamp(seg["end"], srt=False)
        text = seg.get("text", "").strip()
        if not text:
            continue
        lines.append(f"{start} --> {end}")
        lines.append(text)
        lines.append("")
    out_path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")


def write_pdf(out_path: Path, text: str, title: str = "Transcription"):
    """
    Write transcription result to PDF file using fpdf2.

    Args:
        out_path: Output file path (.pdf)
        text: Transcription text
        title: Document title (usually the file name)
    """
    from fpdf import FPDF
    from datetime import datetime

    pdf = FPDF()
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    # Try to use Unicode font, fall back to Helvetica
    font_family = "Helvetica"
    bold_style = "B"

    # Check for DejaVuSans bundled font
    font_path = _get_assets_dir() / "fonts" / "DejaVuSans.ttf"
    if font_path.exists():
        try:
            pdf.add_font("DejaVu", "", str(font_path), uni=True)
            bold_path = font_path.parent / "DejaVuSans-Bold.ttf"
            if bold_path.exists():
                pdf.add_font("DejaVu", "B", str(bold_path), uni=True)
            else:
                pdf.add_font("DejaVu", "B", str(font_path), uni=True)
            font_family = "DejaVu"
            bold_style = "B"
        except Exception as e:
            raise RuntimeError(f"Failed to load Unicode font for PDF export: {e}")
    else:
        raise RuntimeError("Unicode font DejaVuSans.ttf not found. Cannot safely export PDF.")

    # Title
    pdf.set_font(font_family, bold_style, 16)
    pdf.cell(0, 10, title, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)

    # Timestamp
    pdf.set_font(font_family, "", 8)
    pdf.set_text_color(128, 128, 128)
    pdf.cell(0, 6, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
             new_x="LMARGIN", new_y="NEXT")
    pdf.ln(8)

    # Content with paragraphs
    pdf.set_text_color(0, 0, 0)
    pdf.set_font(font_family, "", 11)

    paragraphs = text.strip().split('\n')
    for para in paragraphs:
        para = para.strip()
        if not para:
            pdf.ln(5)
            continue
        pdf.multi_cell(0, 6, para)
        pdf.ln(2)

    pdf.output(str(out_path))


def export_results(
    result: dict,
    base_path: Path,
    formats: list[str],
) -> dict:
    """
    Export transcription results to requested formats.

    Args:
        result: Result from model.transcribe()
        base_path: Base path for output file (without extension)
        formats: List of desired formats ['txt', 'srt', 'vtt', 'pdf']

    Returns:
        dict with format as key and saved Path as value.
        Example: {'txt': Path('output.txt'), 'srt': Path('output.srt')}
    """
    full_text = result.get("text", "").strip()
    segments = result.get("segments", []) or []
    saved_files = {}

    if "txt" in formats:
        txt_path = base_path.with_suffix(".txt")
        write_txt(txt_path, full_text)
        saved_files["txt"] = txt_path

    if "srt" in formats:
        srt_path = base_path.with_suffix(".srt")
        write_srt(srt_path, segments)
        saved_files["srt"] = srt_path

    if "vtt" in formats:
        vtt_path = base_path.with_suffix(".vtt")
        write_vtt(vtt_path, segments)
        saved_files["vtt"] = vtt_path

    if "pdf" in formats:
        pdf_path = base_path.with_suffix(".pdf")
        if full_text:
            try:
                write_pdf(pdf_path, full_text, title=base_path.name)
                saved_files["pdf"] = pdf_path
            except Exception as e:
                import logging
                logging.warning(f"Skipping PDF export: {e}")

    return saved_files
