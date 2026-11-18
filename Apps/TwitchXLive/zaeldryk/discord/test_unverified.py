#!/usr/bin/env python3
"""Captcha grace period. No Discord calls."""

from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from unverified import (
    CAUSE_KICK,
    UnverifiedStore,
    can_view_unverified,
    clock_start,
    is_due,
    is_kick_protected,
    kick_at,
    reminder_at,
)

DEPLOYED = datetime(2026, 11, 10, 17, 0, tzinfo=timezone.utc)
NOW = DEPLOYED


class ClockTests(unittest.TestCase):
    def test_existing_member_starts_at_deployment(self):
        joined = DEPLOYED - timedelta(days=30)
        start = clock_start(joined, DEPLOYED)
        self.assertEqual(start, DEPLOYED)
        self.assertFalse(is_due(reminder_at(start), NOW))
        self.assertFalse(is_due(kick_at(start), NOW + timedelta(hours=71)))
        self.assertTrue(is_due(reminder_at(start), NOW + timedelta(hours=24)))
        self.assertTrue(is_due(kick_at(start), NOW + timedelta(hours=72)))

    def test_new_member_starts_at_join(self):
        joined = DEPLOYED + timedelta(hours=3)
        start = clock_start(joined, DEPLOYED)
        self.assertEqual(start, joined)
        self.assertEqual(reminder_at(start), joined + timedelta(hours=24))
        self.assertEqual(kick_at(start), joined + timedelta(hours=72))


class ProtectionTests(unittest.TestCase):
    def test_staff_owner_and_bots_are_kept(self):
        self.assertTrue(is_kick_protected(set(), is_bot=True, is_owner=False))
        self.assertTrue(is_kick_protected(set(), is_bot=False, is_owner=True))
        self.assertTrue(is_kick_protected({"⚔️ Sentinelle"}, is_bot=False, is_owner=False))
        self.assertTrue(is_kick_protected({"🌑 Ombre"}, is_bot=False, is_owner=False))
        self.assertFalse(is_kick_protected({"🐺 Disciple"}, is_bot=False, is_owner=False))
        self.assertFalse(is_kick_protected(set(), is_bot=False, is_owner=False))

    def test_staff_can_open_the_list(self):
        self.assertTrue(can_view_unverified({"👑 Archonte de Zaeldryk"}, administrator=False, manage_guild=False, manage_messages=False))
        self.assertTrue(can_view_unverified(set(), administrator=False, manage_guild=True, manage_messages=False))
        self.assertFalse(can_view_unverified({"🐺 Disciple"}, administrator=False, manage_guild=False, manage_messages=False))


class StoreTests(unittest.TestCase):
    def test_deploy_time_is_kept_and_kick_flag_is_one_shot(self):
        with tempfile.TemporaryDirectory() as folder:
            store = UnverifiedStore(Path(folder) / "unverified.sqlite")
            first = store.deployed_at(DEPLOYED)
            second = store.deployed_at(DEPLOYED + timedelta(days=2))
            self.assertEqual(first, second)
            self.assertEqual(store.reminder_status(4), "non")
            store.mark_reminder(4, dm_ok=False, when=DEPLOYED)
            self.assertEqual(store.reminder_status(4), "non (DM fermés)")
            self.assertTrue(store.already_reminded(4))
            store.mark_bot_kick(9, DEPLOYED)
            self.assertTrue(store.consume_bot_kick(9))
            self.assertFalse(store.consume_bot_kick(9))
            store.add_departure(9, "invite", DEPLOYED, DEPLOYED + timedelta(hours=2), CAUSE_KICK)
            rows = store.recent_departures(20)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["cause"], CAUSE_KICK)
            self.assertEqual(rows[0]["username"], "invite")


if __name__ == "__main__":
    unittest.main()
