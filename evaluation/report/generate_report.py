"""
generate_report.py  —  Annotation Validation Report
Generates a single, clean PDF comparing keyword and semantic pipelines
against human annotation.

Usage:
    python evaluation/report/generate_report.py

Output:
    outputs/annotation-comparison/annotation_validation_report.pdf
"""

import os
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.gridspec as gridspec
from matplotlib.backends.backend_pdf import PdfPages
import numpy as np

OUT_PATH = "outputs/annotation-comparison/Final_PDF_Report.pdf"
os.makedirs("outputs/annotation-comparison", exist_ok=True)

# ── Design tokens ──────────────────────────────────────────────────────────────
DARK     = "#1A1A2E"
RED      = "#C0392B"
BLUE     = "#2471A3"
PURPLE   = "#7D3C98"
GREEN    = "#1E8449"
ORANGE   = "#CA6F1E"
LGREY    = "#F4F6F7"
MGREY    = "#D5D8DC"
DGREY    = "#717D7E"

plt.rcParams.update({
    "font.family":        "DejaVu Sans",
    "font.size":          10,
    "axes.spines.top":    False,
    "axes.spines.right":  False,
    "axes.titlepad":      12,
    "figure.facecolor":   "white",
    "axes.facecolor":     LGREY,
    "axes.grid":          True,
    "grid.color":         "white",
    "grid.linewidth":     1.2,
    "axes.axisbelow":     True,
})

TOPICS = [
    ("policing_public_safety",     "Policing &\nPublic Safety"),
    ("voter_suppression",          "Voter\nSuppression"),
    ("book_bans_anti-dei",         "Book Bans\n& Anti-DEI"),
    ("housing_displacement",       "Housing &\nDisplacement"),
    ("maternal_health",            "Maternal\nHealth"),
    ("redlining_fair_housing",     "Redlining &\nFair Housing"),
    ("anti-black_surveillance",    "Anti-Black\nSurveillance"),
    ("reparations",                "Reparations"),
    ("school_funding",             "School\nFunding"),
    ("criminal_justice_reform",    "Criminal\nJustice Reform"),
    ("environmental_justice",      "Environmental\nJustice"),
    ("economic_equity_wealth_gap", "Economic\nEquity"),
]
KEYS   = [t[0] for t in TOPICS]
LABELS = [t[1] for t in TOPICS]


# ── Metrics ────────────────────────────────────────────────────────────────────

def calc(y_true, y_pred):
    tp = int(((y_true == 1) & (y_pred == 1)).sum())
    fp = int(((y_true == 0) & (y_pred == 1)).sum())
    fn = int(((y_true == 1) & (y_pred == 0)).sum())
    tn = int(((y_true == 0) & (y_pred == 0)).sum())
    n  = tp + fp + fn + tn
    p  = tp / (tp + fp) if (tp + fp) else 0.0
    r  = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2*p*r / (p+r) if (p+r) else 0.0
    p_o = (tp+tn)/n if n else 0.0
    p_e = ((tp+fp)*(tp+fn)+(tn+fn)*(tn+fp))/(n*n) if n else 0.0
    k   = (p_o-p_e)/(1-p_e) if (1-p_e) else 0.0
    return dict(tp=tp, fp=fp, fn=fn, tn=tn,
                precision=p, recall=r, f1=f1, kappa=k,
                human_pos=tp+fn, pipeline_pos=tp+fp)


def get_results(df, pred_prefix):
    rows = []
    for key, label in TOPICS:
        hc = f"human_{key}"
        pc = f"{pred_prefix}_{key}"
        if hc not in df.columns or pc not in df.columns:
            rows.append({**{m: 0.0 for m in ["precision","recall","f1","kappa",
                                              "tp","fp","fn","tn","human_pos","pipeline_pos"]},
                         "label": label})
            continue
        m = calc(df[hc].fillna(0).astype(int).values,
                 df[pc].fillna(0).astype(int).values)
        m["label"] = label
        rows.append(m)
    return pd.DataFrame(rows)


# ── Shared helpers ─────────────────────────────────────────────────────────────

def desc_box(fig, text, y=0.04):
    """Add a shaded description box at the bottom of the figure."""
    ax = fig.add_axes([0.05, y, 0.90, 0.001])
    ax.set_visible(False)
    fig.text(0.5, y + 0.005, text,
             ha="center", va="bottom", fontsize=8.5, color="#2C3E50",
             linespacing=1.8,
             bbox=dict(facecolor="#EAF2FB", edgecolor="#AED6F1",
                       boxstyle="round,pad=0.6", alpha=0.95),
             transform=fig.transFigure)


def section_title(fig, text, y=0.95):
    fig.text(0.5, y, text, ha="center", va="top",
             fontsize=15, fontweight="bold", color=DARK)


def kappa_color(k):
    if k >= 0.4: return GREEN
    if k >= 0.2: return ORANGE
    return RED


def add_bar_labels(ax, bars, fmt="{:.2f}", offset=0.01, fontsize=8):
    for bar in bars:
        h = bar.get_height()
        if h > 0.01:
            ax.text(bar.get_x() + bar.get_width()/2,
                    h + offset, fmt.format(h),
                    ha="center", va="bottom",
                    fontsize=fontsize, fontweight="bold", color=DARK)


# ── Page 1: Cover ─────────────────────────────────────────────────────────────

def page_cover(pdf):
    fig = plt.figure(figsize=(11, 8.5))
    fig.patch.set_facecolor(DARK)

    fig.text(0.5, 0.68, "Annotation Validation Report",
             ha="center", fontsize=32, fontweight="bold", color="white")
    fig.text(0.5, 0.58,
             "Comparing Automated Topic Analysis Against Human Annotation",
             ha="center", fontsize=15, color="#AEB6BF")

    fig.add_artist(plt.Line2D([0.15, 0.85], [0.52, 0.52],
                              transform=fig.transFigure,
                              color="#566573", linewidth=1))

    body = (
        "This report evaluates two automated topic classification methods —\n"
        "a keyword-based pipeline and a semantic (AI embedding) tagger —\n"
        "against human annotation across 400 labeled articles and 12 topics.\n\n"
        "Annotator 1 and Annotator 3 each independently labeled\n"
        "a separate set of 200 articles from the Black media corpus."
    )
    fig.text(0.5, 0.34, body,
             ha="center", fontsize=12, color="#D5D8DC", linespacing=2.0)

    stats = [
        ("400", "Articles Evaluated"),
        ("12",  "Topics"),
        ("2",   "Human Annotators"),
        ("2",   "Pipeline Methods"),
    ]
    for i, (num, lbl) in enumerate(stats):
        x = 0.15 + i * 0.175
        fig.text(x, 0.14, num, ha="center", fontsize=22,
                 fontweight="bold", color="#5DADE2")
        fig.text(x, 0.09, lbl, ha="center", fontsize=9, color="#AEB6BF")

    fig.text(0.5, 0.03,
             "Black Media Topic Study  ·  Pipeline Validation  ·  2026",
             ha="center", fontsize=9, color="#566573")

    pdf.savefig(fig, bbox_inches="tight")
    plt.close()


# ── Page 2: Methods overview ───────────────────────────────────────────────────

