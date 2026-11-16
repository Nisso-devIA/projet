#!/usr/bin/env python3
import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

from replay import (
    description_for,
    discord_text,
    fallback_chapters,
    game_label,
    journal_done,
    parse_duration,
    select_evening_vod,
    title_for,
)

PARIS = ZoneInfo("Europe/Paris")


class ReplayTests(unittest.TestCase):
    def test_duration_and_evening_window(self):
        self.assertEqual(parse_duration("1h46m37s"), 6397)
        vods = [
            {
                "id": "old",
                "type": "archive",
                "created_at": "2026-11-13T20:55:11Z",
                "duration": "2h50m11s",
                "title": "autre",
            },
            {
                "id": "tonight",
                "type": "archive",
                "created_at": "2026-11-16T20:51:55Z",
                "duration": "1h46m37s",
                "title": "Hey Listen",
            },
        ]
        run_at = datetime(2026, 11, 17, 11, 0, tzinfo=PARIS)
        chosen = select_evening_vod(vods, run_at)
        self.assertEqual(chosen["id"], "tonight")
        self.assertIsNone(select_evening_vod(vods, datetime(2026, 11, 16, 11, 0, tzinfo=PARIS)))

    def test_chapters_title_and_discord_text(self):
        chapters = fallback_chapters(6397)
        self.assertGreaterEqual(len(chapters), 3)
        self.assertEqual(chapters[0], (0, "Début du live"))
        self.assertTrue(all(chapters[i][0] + 10 <= chapters[i + 1][0] for i in range(len(chapters) - 1)))
        title = title_for("Aventure", datetime(2026, 11, 16, 23, 38, tzinfo=PARIS))
        self.assertEqual(title, "Rediffusion live – Aventure – 16/11/2026")
        text = description_for(chapters)
        self.assertIn("https://www.twitch.tv/zaeldryk", text)
        self.assertIn("https://discord.gg/3vH2u7pme5", text)
        self.assertNotIn("tiktok", text.lower())
        message = discord_text("Aventure", chapters, "https://www.youtube.com/watch?v=abc")
        self.assertTrue(message.startswith("@everyone"))
        self.assertIn("Sur la route", message)
        self.assertEqual(game_label("balade Ocarina"), "Ocarina of Time")

    def test_journal_skips_a_known_upload(self):
        data = {"vods": {"1": {"youtube_id": "abc", "status": "posted"}}}
        self.assertTrue(journal_done(data, "1"))
        self.assertFalse(journal_done(data, "2"))
        self.assertFalse(journal_done({"vods": {"1": {"status": "uploading"}}}, "1"))


if __name__ == "__main__":
    unittest.main()
