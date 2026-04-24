"""
generate_report.py — PDF Report Generator

Loads analysis outputs, renders the Jinja2 HTML template,
then converts to PDF using WeasyPrint.
"""

import os
import json
import math
from datetime import date, timedelta
from collections import defaultdict

import pandas as pd
from jinja2 import Environment, FileSystemLoader

from analysis.topics import TOPICS

REPORT_DIR = os.path.dirname(__file__)
TEMPLATE_FILE = "template.html"
CSS_PATH = os.path.join(REPORT_DIR, "assets", "styles.css")


def run_report(output_dir: str = "outputs") -> str:
    print("\n[report] ── Generating Report ──")

    output_pdf  = os.path.join(output_dir, "editorial_report.pdf")
    output_html = os.path.join(output_dir, "editorial_report.html")

    # --- Load data ---
    df = _load_csv(os.path.join(output_dir, "articles_tagged.csv"))
    topic_summary = _load_json(os.path.join(output_dir, "topic_summary.json"))
    tfidf_results = _load_json(os.path.join(output_dir, "tfidf_keywords.json"))
    chart_paths = _load_json(os.path.join(output_dir, "chart_paths.json"))

    # Make chart paths absolute for weasyprint
    chart_paths = {k: _abs_path(v) if isinstance(v, str) else v
                   for k, v in chart_paths.items()}

    # Wordcloud paths
    wordcloud_paths = {}
    wc_data = chart_paths.get("wordclouds", {})
    if isinstance(wc_data, dict):
        wordcloud_paths = {k: _abs_path(v) for k, v in wc_data.items()}

    # --- Build template context ---
    context = _build_context(df, topic_summary, tfidf_results, chart_paths, wordcloud_paths)

    # --- Render HTML ---
    env = Environment(loader=FileSystemLoader(REPORT_DIR))
    env.globals["abs"] = abs
    template = env.get_template(TEMPLATE_FILE)
    html_content = template.render(**context)

    os.makedirs(output_dir, exist_ok=True)
    with open(output_html, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"[report] HTML rendered → {output_html}")

    # --- Convert to PDF ---
    try:
        from weasyprint import HTML
        HTML(filename=os.path.abspath(output_html),
             base_url=os.path.abspath(output_dir)).write_pdf(output_pdf)
        print(f"[report] PDF saved → {output_pdf}")
    except ImportError:
        print("[report] WARNING: WeasyPrint not installed. HTML report saved only.")
    except Exception as e:
        print(f"[report] PDF generation error: {e}")
        print(f"[report] HTML report available at: {output_html}")

    print("[report] ── Report Complete ──\n")
    return output_pdf


