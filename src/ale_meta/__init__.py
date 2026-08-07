"""
ale_meta
========
A reproducible, coordinate-based (ALE) meta-analysis pipeline for the
neuroimaging literature, built on NiMARE.

The package is organised as a set of composable stages:

    config      -> load and validate the analysis configuration
    datasets    -> fetch coordinate databases (Neurosynth, NeuroQuery)
    curation    -> select construct-relevant experiments + PRISMA accounting
    ale         -> run ALE with cluster-level FWE correction
    diagnostics -> jackknife, focus-counter, fail-safe N
    macm        -> meta-analytic coactivation modeling
    decoding    -> meta-analytic functional decoding (reverse inference)
    contrast    -> subtraction / conjunction between sub-constructs
    viz         -> glass-brain, surface and interactive visualisation
    report      -> assemble tables and a human-readable summary

Each stage is driven entirely by ``config/config.yaml`` so that the full
analysis is auditable and reproducible from a single command.
"""

__version__ = "0.1.0"
__all__ = [
    "config",
    "datasets",
    "curation",
    "ale",
    "diagnostics",
    "macm",
    "decoding",
    "contrast",
    "viz",
    "report",
]
