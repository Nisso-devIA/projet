#!/usr/bin/env python3
import unittest
from types import SimpleNamespace

from monteur_watch import MONTEUR_ROLE_ID, alert_text, should_alert
from datetime import datetime
from zoneinfo import ZoneInfo


def role(role_id, permissions=0, name="rôle"):
    return SimpleNamespace(id=role_id, permissions=permissions, name=name)


def entry(action, user=None, target=None, before=None, after=None):
    return SimpleNamespace(
        action=SimpleNamespace(name=action),
        user=user,
        target=target,
        before=before or SimpleNamespace(),
        after=after or SimpleNamespace(),
        guild=SimpleNamespace(id=867426693286461490),
    )


class MonteurWatchTests(unittest.TestCase):
    def test_monteur_channel_change_is_sensitive(self):
        actor = SimpleNamespace(id=5, name="monteur", roles=[role(MONTEUR_ROLE_ID)])
        found = should_alert(entry("channel_create", user=actor, target=role(9, name="salon")), True)
        self.assertEqual(found, "channel create")

    def test_nickname_change_is_ignored(self):
        actor = SimpleNamespace(id=5, name="monteur", roles=[role(MONTEUR_ROLE_ID)])
        self.assertIsNone(should_alert(entry("member_update", user=actor), True))

    def test_timeout_by_monteur_is_kept(self):
        actor = SimpleNamespace(id=5, name="monteur", roles=[role(MONTEUR_ROLE_ID)])
        item = entry(
            "member_update",
            user=actor,
            after=SimpleNamespace(communication_disabled_until="2026-11-18T12:00:00+00:00"),
        )
        self.assertEqual(should_alert(item, True), "timeout")

    def test_dangerous_role_added_to_monteur(self):
        member = SimpleNamespace(id=7, name="éditeur", roles=[role(MONTEUR_ROLE_ID)])
        admin = role(3, permissions=1 << 3, name="admin")
        item = entry(
            "member_role_update",
            user=SimpleNamespace(id=1, name="autre", roles=[]),
            target=member,
            before=SimpleNamespace(roles=[role(MONTEUR_ROLE_ID)]),
            after=SimpleNamespace(roles=[role(MONTEUR_ROLE_ID), admin]),
        )
        reason = should_alert(item, False)
        self.assertIn("administrateur", reason)

    def test_grouped_text_counts_repeats(self):
        item = entry(
            "invite_create",
            user=SimpleNamespace(id=5, name="monteur"),
            target=SimpleNamespace(id=4, name="invite"),
        )
        text = alert_text(item, "invite create", datetime(2026, 11, 18, 12, 40, tzinfo=ZoneInfo("Europe/Paris")), 3)
        self.assertIn("Répété 3 fois", text)
        self.assertIn("Europe/Paris", text)
        self.assertNotIn("@everyone", text)


if __name__ == "__main__":
    unittest.main()
