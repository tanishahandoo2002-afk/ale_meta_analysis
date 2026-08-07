"""Visualisation of ALE results.

A clean brain rendering of the convergent clusters is the single most important
visual asset of a meta-analysis. We produce, for any thresholded statistical
map:

* a **glass-brain** maximum-intensity projection (the classic meta-analysis
  figure),
* an **orthogonal slice** stat-map overlaid on the MNI152 template,
* an **interactive HTML** viewer (nilearn) so the result can be explored in a
  browser without any neuroimaging software,
* bar charts for functional-decoding terms and jackknife contributions.

Everything is theme-neutral and saved at publication DPI.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import matplotlib
matplotlib.use("Agg")  # headless rendering
import matplotlib.pyplot as plt
import pandas as pd
from nilearn import plotting

from .config import Config

logger = logging.getLogger(__name__)
_DPI = 200


def glass_brain(stat_img, title: str, fname: str, cfg: Config) -> Path:
    fig = plt.figure(figsize=(10, 4))
    display = plotting.plot_glass_brain(
        stat_img, display_mode="lyrz", colorbar=True, plot_abs=False,
        title=title, figure=fig,
    )
    out = cfg.path("figures") / fname
    fig.savefig(out, dpi=_DPI, bbox_inches="tight")
    plt.close(fig)
    logger.info("Saved glass-brain figure to %s", out)
    return out


def stat_slices(stat_img, title: str, fname: str, cfg: Config) -> Path:
    fig = plt.figure(figsize=(12, 4))
    plotting.plot_stat_map(
        stat_img, display_mode="ortho", colorbar=True, title=title,
        draw_cross=False, figure=fig,
    )
    out = cfg.path("figures") / fname
    fig.savefig(out, dpi=_DPI, bbox_inches="tight")
    plt.close(fig)
    logger.info("Saved slice figure to %s", out)
    return out


def interactive_html(stat_img, title: str, fname: str, cfg: Config) -> Path:
    view = plotting.view_img(stat_img, title=title, threshold=0.0)
    out = cfg.path("figures") / fname
    view.save_as_html(out)
    logger.info("Saved interactive viewer to %s", out)
    return out


def barh(df: pd.DataFrame, label_col: str, value_col: str, title: str,
         fname: str, cfg: Config) -> Optional[Path]:
    if df is None or len(df) == 0:
        return None
    d = df.iloc[::-1]  # largest at top
    fig, ax = plt.subplots(figsize=(8, max(3, 0.35 * len(d))))
    ax.barh(d[label_col].astype(str), d[value_col], color="#4C72B0")
    ax.set_xlabel(value_col)
    ax.set_title(title)
    fig.tight_layout()
    out = cfg.path("figures") / fname
    fig.savefig(out, dpi=_DPI, bbox_inches="tight")
    plt.close(fig)
    logger.info("Saved bar chart to %s", out)
    return out
