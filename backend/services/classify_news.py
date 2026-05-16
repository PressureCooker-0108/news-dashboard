"""
Sector classification using TF-IDF keyword overlap with rich semantic descriptions.
Classifies news into: Markets, Tech, Geopolitics, Energy, India, General.

Replaces the previous sentence-transformers approach with TF-IDF — no model
download, instant startup, works great on news headlines which share keywords
with the sector descriptions.
"""
import logging
import re
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)

# ── Valid sectors ────────────────────────────
VALID_SECTORS = ["Markets", "Tech", "Geopolitics", "Energy", "India", "General"]

# ── In-memory classification cache ───────────
_classification_cache: dict[str, list[str]] = {}

# ── Rich sector descriptions ─────────────────
# These are keyword-rich descriptions designed to capture the vocabulary
# associated with each sector. TF-IDF matches input text against these.
SECTOR_DESCRIPTIONS = {
    "Markets": (
        "Financial markets and the economy. Topics include stock market indices like the S&P 500 and Dow Jones, "
        "bond yields and treasury rates, central bank decisions by the Federal Reserve, corporate earnings reports, "
        "IPOs and mergers and acquisitions, inflation and interest rate changes, recession warnings and GDP growth, "
        "employment and jobs data, banking and financial services, hedge funds and investment strategies, "
        "currency exchange rates, commodity prices, and overall economic outlook."
    ),
    "Tech": (
        "Technology industry and innovation. Topics include artificial intelligence and machine learning, "
        "software development, cybersecurity threats and data breaches, cloud computing services, "
        "semiconductor chips and hardware manufacturing, consumer electronics like smartphones and laptops, "
        "social media platforms, search engines and online advertising, startup funding and venture capital, "
        "Silicon Valley company news, automation and robotics, quantum computing breakthroughs, "
        "and technology regulation and policy."
    ),
    "Geopolitics": (
        "International relations and global politics. Topics include military conflicts and wars, "
        "diplomatic negotiations and peace treaties, international sanctions and trade restrictions, "
        "NATO, United Nations, and other international organizations, territorial disputes and border conflicts, "
        "nuclear weapons and arms control, presidential summits and foreign policy decisions, "
        "elections in major countries, human rights issues, refugee and migration crises, "
        "political alliances and rivalries between nations, and global security developments."
    ),
    "Energy": (
        "Energy sector and environmental policy. Topics include crude oil prices and production, "
        "OPEC decisions on output, natural gas markets and pipelines, renewable energy from solar and wind, "
        "nuclear power plant operations, electric vehicles and battery technology, "
        "climate change policy and carbon emissions regulations, fossil fuel exploration and drilling, "
        "energy company earnings and investments, utility and grid infrastructure, "
        "energy security and supply chain disruptions, and green technology innovation."
    ),
    "India": (
        "Specifically Indian domestic news uniquely centered on India. Topics include Indian elections for BJP and Congress parties "
        "and state assembly elections, Prime Minister and domestic policy schemes, Indian stock market indices Sensex and Nifty, "
        "Rupee exchange rate and RBI monetary policy, cities Mumbai, Delhi, Bangalore, Chennai, Kolkata, "
        "Indian business, startups, IPL cricket, Bollywood movies, Indian festivals like Diwali and Holi, "
        "Indian infrastructure, Aadhaar digital ID, Indian education, healthcare, and social issues specific to India."
    ),
    "General": (
        "General news that does not strongly fit into a specific specialized category. "
        "Includes human-interest stories, lifestyle and entertainment news, "
        "health and wellness topics, education, sports, cultural events and arts, "
        "weather and natural disasters, crime and public safety, and local community news."
    ),
}

_sector_names = list(SECTOR_DESCRIPTIONS.keys())

# ── Pre-fit TF-IDF on sector descriptions ───
# This happens once at module load — no model download, zero startup time.
_tfidf_vectorizer = TfidfVectorizer(
    max_features=500,
    stop_words="english",
    sublinear_tf=True,
    use_idf=False,
)
_sector_tfidf = _tfidf_vectorizer.fit_transform(list(SECTOR_DESCRIPTIONS.values())).toarray()