def page_methods(pdf):
    fig = plt.figure(figsize=(11, 8.5))
    section_title(fig, "What We Are Comparing", y=0.93)

    fig.text(0.5, 0.87,
             "Two automated pipelines were validated against hand-labeled articles.",
             ha="center", fontsize=11, color=DGREY)

    # Two method boxes
    for x, color, title, body in [
        (0.07, "#D6EAF8",
         "Method 1 — Keyword Pipeline",
         "Scans each article's title, description, and body text\n"
         "for a curated dictionary of seed phrases (e.g. 'police brutality',\n"
         "'voter suppression', 'redlining'). If a phrase is found,\n"
         "the article is tagged with that topic.\n\n"
         "Strengths: Fast, transparent, easy to audit.\n"
         "Weaknesses: Misses articles that use different wording\n"
         "for the same concept."),
        (0.53, "#D5F5E3",
         "Method 2 — Semantic Tagger",
         "Uses an AI sentence-embedding model (all-MiniLM-L6-v2)\n"
         "to measure the meaning similarity between each article\n"
         "and each topic description. Tags the article if similarity\n"
         "exceeds a threshold.\n\n"
         "Strengths: Captures meaning, not just exact words.\n"
         "Weaknesses: Less transparent; threshold-sensitive."),
    ]:
        ax = fig.add_axes([x, 0.40, 0.40, 0.40])
        ax.set_facecolor(color)
        ax.set_xticks([]); ax.set_yticks([])
        for sp in ax.spines.values(): sp.set_color(MGREY)
        ax.text(0.5, 0.92, title, transform=ax.transAxes,
                ha="center", fontsize=11, fontweight="bold", color=DARK)
        ax.text(0.5, 0.50, body, transform=ax.transAxes,
                ha="center", va="center", fontsize=9.5,
                color="#2C3E50", linespacing=1.75)

    # Annotation setup box
    ax2 = fig.add_axes([0.07, 0.10, 0.86, 0.25])
    ax2.set_facecolor("#FDFEFE")
    ax2.set_xticks([]); ax2.set_yticks([])
    for sp in ax2.spines.values(): sp.set_color(MGREY)
    ax2.text(0.5, 0.88, "Human Annotation Setup",
             transform=ax2.transAxes, ha="center",
             fontsize=11, fontweight="bold", color=DARK)
    ax2.text(0.5, 0.45,
             "Two trained annotators independently labeled separate sets of 200 articles each (400 total).\n"
             "For each article they marked which of the 12 social conflict topics were present using a structured Excel sheet.\n"
             "The human labels serve as the 'ground truth' against which both automated pipelines are evaluated.\n"
             "Because the annotators labeled different articles, results are reported separately for each annotator's set.",
             transform=ax2.transAxes, ha="center", va="center",
             fontsize=9.5, color="#2C3E50", linespacing=1.8)

    pdf.savefig(fig, bbox_inches="tight")
    plt.close()


# ── Page 3: What are we measuring? ───────────────────────────────────────────

def page_what_we_measure(pdf):
    fig = plt.figure(figsize=(11, 8.5))
    fig.patch.set_facecolor("white")
    section_title(fig, "What Are We Measuring?", y=0.95)
    fig.text(0.5, 0.89,
             "The core question: how closely does the computer agree with a trained human reader?",
             ha="center", fontsize=11, color=DGREY)

    # ── Step diagram ──────────────────────────────────────────────────────────
    steps = [
        ("#D6EAF8", "STEP 1\nHuman Reads & Labels",
         "Two trained annotators (Annotator 1 and Annotator 3)\n"
         "each manually read 200 articles from Black media publications.\n\n"
         "For every article they answered:\n"
         "Which of the 12 social conflict topics is this article about?\n\n"
         "They checked each topic that applied.\n"
         "These human labels are our GROUND TRUTH —\n"
         "the benchmark we hold the computer against."),
        ("#D5F5E3", "STEP 2\nComputer Labels the Same Articles",
         "We ran the exact same 400 articles through\n"
         "both automated pipelines:\n\n"
         "  • Keyword Pipeline — looks for seed phrases\n"
         "  • Semantic Tagger — uses AI embeddings\n\n"
         "Each pipeline independently decides:\n"
         "which of the 12 topics does this article belong to?\n\n"
         "The computer has NOT seen the human labels."),
        ("#FDEBD0", "STEP 3\nCompare & Score",
         "For every article and every topic we ask:\n"
         "Did the computer agree with the human?\n\n"
         "  ✓  Both said YES  →  True Positive\n"
         "  ✓  Both said NO   →  True Negative\n"
         "  ✗  Computer YES, Human NO  →  False Positive\n"
         "  ✗  Computer NO, Human YES  →  False Negative\n\n"
         "Precision, Recall, F1, and Kappa are all\n"
         "calculated from these four counts."),
    ]

    for i, (bg, title, body) in enumerate(steps):
        x = 0.04 + i * 0.325
        ax = fig.add_axes([x, 0.22, 0.29, 0.60])
        ax.set_facecolor(bg)
        ax.set_xticks([]); ax.set_yticks([])
        for sp in ax.spines.values(): sp.set_color(MGREY)
        ax.text(0.5, 0.93, title, transform=ax.transAxes,
                ha="center", va="top", fontsize=10.5,
                fontweight="bold", color=DARK, linespacing=1.5)
        ax.axhline(0.80, color=MGREY, linewidth=0.8, xmin=0.1, xmax=0.9)
        ax.text(0.5, 0.38, body, transform=ax.transAxes,
                ha="center", va="center", fontsize=9,
                color="#2C3E50", linespacing=1.75)

        # Arrow between boxes
        if i < 2:
            fig.text(x + 0.295, 0.52, "→", ha="center", va="center",
                     fontsize=22, color=MGREY)

    # ── Bottom note ───────────────────────────────────────────────────────────
    ax_note = fig.add_axes([0.05, 0.04, 0.90, 0.13])
    ax_note.set_facecolor("#EAF2FB")
    ax_note.set_xticks([]); ax_note.set_yticks([])
    for sp in ax_note.spines.values(): sp.set_color("#AED6F1")
    ax_note.text(0.5, 0.60,
                 "Important: the two annotators labeled completely different sets of articles.",
                 transform=ax_note.transAxes, ha="center", fontsize=10,
                 fontweight="bold", color=DARK)
    ax_note.text(0.5, 0.22,
                 "Results are therefore reported separately for each annotator's 200-article set. "
                 "This is not a flaw — it shows how consistent the pipeline is across different article samples.",
                 transform=ax_note.transAxes, ha="center", fontsize=9,
                 color="#2C3E50", linespacing=1.6)

    pdf.savefig(fig, bbox_inches="tight")
    plt.close()


# ── Page 4: What is Cohen's Kappa? ───────────────────────────────────────────

