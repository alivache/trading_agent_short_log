# agent.py
# Agent principal — research → decizie → trade → jurnal
# rules.json + R-multiple + vanzare partiala + trailing continuu pe high real + stiri + istoric
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

PORTFOLIO_VALUE = float(os.getenv("PORTFOLIO_VALUE_USD", 100000))

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
    fisier = os.path.join(FOLDER, "istoric_portofoliu.csv")
    zi = datetime.now().strftime("%Y-%m-%d")
    randuri = {}
    if os.path.exists(fisier):
        with open(fisier, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                randuri[row["zi"]] = row
    randuri[zi] = {"zi": zi, "valoare": round(valoare, 2),
                   "cash": round(cash, 2), "pozitii": nr_pozitii}
    with open(fisier, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["zi", "valoare", "cash", "pozitii"])
        w.writeheader()
        for z in sorted(randuri.keys()):
            w.writerow(randuri[z])


# ── Vanzare partiala (marcaje) ──
def incarca_partiale():
    fisier = os.path.join(FOLDER, "vanzari_partiale.json")
    if os.path.exists(fisier):
        try:
            with open(fisier) as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def marcheaza_partiala(simbol):
    fisier = os.path.join(FOLDER, "vanzari_partiale.json")
    date = incarca_partiale()
    date[simbol] = datetime.now().isoformat()
    with open(fisier, "w") as f:
        json.dump(date, f, indent=2)


def curata_partiala(simbol):
    fisier = os.path.join(FOLDER, "vanzari_partiale.json")
    date = incarca_partiale()
    if simbol in date:
        del date[simbol]
        with open(fisier, "w") as f:
            json.dump(date, f, indent=2)


# ── Trailing continuu (maxime de profit atinse) ──
def incarca_protectii():
    fisier = os.path.join(FOLDER, "protectii_stop.json")
    if os.path.exists(fisier):
        try:
            with open(fisier) as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def salveaza_protectie(simbol, nivel):
    fisier = os.path.join(FOLDER, "protectii_stop.json")
    date = incarca_protectii()
    if simbol not in date or nivel > date[simbol]:
        date[simbol] = nivel
        with open(fisier, "w") as f:
            json.dump(date, f, indent=2)


def curata_protectie(simbol):
    fisier = os.path.join(FOLDER, "protectii_stop.json")
    date = incarca_protectii()
    if simbol in date:
        del date[simbol]
        with open(fisier, "w") as f:
            json.dump(date, f, indent=2)


def data_intrare_pozitie(simbol):
    """Gaseste data ultimei cumparari (BUY) pentru un simbol din trades.csv."""
    if not os.path.exists(TRADES_CSV):
        return None
    data = None
    try:
        with open(TRADES_CSV, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row["symbol"] == simbol and row["side"] == "BUY":
                    data = row["timestamp"]
    except Exception:
        return None
    return data


def ia_stiri(simbol, maxim=2):
    """Ia titluri de stiri recente pentru un simbol (yfinance, gratuit)."""
    try:
        import yfinance as yf
        ticker = yf.Ticker(simbol)
        news = ticker.news
        titluri = []
        for n in news[:maxim]:
            t = n.get("content", {}).get("title") or n.get("title", "")
            if t:
                titluri.append(t)
        return titluri
    except Exception:
        return []


def putere_semnal(a):
    try:
        return (a["pret"] - a["ma50"]) / a["ma50"] * 100
    except Exception:
        return 0


def selecteaza_diversificat(bullish, detinute, max_pozitii, max_sector, sectoare_detinute=None):
    selectii = []
    pe_sector = dict(sectoare_detinute) if sectoare_detinute else {}
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


def ruleaza(doar_management=False):
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
    if doar_management:
        print("MOD: doar management (fara intrari noi)")
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

    # Curata marcajele pentru pozitii care nu mai exista
    simboluri_active = {p["symbol"] for p in pozitii}
    for simbol in list(incarca_partiale().keys()):
        if simbol not in simboluri_active:
            curata_partiala(simbol)
            curata_protectie(simbol)
            print(f"  🧹 Curatat marcaj vechi: {simbol} (nu mai e in portofoliu)")

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

    # ── Management pozitii: vanzare partiala + trailing continuu ──
    inchideri = []
    pt_cfg = r_exit.get("profit_taking", {"activ": False})
    vp_cfg = pt_cfg.get("vanzare_partiala", {"activ": False})
    tc_cfg = r_exit.get("trailing_continuu", {"activ": False})
    partiale = incarca_partiale()

    for p in pozitii:
        try:
            pl_pct = float(p.get("unrealized_plpc", 0)) * 100
            qty_total = int(p["qty"])
            pret_intrare = float(p["avg_entry_price"])

            # VANZARE PARTIALA la prag (o singura data)
            if (vp_cfg.get("activ") and piata_deschisa
                    and p["symbol"] not in partiale
                    and pl_pct >= vp_cfg["prag_profit_pct"]):
                qty_vand = int(qty_total * vp_cfg["fractiune_vanduta"])
                if qty_vand >= 1:
                    pret_p = float(p["current_price"])
                    limit_p = round(pret_p * (1 - limit_marja), 2)
                    trade.place_order(p["symbol"], qty_vand, "sell", limit_p)
                    salveaza_trade(p["symbol"], "SELL", qty_vand, pret_p, 0)
                    marcheaza_partiala(p["symbol"])
                    inchideri.append(f"{p['symbol']} — VANZARE PARTIALA {qty_vand}/{qty_total} la +{pl_pct:.1f}%")
                    print(f"  💰 PARTIAL {p['symbol']}: vandut {qty_vand}/{qty_total} la +{pl_pct:.1f}% (las restul sa curga)")

            # TRAILING CONTINUU pe HIGH real: stop = (max profit real) - distanta
            stop_efectiv = -stop_loss_pct
            prag_atins = None
            maxime = incarca_protectii()
            max_atins = maxime.get(p["symbol"], pl_pct)
            # High real din yfinance (max profit intraday atins de la intrare)
            try:
                data_int = data_intrare_pozitie(p["symbol"])
                if data_int:
                    high_max = research.high_maxim_de_la(p["symbol"], data_int)
                    if high_max and pret_intrare > 0:
                        pl_max_real = (high_max - pret_intrare) / pret_intrare * 100
                        if pl_max_real > max_atins:
                            max_atins = pl_max_real
            except Exception:
                pass
            if pl_pct > max_atins:
                max_atins = pl_pct
            salveaza_protectie(p["symbol"], round(max_atins, 2))
            if tc_cfg.get("activ") and max_atins >= tc_cfg["prag_activare_pct"]:
                stop_trailing = max_atins - tc_cfg["distanta_trailing_pct"]
                if stop_trailing > stop_efectiv:
                    stop_efectiv = stop_trailing
                    prag_atins = max_atins

            # Verifica iesire (stop loss sau trailing)
            iesire = pl_pct <= stop_efectiv
            if iesire:
                if piata_deschisa:
                    pret_p = float(p["current_price"])
                    limit_p = round(pret_p * (1 - limit_marja), 2)
                    trade.place_order(p["symbol"], p["qty"], "sell", limit_p)
                    salveaza_trade(p["symbol"], "SELL", p["qty"], pret_p, 0)
                    if prag_atins is not None:
                        motiv = f"TRAILING STOP (iesit la +{pl_pct:.1f}%, max atins +{prag_atins:.1f}%)"
                    else:
                        motiv = f"STOP LOSS ({pl_pct:.1f}%)"
                    inchideri.append(f"{p['symbol']} — {motiv}")
                    print(f"  🔴 INCHIS {p['symbol']}: {motiv}")
                else:
                    print(f"  {p['symbol']} sub stop efectiv ({stop_efectiv:.0f}%) — astept deschiderea")
            elif prag_atins is not None:
                print(f"  🛡️  {p['symbol']} +{pl_pct:.1f}% (max +{prag_atins:.1f}%) — stop trailing la +{stop_efectiv:.1f}%")
        except Exception as e:
            print(f"  Eroare verificare {p.get('symbol')}: {e}")

    # ── Regim piata + intrari ──
    prag = r_regime["prag_bearish_pct"] / 100
    piata_in_scadere = (r_regime["stai_deoparte_daca_bearish_majoritate"]
                        and valide and len(bearish) > len(valide) * prag)

    trade_uri = []
    selectii = []
    detinute = [p["symbol"] for p in pozitii]

    if piata_in_scadere:
        print(f"\n⚠️  Piata in scadere ({len(bearish)} bearish din {len(valide)}) — STAU DEOPARTE")
    elif doar_management:
        print("\n🔧 Mod management — fara intrari noi")
    elif not piata_deschisa:
        sectoare_det = {}
        for p in pozitii:
            sec = SECTOARE.get(p["symbol"], "altul")
            sectoare_det[sec] = sectoare_det.get(sec, 0) + 1
        locuri_libere = max(0, max_pozitii - len(pozitii))
        if locuri_libere > 0:
            selectii = selecteaza_diversificat(bullish, detinute, locuri_libere, max_sector, sectoare_det)
        print("\n🌙 Piata inchisa — analiza pregatita, fara ordine")
        if selectii:
            print(f"  La deschidere as cumpara: {', '.join(s['symbol'] for s in selectii)}")
    else:
        locuri_libere = max(0, max_pozitii - len(pozitii))
        if locuri_libere == 0:
            print(f"\n📊 Ai deja {len(pozitii)}/{max_pozitii} pozitii — nu mai cumpar (portofoliu plin)")
            selectii = []
        else:
            sectoare_det = {}
            for p in pozitii:
                sec = SECTOARE.get(p["symbol"], "altul")
                sectoare_det[sec] = sectoare_det.get(sec, 0) + 1
            print(f"\nCaut intrari (max {locuri_libere} locuri libere, max {max_sector}/sector)...")
            selectii = selecteaza_diversificat(bullish, detinute, locuri_libere, max_sector, sectoare_det)
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

    # Stiri Nivel 1 pentru selectie
    stiri_selectie = {}
    if selectii:
        print("\n📰 Iau stiri pentru selectie...")
        for a in selectii:
            titluri = ia_stiri(a["symbol"])
            stiri_selectie[a["symbol"]] = titluri
            if titluri:
                print(f"  {a['symbol']}: {titluri[0][:60]}")

    jurnal = genereaza_jurnal(zi, cash, valoare_totala, pozitii, valide,
                              bullish, bearish, trade_uri, inchideri,
                              piata_in_scadere, piata_deschisa, selectii, reguli, stiri_selectie)
    scrie_jurnal(jurnal)


def genereaza_jurnal(zi, cash, valoare, pozitii, valide, bullish, bearish,
                     trade_uri, inchideri, scadere, piata_deschisa, selectii, reguli, stiri_selectie=None):
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

    if stiri_selectie and any(stiri_selectie.values()):
        linii.append("## Stiri Relevante (selectie)")
        for simbol, titluri in stiri_selectie.items():
            if titluri:
                linii.append(f"**{simbol}:**")
                for t in titluri:
                    linii.append(f"- {t}")
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

    linii.append("## Pozitii Inchise / Modificate")
    linii.append("\n".join(f"- {i}" for i in inchideri) if inchideri else "Niciuna azi.")
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
    import sys
    mod_mgmt = "--management" in sys.argv
    ruleaza(doar_management=mod_mgmt)
