# BLACKBOX_OPS — trading/order_manager.py
# =========================================
# Semi-automatic order placement via Schwab trading API.
# Builds an order from a Signal, shows a full preview, then
# requires explicit y/n confirmation before placing.
#
# REQUIRED ENV VARS:
#   SCHWAB_CLIENT_ID, SCHWAB_CLIENT_SECRET  (used by auth module)
#   SCHWAB_ACCOUNT_ID                        (your Schwab account hash)

from __future__ import annotations
import logging
import os

import requests

from auth.auth import get_headers
from scanner.models import Signal

TRADING_BASE = "https://api.schwabapi.com/trader/v1"

log = logging.getLogger("order")


# ── Public interface ──────────────────────────────────────────────────────────

def preview_and_confirm(signal: Signal) -> bool:
    """Build order from signal, print preview, prompt for confirmation."""
    order = build_order(signal)
    if not order:
        print(f"  [order] Cannot build order for strategy: {signal.strategy}")
        return False

    print_preview(signal, order)
    try:
        answer = input("  Place this order? [y/N]: ").strip().lower()
    except (KeyboardInterrupt, EOFError):
        print("\n  Order cancelled.")
        return False

    if answer == "y":
        return place_order(order)
    print("  Order declined.")
    return False


def build_order(signal: Signal) -> dict | None:
    """Construct a Schwab order payload from a Signal."""
    c        = signal.contract
    strategy = signal.strategy

    if strategy in ("LONG_CALL", "LONG_PUT", "FOLLOW_UNUSUAL"):
        return _single_leg_order(c.symbol, "BUY_TO_OPEN", c.mid)
    if strategy in ("CALL_CREDIT_SPREAD", "PUT_CREDIT_SPREAD"):
        return _vertical_spread_order(c, strategy)
    if strategy == "IRON_CONDOR":
        return _iron_condor_order(c)
    return None


def print_preview(signal: Signal, order: dict) -> None:
    c    = signal.contract
    legs = order.get("orderLegCollection", [])

    print("\n" + "─" * 60)
    print(f"  ORDER PREVIEW  —  {signal.strategy}  ({signal.signal_type})")
    print("─" * 60)
    print(f"  Symbol:     {c.underlying}")
    print(f"  Contract:   {c.symbol}")
    print(f"  Strike:     ${c.strike:.0f}  {c.option_type}  Exp: {c.expiration}  DTE: {c.dte}")
    print(f"  Mid price:  ${c.mid:.2f}  (limit order)")
    print(f"  Delta:      {c.delta:.2f}  |  IV Rank: {c.iv_rank:.0f}  |  Score: {signal.score}/100")
    print(f"  Notes:      {signal.notes}")
    print()

    for i, leg in enumerate(legs, 1):
        instr = leg.get("instrument", {})
        print(f"  Leg {i}: {leg['instruction']:<14}  {instr.get('symbol', '?'):<25}  qty: {leg.get('quantity', 1)}")

    price      = order.get("price")
    order_type = order.get("orderType", "LIMIT")
    print()
    print(f"  Order type: {order_type}  |  Price: ${price:.2f}  |  TIF: {order.get('duration', 'DAY')}")

    if signal.strategy in ("LONG_CALL", "LONG_PUT", "FOLLOW_UNUSUAL"):
        print(f"  Max loss:   ${c.mid * 100:.0f}  (1 contract × 100 shares)")
    elif "SPREAD" in signal.strategy:
        print(f"  Max loss:   Defined (spread width - credit received)")
    print("─" * 60)


def place_order(order: dict) -> bool:
    """Submit the order to Schwab."""
    account_id             = _require_env("SCHWAB_ACCOUNT_ID")
    headers                = get_headers()
    headers["Content-Type"] = "application/json"

    try:
        resp = requests.post(
            f"{TRADING_BASE}/accounts/{account_id}/orders",
            headers=headers,
            json=order,
            timeout=15,
        )
        if resp.status_code == 201:
            order_id = resp.headers.get("Location", "").split("/")[-1]
            print(f"\n  Order placed. Order ID: {order_id}\n")
            log.info(f"Order placed: {order_id}")
            return True
        print(f"\n  Order failed: {resp.status_code} — {resp.text[:300]}\n")
        log.error(f"Order placement failed: {resp.status_code} {resp.text[:300]}")
        return False
    except Exception as e:
        print(f"\n  Order error: {e}\n")
        log.error(f"Order placement error: {e}")
        return False


def get_account_id() -> str | None:
    """Fetch the linked Schwab account hash (use for initial setup)."""
    headers = get_headers()
    try:
        resp = requests.get(f"{TRADING_BASE}/accounts", headers=headers, timeout=10)
        resp.raise_for_status()
        accounts = resp.json()
        if accounts:
            return accounts[0].get("securitiesAccount", {}).get("accountNumber")
    except Exception as e:
        log.error(f"Account fetch failed: {e}")
    return None


# ── Order builders ────────────────────────────────────────────────────────────

def _single_leg_order(symbol: str, instruction: str, limit_price: float) -> dict:
    return {
        "orderType":          "LIMIT",
        "session":            "NORMAL",
        "duration":           "DAY",
        "price":              round(limit_price, 2),
        "orderStrategyType":  "SINGLE",
        "orderLegCollection": [{
            "instruction": instruction,
            "quantity":    1,
            "instrument":  {"symbol": symbol, "assetType": "OPTION"},
        }],
    }


def _vertical_spread_order(contract, strategy: str) -> dict:
    direction  = "CALL" if "CALL" in strategy else "PUT"
    net_credit = round(contract.mid * 0.5, 2)
    return {
        "orderType":          "NET_CREDIT",
        "session":            "NORMAL",
        "duration":           "DAY",
        "price":              net_credit,
        "orderStrategyType":  "SINGLE",
        "orderLegCollection": [
            {"instruction": "SELL_TO_OPEN", "quantity": 1,
             "instrument":  {"symbol": contract.symbol, "assetType": "OPTION"}},
            {"instruction": "BUY_TO_OPEN",  "quantity": 1,
             "instrument":  {"symbol": f"[{direction}_LONG_LEG_SYMBOL]", "assetType": "OPTION"}},
        ],
        "_note": "Verify long leg symbol from chain before placing",
    }


def _iron_condor_order(contract) -> dict:
    return {
        "orderType":          "NET_CREDIT",
        "session":            "NORMAL",
        "duration":           "DAY",
        "price":              round(contract.mid * 0.4, 2),
        "orderStrategyType":  "SINGLE",
        "orderLegCollection": [
            {"instruction": "SELL_TO_OPEN", "quantity": 1,
             "instrument": {"symbol": "[CALL_SHORT_STRIKE]", "assetType": "OPTION"}},
            {"instruction": "BUY_TO_OPEN",  "quantity": 1,
             "instrument": {"symbol": "[CALL_LONG_STRIKE]",  "assetType": "OPTION"}},
            {"instruction": "SELL_TO_OPEN", "quantity": 1,
             "instrument": {"symbol": "[PUT_SHORT_STRIKE]",  "assetType": "OPTION"}},
            {"instruction": "BUY_TO_OPEN",  "quantity": 1,
             "instrument": {"symbol": "[PUT_LONG_STRIKE]",   "assetType": "OPTION"}},
        ],
        "_note": "Iron condor — populate all four leg symbols from chain before placing",
    }


def _require_env(name: str) -> str:
    val = os.environ.get(name)
    if not val:
        raise EnvironmentError(f"Missing required environment variable: {name}")
    return val
