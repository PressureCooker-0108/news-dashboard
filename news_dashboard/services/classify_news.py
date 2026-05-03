"""
Sector classification using OpenAI LLM with embedding fallback.
Classifies news into: Markets, Tech, Geopolitics, Energy, India, General.
"""
import os
import json
import logging
from sentence_transformers import SentenceTransformer, util
import torch

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# Valid sectors
# ──────────────────────────────────────────────
VALID_SECTORS = ["Markets", "Tech", "Geopolitics", "Energy", "India"]

# ──────────────────────────────────────────────
# In-memory classification cache (title → sectors list)
# ──────────────────────────────────────────────
_classification_cache: dict[str, list[str]] = {}

# ──────────────────────────────────────────────
# Embedding fallback setup (lazy-loaded)
# ──────────────────────────────────────────────
SECTOR_DESCRIPTIONS = {
    "Markets": "stock market crash, Wall Street, S&P 500, Dow Jones, NASDAQ, bond yields, inflation rate, Federal Reserve interest rates, corporate earnings, IPO, bankruptcy, airline collapse, recession, GDP growth, hedge fund, investment banking, financial crisis",
    "Tech": "artificial intelligence, machine learning, ChatGPT, semiconductor chip, software engineering, cybersecurity hack, cloud computing AWS, Apple iPhone, Google search, Meta Facebook, startup funding, Silicon Valley, robotics automation, quantum computing",
    "Geopolitics": "war military attack, diplomatic negotiations, NATO alliance, United Nations resolution, sanctions embargo, territorial dispute, nuclear weapons, peace talks ceasefire, president prime minister summit, foreign policy, invasion troops, Middle East conflict Iran Israel",
    "Energy": "crude oil price barrel, OPEC production cut, natural gas pipeline, solar wind renewable, nuclear power plant, carbon emissions climate, oil tanker shipping, refinery fuel costs, energy crisis shortage, electric vehicle battery",
    "India": "India Modi BJP Congress, Rupee RBI Sensex Nifty BSE NSE, Mumbai Delhi Kolkata Chennai, Indian election Lok Sabha, IPL cricket BCCI, Aadhaar GST, state assembly election India, Indian government ministry",


_embed_model = None
_sector_embeddings = None

def _get_embed_model():
    global _embed_model, _sector_embeddings
    if _embed_model is None:
        _embed_model = SentenceTransformer("all-MiniLM-L6-v2")
        _sector_embeddings = _embed_model.encode(
            list(SECTOR_DESCRIPTIONS.values()), convert_to_tensor=True
        )
    return _embed_model, _sector_embeddings


# ──────────────────────────────────────────────
# OpenAI LLM classification
# ──────────────────────────────────────────────
def _classify_with_llm(combined_text: str) -> list[str] | None:
    """Call OpenAI to classify the news text into 1-2 sectors.
    Returns a list of sectors or None on failure."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.warning("OPENAI_API_KEY not set — skipping LLM classification")
        return None

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)

        prompt = f"""Classify the following news into the most relevant sectors.

Sectors:
- Markets (financial markets, stocks, bonds, economy, inflation, central banks)
- Tech (technology, AI, software, startups, semiconductors)
- Geopolitics (government, elections, war, diplomacy, international relations, military)
- Energy (oil, gas, renewable energy, power, climate policy)
- India (Indian economy, Indian politics, Indian companies, domestic Indian news)

Rules:
- Return 1 or 2 most relevant sectors ONLY
- Use the MEANING of the text, not just keywords
- If the news doesn't clearly fit any sector, return ["General"]
- A story about India's tech industry should be ["Tech", "India"]
- A story about oil prices affecting markets should be ["Energy", "Markets"]

News:
{combined_text[:500]}

Return ONLY valid JSON:
{{"sectors": ["Sector1"]}}"""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=60,
        )

        content = response.choices[0].message.content.strip()
        # Parse JSON from response
        # Handle potential markdown code blocks
        if content.startswith("```"):
            content = content.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        
        parsed = json.loads(content)
        sectors = parsed.get("sectors", [])

        # Validate sectors
        validated = [s for s in sectors if s in VALID_SECTORS]
        if validated:
            return validated
        return ["General"]

    except Exception as e:
        logger.warning("LLM classification failed: %s", e)
        return None


# ──────────────────────────────────────────────
# Embedding fallback classification
# ──────────────────────────────────────────────
def _classify_with_embeddings(combined_text: str) -> list[str]:
    """Fallback: classify using cosine similarity against sector descriptions.
    Returns top 1-2 sectors. Always assigns the best match rather than defaulting to General."""
    model, sector_embs = _get_embed_model()
    sector_names = list(SECTOR_DESCRIPTIONS.keys())

    # Truncate to titles-length text for better embedding similarity
    truncated = combined_text[:300]
    text_embedding = model.encode(truncated, convert_to_tensor=True)
    scores = util.cos_sim(text_embedding, sector_embs)[0]

    # Sort sectors by score
    scored = [(sector_names[i], scores[i].item()) for i in range(len(sector_names))]
    scored.sort(key=lambda x: x[1], reverse=True)

    # Always pick the top sector; add second if it's close (within 0.05)
    results = [scored[0][0]]
    if len(scored) > 1 and (scored[1][1] >= 0.25 and scored[0][1] - scored[1][1] < 0.05):
        results.append(scored[1][0])

    return results


# ──────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────
def classify_sectors(combined_text: str) -> list[str]:
    """Classify news text into 1-2 sectors.
    Uses LLM first, falls back to embeddings, caches results.
    
    Args:
        combined_text: title + description/snippet combined text
    
    Returns:
        List of 1-2 sector strings (e.g. ["Tech", "Markets"])
    """
    # Check cache
    cache_key = combined_text[:200]  # Truncate for cache key
    if cache_key in _classification_cache:
        return _classification_cache[cache_key]

    # Try LLM first
    sectors = _classify_with_llm(combined_text)

    # Fallback to embeddings if LLM fails
    if sectors is None:
        sectors = _classify_with_embeddings(combined_text)

    # Cache and return
    _classification_cache[cache_key] = sectors
    return sectors


# Keep backward compatibility — single-sector wrapper
def classify_sector(title: str) -> str:
    """Legacy single-sector classification. Returns first sector."""
    sectors = classify_sectors(title)
    return sectors[0] if sectors else "General"
