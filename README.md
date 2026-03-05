# BLACKBOX_OPS

Automated options and futures scanner with signal generation, alerts, paper trading, and order placement via the Schwab API.

## Project Structure

```
BLACKBOX-OPS/
├── auth/               Schwab OAuth2 token manager
├── scanner/            Options chain scanner
│   ├── config.py       All tunable thresholds
│   ├── models.py       OptionContract + Signal dataclasses
│   ├── market_hours.py Market hours check
│   ├── client.py       Schwab API calls (chain + IV rank)
│   ├── iv_history.py   Rolling IV history for true IV Rank
│   ├── parser.py       Chain JSON → OptionContract objects
│   ├── filters.py      Quality filter engine
│   ├── signals.py      Signal generator + scoring
│   ├── output.py       JSON save + terminal summary
│   └── scanner.py      Orchestrator (entry point)
├── futures/            Futures scanner
│   ├── config.py
│   ├── models.py       FuturesQuote + FuturesSignal
│   ├── client.py       Schwab quotes API
│   ├── signals.py      Momentum + volume scoring
│   └── scanner.py      Orchestrator (entry point)
├── alerts/
│   └── engine.py       Desktop / SMS / Email / Discord alerts
├── trading/
│   └── order_manager.py  Semi-auto order placement
├── backtest/
│   ├── data_collector.py Paper trade logger
│   └── engine.py         Mark-to-market + P&L report
├── data/               Runtime output (gitignored)
├── .env                Credentials (gitignored)
├── requirements.txt
└── pyrightconfig.json
```

## Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Create .env with your Schwab credentials
cp .env.example .env   # then fill in your values

# 3. Authorize (opens browser for Schwab OAuth login)
python -m auth.auth
```

## Usage

```bash
# Options scanner — run once
python -m scanner.scanner

# Options scanner — loop every 5 min
python -m scanner.scanner --loop

# Scan specific symbols
python -m scanner.scanner --symbols NVDA TSLA --loop

# Log signals as paper trades
python -m scanner.scanner --paper --loop

# Prompt to place top signal as a real order
python -m scanner.scanner --execute

# Futures scanner
python -m futures.scanner --loop

# Alert engine (watches signals, fires desktop/SMS/Discord)
python -m alerts.engine

# Paper trading P&L report
python -m backtest.engine --report

# Mark-to-market + report
python -m backtest.engine
```

## Configuration

Edit `scanner/config.py` to tune options thresholds.
Edit `futures/config.py` to tune futures thresholds.

| Filter           | Default     |
|------------------|-------------|
| IV Rank          | ≥ 30        |
| Delta            | 0.20 – 0.55 |
| DTE              | 7 – 60 days |
| Open Interest    | ≥ 100       |
| Volume           | ≥ 50        |
| Bid/Ask Spread   | ≤ 15%       |
| Unusual Activity | Vol/OI ≥ 3x |

## Environment Variables

| Variable              | Required | Description                        |
|-----------------------|----------|------------------------------------|
| SCHWAB_CLIENT_ID      | Yes      | App Key from developer.schwab.com  |
| SCHWAB_CLIENT_SECRET  | Yes      | App Secret                         |
| SCHWAB_REDIRECT_URI   | Yes      | Registered redirect (127.0.0.1)    |
| SCHWAB_ACCOUNT_ID     | Trading  | Account hash for order placement   |
| TWILIO_SID            | Optional | SMS alerts via Twilio              |
| TWILIO_TOKEN          | Optional |                                    |
| TWILIO_FROM           | Optional |                                    |
| TWILIO_TO             | Optional |                                    |
| DISCORD_WEBHOOK_URL   | Optional | Discord channel alerts             |
| ALERT_EMAIL_FROM      | Optional | Email alerts (Gmail SMTP)          |
| ALERT_EMAIL_TO        | Optional |                                    |
| ALERT_SMTP_PASSWORD   | Optional |                                    |