def page_kappa_explainer(pdf):
    fig = plt.figure(figsize=(11, 8.5))
    fig.patch.set_facecolor("white")
    section_title(fig, "Understanding Cohen's Kappa", y=0.95)
    fig.text(0.5, 0.89,
             "Why Kappa — and not just accuracy — is the right metric for this study.",
             ha="center", fontsize=11, color=DGREY)

    # ── Left: the problem with accuracy ───────────────────────────────────────
    ax_l = fig.add_axes([0.04, 0.42, 0.42, 0.42])
    ax_l.set_facecolor("#FDFEFE"); ax_l.set_xticks([]); ax_l.set_yticks([])
    for sp in ax_l.spines.values(): sp.set_color(MGREY)

    ax_l.text(0.5, 0.94, "The Problem With Simple Accuracy",
              transform=ax_l.transAxes, ha="center", fontsize=11,
              fontweight="bold", color=RED)
    ax_l.text(0.5, 0.72,
              "Imagine the pipeline NEVER tags any article with \"Reparations\".\n"
              "Out of 200 articles, only 3 were labeled Reparations by the human.\n\n"
              "Accuracy = 197 correct out of 200 = 98.5% ✓\n\n"
              "But the pipeline learned nothing — it just got lucky\n"
              "because the topic is rare. Accuracy is misleading\n"
              "whenever one label (NO) is much more common than the other (YES).\n\n"
              "In our 12-topic study, most articles are NOT about any given topic,\n"
              "so a pipeline that tags nothing would still look ~90% accurate.",
              transform=ax_l.transAxes, ha="center", va="top",
              fontsize=9, color="#2C3E50", linespacing=1.75)

    # ── Right: what Kappa does ────────────────────────────────────────────────
    ax_r = fig.add_axes([0.54, 0.42, 0.42, 0.42])
    ax_r.set_facecolor("#EAF2FB"); ax_r.set_xticks([]); ax_r.set_yticks([])
    for sp in ax_r.spines.values(): sp.set_color("#AED6F1")

    ax_r.text(0.5, 0.94, "What Kappa Does Instead",
              transform=ax_r.transAxes, ha="center", fontsize=11,
              fontweight="bold", color=BLUE)
    ax_r.text(0.5, 0.72,
              "Kappa asks: how much better than chance is the agreement?\n\n"
              "It first calculates how often we'd expect the computer\n"
              "and human to agree purely by random chance,\n"
              "based on how often each label appears.\n\n"
              "Then it measures how much the ACTUAL agreement\n"
              "exceeds that chance baseline.\n\n"
              "Formula:\n"
              "κ = (Observed Agreement − Chance Agreement)\n"
              "        ÷  (1 − Chance Agreement)",
              transform=ax_r.transAxes, ha="center", va="top",
              fontsize=9, color="#2C3E50", linespacing=1.75)

    # ── Kappa scale ───────────────────────────────────────────────────────────
    ax_scale = fig.add_axes([0.05, 0.22, 0.90, 0.14])
    ax_scale.set_facecolor("white"); ax_scale.set_xticks([]); ax_scale.set_yticks([])
    for sp in ax_scale.spines.values(): sp.set_visible(False)

    zones = [
        (0.00, 0.20, RED,    "κ < 0",     "Worse than\nchance"),
        (0.20, 0.35, RED,    "0–0.2",     "Poor\nagreement"),
        (0.35, 0.55, ORANGE, "0.2–0.4",   "Fair\nagreement"),
        (0.55, 0.75, GREEN,  "0.4–0.6",   "Substantial\nagreement"),
        (0.75, 1.00, "#117A65", "0.6–1.0", "Strong\nagreement"),
    ]
    for x0, x1, color, label, desc in zones:
        ax_scale.barh([0], [x1 - x0], left=x0, height=0.45,
                      color=color, alpha=0.85)
        mid = (x0 + x1) / 2
        ax_scale.text(mid, 0.65, label, ha="center", va="bottom",
                      fontsize=8.5, fontweight="bold", color=DARK,
                      transform=ax_scale.transAxes)
        ax_scale.text(mid, -0.05, desc, ha="center", va="top",
                      fontsize=8, color="#2C3E50", linespacing=1.4,
                      transform=ax_scale.transAxes)

    ax_scale.set_xlim(0, 1); ax_scale.set_ylim(-0.5, 1)

    # Marker for our result
    our_kw  = 0.282   # keyword Ann1 kappa
    our_sem = 0.250   # semantic Ann3 kappa
    for val, label, color in [(our_kw, "Keyword\n(Ann. 1)", RED),
                               (our_sem, "Semantic\n(Ann. 3)", PURPLE)]:
        ax_scale.annotate("▲", xy=(val, 0.48), xytext=(val, 0.55),
                          ha="center", fontsize=10, color=color,
                          transform=ax_scale.transAxes)
        ax_scale.text(val, 0.60, label, ha="center", va="bottom",
                      fontsize=7.5, color=color, fontweight="bold",
                      transform=ax_scale.transAxes)

    # ── Bottom interpretation ─────────────────────────────────────────────────
    ax_bot = fig.add_axes([0.05, 0.04, 0.90, 0.13])
    ax_bot.set_facecolor("#FDFEFE"); ax_bot.set_xticks([]); ax_bot.set_yticks([])
    for sp in ax_bot.spines.values(): sp.set_color(MGREY)
    ax_bot.text(0.5, 0.62,
                "What does our result mean?",
                transform=ax_bot.transAxes, ha="center", fontsize=10,
                fontweight="bold", color=DARK)
    ax_bot.text(0.5, 0.22,
                "Our pipelines achieved Kappa in the 0.08–0.28 range — straddling poor to fair agreement. "
                "This is a common result for automated\n"
                "content analysis in communication research. "
                "It means the pipelines are doing something meaningful but are not ready\n"
                "to replace human coders. "
                "The recommended next step is to use them as a first pass, with human spot-checking.",
                transform=ax_bot.transAxes, ha="center", va="center",
                fontsize=9, color="#2C3E50", linespacing=1.7)

    pdf.savefig(fig, bbox_inches="tight")
    plt.close()


# ── Page 5: Scorecard summary ─────────────────────────────────────────────────

