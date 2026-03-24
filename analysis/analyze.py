"""
analyze.py — Main Analysis Runner

Orchestrates:
  1. TF-IDF keyword extraction
  2. Topic matching + tagging
  3. Visualization generation
  4. Saving all outputs
"""

import os
import json
import pandas as pd
from analysis.tfidf import extract_tfidf_keywords, save_tfidf
from analysis.topic_matcher import match_topics, build_topic_summary, save_topic_summary
from analysis.visualizations import generate_all_charts

os.makedirs("outputs", exist_ok=True)
os.makedirs("outputs/charts", exist_ok=True)


def run_analysis(articles_path: str = "outputs/articles.csv") -> dict:
    print("\n[analyze] ── Starting Analysis Pipeline ──")

    # --- Load articles ---
    if not os.path.exists(articles_path):
        raise FileNotFoundError(f"articles.csv not found at: {articles_path}")

    df = pd.read_csv(articles_path)
    print(f"[analyze] Loaded {len(df)} articles from {articles_path}")

    if df.empty:
        print("[analyze] WARNING: No articles to analyze.")
        return {}

    # --- Stage 1: TF-IDF ---
    print("[analyze] Running TF-IDF keyword extraction...")
    tfidf_results = extract_tfidf_keywords(df, top_n=50)
    save_tfidf(tfidf_results)

    # --- Stage 2: Topic Matching ---
    print("[analyze] Matching articles to social conflict topics...")
    df_tagged = match_topics(df)
    df_tagged.to_csv("outputs/articles_tagged.csv", index=False)
    print(f"[analyze] Tagged CSV saved → outputs/articles_tagged.csv")

    # Print quick stats
    tagged_count = (df_tagged["topics"].str.strip() != "").sum()
    print(f"[analyze] {tagged_count}/{len(df_tagged)} articles matched at least one topic")

    # --- Stage 3: Build Topic Summary ---
    print("[analyze] Building topic summary...")
    topic_summary = build_topic_summary(df_tagged)
    save_topic_summary(topic_summary)

    # Print topic breakdown
    counts = topic_summary.get("topic_counts", {})
    for topic, count in sorted(counts.items(), key=lambda x: x[1], reverse=True):
        print(f"   → {topic}: {count} articles")

    # --- Stage 4: Generate Visualizations ---
    print("[analyze] Generating charts and visualizations...")
    chart_paths = generate_all_charts(df_tagged, topic_summary, tfidf_results)
    print(f"[analyze] Generated {len(chart_paths)} chart(s)")

    # Save chart paths manifest
    with open("outputs/chart_paths.json", "w") as f:
        json.dump(chart_paths, f, indent=2)

    print("[analyze] ── Analysis Complete ──\n")

    return {
        "df_tagged": df_tagged,
        "tfidf_results": tfidf_results,
        "topic_summary": topic_summary,
        "chart_paths": chart_paths,
    }


if __name__ == "__main__":
    run_analysis()
