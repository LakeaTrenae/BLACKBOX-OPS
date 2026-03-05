# BLACKBOX_OPS — scanner/market_hours.py
# ========================================
# Market hours check for the options scanner.

from datetime import datetime
from zoneinfo import ZoneInfo


def is_market_open() -> bool:
    """Returns True if current ET time is within regular market hours."""
    now_et = datetime.now(ZoneInfo("America/New_York"))
    if now_et.weekday() >= 5:   # Saturday / Sunday
        return False
    market_open  = now_et.replace(hour=9,  minute=30, second=0, microsecond=0)
    market_close = now_et.replace(hour=16, minute=0,  second=0, microsecond=0)
    return market_open <= now_et <= market_close
