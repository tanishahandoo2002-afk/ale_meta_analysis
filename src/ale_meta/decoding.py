"""Meta-analytic functional decoding (reverse inference).

ALE tells us *where* episodic retrieval converges. Decoding closes the loop by
asking the database the inverse question: given this convergent region, which
cognitive terms is it most associated with across ~14,000 studies? This guards
against the circularity of eyeballing a blob and calling it "memory-related".

We use Neurosynth's ROI-association method: for every study, take the mean of
its modeled-activation map inside our region of interest, then correlate that
across-study vector with each term's TF-IDF loading. Terms that rise to the top
(ideally "memory", "retrieval", "recollection", "episodic") corroborate the
functional identity of the region; unexpected terms are scientifically
interesting rather than errors.
"""
from __future__ import annotations

import logging
from typing import Optional

import nibabel as nib
import numpy as np
import pandas as pd
from nimare.dataset import Dataset
from nimare.decode.discrete import ROIAssociationDecoder

from .config import Config

logger = logging.getLogger(__name__)


def _binarize(img) -> "nib.Nifti1Image":
    data = (np.abs(img.get_fdata()) > 0).astype(np.int16)
    return nib.Nifti1Image(data, img.affine, img.header)


def decode_region(full_db: Dataset, roi_img, cfg: Config) -> Optional[pd.DataFrame]:
    """Decode the cognitive terms associated with an ROI (the ALE result map).

    Parameters
    ----------
    full_db : the full database (must carry TF-IDF term features).
    roi_img : a NIfTI image; nonzero voxels define the ROI (e.g. significant
        ALE clusters).
    """
    d = cfg["decoding"]
    if not d.get("enabled"):
        return None

    roi = _binarize(roi_img)
    if roi.get_fdata().sum() == 0:
        logger.warning("ROI is empty; decoding skipped.")
        return None

    logger.info("Decoding ROI against Neurosynth term features...")
    decoder = ROIAssociationDecoder(
        masker=roi,
        feature_group="terms_abstract_tfidf",
    )
    decoder.fit(full_db)
    result = decoder.transform()

    # result is a DataFrame indexed by feature with a correlation column.
    result = result.copy()
    col = result.columns[0]
    result["term"] = [ix.split("__")[-1] for ix in result.index]
    result = result.rename(columns={col: "r"}).sort_values("r", ascending=False)
    top = result[["term", "r"]].head(int(d["top_n_terms"])).reset_index(drop=True)

    out = cfg.path("tables") / "functional_decoding.csv"
    top.to_csv(out, index=False)
    logger.info("Wrote top %d decoded terms to %s", len(top), out)
    return top
