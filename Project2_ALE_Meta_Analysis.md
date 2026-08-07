# Project 2: Coordinate-Based (ALE) Meta-Analysis of a Cognitive Process

## Owner
Tanisha Handoo — B.Sc. Neurosciences and Neuropsychology, Amity University
Purpose: this project is intended to be the "neuropsychology/cognitive" complement to Project 1 (EEG classification). It requires no participant recruitment, no lab access, and demonstrates a distinct research skillset — quantitative synthesis of the published fMRI literature — that is well-regarded in cognitive neuroscience and highly relevant for MS applications abroad.

## Goal
Conduct a coordinate-based Activation Likelihood Estimation (ALE) meta-analysis synthesizing peer-reviewed fMRI studies on a single, focused cognitive process, to identify where activation reliably converges across the literature. This mirrors real meta-analytic imaging work done in academic labs (e.g., at Stanford, Harvard-affiliated institutes) and produces a genuine quantitative research output.

## Decision needed first: pick ONE cognitive process (narrow scope, do not go broad)

Recommended candidates, in order of tractability for a first meta-analysis:

1. **Cognitive control / conflict monitoring** — convergence across Stroop, Flanker, and Simon task fMRI studies. Well-studied, large literature, likely to hit target study count easily. Good pairing with Project 1 if Option B (cognitive load) framing was chosen there.
2. **Episodic memory retrieval** — convergence across studies of successful recall/recognition vs. baseline. Large, mature literature.
3. **Emotion regulation** (e.g., cognitive reappraisal) — smaller but very active literature, good if the owner wants a more affective/clinical angle.

**Recommendation to Cowork:** Default to Cognitive control/conflict monitoring unless the owner specifies otherwise — it has the deepest study pool, making it easiest to reach a statistically adequate sample size, and it pairs thematically well if Project 1 used the cognitive-load framing (both probe cognitive control, just via different methods — EEG vs. fMRI meta-synthesis).

## Tools and environment
- **GingerALE** (free software, BrainMap project) — for running the ALE algorithm and cluster-level FWE correction
- Reference manager (Zotero or Mendeley, free) — for organizing included/excluded studies and citations
- Excel/Google Sheets or a simple database — for tracking study screening (PRISMA flow) and coordinate extraction
- Mango or MRIcroGL (free) — for visualizing resulting ALE maps on a brain template
- PubMed, Google Scholar, Web of Science (if accessible) — for literature search

## Step-by-step plan (~5-6 weeks)

### Week 1 — Define question and search strategy
- Finalize the specific cognitive process and precise inclusion criteria:
  - Must report whole-brain fMRI results (not ROI-only)
  - Must report coordinates in a standard stereotactic space (Talairach or MNI)
  - Healthy adult participants (exclude patient/clinical samples unless the meta-analysis is specifically about a clinical population)
  - Task type must match the defined construct (e.g., only conflict-monitoring paradigms: Stroop, Flanker, Simon — not tangentially related tasks)
  - Set a target: aim for 15-25+ included experiments; fewer than ~15-17 experiments is generally considered underpowered for ALE
- Draft and document the search string (e.g., for PubMed: `("Stroop" OR "flanker" OR "Simon task") AND ("fMRI" OR "functional magnetic resonance imaging") AND ("healthy" OR "controls")`)
- Deliverable: 1-page protocol document (question, inclusion/exclusion criteria, search strategy) — this doubles as the methods section skeleton later

### Week 2 — Study screening
- Run the search, export results, deduplicate
- Screen title/abstract, then full text, against inclusion criteria
- Build a PRISMA flow diagram (records identified → screened → excluded with reasons → included)
- Deliverable: PRISMA diagram, final list of included studies with citations

### Week 3 — Coordinate extraction
- For each included study, extract: peak activation coordinates (x,y,z), coordinate space (Talairach or MNI — note if conversion is needed, GingerALE can standardize this), sample size (critical — ALE weights by sample size), contrast used
- Build a structured spreadsheet: one row per coordinate, columns for study ID, coordinate space, x/y/z, sample size
- Format into GingerALE-compatible text file(s) (one file per study, per GingerALE's required format — study name, coordinate space header, then coordinate list)

### Week 4 — Run the ALE analysis
- Import all study files into GingerALE
- Run the ALE algorithm to generate a modeled activation (MA) map per study, then the pooled ALE statistical map
- Apply appropriate multiple-comparisons correction (cluster-level family-wise error correction is standard; note the threshold used, e.g., cluster-forming p < 0.001, FWE p < 0.05)
- Export resulting significant clusters (region labels, peak coordinates, cluster size)

### Week 5 — Interpretation and write-up
- Label resulting clusters anatomically (using an atlas, e.g., via Mango/MRIcroGL or an automated labeling tool)
- Compare convergent regions against existing theoretical models of the cognitive process (e.g., for cognitive control: dorsolateral prefrontal cortex, anterior cingulate cortex — does the result replicate or complicate the standard model?)
- Write up: Introduction (why this question matters, brief literature background) → Methods (PRISMA search, inclusion criteria, ALE methodology, correction method) → Results (PRISMA diagram, ALE map figure, table of significant clusters) → Discussion (interpretation, relation to theory, limitations — publication bias, coordinate reporting inconsistencies, task heterogeneity)
- Target length: 8-12 pages

### Week 6 (buffer)
- Polish figures (brain renderings of ALE clusters are a strong visual asset — prioritize getting at least one clean, presentable brain map image)
- Prepare 1-page plain-language summary
- Evaluate whether the final product is strong enough to submit to an undergraduate research journal (e.g., Journal of Emerging Investigators, Impulse, JYI) — if yes, check specific submission formatting requirements

## Deliverables checklist
- [ ] 1-page protocol document (question, inclusion criteria, search strategy)
- [ ] PRISMA flow diagram
- [ ] Structured coordinate spreadsheet with full study citations
- [ ] GingerALE output (ALE maps, cluster table)
- [ ] Written report (8-12 pages) with PRISMA diagram and brain map figures
- [ ] 1-page plain-language summary
- [ ] (Optional) formatted submission draft for an undergraduate research journal

## Resume outcome (target bullet)
"Coordinate-Based (ALE) Meta-Analysis of [Cognitive Control / Episodic Memory / Emotion Regulation] — Conducted a PRISMA-guided systematic search and coordinate-based meta-analysis (GingerALE) synthesizing [N] fMRI studies on [process]; identified convergent activation in [region(s)], contributing quantitative synthesis to existing theoretical models of [process]."

## Notes for Claude Cowork
- Confirm the specific cognitive process with the owner before beginning the literature search — this determines feasibility (study count) more than anything else in the project.
- The coordinate extraction step (Week 3) is the most tedious and error-prone part; double-check coordinate space (Talairach vs. MNI) per study, since mixing these without conversion will produce invalid results. GingerALE has a built-in Talairach-to-MNI (or reverse) conversion option — use it consistently.
- Sample size per study must be recorded accurately, as ALE weights each study's contribution by its sample size.
- If the initial process choice yields too few qualifying studies (<15), broaden the task inclusion criteria slightly (e.g., add a closely related paradigm) before abandoning the topic — document this decision transparently in the methods section, as this is normal meta-analytic practice.
- This project pairs thematically with Project 1; where natural, note the connection between the two projects in any combined portfolio/resume framing (EEG-level findings vs. fMRI meta-analytic findings on related constructs), but they should remain fully independent, standalone project write-ups.
