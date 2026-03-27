"""
capitalb_scraper.py — Capital B News Sitemap + Category Scraper

Discovery strategy:
  1. Parse sitemap_index.xml (post-sitemap, article-sitemap, news-sitemap)
  2. RSS/Atom feed
  3. Homepage + category pages (with pagination)
  4. WordPress date archives (year/month) for the rolling window

Filters to the rolling 30-day window.
"""

import re
import json
import time
import html as html_lib
from datetime import datetime, timedelta
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from scraper.utils import get_cutoff_date, truncate, HEADERS

DOMAIN = "capitalbnews.org"
BASE_URL = f"https://{DOMAIN}"
SITEMAP_URL = f"{BASE_URL}/sitemap_index.xml"
SITEMAP_HEADERS = {**HEADERS, "Accept": "application/xml, text/xml, */*"}

SPONSORED_KEYWORDS = ["sponsored", "paid content", "partner content", "presented by", "advertorial"]
MAX_CATEGORY_PAGES = 3   # Capital B publishes ~28 articles/month — 3 pages per category is sufficient
MAX_SCRAPE_CANDIDATES = 200  # Hard cap on individual page fetches


# ── Public entry point ────────────────────────────────────────────────────────

def scrape_capitalb(source_name: str, days: int = 30) -> list[dict]:
    cutoff_dt = datetime.now() - timedelta(days=days)

    print(f"  [capitalb] Discovering article URLs via sitemap + categories...")

    seen: set[str] = set()
    candidates: list[tuple[str, object]] = []

    # 1) Sitemap
    for loc, lastmod in _parse_sitemap_urls(SITEMAP_URL):
        if loc and loc not in seen and _looks_like_article(loc):
            seen.add(loc)
            candidates.append((loc, lastmod))
    print(f"  [capitalb] Sitemap: {len(candidates)} article URLs")

    # 2) RSS feed
    for loc, lastmod in _discover_from_feed():
        if loc and loc not in seen and _looks_like_article(loc):
            seen.add(loc)
            candidates.append((loc, lastmod))

    # 3) Homepage + category pages
    for loc, _ in _discover_from_categories():
        if loc and loc not in seen and _looks_like_article(loc):
            seen.add(loc)
            candidates.append((loc, None))

    # 4) Date archives
    for loc, _ in _discover_from_date_archives(days):
        if loc and loc not in seen and _looks_like_article(loc):
            seen.add(loc)
            candidates.append((loc, None))

    # Prioritise sitemap candidates (have lastmod) — put them first, then others
    with_date = [(l, m) for l, m in candidates if m is not None]
    without_date = [(l, m) for l, m in candidates if m is None]
    candidates = with_date + without_date[:max(0, MAX_SCRAPE_CANDIDATES - len(with_date))]
    print(f"  [capitalb] Scraping {len(candidates)} candidates (capped at {MAX_SCRAPE_CANDIDATES})")

    # Scrape each, filter by publish date
    articles = []
    for loc, lastmod in candidates:
        # Quick skip if lastmod clearly outside window
        if lastmod is not None:
            lm = lastmod if isinstance(lastmod, datetime) else datetime(lastmod.year, lastmod.month, lastmod.day)
            if lm < cutoff_dt:
                continue

        article = _scrape_article_page(loc, source_name)
        if not article:
            continue

        pub_dt = _parse_date(article["date_of_publication"])
        if pub_dt and pub_dt < cutoff_dt:
            continue

        articles.append(article)
        time.sleep(0.25)

    print(f"  [capitalb] ✓ {source_name}: {len(articles)} articles retrieved")
    return articles


# ── Sitemap parsing ───────────────────────────────────────────────────────────

def _parse_sitemap_urls(sitemap_url: str):
    text = _fetch_sitemap(sitemap_url)
    if not text or ("<urlset" not in text and "<sitemapindex" not in text):
        return
    soup = BeautifulSoup(text, "xml")
    if soup.find("sitemapindex"):
        allowed = ("post-sitemap", "article-sitemap", "page-sitemap", "news-sitemap")
        for sm in soup.find_all("sitemap"):
            loc_tag = sm.find("loc")
            if not loc_tag or not loc_tag.text:
                continue
            child = loc_tag.text.strip()
            if any(x in child for x in allowed):
                yield from _parse_sitemap_urls(child)
    else:
        for url_tag in soup.find_all("url"):
            loc_tag = url_tag.find("loc")
            if not loc_tag or not loc_tag.text:
                continue
            loc = loc_tag.text.strip()
            if DOMAIN not in loc:
                continue
            lastmod_tag = url_tag.find("lastmod")
            lastmod = None
            if lastmod_tag and lastmod_tag.text:
                dt = _parse_date(lastmod_tag.text)
                lastmod = dt.date() if dt else None
            yield loc, lastmod


