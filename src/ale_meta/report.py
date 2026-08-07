"""Assemble the analysis outputs into human-readable reports.

Produces two artefacts:

* ``results/REPORT.md`` — the full methods+results write-up skeleton: PRISMA
  accounting, the significant-cluster table (with anatomical labels), functional
  decoding, diagnostics, MACM and contrast summaries. This is the backbone of
  the eventual manuscript.
* ``results/SUMMARY.md`` — a one-page plain-language summary for a general
  audience.

Cluster peaks are labelled anatomically against the Harvard-Oxford cortical and
subcortical probabilistic atlases, so each convergent region gets a real
neuroanatomical name rather than a bare coordinate.
"""
from __future__ import annotations

import logging
from datetime import date
from typing import Dict, Optional, Tuple

import numpy as np
import pandas as pd

from .config import Config

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------
# Anatomical labelling
# --------------------------------------------------------------------------
def _load_atlas():
    from nilearn import datasets, image
    cort = datasets.fetch_atlas_harvard_oxford("cort-maxprob-thr25-2mm")
    sub = datasets.fetch_atlas_harvard_oxford("sub-maxprob-thr25-2mm")
    return cort, sub


def _label_peak(xyz: Tuple[float, float, float], cort, sub) -> str:
    """Return the anatomical label for an MNI coordinate, preferring a named
    cortical region and falling back to subcortical structures."""
    from nilearn import image
    import numpy as np

    for atlas in (cort, sub):
        img = atlas.maps if not isinstance(atlas.maps, str) else image.load_img(atlas.maps)
        affine = img.affine
        inv = np.linalg.inv(affine)
        ijk = inv.dot(np.array([*xyz, 1]))[:3].round().astype(int)
        data = img.get_fdata()
        if np.any(ijk < 0) or np.any(ijk >= np.array(data.shape)):
            continue
        idx = int(data[ijk[0], ijk[1], ijk[2]])
        if idx > 0:
            labels = atlas.labels
            name = labels[idx] if idx < len(labels) else f"region {idx}"
            if name and name.lower() != "background":
                return name
    return "Unlabelled / white matter"


def label_clusters(cluster_df: pd.DataFrame) -> pd.DataFrame:
    if cluster_df is None or len(cluster_df) == 0:
        return cluster_df
    try:
        cort, sub = _load_atlas()
    except Exception as exc:
        logger.warning("Could not load atlas for labelling: %s", exc)
        cluster_df = cluster_df.copy()
        cluster_df["Anatomical Label"] = "n/a"
        return cluster_df

    labels = [
        _label_peak((row["X"], row["Y"], row["Z"]), cort, sub)
        for _, row in cluster_df.iterrows()
    ]
    out = cluster_df.copy()
    out["Anatomical Label"] = labels
    return out


# --------------------------------------------------------------------------
# Report assembly
# --------------------------------------------------------------------------
def _md_table(df: pd.DataFrame) -> str:
    if df is None or len(df) == 0:
        return "_No results._\n"
    return df.to_markdown(index=False) + "\n"


