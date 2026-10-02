#!/usr/bin/env python3
"""Publish anonymous live-poll results (counts + %) — no voter names."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List
from urllib.request import Request, urlopen

ZAEL_ROOT = Path(os.environ.get("ZAEL_ROOT", "/home/ubuntu/zaeldryk"))
DISCORD_ENV = ZAEL_ROOT / "config" / "discord.env"
STATE = ZAEL_ROOT / "state" / "live-polls.json"
API_BASE = "https://discord.com/api/v10"
CHANNEL_SONDAGES_ID = 1542633689840877579


def load_token() -> str:
    for line in DISCORD_ENV.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        if k.strip() in ("DISCORD_BOT_TOKEN", "DISCORD_TOKEN", "BOT_TOKEN", "TOKEN"):
            return v.strip().strip('"').strip("'")
    raise SystemExit("DISCORD_BOT_TOKEN not found in discord.env")


def bar(pct: float, width: int = 10) -> str:
    filled = int(round(pct / 100.0 * width))
    filled = max(0, min(width, filled))
    return "█" * filled + "░" * (width - filled)


def counts_for(poll: Dict[str, Any]) -> List[int]:
    options = poll.get("options") or []
    votes = poll.get("votes") or {}
    counts = [0] * len(options)
    for opt_idx in votes.values():
        try:
            i = int(opt_idx)
        except (TypeError, ValueError):
            continue
        if 0 <= i < len(options):
            counts[i] += 1
    return counts


def build_content(poll: Dict[str, Any]) -> str:
    question = poll.get("question") or "Sondage"
    options = poll.get("options") or []
    counts = counts_for(poll)
    total = sum(counts)
    lines = [
        "@everyone",
        f"**📊 Résultats — {question}**",
        f"_{total} vote(s) · anonymes (sans noms)_",
        "",
    ]
    ranked = sorted(range(len(options)), key=lambda i: counts[i], reverse=True)
    for i in ranked:
        n = counts[i]
        pct = (n / total * 100.0) if total else 0.0
        medal = "🥇 " if ranked and i == ranked[0] and total else ""
        lines.append(f"{medal}**{options[i]}**")
        lines.append(f"`{bar(pct)}` **{pct:.0f}%** · {n} vote(s)")
        lines.append("")
    return "\n".join(lines).strip()


def post_message(token: str, channel_id: int, content: str) -> dict:
    body = json.dumps({"content": content, "allowed_mentions": {"parse": ["everyone"]}}).encode()
    req = Request(
        f"{API_BASE}/channels/{channel_id}/messages",
        data=body,
        headers={
            "Authorization": f"Bot {token}",
            "Content-Type": "application/json",
            "User-Agent": "ZaeldrykPollResults/1.0",
        },
        method="POST",
    )
    with urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def main() -> None:
    token = load_token()
    data = json.loads(STATE.read_text(encoding="utf-8"))
    if not data:
        print("No polls in state")
        return
    changed = False
    for pid, poll in data.items():
        content = build_content(poll)
        ch = int(poll.get("channel_id") or CHANNEL_SONDAGES_ID)
        msg = post_message(token, ch, content)
        poll["results_posted"] = True
        changed = True
        print(f"OK {pid} -> https://discord.com/channels/{poll.get('guild_id', '')}/{ch}/{msg['id']}")
        print(content.replace("@everyone", "[@everyone]"))
        print("---")
    if changed:
        STATE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        print("state updated (results_posted)")


if __name__ == "__main__":
    main()
