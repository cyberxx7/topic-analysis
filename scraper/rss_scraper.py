"""
rss_scraper.py — Robust RSS Feed Scraper

Fetches and parses RSS/Atom feeds for all 7 Black media publications.
Per-source configuration handles each site's unique quirks:
  - Date fields (published_parsed preferred over string)
  - Category extraction (tags, URL path fallback)
  - Snippet extraction (content vs summary, HTML cleaning)
  - Minimum snippet length enforcement

Returns a list of validated article dicts matching the data schema.
"""

import time
import requests
import feedparser

from scraper.utils import (
    get_cutoff_date,
    parse_entry_date,
    is_within_window,
    format_date,
    clean_html,
    truncate,
    category_from_url,
    HEADERS,
)

# ── Per-source configuration ──────────────────────────────────────────────────
#
# snippet_field:  which RSS field to prefer for the article snippet
#   "content"   → entry.content[0].value  (full article body excerpt)
#   "summary"   → entry.summary           (feed-provided excerpt)
#   "both"      → try content first, fall back to summary
#
# category_source:
#   "tags"      → use entry.tags[0].term
#   "url"       → derive category from the article URL path
#   "both"      → try tags first, fall back to URL
#
# snippet_min_chars: re-fetch article page if snippet is shorter than this

SOURCE_CONFIG = {
    "thegrio.com": {
        "snippet_field": "both",
        "category_source": "tags",
        "snippet_min_chars": 80,
    },
    "theroot.com": {
        # Summary contains HTML + "appeared first on" boilerplate; content is better
        "snippet_field": "both",
        "category_source": "tags",
        "snippet_min_chars": 80,
    },
    "newsone.com": {
        "snippet_field": "both",
        "category_source": "tags",
        "snippet_min_chars": 80,
    },
    "capitalbnews.org": {
        # Rich summaries, HTML-encoded
        "snippet_field": "both",
        "category_source": "tags",
        "snippet_min_chars": 100,
    },
    "blavity.com": {
        "snippet_field": "both",
        "category_source": "tags",
        "snippet_min_chars": 80,
    },
    "essence.com": {
        # No category tags in feed — derive from URL path
        "snippet_field": "both",
        "category_source": "url",
        "snippet_min_chars": 80,
    },
    "ebony.com": {
        "snippet_field": "both",
        "category_source": "tags",
        "snippet_min_chars": 80,
    },
}

# Snippet length cap (chars) — enough context without bloating the CSV
SNIPPET_MAX_CHARS = 500


def scrape_rss(source_name: str, feed_url: str, days: int = 30) -> list[dict]:
    """
    Scrape articles from an RSS/Atom feed within the rolling window.

    Args:
        source_name:  domain key (e.g. "thegrio.com") used for config lookup
                      and stored in the 'source' field
        feed_url:     full URL of the RSS/Atom feed
        days:         rolling window size in days (default 30)

    Returns:
        List of article dicts with keys:
          title, description, source, date_of_publication, category, link
    """
    cutoff = get_cutoff_date(days)
    config = SOURCE_CONFIG.get(source_name, {
        "snippet_field": "both",
        "category_source": "both",
        "snippet_min_chars": 80,
    })

    print(f"  [rss] Fetching {source_name} → {feed_url}")

    feed = _fetch_feed(feed_url)
    if feed is None:
        return []

    articles = []
    skipped_old = 0

    for entry in feed.entries:
        try:
            article = _parse_entry(entry, source_name, config)
        except Exception as exc:
            print(f"  [rss]   ✗ parse error ({source_name}): {exc}")
            continue

        if article is None:
            continue

        # Date-window filter
        dt = parse_entry_date(entry)
        if not is_within_window(dt, cutoff):
            skipped_old += 1
            continue

        articles.append(article)
        time.sleep(0.03)  # gentle rate-limiting

    print(
        f"  [rss]   ✓ {source_name}: {len(articles)} articles "
        f"(skipped {skipped_old} outside window)"
    )
    return articles


# ── Internal helpers ──────────────────────────────────────────────────────────

