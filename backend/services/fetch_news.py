import hashlib
import feedparser
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

# List of expanded RSS sources
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
    {"name": "NYTimes", "url": "https://rss.nytimes.com/services/xml/rss/nyt/World.xml"},
    {"name": "BBC", "url": "http://feeds.bbci.co.uk/news/world/rss.xml"},
    {"name": "Reuters", "url": "http://feeds.reuters.com/reuters/topNews"},
    {"name": "Al Jazeera", "url": "https://www.aljazeera.com/xml/rss/all.xml"},
    {"name": "The Guardian", "url": "https://www.theguardian.com/world/rss"}
]

def fetch_rss_feeds() -> list[dict]:
    """Fetch and normalize articles from multiple RSS sources."""
    articles = []
    seen_urls = set()

    for source in RSS_SOURCES:
        try:
            logger.info(f"Fetching RSS feed: {source['name']}")
            feed = feedparser.parse(source["url"])
            
            for entry in feed.entries:
                link = entry.get('link', '').strip()
                if not link or link in seen_urls:
                    continue
                
                seen_urls.add(link)
                title = entry.get('title', '').strip()
                if not title:
                    continue
                
                # Normalize published date
                published_at = datetime.now(timezone.utc).isoformat()
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    published_at = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc).isoformat()
                
                # Create unique ID for the article
                article_id = hashlib.md5(link.encode('utf-8')).hexdigest()
                
                articles.append({
                    "id": article_id,
                    "title": title.lower(), # Normalise titles (lowercase as requested)
                    "url": link,
                    "source": source["name"],
                    "published_at": published_at,
                    "content_snippet": entry.get('summary', ''),
                })
        except Exception as e:
            logger.error(f"Error fetching from {source['name']}: {e}")

    logger.info(f"Fetched {len(articles)} total articles across all sources.")
    return articles
