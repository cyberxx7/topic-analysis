"""
build_annotation_dataset.py — Build Annotation Dataset

Collects articles from a configurable window (default: 365 days = May 2025–May 2026),
applies topic matching, and produces a balanced stratified sample of ~1,000 articles
with equal representation across all publication sources.

Usage:
    # Full run (scrape + analyze + sample):
    python3.11 evaluation/scripts/build_annotation_dataset.py

    # Skip scraping if data already collected:
    python3.11 evaluation/scripts/build_annotation_dataset.py --input outputs/2026-04-24/articles_tagged.csv

    # Custom sample size:
    python3.11 evaluation/scripts/build_annotation_dataset.py --n 1000

Output:
    evaluation/annotation/full_corpus_365d.csv       — all articles from 365-day window
    evaluation/annotation/annotation_sample_1000.csv — balanced 1,000-article sample
"""

import argparse
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from analysis.topics import TOPICS

TOPIC_IDS = [t["id"] for t in TOPICS]
OUTPUT_DIR = "evaluation/annotation"
CORPUS_PATH = os.path.join(OUTPUT_DIR, "full_corpus_365d.csv")
SAMPLE_PATH = os.path.join(OUTPUT_DIR, "annotation_sample_1000.csv")


# ── Stage 1: Data collection ──────────────────────────────────────────────────

def collect_and_analyze(days: int) -> str:
    """Run scraper + topic analysis, return path to articles_tagged.csv."""
    from datetime import datetime
    run_date = datetime.now().strftime("%Y-%m-%d")
    out_dir = os.path.join("outputs", f"{run_date}-annotation")
    os.makedirs(out_dir, exist_ok=True)

    print(f"\n[Stage 1] Scraping {days}-day window → {out_dir}")
    from scraper.scrape import run_scraper
    df = run_scraper(days=days, output_dir=out_dir)
    print(f"[Stage 1] {len(df)} articles scraped")

    print(f"\n[Stage 2] Running topic analysis ...")
    from analysis.analyze import run_analysis
    run_analysis(output_dir=out_dir)

    tagged_path = os.path.join(out_dir, "articles_tagged.csv")
    print(f"[Stage 2] ✓ Tagged corpus → {tagged_path}")
    return tagged_path


# ── Stage 2: Balanced sampling ────────────────────────────────────────────────

def create_balanced_sample(
    input_path: str,
    corpus_output: str,
    sample_output: str,
    n: int = 1000,
    seed: int = 42,
) -> pd.DataFrame:
    """
    Create a balanced n-article sample with equal representation per source.

    Strategy:
      - Equal base allocation per source (n // num_sources)
      - Sources with fewer articles than their base share contribute all they have;
        their unmet slots are redistributed proportionally to larger sources.
    """
    print(f"\n[Sampler] Loading {input_path} ...")
    df = pd.read_csv(input_path)
    print(f"[Sampler] {len(df)} total articles, "
          f"{(df['topic_count'] > 0).sum()} pipeline-tagged")

    # Save full corpus for reference
    os.makedirs(os.path.dirname(corpus_output), exist_ok=True)
    df.to_csv(corpus_output, index=False)
    print(f"[Sampler] Full corpus saved → {corpus_output}")

    sources = sorted(df["source"].unique())
    print(f"\n[Sampler] {len(sources)} sources found:")
    for src in sources:
        cnt = len(df[df["source"] == src])
        tagged = (df[df["source"] == src]["topic_count"] > 0).sum()
        print(f"  {src:<28} {cnt:>5} articles  ({tagged} tagged by pipeline)")

    # -- Balanced allocation --
    base = n // len(sources)
    short_sources, surplus_sources = [], []
    for src in sources:
        if len(df[df["source"] == src]) <= base:
            short_sources.append(src)
        else:
            surplus_sources.append(src)

    samples = []

    # Take all articles from under-represented sources
    leftover = 0
    for src in short_sources:
        src_df = df[df["source"] == src]
        samples.append(src_df)
        leftover += base - len(src_df)

    # Distribute leftover slots proportionally among surplus sources
    surplus_total = sum(len(df[df["source"] == s]) for s in surplus_sources)
    for src in surplus_sources:
        src_df = df[df["source"] == src]
        if surplus_total > 0:
            extra = round(leftover * len(src_df) / surplus_total)
        else:
            extra = 0
        allocation = min(base + extra, len(src_df))
        samples.append(src_df.sample(n=allocation, random_state=seed))

    sample = (
        pd.concat(samples)
        .drop_duplicates(subset=["link"])
        .sample(frac=1, random_state=seed)
        .reset_index(drop=True)
    )
    if len(sample) > n:
        sample = sample.head(n)

    # -- Build output columns --
    out = pd.DataFrame()
    out["article_id"]       = sample.index + 1
    out["source"]           = sample["source"].values
    out["date"]             = sample["date_of_publication"].values
    out["title"]            = sample["title"].values
    out["description"]      = sample["description"].values
    out["link"]             = sample["link"].values
    out["pipeline_topics"]  = sample["topics"].fillna("").values
    out["pipeline_phrases"] = sample["matched_phrases"].fillna("").values

    # Pre-fill pipeline predictions as ✓ (applies) or blank (does not apply)
    for tid in TOPIC_IDS:
        out[f"label_{tid}"] = sample["topic_ids"].apply(
            lambda ids: "✓" if isinstance(ids, str) and tid in ids.split("; ") else ""
        ).values

    out["other"]             = ""
    out["other_category"]    = ""
    out["annotator_notes"]   = ""

    os.makedirs(os.path.dirname(sample_output), exist_ok=True)
    out.to_csv(sample_output, index=False)

    print(f"\n[Sampler] ✓ Balanced sample of {len(out)} articles → {sample_output}")
    print(f"\n  Per-source breakdown:")
    print(f"  {'Source':<28} {'Articles':>9}  {'Pipeline-tagged':>15}")
    print(f"  {'─'*28} {'─'*9}  {'─'*15}")
    for src in sorted(out["source"].unique()):
        g = out[out["source"] == src]
        tagged = (g["pipeline_topics"].str.strip() != "").sum()
        print(f"  {src:<28} {len(g):>9}  {tagged:>15}")

    print(f"\n  Next step: python3.11 evaluation/scripts/create_excel_sheet.py")
    return out


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build annotation dataset")
    parser.add_argument(
        "--input", default=None,
        help="Path to an existing articles_tagged.csv (skips scraping)"
    )
    parser.add_argument("--days", type=int, default=365,
                        help="Rolling collection window in days (default: 365)")
    parser.add_argument("--n", type=int, default=1000,
                        help="Number of articles in balanced sample (default: 1000)")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    if args.input:
        tagged_path = args.input
    else:
        tagged_path = collect_and_analyze(days=args.days)

    create_balanced_sample(
        input_path=tagged_path,
        corpus_output=CORPUS_PATH,
        sample_output=SAMPLE_PATH,
        n=args.n,
        seed=args.seed,
    )
