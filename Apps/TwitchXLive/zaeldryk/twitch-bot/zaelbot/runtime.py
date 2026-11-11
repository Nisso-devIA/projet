"""Boucle Twitch : chat, EventSub, relais TikTok. Aucun envoi tant que le .env est vide."""

from __future__ import annotations

import asyncio
import datetime
import json
import logging
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from twitchio.ext import commands

from zaelbot.auth import refresh_token
from zaelbot.commands import CooldownBook, CommandBook, manage_command, parse_command, render_response, save_commands
from zaelbot.events import event_from_notification, render_event, tiktok_line
from zaelbot.greeting import DEFAULT_DELAY_SECONDS, DEFAULT_RULES_TEXT, LiveGreeting
from zaelbot.helix_text import followage_text, shoutout_text, uptime_text
from zaelbot.moderation import ModerationConfig, ModerationState, hate_command, sanction_line
from zaelbot.permissions import allows, permission_level
from zaelbot.store import atomic_write, ensure_copy, read_json
from zaelbot.tiktok_filter import TikTokFilter
from zaelbot.timers import Timer, TimerScheduler

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
LOG_DIR = ROOT / "logs"
CHANNEL_LOGIN = os.environ.get("TWITCH_CHANNEL", "zaeldryk").lower()
BROADCASTER_ID = os.environ.get("TWITCH_BROADCASTER_ID", "")
BOT_LOGIN = os.environ.get("TWITCH_BOT_LOGIN", "").lower()
BOT_USER_ID = os.environ.get("TWITCH_BOT_USER_ID", "")

log = logging.getLogger("zaelbot")


