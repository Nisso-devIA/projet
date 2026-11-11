#!/usr/bin/env python3
import json
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from zaelbot.commands import BUILTINS
from zaelbot.greeting import DEFAULT_RULES_TEXT, LiveGreeting
from zaelbot.moderation import ModerationState, hate_command, sanction_line
from zaelbot.normalize import contains_term, normalize_text

ROOT = Path(__file__).resolve().parent.parent
DAY = 86400


class NormalizeTests(unittest.TestCase):
    def test_variants_match_and_innocent_words_do_not(self):
        for message in ("N1QU3", "n i q u e", "n.i.q.u.e", "niiique", "énculé"):
            self.assertTrue(contains_term(message, "nique") or contains_term(message, "encule"), message)
        self.assertEqual(normalize_text("enculé"), "encule")
        for innocent in ("niquel", "nike", "poutine", "député", "computer", "réputation"):
            self.assertFalse(contains_term(innocent, "nique"), innocent)
            self.assertFalse(contains_term(innocent, "nik"), innocent)
            self.assertFalse(contains_term(innocent, "pute"), innocent)
            self.assertFalse(contains_term(innocent, "putain"), innocent)
            self.assertFalse(contains_term(innocent, "putin"), innocent)


class HateSpamPromoTests(unittest.TestCase):
    def setUp(self):
        self.state = ModerationState()

    def test_hate_bans_including_vip_and_spares_mods(self):
        banned = self.state.inspect("viewer", "espèce de bougnoule", 0)
        self.assertEqual(banned.action, "ban")
        self.assertEqual(banned.reason, "haine")
        self.assertNotIn("bougnoule", banned.warning)
        spaced = self.state.inspect("viewer", "b o u g n o u l e", 1)
        self.assertEqual(spaced.action, "ban")
        self.assertEqual(self.state.inspect("vip", "faggot", 2, level="vip").action, "ban")
        self.assertIsNone(self.state.inspect("modo", "faggot", 3, level="mod"))
        self.assertIsNone(self.state.inspect("zaeldryk", "faggot", 4, level="broadcaster"))

    def test_false_friends_are_not_hate_or_insults(self):
        for index, text in enumerate(("c'est niquel", "j'ai des nike", "une poutine", "le député", "computer", "sa réputation", "disputer", "imputer")):
            self.assertIsNone(self.state.inspect(f"viewer{index}", text, index * 100), text)

    def test_putain_family_is_vulgar(self):
        samples = ("oh putain", "putains", "pute", "des putes", "putin", "ptn", "put1", "p.u.t.e", "puuuutain")
        for index, text in enumerate(samples):
            action = self.state.inspect(f"viewer{index}", text, index)
            self.assertIsNotNone(action, text)
            self.assertEqual(action.reason, "vulgarite", text)
            self.assertEqual(action.action, "warn", text)
            self.assertNotIn("putain", action.warning.casefold())
            self.assertNotIn("pute", action.warning.casefold())

    def test_spam_bot_bans_and_skips_vip(self):
        self.assertEqual(self.state.inspect("bot", "best viewers on streamboo", 0).action, "ban")
        self.assertEqual(self.state.inspect("bot", "cheap followers bit.ly/x", 1).reason, "spam-bot")
        first = self.state.inspect("bot", "hello https://example.com viewers", 2, first_message=True)
        self.assertEqual(first.reason, "spam-bot")
        self.assertNotIn("streamboo", first.warning)
        self.assertIsNone(self.state.inspect("vip", "best viewers", 3, level="vip"))
        self.assertIsNone(self.state.inspect("viewer", "je vais sur google", 4))

    def test_promo_warns_except_own_links_permit_and_staff(self):
        other = self.state.inspect("viewer", "viens https://twitch.tv/someone", 0)
        self.assertEqual(other.reason, "autopromo")
        self.assertEqual(other.action, "warn")
        self.assertNotIn("someone", other.warning)
        for offset, link in enumerate(
            (
                "https://twitch.tv/zaeldryk",
                "https://discord.gg/3vH2u7pme5",
                "https://www.tiktok.com/@zaeldryk",
                "https://youtube.com/@zaeldryk",
                "https://kick.com/zaeldryk",
            ),
            start=1,
        ):
            self.assertIsNone(self.state.inspect("viewer", link, offset * 100), link)
        self.assertEqual(self.state.inspect("viewer", "https://discord.gg/autre", 600).reason, "autopromo")
        self.state.grant_permit("viewer", 10)
        self.assertIsNone(self.state.inspect("viewer", "follow moi https://twitch.tv/someone", 11))
        self.assertIsNone(self.state.inspect("modo", "https://twitch.tv/someone", 12, level="mod"))

    def test_vulgar_ladder_persists_and_expires(self):
        first = self.state.inspect("bob", "connard", 0)
        second = self.state.inspect("bob", "nique ta mère", 10)
        self.assertEqual((first.action, first.strike), ("warn", 1))
        self.assertEqual((second.action, second.duration), ("timeout", 300))
        self.assertNotIn("connard", first.warning)
        reloaded = ModerationState(strikes=self.state.export_strikes())
        third = reloaded.inspect("bob", "fdp", 20)
        self.assertEqual(third.action, "ban")
        self.assertEqual(third.strike, 3)
        expired = ModerationState(strikes=self.state.export_strikes())
        again = expired.inspect("bob", "connard", 10 + 30 * DAY + 1)
        self.assertEqual((again.action, again.strike), ("warn", 1))

    def test_mods_can_extend_the_hate_list(self):
        self.assertIn("modérateur", hate_command(self.state, "addhate", "mottest", "everyone"))
        self.assertIn("ajouté", hate_command(self.state, "addhate", "mottest", "mod"))
        self.assertEqual(self.state.inspect("viewer", "M0TT3ST", 0).reason, "haine")
        self.assertIn("retiré", hate_command(self.state, "delhate", "mottest", "mod"))
        self.assertIsNone(self.state.inspect("viewer", "mottest", 1))

    def test_sanction_log_has_no_message_body(self):
        line = sanction_line("bob", "haine", "ban", "2026-11-11 00:00:00")
        self.assertNotIn("bougnoule", line)
        self.assertIn("rule=haine", line)
        self.assertIn("action=ban", line)


