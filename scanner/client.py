# BLACKBOX_OPS — scanner/client.py
# ==================================
# Schwab API calls: option chain and IV rank fetches.

from __future__ import annotations
import logging
import requests
from datetime import date, timedelta

from auth.auth import get_headers
from scanner import config as cfg
from scanner import iv_history

BASE_URL = "https://api.schwabapi.com/marketdata/v1"

log = logging.getLogger("scanner")


def fetch_option_chain(symbol: str) -> dict | None:
    """Pull full option chain for a symbol from the Schwab API."""
    headers = get_headers()
    today   = date.today()
    to_date = today + timedelta(days=cfg.DTE_MAX)

    params = {
        "symbol":                 symbol,
        "contractType":           "ALL",
        "includeUnderlyingQuote": "true",
        "fromDate":               today.isoformat(),
        "toDate":                 to_date.isoformat(),
    }

    try:
        resp = requests.get(f"{BASE_URL}/chains", headers=headers, params=params, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except requests.HTTPError as e:
        log.error(f"Chain fetch failed for {symbol}: {e} — {resp.text[:200]}")
        return None
    except Exception as e:
        log.error(f"Unexpected error fetching {symbol}: {e}")
        return None


def fetch_iv_rank(symbol: str, chain_data: dict | None = None) -> float:
    """
    Return true IV rank (0–100) using rolling historical IV.
    Extracts current ATM IV from the already-fetched chain when possible.
    Records the reading for future rank calculations.
    """
    current_iv = _extract_atm_iv(chain_data) if chain_data else _fetch_quote_iv(symbol)
    if current_iv and current_iv > 0:
        iv_history.record_iv(symbol, current_iv)
        return iv_history.get_iv_rank(symbol, current_iv)
    return 50.0


def _extract_atm_iv(chain_data: dict) -> float | None:
    """Pull ATM call IV directly from the option chain response."""
    underlying_price = chain_data.get("underlyingPrice", 0)
    if not underlying_price:
        return None

    best_iv   = None
    best_diff = float("inf")

    for _, strikes in chain_data.get("callExpDateMap", {}).items():
        for strike_str, option_list in strikes.items():
            diff = abs(float(strike_str) - underlying_price)
            if diff < best_diff and option_list:
                iv = (option_list[0].get("volatility") or 0) / 100
                if iv > 0:
                    best_diff = diff
                    best_iv   = iv

    return best_iv


def _fetch_quote_iv(symbol: str) -> float | None:
    """Fallback: fetch current IV from the quotes endpoint."""
    headers = get_headers()
    try:
        resp = requests.get(
            f"{BASE_URL}/quotes",
            headers=headers,
            params={"symbols": symbol, "fields": "quote"},
            timeout=8,
        )
        resp.raise_for_status()
        raw = resp.json().get(symbol, {}).get("quote", {}).get("volatility", 0) or 0
        return round(raw / 100, 4) if raw > 0 else None
    except Exception as e:
        log.warning(f"Quote IV fetch failed for {symbol}: {e}")
        return None
