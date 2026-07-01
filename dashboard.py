from flask import Flask, render_template_string, request
import os
import sys
import glob
import re
import csv
import json
import requests
from datetime import datetime
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import compute_perf

load_dotenv()

ALPACA_KEY = os.getenv("APCA_API_KEY_ID")
ALPACA_SECRET = os.getenv("APCA_API_SECRET_KEY")
BASE_URL = os.getenv("APCA_BASE_URL")
HEADERS = {"APCA-API-KEY-ID": ALPACA_KEY, "APCA-API-SECRET-KEY": ALPACA_SECRET}

app = Flask(__name__)
FOLDER = "/home/liviu_anton/trading-agent-v2"
JOURNAL_DIR = os.path.join(FOLDER, "journal")
RULES_FILE = os.path.join(FOLDER, "rules.json")
ISTORIC_FILE = os.path.join(FOLDER, "istoric_portofoliu.csv")
TRADES_CSV = os.path.join(FOLDER, "trades.csv")

SECTOARE = {
    "AAPL": "tech", "MSFT": "tech", "GOOGL": "tech", "AMZN": "tech", "META": "tech",
    "NVDA": "semi", "TSLA": "auto", "AVGO": "semi", "ORCL": "software", "CRM": "software",
    "AMD": "semi", "INTC": "semi", "QCOM": "semi", "TXN": "semi", "MU": "semi",
    "AMAT": "semi", "ADI": "semi", "LRCX": "semi", "KLAC": "semi", "MRVL": "semi",
    "ADBE": "software", "NOW": "software", "INTU": "software", "PANW": "software",
    "SNOW": "software", "CRWD": "software", "DDOG": "software", "NET": "software",
    "ZS": "software", "PLTR": "software", "NFLX": "media", "DIS": "media",
    "JPM": "financiar", "BAC": "financiar", "WFC": "financiar", "GS": "financiar",
    "MS": "financiar", "C": "financiar", "V": "financiar", "MA": "financiar",
    "MRNA": "biotech", "BNTX": "biotech", "VRTX": "biotech", "REGN": "biotech",
    "GILD": "biotech", "BIIB": "biotech", "COIN": "crypto", "MARA": "crypto",
    "RIOT": "crypto", "SOFI": "fintech", "AFRM": "fintech", "HOOD": "fintech",
    "GE": "industrial", "CAT": "industrial", "RTX": "industrial",
    "SPY": "etf", "QQQ": "etf", "IWM": "etf", "DIA": "etf",
}


def get_account():
    try:
        return requests.get(f"{BASE_URL}/v2/account", headers=HEADERS, timeout=10).json()
    except:
        return {}


def get_positions():
    try:
        d = requests.get(f"{BASE_URL}/v2/positions", headers=HEADERS, timeout=10).json()
        return d if isinstance(d, list) else []
    except:
        return []


def get_clock():
    try:
        return requests.get(f"{BASE_URL}/v2/clock", headers=HEADERS, timeout=10).json()
    except:
        return {"is_open": False}


def incarca_reguli():
    try:
        with open(RULES_FILE) as f:
            return json.load(f)
    except:
        return {}


def stop_efectiv_pct(pl_pct, stop_loss_pct, pt_cfg, simbol=None, maxime=None):
    """Calculeaza stop-ul efectiv folosind trailing continuu (max real - distanta)."""
    stop = -stop_loss_pct
    prag = None
    try:
        with open(RULES_FILE) as f:
            reg = json.load(f)
        tc = reg["exit"].get("trailing_continuu", {})
    except Exception:
        tc = {}
    if tc.get("activ") and simbol and maxime:
        max_atins = maxime.get(simbol, pl_pct)
        if max_atins >= tc.get("prag_activare_pct", 5):
            stop_trailing = max_atins - tc.get("distanta_trailing_pct", 5)
            if stop_trailing > stop:
                stop = stop_trailing
                prag = max_atins
    return stop, prag


