# ALE Meta-Analysis of Episodic Memory Retrieval — Results

_Generated 2026-08-06 · owner: Tanisha Handoo_

## 1. Data sources & PRISMA accounting

Studies were drawn from multiple public coordinate databases and screened by cognitive term against the construct.

| source     |   identified |   matched_inclusion |   removed_exclusion |   removed_low_foci |   included |
|:-----------|-------------:|--------------------:|--------------------:|-------------------:|-----------:|
| neurosynth |        14371 |                1276 |                 262 |                  0 |        250 |
| neuroquery |        13459 |                4934 |                3551 |                  0 |        250 |
| ALL        |        27830 |                6210 |                3813 |                  0 |        500 |


**Final included experiments (merged, de-duplicated): 434.**


## 2. Convergent activation (ALE + cluster-level FWE)

ALE with an approximate null; cluster-forming p < 0.001, cluster-level FWE p < 0.05, 2000 permutations.

| Cluster ID   |   X |   Y |   Z |   Peak Stat |   Cluster Size (mm3) | Anatomical Label                               |
|:-------------|----:|----:|----:|------------:|---------------------:|:-----------------------------------------------|
| 1            |  32 |  24 |  -4 |    13.846   |                 6360 | Insular Cortex                                 |
| 2            | -24 | -18 | -18 |    13.5472  |                90392 | Left Hippocampus                               |
| 2a           | -28 | -36 | -14 |    12.4302  |                      | Parahippocampal Gyrus, posterior division      |
| 2b           |  -6 | -56 |  24 |    12.3169  |                      | Precuneous Cortex                              |
| 2c           | -36 | -56 |  44 |    11.2051  |                      | Left Cerebral Cortex                           |
| 3            | -32 |  24 |  -4 |    11.9121  |                76168 | Frontal Orbital Cortex                         |
| 3a           | -46 |  22 |  24 |    11.7064  |                      | Left Cerebral Cortex                           |
| 3b           |  -4 |  16 |  48 |    11.2876  |                      | Paracingulate Gyrus                            |
| 3c           | -44 |   8 |  30 |    10.7417  |                      | Precentral Gyrus                               |
| 4            |  24 | -10 | -20 |    11.4571  |                19984 | Right Hippocampus                              |
| 4a           |  26 | -24 | -16 |    10.6785  |                      | Right Hippocampus                              |
| 4b           |  30 | -40 | -12 |     7.432   |                      | Temporal Occipital Fusiform Cortex             |
| 4c           |  52 | -56 | -12 |     4.99774 |                      | Inferior Temporal Gyrus, temporooccipital part |
| 5            |  36 | -62 |  44 |     7.28951 |                15896 | Lateral Occipital Cortex, superior division    |
| 5a           |  44 | -64 |  26 |     7.1482  |                      | Lateral Occipital Cortex, superior division    |
| 5b           |  40 | -54 |  44 |     5.93152 |                      | Angular Gyrus                                  |
| 5c           |  46 | -38 |  48 |     5.39291 |                      | Supramarginal Gyrus, posterior division        |
| 6            | -12 |   6 |   8 |     6.2733  |                 6440 | Left Cerebral White Matter                     |
| 6a           |  -4 | -12 |   8 |     6.13123 |                      | Left Thalamus                                  |
| 6b           |  -8 |  12 |  -4 |     5.47826 |                      | Left Accumbens                                 |
| 7            |  48 |  14 |  30 |     6.11243 |                 6968 | Inferior Frontal Gyrus, pars opercularis       |
| 7a           |  48 |  30 |  20 |     4.67023 |                      | Middle Frontal Gyrus                           |
| 7b           |  50 |  28 |  28 |     4.54934 |                      | Middle Frontal Gyrus                           |
| 7c           |  44 |  38 |  26 |     4.01849 |                      | Frontal Pole                                   |


## 3. Functional decoding (reverse inference)

Cognitive terms most associated with the convergent region across the full database.

| term             |         r |
|:-----------------|----------:|
| retrieval        | 0.140524  |
| memory           | 0.138504  |
| episodic         | 0.117593  |
| task             | 0.104638  |
| network          | 0.103196  |
| processes        | 0.101334  |
| memory retrieval | 0.0942753 |
| engaged          | 0.0921066 |
| tasks            | 0.0887919 |
| encoding         | 0.0887356 |
| prefrontal       | 0.0872672 |
| semantic         | 0.085599  |
| medial           | 0.0836349 |
| episodic memory  | 0.0827828 |
| networks         | 0.0808637 |
| autobiographical | 0.0772415 |
| hippocampus      | 0.076884  |
| medial temporal  | 0.0750148 |
| parietal         | 0.0741212 |
| frontal          | 0.0696234 |


## 4. Robustness diagnostics

Per-cluster stability. **n experiments (focus)** = independent experiments reporting a focus in the cluster (more = more robust). **max single-study influence** = the largest leave-one-out jackknife contribution of any one experiment (lower = less dependent on a single study).

