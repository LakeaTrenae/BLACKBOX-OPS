# BLACKBOX_OPS — scanner/config.py
# ==================================
# All scanner thresholds. Edit here without touching core logic.

# ── Watchlist ─────────────────────────────────────────────────────────────────
WATCHLIST = [
    "SPY",   # S&P 500 ETF       — high liquidity, tight spreads
    "QQQ",   # Nasdaq ETF        — tech exposure
    "NVDA",  # NVIDIA            — high IV, momentum
    "TSLA",  # Tesla             — volatile, big premiums
    "AAPL",  # Apple             — liquid, steady
    "AMZN",  # Amazon            — large cap, decent IV
    "META",  # Meta              — high momentum
    "MSFT",  # Microsoft         — lower vol, steady theta
    # Add your own:
    # "AMD", "GOOGL", "NFLX", "COIN",
]

# ── Scan Schedule ─────────────────────────────────────────────────────────────
SCAN_INTERVAL_MINUTES = 5

# ── IV Rank ───────────────────────────────────────────────────────────────────
IV_RANK_MIN  = 30   # ignore low-IV environments
IV_RANK_HIGH = 60   # "high IV" tag threshold

# ── Delta ─────────────────────────────────────────────────────────────────────
DELTA_MIN     = 0.20
DELTA_MAX     = 0.55
DELTA_NEUTRAL = 0.20  # delta ≤ this = neutral / condor candidate

# ── DTE ───────────────────────────────────────────────────────────────────────
DTE_MIN = 7
DTE_MAX = 60

# ── Liquidity ─────────────────────────────────────────────────────────────────
OI_MIN          = 100
VOLUME_MIN      = 50
SPREAD_PCT_MAX  = 0.15   # max bid/ask spread as % of mid

# ── Unusual Activity ──────────────────────────────────────────────────────────
UNUSUAL_VOL_OI_RATIO = 3.0  # volume > 3x OI = smart money signal

# ── Scoring ───────────────────────────────────────────────────────────────────
MIN_SIGNAL_SCORE = 40
PREFER_SPREADS   = True

# ── Output ────────────────────────────────────────────────────────────────────
SIGNALS_OUTPUT_PATH = "data/signals_latest.json"
LOG_PATH            = "data/scanner.log"
TOP_N_SIGNALS       = 10
