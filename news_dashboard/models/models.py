from sqlalchemy import Column, Integer, String, Float
from .database import Base

class Article(Base):
    """Stores individual news articles from RSS feeds."""
    __tablename__ = "articles"
    
    id = Column(String, primary_key=True, index=True)
    title = Column(String, nullable=False)
    url = Column(String, unique=True, index=True, nullable=False)
    source = Column(String)
    published_at = Column(String)
    content_snippet = Column(String)
    fetched_at = Column(String, nullable=False)
    cluster_id = Column(Integer, nullable=True)

class Cluster(Base):
    """Stores clusters of related articles."""
    __tablename__ = "clusters"
    
    id = Column(Integer, primary_key=True, index=True)
    theme = Column(String)

class Summary(Base):
    """Stores processed, ranked, and summarized stories."""
    __tablename__ = "summaries"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    summary = Column(String)
    why_it_matters = Column(String)
    url = Column(String)
    score = Column(Float)
    article_count = Column(Integer)
    source = Column(String)
    published_at = Column(String)
    latest_at = Column(String)
    created_at = Column(String, nullable=False)
    # Multi-label sectors stored as JSON string e.g. '["Tech", "Markets"]'
    sectors = Column(String, default='["General"]')
