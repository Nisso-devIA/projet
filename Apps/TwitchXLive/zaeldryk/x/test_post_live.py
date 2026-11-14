#!/usr/bin/env python3
"""Offline checks for the live X post. No network."""
from __future__ import annotations

import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from post_live import (  # noqa: E402
    TEMPLATES,
    TWEET_LIMIT,
    choose_index,
    next_index,
    read_index,
    render_tweet,
    should_skip,
    strip_leading_emoji,
    title_has_hey_listen,
    weighted_length,
    write_index,
)

NOW = datetime(2026, 11, 10, 12, 0, tzinfo=timezone.utc)
SAMPLE = "🧚 Hey Listen, je t'attends pour la suite de l'aventure, ne traîne pas 😉"


class RenderTests(unittest.TestCase):
    def test_rotation_order(self):
        self.assertEqual(next_index(None), 0)
        self.assertEqual(next_index(0), 1)
        self.assertEqual(next_index(1), 2)
        self.assertEqual(next_index(2), 0)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "index.txt"
            write_index(path, 1)
            self.assertEqual(read_index(path), 1)

    def test_title_is_substituted(self):
        for template in TEMPLATES:
            text = render_tweet(template, SAMPLE)
            self.assertNotIn("{titre}", text)
            self.assertIn("Hey Listen", text)
            self.assertNotIn("⚔️ 🧚", text)
            self.assertIn("https://www.twitch.tv/zaeldryk", text)
            self.assertLessEqual(weighted_length(text), TWEET_LIMIT)

    def test_long_title_is_truncated(self):
        title = "A" * 500
        text = render_tweet(TEMPLATES[0], title)
        self.assertLessEqual(weighted_length(text), TWEET_LIMIT)
        self.assertIn("…", text)
        self.assertNotIn("A" * 500, text)

    def test_url_counts_as_23(self):
        only = "https://www.twitch.tv/zaeldryk"
        self.assertEqual(weighted_length(only), 23)
        self.assertGreater(len(only), 23)

    def test_one_tweet_per_stream(self):
        state = {
            "message_ids": ["99"],
            "stream_id": "live-1",
            "started_at": "t1",
        }
        self.assertTrue(should_skip(state, "live-1", "t1", NOW))
        self.assertFalse(should_skip(state, "live-2", "t2", NOW))
        recent = {
            "message_ids": ["99"],
            "posted_at": (NOW - timedelta(minutes=3)).isoformat(),
        }
        self.assertTrue(should_skip(recent, "", "", NOW))

    def test_leading_emoji_is_removed_from_the_title(self):
        self.assertEqual(
            strip_leading_emoji(SAMPLE),
            "Hey Listen, je t'attends pour la suite de l'aventure, ne traîne pas 😉",
        )
        text = render_tweet(TEMPLATES[1], SAMPLE)
        self.assertIn("🗡️ Hey Listen,", text)
        self.assertNotIn("🧚 Hey Listen", text)

    def test_hey_listen_skips_template_a_and_advances(self):
        self.assertTrue(title_has_hey_listen("Hey, Listen !"))
        self.assertTrue(title_has_hey_listen(SAMPLE))
        self.assertFalse(title_has_hey_listen("On reprend le temple"))
        self.assertEqual(choose_index(None, SAMPLE), 1)
        self.assertEqual(choose_index(2, SAMPLE), 1)
        self.assertEqual(choose_index(0, SAMPLE), 1)
        self.assertEqual(choose_index(1, SAMPLE), 2)
        self.assertEqual(choose_index(2, "On reprend le temple"), 0)


if __name__ == "__main__":
    unittest.main()
