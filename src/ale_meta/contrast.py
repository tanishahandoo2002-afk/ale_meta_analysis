"""Subtraction and conjunction between two sub-constructs of retrieval.

Episodic retrieval is not monolithic. Dual-process theory distinguishes
*recollection* (recall of contextual detail, hippocampal/parietal) from
*familiarity* (a context-free sense of oldness). We operationalise a coarse
version of this split — recognition/familiarity vs. recall/autobiographical —
and ask two complementary questions:

* **Subtraction (A > B and B > A):** where does convergence differ between the
  two sub-constructs? NiMARE's ALESubtraction builds a null by randomly
  reassigning experiments to the two groups, so differences reflect genuine
  between-group divergence rather than differing study counts.
* **Conjunction (A AND B):** where do *both* sub-constructs converge — the
  shared retrieval core — computed as the voxelwise minimum of the two
  thresholded ALE maps (the standard minimum-statistic conjunction).

This turns a single meta-analysis into a test of a real theoretical model.
"""
from __future__ import annotations

import logging
from typing import Optional

import nibabel as nib
import numpy as np
from nimare.dataset import Dataset
from nimare.meta.cbma.ale import ALESubtraction
from nimare.meta.kernel import ALEKernel

from . import anatomy
from .config import Config
from .ale import make_corrector, make_estimator
from .curation import _labels_for_terms, _studies_matching

logger = logging.getLogger(__name__)

_Z_MAP = "z_desc-size_level-cluster_corr-FWE_method-montecarlo"
_LOGP_MAP = "logp_desc-size_level-cluster_corr-FWE_method-montecarlo"


def _subset_by_terms(retrieval_dset: Dataset, terms, thresh: float) -> Optional[Dataset]:
    labels = _labels_for_terms(retrieval_dset, terms)
    ids = sorted(_studies_matching(retrieval_dset, labels, thresh))
    if not ids:
        return None
    return retrieval_dset.slice(ids)


def _corrected_ale(dset: Dataset, cfg: Config):
    res = make_estimator(cfg).fit(dset)
    return make_corrector(cfg).transform(res)


def _sig_mask(corrected, cfg: Config) -> np.ndarray:
    import math
    logp = corrected.get_map(_LOGP_MAP).get_fdata()
    return logp >= -math.log10(float(cfg["ale"]["fwe_cluster_p"]))


def run_contrast(retrieval_dset: Dataset, cfg: Config):
    """Run subtraction + conjunction between the two configured sub-constructs.

    Returns a dict of saved map paths and the two group sizes.
    """
    c = cfg["contrast"]
    if not c.get("enabled"):
        return None

    thresh = float(cfg["curation"]["term_frequency_threshold"])
    a_name, b_name = c["group_a"]["name"], c["group_b"]["name"]
    dset_a = _subset_by_terms(retrieval_dset, c["group_a"]["terms"], thresh)
    dset_b = _subset_by_terms(retrieval_dset, c["group_b"]["terms"], thresh)

    if dset_a is None or dset_b is None:
        logger.warning("One sub-construct has no experiments; contrast skipped.")
        return None

    # Keep the two groups disjoint so the subtraction is well-defined.
    shared = set(dset_a.ids) & set(dset_b.ids)
    if shared:
        a_only = [i for i in dset_a.ids if i not in shared]
        b_only = [i for i in dset_b.ids if i not in shared]
        dset_a = dset_a.slice(a_only) if a_only else None
        dset_b = dset_b.slice(b_only) if b_only else None
        if dset_a is None or dset_b is None:
            logger.warning("Groups fully overlap; contrast skipped.")
            return None

    logger.info("Contrast groups: %s=%d exps, %s=%d exps",
                a_name, len(dset_a.ids), b_name, len(dset_b.ids))

    maps_dir = cfg.path("maps")

    # --- Subtraction (A vs B) ------------------------------------------------
    logger.info("Running ALE subtraction (%s vs %s)...", a_name, b_name)
    n = int(cfg["ale"].get("fixed_sample_size", 20))
    sub = ALESubtraction(kernel_transformer=ALEKernel(sample_size=n),
                         n_iters=int(c["n_iters"]),
                         n_cores=int(cfg["ale"]["n_cores"]))
    sub_res = sub.fit(dset_a, dset_b)
    sub_res.save_maps(output_dir=str(maps_dir), prefix=f"subtraction_{a_name}_vs_{b_name}")

    # --- Conjunction (A AND B), minimum-statistic ---------------------------
    logger.info("Computing conjunction (%s AND %s)...", a_name, b_name)
    corr_a = _corrected_ale(dset_a, cfg)
    corr_b = _corrected_ale(dset_b, cfg)
    z_a = corr_a.get_map(_Z_MAP)
    z_b = corr_b.get_map(_Z_MAP)
    mask_a = _sig_mask(corr_a, cfg)
    mask_b = _sig_mask(corr_b, cfg)

    za, zb = z_a.get_fdata(), z_b.get_fdata()
    both = mask_a & mask_b
    conj = np.where(both, np.minimum(za, zb), 0.0)
    conj_img = nib.Nifti1Image(conj, z_a.affine, z_a.header)
    conj_path = maps_dir / f"conjunction_{a_name}_AND_{b_name}.nii.gz"
    conj_img.to_filename(conj_path)
    logger.info("Saved conjunction map (%d voxels) to %s",
                int((conj != 0).sum()), conj_path)

    try:
        rel_conj = conj_path.relative_to(cfg.root)
    except ValueError:
        rel_conj = conj_path
    info = {
        "group_a": a_name, "n_a": len(dset_a.ids),
        "group_b": b_name, "n_b": len(dset_b.ids),
        "subtraction_prefix": f"subtraction_{a_name}_vs_{b_name}",
        "conjunction_map": str(rel_conj),
        "conjunction_voxels": int((conj != 0).sum()),
    }
    info.update(interpret_contrast(cfg, a_name, b_name))
    return info


