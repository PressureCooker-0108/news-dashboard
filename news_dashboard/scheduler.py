import logging
from datetime import datetime, timezone
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from .models.database import save_articles, get_recent_articles, save_stories
from .services.fetch_news import fetch_rss_feeds
from .services.clean_news import clean_articles
from .services.cluster_news import cluster_articles
from .services.classify_news import classify_sectors
from .services.rank_news import rank_clusters
from .services.summarize_news import summarize_stories

logger = logging.getLogger(__name__)

def _build_cluster_text(cluster: list[dict]) -> str:
    """Combine titles + snippets from the cluster for context-aware classification."""
    parts = []
    for article in cluster[:5]:  # Limit to 5 articles to keep text manageable
        title = article.get("title", "")
        snippet = article.get("content_snippet", "")
        if title:
            parts.append(title)
        if snippet:
            parts.append(snippet[:150])
    return " ".join(parts)

def run_pipeline() -> None:
    """Execute the full news pipeline."""
    start = datetime.now(timezone.utc)
    logger.info("═══ Pipeline run started at %s ═══", start.isoformat())

    try:
        # 1. Fetch
        articles = fetch_rss_feeds()
        if not articles:
            logger.warning("No articles fetched")
            return

        # 2. Clean
        articles = clean_articles(articles)

        # 3. Persist articles
        save_articles(articles)

        # 4. Load recent window
        recent = get_recent_articles(hours=24)
        if not recent:
            logger.warning("No recent articles")
            return

        # 5. Cluster
        clusters = cluster_articles(recent)

        # 6. Rank
        ranked = rank_clusters(clusters)

        # 7. Classify (Multi-sector with full context)
        for story in ranked:
            cluster = story["cluster"]
            combined_text = _build_cluster_text(cluster)
            story["sectors"] = classify_sectors(combined_text)

        # 8. Summarise
        stories = summarize_stories(ranked)

        # 9. Save Stories
        save_stories(stories)

        elapsed = (datetime.now(timezone.utc) - start).total_seconds()
        logger.info("═══ Pipeline complete: %d stories in %.1fs ═══", len(stories), elapsed)

    except Exception:
        logger.exception("Pipeline run failed")

def start_scheduler() -> None:
    """Start APScheduler."""
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
