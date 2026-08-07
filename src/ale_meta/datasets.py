"""Fetch coordinate databases from multiple public sources.

We draw on two large, independently constructed public databases:

* **Neurosynth** (~14k studies) — coordinates + a TF-IDF term x study feature
  matrix produced by automated text mining. The feature matrix is what lets us
  select studies by cognitive term.
* **NeuroQuery** (~13k studies) — an independently built database with a
  different extraction pipeline; used to cross-check convergence and reduce
  dependence on any single database's idiosyncrasies.

Both are fetched through NiMARE and cached on disk, so the download happens once
and every subsequent run is fast and fully offline.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict

from nimare.dataset import Dataset
from nimare.extract import fetch_neuroquery, fetch_neurosynth
from nimare.io import convert_neurosynth_to_dataset

from .config import Config

logger = logging.getLogger(__name__)

# Cached NiMARE Dataset filenames (pickled) so we skip re-conversion.
_CACHE_NAMES = {
    "neurosynth": "neurosynth_dataset.pkl.gz",
    "neuroquery": "neuroquery_dataset.pkl.gz",
}


def _fetch_neuroquery_lowmem(data_dir: Path) -> Dataset:
    """Convert NeuroQuery using only its compact ~6.3k-term TF-IDF vocabulary.

    NeuroQuery ships several feature matrices, including a 156,521-term count
    matrix that is enormous and blows up memory during conversion. We fetch the
    raw files and convert with *only* the ``neuroquery6308_combined_tfidf``
    feature group — the interpretable, low-memory term space — which is all we
    need for term-based curation and decoding.
    """
    files = fetch_neuroquery(data_dir=str(data_dir), return_type="files")[0]
    # Pick the single lightweight TF-IDF feature group.
    tfidf = next(
        f for f in files["features"]
        if "tfidf" in Path(f["features"]).name and "6308" in Path(f["features"]).name
    )
    logger.info("Converting NeuroQuery with TF-IDF vocab only: %s",
                Path(tfidf["vocabulary"]).name)
    return convert_neurosynth_to_dataset(
        coordinates_file=files["coordinates"],
        metadata_file=files["metadata"],
        annotations_files=[tfidf],
    )


def _fetch_one(source: str, data_dir: Path) -> Dataset:
    """Fetch a single database as a NiMARE Dataset, caching the result."""
    cache_path = data_dir / _CACHE_NAMES[source]
    if cache_path.exists():
        logger.info("Loading cached %s dataset from %s", source, cache_path)
        try:
            return Dataset.load(cache_path)
        except (EOFError, OSError) as exc:
            # A run interrupted mid-save can leave a truncated gzip; rebuild it.
            logger.warning("Cached %s dataset is corrupt (%s); re-fetching.",
                           source, exc)
            cache_path.unlink(missing_ok=True)

    logger.info("Downloading %s database (this can take several minutes)...", source)
    if source == "neurosynth":
        # Neurosynth's default dataset bundles a compact TF-IDF term matrix that
        # curation relies on. NiMARE returns a 1-element list of Datasets.
        dset = fetch_neurosynth(data_dir=str(data_dir), return_type="dataset")
        if isinstance(dset, (list, tuple)):
            dset = dset[0]
    else:
        dset = _fetch_neuroquery_lowmem(data_dir)

    logger.info("%s: %d studies, %d coordinates",
                source, len(dset.ids), len(dset.coordinates))
    # Atomic save: write to a temp file then rename, so an interrupted run can
    # never leave a half-written (corrupt) cache behind.
    tmp_path = cache_path.with_suffix(cache_path.suffix + ".tmp")
    dset.save(tmp_path)
    tmp_path.replace(cache_path)
    return dset


def fetch_all(cfg: Config) -> Dict[str, Dataset]:
    """Fetch every database enabled in the config. Returns {source: Dataset}."""
    data_dir = cfg.path("data_raw")
    out: Dict[str, Dataset] = {}
    for source, spec in cfg["databases"].items():
        if not spec.get("enabled"):
            continue
        if source not in _CACHE_NAMES:
            logger.warning("Unknown database '%s' in config; skipping", source)
            continue
        out[source] = _fetch_one(source, data_dir)
    if not out:
        raise RuntimeError("No databases fetched — check config 'databases' section")
    return out