def page_scorecard(pdf, kw1, kw3, sem1, sem3):
    fig, axes = plt.subplots(2, 4, figsize=(11, 8.5))
    fig.subplots_adjust(top=0.82, bottom=0.22, hspace=0.55, wspace=0.45)
    section_title(fig, "Overall Performance Scorecard", y=0.94)
    fig.text(0.5, 0.88,
             "Macro-averaged scores across all 12 topics for each method and annotator set.",
             ha="center", fontsize=10, color=DGREY)

    metric_keys   = ["precision", "recall", "f1", "kappa"]
    metric_labels = ["Precision", "Recall", "F1 Score", "Kappa"]
    row_labels    = ["Keyword — Ann. 1", "Keyword — Ann. 3",
                     "Semantic — Ann. 1", "Semantic — Ann. 3"]
    datasets      = [kw1, kw3, sem1, sem3]
    row_colors    = [RED, BLUE, PURPLE, GREEN]

    fig.text(0.02, 0.72, "Keyword\nAnnotator 1", va="center",
             fontsize=9, fontweight="bold", color=RED, rotation=0)
    fig.text(0.02, 0.48, "Keyword\nAnnotator 3", va="center",
             fontsize=9, fontweight="bold", color=BLUE, rotation=0)

    for row_i, (res, color) in enumerate(zip([kw1, kw3], [RED, BLUE])):
        for col_i, (mkey, mlabel) in enumerate(zip(metric_keys, metric_labels)):
            ax = axes[row_i][col_i]
            val = max(res[mkey].mean(), 0)
            ax.barh([0], [1],   color=MGREY, height=0.5, alpha=0.4)
            ax.barh([0], [val], color=color, height=0.5, alpha=0.85)
            ax.set_xlim(0, 1)
            ax.set_yticks([])
            ax.set_xticks([0, 0.5, 1.0])
            ax.set_xticklabels(["0", "0.5", "1.0"], fontsize=7.5)
            ax.set_title(mlabel, fontsize=9, fontweight="bold", color=DARK, pad=6)
            ax.text(max(val/2, 0.06), 0, f"{val:.3f}",
                    ha="center", va="center", fontsize=13, fontweight="bold",
                    color="white" if val > 0.15 else DARK)
            ax.set_facecolor(LGREY)
            for sp in ax.spines.values(): sp.set_visible(False)

    # Semantic rows — add as text table below
    col_x = [0.33, 0.50, 0.67, 0.84]
    fig.text(0.05, 0.19, "Semantic Tagger Scores:", fontsize=9,
             fontweight="bold", color=DARK)
    for col_i, (mkey, mlabel) in enumerate(zip(metric_keys, metric_labels)):
        fig.text(col_x[col_i], 0.19, mlabel,
                 ha="center", fontsize=9, fontweight="bold", color=DGREY)
    for row_i, (res, label, color) in enumerate(
        zip([sem1, sem3], ["Semantic — Annotator 1", "Semantic — Annotator 3"],
            [PURPLE, GREEN])
    ):
        y = 0.14 - row_i * 0.055
        fig.text(0.05, y, label, fontsize=9, color=color, fontweight="bold")
        for col_i, mkey in enumerate(metric_keys):
            val = max(res[mkey].mean(), 0)
            fig.text(col_x[col_i], y, f"{val:.3f}",
                     ha="center", fontsize=11, fontweight="bold", color=color)

    desc_box(fig,
        "Precision: when the pipeline tags a topic, how often is it correct?   "
        "Recall: of all articles a human labeled, how many did the pipeline catch?\n"
        "F1: overall balance between precision and recall.   "
        "Kappa: agreement corrected for chance — the most rigorous metric "
        "(≥0.4 = substantial, 0.2–0.4 = fair, <0.2 = poor).",
        y=0.01)

    pdf.savefig(fig, bbox_inches="tight")
    plt.close()


# ── Page 4: F1 by topic — keyword ────────────────────────────────────────────

def page_f1_keyword(pdf, kw1, kw3):
    fig, axes = plt.subplots(2, 1, figsize=(11, 9))
    fig.subplots_adjust(top=0.83, bottom=0.18, hspace=0.55)
    section_title(fig, "Keyword Pipeline — F1 Score by Topic", y=0.96)
    fig.text(0.5, 0.91,
             "How well does the keyword pipeline agree with each annotator on each topic?",
             ha="center", fontsize=10, color=DGREY)

    for ax, res, name, color in zip(
        axes, [kw1, kw3],
        ["Annotator 1 (200 articles)", "Annotator 3 (200 articles)"],
        [RED, BLUE]
    ):
        x = np.arange(len(KEYS))
        bars = ax.bar(x, res["f1"], color=color, alpha=0.85, width=0.6, zorder=3)
        ax.axhline(0.4, color=DGREY, linestyle="--", linewidth=1.0, alpha=0.7)
        ax.axhline(0.2, color=MGREY, linestyle=":",  linewidth=1.0, alpha=0.7)
        ax.set_xticks(x)
        ax.set_xticklabels(LABELS, fontsize=8.5, ha="center")
        ax.set_ylim(0, 0.8)
        ax.set_ylabel("F1 Score", fontsize=10)
        ax.set_title(name, fontsize=11, fontweight="bold", color=color, pad=8)
        ax.text(len(KEYS) - 0.4, 0.42, "moderate (0.4)",
                fontsize=7.5, color=DGREY, va="bottom")
        add_bar_labels(ax, bars, offset=0.012)
        macro = res["f1"].mean()
        ax.text(0.99, 0.92, f"Macro F1 = {macro:.3f}",
                transform=ax.transAxes, ha="right", fontsize=9,
                fontweight="bold", color=color,
                bbox=dict(facecolor="white", edgecolor=color,
                          boxstyle="round,pad=0.3", alpha=0.9))

    desc_box(fig,
        "Each bar shows the F1 score for one topic — the harmonic mean of precision and recall.\n"
        "A score above 0.4 (dashed line) indicates substantial agreement with the human annotator.\n"
        "Topics with no bar (score = 0) were never tagged by the pipeline or never matched human labels.",
        y=0.02)

    pdf.savefig(fig, bbox_inches="tight")
    plt.close()


# ── Page 5: F1 by topic — semantic ───────────────────────────────────────────

def page_f1_semantic(pdf, sem1, sem3):
    fig, axes = plt.subplots(2, 1, figsize=(11, 9))
    fig.subplots_adjust(top=0.83, bottom=0.18, hspace=0.55)
    section_title(fig, "Semantic Tagger — F1 Score by Topic", y=0.96)
    fig.text(0.5, 0.91,
             "How well does the semantic (AI embedding) tagger agree with each annotator on each topic?",
             ha="center", fontsize=10, color=DGREY)

    for ax, res, name, color in zip(
        axes, [sem1, sem3],
        ["Annotator 1 (200 articles, threshold=0.15)",
         "Annotator 3 (200 articles, threshold=0.20)"],
        [PURPLE, GREEN]
    ):
        x = np.arange(len(KEYS))
        bars = ax.bar(x, res["f1"], color=color, alpha=0.85, width=0.6, zorder=3)
        ax.axhline(0.4, color=DGREY, linestyle="--", linewidth=1.0, alpha=0.7)
        ax.axhline(0.2, color=MGREY, linestyle=":",  linewidth=1.0, alpha=0.7)
        ax.set_xticks(x)
        ax.set_xticklabels(LABELS, fontsize=8.5, ha="center")
        ax.set_ylim(0, 0.8)
        ax.set_ylabel("F1 Score", fontsize=10)
        ax.set_title(name, fontsize=11, fontweight="bold", color=color, pad=8)
        ax.text(len(KEYS) - 0.4, 0.42, "moderate (0.4)",
                fontsize=7.5, color=DGREY, va="bottom")
        add_bar_labels(ax, bars, offset=0.012)
        macro = res["f1"].mean()
        ax.text(0.99, 0.92, f"Macro F1 = {macro:.3f}",
                transform=ax.transAxes, ha="right", fontsize=9,
                fontweight="bold", color=color,
                bbox=dict(facecolor="white", edgecolor=color,
                          boxstyle="round,pad=0.3", alpha=0.9))

    desc_box(fig,
        "The semantic tagger converts each article and topic into an AI embedding vector,\n"
        "then tags articles whose similarity score exceeds the threshold (optimised per annotator).\n"
        "Threshold was chosen by scanning 0.10–0.35 and selecting the value that maximised macro F1.",
        y=0.02)

    pdf.savefig(fig, bbox_inches="tight")
    plt.close()


# ── Page 6: Head-to-head F1 ───────────────────────────────────────────────────