def _setup_logging() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    level = getattr(logging, os.environ.get("LOG_LEVEL", "INFO").upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(LOG_DIR / "bot.log", encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )


def _load_book() -> CommandBook:
    ensure_copy(ROOT / "commands.example.json", DATA / "commands.json")
    raw = read_json(DATA / "commands.json", {})
    return CommandBook(raw if isinstance(raw, dict) else {})


def _load_moderation() -> ModerationState:
    ensure_copy(ROOT / "moderation.example.json", DATA / "moderation.json")
    raw = read_json(DATA / "moderation.json", {})
    strikes = read_json(DATA / "vulgar-strikes.json", {})
    return ModerationState(
        ModerationConfig.from_dict(raw if isinstance(raw, dict) else {}),
        strikes if isinstance(strikes, dict) else {},
    )


def _load_greeting() -> LiveGreeting:
    ensure_copy(ROOT / "regles.example.txt", DATA / "regles.txt")
    text = (DATA / "regles.txt").read_text(encoding="utf-8").strip() or DEFAULT_RULES_TEXT
    ensure_copy(ROOT / "greeting.example.json", DATA / "greeting.json")
    raw = read_json(DATA / "greeting.json", {})
    delay = DEFAULT_DELAY_SECONDS
    sent = []
    if isinstance(raw, dict):
        delay = int(raw.get("delay_seconds") or DEFAULT_DELAY_SECONDS)
        sent = list(raw.get("sent_stream_ids") or [])
    return LiveGreeting(text, delay, sent)


def _save_greeting(greeting: LiveGreeting) -> None:
    atomic_write(
        DATA / "greeting.json",
        {"delay_seconds": greeting.delay_seconds, "sent_stream_ids": sorted(greeting.sent)},
    )


def _load_timers() -> TimerScheduler:
    ensure_copy(ROOT / "timers.example.json", DATA / "timers.json")
    raw = read_json(DATA / "timers.json", [])
    timers = [Timer.from_dict(item) for item in raw] if isinstance(raw, list) else []
    return TimerScheduler(timers)


def _load_templates() -> dict:
    ensure_copy(ROOT / "events.example.json", DATA / "events.json")
    raw = read_json(DATA / "events.json", {})
    return raw if isinstance(raw, dict) else {}


class Helix:
    def __init__(self, client_id: str, token: str) -> None:
        self.client_id = client_id
        self.token = token

    def _request(self, method: str, path: str, body: dict | None = None, query: dict | None = None):
        url = "https://api.twitch.tv/helix" + path
        if query:
            url += "?" + urllib.parse.urlencode(query)
        data = json.dumps(body).encode() if body is not None else None
        request = urllib.request.Request(
            url,
            data=data,
            method=method,
            headers={
                "Client-Id": self.client_id,
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                raw = response.read()
                return response.status, json.loads(raw) if raw else {}
        except urllib.error.HTTPError as exc:
            return exc.code, {}

    def stream_started_at(self) -> str | None:
        status, payload = self._request("GET", "/streams", query={"user_id": BROADCASTER_ID})
        if status != 200:
            return None
        data = payload.get("data") or []
        if not data:
            return None
        return data[0].get("started_at")

    def channel(self) -> dict:
        status, payload = self._request("GET", "/channels", query={"broadcaster_id": BROADCASTER_ID})
        if status != 200 or not payload.get("data"):
            return {}
        return payload["data"][0]

    def set_channel(self, title: str | None = None, game_id: str | None = None) -> bool:
        body = {"broadcaster_id": BROADCASTER_ID}
        # Helix wants the id in the query for this endpoint.
        query = {"broadcaster_id": BROADCASTER_ID}
        payload = {}
        if title is not None:
            payload["title"] = title
        if game_id is not None:
            payload["game_id"] = game_id
        status, _ = self._request("PATCH", "/channels", body=payload, query=query)
        return status == 204

    def search_game(self, query: str) -> str | None:
        status, payload = self._request("GET", "/search/categories", query={"query": query, "first": 1})
        if status != 200 or not payload.get("data"):
            return None
        return payload["data"][0].get("id")

    def followed_at(self, user_id: str) -> str | None:
        status, payload = self._request(
            "GET",
            "/channels/followers",
            query={"broadcaster_id": BROADCASTER_ID, "user_id": user_id, "first": 1},
        )
        if status != 200 or not payload.get("data"):
            return None
        return payload["data"][0].get("followed_at")

    def user_by_login(self, login: str) -> dict | None:
        status, payload = self._request("GET", "/users", query={"login": login.lower()})
        if status != 200 or not payload.get("data"):
            return None
        return payload["data"][0]

    def timeout(self, user_id: str, duration: int, reason: str) -> None:
        self._request(
            "POST",
            "/moderation/bans",
            body={"data": {"user_id": user_id, "duration": duration, "reason": reason[:200]}},
            query={"broadcaster_id": BROADCASTER_ID, "moderator_id": BOT_USER_ID},
        )

    def ban(self, user_id: str, reason: str) -> None:
        self._request(
            "POST",
            "/moderation/bans",
            body={"data": {"user_id": user_id, "reason": reason[:200]}},
            query={"broadcaster_id": BROADCASTER_ID, "moderator_id": BOT_USER_ID},
        )

    def delete_message(self, message_id: str) -> None:
        self._request(
            "DELETE",
            "/moderation/chat",
            query={
                "broadcaster_id": BROADCASTER_ID,
                "moderator_id": BOT_USER_ID,
                "message_id": message_id,
            },
        )

    def shoutout(self, to_broadcaster_id: str) -> None:
        self._request(
            "POST",
            "/chat/shoutouts",
            query={
                "from_broadcaster_id": BROADCASTER_ID,
                "to_broadcaster_id": to_broadcaster_id,
                "moderator_id": BOT_USER_ID,
            },
        )

    def subscribe_event(self, session_id: str, event_type: str, version: str, condition: dict) -> int:
        status, _ = self._request(
            "POST",
            "/eventsub/subscriptions",
            body={
                "type": event_type,
                "version": version,
                "condition": condition,
                "transport": {"method": "websocket", "session_id": session_id},
            },
        )
        return status


class ZaelBot(commands.Bot):
    def __init__(self, token: str) -> None:
        super().__init__(token=token, prefix="!", initial_channels=[CHANNEL_LOGIN])
        self.book = _load_book()
        self.moderation = _load_moderation()
        self.timers = _load_timers()
        self.templates = _load_templates()
        self.cooldowns = CooldownBook()
        self.relay_enabled = os.environ.get("TIKTOK_RELAY", "0") == "1"
        self.greeting = _load_greeting()
        self.tiktok_filter = TikTokFilter()
        self.helix = Helix(os.environ["TWITCH_CLIENT_ID"], token)
        self._token = token

    async def event_ready(self) -> None:
        log.info("Connecté au chat de #%s", CHANNEL_LOGIN)
        asyncio.create_task(self._greet_current_live())
        asyncio.create_task(self._timers_loop())
        asyncio.create_task(self._eventsub_loop())
        asyncio.create_task(self._tiktok_loop())
        asyncio.create_task(self._refresh_loop())

    async def event_message(self, message) -> None:
        if message.echo or message.author is None:
            return
        author = message.author
        level = permission_level(
            author.badges,
            is_mod=author.is_mod,
            is_sub=author.is_subscriber,
            is_vip=author.is_vip,
        )
        text = message.content or ""
        action = self.moderation.inspect(
            author.name,
            text,
            _wall_now(),
            level=level,
            first_message=bool(getattr(message, "first", False)),
        )
        if action is not None:
            await self._apply_sanction(message, action)
            return
        parsed = parse_command(text)
        if parsed is None:
            self.timers.on_chat_message()
            return
        name, args = parsed
        reply = await self._dispatch(name, args, author, level)
        if reply:
            channel = message.channel
            await channel.send(reply[:450])

    async def _dispatch(self, name: str, args: str, author, level: str) -> str | None:
        now = _now()
        if name == "regles":
            if not self.cooldowns.ready(name, author.name, now, 10, 30):
                return None
            self.cooldowns.mark(name, author.name, now, 10, 30)
            return self.greeting.text
        if name in {"addhate", "delhate"}:
            reply = hate_command(self.moderation, name, args, level)
            if reply.startswith("Terme "):
                atomic_write(DATA / "moderation.json", _config_dict(self.moderation.config))
            return reply
        if name in {"addcmd", "editcmd", "delcmd"}:
            reply = manage_command(self.book, name, args, level)
            if reply.startswith("Commande "):
                save_commands(DATA / "commands.json", self.book)
            return reply
        if name == "permit":
            if not allows(level, "mod"):
                return "Réservé aux modérateurs."
            target = args.split()[0] if args else ""
            if not target:
                return "Usage : !permit pseudo"
            self.moderation.grant_permit(target, now)
            return f"{target} peut poster un lien pendant {int(self.moderation.config.permit_seconds)} s."
        if name == "relais":
            if not allows(level, "mod"):
                return "Réservé aux modérateurs."
            choice = args.strip().lower()
            if choice not in {"on", "off"}:
                return "Usage : !relais on ou !relais off"
            self.relay_enabled = choice == "on"
            return "Relais TikTok activé." if self.relay_enabled else "Relais TikTok coupé."
        if name in {"commandes", "commands"}:
            names = ["uptime", "followage", "so", "titre", "jeu", "permit", "relais", "regles"] + self.book.visible_names()
            return "Commandes : " + ", ".join(f"!{item}" for item in names)
        if name in {"uptime", "followage", "so", "shoutout", "titre", "title", "jeu", "game"}:
            if not self.cooldowns.ready(name, author.name, now, 10, 15):
                return None
            self.cooldowns.mark(name, author.name, now, 10, 15)
            return await asyncio.to_thread(self._builtin, name, args, author, level)
        command = self.book.get(name)
        if command is None:
            return None
        if not allows(level, command.permission):
            return None
        if not self.cooldowns.ready(name, author.name, now, command.cooldown, command.user_cooldown):
            return None
        self.cooldowns.mark(name, author.name, now, command.cooldown, command.user_cooldown)
        return render_response(command.response, author.display_name or author.name, args, CHANNEL_LOGIN)

    def _builtin(self, name: str, args: str, author, level: str) -> str | None:
        import datetime as dt

        if name == "uptime":
            return uptime_text(self.helix.stream_started_at(), dt.datetime.now(dt.timezone.utc))
        if name == "followage":
            if not author.id:
                return "Impossible de lire ce follow."
            return followage_text(author.display_name or author.name, self.helix.followed_at(author.id), dt.datetime.now(dt.timezone.utc))
        if name in {"so", "shoutout"}:
            if not allows(level, "mod"):
                return "Réservé aux modérateurs."
            login = args.split()[0].lstrip("@") if args else ""
            if not login:
                return "Usage : !so pseudo"
            user = self.helix.user_by_login(login)
            if not user:
                return "Chaîne introuvable."
            self.helix.shoutout(user["id"])
            return shoutout_text(user.get("login") or login)
        if name in {"titre", "title"}:
            if not args:
                return self.helix.channel().get("title") or "Titre indisponible."
            if not allows(level, "mod"):
                return "Réservé aux modérateurs."
            if not self.helix.set_channel(title=args[:140]):
                return "Le titre n'a pas pu être changé."
            return "Titre mis à jour."
        if name in {"jeu", "game"}:
            current = self.helix.channel().get("game_name") or "Jeu indisponible."
            if not args:
                return f"Jeu en cours : {current}"
            if not allows(level, "mod"):
                return "Réservé aux modérateurs."
            game_id = self.helix.search_game(args)
            if not game_id or not self.helix.set_channel(game_id=game_id):
                return "Le jeu n'a pas pu être changé."
            return "Jeu mis à jour."
        return None

    async def _timers_loop(self) -> None:
        await self.wait_for_ready()
        while True:
            await asyncio.sleep(15)
            channel = self.get_channel(CHANNEL_LOGIN)
            if channel is None:
                continue
            for timer in self.timers.due(_now()):
                await channel.send(timer.message[:450])

    async def _refresh_loop(self) -> None:
        while True:
            await asyncio.sleep(1800)
            try:
                bundle = await asyncio.to_thread(
                    refresh_token,
                    os.environ["TWITCH_CLIENT_ID"],
                    os.environ["TWITCH_CLIENT_SECRET"],
                    os.environ["TWITCH_BOT_REFRESH_TOKEN"],
                )
            except Exception as exc:
                log.warning("Refresh du jeton impossible : %s", exc)
                continue
            self._token = bundle.access_token
            self.helix.token = bundle.access_token
            os.environ["TWITCH_BOT_ACCESS_TOKEN"] = bundle.access_token
            os.environ["TWITCH_BOT_REFRESH_TOKEN"] = bundle.refresh_token
            _write_env_tokens(bundle.access_token, bundle.refresh_token)
            log.info("Jeton du bot rafraîchi")

    async def _eventsub_loop(self) -> None:
        import aiohttp

        url = "wss://eventsub.wss.twitch.tv/ws?keepalive_timeout_seconds=30"
        while True:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.ws_connect(url) as ws:
                        async for raw in ws:
                            if raw.type != aiohttp.WSMsgType.TEXT:
                                continue
                            message = json.loads(raw.data)
                            kind = message.get("metadata", {}).get("message_type")
                            payload = message.get("payload", {})
                            if kind == "session_welcome":
                                session_id = payload["session"]["id"]
                                await asyncio.to_thread(self._subscribe_all, session_id)
                            elif kind == "session_reconnect":
                                url = payload["session"]["reconnect_url"]
                                break
                            elif kind == "notification":
                                if payload.get("subscription", {}).get("type") == "stream.online":
                                    await self._on_stream_online(payload.get("event") or {})
                                else:
                                    await self._on_notification(payload)
            except Exception as exc:
                log.warning("EventSub interrompu : %s", type(exc).__name__)
                await asyncio.sleep(10)

    def _subscribe_all(self, session_id: str) -> None:
        moderator = BOT_USER_ID or BROADCASTER_ID
        specs = [
            ("channel.follow", "2", {"broadcaster_user_id": BROADCASTER_ID, "moderator_user_id": moderator}),
            ("channel.subscribe", "1", {"broadcaster_user_id": BROADCASTER_ID}),
            ("channel.subscription.message", "1", {"broadcaster_user_id": BROADCASTER_ID}),
            ("channel.subscription.gift", "1", {"broadcaster_user_id": BROADCASTER_ID}),
            ("channel.cheer", "1", {"broadcaster_user_id": BROADCASTER_ID}),
            ("channel.raid", "1", {"to_broadcaster_user_id": BROADCASTER_ID}),
            ("stream.online", "1", {"broadcaster_user_id": BROADCASTER_ID}),
        ]
        for event_type, version, condition in specs:
            status = self.helix.subscribe_event(session_id, event_type, version, condition)
            log.info("EventSub %s -> %s", event_type, status)

    async def _on_notification(self, payload: dict) -> None:
        event_type = payload.get("subscription", {}).get("type", "")
        event = payload.get("event") or {}
        parsed = event_from_notification(event_type, event)
        if parsed is None:
            return
        kind, data = parsed
        text = render_event(kind, data, self.templates)
        channel = self.get_channel(CHANNEL_LOGIN)
        if channel is None or not text:
            return
        await channel.send(text[:450])
        if kind == "raid" and data.get("from_id"):
            await asyncio.to_thread(self.helix.shoutout, data["from_id"])

    async def _tiktok_loop(self) -> None:
        unique = os.environ.get("TIKTOK_UNIQUE_ID", "zaeldryk").lstrip("@")
        while True:
            if not self.relay_enabled:
                await asyncio.sleep(5)
                continue
            try:
                await self._tiktok_once(unique)
            except Exception as exc:
                log.warning("Relais TikTok en pause : %s", type(exc).__name__)
                await asyncio.sleep(30)

    async def _tiktok_once(self, unique: str) -> None:
        from TikTokLive import TikTokLiveClient
        from TikTokLive.events import CommentEvent, LiveEndEvent

        client = TikTokLiveClient(unique_id=unique)

        @client.on(CommentEvent)
        async def on_comment(event) -> None:
            if not self.relay_enabled:
                return
            author = getattr(getattr(event, "user", None), "nickname", None) or "tiktok"
            text = getattr(event, "comment", "") or ""
            line = tiktok_line(str(author), str(text))
            if line is None or not self.tiktok_filter.accept(str(author), line, _now()):
                return
            channel = self.get_channel(CHANNEL_LOGIN)
            if channel is not None:
                await channel.send(line[:450])

        @client.on(LiveEndEvent)
        async def on_end(_event) -> None:
            raise RuntimeError("live tiktok terminé")

        await client.connect()

    async def send_relay(self, line: str) -> None:
        channel = self.get_channel(CHANNEL_LOGIN)
        if channel is not None and self.relay_enabled:
            await channel.send(line[:450])

    async def _apply_sanction(self, message, action) -> None:
        author = message.author
        _log_sanction(author.name, action.reason, action.action)
        if action.reason == "vulgarite":
            atomic_write(DATA / "vulgar-strikes.json", self.moderation.export_strikes())
        if getattr(message, "id", None):
            await asyncio.to_thread(self.helix.delete_message, message.id)
        if action.warning:
            await message.channel.send(action.warning[:450])
        if not author.id:
            return
        if action.action == "ban":
            await asyncio.to_thread(self.helix.ban, author.id, action.reason)
        elif action.action == "timeout" and action.duration:
            await asyncio.to_thread(self.helix.timeout, author.id, action.duration, action.reason)

    async def _greet_current_live(self) -> None:
        started = await asyncio.to_thread(self.helix.stream_started_at)
        if started:
            await self._schedule_greeting(started, started)

    async def _on_stream_online(self, event: dict) -> None:
        started = str(event.get("started_at") or "")
        if started:
            await self._schedule_greeting(started, started)

    async def _schedule_greeting(self, stream_id: str, started_at: str) -> None:
        if not self.greeting.claim(stream_id):
            return
        try:
            started = datetime.datetime.fromisoformat(started_at.replace("Z", "+00:00"))
        except ValueError:
            self.greeting.cancel(stream_id)
            return
        wait = self.greeting.wait_seconds(started, datetime.datetime.now(datetime.timezone.utc))
        await asyncio.sleep(wait)
        channel = None
        for _ in range(6):
            channel = self.get_channel(CHANNEL_LOGIN)
            if channel is not None:
                break
            await asyncio.sleep(5)
        if channel is None:
            self.greeting.cancel(stream_id)
            return
        try:
            await channel.send(self.greeting.text[:450])
        except Exception as exc:
            self.greeting.cancel(stream_id)
            log.warning("Message de règles non envoyé : %s", type(exc).__name__)
            return
        self.greeting.mark_sent(stream_id)
        _save_greeting(self.greeting)
        log.info("Message de règles envoyé pour le live %s", stream_id)


def _log_sanction(user: str, rule: str, action: str) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    with (LOG_DIR / "moderation.log").open("a", encoding="utf-8") as handle:
        handle.write(sanction_line(user, rule, action, stamp))


def _config_dict(config) -> dict:
    from dataclasses import asdict

    return asdict(config)


def _wall_now() -> float:
    import time

    return time.time()


def _now() -> float:
    import time

    return time.monotonic()


def _write_env_tokens(access_token: str, refresh_token_value: str) -> None:
    path = ROOT / ".env"
    if not path.exists():
        return
    lines = path.read_text(encoding="utf-8").splitlines()
    updates = {
        "TWITCH_BOT_ACCESS_TOKEN": access_token,
        "TWITCH_BOT_REFRESH_TOKEN": refresh_token_value,
    }
    seen = set()
    out = []
    for line in lines:
        key = line.split("=", 1)[0] if "=" in line else ""
        if key in updates:
            out.append(f"{key}={updates[key]}")
            seen.add(key)
        else:
            out.append(line)
    for key, value in updates.items():
        if key not in seen:
            out.append(f"{key}={value}")
    temporary = path.with_suffix(".env.tmp")
    temporary.write_text("\n".join(out) + "\n", encoding="utf-8")
    temporary.replace(path)
    os.chmod(path, 0o600)


def missing_settings() -> list[str]:
    required = ["TWITCH_CLIENT_ID", "TWITCH_CLIENT_SECRET", "TWITCH_BOT_ACCESS_TOKEN", "TWITCH_BOT_REFRESH_TOKEN"]
    return [key for key in required if not os.environ.get(key)]


def main() -> None:
    _setup_logging()
    missing = missing_settings()
    if missing:
        log.error("Configuration incomplète : %s", ", ".join(missing))
        raise SystemExit(1)
    token = os.environ["TWITCH_BOT_ACCESS_TOKEN"]
    if token.startswith("oauth:"):
        token = token.split(":", 1)[1]
    bot = ZaelBot(token)
    bot.run()


if __name__ == "__main__":
    main()
