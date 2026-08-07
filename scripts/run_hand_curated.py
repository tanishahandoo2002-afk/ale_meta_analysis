#!/usr/bin/env python
"""Run a rigorous, hand-curated ALE meta-analysis and compare it to the
automated (Neurosynth/NeuroQuery) result.

This is the classic, gold-standard workflow the original brief describes: you
read papers, extract peak tables and *real sample sizes* by hand into a
GingerALE/Sleuth file (see data/hand_curated/TEMPLATE_sleuth.txt), and this
script runs the analysis. Because a hand-curated file carries true per-study
sample sizes, it uses the proper **sample-size-weighted** ALE kernel (not the
fixed kernel the automated pipeline must fall back on), and is what a
neuroscience reviewer recognises as a rigorous meta-analysis.

The script then measures how well the automated large-scale map agrees with the
hand-curated one — demonstrating both skill sets and cross-validating the result.

Usage:
    PYTHONPATH=src python scripts/run_hand_curated.py data/hand_curated/YOURFILE_sleuth.txt
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from nimare.correct import FWECorrector
from nimare.io import convert_sleuth_to_dataset
from nimare.meta.cbma.ale import ALE

from ale_meta import anatomy
from ale_meta.ale import significant_z_image
from ale_meta.config import load_config


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("sleuth_file", help="hand-curated Sleuth/GingerALE .txt file")
    p.add_argument("--n-iters", type=int, default=5000,
                   help="permutations (>=5000 for publication; default 5000)")
    args = p.parse_args()

    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(message)s",
                        datefmt="%H:%M:%S")
    cfg = load_config()
    out_dir = cfg.root / "results" / "hand_curated"
    out_dir.mkdir(parents=True, exist_ok=True)

    sleuth = Path(args.sleuth_file)
    if not sleuth.exists():
        print(f"File not found: {sleuth}", file=sys.stderr)
        return 1

    logging.info("Importing hand-curated coordinates from %s", sleuth)
    dset = convert_sleuth_to_dataset(str(sleuth))
    n_exp = len(dset.ids)
    logging.info("%d experiments, %d foci imported", n_exp, len(dset.coordinates))
    if n_exp < 15:
        logging.warning("Only %d experiments — ALE is considered underpowered "
                        "below ~15-17 (Eickhoff et al., 2016).", n_exp)

    # Proper sample-size-weighted ALE (the whole point of hand curation).
    logging.info("Running sample-size-weighted ALE (%d permutations)...", args.n_iters)
    est = ALE(null_method="approximate", n_cores=int(cfg["ale"]["n_cores"]))
    res = est.fit(dset)
    corr = FWECorrector(method="montecarlo",
                        voxel_thresh=float(cfg["ale"]["cluster_forming_p"]),
                        n_iters=int(args.n_iters), n_cores=int(cfg["ale"]["n_cores"]))
    corrected = corr.transform(res)
    corrected.save_maps(output_dir=str(out_dir), prefix="handcurated")

    sig = significant_z_image(corrected, cfg)
    clusters = anatomy.clusters_from_image(sig)
    clusters.to_csv(out_dir / "handcurated_clusters.csv", index=False)
    logging.info("Hand-curated ALE: %d significant clusters", len(clusters))
    print("\n=== Hand-curated convergent clusters ===")
    print(clusters[["X", "Y", "Z", "Peak Stat", "Cluster Size (mm3)",
                    "Anatomical Label"]].to_string(index=False) if len(clusters)
          else "(none survived correction)")

    # Compare with the automated result, if present.
    auto_path = cfg.path("tables") / "ale_clusters_labelled.csv"
    if auto_path.exists() and len(clusters):
        auto = pd.read_csv(auto_path)
        pa = clusters[["X", "Y", "Z"]].values
        pb = auto[["X", "Y", "Z"]].values
        rec = sum(np.min(np.linalg.norm(pb - x, axis=1)) <= 15 for x in pa) / len(pa)
        logging.info("Concordance: %.0f%% of hand-curated clusters have an "
                     "automated-result peak within 15 mm.", 100 * rec)
        print(f"\nAgreement with the automated pipeline: {100*rec:.0f}% of "
              f"hand-curated clusters match within 15 mm.")

    print(f"\nOutputs in {out_dir}/ (maps + handcurated_clusters.csv).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
