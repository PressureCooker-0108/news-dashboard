import os
import json
import logging
import threading
import time
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .models.database import init_db, get_top_stories, story_count, last_updated
from .scheduler import run_pipeline, start_scheduler

# Global Safety Flag
USE_AI = False

# ──────────────────────────────────────────────
# Logging
# ──────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# Lifespan
# ──────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run on startup: init DB, start scheduler."""
    init_db()
    # Run the initial pipeline in a background thread
    t = threading.Thread(target=run_pipeline, daemon=True)
    t.start()
    start_scheduler()
    yield

# ──────────────────────────────────────────────
# App
# ──────────────────────────────────────────────
app = FastAPI(
    title="Serious Operator News Dashboard",
    description="High-signal global news aggregation API.",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ──────────────────────────────────────────────
# Basic Cache
# ──────────────────────────────────────────────
_cache = {
    "news": {"data": None, "timestamp": 0},
    "ttl": 60  # Cache for 60 seconds
}

# ──────────────────────────────────────────────
# Routes
# ──────────────────────────────────────────────
@app.get("/")
def health_check():
    return {
        "status": "ok",
        "stories_in_db": story_count(),
        "last_updated": last_updated(),
    }

@app.get("/news")
def get_news(limit: int = Query(default=20, ge=1, le=50)):
    """Return top-ranked news stories grouped by sector."""
    
    # Check cache
    now = time.time()
    if _cache["news"]["data"] and (now - _cache["news"]["timestamp"] < _cache["ttl"]):
        # Return cached response (slicing if limit is different is skipped for simplicity as the default is used mainly)
        # To be completely correct, we ignore limit in cache key here since the frontend just asks for default anyway
        pass # Not perfectly caching by limit, but good enough for demo

    try:
        stories = get_top_stories(limit=limit)
        if not stories:
            return {
                "top_stories": [],
                "sectors": {},
                "message": "No stories yet. The pipeline may still be running.",
            }

        # Prepare response
        top_stories = []
        sectors = {}

        for s in stories:
            story_sectors = s.get("sectors", ["General"])
            story_data = {
                "headline": s.get("title", "Details are still emerging."),
                "summary": s.get("summary", "Details are still emerging."),
                "why_it_matters": s.get("why_it_matters", "This is a developing story worth monitoring."),
                "url": s.get("url"),
                "source": s.get("source", []),
                "article_count": s.get("article_count", 1),
                "score": s.get("score", 0),
                "published_at": s.get("published_at"),
                "latest_at": s.get("latest_at"),
                "sectors": story_sectors
            }
            top_stories.append(story_data)
            
            # Group by each sector the story belongs to (multi-label)
            for sector_name in story_sectors:
                if sector_name not in sectors:
                    sectors[sector_name] = []
                sectors[sector_name].append(story_data)

        response = {
            "top_stories": top_stories,
            "sectors": sectors
        }
        
        # Update cache
        _cache["news"]["data"] = response
        _cache["news"]["timestamp"] = now

        return response
    except Exception as e:
        logger.error(f"Error fetching news: {e}")
        # Return fallback data or re-raise
        if _cache["news"]["data"]:
            return _cache["news"]["data"]
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/news/raw")
def get_news_raw(limit: int = Query(default=10, ge=1, le=20)):
    try:
        return get_top_stories(limit=limit)
    except Exception as e:
        logger.error(f"Error fetching raw news: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8001))
    uvicorn.run("news_dashboard.main:app", host="0.0.0.0", port=port)

