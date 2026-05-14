import hashlib
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

import feedparser

logger = logging.getLogger(__name__)

# ── RSS Sources ──────────────────────────────
# Each source is fetched in parallel. Duplicates have been removed.

RSS_SOURCES = [
    {"name": "NYTimes World", "url": "https://rss.nytimes.com/services/xml/rss/nyt/World.xml"},
    {"name": "NYTimes Home", "url": "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml"},
    {"name": "BBC World", "url": "http://feeds.bbci.co.uk/news/world/rss.xml"},
    {"name": "BBC General", "url": "http://feeds.bbci.co.uk/news/rss.xml"},
    {"name": "Reuters Top News", "url": "http://feeds.reuters.com/reuters/topNews"},
    {"name": "Reuters Business", "url": "http://feeds.reuters.com/reuters/businessNews"},
    {"name": "Al Jazeera", "url": "https://www.aljazeera.com/xml/rss/all.xml"},
    {"name": "The Guardian World", "url": "https://www.theguardian.com/world/rss"},
    {"name": "The Guardian Tech", "url": "https://www.theguardian.com/uk/technology/rss"},
    {"name": "Financial Times", "url": "https://www.ft.com/rss/home"},
    {"name": "Wall Street Journal World", "url": "https://feeds.a.dj.com/rss/RSSWorldNews.xml"},
    {"name": "CNBC Top News", "url": "https://www.cnbc.com/id/100003114/device/rss/rss.html"},
    {"name": "MarketWatch", "url": "https://www.marketwatch.com/rss/topstories"},
    {"name": "Yahoo Finance", "url": "https://finance.yahoo.com/news/rssindex"},
    {"name": "Investing.com", "url": "https://www.investing.com/rss/news.rss"},
    {"name": "Seeking Alpha", "url": "https://seekingalpha.com/feed.xml"},
    {"name": "TechCrunch", "url": "https://techcrunch.com/feed/"},
    {"name": "The Verge", "url": "https://www.theverge.com/rss/index.xml"},
    {"name": "Ars Technica", "url": "http://feeds.arstechnica.com/arstechnica/index"},
    {"name": "Wired", "url": "https://www.wired.com/feed/rss"},
    {"name": "VentureBeat", "url": "https://venturebeat.com/feed/"},
    {"name": "Artificial Intelligence News", "url": "https://www.artificialintelligence-news.com/feed/"},
    {"name": "Foreign Policy", "url": "https://foreignpolicy.com/feed/"},
    {"name": "Economist International", "url": "https://www.economist.com/international/rss.xml"},
    {"name": "DW (Germany)", "url": "https://www.dw.com/en/top-stories/s-9097/rss"},
    {"name": "SCMP (China)", "url": "https://www.scmp.com/rss/91/feed"},
    {"name": "Japan Times", "url": "https://www.japantimes.co.jp/feed/"},
    {"name": "Times of India", "url": "https://timesofindia.indiatimes.com/rssfeedstopstories.cms"},
    {"name": "The Hindu", "url": "https://www.thehindu.com/news/national/feeder/default.rss"},
    {"name": "Indian Express", "url": "https://indianexpress.com/section/india/feed/"},
    {"name": "LiveMint", "url": "https://www.livemint.com/rss/news"},
    {"name": "Economic Times", "url": "https://economictimes.indiatimes.com/rssfeedstopstories.cms"},
    {"name": "Business Standard", "url": "https://www.business-standard.com/rss/home_page_top_stories.rss"},
    {"name": "Moneycontrol", "url": "https://www.moneycontrol.com/rss/latestnews.xml"},
    {"name": "OilPrice", "url": "https://oilprice.com/rss/main"},
    {"name": "Energy Voice", "url": "https://www.energyvoice.com/feed/"},
]


# ── Helper ───────────────────────────────────

def _fetch_single_source(source: dict) -> list[dict]:
    """Fetch and normalize articles from a single RSS source.

    Runs in a worker thread. Returns a list of article dicts.
    """
    try:
        feed = feedparser.parse(source["url"])
        articles = []

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
