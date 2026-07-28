"""
make_figures.py — generates every figure for the AAAI-27 AISI paper from the
evaluation CSVs in evaluation/results/. All grayscale, vector PDF output,
sized for the AAAI two-column format (column width ~3.3 in).

Usage (from repo root):
    python3.11 paper/figures/make_figures.py

Outputs (paper/figures/):
    fig_pipeline.pdf   — pipeline architecture (Fig 1)
    fig_iaa.pdf        — per-topic inter-annotator agreement (Fig 2)
    fig_methods.pdf    — method comparison vs human ceiling (Fig 3)
    fig_pertopic.pdf   — per-topic supervised F1, both directions (Fig 4)
"""

import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

RES = "evaluation/results"
OUT = "paper/figures"
os.makedirs(OUT, exist_ok=True)

plt.rcParams.update({
    "font.family": "serif",
    "font.size": 8,
    "axes.linewidth": 0.6,
    "xtick.direction": "out",
    "ytick.direction": "out",
})

DARK, MID, LIGHT, PALE = "#333333", "#777777", "#aaaaaa", "#d8d8d8"

SHORT = {
    "Policing/Public Safety": "Policing/Pub. Safety",
    "Voter Suppression": "Voter Suppression",
    "Book Bans/Anti-DEI": "Book Bans/Anti-DEI",
    "Housing/Displacement": "Housing/Displace.",
    "Maternal Health": "Maternal Health",
    "Redlining/Fair Housing": "Redlining",
    "Anti-Black Surveillance": "Surveillance",
    "Reparations": "Reparations",
    "School Funding": "School Funding",
    "Criminal Justice Reform": "Crim. Justice Ref.",
    "Environmental Justice": "Environ. Justice",
    "Economic Equity/Wealth Gap": "Econ. Equity",
}
TOPICS = list(SHORT.keys())


# ── Fig 1: pipeline architecture ─────────────────────────────────────────────
def fig_pipeline():
    fig, ax = plt.subplots(figsize=(3.4, 1.35))
    ax.axis("off")
    stages = [
        ("Scrape", "10 Black media\npubs, rolling\nmonthly"),
        ("Analyze", "supervised\nper-topic\nclassifier"),
        ("Report", "CSV artifacts,\nPDF editorial\nreport"),
        ("Deliver", "cloud drive,\nCI/CD"),
    ]
    # Wider boxes, narrower gaps, and a smaller arrowhead so nothing spills
    # past a box edge into the neighboring arrow or box.
    w, h, gap, y, x0 = 0.225, 0.68, 0.028, 0.16, 0.005
    for i, (name, desc) in enumerate(stages):
        x = x0 + i * (w + gap)
        ax.add_patch(plt.Rectangle((x, y), w, h, fill=True, facecolor=PALE,
                                   edgecolor=DARK, linewidth=0.8))
        ax.text(x + w / 2, y + h - 0.13, name, ha="center", va="center",
                fontsize=7.2, fontweight="bold", color=DARK)
        ax.text(x + w / 2, y + h / 2 - 0.14, desc, ha="center", va="center",
                fontsize=4.7, color="#222222", linespacing=1.5)
        if i < 3:
            ax.annotate("", xy=(x + w + gap - 0.004, y + h / 2),
                        xytext=(x + w + 0.004, y + h / 2),
                        arrowprops=dict(arrowstyle="->", lw=0.8, color=DARK,
                                        mutation_scale=7))
    ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    fig.savefig(f"{OUT}/fig_pipeline.pdf", bbox_inches="tight")
    plt.close(fig)


# ── Fig 2: per-topic IAA ─────────────────────────────────────────────────────
def fig_iaa():
    iaa = pd.read_csv(f"{RES}/iaa_results.csv")
    iaa = iaa[~iaa["topic"].isin(["MACRO AVG", "POOLED"])]
    s1 = iaa[iaa["set"] == "set1"].set_index("topic")["kappa"]
    s3 = iaa[iaa["set"] == "set3"].set_index("topic")["kappa"]

    ypos = np.arange(len(TOPICS))[::-1]
    fig, ax = plt.subplots(figsize=(3.3, 2.7))
    bh = 0.38
    ax.barh(ypos + bh / 2, [s1[t] for t in TOPICS], height=bh,
            color=DARK, label="Expert vs Annotator 1")
    ax.barh(ypos - bh / 2, [s3[t] for t in TOPICS], height=bh,
            color=LIGHT, label="Expert vs Annotator 3")
    ax.set_yticks(ypos)
    ax.set_yticklabels([SHORT[t] for t in TOPICS], fontsize=6.8)
    ax.axvline(0, color="black", lw=0.6)
    ax.set_xlabel("Cohen's $\\kappa$", fontsize=7.5)
    ax.set_xlim(-0.05, 0.85)
    ax.legend(fontsize=6.2, frameon=False, loc="lower right")
    ax.spines[["top", "right"]].set_visible(False)
    fig.savefig(f"{OUT}/fig_iaa.pdf", bbox_inches="tight")
    plt.close(fig)


