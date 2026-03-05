# BLACKBOX_OPS — futures/models.py
# ==================================
# Dataclasses for futures quotes and signals.

from dataclasses import dataclass


@dataclass
class FuturesQuote:
    symbol:        str    # e.g. "/ES", "/CL"
    description:   str
    last:          float
    bid:           float
    ask:           float
    volume:        int
    open_interest: int
    change:        float  # absolute change from prev close
    change_pct:    float  # % change from prev close
    high:          float
    low:           float
    open:          float
    prev_close:    float
    session:       str    # "NORMAL", "EXTENDED", "OVERNIGHT"
    vol_avg_5d:    float  # rolling 5-reading volume average


@dataclass
class FuturesSignal:
    timestamp:   str
    symbol:      str
    description: str
    signal_type: str   # "BULLISH" | "BEARISH" | "NEUTRAL"
    score:       int   # 0–100
    notes:       str
    quote:       FuturesQuote
