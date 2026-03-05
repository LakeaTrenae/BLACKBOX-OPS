# BLACKBOX_OPS — backtest/data_collector.py
# ===========================================
# Paper trade logger. Activated via --paper flag on scanner.
# Appends new signals as open paper positions to data/paper_trades.json.

import json
import logging
import uuid
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from scanner import config as cfg
from scanner.models import Signal

PAPER_TRADES_PATH = Path(cfg.SIGNALS_OUTPUT_PATH).parent / "paper_trades.json"

log = logging.getLogger("backtest")


def log_paper_trades(signals: list[Signal]) -> None:
    """Add new signals as open paper trades. Skips duplicates."""
    trades   = _load()
    open_keys = {
        f"{t['underlying']}|{t['strategy']}|{t['contract']['expiration']}"
        for t in trades if t["status"] == "OPEN"
    }

    added = 0
    now   = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for s in signals:
        key = f"{s.underlying}|{s.strategy}|{s.contract.expiration}"
        if key in open_keys:
            continue

        trades.append({
            "id":              str(uuid.uuid4())[:8],
            "timestamp_open":  now,
            "underlying":      s.underlying,
            "strategy":        s.strategy,
            "signal_type":     s.signal_type,
            "score":           s.score,
            "entry_price":     s.contract.mid,
            "current_price":   s.contract.mid,
            "pnl_pct":         0.0,
            "status":          "OPEN",
            "exit_price":      None,
            "timestamp_close": None,
            "exit_reason":     None,
            "contract":        asdict(s.contract),
        })
        open_keys.add(key)
        added += 1

    _save(trades)
    if added:
        log.info(f"Paper trades: logged {added} new position(s) → {PAPER_TRADES_PATH}")


def _load() -> list:
    if PAPER_TRADES_PATH.exists():
        try:
            return json.loads(PAPER_TRADES_PATH.read_text())
        except Exception:
            pass
    return []


def _save(trades: list) -> None:
    PAPER_TRADES_PATH.parent.mkdir(parents=True, exist_ok=True)
    PAPER_TRADES_PATH.write_text(json.dumps(trades, indent=2))
