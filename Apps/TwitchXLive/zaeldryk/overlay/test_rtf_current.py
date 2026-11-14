#!/usr/bin/env python3
import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

from rtf_current import announcement_target, build_snapshot, planning_slots

PARIS = ZoneInfo("Europe/Paris")
MAP = {"364111337036447745": "mrkrakotte", "1": "zaeldryk"}
GRID = """22H-23H🇫🇷:
23H-00H🇫🇷/17H-18H🇨🇦: <@364111337036447745>
11H-12H🇫🇷: <@1>
12H-13H🇫🇷: <@364111337036447745>
"""


class RtfCurrentTests(unittest.TestCase):
    def test_planning_prefers_a_live_slot_and_hides_zaeldryk(self):
        messages = [
            {"id": "g", "timestamp": "2026-11-14T08:00:00Z", "content": GRID, "mentions": []},
            {"id": "c", "timestamp": "2026-11-14T09:00:00Z", "content": "11h-12h : annulation <@1>"},
        ]
        slots = planning_slots(messages, MAP)
        self.assertEqual(slots[11]["login"], "")
        self.assertEqual(slots[23]["login"], "mrkrakotte")
        moment = datetime(2026, 11, 14, 12, 10, tzinfo=PARIS)
        snap = build_snapshot(
            moment=moment,
            slots=slots,
            announcement={"login": "renardefury", "msg_id": "a", "since": "2026-11-14T10:11:42+00:00"},
            live={"mrkrakotte"},
            zaeldryk_live=False,
        )
        self.assertEqual(snap["login"], "mrkrakotte")
        self.assertEqual(snap["source"], "planning")
        self.assertEqual(snap["current_slot"]["login"], "mrkrakotte")
        self.assertTrue(snap["current_slot"]["live"])
        self.assertEqual(snap["next_slot"]["start"][11:13], "13")

    def test_announcement_is_used_when_the_slot_is_offline(self):
        slots = planning_slots(
            [{"id": "g", "timestamp": "2026-11-14T08:00:00Z", "content": GRID, "mentions": []}],
            MAP,
        )
        moment = datetime(2026, 11, 14, 12, 10, tzinfo=PARIS)
        snap = build_snapshot(
            moment=moment,
            slots=slots,
            announcement={"login": "renardefury", "msg_id": "157", "since": "2026-11-14T10:11:42.723000+00:00"},
            live={"renardefury"},
            zaeldryk_live=True,
        )
        self.assertEqual(snap["login"], "renardefury")
        self.assertEqual(snap["source"], "announcement")
        self.assertEqual(snap["source_msg_id"], "157")
        self.assertEqual(snap["current_slot"]["login"], "mrkrakotte")
        self.assertFalse(snap["current_slot"]["live"])
        self.assertTrue(snap["zaeldryk_live"])

    def test_empty_when_nobody_scheduled_or_announced_is_live(self):
        text = "La suite du raid avec renardefury !! \nhttps://www.twitch.tv/renardefury"
        found = announcement_target(
            [{"id": "9", "timestamp": "2026-11-14T10:11:42Z", "content": text, "embeds": [{"url": "https://www.twitch.tv/renardefury"}]}]
        )
        self.assertEqual(found["login"], "renardefury")
        snap = build_snapshot(
            moment=datetime(2026, 11, 14, 11, 5, tzinfo=PARIS),
            slots={},
            announcement=found,
            live=set(),
            zaeldryk_live=False,
        )
        self.assertEqual(snap["login"], "")
        self.assertEqual(snap["source_msg_id"], "9")

    def test_zaeldryk_announcement_is_not_a_target(self):
        found = announcement_target(
            [{"id": "1", "timestamp": "2026-11-14T10:00:00Z", "content": "https://www.twitch.tv/zaeldryk", "embeds": []}]
        )
        self.assertEqual(found["login"], "")


if __name__ == "__main__":
    unittest.main()
