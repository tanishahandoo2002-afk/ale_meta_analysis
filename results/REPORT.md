# ALE Meta-Analysis of Episodic Memory Retrieval — Results

_Generated 2026-07-27 · owner: Tanisha Handoo_

## 1. Data sources & PRISMA accounting

Studies were drawn from multiple public coordinate databases and screened by cognitive term against the construct.

| source     |   identified |   matched_inclusion |   removed_exclusion |   removed_low_foci |   included |
|:-----------|-------------:|--------------------:|--------------------:|-------------------:|-----------:|
| neurosynth |        14371 |                1276 |                 262 |                  0 |        100 |
| neuroquery |        13459 |                4934 |                3551 |                  0 |        100 |
| ALL        |        27830 |                6210 |                3813 |                  0 |        200 |


**Final included experiments (merged, de-duplicated): 171.**


## 2. Convergent activation (ALE + cluster-level FWE)

ALE with an approximate null; cluster-forming p < 0.001, cluster-level FWE p < 0.05, 500 permutations.

|   Cluster ID |   X |   Y |   Z |   Peak Stat |   Cluster Size (mm3) | Anatomical Label                            |
|-------------:|----:|----:|----:|------------:|---------------------:|:--------------------------------------------|
|            1 | -14 | -62 |  28 |     2.87816 |                39480 | Precuneous Cortex                           |
|            2 | -40 |  22 |  18 |     2.87816 |                28464 | Left Cerebral White Matter                  |
|            3 | -26 | -24 | -14 |     2.87816 |                15288 | Left Hippocampus                            |
|            4 | -10 |  -2 |   6 |     2.87816 |                 4752 | Left Thalamus                               |
|            5 |  -4 |  36 |  32 |     2.87816 |                16200 | Paracingulate Gyrus                         |
|            6 |  26 | -22 | -16 |     2.87816 |                10608 | Right Hippocampus                           |
|            7 |  42 | -66 |  34 |     2.87816 |                 7504 | Lateral Occipital Cortex, superior division |


## 3. Functional decoding (reverse inference)

Cognitive terms most associated with the convergent region across the full database.

| term             |         r |
|:-----------------|----------:|
| retrieval        | 0.158741  |
| memory           | 0.1522    |
| episodic         | 0.14199   |
| memory retrieval | 0.111351  |
| network          | 0.10936   |
| medial           | 0.104183  |
| hippocampus      | 0.102885  |
| autobiographical | 0.101111  |
| episodic memory  | 0.100916  |
| processes        | 0.099062  |
| encoding         | 0.0924732 |
| medial temporal  | 0.0908953 |
| networks         | 0.0906323 |
| engaged          | 0.0891083 |
| semantic         | 0.0879703 |
| prefrontal       | 0.0879353 |
| task             | 0.0867402 |
| default          | 0.0821121 |
| recollection     | 0.0781733 |
| memories         | 0.0745964 |


## 4. Robustness diagnostics

Per-cluster stability. **n experiments (focus)** = independent experiments reporting a focus in the cluster (more = more robust). **max single-study influence** = the largest leave-one-out jackknife contribution of any one experiment (lower = less dependent on a single study).

| cluster         |   n experiments (focus) |   max single-study influence | region                                      |
|:----------------|------------------------:|-----------------------------:|:--------------------------------------------|
| PositiveTail 1  |                     136 |                        0.04  | Precuneous Cortex                           |
| PositiveTail 2  |                     131 |                        0.025 | Left Cerebral White Matter                  |
| PositiveTail 3  |                     105 |                        0.02  | Left Hippocampus                            |
| PositiveTail 4  |                      53 |                        0.057 | Left Thalamus                               |
| PositiveTail 5  |                     110 |                        0.036 | Paracingulate Gyrus                         |
| PositiveTail 6  |                      90 |                        0.03  | Right Hippocampus                           |
| PositiveTail 7  |                      78 |                        0.03  | Lateral Occipital Cortex, superior division |
| PositiveTail 8  |                      36 |                        0.038 | Insular Cortex                              |
| PositiveTail 9  |                      28 |                        0.07  | Middle Temporal Gyrus, posterior division   |
| PositiveTail 10 |                      30 |                        0.046 | Right Caudate                               |
| PositiveTail 11 |                      29 |                        0.048 | Middle Temporal Gyrus, anterior division    |


