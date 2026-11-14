"""Commandes personnalisées, cooldowns et commandes de gestion."""

from __future__ import annotations

import re
from dataclasses import dataclass

from zaelbot.permissions import allows
from zaelbot.store import atomic_write, read_json

NAME_RE = re.compile(r"^[a-z0-9_]{1,30}$")
BUILTINS = {
    "uptime",
    "followage",
    "so",
    "shoutout",
    "titre",
    "title",
    "jeu",
    "game",
    "permit",
    "addcmd",
    "editcmd",
    "delcmd",
    "commandes",
    "commands",
    "relais",
    "regles",
    "addhate",
    "delhate",
    "clip",
    "mort",
    "morts",
    "mortreset",
    "pari",
    "sondage",
}


@dataclass
class Command:
    name: str
    response: str
    permission: str = "everyone"
    cooldown: float = 10
    user_cooldown: float = 30
    enabled: bool = True
    aliases: tuple[str, ...] = ()


def parse_command(content: str, prefix: str = "!") -> tuple[str, str] | None:
    text = (content or "").strip()
    if not text.startswith(prefix):
        return None
    body = text[len(prefix):].strip()
    if not body:
        return None
    name, _, args = body.partition(" ")
    name = name.lower().lstrip(prefix).strip()
    if not name:
        return None
    return name, args.strip()


def render_response(template: str, user: str, args: str, channel: str) -> str:
    return (
        template.replace("{user}", user)
        .replace("{args}", args)
        .replace("{channel}", channel)
    )


class CooldownBook:
    def __init__(self) -> None:
        self.global_until: dict[str, float] = {}
        self.user_until: dict[tuple[str, str], float] = {}

    def ready(self, name: str, user: str, now: float, global_cd: float, user_cd: float) -> bool:
        if now < self.global_until.get(name, 0):
            return False
        if now < self.user_until.get((name, user.lower()), 0):
            return False
        return True

    def mark(self, name: str, user: str, now: float, global_cd: float, user_cd: float) -> None:
        if global_cd > 0:
            self.global_until[name] = now + global_cd
        if user_cd > 0:
            self.user_until[(name, user.lower())] = now + user_cd


class CommandBook:
    def __init__(self, commands: dict | None = None) -> None:
        self.commands: dict[str, Command] = {}
        self.aliases: dict[str, str] = {}
        for name, raw in (commands or {}).items():
            command = self._from_raw(name, raw)
            self.commands[command.name] = command
            for alias in command.aliases:
                self.aliases[alias] = command.name

    @staticmethod
    def _from_raw(name: str, raw: dict) -> Command:
        return Command(
            name=name.lower(),
            response=str(raw.get("response") or ""),
            permission=str(raw.get("permission") or "everyone"),
            cooldown=float(raw.get("cooldown") or 0),
            user_cooldown=float(raw.get("user_cooldown") or 0),
            enabled=bool(raw.get("enabled", True)),
            aliases=tuple(
                str(alias).lower().lstrip("!")
                for alias in (raw.get("aliases") or [])
                if str(alias).strip()
            ),
        )

    def to_dict(self) -> dict:
        return {
            cmd.name: {
                "response": cmd.response,
                "permission": cmd.permission,
                "cooldown": cmd.cooldown,
                "user_cooldown": cmd.user_cooldown,
                "enabled": cmd.enabled,
                **({"aliases": list(cmd.aliases)} if cmd.aliases else {}),
            }
            for cmd in self.commands.values()
        }

    def get(self, name: str) -> Command | None:
        key = name.lower()
        key = self.aliases.get(key, key)
        cmd = self.commands.get(key)
        if cmd is None or not cmd.enabled:
            return None
        return cmd

    def visible_names(self) -> list[str]:
        return sorted(cmd.name for cmd in self.commands.values() if cmd.enabled)

    def add(self, name: str, response: str) -> str | None:
        clean = name.lower().lstrip("!").strip()
        if not NAME_RE.match(clean):
            return "Nom de commande invalide."
        if clean in BUILTINS:
            return "Cette commande est réservée."
        if clean in self.commands:
            return "Cette commande existe déjà. Utilise !editcmd."
        if not response.strip():
            return "Il manque le texte de la commande."
        self.commands[clean] = Command(name=clean, response=response.strip())
        return None

    def edit(self, name: str, response: str) -> str | None:
        clean = name.lower().lstrip("!").strip()
        if clean not in self.commands:
            return "Commande introuvable."
        if not response.strip():
            return "Il manque le nouveau texte."
        self.commands[clean].response = response.strip()
        return None

    def delete(self, name: str) -> str | None:
        clean = name.lower().lstrip("!").strip()
        if clean not in self.commands:
            return "Commande introuvable."
        del self.commands[clean]
        return None


def load_commands(path) -> CommandBook:
    raw = read_json_safe(path)
    if not isinstance(raw, dict):
        raw = {}
    return CommandBook(raw)


def save_commands(path, book: CommandBook) -> None:
    atomic_write(path, book.to_dict())


def read_json_safe(path):
    from zaelbot.store import read_json

    return read_json(path, {})


def manage_command(book: CommandBook, name: str, args: str, level: str) -> str:
    if not allows(level, "mod"):
        return "Réservé aux modérateurs."
    if name == "addcmd":
        cmd_name, _, response = args.partition(" ")
        error = book.add(cmd_name, response)
        return error or f"Commande !{cmd_name.lower().lstrip('!')} ajoutée."
    if name == "editcmd":
        cmd_name, _, response = args.partition(" ")
        error = book.edit(cmd_name, response)
        return error or f"Commande !{cmd_name.lower().lstrip('!')} mise à jour."
    if name == "delcmd":
        error = book.delete(args)
        return error or f"Commande !{args.lower().lstrip('!')} supprimée."
    return "Commande de gestion inconnue."
