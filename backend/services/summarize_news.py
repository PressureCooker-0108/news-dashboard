import logging
import re
import numpy as np
from sentence_transformers import SentenceTransformer
from config import TOPIC_TEMPLATES

logger = logging.getLogger(__name__)

_model = None

def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def _pick_headline(cluster: list[dict]) -> tuple[str, str]:
    """
    Pick the best headline from a cluster.
    Uses centroid-based selection: finds the title closest to the semantic centroid.
    Also prefers titles that are informative (longer, more substantive) as a tiebreaker.
    """
    if len(cluster) == 1:
        return cluster[0]["title"], cluster[0]["url"]
    try:
        model = _get_model()
        titles = [a["title"] for a in cluster]
        embeddings = model.encode(titles, show_progress_bar=False)
        centroid = np.mean(embeddings, axis=0)
        centroid_norm = np.linalg.norm(centroid) + 1e-9
        emb_norms = np.linalg.norm(embeddings, axis=1)
        sims = (embeddings @ centroid) / (emb_norms * centroid_norm)

        # Prefer more informative titles (longer, more substantive) when similarity is close
        # Weight: 80% similarity, 20% title informativeness (length normalized)
        title_lengths = np.array([max(len(t.split()), 3) for t in titles])
        max_len = title_lengths.max()
        length_scores = title_lengths / max_len if max_len > 0 else np.ones_like(title_lengths)

        combined_scores = 0.8 * sims + 0.2 * length_scores
        best_idx = int(np.argmax(combined_scores))
        return titles[best_idx], cluster[best_idx]["url"]
    except Exception:
        return cluster[0]["title"], cluster[0]["url"]


_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")

# ──────────────────────────────────────────────
# Enriched topic descriptions for "Why It Matters"
# These are rich semantic descriptions that work well with sentence transformers
# for matching story content to the most relevant context template.
# ──────────────────────────────────────────────
_TOPIC_EMBEDDINGS = {
    "election": (
        "Elections, political campaigns, voting, and transitions of power. "
        "Changes in government leadership that affect policy direction, "
        "market sentiment, and international relations."
    ),
    "war": (
        "Armed conflicts, military operations, wars, and invasions. "
        "Geopolitical instability that disrupts global supply chains, "
        "affects energy prices, and creates humanitarian crises."
    ),
    "economy": (
        "Economic indicators, GDP growth, inflation, unemployment, "
        "recessions, and fiscal policy. Broad economic shifts that "
        "impact business investment, consumer spending, and markets."
    ),
    "fed": (
        "Central bank policy, Federal Reserve decisions, interest rate "
        "changes, and monetary policy directly influencing borrowing costs "
        "and capital flows."
    ),
    "rate": (
        "Interest rate decisions by central banks, bond yields, "
        "and borrowing costs. Rate changes ripple through mortgages, "
        "business loans, corporate financing, and currency markets."
    ),
    "ai": (
        "Artificial intelligence, machine learning, automation, and "
        "advanced computing. AI breakthroughs are reshaping industries, "
        "labor markets, productivity, and competitive dynamics worldwide."
    ),
    "climate": (
        "Climate change, extreme weather events, environmental policy, "
        "and natural disasters. Climate developments affect agriculture, "
        "insurance, infrastructure, energy policy, and supply chains."
    ),
    "market": (
        "Stock market movements, trading, investor sentiment, and "
        "market volatility. Market movements reflect investor confidence "
        "and can signal broader economic trends and risks."
    ),
    "health": (
        "Public health crises, disease outbreaks, healthcare policy, "
        "and medical breakthroughs. Health issues affect workforce "
        "productivity, government spending, and global supply chains."
    ),
    "trade": (
        "International trade, tariffs, trade wars, and trade agreements. "
        "Trade policy changes directly affect prices, employment, "
        "manufacturing, and international relations."
    ),
}


