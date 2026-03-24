"""
scraper/utils.py — Shared Scraper Utilities
"""

import re
import time
import hashlib
from datetime import datetime, timedelta, timezone
from bs4 import BeautifulSoup


# ── Date helpers ──────────────────────────────────────────────────────────────

def get_cutoff_date(days: int = 30) -> datetime:
    """Return timezone-aware UTC cutoff date N days ago."""
    return datetime.now(timezone.utc) - timedelta(days=days)


def struct_time_to_datetime(st) -> datetime | None:
    """Convert feedparser's time.struct_time (always UTC) to aware datetime."""
    if st is None:
        return None
    try:
        return datetime(
            st.tm_year, st.tm_mon, st.tm_mday,
            st.tm_hour, st.tm_min, st.tm_sec,
            tzinfo=timezone.utc,
        )
    except (ValueError, AttributeError):
        return None


def parse_date_string(raw: str) -> datetime | None:
    """
    Parse a date string in multiple formats.
    Returns timezone-aware datetime or None.
    """
    if not raw:
        return None

    # Normalise "UTC" timezone suffix → "+0000"
    raw = re.sub(r"\bUTC\b", "+0000", raw.strip())

    formats = [
        "%a, %d %b %Y %H:%M:%S %z",
        "%a, %d %b %Y %H:%M:%S GMT",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%B %d, %Y",
        "%b %d, %Y",
        "%d %B %Y",
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(raw, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            continue
    return None


def parse_entry_date(entry) -> datetime | None:
    """
    Best-effort date extraction from a feedparser entry.
    Priority: published_parsed → updated_parsed → published string → updated string
    """
    # struct_time fields (feedparser always provides these in UTC when present)
    for field in ("published_parsed", "updated_parsed"):
        st = getattr(entry, field, None)
        dt = struct_time_to_datetime(st)
        if dt:
            return dt

    # Fall back to string fields
    for field in ("published", "updated"):
        raw = getattr(entry, field, None)
        if raw:
            dt = parse_date_string(raw)
            if dt:
                return dt

    return None


def is_within_window(dt: datetime | None, cutoff: datetime) -> bool:
    """Return True if dt is within the rolling window (or unknown)."""
    if dt is None:
        return True  # include if we cannot determine date
    return dt >= cutoff


def format_date(dt: datetime | None) -> str:
    """Format datetime to YYYY-MM-DD, or empty string."""
    return dt.strftime("%Y-%m-%d") if dt else ""


# ── Text helpers ──────────────────────────────────────────────────────────────

def clean_html(text: str) -> str:
    """Strip HTML tags and decode entities, normalize whitespace."""
    if not text:
        return ""
    soup = BeautifulSoup(text, "html.parser")
    # Remove script/style blocks entirely
    for tag in soup(["script", "style", "aside", "figure"]):
        tag.decompose()
    cleaned = soup.get_text(separator=" ")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    # Remove common RSS boilerplate fragments
    cleaned = re.sub(
        r"The post .+ appeared first on .+\.$", "", cleaned, flags=re.IGNORECASE
    ).strip()
    return cleaned


def truncate(text: str, max_chars: int = 500) -> str:
    """Truncate at a sentence boundary near max_chars."""
    if len(text) <= max_chars:
        return text
    cut = text[:max_chars]
    # Try to cut at last sentence end
    for sep in (". ", "! ", "? "):
        idx = cut.rfind(sep)
        if idx > max_chars * 0.6:
            return cut[: idx + 1].strip()
    return cut.rstrip() + "…"


def category_from_url(url: str) -> str:
    """
    Extract a category slug from a URL path.
    e.g. https://www.essence.com/beauty/article-slug/ → "Beauty"
    """
    if not url:
        return ""
    # Strip domain, split path
    path = re.sub(r"^https?://[^/]+", "", url)
    parts = [p for p in path.split("/") if p and not re.match(r"^\d{4}$", p)]
    if not parts:
        return ""
    # First meaningful segment, title-cased
    slug = parts[0].replace("-", " ").replace("_", " ").title()
    # Reject segments that look like article slugs (too many words or digits)
    if len(slug.split()) > 3 or re.search(r"\d", slug):
        return ""
    return slug


def deduplicate(articles: list, key: str = "link") -> list:
    """Remove duplicate articles by the given key."""
    seen = set()
    unique = []
    for article in articles:
        val = article.get(key, "")
        if val and val not in seen:
            seen.add(val)
            unique.append(article)
    return unique


# ── HTTP headers ──────────────────────────────────────────────────────────────

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}
