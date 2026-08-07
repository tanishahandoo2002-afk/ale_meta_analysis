# Pre-analysis protocol

A pre-registered-style protocol fixes the analysis decisions *before* looking at
results, which is what makes a meta-analysis credible rather than a fishing
expedition. This document doubles as the Methods-section skeleton.

## 1. Question
Across the published task-fMRI literature, where does brain activation reliably
converge during **episodic memory retrieval** in healthy adults, and how does
convergence differ between recognition- and recall-based retrieval?

## 2. Construct definition
Episodic memory retrieval = the recovery of a specific past event together with
its spatiotemporal/contextual detail (Tulving). Operationalised via the
cognitive terms used to tag studies in coordinate databases (see §4).

## 3. Data sources
- **Neurosynth** v7 (~14,371 studies) — primary; supplies coordinates and the
  TF-IDF term matrix used for selection and decoding.
- **NeuroQuery** v1 (~13k studies) — independent database; contributes
  coordinates and a second term namespace for multi-source synthesis.

Rationale for multiple sources: reduces dependence on any one database's
extraction idiosyncrasies and broadens coverage.

## 4. Inclusion / exclusion (term-based screening)
**Include** a study if it loads (TF-IDF ≥ 0.001) on ≥1 of:
`episodic memory, retrieval, recollection, recognition memory, autobiographical,
remember, encoding retrieval`.

**Exclude** if it loads on any of:
`working memory, schizophrenia, alzheimer, lesion, rodent`
(off-construct paradigms and clinical/animal samples).

**Additional filter:** ≥1 reported focus (coordinate) per experiment.

Exact-term matching is used deliberately so that, e.g., "recognition" cannot
sweep in perceptual "face/object recognition" studies.

## 5. Analysis plan
1. **ALE** with the sample-size-weighted Gaussian kernel and an approximate null.
2. **Cluster-level FWE correction** (Monte-Carlo): cluster-forming p < 0.001,
   cluster-level p < 0.05, 5,000 permutations.
3. **Anatomical labelling** of surviving cluster peaks (Harvard-Oxford atlas).
4. **Diagnostics:** jackknife (leave-one-out), focus-counter, file-drawer
   robustness screen.
5. **MACM** seeded at the strongest cluster peak (6 mm sphere) against the full
   database.
6. **Functional decoding** of the convergent region against the full term set.
7. **Subtraction & conjunction:** recognition/familiarity vs. recall/
   autobiographical.

## 6. Power
ALE is considered underpowered below ~17 experiments (Eickhoff et al., 2016).
The database-driven approach yields far more than this; the power concern is
inverted (very large N → almost everything converges), so interpretation
emphasises effect location and robustness, not mere significance.

## 7. Deliverables
PRISMA diagram · significant-cluster table · brain figures · decoding table ·
diagnostics tables · MACM & contrast maps · written REPORT.md + plain-language
SUMMARY.md.

## 8. Reproducibility
Single config file; fixed random seed; cached raw data; one-command execution.
