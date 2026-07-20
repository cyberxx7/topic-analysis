# Hybrid Soft Boost Tagger — Evaluation Report

**Project:** Black Media Intelligence Pipeline — Topic Tagging Validation
**Date:** July 13, 2026
**Prepared by:** Ademola Adeniyi

---

## 1. Purpose

Following the suggestion to combine our two existing topic-tagging approaches, we built and evaluated a **hybrid tagger** that merges the keyword (seed-phrase) pipeline with the semantic (sentence-embedding) tagger. This report summarizes the design, results against human annotation, and recommended next steps.

## 2. Evaluation Setup

- **Gold standard:** 400 human-annotated articles (two annotators, 200 articles each, drawn from a stratified 1,000-article sample spanning 10 Black media publications over a 365-day window).
- **Labels:** 12 social conflict topics (multi-label — an article can carry several topics).
- **Metrics:** Macro F1 (primary for retrieval quality) and Cohen's Kappa (chance-corrected agreement), averaged across all 12 topics.

## 3. Methods Compared

| # | Method | Description |
|---|--------|-------------|
| 1 | Keyword Pipeline | Seed-phrase regex matching on title + description + body (production system) |
| 2 | Semantic Tagger | Cosine similarity between article and topic embeddings (all-MiniLM-L6-v2), globally tuned threshold |
| 3 | Hybrid OR | Tag if *either* method fires |
| 4 | Hybrid AND | Tag only if *both* methods agree |
| 5 | **Hybrid Soft Boost** | Keyword match always kept; semantic adds a tag only when its similarity score exceeds a **per-topic threshold** found by grid search (0.05–0.45) |

## 4. Results

### Overall (both annotator sets pooled)

| Method | Macro F1 | Macro Kappa |
|--------|----------|-------------|
| Keyword Pipeline | 0.214 | 0.183 |
| Semantic Tagger | 0.266 | 0.225 |
| Hybrid OR | 0.229 | 0.181 |
| Hybrid AND | 0.259 | 0.244 |
| **Hybrid Soft Boost** | **0.336** | **0.297** |

**The Soft Boost hybrid is the best method on both metrics** — a **+57% relative F1 improvement** over the keyword baseline and **+26%** over the semantic baseline.

### Per annotator

| Method | Ann. 1 F1 | Ann. 1 Kappa | Ann. 3 F1 | Ann. 3 Kappa |
|--------|-----------|--------------|-----------|--------------|
| Keyword Pipeline | 0.313 | 0.282 | 0.115 | 0.083 |
| Semantic Tagger | 0.257 | 0.200 | 0.275 | 0.250 |
| **Hybrid Soft Boost** | **0.411** | **0.363** | 0.261 | 0.231 |

### Why Soft Boost wins

- **Hybrid OR** inflates recall but collapses precision (fires on nearly everything).
- **Hybrid AND** protects precision but collapses recall (rarely fires).
- **Soft Boost** keeps the keyword matcher's precision as an anchor and lets the semantic signal contribute only where it is confident (per-topic calibrated threshold). It improves recall without the precision cost of OR.

### Per-topic view (Soft Boost)

- **Strong topics (adequate human support, n ≥ 13 positives):** Housing (F1 0.58 / 0.48), Economic Equity (0.50 / 0.57), Policing (0.46 / 0.35), Maternal Health (0.50 / 0.40).
- **Weak topics are support-limited, not method-limited:** Reparations (0–5 human positives), Redlining and Surveillance (zero positives in annotator 3's set) score at or near 0 for *every* method. These topics drag the macro average down; with n = 0–5 positives they cannot be meaningfully measured.

## 5. Limitations (known, and addressable)

1. **Threshold tuning leak.** Soft Boost thresholds were grid-searched on the same 200-article sets used for evaluation, so 0.336 is likely somewhat optimistic. Needs a proper tune/test split before publication.
2. **No inter-annotator agreement.** The two annotators labeled disjoint article sets, so we cannot compute a human agreement ceiling to contextualize machine scores.
3. **Annotator inconsistency.** The keyword pipeline scores 3× higher on annotator 1 than annotator 3 (0.313 vs 0.115 F1), suggesting the two annotators applied the guidelines differently.
4. **Anchoring risk.** Annotation sheets were pre-filled with pipeline predictions rather than blank.
5. **Rare-topic support.** Four of twelve topics have too few positive labels to evaluate.

## 6. Recommended Next Steps

**Methodology (highest priority — needed for a defensible paper):**

1. **Cross-annotator threshold validation** — tune Soft Boost thresholds on annotator 1's set, evaluate on annotator 3's (and vice versa). Removes the tuning leak. *(Code change only; no new annotation needed.)*
2. **Shared overlap set for inter-annotator agreement** — have both annotators label the same ~50 articles to establish a human Kappa ceiling. This reframes all results (e.g., "the hybrid reaches X% of human-level agreement").
3. **Targeted annotation round for rare topics** — use semantic similarity scores to oversample candidate Reparations / Redlining / Surveillance articles so each topic reaches ≥15 positives.

**Modeling (potential accuracy gains):**

4. **LLM-based zero-shot tagging** as an additional comparison arm (send article + topic definition to an LLM; likely the largest single accuracy gain, and a natural fit for the AIware venue).
5. **Supervised classifier** — with ~400 labeled articles, logistic regression over sentence embeddings per topic is feasible and often beats threshold-based similarity.
6. **Error analysis** — manually review false positives/negatives per topic to separate tagger errors from annotation errors and refine seed phrases / guidelines.

**Reporting:**

7. Report **support-stratified results** (topics with n ≥ 10 positives vs. n < 5) and bootstrap confidence intervals in the paper, and frame the contribution as dataset/pipeline infrastructure validated by this evaluation.

---

*Full method-by-method, topic-by-topic tables: `evaluation/results/hybrid_vs_human.txt`. Per-article predictions: `evaluation/results/hybrid_vs_human_predictions.csv`. Visual report (16-page PDF): `outputs/annotation-comparison/Final_PDF_Report.pdf`.*
