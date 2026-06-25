# agent.py
# Agent principal — research → decizie → trade → jurnal
# Reguli citite din rules.json. Salveaza trade-uri in trades.csv (pt R-multiple).
import os
import json
import sys
import csv
from datetime import datetime
from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "scripts"))
import research
import trade

load_dotenv()

FOLDER = os.path.dirname(os.path.abspath(__file__))
WATCHLIST_FILE = os.path.join(FOLDER, "watchlist.json")
RULES_FILE = os.path.join(FOLDER, "rules.json")
JOURNAL_DIR = os.path.join(FOLDER, "journal")
TRADES_CSV = os.path.join(FOLDER, "trades.csv")

# Portofoliu pentru calcul sizing (din .env, fallback)
PORTFOLIO_VALUE = float(os.getenv("PORTFOLIO_VALUE_USD", 100000))

# Harta sectoarelor (pentru diversificare)
SECTOARE = {
    "AAPL": "tech", "MSFT": "tech", "GOOGL": "tech", "AMZN": "tech",
    "META": "tech", "NVDA": "semi", "TSLA": "auto", "AVGO": "semi",
    "ORCL": "software", "CRM": "software", "AMD": "semi", "INTC": "semi",
    "QCOM": "semi", "TXN": "semi", "MU": "semi", "AMAT": "semi",
    "ADI": "semi", "LRCX": "semi", "KLAC": "semi", "MRVL": "semi",
    "ADBE": "software", "NOW": "software", "INTU": "software", "PANW": "software",
    "SNOW": "software", "CRWD": "software", "DDOG": "software", "NET": "software",
    "ZS": "software", "PLTR": "software", "NFLX": "media", "DIS": "media",
    "CMCSA": "media", "T": "telecom", "VZ": "telecom", "TMUS": "telecom",
    "JPM": "financiar", "BAC": "financiar", "WFC": "financiar", "GS": "financiar",
    "MS": "financiar", "C": "financiar", "BLK": "financiar", "SCHW": "financiar",
    "AXP": "financiar", "V": "financiar", "MA": "financiar", "PYPL": "fintech",
    "UNH": "sanatate", "JNJ": "sanatate", "LLY": "sanatate", "PFE": "sanatate",
    "MRK": "sanatate", "ABBV": "sanatate", "TMO": "sanatate", "ABT": "sanatate",
    "DHR": "sanatate", "BMY": "sanatate", "WMT": "consum", "COST": "consum",
    "HD": "consum", "NKE": "consum", "MCD": "consum", "SBUX": "consum",
    "TGT": "consum", "LOW": "consum", "KO": "consum", "PEP": "consum",
    "PG": "consum", "XOM": "energie", "CVX": "energie", "COP": "energie",
    "SLB": "energie", "EOG": "energie", "MPC": "energie", "PSX": "energie",
    "BA": "industrial", "CAT": "industrial", "GE": "industrial", "HON": "industrial",
    "UPS": "industrial", "RTX": "industrial", "LMT": "industrial", "DE": "industrial",
    "F": "auto", "GM": "auto", "RIVN": "auto", "LCID": "auto", "NIO": "auto",
    "COIN": "crypto", "MARA": "crypto", "RIOT": "crypto", "SOFI": "fintech",
    "AFRM": "fintech", "UPST": "fintech", "DKNG": "consum", "ROKU": "media",
    "SHOP": "software", "ABNB": "consum", "UBER": "tech", "LYFT": "tech",
    "SNAP": "media", "PINS": "media", "RBLX": "media", "HOOD": "fintech",
    "DASH": "consum", "MRNA": "biotech", "BNTX": "biotech", "VRTX": "biotech",
    "REGN": "biotech", "GILD": "biotech", "BIIB": "biotech", "BABA": "china",
    "JD": "china", "PDD": "china", "BIDU": "china", "SPY": "etf",
    "QQQ": "etf", "IWM": "etf", "DIA": "etf",
}


def incarca_reguli():
    with open(RULES_FILE) as f:
        return json.load(f)


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


