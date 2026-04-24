"""
validation/sample_articles.py — Manual Validation Sampler

Draws a stratified sample of articles from the pipeline's tagged output
and exports a CSV ready for manual human labeling.

Sampling strategy:
  - 200 articles total
  - Proportional by source (so all 7 outlets are represented)
  - Within each source: 50% tagged by pipeline, 50% untagged
    (ensures we can catch both false positives and false negatives)

Output:
  validation/validation_sample.csv

The CSV has one column per topic (label_<topic_id>).
Fill each with 1 if the article covers that topic, 0 if not.
Leave blank only if you are unsure — the evaluator will skip blanks.

Usage:
    python3.11 -m validation.sample_articles
    # or
    python3.11 validation/sample_articles.py [--input outputs/articles_tagged.csv]
                                              [--n 200]
                                              [--output validation/validation_sample.csv]
                                              [--seed 42]
"""

import argparse
import os
import pandas as pd
from analysis.topics import TOPICS

TOPIC_IDS = [t["id"] for t in TOPICS]
TOPIC_NAMES = {t["id"]: t["name"] for t in TOPICS}


def sample_articles(
    input_path: str = "outputs/articles_tagged.csv",
    output_path: str = "validation/validation_sample.csv",
    n: int = 200,
    seed: int = 42,
) -> pd.DataFrame:
    print(f"\n[sampler] Loading {input_path} ...")
    df = pd.read_csv(input_path)
    print(f"[sampler] {len(df)} articles loaded ({(df['topic_count'] > 0).sum()} tagged by pipeline)")

    df["_tagged"] = df["topic_count"] > 0

    samples = []
    sources = df["source"].unique()
    total   = len(df)

    # Strategy:
    # - Every source gets a guaranteed minimum of MIN_PER_SOURCE articles
    #   (or all its articles if it has fewer than the minimum)
    # - Remaining slots are distributed proportionally among larger sources
    MIN_PER_SOURCE = 15
    guaranteed     = {src: min(MIN_PER_SOURCE, len(df[df["source"] == src]))
                      for src in sources}
    guaranteed_total = sum(guaranteed.values())
    remaining_slots  = max(0, n - guaranteed_total)

    for source in sources:
        src_df    = df[df["source"] == source]
        base      = guaranteed[source]

        # Extra proportional slots for larger sources
        extra = round(remaining_slots * len(src_df) / total) if remaining_slots > 0 else 0
        allocation = min(base + extra, len(src_df))

        # Split allocation 50/50 between tagged and untagged
        half = allocation // 2
        tagged_pool   = src_df[src_df["_tagged"]]
        untagged_pool = src_df[~src_df["_tagged"]]

        tagged = tagged_pool.sample(
            n=min(half, len(tagged_pool)), random_state=seed
        )
        untagged = untagged_pool.sample(
            n=min(allocation - len(tagged), len(untagged_pool)), random_state=seed
        )
        samples.append(pd.concat([tagged, untagged]))

    sample = (
        pd.concat(samples)
        .drop_duplicates()
        .sample(frac=1, random_state=seed)
        .reset_index(drop=True)
    )

    # Trim to exactly n if over
    if len(sample) > n:
        sample = sample.head(n)

    print(f"[sampler] Sampled {len(sample)} articles "
          f"({sample['_tagged'].sum()} pipeline-tagged, "
          f"{(~sample['_tagged']).sum()} pipeline-untagged)")

    # ── Build output columns ──────────────────────────────────────────
    out = pd.DataFrame()
    out["article_id"]          = sample.index + 1
    out["source"]              = sample["source"].values
    out["date"]                = sample["date_of_publication"].values
    out["title"]               = sample["title"].values
    out["description"]         = sample["description"].values
    out["link"]                = sample["link"].values
    out["pipeline_topics"]     = sample["topics"].values
    out["pipeline_phrases"]    = sample["matched_phrases"].values

    # One labeling column per topic, pre-filled with pipeline prediction
    # so annotators can confirm/correct rather than starting from scratch.
    for tid in TOPIC_IDS:
        col = f"label_{tid}"
        out[col] = sample["topic_ids"].apply(
            lambda ids: 1 if isinstance(ids, str) and tid in ids.split("; ") else 0
        ).values

    out["annotator_notes"] = ""

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    out.to_csv(output_path, index=False)

    print(f"\n[sampler] ✓ Saved validation sample → {output_path}")
    print(f"\n  Instructions:")
    print(f"  1. Open {output_path} in Excel / Google Sheets")
    print(f"  2. For each article, review title + description")
    print(f"  3. Set label_<topic> = 1 if article covers that topic, 0 if not")
    print(f"     (Pipeline predictions are pre-filled — correct any mistakes)")
    print(f"  4. Save and run: python3.11 -m validation.evaluate\n")

    # Print per-source breakdown
    print(f"  {'Source':<22} {'Articles':>9}  {'Pipeline-tagged':>15}")
    print(f"  {'─'*22} {'─'*9}  {'─'*15}")
    for src in sorted(out["source"].unique()):
        g = out[out["source"] == src]
        tagged = (g["pipeline_topics"].str.strip() != "").sum()
        print(f"  {src:<22} {len(g):>9}  {tagged:>15}")

    return out


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sample articles for manual validation")
    parser.add_argument("--input",  default="outputs/articles_tagged.csv")
    parser.add_argument("--output", default="validation/validation_sample.csv")
    parser.add_argument("--n",      type=int, default=200)
    parser.add_argument("--seed",   type=int, default=42)
    args = parser.parse_args()

    sample_articles(
        input_path=args.input,
        output_path=args.output,
        n=args.n,
        seed=args.seed,
    )
