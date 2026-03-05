# BLACKBOX_OPS — futures/client.py
# ==================================
# Schwab API calls for futures quotes.

from __future__ import annotations
import json
import logging
import requests
from pathlib import Path

from auth.auth import get_headers
from futures import config as cfg
from futures.models import FuturesQuote

BASE_URL = "https://api.schwabapi.com/marketdata/v1"

log = logging.getLogger("futures")


def fetch_futures_quotes(symbols: list[str]) -> list[FuturesQuote]:
    """Fetch real-time quotes for a list of futures symbols."""
    headers = get_headers()

    try:
        resp = requests.get(
            f"{BASE_URL}/quotes",
            headers=headers,
            params={"symbols": ",".join(symbols), "fields": "quote,reference"},
            timeout=12,
        )
        resp.raise_for_status()
        raw = resp.json()
    except requests.HTTPError as e:
        log.error(f"Futures quote fetch failed: {e}")
        return []
    except Exception as e:
        log.error(f"Unexpected error fetching futures quotes: {e}")
        return []

    vol_history = _load_vol_history()
    quotes = []

    for sym in symbols:
        data = raw.get(sym)
        if not data:
            log.debug(f"No data returned for {sym}")
            continue

        q      = data.get("quote", {})
        ref    = data.get("reference", {})
        volume = int(q.get("totalVolume", 0) or 0)
        avg_vol = _update_vol_history(vol_history, sym, volume)

        session_raw = q.get("tradingHours", "") or ""
        if "REGULAR" in session_raw.upper():
            session = "NORMAL"
        elif "EXTENDED" in session_raw.upper():
            session = "EXTENDED"
        else:
            session = "OVERNIGHT"

        quotes.append(FuturesQuote(
            symbol=sym,
            description=ref.get("description", sym),
            last=float(q.get("lastPrice", 0) or 0),
            bid=float(q.get("bidPrice", 0) or 0),
            ask=float(q.get("askPrice", 0) or 0),
            volume=volume,
            open_interest=int(q.get("openInterest", 0) or 0),
            change=float(q.get("netChange", 0) or 0),
            change_pct=float(q.get("netPercentChange", 0) or 0),
            high=float(q.get("highPrice", 0) or 0),
            low=float(q.get("lowPrice", 0) or 0),
            open=float(q.get("openPrice", 0) or 0),
            prev_close=float(q.get("closePrice", 0) or 0),
            session=session,
            vol_avg_5d=avg_vol,
        ))

    _save_vol_history(vol_history)
    return quotes


def _load_vol_history() -> dict:
    path = Path(cfg.VOL_HISTORY_PATH)
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            pass
    return {}


def _save_vol_history(history: dict) -> None:
    path = Path(cfg.VOL_HISTORY_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(history, indent=2))


def _update_vol_history(history: dict, symbol: str, current_volume: int) -> float:
    """Maintain a rolling 5-reading volume window. Returns current average."""
    readings = history.get(symbol, [])
    readings.append(current_volume)
    readings = readings[-5:]
    history[symbol] = readings
    return sum(readings) / len(readings) if readings else float(current_volume)
