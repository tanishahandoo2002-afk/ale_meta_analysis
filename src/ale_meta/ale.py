"""Run Activation Likelihood Estimation with cluster-level FWE correction.

ALE treats every reported peak not as a point but as a 3-D Gaussian probability
distribution whose width scales (inversely) with the study's sample size — a
larger study localises activation more precisely, so it gets a tighter kernel
and more weight. For each voxel, ALE asks: across all studies, how likely is it
that *at least one* study truly activated here? Voxels where many independent
studies' kernels overlap yield high ALE scores, marking spatial convergence.

Significance is assessed against an empirical null built by permutation, then
corrected for multiple comparisons at the **cluster level** using family-wise
error (Monte Carlo). Cluster-level FWE is the current field standard because
voxel-level correction is overly conservative and uncorrected maps massively
inflate false positives (Eickhoff et al., 2016).
"""
from __future__ import annotations

import logging
import math
from typing import Optional

import numpy as np
import pandas as pd
from nilearn.reporting import get_clusters_table
from nimare.correct import FWECorrector
from nimare.dataset import Dataset
from nimare.meta.cbma.ale import ALE
from nimare.meta.kernel import ALEKernel

from .config import Config

logger = logging.getLogger(__name__)

# NiMARE's canonical name for the cluster-level FWE corrected maps.
_Z_MAP = "z_desc-size_level-cluster_corr-FWE_method-montecarlo"
_LOGP_MAP = "logp_desc-size_level-cluster_corr-FWE_method-montecarlo"


def make_estimator(cfg: Config) -> ALE:
    """Build an ALE estimator with a fixed-size kernel.

    Automated databases (Neurosynth, NeuroQuery) do not report per-study sample
    sizes, so we cannot size each Gaussian kernel by n as ALE normally does.
    Instead we fix the kernel to a nominal sample size (config
    ``ale.fixed_sample_size``) — a standard, documented accommodation. This is
    used by *every* ALE in the pipeline (main, jackknife, MACM, contrast) so the
    kernel is consistent throughout.
    """
    n = int(cfg["ale"].get("fixed_sample_size", 20))
    kernel = ALEKernel(sample_size=n)
    return ALE(kernel_transformer=kernel, null_method="approximate",
               n_cores=int(cfg["ale"]["n_cores"]))


def make_corrector(cfg: Config, n_iters: int | None = None) -> FWECorrector:
    """Build the cluster-level FWE Monte-Carlo corrector from config."""
    a = cfg["ale"]
    return FWECorrector(
        method="montecarlo",
        voxel_thresh=float(a["cluster_forming_p"]),
        n_iters=int(n_iters if n_iters is not None else a["n_iters"]),
        n_cores=int(a["n_cores"]),
    )


def run_ale(dset: Dataset, cfg: Config):
    """Fit ALE and apply cluster-level FWE correction.

    Returns the corrected NiMARE MetaResult.
    """
    a = cfg["ale"]
    cfg.apply_seed()

    logger.info("Fitting ALE on %d experiments (%d permutations)...",
                len(dset.ids), a["n_iters"])
    estimator = make_estimator(cfg)
    results = estimator.fit(dset)

    logger.info("Applying cluster-level FWE (cluster-forming p<%s, %d iters)...",
                a["cluster_forming_p"], a["n_iters"])
    corrector = make_corrector(cfg)
    corrected = corrector.transform(results)

    # Persist the key statistical maps for visualisation / reuse.
    maps_dir = cfg.path("maps")
    corrected.save_maps(output_dir=str(maps_dir), prefix="ale")
    logger.info("Saved ALE maps to %s", maps_dir)
    return corrected


def significant_z_image(corrected, cfg: Config):
    """Return a Nifti image of z-scores restricted to clusters that survive
    the cluster-level FWE threshold (config ale.fwe_cluster_p)."""
    import nibabel as nib

    # Mask the *raw* (uncorrected) ALE z map by which voxels fall in
    # cluster-FWE-significant clusters. Using the raw z (not the cluster-level
    # corrected z, which is uniform within a cluster) means the map and the
    # cluster table carry informative, graded peak intensities — e.g. the
    # hippocampus emerges as the strongest peak rather than every cluster
    # sharing one value.
    z_img = corrected.get_map("z")          # uncorrected ALE z
    logp_img = corrected.get_map(_LOGP_MAP)  # cluster-level FWE significance

    fwe_p = float(cfg["ale"]["fwe_cluster_p"])
    logp_thresh = -math.log10(fwe_p)

    z_data = z_img.get_fdata()
    logp_data = logp_img.get_fdata()
    mask = logp_data >= logp_thresh
    thresh_data = np.where(mask, z_data, 0.0)
    return nib.Nifti1Image(thresh_data, z_img.affine, z_img.header)


def cluster_table(corrected, cfg: Config) -> pd.DataFrame:
    """Build a table of significant convergent clusters (peak coords, size, z).

    This is the headline Results table of the meta-analysis.
    """
    thresh_img = significant_z_image(corrected, cfg)
    table = get_clusters_table(thresh_img, stat_threshold=0.0)

    if table is None or len(table) == 0:
        logger.warning("No clusters survived cluster-level FWE correction.")
        return pd.DataFrame(
            columns=["Cluster ID", "X", "Y", "Z", "Peak Stat", "Cluster Size (mm3)"]
        )

    out_path = cfg.path("tables") / "ale_significant_clusters.csv"
    table.to_csv(out_path, index=False)
    logger.info("Wrote %d clusters to %s", len(table), out_path)
    return table


def peak_coordinate(corrected, cfg: Config) -> Optional[tuple]:
    """Return the (x, y, z) MNI coordinate of the strongest surviving cluster,
    used downstream as the MACM seed. None if nothing survives."""
    table = cluster_table(corrected, cfg)
    if len(table) == 0:
        return None
    top = table.sort_values("Peak Stat", ascending=False).iloc[0]
    return (float(top["X"]), float(top["Y"]), float(top["Z"]))
