#!/usr/bin/env python3
"""Level curve, XP gates and the SQLite store. No Discord calls."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from levels import (
    AFK_CHANNEL_ID,
    COMMANDES_CHANNEL_ID,
    REGLEMENT_CHANNEL_ID,
    LevelStore,
    cooldown_elapsed,
    level_from_xp,
    progress_in_level,
    rank_index_for_level,
    text_xp_allowed,
    total_xp_for_level,
    voice_xp_allowed,
    xp_to_next,
)


class CurveTests(unittest.TestCase):
    def test_mee6_steps(self):
        self.assertEqual(xp_to_next(0), 100)
        self.assertEqual(xp_to_next(1), 155)
        self.assertEqual(xp_to_next(2), 5 * 4 + 50 * 2 + 100)

    def test_level_from_total(self):
        self.assertEqual(level_from_xp(0), 0)
        self.assertEqual(level_from_xp(99), 0)
        self.assertEqual(level_from_xp(100), 1)
        self.assertEqual(level_from_xp(100 + 154), 1)
        self.assertEqual(level_from_xp(100 + 155), 2)
        self.assertEqual(total_xp_for_level(2), 100 + 155)

    def test_progress_resets_each_level(self):
        level, into, need = progress_in_level(100)
        self.assertEqual((level, into, need), (1, 0, 155))


class GateTests(unittest.TestCase):
    def test_text_rules(self):
        self.assertFalse(text_xp_allowed("bonjour", 1, None, True))
        self.assertFalse(text_xp_allowed("ok", 1, None, False))
        self.assertFalse(text_xp_allowed("bonjour", REGLEMENT_CHANNEL_ID, None, False))
        self.assertFalse(text_xp_allowed("bonjour", 9, COMMANDES_CHANNEL_ID, False))
        self.assertTrue(text_xp_allowed("hey", 1, None, False))

    def test_cooldown(self):
        self.assertTrue(cooldown_elapsed(None, 100))
        self.assertFalse(cooldown_elapsed(90, 149))
        self.assertTrue(cooldown_elapsed(90, 150))

    def test_voice_rules(self):
        self.assertFalse(voice_xp_allowed(
            channel_id=AFK_CHANNEL_ID, afk_channel_id=None,
            non_bot_members=3, self_muted=False, self_deafened=False, author_is_bot=False,
        ))
        self.assertFalse(voice_xp_allowed(
            channel_id=5, afk_channel_id=None,
            non_bot_members=1, self_muted=False, self_deafened=False, author_is_bot=False,
        ))
        self.assertFalse(voice_xp_allowed(
            channel_id=5, afk_channel_id=None,
            non_bot_members=2, self_muted=True, self_deafened=False, author_is_bot=False,
        ))
        self.assertTrue(voice_xp_allowed(
            channel_id=5, afk_channel_id=9,
            non_bot_members=2, self_muted=False, self_deafened=False, author_is_bot=False,
        ))


class RankTests(unittest.TestCase):
    def test_highest_rank_only(self):
        self.assertIsNone(rank_index_for_level(4))
        self.assertEqual(rank_index_for_level(5), 0)
        self.assertEqual(rank_index_for_level(19), 1)
        self.assertEqual(rank_index_for_level(50), 4)


class StoreTests(unittest.TestCase):
    def test_text_cooldown_and_voice_stack(self):
        with tempfile.TemporaryDirectory() as folder:
            store = LevelStore(Path(folder) / "levels.sqlite")
            first = store.grant_text(7, now=1_000)
            second = store.grant_text(7, now=1_030)
            third = store.grant_text(7, now=1_060)
            voice = store.grant_voice(7)
            self.assertIsNotNone(first)
            self.assertIsNone(second)
            self.assertEqual(third.old_xp, first.new_xp)
            self.assertEqual(voice.old_xp, third.new_xp)
            self.assertEqual(store.position(7, voice.new_xp), 1)
            self.assertEqual(store.top(10), [(7, voice.new_xp)])


if __name__ == "__main__":
    unittest.main()
