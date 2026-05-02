"""
Score and rank story clusters by coverage + recency.
"""

import logging
from datetime import datetime, timezone

from dateutil import parser as dateutil_parser

from .config import COVERAGE_WEIGHT, MAX_STORIES, RECENCY_WEIGHT

logger = logging.getLogger(__name__)


def _latest_timestamp(cluster: list[dict]) -> datetime:
    """Return the most recent published_at in a cluster."""
    latest = datetime.min.replace(tzinfo=timezone.utc)
    for article in cluster:
        raw = article.get("published_at")
        if not raw:
            continue
        try:
            dt = dateutil_parser.parse(raw)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            if dt > latest:
                latest = dt
        except (ValueError, OverflowError):
            continue
    return latest


def _recency_score(latest: datetime) -> float:
    """
    1.0 if the story broke < 2 hours ago,
    decays linearly to 0.0 at 24 hours,
    capped at 0.0 for anything older.
    """
    now = datetime.now(timezone.utc)
    age_hours = (now - latest).total_seconds() / 3600.0
    if age_hours <= 2:
        return 1.0
    if age_hours >= 24:
        return 0.0
    # Linear decay from 1.0 at 2h to 0.0 at 24h
    return max(0.0, 1.0 - (age_hours - 2) / 22.0)


def rank_clusters(clusters: list[list[dict]]) -> list[dict]:
    """
    Score each cluster and return the top MAX_STORIES,
    sorted descending by final score.

    Returns a list of dicts:
        { "cluster": [...articles...], "score": float,
          "article_count": int, "latest_at": str, "sources": [...] }
    """
    if not clusters:
        return []

    # Coverage normalisation: largest cluster size
    max_size = max(len(c) for c in clusters)

    scored: list[dict] = []
    for cluster in clusters:
        size = len(cluster)
        coverage = size / max_size if max_size > 0 else 0.0

        latest = _latest_timestamp(cluster)
        recency = _recency_score(latest)

        final = COVERAGE_WEIGHT * coverage + RECENCY_WEIGHT * recency

        sources = sorted({a.get("source", "Unknown") for a in cluster})

        scored.append(
            {
                "cluster": cluster,
                "score": round(final, 4),
                "article_count": size,
                "latest_at": latest.isoformat(),
                "sources": sources,
            }
        )

    scored.sort(key=lambda s: s["score"], reverse=True)
    top = scored[:MAX_STORIES]
    logger.info("Ranked %d clusters → top %d stories", len(scored), len(top))
    return top
