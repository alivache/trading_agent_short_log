# scripts/trade.py
# Plaseaza ordine, verifica piata, valideaza ordine inainte de plasare
import os
import requests
import json
import sys
from dotenv import load_dotenv

load_dotenv()

ALPACA_KEY = os.getenv("APCA_API_KEY_ID")
ALPACA_SECRET = os.getenv("APCA_API_SECRET_KEY")
BASE_URL = os.getenv("APCA_BASE_URL")

MAX_POZITIE_PCT = float(os.getenv("MAX_POZITIE_PCT", 5))
REZERVA_CASH_PCT = float(os.getenv("REZERVA_CASH_PCT", 20))
EXPUNERE_MAX_PCT = float(os.getenv("EXPUNERE_MAX_PCT", 80))

HEADERS = {
    "APCA-API-KEY-ID": ALPACA_KEY,
    "APCA-API-SECRET-KEY": ALPACA_SECRET,
    "Content-Type": "application/json"
}


def place_order(symbol, qty, side, limit_price=None):
    """Plaseaza un ordin buy sau sell."""
    order_data = {
        "symbol": symbol,
        "qty": qty,
        "side": side,
        "type": "limit" if limit_price else "market",
        "time_in_force": "day",
    }
    if limit_price:
        order_data["limit_price"] = str(limit_price)

    url = f"{BASE_URL}/v2/orders"
    r = requests.post(url, headers=HEADERS, json=order_data)
    return r.json()


def cancel_all_orders():
    """Anuleaza toate ordinele deschise."""
    url = f"{BASE_URL}/v2/orders"
    r = requests.delete(url, headers=HEADERS)
    return r.status_code


def get_market_status():
    """Verifica daca piata e deschisa."""
    url = f"{BASE_URL}/v2/clock"
    r = requests.get(url, headers=HEADERS)
    return r.json()


def validate_order(symbol, qty, current_price, account_value, current_positions):
    """Verificari de siguranta inainte de a plasa orice ordin (Layer 2)."""
    order_value = qty * current_price
    allocation_pct = (order_value / account_value) * 100

    # Verifica marimea maxima a pozitiei
    if allocation_pct > MAX_POZITIE_PCT:
        return False, f"Ordinul depaseste limita de {MAX_POZITIE_PCT}% alocare: {allocation_pct:.1f}%"

    # Verifica expunerea totala (pozitii + acest ordin < EXPUNERE_MAX)
    total_invested = sum(float(p.get("market_value", 0)) for p in current_positions)
    expunere_noua = (total_invested + order_value) / account_value * 100
    if expunere_noua > EXPUNERE_MAX_PCT:
        return False, f"Ordinul ar incalca rezerva de cash de {REZERVA_CASH_PCT}% (expunere ar fi {expunere_noua:.1f}%)"

    return True, "Ordin validat"


if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else "status"

    if action == "status":
        print(json.dumps(get_market_status(), indent=2))
    elif action == "order":
        symbol = sys.argv[2]
        qty = sys.argv[3]
        side = sys.argv[4]
        limit_price = sys.argv[5] if len(sys.argv) > 5 else None
        print(json.dumps(place_order(symbol, qty, side, limit_price), indent=2))
    elif action == "cancel":
        print(cancel_all_orders())
