"""
Configuration for the Serious Operator News Dashboard.
RSS feeds, constants, and topic templates.
"""

# ──────────────────────────────────────────────
# RSS Feed Sources
# ──────────────────────────────────────────────
RSS_FEEDS = [
    # Global News
    "https://feeds.bbci.co.uk/news/rss.xml",
    "https://feeds.bbci.co.uk/news/world/rss.xml",
    "https://www.aljazeera.com/xml/rss/all.xml",
    "https://feeds.npr.org/1001/rss.xml",
    "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
    "https://rss.nytimes.com/services/xml/rss/nyt/Business.xml",
    # Business & Markets
    "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114",
    "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10000664",
    "https://feeds.marketwatch.com/marketwatch/topstories/",
    "https://www.investing.com/rss/news.rss",
    # Tech
    "https://techcrunch.com/feed/",
    "https://news.ycombinator.com/rss",
    "https://www.wired.com/feed/rss",
    # India
    "https://www.thehindu.com/news/international/?service=rss",
    "https://feeds.feedburner.com/ndtvnews-top-stories",
    "https://timesofindia.indiatimes.com/rss/4719148.cms",
]

# ──────────────────────────────────────────────
# Pipeline Constants
# ──────────────────────────────────────────────
MAX_STORIES = 20
CLUSTER_THRESHOLD = 0.45
RECENCY_WEIGHT = 0.4
COVERAGE_WEIGHT = 0.6

# Database
# Migration to Supabase complete.

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
    "default": "This is a developing story worth monitoring.",
}
