from flask import Flask, render_template_string, request
import os
import sys
import glob
import re
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


def parse_candidati(continut):
    if not continut:
        return []
    rezultat = []
    randuri = re.findall(
        r"\| (\w+) \| (\w+) \| \$([\d.]+) \| \$([\d.]+) \| \+([\d.]+)% \|", continut)
    for simbol, sector, pret, ma50, putere in randuri:
        rezultat.append({"symbol": simbol, "sector": sector,
                         "pret": float(pret), "ma50": float(ma50), "putere": float(putere)})
    return rezultat


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
        .badge-sel { background: #1a3a1f; color: #3fb950; }
        .bar-bg { background: #21262d; border-radius: 4px; height: 8px; width: 100px; display: inline-block; vertical-align: middle; }
        .bar-fill { background: #3fb950; height: 8px; border-radius: 4px; }
        .status-dot { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 6px; }
        .status-online { background: #3fb950; } .status-offline { background: #f85149; }
        .sentiment { display: flex; gap: 4px; height: 30px; border-radius: 6px; overflow: hidden; margin-bottom: 8px; }
        .sent-bull { background: #3fb950; } .sent-bear { background: #f85149; } .sent-lat { background: #30363d; }
        .hist-row { display: flex; align-items: center; gap: 10px; margin-bottom: 6px; }
        .hist-label { width: 70px; font-size: 12px; color: #8b949e; font-family: monospace; }
        .hist-bar { height: 22px; border-radius: 4px; min-width: 2px; }
        .hist-count { font-size: 12px; color: #c9d1d9; }
        .timestamp { text-align: right; color: #8b949e; font-size: 12px; margin-top: 20px; }
        .jurnal-box { background: #0d1117; border: 1px solid #30363d; border-radius: 8px; padding: 20px; }
        .jurnal-select { background: #21262d; color: #e6edf3; border: 1px solid #30363d;
            border-radius: 6px; padding: 8px 12px; font-size: 14px; margin-bottom: 15px; }
        .jurnal-content { white-space: pre-wrap; font-family: 'Courier New', monospace;
            font-size: 13px; line-height: 1.6; color: #c9d1d9; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🤖 Trading Agent V2</h1>
        <div class="subtitle">MA20/MA50 · putere semnal · diversificare · R-multiple · LONG only</div>

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
            <div class="card"><h3>Best / Worst</h3>
                <div class="value" style="font-size:15px;">
                    <span class="green">{{ perf.best.symbol }} {{ "%+.1f"|format(perf.best.R) }}R</span><br>
                    <span class="red">{{ perf.worst.symbol }} {{ "%+.1f"|format(perf.worst.R) }}R</span></div></div>
        </div>

        <h2>📈 Distributie R-Multiple</h2>
        <div class="card">
            {% set maxc = perf.histograma.values()|max %}
            {% for label, count in perf.histograma.items() %}
            <div class="hist-row">
                <span class="hist-label">{{ label }}</span>
                <div class="hist-bar" style="width: {{ (count / maxc * 400) if maxc > 0 else 2 }}px;
                    background: {{ '#3fb950' if '..' in label and not label.startswith('-') and label != '-1..0R' else '#f85149' if label.startswith('<') or label.startswith('-') else '#3fb950' }};"></div>
                <span class="hist-count">{{ count }}</span>
            </div>
            {% endfor %}
        </div>
        {% elif perf %}
        <h2>📊 Performanta R-Multiple</h2>
        <div class="card" style="text-align:center;color:#8b949e;">
            {{ perf.mesaj if perf.mesaj else "Niciun trade inchis inca" }}
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
            <thead><tr><th>Simbol</th><th>Cant.</th><th>Intrare</th><th>Curent</th><th>P&L</th><th>P&L %</th></tr></thead>
            <tbody>
                {% for p in pozitii %}
                <tr>
                    <td><strong>{{ p.symbol }}</strong></td>
                    <td>{{ p.qty }}</td>
                    <td>${{ "%.2f"|format(p.avg_entry_price) }}</td>
                    <td>${{ "%.2f"|format(p.current_price) }}</td>
                    <td class="{{ 'green' if p.unrealized_pl >= 0 else 'red' }}">${{ "%.2f"|format(p.unrealized_pl) }}</td>
                    <td class="{{ 'green' if p.unrealized_plpc >= 0 else 'red' }}">{{ "%+.2f"|format(p.unrealized_plpc * 100) }}%</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        {% endif %}

        {% if selectie %}
        <h2>🎯 Selectie Diversificata (max 2/sector)</h2>
        <table>
            <thead><tr><th>Simbol</th><th>Sector</th><th>Putere (% peste MA50)</th></tr></thead>
            <tbody>
                {% for s in selectie %}
                <tr>
                    <td><strong>{{ s.symbol }}</strong> <span class="badge badge-sel">ALES</span></td>
                    <td><span class="badge">{{ s.sector }}</span></td>
                    <td class="green">+{{ "%.1f"|format(s.putere) }}%</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        {% endif %}

        {% if candidati %}
        <h2>📈 Top Candidati Bullish (dupa putere semnal)</h2>
        <table>
            <thead><tr><th>Simbol</th><th>Sector</th><th>Pret</th><th>Putere</th><th></th></tr></thead>
            <tbody>
                {% for c in candidati %}
                <tr>
                    <td><strong>{{ c.symbol }}</strong></td>
                    <td><span class="badge">{{ c.sector }}</span></td>
                    <td>${{ "%.2f"|format(c.pret) }}</td>
                    <td class="green">+{{ "%.1f"|format(c.putere) }}%</td>
                    <td><span class="bar-bg"><span class="bar-fill" style="width: {{ [c.putere * 2, 100]|min }}px"></span></span></td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
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

    pozitii = []
    for p in get_positions():
        try:
            pozitii.append({
                "symbol": p["symbol"], "qty": int(p["qty"]),
                "avg_entry_price": float(p["avg_entry_price"]),
                "current_price": float(p["current_price"]),
                "unrealized_pl": float(p["unrealized_pl"]),
                "unrealized_plpc": float(p["unrealized_plpc"]),
            })
        except:
            pass

    zile = lista_jurnale()
    zi_curenta = request.args.get("zi", zile[0] if zile else None)
    jurnal_continut = citeste_jurnal(zi_curenta) if zi_curenta else "Niciun jurnal."

    ultim = citeste_jurnal(zile[0]) if zile else None
    rezumat = parse_rezumat(ultim)
    candidati = parse_candidati(ultim)
    selectie = parse_selectie(ultim)

    try:
        perf = compute_perf.calculeaza_R()
    except Exception:
        perf = None

    return render_template_string(
        HTML, cash=cash, portofoliu=portofoliu, pl_total=pl_total,
        pozitii=pozitii, bursa_deschisa=bursa_deschisa,
        rezumat=rezumat, candidati=candidati, selectie=selectie, perf=perf,
        zile=zile, zi_curenta=zi_curenta, jurnal_continut=jurnal_continut,
        now=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8081)
