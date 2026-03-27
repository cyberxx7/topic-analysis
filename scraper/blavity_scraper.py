"""
blavity_scraper.py — Blavity Category + Playwright Scraper

Blavity is a JS-rendered SPA — sitemap returns HTML, RSS caps at 10 items.

Strategy:
  1. Playwright headless browser — scrapes 8 category pages with pagination
  2. Requests-based category pagination fallback (if Playwright unavailable)

Filters to the rolling 30-day window. Articles without a parseable date
are skipped.
"""

import re
import json
import time
from datetime import datetime, timedelta
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from scraper.utils import get_cutoff_date, truncate, HEADERS

DOMAIN = "blavity.com"
BASE_URL = f"https://{DOMAIN}"

CATEGORIES = [
    "/categories/black-news",
    "/categories/politics",
    "/categories/social-justice",
    "/categories/entertainment",
    "/categories/health",
    "/categories/education",
    "/categories/business-technology",
    "/categories/lifestyle",
]

MAX_PAGES_PER_CATEGORY = 10
PAGE_LOAD_TIMEOUT      = 20_000
SCROLL_PAUSE           = 1.2


# ── Public entry point ────────────────────────────────────────────────────────

def scrape_blavity(source_name: str, days: int = 30) -> list[dict]:
    cutoff_dt = datetime.now() - timedelta(days=days)

    print(f"  [blavity] Scraping via Playwright category pages...")
    articles = _scrape_via_playwright(source_name, cutoff_dt)

    if not articles:
        print(f"  [blavity] Playwright returned 0 — trying requests fallback...")
        articles = _scrape_via_requests(source_name, cutoff_dt)

    print(f"  [blavity] ✓ {source_name}: {len(articles)} articles retrieved")
    return articles


# ── Playwright scraper ────────────────────────────────────────────────────────

def _scrape_via_playwright(source_name: str, cutoff_dt: datetime) -> list[dict]:
    try:
        from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
    except ImportError:
        print("  [blavity] Playwright not installed.")
        return []

    articles = []
    seen_urls: set[str] = set()

    try:
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
            page.route(
                re.compile(r"\.(png|jpg|gif|svg|woff2?|mp4|webp)$"),
                lambda route: route.abort(),
            )

            hit_old = False
            for category_path in CATEGORIES:
                if hit_old:
                    break
                for page_num in range(1, MAX_PAGES_PER_CATEGORY + 1):
                    url = BASE_URL + category_path if page_num == 1 else f"{BASE_URL}{category_path}?page={page_num}"
                    try:
                        page.goto(url, timeout=PAGE_LOAD_TIMEOUT, wait_until="domcontentloaded")
                        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                        time.sleep(SCROLL_PAUSE)
                    except PWTimeout:
                        break

                    links = _extract_links_from_page(page)
                    new_links = [l for l in links if l not in seen_urls]
                    if not new_links:
                        break

                    for link in new_links:
                        seen_urls.add(link)
                        try:
                            article = _scrape_article_playwright(page, link, source_name)
                        except Exception:
                            continue
                        if not article:
                            continue
                        pub_dt = _parse_date(article["date_of_publication"])
                        if not pub_dt:
                            continue  # skip undated articles
                        if pub_dt < cutoff_dt:
                            hit_old = True
                            break
                        articles.append(article)

                    if hit_old:
                        break

            browser.close()
    except Exception as e:
        print(f"  [blavity] Playwright error: {e}")

    return articles


def _extract_links_from_page(page) -> list[str]:
    anchors = page.query_selector_all("a[href]")
    links = []
    for a in anchors:
        try:
            href = a.get_attribute("href") or ""
        except Exception:
            continue
        if not href:
            continue
        if href.startswith("/"):
            href = BASE_URL + href
        if DOMAIN not in href:
            continue
        if not _looks_like_article(href):
            continue
        if href not in links:
            links.append(href)
    return links


