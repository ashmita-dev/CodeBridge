"""Open the PPTX in Microsoft PowerPoint, count slides, and export each slide to PNG.

Usage: python render_slides.py <output-dir>
"""
import sys
from pathlib import Path

import win32com.client

ROOT = Path(__file__).resolve().parent.parent
PPTX = ROOT / "CodeBridge_Presentation.pptx"
out = Path(sys.argv[1]).resolve()
out.mkdir(parents=True, exist_ok=True)

app = win32com.client.DispatchEx("PowerPoint.Application")
try:
    pres = app.Presentations.Open(str(PPTX), ReadOnly=True, Untitled=False, WithWindow=False)
    count = pres.Slides.Count
    width = pres.PageSetup.SlideWidth / 72
    height = pres.PageSetup.SlideHeight / 72
    for i in range(1, count + 1):
        pres.Slides(i).Export(str(out / f"slide{i:02d}.png"), "PNG", 1600, 900)
    pres.Close()
finally:
    app.Quit()
print(f"PowerPoint slide count: {count}; size {width:.3f} x {height:.3f} in")
sys.exit(0 if count == 15 else 1)