# ── Fig 3: method comparison vs human ceiling ────────────────────────────────
def fig_methods():
    # Seven multi-word method names don't fit in a single AAAI column without
    # the x-tick labels running into each other, so this figure is generated
    # wide and placed as a two-column (figure*) spanning figure in the paper.
    hy = pd.read_csv(f"{RES}/hybrid_vs_human.csv")
    su = pd.read_csv(f"{RES}/supervised_vs_human.csv")
    methods = [
        ("Keyword", hy[hy["method"] == "Keyword Pipeline"]),
        ("Semantic", hy[hy["method"] == "Semantic Tagger"]),
        ("Hybrid OR", hy[hy["method"] == "Hybrid OR (Union)"]),
        ("Hybrid AND", hy[hy["method"] == "Hybrid AND (Intersect)"]),
        ("Soft Boost (in-sample)", hy[hy["method"] == "Hybrid Soft Boost"]),
        ("Soft Boost (CV)", hy[hy["method"] == "Hybrid Soft Boost (CV)"]),
        ("Supervised (CV)", su),
    ]
    names = [m[0] for m in methods]
    f1s = [m[1]["f1"].mean() for m in methods]
    kps = [m[1]["kappa"].mean() for m in methods]
    x = np.arange(len(names))

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(6.8, 2.3),
                                 gridspec_kw={"wspace": 0.28})
    colors = [MID] * 4 + [PALE, MID, DARK]

    a1.bar(x, f1s, 0.62, color=colors, edgecolor=DARK, linewidth=0.5)
    a1.set_ylabel("Macro F1", fontsize=8.5)
    a1.set_ylim(0, 0.42)
    for xi, v in zip(x, f1s):
        a1.text(xi, v + 0.008, f"{v:.3f}", ha="center", fontsize=6.5)

    a2.bar(x, kps, 0.62, color=colors, edgecolor=DARK, linewidth=0.5)
    a2.axhline(0.327, color="black", lw=0.8, ls="--")
    a2.axhline(0.384, color="black", lw=0.8, ls=":")
    a2.text(6.65, 0.331, "human baseline (set 1)", fontsize=6.2,
            ha="right", va="bottom")
    a2.text(6.65, 0.388, "human baseline (set 3)", fontsize=6.2,
            ha="right", va="bottom")
    a2.set_ylabel("Macro Cohen's $\\kappa$", fontsize=8.5)
    a2.set_ylim(0, 0.42)
    for xi, v in zip(x, kps):
        a2.text(xi, v + 0.008, f"{v:.3f}", ha="center", fontsize=6.5)

    # Rotated, single-line labels give each of the seven methods its own
    # clear diagonal lane instead of stacking multi-line labels on top of
    # each other in a narrow column width.
    for ax in (a1, a2):
        ax.set_xticks(x)
        ax.set_xticklabels(names, fontsize=7.2, rotation=32, ha="right",
                           rotation_mode="anchor")
        ax.spines[["top", "right"]].set_visible(False)
        ax.set_xlim(-0.7, len(names) - 0.3)
    fig.savefig(f"{OUT}/fig_methods.pdf", bbox_inches="tight")
    plt.close(fig)


# ── Fig 4: per-topic supervised F1 heatmap ───────────────────────────────────
def fig_pertopic():
    su = pd.read_csv(f"{RES}/supervised_vs_human.csv")
    t1 = su[su["annotator"] == "annotator_1"].set_index("topic")["f1"]
    t3 = su[su["annotator"] == "annotator_3"].set_index("topic")["f1"]
    data = np.array([[t3.get(t, np.nan), t1.get(t, np.nan)] for t in TOPICS])

    fig, ax = plt.subplots(figsize=(3.3, 2.5))
    im = ax.imshow(data, cmap="Greys", vmin=0, vmax=0.8, aspect="auto")
    ax.set_yticks(range(len(TOPICS)))
    ax.set_yticklabels([SHORT[t] for t in TOPICS], fontsize=6.8)
    ax.set_xticks([0, 1])
    ax.set_xticklabels(["Test: Annotator 3\n(train: Ann. 1)",
                        "Test: Annotator 1\n(train: Ann. 3)"], fontsize=6.4)
    for i in range(len(TOPICS)):
        for j in range(2):
            v = data[i, j]
            ax.text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=6,
                    color="white" if v > 0.45 else "black")
    cb = fig.colorbar(im, ax=ax, shrink=0.85)
    cb.set_label("F1", fontsize=7)
    cb.ax.tick_params(labelsize=6)
    fig.savefig(f"{OUT}/fig_pertopic.pdf", bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    fig_pipeline()
    fig_iaa()
    fig_methods()
    fig_pertopic()
    print("Figures written to", OUT)
