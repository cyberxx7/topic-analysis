"""
wp_scraper.py — WordPress REST API Scraper

Fetches ALL articles published within the rolling window by paginating
through the /wp-json/wp/v2/posts endpoint with a date filter.

Supports: thegrio.com, theroot.com, newsone.com, capitalbnews.org, ebony.com
"""

import time
import requests
from datetime import datetime, timezone

from scraper.utils import (
    get_cutoff_date,
    format_date,
    clean_html,
    truncate,
    HEADERS,
)

# WP REST API settings
PER_PAGE    = 100          # max allowed by WP
REQUEST_DELAY = 0.4        # seconds between pages
MAX_PAGES   = 50           # safety cap (~5000 articles per source)
TIMEOUT     = 15

# Fields to request + embed taxonomy terms for category names
WP_FIELDS  = "id,date,title,link,excerpt,categories,author,author_name,author_info,authors,yoast_head_json,_links"
WP_EMBED   = "wp:term,wp:author"  # embeds category and author objects inline


def scrape_wp(source_name: str, base_url: str, days: int = 30) -> list[dict]:
    """
    Scrape all articles within the rolling window via WordPress REST API.

    Args:
        source_name:  domain key (e.g. "thegrio.com")
        base_url:     site root URL (e.g. "https://thegrio.com")
        days:         rolling window in days

    Returns:
        List of article dicts with keys:
          title, description, source, date_of_publication, category, link
    """
    cutoff    = get_cutoff_date(days)
    after_str = cutoff.strftime("%Y-%m-%dT%H:%M:%S")
    endpoint  = f"{base_url.rstrip('/')}/wp-json/wp/v2/posts"

    print(f"  [wp]  Fetching {source_name} via WP REST API (after {after_str[:10]})")

    # First request — get total count
    params = {
        "per_page": PER_PAGE,
        "after":    after_str,
        "_fields":  WP_FIELDS,
        "_embed":   WP_EMBED,
        "page":     1,
        "orderby":  "date",
        "order":    "desc",
    }

    try:
        r = _get(endpoint, params)
    except Exception as exc:
        print(f"  [wp]  ✗ {source_name}: {exc}")
        return []

    total_articles = int(r.headers.get("X-WP-Total", 0))
    total_pages    = int(r.headers.get("X-WP-TotalPages", 1))
    total_pages    = min(total_pages, MAX_PAGES)

    print(f"  [wp]  {source_name}: {total_articles} articles across {total_pages} pages")

    articles  = []
    page_data = r.json()

    if not isinstance(page_data, list):
        print(f"  [wp]  ✗ {source_name}: unexpected response format")
        return []

    # Parse first page
    for post in page_data:
        article = _parse_post(post, source_name)
        if article:
            articles.append(article)

    # Fetch remaining pages
    for page in range(2, total_pages + 1):
        time.sleep(REQUEST_DELAY)
        params["page"] = page
        try:
            r = _get(endpoint, params)
            page_data = r.json()
            if not isinstance(page_data, list) or not page_data:
                break
            for post in page_data:
                article = _parse_post(post, source_name)
                if article:
                    articles.append(article)
        except Exception as exc:
            print(f"  [wp]  ⚠ {source_name} page {page}: {exc}")
            break

        # Early stop if we got fewer results than requested (last page)
        if len(page_data) < PER_PAGE:
            break

    print(f"  [wp]  ✓ {source_name}: {len(articles)} articles retrieved")
    return articles


def _get(endpoint: str, params: dict) -> requests.Response:
    """Make a GET request with retries on transient failures."""
    for attempt in range(3):
        try:
            r = requests.get(endpoint, params=params, headers=HEADERS,
                             timeout=TIMEOUT)
            if r.status_code == 400:
                # WP returns 400 when page exceeds total — normal end condition
                raise StopIteration("end of results")
            r.raise_for_status()
            return r
        except StopIteration:
            raise
        except requests.RequestException as exc:
            if attempt == 2:
                raise
            time.sleep(1.5 * (attempt + 1))