**File-drawer robustness** — surviving clusters as synthetic null experiments are injected:

|   noise_added |   n_clusters |
|--------------:|-------------:|
|             0 |            9 |
|            15 |            7 |
|            30 |            6 |


## 5. Meta-analytic coactivation modeling (MACM)

Seed at strongest ALE peak (-14.0, -62.0, 28.0); 60 coactivating studies. See `results/figures/macm_glass_brain.png`.


## 6. Sub-construct contrast (subtraction & conjunction)

Dual-process test: **recognition** (60 exps) vs **recall** (28 exps). Subtraction maps are voxelwise-thresholded (not cluster-FWE); interpret directionally.


**Where recognition > recall** (top clusters):

|   X |   Y |   Z |   Cluster Size (mm3) | Anatomical Label                               |
|----:|----:|----:|---------------------:|:-----------------------------------------------|
| -40 | -58 |  56 |                 8480 | Lateral Occipital Cortex, superior division    |
|  20 | -32 |  76 |                 6544 | Postcentral Gyrus                              |
|  18 |   0 |  38 |                 2072 | Right Cerebral White Matter                    |
|  40 | -50 |  38 |                 1992 | Angular Gyrus                                  |
|  44 |  30 |  30 |                 1952 | Middle Frontal Gyrus                           |
| -26 |  32 |   4 |                 1432 | Left Cerebral White Matter                     |
|   0 | -92 | -12 |                  960 | Occipital Pole                                 |
| -60 | -54 | -20 |                  864 | Inferior Temporal Gyrus, temporooccipital part |
|  36 | -20 | -12 |                  544 | Right Hippocampus                              |
| -12 | -36 |  16 |                  448 | Left Cerebral White Matter                     |


**Where recall > recognition** (top clusters):

|   X |   Y |   Z |   Cluster Size (mm3) | Anatomical Label                            |
|----:|----:|----:|---------------------:|:--------------------------------------------|
| -36 | -44 |  -6 |                30464 | Left Cerebral White Matter                  |
| -16 |  44 |  10 |                15960 | Left Cerebral White Matter                  |
| -50 |  16 |  26 |                12432 | Inferior Frontal Gyrus, pars opercularis    |
|   4 | -58 |  12 |                11640 | Precuneous Cortex                           |
|  70 | -16 | -12 |                10704 | Middle Temporal Gyrus, posterior division   |
|  26 |  30 |  54 |                 6304 | Superior Frontal Gyrus                      |
|  48 | -64 | -34 |                 5816 | Unlabelled / white matter                   |
|  52 | -66 |  26 |                 5816 | Lateral Occipital Cortex, superior division |
| -34 | -70 | -28 |                 5696 | Unlabelled / white matter                   |
| -18 | -16 |  20 |                 5688 | Left Cerebral White Matter                  |


**Shared retrieval core** (recognition ∧ recall conjunction, 802 voxels):

|   X |   Y |   Z |   Cluster Size (mm3) | Anatomical Label                            |
|----:|----:|----:|---------------------:|:--------------------------------------------|
| -26 | -26 | -16 |                 2968 | Left Hippocampus                            |
|  -6 | -56 |  20 |                 1616 | Precuneous Cortex                           |
|  26 | -24 | -18 |                  832 | Right Cerebral White Matter                 |
| -48 | -66 |  30 |                  752 | Lateral Occipital Cortex, superior division |
| -48 |  24 |  24 |                  192 | Inferior Frontal Gyrus, pars triangularis   |


## 7. Limitations

- Term-based selection from automated databases is broader and noisier than hand-screened full-text inclusion; treat this as a high-throughput complement to a manual PRISMA review, not a replacement.
- Coordinate reporting inconsistencies and publication bias affect all CBMA; robustness can be probed with the optional file-drawer screen (config `diagnostics.fail_safe_n`).
- ALE kernels use a fixed nominal sample size because automated databases do not report per-study n, so studies are not sample-size-weighted as in a classic hand-extracted ALE.
- Neurosynth/NeuroQuery coordinates are extracted automatically and may include non-activation or contrast-ambiguous foci.
