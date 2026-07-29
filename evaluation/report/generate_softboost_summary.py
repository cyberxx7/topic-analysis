"""
generate_softboost_summary.py — Soft Boost Evaluation Summary (for PI)

A condensed 4-page evaluation memo in a plain academic style:

  Page 1: Title, overview, and description of all five methods
  Page 2: Results table and grayscale bar charts (per annotator + pooled)
  Page 3: Soft Boost F1 per topic, split by annotator, with label support
  Page 4: Limitations and recommended next steps

Usage:
    python3.11 evaluation/report/generate_softboost_summary.py

Output:
    evaluation/results/SOFT_BOOST_EVALUATION_REPORT.pdf
"""

import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

OUT_PATH = "evaluation/results/SOFT_BOOST_EVALUATION_REPORT.pdf"
IN_PATH  = "evaluation/results/hybrid_vs_human.csv"

INK    = "#1B1B1B"   # near-black text
GREY1  = "#3A3A3A"   # dark grey  (Annotator 1 bars)
GREY2  = "#B0B0B0"   # light grey (Annotator 3 bars)
RULE   = "#888888"   # horizontal rules
FAINT  = "#666666"   # secondary text

plt.rcParams.update({
    "font.family":       "DejaVu Serif",
    "font.size":         10,
    "text.color":        INK,
    "axes.edgecolor":    INK,
    "axes.labelcolor":   INK,
    "xtick.color":       INK,
    "ytick.color":       INK,
    "figure.facecolor":  "white",
    "axes.facecolor":    "white",
    "axes.grid":         False,
    "axes.spines.top":   False,
    "axes.spines.right": False,
})

PAGE = (8.5, 11)   # portrait letter

METHOD_ORDER = [
    "Keyword Pipeline",
    "Semantic Tagger",
    "Hybrid OR (Union)",
    "Hybrid AND (Intersect)",
    "Hybrid Soft Boost",
]
METHOD_SHORT = ["Keyword", "Semantic", "Hybrid OR", "Hybrid AND", "Soft Boost"]


# ── Small helpers ─────────────────────────────────────────────────────────────

def rule(fig, y, x0=0.09, x1=0.91, lw=0.8, color=RULE):
    fig.add_artist(plt.Line2D([x0, x1], [y, y], transform=fig.transFigure,
                              color=color, linewidth=lw))


def heading(fig, num, text, y):
    fig.text(0.09, y, f"{num}.  {text}", ha="left", va="top",
             fontsize=12.5, fontweight="bold", color=INK)


def para(fig, text, y, size=9.5, x=0.09, spacing=1.65):
    fig.text(x, y, text, ha="left", va="top", fontsize=size,
             color=INK, linespacing=spacing, wrap=True)


def footer(fig, page_num):
    fig.text(0.5, 0.030,
             f"Hybrid Soft Boost Evaluation — {page_num} of 4",
             ha="center", fontsize=8, color=FAINT)


# ── Page 1: Title, overview, methods ─────────────────────────────────────────

