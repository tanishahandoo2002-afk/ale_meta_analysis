# Hand-curated ALE — the rigorous complement

The automated pipeline (Neurosynth + NeuroQuery) is a large-scale, reproducible
synthesis, but it uses text-mined coordinates and a fixed kernel. The
**gold-standard** ALE that neuroscience reviewers most recognise is
**hand-curated**: you read the papers, extract the peak tables and true sample
sizes yourself, and run sample-size-weighted ALE. Doing a small hand-curated
analysis *alongside* the automated one demonstrates both skill sets and
cross-validates the result — the single highest-value addition for a research
profile.

## Workflow (~the Week 1–3 plan from the brief)

1. **Search.** Run the documented search string (see `docs/PROTOCOL.md`) in
   PubMed / Google Scholar. Export and de-duplicate hits.
2. **Screen** title/abstract, then full text, against the inclusion criteria
   (whole-brain fMRI, healthy adults, episodic *retrieval* contrast, coordinates
   in MNI or Talairach). Aim for **20–30 experiments**.
3. **Extract** each included experiment into `data/hand_curated/…_sleuth.txt`
   using `data/hand_curated/TEMPLATE_sleuth.txt` as the format guide: study name,
   `// Subjects=N` (the real sample size), then one `x y z` line per peak.
   - Convert any Talairach coordinates to MNI first (GingerALE and NiMARE both
     offer this; keep it consistent).
   - Record the exact contrast used per experiment (in the study-name line).
4. **Run** it:
   ```bash
   PYTHONPATH=src python scripts/run_hand_curated.py data/hand_curated/YOURFILE_sleuth.txt
   ```
   This runs **sample-size-weighted** ALE with cluster-level FWE, labels the
   clusters, and reports how well the automated large-scale map agrees with your
   hand-curated one. Outputs land in `results/hand_curated/`.

## Why it matters
- Uses **real sample sizes** → proper ALE weighting (the automated databases
  can't provide this).
- Full-text screening removes the noise inherent in text-mined selection.
- Demonstrates the classic systematic-review + meta-analysis skill, and lets you
  state: *"the automated pipeline recovers the hand-curated result"* — a strong,
  defensible claim.

Everything else (PRISMA diagram, figures, dashboard) can be pointed at the
hand-curated dataset with the same code.
