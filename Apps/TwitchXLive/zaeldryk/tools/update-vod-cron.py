#!/usr/bin/env python3
from pathlib import Path
import subprocess

old = "* /15 * * * * /home/ubuntu/zaeldryk/twitch/delete-offline-vods.sh"
# wrong - cron is */15
raw = subprocess.check_output(["crontab", "-l"], text=True)
lines = []
changed = False
for line in raw.splitlines():
    if line.strip().endswith("/home/ubuntu/zaeldryk/twitch/delete-offline-vods.sh"):
        lines.append("* * * * * /home/ubuntu/zaeldryk/twitch/delete-offline-vods.sh")
        changed = True
    else:
        lines.append(line)
if not changed:
    lines.append("* * * * * /home/ubuntu/zaeldryk/twitch/delete-offline-vods.sh")
text = "\n".join(lines) + "\n"
subprocess.run(["crontab", "-"], input=text, text=True, check=True)
print("CRON_UPDATED")
print(subprocess.check_output(["crontab", "-l"], text=True))
