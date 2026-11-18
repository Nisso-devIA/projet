#!/usr/bin/env python3
import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

from rtf_current import DAYS, announcement_target, build_snapshot, planning_slots

PARIS = ZoneInfo("Europe/Paris")
MAP = {"364111337036447745": "mrkrakotte", "1": "zaeldryk"}


class RtfCurrentTests(unittest.TestCase):
    def test_separate_messages_cover_two_hour_slots(self):
        messages = [
            {"id": "old", "timestamp": "2026-08-01T09:00:00Z", "content": "10H-12H🇫🇷:\n12H-14H🇫🇷:\n14H-16H🇫🇷:\n", "mentions": []},
            {"id": "a", "timestamp": "2026-11-14T10:10:50Z", "content": "12h-14h <@311>", "mentions": [{"id": "311", "username": "elodie15", "global_name": "renardefury"}]},
            {"id": "b", "timestamp": "2026-11-14T10:36:44Z", "content": "14H-16H🇫🇷 <@136>", "mentions": [{"id": "136", "username": "aokiira_"}]},
            {"id": "c", "timestamp": "2026-11-14T10:38:59Z", "content": "16H-18H🇫🇷: <@155>", "mentions": [{"id": "155", "username": "evilys"}]},
        ]
        profiles = {
            "311": {"twitch": "renardefury", "nick": "renardefury", "username": "elodie15", "global_name": "renardefury"},
            "136": {"twitch": "aokiira_", "nick": "AoKiira_", "username": "aokiira_", "global_name": "AoKira"},
            "155": {"twitch": "evilys_", "nick": "Evilys_", "username": "evilys", "global_name": "Evilys"},
        }
        slots = planning_slots(messages, {}, profiles)
        moment = datetime(2026, 11, 14, 13, 10, tzinfo=PARIS)
        snap = build_snapshot(
            moment=moment,
            slots=slots,
            announcement={"login": "renardefury", "msg_id": "ann", "since": "2026-11-14T10:11:42+00:00"},
            live={"renardefury"},
            zaeldryk_live=False,
        )
        self.assertEqual(snap["current_slot"]["login"], "renardefury")
        self.assertTrue(snap["current_slot"]["live"])
        self.assertEqual(snap["login"], "renardefury")
        self.assertEqual(snap["source"], "planning")
        self.assertTrue(snap["match"])
        self.assertEqual(snap["next_slot"]["login"], "aokiira_")
        self.assertEqual(snap["next_slot"]["start"][11:13], "14")

    def test_formats_and_minutes_and_one_hour(self):
        messages = [
            {"id": "m", "timestamp": "2026-11-14T20:00:00Z", "content": "23h30-00h15 <@364111337036447745>", "mentions": []},
            {"id": "n", "timestamp": "2026-11-14T21:00:00Z", "content": "23H-00H🇫🇷/17H-18H🇨🇦: <@9>", "mentions": [{"id": "9", "username": "other"}]},
        ]
        slots = planning_slots(messages, MAP)
        late = datetime(2026, 11, 14, 23, 40, tzinfo=PARIS)
        snap = build_snapshot(moment=late, slots=slots, announcement={"login": "", "msg_id": "", "since": ""}, live=set(), zaeldryk_live=False)
        self.assertEqual(snap["current_slot"]["login"], "mrkrakotte")
        hour = datetime(2026, 11, 14, 23, 10, tzinfo=PARIS)
        snap = build_snapshot(moment=hour, slots=slots, announcement={"login": "", "msg_id": "", "since": ""}, live={"other"}, zaeldryk_live=False)
        self.assertEqual(snap["current_slot"]["login"], "other")
        self.assertEqual(snap["login"], "other")

    def test_same_live_streamer_uses_planning_and_mismatch_falls_back(self):
        slots = planning_slots(
            [{"id": "a", "timestamp": "2026-11-14T10:00:00Z", "content": "12h-14h <@311>", "mentions": [{"id": "311", "username": "elodie15"}]}],
            {},
        )
        moment = datetime(2026, 11, 14, 12, 24, tzinfo=PARIS)
        same = build_snapshot(
            moment=moment,
            slots=slots,
            announcement={"login": "elodie15", "msg_id": "ann", "since": "2026-11-14T10:11:42+00:00"},
            live={"elodie15"},
            zaeldryk_live=False,
        )
        self.assertTrue(same["match"])
        self.assertEqual(same["login"], "elodie15")
        self.assertEqual(same["source"], "planning")
        differ = build_snapshot(
            moment=moment,
            slots=slots,
            announcement={"login": "renardefury", "msg_id": "ann", "since": "2026-11-14T10:11:42+00:00"},
            live={"renardefury"},
            zaeldryk_live=False,
        )
        self.assertFalse(differ["match"])
        self.assertEqual(differ["login"], "renardefury")
        self.assertEqual(differ["source"], "announcement")
        self.assertEqual(differ["current_slot"]["login"], "elodie15")
        self.assertFalse(differ["current_slot"]["live"])
        empty = build_snapshot(
            moment=moment,
            slots=slots,
            announcement={"login": "renardefury", "msg_id": "ann", "since": "t"},
            live=set(),
            zaeldryk_live=False,
        )
        self.assertEqual(empty["login"], "")

    def test_no_slot_uses_the_live_announcement(self):
        text = "La suite du raid avec renardefury !! \nhttps://www.twitch.tv/renardefury"
        found = announcement_target(
            [{"id": "9", "timestamp": "2026-11-14T10:11:42Z", "content": text, "embeds": [{"url": "https://www.twitch.tv/renardefury"}]}]
        )
        snap = build_snapshot(
            moment=datetime(2026, 11, 14, 11, 5, tzinfo=PARIS),
            slots=[],
            announcement=found,
            live={"renardefury"},
            zaeldryk_live=False,
        )
        self.assertEqual(snap["login"], "renardefury")
        self.assertEqual(snap["source"], "announcement")

    def test_date_header_overrides_the_channel_day(self):
        messages = [
            {
                "id": "fri",
                "timestamp": "2026-11-13T18:00:00Z",
                "channel_id": DAYS[0],
                "content": "Samedi 14\n21H-22H🇫🇷: <@364111337036447745>",
                "mentions": [],
            },
            {
                "id": "sat",
                "timestamp": "2026-11-14T10:10:50Z",
                "channel_id": DAYS[5],
                "content": "12h-14h <@311>",
                "mentions": [{"id": "311", "username": "elodie15", "global_name": "renardefury"}],
            },
        ]
        moment = datetime(2026, 11, 14, 12, 24, tzinfo=PARIS)
        slots = planning_slots(messages, MAP, moment=moment)
        snap = build_snapshot(
            moment=moment,
            slots=slots,
            announcement={"login": "renardefury", "msg_id": "ann", "since": "2026-11-14T11:00:00+00:00"},
            live={"renardefury"},
            zaeldryk_live=False,
        )
        self.assertEqual(snap["current_slot"]["login"], "renardefury")
        self.assertTrue(snap["match"])
        self.assertEqual(snap["source"], "planning")
        friday = [row for row in snap["week"] if row["day"] == "samedi" and row["start"] == "21:00"]
        self.assertEqual(friday[0]["login"], "mrkrakotte")
        self.assertEqual(friday[0]["date"], "2026-11-14")

    def test_display_name_beats_a_different_username(self):
        slots = planning_slots(
            [{
                "id": "a",
                "timestamp": "2026-11-14T10:10:50Z",
                "content": "12h-14h <@311>",
                "mentions": [{"id": "311", "username": "elodie15", "global_name": "renardefury"}],
            }],
            {},
        )
        self.assertEqual(slots[0]["login"], "renardefury")

    def test_zaeldryk_is_excluded(self):
        found = announcement_target(
            [{"id": "1", "timestamp": "2026-11-14T10:00:00Z", "content": "https://www.twitch.tv/zaeldryk", "embeds": []}]
        )
        self.assertEqual(found["login"], "")
        slots = planning_slots(
            [{"id": "g", "timestamp": "2026-11-14T08:00:00Z", "content": "12H-14H🇫🇷: <@1>", "mentions": []}],
            MAP,
        )
        self.assertEqual(slots[0]["login"], "")


if __name__ == "__main__":
    unittest.main()
