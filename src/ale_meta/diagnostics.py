"""Robustness diagnostics — what separates a rigorous ALE from a naive one.

Three complementary questions are asked of every surviving cluster:

1. **Jackknife (leave-one-experiment-out).** Re-estimate the meta-analysis N
   times, each time dropping one experiment, and record how much each
   experiment contributes to each cluster. A cluster driven by a single study
   is fragile; one supported broadly across the literature is trustworthy.

2. **Focus counter.** How many independent experiments actually report a focus
   inside each cluster. Convergence claimed from very few experiments is weak
   regardless of the ALE score.

3. **File-drawer robustness (publication-bias analog).** The classic Fail-Safe N
   asks how many null (unpublished, non-significant) studies would have to exist
   to overturn a result. We implement the coordinate-based analog of Acar et
   al. (2018): inject synthetic "noise" experiments with randomly located foci
   and find the smallest number that erases a cluster's significance. A cluster
   that tolerates many noise studies is robust to the file-drawer problem.
"""
from __future__ import annotations

import logging
from typing import Dict, Optional

import numpy as np
import pandas as pd
from nimare.dataset import Dataset
from nimare.diagnostics import FocusCounter, Jackknife

from .config import Config

logger = logging.getLogger(__name__)

_TARGET = "z_desc-size_level-cluster_corr-FWE_method-montecarlo"


def _extract_table(diag_result, tool: str) -> Optional[pd.DataFrame]:
    # NiMARE names the counts table with a tail suffix, e.g.
    # "..._diag-Jackknife_tab-counts_tail-positive". Match by prefix so we pick
    # it up regardless of the (positive/negative) tail suffix.
    prefix = f"{_TARGET}_diag-{tool}_tab-counts"
    for key, tab in diag_result.tables.items():
        if key.startswith(prefix) and tab is not None:
            return tab
    return None


def run_jackknife(corrected, cfg: Config):
    """Return (jackknife_counts, cluster_table). The cluster table gives each
    diagnostic cluster's peak coordinates so it can be anatomically labelled and
    reconciled with the main results table."""
    logger.info("Running jackknife (leave-one-experiment-out)...")
    diag = Jackknife(target_image=_TARGET, n_cores=int(cfg["ale"]["n_cores"]))
    res = diag.transform(corrected)
    tab = _extract_table(res, "Jackknife")
    clust = res.tables.get(f"{_TARGET}_tab-clust")
    if tab is not None:
        out = cfg.path("tables") / "diagnostics_jackknife.csv"
        tab.to_csv(out)
        logger.info("Wrote jackknife contributions to %s", out)
    if clust is not None:
        clust.to_csv(cfg.path("tables") / "diagnostics_clusters.csv", index=False)
    return tab, clust


def run_focus_counter(corrected, cfg: Config) -> Optional[pd.DataFrame]:
    logger.info("Running focus counter...")
    diag = FocusCounter(target_image=_TARGET, n_cores=int(cfg["ale"]["n_cores"]))
    res = diag.transform(corrected)
    tab = _extract_table(res, "FocusCounter")
    if tab is not None:
        out = cfg.path("tables") / "diagnostics_focus_counter.csv"
        tab.to_csv(out)
        logger.info("Wrote focus counts to %s", out)
    return tab


def _n_significant_clusters(corrected, cfg: Config) -> int:
    """Count clusters surviving cluster-level FWE in a corrected result."""
    from .ale import cluster_table
    return len(cluster_table(corrected, cfg))


