"""
scrape.py — Main Scraper Orchestrator

Fetches ALL articles published within the rolling window from 7 Black media
publications. Uses the best available method per source:

  WordPress REST API  → thegrio, theroot, newsone, capitalbnews, ebony
  Paginated HTML      → essence, blavity
  RSS (fallback only) → any site where above methods fail

Writes outputs/articles.csv and prints a per-source data quality report.
"""

import os
import pandas as pd

from scraper.rss_scraper        import scrape_rss
from scraper.wp_scraper         import scrape_wp
from scraper.html_scraper       import scrape_html
from scraper.playwright_scraper import scrape_playwright
from scraper.blavity_scraper    import scrape_blavity
from scraper.capitalb_scraper   import scrape_capitalb
from scraper.utils              import deduplicate

os.makedirs("outputs", exist_ok=True)

# ── Publication registry ──────────────────────────────────────────────────────
#
# method:       "wp"   → WordPress REST API (full 30-day coverage)
#               "html" → Paginated HTML scraping
#               "rss"  → RSS feed only (limited, last resort)
#
# rss_url:      RSS feed URL (used as fallback if primary method returns 0)

PUBLICATIONS = [
    {
        "name":     "thegrio.com",
        "method":   "wp",
        "base_url": "https://thegrio.com",
        "rss_url":  "https://thegrio.com/feed/",
    },
    {
        "name":     "theroot.com",
        "method":   "wp",
        "base_url": "https://www.theroot.com",
        "rss_url":  "https://www.theroot.com/rss/",
    },
    {
        "name":     "newsone.com",
        "method":   "wp",
        "base_url": "https://newsone.com",
        "rss_url":  "https://newsone.com/feed/",
    },
    {
        "name":     "capitalbnews.org",
        "method":   "capitalb",
        "rss_url":  "https://capitalbnews.org/feed/",
    },
    {
        "name":     "ebony.com",
        "method":   "wp",
        "base_url": "https://www.ebony.com",
        "rss_url":  "https://www.ebony.com/feed/",
    },
    {
        "name":     "essence.com",
        "method":   "html",
        "html_domain": "essence.com",
        "rss_url":  "https://www.essence.com/feed/",
    },
    {
        "name":     "blavity.com",
        "method":   "blavity",
        "rss_url":  "https://blavity.com/rss",
    },
]

SCHEMA_COLUMNS = [
    "title",
    "description",
    "source",
    "date_of_publication",
    "category",
    "author",
    "link",
]


def run_scraper(days: int = 30) -> pd.DataFrame:
    """
    Run all scrapers and return the consolidated, deduplicated DataFrame.

    Args:
        days: rolling window in days (default 30)

    Returns:
        pd.DataFrame written to outputs/articles.csv
    """
    print(f"\n[scraper] ── Starting Scrape  (window: {days} days) ──")
    all_articles: list[dict] = []

    for pub in PUBLICATIONS:
        name     = pub["name"]
        method   = pub["method"]
        articles = []

        # ── Primary method ────────────────────────────────────────────
        if method == "wp":
            articles = scrape_wp(name, pub["base_url"], days=days)

        elif method == "html":
            articles = scrape_html(name, pub["html_domain"], days=days)

        elif method == "playwright":
            articles = scrape_playwright(name, days=days)

        elif method == "blavity":
            articles = scrape_blavity(name, days=days)

        elif method == "capitalb":
            articles = scrape_capitalb(name, days=days)

        # ── RSS fallback ──────────────────────────────────────────────
        # Fall back if primary returned 0, or suspiciously few (< 5) articles
        if (not articles or len(articles) < 5) and pub.get("rss_url"):
            reason = "0 articles" if not articles else f"only {len(articles)} article(s)"
            print(f"  [scraper] ⚠ Primary method returned {reason} for {name} — falling back to RSS")
            articles = scrape_rss(name, pub["rss_url"], days=days)

        if not articles:
            print(f"  [scraper] ✗ No articles retrieved for {name}")

        all_articles.extend(articles)

    if not all_articles:
        print("[scraper] ✗ No articles scraped from any source.")
        return pd.DataFrame(columns=SCHEMA_COLUMNS)

    df = pd.DataFrame(all_articles)

    # Ensure schema columns all present
    for col in SCHEMA_COLUMNS:
        if col not in df.columns:
            df[col] = ""
    df = df[SCHEMA_COLUMNS].fillna("")

    # Deduplicate by URL
    before = len(df)
    df = df.drop_duplicates(subset=["link"]).reset_index(drop=True)
    if before > len(df):
        print(f"\n[scraper] Removed {before - len(df)} duplicate URLs ({before} → {len(df)})")

    # Sort by date descending
    df["_sort"] = pd.to_datetime(df["date_of_publication"], errors="coerce")
    df = df.sort_values("_sort", ascending=False).drop(columns=["_sort"])
    df["date_of_publication"] = pd.to_datetime(
        df["date_of_publication"], errors="coerce"
    ).dt.strftime("%Y-%m-%d").fillna("")
    df = df.reset_index(drop=True)

    _print_quality_report(df)

    # Save combined CSV
    output_path = "outputs/articles.csv"
    df.to_csv(output_path, index=False, encoding="utf-8")
    print(f"\n[scraper] ✓ Saved {len(df)} articles → {output_path}")

    # Save per-source CSVs
    for source in df["source"].unique():
        src_df = df[df["source"] == source].reset_index(drop=True)
        src_filename = source.replace(".", "_").replace("/", "_")
        src_path = f"outputs/{src_filename}.csv"
        src_df.to_csv(src_path, index=False, encoding="utf-8")
        print(f"[scraper] ✓ Saved {len(src_df)} articles → {src_path}")

    print("[scraper] ── Scrape Complete ──\n")
    return df


def _print_quality_report(df: pd.DataFrame) -> None:
    print(f"\n[scraper] ── Data Quality Report ──")
    print(f"  {'Source':<22} {'Articles':>9}  {'Date%':>6}  {'Snippet%':>8}  {'Category%':>10}")
    print(f"  {'─'*22} {'─'*9}  {'─'*6}  {'─'*8}  {'─'*10}")
    for source in sorted(df["source"].unique()):
        g = df[df["source"] == source]
        n = len(g)
        d = round((g["date_of_publication"].str.strip() != "").sum() / n * 100)
        s = round((g["description"].str.strip() != "").sum() / n * 100)
        c = round((g["category"].str.strip() != "").sum() / n * 100)
        print(f"  {source:<22} {n:>9}  {d:>5}%  {s:>7}%  {c:>9}%")
    print(f"\n  Total: {len(df)} articles")


if __name__ == "__main__":
    run_scraper()
