#!/usr/bin/env python3
import json
from pathlib import Path

p = Path("/home/ubuntu/zaeldryk/state/live-polls.json")
data = json.loads(p.read_text(encoding="utf-8"))
for poll in data.values():
    poll["results_posted"] = True
p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
print("marked results_posted for", len(data), "polls")