def _scrape_article_playwright(page, url: str, source_name: str) -> dict | None:
    from playwright.sync_api import TimeoutError as PWTimeout
    try:
        page.goto(url, timeout=15_000, wait_until="domcontentloaded")
    except PWTimeout:
        return None

    title = (
        _pw_meta(page, "og:title")
        or _pw_meta(page, "twitter:title")
        or page.title()
        or ""
    )
    title = _clean(title)
    if not title or len(title) < 5:
        return None

    description = (
        _pw_meta(page, "description")
        or _pw_meta(page, "og:description")
        or _pw_meta(page, "twitter:description")
        or ""
    )
    description = truncate(_clean(description), 500)

    raw_date = _pw_meta(page, "article:published_time") or _pw_time(page) or ""
    pub_dt = _parse_date(raw_date)
    date_str = pub_dt.strftime("%Y-%m-%d") if pub_dt else ""

    category = _pw_meta(page, "article:section") or _category_from_url(url)
    author = _pw_meta(page, "author") or _pw_meta(page, "article:author") or _pw_schema_author(page)

    return {
        "title":               title[:500],
        "description":         description,
        "source":              source_name,
        "date_of_publication": date_str,
        "category":            _clean(category).title()[:100],
        "author":              _clean(author)[:150],
        "link":                url,
    }


# ── Requests fallback ─────────────────────────────────────────────────────────

def _scrape_via_requests(source_name: str, cutoff_dt: datetime) -> list[dict]:
    seen: set[str] = set()
    articles = []
    hit_old = False

    for category_path in CATEGORIES:
        if hit_old:
            break
        for page_num in range(1, MAX_PAGES_PER_CATEGORY + 1):
            url = BASE_URL + category_path if page_num == 1 else f"{BASE_URL}{category_path}?page={page_num}"
            html = _fetch(url)
            if not html:
                break

            soup = BeautifulSoup(html, "html.parser")
            links = []
            for a in soup.find_all("a", href=True):
                href = (a.get("href") or "").strip()
                if not href:
                    continue
                # Handle relative URLs
                if href.startswith("/"):
                    href = BASE_URL + href
                elif not href.startswith("http"):
                    continue
                if href not in seen and _looks_like_article(href):
                    links.append(href)

            if not links:
                break

            for link in links:
                seen.add(link)
                article = _scrape_article_requests(link, source_name)
                if not article:
                    continue
                pub_dt = _parse_date(article["date_of_publication"])
                if not pub_dt:
                    continue  # skip undated
                if pub_dt < cutoff_dt:
                    hit_old = True
                    break
                articles.append(article)
                time.sleep(0.3)

            if hit_old:
                break
            time.sleep(0.5)

    return articles


def _scrape_article_requests(url: str, source_name: str) -> dict | None:
    html = _fetch(url)
    if not html:
        return None
    soup = BeautifulSoup(html, "html.parser")

    title = _meta(soup, "og:title") or _meta(soup, "twitter:title")
    if not title:
        h1 = soup.find("h1")
        title = h1.get_text(strip=True) if h1 else ""
    title = _clean(title)
    if not title or len(title) < 5:
        return None

    description = (
        _meta(soup, "description")
        or _meta(soup, "og:description")
        or ""
    )
    description = truncate(_clean(description), 500)

    raw_date = _meta(soup, "article:published_time") or _time_element(soup) or _jsonld_date(soup) or ""
    pub_dt = _parse_date(raw_date)
    date_str = pub_dt.strftime("%Y-%m-%d") if pub_dt else ""

    category = _meta(soup, "article:section") or _category_from_url(url)
    author = _meta(soup, "author") or _meta(soup, "article:author") or _schema_author(soup)

    return {
        "title":               title[:500],
        "description":         description,
        "source":              source_name,
        "date_of_publication": date_str,
        "category":            _clean(category).title()[:100],
        "author":              _clean(author)[:150],
        "link":                url,
    }


# ── Playwright helpers ────────────────────────────────────────────────────────

def _pw_meta(page, name: str) -> str:
    el = (page.query_selector(f'meta[property="{name}"]')
          or page.query_selector(f'meta[name="{name}"]'))
    return (el.get_attribute("content") or "") if el else ""


