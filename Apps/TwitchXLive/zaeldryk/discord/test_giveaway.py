#!/usr/bin/env python3
"""Giveaway logic and slash registration. No Discord calls."""

from __future__ import annotations

import random
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

import discord
from discord.ext import commands

from giveaway import (
    DEFAULT_CHANNEL_ID,
    GUILD_ID,
    GiveawayStore,
    draw_winners,
    embed_dict,
    end_announcement,
    has_twitch_link,
    is_giveaway_admin,
    parse_duration,
    register_giveaway,
    reroll_winners,
    start_content,
    twitch_from_profile,
)

NOW = datetime(2026, 11, 14, 15, 0, tzinfo=timezone.utc)


class LogicTests(unittest.TestCase):
    def test_duration_and_admin(self):
        self.assertEqual(parse_duration("30m"), 1800)
        self.assertEqual(parse_duration("2h"), 7200)
        self.assertEqual(parse_duration("1j"), 86400)
        self.assertIsNone(parse_duration("0m"))
        self.assertIsNone(parse_duration("bientôt"))
        self.assertTrue(is_giveaway_admin(False, True))
        self.assertTrue(is_giveaway_admin(True, False))
        self.assertFalse(is_giveaway_admin(False, False))

    def test_draw_reroll_and_twitch(self):
        rng = random.Random(1)
        winners = draw_winners(["a", "b", "c", "a"], 2, rng)
        self.assertEqual(len(winners), 2)
        self.assertEqual(len(set(winners)), 2)
        self.assertEqual(draw_winners([], 1, random.Random(1)), [])
        again = reroll_winners(["a", "b", "c", "d"], ["a", "b"], 2, random.Random(2))
        self.assertEqual(len(again), 2)
        self.assertTrue(set(again).isdisjoint({"a", "b"}))
        fallback = reroll_winners(["a", "b"], ["a", "b"], 1, random.Random(1))
        self.assertEqual(len(fallback), 1)
        self.assertTrue(has_twitch_link([{"type": "twitch", "name": "zaeldryk"}]))
        self.assertFalse(has_twitch_link([{"type": "youtube", "name": "zaeldryk"}]))
        self.assertTrue(twitch_from_profile({"connected_accounts": [{"type": "twitch", "name": "zaeldryk"}]}))
        self.assertFalse(twitch_from_profile({}))

    def test_store_survives_reload_and_default_channel(self):
        self.assertEqual(DEFAULT_CHANNEL_ID, 1571186470696259584)
        with tempfile.TemporaryDirectory() as folder:
            store = GiveawayStore(Path(folder) / "giveaways.json")
            item = store.create(
                guild_id=GUILD_ID,
                channel_id=DEFAULT_CHANNEL_ID,
                prize="Un jeu",
                winners_count=1,
                seconds=1800,
                host_id=5,
                twitch_required=True,
                ping_everyone=False,
                now=NOW,
            )
            joined, action = store.toggle(item["id"], 9)
            self.assertEqual(action, "joined")
            self.assertEqual(joined["participants"], ["9"])
            left, action = store.toggle(item["id"], 9)
            self.assertEqual(action, "left")
            self.assertEqual(left["participants"], [])
            store.toggle(item["id"], 9)
            store.toggle(item["id"], 10)
            reloaded = GiveawayStore(store.path)
            found, error = reloaded.resolve(GUILD_ID, None, {"open"})
            self.assertIsNone(error)
            self.assertEqual(found["id"], item["id"])
            self.assertEqual(found["channel_id"], str(DEFAULT_CHANNEL_ID))
            self.assertEqual(reloaded.due(NOW + timedelta(minutes=29)), [])
            self.assertEqual(len(reloaded.due(NOW + timedelta(minutes=30))), 1)
            ended = reloaded.finish(item["id"], random.Random(3))
            self.assertEqual(ended["status"], "ended")
            self.assertEqual(len(ended["winners"]), 1)
            payload = embed_dict(ended)
            self.assertIn("🐺 Zaelys", payload["title"])
            self.assertNotIn("@everyone", payload["description"])
            content, mentions = end_announcement(ended)
            self.assertNotIn("@everyone", content)
            self.assertEqual(mentions["parse"], [])
            ended["ping_everyone"] = True
            content, mentions = end_announcement(ended)
            self.assertTrue(content.startswith("@everyone "))
            self.assertEqual(mentions["parse"], ["everyone"])
            quiet, mentions = start_content(False)
            self.assertEqual(quiet, "")
            self.assertEqual(mentions, {"parse": []})
            cancelled = reloaded.cancel(item["id"])
            self.assertIsNone(cancelled)


class RegistrationTests(unittest.TestCase):
    def test_slash_group_is_registered(self):
        bot = commands.Bot(command_prefix="!", intents=discord.Intents.default())
        register_giveaway(bot)
        commands_in_guild = bot.tree.get_commands(guild=discord.Object(id=GUILD_ID))
        group = next(command for command in commands_in_guild if command.name == "giveaway")
        names = sorted(command.name for command in group.commands)
        self.assertEqual(names, ["cancel", "end", "reroll", "start"])
        start = group.get_command("start")
        parameters = sorted(parameter.name for parameter in start.parameters)
        self.assertEqual(parameters, ["duree", "everyone", "gagnants", "lot", "salon", "twitch"])


if __name__ == "__main__":
    unittest.main()
