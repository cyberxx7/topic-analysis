"""
visualizations.py — Chart & Graph Generation (Light Research Theme)

Generates all charts for the editorial report:
  1.  Topic frequency horizontal bar chart
  2.  Publication source donut chart
  3.  Source × Topic coverage heatmap
  4.  Articles published over time (line)
  5.  Top TF-IDF keywords horizontal bar
  6.  Topic coverage rate gauge
  7.  Multi-topic distribution bar
  8.  Word clouds per topic (if wordcloud installed)
"""

import os
import warnings
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns
from analysis.topics import TOPICS, TOPIC_COLORS

warnings.filterwarnings("ignore")

OUTPUT_DIR = "outputs/charts"  # overridden at runtime by generate_all_charts()

# ── Shared light-theme style ──────────────────────────────────────────────────

BG       = "#ffffff"
PANEL    = "#f7f8fa"
TEXT     = "#1a1d23"
MUTED    = "#5c6070"
ACCENT   = "#1d4ed8"
GRID     = "#e2e6ef"
BORDER   = "#dde1e9"

plt.rcParams.update({
    "font.family":        "DejaVu Sans",
    "font.size":          9,
    "text.color":         TEXT,
    "axes.labelcolor":    TEXT,
    "axes.edgecolor":     BORDER,
    "axes.facecolor":     BG,
    "axes.spines.top":    False,
    "axes.spines.right":  False,
    "figure.facecolor":   BG,
    "xtick.color":        MUTED,
    "ytick.color":        MUTED,
    "xtick.labelsize":    8,
    "ytick.labelsize":    8,
    "grid.color":         GRID,
    "grid.linestyle":     "--",
    "grid.linewidth":     0.7,
    "grid.alpha":         1.0,
    "axes.titlesize":     11,
    "axes.titleweight":   "bold",
    "axes.titlecolor":    TEXT,
    "axes.titlepad":      12,
})


def generate_all_charts(
    df: pd.DataFrame,
    topic_summary: dict,
    tfidf_results: dict,
    output_dir: str = "outputs/charts",
) -> dict:
    """Generate all charts and return {chart_name: file_path}."""
    global OUTPUT_DIR
    OUTPUT_DIR = output_dir
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    paths = {}
    paths["topic_frequency"]       = chart_topic_frequency(topic_summary)
    paths["source_breakdown"]      = chart_source_breakdown(df)
    paths["source_topic_heatmap"]  = chart_source_topic_heatmap(topic_summary)
    paths["articles_over_time"]    = chart_articles_over_time(df)
    paths["top_keywords"]          = chart_top_keywords(tfidf_results)
    paths["topic_coverage_rate"]   = chart_coverage_rate(topic_summary)
    paths["multi_topic_articles"]  = chart_multi_topic_distribution(df)
    try:
        paths["wordclouds"] = chart_wordclouds(df, topic_summary)
    except Exception:
        pass
    return paths


# ── 1. Topic Frequency ────────────────────────────────────────────────────────

def chart_topic_frequency(topic_summary: dict) -> str:
    counts = topic_summary.get("topic_counts", {})
    if not counts:
        return ""

    items  = sorted(counts.items(), key=lambda x: x[1])
    labels = [i[0] for i in items]
    values = [i[1] for i in items]
    colors = [TOPIC_COLORS.get(l, ACCENT) for l in labels]

    fig, ax = plt.subplots(figsize=(11, max(5, len(labels) * 0.55 + 1.5)))

    bars = ax.barh(labels, values, color=colors, edgecolor="none", height=0.6)

    for bar, val in zip(bars, values):
        ax.text(
            val + 0.15, bar.get_y() + bar.get_height() / 2,
            str(val), va="center", fontsize=8.5, fontweight="bold", color=TEXT,
        )

    ax.set_xlabel("Number of Articles", labelpad=8, color=MUTED, fontsize=8.5)
    ax.set_title("Article Count by Social Conflict Topic")
    ax.xaxis.grid(True)
    ax.set_axisbelow(True)
    ax.spines["left"].set_visible(False)
    plt.tight_layout(pad=1.4)

    path = f"{OUTPUT_DIR}/topic_frequency.png"
    plt.savefig(path, dpi=150, bbox_inches="tight", facecolor=BG)
    plt.close()
    return path


