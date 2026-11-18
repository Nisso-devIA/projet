#!/usr/bin/env python3
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

ROOT = Path(__file__).resolve().parent.parent

from zaelbot.commands import CooldownBook, CommandBook, manage_command, parse_command, render_response
from zaelbot.permissions import allows, permission_level


class ParseTests(unittest.TestCase):
    def test_parse_name_and_args(self):
        self.assertEqual(parse_command("!discord"), ("discord", ""))
        book = CommandBook(json.loads((ROOT / "commands.example.json").read_text(encoding="utf-8")))
        self.assertEqual(book.get("tip").name, "don")
        self.assertEqual(book.get("soutien").name, "don")
        self.assertIn("ko-fi.com/zaeldryk", book.get("don").response)
        self.assertNotIn("tip", book.visible_names())
        self.assertEqual(parse_command("  !So Zaeldryk"), ("so", "Zaeldryk"))
        self.assertIsNone(parse_command("bonjour"))
        self.assertIsNone(parse_command("!"))

    def test_placeholders(self):
        text = render_response("Salut {user} {args} sur {channel}", "Nisso", "oot", "zaeldryk")
        self.assertEqual(text, "Salut Nisso oot sur zaeldryk")


class PermissionTests(unittest.TestCase):
    def test_badges(self):
        self.assertEqual(permission_level({"broadcaster": "1"}), "broadcaster")
        self.assertEqual(permission_level(set(), is_mod=True), "mod")
        self.assertEqual(permission_level(set(), is_vip=True), "vip")
        self.assertEqual(permission_level(set(), is_sub=True), "sub")
        self.assertEqual(permission_level(set()), "everyone")

    def test_hierarchy(self):
        self.assertTrue(allows("mod", "sub"))
        self.assertFalse(allows("everyone", "vip"))


class BookTests(unittest.TestCase):
    def test_add_edit_delete_and_reserved_names(self):
        book = CommandBook()
        self.assertEqual(manage_command(book, "addcmd", "discord Le lien", "everyone"), "Réservé aux modérateurs.")
        self.assertIsNone(book.get("discord"))
        self.assertIn("ajoutée", manage_command(book, "addcmd", "discord Le lien", "mod"))
        self.assertEqual(book.get("discord").response, "Le lien")
        self.assertIn("réservée", manage_command(book, "addcmd", "so autre", "broadcaster"))
        self.assertIn("mise à jour", manage_command(book, "editcmd", "discord Nouveau", "mod"))
        self.assertEqual(book.get("discord").response, "Nouveau")
        self.assertIn("supprimée", manage_command(book, "delcmd", "discord", "mod"))
        self.assertIsNone(book.get("discord"))


class CooldownTests(unittest.TestCase):
    def test_global_and_user_cooldowns(self):
        book = CooldownBook()
        self.assertTrue(book.ready("discord", "a", 100, 10, 30))
        book.mark("discord", "a", 100, 10, 30)
        self.assertFalse(book.ready("discord", "b", 105, 10, 30))
        self.assertFalse(book.ready("discord", "a", 115, 10, 30))
        self.assertTrue(book.ready("discord", "b", 115, 10, 30))
        self.assertTrue(book.ready("discord", "a", 130, 10, 30))


if __name__ == "__main__":
    unittest.main()