def _diagnostics_summary(diagnostics: Dict[str, pd.DataFrame]):
    """Collapse the per-experiment focus and jackknife tables into one compact
    per-cluster stability table (contributing experiments + max single-study
    influence). Both NiMARE tables share the same experiment×cluster shape."""
    focus = diagnostics.get("focus_counter")
    jk = diagnostics.get("jackknife")
    if focus is None and jk is None:
        return None

    # Tables carry an 'id' string column plus one numeric column per cluster
    # ('PositiveTail N' / 'NegativeTail N'); use only the cluster columns.
    rows = {}
    if focus is not None and len(focus):
        for col in [c for c in focus.columns if "Tail" in str(c)]:
            rows.setdefault(str(col), {})["n experiments (focus)"] = int(
                (focus[col] > 0).sum())
    if jk is not None and len(jk):
        for col in [c for c in jk.columns if "Tail" in str(c)]:
            rows.setdefault(str(col), {})["max single-study influence"] = round(
                float(jk[col].max()), 3)

    if not rows:
        return None
    df = pd.DataFrame([{"cluster": k, **v} for k, v in rows.items()])

    # Attach each diagnostic cluster's anatomical label (Point 1: reconcile the
    # diagnostics with the main results by giving every cluster a region name).
    clust = diagnostics.get("cluster_table")
    if clust is not None and len(clust) and "Cluster ID" in clust.columns:
        from . import anatomy
        labels = {
            str(r["Cluster ID"]): anatomy.label_peak((r["X"], r["Y"], r["Z"]))
            for _, r in clust.iterrows()
        }
        df["region"] = df["cluster"].map(labels).fillna("")

    def _order(c):  # numeric order of "PositiveTail 3" etc.
        digits = "".join(ch for ch in str(c) if ch.isdigit())
        return int(digits) if digits else 0
    df = df.sort_values("cluster", key=lambda s: s.map(_order)).reset_index(drop=True)
    return df


def build_report(cfg: Config, *, prisma: pd.DataFrame,
                 clusters: pd.DataFrame, decoding: Optional[pd.DataFrame],
                 diagnostics: Dict[str, pd.DataFrame],
                 macm_info: Optional[dict], contrast_info: Optional[dict],
                 n_experiments: int) -> None:
    construct = cfg["project"]["construct"]
    a = cfg["ale"]
    labelled = label_clusters(clusters)
    labelled_path = cfg.path("tables") / "ale_clusters_labelled.csv"
    if labelled is not None and len(labelled):
        labelled.to_csv(labelled_path, index=False)

    lines = []
    lines.append(f"# ALE Meta-Analysis of {construct.title()} — Results\n")
    lines.append(f"_Generated {date.today().isoformat()} · owner: "
                 f"{cfg['project']['owner']}_\n")

    lines.append("## 1. Data sources & PRISMA accounting\n")
    lines.append("Studies were drawn from multiple public coordinate databases "
                 "and screened by cognitive term against the construct.\n")
    lines.append(_md_table(prisma))
    lines.append(f"\n**Final included experiments (merged, de-duplicated): "
                 f"{n_experiments}.**\n")
    if n_experiments < 17:
        lines.append("\n> ⚠️ Fewer than ~17 experiments is considered "
                     "underpowered for ALE (Eickhoff et al., 2016). Interpret "
                     "with caution or broaden inclusion terms.\n")

    lines.append("\n## 2. Convergent activation (ALE + cluster-level FWE)\n")
    lines.append(f"ALE with an approximate null; cluster-forming "
                 f"p < {a['cluster_forming_p']}, cluster-level FWE "
                 f"p < {a['fwe_cluster_p']}, {a['n_iters']} permutations.\n")
    lines.append(_md_table(labelled))

    lines.append("\n## 3. Functional decoding (reverse inference)\n")
    lines.append("Cognitive terms most associated with the convergent region "
                 "across the full database.\n")
    lines.append(_md_table(decoding))

    lines.append("\n## 4. Robustness diagnostics\n")
    diag_summary = _diagnostics_summary(diagnostics)
    if diag_summary is not None and len(diag_summary):
        lines.append(
            "Per-cluster stability. **n experiments (focus)** = independent "
            "experiments reporting a focus in the cluster (more = more robust). "
            "**max single-study influence** = the largest leave-one-out "
            "jackknife contribution of any one experiment (lower = less "
            "dependent on a single study).\n")
        lines.append(_md_table(diag_summary))
    else:
        lines.append("_Diagnostics not run or produced no per-cluster table._\n")
    if "file_drawer" in diagnostics:
        lines.append("\n**File-drawer robustness** — surviving clusters as "
                     "synthetic null experiments are injected:\n")
        lines.append(_md_table(diagnostics["file_drawer"]))

    lines.append("\n## 5. Meta-analytic coactivation modeling (MACM)\n")
    if macm_info:
        lines.append(f"Seed at strongest ALE peak "
                     f"{macm_info.get('seed_xyz')}; "
                     f"{macm_info.get('n_studies')} coactivating studies. "
                     f"See `results/figures/macm_glass_brain.png`.\n")
    else:
        lines.append("_MACM not run or no seed available._\n")

    lines.append("\n## 6. Sub-construct contrast (subtraction & conjunction)\n")
    if contrast_info:
        a, b = contrast_info["group_a"], contrast_info["group_b"]
        lines.append(
            f"Dual-process test: **{a}** ({contrast_info['n_a']} exps) vs "
            f"**{b}** ({contrast_info['n_b']} exps). Subtraction maps are "
            f"voxelwise-thresholded (not cluster-FWE); interpret directionally.\n")
        cols = ["X", "Y", "Z", "Cluster Size (mm3)", "Anatomical Label"]

        def _ctab(key):
            t = contrast_info.get(key)
            return _md_table(t[cols]) if t is not None and len(t) else "_none._\n"

        lines.append(f"\n**Where {a} > {b}** (top clusters):\n")
        lines.append(_ctab("subtraction_a_gt_b"))
        lines.append(f"\n**Where {b} > {a}** (top clusters):\n")
        lines.append(_ctab("subtraction_b_gt_a"))
        lines.append(f"\n**Shared retrieval core** ({a} ∧ {b} conjunction, "
                     f"{contrast_info['conjunction_voxels']} voxels):\n")
        lines.append(_ctab("conjunction_clusters"))
    else:
        lines.append("_Contrast not run._\n")

    lines.append("\n## 7. Limitations\n")
    lines.append(
        "- Term-based selection from automated databases is broader and noisier "
        "than hand-screened full-text inclusion; treat this as a high-throughput "
        "complement to a manual PRISMA review, not a replacement.\n"
        "- Coordinate reporting inconsistencies and publication bias affect all "
        "CBMA; robustness can be probed with the optional file-drawer screen "
        "(config `diagnostics.fail_safe_n`).\n"
        "- ALE kernels use a fixed nominal sample size because automated "
        "databases do not report per-study n, so studies are not sample-size-"
        "weighted as in a classic hand-extracted ALE.\n"
        "- Neurosynth/NeuroQuery coordinates are extracted automatically and may "
        "include non-activation or contrast-ambiguous foci.\n")

    report_path = cfg.path("results") / "REPORT.md"
    report_path.write_text("\n".join(lines))
    logger.info("Wrote full report to %s", report_path)

    _build_summary(cfg, labelled, decoding, n_experiments)


