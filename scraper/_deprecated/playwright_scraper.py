"""
playwright_scraper.py — Headless Browser Scraper (Blavity)

Used for JavaScript-rendered sites that block standard HTTP scraping.
Renders pages using a real Chromium browser via Playwright, then
extracts article metadata from the rendered DOM.

Currently used for: blavity.com
"""

import re
import time
from datetime import datetime, timezone

from scraper.utils import (
    get_cutoff_date,
    parse_date_string as parse_date,
    is_within_window,
    clean_html,
    truncate,
    category_from_url,
    format_date,
)

# Categories to scrape on Blavity
BLAVITY_CATEGORIES = [
    "https://blavity.com/category/black-news",
    "https://blavity.com/category/politics",
    "https://blavity.com/category/social-justice",
    "https://blavity.com/category/entertainment",
    "https://blavity.com/category/health",
    "https://blavity.com/category/education",
    "https://blavity.com/category/business-technology",
    "https://blavity.com/category/lifestyle",
]

MAX_PAGES_PER_CATEGORY = 8
PAGE_LOAD_TIMEOUT      = 20_000   # ms
ARTICLE_LOAD_TIMEOUT   = 15_000   # ms
SCROLL_PAUSE           = 1.2      # seconds — let lazy-loaded content render


def scrape_playwright(source_name: str, days: int = 30) -> list[dict]:
    """
    Scrape articles from a JS-rendered site using Playwright (Chromium).

    Args:
        source_name:  domain key (e.g. "blavity.com")
        days:         rolling window in days

    Returns:
        List of article dicts.
    """
    try:
        from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
    except ImportError:
        print("  [pw]  ✗ Playwright not installed. Run: pip install playwright && playwright install chromium")
        return []

    cutoff   = get_cutoff_date(days)
    articles = []
    seen     = set()

    print(f"  [pw]  Launching Chromium for {source_name}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 900},
        )
        page = context.new_page()
        # Block ads/trackers to speed up loads
        page.route(
            re.compile(r"\.(png|jpg|gif|svg|woff2?|mp4|webp)$"),
            lambda route: route.abort(),
        )

        hit_old = False
        for category_url in BLAVITY_CATEGORIES:
            if hit_old:
                break

            for page_num in range(1, MAX_PAGES_PER_CATEGORY + 1):
                url = category_url if page_num == 1 else f"{category_url}?page={page_num}"

                try:
                    page.goto(url, timeout=PAGE_LOAD_TIMEOUT, wait_until="domcontentloaded")
                    # Scroll to trigger lazy loading
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    time.sleep(SCROLL_PAUSE)
                except PWTimeout:
                    print(f"  [pw]  ⚠ Timeout loading {url}")
                    break

                # Extract article links from listing page
                links = _extract_links(page, "blavity.com")
                if not links:
                    break

                new_links = [l for l in links if l not in seen]
                if not new_links:
                    break

                for link in new_links:
                    seen.add(link)
                    try:
                        article = _scrape_article_page(page, link, source_name)
                    except Exception as exc:
                        print(f"  [pw]  ⚠ {link[:60]}: {exc}")
                        continue

                    if not article:
                        continue

                    dt = parse_date(article["date_of_publication"])
                    if dt and not is_within_window(dt, cutoff):
                        hit_old = True
                        break

                    articles.append(article)

                if hit_old:
                    break

        browser.close()

    print(f"  [pw]  ✓ {source_name}: {len(articles)} articles retrieved")
    return articles


def _extract_links(page, domain: str) -> list[str]:
    """Extract article URLs from the current listing page."""
    anchors = page.query_selector_all("a[href]")
    links   = []
    for a in anchors:
        try:
            href = a.get_attribute("href") or ""
        except Exception:
            continue
        if not href or domain not in href:
            continue
        # Skip category/tag/author pages
        if re.search(r"/(category|tag|author|page)/", href):
            continue
        # Must look like an article slug (has path beyond root)
        path = re.sub(r"^https?://[^/]+", "", href)
        if len(path.strip("/").split("/")) < 1:
            continue
        if href not in links:
            links.append(href)
    return links


def _scrape_article_page(page, url: str, source_name: str) -> dict | None:
    """Render and extract metadata from an individual article page."""
    from playwright.sync_api import TimeoutError as PWTimeout

    try:
        page.goto(url, timeout=ARTICLE_LOAD_TIMEOUT, wait_until="domcontentloaded")
    except PWTimeout:
        return None

    # Extract via meta tags (most reliable, present immediately after DOM load)
    title = (
        _get_meta(page, "og:title")
        or _get_meta(page, "twitter:title")
        or page.title()
        or ""
    )
    title = clean_html(title).strip()
    if not title:
        return None

    snippet = (
        _get_meta(page, "description")
        or _get_meta(page, "og:description")
        or _get_meta(page, "twitter:description")
        or ""
    )
    snippet = truncate(clean_html(snippet), 500)

    raw_date = (
        _get_meta(page, "article:published_time")
        or _get_meta(page, "pubdate")
        or _get_time_element(page)
        or ""
    )
    dt = parse_date(raw_date) if raw_date else None
    date_str = dt.strftime("%Y-%m-%d") if dt else raw_date[:10] if raw_date else ""

    category = (
        _get_meta(page, "article:section")
        or category_from_url(url)
    )
    category = clean_html(category).title()

    author = (
        _get_meta(page, "author")
        or _get_meta(page, "article:author")
        or _get_schema_author(page)
        or ""
    )
    author = clean_html(author).strip()

    return {
        "title":               title[:500],
        "description":         snippet,
        "source":              source_name,
        "date_of_publication": date_str,
        "category":            category[:100],
        "author":              author[:150],
        "link":                url,
    }


# ── Page helpers ──────────────────────────────────────────────────────────────

def _get_meta(page, name: str) -> str:
    el = (
        page.query_selector(f'meta[property="{name}"]')
        or page.query_selector(f'meta[name="{name}"]')
    )
    return (el.get_attribute("content") or "") if el else ""


def _get_time_element(page) -> str:
    el = page.query_selector("time[datetime]") or page.query_selector("time")
    if not el:
        return ""
    return el.get_attribute("datetime") or el.inner_text() or ""


def _get_schema_author(page) -> str:
    """Try to extract author from JSON-LD schema on the page."""
    try:
        scripts = page.query_selector_all('script[type="application/ld+json"]')
        import json
        for s in scripts:
            data = json.loads(s.inner_text() or "{}")
            for item in (data if isinstance(data, list) else [data]):
                if isinstance(item, dict):
                    author = item.get("author", {})
                    if isinstance(author, dict):
                        return author.get("name", "")
                    if isinstance(author, list) and author:
                        return author[0].get("name", "")
    except Exception:
        pass
    return ""
