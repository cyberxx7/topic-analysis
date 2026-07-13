"""
visualize_comparison.py

Generate and save visualizations comparing pipeline topic analysis
against human annotation. Reads from annotation/pipeline_vs_human.csv
which is produced by run_pipeline_on_annotations.py.

Usage:
    python annotation/visualize_comparison.py

Outputs saved to: outputs/annotation-comparison/
"""

import os
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

OUT_DIR = "outputs/annotation-comparison"
os.makedirs(OUT_DIR, exist_ok=True)

COLORS = {
    "annotator_1": "#E84855",
    "annotator_3": "#2E86AB",
    "kappa_good":  "#2ECC71",
    "kappa_mod":   "#F39C12",
    "kappa_poor":  "#E74C3C",
    "tp": "#27AE60", "fp": "#E74C3C", "fn": "#F39C12",
}

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "figure.dpi": 150,
})

TOPIC_MAP = {
    "policing_public_safety":      "Policing",
    "voter_suppression":           "Voter\nSuppression",
    "book_bans_anti-dei":          "Book Bans/\nAnti-DEI",
    "housing_displacement":        "Housing",
    "maternal_health":             "Maternal\nHealth",
    "redlining_fair_housing":      "Redlining",
    "anti-black_surveillance":     "Surveillance",
    "reparations":                 "Reparations",
    "school_funding":              "School\nFunding",
    "criminal_justice_reform":     "Criminal\nJustice",
    "environmental_justice":       "Env. Justice",
    "economic_equity_wealth_gap":  "Economic\nEquity",
}

TOPIC_KEYS = list(TOPIC_MAP.keys())
SHORT_LABELS = list(TOPIC_MAP.values())


# ── Metrics ────────────────────────────────────────────────────────────────────

def compute_metrics(y_true, y_pred):
    tp = int(((y_true == 1) & (y_pred == 1)).sum())
    fp = int(((y_true == 0) & (y_pred == 1)).sum())
    fn = int(((y_true == 1) & (y_pred == 0)).sum())
    tn = int(((y_true == 0) & (y_pred == 0)).sum())
    n  = tp + fp + fn + tn
    prec = tp / (tp + fp) if (tp + fp) else 0.0
    rec  = tp / (tp + fn) if (tp + fn) else 0.0
    f1   = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
    p_o  = (tp + tn) / n if n else 0.0
    p_e  = ((tp+fp)*(tp+fn) + (tn+fn)*(tn+fp)) / (n*n) if n else 0.0
    kap  = (p_o - p_e) / (1 - p_e) if (1 - p_e) else 0.0
    return dict(tp=tp, fp=fp, fn=fn, tn=tn,
                precision=prec, recall=rec, f1=f1, kappa=kap,
                human_pos=tp+fn, pipeline_pos=tp+fp)


def build_results(df):
    rows = []
    for key, label in TOPIC_MAP.items():
        h_col = f"human_{key}"
        p_col = f"pipeline_{key}"
        if h_col not in df.columns:
            continue
        m = compute_metrics(
            df[h_col].fillna(0).astype(int).values,
            df[p_col].fillna(0).astype(int).values,
        )
        m["short"] = label
        m["key"]   = key
        rows.append(m)
    return pd.DataFrame(rows)


# ── Chart 1: F1 Score by Topic — both annotators ──────────────────────────────

