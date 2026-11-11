"""Rafraîchissement du jeton OAuth du compte bot. Ne journalise jamais le secret."""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

TOKEN_URL = "https://id.twitch.tv/oauth2/token"
SCOPES = [
    "chat:read",
    "chat:edit",
    "user:read:chat",
    "user:write:chat",
    "user:bot",
    "channel:bot",
    "channel:manage:broadcast",
    "moderator:manage:shoutouts",
    "moderator:manage:banned_users",
    "moderator:read:followers",
    "channel:read:subscriptions",
    "bits:read",
]

# Ces scopes doivent être sur le jeton du broadcaster, pas sur celui du bot.
# L'API des clips, paris et sondages exige que l'utilisateur du jeton soit zaeldryk.
BROADCASTER_SCOPES = [
    "clips:edit",
    "channel:manage:predictions",
    "channel:manage:polls",
]


@dataclass
class TokenBundle:
    access_token: str
    refresh_token: str
    expires_in: int


def refresh_fields(client_id: str, client_secret: str, refresh_token: str) -> dict:
    return {
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }


def parse_token_response(payload: dict) -> TokenBundle:
    access = payload.get("access_token") or ""
    refresh = payload.get("refresh_token") or ""
    if not access or not refresh:
        raise ValueError("réponse OAuth incomplète")
    return TokenBundle(access, refresh, int(payload.get("expires_in") or 0))


def refresh_token(client_id: str, client_secret: str, refresh_token_value: str) -> TokenBundle:
    data = urllib.parse.urlencode(refresh_fields(client_id, client_secret, refresh_token_value)).encode()
    request = urllib.request.Request(TOKEN_URL, data=data, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"refresh HTTP {exc.code}") from exc
    return parse_token_response(payload)
