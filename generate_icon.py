"""
Generate VoxiDesk app icon (app.ico and app.png).
Run this script if the icon files are missing or corrupted.

Usage:
    python generate_icon.py
"""

import struct
import zlib
from pathlib import Path

ASSETS_DIR = Path(__file__).parent / "assets" / "icons"
ICO_PATH = ASSETS_DIR / "app.ico"
PNG_PATH = ASSETS_DIR / "app.png"

# A simple 64x64 microphone icon encoded as PNG (RGBA)
# This is a minimal fallback icon
ICON_WIDTH = 64
ICON_HEIGHT = 64


def create_png(width: int, height: int) -> bytes:
    """Create a minimal microphone icon as PNG."""
    # Microphone shape using raw pixel data (RGBA)
    pixels = bytearray()
    mic_color = (100, 180, 255, 255)  # Light blue
    bg_color = (0, 0, 0, 0)  # Transparent
    shadow = (60, 60, 80, 200)

    cx, cy = width // 2, height // 2 - 2
    r = 8  # mic body radius
    for y in range(height):
        for x in range(width):
            dx, dy = x - cx, y - cy
            dist = (dx * dx + dy * dy) ** 0.5

            # Mic body (circle)
            if dist < r:
                pixels.extend(mic_color)
            # Mic stand (vertical line)
            elif abs(dx) < 2 and abs(dy) < r + 6 and y > cy + r - 2:
                pixels.extend(mic_color)
            # Mic arc at bottom
            elif abs(dx) < r + 2 and abs(y - (cy + r + 6)) < 2:
                pixels.extend(mic_color)
            # Mic base
            elif abs(dx) < r + 4 and abs(y - (cy + r + 10)) < 2:
                pixels.extend(mic_color)
            # Shadow effect
            elif dist < r + 3 and dist >= r:
                alpha = max(0, int(150 * (1 - (dist - r) / 3)))
                pixels.extend((*shadow[:3], alpha))
            else:
                pixels.extend(bg_color)

    # Create PNG
    def create_png_raw(width, height, pixel_data):
        def chunk(chunk_type, data):
            c = chunk_type + data
            crc = struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)
            return struct.pack(">I", len(data)) + c + crc

        sig = b'\x89PNG\r\n\x1a\n'
        ihdr = chunk(b'IHDR', struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))

        raw = b''
        for y in range(height):
            raw += b'\x00'  # filter byte
            for x in range(width):
                idx = (y * width + x) * 4
                raw += bytes(pixel_data[idx:idx + 4])

        idat = chunk(b'IDAT', zlib.compress(raw))
        iend = chunk(b'IEND', b'')
        return sig + ihdr + idat + iend

    return create_png_raw(width, height, pixels)


def create_ico(png_data: bytes) -> bytes:
    """Wrap PNG data in an ICO container."""
    # ICO header
    ico = struct.pack('<HHH', 0, 1, 1)  # Reserved, Type=1 (ICO), Count=1
    # Directory entry
    w = ICON_WIDTH if ICON_WIDTH < 256 else 0
    h = ICON_HEIGHT if ICON_HEIGHT < 256 else 0
    size = len(png_data)
    offset = 6 + 16  # header + 1 entry
    ico += struct.pack('<BBBBHHIH', w, h, 0, 0, 1, 32, size, offset)
    ico += png_data
    return ico


def main():
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)

    print("Generating VoxiDesk icon...")

    png_data = create_png(ICON_WIDTH, ICON_HEIGHT)
    ico_data = create_ico(png_data)

    with open(PNG_PATH, 'wb') as f:
        f.write(png_data)
    print(f"  ✓ {PNG_PATH} ({len(png_data)} bytes)")

    with open(ICO_PATH, 'wb') as f:
        f.write(ico_data)
    print(f"  ✓ {ICO_PATH} ({len(ico_data)} bytes)")

    print("\nDone! Icon files created successfully.")


if __name__ == "__main__":
    main()