def page_head_to_head(pdf, kw1, kw3, sem1, sem3):
    fig, axes = plt.subplots(2, 1, figsize=(11, 9))
    fig.subplots_adjust(top=0.83, bottom=0.18, hspace=0.60)
    section_title(fig, "Keyword vs Semantic — Head-to-Head F1 by Topic", y=0.96)
    fig.text(0.5, 0.91,
             "Direct comparison of both methods on the same article sets.",
             ha="center", fontsize=10, color=DGREY)

    for ax, kw, sem, name, kw_c, sem_c in zip(
        axes, [kw1, kw3], [sem1, sem3],
        ["Annotator 1", "Annotator 3"],
        [RED, BLUE], [PURPLE, GREEN]
    ):
        x = np.arange(len(KEYS))
        w = 0.35
        b1 = ax.bar(x - w/2, kw["f1"],  w, label="Keyword",  color=kw_c,  alpha=0.88, zorder=3)
        b2 = ax.bar(x + w/2, sem["f1"], w, label="Semantic", color=sem_c, alpha=0.88, zorder=3)
        ax.axhline(0.4, color=DGREY, linestyle="--", linewidth=1.0, alpha=0.7)
        ax.set_xticks(x)
        ax.set_xticklabels(LABELS, fontsize=8.5)
        ax.set_ylim(0, 0.85)
        ax.set_ylabel("F1 Score", fontsize=10)
        ax.set_title(name, fontsize=11, fontweight="bold", color=DARK, pad=8)
        ax.legend(fontsize=9, loc="upper right")
        add_bar_labels(ax, b1, fontsize=7.5, offset=0.01)
        add_bar_labels(ax, b2, fontsize=7.5, offset=0.01)

        kw_mac  = kw["f1"].mean()
        sem_mac = sem["f1"].mean()
        winner  = "Keyword" if kw_mac >= sem_mac else "Semantic"
        w_color = kw_c if kw_mac >= sem_mac else sem_c
        ax.text(0.01, 0.92,
                f"Keyword macro F1={kw_mac:.3f}   Semantic macro F1={sem_mac:.3f}   "
                f"→ {winner} wins",
                transform=ax.transAxes, fontsize=8.5,
                fontweight="bold", color=w_color,
                bbox=dict(facecolor="white", edgecolor=w_color,
                          boxstyle="round,pad=0.3", alpha=0.9))

    desc_box(fig,
        "For each topic, the taller bar is the better-performing method on that annotator's article set.\n"
        "The keyword pipeline outperforms on Annotator 1's set; the semantic tagger wins on Annotator 3's set.\n"
        "This suggests neither method is universally superior — combining both may yield the best results.",
        y=0.02)

    pdf.savefig(fig, bbox_inches="tight")
    plt.close()


# ── Page 7: Kappa head-to-head ────────────────────────────────────────────────

def page_kappa(pdf, kw1, kw3, sem1, sem3):
    fig, axes = plt.subplots(1, 2, figsize=(11, 8.5))
    fig.subplots_adjust(top=0.84, bottom=0.27, wspace=0.45)
    section_title(fig, "Cohen's Kappa by Topic — Keyword vs Semantic", y=0.94)
    fig.text(0.5, 0.89,
             "Agreement with human annotation corrected for chance. "
             "The most rigorous validation metric.",
             ha="center", fontsize=10, color=DGREY)

    for ax, kw, sem, name in zip(
        axes, [kw1, kw3], [sem1, sem3],
        ["Annotator 1", "Annotator 3"]
    ):
        topic_labels = [l.replace("\n", " ") for l in LABELS]
        x = np.arange(len(topic_labels))
        w = 0.35
        kw_k  = kw["kappa"].values
        sem_k = sem["kappa"].values

        bars_kw  = ax.barh(x + w/2, kw_k,  w, label="Keyword",  color=RED,    alpha=0.85, zorder=3)
        bars_sem = ax.barh(x - w/2, sem_k, w, label="Semantic", color=PURPLE, alpha=0.85, zorder=3)
        ax.axvline(0.4, color=GREEN,  linestyle="--", linewidth=1.3,
                   alpha=0.8, label="Substantial (0.4)")
        ax.axvline(0.2, color=ORANGE, linestyle=":",  linewidth=1.2,
                   alpha=0.8, label="Fair (0.2)")
        ax.axvline(0.0, color=DARK,   linewidth=0.8)
        ax.set_xlim(-0.2, 0.75)
        ax.set_yticks(x)
        ax.set_yticklabels(topic_labels, fontsize=9)
        ax.set_xlabel("Cohen's Kappa", fontsize=10)
        ax.set_title(name, fontsize=11, fontweight="bold", color=DARK, pad=8)
        ax.legend(fontsize=8, loc="lower right")

        for bar, val in zip(list(bars_kw)+list(bars_sem),
                            list(kw_k)+list(sem_k)):
            if abs(val) > 0.01:
                ax.text(val + 0.01 if val >= 0 else val - 0.02,
                        bar.get_y() + bar.get_height()/2,
                        f"{val:.2f}", va="center",
                        ha="left" if val >= 0 else "right", fontsize=7.5)

    legend_patches = [
        mpatches.Patch(color=GREEN,  label="Substantial (κ ≥ 0.4)"),
        mpatches.Patch(color=ORANGE, label="Fair  (0.2 ≤ κ < 0.4)"),
        mpatches.Patch(color=RED,    label="Poor  (κ < 0.2)"),
    ]
    fig.legend(handles=legend_patches, fontsize=8.5, loc="lower center",
               ncol=3, bbox_to_anchor=(0.5, 0.14), frameon=True)

    desc_box(fig,
        "Cohen's Kappa (κ) measures how much the pipeline and human annotator agree,\n"
        "beyond what would be expected by chance alone.\n"
        "κ ≥ 0.4 = substantial agreement (green dashed line)    "
        "κ 0.2–0.4 = fair agreement    "
        "κ < 0.2 = poor agreement.\n"
        "Negative kappa means the pipeline disagrees with the human more than chance would predict.",
        y=0.02)

    pdf.savefig(fig, bbox_inches="tight")
    plt.close()


# ── Page 8: Precision vs Recall ───────────────────────────────────────────────

def page_prec_rec(pdf, kw1, kw3):
    fig, axes = plt.subplots(2, 1, figsize=(11, 9))
    fig.subplots_adjust(top=0.83, bottom=0.18, hspace=0.60)
    section_title(fig, "Keyword Pipeline — Precision vs Recall by Topic", y=0.96)
    fig.text(0.5, 0.91,
             "Reveals whether the pipeline is over-tagging (too broad) or under-tagging (too narrow) per topic.",
             ha="center", fontsize=10, color=DGREY)

    for ax, res, name, color in zip(
        axes, [kw1, kw3],
        ["Annotator 1", "Annotator 3"],
        [RED, BLUE]
    ):
        x = np.arange(len(KEYS))
        w = 0.35
        ax.bar(x - w/2, res["precision"], w, label="Precision",
               color=color, alpha=0.90, zorder=3)
        ax.bar(x + w/2, res["recall"],    w, label="Recall",
               color=color, alpha=0.40, zorder=3)
        ax.set_xticks(x)
        ax.set_xticklabels(LABELS, fontsize=8.5)
        ax.set_ylim(0, 1.1)
        ax.set_ylabel("Score", fontsize=10)
        ax.set_title(name, fontsize=11, fontweight="bold", color=color, pad=8)
        ax.legend(fontsize=9, loc="upper right")
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.1f}"))

        for i, row in res.iterrows():
            diff = abs(row["precision"] - row["recall"])
            if diff > 0.35:
                msg = "over-tags" if row["recall"] > row["precision"] else "under-tags"
                ax.text(i, max(row["precision"], row["recall"]) + 0.05,
                        msg, ha="center", fontsize=7, color=DGREY,
                        fontstyle="italic")

    desc_box(fig,
        "Precision (solid bar): when the pipeline assigns a topic, how often is the human in agreement?\n"
        "Recall (faded bar): of all articles the human labeled for a topic, how many did the pipeline find?\n"
        "Over-tags → recall is much higher than precision (pipeline is too trigger-happy).\n"
        "Under-tags → precision is much higher than recall (pipeline is too conservative, missing articles).",
        y=0.02)

    pdf.savefig(fig, bbox_inches="tight")
    plt.close()