# ── 2. Source Breakdown Donut ─────────────────────────────────────────────────

def chart_source_breakdown(df: pd.DataFrame) -> str:
    if df.empty or "source" not in df.columns:
        return ""

    counts  = df["source"].value_counts()
    labels  = counts.index.tolist()
    values  = counts.values.tolist()
    palette = [
        "#1d4ed8", "#0891b2", "#059669", "#d97706",
        "#dc2626", "#7c3aed", "#db2777", "#374151",
        "#065f46", "#92400e", "#1e3a5f", "#6b21a8",
    ]
    # If more sources than palette entries, cycle through palette
    colors = [palette[i % len(palette)] for i in range(len(labels))]

    fig, ax = plt.subplots(figsize=(8, 7))
    wedges, _, autotexts = ax.pie(
        values,
        colors=colors,
        autopct="%1.1f%%",
        startangle=140,
        wedgeprops={"width": 0.52, "edgecolor": BG, "linewidth": 2},
        pctdistance=0.77,
    )
    for at in autotexts:
        at.set_fontsize(8)
        at.set_color(BG)
        at.set_fontweight("bold")

    ax.text(0, 0, f"{sum(values)}\narticles", ha="center", va="center",
            fontsize=13, fontweight="bold", color=TEXT)

    patches = [
        mpatches.Patch(color=colors[i], label=f"{labels[i]}  ({values[i]})")
        for i in range(len(labels))
    ]
    ax.legend(
        handles=patches, loc="lower center",
        bbox_to_anchor=(0.5, -0.1), ncol=2,
        frameon=False, fontsize=8.5, labelcolor=TEXT,
    )
    ax.set_title("Article Distribution by Publication")
    plt.tight_layout(pad=1.4)

    path = f"{OUTPUT_DIR}/source_breakdown.png"
    plt.savefig(path, dpi=150, bbox_inches="tight", facecolor=BG)
    plt.close()
    return path


# ── 3. Source × Topic Heatmap ─────────────────────────────────────────────────

def chart_source_topic_heatmap(topic_summary: dict) -> str:
    matrix  = topic_summary.get("source_topic_matrix", {})
    if not matrix:
        return ""

    topic_names = [t["name"] for t in TOPICS]
    sources     = sorted(matrix.keys())

    data = [[matrix[s].get(t, 0) for t in topic_names] for s in sources]
    df_h = pd.DataFrame(data, index=sources, columns=topic_names)

    # Shorten long topic names
    short = {t: t.replace(" & ", "\n& ") for t in topic_names}
    df_h.columns = [short[c] for c in df_h.columns]

    fig, ax = plt.subplots(figsize=(18, max(4, len(sources) * 0.85 + 2)))
    cmap = sns.light_palette(ACCENT, as_cmap=True)

    sns.heatmap(
        df_h, ax=ax, cmap=cmap, annot=True, fmt="d",
        linewidths=0.5, linecolor=PANEL,
        cbar_kws={"shrink": 0.55, "label": "Article Count"},
        annot_kws={"size": 9, "color": TEXT},
    )
    ax.set_title("Topic Coverage by Publication")
    ax.set_xlabel("")
    ax.set_ylabel("")
    plt.xticks(rotation=35, ha="right", fontsize=8)
    plt.yticks(rotation=0, fontsize=9)
    plt.tight_layout(pad=1.4)

    path = f"{OUTPUT_DIR}/source_topic_heatmap.png"
    plt.savefig(path, dpi=150, bbox_inches="tight", facecolor=BG)
    plt.close()
    return path


# ── 4. Articles Over Time ─────────────────────────────────────────────────────