def salveaza_trade(simbol, side, qty, pret, stop_price):
    """Salveaza trade in CSV pentru calcul R-multiple ulterior."""
    exista = os.path.exists(TRADES_CSV)
    with open(TRADES_CSV, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if not exista:
            w.writerow(["timestamp", "symbol", "side", "qty",
                        "entry_price", "stop_price", "sector"])
        w.writerow([datetime.now().isoformat(), simbol, side, qty,
                    round(pret, 2), round(stop_price, 2),
                    SECTOARE.get(simbol, "altul")])


def salveaza_istoric(valoare, cash, nr_pozitii):
    """Salveaza valoarea portofoliului zilnic pentru grafic evolutie."""
    import csv as _csv
    fisier = os.path.join(FOLDER, "istoric_portofoliu.csv")
    zi = datetime.now().strftime("%Y-%m-%d")
    randuri = {}
    if os.path.exists(fisier):
        with open(fisier, encoding="utf-8") as f:
            for row in _csv.DictReader(f):
                randuri[row["zi"]] = row
    randuri[zi] = {"zi": zi, "valoare": round(valoare, 2),
                   "cash": round(cash, 2), "pozitii": nr_pozitii}
    with open(fisier, "w", newline="", encoding="utf-8") as f:
        w = _csv.DictWriter(f, fieldnames=["zi", "valoare", "cash", "pozitii"])
        w.writeheader()
        for z in sorted(randuri.keys()):
            w.writerow(randuri[z])


def putere_semnal(a):
    try:
        return (a["pret"] - a["ma50"]) / a["ma50"] * 100
    except Exception:
        return 0


def selecteaza_diversificat(bullish, detinute, max_pozitii, max_sector):
    selectii = []
    pe_sector = {}
    for a in bullish:
        if len(selectii) >= max_pozitii:
            break
        if a["symbol"] in detinute:
            continue
        sector = a.get("sector", "altul")
        if pe_sector.get(sector, 0) >= max_sector:
            continue
        selectii.append(a)
        pe_sector[sector] = pe_sector.get(sector, 0) + 1
    return selectii


def ruleaza():
    print("=" * 50)
    print("AGENT TRADING V2 — sesiune completa")
    print("=" * 50)

    reguli = incarca_reguli()
    r_entry = reguli["entry_filters"]
    r_sel = reguli["selection"]
    r_exit = reguli["exit"]
    r_risk = reguli["risk"]
    r_regime = reguli["market_regime"]

    stop_loss_pct = r_exit["stop_loss_pct"]
    limit_marja = r_risk["limit_order_marja_pct"] / 100
    max_pozitie_pct = r_risk["max_pozitie_pct"]
    max_pozitii = r_sel["max_pozitii_noi"]
    max_sector = r_sel["max_per_sector"]
    min_pret = reguli["universe_filters"]["min_price_usd"]

    print(f"Strategie: {reguli['strategy_name']}")
    print(f"Reguli: SL={stop_loss_pct}% | max {max_pozitii} pozitii | "
          f"max {max_sector}/sector | pozitie {max_pozitie_pct}%")

    status = trade.get_market_status()
    piata_deschisa = status.get("is_open", False)
    zi = datetime.now().strftime("%Y-%m-%d")

    account = research.get_account()
    cash = float(account.get("cash", 0))
    valoare_totala = float(account.get("portfolio_value", 0))
    pozitii = research.get_positions()
    if not isinstance(pozitii, list):
        pozitii = []

    print(f"Cash: ${cash:.2f} | Portofoliu: ${valoare_totala:.2f}")
    print(f"Pozitii deschise: {len(pozitii)} | Piata: {'DESCHISA' if piata_deschisa else 'INCHISA'}")
    salveaza_istoric(valoare_totala, cash, len(pozitii))

    wl = incarca_watchlist()
    simboluri = [item["symbol"] for item in wl["watchlist"]]
    aloc = {item["symbol"]: item["max_allocation_pct"] for item in wl["watchlist"]}
    print(f"\nAnalizez {len(simboluri)} actiuni (descarcare in bloc)...")
    rezultate = research.analizeaza_toate(simboluri)

    analize = []
    erori = 0
    for s in simboluri:
        a = rezultate.get(s, {"symbol": s, "eroare": "lipsa"})
        a["max_allocation_pct"] = aloc[s]
        analize.append(a)
        if "eroare" in a:
            erori += 1

    valide = [a for a in analize if "eroare" not in a]
    # Filtru pret minim
    valide = [a for a in valide if a.get("pret", 0) >= min_pret]
    bullish = [a for a in valide if a.get("trend") == "bullish"]
    bearish = [a for a in valide if a.get("trend") == "bearish"]

    for a in bullish:
        a["putere"] = putere_semnal(a)
        a["sector"] = SECTOARE.get(a["symbol"], "altul")
    bullish = [a for a in bullish if a["putere"] >= r_entry["min_putere_pct"]]
    bullish.sort(key=lambda x: x["putere"], reverse=True)

    print(f"  Analizate: {len(valide)} OK, {erori} erori")
    print(f"  Bullish: {len(bullish)} | Bearish: {len(bearish)} | "
          f"Lateral: {len(valide) - len(bullish) - len(bearish)}")
    if bullish:
        print("  Top candidati (dupa putere semnal):")
        for a in bullish[:8]:
            print(f"    {a['symbol']} ({a['sector']}) +{a['putere']:.1f}% peste MA50")

    # Stop loss pe pozitii existente
    inchideri = []
    pt_cfg = r_exit.get("profit_taking", {"activ": False})
    for p in pozitii:
        try:
            pl_pct = float(p.get("unrealized_plpc", 0)) * 100
            stop_efectiv = -stop_loss_pct
            prag_atins = None
            if pt_cfg.get("activ"):
                for prag in pt_cfg["praguri"]:
                    if pl_pct >= prag["profit_pct"]:
                        if prag["muta_stop_la_pct"] > stop_efectiv:
                            stop_efectiv = prag["muta_stop_la_pct"]
                            prag_atins = prag["profit_pct"]
            iesire = pl_pct <= stop_efectiv
            if iesire:
                if piata_deschisa:
                    pret = float(p["current_price"])
                    limit = round(pret * (1 - limit_marja), 2)
                    trade.place_order(p["symbol"], p["qty"], "sell", limit)
                    salveaza_trade(p["symbol"], "SELL", p["qty"], pret, 0)
                    if prag_atins is not None:
                        motiv = f"PROFIT-TAKING (stop urcat la {stop_efectiv:.0f}% dupa +{prag_atins:.0f}%)"
                    else:
                        motiv = f"STOP LOSS ({pl_pct:.1f}%)"
                    inchideri.append(f"{p['symbol']} — {motiv}")
                    print(f"  🔴 INCHIS {p['symbol']}: {motiv} | P&L acum {pl_pct:.1f}%")
                else:
                    print(f"  {p['symbol']} sub stop efectiv ({stop_efectiv:.0f}%) — astept deschiderea")
            elif pt_cfg.get("activ") and prag_atins is not None:
                print(f"  🛡️  {p['symbol']} +{pl_pct:.1f}% — stop protejat la {stop_efectiv:.0f}% (prag +{prag_atins:.0f}% atins)")
        except Exception as e:
            print(f"  Eroare verificare {p.get('symbol')}: {e}")

    # Regim de piata
    prag = r_regime["prag_bearish_pct"] / 100
    piata_in_scadere = (r_regime["stai_deoparte_daca_bearish_majoritate"]
                        and valide and len(bearish) > len(valide) * prag)

    trade_uri = []
    selectii = []
    detinute = [p["symbol"] for p in pozitii]

    if piata_in_scadere:
        print(f"\n⚠️  Piata in scadere ({len(bearish)} bearish din {len(valide)}) — STAU DEOPARTE")
    elif not piata_deschisa:
        selectii = selecteaza_diversificat(bullish, detinute, max_pozitii, max_sector)
        print("\n🌙 Piata inchisa — analiza pregatita, fara ordine")
        if selectii:
            print(f"  La deschidere as cumpara: {', '.join(s['symbol'] for s in selectii)}")
    else:
        print(f"\nCaut intrari (max {max_pozitii}, max {max_sector}/sector)...")
        selectii = selecteaza_diversificat(bullish, detinute, max_pozitii, max_sector)
        for a in selectii:
            max_alocare = min(max_pozitie_pct, a["max_allocation_pct"])
            suma = valoare_totala * max_alocare / 100
            pret = a["pret"]
            qty = int(suma / pret)
            if qty < 1:
                continue
            valid, motiv = trade.validate_order(a["symbol"], qty, pret, valoare_totala, pozitii)
            if not valid:
                print(f"  {a['symbol']}: respins — {motiv}")
                continue
            limit = round(pret * (1 + limit_marja), 2)
            stop_price = pret * (1 - stop_loss_pct / 100)
            trade.place_order(a["symbol"], qty, "buy", limit)
            salveaza_trade(a["symbol"], "BUY", qty, limit, stop_price)
            trade_uri.append(f"{a['symbol']} ({a['sector']}) BUY {qty} @ ${limit}")
            print(f"  ✅ {a['symbol']} ({a['sector']}) BUY {qty} @ ${limit} | +{a['putere']:.1f}% peste MA50")

    jurnal = genereaza_jurnal(zi, cash, valoare_totala, pozitii, valide,
                              bullish, bearish, trade_uri, inchideri,
                              piata_in_scadere, piata_deschisa, selectii, reguli)
    scrie_jurnal(jurnal)


def genereaza_jurnal(zi, cash, valoare, pozitii, valide, bullish, bearish,
                     trade_uri, inchideri, scadere, piata_deschisa, selectii, reguli):
    linii = [f"# Jurnal Trading — {zi}\n"]
    linii.append(f"*Strategie: {reguli['strategy_name']}*\n")
    linii.append("## Stare Portofoliu")
    linii.append(f"- Cash: ${cash:.2f}")
    poz_str = ", ".join(f"{p['symbol']} ({p['qty']} @ ${float(p['avg_entry_price']):.2f})"
                        for p in pozitii) if pozitii else "Nicio pozitie"
    linii.append(f"- Pozitii: {poz_str}")
    linii.append(f"- Valoare totala: ${valoare:.2f}\n")

    linii.append("## Status Piata")
    linii.append("Piata DESCHISA" if piata_deschisa else "Piata INCHISA (fara ordine plasate)")
    linii.append("")

    linii.append("## Rezumat Analiza")
    linii.append(f"- Actiuni analizate: {len(valide)}")
    linii.append(f"- Bullish: {len(bullish)} | Bearish: {len(bearish)} | "
                 f"Lateral: {len(valide) - len(bullish) - len(bearish)}")
    linii.append("")

    if bullish:
        linii.append("## Top 15 Candidati Bullish (sortati dupa putere semnal)")
        linii.append("| Simbol | Sector | Pret | MA50 | % peste MA50 |")
        linii.append("|--------|--------|------|------|--------------|")
        for a in bullish[:15]:
            linii.append(f"| {a['symbol']} | {a.get('sector','?')} | ${a['pret']} | "
                         f"${a['ma50']} | +{a.get('putere',0):.1f}% |")
        linii.append("")

    if selectii:
        linii.append("## Selectie Diversificata (max 2/sector)")
        for a in selectii:
            linii.append(f"- {a['symbol']} ({a.get('sector','?')}) — +{a.get('putere',0):.1f}% peste MA50")
        linii.append("")

    if scadere:
        linii.append("## Decizie Generala")
        linii.append("Majoritatea actiunilor in trend descendent. Agentul a stat deoparte.\n")

    linii.append("## Trade-uri Executate")
    if trade_uri:
        for t in trade_uri:
            linii.append(f"- {t}")
    else:
        linii.append("Niciun trade nou azi.")
    linii.append("")

    linii.append("## Pozitii Inchise")
    linii.append(", ".join(inchideri) if inchideri else "Niciuna azi.")
    linii.append("")

    linii.append("## Reflectie")
    if not piata_deschisa:
        if selectii:
            s = ", ".join(a["symbol"] for a in selectii)
            linii.append(f"Piata inchisa — analiza pregatita. {len(bullish)} candidati bullish. "
                         f"La deschidere as cumpara (diversificat): {s}.")
        else:
            linii.append(f"Piata inchisa — {len(bullish)} candidati bullish identificati.")
    elif scadere:
        linii.append(f"Piata in scadere ({len(bearish)} bearish) — stau deoparte. Astept stabilizare.")
    elif trade_uri:
        linii.append(f"Am intrat in {len(trade_uri)} pozitii diversificate, "
                     f"alese dupa putere de semnal din {len(bullish)} candidati.")
    else:
        linii.append(f"Candidati bullish existau ({len(bullish)}) dar respinsi de limite/cash sau detinuti.")

    return "\n".join(linii)


if __name__ == "__main__":
    ruleaza()
