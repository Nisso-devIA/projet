#!/usr/bin/env python3
import importlib.util
import unittest
from pathlib import Path

_spec = importlib.util.spec_from_file_location("chatters", Path(__file__).resolve().with_name("chatters.py"))
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
apply_sample = _mod.apply_sample
keep_login = _mod.keep_login
paris_day = _mod.paris_day
summary_text = _mod.summary_text
update_env_text = _mod.update_env_text


class ChatterTests(unittest.TestCase):
    def test_excludes_broadcaster_and_known_bots(self):
        self.assertFalse(keep_login("Zaeldryk"))
        self.assertFalse(keep_login("zaeldryk_bot"))
        self.assertFalse(keep_login("Nightbot"))
        self.assertTrue(keep_login("belka_dz"))

    def test_paris_day_uses_the_stream_start(self):
        self.assertEqual(paris_day("2026-11-18T20:54:16Z"), "2026-11-18")
        self.assertEqual(paris_day("2026-11-18T23:30:00Z"), "2026-11-19")

    def test_samples_estimate_presence_and_lurkers(self):
        viewers = apply_sample({}, ["belka_dz", "zaeldryk", "nightbot"], "2026-11-18T22:00:00+01:00", None)
        viewers = apply_sample(viewers, ["belka_dz", "quiet_one"], "2026-11-18T22:05:00+01:00", {"belka_dz": 3})
        self.assertNotIn("zaeldryk", viewers)
        self.assertNotIn("nightbot", viewers)
        self.assertEqual(viewers["belka_dz"]["samples"], 2)
        self.assertEqual(viewers["belka_dz"]["estimated_minutes"], 2)
        self.assertEqual(viewers["belka_dz"]["first_seen"], "2026-11-18T22:00:00+01:00")
        self.assertEqual(viewers["belka_dz"]["last_seen"], "2026-11-18T22:05:00+01:00")
        self.assertFalse(viewers["belka_dz"]["lurker"])
        self.assertTrue(viewers["quiet_one"]["lurker"])
        self.assertEqual(viewers["quiet_one"]["messages"], 0)

    def test_summary_counts_lurkers(self):
        text = summary_text(
            {
                "day": "2026-11-18",
                "stream_id": "9",
                "samples": ["a", "b"],
                "viewers": {
                    "a": {"login": "a", "estimated_minutes": 10, "samples": 2, "lurker": False},
                    "b": {"login": "b", "estimated_minutes": 5, "samples": 1, "lurker": True},
                },
            }
        )
        self.assertIn("chatters : 2", text)
        self.assertIn("lurkers : 1", text)
        self.assertIn("a · 10 min", text)

    def test_chatters_token_update_leaves_the_other_tokens(self):
        original = "\n".join(
            [
                "TWITCH_BOT_ACCESS_TOKEN=bot-access",
                "TWITCH_BOT_REFRESH_TOKEN=bot-refresh",
                "TWITCH_BROADCASTER_ACCESS_TOKEN=raid-access",
                "TWITCH_BROADCASTER_REFRESH_TOKEN=raid-refresh",
                "TWITCH_CHATTERS_ACCESS_TOKEN=old-access",
                "TWITCH_CHATTERS_REFRESH_TOKEN=old-refresh",
            ]
        )
        updated = update_env_text(
            original,
            {
                "TWITCH_CHATTERS_ACCESS_TOKEN": "new-access",
                "TWITCH_CHATTERS_REFRESH_TOKEN": "new-refresh",
            },
        )
        self.assertIn("TWITCH_BOT_ACCESS_TOKEN=bot-access\n", updated)
        self.assertIn("TWITCH_BROADCASTER_ACCESS_TOKEN=raid-access\n", updated)
        self.assertIn("TWITCH_BROADCASTER_REFRESH_TOKEN=raid-refresh\n", updated)
        self.assertIn("TWITCH_CHATTERS_ACCESS_TOKEN=new-access\n", updated)
        self.assertNotIn("old-access", updated)


if __name__ == "__main__":
    unittest.main()