class GreetingTests(unittest.TestCase):
    def test_default_text_and_command_are_reserved(self):
        text = (ROOT / "regles.example.txt").read_text(encoding="utf-8").strip()
        self.assertEqual(text, DEFAULT_RULES_TEXT)
        self.assertIn("regles", BUILTINS)
        config = json.loads((ROOT / "greeting.example.json").read_text(encoding="utf-8"))
        self.assertEqual(config["delay_seconds"], 120)
        listed = json.loads((ROOT / "moderation.example.json").read_text(encoding="utf-8"))
        self.assertIn("bougnoule", listed["hate_words"])
        self.assertEqual(listed["vulgar_strike_days"], 30)

    def test_one_greeting_per_live_survives_a_restart(self):
        start = datetime(2026, 11, 11, tzinfo=timezone.utc)
        greeting = LiveGreeting(DEFAULT_RULES_TEXT, 120)
        self.assertTrue(greeting.claim(start.isoformat()))
        self.assertFalse(greeting.claim(start.isoformat()))
        self.assertEqual(greeting.wait_seconds(start, start), 120)
        self.assertEqual(greeting.wait_seconds(start, start + timedelta(seconds=130)), 0)
        greeting.mark_sent(start.isoformat())
        restarted = LiveGreeting(DEFAULT_RULES_TEXT, 120, sorted(greeting.sent))
        self.assertFalse(restarted.claim(start.isoformat()))
        later = start + timedelta(hours=5)
        self.assertTrue(restarted.claim(later.isoformat()))
        self.assertEqual(restarted.text, DEFAULT_RULES_TEXT)


if __name__ == "__main__":
    unittest.main()
