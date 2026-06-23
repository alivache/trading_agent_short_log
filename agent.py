# agent.py
# Agent principal — orchestreaza research → decizie → trade → jurnal
# Versiune Python pura, inspirata din arhitectura MindStudio/Claude Code
import os
import json
import sys
from datetime import datetime
from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "scripts"))
import research
import trade

load_dotenv()

FOLDER = os.path.dirname(os.path.abspath(__file__))
WATCHLIST_FILE = os.path.join(FOLDER, "watchlist.json")
JOURNAL_DIR = os.path.join(FOLDER, "journal")

MAX_POZITIE_PCT = float(os.getenv("MAX_POZITIE_PCT", 5))
STOP_LOSS_PCT = float(os.getenv("STOP_LOSS_PCT", 8))
LIMIT_MARJA = float(os.getenv("LIMIT_ORDER_MARJA_PCT", 0.2)) / 100
MAX_TRADES = int(os.getenv("MAX_TRADES_PER_ZI", 5))


def incarca_watchlist():
    with open(WATCHLIST_FILE) as f:
        return json.load(f)


def scrie_jurnal(continut):
    os.makedirs(JOURNAL_DIR, exist_ok=True)
    zi = datetime.now().strftime("%Y-%m-%d")
    cale = os.path.join(JOURNAL_DIR, f"{zi}.md")
    with open(cale, "w", encoding="utf-8") as f:
        f.write(continut)
    print(f"Jurnal scris: {cale}")
    return cale


def ruleaza():
    print("=" * 50)
    print("AGENT TRADING V2 — sesiune completa")
    print("=" * 50)

    # 1. Verifica piata
    status = trade.get_market_status()
    piata_deschisa = status.get("is_open", False)
    zi = datetime.now().strftime("%Y-%m-%d")

    # 2. Citeste contul si pozitiile
    account = research.get_account()
    cash = float(account.get("cash", 0))
    valoare_totala = float(account.get("portfolio_value", 0))
    pozitii = research.get_positions()

    print(f"Cash: ${cash:.2f} | Portofoliu: ${valoare_totala:.2f}")
    print(f"Pozitii deschise: {len(pozitii)}")
    print(f"Piata: {'DESCHISA' if piata_deschisa else 'INCHISA'}")

    # 3. Research watchlist
    wl = incarca_watchlist()
    analize = []
    print("\nAnalizez watchlist...")
    for item in wl["watchlist"]:
        a = research.analiza_simbol(item["symbol"])
        a["max_allocation_pct"] = item["max_allocation_pct"]
        analize.append(a)
        print(f"  {a['symbol']}: ${a.get('pret','?')} | "
              f"MA20={a.get('ma20','?')} MA50={a.get('ma50','?')} | {a.get('trend','?')}")

    # 4. Verifica stop loss pe pozitii existente
    inchideri = []
    for p in pozitii:
        try:
            pl_pct = float(p.get("unrealized_plpc", 0)) * 100
            if pl_pct <= -STOP_LOSS_PCT:
                if piata_deschisa:
                    pret = float(p["current_price"])
                    limit = round(pret * (1 - LIMIT_MARJA), 2)
                    rez = trade.place_order(p["symbol"], p["qty"], "sell", limit)
                    inchideri.append(f"{p['symbol']} (SL {pl_pct:.1f}%)")
                    print(f"  STOP LOSS {p['symbol']}: {pl_pct:.1f}%")
        except Exception as e:
            print(f"  Eroare verificare {p.get('symbol')}: {e}")

    # 5. Cauta intrari noi (doar daca piata e bullish in general)
    bullish = [a for a in analize if a.get("trend") == "bullish"]
    bearish = [a for a in analize if a.get("trend") == "bearish"]
    piata_in_scadere = len(bearish) > len(analize) / 2

    trade_uri = []
    simboluri_detinute = [p["symbol"] for p in pozitii]

    if piata_in_scadere:
        print("\n⚠️  Majoritatea simbolurilor sunt bearish — STAU DEOPARTE")
    elif piata_deschisa:
        print(f"\nCaut intrari ({len(bullish)} simboluri bullish)...")
        for a in bullish:
            if len(trade_uri) >= MAX_TRADES:
                break
            if a["symbol"] in simboluri_detinute:
                continue
            # Calcul cantitate cu limita de alocare
            max_alocare = min(MAX_POZITIE_PCT, a["max_allocation_pct"])
            suma = valoare_totala * max_alocare / 100
            pret = a["pret"]
            qty = int(suma / pret)
            if qty < 1:
                continue
            valid, motiv = trade.validate_order(
                a["symbol"], qty, pret, valoare_totala, pozitii
            )
            if not valid:
                print(f"  {a['symbol']}: respins — {motiv}")
                continue
            limit = round(pret * (1 + LIMIT_MARJA), 2)
            rez = trade.place_order(a["symbol"], qty, "buy", limit)
            trade_uri.append(f"{a['symbol']} BUY {qty} @ ${limit}")
            print(f"  ✅ {a['symbol']} BUY {qty} @ ${limit}")

    # 6. Scrie jurnal
    jurnal = genereaza_jurnal(zi, cash, valoare_totala, pozitii,
                              analize, trade_uri, inchideri, piata_in_scadere)
    scrie_jurnal(jurnal)


def genereaza_jurnal(zi, cash, valoare, pozitii, analize, trade_uri, inchideri, scadere):
    linii = [f"# Jurnal Trading — {zi}\n"]
    linii.append("## Stare Portofoliu")
    linii.append(f"- Cash: ${cash:.2f}")
    poz_str = ", ".join(f"{p['symbol']} ({p['qty']} @ ${float(p['avg_entry_price']):.2f})"
                        for p in pozitii) if pozitii else "Nicio pozitie"
    linii.append(f"- Pozitii: {poz_str}")
    linii.append(f"- Valoare totala: ${valoare:.2f}\n")

    linii.append("## Research Piata")
    for a in analize:
        linii.append(f"### {a['symbol']}")
        linii.append(f"- Pret: ${a.get('pret','?')} | MA20: ${a.get('ma20','?')} | "
                     f"MA50: ${a.get('ma50','?')} | Trend: {a.get('trend','?')}")
    linii.append("")

    if scadere:
        linii.append("## Decizie Generala")
        linii.append("Majoritatea simbolurilor sunt in trend descendent. "
                     "Agentul a stat deoparte (LONG-only nu profita din scadere).\n")

    linii.append("## Trade-uri Executate")
    if trade_uri:
        linii.append("| Simbol | Actiune |")
        linii.append("|--------|---------|")
        for t in trade_uri:
            linii.append(f"| {t} | |")
    else:
        linii.append("Niciun trade nou azi.")
    linii.append("")

    linii.append("## Pozitii Inchise")
    linii.append(", ".join(inchideri) if inchideri else "Niciuna azi.")
    linii.append("")

    linii.append("## Reflectie")
    if scadere:
        linii.append("Piata in scadere — corect sa stau deoparte. Astept stabilizare.")
    elif trade_uri:
        linii.append(f"Am intrat in {len(trade_uri)} pozitii pe simboluri cu trend bullish confirmat.")
    else:
        linii.append("Nicio oportunitate clara azi. Rabdarea e o pozitie valida.")

    return "\n".join(linii)


if __name__ == "__main__":
    ruleaza()
