"""
Pipeline orchestrator and APScheduler cron job.
"""

import logging
from datetime import datetime, timezone

from .fetcher import fetch_all_feeds
from .database import save_articles, get_recent_articles, save_stories
from .clusterer import cluster_articles
from .ranker import rank_clusters
from .summarizer import summarize_stories

logger = logging.getLogger(__name__)


def run_pipeline() -> None:
    """
    Execute the full news pipeline:
    1. Fetch RSS feeds
    2. Save articles to DB
    3. Load recent articles (last 24h)
    4. Cluster into stories
    5. Rank stories
    6. Summarise stories
    7. Save stories to DB
    """
    start = datetime.now(timezone.utc)
    logger.info("═══ Pipeline run started at %s ═══", start.isoformat())

    try:
        # 1. Fetch
        articles = fetch_all_feeds()
        if not articles:
            logger.warning("No articles fetched — skipping rest of pipeline")
            return

        # 2. Persist
        save_articles(articles)

        # 3. Recent window
        recent = get_recent_articles(hours=24)
        logger.info("Recent articles (24h window): %d", len(recent))
        if not recent:
            logger.warning("No recent articles — skipping clustering")
            return

        # 4. Cluster
        clusters = cluster_articles(recent)

        # 5. Rank
        ranked = rank_clusters(clusters)

        # 6. Summarise
        stories = summarize_stories(ranked)

        # 7. Save
        save_stories(stories)

        elapsed = (datetime.now(timezone.utc) - start).total_seconds()
        logger.info(
            "═══ Pipeline complete: %d stories in %.1fs ═══", len(stories), elapsed
        )

    except Exception:
        logger.exception("Pipeline run failed")


def start_scheduler() -> None:
    """
    Start APScheduler with a daily cron trigger at 07:00 local time.
    The scheduler runs in a background thread — non-blocking.
    """
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger

    scheduler = BackgroundScheduler()
    scheduler.add_job(
        run_pipeline,
        trigger=CronTrigger(hour=7, minute=0),
        id="daily_news_pipeline",
        name="Daily news pipeline",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Scheduler started — next run daily at 07:00 local time")
