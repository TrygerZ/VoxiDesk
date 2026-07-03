"""Central design tokens for VoxiDesk — warm graphite + Claude orange (dark-only).

This module is the single source of truth for colors, fonts, and spacing.
UI code must import from here instead of hardcoding hex literals so the whole
app stays visually consistent and easy to retune.
"""

# --- Color palette (warm graphite neutrals + Claude terracotta accent) ---

# Surfaces
BG_BASE = "#1A1917"       # App window background (warm near-black)
SURFACE = "#232220"       # Panels / cards
SURFACE_HI = "#2C2A27"    # Elevated rows, inputs, dropzone
BORDER = "#38352F"        # Hairline separators, input borders

# Accent (Claude orange)
ACCENT = "#D97757"        # Primary buttons, progress, focus, current match
ACCENT_HOVER = "#C4633F"  # Hover / pressed
ACCENT_SOFT = "#3A2A22"   # Subtle orange-tinted fill (drag-active, highlights)

# Text
TEXT = "#ECEAE3"          # Primary warm off-white
TEXT_MUTED = "#928E84"    # Secondary / help text
TEXT_DISABLED = "#5C584F" # Disabled text
TEXT_ON_ACCENT = "#1A1917"  # Text drawn on top of an accent fill

# Semantic status
SUCCESS = "#7FB069"       # Done / CUDA available
WARNING = "#E0A458"       # Warnings
DANGER = "#CC6B57"        # Cancel / delete / error
DANGER_HOVER = "#B5573F"  # Danger hover

# Search highlight (on the read-only preview textbox)
HIGHLIGHT_BG = ACCENT_SOFT
HIGHLIGHT_FG = TEXT
HIGHLIGHT_CURRENT_BG = ACCENT
HIGHLIGHT_CURRENT_FG = TEXT_ON_ACCENT

# --- Typography ---

FONT_FAMILY = "Segoe UI"
FONT_MONO = "Consolas"


def font(size: int, weight: str = "normal") -> tuple:
    """Return a UI font tuple for the given size and weight."""
    return (FONT_FAMILY, size, weight)


def mono(size: int, weight: str = "normal") -> tuple:
    """Return a monospace font tuple (used for logs)."""
    return (FONT_MONO, size, weight)


# Named type scale (hierarchy comes from size/weight, not emoji)
FONT_TITLE = font(15, "bold")     # Page / section title, wordmark
FONT_HEADER = font(13, "bold")    # Card header
FONT_BODY = font(12)              # Body / control text
FONT_CAPTION = font(11)           # Help / caption text
FONT_LOG = mono(11)               # Log output

# --- Spacing & geometry ---

GAP = 16          # Vertical gap between major sections
PAD_X = 20        # Standard inner horizontal padding
PAD_Y = 14        # Standard inner vertical padding
RADIUS_BTN = 8    # Button corner radius
RADIUS_CARD = 12  # Card / panel corner radius
