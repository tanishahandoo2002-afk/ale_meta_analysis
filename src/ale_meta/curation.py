"""Select construct-relevant experiments and keep a PRISMA-style audit trail.

In a manual meta-analysis you write a Boolean search string, run it in PubMed,
and screen the hits by hand. Here the equivalent operation is performed against
each database's term x study feature matrix: a study is *included* if it loads
on at least one inclusion term above threshold, and *excluded* if it loads on
any exclusion term. Every count is recorded so we can render a genuine PRISMA
flow diagram (records identified -> screened -> excluded with reasons ->
included), which is the field-standard transparency artefact.

Term-based selection is exactly how large automated meta-analyses (Neurosynth,
NeuroQuery) define a construct, and it makes the whole screening step
reproducible rather than a subjective judgement call.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, asdict
from typing import Dict, List

import pandas as pd
from nimare.dataset import Dataset

from .config import Config

logger = logging.getLogger(__name__)


@dataclass
class PrismaRecord:
    """Counts for one database's contribution to the PRISMA flow."""

    source: str
    identified: int          # studies in the database
    matched_inclusion: int   # loaded on >=1 inclusion term
    removed_exclusion: int   # dropped for loading on an exclusion term
    removed_low_foci: int    # dropped for too few coordinates
    included: int            # survived all filters


def _labels_for_terms(dset: Dataset, terms: List[str]) -> List[str]:
    """Map plain-English terms to the database's feature-label namespace.

    Neurosynth/NeuroQuery labels look like ``terms_abstract_tfidf__memory``.
    We match on the *exact* trailing term. Exact matching is deliberate: a
    substring rule would let "recognition" sweep in "face recognition" and
    "object recognition" (perceptual paradigms, off-construct), silently
    polluting the sample. We restrict to the TF-IDF term features and ignore the
    LDA topic features so selection maps cleanly onto interpretable terms.
    """
    # Match TF-IDF term features from either database namespace:
    # Neurosynth -> "terms_abstract_tfidf__<term>"
    # NeuroQuery -> "neuroquery6308_combined_tfidf__<term>"
    all_labels = [l for l in dset.get_labels() if "tfidf__" in l]
    wanted = {t.lower().strip() for t in terms}
    matched = [lab for lab in all_labels if lab.split("__")[-1].lower() in wanted]
    return sorted(set(matched))


def _rank_by_relevance(dset: Dataset, ids: List[str],
                       incl_labels: List[str]) -> List[str]:
    """Order ``ids`` by how strongly they load on the inclusion terms, so a cap
    keeps the most construct-relevant experiments."""
    ann = dset.annotations
    cols = [c for c in incl_labels if c in ann.columns]
    if not cols:
        return list(ids)
    sub = ann[ann["id"].isin(ids)].copy()
    sub["_score"] = sub[cols].sum(axis=1)
    sub = sub.sort_values("_score", ascending=False)
    return sub["id"].tolist()


def _studies_matching(dset: Dataset, labels: List[str], thresh: float) -> set:
    """Union of study IDs loading above ``thresh`` on any of ``labels``."""
    hits: set = set()
    for lab in labels:
        try:
            ids = dset.get_studies_by_label(labels=[lab], label_threshold=thresh)
        except Exception as exc:  # label may be absent in a given database
            logger.debug("label %s not usable: %s", lab, exc)
            continue
        hits.update(ids)
    return hits


def _studies_matching_min(dset: Dataset, labels: List[str], thresh: float,
                          min_matches: int) -> set:
    """Study IDs that load above ``thresh`` on at least ``min_matches`` of the
    given labels (stricter AND-of-N selection for sensitivity analysis)."""
    from collections import Counter
    counts: Counter = Counter()
    for lab in labels:
        try:
            ids = dset.get_studies_by_label(labels=[lab], label_threshold=thresh)
        except Exception:
            continue
        counts.update(ids)
    return {sid for sid, n in counts.items() if n >= min_matches}


