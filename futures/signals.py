# BLACKBOX_OPS — futures/signals.py
# ====================================
# Signal generator for futures quotes.
# Scores each contract 0–100 on momentum + volume factors.

from datetime import datetime

from futures import config as cfg
from futures.models import FuturesQuote, FuturesSignal


def generate_signals(quotes: list[FuturesQuote]) -> list[FuturesSignal]:
    """Score each futures quote and return signals above MIN_SCORE."""
    signals = []
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for q in quotes:
        score, signal_type, notes = _score_quote(q)
        if score < cfg.MIN_SCORE:
            continue
        signals.append(FuturesSignal(
            timestamp=now,
            symbol=q.symbol,
            description=q.description,
            signal_type=signal_type,
            score=score,
            notes=notes,
            quote=q,
        ))

    signals.sort(key=lambda s: s.score, reverse=True)
    return signals


def _score_quote(q: FuturesQuote) -> tuple[int, str, str]:
    """Score a futures quote. Returns (score, signal_type, notes)."""
    score       = 0
    notes_parts = []
    change_pct  = abs(q.change_pct)

    # Momentum (0–40 pts)
    if change_pct >= cfg.MOMENTUM_EXTREME_PCT:
        score += 25; notes_parts.append(f"Extreme move {q.change_pct:+.2f}%")
    elif change_pct >= cfg.MOMENTUM_STRONG_PCT:
        score += 40; notes_parts.append(f"Strong momentum {q.change_pct:+.2f}%")
    else:
        score += int(change_pct / cfg.MOMENTUM_STRONG_PCT * 20)

    # Volume spike (0–35 pts)
    if q.vol_avg_5d > 0:
        ratio = q.volume / q.vol_avg_5d
        if ratio >= cfg.VOLUME_SPIKE_RATIO * 2:
            score += 35; notes_parts.append(f"Massive volume spike ({ratio:.1f}x avg)")
        elif ratio >= cfg.VOLUME_SPIKE_RATIO:
            score += 20; notes_parts.append(f"Volume spike ({ratio:.1f}x avg)")
        elif ratio >= 1.3:
            score += 10; notes_parts.append(f"Above-avg volume ({ratio:.1f}x)")

    # Session bonus (0–15 pts)
    if q.session == "NORMAL":
        score += 15; notes_parts.append("RTH session")
    elif q.session == "EXTENDED":
        score += 8

    # Spread quality (0–10 pts)
    if q.bid > 0 and q.ask > 0 and q.last > 0:
        spread_pct = (q.ask - q.bid) / q.last
        if spread_pct <= 0.001:
            score += 10
        elif spread_pct <= 0.003:
            score += 5

    # Direction
    if q.change_pct > 0:
        signal_type = "BULLISH"
    elif q.change_pct < 0:
        signal_type = "BEARISH"
    else:
        signal_type = "NEUTRAL"

    if change_pct >= cfg.MOMENTUM_EXTREME_PCT:
        notes_parts.append("Possible exhaustion/reversal")
        signal_type = "NEUTRAL"

    return min(score, 100), signal_type, " · ".join(notes_parts) or "No notable factors"
