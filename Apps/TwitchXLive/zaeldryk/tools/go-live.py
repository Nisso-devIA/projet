#!/usr/bin/env python3
"""Lance un preset de live : titre + catégorie Twitch. OBS suit si le WebSocket est ouvert."""
from __future__ import annotations

import os
import shlex
import subprocess
import sys
from pathlib import Path

VPS = "ubuntu@57.128.177.132"
REMOTE = "/home/ubuntu/zaeldryk/tools/set-stream-title.py"


def ssh_key() -> Path:
    env = os.environ.get("ZAEL_SSH_KEY", "").strip()
    if env:
        return Path(env)
    names = ("vps to", "ssh-key-ovh-2026-08-28")
    repo_key = Path(__file__).resolve().parents[4].joinpath(*names)
    windows_key = Path(r"C:\Users\nacim\Documents\projet").joinpath(*names)
    for candidate in (repo_key, windows_key):
        if candidate.is_file():
            return candidate
    return repo_key


def remote_command(game: str, apply: bool) -> str:
    parts = ["python3", REMOTE, game]
    if apply:
        parts.append("--apply")
    return " ".join(shlex.quote(part) for part in parts)


def twitch(game: str, apply: bool) -> int:
    key = ssh_key()
    if not key.is_file():
        print(f"clé SSH introuvable : {key}")
        return 1
    cmd = [
        "ssh",
        "-i",
        str(key),
        "-o",
        "StrictHostKeyChecking=accept-new",
        VPS,
        remote_command(game, apply),
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
        print("obs non contacte pour", game, ": titre et categorie Twitch seulement.")
        return
    scene = cfg.get("OBS_SCENE") or "Scène"
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
