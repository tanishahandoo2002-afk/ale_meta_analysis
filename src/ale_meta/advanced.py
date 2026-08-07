"""Higher-order analyses that raise the study to research level.

1. **Encoding vs. retrieval** — the classic memory dissociation (cf. the
   subsequent-memory effect / HERA model). We build separate ALE maps for
   episodic *encoding* and *retrieval* studies and contrast them, testing where
   the two phases diverge and the core they share.
2. **Default-mode-network overlap** — a quantitative test of the long-standing
   claim that episodic retrieval recruits the default-mode network (DMN). We
   measure the spatial overlap (Dice, and fraction of the retrieval map inside
   the DMN) against the canonical Yeo-2011 7-network DMN.
3. **Landmark-region recovery** — does the automated result recover each node of
   the canonical *core recollection network* (Rugg & Vilberg, 2013)? For each
   representative node we report the nearest significant ALE peak and its
   distance, i.e. an independent check against the hypothesis-driven literature.

All outputs are written under results/ (tables + figures) and surfaced on the
dashboard. Analyses 2 and 3 read the already-computed ALE map (no recompute);
analysis 1 runs two additional ALEs.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import nibabel as nib
import numpy as np
import pandas as pd
from nilearn import datasets, image
from nimare.meta.cbma.ale import ALESubtraction
from nimare.meta.kernel import ALEKernel

from . import anatomy, figures
from .ale import make_corrector, make_estimator, significant_z_image
from .config import Config
from .curation import (_labels_for_terms, _studies_matching)

logger = logging.getLogger(__name__)


# ==========================================================================
# 2. Default-mode-network overlap  (cheap: uses the saved ALE map)
# ==========================================================================
def dmn_overlap(cfg: Config) -> Optional[dict]:
    sig = figures.sig_image_from_disk("ale", cfg)
    if sig is None:
        logger.warning("No ALE map on disk; skipping DMN overlap.")
        return None

    yeo = datasets.fetch_atlas_yeo_2011()
    dmn_src = image.index_img(yeo["maps"], 0) if len(
        image.load_img(yeo["maps"]).shape) == 4 else image.load_img(yeo["maps"])
    # DMN = network 7 in the Yeo-2011 7-network parcellation.
    dmn_bin = image.math_img("(img == 7).astype('int8')", img=dmn_src)
    dmn_r = image.resample_to_img(dmn_bin, sig, interpolation="nearest",
                                  force_resample=True, copy_header=True)

    ale_bin = (np.abs(sig.get_fdata()) > 0)
    dmn_arr = dmn_r.get_fdata() > 0
    inter = int(np.logical_and(ale_bin, dmn_arr).sum())
    dice = round(2 * inter / (ale_bin.sum() + dmn_arr.sum()), 3) if (
        ale_bin.sum() + dmn_arr.sum()) else 0.0
    frac_in = round(inter / ale_bin.sum(), 3) if ale_bin.sum() else 0.0

    # overlay figure: ALE map with DMN outline
    from nilearn import plotting
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig = plt.figure(figsize=(12, 4))
    disp = plotting.plot_stat_map(sig, display_mode="z", cut_coords=6,
                                  title="Retrieval convergence (hot) within the "
                                        "default-mode network (green outline)",
                                  cmap="inferno", colorbar=True, figure=fig,
                                  draw_cross=False)
    try:
        disp.add_contours(dmn_r, levels=[0.5], colors="limegreen", linewidths=1.2)
    except Exception as exc:
        logger.warning("DMN contour overlay failed: %s", exc)
    out_fig = cfg.path("figures") / "dmn_overlap.png"
    fig.savefig(out_fig, dpi=200, bbox_inches="tight")
    plt.close(fig)

    result = {"dice": dice, "fraction_retrieval_in_dmn": frac_in,
              "ale_voxels": int(ale_bin.sum()), "dmn_voxels": int(dmn_arr.sum())}
    (cfg.path("tables") / "dmn_overlap.json").write_text(json.dumps(result, indent=2))
    logger.info("DMN overlap: Dice=%.3f, %.0f%% of retrieval map lies in the DMN",
                dice, 100 * frac_in)
    return result


# ==========================================================================
# 3. Landmark-region recovery  (cheap: uses the saved ALE map)
# ==========================================================================
# Representative MNI coordinates for the canonical core recollection network
# (Rugg & Vilberg, 2013). These are canonical node locations from the review
# literature, used to test whether the automated map recovers each node.
_LANDMARKS: List[Tuple[str, Tuple[int, int, int]]] = [
    ("Left hippocampus", (-24, -22, -16)),
    ("Right hippocampus", (24, -20, -16)),
    ("Precuneus / posterior cingulate", (-6, -58, 28)),
    ("Retrosplenial cortex", (-4, -52, 18)),
    ("Left angular gyrus (lateral parietal)", (-44, -72, 36)),
    ("Medial prefrontal cortex", (-4, 52, 2)),
    ("Left dorsolateral PFC (retrieval control)", (-44, 24, 28)),
]


def landmark_recovery(cfg: Config, radius: float = 15.0) -> Optional[pd.DataFrame]:
    sig = figures.sig_image_from_disk("ale", cfg)
    if sig is None:
        return None
    data = sig.get_fdata()
    aff = sig.affine
    ijk = np.array(np.where(np.abs(data) > 0))
    if ijk.size == 0:
        return None
    xyz = nib.affines.apply_affine(aff, ijk.T)          # significant voxel coords
    vals = data[np.abs(data) > 0]

    rows = []
    for name, coord in _LANDMARKS:
        d = np.linalg.norm(xyz - np.array(coord), axis=1)
        j = int(np.argmin(d))
        rows.append({
            "Recollection-network node": name,
            "x": coord[0], "y": coord[1], "z": coord[2],
            "Nearest ALE peak (mm)": round(float(d[j]), 1),
            "ALE z there": round(float(vals[j]), 2),
            "Recovered": "yes" if d[j] <= radius else "no",
        })
    df = pd.DataFrame(rows)
    df.to_csv(cfg.path("tables") / "landmark_recovery.csv", index=False)
    n_ok = (df["Recovered"] == "yes").sum()
    logger.info("Landmark recovery: %d/%d canonical nodes recovered within %.0f mm",
                n_ok, len(df), radius)
    return df


# ==========================================================================
# 1. Encoding vs. retrieval contrast  (runs two ALEs)
# ==========================================================================
def _select(dsets: Dict, cfg: Config, terms: List[str]):
    """Select construct-matching, exclusion-free studies across all databases
    and merge (de-duplicated) into one Dataset."""
    thresh = float(cfg["curation"]["term_frequency_threshold"])
    excl_terms = cfg["curation"]["exclusion_terms"]
    parts, seen = [], set()
    for dset in dsets.values():
        incl = _labels_for_terms(dset, terms)
        excl = _labels_for_terms(dset, excl_terms)
        ids = _studies_matching(dset, incl, thresh) - _studies_matching(dset, excl, thresh)
        ids = sorted(i for i in ids if i not in seen)
        if not ids:
            continue
        parts.append(dset.slice(ids))
        seen.update(ids)
    if not parts:
        return None
    merged = parts[0]
    for p in parts[1:]:
        merged = merged.merge(p)
    return merged


def encoding_vs_retrieval(cfg: Config, dsets: Dict, n_iters: int = 500) -> Optional[dict]:
    enc_terms = ["encoding", "subsequent memory", "incidental", "encoding retrieval"]
    ret_terms = cfg["curation"]["inclusion_terms"]

    enc = _select(dsets, cfg, enc_terms)
    ret = _select(dsets, cfg, ret_terms)
    if enc is None or ret is None:
        logger.warning("Encoding/retrieval selection empty; skipping.")
        return None

    # keep the groups disjoint so the subtraction is well-defined
    shared = set(enc.ids) & set(ret.ids)
    enc_ids = [i for i in enc.ids if i not in shared]
    ret_ids = [i for i in ret.ids if i not in shared]
    # cap for tractability, most-relevant kept implicitly by slicing
    cap = 150
    enc = enc.slice(enc_ids[:cap]); ret = ret.slice(ret_ids[:cap])
    logger.info("Encoding vs retrieval: %d encoding, %d retrieval experiments",
                len(enc.ids), len(ret.ids))

    maps = cfg.path("maps")
    n = int(cfg["ale"].get("fixed_sample_size", 20))
    sub = ALESubtraction(kernel_transformer=ALEKernel(sample_size=n),
                         n_iters=n_iters, n_cores=int(cfg["ale"]["n_cores"]))
    sub_res = sub.fit(enc, ret)
    sub_res.save_maps(output_dir=str(maps), prefix="encVSret")

    # single-group ALEs for the conjunction (shared memory core)
    def _sig(dset):
        res = make_estimator(cfg).fit(dset)
        corr = make_corrector(cfg, n_iters=n_iters).transform(res)
        return significant_z_image(corr, cfg)
    enc_sig, ret_sig = _sig(enc), _sig(ret)
    ea, ra = enc_sig.get_fdata(), ret_sig.get_fdata()
    both = (np.abs(ea) > 0) & (np.abs(ra) > 0)
    conj = np.where(both, np.minimum(ea, ra), 0.0)
    conj_img = nib.Nifti1Image(conj, enc_sig.affine, enc_sig.header)
    conj_img.to_filename(maps / "encVSret_conjunction.nii.gz")

    # labelled cluster tables from the subtraction difference map
    sub_path = maps / "encVSret_z_desc-group1MinusGroup2.nii.gz"
    tables = cfg.path("tables")
    out = {"n_encoding": len(enc.ids), "n_retrieval": len(ret.ids)}
    if sub_path.exists():
        d = nib.load(sub_path)
        data = d.get_fdata()
        pos = nib.Nifti1Image(np.where(data >= 2.0, data, 0.0), d.affine, d.header)
        neg = nib.Nifti1Image(np.where(data <= -2.0, -data, 0.0), d.affine, d.header)
        tp = anatomy.clusters_from_image(pos, min_size_mm3=200, top_n=10)
        tn = anatomy.clusters_from_image(neg, min_size_mm3=200, top_n=10)
        tp.to_csv(tables / "encVSret_encoding_gt_retrieval.csv", index=False)
        tn.to_csv(tables / "encVSret_retrieval_gt_encoding.csv", index=False)
        out["n_enc_gt_ret"] = len(tp)
        out["n_ret_gt_enc"] = len(tn)
    conj_tab = anatomy.clusters_from_image(conj_img)
    conj_tab.to_csv(tables / "encVSret_conjunction.csv", index=False)
    out["n_shared"] = len(conj_tab)

    # glass-brain of the difference
    figures.glass(nib.load(sub_path) if sub_path.exists() else conj_img,
                  "Encoding (warm) vs. retrieval (cool)",
                  "encVSret_glass.png", cfg, plot_abs=False)
    (tables / "encVSret_summary.json").write_text(json.dumps(out, indent=2))
    logger.info("Encoding vs retrieval done: %s", out)
    return out
