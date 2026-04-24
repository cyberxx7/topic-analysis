"""
synapse_scraper.py — Blavity Inc. Synapse RSS Feed Scraper

Fetches articles from the Synapse platform (synapse.blavityinc.com),
which provides a clean RSS 2.0 feed sourced directly from Blavity Inc's
WordPress backend. Covers 4 publications in one request:

  - blavity.com
  - 21ninety.com
  - travelnoire.com
  - afrotech.com

The date range is built dynamically from the first day of the current
month to the first day of the next month, matching the pipeline's
rolling window. Pagination is handled automatically.
"""

import json
import calendar
import requests
import feedparser
from datetime import datetime
from urllib.parse import urlencode, urlparse

from scraper.utils import truncate, clean_html

SYNAPSE_API = "https://synapse.blavityinc.com/api/feed"
BRANDS      = "blavity,21ninety,travelnoire,afrotech"
PER_PAGE    = 50   # max articles per page

# Map link domains → source names used in our schema
DOMAIN_TO_SOURCE = {
    "blavity.com":      "blavity.com",
    "21ninety.com":     "21ninety.com",
    "travelnoire.com":  "travelnoire.com",
    "afrotech.com":     "afrotech.com",
}


def scrape_synapse(days: int = 30) -> list[dict]:
    """
    Fetch all articles from Synapse for the current calendar month.

    Args:
        days: used only to label the window in log output;
              the actual date range is always the full current month.

    Returns:
        list of article dicts matching the pipeline schema.
    """
    after, before = _current_month_range()
    date_filter   = f"{days}d"

    print(f"  [synapse] Fetching {BRANDS} | {after[:10]} → {before[:10]}")

    all_articles: list[dict] = []
    page = 1

    while True:
        filters = json.dumps({"before": before, "after": after})
        params  = {
            "brand":      BRANDS,
            "perPage":    PER_PAGE,
            "filters":    filters,
            "dateFilter": date_filter,
            "page":       page,
        }
        url = SYNAPSE_API + "?" + urlencode(params)

        try:
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
        except requests.RequestException as e:
            print(f"  [synapse] ✗ Request failed (page {page}): {e}")
            break

        feed     = feedparser.parse(resp.content)
        entries  = feed.entries

        if not entries:
            break  # no more pages

        for entry in entries:
            article = _parse_entry(entry)
            if article:
                all_articles.append(article)

        print(f"  [synapse] Page {page}: {len(entries)} articles "
              f"(total so far: {len(all_articles)})")

        # Stop if we got fewer than a full page — no more pages exist
        if len(entries) < PER_PAGE:
            break

        page += 1

    # Deduplicate by URL
    seen: set[str] = set()
    unique = []
    for a in all_articles:
        if a["link"] not in seen:
            seen.add(a["link"])
            unique.append(a)

    print(f"  [synapse] ✓ {len(unique)} unique articles retrieved across all brands")
    return unique


def _parse_entry(entry) -> dict | None:
    """Parse a feedparser entry into our article schema."""
    link = (entry.get("link") or "").strip()
    if not link:
        return None

    source = _source_from_url(link)
    if not source:
        return None

    title = _clean(entry.get("title", ""))
    if not title or len(title) < 5:
        return None

    # Prefer summary over content for description
    description = (
        _clean(entry.get("summary", ""))
        or _clean(entry.get("content", [{}])[0].get("value", "") if entry.get("content") else "")
    )
    description = truncate(description, 500)

    # Date
    pub_date = entry.get("published_parsed") or entry.get("updated_parsed")
    if pub_date:
        date_str = datetime(*pub_date[:6]).strftime("%Y-%m-%d")
    else:
        date_str = ""

    # Category — feedparser puts these in entry.tags
    category = ""
    tags = entry.get("tags", [])
    if tags:
        category = tags[0].get("term", "").strip().title()

    # Author
    author = _clean(entry.get("author", ""))

    return {
        "title":               title[:500],
        "description":         description,
        "source":              source,
        "date_of_publication": date_str,
        "category":            category[:100],
        "author":              author[:150],
        "link":                link,
    }


def _source_from_url(url: str) -> str | None:
    """Extract the publication source name from the article URL."""
    try:
        netloc = urlparse(url).netloc.lower().lstrip("www.")
        for domain, source in DOMAIN_TO_SOURCE.items():
            if domain in netloc:
                return source
    except Exception:
        pass
    return None


def _current_month_range() -> tuple[str, str]:
    """
    Return (after, before) ISO timestamps for the current calendar month.

    Example (April 2026):
        after  = "2026-04-01T00:00:00.000Z"
        before = "2026-05-01T00:00:00.000Z"
    """
    now   = datetime.utcnow()
    year  = now.year
    month = now.month

    after = f"{year:04d}-{month:02d}-01T00:00:00.000Z"

    # First day of next month
    if month == 12:
        before = f"{year + 1:04d}-01-01T00:00:00.000Z"
    else:
        before = f"{year:04d}-{month + 1:02d}-01T00:00:00.000Z"

    return after, before


def _clean(text: str) -> str:
    if not text:
        return ""
    return clean_html(str(text)).strip()
