"""
reanalyze_with_body.py — Re-run Topic Analysis with Full Body Text

Reads annotation_sample_1000.csv (which now has a 'body' column),
re-runs the topic matching against title + description + body,
updates the label_* columns, and regenerates the annotation Excel sheet.

Usage:
    python3.11 evaluation/scripts/reanalyze_with_body.py
"""

import os
import sys
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from analysis.topic_matcher import match_topics
from analysis.topics import TOPICS

TOPIC_IDS   = [t["id"] for t in TOPICS]
SAMPLE_PATH = "evaluation/annotation/annotation_sample_1000.csv"
CHECK       = "✓"


def reanalyze():
    print(f"\n[reanalyze] Loading {SAMPLE_PATH} ...")
    df = pd.read_csv(SAMPLE_PATH)
    print(f"[reanalyze] {len(df)} articles loaded")

    has_body = df["body"].fillna("").str.strip().ne("").sum()
    print(f"[reanalyze] {has_body} articles have body text")

    # Remap columns to what match_topics() expects
    analysis_df = df.rename(columns={
        "date": "date_of_publication",
        "link": "link",
    }).copy()

    print(f"\n[reanalyze] Running topic matching on title + description + body ...")
    tagged = match_topics(analysis_df)

    # Count before and after
    old_tagged = df[[f"label_{tid}" for tid in TOPIC_IDS]].eq(CHECK).any(axis=1).sum()

    # Update label_* columns from new predictions
    for tid in TOPIC_IDS:
        col = f"label_{tid}"
        df[col] = tagged["topic_ids"].apply(
            lambda ids: CHECK if isinstance(ids, str) and tid in ids.split("; ") else ""
        ).values

    new_tagged = df[[f"label_{tid}" for tid in TOPIC_IDS]].eq(CHECK).any(axis=1).sum()

    df.to_csv(SAMPLE_PATH, index=False)
    print(f"\n[reanalyze] ✓ Updated {SAMPLE_PATH}")
    print(f"\n  Before (title + description only) : {old_tagged} articles tagged")
    print(f"  After  (+ full body text)          : {new_tagged} articles tagged")
    print(f"  Improvement                        : +{new_tagged - old_tagged} articles")

    print(f"\n  Per-topic breakdown:")
    print(f"  {'Topic':<35} {'Before':>8}  {'After':>8}  {'Change':>8}")
    print(f"  {'─'*35} {'─'*8}  {'─'*8}  {'─'*8}")
    for topic in TOPICS:
        tid   = topic["id"]
        col   = f"label_{tid}"
        after = (df[col] == CHECK).sum()
        # Before count: use original tagged data
        before_val = tagged["topic_ids"].apply(
            lambda ids: 1 if isinstance(ids, str) and tid in ids.split("; ") else 0
        )
        # We don't have "before" stored separately so just show after
        print(f"  {topic['name']:<35} {'—':>8}  {after:>8}")

    print(f"\n  Next step: python3.11 evaluation/scripts/create_excel_sheet.py")


if __name__ == "__main__":
    reanalyze()
