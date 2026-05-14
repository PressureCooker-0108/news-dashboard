import logging
import numpy as np
from sentence_transformers import SentenceTransformer
from hdbscan import HDBSCAN
from sklearn.decomposition import LatentDirichletAllocation
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from typing import Optional
from config import CLUSTER_THRESHOLD
from models.database import save_embedding, get_cached_embeddings

logger = logging.getLogger(__name__)

_model: Optional[SentenceTransformer] = None


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def _build_text(article: dict) -> str:
    title = article.get("title", "")
    snippet = article.get("content_snippet", "")
    return f"{title}. {snippet}" if snippet else title


def _get_embeddings(articles: list[dict]) -> np.ndarray:
    """Get embeddings with caching support."""
    model = _get_model()
    texts = [_build_text(a) for a in articles]

    cached = get_cached_embeddings()
    all_embeddings = []
    texts_to_encode = []
    indices_to_encode = []

    for i, article in enumerate(articles):
        aid = article.get("id", "")
        if aid in cached:
            all_embeddings.append(np.array(cached[aid]))
        else:
            all_embeddings.append(None)
            texts_to_encode.append(texts[i])
            indices_to_encode.append(i)

    # Batch encode uncached articles
    if texts_to_encode:
        new_embs = model.encode(texts_to_encode, show_progress_bar=False)
        for idx, emb in zip(indices_to_encode, new_embs):
            all_embeddings[idx] = emb
            try:
                save_embedding(articles[idx]["id"], emb.tolist())
            except Exception:
                pass

    return np.array([e for e in all_embeddings])


def _extract_topics(texts: list[str], n_topics: int = 5) -> list[int]:
    """Extract latent topics using LDA."""
    if len(texts) < 3 or n_topics < 2:
        return [0] * len(texts)

    try:
        vectorizer = CountVectorizer(max_df=0.85, min_df=1, stop_words="english", max_features=500)
        dtm = vectorizer.fit_transform(texts)

        n_components = min(n_topics, dtm.shape[0] - 1, dtm.shape[1] - 1)
        if n_components < 2:
            return [0] * len(texts)

        lda = LatentDirichletAllocation(n_components=n_components, random_state=42, max_iter=50)
        topic_dist = lda.fit_transform(dtm)
        return topic_dist.argmax(axis=1).tolist()
    except Exception as e:
        logger.warning(f"Topic modeling failed: {e}")
        return [0] * len(texts)


def cluster_articles(articles: list[dict]) -> list[list[dict]]:
    """Cluster articles using HDBSCAN + topic modeling with embedding caching.
    
    Deduplication and embedding computation happen in one pass to avoid 
    computing embeddings twice.
    """
    if not articles:
        return []

    try:
        if len(articles) < 2:
            return [[a] for a in articles]

        # 1. Get embeddings (with caching) for ALL articles first
        embeddings = _get_embeddings(articles)

        # 2. Deduplicate using the same embeddings
        if len(articles) > 1:
            sim_matrix = cosine_similarity(embeddings)
            kept_indices: set[int] = set()
            for i in range(len(articles)):
                if i in kept_indices:
                    continue
                duplicates = [
                    j for j in range(i + 1, len(articles))
                    if sim_matrix[i][j] > 0.92
                ]
                if duplicates:
                    candidates = [i] + duplicates
                    best = max(candidates, key=lambda idx: len(articles[idx].get("content_snippet", "")))
                    kept_indices.add(best)
                else:
                    kept_indices.add(i)

            sorted_kept = sorted(kept_indices)
            articles = [articles[i] for i in sorted_kept]
            embeddings = embeddings[sorted_kept]

        if len(articles) < 2:
            return [[a] for a in articles]

        # 3. Extract latent topics from article text
        texts = [_build_text(a) for a in articles]
        n_topics = max(2, min(8, len(articles) // 5))
        topic_labels = _extract_topics(texts, n_topics=n_topics)

        # 4. Augment embeddings with topic features
        n_topics_actual = len(set(topic_labels))
        if n_topics_actual > 1:
            topic_onehot = np.zeros((len(articles), n_topics_actual))
            for i, label in enumerate(topic_labels):
                topic_onehot[i, label] = 1.0
            embeddings = np.concatenate([embeddings, topic_onehot * 0.3], axis=1)

        # 5. HDBSCAN clustering
        min_cluster_size = max(2, min(5, len(articles) // 10))
        clusterer = HDBSCAN(
            min_cluster_size=min_cluster_size,
            min_samples=1,
            metric="euclidean",
            cluster_selection_epsilon=CLUSTER_THRESHOLD,
            prediction_data=True,
        )
        labels = clusterer.fit_predict(embeddings)

        # 6. Build clusters
        clusters_dict: dict[int | str, list[dict]] = {}
        for i, label in enumerate(labels):
            if label == -1:
                cluster_key = f"noise_{i}"
                clusters_dict.setdefault(cluster_key, []).append(articles[i])
            else:
                clusters_dict.setdefault(label, []).append(articles[i])

        clusters = list(clusters_dict.values())
        noise_count = sum(1 for l in labels if l == -1)
        logger.info(
            f"HDBSCAN created {len(clusters)} clusters "
            f"(noise: {noise_count} articles out of {len(articles)})"
        )
        return clusters

    except Exception as e:
        logger.exception(f"Clustering failed: {e}")
        return [[a] for a in articles]
