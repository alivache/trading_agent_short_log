# scripts/research.py
# Citeste date de piata de la Alpaca: bars, news, account, positions
import os
import requests
import json
import sys
from dotenv import load_dotenv

load_dotenv()

ALPACA_KEY = os.getenv("APCA_API_KEY_ID")
ALPACA_SECRET = os.getenv("APCA_API_SECRET_KEY")
BASE_URL = os.getenv("APCA_BASE_URL")

HEADERS = {
    "APCA-API-KEY-ID": ALPACA_KEY,
    "APCA-API-SECRET-KEY": ALPACA_SECRET,
}


def get_bars(symbol, timeframe="1Day", limit=60):
    """Descarca bare istorice de pret pentru un simbol."""
    url = f"https://data.alpaca.markets/v2/stocks/{symbol}/bars"
    params = {"timeframe": timeframe, "limit": limit, "adjustment": "raw"}
    r = requests.get(url, headers=HEADERS, params=params)
    return r.json()


def get_account():
    """Starea curenta a portofoliului."""
    url = f"{BASE_URL}/v2/account"
    r = requests.get(url, headers=HEADERS)
    return r.json()


def get_positions():
    """Toate pozitiile deschise."""
    url = f"{BASE_URL}/v2/positions"
    r = requests.get(url, headers=HEADERS)
    return r.json()


def get_news(symbol):
    """Stiri recente pentru un simbol."""
    url = "https://data.alpaca.markets/v1beta1/news"
    params = {"symbols": symbol, "limit": 5, "sort": "desc"}
    r = requests.get(url, headers=HEADERS, params=params)
    return r.json()


def calculeaza_ma(bars, perioada):
    """Calculeaza media mobila simpla din bare."""
    inchideri = [b["c"] for b in bars.get("bars", [])]
    if len(inchideri) < perioada:
        return None
    return sum(inchideri[-perioada:]) / perioada


def analiza_simbol(symbol):
    """Analiza completa: pret, MA20, MA50, trend, stiri."""
    bars = get_bars(symbol, limit=60)
    barr = bars.get("bars", [])
    if not barr:
        return {"symbol": symbol, "eroare": "fara date"}

    pret = barr[-1]["c"]
    ma20 = calculeaza_ma(bars, 20)
    ma50 = calculeaza_ma(bars, 50)

    trend = "necunoscut"
    if ma20 and ma50:
        if pret > ma20 > ma50:
            trend = "bullish"
        elif pret < ma20 < ma50:
            trend = "bearish"
        else:
            trend = "lateral"

    return {
        "symbol": symbol,
        "pret": round(pret, 2),
        "ma20": round(ma20, 2) if ma20 else None,
        "ma50": round(ma50, 2) if ma50 else None,
        "trend": trend
    }


if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else "account"
    symbol = sys.argv[2] if len(sys.argv) > 2 else None

    if action == "bars" and symbol:
        print(json.dumps(get_bars(symbol), indent=2))
    elif action == "news" and symbol:
        print(json.dumps(get_news(symbol), indent=2))
    elif action == "positions":
        print(json.dumps(get_positions(), indent=2))
    elif action == "analiza" and symbol:
        print(json.dumps(analiza_simbol(symbol), indent=2))
    else:
        print(json.dumps(get_account(), indent=2))
