"""
RSS feed fetcher and article normaliser.
"""

import hashlib
import html
import logging
import re
from datetime import datetime, timezone
from typing import Optional

import feedparser
from dateutil import parser as dateutil_parser

from .config import RSS_FEEDS

logger = logging.getLogger(__name__)

# Regex to strip HTML tags
_HTML_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(text: str) -> str:
    """Remove HTML tags and decode entities."""
    if not text:
        return ""
    text = _HTML_TAG_RE.sub("", text)
    text = html.unescape(text)
    return text.strip()


def _parse_date(entry) -> str:
    """Best-effort parse of a feedparser entry's date to UTC ISO string."""
    for attr in ("published", "updated", "created"):
        raw = getattr(entry, attr, None) or entry.get(attr)
        if raw:
            try:
                dt = dateutil_parser.parse(raw)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt.astimezone(timezone.utc).isoformat()
            except (ValueError, OverflowError):
                continue
    # Fallback: now
    return datetime.now(timezone.utc).isoformat()


def _extract_source(feed_url: str, feed_title: Optional[str]) -> str:
    """Derive a human-readable source name."""
    if feed_title:
        # Split on common delimiters: em-dash, en-dash, pipe, colon, hyphen-with-spaces
        name = re.split(r"\s*[–—|:]\s*|\s+-\s+", feed_title)[0].strip()
        # Also strip "> section" patterns like "NYT > World News"
        name = re.split(r"\s*>\s*", name)[0].strip()
        if name:
            return name
    # Fallback: domain name
    try:
        from urllib.parse import urlparse
        domain = urlparse(feed_url).netloc
        return domain.replace("www.", "").split(".")[0].capitalize()
    except Exception:
        return "Unknown"


def _article_id(url: str) -> str:
    """Deterministic ID from the article URL."""
    return hashlib.sha256(url.encode()).hexdigest()[:16]


def _snippet(entry) -> str:
    """Extract a content snippet from a feed entry."""
    # Try content field first
    if hasattr(entry, "content") and entry.content:
        return _strip_html(entry.content[0].get("value", ""))[:500]
    # Fallback to summary / description
    raw = entry.get("summary") or entry.get("description") or ""
    return _strip_html(raw)[:500]


def _fetch_single_feed(feed_url: str) -> list[dict]:
    """Parse one RSS feed and return normalised article dicts."""
    articles: list[dict] = []
    try:
        feed = feedparser.parse(feed_url)
        source = _extract_source(feed_url, feed.feed.get("title"))
        for entry in feed.entries:
            url = entry.get("link", "").strip()
            title = _strip_html(entry.get("title", "")).strip()
            if not url or not title:
                continue
            articles.append(
                {
                    "id": _article_id(url),
                    "title": title,
                    "url": url,
                    "source": source,
                    "published_at": _parse_date(entry),
                    "content_snippet": _snippet(entry),
                }
            )
        logger.info("Fetched %d articles from %s (%s)", len(articles), source, feed_url)
    except Exception:
        logger.exception("Failed to fetch feed: %s", feed_url)
    return articles


def fetch_all_feeds() -> list[dict]:
    """
    Fetch every configured RSS feed, normalise entries,
    and return a de-duplicated list of article dicts.
    """
    all_articles: list[dict] = []
    seen_urls: set[str] = set()

    for feed_url in RSS_FEEDS:
        for article in _fetch_single_feed(feed_url):
            if article["url"] not in seen_urls:
                seen_urls.add(article["url"])
                all_articles.append(article)

    logger.info("Total unique articles fetched: %d", len(all_articles))
    return all_articles
