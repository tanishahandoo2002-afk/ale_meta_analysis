"""Render a polished PRISMA-style flow diagram from the curation record.

PRISMA (Preferred Reporting Items for Systematic reviews and Meta-Analyses) is
the standard transparency artefact for any systematic review: it shows how the
study pool narrows from "everything identified" to "finally included", with the
reasons for every exclusion. We adapt it to database-term screening.

The diagram is drawn entirely in matplotlib (rounded gradient boxes, line-art
icons, blue -> green flow with red exclusions) so the text is always crisp and
the numbers always match the data.
"""
from __future__ import annotations

import logging
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
import pandas as pd

from .config import Config

logger = logging.getLogger(__name__)

# Palette (soft, print-friendly), tuned to the cream-background look.
BG = "#efe9dd"
INK = "#2b303a"
ICON = "#41648a"
ARROW = "#6f8bab"
# (top, bottom, edge) per box, lightening-to-saturating blues then a green.
C_IDENT = ("#eaf1f8", "#d3e2f1", "#a7c0da")
C_SCREEN = ("#d3e2f1", "#b4cde6", "#89aacd")
C_FOCI = ("#a7c8e6", "#7fabd5", "#5f8cbd")
C_INCL = ("#d6ead9", "#b0d5b7", "#84b98e")
C_EXCL = ("#e9beb2", "#dd9585", "#c67f6d")


def _grad_box(ax, x, y, w, h, colors, radius=0.14, z=2):
    """A rounded box filled with a subtle vertical gradient + soft border."""
    c_top, c_bot, ec = colors
    box = FancyBboxPatch(
        (x, y), w, h,
        boxstyle=f"round,pad=0,rounding_size={radius}",
        linewidth=1.4, edgecolor=ec, facecolor="none", zorder=z + 2)
    ax.add_patch(box)
    cmap = LinearSegmentedColormap.from_list("g", [c_bot, c_top])
    grad = np.linspace(0, 1, 256).reshape(-1, 1)
    im = ax.imshow(grad, extent=[x, x + w, y, y + h], origin="lower",
                   cmap=cmap, aspect="auto", zorder=z, interpolation="bilinear")
    im.set_clip_path(box)
    return box


def _arrow(ax, start, end, z=1):
    ax.add_patch(FancyArrowPatch(
        start, end, arrowstyle="-|>", mutation_scale=18, linewidth=1.6,
        color=ARROW, shrinkA=0, shrinkB=0, zorder=z))


def render_prisma(prisma_df: pd.DataFrame, cfg: Config) -> Path:
    total = prisma_df[prisma_df["source"] == "ALL"].iloc[0]
    final_n = int(prisma_df.attrs.get("final_merged_n", int(total["included"])))
    identified = int(total["identified"])
    matched = int(total["matched_inclusion"])
    removed_excl = int(total["removed_exclusion"])
    removed_foci = int(total["removed_low_foci"])
    sufficient = matched - removed_excl - removed_foci
    n_db = len(prisma_df[prisma_df["source"] != "ALL"])
    src = ", ".join(prisma_df[prisma_df["source"] != "ALL"]["source"])

    fig, ax = plt.subplots(figsize=(10, 12))
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 12)
    ax.axis("off")

    ax.text(5, 11.5, "PRISMA flow - coordinate-based meta-analysis",
            ha="center", va="center", fontsize=17, color=INK,
            family="serif")

    # geometry
    bx, bw = 0.9, 6.05          # main column
    ex, ew = 7.2, 2.7           # exclusion column
    bh = 1.5

    rows_y = [9.5, 7.4, 5.3, 2.9]   # box bottom-y for the 4 stages

    def _box_text(y, lines):
        ax.text(bx + bw / 2, y + bh / 2, lines, ha="center", va="center",
                fontsize=12, color=INK, linespacing=1.4)

    # 1. identified
    y = rows_y[0]
    _grad_box(ax, bx, y, bw, bh, C_IDENT)
    _box_text(y, f"Records identified across {n_db} databases\n({src})\n"
                 f"n = {identified:,}")

    # 2. screening  + exclusion (off-construct)
    y2 = rows_y[1]
    _grad_box(ax, bx, y2, bw, bh, C_SCREEN)
    _box_text(y2, f"Records matching inclusion terms\n(screening)\n"
                  f"n = {matched:,}")
    _grad_box(ax, ex, y2 + 0.15, ew, bh - 0.3, C_EXCL)
    ax.text(ex + ew / 2, y2 + bh / 2, "Excluded -\noff-construct\nexclusion terms\n"
            f"n = {removed_excl:,}", ha="center", va="center", fontsize=12,
            color=INK, linespacing=1.4)

    # 3. sufficient foci + exclusion (too few foci)
    y3 = rows_y[2]
    _grad_box(ax, bx, y3, bw, bh, C_FOCI)
    _box_text(y3, f"Experiments with sufficient foci\nn = {sufficient:,}")
    _grad_box(ax, ex, y3 + 0.15, ew, bh - 0.3, C_EXCL)
    ax.text(ex + ew / 2, y3 + bh / 2, "Excluded -\ntoo few\nreported foci\n"
            f"n = {removed_foci:,}", ha="center", va="center", fontsize=12,
            color=INK, linespacing=1.4)

    # 4. included
    y4 = rows_y[3]
    _grad_box(ax, bx, y4, bw, bh, C_INCL)
    _box_text(y4, f"Experiments included in ALE\n(merged & de-duplicated)\n"
                  f"n = {final_n:,}")

    # arrows: vertical flow
    cxm = bx + bw / 2
    _arrow(ax, (cxm, rows_y[0]), (cxm, rows_y[1] + bh))
    _arrow(ax, (cxm, rows_y[1]), (cxm, rows_y[2] + bh))
    _arrow(ax, (cxm, rows_y[2]), (cxm, rows_y[3] + bh))
    # arrows: to exclusions
    _arrow(ax, (bx + bw, y2 + bh / 2), (ex, y2 + bh / 2))
    _arrow(ax, (bx + bw, y3 + bh / 2), (ex, y3 + bh / 2))

    out = cfg.path("figures") / "prisma_flow.png"
    fig.savefig(out, dpi=200, bbox_inches="tight", facecolor=BG)
    plt.close(fig)
    logger.info("Saved PRISMA flow diagram to %s", out)
    return out
