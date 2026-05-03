import logging
from datetime import datetime, timezone
from dateutil import parser as dateutil_parser
from ..config import COVERAGE_WEIGHT, MAX_STORIES, RECENCY_WEIGHT

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
    """1.0 if < 2h old, decay to 0 at 24h."""
    now = datetime.now(timezone.utc)
    age_hours = (now - latest).total_seconds() / 3600.0
    if age_hours <= 2:
        return 1.0
    if age_hours >= 24:
        return 0.0
    return max(0.0, 1.0 - (age_hours - 2) / 22.0)

def rank_clusters(clusters: list[list[dict]]) -> list[dict]:
    """Score each cluster and return top MAX_STORIES."""
    if not clusters:
        return []

    max_size = max(len(c) for c in clusters)
    scored: list[dict] = []

    for cluster in clusters:
        size = len(cluster)
        coverage = size / max_size if max_size > 0 else 0.0
        latest = _latest_timestamp(cluster)
        recency = _recency_score(latest)

        final = COVERAGE_WEIGHT * coverage + RECENCY_WEIGHT * recency
        sources = sorted({a.get("source", "Unknown") for a in cluster})

        scored.append({
            "cluster": cluster,
            "score": round(final, 4),
            "article_count": size,
            "latest_at": latest.isoformat(),
            "sources": sources,
        })

    scored.sort(key=lambda s: s["score"], reverse=True)
    return scored[:MAX_STORIES]
