"""Meta-Analytic Coactivation Modeling (MACM).

Once ALE tells us *where* the literature converges, MACM asks: what does that
region tend to co-activate with, across the *entire* database, independent of
any single task? The logic: take a seed region (here, the peak of the strongest
episodic-retrieval cluster), select every study in the full database that
reports a focus inside that seed, and run an ALE on that subset. Regions that
converge in this seed-based subset form the seed's task-independent
"co-activation network" — a meta-analytic estimate of functional connectivity
built purely from published coordinates.

For an episodic-retrieval hub such as the hippocampus or posterior
parietal/retrosplenial cortex, MACM should recover the wider core recollection
network (medial prefrontal cortex, posterior cingulate/precuneus, lateral
parietal, medial temporal lobe) — a strong, interpretable validation.
"""
from __future__ import annotations

import logging
from typing import Tuple

import numpy as np
from nimare.dataset import Dataset

from .config import Config

logger = logging.getLogger(__name__)


def run_macm(full_db: Dataset, seed_xyz: Tuple[float, float, float], cfg: Config):
    """Run a seed-based MACM against the full coordinate database.

    Parameters
    ----------
    full_db : the complete (uncurated) database Dataset — MACM deliberately
        draws coactivation from the whole literature, not just retrieval studies.
    seed_xyz : (x, y, z) MNI coordinate of the seed, e.g. the top ALE peak.
    """
    m = cfg["macm"]
    radius = float(m["sphere_radius_mm"])
    logger.info("Selecting studies with foci within %.0f mm of seed %s...",
                radius, seed_xyz)

    seed_ids = full_db.get_studies_by_coordinate([seed_xyz], r=radius)
    if not seed_ids:
        logger.warning("No studies found near seed; MACM skipped.")
        return None, None

    # Cap the coactivating set for tractability (a seed in a well-studied region
    # can pull in many hundreds of studies, making FWE prohibitively slow).
    max_studies = m.get("max_studies")
    n_found = len(seed_ids)
    if max_studies and n_found > int(max_studies):
        rng = np.random.default_rng(cfg.seed)
        seed_ids = sorted(rng.choice(sorted(seed_ids), size=int(max_studies),
                                     replace=False).tolist())
        logger.info("MACM: %d studies coactivate; using a random sample of %d",
                    n_found, len(seed_ids))
    else:
        logger.info("MACM subset: %d studies coactivating with the seed", n_found)

    macm_dset = full_db.slice(seed_ids)

    from .ale import make_corrector, make_estimator
    res = make_estimator(cfg).fit(macm_dset)
    corrected = make_corrector(cfg, n_iters=int(m.get("n_iters",
                                cfg["ale"]["n_iters"]))).transform(res)

    maps_dir = cfg.path("maps")
    corrected.save_maps(output_dir=str(maps_dir), prefix="macm")
    logger.info("Saved MACM maps to %s", maps_dir)
    return corrected, macm_dset
