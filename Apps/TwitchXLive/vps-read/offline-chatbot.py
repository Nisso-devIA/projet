import asyncio
asyncio.set_event_loop(asyncio.new_event_loop())
from twitchio.ext import commands
import aiohttp
from datetime import datetime, timedelta

CLIENT_ID = "j2eaj1gxokr77a3lrzso63tr6wvk22"
TOKEN = open("/home/ubuntu/twitch_token.txt").read().strip()
BROADCASTER_ID = "426411773"
CHANNEL = "zaeldryk"

OFFLINE_MESSAGE = "⚔️ Salut l'ami(e) ! Je suis offline pour le moment. Le prochain live arrive bientôt — follow pour ne rien rater 🔔"
COOLDOWN = 300  # 5 minutes
last_reply = datetime.min

OFFLINE_KEYWORDS = ["offline", "ending", "brb", "fin de live", "hors ligne"]

# Comptes à ignorer (toi + bots éventuels)
IGNORED_USERS = ["zaeldryk", "streamelements", "nightbot", "moobot", "fossabot"]

class Bot(commands.Bot):
    def __init__(self):
        super().__init__(token=TOKEN, prefix="!", initial_channels=[CHANNEL])

    async def event_ready(self):
        print(f"{datetime.now()} - Bot connecté en tant que {self.nick}", flush=True)

    async def event_message(self, message):
        global last_reply

        if message.echo:
            return

        author = message.author.name.lower()

        # Ignore toi-même et les bots
        if author in IGNORED_USERS:
            return

        print(f"{datetime.now()} - Message reçu de {author}: {message.content}", flush=True)

        is_offline_mode = await self.is_offline_mode()
        print(f"{datetime.now()} - Mode offline ? {is_offline_mode}", flush=True)

        if not is_offline_mode:
            return

        now = datetime.now()
        if now - last_reply < timedelta(seconds=COOLDOWN):
            print(f"{datetime.now()} - Cooldown actif, on ignore", flush=True)
            return

        success = await self.send_helix_message(OFFLINE_MESSAGE)
        if success:
            last_reply = now
            print(f"{datetime.now()} - Réponse offline envoyée avec succès", flush=True)
        else:
            print(f"{datetime.now()} - Échec de l'envoi du message", flush=True)

    async def send_helix_message(self, text):
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
            async with session.post(url, headers=headers, json=payload) as resp:
                if resp.status == 200:
                    return True
                error = await resp.text()
                print(f"{datetime.now()} - Erreur API ({resp.status}): {error}", flush=True)
                return False

    async def is_offline_mode(self):
        url = f"https://api.twitch.tv/helix/streams?user_id={BROADCASTER_ID}"
        headers = {
            "Client-ID": CLIENT_ID,
            "Authorization": f"Bearer {TOKEN}"
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as resp:
                data = await resp.json()
                streams = data.get("data", [])
                if not streams:
                    return True
                title = streams[0].get("title", "").lower()
                print(f"{datetime.now()} - Titre : {title}", flush=True)
                return any(k in title for k in OFFLINE_KEYWORDS)

bot = Bot()
bot.run()
