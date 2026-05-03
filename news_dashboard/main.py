import json
import logging
import threading
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from .models.database import init_db, get_top_stories, story_count, last_updated
from .scheduler import run_pipeline, start_scheduler

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
            "headline": s["title"],
            "summary": s["summary"],
            "why_it_matters": s["why_it_matters"],
            "url": s.get("url"),
            "source": s["source"],
            "article_count": s["article_count"],
            "score": s["score"],
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

    return {
        "top_stories": top_stories,
        "sectors": sectors
    }

@app.get("/news/raw")
def get_news_raw(limit: int = Query(default=10, ge=1, le=20)):
    stories = get_top_stories(limit=limit)
    return stories

