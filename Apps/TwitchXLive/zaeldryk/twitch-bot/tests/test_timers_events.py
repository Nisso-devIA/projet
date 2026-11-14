#!/usr/bin/env python3
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from zaelbot.auth import parse_token_response, refresh_fields
from zaelbot.events import event_from_notification, raid_thanks_text, render_event, tiktok_line
from zaelbot.raid_thanks import SeenRaids, chat_body
from zaelbot.helix_text import followage_text, uptime_text
from zaelbot.tiktok_filter import TikTokFilter
from zaelbot.timers import Timer, TimerScheduler


class TimerTests(unittest.TestCase):
    def test_timer_waits_for_chat_activity(self):
        timer = Timer("discord", "lien", interval_seconds=100, min_messages=3, last_sent=0)
        scheduler = TimerScheduler([timer])
        scheduler.on_chat_message()
        scheduler.on_chat_message()
        self.assertEqual(scheduler.due(500), [])
        scheduler.on_chat_message()
        due = scheduler.due(500)
        self.assertEqual([item.name for item in due], ["discord"])
        self.assertEqual(scheduler.due(500), [])
        scheduler.on_chat_message()
        scheduler.on_chat_message()
        scheduler.on_chat_message()
        self.assertEqual(scheduler.due(550), [])
        self.assertEqual([item.name for item in scheduler.due(700)], ["discord"])

    def test_don_timer_waits_and_does_not_follow_discord(self):
        discord = Timer("discord", "d", interval_seconds=1800, min_messages=8, last_sent=0)
        don = Timer("don", "k", interval_seconds=2700, min_messages=8, last_sent=-450)
        scheduler = TimerScheduler([discord, don], gap_seconds=120)
        for _ in range(8):
            scheduler.on_chat_message()
        self.assertEqual([item.name for item in scheduler.due(1800)], ["discord"])
        self.assertEqual(scheduler.due(1810), [])
        self.assertEqual([item.name for item in scheduler.due(2250)], ["don"])


class EventTests(unittest.TestCase):
    def test_notifications_become_chat_lines(self):
        kind, payload = event_from_notification("channel.raid", {"from_broadcaster_user_name": "Nisso", "viewers": 12, "from_broadcaster_user_id": "9"})
        self.assertEqual(kind, "raid")
        self.assertIn("Nisso", render_event(kind, payload))
        self.assertEqual(payload["from_id"], "9")
        gift = event_from_notification("channel.subscribe", {"user_name": "A", "is_gift": True})
        self.assertIsNone(gift)
        many = raid_thanks_text("Nisso", 12)
        one = raid_thanks_text("@Nisso", 1)
        self.assertEqual(
            many,
            "🐺 Bienvenue au royaume de Zaelys, la meute de @Nisso ! Merci pour ce raid de 12 guerriers ⚔️",
        )
        self.assertEqual(
            one,
            "🐺 Bienvenue au royaume de Zaelys, la meute de @Nisso ! Merci pour ce raid de 1 guerrier ⚔️",
        )
        seen = SeenRaids()
        self.assertEqual(seen.claim("evt-1", "Nisso", 12), many)
        self.assertIsNone(seen.claim("evt-1", "Nisso", 12))
        self.assertIsNone(seen.claim("", "Nisso", 12))
        body = chat_body("426411773", many)
        self.assertEqual(body["sender_id"], "426411773")
        self.assertEqual(body["broadcaster_id"], body["sender_id"])

    def test_tiktok_line_and_filter(self):
        self.assertEqual(tiktok_line("Luna", "  salut   "), "🎵 Luna : salut")
        self.assertIsNone(tiktok_line("Luna", "   "))
        gate = TikTokFilter(repeat_seconds=10)
        self.assertTrue(gate.accept("Luna", "salut", 0))
        self.assertFalse(gate.accept("Luna", "salut", 5))
        self.assertTrue(gate.accept("Luna", "salut", 11))

    def test_uptime_and_token_parse(self):
        text = uptime_text("2026-11-10T20:00:00Z", datetime(2026, 11, 10, 22, 30, tzinfo=timezone.utc))
        self.assertIn("2 h 30 min", text)
        self.assertEqual(followage_text("Luna", None, datetime.now(timezone.utc)), "Luna ne follow pas la chaîne.")
        bundle = parse_token_response({"access_token": "a", "refresh_token": "b", "expires_in": 30})
        self.assertEqual(bundle.expires_in, 30)
        fields = refresh_fields("id", "secret", "refresh")
        self.assertEqual(fields["grant_type"], "refresh_token")
        self.assertNotIn("access_token", fields)


if __name__ == "__main__":
    unittest.main()