def chart_articles_over_time(df: pd.DataFrame) -> str:
    if df.empty or "date_of_publication" not in df.columns:
        return ""

    df = df.copy()
    df["date_of_publication"] = pd.to_datetime(
        df["date_of_publication"], errors="coerce"
    )
    df = df.dropna(subset=["date_of_publication"])
    if df.empty:
        return ""

    daily = (
        df.groupby(df["date_of_publication"].dt.date)
        .size().reset_index(name="count")
    )
    daily.columns = ["date", "count"]
    daily = daily.sort_values("date")

    palette = [
        "#1d4ed8", "#0891b2", "#059669", "#d97706",
        "#dc2626", "#7c3aed", "#db2777",
    ]

    fig, ax = plt.subplots(figsize=(13, 4.5))
    ax.fill_between(daily["date"], daily["count"], alpha=0.08, color=ACCENT)
    ax.plot(daily["date"], daily["count"], color=ACCENT, linewidth=2,
            marker="o", markersize=3.5, label="All publications")

    for i, (source, grp) in enumerate(df.groupby("source")):
        src_daily = grp.groupby(grp["date_of_publication"].dt.date).size().reset_index()
        src_daily.columns = ["date", "count"]
        src_daily = src_daily.sort_values("date")
        ax.plot(
            src_daily["date"], src_daily["count"],
            color=palette[i % len(palette)],
            linewidth=1, alpha=0.7, label=source,
        )

    ax.set_title("Daily Article Volume — 30-Day Window")
    ax.set_xlabel("Date", labelpad=6, color=MUTED, fontsize=8.5)
    ax.set_ylabel("Articles", labelpad=6, color=MUTED, fontsize=8.5)
    ax.legend(fontsize=7.5, frameon=True, framealpha=0.9,
               edgecolor=BORDER, loc="upper left", ncol=2)
    ax.xaxis.grid(True)
    ax.set_axisbelow(True)
    plt.xticks(rotation=30, ha="right")
    plt.tight_layout(pad=1.4)

    path = f"{OUTPUT_DIR}/articles_over_time.png"
    plt.savefig(path, dpi=150, bbox_inches="tight", facecolor=BG)
    plt.close()
    return path


# ── 5. Top TF-IDF Keywords ────────────────────────────────────────────────────

def chart_top_keywords(tfidf_results: dict) -> str:
    kws = tfidf_results.get("global", [])[:20]
    if not kws:
        return ""

    labels = [k["keyword"] for k in kws][::-1]
    scores = [k["score"] for k in kws][::-1]

    norm   = plt.Normalize(min(scores), max(scores))
    cmap   = matplotlib.colormaps["Blues"]
    colors = [cmap(0.35 + 0.5 * norm(s)) for s in scores]

    fig, ax = plt.subplots(figsize=(11, 6.5))
    bars = ax.barh(labels, scores, color=colors, edgecolor="none", height=0.65)

    for bar, score in zip(bars, scores):
        ax.text(score + 0.0005, bar.get_y() + bar.get_height() / 2,
                f"{score:.4f}", va="center", fontsize=8, color=MUTED)

    ax.set_title("Top 20 TF-IDF Keywords — All Publications")
    ax.set_xlabel("TF-IDF Score", labelpad=8, color=MUTED, fontsize=8.5)
    ax.spines["left"].set_visible(False)
    ax.xaxis.grid(True)
    ax.set_axisbelow(True)
    plt.tight_layout(pad=1.4)

    path = f"{OUTPUT_DIR}/top_keywords.png"
    plt.savefig(path, dpi=150, bbox_inches="tight", facecolor=BG)
    plt.close()
    return path


# ── 6. Coverage Rate Gauge ────────────────────────────────────────────────────

