"""
BLACKBOX_OPS — scanner/scanner.py
===================================
Options scanner orchestrator. Runs the full pipeline every 5 minutes
during market hours.

USAGE (from project root):
  python -m scanner.scanner               # run once
  python -m scanner.scanner --loop        # run every 5 min
  python -m scanner.scanner --symbols NVDA TSLA --loop
  python -m scanner.scanner --iv-min 50
  python -m scanner.scanner --execute     # prompt to place top signal as order
  python -m scanner.scanner --paper       # log signals to paper_trades.json
"""

import argparse
import logging
import time

from scanner import config as cfg
from scanner.market_hours import is_market_open
from scanner.client import fetch_option_chain, fetch_iv_rank
from scanner.parser import parse_contracts
from scanner.filters import apply_filters
from scanner.signals import generate_signals
from scanner.output import print_summary, save_signals

# ── Logging ───────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(cfg.LOG_PATH),
    ],
)
log = logging.getLogger("scanner")

# ── Scanner ───────────────────────────────────────────────────────────────────

def run_scan(execute: bool = False, paper: bool = False) -> list:
    """Execute one full scan across the watchlist."""
    if not is_market_open():
        log.info("Market closed — skipping scan.")
        return []

    log.info(f"Starting scan — {len(cfg.WATCHLIST)} symbols")
    all_signals = []

    for symbol in cfg.WATCHLIST:
        log.info(f"  Scanning {symbol} …")
        chain = fetch_option_chain(symbol)
        if not chain:
            continue

        iv_rank   = fetch_iv_rank(symbol, chain)
        contracts = parse_contracts(chain, iv_rank)
        filtered  = apply_filters(contracts)
        signals   = generate_signals(filtered)

        log.info(
            f"  {symbol}: {len(contracts)} contracts → "
            f"{len(filtered)} passed filters → {len(signals)} signals"
        )
        all_signals.extend(signals)

    all_signals.sort(key=lambda s: s.score, reverse=True)
    print_summary(all_signals)
    save_signals(all_signals)

    if paper and all_signals:
        from backtest.data_collector import log_paper_trades
        log_paper_trades(all_signals)

    if execute and all_signals:
        from trading.order_manager import preview_and_confirm
        preview_and_confirm(all_signals[0])

    return all_signals


# ── Entry Point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="BLACKBOX_OPS Options Scanner")
    parser.add_argument("--loop",    action="store_true", help="Run every 5 minutes")
    parser.add_argument("--symbols", nargs="+",           help="Override watchlist symbols")
    parser.add_argument("--iv-min",  type=float,          help="Override IV rank minimum")
    parser.add_argument("--execute", action="store_true", help="Prompt to place top signal as order")
    parser.add_argument("--paper",   action="store_true", help="Log signals to paper_trades.json")
    args = parser.parse_args()

    if args.symbols:
        cfg.WATCHLIST[:] = [s.upper() for s in args.symbols]
    if args.iv_min is not None:
        cfg.IV_RANK_MIN = args.iv_min

    interval = cfg.SCAN_INTERVAL_MINUTES * 60

    if args.loop:
        log.info(f"Scanner loop started — interval: {cfg.SCAN_INTERVAL_MINUTES} min")
        while True:
            run_scan(execute=args.execute, paper=args.paper)
            log.info(f"Next scan in {cfg.SCAN_INTERVAL_MINUTES} minutes …")
            time.sleep(interval)
    else:
        run_scan(execute=args.execute, paper=args.paper)
