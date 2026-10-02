#!/usr/bin/env python3
from pathlib import Path
import subprocess

cfg = Path("/home/ubuntu/zaeldryk/config")
for f in cfg.glob("*.env"):
    b = f.read_bytes()
    if b"\r" in b:
        f.write_bytes(b.replace(b"\r\n", b"\n").replace(b"\r", b"\n"))
        print("fixed CRLF", f.name)
    else:
        print("ok", f.name)

print("\n=== services ===")
print(
    subprocess.check_output(
        [
            "systemctl",
            "is-active",
            "moderation-bot",
            "offline-chatbot",
            "zaeldryk-discord",
            "twitch-offline",
            "whatsapp-bot",
            "zaeldryk-live",
        ],
        text=True,
    )
)

for name in ("moderation-bot.log", "offline-chatbot.log"):
    p = Path("/home/ubuntu/zaeldryk/logs") / name
    lines = p.read_text(errors="replace").splitlines()
    print(f"\n=== {name} tail ===")
    for line in lines[-20:]:
        print(line)

# Success markers
for name, needles in (
    ("moderation-bot.log", ("Ready", "ready", "connected", "Logged", "Listening", "ModBot")),
    ("offline-chatbot.log", ("Ready", "ready", "connected", "Logged", "Listening", "Bot")),
):
    text = Path("/home/ubuntu/zaeldryk/logs", name).read_text(errors="replace")
    hits = [n for n in needles if n.lower() in text.lower()]
    print(f"{name} markers: {hits or 'none'}")

wa = Path("/home/ubuntu/whatsapp-bot/logs/bot.log")
if wa.exists():
    text = wa.read_text(errors="replace")
    for needle in ("connection open", "Connection Open", "logged out", "QR", "error", "opened"):
        if needle.lower() in text.lower():
            print("whatsapp has:", needle)
    # last non-msg notify lines
    interesting = [
        ln
        for ln in text.splitlines()
        if any(x in ln.lower() for x in ("open", "connect", "qr", "error", "fail", "ready", "start"))
    ]
    print("\n=== whatsapp interesting tail ===")
    for ln in interesting[-15:]:
        print(ln[:200])