| cluster        |   n experiments (focus) |   max single-study influence | region                                      |
|:---------------|------------------------:|-----------------------------:|:--------------------------------------------|
| PositiveTail 1 |                     393 |                        0.013 | Left Cerebral White Matter                  |
| PositiveTail 2 |                     365 |                        0.01  | Middle Frontal Gyrus                        |
| PositiveTail 3 |                     249 |                        0.019 | Right Hippocampus                           |
| PositiveTail 4 |                     203 |                        0.013 | Lateral Occipital Cortex, superior division |
| PositiveTail 5 |                     117 |                        0.018 | Middle Frontal Gyrus                        |
| PositiveTail 6 |                     104 |                        0.028 | Left Thalamus                               |
| PositiveTail 7 |                     123 |                        0.017 | Frontal Orbital Cortex                      |


**File-drawer robustness** — surviving clusters as synthetic null experiments are injected:

|   noise_added |   n_clusters |
|--------------:|-------------:|
|             0 |           24 |
|            15 |           24 |
|            30 |           20 |


## 5. Meta-analytic coactivation modeling (MACM)

Seed at strongest ALE peak (32.0, 24.0, -4.0); 60 coactivating studies. See `results/figures/macm_glass_brain.png`.


## 6. Sub-construct contrast (subtraction & conjunction)

Dual-process test: **recognition** (133 exps) vs **recall** (86 exps). Subtraction maps are voxelwise-thresholded (not cluster-FWE); interpret directionally.


**Where recognition > recall** (top clusters):

|   X |   Y |   Z |   Cluster Size (mm3) | Anatomical Label                            |
|----:|----:|----:|---------------------:|:--------------------------------------------|
| -20 | -46 |  66 |                 8344 | Postcentral Gyrus                           |
|  36 | -30 |  58 |                 7432 | Postcentral Gyrus                           |
| -38 | -58 |  50 |                 5728 | Left Cerebral Cortex                        |
| -26 | -34 |   0 |                 2944 | Left Cerebral White Matter                  |
| -36 | -54 | -40 |                 2704 | Unlabelled / white matter                   |
|  40 | -62 |  54 |                 2696 | Lateral Occipital Cortex, superior division |
| -30 |  22 |  -4 |                 2160 | Insular Cortex                              |
|  10 |   8 |  -4 |                 1960 | Right Cerebral White Matter                 |
| -22 |  -8 |  70 |                 1664 | Superior Frontal Gyrus                      |
|   2 | -98 | -10 |                 1568 | Occipital Pole (near peak)                  |


**Where recall > recognition** (top clusters):

|   X |   Y |   Z |   Cluster Size (mm3) | Anatomical Label                            |
|----:|----:|----:|---------------------:|:--------------------------------------------|
|   6 | -58 | -44 |                26600 | Unlabelled / white matter                   |
| -58 |  -8 | -14 |                 9888 | Middle Temporal Gyrus, anterior division    |
|  62 | -12 |   0 |                 7072 | Right Cerebral White Matter                 |
| -16 |  44 | -20 |                 5552 | Frontal Pole                                |
|  24 | -74 | -28 |                 4968 | Unlabelled / white matter                   |
|  52 | -64 |  28 |                 3688 | Lateral Occipital Cortex, superior division |
| -20 |  14 |  60 |                 2176 | Superior Frontal Gyrus                      |
| -56 | -62 |  24 |                 2152 | Lateral Occipital Cortex, superior division |
| -30 | -68 | -24 |                 1648 | Left Cerebral Cortex (near peak)            |
|  42 | -58 | -28 |                 1544 | Right Cerebral Cortex (near peak)           |


**Shared retrieval core** (recognition ∧ recall conjunction, 3234 voxels):

|   X |   Y |   Z |   Cluster Size (mm3) | Anatomical Label                            |
|----:|----:|----:|---------------------:|:--------------------------------------------|
| -26 | -24 | -16 |                 7376 | Left Hippocampus                            |
|  -6 | -58 |  24 |                 4456 | Precuneous Cortex                           |
|  26 | -22 | -18 |                 3784 | Right Hippocampus                           |
| -46 |  16 |  26 |                 3672 | Inferior Frontal Gyrus, pars opercularis    |
| -46 | -68 |  32 |                 2640 | Lateral Occipital Cortex, superior division |
|  -4 |  52 |   2 |                 2368 | Paracingulate Gyrus                         |
|  -2 |  12 |  50 |                  872 | Paracingulate Gyrus                         |
| -44 |  22 |   0 |                  352 | Frontal Opercular Cortex                    |
|  40 | -70 |  36 |                  248 | Lateral Occipital Cortex, superior division |


## 7. Limitations

- Term-based selection from automated databases is broader and noisier than hand-screened full-text inclusion; treat this as a high-throughput complement to a manual PRISMA review, not a replacement.
- Coordinate reporting inconsistencies and publication bias affect all CBMA; robustness can be probed with the optional file-drawer screen (config `diagnostics.fail_safe_n`).
- ALE kernels use a fixed nominal sample size because automated databases do not report per-study n, so studies are not sample-size-weighted as in a classic hand-extracted ALE.
- Neurosynth/NeuroQuery coordinates are extracted automatically and may include non-activation or contrast-ambiguous foci.