def curate_database(source: str, dset: Dataset, cfg: Config):
    """Return (included_dataset, PrismaRecord) for a single database."""
    cur = cfg["curation"]
    thresh = float(cur["term_frequency_threshold"])

    incl_labels = _labels_for_terms(dset, cur["inclusion_terms"])
    excl_labels = _labels_for_terms(dset, cur["exclusion_terms"])
    logger.info("[%s] %d inclusion labels, %d exclusion labels matched",
                source, len(incl_labels), len(excl_labels))

    identified = len(dset.ids)
    # A study is included if it loads on at least `min_inclusion_matches`
    # distinct inclusion terms. min=1 is the default (broad, OR logic); raising
    # it to 2+ yields a stricter, more specific construct — the knob a
    # sensitivity analysis turns to check the result is not an artefact of loose
    # selection.
    min_matches = int(cur.get("min_inclusion_matches", 1))
    if min_matches <= 1:
        included_ids = _studies_matching(dset, incl_labels, thresh)
    else:
        included_ids = _studies_matching_min(dset, incl_labels, thresh, min_matches)
    matched_inclusion = len(included_ids)

    excluded_ids = _studies_matching(dset, excl_labels, thresh)
    after_excl = included_ids - excluded_ids
    removed_exclusion = matched_inclusion - len(after_excl)

    # Enforce a minimum number of reported foci per experiment.
    min_foci = int(cur["min_foci_per_study"])
    coords = dset.coordinates
    foci_counts = coords.groupby("id").size()
    enough = set(foci_counts[foci_counts >= min_foci].index)
    final_ids = sorted(after_excl & enough)
    removed_low_foci = len(after_excl) - len(final_ids)

    # Optional cap: keep the experiments most topically central to the
    # construct, ranked by their summed inclusion-term TF-IDF loading. This is a
    # principled reduction (the N studies most about the construct), not an
    # arbitrary truncation, and keeps the compute-heavy stages tractable.
    max_exp = cur.get("max_experiments")
    if max_exp and len(final_ids) > int(max_exp):
        final_ids = _rank_by_relevance(dset, final_ids, incl_labels)[: int(max_exp)]

    final_ids = sorted(final_ids)

    record = PrismaRecord(
        source=source,
        identified=identified,
        matched_inclusion=matched_inclusion,
        removed_exclusion=removed_exclusion,
        removed_low_foci=removed_low_foci,
        included=len(final_ids),
    )
    logger.info("[%s] included %d experiments", source, len(final_ids))

    included_dset = dset.slice(final_ids) if final_ids else None
    return included_dset, record


def curate_all(dsets: Dict[str, Dataset], cfg: Config):
    """Curate every database, merge included studies, and return
    (merged_dataset, prisma_dataframe)."""
    records: List[PrismaRecord] = []
    included_dsets: List[Dataset] = []

    for source, dset in dsets.items():
        inc, rec = curate_database(source, dset, cfg)
        records.append(rec)
        if inc is not None:
            included_dsets.append(inc)

    if not included_dsets:
        raise RuntimeError(
            "No experiments survived curation. Loosen inclusion terms or "
            "lower curation.term_frequency_threshold in config."
        )

    # The same paper often appears in multiple databases under the same
    # (PMID-based) ID. De-duplicate across sources: keep the first database's
    # copy and drop any already-seen IDs from later databases before merging.
    merged = included_dsets[0]
    seen = set(merged.ids)
    n_dupes = 0
    for extra in included_dsets[1:]:
        new_ids = [i for i in extra.ids if i not in seen]
        n_dupes += len(extra.ids) - len(new_ids)
        if not new_ids:
            continue
        merged = merged.merge(extra.slice(new_ids))
        seen.update(new_ids)
    if n_dupes:
        logger.info("Removed %d cross-database duplicate experiments", n_dupes)

    prisma_df = pd.DataFrame([asdict(r) for r in records])
    prisma_df.loc["TOTAL"] = prisma_df.drop(columns=["source"]).sum(numeric_only=True)
    prisma_df.loc["TOTAL", "source"] = "ALL"
    # After merging across databases, the final unique-experiment count:
    prisma_df.attrs["final_merged_n"] = len(merged.ids)

    logger.info("Merged included dataset: %d experiments, %d coordinates",
                len(merged.ids), len(merged.coordinates))
    return merged, prisma_df
