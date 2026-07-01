# Trading Agent V2

Agent de tranzactionare in Python pur pe Google Cloud VM. Cont paper Alpaca.
Strategie: MA20/MA50 trend, LONG only, cu selectie pe putere de semnal,
diversificare pe sectoare, vanzare partiala si trailing stop continuu.

## Structura

```
trading-agent-v2/
├── rules.json          # TOATE regulile strategiei (editezi aici, nu codul)
├── watchlist.json      # ~120 actiuni lichide
├── agent.py            # Scriptul principal
├── compute_perf.py     # Calcul performanta R-multiple
├── dashboard.py        # Dashboard web Flask (port 8081)
├── reduce_pozitii.py   # Script de urgenta: reduce la max pozitii
├── trades.csv          # Istoric trade-uri (auto)
├── istoric_portofoliu.csv    # Valoare zilnica (auto, pt grafic)
├── vanzari_partiale.json     # Marcaje vanzari partiale (auto)
├── protectii_stop.json       # Maxime profit per pozitie, pt trailing (auto)
├── .env                # Chei API (APCA_*)
├── journal/            # Jurnale zilnice (YYYY-MM-DD.md)
└── scripts/
    ├── research.py     # Date yfinance (bulk + high real) + Alpaca
    └── trade.py        # Ordine + validare risc
```

## Strategie (in rules.json)

- **Intrare**: pret > MA20 > MA50, sortare dupa putere semnal (% peste MA50)
- **Selectie**: max 2/sector, max 5 pozitii TOTAL (tine cont de cele existente)
- **Iesire pe 2 nivele**:
  1. **Vanzare partiala**: la +10% profit, vinde jumatate (o data)
  2. **Trailing continuu**: stop = (max profit real atins) - 5%, urmareste high-ul real din yfinance
- **Stop loss baza**: -8% (cat nu s-a activat trailing-ul)
- **Regim piata**: daca >50% bearish → STAU DEOPARTE
- **Risc**: max 5%/pozitie, 20% rezerva cash, limit orders

## Cum schimbi strategia (rules.json)

| Vrei sa... | Schimbi in rules.json |
|---|---|
| Stop loss mai strans | exit.stop_loss_pct |
| Trailing mai larg (chips volatili) | exit.trailing_continuu.distanta_trailing_pct: 8.0 |
| Prag vanzare partiala | exit.profit_taking.vanzare_partiala.prag_profit_pct |
| Max actiuni/sector | selection.max_per_sector |
| Numar pozitii | selection.max_pozitii_noi |

## Cum functioneaza iesirile (exemplu MU)

1. MU urca la +10% → vinde jumatate (incasezi profit), marcheaza ca partiala
2. Restul: trailing la 5% sub max real. MU atinge +26% → stop la +21%
3. MU cade sub +21% → vinde restul, prinzi profitul aproape de varf

Trailing-ul foloseste HIGH-ul real din yfinance (nu doar profitul la momentul rularii),
deci prinde varfurile intraday chiar daca agentul n-a rulat fix atunci.

## Comenzi utile

```bash
~/trading/venv/bin/python3 agent.py                    # sesiune completa
~/trading/venv/bin/python3 agent.py --management        # doar management, fara intrari
~/trading/venv/bin/python3 compute_perf.py             # performanta R
~/trading/venv/bin/python3 reduce_pozitii.py           # reduce la max pozitii
cat journal/$(date +%Y-%m-%d).md                       # jurnal azi
```

## Dashboard (port 8081)

http://mini-trading.duckdns.org:8081

Contine: carduri portofoliu, grafic evolutie, R-multiple + histograma,
sentiment piata (bullish/bearish din 120), pozitii cu stop trailing vizibil,
distributie pe sectoare, tranzactii pe zi cu P&L, selector jurnale.

## Cron (2 rulari: 1 completa + management)

```cron
0 10 * * 1-5 cd ~/trading-agent-v2 && ~/trading/venv/bin/python3 agent.py >> agent.log 2>&1
0 13 * * 1-5 cd ~/trading-agent-v2 && ~/trading/venv/bin/python3 agent.py --management >> agent.log 2>&1
15 16 * * 1-5 cd ~/trading-agent-v2 && ~/trading/venv/bin/python3 agent.py --management >> agent.log 2>&1
```

## R-Multiple

R = (pret_iesire - pret_intrare) / (pret_intrare - stop_price)
R mediu pozitiv = strategia are edge. Ai nevoie de 20-30 trade-uri pentru relevanta.

## ATENTIE

- Acelasi cont Alpaca ca multi_tf → opreste multi_tf cand rulezi v2
- LONG-only, cont PAPER (bani virtuali)
- Trailing 5% poate fi strans pentru chips volatili — considera 7-8%

## Istoric versiuni

- v1: 5 actiuni
- v2.1: watchlist 120 + descarcare bulk
- v2.2: selectie pe putere + diversificare sectoare
- v2.3: rules.json + R-multiple
- v2.4: stiri Nivel 1 + dashboard imbunatatit
- v2.5: vanzare partiala la +10%
- v2.6: trailing continuu pe high real + fix bug 14 pozitii + fix afisare dashboard
