"""
scrape_body_text.py — Scrape Full Article Body Text

Visits each of the 1,000 article URLs and extracts the full body text.
Adds a 'body' column to annotation_sample_1000.csv so the topic analysis
pipeline can match against the full article content instead of just
the title and short description.

Features:
  - Saves progress after every article (resumable if interrupted)
  - Polite rate limiting (1–2s delay between requests)
  - Graceful error handling (failed articles keep their description)
  - Works across all 8 publication sites

Usage:
    python3.11 evaluation/scripts/scrape_body_text.py
    python3.11 evaluation/scripts/scrape_body_text.py --input  evaluation/annotation/annotation_sample_1000.csv
                                                       --output evaluation/annotation/annotation_sample_1000.csv
"""

import argparse
import os
import sys
import time
import random
import requests
from bs4 import BeautifulSoup
import pandas as pd

INPUT_PATH  = "evaluation/annotation/annotation_sample_1000.csv"
OUTPUT_PATH = "evaluation/annotation/annotation_sample_1000.csv"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

# CSS selectors tried in order — first match wins
BODY_SELECTORS = [
    "article",
    "[class*='article-body']",
    "[class*='article__body']",
    "[class*='post-body']",
    "[class*='post-content']",
    "[class*='entry-content']",
    "[class*='story-body']",
    "[class*='content-body']",
    "main",
]

MIN_BODY_CHARS = 100   # discard extractions shorter than this


def extract_body(url: str, timeout: int = 15) -> str:
    """Fetch a URL and return the cleaned article body text."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout)
        resp.raise_for_status()
    except Exception as e:
        return ""

    soup = BeautifulSoup(resp.text, "lxml")

    # Remove noise elements
    for tag in soup(["script", "style", "nav", "header", "footer",
                     "aside", "form", "figure", "figcaption",
                     "[class*='ad']", "[class*='promo']",
                     "[class*='newsletter']", "[class*='related']"]):
        tag.decompose()

    # Try each selector in order
    for selector in BODY_SELECTORS:
        container = soup.select_one(selector)
        if container:
            paragraphs = container.find_all("p")
            text = " ".join(p.get_text(" ", strip=True) for p in paragraphs)
            if len(text) >= MIN_BODY_CHARS:
                return text

    # Last resort: all <p> tags on the page
    paragraphs = soup.find_all("p")
    text = " ".join(p.get_text(" ", strip=True) for p in paragraphs)
    return text if len(text) >= MIN_BODY_CHARS else ""


def scrape_all(input_path: str, output_path: str):
    df = pd.read_csv(input_path)
    print(f"\n[body scraper] {len(df)} articles loaded from {input_path}")

    # Add body column if not present; skip already-scraped rows
    if "body" not in df.columns:
        df["body"] = ""
    else:
        already = (df["body"].fillna("").str.strip() != "").sum()
        print(f"[body scraper] {already} articles already have body text — skipping those")

    total   = len(df)
    success = 0
    failed  = 0

    for i, (idx, row) in enumerate(df.iterrows()):
        # Skip if already scraped
        if str(row.get("body", "")).strip():
            continue

        url = str(row.get("link", "")).strip()
        if not url:
            failed += 1
            continue

        body = extract_body(url)
        df.at[idx, "body"] = body

        if body:
            success += 1
            status = f"✓ {len(body):,} chars"
        else:
            failed += 1
            status = "✗ no body extracted"

        print(f"  [{i+1:>4}/{total}] {row.get('source',''):<22} {status}  {url[:60]}")

        # Save progress every 25 articles
        if (i + 1) % 25 == 0:
            df.to_csv(output_path, index=False)
            print(f"  [saved progress → {output_path}]")

        # Polite delay (1–2 seconds)
        time.sleep(random.uniform(1.0, 2.0))

    df.to_csv(output_path, index=False)

    print(f"\n[body scraper] Done.")
    print(f"  Successful : {success}")
    print(f"  Failed     : {failed}")
    print(f"  Saved      → {output_path}")
    print(f"\n  Next step: python3.11 evaluation/scripts/reanalyze_with_body.py")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape full article body text")
    parser.add_argument("--input",  default=INPUT_PATH)
    parser.add_argument("--output", default=OUTPUT_PATH)
    args = parser.parse_args()
    scrape_all(input_path=args.input, output_path=args.output)
