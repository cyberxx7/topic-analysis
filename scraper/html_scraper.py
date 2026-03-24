"""
html_scraper.py — Paginated HTML Scraper

Used for sites that block or have broken REST APIs:
  - Blavity  (JS-heavy SPA, no public WP API)
  - Essence  (WP API returns corrupt dates)

Strategy: scrape paginated category listing pages, extract article cards,
then fetch each article page for accurate metadata.
"""

import re
import time
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone

from scraper.utils import (
    get_cutoff_date,
    parse_date_string as parse_date,
    is_within_window,
    clean_html as clean_text,
    format_date,
    truncate,
    category_from_url,
    HEADERS,
)

# ── Per-source configuration ──────────────────────────────────────────────────

SOURCE_CONFIGS = {
    "essence.com": {
        # Category listing pages to iterate through
        "listing_pages": [
            "https://www.essence.com/news/",
            "https://www.essence.com/news/money-career/",
            "https://www.essence.com/news/politics/",
            "https://www.essence.com/lifestyle/",
            "https://www.essence.com/entertainment/",
            "https://www.essence.com/fashion/",
            "https://www.essence.com/beauty/",
            "https://www.essence.com/health-wellness/",
        ],
        # Pagination: append ?page=N or /page/N/
        "pagination_style": "path",    # uses /page/2/, /page/3/ etc.
        "max_pages":        15,
        "article_selector": "h2 a, h3 a, .article-card a, .card-title a, article a[href]",
        "title_selector":   "h1.entry-title, h1.article__title, h1",
        "desc_selector":    "meta[name='description'], meta[property='og:description']",
        "date_selector":    "meta[property='article:published_time'], time[datetime]",
        "category_selector":"meta[property='article:section']",
        "page_delay":       0.6,
        "article_delay":    0.5,
    },
    "blavity.com": {
        "listing_pages": [
            "https://blavity.com/category/black-news",
            "https://blavity.com/category/politics",
            "https://blavity.com/category/entertainment",
            "https://blavity.com/category/social-justice",
            "https://blavity.com/category/health",
            "https://blavity.com/category/education",
            "https://blavity.com/category/business-technology",
        ],
        "pagination_style": "query",   # uses ?page=N
        "max_pages":        10,
        "article_selector": "a.article-card__link, h2 a, h3 a, .post-title a, article a",
        "title_selector":   "h1.article-title, h1.entry-title, h1",
        "desc_selector":    "meta[name='description'], meta[property='og:description']",
        "date_selector":    "meta[property='article:published_time'], time[datetime]",
        "category_selector":"meta[property='article:section'], .category a",
        "page_delay":       0.8,
        "article_delay":    0.6,
    },
}

REQUEST_TIMEOUT = 15


def scrape_html(source_name: str, domain: str, days: int = 30) -> list[dict]:
    """
    Scrape articles from paginated HTML listing pages.

    Args:
        source_name: domain key (e.g. "essence.com")
        domain:      config key matching SOURCE_CONFIGS
        days:        rolling window in days

    Returns:
        List of article dicts.
    """
    config = SOURCE_CONFIGS.get(domain)
    if not config:
        print(f"  [html] No config for: {domain}")
        return []

    cutoff   = get_cutoff_date(days)
    articles = []
    seen     = set()

    print(f"  [html] Scraping {source_name} via paginated HTML")

    for listing_url in config["listing_pages"]:
        page_articles, stop = _scrape_listing(
            listing_url, source_name, config, cutoff, seen
        )
        articles.extend(page_articles)
        if stop:
            break  # hit articles older than window — no need to keep paginating

    print(f"  [html] ✓ {source_name}: {len(articles)} articles retrieved")
    return articles


# ── Internal: listing page pagination ────────────────────────────────────────

def _scrape_listing(
    base_url: str,
    source_name: str,
    config: dict,
    cutoff,
    seen: set,
) -> tuple[list, bool]:
    """Paginate through a single listing URL. Returns (articles, stop_flag)."""
    articles    = []
    hit_old_article = False

    for page_num in range(1, config["max_pages"] + 1):
        url = _paginate(base_url, page_num, config["pagination_style"])
        links = _get_article_links(url, config["article_selector"], source_name)

        if not links:
            break

        for link in links:
            if link in seen:
                continue
            seen.add(link)

            time.sleep(config["article_delay"])
            article = _scrape_article(link, source_name, config)
            if not article:
                continue

            # Date-window check
            dt = parse_date(article["date_of_publication"])
            if dt and not is_within_window(dt, cutoff):
                hit_old_article = True
                continue

            articles.append(article)

        if hit_old_article:
            break  # rest of pages will be older

        time.sleep(config["page_delay"])

    return articles, hit_old_article


