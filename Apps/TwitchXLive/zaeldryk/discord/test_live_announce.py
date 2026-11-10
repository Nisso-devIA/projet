#!/usr/bin/env python3
"""Checks for live-announcement dedupe and cleanup. No Discord calls."""
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "live_announce", Path(__file__).resolve().with_name("live-announce.py")
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
already_announced = _mod.already_announced
is_own_live_embed = _mod.is_own_live_embed
load_state = _mod.load_state
message_ids = _mod.message_ids
remember_message = _mod.remember_message
save_state = _mod.save_state


NOW = datetime(2026, 11, 10, 12, 0, tzinfo=timezone.utc)


class StateTests(unittest.TestCase):
    def test_legacy_single_id_is_kept(self):
        state = load_state_from({"channel_id": "1", "message_id": "abc"})
        self.assertEqual(message_ids(state), ["abc"])

    def test_same_stream_is_not_posted_twice(self):
        state = {"message_ids": ["abc"], "stream_id": "live-1", "started_at": "t1"}
        self.assertTrue(already_announced(state, "live-1", "t1", NOW))
        self.assertFalse(already_announced(state, "live-2", "t2", NOW))

    def test_recent_post_without_stream_id_is_skipped(self):
        state = {
            "message_ids": ["abc"],
            "posted_at": (NOW - timedelta(minutes=2)).isoformat(),
        }
        self.assertTrue(already_announced(state, "", "", NOW))
        later = NOW + timedelta(minutes=11)
        self.assertFalse(already_announced(state, "", "", later))

    def test_remember_appends_and_stays_compatible(self):
        state = remember_message(
            {"message_id": "old"},
            channel_id="chan",
            message_id="new",
            stream_id="live-9",
            started_at="start",
            posted_at=NOW.isoformat(),
        )
        self.assertEqual(state["message_ids"], ["old", "new"])
        self.assertEqual(state["message_id"], "new")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.json"
            save_state(path, state)
            loaded = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(loaded["message_ids"], ["old", "new"])
            self.assertEqual(loaded["message_id"], "new")

    def test_sweep_matches_only_this_bot(self):
        own = {
            "author": {"id": "42", "bot": True},
            "embeds": [{"title": "🔴 Zaeldryk est en LIVE !"}],
        }
        other = {
            "author": {"id": "7", "bot": True},
            "embeds": [{"title": "🔴 Zaeldryk est en LIVE !"}],
        }
        human = {
            "author": {"id": "42", "bot": False},
            "embeds": [{"title": "est en LIVE"}],
        }
        webhook = {
            "author": {"id": "42", "bot": True},
            "webhook_id": "99",
            "embeds": [{"title": "est en LIVE"}],
        }
        self.assertTrue(is_own_live_embed(own, "42"))
        self.assertFalse(is_own_live_embed(other, "42"))
        self.assertFalse(is_own_live_embed(human, "42"))
        self.assertFalse(is_own_live_embed(webhook, "42"))


def load_state_from(payload: dict):
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "state.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        return load_state(path)


if __name__ == "__main__":
    unittest.main()
