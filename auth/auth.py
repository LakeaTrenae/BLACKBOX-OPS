# BLACKBOX_OPS — auth/auth.py
# ============================
# Schwab OAuth2 token manager.
# Handles the initial browser-based login, token storage, and auto-refresh.
#
# REQUIRED ENV VARS (set in .env):
#   SCHWAB_CLIENT_ID      — your App Key from developer.schwab.com
#   SCHWAB_CLIENT_SECRET  — your App Secret
#   SCHWAB_REDIRECT_URI   — must match what you registered (e.g. https://127.0.0.1)
#
# FIRST RUN:
#   python -m auth.auth
#   Follow the browser prompt, paste the redirect URL, token is saved to data/token.json

from __future__ import annotations
import base64
import json
import logging
import os
import webbrowser
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlencode, urlparse, parse_qs

import requests
from dotenv import load_dotenv

load_dotenv()

log = logging.getLogger("auth")

TOKEN_PATH    = Path("data/token.json")
AUTH_BASE     = "https://api.schwabapi.com/v1/oauth"
TOKEN_URL     = f"{AUTH_BASE}/token"
AUTH_URL      = f"{AUTH_BASE}/authorize"


def get_headers() -> dict:
    """Return Authorization headers with a valid access token, refreshing if needed."""
    token = _load_token()
    if not token or _is_expired(token):
        token = _refresh(token)
    return {"Authorization": f"Bearer {token['access_token']}"}


# ── Token lifecycle ───────────────────────────────────────────────────────────

def _load_token() -> dict | None:
    if TOKEN_PATH.exists():
        try:
            return json.loads(TOKEN_PATH.read_text())
        except Exception:
            pass
    return None


def _is_expired(token: dict) -> bool:
    expires_at = token.get("expires_at", 0)
    return datetime.utcnow().timestamp() >= expires_at - 60  # 60s buffer


def _refresh(token: dict | None) -> dict:
    """Refresh using refresh_token. Falls back to full auth flow if needed."""
    if token and token.get("refresh_token"):
        try:
            new_token = _token_request({
                "grant_type":    "refresh_token",
                "refresh_token": token["refresh_token"],
            })
            _save_token(new_token)
            log.info("Token refreshed.")
            return new_token
        except Exception as e:
            log.warning(f"Refresh failed ({e}) — starting full auth flow.")
    return _full_auth_flow()


def _full_auth_flow() -> dict:
    """Interactive OAuth2 PKCE flow. Requires a browser and paste of redirect URL."""
    client_id    = _require_env("SCHWAB_CLIENT_ID")
    redirect_uri = os.environ.get("SCHWAB_REDIRECT_URI", "https://127.0.0.1")

    params = {
        "response_type": "code",
        "client_id":     client_id,
        "redirect_uri":  redirect_uri,
        "scope":         "readonly",
    }
    url = f"{AUTH_URL}?{urlencode(params)}"

    print("\n" + "─" * 60)
    print("  BLACKBOX_OPS — Schwab Authorization")
    print("─" * 60)
    print("  Opening browser for Schwab login…")
    print(f"  If browser does not open, visit:\n  {url}\n")
    webbrowser.open(url)

    redirected = input("  Paste the full redirect URL here: ").strip()
    code = parse_qs(urlparse(redirected).query).get("code", [None])[0]
    if not code:
        raise ValueError("No authorization code found in redirect URL.")

    token = _token_request({
        "grant_type":   "authorization_code",
        "code":         code,
        "redirect_uri": redirect_uri,
    })
    _save_token(token)
    log.info("Authorization complete. Token saved.")
    return token


def _token_request(data: dict) -> dict:
    client_id     = _require_env("SCHWAB_CLIENT_ID")
    client_secret = _require_env("SCHWAB_CLIENT_SECRET")
    credentials   = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()

    resp = requests.post(
        TOKEN_URL,
        headers={
            "Authorization": f"Basic {credentials}",
            "Content-Type":  "application/x-www-form-urlencoded",
        },
        data=data,
        timeout=15,
    )
    resp.raise_for_status()
    token = resp.json()
    token["expires_at"] = (
        datetime.utcnow() + timedelta(seconds=token.get("expires_in", 1800))
    ).timestamp()
    return token


def _save_token(token: dict) -> None:
    TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_PATH.write_text(json.dumps(token, indent=2))


def _require_env(name: str) -> str:
    val = os.environ.get(name)
    if not val:
        raise EnvironmentError(
            f"Missing required environment variable: {name}\n"
            f"Add it to your .env file."
        )
    return val


# ── CLI: run once to authorize ────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
    token = _load_token()
    if token and not _is_expired(token):
        print("Token is valid. No action needed.")
    else:
        _full_auth_flow()
        print("Done. Token saved to data/token.json")