def interpret_contrast(cfg: Config, a_name: str, b_name: str,
                       subtraction_z: float = 2.0) -> dict:
    """Extract and anatomically label clusters from the (saved) contrast maps.

    Turns the raw subtraction/conjunction NIfTIs into interpretable, labelled
    cluster tables: where recognition > recall, where recall > recognition, and
    the shared retrieval core. Reads maps from disk so it can also be run
    standalone to (re)interpret an existing analysis.
    """
    maps_dir = cfg.path("maps")
    tables_dir = cfg.path("tables")
    out: dict = {}

    # --- Subtraction: split into A>B (positive z) and B>A (negative z) -------
    sub_path = maps_dir / f"subtraction_{a_name}_vs_{b_name}_z_desc-group1MinusGroup2.nii.gz"
    if sub_path.exists():
        img = nib.load(sub_path)
        data = img.get_fdata()
        pos = nib.Nifti1Image(np.where(data >= subtraction_z, data, 0.0),
                              img.affine, img.header)
        neg = nib.Nifti1Image(np.where(data <= -subtraction_z, -data, 0.0),
                              img.affine, img.header)
        # Difference maps are voxelwise-thresholded (not cluster-FWE), so keep a
        # firm size floor and only the largest clusters for interpretability.
        tab_pos = anatomy.clusters_from_image(pos, min_size_mm3=200, top_n=10)
        tab_neg = anatomy.clusters_from_image(neg, min_size_mm3=200, top_n=10)
        if len(tab_pos):
            tab_pos.to_csv(tables_dir / f"contrast_{a_name}_gt_{b_name}.csv", index=False)
        if len(tab_neg):
            tab_neg.to_csv(tables_dir / f"contrast_{b_name}_gt_{a_name}.csv", index=False)
        out["subtraction_a_gt_b"] = tab_pos
        out["subtraction_b_gt_a"] = tab_neg
        logger.info("Contrast: %d %s>%s clusters, %d %s>%s clusters",
                    len(tab_pos), a_name, b_name, len(tab_neg), b_name, a_name)

    # --- Conjunction: shared retrieval core ---------------------------------
    conj_path = maps_dir / f"conjunction_{a_name}_AND_{b_name}.nii.gz"
    if conj_path.exists():
        conj_tab = anatomy.clusters_from_image(nib.load(conj_path))
        if len(conj_tab):
            conj_tab.to_csv(tables_dir / f"conjunction_{a_name}_AND_{b_name}.csv", index=False)
        out["conjunction_clusters"] = conj_tab
        logger.info("Contrast: %d shared-core (conjunction) clusters", len(conj_tab))

    return out
