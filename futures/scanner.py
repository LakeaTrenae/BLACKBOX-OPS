"""
BLACKBOX_OPS — futures/scanner.py
===================================
Futures scanner orchestrator.

USAGE (from project root):
  python -m futures.scanner              # run once
  python -m futures.scanner --loop      # run every 5 min
  python -m futures.scanner --symbols /ES /NQ --loop
"""

from __future__ import annotations
import argparse
import json
import logging
import time
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from futures import config as cfg
from futures.client import fetch_futures_quotes
from futures.signals import generate_signals
from futures.models import FuturesSignal

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
log = logging.getLogger("futures")

# ── Scanner ───────────────────────────────────────────────────────────────────

def run_scan(watchlist: list[str] | None = None) -> list[FuturesSignal]:
    """Fetch and score all futures in the watchlist."""
    symbols = watchlist or cfg.WATCHLIST
    log.info(f"Futures scan — {len(symbols)} contracts")

    quotes  = fetch_futures_quotes(symbols)
    signals = generate_signals(quotes)

    log.info(f"  {len(quotes)} quotes → {len(signals)} signals")
    _print_summary(signals)
    _save_signals(signals)
    return signals


def _print_summary(signals: list[FuturesSignal]) -> None:
    if not signals:
        log.info("No futures signals this scan.")
        return

    print("\n" + "═" * 70)
    print(f"  FUTURES SCAN — {datetime.now().strftime('%H:%M:%S')}  |  {len(signals)} signal(s)")
    print("═" * 70)
    for s in signals[:cfg.TOP_N]:
        q     = s.quote
        arrow = "▲" if s.signal_type == "BULLISH" else ("▼" if s.signal_type == "BEARISH" else "◆")
        print(
            f"  {arrow} {s.symbol:<6}  {q.last:>10.2f}  "
            f"Chg: {q.change_pct:+.2f}%  "
            f"Vol: {q.volume:>8,}  Score: {s.score}"
        )
        print(f"         {s.notes}")
        print()
    print("═" * 70 + "\n")


def _save_signals(signals: list[FuturesSignal]) -> None:
    out = Path(cfg.SIGNALS_OUTPUT_PATH)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps([{**asdict(s), "quote": asdict(s.quote)} for s in signals], indent=2))
    log.info(f"Saved {len(signals)} futures signals → {out}")


# ── Entry Point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="BLACKBOX_OPS Futures Scanner")
    parser.add_argument("--loop",    action="store_true", help="Run every 5 minutes")
    parser.add_argument("--symbols", nargs="+",           help="Override futures watchlist")
    args = parser.parse_args()

    watchlist = [s.upper() for s in args.symbols] if args.symbols else None
    interval  = cfg.SCAN_INTERVAL_MINUTES * 60

    if args.loop:
        log.info(f"Futures scanner loop — interval: {cfg.SCAN_INTERVAL_MINUTES} min")
        while True:
            run_scan(watchlist)
            log.info(f"Next futures scan in {cfg.SCAN_INTERVAL_MINUTES} minutes …")
            time.sleep(interval)
    else:
        run_scan(watchlist)
