#!/usr/bin/env python
"""Publication-supporting analyses that stand alongside the main ALE:

1. **Sleuth / GingerALE export** — write the included coordinates in the exact
   text format GingerALE (BrainMap) reads, so the whole analysis can be
   independently reproduced in the classic tool named in the brief.
2. **Sensitivity analysis** — re-run ALE under a *stricter* construct definition
   (each study must load on >=2 inclusion terms) and quantify how much the
   convergent map changes. A result that survives a stricter filter is not an
   artefact of loose selection.
3. **Cross-database validation** — run ALE separately on Neurosynth-only and
   NeuroQuery-only studies and measure spatial agreement. Convergence found by
   two independently built databases is far more credible than either alone.

Writes distinct output files under results/ (never clobbers the main ALE maps).

Usage:  PYTHONPATH=src python scripts/publication_extras.py [--n-iters 1000]
"""
from __future__ import annotations

import argparse
import logging
from pathlib import Path

import numpy as np
import pandas as pd

from ale_meta import ale, anatomy, curation, datasets
from ale_meta.config import load_config


# --------------------------------------------------------------------------
def export_sleuth(merged, cfg) -> Path:
    """Write GingerALE/Sleuth-format text: one block per experiment with a
    reference-space header, a subject count, then its coordinate list."""
    out_dir = cfg.root / "results" / "gingerale"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "episodic_retrieval_sleuth.txt"

    coords = merged.coordinates
    # sample sizes (fixed nominal, since databases lack per-study n)
    n_default = int(cfg["ale"].get("fixed_sample_size", 20))
    lines = ["// Reference=MNI", ""]
    for sid, grp in coords.groupby("id"):
        lines.append(f"// {sid}")
        lines.append(f"// Subjects={n_default}")
        for _, r in grp.iterrows():
            lines.append(f"{r['x']:.1f}\t{r['y']:.1f}\t{r['z']:.1f}")
        lines.append("")
    out.write_text("\n".join(lines))
    logging.info("Wrote %d experiments to Sleuth file %s",
                 coords['id'].nunique(), out)
    return out


# --------------------------------------------------------------------------
def _ale_clusters(dset, cfg, n_iters):
    """Run ALE+FWE on a dataset and return a labelled cluster table."""
    est = ale.make_estimator(cfg)
    res = est.fit(dset)
    corr = ale.make_corrector(cfg, n_iters=n_iters).transform(res)
    sig = ale.significant_z_image(corr, cfg)
    return anatomy.clusters_from_image(sig), sig


def _concordance(a: pd.DataFrame, b: pd.DataFrame, radius=12.0) -> dict:
    """Fraction of clusters in `a` with a peak within `radius` mm of some peak
    in `b`, and vice-versa (a simple spatial-agreement metric)."""
    if a is None or b is None or len(a) == 0 or len(b) == 0:
        return {"a_in_b": 0.0, "b_in_a": 0.0, "n_a": len(a) if a is not None else 0,
                "n_b": len(b) if b is not None else 0}
    pa = a[["X", "Y", "Z"]].values
    pb = b[["X", "Y", "Z"]].values

    def frac(src, dst):
        hit = 0
        for p in src:
            if np.min(np.linalg.norm(dst - p, axis=1)) <= radius:
                hit += 1
        return hit / len(src)
    return {"a_in_b": round(frac(pa, pb), 3), "b_in_a": round(frac(pb, pa), 3),
            "n_a": len(a), "n_b": len(b)}


# --------------------------------------------------------------------------
def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--n-iters", type=int, default=1000,
                   help="permutations for these supporting ALEs (default 1000)")
    args = p.parse_args()

    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(message)s",
                        datefmt="%H:%M:%S")
    cfg = load_config()
    tables = cfg.path("tables")
    dsets = datasets.fetch_all(cfg)

    # --- main curation (baseline) -----------------------------------------
    merged, _ = curation.curate_all(dsets, cfg)

    # 1. Sleuth export ------------------------------------------------------
    export_sleuth(merged, cfg)

    # main-result clusters (for comparison)
    logging.info("Baseline ALE for comparison (%d exps)...", len(merged.ids))
    main_clusters, _ = _ale_clusters(merged, cfg, args.n_iters)
    main_clusters.to_csv(tables / "validation_baseline_clusters.csv", index=False)

    # 2. Sensitivity: stricter construct (>=2 inclusion terms) -------------
    logging.info("Sensitivity analysis: min_inclusion_matches = 2 ...")
    strict_cfg = load_config()
    strict_cfg.raw["curation"]["min_inclusion_matches"] = 2
    strict_merged, _ = curation.curate_all(dsets, strict_cfg)
    logging.info("Strict construct kept %d experiments", len(strict_merged.ids))
    strict_clusters, _ = _ale_clusters(strict_merged, strict_cfg, args.n_iters)
    strict_clusters.to_csv(tables / "sensitivity_clusters.csv", index=False)
    sens = _concordance(main_clusters, strict_clusters)

    # 3. Cross-database validation -----------------------------------------
    logging.info("Cross-database validation (Neurosynth vs NeuroQuery)...")
    per_db = {}
    for src, dset in dsets.items():
        inc, _ = curation.curate_database(src, dset, cfg)
        if inc is None:
            continue
        cl, _ = _ale_clusters(inc, cfg, args.n_iters)
        cl.to_csv(tables / f"crossdb_{src}_clusters.csv", index=False)
        per_db[src] = cl
        logging.info("  %s: %d experiments -> %d clusters", src, len(inc.ids), len(cl))
    crossdb = {}
    if len(per_db) == 2:
        (na, ca), (nb, cb) = list(per_db.items())
        crossdb = {"db_a": na, "db_b": nb, **_concordance(ca, cb)}

    # --- summary -----------------------------------------------------------
    summary = {
        "sensitivity": {"strict_n_experiments": len(strict_merged.ids), **sens},
        "cross_database": crossdb,
    }
    (tables / "validation_summary.json").write_text(
        __import__("json").dumps(summary, indent=2))
    logging.info("Sensitivity: %.0f%% of baseline clusters replicate under the "
                 "stricter construct (n=%d).", 100 * sens["a_in_b"],
                 summary["sensitivity"]["strict_n_experiments"])
    if crossdb:
        logging.info("Cross-database: %.0f%% of %s clusters have a match in %s "
                     "(and %.0f%% vice-versa).", 100 * crossdb["a_in_b"],
                     crossdb["db_a"], crossdb["db_b"], 100 * crossdb["b_in_a"])
    logging.info("Publication extras complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
