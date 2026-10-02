#!/usr/bin/env python3
from pathlib import Path
import subprocess

def grep_file(path, needles, limit=30):
    lines = Path(path).read_text(errors="replace").splitlines()
    out = []
    for ln in lines:
        low = ln.lower()
        if any(n.lower() in low for n in needles):
            out.append(ln[:220])
    return out[-limit:]

print("=== moderation interesting ===")
for ln in grep_file(
    "/home/ubuntu/zaeldryk/logs/moderation-bot.log",
    ["ready", "connected", "listening", "error", "TypeError", "ModuleNotFound", "login", "joined", "channel"],
):
    print(ln)

print("\n=== offline interesting ===")
for ln in grep_file(
    "/home/ubuntu/zaeldryk/logs/offline-chatbot.log",
    ["ready", "connected", "listening", "error", "TypeError", "ModuleNotFound", "login", "joined", "channel"],
):
    print(ln)

print("\n=== discord interesting ===")
for ln in grep_file(
    "/home/ubuntu/zaeldryk/logs/discord-bot.log",
    ["connect", "ready", "error", "poll", "synced"],
):
    print(ln)

print("\n=== twitchio / discord.py versions ===")
print(subprocess.check_output(["python3", "-m", "pip", "show", "twitchio", "discord.py"], text=True, stderr=subprocess.STDOUT)[:800])

print("\n=== open fds / cwd of bots ===")
for pat in ("moderation-bot.py", "offline-chatbot.py", "zaeldryk-discord-bot.py", "whatsapp-bot/src/index.js"):
    try:
        out = subprocess.check_output(["pgrep", "-af", pat], text=True).strip()
        print(out or f"(no {pat})")
    except subprocess.CalledProcessError:
        print(f"DOWN {pat}")

# Check if IRC sockets open for twitch bots
print("\n=== network to twitch/discord (ss) ===")
try:
    ss = subprocess.check_output(["ss", "-tnp"], text=True, stderr=subprocess.DEVNULL)
    for needle in ("twitch", "discord", "whatsapp", "5222", "443"):
        pass
    interesting = [ln for ln in ss.splitlines() if any(x in ln for x in ("443", "6667", "6697")) and ("python" in ln or "node" in ln)]
    for ln in interesting[:25]:
        print(ln)
except Exception as e:
    print(e)

print("\n=== youtube clips last ===")
print(Path("/home/ubuntu/zaeldryk/logs/youtube-clips.log").read_text(errors="replace")[-500:])

print("\n=== freegames timer next / last ===")
print(subprocess.check_output(["systemctl", "list-timers", "zaeldryk-freegames.timer", "zaeldryk-news.timer", "--no-pager"], text=True))
