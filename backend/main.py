import logging
import threading
import json
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, StreamingResponse

from models.database import (
    init_db, get_top_stories, story_count, last_updated,
    get_stories_by_sector, get_market_data, get_latest_briefing,
    get_source_diversity, get_trending_topics, get_sector_summaries
)
from scheduler import run_pipeline, start_scheduler
from services.market_data import fetch_and_store_market_data, get_big_market_movers
from services.briefing import generate_briefing
from services.pdf_briefing import generate_pdf_briefing

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

# ── Cache ──
_news_cache: dict = {}
_news_cache_ts: float = 0
_CACHE_TTL = 60  # seconds

_SECTORS = ["All", "Markets", "Tech", "Geopolitics", "Energy", "India", "General"]

# ── Lifespan ──

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing database...")
    init_db()
    logger.info("Database initialized.")

    # Run pipeline in background on startup
    def _initial_run():
        try:
            run_pipeline()
        except Exception as e:
            logger.warning(f"Initial pipeline run failed (will retry via scheduler): {e}")

    t = threading.Thread(target=_initial_run, daemon=True)
    t.start()

    # Start APScheduler
    start_scheduler()

    yield


app = FastAPI(title="Serious Operator News Dashboard", version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Health ──

@app.get("/")
def health():
    return {
        "status": "seriously operational",
        "stories": story_count(),
        "last_updated": last_updated(),
    }


# ── News Endpoints ──

@app.get("/news")
def get_news(force_refresh: bool = Query(False, description="Bypass cache")):
    global _news_cache, _news_cache_ts
    now = datetime.now(timezone.utc).timestamp()

    if not force_refresh and _news_cache and (now - _news_cache_ts) < _CACHE_TTL:
        return _news_cache

    try:
        stories = get_top_stories(limit=20)

        # Group stories by sector
        sector_stories: dict[str, list[dict]] = {}
        for s in stories:
            for sector in s.get("sectors", ["General"]):
                sector_stories.setdefault(sector, []).append(s)

        # Order sectors
        sectors_in_order = [s for s in _SECTORS if s != "All" and s in sector_stories]

        result = {
            "top_stories": stories,
            "sector_stories": sector_stories,
            "sectors": sectors_in_order,
            "last_updated": last_updated(),
        }

        _news_cache = result
        _news_cache_ts = now
        return result

    except Exception as e:
        logger.exception(f"Failed to fetch news: {e}")
        if _news_cache:
            return _news_cache
        return {"top_stories": [], "sector_stories": {}, "sectors": [], "last_updated": None}


@app.get("/news/stories")
def get_all_stories(limit: int = Query(20, ge=1, le=100)):
    """Get all top stories raw."""
    return {"stories": get_top_stories(limit=limit)}


@app.get("/news/sectors")
def get_sectors():
    """Get list of active sectors with story counts."""
    stories = get_top_stories(limit=100)
    sector_counts: dict[str, int] = {}
    for s in stories:
        for sector in s.get("sectors", ["General"]):
            sector_counts[sector] = sector_counts.get(sector, 0) + 1
    return {"sectors": [{"name": k, "count": v} for k, v in sorted(sector_counts.items(), key=lambda x: -x[1])]}


@app.get("/news/sector/{sector}")
def get_sector_news(sector: str, limit: int = Query(20, ge=1, le=50)):
    """Get top stories for a specific sector."""
    stories = get_stories_by_sector(sector, limit=limit)
    return {
        "sector": sector,
        "stories": stories,
        "count": len(stories),
    }


@app.get("/news/sector-summaries")
def sector_summaries():
    """Get summary descriptions for each sector."""
    return {"summaries": get_sector_summaries()}


# ── Market Data ──

@app.get("/markets")
def markets():
    """Get current market data for all tracked tickers."""
    try:
        data = get_market_data()
        if not data:
            # Fetch fresh data
            data = fetch_and_store_market_data()
        movers = get_big_market_movers()
        return {
            "all": data,
            "gainers": movers["gainers"],
            "losers": movers["losers"],
            "indices": movers["indices"],
        }
    except Exception as e:
        logger.exception(f"Market data error: {e}")
        return {"all": [], "gainers": [], "losers": [], "indices": []}


@app.post("/markets/refresh")
def refresh_markets():
    """Force refresh market data."""
    data = fetch_and_store_market_data()
    return {"status": "refreshed", "count": len(data)}


# ── Briefing & Export ──

@app.get("/briefing")
def get_briefing():
    """Get the latest executive briefing."""
    briefing = get_latest_briefing()
    if briefing:
        return briefing
    # Generate on demand
    content = generate_briefing()
    return {"content": content, "created_at": datetime.now(timezone.utc).isoformat()}


@app.post("/briefing/generate")
def generate_new_briefing():
    """Generate a fresh executive briefing."""
    content = generate_briefing()
    return {"content": content, "created_at": datetime.now(timezone.utc).isoformat()}


@app.get("/export/markdown")
def export_markdown():
    """Export the full briefing as markdown."""
    briefing = get_latest_briefing()
    content = briefing["content"] if briefing else generate_briefing()
    filename = f"operator-brief-{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.md"
    return PlainTextResponse(
        content,
        media_type="text/markdown",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@app.get("/export/json")
def export_json():
    """Export all data as JSON."""
    stories = get_top_stories(limit=50)
    market = get_market_data()
    diversity = get_source_diversity()
    data = {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "stories": stories,
        "markets": market,
        "source_diversity": diversity,
    }
    filename = f"operator-brief-{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.json"
    return JSONResponse(
        content=data,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@app.get("/export/pdf")
def export_pdf():
    """Export the full briefing as a structured PDF."""
    try:
        pdf_bytes = generate_pdf_briefing()
        return StreamingResponse(
            iter([pdf_bytes]),
            media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=operator-brief-{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.pdf",
            "Content-Type": "application/pdf",
        },
        )
    except Exception as e:
        logger.exception(f"PDF generation failed: {e}")
        return PlainTextResponse("Failed to generate PDF", status_code=500)


# ── Source Diversity ──

@app.get("/sources")
def source_diversity():
    """Get source diversity information."""
    return {"sources": get_source_diversity()}


# ── Trending ──

@app.get("/trending")
def trending(hours: int = Query(48, ge=1, le=168)):
    """Get trending topics over the specified time period."""
    return {"trending": get_trending_topics(hours=hours)}


# ── Pipeline Control ──

@app.post("/pipeline/run")
def trigger_pipeline():
    """Manually trigger the news pipeline."""
    try:
        run_pipeline()
        return {"status": "pipeline completed"}
    except Exception as e:
        logger.exception("Pipeline run failed")
        return {"status": "error", "detail": str(e)}


# ── Main ──

if __name__ == "__main__":
    import os
    import uvicorn
    port = int(os.environ.get("PORT", 8001))
    uvicorn.run(app, host="0.0.0.0", port=port)
