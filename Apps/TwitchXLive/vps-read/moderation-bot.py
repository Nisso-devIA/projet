import asyncio
asyncio.set_event_loop(asyncio.new_event_loop())
from twitchio.ext import commands
import aiohttp
import re
from datetime import datetime, timedelta
from collections import defaultdict, deque
import json
import os

# === CONFIG ===
CLIENT_ID = "j2eaj1gxokr77a3lrzso63tr6wvk22"
TOKEN = open("/home/ubuntu/twitch_token.txt").read().strip()
BROADCASTER_ID = "426411773"
CHANNEL = "zaeldryk"
DATA_FILE = "/home/ubuntu/moderation_data.json"

TIMEOUTS = {
    3: 600,      # 10 min
    4: 3600,     # 1h
    5: 86400,    # 24h
}

BANNED_WORDS = [
    "fdp", "ntm", "nique", "enculé", "encule", "salope", "pute", "connard", "connasse",
    "pd", "tapette", "fgts", "fgt", "bâtard", "batard", "fils de pute",
    "fuck", "shit", "bitch", "asshole", "motherfucker", "cunt"
]

LINK_REGEX = re.compile(r"(https?://|www\.|\.com|\.fr|\.net|\.gg|\.tv|\.be|\.org)", re.IGNORECASE)
CAPS_THRESHOLD = 0.70
MIN_CAPS_LENGTH = 6
MAX_EMOTES = 6
MAX_SYMBOLS = 8
MAX_REPEATED_WORD = 4
SPAM_MESSAGES = 4
SPAM_WINDOW = 10  # secondes

class ModBot(commands.Bot):
    def __init__(self):
        super().__init__(token=TOKEN, prefix="!", initial_channels=[CHANNEL])
        self.warnings = self.load_data()
        self.user_messages = defaultdict(lambda: deque(maxlen=10))

    def load_data(self):
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r") as f:
                return defaultdict(int, json.load(f))
        return defaultdict(int)

    def save_data(self):
        with open(DATA_FILE, "w") as f:
            json.dump(dict(self.warnings), f)

    async def note_place(self, message, content):
        parts = content.split(None, 1)
        place = parts[1].strip() if len(parts) > 1 else ""
        path = "/home/ubuntu/zaeldryk/state/oot-place.txt"
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(place)
        if not place or place.lower() in {"reset", "stop", "aucun"}:
            reply = "Lieu effacé. Le titre redevient général."
        else:
            reply = f"Lieu noté : {place}. Le titre Twitch suit dans moins de 2 min."
        print(f"{datetime.now()} - !ici {place or '(reset)'}", flush=True)
        await message.channel.send(reply)

    async def event_ready(self):
        print(f"{datetime.now()} - Moderation Bot connecté (version complète)", flush=True)

    async def event_message(self, message):
        if message.echo or message.author is None:
            return

        content_now = (message.content or "").strip()
        if content_now.lower().startswith("!ici") and message.author.is_broadcaster:
            await self.note_place(message, content_now)
            return

        if message.author.is_broadcaster or message.author.is_mod:
            return

        author = message.author.name.lower()
        content = message.content.strip()
        content_lower = content.lower()
        now = datetime.now()

        reason = None

        # 1. Insultes
        for word in BANNED_WORDS:
            if re.search(rf"\b{re.escape(word)}\b", content_lower):
                reason = "Insulte"
                break

        # 2. Liens
        if not reason and LINK_REGEX.search(content):
            reason = "Lien non autorisé"

        # 3. Majuscules
        if not reason and len(content) >= MIN_CAPS_LENGTH:
            letters = [c for c in content if c.isalpha()]
            if letters and (sum(1 for c in letters if c.isupper()) / len(letters)) >= CAPS_THRESHOLD:
                reason = "Majuscules excessives"

        # 4. Excess Emotes (compte approximatif des :emote: et mots type Kappa)
        if not reason:
            emote_count = len(re.findall(r"\b\w+\b", content))  # approximation simple
            # Mieux: compter les emotes Twitch si possible, sinon on garde simple
            if content.count(":") >= 6 or content.count("Kappa") + content.count("Pog") > MAX_EMOTES:
                reason = "Trop d'emotes"

        # 5. Excess Symbols
        if not reason:
            symbols = len(re.findall(r"[^\w\s]", content))
            if symbols > MAX_SYMBOLS:
                reason = "Trop de symboles"

        # 6. Répétitions de mots
        if not reason:
            words = re.findall(r"\b\w+\b", content_lower)
            for w in set(words):
                if words.count(w) >= MAX_REPEATED_WORD and len(w) > 2:
                    reason = "Répétition de mots"
                    break

        # 7. Spam (trop de messages en peu de temps)
        if not reason:
            self.user_messages[author].append(now)
            recent = [t for t in self.user_messages[author] if (now - t).total_seconds() <= SPAM_WINDOW]
            if len(recent) >= SPAM_MESSAGES:
                reason = "Spam"

        if not reason:
            return

        # Application de la sanction
        self.warnings[author] += 1
        count = self.warnings[author]
        self.save_data()

        print(f"{datetime.now()} - {author} | Infraction #{count} ({reason}) : {content[:50]}", flush=True)

        if count == 1:
            await self.send_message(f"@{message.author.name} ⚠️ Avertissement 1/2 – {reason}")
        elif count == 2:
            await self.send_message(f"@{message.author.name} ⚠️ Avertissement 2/2 – {reason}. Prochain = timeout.")
        elif count in TIMEOUTS:
            seconds = TIMEOUTS[count]
            await self.timeout_user(message.author.id, seconds, reason)
            await self.send_message(f"@{message.author.name} ⏳ Timeout {self.format_time(seconds)} – {reason}")
        else:
            await self.ban_user(message.author.id, reason)
            await self.send_message(f"@{message.author.name} 🔨 Ban permanent – {reason}")
            if author in self.warnings:
                del self.warnings[author]
                self.save_data()

    async def send_message(self, text):
        url = "https://api.twitch.tv/helix/chat/messages"
        headers = {
            "Client-ID": CLIENT_ID,
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/json"
        }
        payload = {
            "broadcaster_id": BROADCASTER_ID,
            "sender_id": BROADCASTER_ID,
            "message": text
        }
        async with aiohttp.ClientSession() as session:
            await session.post(url, headers=headers, json=payload)

    async def timeout_user(self, user_id, duration, reason):
        url = f"https://api.twitch.tv/helix/moderation/bans?broadcaster_id={BROADCASTER_ID}&moderator_id={BROADCASTER_ID}"
        headers = {
            "Client-ID": CLIENT_ID,
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/json"
        }
        payload = {"data": {"user_id": str(user_id), "duration": duration, "reason": reason}}
        async with aiohttp.ClientSession() as session:
            await session.post(url, headers=headers, json=payload)

    async def ban_user(self, user_id, reason):
        url = f"https://api.twitch.tv/helix/moderation/bans?broadcaster_id={BROADCASTER_ID}&moderator_id={BROADCASTER_ID}"
        headers = {
            "Client-ID": CLIENT_ID,
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/json"
        }
        payload = {"data": {"user_id": str(user_id), "reason": reason}}
        async with aiohttp.ClientSession() as session:
            await session.post(url, headers=headers, json=payload)

    def format_time(self, seconds):
        if seconds < 3600:
            return f"{seconds // 60} min"
        if seconds < 86400:
            return f"{seconds // 3600}h"
        return "24h"

bot = ModBot()
bot.run()
