# BLACKBOX_OPS — scanner/signals.py
# ====================================
# Signal generator: scores filtered contracts and emits ranked signals.

from datetime import datetime

from scanner import config as cfg
from scanner.models import OptionContract, Signal


def generate_signals(contracts: list[OptionContract]) -> list[Signal]:
    """Convert filtered contracts into actionable trading signals."""
    signals = []
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for c in contracts:
        score, strategy, signal_type, notes = _score_contract(c)
        if score < cfg.MIN_SIGNAL_SCORE:
            continue
        signals.append(Signal(
            timestamp=now,
            underlying=c.underlying,
            signal_type=signal_type,
            strategy=strategy,
            contract=c,
            score=score,
            notes=notes,
        ))

    signals.sort(key=lambda s: s.score, reverse=True)
    return signals


def _score_contract(c: OptionContract) -> tuple[int, str, str, str]:
    """Score 0–100. Returns (score, strategy, signal_type, notes)."""
    score = 0
    notes_parts = []

    # IV Rank (0–30 pts)
    if c.iv_rank >= 70:
        score += 30; notes_parts.append(f"IV Rank {c.iv_rank:.0f} — premium rich")
    elif c.iv_rank >= 50:
        score += 20; notes_parts.append(f"IV Rank {c.iv_rank:.0f} — elevated")
    elif c.iv_rank >= 30:
        score += 10; notes_parts.append(f"IV Rank {c.iv_rank:.0f} — moderate")

    # Delta sweet spot (0–20 pts)
    if 0.35 <= c.delta <= 0.45:
        score += 20; notes_parts.append("Delta in ideal ATM range")
    elif 0.25 <= c.delta < 0.35 or 0.45 < c.delta <= 0.55:
        score += 12

    # DTE 21–45 (0–20 pts)
    if 21 <= c.dte <= 45:
        score += 20; notes_parts.append(f"{c.dte} DTE — theta decay sweet spot")
    elif c.dte < 21:
        score += 8

    # Liquidity (0–15 pts)
    if c.open_interest >= 1000 and c.volume >= 200:
        score += 15; notes_parts.append("High OI + volume")
    elif c.open_interest >= 500:
        score += 8

    # Spread tightness (0–10 pts)
    if c.spread_pct <= 0.05:
        score += 10; notes_parts.append("Tight spread — easy fill")
    elif c.spread_pct <= 0.10:
        score += 5

    # Unusual activity bonus (0–5 pts)
    if "UNUSUAL_ACTIVITY" in c.tags:
        score += 5; notes_parts.append(f"Unusual activity (vol/OI {c.vol_oi_ratio:.1f}x)")

    # Strategy + direction
    if c.iv_rank >= 50 and 21 <= c.dte <= 45:
        if c.delta <= cfg.DELTA_NEUTRAL:
            strategy, signal_type = "IRON_CONDOR", "NEUTRAL"
        elif c.option_type == "CALL":
            strategy    = "LONG_CALL" if c.iv_rank < 60 else "CALL_CREDIT_SPREAD"
            signal_type = "BULLISH"
        else:
            strategy    = "LONG_PUT" if c.iv_rank < 60 else "PUT_CREDIT_SPREAD"
            signal_type = "BEARISH"
    elif "UNUSUAL_ACTIVITY" in c.tags:
        strategy    = "FOLLOW_UNUSUAL"
        signal_type = "BULLISH" if c.option_type == "CALL" else "BEARISH"
        notes_parts.append("Smart money flow detected")
    else:
        strategy    = "LONG_CALL" if c.option_type == "CALL" else "LONG_PUT"
        signal_type = "BULLISH"   if c.option_type == "CALL" else "BEARISH"

    return min(score, 100), strategy, signal_type, " · ".join(notes_parts)