def incarca_istoric():
    if not os.path.exists(ISTORIC_FILE):
        return []
    randuri = []
    with open(ISTORIC_FILE, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            try:
                randuri.append({"zi": row["zi"], "valoare": float(row["valoare"])})
            except:
                pass
    return randuri


def tranzactii_zi(zi):
    """Citeste tranzactiile dintr-o zi, cu P&L atasat la vanzari."""
    if not zi or not os.path.exists(TRADES_CSV):
        return []

    # Calculeaza P&L per vanzare (FIFO) din tot istoricul
    pnl_per_vanzare = {}  # (symbol, exit_price_rotunjit) -> {pnl, pct}
    try:
        rez = compute_perf.calculeaza_R()
        for pereche in rez.get("perechi", []):
            cheie = (pereche["symbol"], round(pereche["exit"], 2))
            pct = (pereche["exit"] / pereche["entry"] - 1) * 100 if pereche["entry"] else 0
            pnl_per_vanzare[cheie] = {"pnl": pereche["pnl"], "pct": pct, "R": pereche["R"]}
    except Exception:
        pass

    tranzactii = []
    try:
        with open(TRADES_CSV, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                ts = row.get("timestamp", "")
                if ts[:10] == zi:
                    side = row.get("side", "")
                    symbol = row.get("symbol", "")
                    pret = row.get("entry_price", "")
                    pnl_info = None
                    if side == "SELL":
                        try:
                            cheie = (symbol, round(float(pret), 2))
                            pnl_info = pnl_per_vanzare.get(cheie)
                        except Exception:
                            pnl_info = None
                    tranzactii.append({
                        "ora": ts[11:19] if len(ts) >= 19 else "",
                        "symbol": symbol,
                        "side": side,
                        "qty": row.get("qty", ""),
                        "pret": pret,
                        "sector": row.get("sector", ""),
                        "pnl": pnl_info["pnl"] if pnl_info else None,
                        "pct": pnl_info["pct"] if pnl_info else None,
                        "R": pnl_info["R"] if pnl_info else None,
                    })
    except Exception:
        return []
    return tranzactii


def lista_jurnale():
    fisiere = sorted(glob.glob(os.path.join(JOURNAL_DIR, "*.md")), reverse=True)
    return [os.path.basename(f).replace(".md", "") for f in fisiere]


def citeste_jurnal(zi):
    cale = os.path.join(JOURNAL_DIR, f"{zi}.md")
    if os.path.exists(cale):
        with open(cale, encoding="utf-8") as f:
            return f.read()
    return None


def parse_rezumat(continut):
    if not continut:
        return None
    m = re.search(r"Bullish: (\d+) \| Bearish: (\d+) \| Lateral: (\d+)", continut)
    if m:
        return {"bullish": int(m.group(1)), "bearish": int(m.group(2)), "lateral": int(m.group(3))}
    return None


def parse_selectie(continut):
    if not continut:
        return []
    sectiune = re.search(r"## Selectie Diversificata.*?\n(.*?)(?=\n## )", continut, re.DOTALL)
    if not sectiune:
        return []
    selectii = []
    for l in sectiune.group(1).strip().split("\n"):
        m = re.match(r"- (\w+) \((\w+)\) — \+([\d.]+)%", l)
        if m:
            selectii.append({"symbol": m.group(1), "sector": m.group(2), "putere": float(m.group(3))})
    return selectii


def sparkline_points(istoric, w=600, h=120):
    if len(istoric) < 2:
        return None
    valori = [x["valoare"] for x in istoric]
    vmin, vmax = min(valori), max(valori)
    span = vmax - vmin if vmax > vmin else 1
    pad = 10
    n = len(valori)
    pts = []
    for i, v in enumerate(valori):
        x = pad + i * (w - 2 * pad) / (n - 1)
        y = h - pad - (v - vmin) / span * (h - 2 * pad)
        pts.append(f"{x:.1f},{y:.1f}")
    return {"points": " ".join(pts), "vmin": vmin, "vmax": vmax,
            "prima": valori[0], "ultima": valori[-1], "w": w, "h": h,
            "zile": [x["zi"][5:] for x in istoric]}


HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Trading Agent V2</title>
    <meta http-equiv="refresh" content="120">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: #0f1419; color: #e6edf3; padding: 20px; min-height: 100vh; }
        .container { max-width: 1200px; margin: 0 auto; }
        h1 { color: #58a6ff; margin-bottom: 5px; font-size: 28px; }
        .subtitle { color: #8b949e; font-size: 14px; margin-bottom: 20px; }
        h2 { color: #58a6ff; margin: 25px 0 15px; font-size: 20px; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px; margin-bottom: 25px; }
        .card { background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 18px; }
        .card h3 { color: #8b949e; font-size: 11px; text-transform: uppercase;
            margin-bottom: 8px; letter-spacing: 1px; }
        .card .value { font-size: 22px; font-weight: bold; }
        .green { color: #3fb950; } .red { color: #f85149; } .yellow { color: #d29922; }
        .gray { color: #8b949e; } .blue { color: #58a6ff; }
        table { width: 100%; border-collapse: collapse; background: #161b22;
            border-radius: 8px; overflow: hidden; margin-bottom: 25px; }
        th, td { padding: 10px 14px; text-align: left; border-bottom: 1px solid #30363d; }
        th { background: #21262d; color: #8b949e; font-size: 12px; text-transform: uppercase; }
        tr:last-child td { border-bottom: none; }
        .badge { display: inline-block; padding: 3px 10px; border-radius: 4px;
            font-size: 11px; font-weight: bold; background: #21262d; color: #8b949e; }
        .badge-protejat { background: #1a3a1f; color: #3fb950; }
        .badge-risc { background: #3a2a1a; color: #d29922; }
        .status-dot { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 6px; }
        .status-online { background: #3fb950; } .status-offline { background: #f85149; }
        .sentiment { display: flex; gap: 4px; height: 30px; border-radius: 6px; overflow: hidden; margin-bottom: 8px; }
        .sent-bull { background: #3fb950; } .sent-bear { background: #f85149; } .sent-lat { background: #30363d; }
        .sector-row { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }
        .sector-label { width: 90px; font-size: 13px; color: #c9d1d9; }
        .sector-bar { height: 24px; border-radius: 4px; background: #58a6ff; min-width: 4px;
            display: flex; align-items: center; padding-left: 8px; font-size: 12px; font-weight: bold; color: #0f1419; }
        .timestamp { text-align: right; color: #8b949e; font-size: 12px; margin-top: 20px; }
        .jurnal-box { background: #0d1117; border: 1px solid #30363d; border-radius: 8px; padding: 20px; }
        .jurnal-select { background: #21262d; color: #e6edf3; border: 1px solid #30363d;
            border-radius: 6px; padding: 8px 12px; font-size: 14px; margin-bottom: 15px; }
        .jurnal-content { white-space: pre-wrap; font-family: 'Courier New', monospace;
            font-size: 13px; line-height: 1.6; color: #c9d1d9; }
        .chart-box { background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 20px; margin-bottom: 25px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🤖 Trading Agent V2</h1>
        <div class="subtitle">MA20/MA50 · putere semnal · diversificare · R-multiple · profit-taking</div>

        <div class="grid">
            <div class="card"><h3>Cash</h3><div class="value">${{ "%.0f"|format(cash) }}</div></div>
            <div class="card"><h3>Portofoliu</h3><div class="value">${{ "%.0f"|format(portofoliu) }}</div></div>
            <div class="card"><h3>P&L Total</h3>
                <div class="value {{ 'green' if pl_total >= 0 else 'red' }}">${{ "%.2f"|format(pl_total) }}</div></div>
            <div class="card"><h3>Pozitii</h3><div class="value">{{ pozitii|length }}</div></div>
            <div class="card"><h3>Bursa</h3>
                <div class="value">
                    <span class="status-dot {{ 'status-online' if bursa_deschisa else 'status-offline' }}"></span>
                    {{ 'OPEN' if bursa_deschisa else 'CLOSED' }}</div></div>
        </div>

        {% if spark %}
        <h2>📈 Evolutie Portofoliu ({{ spark.zile|length }} zile)</h2>
        <div class="chart-box">
            <svg viewBox="0 0 {{ spark.w }} {{ spark.h }}" style="width:100%;height:160px;">
                <polyline points="{{ spark.points }}" fill="none"
                    stroke="{{ '#3fb950' if spark.ultima >= spark.prima else '#f85149' }}" stroke-width="2"/>
            </svg>
            <div style="display:flex;justify-content:space-between;color:#8b949e;font-size:12px;margin-top:8px;">
                <span>{{ spark.zile[0] }}: ${{ "%.0f"|format(spark.prima) }}</span>
                <span class="{{ 'green' if spark.ultima >= spark.prima else 'red' }}">
                    {{ spark.zile[-1] }}: ${{ "%.0f"|format(spark.ultima) }}
                    ({{ "%+.2f"|format((spark.ultima/spark.prima - 1)*100) }}%)</span>
            </div>
        </div>
        {% endif %}

        {% if perf and perf.total > 0 %}
        <h2>📊 Performanta R-Multiple ({{ perf.total }} trade-uri inchise)</h2>
        <div class="grid">
            <div class="card"><h3>Suma R</h3>
                <div class="value {{ 'green' if perf.suma_R >= 0 else 'red' }}">{{ "%+.2f"|format(perf.suma_R) }}R</div></div>
            <div class="card"><h3>R Mediu/trade</h3>
                <div class="value {{ 'green' if perf.avg_R >= 0 else 'red' }}">{{ "%+.2f"|format(perf.avg_R) }}R</div></div>
            <div class="card"><h3>Win Rate</h3>
                <div class="value {{ 'green' if perf.win_rate >= 50 else 'yellow' }}">{{ perf.win_rate }}%</div></div>
            <div class="card"><h3>P&L ($)</h3>
                <div class="value {{ 'green' if perf.suma_pnl >= 0 else 'red' }}">${{ "%.2f"|format(perf.suma_pnl) }}</div></div>
        </div>
        {% endif %}

        {% if rezumat %}
        <h2>🌡️ Sentiment Piata ({{ rezumat.bullish + rezumat.bearish + rezumat.lateral }} actiuni)</h2>
        {% set total = rezumat.bullish + rezumat.bearish + rezumat.lateral %}
        <div class="sentiment">
            <div class="sent-bull" style="width: {{ rezumat.bullish / total * 100 }}%"></div>
            <div class="sent-lat" style="width: {{ rezumat.lateral / total * 100 }}%"></div>
            <div class="sent-bear" style="width: {{ rezumat.bearish / total * 100 }}%"></div>
        </div>
        <div class="subtitle">
            <span class="green">● {{ rezumat.bullish }} bullish</span> &nbsp;
            <span class="gray">● {{ rezumat.lateral }} lateral</span> &nbsp;
            <span class="red">● {{ rezumat.bearish }} bearish</span>
        </div>
        {% endif %}

        <h2>📂 Pozitii Deschise ({{ pozitii|length }})</h2>
        {% if pozitii|length == 0 %}
        <div class="card" style="text-align:center;color:#8b949e;">Nicio pozitie deschisa</div>
        {% else %}
        <table>
            <thead><tr><th>Simbol</th><th>Sector</th><th>Cant.</th><th>Intrare</th><th>Curent</th><th>P&L %</th><th>Protectie Stop</th></tr></thead>
            <tbody>
                {% for p in pozitii %}
                <tr>
                    <td><strong>{{ p.symbol }}</strong></td>
                    <td><span class="badge">{{ p.sector }}</span></td>
                    <td>{{ p.qty }}</td>
                    <td>${{ "%.2f"|format(p.avg_entry_price) }}</td>
                    <td>${{ "%.2f"|format(p.current_price) }}</td>
                    <td class="{{ 'green' if p.pl_pct >= 0 else 'red' }}">{{ "%+.1f"|format(p.pl_pct) }}%</td>
                    <td>
                        {% if p.prag %}
                        <span class="badge badge-protejat">🛡️ stop la {{ "%.0f"|format(p.stop_efectiv) }}% (prag +{{ "%.0f"|format(p.prag) }}%)</span>
                        {% else %}
                        <span class="badge badge-risc">stop la {{ "%.0f"|format(p.stop_efectiv) }}%</span>
                        {% endif %}
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        {% endif %}

        {% if sectoare %}
        <h2>🥧 Distributie pe Sectoare</h2>
        <div class="card">
            {% set maxval = sectoare.values()|map(attribute='valoare')|max %}
            {% for sector, d in sectoare.items() %}
            <div class="sector-row">
                <span class="sector-label">{{ sector }}</span>
                <div class="sector-bar" style="width: {{ (d.valoare / maxval * 400) if maxval > 0 else 4 }}px;">
                    ${{ "%.0f"|format(d.valoare) }}
                </div>
                <span class="gray" style="font-size:12px;">{{ d.count }} poz.</span>
            </div>
            {% endfor %}
        </div>
        {% endif %}

        {% if selectie %}
        <h2>🎯 Ultima Selectie Diversificata</h2>
        <table>
            <thead><tr><th>Simbol</th><th>Sector</th><th>Putere</th></tr></thead>
            <tbody>
                {% for s in selectie %}
                <tr><td><strong>{{ s.symbol }}</strong></td>
                    <td><span class="badge">{{ s.sector }}</span></td>
                    <td class="green">+{{ "%.1f"|format(s.putere) }}%</td></tr>
                {% endfor %}
            </tbody>
        </table>
        {% endif %}

        {% if tranzactii %}
        <h2>💱 Tranzactii in {{ zi_curenta }} ({{ tranzactii|length }})</h2>
        <table>
            <thead><tr><th>Ora</th><th>Actiune</th><th>Simbol</th><th>Sector</th><th>Cant.</th><th>Pret</th><th>P&L</th></tr></thead>
            <tbody>
                {% for t in tranzactii %}
                <tr>
                    <td class="gray">{{ t.ora }}</td>
                    <td>
                        {% if t.side == 'BUY' %}
                        <span class="badge" style="background:#1a3a1f;color:#3fb950;">▲ BUY</span>
                        {% else %}
                        <span class="badge" style="background:#3a1a1a;color:#f85149;">▼ SELL</span>
                        {% endif %}
                    </td>
                    <td><strong>{{ t.symbol }}</strong></td>
                    <td><span class="badge">{{ t.sector }}</span></td>
                    <td>{{ t.qty }}</td>
                    <td>${{ t.pret }}</td>
                    <td>
                        {% if t.pnl is not none %}
                        <span class="{{ 'green' if t.pnl >= 0 else 'red' }}">
                            ${{ "%.2f"|format(t.pnl) }} ({{ "%+.1f"|format(t.pct) }}%)
                            {% if t.R is not none %}<span class="gray" style="font-size:11px;"> {{ "%+.2f"|format(t.R) }}R</span>{% endif %}
                        </span>
                        {% else %}
                        <span class="gray">—</span>
                        {% endif %}
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        {% else %}
        {% if zi_curenta %}
        <h2>💱 Tranzactii in {{ zi_curenta }}</h2>
        <div class="card" style="text-align:center;color:#8b949e;">Nicio tranzactie in aceasta zi</div>
        {% endif %}
        {% endif %}

        <h2>📓 Jurnale</h2>
        <div class="jurnal-box">
            <select class="jurnal-select" onchange="window.location.href='/?zi=' + this.value">
                {% for z in zile %}
                <option value="{{ z }}" {{ 'selected' if z == zi_curenta else '' }}>{{ z }}</option>
                {% endfor %}
            </select>
            <div class="jurnal-content">{{ jurnal_continut }}</div>
        </div>

        <div class="timestamp">Actualizat: {{ now }} | Auto-refresh: 120s | Port 8081</div>
    </div>
</body>
</html>
"""


@app.route("/")
def dashboard():
    account = get_account()
    cash = float(account.get("cash", 0))
    portofoliu = float(account.get("portfolio_value", 0))
    pl_total = portofoliu - 100000

    try:
        bursa_deschisa = get_clock().get("is_open", False)
    except:
        bursa_deschisa = False

    reguli = incarca_reguli()
    stop_loss_pct = reguli.get("exit", {}).get("stop_loss_pct", 8)
    pt_cfg = reguli.get("exit", {}).get("profit_taking", {"activ": False})
    maxime_stop = {}
    try:
        cale_prot = os.path.join(FOLDER, "protectii_stop.json")
        if os.path.exists(cale_prot):
            with open(cale_prot) as f:
                maxime_stop = json.load(f)
    except Exception:
        maxime_stop = {}

    pozitii = []
    sectoare = {}
    for p in get_positions():
        try:
            pl_pct = float(p["unrealized_plpc"]) * 100
            stop_ef, prag = stop_efectiv_pct(pl_pct, stop_loss_pct, pt_cfg, p["symbol"], maxime_stop)
            sector = SECTOARE.get(p["symbol"], "altul")
            mv = float(p["market_value"])
            pozitii.append({
                "symbol": p["symbol"], "sector": sector, "qty": int(p["qty"]),
                "avg_entry_price": float(p["avg_entry_price"]),
                "current_price": float(p["current_price"]),
                "pl_pct": pl_pct, "stop_efectiv": stop_ef, "prag": prag,
            })
            sectoare.setdefault(sector, {"valoare": 0, "count": 0})
            sectoare[sector]["valoare"] += mv
            sectoare[sector]["count"] += 1
        except:
            pass
    sectoare = dict(sorted(sectoare.items(), key=lambda x: x[1]["valoare"], reverse=True))

    zile = lista_jurnale()
    zi_curenta = request.args.get("zi", zile[0] if zile else None)
    jurnal_continut = citeste_jurnal(zi_curenta) if zi_curenta else "Niciun jurnal."
    tranzactii = tranzactii_zi(zi_curenta)

    ultim = citeste_jurnal(zile[0]) if zile else None
    rezumat = parse_rezumat(ultim)
    selectie = parse_selectie(ultim)

    try:
        perf = compute_perf.calculeaza_R()
    except:
        perf = None

    spark = sparkline_points(incarca_istoric())

    return render_template_string(
        HTML, cash=cash, portofoliu=portofoliu, pl_total=pl_total,
        pozitii=pozitii, sectoare=sectoare, bursa_deschisa=bursa_deschisa,
        rezumat=rezumat, selectie=selectie, perf=perf, spark=spark,
        zile=zile, zi_curenta=zi_curenta, jurnal_continut=jurnal_continut, tranzactii=tranzactii,
        now=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8081)
