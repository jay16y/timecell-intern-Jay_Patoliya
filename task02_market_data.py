"""
Task 02 — Live Market Data Fetcher
Timecell.AI Summer Internship 2025

Fetches real-time prices for crypto, stocks, and commodities
from free public APIs (CoinGecko + yfinance). Handles API failures
gracefully — logs errors and continues with remaining assets.

AI Tools Used: Claude (API endpoint selection, error-handling patterns)
"""

import requests
import yfinance as yf
from datetime import datetime, timezone, timedelta
import logging

# ── Logging setup ────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="  %(levelname)s │ %(message)s"
)
log = logging.getLogger(__name__)

# IST timezone (UTC+5:30)
IST = timezone(timedelta(hours=5, minutes=30))


# ── Fetchers ─────────────────────────────────────────────

def fetch_crypto_price(symbol):
    """
    Fetch crypto price from CoinGecko free API.

    CoinGecko uses full names as IDs (bitcoin, ethereum, etc.)
    Endpoint: /api/v3/simple/price?ids=bitcoin&vs_currencies=usd
    """
    # Map common ticker symbols to CoinGecko IDs
    coingecko_ids = {
        "BTC": "bitcoin",
        "ETH": "ethereum",
        "SOL": "solana",
        "DOGE": "dogecoin",
    }

    coin_id = coingecko_ids.get(symbol.upper())
    if not coin_id:
        raise ValueError(f"Unknown crypto symbol: {symbol}")

    url = "https://api.coingecko.com/api/v3/simple/price"
    params = {"ids": coin_id, "vs_currencies": "usd"}

    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()

    data = response.json()
    price = data[coin_id]["usd"]

    return {"name": symbol.upper(), "price": price, "currency": "USD", "status": "✓"}


def fetch_stock_price(symbol, display_name=None):
    """
    Fetch stock/index price using yfinance.

    Common tickers:
      NIFTY50 → ^NSEI    Sensex → ^BSESN
      Reliance → RELIANCE.NS   TCS → TCS.NS
    """
    ticker = yf.Ticker(symbol)
    hist = ticker.history(period="1d")

    if hist.empty:
        raise ValueError(f"No data returned for {symbol}")

    price = round(float(hist["Close"].iloc[-1]), 2)
    name = display_name or symbol

    # INR for Indian markets, USD otherwise
    currency = "INR" if symbol.endswith(".NS") or symbol.startswith("^NS") or symbol.startswith("^BS") else "USD"

    return {"name": name, "price": price, "currency": currency, "status": "✓"}


def fetch_commodity_price(symbol, display_name=None):
    """
    Fetch commodity price using yfinance.

    Common tickers:
      Gold futures → GC=F (USD/oz)
      Silver → SI=F    Crude Oil → CL=F
    """
    ticker = yf.Ticker(symbol)
    hist = ticker.history(period="1d")

    if hist.empty:
        raise ValueError(f"No data returned for {symbol}")

    price = round(float(hist["Close"].iloc[-1]), 2)
    name = display_name or symbol

    return {"name": name, "price": price, "currency": "USD/oz", "status": "✓"}


# ── Main Fetch Logic (with error handling) ───────────────

def fetch_all_prices(assets):
    """
    Fetch prices for a list of assets. If any single fetch fails,
    log the error and continue — never crash the whole pipeline.

    Args:
        assets: list of dicts with keys: symbol, type, name
               type must be one of: 'crypto', 'stock', 'commodity'

    Returns:
        list of result dicts with: name, price, currency, status
    """
    # Route each asset type to its fetcher
    fetchers = {
        "crypto":    lambda a: fetch_crypto_price(a["symbol"]),
        "stock":     lambda a: fetch_stock_price(a["symbol"], a.get("name")),
        "commodity": lambda a: fetch_commodity_price(a["symbol"], a.get("name")),
    }

    results = []

    for asset in assets:
        try:
            fetcher = fetchers.get(asset["type"])
            if not fetcher:
                raise ValueError(f"Unknown asset type: {asset['type']}")

            log.info(f"Fetching {asset['name']} ({asset['symbol']})...")
            result = fetcher(asset)
            results.append(result)
            log.info(f"  → {result['name']}: {result['price']:,.2f} {result['currency']}")

        except Exception as e:
            # Log the error but DON'T crash — continue with other assets
            log.error(f"Failed to fetch {asset['name']}: {e}")
            results.append({
                "name": asset.get("name", asset["symbol"]),
                "price": None,
                "currency": "—",
                "status": "✗ FAILED",
            })

    return results


# ── Table Printer ────────────────────────────────────────

def print_price_table(results):
    """
    Print a clean bordered table of asset prices.

    Successful fetches show the price; failed ones show an error marker.
    Timestamp is shown in IST (Indian Standard Time).
    """
    now_ist = datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST")

    # Format rows
    rows = []
    for r in results:
        if r["price"] is not None:
            price_str = f"{r['price']:,.2f}"
        else:
            price_str = "— error —"
        rows.append((r["name"], price_str, r["currency"], r["status"]))

    # Column widths (with padding)
    headers = ("Asset", "Price", "Currency", "Status")
    col_widths = [
        max(len(headers[i]), max(len(row[i]) for row in rows)) + 2
        for i in range(4)
    ]

    # Table drawing helpers
    def border(left, mid, right, fill="─"):
        return left + mid.join(fill * w for w in col_widths) + right

    def data_row(values):
        cells = [f" {values[i].ljust(col_widths[i] - 2)} " for i in range(4)]
        return "│" + "│".join(cells) + "│"

    # Print
    print(f"\n  Asset Prices — fetched at {now_ist}")
    print(f"  {border('┌', '┬', '┐')}")
    print(f"  {data_row(headers)}")
    print(f"  {border('├', '┼', '┤')}")
    for row in rows:
        print(f"  {data_row(row)}")
    print(f"  {border('└', '┴', '┘')}")

    # Summary
    success = sum(1 for r in results if r["price"] is not None)
    failed = len(results) - success
    print(f"\n  Fetched {success}/{len(results)} assets successfully.", end="")
    if failed > 0:
        print(f" ({failed} failed)", end="")
    print("\n")


# ── Main ─────────────────────────────────────────────────

if __name__ == "__main__":
    # Assets to fetch — at least 1 stock, 1 crypto, 1 commodity
    assets = [
        {"symbol": "BTC",   "type": "crypto",    "name": "BTC"},
        {"symbol": "^NSEI", "type": "stock",      "name": "NIFTY50"},
        {"symbol": "GC=F",  "type": "commodity",  "name": "GOLD"},
    ]

    results = fetch_all_prices(assets)
    print_price_table(results)