def chart_coverage_rate(topic_summary: dict) -> str:
    rate   = topic_summary.get("coverage_rate", 0)
    total  = topic_summary.get("total_articles", 0)
    tagged = topic_summary.get("tagged_articles", 0)

    fig, ax = plt.subplots(figsize=(6, 4), subplot_kw={"aspect": "equal"})
    ax.set_xlim(-1.3, 1.3)
    ax.set_ylim(-0.35, 1.3)
    ax.axis("off")

    theta_bg   = np.linspace(np.pi, 0, 200)
    ax.plot(np.cos(theta_bg), np.sin(theta_bg),
            color=GRID, linewidth=16, solid_capstyle="round")

    color  = ACCENT if rate >= 50 else "#d97706" if rate >= 25 else "#dc2626"
    filled = np.linspace(np.pi, np.pi - np.pi * rate / 100, 200)
    ax.plot(np.cos(filled), np.sin(filled),
            color=color, linewidth=16, solid_capstyle="round")

    ax.text(0, 0.18, f"{rate:.1f}%", ha="center", va="center",
            fontsize=30, fontweight="bold", color=TEXT, family="Helvetica Neue")
    ax.text(0, -0.04, "Topic Coverage Rate", ha="center",
            fontsize=9, color=MUTED)
    ax.text(-1.1, -0.22, f"{tagged}\nTagged", ha="center",
            fontsize=8.5, color=MUTED)
    ax.text(1.1, -0.22, f"{total - tagged}\nUntagged", ha="center",
            fontsize=8.5, color=MUTED)

    fig.patch.set_facecolor(BG)
    path = f"{OUTPUT_DIR}/coverage_rate.png"
    plt.savefig(path, dpi=150, bbox_inches="tight", facecolor=BG)
    plt.close()
    return path


# ── 7. Multi-Topic Distribution ───────────────────────────────────────────────

def chart_multi_topic_distribution(df: pd.DataFrame) -> str:
    if df.empty or "topic_count" not in df.columns:
        return ""

    counts = df["topic_count"].value_counts().sort_index()
    labels = [f"{i} Topic{'s' if i != 1 else ''}" for i in counts.index]
    palette = ["#e2e8f0", "#93c5fd", "#3b82f6", "#1d4ed8", "#1e3a8a"]
    colors  = palette[: len(labels)]

    fig, ax = plt.subplots(figsize=(7, 4))
    bars = ax.bar(labels, counts.values, color=colors,
                  edgecolor=BORDER, width=0.5, linewidth=0.7)

    for bar, val in zip(bars, counts.values):
        ax.text(bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.3,
                str(val), ha="center", fontsize=9,
                fontweight="bold", color=TEXT)

    ax.set_title("Topics Matched per Article")
    ax.set_ylabel("Article Count", labelpad=6, color=MUTED, fontsize=8.5)
    ax.yaxis.grid(True)
    ax.set_axisbelow(True)
    plt.tight_layout(pad=1.4)

    path = f"{OUTPUT_DIR}/multi_topic_distribution.png"
    plt.savefig(path, dpi=150, bbox_inches="tight", facecolor=BG)
    plt.close()
    return path


# ── 8. Word Clouds ────────────────────────────────────────────────────────────

def chart_wordclouds(df: pd.DataFrame, topic_summary: dict) -> dict:
    from wordcloud import WordCloud

    paths            = {}
    articles_by_topic = topic_summary.get("top_articles_per_topic", {})

    for topic in TOPICS:
        name     = topic["name"]
        articles = articles_by_topic.get(name, [])
        if len(articles) < 3:
            continue

        corpus = " ".join(a.get("title", "") for a in articles).lower()
        wc = WordCloud(
            width=900, height=380,
            background_color=BG,
            color_func=lambda *a, **kw: topic["color"],
            max_words=60,
            prefer_horizontal=0.85,
            collocations=False,
        ).generate(corpus)

        fig, ax = plt.subplots(figsize=(10, 4))
        ax.imshow(wc, interpolation="bilinear")
        ax.axis("off")
        ax.set_title(f"Key Terms: {name}", pad=10)
        fig.patch.set_facecolor(BG)
        plt.tight_layout(pad=0.5)

        safe_id = topic["id"]
        path    = f"{OUTPUT_DIR}/wordcloud_{safe_id}.png"
        plt.savefig(path, dpi=130, bbox_inches="tight", facecolor=BG)
        plt.close()
        paths[name] = path

    return paths
