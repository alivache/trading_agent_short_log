#!/usr/bin/env python3
"""
Reduce numarul de pozitii la MAX_POZITII, inchizand cele mai SLABE
(dupa P&L%), pastrand cele mai profitabile. Foloseste limit orders.
Ruleaza doar cand piata e deschisa.
"""
import os
import sys
import json
import requests
from dotenv import load_dotenv

load_dotenv()

ALPACA_KEY = os.getenv("APCA_API_KEY_ID")
ALPACA_SECRET = os.getenv("APCA_API_SECRET_KEY")
BASE_URL = os.getenv("APCA_BASE_URL")
HEADERS = {
    "APCA-API-KEY-ID": ALPACA_KEY,
    "APCA-API-SECRET-KEY": ALPACA_SECRET,
    "Content-Type": "application/json",
}

FOLDER = os.path.dirname(os.path.abspath(__file__))
RULES_FILE = os.path.join(FOLDER, "rules.json")


def get_max_pozitii():
    try:
        with open(RULES_FILE) as f:
            r = json.load(f)
        return r["selection"]["max_pozitii_noi"]
    except Exception:
        return 5


def get_marja():
    try:
        with open(RULES_FILE) as f:
            r = json.load(f)
        return r["risk"]["limit_order_marja_pct"] / 100
    except Exception:
        return 0.002


def get_positions():
    r = requests.get(f"{BASE_URL}/v2/positions", headers=HEADERS, timeout=10)
    d = r.json()
    return d if isinstance(d, list) else []


def get_clock():
    r = requests.get(f"{BASE_URL}/v2/clock", headers=HEADERS, timeout=10)
    return r.json()


def vinde(simbol, qty, pret, marja):
    limit = round(pret * (1 - marja), 2)
    order = {
        "symbol": simbol, "qty": qty, "side": "sell",
        "type": "limit", "time_in_force": "day", "limit_price": str(limit),
    }
    r = requests.post(f"{BASE_URL}/v2/orders", headers=HEADERS, json=order, timeout=10)
    return r.json(), limit


def main():
    max_poz = get_max_pozitii()
    marja = get_marja()

    clock = get_clock()
    if not clock.get("is_open"):
        print(f"❌ Piata e INCHISA. Se deschide: {clock.get('next_open')}")
        print("   Ruleaza scriptul cand piata e deschisa (limit orders day).")
        return

    pozitii = get_positions()
    n = len(pozitii)
    print(f"Pozitii curente: {n} | Limita: {max_poz}")

    if n <= max_poz:
        print(f"✅ Ai deja {n} pozitii (sub limita {max_poz}). Nimic de facut.")
        return

    # Sorteaza dupa P&L% DESCRESCATOR (cele mai bune primele)
    for p in pozitii:
        p["_pl_pct"] = float(p.get("unrealized_plpc", 0)) * 100

    pozitii.sort(key=lambda x: x["_pl_pct"], reverse=True)

    de_pastrat = pozitii[:max_poz]
    de_vandut = pozitii[max_poz:]

    print(f"\n📊 PASTREZ cele mai bune {max_poz}:")
    for p in de_pastrat:
        print(f"  🟢 {p['symbol']}: {p['_pl_pct']:+.1f}%")

    print(f"\n🔴 INCHID cele mai slabe {len(de_vandut)}:")
    for p in de_vandut:
        print(f"  {p['symbol']}: {p['_pl_pct']:+.1f}%")

    # Confirmare
    print(f"\n⚠️  Voi plasa {len(de_vandut)} ordine de VANZARE (limit orders).")
    raspuns = input("Confirmi? (da/nu): ").strip().lower()
    if raspuns not in ("da", "d", "yes", "y"):
        print("Anulat. Nicio vanzare.")
        return

    print()
    for p in de_vandut:
        try:
            pret = float(p["current_price"])
            rez, limit = vinde(p["symbol"], p["qty"], pret, marja)
            if "id" in rez:
                print(f"  ✅ Vandut {p['symbol']} ({p['qty']}) @ limit ${limit}")
            else:
                print(f"  ⚠️  {p['symbol']}: {rez.get('message', rez)}")
        except Exception as e:
            print(f"  ❌ Eroare {p['symbol']}: {e}")

    print(f"\n✅ Gata. Ar trebui sa ramai cu {max_poz} pozitii dupa executarea ordinelor.")
    print("   Verifica: ~/trading/venv/bin/python3 scripts/research.py positions")


if __name__ == "__main__":
    main()
