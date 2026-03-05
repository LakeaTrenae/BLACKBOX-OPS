# BLACKBOX_OPS — alerts/engine.py
# ==================================
# Multi-channel alert engine. Watches signals_latest.json and fires
# alerts when high-score signals appear.
#
# CHANNELS (configure via env vars):
#   Desktop (macOS):  always on
#   SMS:     TWILIO_SID, TWILIO_TOKEN, TWILIO_FROM, TWILIO_TO
#   Email:   ALERT_EMAIL_FROM, ALERT_EMAIL_TO, ALERT_SMTP_HOST,
#            ALERT_SMTP_PORT, ALERT_SMTP_PASSWORD
#   Discord: DISCORD_WEBHOOK_URL
#
# USAGE (from project root):
#   python -m alerts.engine
#   python -m alerts.engine --min-score 70

import argparse
import json
import logging
import os
import smtplib
import subprocess
import time
from email.mime.text import MIMEText
from pathlib import Path

import requests

from scanner import config as cfg

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("alerts")

POLL_INTERVAL = 60   # seconds between checks
SIGNALS_PATH  = Path(cfg.SIGNALS_OUTPUT_PATH)


# ── Dispatcher ────────────────────────────────────────────────────────────────

def dispatch(signal: dict) -> None:
    title = f"BLACKBOX_OPS  {signal['signal_type']}  {signal['underlying']}"
    body  = _format_body(signal)
    _desktop_notify(title, body)
    _sms(title, body)
    _email(title, body)
    _discord(title, body, signal)
    log.info(f"Alerts fired — {signal['underlying']} {signal['strategy']}  score:{signal['score']}")


def _format_body(s: dict) -> str:
    c = s["contract"]
    return (
        f"{s['strategy']}  |  Score: {s['score']}/100\n"
        f"{c['option_type']}  Strike: ${c['strike']:.0f}  "
        f"Exp: {c['expiration']}  DTE: {c['dte']}\n"
        f"Mid: ${c['mid']:.2f}  Δ{c['delta']:.2f}  "
        f"IVR: {c['iv_rank']:.0f}  Spread: {c['spread_pct']*100:.1f}%\n"
        f"{s['notes']}"
    )


# ── Desktop (macOS) ───────────────────────────────────────────────────────────

def _desktop_notify(title: str, body: str) -> None:
    try:
        script = f'display notification "{body}" with title "{title}" sound name "Ping"'
        subprocess.run(["osascript", "-e", script], check=True, capture_output=True)
    except Exception as e:
        log.debug(f"Desktop notify failed: {e}")


# ── SMS (Twilio) ──────────────────────────────────────────────────────────────

def _sms(title: str, body: str) -> None:
    sid, token, from_, to = (
        os.environ.get(k) for k in ("TWILIO_SID", "TWILIO_TOKEN", "TWILIO_FROM", "TWILIO_TO")
    )
    if not all([sid, token, from_, to]):
        return
    try:
        requests.post(
            f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json",
            auth=(sid, token),
            data={"From": from_, "To": to, "Body": f"{title}\n{body}"},
            timeout=10,
        ).raise_for_status()
    except Exception as e:
        log.warning(f"SMS failed: {e}")


# ── Email (SMTP) ──────────────────────────────────────────────────────────────

def _email(title: str, body: str) -> None:
    from_  = os.environ.get("ALERT_EMAIL_FROM")
    to     = os.environ.get("ALERT_EMAIL_TO")
    host   = os.environ.get("ALERT_SMTP_HOST", "smtp.gmail.com")
    port   = int(os.environ.get("ALERT_SMTP_PORT", 587))
    passwd = os.environ.get("ALERT_SMTP_PASSWORD")
    if not all([from_, to, passwd]):
        return
    try:
        msg = MIMEText(body)
        msg["Subject"], msg["From"], msg["To"] = title, from_, to
        with smtplib.SMTP(host, port, timeout=10) as smtp:
            smtp.starttls()
            smtp.login(from_, passwd)
            smtp.send_message(msg)
    except Exception as e:
        log.warning(f"Email failed: {e}")


# ── Discord ───────────────────────────────────────────────────────────────────

def _discord(title: str, body: str, signal: dict) -> None:
    url = os.environ.get("DISCORD_WEBHOOK_URL")
    if not url:
        return
    color = (0x00C853 if signal["signal_type"] == "BULLISH"
             else 0xD50000 if signal["signal_type"] == "BEARISH"
             else 0xFFAB00)
    try:
        requests.post(url, json={"embeds": [{
            "title":       title,
            "description": body,
            "color":       color,
            "footer":      {"text": f"BLACKBOX_OPS  ·  {signal['timestamp']}"},
        }]}, timeout=10).raise_for_status()
    except Exception as e:
        log.warning(f"Discord failed: {e}")


# ── Watcher ───────────────────────────────────────────────────────────────────

def watch(min_score: int) -> None:
    log.info(f"Alert engine started — watching {SIGNALS_PATH}  min_score={min_score}")
    seen: set[str] = set()

    while True:
        try:
            if SIGNALS_PATH.exists():
                for s in json.loads(SIGNALS_PATH.read_text()):
                    key = f"{s['timestamp']}|{s['underlying']}|{s['strategy']}"
                    if key not in seen and s["score"] >= min_score:
                        seen.add(key)
                        dispatch(s)
        except Exception as e:
            log.error(f"Watcher error: {e}")
        time.sleep(POLL_INTERVAL)


# ── Entry Point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="BLACKBOX_OPS Alert Engine")
    ap.add_argument("--min-score", type=int, default=cfg.MIN_SIGNAL_SCORE,
                    help="Minimum score to trigger alert")
    args = ap.parse_args()
    watch(args.min_score)