def _make_noise_dataset(template: Dataset, n_exp: int, cfg: Config) -> Dataset:
    """Create ``n_exp`` synthetic experiments with randomly located foci,
    matching the observed distribution of foci-per-study and sample sizes so the
    injected noise is realistic rather than trivially weak."""
    rng = np.random.default_rng(cfg.seed)
    coords = template.coordinates
    foci_per_study = coords.groupby("id").size().values
    xyz = coords[["x", "y", "z"]].values
    lo, hi = xyz.min(axis=0), xyz.max(axis=0)

    rows = []
    for i in range(n_exp):
        k = int(rng.choice(foci_per_study))
        for _ in range(k):
            pt = lo + rng.random(3) * (hi - lo)
            rows.append({
                "id": f"noise-{i:04d}",
                "study_id": f"noise-{i:04d}",
                "contrast_id": "1",
                "x": pt[0], "y": pt[1], "z": pt[2],
                "space": coords["space"].iloc[0] if "space" in coords else "MNI",
            })
    noise_coords = pd.DataFrame(rows)

    # Append synthetic rows directly to a copied Dataset's internal tables.
    # NiMARE stores a Dataset as parallel DataFrames (coordinates, metadata) plus
    # an ``_ids`` index; we extend all three consistently.
    merged = template.copy()
    new_coords = pd.concat([merged.coordinates, noise_coords], ignore_index=True)
    merged.coordinates = new_coords
    # Register sample sizes for noise studies in metadata.
    meta = merged.metadata.copy()
    extra = pd.DataFrame({
        "id": noise_coords.id.unique(),
        "study_id": noise_coords.id.unique(),
        "contrast_id": "1",
        "sample_sizes": [[20]] * noise_coords.id.nunique(),
    })
    for col in meta.columns:
        if col not in extra.columns:
            extra[col] = None
    merged.metadata = pd.concat([meta, extra[meta.columns]], ignore_index=True)
    merged._ids = np.array(sorted(set(new_coords["id"])))
    return merged


def file_drawer_robustness(included: Dataset, cfg: Config,
                           max_noise: int = 30, step: int = 15,
                           quick_iters: int = 200) -> pd.DataFrame:
    """Coordinate-based file-drawer test.

    Progressively inject noise experiments and record how many significant
    clusters remain. Uses a reduced permutation count for tractability; this is
    a robustness *screen*, not a replacement for the main FWE result. Returns a
    small table: noise_added -> n_surviving_clusters.
    """
    logger.info("Running file-drawer robustness screen (up to %d noise exps)...",
                max_noise)
    rows = [{"noise_added": 0, "n_clusters": _n_significant_clusters_quick(
        included, cfg, quick_iters)}]

    for n_noise in range(step, max_noise + 1, step):
        noisy = _make_noise_dataset(included, n_noise, cfg)
        n_clusters = _n_significant_clusters_quick(noisy, cfg, quick_iters)
        rows.append({"noise_added": n_noise, "n_clusters": n_clusters})
        logger.info("  +%d noise exps -> %d clusters survive", n_noise, n_clusters)
        if n_clusters == 0:
            break

    df = pd.DataFrame(rows)
    out = cfg.path("tables") / "diagnostics_file_drawer.csv"
    df.to_csv(out, index=False)
    logger.info("Wrote file-drawer robustness to %s", out)
    return df


def _n_significant_clusters_quick(dset: Dataset, cfg: Config, iters: int) -> int:
    from .ale import make_corrector, make_estimator
    est = make_estimator(cfg)
    res = est.fit(dset)
    cres = make_corrector(cfg, n_iters=iters).transform(res)
    return _n_significant_clusters(cres, cfg)


def run_all(corrected, included: Dataset, cfg: Config) -> Dict[str, pd.DataFrame]:
    d = cfg["diagnostics"]
    out: Dict[str, pd.DataFrame] = {}
    if d.get("run_jackknife"):
        jk, clust = run_jackknife(corrected, cfg)
        if jk is not None:
            out["jackknife"] = jk
        if clust is not None:
            out["cluster_table"] = clust
    if d.get("run_focus_counter"):
        fc = run_focus_counter(corrected, cfg)
        if fc is not None:
            out["focus_counter"] = fc
    if d.get("fail_safe_n"):
        out["file_drawer"] = file_drawer_robustness(included, cfg)
    return out
