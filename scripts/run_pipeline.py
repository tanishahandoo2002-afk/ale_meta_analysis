#!/usr/bin/env python
"""End-to-end ALE meta-analysis pipeline.

Runs every stage in order, driven entirely by ``config/config.yaml``:

    1. fetch coordinate databases (Neurosynth, NeuroQuery)
    2. curate construct-relevant experiments + PRISMA accounting
    3. ALE with cluster-level FWE correction  -> cluster table + brain figures
    4. robustness diagnostics (jackknife, focus counter, file-drawer)
    5. functional decoding of the convergent region
    6. meta-analytic coactivation modeling (MACM) from the top peak
    7. sub-construct subtraction & conjunction contrast
    8. assemble REPORT.md + SUMMARY.md

Usage:
    PYTHONPATH=src python scripts/run_pipeline.py [--config config/config.yaml]
                                                  [--skip-diagnostics]
                                                  [--skip-macm] [--skip-contrast]
                                                  [--fast]
``--fast`` drops permutation counts for a quick smoke test.
"""
from __future__ import annotations

import argparse
import logging
import sys

from ale_meta import (ale, contrast, curation, dashboard, datasets, decoding,
                      diagnostics, figures, prisma, report, viz)
from ale_meta.config import load_config


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--config", default=None)
    p.add_argument("--skip-diagnostics", action="store_true")
    p.add_argument("--skip-macm", action="store_true")
    p.add_argument("--skip-contrast", action="store_true")
    p.add_argument("--skip-advanced", action="store_true",
                   help="skip extended analyses (enc-vs-ret, DMN, landmarks)")
    p.add_argument("--fast", action="store_true",
                   help="reduce permutations for a quick smoke test")
    args = p.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    log = logging.getLogger("pipeline")

    cfg = load_config(args.config)
    if args.fast:
        cfg.raw["ale"]["n_iters"] = 100
        cfg.raw["contrast"]["n_iters"] = 100
        cfg.raw["macm"]["n_iters"] = 100
        cfg.raw["macm"]["max_studies"] = 80
        cfg.raw["curation"]["max_experiments"] = 60
        cfg.raw["diagnostics"]["fail_safe_n"] = False
        log.info("FAST mode: n_iters=100, max_experiments=60, MACM<=80 studies, "
                 "file-drawer off (smoke test only — not for interpretation)")

    # -- 1. data ------------------------------------------------------------
    log.info("STAGE 1/8 — fetching databases")
    dsets = datasets.fetch_all(cfg)
    # Keep the largest raw DB around for MACM / decoding (needs term features).
    full_db = max(dsets.values(), key=lambda d: len(d.ids))

    # -- 2. curation + PRISMA ----------------------------------------------
    log.info("STAGE 2/8 — curating experiments")
    merged, prisma_df = curation.curate_all(dsets, cfg)
    prisma_df.to_csv(cfg.path("tables") / "prisma_counts.csv", index=False)
    prisma.render_prisma(prisma_df, cfg)
    n_exp = len(merged.ids)

    # -- 3. ALE + FWE -------------------------------------------------------
    log.info("STAGE 3/8 — ALE with cluster-level FWE")
    corrected = ale.run_ale(merged, cfg)
    clusters = ale.cluster_table(corrected, cfg)
    sig_img = ale.significant_z_image(corrected, cfg)
    viz.glass_brain(sig_img, "Episodic retrieval — convergent activation (ALE, FWE)",
                    "ale_glass_brain.png", cfg)
    viz.stat_slices(sig_img, "Episodic retrieval — ALE (cluster-FWE)",
                    "ale_slices.png", cfg)
    viz.interactive_html(sig_img, "ALE — episodic retrieval",
                         "ale_interactive.html", cfg)

    # -- 4. diagnostics -----------------------------------------------------
    diag: dict = {}
    if not args.skip_diagnostics and len(clusters):
        log.info("STAGE 4/8 — robustness diagnostics")
        diag = diagnostics.run_all(corrected, merged, cfg)
        if "focus_counter" in diag:
            viz.barh(_focus_summary(diag["focus_counter"]),
                     "cluster", "n_experiments",
                     "Experiments contributing to each cluster",
                     "diag_focus_counter.png", cfg)
    else:
        log.info("STAGE 4/8 — diagnostics skipped")

    # -- 5. decoding --------------------------------------------------------
    dec = None
    if len(clusters):
        log.info("STAGE 5/8 — functional decoding")
        dec = decoding.decode_region(full_db, sig_img, cfg)
        if dec is not None:
            viz.barh(dec, "term", "r",
                     "Functional decoding — top associated terms",
                     "decoding_terms.png", cfg)
    else:
        log.info("STAGE 5/8 — decoding skipped (no clusters)")

    # -- 6. MACM ------------------------------------------------------------
    macm_info = None
    if not args.skip_macm and cfg["macm"]["enabled"] and len(clusters):
        log.info("STAGE 6/8 — meta-analytic coactivation modeling")
        seed = ale.peak_coordinate(corrected, cfg)
        if seed:
            from ale_meta import macm as macm_mod
            macm_corr, macm_dset = macm_mod.run_macm(full_db, seed, cfg)
            if macm_corr is not None:
                macm_sig = ale.significant_z_image(macm_corr, cfg)
                viz.glass_brain(macm_sig,
                                f"MACM — coactivation with seed {seed}",
                                "macm_glass_brain.png", cfg)
                macm_info = {"seed_xyz": seed, "n_studies": len(macm_dset.ids)}
    else:
        log.info("STAGE 6/8 — MACM skipped")

    # -- 7. contrast --------------------------------------------------------
    contrast_info = None
    if not args.skip_contrast and cfg["contrast"]["enabled"]:
        log.info("STAGE 7/8 — sub-construct subtraction & conjunction")
        contrast_info = contrast.run_contrast(merged, cfg)
    else:
        log.info("STAGE 7/8 — contrast skipped")

    # -- 7b. extended analyses (encoding-vs-retrieval, DMN overlap, landmarks) --
    if not args.skip_advanced:
        log.info("STAGE 7b — extended analyses (enc-vs-ret, DMN, landmarks)")
        from ale_meta import advanced
        try:
            advanced.dmn_overlap(cfg)
            advanced.landmark_recovery(cfg)
            # encoding-vs-retrieval runs 3 Monte-Carlo ALEs internally, so cap
            # its permutations (a directional contrast doesn't need the main
            # map's null resolution) to keep total runtime in budget.
            advanced.encoding_vs_retrieval(
                cfg, dsets, n_iters=min(int(cfg["ale"]["n_iters"]), 500))
        except Exception as exc:  # never let extras sink the main run
            log.warning("Extended analyses failed: %s", exc)
    else:
        log.info("STAGE 7b — extended analyses skipped")

    # -- 8. report ----------------------------------------------------------
    log.info("STAGE 8/8 — assembling report")
    report.build_report(
        cfg, prisma=prisma_df, clusters=clusters, decoding=dec,
        diagnostics=diag, macm_info=macm_info, contrast_info=contrast_info,
        n_experiments=n_exp,
    )

    # -- 9. rich figures + dashboard ---------------------------------------
    log.info("Rendering rich figures (surface, montages, contrast, diagnostics)")
    figures.regenerate_from_disk(cfg)
    log.info("Assembling results dashboard")
    dashboard.build_dashboard(cfg)

    log.info("DONE. See results/dashboard.html, results/REPORT.md, "
             "results/SUMMARY.md, results/figures/")
    return 0


def _focus_summary(focus_df):
    """Collapse the per-experiment focus-count table to per-cluster totals.

    The NiMARE table has an 'id' string column plus one numeric column per
    cluster ('PositiveTail N' / 'NegativeTail N'); operate on the cluster
    columns only."""
    import pandas as pd
    if focus_df is None or len(focus_df) == 0:
        return pd.DataFrame(columns=["cluster", "n_experiments"])
    cluster_cols = [c for c in focus_df.columns if "Tail" in str(c)]
    counts = (focus_df[cluster_cols] > 0).sum(axis=0)
    return pd.DataFrame({"cluster": counts.index.astype(str),
                         "n_experiments": counts.values})


if __name__ == "__main__":
    sys.exit(main())
