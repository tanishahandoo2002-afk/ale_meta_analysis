# Coordinate-Based (ALE) Meta-Analysis of Episodic Memory Retrieval

A fully reproducible, coordinate-based **Activation Likelihood Estimation (ALE)**
meta-analysis pipeline that synthesises the published fMRI literature on
**episodic memory retrieval** — computed end-to-end in open-source Python
([NiMARE](https://nimare.readthedocs.io)) on real coordinates pulled from
multiple public neuroimaging databases.

> **Owner:** Tanisha Handoo — B.Sc. Neurosciences & Neuropsychology, Amity University.
> This is the computational / cognitive-neuroscience complement to an EEG
> classification project: where that works at the single-study, signal level,
> this works at the level of *quantitative synthesis across the whole
> literature*.

---

## Why this is more than a manual GingerALE study

The original brief describes the classic manual workflow: search PubMed by hand,
screen abstracts, type coordinates into GingerALE, threshold, and write up. This
project keeps that scientific logic but rebuilds it as **reproducible code** and
extends it with methods that a point-and-click workflow cannot easily do:

| Capability | Manual GingerALE | This pipeline |
|---|---|---|
| Literature ingest | Manual PubMed search + typing coordinates | Programmatic pull from **Neurosynth (~14k studies)** and **NeuroQuery (~13k studies)** |
| Screening / PRISMA | Manual, subjective | Reproducible term-based selection with an auto-generated **PRISMA flow diagram** |
| ALE + FWE | ✔ | ✔ (cluster-level FWE, Monte-Carlo) |
| Robustness diagnostics | — | **Jackknife**, **focus-counter**, **file-drawer / publication-bias** screen |
| Connectivity | — | **Meta-analytic coactivation modeling (MACM)** |
| Reverse inference | — | **Functional decoding** against ~14k studies |
| Theory testing | — | **Subtraction & conjunction** (recognition vs. recall) |
| Anatomical labelling | Manual atlas lookup | Automated Harvard-Oxford labelling |
| Reproducibility | Low | One command, one config file, fixed seed |

Every parameter lives in [`config/config.yaml`](config/config.yaml); change it,
re-run, and the whole analysis (including figures and the written report)
regenerates.

---

## The neuroscience question

Episodic memory retrieval — recovering a specific past experience with its
spatiotemporal context — is theorised to depend on a **core recollection
network**: medial temporal lobe (esp. hippocampus), posterior medial parietal
cortex (precuneus / posterior cingulate / retrosplenial), lateral parietal
cortex (angular gyrus), and medial prefrontal cortex. Dual-process theory
further splits retrieval into **recollection** (detailed, context-rich,
hippocampal/parietal) and **familiarity** (context-free "oldness",
perirhinal). This pipeline asks, quantitatively across the literature:

1. **Where** does activation reliably converge during episodic retrieval? (ALE)
2. **How robust** is each convergent region to individual studies and to the
   file-drawer problem? (diagnostics)
3. **What network** does the strongest hub co-activate with? (MACM)
4. **What is the region's functional identity** per the wider literature? (decoding)
5. **Do recognition and recall diverge** where dual-process theory predicts?
   (subtraction / conjunction)

See [`docs/METHODS.md`](docs/METHODS.md) for the full methodology and
[`docs/GLOSSARY.md`](docs/GLOSSARY.md) for the neuroscience and method concepts.

---

## Quickstart

```bash
# 1. Environment (Python 3.9–3.12; developed on 3.11)
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2. Run the whole pipeline (first run downloads ~0.5 GB of databases and caches them)
PYTHONPATH=src python scripts/run_pipeline.py

# Quick smoke test with fewer permutations:
PYTHONPATH=src python scripts/run_pipeline.py --fast

# Larger / higher-iteration runs: CAP THE THREADS or joblib+BLAS+numba will
# oversubscribe (hundreds of threads, load average 200+). Always prefix:
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
NUMEXPR_NUM_THREADS=1 NUMBA_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 \
  PYTHONPATH=src python scripts/run_pipeline.py --config config/config_bounded.yaml

# Skip the expensive stages:
PYTHONPATH=src python scripts/run_pipeline.py --skip-diagnostics --skip-macm
```

Outputs land in `results/`:

```
results/
├── REPORT.md                 # full methods + results write-up skeleton
├── SUMMARY.md                # one-page plain-language summary
├── figures/
│   ├── prisma_flow.png       # PRISMA study-selection diagram
│   ├── ale_glass_brain.png   # convergent activation (headline figure)
│   ├── ale_slices.png
│   ├── ale_interactive.html  # explore the map in a browser
│   ├── macm_glass_brain.png  # coactivation network
│   ├── decoding_terms.png    # functional decoding bar chart
│   └── diag_focus_counter.png
├── tables/                   # every result as CSV
└── maps/                     # NIfTI statistical maps (open in Mango/MRIcroGL)
```

---

## Repository layout

```
config/config.yaml            # single source of truth for every parameter
src/ale_meta/
├── config.py                 # typed config loader + reproducible seeding
├── datasets.py               # fetch/cache Neurosynth + NeuroQuery
├── curation.py               # term-based study selection + PRISMA accounting
├── prisma.py                 # PRISMA flow-diagram rendering
├── ale.py                    # ALE + cluster-level FWE, cluster tables
├── diagnostics.py            # jackknife, focus-counter, file-drawer robustness
├── macm.py                   # meta-analytic coactivation modeling
├── decoding.py               # functional decoding (reverse inference)
├── contrast.py               # subtraction + conjunction of sub-constructs
├── viz.py                    # glass-brain / slices / interactive / bar charts
└── report.py                 # anatomical labelling + REPORT.md / SUMMARY.md
scripts/run_pipeline.py       # end-to-end orchestrator
docs/                         # PROTOCOL, METHODS, GLOSSARY
```

---

## Data provenance & honesty note

Coordinates come from **Neurosynth** and **NeuroQuery**, large databases built by
*automated* text-mining and coordinate extraction. This makes the analysis
reproducible and high-throughput, but the selection is broader and noisier than
hand-screened, full-text inclusion. Treat the result as a **large-scale,
automated complement** to a manual PRISMA review, not a substitute for one. No
results are fabricated: every number in `results/` is computed from real
published coordinates by the code in this repository.

## Key references
- Eickhoff et al. (2012, 2016) — ALE algorithm and cluster-level FWE.
- Yarkoni et al. (2011) — Neurosynth.
- Dockès et al. (2020) — NeuroQuery.
- Salo et al. (2023) — NiMARE.
- Rugg & Vilberg (2013) — core recollection network.
