# Glossary — neuroscience & method concepts

A quick-reference for the concepts this project touches, aimed at making the work
legible to both a cognitive-neuroscience and a computational reader.

## Cognitive neuroscience

**Episodic memory** — memory for specific personally experienced events, bound
to their time, place, and context (Tulving, 1972). Distinct from *semantic*
memory (facts) and *working* memory (transient online maintenance).

**Retrieval** — the process of accessing and reconstructing a stored memory.
Contrasted with *encoding* (forming the memory). This meta-analysis targets
retrieval-phase activation.

**Recollection vs. familiarity (dual-process theory)** — recollection is
detailed, context-rich re-experiencing (associated with hippocampus and
posterior parietal cortex); familiarity is a context-free sense of prior
occurrence (associated with perirhinal cortex). The subtraction/conjunction
analysis probes this distinction.

**Core recollection network** — the set of regions reliably engaged by
successful episodic retrieval: hippocampus / medial temporal lobe, precuneus /
posterior cingulate / retrosplenial cortex, lateral (inferior) parietal cortex
including the angular gyrus, and medial prefrontal cortex. Overlaps substantially
with the **default mode network**.

**Autobiographical memory** — episodic memory for one's own life events; a
retrieval sub-type emphasised in the recall group of the contrast.

**Reverse inference** — inferring a cognitive process from an observed activation
pattern (e.g., "this region is active, therefore memory is engaged"). Risky when
done informally; functional decoding quantifies it against a large database.

## Neuroimaging & spaces

**fMRI / BOLD** — functional MRI measuring the blood-oxygen-level-dependent
signal as a proxy for neural activity.

**Stereotactic space (MNI / Talairach)** — standardised 3-D coordinate systems
that let peaks from different brains/studies be compared. Mixing spaces without
conversion invalidates a meta-analysis; databases here are harmonised to MNI152.

**Focus / peak coordinate** — an (x, y, z) location of a local maximum of a
significant activation cluster, as reported in a paper. The atomic unit of CBMA.

**Voxel** — a 3-D pixel; the unit of an fMRI volume (here 2 mm isotropic).

## Meta-analytic methods

**Coordinate-based meta-analysis (CBMA)** — meta-analysis using reported peak
coordinates rather than full statistical images (which are rarely shared).

**ALE (Activation Likelihood Estimation)** — the CBMA method used here; models
foci as sample-size-weighted 3-D Gaussians and finds voxels of above-chance
spatial convergence. See `METHODS.md §1`.

**Modeled Activation (MA) map** — a single study's foci rendered as Gaussian
probability blobs; the building block of the ALE statistic.

**Null distribution / permutation** — the distribution of the statistic expected
under "no convergence", built by randomly relocating foci; observed values are
significant if they exceed it.

**Family-wise error (FWE)** — the probability of ≥1 false positive across all
voxels/clusters. **Cluster-level FWE** corrects on cluster extent and is the ALE
standard. See `METHODS.md §2`.

**Cluster-forming threshold** — the voxel-level p (here 0.001) used to define
candidate clusters before extent-based correction.

**PRISMA** — Preferred Reporting Items for Systematic reviews and Meta-Analyses;
the standard flow diagram documenting study selection.

**Jackknife** — leave-one-out resampling used here to measure each experiment's
influence on each cluster.

**Fail-Safe N / file-drawer problem** — the concern that unpublished null results
sit in researchers' "file drawers", biasing meta-analyses; Fail-Safe N estimates
how many such studies would overturn a result. We implement a coordinate-based
analog.

**MACM (Meta-Analytic Coactivation Modeling)** — estimating a region's
task-independent co-activation network from the coordinate database.

**Functional decoding** — inferring the cognitive terms associated with a region
by correlating activation with term loadings across a database (quantified
reverse inference).

**Subtraction / conjunction** — contrasts identifying where two conditions
*differ* (subtraction) or *both* converge (conjunction, minimum-statistic).

## Software

**NiMARE** — Neuroimaging Meta-Analysis Research Environment; the Python library
implementing ALE, correction, diagnostics, MACM, and decoding used throughout.

**Neurosynth / NeuroQuery** — large databases of automatically extracted fMRI
coordinates and text features; the data sources here.

**Nilearn** — neuroimaging plotting/masking library used for figures and atlases.

**GingerALE** — the classic point-and-click ALE tool named in the original brief;
this project reproduces and extends its analysis programmatically.
