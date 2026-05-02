"""
Serious Operator News Dashboard — FastAPI application.
"""

import json
import logging
import threading
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from .database import init_db, get_top_stories, story_count, last_updated
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
# Lifespan (startup / shutdown)
# ──────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run on startup: init DB, run pipeline once in background, start scheduler."""
    init_db()
    # Run the initial pipeline in a background thread so the server starts fast
    t = threading.Thread(target=run_pipeline, daemon=True)
    t.start()
    start_scheduler()
    logger.info("Server is ready.")
    yield
    logger.info("Server shutting down.")


# ──────────────────────────────────────────────
# App
# ──────────────────────────────────────────────
app = FastAPI(
    title="Serious Operator News Dashboard",
    description="High-signal global news aggregation, clustering, and ranking API.",
    version="1.0.0",
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
    """Health check endpoint."""
    return {
        "status": "ok",
        "stories_in_db": story_count(),
        "last_updated": last_updated(),
    }


@app.get("/news")
def get_news(limit: int = Query(default=20, ge=1, le=50)):
    """Return top-ranked news stories."""
    stories = get_top_stories(limit=limit)
    if not stories:
        return {
            "count": 0,
            "stories": [],
            "message": "No stories yet. The pipeline may still be running — check back in a minute.",
        }

    result = []
    for rank, s in enumerate(stories, start=1):
        sources = s["sources"]
        if isinstance(sources, str):
            try:
                sources = json.loads(sources)
            except (json.JSONDecodeError, ValueError):
                sources = [sources]
        result.append(
            {
                "rank": rank,
                "headline": s["headline"],
                "summary": s["summary"],
                "why_it_matters": s["why_it_matters"],
                "url": s.get("url"),
                "sources": sources,
                "article_count": s["article_count"],
                "score": s["score"],
                "latest_at": s.get("latest_at"),
            }
        )

    return {"count": len(result), "stories": result}


@app.get("/news/raw")
def get_news_raw(limit: int = Query(default=10, ge=1, le=20)):
    """Flat, minimal story list — optimised for frontend consumption."""
    stories = get_top_stories(limit=limit)
    if not stories:
        return []
    result = []
    for s in stories:
        sources = s["sources"]
        if isinstance(sources, str):
            try:
                sources = json.loads(sources)
            except Exception:
                sources = [sources]
        result.append({
            "headline": s["headline"],
            "summary": s["summary"],
            "why_it_matters": s["why_it_matters"],
            "sources": sources,
        })
    return result