def _make_summary(cluster: list[dict]) -> str:
    """
    Extractive summarization using embeddings.
    
    Collects all snippets from the cluster, splits them into sentences,
    embeds each sentence, and selects the most information-rich and
    representative sentences (closest to the semantic centroid).
    This produces a coherent multi-sentence summary that captures the
    key angles of the story.
    """
    snippets = [a.get("content_snippet", "") for a in cluster if a.get("content_snippet")]
    if not snippets:
        return "Details are still emerging."

    # Extract all sentences from all snippets
    all_sentences = []
    for snippet in snippets:
        snippet_sentences = _SENTENCE_RE.split(snippet)
        for s in snippet_sentences:
            s = s.strip()
            # Filter out very short fragments and boilerplate
            if len(s) > 30 and not s.startswith("<") and len(s.split()) >= 4:
                all_sentences.append(s)

    if not all_sentences:
        # Fallback: just use the first snippet as-is
        combined = snippets[0].strip()
        sentences = _SENTENCE_RE.split(combined)
        summary = ". ".join(s.strip() for s in sentences[:2] if s.strip())
        if summary and not summary.endswith("."):
            summary += "."
        return summary or "Details are still emerging."

    # Deduplicate near-identical sentences
    unique_sentences = []
    seen = set()
    for s in all_sentences:
        key = s.lower()[:60]
        if key not in seen:
            seen.add(key)
            unique_sentences.append(s)

    if len(unique_sentences) <= 2:
        return " ".join(unique_sentences) + ("." if not unique_sentences[-1].endswith(".") else "")

    try:
        model = _get_model()
        sent_embs = model.encode(unique_sentences, show_progress_bar=False)

        # Normalize for cosine similarity
        norms = np.linalg.norm(sent_embs, axis=1, keepdims=True) + 1e-9
        sent_embs = sent_embs / norms

        # Centroid: the "average" meaning of all sentences
        centroid = np.mean(sent_embs, axis=0)
        centroid_norm = np.linalg.norm(centroid) + 1e-9
        centroid = centroid / centroid_norm

        # Score each sentence: similarity to centroid
        # Higher = more representative of the cluster's overall content
        sims = sent_embs @ centroid

        # Also score by informativeness (prefer sentences with named entities, numbers, etc.)
        inform_scores = []
        for s in unique_sentences:
            # Count uppercase words (likely proper nouns), numbers, and longer words
            upper_words = sum(1 for w in s.split() if w[0].isupper() if len(w) > 1)
            has_numbers = bool(re.search(r"\d+", s))
            word_count = len(s.split())
            score = word_count / 30.0 + upper_words / 5.0 + (0.5 if has_numbers else 0)
            inform_scores.append(min(score, 2.0))
        inform_scores = np.array(inform_scores)

        # Combined: 70% representativeness + 30% informativeness
        combined_scores = 0.7 * sims + 0.3 * (inform_scores / inform_scores.max() if inform_scores.max() > 0 else 0)

        # Pick top 3 sentences, ensuring some diversity
        ranked_indices = np.argsort(-combined_scores)

        selected = []
        for idx in ranked_indices:
            if len(selected) >= 3:
                break
            # Avoid selecting very similar sentences to the ones already picked
            if selected:
                selected_emb = sent_embs[idx]
                too_similar = False
                for sel_idx in selected:
                    if float(selected_emb @ sent_embs[sel_idx]) > 0.85:
                        too_similar = True
                        break
                if not too_similar:
                    selected.append(int(idx))
            else:
                selected.append(int(idx))

        # Assemble the summary in original order (for coherence)
        selected.sort()
        selected_sentences = [unique_sentences[i] for i in selected]

        summary = " ".join(selected_sentences)
        if not summary.endswith("."):
            summary += "."
        return summary

    except Exception:
        logger.exception("Extractive summarization failed, falling back")
        combined = " ".join(snippets[:2]).strip()
        sentences = _SENTENCE_RE.split(combined)
        summary = ". ".join(s.strip() for s in sentences[:2] if s.strip())
        if summary and not summary.endswith("."):
            summary += "."
        return summary or "Details are still emerging."


def _why_it_matters(cluster: list[dict]) -> str:
    """
    Determine why a story matters using embedding-based topic matching.
    
    Instead of naive regex keyword matching, this approach embeds the
    cluster's text and compares against enriched topic descriptions
    to find the most relevant context.
    """
    combined_text = " ".join(
        a["title"] + ". " + a.get("content_snippet", "")[:200]
        for a in cluster[:5]
    )

    try:
        model = _get_model()
        # Encode the combined text
        text_emb = model.encode([combined_text[:500]], show_progress_bar=False)[0]

        # Encode topic descriptions
        topic_names = list(_TOPIC_EMBEDDINGS.keys())
        topic_embs = model.encode(
            [_TOPIC_EMBEDDINGS[t] for t in topic_names],
            show_progress_bar=False,
        )

        # Normalize
        text_emb = text_emb / (np.linalg.norm(text_emb) + 1e-9)
        topic_embs = topic_embs / (np.linalg.norm(topic_embs, axis=1, keepdims=True) + 1e-9)

        # Compute similarities
        sims = topic_embs @ text_emb

        best_idx = int(np.argmax(sims))
        best_topic = topic_names[best_idx]
        best_score = float(sims[best_idx])

        # Only use topic if similarity is above threshold
        if best_score > 0.3:
            return TOPIC_TEMPLATES.get(best_topic, TOPIC_TEMPLATES["default"])

        return TOPIC_TEMPLATES["default"]
    except Exception:
        # Fallback to keyword-based matching
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

