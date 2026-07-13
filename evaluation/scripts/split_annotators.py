"""
split_annotators.py — Split 1,000 Articles into Annotator Workbooks

Splits annotation_sample_clean.csv into N batches and creates one Excel
workbook per annotator. Each workbook contains:
  - Sheet 1 "Instructions": full how-to guide + topic definitions
  - Sheet 2 "Annotation":   that annotator's articles (blank topic columns)

Output:
  evaluation/annotation/annotators/annotator_1.xlsx  (articles   1–200)
  evaluation/annotation/annotators/annotator_2.xlsx  (articles 201–400)
  evaluation/annotation/annotators/annotator_3.xlsx  (articles 401–600)
  evaluation/annotation/annotators/annotator_4.xlsx  (articles 601–800)
  evaluation/annotation/annotators/annotator_5.xlsx  (articles 801–1000)

Usage:
    python3.11 evaluation/scripts/split_annotators.py
    python3.11 evaluation/scripts/split_annotators.py --n-annotators 5 --batch-size 200
"""

import argparse
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from evaluation.scripts.create_excel_sheet import create_workbook

INPUT_PATH = "evaluation/annotation/annotation_sample_clean.csv"
OUTPUT_DIR = "evaluation/annotation/annotators"


def split_and_create(input_path: str, output_dir: str, batch_size: int = 200):
    df = pd.read_csv(input_path)
    total = len(df)
    print(f"\n[split] {total} articles loaded from {input_path}")

    os.makedirs(output_dir, exist_ok=True)

    n_batches = (total + batch_size - 1) // batch_size  # ceiling division
    print(f"[split] Splitting into {n_batches} batches of ~{batch_size} articles each\n")

    for i in range(n_batches):
        start = i * batch_size
        end   = min(start + batch_size, total)
        batch = df.iloc[start:end].copy()
        batch["article_id"] = range(1, len(batch) + 1)  # reset IDs to 1–200 per sheet

        # Save batch CSV (temp, used only to feed create_workbook)
        batch_csv  = os.path.join(output_dir, f"_batch_{i+1}.csv")
        batch_xlsx = os.path.join(output_dir, f"annotator_{i+1}.xlsx")
        batch.to_csv(batch_csv, index=False)

        print(f"  Annotator {i+1}  articles {start+1:>4}–{end:<4}  → {batch_xlsx}")
        create_workbook(input_path=batch_csv, output_path=batch_xlsx)

        # Remove temp CSV
        os.remove(batch_csv)

    print(f"\n[split] ✓ {n_batches} annotator workbooks saved → {output_dir}/")
    print(f"\n  Files to send:")
    for i in range(n_batches):
        print(f"    annotator_{i+1}.xlsx  +  ANNOTATION_GUIDELINES.md")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Split articles into per-annotator workbooks")
    parser.add_argument("--input",        default=INPUT_PATH)
    parser.add_argument("--output-dir",   default=OUTPUT_DIR)
    parser.add_argument("--batch-size",   type=int, default=200)
    args = parser.parse_args()

    split_and_create(
        input_path=args.input,
        output_dir=args.output_dir,
        batch_size=args.batch_size,
    )