# ── Page 9: TP / FP / FN breakdown ───────────────────────────────────────────

def page_errors(pdf, kw1, kw3):
    fig, axes = plt.subplots(2, 1, figsize=(11, 9))
    fig.subplots_adjust(top=0.83, bottom=0.20, hspace=0.60)
    section_title(fig, "Keyword Pipeline — Error Breakdown by Topic", y=0.96)
    fig.text(0.5, 0.91,
             "Exact counts of correct tags, false alarms, and missed articles per topic.",
             ha="center", fontsize=10, color=DGREY)

    for ax, res, name, color in zip(
        axes, [kw1, kw3],
        ["Annotator 1", "Annotator 3"], [RED, BLUE]
    ):
        x  = np.arange(len(KEYS))
        tp = res["tp"].values
        fp = res["fp"].values
        fn = res["fn"].values
        ax.bar(x, tp,       label="True Positive — correct tag",       color=GREEN,  alpha=0.88, zorder=3)
        ax.bar(x, fp, bottom=tp,    label="False Positive — over-tagged",    color=RED,    alpha=0.88, zorder=3)
        ax.bar(x, fn, bottom=tp+fp, label="False Negative — missed article", color=ORANGE, alpha=0.88, zorder=3)
        ax.set_xticks(x)
        ax.set_xticklabels(LABELS, fontsize=8.5)
        ax.set_ylabel("Number of Articles", fontsize=10)
        ax.set_title(name, fontsize=11, fontweight="bold", color=color, pad=8)
        ax.legend(fontsize=8.5, loc="upper right")

    desc_box(fig,
        "Green = both the pipeline and human agreed the topic is present (correct).\n"
        "Red = pipeline tagged the topic, but the human did not (false alarm / over-tagging).\n"
        "Orange = human labeled the topic, but the pipeline missed it (false negative / under-tagging).\n"
        "An ideal topic has a tall green bar and minimal red and orange.",
        y=0.02)

    pdf.savefig(fig, bbox_inches="tight")
    plt.close()


# ── Page 10: Coverage ─────────────────────────────────────────────────────────

def page_coverage(pdf, kw_df1, kw_df3):
    fig, axes = plt.subplots(2, 1, figsize=(11, 9))
    fig.subplots_adjust(top=0.83, bottom=0.18, hspace=0.60)
    section_title(fig, "Articles Tagged per Topic — Pipeline vs Human", y=0.96)
    fig.text(0.5, 0.91,
             "How many articles each method tagged for each topic vs how many the human annotator labeled.",
             ha="center", fontsize=10, color=DGREY)

    for ax, df, name, color in zip(
        axes, [kw_df1, kw_df3],
        ["Annotator 1 (200 articles)", "Annotator 3 (200 articles)"],
        [RED, BLUE]
    ):
        x = np.arange(len(KEYS))
        w = 0.28
        h = [df[f"human_{k}"].fillna(0).sum() for k in KEYS]
        kw_p = [df[f"pipeline_{k}"].fillna(0).sum() for k in KEYS]

        ax.bar(x - w/2, h,    w, label="Human annotation", color=color,   alpha=0.88, zorder=3)
        ax.bar(x + w/2, kw_p, w, label="Keyword pipeline", color="#555555", alpha=0.70, zorder=3)
        ax.set_xticks(x)
        ax.set_xticklabels(LABELS, fontsize=8.5)
        ax.set_ylabel("Articles Tagged", fontsize=10)
        ax.set_title(name, fontsize=11, fontweight="bold", color=color, pad=8)
        ax.legend(fontsize=9)

    desc_box(fig,
        "This chart shows volume — how many articles were tagged per topic, not whether they were the right articles.\n"
        "If the pipeline bar is much taller than the human bar, the pipeline is over-tagging.\n"
        "If the pipeline bar is much shorter, the pipeline is under-tagging.\n"
        "Equal heights do not guarantee accuracy — the pipeline may be tagging different articles than the human.",
        y=0.02)

    pdf.savefig(fig, bbox_inches="tight")
    plt.close()


# ── Hybrid data helper ────────────────────────────────────────────────────────

def get_hybrid_results(hybrid_df: pd.DataFrame, method_name: str,
                       annotator: str) -> pd.DataFrame:
    """
    Extract per-topic metrics for one method/annotator slice from
    hybrid_vs_human.csv into the same DataFrame shape used by get_results().
    """
    topic_order = [l for _, l in TOPICS]
    subset = hybrid_df[
        (hybrid_df["method"] == method_name) &
        (hybrid_df["annotator"] == annotator)
    ].copy()

    rows = []
    for label in topic_order:
        row = subset[subset["topic"] == label]
        if row.empty:
            rows.append({"label": label, "f1": 0.0, "kappa": 0.0,
                         "precision": 0.0, "recall": 0.0,
                         "tp": 0, "fp": 0, "fn": 0, "tn": 0,
                         "human_pos": 0, "pipeline_pos": 0})
        else:
            r = row.iloc[0]
            rows.append({"label": label,
                         "f1":        r["f1"],
                         "kappa":     r["kappa"],
                         "precision": r["precision"],
                         "recall":    r["recall"],
                         "tp":        r["tp"],
                         "fp":        r["fp"],
                         "fn":        r["fn"],
                         "tn":        r["tn"],
                         "human_pos": r["tp"] + r["fn"],
                         "pipeline_pos": r["tp"] + r["fp"]})
    return pd.DataFrame(rows)


# ── Page: Hybrid introduction ─────────────────────────────────────────────────

