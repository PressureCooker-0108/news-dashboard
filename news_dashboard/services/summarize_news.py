import logging
import re
import numpy as np
from sentence_transformers import SentenceTransformer
from ..config import TOPIC_TEMPLATES

logger = logging.getLogger(__name__)

_model = None

def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model

def _pick_headline(cluster: list[dict]) -> tuple[str, str]:
    """Pick title closest to centroid."""
    if len(cluster) == 1:
        return cluster[0]["title"], cluster[0]["url"]
    try:
        model = _get_model()
        titles = [a["title"] for a in cluster]
        embeddings = model.encode(titles, show_progress_bar=False)
        centroid = np.mean(embeddings, axis=0)
        sims = embeddings @ centroid / (np.linalg.norm(embeddings, axis=1) * np.linalg.norm(centroid) + 1e-9)
        best_idx = int(np.argmax(sims))
        return titles[best_idx], cluster[best_idx]["url"]
    except Exception:
        return cluster[0]["title"], cluster[0]["url"]

_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")

def _make_summary(cluster: list[dict]) -> str:
    """Concatenate snippets and truncate."""
    snippets = [a.get("content_snippet", "") for a in cluster if a.get("content_snippet")]
    if not snippets:
        return "Details are still emerging."
    combined = " ".join(snippets[:2]).strip()
    sentences = _SENTENCE_RE.split(combined)
    summary = ". ".join(s.strip() for s in sentences[:2] if s.strip())
    if summary and not summary.endswith("."):
        summary += "."
    return summary or "Details are still emerging."

def _why_it_matters(cluster: list[dict]) -> str:
    """Keyword based matching."""
    combined_titles = " ".join(a["title"] for a in cluster).lower()
    for keyword, template in TOPIC_TEMPLATES.items():
        if keyword == "default":
            continue
        if re.search(r"\b" + re.escape(keyword) + r"\b", combined_titles):
            return template
    return TOPIC_TEMPLATES["default"]

def summarize_stories(ranked_stories: list[dict]) -> list[dict]:
    """Enrich stories with headlines/summaries."""
    results: list[dict] = []
    for story in ranked_stories:
        cluster = story["cluster"]
        title, url = _pick_headline(cluster)
        summary = _make_summary(cluster)
        why = _why_it_matters(cluster)

        results.append({
            "title": title,
            "summary": summary,
            "why_it_matters": why,
            "url": url,
            "score": story["score"],
            "article_count": story["article_count"],
            "source": story["sources"],
            "published_at": story["latest_at"],
            "latest_at": story["latest_at"],
            "sectors": story.get("sectors", ["General"])
        })
    return results

