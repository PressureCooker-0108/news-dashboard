"""
Configuration for the Serious Operator News Dashboard.
RSS feeds (with sector tags), constants, and topic templates.

Each RSS source can be tagged with one or more sectors:
  - Articles inherit these sectors automatically (primary classification)
  - TF-IDF classification runs as a secondary refinement for multi-sector
  - Empty list means TF-IDF is the sole classifier (fallback)
"""

# ──────────────────────────────────────────────
# RSS Feed Sources (with sector mapping)
# ──────────────────────────────────────────────
# Format: { "name": ..., "url": ..., "sectors": [...] }
#   - sectors: list of sector tags this feed primarily covers
#   - empty list [] = unclassified → uses TF-IDF classifier only
# ──────────────────────────────────────────────

RSS_SOURCES = [
    # ── Geopolitics / World News ──
    {"name": "BBC World", "url": "https://feeds.bbci.co.uk/news/world/rss.xml", "sectors": ["Geopolitics"]},
    {"name": "BBC General", "url": "https://feeds.bbci.co.uk/news/rss.xml", "sectors": ["Geopolitics", "General"]},
    {"name": "Al Jazeera", "url": "https://www.aljazeera.com/xml/rss/all.xml", "sectors": ["Geopolitics"]},
    {"name": "The Guardian World", "url": "https://www.theguardian.com/world/rss", "sectors": ["Geopolitics"]},
    {"name": "The Guardian UK", "url": "https://www.theguardian.com/uk/rss", "sectors": ["Geopolitics", "General"]},
    {"name": "Foreign Policy", "url": "https://foreignpolicy.com/feed/", "sectors": ["Geopolitics"]},
    {"name": "DW (Germany)", "url": "https://www.dw.com/en/top-stories/s-9097/rss", "sectors": ["Geopolitics"]},
    {"name": "SCMP (China)", "url": "https://www.scmp.com/rss/91/feed", "sectors": ["Geopolitics"]},
    {"name": "Japan Times", "url": "https://www.japantimes.co.jp/feed/", "sectors": ["Geopolitics"]},

    # ── US & Global Politics ──
    {"name": "NYTimes World", "url": "https://rss.nytimes.com/services/xml/rss/nyt/World.xml", "sectors": ["Geopolitics"]},
    {"name": "NYTimes Politics", "url": "https://rss.nytimes.com/services/xml/rss/nyt/Politics.xml", "sectors": ["Geopolitics"]},
    {"name": "NYTimes Economy", "url": "https://rss.nytimes.com/services/xml/rss/nyt/Economy.xml", "sectors": ["Markets"]},
    {"name": "Washington Post National", "url": "https://feeds.washingtonpost.com/rss/national", "sectors": ["Geopolitics", "General"]},
    {"name": "NPR News", "url": "https://feeds.npr.org/1001/rss.xml", "sectors": ["Geopolitics", "General"]},

    # ── Markets & Business ──
    {"name": "NYTimes Business", "url": "https://rss.nytimes.com/services/xml/rss/nyt/Business.xml", "sectors": ["Markets"]},
    {"name": "CNBC Top News", "url": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114", "sectors": ["Markets"]},
    {"name": "CNBC Finance", "url": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10000664", "sectors": ["Markets"]},
    {"name": "MarketWatch", "url": "https://feeds.marketwatch.com/marketwatch/topstories/", "sectors": ["Markets"]},
    {"name": "Investing.com", "url": "https://www.investing.com/rss/news.rss", "sectors": ["Markets"]},
    {"name": "NPR Business", "url": "https://feeds.npr.org/1014/rss.xml", "sectors": ["Markets"]},
    {"name": "The Guardian Business", "url": "https://www.theguardian.com/business/rss", "sectors": ["Markets"]},
    {"name": "LiveMint", "url": "https://www.livemint.com/rss/news", "sectors": ["Markets", "India"]},
    {"name": "Economic Times", "url": "https://economictimes.indiatimes.com/rssfeedstopstories.cms", "sectors": ["Markets", "India"]},
    {"name": "Business Standard", "url": "https://www.business-standard.com/rss/home_page_top_stories.rss", "sectors": ["Markets", "India"]},
    {"name": "Moneycontrol", "url": "https://www.moneycontrol.com/rss/latestnews.xml", "sectors": ["Markets", "India"]},

    # ── Tech ──
    {"name": "BBC Technology", "url": "https://feeds.bbci.co.uk/news/technology/rss.xml", "sectors": ["Tech"]},
    {"name": "NYTimes Technology", "url": "https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml", "sectors": ["Tech"]},
    {"name": "TechCrunch", "url": "https://techcrunch.com/feed/", "sectors": ["Tech"]},
    {"name": "Hacker News", "url": "https://news.ycombinator.com/rss", "sectors": ["Tech"]},
    {"name": "Wired", "url": "https://www.wired.com/feed/rss", "sectors": ["Tech"]},
    {"name": "The Verge", "url": "https://www.theverge.com/rss/index.xml", "sectors": ["Tech"]},
    {"name": "Ars Technica", "url": "http://feeds.arstechnica.com/arstechnica/index", "sectors": ["Tech"]},
    {"name": "VentureBeat", "url": "https://venturebeat.com/feed/", "sectors": ["Tech"]},
    {"name": "Artificial Intelligence News", "url": "https://www.artificialintelligence-news.com/feed/", "sectors": ["Tech"]},

    # ── India ──
    {"name": "Times of India", "url": "https://timesofindia.indiatimes.com/rss/4719148.cms", "sectors": ["India"]},
    {"name": "The Hindu", "url": "https://www.thehindu.com/news/international/?service=rss", "sectors": ["India"]},
    {"name": "NDTV", "url": "https://feeds.feedburner.com/ndtvnews-top-stories", "sectors": ["India"]},
    {"name": "Indian Express", "url": "https://indianexpress.com/section/india/feed/", "sectors": ["India"]},

    # ── Energy ──
    {"name": "OilPrice.com", "url": "https://oilprice.com/rss/main", "sectors": ["Energy"]},
    {"name": "Energy Voice", "url": "https://www.energyvoice.com/feed/", "sectors": ["Energy"]},

    # ── General / Fallback (use TF-IDF) ──
    {"name": "The Guardian Tech", "url": "https://www.theguardian.com/uk/technology/rss", "sectors": ["Tech"]},
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
