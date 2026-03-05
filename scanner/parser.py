# BLACKBOX_OPS — scanner/parser.py
# ==================================
# Parses Schwab option chain JSON into OptionContract objects.

from __future__ import annotations
from scanner import config as cfg
from scanner.models import OptionContract


def parse_contracts(chain_data: dict, iv_rank: float) -> list[OptionContract]:
    """Parse Schwab chain JSON into a flat list of OptionContract objects."""
    contracts = []

    for option_type_key in ("callExpDateMap", "putExpDateMap"):
        option_type = "CALL" if "call" in option_type_key else "PUT"
        exp_map     = chain_data.get(option_type_key, {})

        for exp_str, strikes in exp_map.items():
            # exp_str format: "2026-03-21:30"  (date:dte)
            try:
                exp_date_str, dte_str = exp_str.split(":")
                dte = int(dte_str)
            except ValueError:
                continue

            if not (cfg.DTE_MIN <= dte <= cfg.DTE_MAX):
                continue

            for strike_str, option_list in strikes.items():
                for opt in option_list:
                    bid = opt.get("bid", 0.0)
                    ask = opt.get("ask", 0.0)
                    mid = round((bid + ask) / 2, 2) if bid and ask else 0.0

                    if mid <= 0:
                        continue

                    spread_pct = round((ask - bid) / mid, 4) if mid > 0 else 1.0
                    volume     = opt.get("totalVolume", 0)
                    oi         = opt.get("openInterest", 0)
                    vol_oi     = round(volume / oi, 2) if oi > 0 else 0.0
                    delta      = abs(opt.get("delta", 0.0) or 0.0)
                    iv         = round((opt.get("volatility", 0.0) or 0.0) / 100, 4)

                    contracts.append(OptionContract(
                        symbol=opt.get("symbol", ""),
                        underlying=chain_data.get("symbol", ""),
                        option_type=option_type,
                        strike=float(strike_str),
                        expiration=exp_date_str,
                        dte=dte,
                        bid=bid,
                        ask=ask,
                        mid=mid,
                        volume=volume,
                        open_interest=oi,
                        delta=delta,
                        gamma=opt.get("gamma", 0.0) or 0.0,
                        theta=opt.get("theta", 0.0) or 0.0,
                        vega=opt.get("vega", 0.0) or 0.0,
                        iv=iv,
                        iv_rank=iv_rank,
                        spread_pct=spread_pct,
                        vol_oi_ratio=vol_oi,
                        tags=_build_tags(iv_rank, delta, dte, volume, oi, spread_pct, vol_oi),
                    ))

    return contracts


def _build_tags(iv_rank, delta, dte, volume, oi, spread_pct, vol_oi) -> list[str]:
    tags = []
    if iv_rank >= cfg.IV_RANK_HIGH:
        tags.append("HIGH_IV")
    elif iv_rank >= cfg.IV_RANK_MIN:
        tags.append("ELEVATED_IV")
    if dte <= 21:
        tags.append("SHORT_DTE")
    elif dte >= 45:
        tags.append("LONG_DTE")
    if delta <= cfg.DELTA_NEUTRAL:
        tags.append("NEUTRAL_DELTA")
    if spread_pct <= 0.05:
        tags.append("TIGHT_SPREAD")
    elif spread_pct >= cfg.SPREAD_PCT_MAX:
        tags.append("WIDE_SPREAD")
    if vol_oi >= cfg.UNUSUAL_VOL_OI_RATIO:
        tags.append("UNUSUAL_ACTIVITY")
    if volume >= 500:
        tags.append("HIGH_VOLUME")
    if oi >= 1000:
        tags.append("HIGH_OI")
    return tags
