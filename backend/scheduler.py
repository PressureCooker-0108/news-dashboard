import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session
from loguru import logger

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
    init_db, save_sector_summary, SessionLocal
)

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
    """Run the full news processing pipeline.

    Pipeline steps 11 (market data) and 12 (briefing) are I/O-bound and
    independent of each other, so they run in parallel via ThreadPoolExecutor.
    Database writes (steps 3, 9, 10) share a single session for batching.
    """
    start = time.time()
    logger.info("=== Pipeline start ===")

    try:
        # ── Phase 1: Core pipeline (sequential) ──

        # 1. Fetch
        logger.info("Fetching articles...")
        articles = fetch_rss_feeds()
        logger.info(f"Fetched {len(articles)} articles")

        # 2. Clean
        articles = clean_articles(articles)
        logger.info(f"Cleaned {len(articles)} articles")

        # 3-10 use a single DB session for batched writes
        db: Session = SessionLocal()
        try:
            # 3. Persist (batched)
            inserted = save_articles(articles, db=db)
            logger.info(f"Inserted {inserted} new articles")

            # 4. Get recent articles for clustering (separate session — read-only)
            db.close()
            recent = get_recent_articles(hours=24)
            db = SessionLocal()
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

            # 9. Generate & save sector summaries (batched)
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
                    save_sector_summary(sector, summary, len(sector_stories), db=db)
                except Exception as e:
                    logger.warning(f"Failed to save sector summary for {sector}: {e}")

            # 10. Save stories (batched)
            logger.info(f"Saving {len(stories)} stories...")
            save_stories(stories, db=db)
            logger.info(f"Saved {len(stories)} stories")

            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

        # ── Phase 2: I/O parallel (market data + briefing run concurrently) ──
        _run_post_pipeline()

        elapsed = time.time() - start
        logger.info(f"=== Pipeline complete in {elapsed:.1f}s ===")

    except Exception as e:
        logger.exception(f"Pipeline failed: {e}")
        elapsed = time.time() - start
        logger.info(f"=== Pipeline failed after {elapsed:.1f}s ===")


def _run_post_pipeline() -> None:
    """Run market data and briefing in parallel (both are I/O-bound)."""
    def _market():
        md = fetch_and_store_market_data()
        logger.info(f"Fetched {len(md)} market data points")

    def _briefing():
        generate_briefing()
        logger.info("Briefing generated")

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = {
            executor.submit(_market): "market data",
            executor.submit(_briefing): "briefing",
        }
        for future in as_completed(futures):
            name = futures[future]
            try:
                future.result()
            except Exception as e:
                logger.warning(f"{name} failed: {e}")


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
