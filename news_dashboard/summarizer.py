"""
Deterministic, local summariser — no LLM required.
Generates headline, summary, and why_it_matters for each ranked story.
"""

import logging
import re

import numpy as np
from sentence_transformers import SentenceTransformer

from .config import TOPIC_TEMPLATES

logger = logging.getLogger(__name__)

# Reuse the same model singleton from clusterer
_model = None


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


# ──────────────────────────────────────────────
# Headline: most representative title
# ──────────────────────────────────────────────
def _pick_headline(cluster: list[dict]) -> str:
    """
    Choose the title whose embedding is closest to the cluster centroid.
    Falls back to the first title if embedding fails.
    """
    if len(cluster) == 1:
        return cluster[0]["title"]

    try:
        model = _get_model()
        titles = [a["title"] for a in cluster]
        embeddings = model.encode(titles, show_progress_bar=False)
        centroid = np.mean(embeddings, axis=0)
        # Cosine similarity to centroid
        sims = embeddings @ centroid / (
            np.linalg.norm(embeddings, axis=1) * np.linalg.norm(centroid) + 1e-9
        )
        best_idx = int(np.argmax(sims))
        return titles[best_idx]
    except Exception:
        logger.warning("Headline selection via embeddings failed; using first title")
        return cluster[0]["title"]


# ──────────────────────────────────────────────
# Summary: first 2 sentences from top snippets
# ──────────────────────────────────────────────
_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")


def _make_summary(cluster: list[dict]) -> str:
    """
    Concatenate the top-2 article snippets and truncate to 2 sentences.
    """
    snippets = [a.get("content_snippet", "") for a in cluster if a.get("content_snippet")]
    if not snippets:
        return "No summary available."

    combined = " ".join(snippets[:2]).strip()
    sentences = _SENTENCE_RE.split(combined)
    summary = ". ".join(s.strip() for s in sentences[:2] if s.strip())
    if summary and not summary.endswith("."):
        summary += "."
    return summary or "No summary available."


# ──────────────────────────────────────────────
# Why-it-matters: keyword → template
# ──────────────────────────────────────────────
def _why_it_matters(cluster: list[dict]) -> str:
    """
    Scan cluster headlines for the first matching keyword
    and return the corresponding template string.
    """
    combined_titles = " ".join(a["title"] for a in cluster).lower()
    for keyword, template in TOPIC_TEMPLATES.items():
        if keyword == "default":
            continue
        # Use word boundaries to avoid false positives (e.g. "ai" in "airlines")
        if re.search(r"\b" + re.escape(keyword) + r"\b", combined_titles):
            return template
    return TOPIC_TEMPLATES["default"]


# ──────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────
def summarize_stories(ranked_stories: list[dict]) -> list[dict]:
    """
    Enrich each ranked story dict with headline, summary, and why_it_matters.
    `ranked_stories` comes from ranker.rank_clusters().
    """
    results: list[dict] = []
    for story in ranked_stories:
        cluster = story["cluster"]
        headline = _pick_headline(cluster)
        summary = _make_summary(cluster)
        why = _why_it_matters(cluster)

        results.append(
            {
                "headline": headline,
                "summary": summary,
                "why_it_matters": why,
                "score": story["score"],
                "article_count": story["article_count"],
                "sources": story["sources"],
                "latest_at": story["latest_at"],
            }
        )

    logger.info("Summarised %d stories", len(results))
    return results
