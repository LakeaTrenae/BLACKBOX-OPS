# BLACKBOX_OPS — scanner/filters.py
# ====================================
# Quality filter engine for option contracts.

from scanner import config as cfg
from scanner.models import OptionContract


def apply_filters(contracts: list[OptionContract]) -> list[OptionContract]:
    """Return only contracts that pass all quality filters."""
    filtered = []
    for c in contracts:
        if c.iv_rank < cfg.IV_RANK_MIN:
            continue
        if not (cfg.DELTA_MIN <= c.delta <= cfg.DELTA_MAX):
            continue
        if c.open_interest < cfg.OI_MIN:
            continue
        if c.volume < cfg.VOLUME_MIN:
            continue
        if c.spread_pct > cfg.SPREAD_PCT_MAX:
            continue
        filtered.append(c)
    return filtered
