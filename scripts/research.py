# scripts/research.py
# Date de pret de la yfinance (gratuit), cont/pozitii de la Alpaca
# Optimizat: descarca toate simbolurile odata (bulk), nu unul cate unul
import os
import requests
import json
import sys
import time
import yfinance as yf
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

ALPACA_KEY = os.getenv("APCA_API_KEY_ID")
ALPACA_SECRET = os.getenv("APCA_API_SECRET_KEY")
BASE_URL = os.getenv("APCA_BASE_URL")

HEADERS = {
    "APCA-API-KEY-ID": ALPACA_KEY,
    "APCA-API-SECRET-KEY": ALPACA_SECRET,
}


def get_bars(symbol, limit=60):
    """Bare istorice pentru UN singur simbol (folosit la testare manuala)."""
    try:
        df = yf.download(symbol, period=f"{limit + 40}d", interval="1d",
                         progress=False, auto_adjust=False)
        if df.empty:
            return {"bars": []}
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df.tail(limit)
        bars = []
        for idx, row in df.iterrows():
            try:
                bars.append({
                    "t": idx.strftime("%Y-%m-%d"),
                    "o": round(float(row["Open"]), 2),
                    "h": round(float(row["High"]), 2),
                    "l": round(float(row["Low"]), 2),
                    "c": round(float(row["Close"]), 2),
                    "v": int(row["Volume"]) if not pd.isna(row["Volume"]) else 0
                })
            except Exception:
                continue
        return {"bars": bars}
    except Exception as e:
        return {"bars": [], "eroare": str(e)}


def analizeaza_toate(simboluri):
    """Descarca TOATE simbolurile odata si calculeaza MA20/MA50/trend pentru fiecare.
    Mult mai rapid si evita rate-limit fata de cereri individuale."""
    rezultat = {}
    try:
        df = yf.download(simboluri, period="100d", interval="1d",
                         group_by="ticker", progress=False, threads=True,
                         auto_adjust=False)
    except Exception as e:
        # Fallback: returneaza erori pentru toate
        for s in simboluri:
            rezultat[s] = {"symbol": s, "eroare": f"download esuat: {e}"}
        return rezultat

    for simbol in simboluri:
        try:
            if len(simboluri) > 1:
                d = df[simbol].dropna()
            else:
                d = df.dropna()
            if len(d) < 50:
                rezultat[simbol] = {"symbol": simbol, "eroare": "date insuficiente"}
                continue

            inchideri = d["Close"].tolist()
            pret = round(float(inchideri[-1]), 2)
            ma20 = round(sum(inchideri[-20:]) / 20, 2)
            ma50 = round(sum(inchideri[-50:]) / 50, 2)

            if pret > ma20 > ma50:
                trend = "bullish"
            elif pret < ma20 < ma50:
                trend = "bearish"
            else:
                trend = "lateral"

            rezultat[simbol] = {
                "symbol": simbol, "pret": pret,
                "ma20": ma20, "ma50": ma50, "trend": trend
            }
        except Exception as e:
            rezultat[simbol] = {"symbol": simbol, "eroare": str(e)}

    return rezultat


def high_maxim_de_la(symbol, data_intrare):
    """Returneaza cel mai mare High atins de la data_intrare pana azi (yfinance)."""
    try:
        import pandas as pd
        from datetime import datetime, timedelta
        d0 = datetime.strptime(data_intrare[:10], "%Y-%m-%d")
        zile = max((datetime.now() - d0).days + 5, 7)
        df = yf.download(symbol, period=f"{zile}d", interval="1d",
                         progress=False, auto_adjust=False)
        if df.empty:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df[df.index >= d0.strftime("%Y-%m-%d")]
        if df.empty or "High" not in df.columns:
            return None
        return round(float(df["High"].max()), 2)
    except Exception:
        return None


def get_account():
    url = f"{BASE_URL}/v2/account"
    r = requests.get(url, headers=HEADERS)
    return r.json()


def get_positions():
    url = f"{BASE_URL}/v2/positions"
    r = requests.get(url, headers=HEADERS)
    return r.json()


def get_news(symbol):
    url = "https://data.alpaca.markets/v1beta1/news"
    params = {"symbols": symbol, "limit": 5, "sort": "desc"}
    r = requests.get(url, headers=HEADERS, params=params)
    return r.json()


def calculeaza_ma(bars, perioada):
    inchideri = [b["c"] for b in bars.get("bars", [])]
    if len(inchideri) < perioada:
        return None
    return sum(inchideri[-perioada:]) / perioada


def analiza_simbol(symbol):
    """Analiza pentru UN simbol (testare manuala)."""
    bars = get_bars(symbol, limit=60)
    barr = bars.get("bars", [])
    if not barr:
        rez = {"symbol": symbol, "eroare": "fara date"}
        if "eroare" in bars:
            rez["detalii"] = bars["eroare"]
        return rez
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
        "symbol": symbol, "pret": round(pret, 2),
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
