import hashlib
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

import feedparser

from config import RSS_SOURCES

logger = logging.getLogger(__name__)


# ── Helper ───────────────────────────────────

def _fetch_single_source(source: dict) -> list[dict]:
    """Fetch and normalize articles from a single RSS source.

    Runs in a worker thread. Returns a list of article dicts.
    Includes the source's sector tags so downstream classification
    can use them as a primary signal.
    """
    try:
        feed = feedparser.parse(source["url"])
        articles = []
        source_sectors = source.get("sectors", [])

        for entry in feed.entries:
            link = entry.get("link", "").strip()
            title = entry.get("title", "").strip()
            if not link or not title:
                continue

            # Normalize published date
            published_at = datetime.now(timezone.utc).isoformat()
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                published_at = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc).isoformat()

            # Create unique ID from URL
            article_id = hashlib.md5(link.encode("utf-8")).hexdigest()

            articles.append({
                "id": article_id,
                "title": title.lower(),
                "url": link,
                "source": source["name"],
                "published_at": published_at,
                "content_snippet": entry.get("summary", ""),
                "source_sectors": source_sectors,  # Tags inherited from RSS source
            })

        logger.info(f"  {source['name']}: {len(articles)} articles")
        return articles

    except Exception as e:
        logger.error(f"  {source['name']}: Error — {e}")
        return []


# ── Main Fetcher ─────────────────────────────

def fetch_rss_feeds() -> list[dict]:
    """Fetch and normalize articles from multiple RSS sources in parallel.

    Uses a thread pool (8 workers) for I/O-bound HTTP requests.
    Deduplicates by URL across all sources.
    """
    seen_urls: set[str] = set()
    all_articles: list[dict] = []

    logger.info(f"Fetching {len(RSS_SOURCES)} RSS feeds in parallel (8 workers)...")

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(_fetch_single_source, src): src for src in RSS_SOURCES}

        for future in as_completed(futures):
            source = futures[future]
            source_articles = future.result()

            # Deduplicate against seen URLs (main thread, so no race condition)
            for article in source_articles:
                if article["url"] not in seen_urls:
                    seen_urls.add(article["url"])
                    all_articles.append(article)

    logger.info(f"Fetched {len(all_articles)} unique articles across all sources.")
    return all_articles