def page_title_methods(pdf):
    fig = plt.figure(figsize=PAGE)

    fig.text(0.09, 0.945, "Evaluation of a Hybrid Topic Tagger",
             ha="left", fontsize=18, fontweight="bold", color=INK)
    fig.text(0.09, 0.915, "Keyword and Semantic Methods Combined, "
             "Validated Against Human Annotation",
             ha="left", fontsize=11, color=FAINT, style="italic")

    fig.text(0.09, 0.885,
             "Black Media Topic Study   ·   Prepared by Research Team   ·   July 13, 2026",
             ha="left", fontsize=9, color=FAINT)
    rule(fig, 0.870)

    heading(fig, 1, "Overview", 0.845)
    para(fig,
         "We evaluated five automated topic-tagging methods against a gold standard of 400 human-annotated\n"
         "articles: 200 labeled by Annotator 1 and 200 labeled by Annotator 3, drawn from a stratified\n"
         "1,000-article sample covering 10 Black media publications over a 365-day window. Each article was\n"
         "labeled for the presence of 12 social conflict topics (multi-label). Performance is reported as macro-\n"
         "averaged F1 and Cohen's Kappa across all 12 topics. The best method, a hybrid we call Soft Boost,\n"
         "reaches a pooled macro F1 of 0.336 and Kappa of 0.297 — a 57% relative F1 improvement over the\n"
         "keyword baseline and 26% over the semantic baseline.",
         0.822)

    heading(fig, 2, "The Two Base Methods", 0.680)
    para(fig,
         "Keyword Pipeline (production system).  Scans each article's title, description, and body text for a\n"
         "curated dictionary of seed phrases per topic (e.g. “police brutality”, “voter suppression”). Transparent\n"
         "and precise, but misses articles that express a topic in different words.\n\n"
         "Semantic Tagger.  Encodes each article and each topic description with a sentence-embedding model\n"
         "(all-MiniLM-L6-v2) and tags the article when the cosine similarity between the two exceeds a threshold.\n"
         "Captures meaning beyond exact wording, but is noisier and threshold-sensitive.",
         0.657)

    heading(fig, 3, "The Three Hybrid Strategies", 0.515)
    para(fig,
         "Hybrid OR (Union).  An article receives a topic tag if either the keyword pipeline or the semantic\n"
         "tagger fires. This maximizes recall — nothing either method finds is lost — but every false positive\n"
         "from both methods is kept as well, so precision drops sharply. In our data, OR raised recall to 0.62\n"
         "(Annotator 1 set) but cut precision to 0.19, leaving F1 no better than the baselines.\n\n"
         "Hybrid AND (Intersection).  An article receives a tag only when both methods independently agree.\n"
         "This is the mirror image of OR: precision improves (0.48 on the Annotator 1 set, the highest of any\n"
         "method) because two independent signals must concur, but recall collapses to 0.28 because the two\n"
         "methods often fire on different articles. Many true positives found by only one method are discarded.\n\n"
         "Hybrid Soft Boost.  The keyword pipeline acts as the anchor: every keyword match is always kept,\n"
         "preserving its precision. The semantic signal is then allowed to add tags — but only when its raw\n"
         "similarity score clears a per-topic threshold, found by grid search over the range 0.05–0.45. Topics\n"
         "where semantic similarity is reliable receive a low threshold (more semantic additions); topics where\n"
         "it is noisy receive a high threshold (few or none). This calibration is what OR lacks: the semantic\n"
         "tagger contributes only where it is demonstrably trustworthy, so recall improves without the\n"
         "precision cost of a blanket union.",
         0.492)

    footer(fig, 1)
    pdf.savefig(fig)
    plt.close()


# ── Page 2: Results ───────────────────────────────────────────────────────────

def page_results(pdf, df):
    fig = plt.figure(figsize=PAGE)

    heading(fig, 4, "Results", 0.945)
    para(fig,
         "The table reports macro-averaged scores per annotator set and pooled across both. Soft Boost is the\n"
         "best method on F1 and Kappa in the pooled results and on the Annotator 1 set; on the Annotator 3 set\n"
         "it is second to the semantic tagger by a small margin (F1 0.261 vs 0.275).",
         0.922)

    # ── Results table (drawn manually) ────────────────────────────────
    col_x   = [0.09, 0.33, 0.415, 0.50, 0.585, 0.685, 0.775]
    headers = ["Method", "Ann. 1\nF1", "Ann. 1\nKappa", "Ann. 3\nF1",
               "Ann. 3\nKappa", "Pooled\nF1", "Pooled\nKappa"]

    top = 0.845
    for x, h in zip(col_x, headers):
        fig.text(x, top, h, ha="left", va="bottom", fontsize=9,
                 fontweight="bold", color=INK, linespacing=1.3)
    rule(fig, top - 0.008, lw=1.2, color=INK)

    row_y = top - 0.032
    for method, short in zip(METHOD_ORDER, METHOD_SHORT):
        sub  = df[df["method"] == method]
        a1   = sub[sub["annotator"] == "annotator_1"]
        a3   = sub[sub["annotator"] == "annotator_3"]
        vals = [a1["f1"].mean(), a1["kappa"].mean(),
                a3["f1"].mean(), a3["kappa"].mean(),
                sub["f1"].mean(), sub["kappa"].mean()]
        bold = method == "Hybrid Soft Boost"
        fw   = "bold" if bold else "normal"
        fig.text(col_x[0], row_y, short, ha="left", fontsize=9.5,
                 fontweight=fw, color=INK)
        for x, v in zip(col_x[1:], vals):
            fig.text(x, row_y, f"{v:.3f}", ha="left", fontsize=9.5,
                     fontweight=fw, color=INK)
        row_y -= 0.026

    rule(fig, row_y + 0.016, lw=1.2, color=INK)
    fig.text(0.09, row_y - 0.002,
             "Bold row: best pooled scores. Each annotator set is 200 articles; pooled figures average both sets.",
             fontsize=8, color=FAINT)

    # ── Bar charts: F1 and Kappa per annotator ────────────────────────
    xpos  = np.arange(len(METHOD_ORDER))
    width = 0.36

    for i, (metric, label) in enumerate([("f1", "Macro F1"), ("kappa", "Macro Kappa")]):
        ax = fig.add_axes([0.10 + i * 0.45, 0.24, 0.36, 0.36])
        v1 = [df[(df["method"] == m) & (df["annotator"] == "annotator_1")][metric].mean()
              for m in METHOD_ORDER]
        v3 = [df[(df["method"] == m) & (df["annotator"] == "annotator_3")][metric].mean()
              for m in METHOD_ORDER]

        ax.bar(xpos - width/2, v1, width, color=GREY1, label="Annotator 1")
        ax.bar(xpos + width/2, v3, width, color=GREY2, edgecolor=GREY1,
               linewidth=0.5, label="Annotator 3")

        for xi, v in zip(xpos - width/2, v1):
            ax.text(xi, v + 0.006, f"{v:.2f}", ha="center", fontsize=6.5, color=INK)
        for xi, v in zip(xpos + width/2, v3):
            ax.text(xi, v + 0.006, f"{v:.2f}", ha="center", fontsize=6.5, color=INK)

        ax.set_xticks(xpos)
        ax.set_xticklabels(METHOD_SHORT, fontsize=7.5, rotation=30, ha="right")
        ax.set_ylim(0, 0.48)
        ax.set_title(label, fontsize=10.5, fontweight="bold", color=INK)
        ax.tick_params(axis="y", labelsize=8)
        if i == 0:
            ax.set_ylabel("Score", fontsize=9)
            ax.legend(fontsize=8, frameon=False, loc="upper left")

    para(fig,
         "Reading the charts: the keyword pipeline performs well on the Annotator 1 set (F1 0.313) but poorly on\n"
         "the Annotator 3 set (F1 0.115) — a gap discussed under Limitations. The semantic tagger is more stable\n"
         "across the two sets. Soft Boost gives the largest improvement where the keyword anchor is strong\n"
         "(Annotator 1: F1 0.411, Kappa 0.363) and remains competitive on the Annotator 3 set.",
         0.175)

    footer(fig, 2)
    pdf.savefig(fig)
    plt.close()


