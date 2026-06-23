# Trading Agent V2

Agent de tranzactionare inspirat din arhitectura MindStudio (Claude Code + Alpaca),
implementat in Python pur. Ruleaza pe acelasi VM ca agentul anterior.

## Structura

```
trading-agent-v2/
├── CLAUDE.md           # Instructiunile / regulile agentului
├── watchlist.json      # Actiunile + limite de alocare
├── agent.py            # Scriptul principal (research → decizie → trade → jurnal)
├── .env.example        # Template configurare (copiaza in .env)
├── journal/            # Jurnale zilnice (YYYY-MM-DD.md)
└── scripts/
    ├── research.py     # Citeste date Alpaca (bars, news, account)
    └── trade.py        # Plaseaza ordine + validare risc
```

## Initializare pe VM

```bash
# 1. Creeaza directorul
mkdir -p ~/trading-agent-v2/scripts ~/trading-agent-v2/journal
cd ~/trading-agent-v2

# 2. Copiaza toate fisierele (vezi continutul din chat)

# 3. Creeaza .env din template si completeaza cheile
cp .env.example .env
nano .env

# 4. Foloseste acelasi venv ca agentul anterior, sau creeaza unul nou
# (are nevoie de: requests, python-dotenv)
~/trading/venv/bin/pip install requests python-dotenv

# 5. Test research (verifica conexiunea Alpaca)
~/trading/venv/bin/python3 scripts/research.py account

# 6. Test analiza un simbol
~/trading/venv/bin/python3 scripts/research.py analiza AAPL

# 7. Verifica statusul pietei
~/trading/venv/bin/python3 scripts/trade.py status

# 8. Ruleaza o sesiune completa
~/trading/venv/bin/python3 agent.py
```

## Diferente fata de articol

- **Python pur** in loc de Claude Code (zero costuri tokens, ruleaza pe VM)
- Acelasi sistem de jurnal structurat
- Aceleasi reguli de risc (5% pozitie, 8% stop loss, 20% cash, 80% expunere max)
- Limit orders, nu market orders
- LONG-only (ca in articol)

## Reguli de risc (3 straturi)

1. **CLAUDE.md** — reguli in limbaj natural
2. **trade.py validate_order()** — verificare la nivel de cod inainte de plasare
3. **Alpaca** — protectii built-in (buying power, day-trade)

## Rulare programata (cron)

Pentru a rula automat ca in articol (3 sesiuni pe zi), adauga in crontab:

```cron
# Research + trade la 10:00 ET
0 10 * * 1-5 /home/liviu_anton/trading/venv/bin/python3 /home/liviu_anton/trading-agent-v2/agent.py >> /home/liviu_anton/trading-agent-v2/agent.log 2>&1
```

## ATENTIE

- Articolul (si acest agent) e LONG-only — NU profita din piata in scadere, doar sta deoparte
- Pentru profit din scadere ai nevoie de SHORT selling (risc nelimitat) — nerecomandat la inceput
- Ruleaza pe cont PAPER. Nu trece la bani reali fara luni de validare
- Daca rulezi simultan cu multi_tf pe acelasi cont Alpaca, pozitiile se vor AMESTECA
