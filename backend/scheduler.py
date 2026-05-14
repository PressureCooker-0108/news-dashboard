import logging
import time
from datetime import datetime, timezone
from apscheduler.schedulers.background import BackgroundScheduler

from services.fetch_news import fetch_rss_feeds
from services.clean_news import clean_articles
from services.cluster_news import cluster_articles
from services.classify_news import classify_sectors
from services.summarize_news import summarize_stories
from services.rank_news import rank_clusters
from services.market_data import fetch_and_store_market_data
from services.briefing import generate_briefing
from models.database import (
    save_articles, get_recent_articles, save_stories,
    init_db, save_sector_summary
)

logger = logging.getLogger(__name__)

_scheduler = BackgroundScheduler()


def _build_cluster_text(cluster: list[dict]) -> str:
    """Build a combined text snippet from a cluster for classification."""
    parts = []
    for a in cluster[:5]:
        title = a.get("title", "")
        snippet = a.get("content_snippet", "")[:150]
        parts.append(f"{title}. {snippet}" if snippet else title)
    return " ".join(parts)


def run_pipeline() -> None:
    """Run the full news processing pipeline."""
    start = time.time()
    logger.info("=== Pipeline start ===")

    try:
        # 1. Fetch
        logger.info("Fetching articles...")
        articles = fetch_rss_feeds()
        logger.info(f"Fetched {len(articles)} articles")

        # 2. Clean
        articles = clean_articles(articles)
        logger.info(f"Cleaned {len(articles)} articles")

        # 3. Persist
        inserted = save_articles(articles)
        logger.info(f"Inserted {inserted} new articles")

        # 4. Get recent articles for clustering
        recent = get_recent_articles(hours=24)
        logger.info(f"Got {len(recent)} recent articles for clustering")

        if not recent:
            logger.warning("No recent articles to process")
            return

        # 5. Cluster using HDBSCAN with topic modeling
        clusters = cluster_articles(recent)
        logger.info(f"Created {len(clusters)} clusters")
        cluster_sizes = [len(c) for c in clusters]
        if cluster_sizes:
            logger.info(
                f"Cluster sizes: min={min(cluster_sizes)} max={max(cluster_sizes)} "
                f"avg={sum(cluster_sizes)/len(cluster_sizes):.1f}"
            )

        # 6. Rank clusters
        ranked = rank_clusters(clusters)
        logger.info(f"Ranked {len(ranked)} stories")

        # 7. Classify each cluster
        for story in ranked:
            cluster = story["cluster"]
            text = _build_cluster_text(cluster)
            sectors = classify_sectors(text)
            story["sectors"] = sectors

        # 8. Summarize
        stories = summarize_stories(ranked)

        # 9. Generate sector summaries
        sector_groups: dict[str, list[dict]] = {}
        for s in stories:
            for sector in s.get("sectors", ["General"]):
                sector_groups.setdefault(sector, []).append(s)

        for sector, sector_stories in sector_groups.items():
            headlines = [s["title"] for s in sector_stories[:5]]
            summary = f"{len(sector_stories)} stories in {sector}. " + " ".join(
                f"'{h}'" for h in headlines[:3]
            )
            try:
                save_sector_summary(sector, summary, len(sector_stories))
            except Exception as e:
                logger.warning(f"Failed to save sector summary for {sector}: {e}")

        # 10. Save stories
        logger.info(f"Saving {len(stories)} stories...")
        save_stories(stories)
        logger.info(f"Saved {len(stories)} stories")

        # 11. Fetch market data
        try:
            market_data = fetch_and_store_market_data()
            logger.info(f"Fetched {len(market_data)} market data points")
        except Exception as e:
            logger.warning(f"Market data fetch failed: {e}")

        # 12. Generate briefing
        try:
            generate_briefing()
            logger.info("Briefing generated")
        except Exception as e:
            logger.warning(f"Briefing generation failed: {e}")

        elapsed = time.time() - start
        logger.info(f"=== Pipeline complete in {elapsed:.1f}s ===")

    except Exception as e:
        logger.exception(f"Pipeline failed: {e}")
        elapsed = time.time() - start
        logger.info(f"=== Pipeline failed after {elapsed:.1f}s ===")


def start_scheduler():
    """Start the APScheduler to run pipeline daily."""
    if _scheduler.get_jobs():
        return  # Already started

    _scheduler.add_job(
        run_pipeline,
        "interval",
        hours=6,
        id="news_pipeline",
        replace_existing=True,
    )
    _scheduler.start()
    logger.info("Scheduler started — pipeline runs every 6 hours")
