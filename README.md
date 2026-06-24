# Trading Agent V2

Agent de tranzactionare in Python pur, inspirat din arhitectura MindStudio + HumbledTrader.
Ruleaza pe Google Cloud VM. Cont paper Alpaca. Strategie: MA20/MA50 trend, LONG only,
cu selectie pe putere de semnal si diversificare pe sectoare.

## Structura

```
trading-agent-v2/
├── rules.json          # TOATE regulile strategiei (editezi aici, nu codul)
├── watchlist.json      # ~120 actiuni lichide
├── agent.py            # Scriptul principal (research → decizie → trade → jurnal)
├── compute_perf.py     # Calcul performanta R-multiple din trades.csv
├── dashboard.py        # Dashboard web Flask (port 8081)
├── trades.csv          # Istoric trade-uri (generat automat, pt R-multiple)
├── .env                # Chei API + config (APCA_*)
├── journal/            # Jurnale zilnice (YYYY-MM-DD.md)
└── scripts/
    ├── research.py     # Date yfinance (bulk) + cont/pozitii Alpaca
    └── trade.py        # Plaseaza ordine + validare risc
```

## Strategie (in rules.json)

- **Intrare**: pret > MA20 > MA50 (trend ascendent confirmat)
- **Selectie**: sortare dupa putere semnal (% peste MA50), max 2/sector, max 5 pozitii
- **Iesire**: stop loss 8%, sau inversare trend (MA20 < MA50)
- **Regim piata**: daca >50% din actiuni sunt bearish → STAU DEOPARTE
- **Risc**: max 5% per pozitie, 20% rezerva cash, 80% expunere maxima, limit orders

## Initializare pe VM

```bash
mkdir -p ~/trading-agent-v2/scripts ~/trading-agent-v2/journal
cd ~/trading-agent-v2
# Copiaza fisierele (vezi continutul din chat)

# .env cu chei (prefix APCA_, nu ALPACA_)
cat > .env << 'EOF'
APCA_API_KEY_ID=cheia_ta
APCA_API_SECRET_KEY=secretul_tau
APCA_BASE_URL=https://paper-api.alpaca.markets
PORTFOLIO_VALUE_USD=100000
EOF

# Dependinte
~/trading/venv/bin/pip install requests python-dotenv yfinance pandas flask

# Test
~/trading/venv/bin/python3 scripts/research.py account
~/trading/venv/bin/python3 agent.py
```

## Comenzi utile

```bash
# Ruleaza o sesiune completa
~/trading/venv/bin/python3 agent.py

# Vezi jurnalul de azi
cat ~/trading-agent-v2/journal/$(date +%Y-%m-%d).md

# Performanta R-multiple
~/trading/venv/bin/python3 compute_perf.py

# Analiza un simbol (test)
~/trading/venv/bin/python3 scripts/research.py analiza AAPL

# Status piata
~/trading/venv/bin/python3 scripts/trade.py status

# Pozitii deschise
~/trading/venv/bin/python3 scripts/research.py positions
```

## Cum schimbi strategia (rules.json)

Editezi `rules.json` fara sa atingi codul. Exemple:

| Vrei sa... | Schimbi in rules.json |
|---|---|
| Stop loss mai strans (6%) | `exit.stop_loss_pct: 6.0` |
| Max 3 actiuni per sector | `selection.max_per_sector: 3` |
| Mai multe pozitii (8) | `selection.max_pozitii_noi: 8` |
| Pozitii mai mari (8%) | `risk.max_pozitie_pct: 8.0` |
| Prag bearish mai sus (60%) | `market_regime.prag_bearish_pct: 60.0` |
| Doar semnale puternice (>5%) | `entry_filters.min_putere_pct: 5.0` |

Dupa orice modificare, ruleaza agent.py — citeste automat noile valori.

## R-Multiple (metrica de performanta)

R = cat ai castigat raportat la cat ai riscat pe acel trade.
- R = (pret_iesire - pret_intrare) / (pret_intrare - stop_price)
- +2R = ai castigat dublul riscului. -1R = ai pierdut exact cat riscai (stop loss).

**De ce conteaza**: R mediu pozitiv = strategia are edge real, independent de marimea pozitiilor.
R mediu negativ = pierzi pe termen lung, oricat de mare ar fi win rate-ul.

Dashboard-ul (port 8081) arata: suma R, R mediu/trade, win rate, best/worst, histograma R.

## Dashboard

```bash
# Manual
~/trading/venv/bin/python3 dashboard.py

# Sau ca serviciu
sudo systemctl restart dashboard-v2.service
```

Acceseaza: http://mini-trading.duckdns.org:8081
(necesita firewall TCP:8081 deschis in Google Cloud Console)

Contine: carduri portofoliu, performanta R-multiple + histograma, sentiment piata
(bullish/bearish/lateral din 120), pozitii deschise, selectie diversificata,
top candidati bullish, selector jurnale.

## Rulare automata (cron, 3x/zi ca in articol)

```cron
45 9 * * 1-5 cd /home/liviu_anton/trading-agent-v2 && /home/liviu_anton/trading/venv/bin/python3 agent.py >> /home/liviu_anton/trading-agent-v2/agent.log 2>&1
0 10 * * 1-5 cd /home/liviu_anton/trading-agent-v2 && /home/liviu_anton/trading/venv/bin/python3 agent.py >> /home/liviu_anton/trading-agent-v2/agent.log 2>&1
15 16 * * 1-5 cd /home/liviu_anton/trading-agent-v2 && /home/liviu_anton/trading/venv/bin/python3 agent.py >> /home/liviu_anton/trading-agent-v2/agent.log 2>&1
```

IMPORTANT: `cd` la inceput e esential (load_dotenv cauta .env in directorul curent).

## ATENTIE

- Acelasi cont Alpaca ca multi_tf → daca ruleaza ambele, pozitiile se amesteca.
  Pentru testare curata v2, opreste multi_tf: `sudo systemctl stop trading.service`
- LONG-only — NU profita din piata in scadere, doar sta deoparte
- Cont PAPER (bani virtuali) — nu trece la bani reali fara luni de validare
- yfinance poate da rate-limit; descarcarea in bloc (analizeaza_toate) minimizeaza riscul

## Istoric modificari

- v1: 5 actiuni, analiza individuala, jurnal simplu
- v2.1: watchlist 120 actiuni, descarcare in bloc (analizeaza_toate)
- v2.2: selectie pe putere semnal + diversificare pe sectoare (max 2/sector)
- v2.3: reguli centralizate in rules.json + R-multiple tracking (trades.csv + compute_perf.py + dashboard)
