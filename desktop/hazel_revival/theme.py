"""Visual tokens — matches public/css/app.css."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PUBLIC_ASSETS = REPO_ROOT / "public" / "assets"
MASK_IMAGE = PUBLIC_ASSETS / "mask.jpg"

BG = "#070708"
SURFACE = "#141418"
SURFACE_GLASS = "#121216"
BORDER = "#2a2a30"
TEXT = "#f4f4f5"
MUTED = "#9a9aa3"
ACCENT = "#44d62c"
ACCENT_DIM = "#1a3a14"
ERROR = "#ff6b6b"
WARNING = "#f5d090"
WARNING_BG = "#2a2210"
WARNING_BORDER = "#5a4520"

FONT = ("Inter", 13)
FONT_SM = ("Inter", 11)
FONT_XS = ("Inter", 10)
DISPLAY = ("Segoe UI", 28, "bold")
DISPLAY_SM = ("Segoe UI", 16, "bold")

MAX_WIDTH = 520