def _paginate(base_url: str, page: int, style: str) -> str:
    if page == 1:
        return base_url
    if style == "path":
        return base_url.rstrip("/") + f"/page/{page}/"
    return base_url + (f"?page={page}" if "?" not in base_url else f"&page={page}")


def _get_article_links(listing_url: str, selector: str, source_name: str) -> list:
    """Fetch listing page and return unique article URLs."""
    try:
        r = requests.get(listing_url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        if r.status_code == 404:
            return []
        r.raise_for_status()
    except requests.RequestException as exc:
        print(f"  [html] ⚠ listing page {listing_url}: {exc}")
        return []

    soup  = BeautifulSoup(r.text, "html.parser")
    links = []
    domain = re.sub(r"^https?://", "", listing_url).split("/")[0]

    for a in soup.select(selector):
        href = (a.get("href") or "").strip()
        if not href:
            continue
        if href.startswith("/"):
            href = f"https://{domain}{href}"
        # Only include actual article URLs for this domain
        if domain not in href:
            continue
        # Filter out pagination/category/tag links
        if re.search(r"/(category|tag|author|page)/", href):
            continue
        if href not in links:
            links.append(href)

    return links


# ── Internal: individual article page ────────────────────────────────────────

def _scrape_article(url: str, source_name: str, config: dict) -> dict | None:
    """Fetch an article page and extract title, snippet, date, category."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        if r.status_code in (404, 410):
            return None
        r.raise_for_status()
    except requests.RequestException:
        return None

    soup = BeautifulSoup(r.text, "html.parser")

    # Title
    title = _meta(soup, "og:title") or _tag_text(soup, config["title_selector"])
    if not title:
        title = clean_text(soup.title.get_text()) if soup.title else ""
    title = clean_text(title).strip()
    if not title:
        return None

    # Snippet — prefer meta description
    snippet = (
        _meta(soup, "description")
        or _meta(soup, "og:description")
        or _meta(soup, "twitter:description")
        or _tag_text(soup, config["desc_selector"])
    )
    snippet = truncate(clean_text(snippet), 500)

    # Date — prefer meta tags (most reliable)
    date_str = (
        _meta_attr(soup, "article:published_time")
        or _meta_attr(soup, "pubdate")
        or _time_element(soup)
        or _tag_attr(soup, config["date_selector"])
    )
    # Normalise to YYYY-MM-DD
    dt = parse_date(date_str) if date_str else None
    date_out = dt.strftime("%Y-%m-%d") if dt else date_str[:10] if date_str else ""

    # Category — prefer og:article:section or URL
    category = (
        _meta_attr(soup, "article:section")
        or _tag_text(soup, config["category_selector"])
        or category_from_url(url)
    )
    category = clean_text(category).title()

    # Author — try common meta tags
    author = (
        _meta(soup, "author")
        or _meta(soup, "article:author")
        or _tag_text(soup, ".author-name, .byline, [rel='author']")
    )
    author = clean_text(author).strip()

    return {
        "title":               title[:500],
        "description":         snippet,
        "source":              source_name,
        "date_of_publication": date_out,
        "category":            category[:100],
        "author":              author[:150],
        "link":                url,
    }


# ── HTML helpers ──────────────────────────────────────────────────────────────

def _meta(soup: BeautifulSoup, prop: str) -> str:
    """Get meta tag content by name or property."""
    tag = (soup.find("meta", {"property": prop})
           or soup.find("meta", {"name": prop}))
    return (tag.get("content", "") or "") if tag else ""


def _meta_attr(soup: BeautifulSoup, prop: str) -> str:
    """Alias for _meta — returns content attribute."""
    return _meta(soup, prop)


def _tag_text(soup: BeautifulSoup, selector: str) -> str:
    """Get text content of the first matching element."""
    el = soup.select_one(selector)
    if not el:
        return ""
    content = el.get("content") or el.get("datetime") or el.get_text()
    return (content or "").strip()


def _tag_attr(soup: BeautifulSoup, selector: str) -> str:
    """Get datetime/content attribute of the first matching element."""
    el = soup.select_one(selector)
    if not el:
        return ""
    return el.get("content") or el.get("datetime") or ""


def _time_element(soup: BeautifulSoup) -> str:
    """Find any <time> element and return its datetime attribute or text."""
    el = soup.find("time")
    if not el:
        return ""
    return el.get("datetime") or el.get_text().strip()
