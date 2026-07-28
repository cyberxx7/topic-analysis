# Paper Outline — AAAI-27 AISI Special Track

**Title (working):** Bridging the Data Gap: A Human-Validated Pipeline for
Culturally Aligned Topic Detection in Black Media

**Format:** AAAI two-column, 7 content pages + 2 reference pages, double-blind.
**Deadline:** full paper July 28–29, 2026. Code/supplementary July 31.

**Storyline:** "We propose and validate a practical, incrementally improved
pipeline for culturally aligned topic detection in minority media."

---

## 1. Introduction (~1 page)

- The data gap: Black media publications are systematically absent from
  mainstream corpora (C4, Common Crawl) → structural blind spots in LLMs.
- Prior work (AIware submission) built collection infrastructure; reviewers
  asked: *are the labels any good?* This paper answers that.
- Contributions:
  1. Extended 10-publication pipeline (rolling monthly horizon, ~1,200 articles/cycle)
  2. 400-article human-annotated benchmark + inter-annotator agreement analysis
  3. Leak-free comparative evaluation of six tagging methods
  4. Validated supervised classifier adopted as the production tagger

## 2. Related Work (~0.75 page)

- Community/minority media in NLP; data equity; Black press scholarship
  (**Dr. Johnson to suggest citations**)
- Topic detection: keyword, embedding, hybrid, supervised
- IAA in subjective annotation tasks (contextualize κ 0.33–0.38)

## 3. Pipeline Overview (~0.75 page)

- Brief: 4 stages (scrape → analyze → report → deliver), 10 publications,
  GitHub Actions automation. Cite prior paper, keep short.
- **Table 1:** 12-topic social-conflict taxonomy
- **Figure 1:** pipeline architecture diagram (4 stages, updated with
  supervised classifier in the analyze stage)

## 4. Human Annotation & Agreement (~1 page)

- Protocol: 2 annotators × 200 articles, 12 topics
- Expert re-labeling → IAA: macro κ 0.33 / 0.38, pooled κ 0.41 / 0.53
- Positioning (per PI meeting): manual annotation = **baseline standard, not
  perfect ground truth**. Explain κ honestly:
  - topic sparsity (some topics near-zero positives)
  - scraped feed dominated by sports/entertainment outside the 12 topics
  - platform miscategorization (policing stories under generic "politics")
- Moderate agreement is a *finding about the task*, not a flaw.
- **Figure 2:** per-topic IAA bar chart (grayscale, both sets)
- **Table 2 (or merged into Fig 2):** per-set macro + pooled κ

## 5. Tagging Methods (~1 page)

- 5.1 Keyword tagger (seed phrases) — brief
- 5.2 Semantic tagger (embedding cosine similarity) — brief
- 5.3 Hybrid: OR, AND, Soft Boost (per-topic calibrated thresholds)
- 5.4 **Supervised classifier (emphasis):** per-topic logistic regression on
  sentence embeddings + keyword binary + semantic score; sparse-topic fallback

## 6. Evaluation (~1.5 pages)

- Cross-annotator validation protocol; explicit account of the
  threshold-tuning leak and fix (transparency as strength)
- **Table 3 (main results):** 6 methods × Macro F1 / κ, in-sample vs CV
- **Figure 3:** method comparison bar chart with human-ceiling line overlaid
  (the money figure: classifier at 77–91% of human baseline)
- **Figure 4 (optional / space permitting):** per-topic F1 heatmap,
  measurable vs unmeasurable topics
- Headline: Supervised (CV) F1 0.322 / κ 0.297

## 7. Limitations & Discussion (~0.75 page)

- Modest κ; rare-topic sparsity; anchoring risk (sheets pre-filled with
  pipeline predictions); two annotators; no downstream LLM experiment yet
- Scale-vs-validity tension: kept full scale, report honestly rather than
  filtering to inflate metrics

## 8. Conclusion & Future Work (~0.25 page)

- Foundational, incrementally validated pipeline — not a finished
  large-scale system
- Future: complete annotation across all datasets, stricter subtopic
  filtering, downstream cultural-alignment experiments
- Release: code, taxonomy, annotation metadata (not full text — copyright)

---

## Figures & tables summary (all grayscale, generated from one script)

| # | Type | Content | Section |
|---|------|---------|---------|
| Fig 1 | diagram | pipeline architecture (4 stages) | 3 |
| Tab 1 | table | 12-topic taxonomy | 3 |
| Fig 2 | bar chart | per-topic IAA κ, both sets | 4 |
| Tab 3 | table | main results: 6 methods, F1/κ, in-sample vs CV | 6 |
| Fig 3 | bar chart | method comparison + human-ceiling line | 6 |
| Fig 4 | heatmap | per-topic F1 (optional) | 6 |

Plan: one script `paper/figures/make_figures.py` regenerates every figure
from the CSVs in `evaluation/results/` — reproducible, and the script ships
with the code release.
