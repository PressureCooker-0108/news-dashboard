"""
SQLite database layer for articles and stories.
"""

import sqlite3
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from .config import DATABASE_PATH

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# Schema
# ──────────────────────────────────────────────
_SCHEMA = """
CREATE TABLE IF NOT EXISTS articles (
    id          TEXT PRIMARY KEY,
    title       TEXT NOT NULL,
    url         TEXT UNIQUE NOT NULL,
    source      TEXT,
    published_at TEXT,
    content_snippet TEXT,
    fetched_at  TEXT NOT NULL,
    cluster_id  INTEGER
);

CREATE TABLE IF NOT EXISTS stories (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    headline        TEXT NOT NULL,
    summary         TEXT,
    why_it_matters  TEXT,
    score           REAL,
    article_count   INTEGER,
    sources         TEXT,
    latest_at       TEXT,
    created_at      TEXT NOT NULL
);
"""


def _connect() -> sqlite3.Connection:
    """Return a connection with row-factory enabled."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn


# ──────────────────────────────────────────────
# Initialisation
# ──────────────────────────────────────────────
def init_db() -> None:
    """Create tables if they don't exist."""
    try:
        conn = _connect()
        conn.executescript(_SCHEMA)
        conn.commit()
        conn.close()
        logger.info("Database initialised at %s", DATABASE_PATH)
    except Exception:
        logger.exception("Failed to initialise database")
        raise


# ──────────────────────────────────────────────
# Article helpers
# ──────────────────────────────────────────────
def save_articles(articles: list[dict]) -> int:
    """Insert articles, skipping duplicates. Returns count of newly inserted rows."""
    if not articles:
        return 0
    conn = _connect()
    inserted = 0
    for a in articles:
        try:
            conn.execute(
                """
                INSERT OR IGNORE INTO articles
                    (id, title, url, source, published_at, content_snippet, fetched_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    a["id"],
                    a["title"],
                    a["url"],
                    a["source"],
                    a["published_at"],
                    a.get("content_snippet", ""),
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            inserted += conn.total_changes  # rough count
        except Exception:
            logger.warning("Skipping article %s: duplicate or error", a.get("url"))
    conn.commit()
    conn.close()
    logger.info("Saved %d new articles (of %d fetched)", inserted, len(articles))
    return inserted


def get_recent_articles(hours: int = 24) -> list[dict]:
    """Return articles fetched within the last `hours` hours."""
    conn = _connect()
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
    rows = conn.execute(
        "SELECT * FROM articles WHERE fetched_at >= ? ORDER BY published_at DESC",
        (cutoff,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_article_cluster(article_id: str, cluster_id: int) -> None:
    """Tag an article with its cluster id."""
    conn = _connect()
    conn.execute(
        "UPDATE articles SET cluster_id = ? WHERE id = ?", (cluster_id, article_id)
    )
    conn.commit()
    conn.close()


# ──────────────────────────────────────────────
# Story helpers
# ──────────────────────────────────────────────
def save_stories(stories: list[dict]) -> None:
    """Wipe old stories and insert fresh batch."""
    conn = _connect()
    conn.execute("DELETE FROM stories")  # replace with latest run
    now = datetime.now(timezone.utc).isoformat()
    for s in stories:
        conn.execute(
            """
            INSERT INTO stories
                (headline, summary, why_it_matters, score, article_count, sources, latest_at, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                s["headline"],
                s["summary"],
                s["why_it_matters"],
                s["score"],
                s["article_count"],
                ",".join(s.get("sources", [])),
                s.get("latest_at", now),
                now,
            ),
        )
    conn.commit()
    conn.close()
    logger.info("Saved %d stories to DB", len(stories))


def get_top_stories(limit: int = 10) -> list[dict]:
    """Return top stories ordered by score, with a cap."""
    conn = _connect()
    rows = conn.execute(
        "SELECT * FROM stories ORDER BY score DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    results = []
    for r in rows:
        d = dict(r)
        d["sources"] = d.get("sources", "").split(",") if d.get("sources") else []
        results.append(d)
    return results


def story_count() -> int:
    """Number of stories currently in the DB."""
    conn = _connect()
    count = conn.execute("SELECT COUNT(*) FROM stories").fetchone()[0]
    conn.close()
    return count


def last_updated() -> Optional[str]:
    """ISO timestamp of the most recently created story, or None."""
    conn = _connect()
    row = conn.execute(
        "SELECT created_at FROM stories ORDER BY created_at DESC LIMIT 1"
    ).fetchone()
    conn.close()
    return row[0] if row else None
