#!/usr/bin/env python3
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from zaelbot.moderation import ModerationConfig, ModerationState
from zaelbot.permissions import is_exempt


class ModerationTests(unittest.TestCase):
    def setUp(self):
        self.state = ModerationState(
            ModerationConfig(
                banned_words=["spoiler"],
                spam_max_messages=3,
                spam_window_seconds=10,
                repeat_count=3,
                caps_min_length=8,
                caps_ratio=0.7,
                timeouts_seconds=[60, 300, 600],
                permit_seconds=60,
            )
        )

    def test_mods_are_exempt(self):
        self.assertTrue(is_exempt("mod"))
        self.assertTrue(is_exempt("vip"))
        self.assertFalse(is_exempt("sub"))
        self.assertIsNone(self.state.inspect("mod", "https://example.com", 0, exempt=True))

    def test_link_then_permit_then_timeout_grows(self):
        self.assertIsNone(self.state.inspect("viewer", "https://ko-fi.com/zaeldryk", 0, exempt=False))
        first = self.state.inspect("viewer", "va sur https://example.com", 0, exempt=False)
        self.assertEqual(first.reason, "lien non autorisé")
        self.assertEqual(first.duration, 60)
        self.state.grant_permit("viewer", 10)
        allowed = self.state.inspect("viewer", "https://example.com/ok", 11, exempt=False)
        self.assertIsNone(allowed)
        second = self.state.inspect("viewer", "https://example.com/encore", 12, exempt=False)
        self.assertEqual(second.duration, 300)

    def test_banned_word_and_caps_and_repeat(self):
        word = self.state.inspect("viewer", "gros spoiler ici", 0, exempt=False)
        self.assertEqual(word.reason, "mot interdit")
        caps = self.state.inspect("other", "POURQUOI TOUT CRIE", 0, exempt=False)
        self.assertEqual(caps.reason, "excès de majuscules")
        self.assertIsNone(self.state.inspect("repeat", "hello", 0, exempt=False))
        self.assertIsNone(self.state.inspect("repeat", "hello", 1, exempt=False))
        repeated = self.state.inspect("repeat", "hello", 2, exempt=False)
        self.assertEqual(repeated.reason, "spam")

    def test_short_shout_passes_and_caps_have_their_own_ladder(self):
        defaults = ModerationState()
        self.assertIsNone(defaults.inspect("viewer", "TROP FORT CE BOSS", 0))
        shout = "POURQUOI TU CRIES COMME CA ENCORE"
        first = defaults.inspect("viewer", shout, 0)
        second = defaults.inspect("viewer", shout, 10)
        third = defaults.inspect("viewer", shout, 20)
        fourth = defaults.inspect("viewer", shout, 30)
        self.assertEqual(first.action, "warn")
        self.assertFalse(first.delete)
        self.assertEqual(first.duration, 0)
        self.assertIn("doucement sur les majuscules", first.warning)
        self.assertEqual(second.strike, 2)
        self.assertFalse(second.delete)
        self.assertEqual(third.action, "timeout")
        self.assertEqual(third.duration, 60)
        self.assertTrue(third.delete)
        self.assertEqual(fourth.duration, 300)
        later = defaults.inspect("viewer", shout, 30 + 1801)
        self.assertEqual(later.action, "warn")
        self.assertEqual(later.strike, 1)
        link = self.state.inspect("viewer", "https://example.com", 0, exempt=False)
        caps = self.state.inspect("viewer", "POURQUOI TOUT CRIE ICI", 1, exempt=False)
        self.assertEqual(link.reason, "lien non autorisé")
        self.assertEqual(caps.reason, "excès de majuscules")
        self.assertEqual(caps.strike, 1)


if __name__ == "__main__":
    unittest.main()
