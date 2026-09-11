# Research Roadmap — from methods project to a real research contribution

**Purpose.** This is the planning reference for turning the current project from a
strong *computational methods demonstration* (recovers the known episodic-retrieval
network from automated databases) into a *credible research contribution* (a novel
question, rigorous methods, and a real output). Every item is tagged for
feasibility on the target machine — an **M1 MacBook Air** (8-core CPU, ~8 GB RAM,
no fan → thermal throttling under sustained load, no CUDA/GPU).

Feasibility tags:
- **✅ M1-feasible** — runs comfortably as-is (with thread caps).
- **⚠️ M1-bounded** — feasible only at a bounded scale (fewer studies / permutations / careful memory).
- **❌ Off-M1** — needs a compute cluster / cloud VM / free Colab; do not attempt full-scale locally.

---

## 0. Where the project stands (honest baseline)

- **Engineering / reproducibility:** strong (A−). Full NiMARE pipeline, two
  databases, MACM, decoding, dual-process + encoding-vs-retrieval contrasts,
  diagnostics, cross-database + sensitivity validation, DMN overlap, landmark
  recovery, interactive dashboard.
- **Scientific novelty:** low (C). It *confirms* the well-established core
  recollection network — there are already published hand-curated ALE
  meta-analyses of episodic retrieval (Spaniol 2009, Kim 2010).
- **What S-tier requires:** a **novel question** + **hand-curated rigor** + a
  **real output** (pre-registration, preprint, open code with a DOI). Not more
  code on the current question.

---

## 1. Tier 1 — the path to a genuine contribution (do these first)

