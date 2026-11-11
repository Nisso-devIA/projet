#!/usr/bin/env python3
import json
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from zaelbot.auth import BROADCASTER_SCOPES
from zaelbot.deaths import DeathCounter
from zaelbot.recap import LiveStats, build_recap, clip_url, discord_payload, duration_text, pick_top_clip, post_webhook
from zaelbot.votes import VoteBook, api_available, parse_vote_args, poll_body, prediction_body, prediction_end_body
from zaelbot.welcome import FirstWelcome

ROOT = Path(__file__).resolve().parent.parent


class DeathTests(unittest.TestCase):
    def test_counts_are_per_game_and_survive_reload(self):
        counter = DeathCounter("Zelda")
        self.assertEqual(counter.add(1), 1)
        self.assertEqual(counter.add(1), 2)
        counter.set_game("Mario")
        self.assertEqual(counter.add(1), 1)
        counter.set_game("Zelda")
        self.assertEqual(counter.add(-1), 1)
        reloaded = DeathCounter.from_dict(counter.export())
        self.assertEqual(reloaded.game, "Zelda")
        self.assertEqual(reloaded.total(), 1)
        reloaded.reset()
        self.assertEqual(reloaded.total(), 0)
        self.assertEqual(reloaded.counts["Mario"], 1)


class VoteTests(unittest.TestCase):
    def test_parse_and_chat_fallback(self):
        parsed = parse_vote_args('"Boss battu ?" Oui | Non 120')
        self.assertEqual(parsed["action"], "start")
        self.assertEqual(parsed["spec"].choices, ["Oui", "Non"])
        self.assertEqual(parsed["spec"].seconds, 120)
        self.assertEqual(parse_vote_args("fin 2")["index"], 2)
        self.assertEqual(parse_vote_args("annule")["action"], "cancel")
        book = VoteBook()
        prompt = book.open_chat("pari", parsed["spec"], 100)
        self.assertIn("1. Oui", prompt)
        self.assertTrue(book.cast("alice", "1", 110))
        self.assertTrue(book.cast("bob", "Non", 110))
        self.assertFalse(book.cast("alice", "bonjour", 110))
        closed = book.close()
        self.assertEqual(closed.tally(), [1, 1])
        self.assertIn("Boss battu", closed.title)

    def test_helix_payloads_and_unavailable_status(self):
        spec = parse_vote_args("« Map ? » Zelda | Mario 10")["spec"]
        body = prediction_body("426411773", spec)
        self.assertEqual(body["prediction_window"], 30)
        self.assertEqual(body["outcomes"][0]["title"], "Zelda")
        poll = poll_body("426411773", spec)
        self.assertEqual(poll["duration"], 15)
        end = prediction_end_body("426411773", "pred", None)
        self.assertEqual(end["status"], "CANCELED")
        self.assertTrue(api_available(200))
        self.assertFalse(api_available(403))
        self.assertFalse(api_available(401))


class WelcomeTests(unittest.TestCase):
    def test_once_per_viewer_and_raid_gap(self):
        book = FirstWelcome(invite="https://discord.gg/3vH2u7pme5", gap_seconds=12)
        first = book.consider("Alice", 1000)
        self.assertIn("Alice", first)
        self.assertIn("discord.gg/3vH2u7pme5", first)
        self.assertIsNone(book.consider("Alice", 1030))
        self.assertIsNone(book.consider("Bob", 1005))
        self.assertIn("bob", book.known)
        later = book.consider("Cara", 1020)
        self.assertIn("Cara", later)
        self.assertIsNone(book.consider("zaeldryk", 1100, is_broadcaster=True))
        self.assertIsNone(book.consider("Nightbot", 1100, bot_login="zaeldrykbot"))
        reloaded = FirstWelcome(book.export()["logins"], gap_seconds=12)
        self.assertIsNone(reloaded.consider("alice", 2000))


class RecapTests(unittest.TestCase):
    def test_recap_lists_the_live_and_hides_mentions(self):
        stats = LiveStats({"started_at": "2026-11-11T18:00:00Z"})
        stats.note_event("follow", {})
        stats.note_event("sub", {})
        stats.note_event("gift", {"count": 3})
        stats.note_event("raid", {"user": "Nisso", "viewers": 12})
        stats.add_chatter("alice")
        stats.add_chatter("alice")
        stats.add_death("Zelda", 2)
        stats.add_clip("ClipOne")
        ended = datetime(2026, 11, 11, 20, 30, tzinfo=timezone.utc)
        self.assertEqual(duration_text(stats.started_at, ended), "2 h 30 min")
        top = pick_top_clip(
            [
                {"id": "ClipOne", "view_count": 4, "url": clip_url("ClipOne")},
                {"id": "ClipTwo", "view_count": 9, "url": clip_url("ClipTwo")},
            ]
        )
        text = build_recap(stats, top, ended)
        self.assertIn("follows : 1", text)
        self.assertIn("Cadeaux : 3", text)
        self.assertIn("Nisso (12)", text)
        self.assertIn("Zelda 2", text)
        self.assertIn("alice (2)", text)
        self.assertIn("clips.twitch.tv/ClipTwo", text)
        self.assertNotIn("@everyone", text)
        payload = discord_payload(text + " @everyone @here")
        self.assertEqual(payload["allowed_mentions"], {"parse": []})
        self.assertNotIn("@everyone", payload["content"])
        self.assertEqual(post_webhook("", text), 0)
        again = LiveStats(stats.export())
        again.begin("2026-11-11T18:00:00Z")
        self.assertEqual(again.follows, 1)
        again.begin("2026-11-12T18:00:00Z")
        self.assertEqual(again.follows, 0)

    def test_examples_and_scopes(self):
        timer = json.loads((ROOT / "timers.example.json").read_text(encoding="utf-8"))
        self.assertEqual(timer[0]["interval_seconds"], 1200)
        self.assertGreaterEqual(timer[0]["min_messages"], 1)
        commands = json.loads((ROOT / "commands.example.json").read_text(encoding="utf-8"))
        self.assertIn("discord.gg/3vH2u7pme5", commands["discord"]["response"])
        moderation = json.loads((ROOT / "moderation.example.json").read_text(encoding="utf-8"))
        self.assertIn("putain", moderation["vulgar_words"])
        self.assertIn("clips:edit", BROADCASTER_SCOPES)
        self.assertIn("channel:manage:predictions", BROADCASTER_SCOPES)
        self.assertIn("channel:manage:polls", BROADCASTER_SCOPES)


if __name__ == "__main__":
    unittest.main()