def _build_context(df, topic_summary, tfidf_results, chart_paths, wordcloud_paths) -> dict:
    today = date.today()
    window_start = today - timedelta(days=30)

    total_articles = topic_summary.get("total_articles", len(df))
    tagged_articles = topic_summary.get("tagged_articles", 0)
    coverage_rate = topic_summary.get("coverage_rate", 0.0)
    topic_counts = topic_summary.get("topic_counts", {})
    source_matrix = topic_summary.get("source_topic_matrix", {})
    articles_by_topic = topic_summary.get("top_articles_per_topic", {})

    # Dominant topic
    dominant_topic = max(topic_counts, key=topic_counts.get) if topic_counts else "N/A"
    dominant_topic_count = topic_counts.get(dominant_topic, 0)
    dominant_topic_short = dominant_topic[:20] + "…" if len(dominant_topic) > 20 else dominant_topic

    # Key finding sentence
    top3 = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)[:3]
    top3_str = ", ".join([f"{t} ({c})" for t, c in top3])
    key_finding = (
        f"During this period, {coverage_rate}% of articles addressed at least one tracked "
        f"social conflict topic. The three most-covered topics were: {top3_str}."
        if top3 else
        "No social conflict topics were matched in this analysis period."
    )

    # Build a lookup: link → category from the tagged DataFrame
    link_to_category = {}
    if not df.empty and "link" in df.columns and "category" in df.columns:
        link_to_category = dict(zip(df["link"], df["category"].fillna("")))

    # Source stats
    source_stats = []
    if not df.empty and "source" in df.columns:
        for source in df["source"].unique():
            src_df     = df[df["source"] == source]
            topics_col = src_df.get("topics", pd.Series(dtype=str))
            if hasattr(topics_col, "str"):
                src_tagged = src_df[topics_col.str.strip() != ""]
            else:
                src_tagged = src_df.iloc[0:0]
            src_topics = source_matrix.get(source, {})
            top_topic  = max(src_topics, key=src_topics.get) if src_topics else "—"
            total      = len(src_df)
            tagged     = len(src_tagged)
            rate       = round(tagged / total * 100, 1) if total > 0 else 0
            source_stats.append({
                "source":         source,
                "total":          total,
                "tagged":         tagged,
                "topics_covered": len(src_topics),
                "rate":           rate,
                "top_topic":      top_topic[:32] + "…" if len(top_topic) > 32 else top_topic,
            })
        source_stats.sort(key=lambda x: x["total"], reverse=True)

    # Topic deep-dive details
    topic_details = []
    for topic in TOPICS:
        name = topic["name"]
        count = topic_counts.get(name, 0)
        raw_articles = articles_by_topic.get(name, [])

        # Sort by date descending
        raw_articles = sorted(
            raw_articles,
            key=lambda a: a.get("date", ""),
            reverse=True
        )

        # Build author lookup from tagged df
        link_to_author = {}
        if not df.empty and "link" in df.columns and "author" in df.columns:
            link_to_author = dict(zip(df["link"], df["author"].fillna("")))

        topic_details.append({
            "id":          topic["id"],
            "name":        name,
            "description": topic["description"],
            "color":       topic["color"],
            "count":       count,
            "articles": [
                {
                    "title":           a.get("title", "")[:160],
                    "link":            a.get("link", ""),
                    "source":          a.get("source", ""),
                    "date":            a.get("date", ""),
                    "category":        link_to_category.get(a.get("link", ""), ""),
                    "author":          link_to_author.get(a.get("link", ""), ""),
                    "matched_phrases": a.get("matched_phrases", [])[:8],
                }
                for a in raw_articles
            ],
        })

    # Sort topic_details by count descending
    topic_details.sort(key=lambda t: t["count"], reverse=True)

    # Top keywords
    top_keywords = tfidf_results.get("global", [])[:30]

    return {
        "generated_date": today.strftime("%B %d, %Y"),
        "window_start": window_start.strftime("%B %d, %Y"),
        "window_end": today.strftime("%B %d, %Y"),
        "total_articles": total_articles,
        "tagged_articles": tagged_articles,
        "coverage_rate": coverage_rate,
        "num_sources": df["source"].nunique() if not df.empty else 0,
        "dominant_topic": dominant_topic,
        "dominant_topic_short": dominant_topic_short,
        "dominant_topic_count": dominant_topic_count,
        "key_finding": key_finding,
        "source_stats": source_stats,
        "topic_details": topic_details,
        "top_keywords": top_keywords,
        "chart_paths": chart_paths,
        "wordcloud_paths": wordcloud_paths,
        "css_path": f"file://{_abs_path(CSS_PATH)}",
    }


def _load_csv(path: str) -> pd.DataFrame:
    if os.path.exists(path):
        return pd.read_csv(path).fillna("")
    print(f"[report] WARNING: {path} not found, using empty DataFrame")
    return pd.DataFrame()


def _load_json(path: str) -> dict:
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    print(f"[report] WARNING: {path} not found")
    return {}


def _abs_path(path: str) -> str:
    if not path:
        return ""
    return os.path.abspath(path)


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--output-dir", default="outputs", help="Output directory")
    a = p.parse_args()
    run_report(output_dir=a.output_dir)
