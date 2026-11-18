"""Join-to-create voice rooms for Salon Vocal temporaire.

Channel ids are fixed. Tracked room ids live in a JSON file so an empty
room is still removed after a restart. The hub channel is never deleted.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

GUILD_ID = 867426693286461490
CATEGORY_ID = 992441333161660477  # Salon Vocal temporaire
HUB_CHANNEL_ID = 992441334352855130  # ↪ Créer un salon vocal
STATE_FILE = Path("/home/ubuntu/zaeldryk/state/temp-voice.json")
EMPTY_GRACE_SECONDS = 5
NAME_LIMIT = 100

_file_lock = asyncio.Lock()


def channel_name(display_name: str) -> str:
    cleaned = " ".join((display_name or "").replace("\n", " ").split())
    if not cleaned:
        cleaned = "membre"
    room = f"🔊 Salon de {cleaned}"
    if len(room) <= NAME_LIMIT:
        return room
    return room[:NAME_LIMIT].rstrip()


def load_channel_ids(path: Path = STATE_FILE) -> list[int]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    raw = data.get("channel_ids") if isinstance(data, dict) else None
    ids: list[int] = []
    for item in raw or []:
        try:
            channel_id = int(item)
        except (TypeError, ValueError):
            continue
        if channel_id != HUB_CHANNEL_ID and channel_id not in ids:
            ids.append(channel_id)
    return ids


def save_channel_ids(ids: list[int], path: Path = STATE_FILE) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    kept: list[int] = []
    for channel_id in ids:
        if channel_id == HUB_CHANNEL_ID or channel_id in kept:
            continue
        kept.append(int(channel_id))
    path.write_text(
        json.dumps({"channel_ids": kept}, indent=2) + "\n",
        encoding="utf-8",
    )


def deletion_allowed(channel_id: int, member_count: int, tracked: set[int]) -> bool:
    if channel_id == HUB_CHANNEL_ID or channel_id not in tracked:
        return False
    return member_count <= 0


def register_temp_voice(bot) -> None:
    import discord

    creating: set[int] = set()

    async def remember(channel_id: int) -> None:
        async with _file_lock:
            ids = load_channel_ids()
            if channel_id != HUB_CHANNEL_ID and channel_id not in ids:
                ids.append(channel_id)
            save_channel_ids(ids)

    async def forget(channel_id: int) -> None:
        async with _file_lock:
            ids = [item for item in load_channel_ids() if item != channel_id]
            save_channel_ids(ids)

    async def delete_room(channel) -> None:
        if channel is None or channel.id == HUB_CHANNEL_ID:
            return
        try:
            await channel.delete(reason="Salon vocal temporaire vide")
            print(f"Temp voice deleted {channel.id}", flush=True)
        except discord.NotFound:
            pass
        except discord.HTTPException as exc:
            print(f"Temp voice delete error {channel.id}: {exc}", flush=True)
            return
        await forget(channel.id)

    async def create_room(member) -> None:
        if member.id in creating:
            return
        creating.add(member.id)
        try:
            guild = member.guild
            category = guild.get_channel(CATEGORY_ID)
            if category is None:
                category = await bot.fetch_channel(CATEGORY_ID)
            created = await guild.create_voice_channel(
                channel_name(member.display_name),
                category=category,
                reason="Salon vocal temporaire",
            )
            await remember(created.id)
            print(f"Temp voice created {created.id} {created.name!r}", flush=True)
            try:
                await created.set_permissions(
                    member,
                    manage_channels=True,
                    move_members=True,
                    reason="Créateur du salon temporaire",
                )
            except discord.HTTPException as exc:
                print(f"Temp voice overwrite error {created.id}: {exc}", flush=True)
            try:
                await member.move_to(created, reason="Salon vocal temporaire")
            except discord.HTTPException as exc:
                print(f"Temp voice move error {created.id}: {exc}", flush=True)
                if not created.members:
                    await delete_room(created)
        except discord.HTTPException as exc:
            print(f"Temp voice create error: {exc}", flush=True)
        finally:
            creating.discard(member.id)

    async def cleanup_later(channel_id: int) -> None:
        if channel_id == HUB_CHANNEL_ID:
            return
        await asyncio.sleep(EMPTY_GRACE_SECONDS)
        tracked = set(load_channel_ids())
        if not deletion_allowed(channel_id, 0, tracked):
            return
        channel = bot.get_channel(channel_id)
        if channel is None:
            try:
                channel = await bot.fetch_channel(channel_id)
            except discord.NotFound:
                await forget(channel_id)
                return
            except discord.HTTPException as exc:
                print(f"Temp voice fetch error {channel_id}: {exc}", flush=True)
                return
        if not isinstance(channel, discord.VoiceChannel):
            return
        if deletion_allowed(channel.id, len(channel.members), set(load_channel_ids())):
            await delete_room(channel)

    async def on_voice_state_update(member, before, after) -> None:
        if member.bot or member.guild is None or member.guild.id != GUILD_ID:
            return
        joined_hub = after.channel is not None and after.channel.id == HUB_CHANNEL_ID
        came_from_hub = before.channel is not None and before.channel.id == HUB_CHANNEL_ID
        if joined_hub and not came_from_hub:
            await create_room(member)
        before_id = before.channel.id if before.channel is not None else None
        after_id = after.channel.id if after.channel is not None else None
        if before_id and before_id != after_id and before_id in set(load_channel_ids()):
            asyncio.create_task(cleanup_later(before_id))

    bot.add_listener(on_voice_state_update, "on_voice_state_update")


async def cleanup_empty_temp_channels(bot) -> int:
    """Delete tracked rooms that are already empty. Leaves the hub alone."""
    import discord

    guild = bot.get_guild(GUILD_ID)
    if guild is None:
        return 0
    removed = 0
    for channel_id in list(load_channel_ids()):
        if channel_id == HUB_CHANNEL_ID:
            continue
        channel = guild.get_channel(channel_id)
        if channel is None:
            try:
                channel = await bot.fetch_channel(channel_id)
            except discord.NotFound:
                async with _file_lock:
                    save_channel_ids([item for item in load_channel_ids() if item != channel_id])
                continue
            except discord.HTTPException as exc:
                print(f"Temp voice startup fetch error {channel_id}: {exc}", flush=True)
                continue
        if not isinstance(channel, discord.VoiceChannel):
            continue
        if not deletion_allowed(channel.id, len(channel.members), set(load_channel_ids())):
            continue
        try:
            await channel.delete(reason="Salon vocal temporaire vide")
        except discord.NotFound:
            pass
        except discord.HTTPException as exc:
            print(f"Temp voice startup delete error {channel_id}: {exc}", flush=True)
            continue
        async with _file_lock:
            save_channel_ids([item for item in load_channel_ids() if item != channel_id])
        removed += 1
        print(f"Temp voice startup deleted {channel_id}", flush=True)
    return removed
