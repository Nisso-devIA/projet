#!/usr/bin/env python3
import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

from rtf_raid import merge_env_text, parse_target, slot_line, user_on_line, wait_until_fire

PARIS = ZoneInfo("Europe/Paris")

JEUDI = """07/11/26
22H-23H🇫🇷/16H-17H🇨🇦:
23H-00H🇫🇷/17H-18H🇨🇦: <@364111337036447745>
"""


class ParseTests(unittest.TestCase):
    def test_jeudi_grid_is_mrkrakotte(self):
        messages = [
            {"timestamp": "2026-01-15T06:08:02Z", "content": "OUVERTURE DES INSCRIPTIONS"},
            {"timestamp": "2026-08-01T09:03:40Z", "content": JEUDI},
            {"timestamp": "2026-11-12T09:32:21Z", "content": "18H-19H🇫🇷 <@1365980593300574298>"},
        ]
        self.assertEqual(parse_target(messages), "364111337036447745")

    def test_later_correction_replaces_the_slot(self):
        messages = [
            {"timestamp": "2026-11-11T18:00:00Z", "content": JEUDI},
            {"timestamp": "2026-11-12T20:00:00Z", "content": "23H-00H🇫🇷 <@624557350531104779>"},
        ]
        self.assertEqual(parse_target(messages), "624557350531104779")

    def test_annulation_clears_the_slot(self):
        messages = [
            {"timestamp": "2026-11-11T18:00:00Z", "content": JEUDI},
            {"timestamp": "2026-11-12T20:00:00Z", "content": "23h-00h : annulation <@364111337036447745>"},
        ]
        self.assertIsNone(parse_target(messages))

    def test_empty_slot(self):
        content = "22H-23H🇫🇷:\n23H-00H🇫🇷/17H-18H🇨🇦:\n"
        self.assertIsNone(user_on_line(slot_line(content)))

    def test_other_hour_is_not_the_raid_slot(self):
        self.assertIsNone(slot_line("18H-19H🇫🇷 <@1>"))

    def test_env_merge_replaces_only_the_named_keys(self):
        original = "TWITCH_CLIENT_ID=app\nTWITCH_BROADCASTER_ACCESS_TOKEN=old-access\nOTHER=keep\n"
        merged = merge_env_text(
            original,
            {
                "TWITCH_BROADCASTER_ACCESS_TOKEN": "new-access",
                "TWITCH_BROADCASTER_REFRESH_TOKEN": "new-refresh",
            },
        )
        self.assertIn("TWITCH_CLIENT_ID=app\n", merged)
        self.assertIn("OTHER=keep\n", merged)
        self.assertIn("TWITCH_BROADCASTER_ACCESS_TOKEN=new-access\n", merged)
        self.assertIn("TWITCH_BROADCASTER_REFRESH_TOKEN=new-refresh\n", merged)
        self.assertNotIn("old-access", merged)

    def test_fire_only_waits_near_225930(self):
        morning = datetime(2026, 11, 12, 12, 0, tzinfo=PARIS)
        self.assertIsNone(wait_until_fire(morning))
        just_after = datetime(2026, 11, 12, 22, 59, 40, tzinfo=PARIS)
        self.assertEqual(wait_until_fire(just_after), just_after)


if __name__ == "__main__":
    unittest.main()
