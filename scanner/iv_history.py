# BLACKBOX_OPS — scanner/iv_history.py
# =======================================
# Rolling IV history tracker for true IV Rank calculation.
#
# IV Rank = (current_iv - 52w_low_iv) / (52w_high_iv - 52w_low_iv) * 100
#
# Appends {date, symbol, iv} to data/iv_history.json each scan.
# Rank becomes meaningful after 30+ days of data; falls back to 50.0 before that.

import json
import logging
from datetime import date, timedelta
from pathlib import Path

from scanner import config as cfg

HISTORY_PATH      = Path(cfg.SIGNALS_OUTPUT_PATH).parent / "iv_history.json"
MIN_DAYS_FOR_RANK = 30
HISTORY_WINDOW    = 365   # days to retain

log = logging.getLogger("scanner")


def record_iv(symbol: str, iv: float) -> None:
    """Append today's IV reading. Prunes entries older than 1 year."""
    history = _load()
    today   = date.today().isoformat()
    cutoff  = (date.today() - timedelta(days=HISTORY_WINDOW)).isoformat()

    entries = history.get(symbol, [])
    for entry in entries:
        if entry["date"] == today:
            entry["iv"] = iv
            break
    else:
        entries.append({"date": today, "iv": iv})

    history[symbol] = [e for e in entries if e["date"] >= cutoff]
    _save(history)


def get_iv_rank(symbol: str, current_iv: float) -> float:
    """Return IV rank (0–100). Falls back to 50.0 if insufficient history."""
    history = _load()
    entries = history.get(symbol, [])

    if len(entries) < MIN_DAYS_FOR_RANK:
        log.debug(f"IV rank {symbol}: {len(entries)} days (need {MIN_DAYS_FOR_RANK}) — using 50.0")
        return 50.0

    ivs     = [e["iv"] for e in entries if e["iv"] > 0]
    low_iv  = min(ivs)
    high_iv = max(ivs)

    if not ivs or high_iv == low_iv:
        return 50.0

    rank = ((current_iv - low_iv) / (high_iv - low_iv)) * 100
    return round(max(0.0, min(100.0, rank)), 1)


def _load() -> dict:
    if HISTORY_PATH.exists():
        try:
            return json.loads(HISTORY_PATH.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _save(history: dict) -> None:
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    HISTORY_PATH.write_text(json.dumps(history, indent=2))
