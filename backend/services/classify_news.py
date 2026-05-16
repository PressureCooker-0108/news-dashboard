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
        "Financial markets and the economy. Stock market indices like the S&P 500 and Dow Jones, "
        "NASDAQ composite, bond yields and treasury rates, Federal Reserve Fed interest rate decisions "
        "rate hikes and rate cuts, central bank monetary policy, corporate earnings reports revenue profit loss, "
        "IPOs and mergers and acquisitions M&A, inflation and deflation and interest rate changes, "
        "recession warnings and GDP growth economic data, employment jobs data unemployment rate layoffs hiring, "
        "banking and financial services banking crisis, hedge funds and investment management strategies, "
        "currency exchange rates dollar euro pound yen forex, commodity prices gold silver copper, "
        "overall economic outlook business cycle, stock buybacks dividends, bull market bear market rally crash correction, "
        "trade war tariffs imports exports, consumer spending retail sales, housing market mortgage rates, "
        "cryptocurrency bitcoin ethereum crypto regulation, venture capital private equity, "
        "insurance banking sector earnings season, quarterly results profit warning."
    ),
    "Tech": (
        "Technology industry and innovation. Artificial intelligence AI machine learning deep learning, "
        "large language models LLM GPT OpenAI ChatGPT, software development apps mobile apps, "
        "cybersecurity threats data breaches hacking ransomware, cloud computing AWS Azure Google Cloud services, "
        "semiconductor chips chip shortage TSMC NVIDIA Intel AMD hardware manufacturing, "
        "consumer electronics smartphones iPhone Samsung Pixel laptops tablets, "
        "social media platforms Facebook Meta Twitter Instagram TikTok, "
        "search engines Google online advertising, startup funding venture capital Series A B C, "
        "Silicon Valley unicorn startup news big tech Apple Microsoft Amazon Meta Google, "
        "automation robotics autonomous self-driving cars, quantum computing breakthroughs, "
        "technology regulation antitrust policy, streaming Netflix Disney Spotify subscription, "
        "gaming video games console PlayStation Xbox Nintendo, augmented reality virtual reality AR VR metaverse, "
        "electric vehicles EV Tesla battery technology, biotech gene editing CRISPR."
    ),
    "Geopolitics": (
        "International relations and global politics. Military conflicts and wars war fighting combat, "
        "diplomatic negotiations peace treaties, international sanctions trade restrictions, "
        "NATO United Nations UN European Union EU, territorial disputes border conflicts, "
        "nuclear weapons missiles arms control, presidential summits foreign policy decisions, "
        "elections voting ballots in major countries, human rights issues refugee migrant migration crises, "
        "political alliances rivalries between nations, global security developments, "
        "Ukraine Russia war invasion, China Taiwan tensions, Middle East Israel Palestine Gaza, "
        "North Korea missile tests, Iran nuclear deal, Afghanistan Taliban, "
        "terrorism extremist groups ISIS Al Qaeda, cyber warfare election interference, "
        "government parliament congress senate legislation policy, protest riot coup revolution, "
        "defense military spending army navy air force drone strike, "
        "espionage intelligence CIA FBI MI5, diplomacy ambassador state visit, "
        "sovereignty independence referendum, political party conservative liberal democrat republican."
    ),
    "Energy": (
        "Energy sector and environmental policy. Crude oil prices and production, "
        "OPEC oil output cuts, natural gas markets LNG pipelines Nord Stream, "
        "renewable energy solar wind hydroelectric, "
        "nuclear power plant operations, electric vehicles EV battery technology, "
        "climate change global warming policy carbon emissions regulations net zero, "
        "fossil fuel coal oil exploration drilling, "
        "energy company earnings Exxon Chevron Shell BP investments, "
        "utility electric grid infrastructure, "
        "energy security supply chain disruptions, green technology innovation, "
        "Brent crude WTI oil price per barrel, gasoline diesel fuel prices, "
        "energy transition decarbonization, hydrogen fuel cells, "
        "offshore drilling deepwater, refinery petrochemical, "
        "OPEC+ Saudi Arabia Russia production quota, strategic petroleum reserve, "
        "environmental regulation EPA, carbon tax cap and trade, "
        "renewable energy credit solar panel wind turbine."
        "ESG sustainable investing green bonds."
    ),
    "India": (
        "Specifically Indian domestic news uniquely centered on India. Indian elections for BJP Congress parties "
        "state assembly elections, Prime Minister Narendra Modi and domestic policy schemes, "
        "Indian stock market indices Sensex Nifty, Rupee exchange rate US dollar INR, "
        "RBI Reserve Bank of India monetary policy interest rate, "
        "cities Mumbai Delhi Bangalore Bengaluru Chennai Kolkata Hyderabad Pune Ahmedabad, "
        "Indian business economy GDP growth, startups unicorns Indian startup ecosystem, "
        "IPL cricket Indian Premier League, Bollywood movies film industry, "
        "Indian festivals Diwali Holi Dussehra Eid, "
        "Indian infrastructure highways railways metro, Aadhaar digital ID UPI digital payment, "
        "Indian education IIT IIM universities, healthcare Ayushman Bharat, "
        "Indian agriculture farming MSP, Indian foreign policy relations, "
        "Supreme Court high court legal judgment, Indian armed forces army navy, "
        "GST tax reform, Make in India manufacturing, Digital India, "
        "Indian telecom Reliance Jio Airtel, Indian IT services TCS Infosys Wipro HCL."
    ),
    "General": (
        "General news that does not strongly fit into a specific specialized category. "
        "Human-interest stories, lifestyle and entertainment news, "
        "health medicine wellness topics, education schools universities colleges, "
        "sports football soccer basketball cricket Olympics games match player team, "
        "cultural events arts music movies film television shows, "
        "weather forecast storm hurricane tornado earthquake flood wildfire natural disaster, "
        "crime police investigation court trial judge prison, "
        "local community news, food recipes restaurants dining travel tourism, "
        "science research discovery space NASA astronomy, "
        "books publishing authors literature, fashion beauty trends, "
        "family parenting relationships marriage, pets animals wildlife conservation, "
        "obituary tribute memorial, opinion editorial commentary."
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

def _compute_sector_scores(combined_text: str) -> dict[str, float]:
    """
    Compute TF-IDF similarity scores for all sectors against the input text.

    Splits text into segments, computes cosine similarity for each segment
    against every sector description, and sums the scores per sector.
    Used to validate source-assigned sectors against actual article content.

    Returns:
        Dict mapping sector name to aggregate similarity score.
    """
    if not combined_text or not combined_text.strip():
        return {s: 0.0 for s in _sector_names}

    segments = _SEGMENT_RE.split(combined_text)
    segments = [s.strip() for s in segments if len(s.strip()) > 20]

    if not segments:
        segments = [combined_text[:500]]

    segment_vecs = _tfidf_vectorizer.transform(segments).toarray()
    sim_matrix = cosine_similarity(segment_vecs, _sector_tfidf)

    scores: dict[str, float] = {}
    for i, name in enumerate(_sector_names):
        scores[name] = float(sim_matrix[:, i].sum())

    return scores


def classify_sectors(combined_text: str, source_sectors: list[str] | None = None) -> list[str]:
    """
    Classify news text into 1-3 sectors.

    Uses a validated two-tier approach:
      1. **Source-assigned sectors** (from RSS feed config) — validated against
         TF-IDF content analysis. Only kept if the article text has meaningful
         similarity to the sector description. This prevents bogus assignments
         like a Mexican cartel article from Times of India being tagged as
         "India" just because of its source.
      2. **TF-IDF always runs** — provides content-based classification that
         complements validated source tags and catches missed sectors.

    The validation is global across all sectors (Markets, Tech, Geopolitics,
    Energy, India, General), not source-specific.

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

    # Always run TF-IDF — needed both as fallback and for source validation
    tfidf_sectors = _classify_with_tfidf(combined_text)
    if not tfidf_sectors:
        tfidf_sectors = ["General"]

    # If no source sectors, use TF-IDF directly
    if not source_sectors or len(source_sectors) == 0:
        _classification_cache[cache_key] = tfidf_sectors
        return tfidf_sectors

    # ── Source sectors exist — validate each against TF-IDF content scores ──
    # This is the key fix: source tags are a PROPOSAL, not an override.
    # We verify the article text actually relates to the source sector.

    sector_scores = _compute_sector_scores(combined_text)

    # Normalize scores so threshold is consistent across articles
    max_score = max(sector_scores.values())
    if max_score <= 0:
        normalized = {s: 0.0 for s in _sector_names}
    else:
        normalized = {s: v / max_score for s, v in sector_scores.items()}

    # Keep source sectors with meaningful TF-IDF similarity to the article
    # Threshold: at least 10% of the top sector's score
    MIN_RELATIVE_SCORE = 0.10
    validated_source = [
        s for s in source_sectors
        if normalized.get(s, 0) >= MIN_RELATIVE_SCORE
    ]

    # Combine: validated source sectors (high-confidence) + TF-IDF's picks
    combined = list(dict.fromkeys(validated_source + tfidf_sectors))

    # Cap at 3 sectors to keep it focused
    result = combined[:3]

    _classification_cache[cache_key] = result
    return result


# Keep backward compatibility — single-sector wrapper
def classify_sector(title: str) -> str:
    """Legacy single-sector classification. Returns first sector."""
    sectors = classify_sectors(title)
    return sectors[0] if sectors else "General"
