"""
BLACKBOX_OPS — backtest/engine.py
===================================
Paper trading P&L engine.

Reads data/paper_trades.json, marks open positions to market via
Schwab quotes API, applies exit rules, and prints a full P&L report.

EXIT RULES:
  LONG_CALL / LONG_PUT   → close at 2x gain, 50% loss, or DTE ≤ 5
  CALL/PUT_CREDIT_SPREAD → close at 50% max profit, or 2x max loss
  IRON_CONDOR            → close at 25% max profit, or 2x max loss

USAGE (from project root):
  python -m backtest.engine           # mark-to-market + report
  python -m backtest.engine --report  # report only (no API calls)
"""

from __future__ import annotations
import argparse
import json
import logging
import requests
from datetime import date, datetime
from pathlib import Path

from auth.auth import get_headers
from scanner import config as cfg

PAPER_TRADES_PATH = Path(cfg.SIGNALS_OUTPUT_PATH).parent / "paper_trades.json"
BASE_URL          = "https://api.schwabapi.com/marketdata/v1"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("backtest")


# ── Mark-to-market ────────────────────────────────────────────────────────────

def mark_to_market() -> None:
    """Fetch current prices for all open positions and update P&L."""
    trades      = _load()
    open_trades = [t for t in trades if t["status"] == "OPEN"]

    if not open_trades:
        log.info("No open paper trades to mark.")
        return

    symbols = [t["contract"]["symbol"] for t in open_trades]
    prices  = _fetch_option_prices(symbols)

    for trade in open_trades:
        sym = trade["contract"]["symbol"]
        if sym not in prices:
            continue

        current_price = prices[sym]
        entry_price   = trade["entry_price"]
        trade["current_price"] = current_price

        if entry_price > 0:
            trade["pnl_pct"] = round((current_price - entry_price) / entry_price * 100, 1)

        exit_reason = _check_exit(trade, current_price)
        if exit_reason:
            trade["status"]          = "CLOSED"
            trade["exit_price"]      = current_price
            trade["timestamp_close"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            trade["exit_reason"]     = exit_reason
            log.info(
                f"Closed {trade['id']} — {trade['underlying']} {trade['strategy']}  "
                f"reason: {exit_reason}  P&L: {trade['pnl_pct']:+.1f}%"
            )

    _save(trades)
    log.info(f"Marked {len(open_trades)} open position(s) to market.")


def _check_exit(trade: dict, current_price: float) -> str | None:
    pnl_pct  = trade.get("pnl_pct", 0.0)
    strategy = trade["strategy"]

    try:
        dte = (date.fromisoformat(trade["contract"].get("expiration", "")) - date.today()).days
        if dte <= 5:
            return "DTE ≤ 5 — approaching expiration"
    except ValueError:
        pass

    if strategy in ("LONG_CALL", "LONG_PUT", "FOLLOW_UNUSUAL"):
        if pnl_pct >= 100:  return "2x gain target hit"
        if pnl_pct <= -50:  return "50% loss stop hit"
    elif "SPREAD" in strategy:
        if pnl_pct >= 50:   return "50% of max profit target hit"
        if pnl_pct <= -200: return "2x max loss stop hit"
    elif strategy == "IRON_CONDOR":
        if pnl_pct >= 25:   return "25% of max profit target hit"
        if pnl_pct <= -200: return "2x max loss stop hit"

    return None


def _fetch_option_prices(symbols: list[str]) -> dict[str, float]:
    headers = get_headers()
    prices  = {}
    for i in range(0, len(symbols), 50):
        chunk = symbols[i:i + 50]
        try:
            resp = requests.get(
                f"{BASE_URL}/quotes",
                headers=headers,
                params={"symbols": ",".join(chunk), "fields": "quote"},
                timeout=12,
            )
            resp.raise_for_status()
            for sym in chunk:
                q   = resp.json().get(sym, {}).get("quote", {})
                bid = q.get("bidPrice", 0) or 0
                ask = q.get("askPrice", 0) or 0
                if bid and ask:
                    prices[sym] = round((bid + ask) / 2, 2)
        except Exception as e:
            log.warning(f"Price fetch failed: {e}")
    return prices


# ── Report ────────────────────────────────────────────────────────────────────

def report() -> None:
    trades = _load()
    if not trades:
        print("No paper trades found. Run scanner with --paper to start tracking.")
        return

    open_t   = [t for t in trades if t["status"] == "OPEN"]
    closed_t = [t for t in trades if t["status"] == "CLOSED"]

    print("\n" + "═" * 72)
    print(f"  BLACKBOX_OPS — PAPER TRADING REPORT  ({len(open_t)} open, {len(closed_t)} closed)")
    print("═" * 72)

    if open_t:
        print(f"\n  OPEN POSITIONS ({len(open_t)})\n")
        print(f"  {'ID':<8} {'Symbol':<7} {'Strategy':<22} {'Entry':>7} {'Current':>8} {'P&L%':>7}")
        print("  " + "─" * 60)
        for t in sorted(open_t, key=lambda x: x.get("pnl_pct", 0), reverse=True):
            print(
                f"  {t['id']:<8} {t['underlying']:<7} {t['strategy']:<22} "
                f"${t['entry_price']:>6.2f}  ${t['current_price']:>6.2f}  "
                f"{t.get('pnl_pct', 0):>+6.1f}%"
            )

    if closed_t:
        wins     = [t for t in closed_t if t.get("pnl_pct", 0) > 0]
        losses   = [t for t in closed_t if t.get("pnl_pct", 0) <= 0]
        avg_win  = sum(t["pnl_pct"] for t in wins)   / len(wins)   if wins   else 0.0
        avg_loss = sum(t["pnl_pct"] for t in losses) / len(losses) if losses else 0.0
        win_rate = len(wins) / len(closed_t) * 100

        print(f"\n  CLOSED POSITIONS ({len(closed_t)})\n")
        print(f"  {'ID':<8} {'Symbol':<7} {'Strategy':<22} {'Entry':>7} {'Exit':>7} {'P&L%':>7}  Reason")
        print("  " + "─" * 72)
        for t in sorted(closed_t, key=lambda x: x.get("timestamp_close", ""), reverse=True):
            print(
                f"  {t['id']:<8} {t['underlying']:<7} {t['strategy']:<22} "
                f"${t['entry_price']:>6.2f}  ${t.get('exit_price', 0):>6.2f}  "
                f"{t.get('pnl_pct', 0):>+6.1f}%  {t.get('exit_reason', '')}"
            )

        print(f"\n  Win rate: {win_rate:.0f}%  ({len(wins)}W / {len(losses)}L)")
        print(f"  Avg win:  {avg_win:+.1f}%   Avg loss: {avg_loss:+.1f}%")

        strategies = {}
        for t in closed_t:
            strategies.setdefault(t["strategy"], []).append(t.get("pnl_pct", 0))
        print(f"\n  BY STRATEGY:")
        for s, pnls in sorted(strategies.items()):
            avg = sum(pnls) / len(pnls)
            print(f"    {s:<25}  {len(pnls):>3} trades  avg P&L: {avg:+.1f}%")

    print("\n" + "═" * 72 + "\n")


# ── Storage ───────────────────────────────────────────────────────────────────

def _load() -> list:
    if PAPER_TRADES_PATH.exists():
        try:
            return json.loads(PAPER_TRADES_PATH.read_text())
        except Exception:
            return []
    return []


def _save(trades: list) -> None:
    PAPER_TRADES_PATH.parent.mkdir(parents=True, exist_ok=True)
    PAPER_TRADES_PATH.write_text(json.dumps(trades, indent=2))


# ── Entry Point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="BLACKBOX_OPS Paper Trading Engine")
    ap.add_argument("--report", action="store_true", help="Print P&L report only (no API calls)")
    args = ap.parse_args()

    if not args.report:
        mark_to_market()
    report()