# ── Discovery: RSS feed ───────────────────────────────────────────────────────

def _discover_from_feed():
    for path in ("/feed/", "/feed", "/?feed=rss2"):
        url = BASE_URL + path
        html = _fetch(url)
        if not html:
            continue
        soup = BeautifulSoup(html, "html.parser")
        seen: set[str] = set()
        for item in soup.find_all("item"):
            link = item.find("link")
            if link:
                href = link.get_text(strip=True)
                if href and DOMAIN in urlparse(href).netloc and href not in seen:
                    seen.add(href)
                    yield href, None
        if seen:
            print(f"  [capitalb] Feed: {len(seen)} URLs from {path}")
            return
        time.sleep(0.3)


# ── Discovery: category pages ─────────────────────────────────────────────────

def _discover_from_categories():
    html = _fetch(BASE_URL)
    if not html:
        return
    soup = BeautifulSoup(html, "html.parser")

    # Collect category URLs from homepage nav
    category_urls: set[str] = set()
    for a in soup.find_all("a", href=True):
        href = (a.get("href") or "").strip()
        if not href.startswith("http"):
            href = BASE_URL.rstrip("/") + ("/" + href.lstrip("/") if href else "")
        if not href or DOMAIN not in urlparse(href).netloc:
            continue
        path = urlparse(href).path.rstrip("/").lower()
        if "/category/" in path:
            path = re.sub(r"/page/\d+/?$", "", path)
            category_urls.add(BASE_URL.rstrip("/") + "/" + path.lstrip("/"))

    seen: set[str] = set()
    for base_cat_url in category_urls:
        base_cat_url = base_cat_url.rstrip("/")
        for page in range(1, MAX_CATEGORY_PAGES + 1):
            url = base_cat_url + f"/page/{page}/" if page > 1 else base_cat_url + "/"
            html = _fetch(url)
            if not html:
                break
            soup = BeautifulSoup(html, "html.parser")
            count = 0
            for a in soup.find_all("a", href=True):
                href = (a.get("href") or "").strip()
                if not href.startswith("http"):
                    href = BASE_URL.rstrip("/") + ("/" + href.lstrip("/") if href else "")
                if href and DOMAIN in urlparse(href).netloc and href not in seen and _looks_like_article(href):
                    seen.add(href)
                    count += 1
                    yield href, None
            time.sleep(0.35)
            if count == 0 and page > 1:
                break

    if seen:
        print(f"  [capitalb] Category pages: {len(seen)} URLs")


# ── Discovery: date archives ──────────────────────────────────────────────────

def _discover_from_date_archives(days: int):
    cutoff = datetime.now() - timedelta(days=days)
    months: set[tuple] = set()
    d = datetime.now()
    while d >= cutoff:
        months.add((d.year, d.month))
        d = datetime(d.year - 1 if d.month == 1 else d.year,
                     12 if d.month == 1 else d.month - 1, 1)

    seen: set[str] = set()
    for year, month in sorted(months):
        url = f"{BASE_URL}/{year}/{month:02d}/"
        html = _fetch(url)
        if not html:
            continue
        soup = BeautifulSoup(html, "html.parser")
        for a in soup.find_all("a", href=True):
            href = (a.get("href") or "").strip()
            if not href.startswith("http"):
                href = BASE_URL.rstrip("/") + ("/" + href.lstrip("/") if href else "")
            if href and DOMAIN in urlparse(href).netloc and href not in seen and _looks_like_article(href):
                seen.add(href)
                yield href, None
        time.sleep(0.25)

    if seen:
        print(f"  [capitalb] Date archives: {len(seen)} URLs")


# ── Article page scraper ──────────────────────────────────────────────────────

