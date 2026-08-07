"""Shared anatomical labelling and cluster extraction.

One place that turns a thresholded statistical image into a labelled cluster
table, so the main ALE result, the MACM result, and the recognition/recall
contrast maps are all described with the same Harvard-Oxford atlas labels and
the same extraction settings. Centralising this is what lets us reconcile
cluster numbering across the report (Point 1).
"""
from __future__ import annotations

import logging
from functools import lru_cache
from typing import Optional, Tuple

import numpy as np
import pandas as pd
from nilearn.reporting import get_clusters_table

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _atlases():
    from nilearn import datasets, image
    cort = datasets.fetch_atlas_harvard_oxford("cort-maxprob-thr25-2mm")
    sub = datasets.fetch_atlas_harvard_oxford("sub-maxprob-thr25-2mm")
    # Pre-load the label volumes once.
    cort_img = cort.maps if not isinstance(cort.maps, str) else image.load_img(cort.maps)
    sub_img = sub.maps if not isinstance(sub.maps, str) else image.load_img(sub.maps)
    return (cort_img, cort.labels), (sub_img, sub.labels)


def _lookup(img, labels, xyz) -> Optional[str]:
    inv = np.linalg.inv(img.affine)
    ijk = inv.dot(np.array([*xyz, 1]))[:3].round().astype(int)
    data = img.get_fdata()
    if np.any(ijk < 0) or np.any(ijk >= np.array(data.shape)):
        return None
    idx = int(data[ijk[0], ijk[1], ijk[2]])
    if 0 < idx < len(labels):
        name = labels[idx]
        if name and name.lower() != "background":
            return name
    return None


def label_peak(xyz: Tuple[float, float, float]) -> str:
    """Anatomical label for an MNI coordinate: a named cortical region if any,
    else a subcortical structure. If the exact voxel is unlabelled (e.g. a peak
    sitting on a gyral boundary or in white matter), search a small neighbourhood
    (up to ~8 mm) for the nearest labelled grey-matter region rather than
    returning 'white matter'."""
    try:
        cort, sub = _atlases()
    except Exception as exc:  # atlas download unavailable
        logger.warning("Atlas unavailable for labelling: %s", exc)
        return "n/a"

    # 1) exact-voxel lookup (cortex preferred, then subcortex)
    for img, labels in (cort, sub):
        name = _lookup(img, labels, xyz)
        if name:
            return name

    # 2) neighbourhood fallback: nearest labelled grey matter within ~8 mm
    best = None
    best_d = 1e9
    for dx in range(-8, 9, 2):
        for dy in range(-8, 9, 2):
            for dz in range(-8, 9, 2):
                d = (dx * dx + dy * dy + dz * dz) ** 0.5
                if d == 0 or d > 8 or d >= best_d:
                    continue
                p = (xyz[0] + dx, xyz[1] + dy, xyz[2] + dz)
                for img, labels in (cort, sub):
                    name = _lookup(img, labels, p)
                    if name:
                        best, best_d = f"{name} (near peak)", d
                        break
    return best or "Unlabelled / white matter"


def clusters_from_image(stat_img, min_distance: float = 8.0,
                        min_size_mm3: float = 100.0,
                        top_n: Optional[int] = None) -> pd.DataFrame:
    """Extract significant clusters from a thresholded stat image and label each
    peak. Returns a tidy table (Cluster ID, X, Y, Z, Peak Stat, size, label).

    Only *main* clusters are kept (nilearn also emits sub-peaks with a blank
    size); clusters below ``min_size_mm3`` are dropped to suppress the many tiny
    white-matter specks that an uncorrected difference map produces. Pass
    ``top_n`` to keep only the largest N."""
    empty = pd.DataFrame(columns=["Cluster ID", "X", "Y", "Z", "Peak Stat",
                                  "Cluster Size (mm3)", "Anatomical Label"])
    table = get_clusters_table(stat_img, stat_threshold=0.0,
                               min_distance=min_distance)
    if table is None or len(table) == 0:
        return empty

    table = table.copy()
    # Keep only main-cluster rows (sub-peaks have a blank/NaN size).
    size = pd.to_numeric(table["Cluster Size (mm3)"], errors="coerce")
    table = table[size.notna() & (size >= float(min_size_mm3))].copy()
    if len(table) == 0:
        return empty
    table = table.sort_values("Cluster Size (mm3)", ascending=False)
    if top_n:
        table = table.head(int(top_n))
    table["Anatomical Label"] = [
        label_peak((r["X"], r["Y"], r["Z"])) for _, r in table.iterrows()
    ]
    return table.reset_index(drop=True)