def _pw_time(page) -> str:
    el = page.query_selector("time[datetime]") or page.query_selector("time")
    if not el:
        return ""
    return el.get_attribute("datetime") or el.inner_text() or ""


def _pw_schema_author(page) -> str:
    try:
        for s in page.query_selector_all('script[type="application/ld+json"]'):
            data = json.loads(s.inner_text() or "{}")
            for item in (data if isinstance(data, list) else [data]):
                if isinstance(item, dict):
                    a = item.get("author", {})
                    if isinstance(a, dict):
                        return a.get("name", "")
                    if isinstance(a, list) and a:
                        return a[0].get("name", "")
    except Exception:
        pass
    return ""


# ── Requests helpers ──────────────────────────────────────────────────────────

def _fetch(url: str) -> str | None:
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        return r.text if r.status_code == 200 else None
    except requests.RequestException:
        return None


def _meta(soup: BeautifulSoup, name: str) -> str:
    tag = soup.find("meta", {"property": name}) or soup.find("meta", {"name": name})
    return (tag.get("content", "") or "") if tag else ""


def _time_element(soup: BeautifulSoup) -> str:
    el = soup.find("time", attrs={"datetime": True}) or soup.find("time")
    if not el:
        return ""
    return el.get("datetime") or el.get_text().strip()


def _jsonld_date(soup: BeautifulSoup) -> str:
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "{}")
            for obj in (data if isinstance(data, list) else [data]):
                if isinstance(obj, dict):
                    date = obj.get("datePublished") or obj.get("dateCreated")
                    if date:
                        return str(date)
        except Exception:
            pass
    return ""


def _schema_author(soup: BeautifulSoup) -> str:
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "{}")
            for item in (data if isinstance(data, list) else [data]):
                if isinstance(item, dict):
                    a = item.get("author", {})
                    if isinstance(a, dict):
                        return a.get("name", "")
                    if isinstance(a, list) and a:
                        return a[0].get("name", "")
        except Exception:
            pass
    return ""


# ── Shared helpers ────────────────────────────────────────────────────────────

def _clean(text: str) -> str:
    if not text:
        return ""
    from scraper.utils import clean_html
    return clean_html(text).strip()


def _parse_date(text: str) -> datetime | None:
    if not text:
        return None
    s = text.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        pass
    for fmt in ("%Y-%m-%d", "%B %d, %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(s[:20], fmt)
        except ValueError:
            pass
    m = re.search(r"\d{4}-\d{2}-\d{2}", s)
    if m:
        try:
            return datetime.fromisoformat(m.group(0))
        except ValueError:
            pass
    return None


def _looks_like_article(url: str) -> bool:
    parsed = urlparse(url)
    if DOMAIN not in parsed.netloc:
        return False
    path = parsed.path.lower().strip("/")
    if not path:
        return False
    # Exclude listing/section pages
    bad = ["tag/", "tags/", "author/", "search", "about", "newsletter",
           "contact", "page/", "events/", "blavity-u", "blavity-books",
           "off-the-shelves", "briefing", "latest", "/category/"]
    # Block bare /categories/X listing pages (no article slug)
    if re.match(r"^categories/[^/]+/?$", path):
        return False
    if any(b in path for b in bad):
        return False
    parts = [p for p in path.split("/") if p]
    if not parts:
        return False
    # Single-segment non-article section names
    section_pages = {"entertainment", "news", "culture", "politics", "health",
                     "women", "lifestyle", "education", "about", "contact"}
    if len(parts) == 1 and (parts[0] in section_pages or len(parts[0]) <= 8):
        return False
    return len(parts[-1]) >= 10


def _category_from_url(url: str) -> str:
    parts = [p for p in urlparse(url).path.strip("/").split("/") if p]
    skip = {"category", "categories", "tag", "author", "page"}
    for part in parts[:-1]:
        if part.lower() not in skip:
            return part.replace("-", " ").title()
    return ""
