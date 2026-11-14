#!/usr/bin/env python3
"""Owner-only bot message edit. No Discord calls and no real edits."""

from __future__ import annotations

import unittest

import discord
from discord.ext import commands

from bot_message import (
    GUILD_ID,
    OWNER_ID,
    can_edit_author,
    edit_payload,
    is_guild_owner,
    modal_custom_id,
    parse_message_ref,
    parse_modal_custom_id,
    register_bot_message,
)


class LogicTests(unittest.TestCase):
    def test_only_the_owner(self):
        self.assertTrue(is_guild_owner(OWNER_ID, OWNER_ID))
        self.assertFalse(is_guild_owner(1, OWNER_ID))
        self.assertFalse(is_guild_owner(OWNER_ID, 1))

    def test_parse_link_or_id(self):
        link = "https://discord.com/channels/867426693286461490/1571186470696259584/1571186472579629066"
        self.assertEqual(parse_message_ref(link, GUILD_ID), (1571186470696259584, 1571186472579629066))
        self.assertEqual(parse_message_ref(link, 1), "autre_serveur")
        self.assertEqual(
            parse_message_ref("1571186470696259584/1571186472579629066", GUILD_ID),
            (1571186470696259584, 1571186472579629066),
        )
        self.assertEqual(
            parse_message_ref("1571186472579629066", GUILD_ID, 1571186470696259584),
            (1571186470696259584, 1571186472579629066),
        )
        self.assertEqual(parse_message_ref("1571186472579629066", GUILD_ID, None), "lien_invalide")

    def test_only_bot_messages_and_mentions_stay_off(self):
        self.assertTrue(can_edit_author(10, 10))
        self.assertFalse(can_edit_author(10, 11))
        quiet = edit_payload("Bonjour\nla meute", False, False)
        self.assertEqual(quiet["allowed_mentions"], {"parse": []})
        self.assertEqual(quiet["content"], "Bonjour\nla meute")
        loud = edit_payload("@everyone salut", True, False)
        self.assertEqual(loud["allowed_mentions"]["parse"], ["users", "roles", "everyone"])
        self.assertEqual(edit_payload("   ", False, False), "vide")
        self.assertEqual(edit_payload("", False, True)["content"], "")
        self.assertEqual(edit_payload("x" * 2001, False, True), "trop_long")
        custom_id = modal_custom_id(4, 5, False)
        self.assertEqual(parse_modal_custom_id(custom_id), (4, 5, False))


class RegistrationTests(unittest.TestCase):
    def test_command_is_hidden_and_registered(self):
        bot = commands.Bot(command_prefix="!", intents=discord.Intents.default())
        register_bot_message(bot)
        commands_in_guild = bot.tree.get_commands(guild=discord.Object(id=GUILD_ID))
        group = next(command for command in commands_in_guild if command.name == "bot-message")
        self.assertEqual(group.default_permissions.value, 0)
        names = sorted(command.name for command in group.commands)
        self.assertEqual(names, ["modifier"])
        modifier = group.get_command("modifier")
        parameters = sorted(parameter.name for parameter in modifier.parameters)
        self.assertEqual(parameters, ["lien", "mentions"])


if __name__ == "__main__":
    unittest.main()