# ── Page 3: Per-topic results ─────────────────────────────────────────────────

def page_topics(pdf, df):
    fig = plt.figure(figsize=PAGE)

    heading(fig, 5, "Soft Boost Performance by Topic", 0.945)
    para(fig,
         "F1 per topic for the Soft Boost method, shown separately for Annotator 1 and Annotator 3, sorted by\n"
         "average F1. The figure above each pair (n) is the number of articles the human annotators marked\n"
         "positive for that topic across both sets — the support available for evaluation.",
         0.922)

    soft   = df[df["method"] == "Hybrid Soft Boost"]
    topics = sorted(soft["topic"].unique(),
                    key=lambda t: -soft[soft["topic"] == t]["f1"].mean())

    f1_1, f1_3, support = [], [], []
    for t in topics:
        r1 = soft[(soft["topic"] == t) & (soft["annotator"] == "annotator_1")]
        r3 = soft[(soft["topic"] == t) & (soft["annotator"] == "annotator_3")]
        f1_1.append(r1["f1"].values[0] if len(r1) else 0.0)
        f1_3.append(r3["f1"].values[0] if len(r3) else 0.0)
        n1 = int(r1["tp"].values[0] + r1["fn"].values[0]) if len(r1) else 0
        n3 = int(r3["tp"].values[0] + r3["fn"].values[0]) if len(r3) else 0
        support.append(n1 + n3)

    ax = fig.add_axes([0.10, 0.42, 0.82, 0.40])
    x = np.arange(len(topics))
    w = 0.38
    ax.bar(x - w/2, f1_1, w, color=GREY1, label="Annotator 1")
    ax.bar(x + w/2, f1_3, w, color=GREY2, edgecolor=GREY1,
           linewidth=0.5, label="Annotator 3")

    for xi, (v1, v3, s) in enumerate(zip(f1_1, f1_3, support)):
        ax.text(xi, max(v1, v3) + 0.02, f"n={s}",
                ha="center", fontsize=7, color=FAINT)

    ax.set_xticks(x)
    ax.set_xticklabels([t.replace("/", " /\n") for t in topics],
                       fontsize=7, rotation=40, ha="right")
    ax.set_ylim(0, 0.72)
    ax.set_ylabel("F1 Score", fontsize=9)
    ax.tick_params(axis="y", labelsize=8)
    ax.legend(fontsize=8.5, frameon=False, loc="upper right")

    heading(fig, "5.1", "Interpretation", 0.325)
    para(fig,
         "Topics with adequate label support score well.  Housing/Displacement (F1 0.58 for Annotator 1,\n"
         "0.48 for Annotator 3), Economic Equity (0.50 / 0.57), Policing (0.46 / 0.35), and Maternal Health\n"
         "(0.50 / 0.40) all have 8 or more positive labels and reach usable performance.\n\n"
         "Weak topics are limited by support, not by the method.  Reparations (n=5), Redlining (n=5), and\n"
         "Anti-Black Surveillance (n=3) have almost no positive labels; Annotator 3's set contains zero positives\n"
         "for Redlining, Surveillance, and Reparations, which is why those bars are absent. Every method —\n"
         "keyword, semantic, and all three hybrids — scores at or near zero on these topics. They pull the macro\n"
         "average down but cannot be meaningfully measured until more positive examples are annotated.",
         0.302)

    footer(fig, 3)
    pdf.savefig(fig)
    plt.close()


