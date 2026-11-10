#!/usr/bin/env python3
"""Temp voice names and the rule that only an empty tracked room is deleted."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from temp_voice import (
    HUB_CHANNEL_ID,
    channel_name,
    deletion_allowed,
    load_channel_ids,
    save_channel_ids,
)


class NameTests(unittest.TestCase):
    def test_uses_the_display_name(self):
        self.assertEqual(channel_name("Nisso"), "🔊 Salon de Nisso")

    def test_empty_name_has_a_fallback(self):
        self.assertEqual(channel_name("   \n"), "🔊 Salon de membre")

    def test_long_name_is_cut_at_the_discord_limit(self):
        room = channel_name("A" * 200)
        self.assertLessEqual(len(room), 100)
        self.assertTrue(room.startswith("🔊 Salon de "))


class StateTests(unittest.TestCase):
    def test_round_trip_skips_the_hub(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "temp-voice.json"
            save_channel_ids([12, HUB_CHANNEL_ID, 12, 34], path)
            self.assertEqual(load_channel_ids(path), [12, 34])


class DeleteRuleTests(unittest.TestCase):
    def test_only_an_empty_tracked_room_can_go(self):
        tracked = {42}
        self.assertTrue(deletion_allowed(42, 0, tracked))
        self.assertFalse(deletion_allowed(42, 1, tracked))
        self.assertFalse(deletion_allowed(99, 0, tracked))
        self.assertFalse(deletion_allowed(HUB_CHANNEL_ID, 0, {HUB_CHANNEL_ID}))


if __name__ == "__main__":
    unittest.main()