def _scrape_article_page(url: str, source_name: str) -> dict | None:
    html = _fetch(url)
    if not html:
        return None
    soup = BeautifulSoup(html, "html.parser")

    # Title
    title = _meta(soup, "og:title") or _meta(soup, "twitter:title")
    if not title:
        h1 = soup.find("h1")
        title = h1.get_text(strip=True) if h1 else ""
    title = _clean_title(title)
    if not title or len(title) < 5:
        return None

    # Description
    description = (
        _meta(soup, "description")
        or _meta(soup, "og:description")
        or _meta(soup, "twitter:description")
        or ""
    )
    description = truncate(_clean_text(description), 500)

    # Date
    raw_date = ""
    for attr in ["property", "name", "itemprop"]:
        for key in ["article:published_time", "datePublished", "pubdate"]:
            tag = soup.find("meta", attrs={attr: key})
            if tag and tag.get("content"):
                raw_date = tag["content"].strip()
                break
        if raw_date:
            break
    if not raw_date:
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string or "{}")
                for obj in (data if isinstance(data, list) else [data]):
                    if isinstance(obj, dict) and obj.get("datePublished"):
                        raw_date = str(obj["datePublished"])
                        break
            except Exception:
                pass
            if raw_date:
                break

    pub_dt = _parse_date(raw_date)
    if not pub_dt:
        return None  # Skip articles without a parseable date
    date_str = pub_dt.strftime("%Y-%m-%d")

    # Category
    category = ""
    for key in ["article:section", "section", "category"]:
        tag = soup.find("meta", attrs={"property": key}) or soup.find("meta", attrs={"name": key})
        if tag and tag.get("content"):
            category = tag["content"].strip()
            break
    if not category:
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string or "{}")
                for obj in (data if isinstance(data, list) else [data]):
                    if isinstance(obj, dict) and obj.get("articleSection"):
                        s = obj["articleSection"]
                        category = s[0] if isinstance(s, list) and s else str(s)
                        break
            except Exception:
                pass
            if category:
                break

    # Author
    author = _meta(soup, "author") or ""
    if not author:
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string or "{}")
                for obj in (data if isinstance(data, list) else [data]):
                    if isinstance(obj, dict):
                        a = obj.get("author", {})
                        if isinstance(a, dict):
                            author = a.get("name", "")
                        elif isinstance(a, list) and a:
                            author = a[0].get("name", "")
                        if author:
                            break
            except Exception:
                pass
            if author:
                break

    if _is_sponsored(url, category, title):
        return None

    return {
        "title":               title[:500],
        "description":         description,
        "source":              source_name,
        "date_of_publication": date_str,
        "category":            _clean_text(category).title()[:100],
        "author":              _clean_text(author)[:150],
        "link":                url,
    }


# ── Helpers ───────────────────────────────────────────────────────────────────

def _fetch(url: str) -> str | None:
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        return r.text if r.status_code == 200 else None
    except requests.RequestException:
        return None


def _fetch_sitemap(url: str) -> str | None:
    try:
        r = requests.get(url, headers=SITEMAP_HEADERS, timeout=20)
        return r.text if r.status_code == 200 else None
    except requests.RequestException:
        return None


def _meta(soup: BeautifulSoup, name: str) -> str:
    tag = soup.find("meta", {"property": name}) or soup.find("meta", {"name": name})
    return (tag.get("content", "") or "") if tag else ""


def _clean_title(t: str) -> str:
    t = html_lib.unescape((t or "").strip())
    for suffix in ("| Capital B News", "- Capital B News", "– Capital B News"):
        if t.endswith(suffix):
            t = t[:-len(suffix)].strip()
    return t


def _clean_text(text: str) -> str:
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
    path = parsed.path.strip("/").lower()
    if not path:
        return False
    bad = ["category/", "categories/", "tag/", "author/", "search", "about",
           "newsletter", "contact", "subscribe", "page/", "privacy", "terms",
           "advertise", "our-team", "masthead", "inside-capital-b"]
    if any(b in path for b in bad):
        return False
    parts = [p for p in path.split("/") if p]
    return bool(parts) and len(parts[-1]) >= 6


def _is_sponsored(*parts: str) -> bool:
    text = " ".join(p for p in parts if p).lower()
    return any(k in text for k in SPONSORED_KEYWORDS)