### 1a. Hand-curated ALE — the rigorous complement  ✅ M1-feasible
The single highest-value addition. Read 20–30 real papers, extract peak tables +
**true sample sizes** into `data/hand_curated/*_sleuth.txt`, and run
`scripts/run_hand_curated.py` (uses proper **sample-size-weighted** ALE — the
strict method the automated pipeline can't). Then show the automated large-scale
map replicates the hand-curated one.
- *Why:* answers the exact question a reviewer/PI will ask; demonstrates the
  classic systematic-review skill; lets you claim "automated pipeline replicates
  a hand-curated meta-analysis."
- *M1:* trivial compute (small N). The work is the reading/curation (yours).
- *Status:* scaffolded (`docs/HAND_CURATION.md`, template, runner).

### 1b. A NOVEL comparative question (pick ONE)  ✅ / ⚠️ M1-feasible
Change the question from "where does retrieval converge?" (answered) to one with
an unknown answer. Reuses the existing two-group contrast machinery.
- **Aging:** episodic retrieval in **younger vs. older adults** — big clean
  literature, strong predictions (reduced MTL, PASA/HAROLD compensation). ✅
- **Clinical (fits neuropsychology):** retrieval in **depression / PTSD / MCI**
  vs. controls — more distinctive, clinically relevant. ✅ (curation effort ↑)
- **Process/material:** **autobiographical vs. laboratory** episodic;
  **item vs. source/associative**; **verbal vs. visual** retrieval. ✅
- *Method:* separate ALEs per group + **proper between-group subtraction with
  cluster-FWE** and a **conjunction** (shared core). ⚠️ each group needs ≥17–20
  experiments; keep pools bounded (see §4).
- *Novelty lives in the question + curation, not new code.*

### 1c. Rigorous between-group contrast  ⚠️ M1-bounded
Upgrade the current voxelwise-thresholded subtraction to NiMARE's
**ALESubtraction with Monte-Carlo cluster-FWE** and a minimum-statistic
conjunction. ~2 extra ALEs + a permutation subtraction; bounded pools + thread
caps keep it to ~1–2 h.

### 1d. A real research output  ✅ M1-feasible
- **Pre-register** the hypothesis on **OSF** *before* running (bumps credibility a
  full tier). 
- **Preprint** to **bioRxiv / PsyArXiv**.
- **GitHub + Zenodo DOI** (Zenodo mints a citable DOI from a GitHub release).
- Submit to an undergraduate research journal (JEI / Impulse / JYI).
- *"Preprint posted" / "under review" is what makes an MS committee treat it as
  research.*

---

## 2. Tier 2 — strong depth additions (all ✅/⚠️ M1-feasible)

### 2a. Automated-vs-hand-curated benchmark (methods contribution)  ⚠️ M1-bounded
Quantify how faithfully Neurosynth/NeuroQuery-based ALE reproduces hand-curated
ALE across 2–3 constructs (e.g., retrieval, working memory, emotion). A genuine
*methods* paper ("can automated databases stand in for hand curation in CBMA?").
Plays to the engineering strength.

### 2b. Recognition vs. familiarity (dual-process), done rigorously  ✅
Sharpen the current recognition/recall split into a proper recollection vs.
familiarity contrast with cluster-FWE — a live theoretical debate (hippocampus
vs. perirhinal).

### 2c. Laterality / HERA quantification  ✅
Quantify left/right asymmetry of the retrieval network (HERA predicts right-PFC
retrieval dominance) with a numeric laterality index per cluster.

### 2d. Richer decoding  ✅
- **BrainMap taxonomy** behavioural-domain / paradigm-class decoding.
- **Cognitive Atlas** concept decoding.
- Neurosynth **posterior-probability (specificity)** decoding, not just
  correlation — guards reverse-inference claims.

### 2e. Meta-analytic connectivity-based parcellation  ⚠️ M1-bounded
Cluster the coactivation profiles (MACM across multiple seeds) to parcellate the
retrieval network into sub-systems. Moderate memory; keep seed count small.

### 2f. Multimodal tie-in with the EEG project (Project 1)  ✅
Frame a combined narrative: EEG (temporal, single-study) + fMRI meta-analysis
(spatial, literature-level) converging on the same construct. A cross-method
synthesis is distinctive and ties the portfolio together. (Discussion/framing +
a shared construct; no heavy compute.)

### 2g. Package as an open tool + JOSS paper  ✅
Add `pyproject.toml`, unit tests, docs; make it `pip install`-able; submit a
short paper to the **Journal of Open Source Software**. A citable open tool is a
real, defensible contribution.

---

## 3. Tier 3 — stretch / other ideas

### ✅ / ⚠️ M1-feasible
- **Direct replication check** vs. a specific published ALE (compare your peaks to
  Spaniol 2009 / Kim 2010 coordinates numerically). ✅
- **Kernel/method comparison** — ALE vs. MKDA vs. KDA on the same data; report
  convergence stability. ✅
- **Split-half / bootstrap reliability** of the convergence map. ⚠️ (compute;
  bounded pool, run overnight).
- **Emotional vs. neutral**, **true vs. false memory**, **retrieval success vs.
  effort**, **sex differences**, **lifespan** meta-analyses — each a self-contained
  novel-ish question reusing the pipeline. ✅ (curation effort).
- **Memory-taxonomy** map: episodic vs. semantic vs. working memory convergence &
  overlap (Dice/conjunction across three ALEs). ⚠️ (3 pools).
- **SCALE** (specific co-activation likelihood estimation) for a seed. ⚠️.

### ❌ Off-M1 (needs cloud / cluster / free Colab)
- **Full-pool (~1,500 studies) ≥5,000-permutation run** — weeks of compute + RAM
  pressure; oversubscribes on M1. Use a cloud VM / university HPC / Colab.
- **Image-based meta-analysis (IBMA)** over many **NeuroVault** unthresholded
  maps — memory-heavy (loads many volumes); do a *small* IBMA locally or the full
  one on cloud.
- **GC-LDA topic-model decoding** at scale — memory-heavy; small vocab only on M1.
- **Anything GPU/deep-learning** — M1 has no CUDA; not applicable to this project
  anyway.

---

## 4. M1 MacBook Air operating playbook (so heavy runs don't melt the machine)

Hard-won lessons from this project's runs:

1. **Always cap threads** or joblib × BLAS × numba oversubscribe to load 200+ and
   thermally throttle:
   ```bash
   OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
   NUMEXPR_NUM_THREADS=1 NUMBA_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 \
     PYTHONPATH=src python scripts/run_pipeline.py --config config/config_bounded.yaml
   ```
2. **Bound the pool.** ~250 experiments/database (~430 merged) with `n_cores: 7`
   completes the full pipeline in ~2.5 h. Going to the full ~1,500-study pool is
   *not* an M1 job.
3. **Permutations:** 2,000 is the practical sweet spot locally (a solid null);
   5,000+ = cloud. Document this in the paper.
4. **RAM is the ceiling (~8 GB).** NeuroQuery's full feature matrix OOMs — the code
   already loads only the compact TF-IDF vocab (`datasets._fetch_neuroquery_lowmem`).
   Avoid loading many NIfTI volumes at once (IBMA).
5. **Cache & don't re-fetch.** Databases are cached as `data/raw/*.pkl.gz`; keep
   them.
6. **Long runs:** launch with `nohup`, monitor, keep the machine awake (they die on
   session teardown), and expect the no-fan Air to throttle after ~30–60 min of
   sustained load — thread caps mitigate this.
7. **Free "off-M1" options for the one heavy final run:** Google Colab (free CPU
   tier — mind RAM/time limits), a small spot cloud VM (a few dollars), or
   university HPC if available.

---

## 5. Suggested sequence

1. **Now (M1):** push current repo to GitHub + Zenodo DOI (portfolio anchor).
2. **Weeks 1–3 (mostly your reading time):** pick the novel question (§1b),
   hand-curate both arms (§1a), pre-register (§1d).
3. **Week 4 (M1, bounded):** rigorous between-group contrast (§1c) + automated
   cross-validation using the existing pipeline.
4. **Week 5:** write it up → preprint (§1d); optionally the tool/JOSS paper (§2g).
5. **Later / opportunistic:** Tier-2/3 additions; the full-pool run on cloud if a
   reviewer asks.

**Bottom line:** S-tier is earned by the novel question + hand-curated rigor + a
posted output — all of which are M1-feasible. The only things that genuinely need
off-M1 compute are the full-pool/high-permutation confirmatory run and large IBMA,
neither of which is required to make the contribution.
