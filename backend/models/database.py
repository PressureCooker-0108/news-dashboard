import os
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL")

# Use connection pooling
engine = create_engine(
    DATABASE_URL, 
    pool_size=5, 
    max_overflow=10,
    connect_args={"sslmode": "require"}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    """Dependency to provide a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

from datetime import datetime, timedelta, timezone
from sqlalchemy import desc

# Import models inline to avoid circular imports during setup
def init_db():
    """Initializes the database schema."""
    from .models import Article, Cluster, Summary
    Base.metadata.create_all(bind=engine)

# ──────────────────────────────────────────────
# Helper Functions
# ──────────────────────────────────────────────

def save_articles(articles_data: list[dict]) -> int:
    from .models import Article
    db = SessionLocal()
    inserted = 0
    now = datetime.now(timezone.utc).isoformat()
    try:
        for a in articles_data:
            exists = db.query(Article).filter(Article.url == a["url"]).first()
            if not exists:
                new_article = Article(
                    id=a["id"],
                    title=a["title"],
                    url=a["url"],
                    source=a["source"],
                    published_at=a["published_at"],
                    content_snippet=a.get("content_snippet", ""),
                    fetched_at=now
                )
                db.add(new_article)
                inserted += 1
        db.commit()
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()
    return inserted

def get_recent_articles(hours: int = 24) -> list[dict]:
    from .models import Article
    db = SessionLocal()
    try:
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
        articles = db.query(Article).filter(Article.fetched_at >= cutoff).all()
        results = [
            {
                "id": a.id,
                "title": a.title,
                "url": a.url,
                "source": a.source,
                "published_at": a.published_at,
                "content_snippet": a.content_snippet,
                "fetched_at": a.fetched_at,
                "cluster_id": a.cluster_id
            }
            for a in articles
        ]
        return results
    finally:
        db.close()

def save_stories(stories_data: list[dict]) -> None:
    from .models import Summary
    db = SessionLocal()
    try:
        db.query(Summary).delete()
        now = datetime.now(timezone.utc).isoformat()
        for s in stories_data:
            # sectors is a list — serialize to JSON string for storage
            sectors = s.get("sectors", ["General"])
            if isinstance(sectors, list):
                sectors_str = json.dumps(sectors)
            else:
                sectors_str = json.dumps([sectors])

            new_story = Summary(
                title=s["title"],
                summary=s["summary"],
                why_it_matters=s["why_it_matters"],
                url=s.get("url"),
                score=s["score"],
                article_count=s["article_count"],
                source=",".join(s.get("source", [])),
                published_at=s.get("published_at", now),
                latest_at=s.get("latest_at", now),
                created_at=now,
                sectors=sectors_str
            )
            db.add(new_story)
        db.commit()
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()

def get_top_stories(limit: int = 10) -> list[dict]:
    from .models import Summary
    db = SessionLocal()
    try:
        stories = db.query(Summary).order_by(desc(Summary.score)).limit(limit).all()
        results = []
        for s in stories:
            # Deserialize sectors JSON string back to list
            try:
                sectors = json.loads(s.sectors) if s.sectors else ["General"]
            except (json.JSONDecodeError, TypeError):
                sectors = ["General"]

            results.append({
                "title": s.title,
                "summary": s.summary,
                "why_it_matters": s.why_it_matters,
                "url": s.url,
                "score": s.score,
                "article_count": s.article_count,
                "source": s.source.split(",") if s.source else [],
                "published_at": s.published_at,
                "latest_at": s.latest_at,
                "created_at": s.created_at,
                "sectors": sectors
            })
        return results
    finally:
        db.close()

def story_count() -> int:
    from .models import Summary
    db = SessionLocal()
    try:
        return db.query(Summary).count()
    finally:
        db.close()

def last_updated() -> str | None:
    from .models import Summary
    db = SessionLocal()
    try:
        res = db.query(Summary.created_at).order_by(desc(Summary.created_at)).first()
        return res[0] if res else None
    finally:
        db.close()
