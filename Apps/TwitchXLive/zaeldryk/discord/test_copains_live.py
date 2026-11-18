#!/usr/bin/env python3
import importlib.util
import unittest
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "copains_live", Path(__file__).resolve().with_name("copains-live.py")
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
friend_embed = _mod.friend_embed
plan = _mod.plan


class CopainsTests(unittest.TestCase):
    def test_first_run_never_posts(self):
        self.assertEqual(plan(True, "", "99"), "seed")
        self.assertEqual(plan(True, "", ""), "seed")

    def test_new_stream_posts_and_repeat_does_not(self):
        self.assertEqual(plan(False, "", "99"), "post")
        self.assertEqual(plan(False, "99", "99"), "skip")
        self.assertEqual(plan(False, "99", ""), "offline")
        self.assertEqual(plan(False, "99", "100"), "post")

    def test_embed_matches_the_zaeldryk_live_shape(self):
        embed = friend_embed("Belka_dz", "belka_dz", "Une partie", "Zelda")
        self.assertEqual(embed["title"], "🔴 Belka_dz est en LIVE !")
        self.assertEqual(embed["description"], "Une partie")
        self.assertEqual(embed["url"], "https://www.twitch.tv/belka_dz")
        self.assertEqual(embed["color"], 0x9146FF)
        self.assertEqual(embed["fields"], [{"name": "Jeu", "value": "Zelda", "inline": True}])
        self.assertEqual(embed["footer"], {"text": "La communauté Zaelrys"})
        self.assertIn("live_user_belka_dz", embed["image"]["url"])


if __name__ == "__main__":
    unittest.main()
