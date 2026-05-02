# Serious Operator News Dashboard

A Python backend that aggregates global news from 15+ RSS feeds, clusters similar articles into stories using sentence embeddings, ranks them by importance, and serves the results via a FastAPI API.  
Built for founders, investors, and analysts who need high-signal, low-noise intelligence.

---

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the server
uvicorn news_dashboard.main:app --reload
```

> **Note:** The first run downloads the `all-MiniLM-L6-v2` embedding model (~80 MB). This takes 1–2 minutes; subsequent starts are instant.

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/`  | Health check — returns story count and last update time |
| `GET`  | `/news` | Top stories (default 10) |
| `GET`  | `/news?limit=5` | Top N stories (max 20) |

### Example Response — `GET /news`

```json
{
  "count": 7,
  "stories": [
    {
      "rank": 1,
      "headline": "Fed Holds Rates Steady Amid Inflation Concerns",
      "summary": "The Federal Reserve kept interest rates unchanged...",
      "why_it_matters": "Central bank decisions directly influence borrowing costs and global capital flows.",
      "sources": ["BBC", "Reuters"],
      "article_count": 5,
      "score": 0.87,
      "latest_at": "2024-01-15T10:30:00+00:00"
    }
  ]
}
```

---

## How the Pipeline Works

1. **Fetch** — Pulls articles from 15 RSS feeds (Reuters, BBC, NYT, Al Jazeera, etc.)
2. **Store** — Normalises dates to UTC, strips HTML, deduplicates by URL, and saves to SQLite
3. **Cluster** — Embeds titles + snippets with `all-MiniLM-L6-v2` and groups similar articles using Agglomerative Clustering
4. **Rank** — Scores each story cluster by `0.6 × coverage + 0.4 × recency` and keeps the top 10
5. **Summarise** — Picks the most representative headline, builds a 2-sentence summary, and generates a "why it matters" blurb via keyword matching

The pipeline runs **once on startup** and then **daily at 07:00** local time via APScheduler.

---

## Adding More RSS Feeds

Open `news_dashboard/config.py` and add URLs to the `RSS_FEEDS` list:

```python
RSS_FEEDS = [
    # ... existing feeds ...
    "https://example.com/rss",
]
```

Restart the server to pick up changes.

---

## Project Structure

```
news_dashboard/
├── main.py          # FastAPI app + routes
├── fetcher.py       # RSS fetching + normalisation
├── database.py      # SQLite schema, queries
├── clusterer.py     # Sentence-embedding clustering
├── ranker.py        # Coverage + recency scoring
├── summarizer.py    # Headline, summary, why-it-matters
├── scheduler.py     # Pipeline orchestrator + cron
└── config.py        # Feeds, constants, templates
```

---

## Tech Stack

Python 3.10+ · FastAPI · SQLite · sentence-transformers · scikit-learn · APScheduler

No paid APIs. Runs fully locally.