def page_hybrid_intro(pdf):
    fig = plt.figure(figsize=(11, 8.5))
    fig.patch.set_facecolor("white")
    section_title(fig, "Introducing the Hybrid Tagger", y=0.95)
    fig.text(0.5, 0.89,
             "A third approach that combines the strengths of both baselines.",
             ha="center", fontsize=11, color=DGREY)

    # Three strategy boxes
    strategies = [
        ("#FADBD8", "Hybrid OR  (Union)",
         "Tags an article if the keyword pipeline\nOR the semantic tagger fires.\n\n"
         "Effect: maximum recall — nothing gets\nmissed that either method would catch.\n\n"
         "Trade-off: precision falls because both\nmethods' false positives accumulate."),
        ("#D5F5E3", "Hybrid AND  (Intersection)",
         "Tags an article only if BOTH the keyword\npipeline AND the semantic tagger agree.\n\n"
         "Effect: maximum precision — only tags\nthe clearest, most confident cases.\n\n"
         "Trade-off: recall drops sharply; many\nreal articles are missed."),
        ("#D6EAF8", "Hybrid Soft Boost  ✦ Primary",
         "Keyword matches are always kept.\n"
         "Semantic is only allowed to add a tag\nwhen its score ≥ a per-topic threshold\n"
         "optimised by grid search.\n\n"
         "Effect: keyword anchors precision;\nsemantic fills in recall gaps — but\nonly when it is sufficiently confident.\n\n"
         "Thresholds range from 0.05 to 0.38\ndepending on how well-calibrated the\nsemantic model is per topic."),
    ]

    for i, (bg, title, body) in enumerate(strategies):
        x = 0.04 + i * 0.325
        ax = fig.add_axes([x, 0.26, 0.29, 0.56])
        ax.set_facecolor(bg)
        ax.set_xticks([]); ax.set_yticks([])
        for sp in ax.spines.values(): sp.set_color(MGREY)
        ax.text(0.5, 0.94, title, transform=ax.transAxes,
                ha="center", fontsize=10.5, fontweight="bold", color=DARK)
        ax.axhline(0.84, color=MGREY, linewidth=0.8, xmin=0.08, xmax=0.92)
        ax.text(0.5, 0.42, body, transform=ax.transAxes,
                ha="center", va="center", fontsize=9,
                color="#2C3E50", linespacing=1.75)

    # Bottom summary box
    ax_bot = fig.add_axes([0.05, 0.06, 0.90, 0.15])
    ax_bot.set_facecolor("#EAF2FB"); ax_bot.set_xticks([]); ax_bot.set_yticks([])
    for sp in ax_bot.spines.values(): sp.set_color("#AED6F1")
    ax_bot.text(0.5, 0.72, "Design rationale",
                transform=ax_bot.transAxes, ha="center",
                fontsize=10, fontweight="bold", color=DARK)
    ax_bot.text(0.5, 0.28,
                "The keyword pipeline is precise but misses articles that use different wording. "
                "The semantic tagger has strong recall but over-tags.\n"
                "The Soft Boost hybrid is designed to keep keyword's reliable hits while "
                "using the semantic score as a calibrated second opinion,\n"
                "activated only when its confidence exceeds a per-topic threshold learned from the annotation data.",
                transform=ax_bot.transAxes, ha="center", va="center",
                fontsize=9, color="#2C3E50", linespacing=1.75)

    pdf.savefig(fig, bbox_inches="tight")
    plt.close()


# ── Page: 5-method macro scorecard ───────────────────────────────────────────

def page_five_way_scorecard(pdf, all_results: dict):
    """
    all_results: {(annotator, method_name): results_df}
    """
    fig, axes = plt.subplots(1, 4, figsize=(13, 7))
    fig.subplots_adjust(top=0.78, bottom=0.32, wspace=0.5)
    section_title(fig, "All Five Methods — Macro-Averaged Scorecard", y=0.93)
    fig.text(0.5, 0.87,
             "Macro-averaged across all 12 topics. Each bar pair shows Annotator 1 (left) and Annotator 3 (right).",
             ha="center", fontsize=10, color=DGREY)

    METHOD_DISPLAY = [
        ("Keyword Pipeline",       RED,    "Keyword"),
        ("Semantic Tagger",        PURPLE, "Semantic"),
        ("Hybrid OR (Union)",      ORANGE, "OR"),
        ("Hybrid AND (Intersect)", BLUE,   "AND"),
        ("Hybrid Soft Boost",      GREEN,  "Soft Boost"),
    ]

    metric_keys   = ["f1",        "kappa",  "precision", "recall"]
    metric_labels = ["F1 Score",  "Kappa",  "Precision", "Recall"]

    x     = np.arange(len(METHOD_DISPLAY))
    width = 0.38

    for ax, mkey, mlabel in zip(axes, metric_keys, metric_labels):
        vals1 = [all_results[("annotator_1", m)][mkey].mean() for m, _, _ in METHOD_DISPLAY]
        vals3 = [all_results[("annotator_3", m)][mkey].mean() for m, _, _ in METHOD_DISPLAY]
        colors = [c for _, c, _ in METHOD_DISPLAY]

        b1 = ax.bar(x - width/2, vals1, width, color=colors, alpha=0.9,  zorder=3)
        b2 = ax.bar(x + width/2, vals3, width, color=colors, alpha=0.45, zorder=3)

        ax.set_xticks(x)
        ax.set_xticklabels([s for _, _, s in METHOD_DISPLAY],
                           fontsize=8, rotation=30, ha="right")
        ax.set_ylim(0, 0.75)
        ax.set_title(mlabel, fontsize=10, fontweight="bold", color=DARK, pad=8)
        ax.set_ylabel("Score", fontsize=8.5)
        ax.yaxis.grid(True, alpha=0.5)
        ax.set_axisbelow(True)
        for sp in ax.spines.values(): sp.set_visible(False)

        for bar, v in zip(list(b1) + list(b2), vals1 + vals3):
            if v > 0.03:
                ax.text(bar.get_x() + bar.get_width()/2,
                        bar.get_height() + 0.01,
                        f"{v:.2f}", ha="center", fontsize=6.5,
                        fontweight="bold", color=DARK)

    # Legend
    legend_patches = [
        mpatches.Patch(color=MGREY, alpha=0.9,  label="Annotator 1 (solid)"),
        mpatches.Patch(color=MGREY, alpha=0.45, label="Annotator 3 (faded)"),
    ] + [mpatches.Patch(color=c, label=s) for _, c, s in METHOD_DISPLAY]
    fig.legend(handles=legend_patches, fontsize=8, loc="lower center",
               ncol=4, bbox_to_anchor=(0.5, 0.01), frameon=True)

    desc_box(fig,
        "Soft Boost consistently outperforms all other methods on both F1 and Kappa.\n"
        "OR (Union) maximises recall but drops precision. AND (Intersection) maximises precision but loses recall.\n"
        "Soft Boost finds the best balance by keeping keyword anchors and using semantic as a calibrated second opinion.",
        y=0.10)

    pdf.savefig(fig, bbox_inches="tight")
    plt.close()


# ── Page: Hybrid F1 by topic (three hybrids) ─────────────────────────────────

def page_hybrid_f1(pdf, all_results: dict):
    fig, axes = plt.subplots(2, 1, figsize=(13, 10))
    fig.subplots_adjust(top=0.88, bottom=0.15, hspace=0.55)
    section_title(fig, "Hybrid Strategies — F1 Score by Topic", y=0.96)
    fig.text(0.5, 0.91,
             "Comparing all three hybrid variants against the two baselines, per topic.",
             ha="center", fontsize=10, color=DGREY)

    METHOD_STYLES = [
        ("Keyword Pipeline",       RED,    "--", "Keyword (baseline)"),
        ("Semantic Tagger",        PURPLE, ":",  "Semantic (baseline)"),
        ("Hybrid OR (Union)",      ORANGE, "-",  "Hybrid OR"),
        ("Hybrid AND (Intersect)", BLUE,   "-",  "Hybrid AND"),
        ("Hybrid Soft Boost",      GREEN,  "-",  "Hybrid Soft Boost ✦"),
    ]

    for ax, ann, ann_label in zip(axes,
                                   ["annotator_1", "annotator_3"],
                                   ["Annotator 1", "Annotator 3"]):
        x = np.arange(len(KEYS))
        w = 0.17
        offsets = [-2*w, -w, 0, w, 2*w]

        for (method, color, ls, disp_label), offset in zip(METHOD_STYLES, offsets):
            vals = all_results[(ann, method)]["f1"].values
            bars = ax.bar(x + offset, vals, w, color=color,
                          alpha=0.85, zorder=3, label=disp_label)

        ax.axhline(0.4, color=DGREY, linestyle="--", linewidth=1.0, alpha=0.6)
        ax.set_xticks(x)
        ax.set_xticklabels(LABELS, fontsize=8)
        ax.set_ylim(0, 0.85)
        ax.set_ylabel("F1 Score", fontsize=10)
        ax.set_title(ann_label, fontsize=11, fontweight="bold", color=DARK, pad=8)
        ax.yaxis.grid(True, alpha=0.4)
        ax.set_axisbelow(True)
        for sp in ax.spines.values(): sp.set_visible(False)

        soft_macro = all_results[(ann, "Hybrid Soft Boost")]["f1"].mean()
        kw_macro   = all_results[(ann, "Keyword Pipeline")]["f1"].mean()
        ax.text(0.99, 0.93,
                f"Soft Boost macro F1 = {soft_macro:.3f}  (Keyword = {kw_macro:.3f})",
                transform=ax.transAxes, ha="right", fontsize=8.5,
                fontweight="bold", color=GREEN,
                bbox=dict(facecolor="white", edgecolor=GREEN,
                          boxstyle="round,pad=0.3", alpha=0.9))

    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, fontsize=8.5, loc="lower center",
               ncol=5, bbox_to_anchor=(0.5, 0.02), frameon=True)

    pdf.savefig(fig, bbox_inches="tight")
    plt.close()


