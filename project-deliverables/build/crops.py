"""Crop the live screenshots to the panel each figure discusses.

Crops are taken from the unmodified captures in assets/screenshots and saved
to assets/screenshots/crops; nothing is drawn or edited, only trimmed.
Coordinates are in pixels of the 2880x1800 (2x) captures.
"""
from pathlib import Path

from PIL import Image

SHOTS = Path(__file__).resolve().parent.parent / "assets" / "screenshots"
OUT = SHOTS / "crops"
OUT.mkdir(exist_ok=True)

RIGHT_PANEL = 1218  # x where the output panel starts
CROPS = {
    # name: (source, (left, top, right, bottom))
    "optimized-panel": ("live-optimized", (RIGHT_PANEL, 140, 2860, 1230)),
    "symbols-panel": ("live-symbols", (RIGHT_PANEL, 140, 2860, 1230)),
    "tokens-panel": ("live-tokens", (RIGHT_PANEL, 140, 2860, 1230)),
    "ast-panel": ("live-ast", (RIGHT_PANEL, 140, 2860, 1230)),
    "diagnostics-panel": ("live-diagnostics-semantic", (RIGHT_PANEL, 140, 2860, 1330)),
    "mobile-top": ("live-mobile", (0, 0, 1000, 1480)),
}

if __name__ == "__main__":
    for name, (src, box) in CROPS.items():
        Image.open(SHOTS / f"{src}.png").crop(box).save(OUT / f"{name}.png", optimize=True)
    print("crops written to", OUT)
