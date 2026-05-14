import logging
import yfinance as yf
from datetime import datetime, timezone
from models.database import save_market_data, get_market_data

logger = logging.getLogger(__name__)

# Key tickers to track by sector
WATCHLIST = [
    # Major Indices
    {"ticker": "^GSPC", "name": "S&P 500", "sector": "Index"},
    {"ticker": "^DJI", "name": "Dow Jones", "sector": "Index"},
    {"ticker": "^IXIC", "name": "NASDAQ", "sector": "Index"},
    {"ticker": "^RUT", "name": "Russell 2000", "sector": "Index"},
    {"ticker": "^VIX", "name": "VIX Volatility", "sector": "Index"},
    # Tech
    {"ticker": "AAPL", "name": "Apple", "sector": "Tech"},
    {"ticker": "MSFT", "name": "Microsoft", "sector": "Tech"},
    {"ticker": "GOOGL", "name": "Alphabet", "sector": "Tech"},
    # AMZN listed under Consumer below
    {"ticker": "NVDA", "name": "NVIDIA", "sector": "Tech"},
    {"ticker": "META", "name": "Meta", "sector": "Tech"},
    {"ticker": "TSLA", "name": "Tesla", "sector": "Tech"},
    {"ticker": "AVGO", "name": "Broadcom", "sector": "Tech"},
    # Markets / Finance
    {"ticker": "JPM", "name": "JPMorgan Chase", "sector": "Finance"},
    {"ticker": "GS", "name": "Goldman Sachs", "sector": "Finance"},
    {"ticker": "V", "name": "Visa", "sector": "Finance"},
    {"ticker": "MA", "name": "Mastercard", "sector": "Finance"},
    {"ticker": "BAC", "name": "Bank of America", "sector": "Finance"},
    {"ticker": "BRK-B", "name": "Berkshire Hathaway", "sector": "Finance"},
    # Energy
    {"ticker": "XOM", "name": "Exxon Mobil", "sector": "Energy"},
    {"ticker": "CVX", "name": "Chevron", "sector": "Energy"},
    {"ticker": "COP", "name": "ConocoPhillips", "sector": "Energy"},
    {"ticker": "SLB", "name": "Schlumberger", "sector": "Energy"},
    # Healthcare
    {"ticker": "UNH", "name": "UnitedHealth", "sector": "Healthcare"},
    {"ticker": "JNJ", "name": "Johnson & Johnson", "sector": "Healthcare"},
    {"ticker": "PFE", "name": "Pfizer", "sector": "Healthcare"},
    {"ticker": "LLY", "name": "Eli Lilly", "sector": "Healthcare"},
    # Consumer
    {"ticker": "WMT", "name": "Walmart", "sector": "Consumer"},
    {"ticker": "AMZN", "name": "Amazon", "sector": "Consumer/ Tech"},
    {"ticker": "HD", "name": "Home Depot", "sector": "Consumer"},
    {"ticker": "MCD", "name": "McDonald's", "sector": "Consumer"},
    {"ticker": "NKE", "name": "Nike", "sector": "Consumer"},
    # India / Emerging Markets
    {"ticker": "^BSESN", "name": "BSE Sensex", "sector": "India"},
    {"ticker": "^NSEI", "name": "Nifty 50", "sector": "India"},
    {"ticker": "EEM", "name": "iShares MSCI Emerging Markets", "sector": "Markets"},
]


def fetch_and_store_market_data() -> list[dict]:
    """Fetch stock prices for all watchlist tickers and store in DB."""
    results = []
    errors = []

    for item in WATCHLIST:
        try:
            ticker = yf.Ticker(item["ticker"])
            info = ticker.info if ticker.info else {}

            price = info.get("regularMarketPrice") or info.get("currentPrice") or info.get("previousClose") or 0
            prev_close = info.get("regularMarketPreviousClose") or info.get("previousClose") or price

            if price and prev_close and prev_close > 0:
                change = round(price - prev_close, 2)
                change_pct = round((change / prev_close) * 100, 2)
            else:
                # Fallback to fast_info
                try:
                    fast = ticker.fast_info
                    price = fast.get("lastPrice", 0)
                    prev_close = fast.get("previousClose", 0) or price
                    change = round(price - prev_close, 2)
                    change_pct = round((change / prev_close) * 100, 2) if prev_close > 0 else 0
                except Exception:
                    continue

            market_cap = info.get("marketCap")
            if market_cap:
                if market_cap >= 1e12:
                    cap_str = f"${market_cap/1e12:.2f}T"
                elif market_cap >= 1e9:
                    cap_str = f"${market_cap/1e9:.2f}B"
                elif market_cap >= 1e6:
                    cap_str = f"${market_cap/1e6:.2f}M"
                else:
                    cap_str = f"${market_cap:,.0f}"
            else:
                cap_str = None

            results.append({
                "ticker": item["ticker"],
                "name": item["name"],
                "price": round(price, 2) if price else 0,
                "change": change,
                "change_pct": change_pct,
                "market_cap": cap_str,
                "sector": item["sector"],
            })

        except Exception as e:
            errors.append(f"{item['ticker']}: {e}")
            continue

    # Store in database
    if results:
        try:
            save_market_data(results)
        except Exception as e:
            logger.error(f"Failed to save market data: {e}")

    if errors:
        logger.warning(f"Market data fetch errors ({len(errors)}): {errors[:3]}...")

    logger.info(f"Fetched market data: {len(results)} tickers")
    return results


def get_big_market_movers(threshold: float = 1.5) -> dict:
    """Get significant market movers (stocks with > threshold% change)."""
    data = get_market_data()

    gainers = [d for d in data if d["change_pct"] >= threshold and d["sector"] != "Index"]
    losers = [d for d in data if d["change_pct"] <= -threshold and d["sector"] != "Index"]

    indices = [d for d in data if d["sector"] == "Index"]

    return {
        "gainers": sorted(gainers, key=lambda x: -x["change_pct"])[:10],
        "losers": sorted(losers, key=lambda x: x["change_pct"])[:10],
        "indices": sorted(indices, key=lambda x: -abs(x.get("change_pct", 0)))[:5],
        "all": data,
    }