def chart_f1_comparison(res1, res3):
    fig, ax = plt.subplots(figsize=(13, 6))
    x = np.arange(len(TOPIC_KEYS))
    w = 0.35

    b1 = ax.bar(x - w/2, res1["f1"], w, label="Annotator 1 (200 articles)",
                color=COLORS["annotator_1"], alpha=0.85, zorder=3)
    b2 = ax.bar(x + w/2, res3["f1"], w, label="Annotator 3 (200 articles)",
                color=COLORS["annotator_3"], alpha=0.85, zorder=3)

    ax.axhline(0.4, color="gray", linestyle="--", linewidth=0.8, alpha=0.6)
    ax.text(len(TOPIC_KEYS) - 0.3, 0.415, "moderate (0.4)",
            fontsize=7.5, color="gray", va="bottom")

    ax.set_xticks(x)
    ax.set_xticklabels(SHORT_LABELS, fontsize=9)
    ax.set_ylim(0, 1)
    ax.set_ylabel("F1 Score", fontsize=11)
    ax.set_title("Pipeline F1 Score vs Human Annotation — by Topic",
                 fontsize=13, fontweight="bold", pad=12)
    ax.legend(fontsize=10)
    ax.yaxis.grid(True, alpha=0.3, zorder=0)
    ax.set_axisbelow(True)

    for bar in list(b1) + list(b2):
        h = bar.get_height()
        if h > 0.01:
            ax.text(bar.get_x() + bar.get_width()/2, h + 0.01,
                    f"{h:.2f}", ha="center", va="bottom", fontsize=7)

    plt.tight_layout()
    path = f"{OUT_DIR}/01_f1_by_topic.png"
    plt.savefig(path, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {path}")


# ── Chart 2: Precision vs Recall — Annotator 1 ────────────────────────────────

def chart_precision_recall(res1, res3):
    fig, axes = plt.subplots(1, 2, figsize=(15, 5), sharey=True)
    for ax, res, name, color in zip(
        axes,
        [res1, res3],
        ["Annotator 1", "Annotator 3"],
        [COLORS["annotator_1"], COLORS["annotator_3"]],
    ):
        x = np.arange(len(TOPIC_KEYS))
        w = 0.3
        ax.bar(x - w/2, res["precision"], w, label="Precision",
               color=color, alpha=0.85, zorder=3)
        ax.bar(x + w/2, res["recall"], w, label="Recall",
               color=color, alpha=0.4, zorder=3)
        ax.set_xticks(x)
        ax.set_xticklabels(SHORT_LABELS, fontsize=8)
        ax.set_ylim(0, 1.05)
        ax.set_title(f"Precision vs Recall — {name}", fontsize=11, fontweight="bold")
        ax.legend(fontsize=9)
        ax.yaxis.grid(True, alpha=0.3, zorder=0)
        ax.set_axisbelow(True)

    axes[0].set_ylabel("Score", fontsize=11)
    fig.suptitle("Pipeline Precision vs Recall by Topic", fontsize=13,
                 fontweight="bold", y=1.01)
    plt.tight_layout()
    path = f"{OUT_DIR}/02_precision_recall.png"
    plt.savefig(path, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {path}")


# ── Chart 3: Cohen's Kappa — both annotators ──────────────────────────────────

def chart_kappa(res1, res3):
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    for ax, res, name in zip(axes, [res1, res3], ["Annotator 1", "Annotator 3"]):
        kappas = res["kappa"].values
        labels = res["short"].tolist()
        bar_colors = [
            COLORS["kappa_good"] if k >= 0.4 else
            COLORS["kappa_mod"]  if k >= 0.2 else
            COLORS["kappa_poor"]
            for k in kappas
        ]
        ax.barh(labels[::-1], kappas[::-1], color=bar_colors[::-1],
                alpha=0.85, zorder=3)
        ax.axvline(0.4, color="#27AE60", linestyle="--", linewidth=1.2, alpha=0.7)
        ax.axvline(0.2, color="#F39C12", linestyle="--", linewidth=1.2, alpha=0.7)
        ax.axvline(0.0, color="black", linewidth=0.8)
        ax.set_xlabel("Cohen's Kappa", fontsize=10)
        ax.set_title(f"Cohen's Kappa — {name}", fontsize=11, fontweight="bold")
        ax.xaxis.grid(True, alpha=0.3, zorder=0)
        ax.set_axisbelow(True)
        for i, k in enumerate(kappas[::-1]):
            ax.text(k + 0.01 if k >= 0 else k - 0.01, i,
                    f"{k:.3f}", va="center",
                    ha="left" if k >= 0 else "right", fontsize=8)

    legend = [
        mpatches.Patch(color=COLORS["kappa_good"], label="Substantial (≥ 0.4)"),
        mpatches.Patch(color=COLORS["kappa_mod"],  label="Fair (0.2–0.4)"),
        mpatches.Patch(color=COLORS["kappa_poor"], label="Poor (< 0.2)"),
    ]
    axes[1].legend(handles=legend, fontsize=8, loc="lower right")
    fig.suptitle("Pipeline Agreement with Human Annotators — Cohen's Kappa",
                 fontsize=13, fontweight="bold", y=1.01)
    plt.tight_layout()
    path = f"{OUT_DIR}/03_kappa_by_topic.png"
    plt.savefig(path, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {path}")


# ── Chart 4: TP / FP / FN stacked bar ────────────────────────────────────────

def chart_tp_fp_fn(res1, res3):
    fig, axes = plt.subplots(1, 2, figsize=(15, 5), sharey=False)
    for ax, res, name in zip(axes, [res1, res3], ["Annotator 1", "Annotator 3"]):
        x   = np.arange(len(TOPIC_KEYS))
        tp  = res["tp"].values
        fp  = res["fp"].values
        fn  = res["fn"].values
        ax.bar(x, tp, label="True Positive",  color=COLORS["tp"], zorder=3)
        ax.bar(x, fp, bottom=tp,      label="False Positive", color=COLORS["fp"], zorder=3)
        ax.bar(x, fn, bottom=tp+fp,   label="False Negative", color=COLORS["fn"], zorder=3)
        ax.set_xticks(x)
        ax.set_xticklabels(res["short"].tolist(), fontsize=8)
        ax.set_ylabel("Article Count", fontsize=10)
        ax.set_title(f"Error Breakdown — {name}", fontsize=11, fontweight="bold")
        ax.legend(fontsize=9)
        ax.yaxis.grid(True, alpha=0.3, zorder=0)
        ax.set_axisbelow(True)

    fig.suptitle("Pipeline Errors by Topic (TP = correct, FP = over-tagged, FN = missed)",
                 fontsize=12, fontweight="bold", y=1.01)
    plt.tight_layout()
    path = f"{OUT_DIR}/04_tp_fp_fn_breakdown.png"
    plt.savefig(path, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {path}")


# ── Chart 5: Article coverage — pipeline vs humans ────────────────────────────

def chart_coverage(df1, df3):
    fig, axes = plt.subplots(1, 2, figsize=(15, 5))
    for ax, df, name in zip(axes, [df1, df3], ["Annotator 1", "Annotator 3"]):
        x = np.arange(len(TOPIC_KEYS))
        w = 0.35
        human_counts    = [df[f"human_{k}"].fillna(0).sum() for k in TOPIC_KEYS]
        pipeline_counts = [df[f"pipeline_{k}"].fillna(0).sum() for k in TOPIC_KEYS]
        ax.bar(x - w/2, human_counts,    w, label="Human",    color="#E84855", alpha=0.85, zorder=3)
        ax.bar(x + w/2, pipeline_counts, w, label="Pipeline", color="#2E86AB", alpha=0.85, zorder=3)
        ax.set_xticks(x)
        ax.set_xticklabels(SHORT_LABELS, fontsize=8)
        ax.set_ylabel("Articles Tagged", fontsize=10)
        ax.set_title(f"Coverage — {name}", fontsize=11, fontweight="bold")
        ax.legend(fontsize=9)
        ax.yaxis.grid(True, alpha=0.3, zorder=0)
        ax.set_axisbelow(True)

    fig.suptitle("Articles Tagged per Topic — Pipeline vs Human (200 articles each)",
                 fontsize=12, fontweight="bold", y=1.01)
    plt.tight_layout()
    path = f"{OUT_DIR}/05_coverage_comparison.png"
    plt.savefig(path, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {path}")


# ── Chart 6: Overall scorecard ────────────────────────────────────────────────

def chart_scorecard(res1, res3):
    fig, axes = plt.subplots(2, 4, figsize=(14, 6))
    fig.suptitle("Pipeline Validation Scorecard — Pipeline vs Human Annotation",
                 fontsize=13, fontweight="bold", y=1.02)

    def gauge(ax, value, label, color):
        v = max(value, 0)
        ax.barh([0], [v],  color=color,    height=0.5, alpha=0.85)
        ax.barh([0], [1],  color="#ECF0F1", height=0.5, alpha=0.4)
        ax.set_xlim(0, 1)
        ax.set_yticks([])
        ax.set_xlabel(label, fontsize=9, fontweight="bold")
        ax.text(0.5, 0, f"{value:.3f}", ha="center", va="center",
                fontsize=16, fontweight="bold",
                color="white" if v > 0.25 else "black")
        for spine in ax.spines.values():
            spine.set_visible(False)

    for row_axes, res, name, color in zip(
        [axes[0], axes[1]],
        [res1, res3],
        ["Annotator 1", "Annotator 3"],
        [COLORS["annotator_1"], COLORS["annotator_3"]],
    ):
        row_axes[0].set_ylabel(name, fontsize=10, fontweight="bold", labelpad=10)
        gauge(row_axes[0], res["precision"].mean(), "Macro Precision", color)
        gauge(row_axes[1], res["recall"].mean(),    "Macro Recall",    color)
        gauge(row_axes[2], res["f1"].mean(),        "Macro F1",        "#8E44AD")
        gauge(row_axes[3], max(res["kappa"].mean(), 0), "Macro Kappa", "#F39C12")

    plt.tight_layout()
    path = f"{OUT_DIR}/06_scorecard.png"
    plt.savefig(path, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {path}")


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    print("Loading pipeline_vs_human.csv...")
    df = pd.read_csv("evaluation/results/pipeline_vs_human.csv")

    df1 = df[df["annotator"] == "annotator_1"].reset_index(drop=True)
    df3 = df[df["annotator"] == "annotator_3"].reset_index(drop=True)

    print(f"  Annotator 1: {len(df1)} articles")
    print(f"  Annotator 3: {len(df3)} articles")

    print("Computing metrics...")
    res1 = build_results(df1)
    res3 = build_results(df3)

    print(f"\nGenerating charts → {OUT_DIR}/")
    chart_f1_comparison(res1, res3)
    chart_precision_recall(res1, res3)
    chart_kappa(res1, res3)
    chart_tp_fp_fn(res1, res3)
    chart_coverage(df1, df3)
    chart_scorecard(res1, res3)

    print(f"\nDone. 6 charts saved to {OUT_DIR}/")


if __name__ == "__main__":
    main()
