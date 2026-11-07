#!/usr/bin/env python3
"""Lance un preset de live : titre + catégorie Twitch. OBS suit si le WebSocket est ouvert."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

KEY = Path(r"C:\Users\nacim\Documents\projet\vps to\ssh-key-ovh-2026-08-28")
VPS = "ubuntu@57.128.177.132"
REMOTE = "/home/ubuntu/zaeldryk/tools/set-stream-title.py"
OBS_SCENE = {
    "zelda": "Scène",
    "ocarina": "Scène",
    "oot": "Scène",
    "witcher": "Scène",
    "mario": "Scène",
}


def twitch(game: str, apply: bool) -> int:
    remote = "python3 " + REMOTE + " " + json.dumps(game)
    if apply:
        remote += " --apply"
    cmd = [
        "ssh",
        "-i",
        str(KEY),
        "-o",
        "StrictHostKeyChecking=no",
        VPS,
        remote,
    ]
    return subprocess.call(cmd)


def obs_env() -> dict:
    out = {}
    env = Path.home() / ".zaeldryk-obs.env"
    if not env.exists():
        return out
    for line in env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = v.strip()
    return out


def obs_scene(game: str) -> None:
    cfg = obs_env()
    host = cfg.get("OBS_HOST", "")
    if not host:
        print("obs non contacte : il est sur l autre PC. Titre et categorie Twitch seulement.")
        return
    low = game.lower()
    scene = cfg.get("OBS_SCENE") or "Scène"
    for key, name in OBS_SCENE.items():
        if key in low:
            scene = name
            break
    try:
        import obsws_python as obs
    except ImportError:
        print("obs ignore : module obsws-python absent. Scene voulue :", scene)
        return
    try:
        cl = obs.ReqClient(
            host=host,
            port=int(cfg.get("OBS_PORT", "4455")),
            password=cfg.get("OBS_WS_PASSWORD", ""),
            timeout=3,
        )
        cl.set_current_program_scene(scene)
        print("obs scene", scene, "sur", host)
    except Exception as exc:
        print("obs ignore", type(exc).__name__)


def main() -> int:
    args = [a for a in sys.argv[1:] if a != "--apply"]
    if not args:
        print("usage: go-live.py <jeu> [--apply]")
        return 1
    game = " ".join(args)
    code = twitch(game, "--apply" in sys.argv)
    if code == 0 and "--apply" in sys.argv:
        obs_scene(game)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
