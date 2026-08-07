# Methods (extended)

This document explains *how* each stage works and *why* it is the right choice —
the material that turns a script into a defensible piece of cognitive
neuroscience.

## 1. Coordinate-based meta-analysis (CBMA), and why ALE

Most fMRI papers report their findings as **peak coordinates** of significant
clusters in a standard stereotactic space (MNI or Talairach), not as full
statistical images. Coordinate-based meta-analysis synthesises these peaks
across studies to find where activation *converges* more than chance.

**Activation Likelihood Estimation (ALE)** is the dominant CBMA method:

1. Each reported focus is modelled as a 3-D Gaussian **Modeled Activation (MA)**
   distribution, representing spatial uncertainty about the "true" location.
2. The Gaussian's width (FWHM) is **inversely tied to the study's sample size** —
   larger studies localise more precisely, so they get tighter kernels and
   greater influence. This is why accurate per-study sample sizes matter.
3. Each study's foci are combined into one MA map (taking the voxelwise maximum,
   so multiple nearby foci in one study don't double-count).
4. The **ALE statistic** at each voxel is the union across studies' MA
   values — the probability that *at least one* study truly activated there.
5. High ALE values mark voxels where many independent studies' kernels overlap:
   spatial convergence.

Contrast with older kernel methods (MKDA, KDA), which use binary spheres; ALE's
sample-size-weighted Gaussians are the current standard for peak convergence.

## 2. Inference and multiple-comparisons correction

The observed ALE map is compared to an **empirical null** obtained by
permutation (foci are redistributed under the null of no spatial convergence).
Because a brain map contains ~200k voxels, we must correct for multiple
comparisons. We use **cluster-level family-wise error (FWE)** via Monte-Carlo:

- A **cluster-forming threshold** (voxel p < 0.001) defines candidate clusters.
- The null distribution of **maximum cluster sizes** is built by permutation.
- Clusters larger than the 95th percentile of that null (cluster p < 0.05)
  survive.

This is the field-recommended approach (Eickhoff et al., 2016): voxel-level FWE
is overly conservative, and *uncorrected* maps massively inflate false
positives. We report the corrected z-map and threshold it at the cluster-FWE
level for all downstream steps.

## 3. Study selection as reproducible screening

A manual meta-analysis screens abstracts by hand. We instead screen against each
database's **term × study feature matrix** (TF-IDF weights from automated text
mining). A study is included if it loads above threshold on an inclusion term
and on none of the exclusion terms. This makes screening deterministic and
re-runnable, and every count feeds the **PRISMA** flow diagram
(identified → matched → excluded-with-reasons → included). The tradeoff:
automated selection is broader/noisier than hand-screened full-text inclusion
(documented as a limitation).

## 4. Robustness diagnostics

Significance alone is not credibility. We add three checks:

- **Jackknife (leave-one-experiment-out).** Re-estimate the meta-analysis N
  times, each dropping one experiment, and quantify each experiment's
  contribution to each cluster. A cluster driven by a single study is fragile.
- **Focus-counter.** Count how many independent experiments report a focus
  inside each cluster — convergence claimed from very few experiments is weak.
- **File-drawer robustness.** The coordinate analog of Rosenthal's Fail-Safe N:
  inject synthetic "null" experiments (randomly located foci, matched to the
  observed foci-count distribution) and find how many are needed to erase a
  cluster's significance. A cluster tolerant of many noise studies is robust to
  the publication-bias / file-drawer problem (cf. Acar et al., 2018).

## 5. Meta-analytic coactivation modeling (MACM)

MACM estimates a region's **task-independent co-activation network** purely from
coordinates: select every study in the *full* database that reports a focus
within a seed region (here, a 6 mm sphere at the strongest ALE peak), then run
ALE on that subset. Regions that converge form the seed's meta-analytic
"connectivity" fingerprint. For an episodic-retrieval hub this should recover the
wider default-mode/recollection network — an interpretable validation.

## 6. Functional decoding (reverse inference)

Decoding asks the inverse of the meta-analysis: *given this region, what
cognitive terms is it associated with across the whole literature?* Using
Neurosynth's ROI-association method, we correlate, across studies, the mean MA
value inside the region with each term's loading. Top terms corroborate (or
complicate) the region's functional identity and guard against the circularity
of naming a blob by eye.

## 7. Subtraction and conjunction

To test **dual-process theory**, retrieval studies are split into a
recognition/familiarity group and a recall/autobiographical group:

- **Subtraction** (NiMARE `ALESubtraction`) builds a null by randomly
  reassigning experiments between the two groups, so surviving differences
  reflect genuine divergence rather than unequal group sizes.
- **Conjunction** uses the **minimum-statistic** approach: a voxel is in the
  conjunction only if it is significant in *both* single-group ALEs, with value
  = the smaller of the two z-scores. This identifies the shared retrieval core.

## 8. Anatomical labelling

Surviving cluster peaks are labelled against the **Harvard-Oxford** cortical and
subcortical probabilistic atlases (max-prob, 25% threshold, 2 mm), preferring a
named cortical region and falling back to subcortical structures — so each result
is a real neuroanatomical name, not a bare coordinate.

## References
- Eickhoff SB et al. (2012). *Activation likelihood estimation meta-analysis
  revisited.* NeuroImage.
- Eickhoff SB et al. (2016). *Behavior, sensitivity, and power of activation
  likelihood estimation characterized by massive empirical simulation.*
  NeuroImage.
- Turkeltaub PE et al. (2012). *Minimizing within-experiment and within-group
  effects in activation likelihood estimation meta-analyses.* HBM.
- Yarkoni T et al. (2011). *Large-scale automated synthesis of human functional
  neuroimaging data.* Nature Methods. (Neurosynth)
- Dockès J et al. (2020). *NeuroQuery, comprehensive meta-analysis of human brain
  mapping.* eLife.
- Salo T et al. (2023). *NiMARE: Neuroimaging Meta-Analysis Research
  Environment.* Aperture Neuro.
- Acar F et al. (2018). *Assessing robustness against potential publication bias
  in ALE meta-analyses.* PLoS ONE.
- Rugg MD, Vilberg KL (2013). *Brain networks underlying episodic memory
  retrieval.* Curr Opin Neurobiol.