# ── Page 4: Limitations and next steps ────────────────────────────────────────

def page_limitations_next(pdf):
    fig = plt.figure(figsize=PAGE)

    heading(fig, 6, "Limitations", 0.945)
    para(fig,
         "1.  Threshold tuning leak.  The Soft Boost per-topic thresholds were grid-searched on the same 200-\n"
         "     article sets used for evaluation. The 0.336 pooled F1 is therefore likely somewhat optimistic and\n"
         "     must be re-estimated with a proper tune/test split before publication.\n\n"
         "2.  No inter-annotator agreement.  Annotator 1 and Annotator 3 labeled disjoint article sets, so we\n"
         "     cannot compute how well two humans agree on this task. Without that ceiling, absolute scores are\n"
         "     hard to interpret: if human–human Kappa is near 0.5 (typical for subjective multi-label news\n"
         "     annotation), a machine Kappa of 0.30 is closer to the ceiling than it appears.\n\n"
         "3.  Annotator inconsistency.  The keyword pipeline scores three times higher against Annotator 1\n"
         "     than against Annotator 3 (F1 0.313 vs 0.115). A gap this large on the same tagger suggests the two\n"
         "     annotators applied the guidelines differently (Annotator 3 marked far fewer positives overall).\n\n"
         "4.  Anchoring risk.  Annotation sheets were pre-filled with pipeline predictions rather than left blank,\n"
         "     which may have biased annotators toward agreeing with the pipeline.\n\n"
         "5.  Rare-topic support.  Four of the twelve topics have 0–5 positive labels and cannot be evaluated.",
         0.920)

    heading(fig, 7, "Recommendations — Positioning for AAAI-27, AISI Special Track", 0.590)

    para(fig,
         "Target venue: the AAAI-27 special track on AI for Social Impact (abstracts due July 21; full papers\n"
         "July 28; code and supplementary material July 31, 2026). Suggested keywords: Social Welfare, Justice,\n"
         "Fairness & Equality (primary); Computational Social Science and Humanities. Each action below\n"
         "addresses one of the track's six review criteria, named in parentheses.",
         0.565)

    para(fig,
         "1.  Fix the threshold leak first (Soundness).  Tune Soft Boost thresholds on Annotator 1's set,\n"
         "     evaluate on Annotator 3's, and vice versa. Final paper numbers depend on this; code change only.\n"
         "2.  Lead with the representation gap (Significance of the problem).  Audit mainstream corpora\n"
         "     (C4, Common Crawl, news aggregators) for the absence of these 10 publications; open with that.\n"
         "3.  Broaden the related work (Engagement with literature).  Add scholarship outside computer\n"
         "     science: the Black press in journalism studies, media representation, and data equity work.\n"
         "4.  Make the evaluation the technical core (Significance to the AI community).  Present per-topic\n"
         "     calibrated Soft Boost as a transferable recipe for low-resource community media domains.\n"
         "5.  Release code and data (Facilitation of follow-up work).  Publish the pipeline and the dataset as\n"
         "     URLs, metadata, and annotations — including the 400 human labels — not full article text.\n"
         "6.  Document deployment (Scope and promise for social impact).  The pipeline already runs monthly\n"
         "     and delivers reports to stakeholders; a short deployment subsection claims this criterion.\n"
         "7.  Decide the venue.  AAAI prohibits concurrent submission of substantially similar work; the\n"
         "     AIware draft must be withdrawn or clearly differentiated before submitting to AISI.",
         0.480,
         size=9)

    rule(fig, 0.105)
    fig.text(0.09, 0.088,
             "Supporting material:  evaluation/results/hybrid_vs_human.txt (full tables);  "
             "hybrid_vs_human_predictions.csv (per-article);\n"
             "outputs/annotation-comparison/Final_PDF_Report.pdf (extended visual comparison).",
             fontsize=8, color=FAINT, linespacing=1.6, va="top")

    footer(fig, 4)
    pdf.savefig(fig)
    plt.close()


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    df = pd.read_csv(IN_PATH)
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with PdfPages(OUT_PATH) as pdf:
        page_title_methods(pdf)
        page_results(pdf, df)
        page_topics(pdf, df)
        page_limitations_next(pdf)
    print(f"Saved: {OUT_PATH}")


if __name__ == "__main__":
    main()
