# BLACKBOX_OPS — scanner/models.py
# ==================================
# Shared dataclasses for the options scanner pipeline.

from __future__ import annotations
from dataclasses import dataclass


@dataclass
class OptionContract:
    symbol:         str
    underlying:     str
    option_type:    str   # "CALL" or "PUT"
    strike:         float
    expiration:     str   # "YYYY-MM-DD"
    dte:            int
    bid:            float
    ask:            float
    mid:            float
    volume:         int
    open_interest:  int
    delta:          float
    gamma:          float
    theta:          float
    vega:           float
    iv:             float         # implied volatility (decimal)
    iv_rank:        float         # 0–100
    spread_pct:     float         # bid/ask spread as % of mid
    vol_oi_ratio:   float         # unusual activity ratio
    tags:           list[str]


@dataclass
class Signal:
    timestamp:      str
    underlying:     str
    signal_type:    str   # "BULLISH" | "BEARISH" | "NEUTRAL" | "UNUSUAL"
    strategy:       str   # "LONG_CALL" | "LONG_PUT" | "IRON_CONDOR" | etc.
    contract:       OptionContract
    score:          int   # 0–100 conviction score
    notes:          str
