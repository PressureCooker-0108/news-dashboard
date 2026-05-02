"""
Embed article titles/snippets and cluster into stories
using sentence-transformers + AgglomerativeClustering.
"""

import logging
from typing import Optional

import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.cluster import AgglomerativeClustering
from sklearn.metrics.pairwise import cosine_distances

from .config import CLUSTER_THRESHOLD

logger = logging.getLogger(__name__)

# Lazy-loaded model singleton
_model: Optional[SentenceTransformer] = None


def _get_model() -> SentenceTransformer:
    """Load the embedding model once (downloads on first run)."""
    global _model
    if _model is None:
        logger.info("Loading sentence-transformers model (all-MiniLM-L6-v2) …")
        _model = SentenceTransformer("all-MiniLM-L6-v2")
        logger.info("Model loaded successfully.")
    return _model


def _build_text(article: dict) -> str:
    """Combine title + snippet for richer embeddings."""
    title = article.get("title", "")
    snippet = article.get("content_snippet", "")
    if snippet:
        return f"{title}. {snippet[:200]}"
    return title


def cluster_articles(articles: list[dict]) -> list[list[dict]]:
    """
    Embed and cluster articles. Returns a list of clusters,
    where each cluster is a list of article dicts.
    Singletons are allowed.
    """
    if not articles:
        return []

    if len(articles) == 1:
        return [articles]

    try:
        model = _get_model()
        texts = [_build_text(a) for a in articles]
        embeddings = model.encode(texts, show_progress_bar=False, batch_size=64)
        embeddings = np.array(embeddings)

        # Cosine distance matrix
        distance_matrix = cosine_distances(embeddings)

        clustering = AgglomerativeClustering(
            n_clusters=None,
            distance_threshold=CLUSTER_THRESHOLD,
            metric="precomputed",
            linkage="average",
        )
        labels = clustering.fit_predict(distance_matrix)

        # Group articles by label
        clusters: dict[int, list[dict]] = {}
        for idx, label in enumerate(labels):
            clusters.setdefault(int(label), []).append(articles[idx])

        logger.info(
            "Clustered %d articles into %d stories", len(articles), len(clusters)
        )
        return list(clusters.values())

    except Exception:
        logger.exception("Clustering failed — falling back to singleton clusters")
        return [[a] for a in articles]
