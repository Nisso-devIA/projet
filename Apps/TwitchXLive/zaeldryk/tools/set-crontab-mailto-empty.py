#!/usr/bin/env python3
import subprocess

raw = subprocess.check_output(["crontab", "-l"], text=True)
lines = raw.splitlines()
out = []
seen_mailto = False
for line in lines:
    if line.strip().startswith("MAILTO="):
        if not seen_mailto:
            out.append('MAILTO=""')
            seen_mailto = True
        continue
    out.append(line)
if not seen_mailto:
    out.insert(0, 'MAILTO=""')
text = "\n".join(out) + "\n"
subprocess.run(["crontab", "-"], input=text, text=True, check=True)
print(subprocess.check_output(["crontab", "-l"], text=True))
