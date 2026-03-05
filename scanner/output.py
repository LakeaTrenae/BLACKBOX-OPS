# BLACKBOX_OPS — scanner/output.py
# ====================================
# Save signals to JSON and print terminal summary.

from __future__ import annotations
import json
import logging
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from scanner import config as cfg
from scanner.models import Signal

log = logging.getLogger("scanner")


def save_signals(signals: list[Signal], path: str | None = None) -> None:
    """Persist latest signals to JSON for the dashboard and alert engine."""
    out_path = Path(path or cfg.SIGNALS_OUTPUT_PATH)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    data = [{**asdict(s), "contract": asdict(s.contract)} for s in signals]
    out_path.write_text(json.dumps(data, indent=2))
    log.info(f"Saved {len(signals)} signals → {out_path}")


def print_summary(signals: list[Signal]) -> None:
    """Print a clean terminal summary of top signals."""
    if not signals:
        log.info("No signals passed filters this scan.")
        return

    print("\n" + "═" * 70)
    print(f"  BLACKBOX_OPS SCAN — {datetime.now().strftime('%H:%M:%S')}  |  {len(signals)} signal(s)")
    print("═" * 70)

    for s in signals[:cfg.TOP_N_SIGNALS]:
        c = s.contract
        arrow = "▲" if s.signal_type == "BULLISH" else ("▼" if s.signal_type == "BEARISH" else "◆")
        print(
            f"  {arrow} {s.underlying:<6} {c.option_type:<4} "
            f"${c.strike:<7.0f} {c.expiration}  DTE:{c.dte:<3}  "
            f"Mid:${c.mid:<5.2f}  Δ{c.delta:.2f}  "
            f"IVR:{c.iv_rank:.0f}  Score:{s.score}  [{s.strategy}]"
        )
        print(f"         {s.notes}")
        if c.tags:
            print(f"         Tags: {' · '.join(c.tags)}")
        print()

    print("═" * 70 + "\n")