def _fetch_feed(feed_url: str) -> feedparser.FeedParserDict | None:
    """Fetch and parse the RSS feed. Returns None on failure."""
    try:
        feed = feedparser.parse(
            feed_url,
            request_headers=HEADERS,
            agent=HEADERS["User-Agent"],
        )
    except Exception as exc:
        print(f"  [rss]   ✗ network error: {exc}")
        return None

    if feed.bozo and not feed.entries:
        print(f"  [rss]   ✗ malformed feed (bozo={feed.bozo_exception})")
        return None

    if not feed.entries:
        print(f"  [rss]   ✗ feed returned 0 entries")
        return None

    return feed


def _parse_entry(
    entry: feedparser.FeedParserDict,
    source_name: str,
    config: dict,
) -> dict | None:
    """
    Parse a single RSS entry into the article schema.
    Returns None if the entry is missing required fields.
    """
    # ── Title ────────────────────────────────────────────────────────
    title = clean_html(getattr(entry, "title", "") or "").strip()
    if not title:
        return None

    # ── URL ──────────────────────────────────────────────────────────
    link = (getattr(entry, "link", "") or "").strip()
    if not link:
        return None

    # ── Date ─────────────────────────────────────────────────────────
    dt = parse_entry_date(entry)
    date_str = format_date(dt)  # YYYY-MM-DD or ""

    # ── Category ─────────────────────────────────────────────────────
    category = _extract_category(entry, link, config["category_source"])

    # ── Snippet ──────────────────────────────────────────────────────
    snippet = _extract_snippet(entry, config["snippet_field"])
    snippet = truncate(snippet, SNIPPET_MAX_CHARS)

    # Warn if snippet is suspiciously short (data quality flag)
    if snippet and len(snippet) < config["snippet_min_chars"]:
        print(
            f"  [rss]   ⚠ short snippet ({len(snippet)} chars) "
            f"for: {title[:60]}"
        )

    # ── Author ───────────────────────────────────────────────────────
    author = clean_html(getattr(entry, "author", "") or "").strip()

    return {
        "title":               title[:500],
        "description":         snippet,
        "source":              source_name,
        "date_of_publication": date_str,
        "category":            category[:100],
        "author":              author[:150],
        "link":                link,
    }


def _extract_snippet(entry: feedparser.FeedParserDict, field_pref: str) -> str:
    """
    Extract and clean the best available snippet from an RSS entry.

    Strategy order (based on field_pref):
      content → entry.content[0].value  (usually longer, full-body excerpt)
      summary → entry.summary           (feed-defined excerpt)
      both    → try content first, then summary; pick the longer clean result
    """
    content_text = ""
    summary_text = ""

    # content field (not all feeds include this)
    if hasattr(entry, "content") and entry.content:
        raw = entry.content[0].get("value", "") or ""
        content_text = clean_html(raw).strip()

    # summary field
    raw_summary = getattr(entry, "summary", "") or ""
    summary_text = clean_html(raw_summary).strip()

    if field_pref == "content":
        return content_text or summary_text
    if field_pref == "summary":
        return summary_text or content_text

    # "both" — pick the longer of the two
    return content_text if len(content_text) >= len(summary_text) else summary_text


def _extract_category(
    entry: feedparser.FeedParserDict,
    link: str,
    source_pref: str,
) -> str:
    """
    Extract the article category.

    Strategy:
      tags  → entry.tags[0].term
      url   → first meaningful path segment of the article URL
      both  → try tags first, fall back to URL path
    """
    tag_category = ""
    url_category = ""

    # From RSS tags
    tags = getattr(entry, "tags", []) or []
    if tags:
        # Some feeds include multiple tags; join them or use the first
        terms = [t.get("term", "").strip() for t in tags if t.get("term", "").strip()]
        if terms:
            # Use the first tag as primary category; append up to 2 more as context
            tag_category = terms[0].title()

    # From URL path
    url_category = category_from_url(link)

    if source_pref == "tags":
        return tag_category or url_category
    if source_pref == "url":
        return url_category or tag_category

    # "both" — prefer tags, fall back to URL
    return tag_category or url_category
