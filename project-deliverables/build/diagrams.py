"""Draw the report diagrams (architecture and compiler pipeline) as PNG files.

The boxes mirror the real modules in backend/app and frontend/src.
Run: python diagrams.py  (needs matplotlib)
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "assets" / "diagrams"
OUT.mkdir(parents=True, exist_ok=True)

INK = "#0f172a"
MUTED = "#475569"
TEAL = "#0d9488"
TEAL_BG = "#ccfbf1"
BLUE_BG = "#dbeafe"
BLUE = "#1d4ed8"
SLATE_BG = "#f1f5f9"
RED = "#b91c1c"
FONT = "Segoe UI"
plt.rcParams["font.family"] = FONT


def box(ax, x, y, w, h, title, sub=None, fc=SLATE_BG, ec=MUTED, title_size=11, sub_size=8.5, bold=True):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.08",
                                fc=fc, ec=ec, lw=1.3))
    if sub:
        ax.text(x + w / 2, y + h * 0.64, title, ha="center", va="center", fontsize=title_size,
                fontweight="bold" if bold else "normal", color=INK)
        ax.text(x + w / 2, y + h * 0.30, sub, ha="center", va="center", fontsize=sub_size, color=MUTED,
                linespacing=1.25)
    else:
        ax.text(x + w / 2, y + h / 2, title, ha="center", va="center", fontsize=title_size,
                fontweight="bold" if bold else "normal", color=INK)


def arrow(ax, x1, y1, x2, y2, text=None, color=INK, style="-|>", dashed=False, text_offset=(0, 0.12), fs=8.5):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle=style, mutation_scale=13, lw=1.3,
                                 color=color, linestyle=(0, (4, 3)) if dashed else "-"))
    if text:
        ax.text((x1 + x2) / 2 + text_offset[0], (y1 + y2) / 2 + text_offset[1], text, ha="center",
                va="bottom", fontsize=fs, color=color)


def architecture():
    fig, ax = plt.subplots(figsize=(10, 5.6), dpi=220)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 5.6)
    ax.axis("off")

    # Frontend (Vercel)
    ax.add_patch(FancyBboxPatch((0.15, 0.35), 3.3, 4.85, boxstyle="round,pad=0.02,rounding_size=0.12",
                                fc="white", ec=BLUE, lw=1.6))
    ax.text(1.8, 4.92, "Browser: React frontend", ha="center", fontsize=11.5, fontweight="bold", color=BLUE)
    ax.text(1.8, 4.62, "Vite + TypeScript + Tailwind  ·  hosted on Vercel", ha="center", fontsize=8.3, color=MUTED)
    box(ax, 0.4, 3.2, 2.8, 1.2, "lib/api.ts · useCompiler", "fetch POST /compile, GET /health\n650 ms auto-compile debounce\n"
        "VITE_API_URL set at build time", fc=BLUE_BG, ec=BLUE)
    box(ax, 0.4, 1.95, 2.8, 0.95, "CodeMirror 6 editor", "syntax highlighting,\ninline error markers", fc=BLUE_BG, ec=BLUE)
    box(ax, 0.4, 0.7, 2.8, 0.95, "Pipeline strip + tabs", "C++, Tokens, AST, Symbols,\nTAC, Optimized TAC, Diagnostics",
        fc=BLUE_BG, ec=BLUE)

    # Backend (Render)
    ax.add_patch(FancyBboxPatch((4.55, 0.35), 5.3, 4.85, boxstyle="round,pad=0.02,rounding_size=0.12",
                                fc="white", ec=TEAL, lw=1.6))
    ax.text(7.2, 4.92, "FastAPI backend (Python 3.13)", ha="center", fontsize=11.5, fontweight="bold", color=TEAL)
    ax.text(7.2, 4.62, "Uvicorn  ·  hosted on Render", ha="center", fontsize=8.3, color=MUTED)
    box(ax, 4.8, 3.45, 2.3, 0.95, "app/main.py", "GET /health · POST /compile\nCORS · 413 · JSON 500", fc=TEAL_BG, ec=TEAL)
    box(ax, 7.3, 3.45, 2.3, 0.95, "config · schemas", "CORS_ORIGINS,\nMAX_SOURCE_CHARS · Pydantic", fc=TEAL_BG, ec=TEAL,
        sub_size=8)
    box(ax, 4.8, 2.4, 4.8, 0.8, "pipeline.compile_source()", "runs the phases in order, times each, stops at the first failing phase",
        fc=TEAL_BG, ec=TEAL)
    ax.text(9.6, 2.2, "app/compiler (no web dependencies)", ha="right", va="top", fontsize=8.3, color=MUTED,
            style="italic")
    # Six phase modules, snaking: top row left-to-right, bottom row right-to-left.
    w, h, step = 1.35, 0.5, 1.725
    top = ["lexer", "parser", "semantic"]
    bottom = ["codegen_cpp", "optimizer", "tacgen"]
    for i, n in enumerate(top):
        box(ax, 4.8 + i * step, 1.35, w, h, n, None, fc=SLATE_BG, ec=TEAL, title_size=9)
    for i, n in enumerate(bottom):
        box(ax, 4.8 + i * step, 0.55, w, h, n, None, fc=SLATE_BG, ec=TEAL, title_size=9)
    for i in range(2):
        arrow(ax, 4.8 + i * step + w, 1.6, 4.8 + (i + 1) * step, 1.6)
        arrow(ax, 4.8 + (i + 1) * step, 0.8, 4.8 + i * step + w, 0.8)
    arrow(ax, 4.8 + 2 * step + w / 2, 1.35, 4.8 + 2 * step + w / 2, 1.05)

    arrow(ax, 3.2, 4.05, 4.8, 4.05, "JSON request", color=BLUE, text_offset=(0, 0.04), fs=8)
    arrow(ax, 4.8, 3.6, 3.2, 3.6, "JSON response", color=TEAL, text_offset=(0, -0.3), fs=8)
    arrow(ax, 5.95, 3.45, 5.95, 3.2)
    arrow(ax, 4.8 + w / 2, 2.4, 4.8 + w / 2, 1.85)
    fig.savefig(OUT / "architecture.png", bbox_inches="tight", facecolor="white")
    plt.close(fig)


def pipeline():
    fig, ax = plt.subplots(figsize=(10, 3.3), dpi=220)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 3.3)
    ax.axis("off")
    phases = [
        ("Lexer", "lexer.py", "tokens"),
        ("Parser", "parser.py", "AST"),
        ("Semantic", "semantic.py", "typed AST +\nsymbol table"),
        ("TAC", "tacgen.py", "three-address\ncode"),
        ("Optimizer", "optimizer.py", "optimized TAC"),
        ("C++ gen", "codegen_cpp.py", "C++17 source"),
    ]
    w, gap, x0, y = 1.38, 0.25, 0.08, 1.75
    ax.text(x0, 3.08, "source text", fontsize=9, color=MUTED)
    for i, (title, mod, out) in enumerate(phases):
        x = x0 + i * (w + gap)
        box(ax, x, y, w, 0.95, title, mod, fc=TEAL_BG, ec=TEAL, title_size=10.5, sub_size=8)
        ax.text(x + w / 2, y - 0.12, out, ha="center", va="top", fontsize=8.2, color=INK, linespacing=1.2)
        if i < len(phases) - 1:
            arrow(ax, x + w, y + 0.47, x + w + gap, y + 0.47)
    # error paths
    ax.add_patch(FancyBboxPatch((x0 + 0.3, 0.12), 4.2, 0.5, boxstyle="round,pad=0.02,rounding_size=0.08",
                                fc="#fee2e2", ec=RED, lw=1.2))
    ax.text(x0 + 2.4, 0.37, "structured diagnostics: stage, code, message, line:column", ha="center",
            va="center", fontsize=8.6, color=RED)
    for i, code in enumerate(["L001–L005", "P001–P002", "S001–S006"]):
        cx = x0 + i * (w + gap) + w / 2
        arrow(ax, cx, y - 0.62, cx, 0.62, color=RED, dashed=True)
        ax.text(cx + 0.06, 0.95, code, fontsize=7.6, color=RED, ha="left")
    ax.text(x0 + 4.7, 0.37, "a failing phase stops the pipeline; later phases are skipped and\nno TAC or C++ is returned",
            fontsize=8.2, color=MUTED, va="center")
    fig.savefig(OUT / "pipeline.png", bbox_inches="tight", facecolor="white")
    plt.close(fig)


if __name__ == "__main__":
    architecture()
    pipeline()
    print("diagrams written to", OUT)
