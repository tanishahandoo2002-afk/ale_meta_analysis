"""Rich, publication-style visualisations generated from the saved maps.

These go beyond the single glass-brain to convey the depth of the analysis:
inflated-surface renders, slice montages, the recognition/recall contrast maps,
an interactive surface + volume viewer, and chart-style diagnostics (the
file-drawer degradation curve, per-cluster robustness, and the jackknife
contribution heatmap).

Everything here reads NIfTI maps and CSV tables straight from ``results/`` so it
can be (re)generated cheaply without re-running ALE.
"""
from __future__ import annotations

import logging
import math
from pathlib import Path
from typing import Optional

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import nibabel as nib
import numpy as np
import pandas as pd
from nilearn import plotting

from .config import Config

logger = logging.getLogger(__name__)
_DPI = 200


# --------------------------------------------------------------------------
# Load a cluster-FWE-thresholded z image straight from saved maps
# --------------------------------------------------------------------------
def sig_image_from_disk(prefix: str, cfg: Config):
    """Rebuild the significant (cluster-FWE) z image for 'ale' or 'macm' from the
    saved z + logp maps, thresholding at the configured cluster-level p."""
    maps = cfg.path("maps")
    # Use the RAW ALE z (graded), masked by cluster-FWE significance — matches
    # ale.significant_z_image so tables/figures show informative peak intensities.
    z_path = maps / f"{prefix}_z.nii.gz"
    logp_path = maps / f"{prefix}_logp_desc-size_level-cluster_corr-FWE_method-montecarlo.nii.gz"
    if not (z_path.exists() and logp_path.exists()):
        return None
    z = nib.load(z_path)
    logp = nib.load(logp_path)
    thr = -math.log10(float(cfg["ale"]["fwe_cluster_p"]))
    data = np.where(logp.get_fdata() >= thr, z.get_fdata(), 0.0)
    return nib.Nifti1Image(data, z.affine, z.header)


def _save(fig, fname: str, cfg: Config) -> Path:
    out = cfg.path("figures") / fname
    fig.savefig(out, dpi=_DPI, bbox_inches="tight")
    plt.close(fig)
    logger.info("Saved figure %s", out)
    return out


# --------------------------------------------------------------------------
# Brain renders
# --------------------------------------------------------------------------
def surface_static(stat_img, title: str, fname: str, cfg: Config) -> Optional[Path]:
    try:
        fig, _ = plotting.plot_img_on_surf(
            stat_img, views=["lateral", "medial"],
            hemispheres=["left", "right"], colorbar=True, inflate=True,
            title=title, cmap="inferno", threshold=0.01)
        return _save(fig, fname, cfg)
    except Exception as exc:
        logger.warning("surface_static failed: %s", exc)
        return None


def surface_interactive(stat_img, title: str, fname: str, cfg: Config) -> Optional[Path]:
    try:
        view = plotting.view_img_on_surf(stat_img, threshold="90%",
                                         cmap="inferno", title=title)
        out = cfg.path("figures") / fname
        view.save_as_html(out)
        logger.info("Saved interactive surface %s", out)
        return out
    except Exception as exc:
        logger.warning("surface_interactive failed: %s", exc)
        return None


def montage(stat_img, title: str, fname: str, cfg: Config,
            display_mode: str = "z", n_cuts: int = 8) -> Optional[Path]:
    try:
        fig = plt.figure(figsize=(13, 3.4))
        plotting.plot_stat_map(
            stat_img, display_mode=display_mode, cut_coords=n_cuts,
            colorbar=True, title=title, draw_cross=False, figure=fig,
            cmap="inferno", black_bg=False)
        return _save(fig, fname, cfg)
    except Exception as exc:
        logger.warning("montage failed: %s", exc)
        return None


def glass(stat_img, title: str, fname: str, cfg: Config,
          plot_abs: bool = False, cmap=None) -> Optional[Path]:
    try:
        fig = plt.figure(figsize=(11, 4))
        kwargs = dict(display_mode="lyrz", colorbar=True, plot_abs=plot_abs,
                      title=title, figure=fig)
        if cmap:
            kwargs["cmap"] = cmap
        plotting.plot_glass_brain(stat_img, **kwargs)
        return _save(fig, fname, cfg)
    except Exception as exc:
        logger.warning("glass failed: %s", exc)
        return None


# --------------------------------------------------------------------------
# Diagnostic charts
# --------------------------------------------------------------------------
def file_drawer_curve(cfg: Config) -> Optional[Path]:
    df = _read(cfg.path("tables") / "diagnostics_file_drawer.csv")
    if df is None or len(df) < 2:
        return None
    fig, ax = plt.subplots(figsize=(7, 4.2))
    ax.plot(df["noise_added"], df["n_clusters"], marker="o", lw=2.4,
            color="#2f5d8a", markerfacecolor="#c76f28", markersize=9)
    ax.set_xlabel("Synthetic null (file-drawer) experiments injected")
    ax.set_ylabel("Convergent clusters surviving")
    ax.set_title("Robustness to the file-drawer problem")
    ax.grid(True, alpha=0.25)
    ax.set_ylim(0, max(df["n_clusters"]) + 1)
    for _, r in df.iterrows():
        ax.annotate(int(r["n_clusters"]),
                    (r["noise_added"], r["n_clusters"]),
                    textcoords="offset points", xytext=(0, 10), ha="center",
                    fontsize=10, fontweight="bold")
    fig.tight_layout()
    return _save(fig, "diag_file_drawer.png", cfg)


