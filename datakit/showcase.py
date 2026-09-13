"""Portfolio / client-facing visuals: spreadsheet-style before/after cards rendered to PNG.

Cards are 4:3 (2000 x 1500 px), the ratio marketplaces like Upwork use for portfolio thumbnails.
"""
from __future__ import annotations

import re
from collections.abc import Sequence
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

INK, MUTED, FAINT = "#0b0b0b", "#52514e", "#898781"
GRID, SURFACE, CHROME = "#e1e0d9", "#fcfcfb", "#f1f0ea"
BAD_FILL, BAD_INK = "#fde8e6", "#b3261e"
GOOD_FILL, GOOD_INK = "#e3f4e3", "#006300"
SANS = ["Segoe UI", "Inter", "DejaVu Sans"]
MONO = ["Consolas", "DejaVu Sans Mono"]
CARD_SIZE = (40 / 3, 10)
DPI = 150

plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["font.sans-serif"] = SANS


def show_whitespace(value: str) -> str:
    """Make invisible mess visible: leading/trailing and repeated spaces become '·'."""
    lead = len(value) - len(value.lstrip(" "))
    trail = len(value) - len(value.rstrip(" ")) if value.strip(" ") else 0
    core = re.sub(r" {2,}", lambda m: "·" * len(m[0]), value.strip(" "))
    return "·" * lead + core + "·" * trail


