# Project Direction & Next Steps

*Last updated: July 17, 2026*

## What this project is

> A pipeline that continuously collects Black media coverage, tags it against 12
> social-conflict topics, and — uniquely — comes with a human-validated benchmark
> proving how well the tagging works.

Everything we keep serves that sentence. Everything else is scope creep.

---

## Current state (July 2026)

- **Pipeline:** 4 stages (scrape → analyze → report → upload), 10 publications, runs monthly.
- **Evaluation done:** 5 methods compared against 400 human-labeled articles
  (Annotator 1 + Annotator 3, 200 each). Best method: **Hybrid Soft Boost**
  (pooled macro F1 0.336, Kappa 0.297). Full results: `evaluation/results/hybrid_vs_human.txt`.
- **Report for PI:** `evaluation/results/SOFT_BOOST_EVALUATION_REPORT.pdf`.
- **Paper draft:** `paper/bridging_the_data_gap.tex` (currently AIware format).

## The lean plan — three moves, in order

### 1. Finish the evaluation's integrity  ← IN PROGRESS
- [x] **Adeniyi:** label the two relabeling sheets — DONE July 19
  (`evaluation/annotation/iaa/adeniyi_set1_LABELED.xlsx`, `adeniyi_set3_LABELED.xlsx`)
- [x] **Claude:** compute inter-annotator agreement — DONE July 19
  (`evaluation/results/iaa_report.txt`). **Human ceiling: macro Kappa 0.327 (set 1),
  0.384 (set 3); pooled Kappa 0.410 / 0.531.** Soft Boost machine Kappa (0.297–0.363)
  is at or near the human-human level — key reframing for the paper.
- [x] **Claude:** fix the threshold-tuning leak — DONE July 19. Added "Hybrid Soft Boost (CV)"
  (thresholds tuned on the other annotator's set). **Honest pooled result: F1 0.267,
  Kappa 0.224** — vs 0.336/0.297 in-sample. The leak accounted for most of Soft Boost's
  apparent advantage; the leak-free hybrid is statistically tied with the semantic
  baseline (0.266/0.225). Report the in-sample figure only as an upper bound.
  Note: cross-annotator CV is a harsh test (annotators themselves only agree at
  κ 0.33–0.38, so threshold transfer suffers annotator shift, not just overfitting).
  This strengthens the motivation for move 2 (supervised classifier).

### 2. One model change — supervised classifier
- [x] Train per-topic logistic regression on sentence embeddings using the 400 labels —
  DONE July 19 (`evaluation/taggers/supervised_tagger.py`).
- [x] Evaluate with the same leak-free cross-annotator protocol as Soft Boost (CV).
  **Result: Supervised (CV) macro F1 0.322, Kappa 0.297 — best method, +21% relative F1
  over the next best honest method.** Its Kappa (0.297) sits at ~77–90% of the human
  ceiling (IAA macro κ 0.327–0.384). Results: `evaluation/results/supervised_vs_human.txt`.
- [ ] **PI decision:** adopt as the single production tagger (train on all 400 labels,
  integrate into `analysis/`); OR/AND retire into the paper's evaluation section.

### 3. Freeze and lock
- [ ] Freeze the 400-article gold set as a versioned benchmark.
- [ ] Add a CI job (GitHub Actions) that runs the tagger against the gold set on every PR
  and reports macro F1 — so `analysis/topics.py` edits can never silently regress quality.

## Decisions needed from PI

- [ ] **Venue:** AAAI-27 AISI special track vs AIware 2026 — cannot submit to both.
  AISI deadlines: **abstract July 21**, full paper July 28, code/supplementary July 31, 2026.
- [ ] Sign-off on the lean plan (retire OR/AND, supervised classifier as headline
  method if it wins).

## AAAI-27 AISI positioning (if chosen)

Keywords: *Social Welfare, Justice, Fairness & Equality* (primary);
*Computational Social Science and Humanities*. Each action maps to a review criterion:

1. Fix threshold leak → **Soundness**
2. Audit mainstream corpora (C4, Common Crawl) for absence of our 10 publications;
   open the paper with that evidence → **Significance of the problem**
3. Add non-CS literature (Black press scholarship, media representation, data equity)
   → **Engagement with literature**
4. Make the evaluation the technical core; per-topic calibrated tagging as a
   transferable recipe for low-resource community media → **Significance to AI community**
5. Release code + dataset as URLs/metadata/annotations incl. the 400 human labels
   (not full text — copyright-aware) → **Facilitation of follow-up work**
6. Document the live monthly deployment → **Scope and promise for social impact**

## Explicitly NOT doing (deferred — cite as future work)

- No LLM tagging arm
- No database migration (CSVs are fine at this scale)
- No embedding model upgrade / chunking / spaCy matcher rewrite
- No new annotation rounds before the deadline (rare-topic gap gets reported honestly)
- No new topics, no new publications — taxonomy frozen at 12, sources at 10

## Known limitations to report honestly

1. Threshold tuning leak (being fixed — move 1)
2. No inter-annotator agreement yet (being fixed — move 1)
3. Annotator inconsistency: keyword F1 0.313 (Ann. 1) vs 0.115 (Ann. 3)
4. Anchoring risk: original sheets were pre-filled with pipeline predictions
5. Rare topics (Reparations, Redlining, Surveillance) have 0–5 positive labels — unmeasurable