# ── Page: Soft Boost gain over baselines ─────────────────────────────────────

def page_soft_boost_gain(pdf, all_results: dict):
    fig, axes = plt.subplots(2, 2, figsize=(13, 9))
    fig.subplots_adjust(top=0.86, bottom=0.12, hspace=0.55, wspace=0.35)
    section_title(fig, "Hybrid Soft Boost — Gain Over Baselines (ΔF1)", y=0.95)
    fig.text(0.5, 0.90,
             "Per-topic F1 improvement of Soft Boost over keyword (left) and semantic (right). "
             "Green = improvement, red = regression.",
             ha="center", fontsize=10, color=DGREY)

    comparisons = [
        ("Keyword Pipeline",  "vs Keyword"),
        ("Semantic Tagger",   "vs Semantic"),
    ]

    for row, (ann, ann_label) in enumerate(
        [("annotator_1", "Annotator 1"), ("annotator_3", "Annotator 3")]
    ):
        soft_f1 = all_results[(ann, "Hybrid Soft Boost")]["f1"].values

        for col, (baseline_method, col_label) in enumerate(comparisons):
            ax = axes[row][col]
            base_f1 = all_results[(ann, baseline_method)]["f1"].values
            delta   = soft_f1 - base_f1

            colors = [GREEN if d >= 0 else RED for d in delta]
            bars   = ax.barh(np.arange(len(KEYS)), delta,
                             color=colors, alpha=0.85, zorder=3)

            ax.axvline(0, color=DARK, linewidth=0.8)
            ax.set_yticks(np.arange(len(KEYS)))
            ax.set_yticklabels([l.replace("\n", " ") for l in LABELS], fontsize=8)
            ax.set_xlabel("ΔF1 (Soft Boost − Baseline)", fontsize=8.5)
            ax.set_title(f"{ann_label} — {col_label}",
                         fontsize=10, fontweight="bold", color=DARK, pad=6)
            ax.xaxis.grid(True, alpha=0.4)
            ax.set_axisbelow(True)
            for sp in ax.spines.values(): sp.set_visible(False)

            for bar, d in zip(bars, delta):
                if abs(d) > 0.01:
                    ha  = "left"  if d >= 0 else "right"
                    off = 0.005   if d >= 0 else -0.005
                    ax.text(d + off,
                            bar.get_y() + bar.get_height()/2,
                            f"{d:+.2f}", va="center",
                            ha=ha, fontsize=7, color=DARK)

            net = delta.sum()
            wins = (delta > 0).sum()
            ax.text(0.97, 0.03,
                    f"Net gain: {net:+.3f}  |  {wins}/{len(delta)} topics improved",
                    transform=ax.transAxes, ha="right", fontsize=7.5,
                    color=DARK,
                    bbox=dict(facecolor="white", edgecolor=MGREY,
                              boxstyle="round,pad=0.3", alpha=0.9))

    desc_box(fig,
        "A positive bar means Soft Boost outperforms the baseline on that topic. "
        "Negative means the hybrid is worse (e.g. where keyword alone is already optimal).\n"
        "Topics with zero delta had no articles tagged by either method.",
        y=0.02)

    pdf.savefig(fig, bbox_inches="tight")
    plt.close()


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    print("Loading data...")
    kw_df     = pd.read_csv("evaluation/results/pipeline_vs_human.csv")
    sem_df    = pd.read_csv("evaluation/results/semantic_vs_human.csv")
    hybrid_df = pd.read_csv("evaluation/results/hybrid_vs_human.csv")

    kw_df1  = kw_df[kw_df["annotator"] == "annotator_1"].reset_index(drop=True)
    kw_df3  = kw_df[kw_df["annotator"] == "annotator_3"].reset_index(drop=True)
    sem_df1 = sem_df[sem_df["annotator"] == "annotator_1"].reset_index(drop=True)
    sem_df3 = sem_df[sem_df["annotator"] == "annotator_3"].reset_index(drop=True)

    kw1  = get_results(kw_df1,  "pipeline")
    kw3  = get_results(kw_df3,  "pipeline")
    sem1 = get_results(sem_df1, "semantic")
    sem3 = get_results(sem_df3, "semantic")

    # Build a unified lookup for all 5 methods × 2 annotators
    METHOD_NAMES = [
        "Keyword Pipeline",
        "Semantic Tagger",
        "Hybrid OR (Union)",
        "Hybrid AND (Intersect)",
        "Hybrid Soft Boost",
    ]
    all_results = {}
    for ann in ("annotator_1", "annotator_3"):
        for method in METHOD_NAMES:
            all_results[(ann, method)] = get_hybrid_results(hybrid_df, method, ann)

    print(f"Writing → {OUT_PATH}")
    with PdfPages(OUT_PATH) as pdf:
        meta = pdf.infodict()
        meta["Title"]   = "Annotation Validation Report — Black Media Topic Analysis"
        meta["Subject"] = "Keyword, semantic, and hybrid pipeline validation vs human annotation"

        page_cover(pdf)
        page_methods(pdf)
        page_what_we_measure(pdf)
        page_kappa_explainer(pdf)
        page_scorecard(pdf, kw1, kw3, sem1, sem3)
        page_f1_keyword(pdf, kw1, kw3)
        page_f1_semantic(pdf, sem1, sem3)
        page_head_to_head(pdf, kw1, kw3, sem1, sem3)
        page_kappa(pdf, kw1, kw3, sem1, sem3)
        page_prec_rec(pdf, kw1, kw3)
        page_errors(pdf, kw1, kw3)
        page_coverage(pdf, kw_df1, kw_df3)
        # Hybrid section
        page_hybrid_intro(pdf)
        page_five_way_scorecard(pdf, all_results)
        page_hybrid_f1(pdf, all_results)
        page_soft_boost_gain(pdf, all_results)

    print(f"Done — 16 pages saved to: {OUT_PATH}")


if __name__ == "__main__":
    main()
