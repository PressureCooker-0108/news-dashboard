"""
Configuration for the Serious Operator News Dashboard.
RSS feeds, constants, and topic templates.
"""

# ──────────────────────────────────────────────
# RSS Feed Sources
# ──────────────────────────────────────────────
RSS_FEEDS = [
    "http://feeds.reuters.com/reuters/topNews",
    "http://feeds.reuters.com/reuters/businessNews",
    "https://feeds.bbci.co.uk/news/rss.xml",
    "https://feeds.bbci.co.uk/news/world/rss.xml",
    "https://www.aljazeera.com/xml/rss/all.xml",
    "https://feeds.npr.org/1001/rss.xml",
    "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
    "https://rss.nytimes.com/services/xml/rss/nyt/Business.xml",
    "https://feeds.a.dz.com/rss/cnbc/world",
    "https://techcrunch.com/feed/",
    "https://news.ycombinator.com/rss",
    "https://www.thehindu.com/news/international/?service=rss",
    "https://feeds.feedburner.com/ndtvnews-top-stories",
    "https://rss.app/feeds/tvYaGCRLkyd3oZHC.xml",
    "https://www.ft.com/rss/home",
]

# ──────────────────────────────────────────────
# Pipeline Constants
# ──────────────────────────────────────────────
MAX_STORIES = 10
CLUSTER_THRESHOLD = 0.35
RECENCY_WEIGHT = 0.4
COVERAGE_WEIGHT = 0.6

# Database
DATABASE_PATH = "news.db"

# ──────────────────────────────────────────────
# Topic → "Why It Matters" Templates
# ──────────────────────────────────────────────
TOPIC_TEMPLATES = {
    "election": "Political transitions can shift policy direction and market sentiment.",
    "war": "Armed conflict affects global supply chains, energy prices, and geopolitical stability.",
    "economy": "Economic shifts impact inflation, employment, and investment decisions globally.",
    "fed": "Central bank decisions directly influence borrowing costs and global capital flows.",
    "rate": "Interest rate changes ripple through mortgages, business loans, and currency markets.",
    "ai": "AI developments are reshaping industries, labor markets, and competitive dynamics.",
    "climate": "Climate events and policy changes affect agriculture, insurance, and infrastructure.",
    "market": "Market movements reflect investor confidence and can signal broader economic trends.",
    "health": "Health crises affect workforce productivity, government spending, and supply chains.",
    "trade": "Trade policy changes affect prices, jobs, and international relations.",
    "default": "This story is receiving significant coverage across multiple major news sources.",
}
