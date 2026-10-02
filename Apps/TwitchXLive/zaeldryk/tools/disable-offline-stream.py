#!/usr/bin/env python3
"""Disable offline filler stream: env flag + stop service + drop reset cron."""
from pathlib import Path
import subprocess
import time

TWITCH_ENV = Path("/home/ubuntu/zaeldryk/config/twitch.env")
STAMP = time.strftime("%Y-%m-%d_%H%M")
BAK = Path(f"/home/ubuntu/backups/{STAMP}_disable-offline-stream")
BAK.mkdir(parents=True, exist_ok=True)


def upsert_env(path: Path, key: str, value: str) -> None:
    lines = path.read_text(encoding="utf-8").splitlines()
    out = []
    found = False
    for line in lines:
        if line.startswith(f"{key}="):
            out.append(f"{key}={value}")
            found = True
        else:
            out.append(line)
    if not found:
        out.append(f"{key}={value}")
    path.write_text("\n".join(out) + "\n", encoding="utf-8")


def main() -> None:
    BAK.joinpath("twitch.env").write_bytes(TWITCH_ENV.read_bytes())
    crontab = subprocess.check_output(["crontab", "-l"], text=True)
    BAK.joinpath("crontab.txt").write_text(crontab, encoding="utf-8")

    upsert_env(TWITCH_ENV, "OFFLINE_STREAM_ENABLED", "0")
    TWITCH_ENV.chmod(0o600)

    # Remove reset-offline cron line (optional keep; script is no-op anyway)
    lines = []
    for line in crontab.splitlines():
        if "reset-offline.sh" in line and not line.strip().startswith("#"):
            lines.append("# " + line + "  # disabled: offline stream off")
        else:
            lines.append(line)
    subprocess.run(["crontab", "-"], input="\n".join(lines) + "\n", text=True, check=True)

    subprocess.run(["sudo", "systemctl", "stop", "twitch-offline.service"], check=False)
    subprocess.run(["sudo", "systemctl", "disable", "twitch-offline.service"], check=False)

    # Cleanup leftover offline VODs
    subprocess.run(["/home/ubuntu/zaeldryk/twitch/delete-offline-vods.sh"], check=False)

    print("OFFLINE_STREAM_ENABLED=0")
    print("twitch-offline:", subprocess.check_output(["systemctl", "is-active", "twitch-offline"], text=True).strip())
    print("enabled:", subprocess.check_output(["systemctl", "is-enabled", "twitch-offline"], text=True).strip())
    print("crontab:")
    print(subprocess.check_output(["crontab", "-l"], text=True))


if __name__ == "__main__":
    main()