def _clip(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _fit_font(width_in: float, n_chars: float, max_size: float, char_w: float) -> float:
    return max(6.5, min(max_size, width_in * 72 / max(n_chars * char_w, 1)))


def new_card() -> Figure:
    return plt.figure(figsize=CARD_SIZE, facecolor=SURFACE)


def save_card(fig: Figure, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=DPI, facecolor=SURFACE)
    plt.close(fig)


def card_header(fig: Figure, eyebrow: str, title: str, subtitle: str) -> None:
    fig.text(0.05, 0.952, eyebrow.upper(), fontsize=11, color=FAINT, fontweight="bold", va="top")
    fig.text(0.05, 0.922, title, fontsize=27, color=INK, fontweight="bold", va="top")
    fig.text(0.05, 0.862, subtitle, fontsize=13, color=MUTED, va="top")


def stat_row(fig: Figure, y: float, stats: Sequence[tuple[str, str]], x0: float = 0.05, x1: float = 0.95) -> float:
    """Big numbers with a muted caption under each. Returns the y below the row."""
    step = (x1 - x0) / len(stats)
    for i, (value, label) in enumerate(stats):
        fig.text(x0 + i * step, y, value, fontsize=30, color=INK, fontweight="bold", va="top")
        fig.text(x0 + i * step, y - 0.062, label, fontsize=11.5, color=MUTED, va="top")
    line_y = y - 0.108
    fig.add_artist(plt.Line2D([x0, x1], [line_y, line_y], color=GRID, linewidth=1))
    return line_y


def section_label(fig: Figure, y: float, text: str, note: str, good: bool) -> None:
    fill, ink = (GOOD_FILL, GOOD_INK) if good else (BAD_FILL, BAD_INK)
    label = fig.text(0.05, y, text, fontsize=12, color=ink, fontweight="bold", va="center",
                     bbox=dict(boxstyle="round,pad=0.45,rounding_size=0.9", facecolor=fill, edgecolor="none"))
    fig.canvas.draw()
    box = label.get_window_extent().transformed(fig.transFigure.inverted())
    fig.text(box.x1 + 0.015, y, note, fontsize=11.5, color=MUTED, va="center")


def draw_sheet(
    fig: Figure,
    top: float,
    frame: pd.DataFrame,
    *,
    highlight: pd.DataFrame | None = None,
    good: bool = False,
    x0: float = 0.05,
    width: float = 0.90,
    max_font: float = 10.5,
    max_chars: int = 32,
    rows_above_header: Sequence[str] = (),
) -> float:
    """Draw a DataFrame as a spreadsheet (column letters, row numbers, grid) with flagged cells tinted.

    ``rows_above_header`` are free-text rows (report titles, blank rows) spilling across columns,
    as they do in real exports. Returns the figure y of the sheet's bottom edge.
    """
    fill, ink = (GOOD_FILL, GOOD_INK) if good else (BAD_FILL, BAD_INK)
    cells = frame.astype(object).where(frame.notna(), "").map(lambda v: _clip(show_whitespace(str(v)), max_chars))
    headers = [str(c) for c in frame.columns]
    widths = [max([len(headers[i])] + [len(v) for v in cells.iloc[:, i]]) + 2.2 for i in range(frame.shape[1])]
    gutter = 3.2
    total = gutter + sum(widths)
    fig_w, fig_h = fig.get_size_inches()
    font = _fit_font(width * fig_w, total, max_font, char_w=0.6)
    n_rows = 1 + len(rows_above_header) + 1 + len(frame)
    row_h = font * 2.0 / 72 / fig_h
    height = row_h * n_rows
    ax = fig.add_axes((x0, top - height, width, height))
    ax.set_xlim(0, total)
    ax.set_ylim(n_rows, 0)
    ax.axis("off")

    edges = [gutter]
    for w in widths:
        edges.append(edges[-1] + w)
    small = font * 0.85
    ax.add_patch(Rectangle((0, 0), total, 1, facecolor=CHROME, edgecolor="none"))
    ax.add_patch(Rectangle((0, 0), gutter, n_rows, facecolor=CHROME, edgecolor="none"))
    for i in range(len(widths)):
        ax.text((edges[i] + edges[i + 1]) / 2, 0.5, chr(65 + i), ha="center", va="center", fontsize=small, color=FAINT)
    for r in range(1, n_rows):
        ax.text(gutter / 2, r + 0.5, str(r), ha="center", va="center", fontsize=small, color=FAINT)

    row = 1
    for text in rows_above_header:
        if text:
            ax.add_patch(Rectangle((gutter, row), total - gutter, 1, facecolor=fill, edgecolor="none"))
            ax.text(edges[0] + 0.8, row + 0.5, text, va="center", fontsize=font, color=ink, fontweight="bold")
        row += 1
    header_row = row
    for i, name in enumerate(headers):
        ax.text(edges[i] + 0.8, row + 0.5, name, va="center", fontsize=font, color=INK, fontweight="bold")
    row += 1
    for r in range(len(frame)):
        for i in range(frame.shape[1]):
            flagged = highlight is not None and bool(highlight.iat[r, i])
            if flagged:
                ax.add_patch(Rectangle((edges[i], row), widths[i], 1, facecolor=fill, edgecolor="none"))
            ax.text(edges[i] + 0.8, row + 0.5, cells.iat[r, i], va="center", fontsize=font, color=ink if flagged else INK)
        row += 1

    for y in range(n_rows + 1):
        ax.plot([0, total], [y, y], color=GRID, linewidth=0.8, solid_capstyle="butt")
    for x in [0, *edges]:
        y_start = header_row if rows_above_header and x not in (0, gutter) else 0
        ax.plot([x, x], [0, 1] if y_start else [0, n_rows], color=GRID, linewidth=0.8)
        if y_start:
            ax.plot([x, x], [y_start, n_rows], color=GRID, linewidth=0.8)
    return top - height


def draw_text_file(
    fig: Figure,
    top: float,
    lines: Sequence[str],
    *,
    x0: float,
    width: float,
    flagged_lines: Sequence[int] = (),
    line_numbers: Sequence[str] | None = None,
    max_font: float = 10.0,
    max_chars: int = 64,
) -> float:
    """Draw raw file lines as in a text editor (line numbers, monospace). Returns the bottom y."""
    shown = [_clip(line, max_chars) for line in lines]
    numbers = list(line_numbers) if line_numbers is not None else [str(i + 1) for i in range(len(shown))]
    fig_w, fig_h = fig.get_size_inches()
    gutter = 3.5
    total = gutter + max(len(s) for s in shown) + 1.5
    font = _fit_font(width * fig_w, total, max_font, char_w=0.56)
    n = len(shown)
    height = font * 1.9 / 72 / fig_h * (n + 0.6)
    ax = fig.add_axes((x0, top - height, width, height))
    ax.set_xlim(0, total)
    ax.set_ylim(n + 0.6, 0)
    ax.axis("off")
    ax.add_patch(Rectangle((0, 0), total, n + 0.6, facecolor="#ffffff", edgecolor=GRID, linewidth=1))
    ax.add_patch(Rectangle((0, 0), gutter, n + 0.6, facecolor=CHROME, edgecolor=GRID, linewidth=1))
    for i, text in enumerate(shown):
        y = i + 0.8
        if i in flagged_lines:
            ax.add_patch(Rectangle((gutter, y - 0.5), total - gutter, 1, facecolor=BAD_FILL, edgecolor="none"))
        ax.text(gutter - 0.8, y, numbers[i], ha="right", va="center", fontsize=font * 0.85, color=FAINT, fontfamily=MONO)
        ax.text(gutter + 0.8, y, text, va="center", fontsize=font, fontfamily=MONO, color=BAD_INK if i in flagged_lines else INK)
    return top - height


def file_caption(fig: Figure, x: float, y: float, name: str, note: str) -> float:
    fig.text(x, y, name, fontsize=11, color=INK, fontweight="bold", va="top", fontfamily=MONO)
    fig.text(x, y - 0.024, note, fontsize=10, color=MUTED, va="top")
    return y - 0.052


def footer(fig: Figure, text: str) -> None:
    fig.text(0.05, 0.03, text, fontsize=10.5, color=FAINT, va="bottom")
