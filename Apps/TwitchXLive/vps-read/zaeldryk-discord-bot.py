import asyncio
from datetime import datetime
from pathlib import Path

import discord
from discord.ext import commands
from discord.ui import Button, View

def _discord_token() -> str:
    path = Path("/home/ubuntu/zaeldryk/config/discord.env")
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("DISCORD_BOT_TOKEN="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise RuntimeError("DISCORD_BOT_TOKEN missing in discord.env")

BOT_TOKEN = _discord_token()
GUILD_ID = 867426693286461490

ROLE_DISCIPLE = "🐺 Disciple"
CHANNEL_REGLEMENT = "📖-règlement"
CHANNEL_BIENVENUE = "📜-bienvenue"
CHANNEL_LOGS = "📝-logs"
CHANNEL_MEMBERS_ID = 1541534998488813659  # ID salon 👥 Membres
CHANNEL_BOTS_ID = 1541534999549837402     # ID salon 🤖 Bots
CHANNEL_DEPARTS = "🚪-départs"  # nom exact du salon

intents = discord.Intents.default()
intents.members = True
intents.guilds = True
intents.moderation = True
intents.message_content = True
intents.invites = True

bot = commands.Bot(command_prefix="!", intents=intents)

class AcceptRulesView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="✅ J'accepte le règlement",
        style=discord.ButtonStyle.green,
        custom_id="accept_rules"
    )
    async def accept_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)

        role = discord.utils.get(interaction.guild.roles, name="🐺 Disciple")
        if role is None:
            await interaction.followup.send("Rôle introuvable.", ephemeral=True)
            return
        if role in interaction.user.roles:
            await interaction.followup.send("Tu as déjà accepté le règlement.", ephemeral=True)
            return

        await interaction.user.add_roles(role)

        bienvenue = discord.utils.get(
            interaction.guild.text_channels,
            name=CHANNEL_BIENVENUE
        )
        if bienvenue:
            embed = discord.Embed(
                title="⚔️ Bienvenue dans Zaeldryk_FR",
                description=(
                    f"Salut {interaction.user.mention} ! Content de t’avoir parmi nous ✨\n\n"
                    f"Tu as maintenant accès au serveur.\n"
                    f"👉 Présente-toi dans le salon <#1541274991197159444> pour qu’on fasse connaissance 🐺🐉"
                ),
                color=discord.Color.gold()
            )
            embed.set_image(url="https://i.imgur.com/tCDZtsy.jpeg")
            await bienvenue.send(embed=embed)

        await interaction.followup.send("✅ Accès débloqué", ephemeral=True)

        try:
            await update_member_counters(interaction.guild)
        except Exception:
            pass

@bot.event
async def on_ready():
    print(f"ZAELDRYK Discord Bot connecté : {bot.user}", flush=True)
    bot.add_view(AcceptRulesView())

    async def counter_loop():
        await bot.wait_until_ready()
        await asyncio.sleep(5)
        while not bot.is_closed():
            for g in bot.guilds:
                try:
                    await update_member_counters(g)
                except Exception as e:
                    print(f"Compteur erreur: {e}", flush=True)
            await asyncio.sleep(300)

    bot.loop.create_task(counter_loop())

@bot.event
async def on_member_join(member):
    await send_log(
        member.guild,
        "📥 Nouveau membre",
        f"{member.mention} (`{member}`) a rejoint",
        discord.Color.green()
    )
    try:
        await update_member_counters(member.guild)
    except Exception:
        pass

@bot.event
async def on_member_remove(member):
    ch = discord.utils.get(member.guild.text_channels, name="🚪-départs")
    if ch:
        embed = discord.Embed(
            title="👋 Départ",
            description=f"**{member}** a quitté le serveur.\nL'aventure s'arrête ici pour cette fois.",
            color=discord.Color.dark_grey()
        )
        embed.set_footer(text=f"ID : {member.id}")
        await ch.send(embed=embed)

    await send_log(
        member.guild,
        "📤 Membre parti",
        f"**{member}** (`{member.id}`) a quitté",
        discord.Color.orange()
    )

    try:
        await update_member_counters(member.guild)
    except Exception:
        pass

@bot.event
async def on_member_ban(guild, user):
    await send_log(guild, "🔨 Bannissement", f"**{user}** a été banni", discord.Color.red())

@bot.event
async def on_member_unban(guild, user):
    await send_log(guild, "♻️ Débannissement", f"**{user}** a été débanni", discord.Color.blue())

@bot.event
async def on_member_update(before, after):
    if before.roles != after.roles:
        added = [r for r in after.roles if r not in before.roles]
        removed = [r for r in before.roles if r not in after.roles]
        if added:
            await send_log(after.guild, "➕ Rôle ajouté", f"{after.mention} a reçu : {', '.join(r.mention for r in added)}", discord.Color.green())
        if removed:
            await send_log(after.guild, "➖ Rôle retiré", f"{after.mention} a perdu : {', '.join(r.mention for r in removed)}", discord.Color.orange())
    if before.nick != after.nick:
        await send_log(after.guild, "📝 Pseudo changé", f"{after.mention} : `{before.nick}` → `{after.nick}`", discord.Color.blue())

@bot.event
async def on_message_delete(message):
    if message.guild and message.author and not message.author.bot:
        content = message.content[:500] if message.content else "*contenu vide*"
        await send_log(message.guild, "🗑️ Message supprimé", f"**{message.author}** dans {message.channel.mention} :\n{content}", discord.Color.red())

@bot.event
async def on_message_edit(before, after):
    if after.guild and after.author and not after.author.bot and before.content != after.content:
        await send_log(after.guild, "✏️ Message modifié", f"**{after.author}** dans {after.channel.mention}\n**Avant :** {before.content[:300]}\n**Après :** {after.content[:300]}", discord.Color.gold())

@bot.event
async def on_guild_channel_create(channel):
    await send_log(channel.guild, "📁 Salon créé", f"**{channel.name}**", discord.Color.green())

@bot.event
async def on_guild_channel_delete(channel):
    await send_log(channel.guild, "📁 Salon supprimé", f"**{channel.name}**", discord.Color.red())

@bot.event
async def on_invite_create(invite):
    inviter = invite.inviter or "Inconnu"
    await send_log(invite.guild, "🔗 Invitation créée", f"Par **{inviter}** | code `{invite.code}`", discord.Color.blue())


async def send_log(guild, title, description, color):
    channel = discord.utils.get(guild.text_channels, name=CHANNEL_LOGS)
    if not channel:
        for c in guild.text_channels:
            if "log" in c.name.lower():
                channel = c
                break
    if channel:
        embed = discord.Embed(
            title=title,
            description=description,
            color=color,
            timestamp=datetime.utcnow(),
        )
        await channel.send(embed=embed)


async def update_member_counters(guild):
    members = sum(1 for m in guild.members if not m.bot)
    bots = sum(1 for m in guild.members if m.bot)
    ch_m = guild.get_channel(CHANNEL_MEMBERS_ID)
    ch_b = guild.get_channel(CHANNEL_BOTS_ID)
    if ch_m:
        new_name = f"👥 Membres : {members}"
        if ch_m.name != new_name:
            await ch_m.edit(name=new_name)
    if ch_b:
        new_name = f"🤖 Bots : {bots}"
        if ch_b.name != new_name:
            await ch_b.edit(name=new_name)


bot.run(BOT_TOKEN)