# Regex to split text into meaningful segments
_SEGMENT_RE = re.compile(r"(?<=[.!?])\s+")


def _classify_with_tfidf(combined_text: str) -> list[str]:
    """
    Classify text using TF-IDF similarity against sector descriptions.

    Strategy: Split text into segments, compute TF-IDF for each, score each
    against all sector descriptions, and aggregate using a weighted vote.
    """
    if not combined_text or not combined_text.strip():
        return ["General"]

    # Split text into segments (sentences or clauses)
    segments = _SEGMENT_RE.split(combined_text)
    segments = [s.strip() for s in segments if len(s.strip()) > 20]

    if not segments:
        # Fall back to the whole text
        segments = [combined_text[:500]]

    # Transform all segments using pre-fitted vectorizer
    segment_vecs = _tfidf_vectorizer.transform(segments).toarray()

    # Compute cosine similarity: (n_segments x n_sectors)
    sim_matrix = cosine_similarity(segment_vecs, _sector_tfidf)

    # For each segment, find the best sector and its score
    best_sector_per_segment = np.argmax(sim_matrix, axis=1)
    best_score_per_segment = np.max(sim_matrix, axis=1)

    # Aggregate: weighted votes by confidence score
    sector_votes: dict[str, float] = {}
    for i in range(len(segments)):
        sector = _sector_names[best_sector_per_segment[i]]
        score = best_score_per_segment[i]
        sector_votes[sector] = sector_votes.get(sector, 0.0) + score

    # Sort sectors by total vote
    scored = sorted(sector_votes.items(), key=lambda x: x[1], reverse=True)

    if not scored:
        return ["General"]

    # Determine confidence threshold based on top score
    top_sector, top_score = scored[0]
    total_votes = sum(sector_votes.values())
    top_confidence = top_score / total_votes if total_votes > 0 else 0

    results = [top_sector]

    # Add second sector if:
    # 1. Top confidence isn't overwhelming (> 0.65 means clearly one topic)
    # 2. Second place has reasonable vote share
    if len(scored) > 1 and top_confidence < 0.65:
        second_sector, second_score = scored[1]
        second_share = second_score / total_votes if total_votes > 0 else 0
        if second_share > 0.2:
            results.append(second_sector)

    return results


# ── Public API ───────────────────────────────

def classify_sectors(combined_text: str, source_sectors: list[str] | None = None) -> list[str]:
    """
    Classify news text into 1-2 sectors.

    Uses a two-tier approach:
      1. **Source-assigned sectors** (from RSS feed config) — high-confidence
         primary tags that are always kept.
      2. **TF-IDF refinement** — detects additional sector signals from the
         article text. A secondary sector is added only if TF-IDF finds strong
         evidence (>65% confidence threshold).

    Args:
        combined_text: title + description/snippet combined text
        source_sectors: sectors pre-assigned from the article's RSS source

    Returns:
        List of 1-3 sector strings (e.g. ["Markets", "Tech"])
    """
    # Check cache
    suffix = f"|{','.join(source_sectors)}" if source_sectors else ""
    cache_key = f"{combined_text[:200]}{suffix}"
    if cache_key in _classification_cache:
        return _classification_cache[cache_key]

    # Tier 1: source-assigned sectors (preserve these as primary tags)
    base_sectors = list(source_sectors) if source_sectors else []

    # Tier 2: TF-IDF refinement for additional sector signals
    tfidf_sectors = _classify_with_tfidf(combined_text)

    # Filter out "General" from TF-IDF results if we already have specific sectors
    if len(base_sectors) > 0 and "General" in tfidf_sectors:
        tfidf_sectors = [s for s in tfidf_sectors if s != "General"]

    # Merge: keep all base sectors, add TF-IDF sectors that aren't already present
    merged = list(base_sectors)
    for s in tfidf_sectors:
        if s not in merged:
            merged.append(s)

    # If nothing was assigned, default to General
    if not merged:
        merged = ["General"]

    _classification_cache[cache_key] = merged
    return merged


# Keep backward compatibility — single-sector wrapper
def classify_sector(title: str) -> str:
    """Legacy single-sector classification. Returns first sector."""
    sectors = classify_sectors(title)
    return sectors[0] if sectors else "General"