def _build_summary(cfg: Config, clusters: pd.DataFrame,
                   decoding: Optional[pd.DataFrame], n: int) -> None:
    construct = cfg["project"]["construct"]
    regions = ", ".join(clusters["Anatomical Label"].head(4)) if (
        clusters is not None and len(clusters)) else "no significant regions"
    terms = ", ".join(decoding["term"].head(5)) if (
        decoding is not None and len(decoding)) else "n/a"

    txt = f"""# Plain-language summary

**Question.** Across the published fMRI literature, where in the brain does
activity reliably converge during **{construct}**?

**What we did.** We pooled peak-activation coordinates from {n} experiments
drawn from large public neuroimaging databases (Neurosynth, NeuroQuery),
selected by cognitive term, and ran an Activation Likelihood Estimation (ALE)
meta-analysis with the field-standard cluster-level family-wise-error
correction. We then checked robustness, mapped the region's wider
co-activation network, and asked the databases which cognitive terms the
region is associated with.

**What we found.** Convergent activation was strongest in: {regions}. The
region was most associated with the terms: {terms} — consistent with its role
in {construct}.

**Why it matters.** This quantitatively synthesises many independent studies
into a single, reproducible map of where the brain supports {construct},
computed end-to-end in open-source Python so anyone can rerun it.
"""
    out = cfg.path("results") / "SUMMARY.md"
    out.write_text(txt)
    logger.info("Wrote plain-language summary to %s", out)
