# BLACKBOX_OPS — futures/config.py
# ==================================
# Configuration for the futures scanner.

# ── Watchlist ─────────────────────────────────────────────────────────────────
WATCHLIST = [
    # Equity index futures
    "/ES",   # E-Mini S&P 500
    "/NQ",   # E-Mini Nasdaq-100
    "/RTY",  # E-Mini Russell 2000
    "/YM",   # E-Mini Dow Jones
    # Commodity futures
    "/CL",   # Crude Oil (WTI)
    "/GC",   # Gold
    "/SI",   # Silver
    "/NG",   # Natural Gas
    # Fixed income futures
    "/ZB",   # 30-Year Treasury Bond
    "/ZN",   # 10-Year Treasury Note
    "/ZF",   # 5-Year Treasury Note
    # FX futures
    "/6E",   # Euro FX
    "/6J",   # Japanese Yen
]

# ── Scan Schedule ─────────────────────────────────────────────────────────────
SCAN_INTERVAL_MINUTES = 5

# ── Signal Thresholds ─────────────────────────────────────────────────────────
MOMENTUM_STRONG_PCT  = 0.5    # % change = strong directional move
MOMENTUM_EXTREME_PCT = 1.5    # % change = extreme move (possible reversal)
VOLUME_SPIKE_RATIO   = 2.0    # current volume > 2x 5-day avg = unusual
MIN_SCORE            = 40     # minimum conviction score to emit signal

# ── Output ────────────────────────────────────────────────────────────────────
SIGNALS_OUTPUT_PATH  = "data/futures_signals_latest.json"
VOL_HISTORY_PATH     = "data/futures_vol_history.json"
LOG_PATH             = "data/futures_scanner.log"
TOP_N                = 10
