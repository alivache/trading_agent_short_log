#!/usr/bin/env python3
"""
Calculeaza performanta in R-multiple din trades.csv.
R = (pret_iesire - pret_intrare) / (pret_intrare - stop_price)
Imperecheaza BUY cu SELL pe simbol (FIFO).
"""
import os
import csv
import json
from datetime import datetime

FOLDER = os.path.dirname(os.path.abspath(__file__))
TRADES_CSV = os.path.join(FOLDER, "trades.csv")


def incarca_trades():
    if not os.path.exists(TRADES_CSV):
        return []
    trades = []
    with open(TRADES_CSV, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            trades.append(row)
    return trades


def calculeaza_R():
    trades = incarca_trades()
    if not trades:
        return {"total": 0, "mesaj": "Niciun trade inca"}

    # Imperecheaza BUY cu SELL pe simbol (FIFO)
    buys = {}  # symbol -> lista de buy-uri deschise
    perechi = []

    for t in trades:
        simbol = t["symbol"]
        side = t["side"]
        if side == "BUY":
            buys.setdefault(simbol, []).append(t)
        elif side == "SELL":
            if simbol in buys and buys[simbol]:
                buy = buys[simbol].pop(0)
                try:
                    entry = float(buy["entry_price"])
                    stop = float(buy["stop_price"])
                    iesire = float(t["entry_price"])  # pretul de vanzare
                    risc = entry - stop
                    if risc > 0:
                        R = (iesire - entry) / risc
                    else:
                        R = 0
                    pnl = (iesire - entry) * int(buy["qty"])
                    perechi.append({
                        "symbol": simbol, "entry": entry, "exit": iesire,
                        "R": round(R, 2), "pnl": round(pnl, 2),
                        "sector": buy.get("sector", "?")
                    })
                except Exception:
                    continue

    if not perechi:
        deschise = sum(len(v) for v in buys.values())
        return {"total": 0, "pozitii_deschise": deschise,
                "mesaj": f"{deschise} pozitii deschise, niciuna inchisa inca"}

    total = len(perechi)
    wins = [p for p in perechi if p["R"] > 0]
    losses = [p for p in perechi if p["R"] <= 0]
    suma_R = sum(p["R"] for p in perechi)
    suma_pnl = sum(p["pnl"] for p in perechi)
    avg_R = suma_R / total if total else 0
    win_rate = len(wins) / total * 100 if total else 0

    # Histograma R
    buckets = {"<-2R": 0, "-2..-1R": 0, "-1..0R": 0,
               "0..1R": 0, "1..2R": 0, "2..3R": 0, ">3R": 0}
    for p in perechi:
        R = p["R"]
        if R <= -2: buckets["<-2R"] += 1
        elif R <= -1: buckets["-2..-1R"] += 1
        elif R <= 0: buckets["-1..0R"] += 1
        elif R <= 1: buckets["0..1R"] += 1
        elif R <= 2: buckets["1..2R"] += 1
        elif R <= 3: buckets["2..3R"] += 1
        else: buckets[">3R"] += 1

    best = max(perechi, key=lambda p: p["R"])
    worst = min(perechi, key=lambda p: p["R"])

    return {
        "total": total,
        "wins": len(wins), "losses": len(losses),
        "win_rate": round(win_rate, 1),
        "suma_R": round(suma_R, 2),
        "avg_R": round(avg_R, 2),
        "suma_pnl": round(suma_pnl, 2),
        "best": {"symbol": best["symbol"], "R": best["R"]},
        "worst": {"symbol": worst["symbol"], "R": worst["R"]},
        "histograma": buckets,
        "perechi": perechi,
        "pozitii_deschise": sum(len(v) for v in buys.values())
    }


if __name__ == "__main__":
    rez = calculeaza_R()
    print(json.dumps(rez, indent=2, ensure_ascii=False))
