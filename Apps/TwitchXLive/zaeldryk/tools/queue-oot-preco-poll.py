#!/usr/bin/env python3
"""Queue OOT remake short poll + announce #📢-annonces."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from announce_common import post_announce  # noqa: E402

SONDAGES_ID = "1542633689840877579"
PENDING = Path("/home/ubuntu/zaeldryk/state/pending-poll.json")

pending = {
    "channel_id": SONDAGES_ID,
    "question": "Ocarina of Time remake — tu as préco quoi ?",
    "options": [
        "Pack 40 ans sécurisé",
        "Jeu seul préco",
        "Je vais craquer",
        "Pas intéressé / j’attends",
    ],
    "delete_message_ids": [],
}
PENDING.parent.mkdir(parents=True, exist_ok=True)
PENDING.write_text(json.dumps(pending, ensure_ascii=False, indent=2), encoding="utf-8")
print("queued", PENDING)

ANNOUNCE = (
    "## Ocarina of Time remake — sondage ⚔️\n\n"
    "Pack **édition 40 ans**, jeu seul, ou tu vas craquer ?\n\n"
    f"👉 **Vote ici :** <#{SONDAGES_ID}>\n\n"
    "Merci de faire partie de la communauté 🐺"
)
msg = post_announce(ANNOUNCE)
print("announce", msg.get("id"))