def _parse_post(post: dict, source_name: str) -> dict | None:
    """Parse a WP REST API post object into the article schema."""

    # Title
    raw_title = post.get("title", {})
    title = clean_html(
        raw_title.get("rendered", "") if isinstance(raw_title, dict) else str(raw_title)
    ).strip()
    if not title:
        return None

    # URL
    link = (post.get("link", "") or "").strip()
    if not link:
        return None

    # Date — WP always returns ISO 8601 in site local time; we treat as UTC
    raw_date = post.get("date", "") or ""
    date_str = raw_date[:10] if raw_date else ""  # YYYY-MM-DD

    # Snippet — prefer yoast meta description, then excerpt
    snippet = ""
    yoast = post.get("yoast_head_json", {}) or {}
    if isinstance(yoast, dict):
        og_desc = yoast.get("og_description", "") or ""
        meta_desc = (yoast.get("description", "") or
                     (yoast.get("schema", {}) or {})
                     .get("description", "") or "")
        snippet = clean_html(og_desc or meta_desc)

    if not snippet:
        raw_excerpt = post.get("excerpt", {})
        excerpt_html = (
            raw_excerpt.get("rendered", "")
            if isinstance(raw_excerpt, dict) else str(raw_excerpt)
        )
        snippet = clean_html(excerpt_html)

    snippet = truncate(snippet, 500)

    # Category — from embedded or tags, fall back to URL slug
    category = _extract_wp_category(post, link)

    author = _extract_wp_author(post)

    return {
        "title":               title[:500],
        "description":         snippet,
        "source":              source_name,
        "date_of_publication": date_str,
        "category":            category[:100],
        "link":                link,
        "author":              author[:150],
    }


def _extract_wp_author(post: dict) -> str:
    """
    Extract author name from a WP post.
    Each site exposes this differently — try all known patterns.
    """
    # Pattern 1: direct author_name field (thegrio)
    name = post.get("author_name", "") or ""
    if name:
        return name.strip()

    # Pattern 2: author_info.display_name (ebony)
    info = post.get("author_info", {}) or {}
    if isinstance(info, dict):
        name = info.get("display_name", "") or ""
        if name:
            return name.strip()

    # Pattern 3: authors[] array with display_name (theroot)
    authors = post.get("authors", []) or []
    if authors and isinstance(authors, list):
        name = authors[0].get("display_name", "") or ""
        if name:
            return name.strip()

    # Pattern 4: yoast author field
    yoast = post.get("yoast_head_json", {}) or {}
    if isinstance(yoast, dict):
        name = yoast.get("author", "") or ""
        if name:
            return name.strip()

    # Pattern 5: embedded wp:author (not all sites allow this)
    embedded = post.get("_embedded", {}) or {}
    wp_authors = embedded.get("wp:author", []) or []
    if wp_authors and isinstance(wp_authors, list):
        name = wp_authors[0].get("name", "") or ""
        if name:
            return name.strip()

    return ""


def _extract_wp_category(post: dict, link: str) -> str:
    """
    Extract category label from a WP post.
    Priority: embedded wp:term categories → URL path slug.
    """
    # Embedded taxonomy terms (requires _embed=wp:term in request)
    embedded = post.get("_embedded", {}) or {}
    term_groups = embedded.get("wp:term", []) or []
    for group in term_groups:
        cats = [
            t.get("name", "").strip()
            for t in group
            if isinstance(t, dict) and t.get("taxonomy") == "category"
            and t.get("name", "").lower() not in ("uncategorized", "")
        ]
        if cats:
            return cats[0].title()

    # Fall back to URL-path slug
    path  = re.sub(r"^https?://[^/]+", "", link)
    parts = [p for p in path.split("/") if p and not re.match(r"^\d{4}$", p)]
    if parts:
        slug = parts[0].replace("-", " ").replace("_", " ").title()
        if len(slug.split()) <= 3 and not re.search(r"\d", slug):
            return slug
    return ""
