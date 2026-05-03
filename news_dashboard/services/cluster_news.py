import logging
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.cluster import AgglomerativeClustering
from sklearn.metrics.pairwise import cosine_distances
from typing import Optional
from ..config import CLUSTER_THRESHOLD

logger = logging.getLogger(__name__)

# Lazy-loaded model singleton
_model: Optional[SentenceTransformer] = None

def _get_model() -> SentenceTransformer:
    """Load the embedding model once."""
    global _model
    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model

def _build_text(article: dict) -> str:
    """Combine title + snippet for richer embeddings."""
    title = article.get("title", "")
    snippet = article.get("content_snippet", "")
    if snippet:
        return f"{title}. {snippet[:200]}"
    return title

def cluster_articles(articles: list[dict]) -> list[list[dict]]:
    """Embed and cluster articles."""
    if not articles:
        return []
    if len(articles) == 1:
        return [articles]

    try:
        model = _get_model()
        texts = [_build_text(a) for a in articles]
        embeddings = model.encode(texts, show_progress_bar=False, batch_size=64)
        embeddings = np.array(embeddings)

        distance_matrix = cosine_distances(embeddings)
        clustering = AgglomerativeClustering(
            n_clusters=None,
            distance_threshold=CLUSTER_THRESHOLD,
            metric="precomputed",
            linkage="average",
        )
        labels = clustering.fit_predict(distance_matrix)

        clusters_dict: dict[int, list[dict]] = {}
        for idx, label in enumerate(labels):
            clusters_dict.setdefault(int(label), []).append(articles[idx])

        return list(clusters_dict.values())
    except Exception:
        logger.exception("Clustering failed")
        return [[a] for a in articles]