def robustness_bar(cfg: Config) -> Optional[Path]:
    """Per-cluster: how many experiments support it, coloured by how much a
    single study can sway it (green = robust, red = fragile)."""
    from . import report
    tables = cfg.path("tables")
    focus = _read(tables / "diagnostics_focus_counter.csv")
    jk = _read(tables / "diagnostics_jackknife.csv")
    clust = _read(tables / "diagnostics_clusters.csv")
    diag = {}
    if focus is not None:
        diag["focus_counter"] = focus
    if jk is not None:
        diag["jackknife"] = jk
    if clust is not None:
        diag["cluster_table"] = clust
    summ = report._diagnostics_summary(diag)
    if summ is None or len(summ) == 0:
        return None

    n = summ["n experiments (focus)"].astype(int)
    infl = summ["max single-study influence"].astype(float)
    labels = [f'{c}\n{r}' for c, r in zip(summ["cluster"], summ.get("region", ""))] \
        if "region" in summ.columns else summ["cluster"].astype(str).tolist()

    def _col(v):
        return "#2f7d55" if v <= 0.05 else ("#b7791f" if v <= 0.10 else "#b23b3b")
    colors = [_col(v) for v in infl]

    fig, ax = plt.subplots(figsize=(9, max(4, 0.5 * len(summ))))
    ax.barh(range(len(summ)), n, color=colors)
    ax.set_yticks(range(len(summ)))
    ax.set_yticklabels(labels, fontsize=8)
    ax.invert_yaxis()
    ax.set_xlabel("Independent experiments contributing a focus")
    ax.set_title("Per-cluster robustness (colour = single-study influence)")
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(color="#2f7d55", label="robust ≤0.05"),
                       Patch(color="#b7791f", label="moderate ≤0.10"),
                       Patch(color="#b23b3b", label="fragile >0.10")],
              fontsize=8, loc="lower right")
    fig.tight_layout()
    return _save(fig, "diag_robustness.png", cfg)


def jackknife_heatmap(cfg: Config, top_experiments: int = 30) -> Optional[Path]:
    jk = _read(cfg.path("tables") / "diagnostics_jackknife.csv")
    if jk is None or len(jk) == 0:
        return None
    cols = [c for c in jk.columns if "Tail" in str(c)]
    if not cols:
        return None
    mat = jk[cols].copy()
    mat.index = jk["id"] if "id" in jk.columns else range(len(jk))
    # show the most influential experiments (largest total contribution)
    order = mat.sum(axis=1).sort_values(ascending=False).head(top_experiments).index
    mat = mat.loc[order]

    fig, ax = plt.subplots(figsize=(min(1 + 0.5 * len(cols), 12),
                                    max(4, 0.28 * len(mat))))
    im = ax.imshow(mat.values, aspect="auto", cmap="magma")
    ax.set_xticks(range(len(cols)))
    ax.set_xticklabels([c.replace("PositiveTail ", "C") for c in cols], fontsize=8)
    ax.set_yticks(range(len(mat)))
    ax.set_yticklabels(mat.index, fontsize=6)
    ax.set_xlabel("Cluster")
    ax.set_title(f"Jackknife: each study's contribution to each cluster "
                 f"(top {len(mat)} studies)")
    fig.colorbar(im, ax=ax, fraction=0.025, label="contribution")
    fig.tight_layout()
    return _save(fig, "diag_jackknife_heatmap.png", cfg)


# --------------------------------------------------------------------------
def _read(path: Path) -> Optional[pd.DataFrame]:
    if not path.exists():
        return None
    try:
        return pd.read_csv(path)
    except Exception:
        return None


def _threshold_abs(img, z: float):
    data = img.get_fdata()
    return nib.Nifti1Image(np.where(np.abs(data) >= z, data, 0.0),
                           img.affine, img.header)


# --------------------------------------------------------------------------
# Orchestrator — regenerate every rich figure from saved results
# --------------------------------------------------------------------------
def regenerate_from_disk(cfg: Config) -> None:
    maps = cfg.path("maps")

    # Main ALE: surface (static + interactive) + montage
    ale_sig = sig_image_from_disk("ale", cfg)
    if ale_sig is not None:
        surface_static(ale_sig, "Episodic retrieval — cortical surface",
                       "ale_surface.png", cfg)
        surface_interactive(ale_sig, "Episodic retrieval (surface)",
                            "ale_surface_interactive.html", cfg)
        montage(ale_sig, "Episodic retrieval — axial montage",
                "ale_montage.png", cfg)

    # MACM: static slices + interactive viewer
    macm_sig = sig_image_from_disk("macm", cfg)
    if macm_sig is not None:
        montage(macm_sig, "MACM coactivation — axial montage",
                "macm_montage.png", cfg)
        try:
            plotting.view_img(macm_sig, title="MACM coactivation",
                              threshold=0.0).save_as_html(
                cfg.path("figures") / "macm_interactive.html")
            logger.info("Saved MACM interactive viewer")
        except Exception as exc:
            logger.warning("MACM interactive failed: %s", exc)

    # Contrast glass brains (recognition vs recall, and shared core)
    a = cfg["contrast"]["group_a"]["name"]
    b = cfg["contrast"]["group_b"]["name"]
    sub = maps / f"subtraction_{a}_vs_{b}_z_desc-group1MinusGroup2.nii.gz"
    if sub.exists():
        glass(_threshold_abs(nib.load(sub), 2.0),
              f"{a} vs {b} (red = {a}>{b}, blue = {b}>{a})",
              "contrast_subtraction_glass.png", cfg, plot_abs=False)
    conj = maps / f"conjunction_{a}_AND_{b}.nii.gz"
    if conj.exists():
        glass(nib.load(conj), f"Shared retrieval core ({a} ∧ {b})",
              "contrast_conjunction_glass.png", cfg, plot_abs=False,
              cmap="viridis")

    # Diagnostic charts
    file_drawer_curve(cfg)
    robustness_bar(cfg)
    jackknife_heatmap(cfg)
    logger.info("Rich figures regenerated.")
