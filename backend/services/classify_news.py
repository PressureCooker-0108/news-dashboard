"""
Sector classification using embedding similarity with rich semantic descriptions.
Classifies news into: Markets, Tech, Geopolitics, Energy, India, General.
"""
import logging
import re
import numpy as np
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# Valid sectors
# ──────────────────────────────────────────────
VALID_SECTORS = ["Markets", "Tech", "Geopolitics", "Energy", "India", "General"]

# ──────────────────────────────────────────────
# In-memory classification cache (title → sectors list)
# ──────────────────────────────────────────────
_classification_cache: dict[str, list[str]] = {}

# ──────────────────────────────────────────────
# Rich semantic sector descriptions (instead of keyword lists)
# These work far better with sentence transformers because they describe
# the *concept* of each sector in natural language.
# ──────────────────────────────────────────────
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

_embed_model = None
_sector_embeddings = None
_sector_names = list(SECTOR_DESCRIPTIONS.keys())

# Regex to split text into meaningful segments
_SEGMENT_RE = re.compile(r"(?<=[.!?])\s+")

def _get_embed_model():
    """Lazy-load the embedding model and pre-compute sector embeddings."""
    global _embed_model, _sector_embeddings
    if _embed_model is None:
        _embed_model = SentenceTransformer("all-MiniLM-L6-v2")
        _sector_embeddings = _embed_model.encode(
            list(SECTOR_DESCRIPTIONS.values()), convert_to_tensor=False
        )
        # Normalize for cosine similarity via dot product
        _sector_embeddings = _sector_embeddings / np.linalg.norm(
            _sector_embeddings, axis=1, keepdims=True
        )
    return _embed_model, _sector_embeddings


def _classify_with_embeddings(combined_text: str) -> list[str]:
    """
    Classify text using multi-granularity embedding similarity.
    
    Strategy: Instead of encoding the whole text at once (which dilutes signal),
    encode individual sentences/segments, score each against all sectors,
    and aggregate using a weighted vote. This captures topical signals that
    might be buried in longer text.
    """
    model, sector_embs = _get_embed_model()

    if not combined_text or not combined_text.strip():
        return ["General"]

    # Split text into segments (sentences or clauses)
    segments = _SEGMENT_RE.split(combined_text)
    segments = [s.strip() for s in segments if len(s.strip()) > 20]

    if not segments:
        # Fall back to encoding the whole text
        segments = [combined_text[:500]]

    # Encode all segments
    segment_embs = model.encode(segments, show_progress_bar=False, convert_to_tensor=False)
    segment_embs = segment_embs / np.linalg.norm(segment_embs, axis=1, keepdims=True)

    # Compute similarity matrix: (n_segments x n_sectors)
    sim_matrix = segment_embs @ sector_embs.T  # dot product since normalized

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
    # 1. Top confidence isn't overwhelming (> 0.65 means it's clearly one topic)
    # 2. Second place has reasonable vote share
    if len(scored) > 1 and top_confidence < 0.65:
        second_sector, second_score = scored[1]
        second_share = second_score / total_votes if total_votes > 0 else 0
        if second_share > 0.2:
            results.append(second_sector)

    return results


# ──────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────
def classify_sectors(combined_text: str) -> list[str]:
    """
    Classify news text into 1-2 sectors using embedding-based semantic matching.
    Uses rich semantic sector descriptions for superior accuracy over keyword lists.
    
    Args:
        combined_text: title + description/snippet combined text
    
    Returns:
        List of 1-2 sector strings (e.g. ["Tech", "Markets"])
    """
    # Check cache
    cache_key = combined_text[:200]
    if cache_key in _classification_cache:
        return _classification_cache[cache_key]

    sectors = _classify_with_embeddings(combined_text)

    # Filter out "General" unless it's the only sector
    if len(sectors) > 1 and "General" in sectors:
        sectors = [s for s in sectors if s != "General"]

    _classification_cache[cache_key] = sectors
    return sectors


# Keep backward compatibility — single-sector wrapper
def classify_sector(title: str) -> str:
    """Legacy single-sector classification. Returns first sector."""
    sectors = classify_sectors(title)
    return sectors[0] if sectors else "General"
