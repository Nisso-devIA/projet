#!/usr/bin/env bash
# Create a full migration archive for zaeldryk stack → new VPS
set -euo pipefail

STAMP=$(date +%Y-%m-%d_%H%M)
OUT_ROOT="/home/ubuntu/backups/${STAMP}_vps-migration-pack"
PACK="$OUT_ROOT/zaeldryk-migration"
ARCHIVE="/home/ubuntu/backups/${STAMP}_zaeldryk-vps-migration.tar.gz"

mkdir -p "$PACK"/{systemd,cron,extras,manifest}

echo "==> Copying /home/ubuntu/zaeldryk (code + config + state)"
rsync -a --delete \
  --exclude '__pycache__/' \
  --exclude '*.pyc' \
  --exclude 'logs/*.log' \
  --exclude 'logs/*.bak' \
  --exclude 'state/*.flock' \
  --exclude 'state/*.lock' \
  /home/ubuntu/zaeldryk/ "$PACK/zaeldryk/"

# Keep log dir empty for structure
mkdir -p "$PACK/zaeldryk/logs"

echo "==> Systemd units"
for u in \
  zaeldryk-live.service \
  zaeldryk-discord.service \
  zaeldryk-discord-dump.service \
  zaeldryk-discord-dump.timer \
  zaeldryk-news.service \
  zaeldryk-news.timer \
  zaeldryk-freegames.service \
  zaeldryk-freegames.timer \
  zaeldryk-games-prompt.service \
  zaeldryk-games-prompt.timer \
  zaeldryk-watchdog.service \
  zaeldryk-watchdog.timer \
  twitch-offline.service \
  offline-chatbot.service \
  moderation-bot.service
do
  if [[ -f "/etc/systemd/system/$u" ]]; then
    cp -a "/etc/systemd/system/$u" "$PACK/systemd/"
  fi
done

echo "==> Crontab"
crontab -l > "$PACK/cron/ubuntu.crontab" 2>/dev/null || true
cp -a /home/ubuntu/zaeldryk/crontab.zaeldryk "$PACK/cron/" 2>/dev/null || true

echo "==> Extras (offline media, etc.)"
if [[ -f /home/ubuntu/thanks.mp4 ]]; then
  cp -a /home/ubuntu/thanks.mp4 "$PACK/extras/"
fi

# Token file path from twitch.env if present
if [[ -f /home/ubuntu/zaeldryk/config/twitch.env ]]; then
  # shellcheck disable=SC1091
  source /home/ubuntu/zaeldryk/config/twitch.env
  if [[ -n "${TWITCH_TOKEN_FILE:-}" && -f "$TWITCH_TOKEN_FILE" ]]; then
    mkdir -p "$PACK/extras/tokens"
    cp -a "$TWITCH_TOKEN_FILE" "$PACK/extras/tokens/"
    echo "TWITCH_TOKEN_FILE=$TWITCH_TOKEN_FILE" > "$PACK/extras/tokens/PATH.txt"
  fi
fi

# X config if any
if [[ -d /home/ubuntu/zaeldryk/config ]]; then
  find /home/ubuntu -maxdepth 2 -name 'x*.env' -o -name 'twitter*.env' 2>/dev/null \
    | head -20 > "$PACK/manifest/extra-env-paths.txt" || true
fi

echo "==> Manifest"
{
  echo "created_at=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "host=$(hostname)"
  echo "user=ubuntu"
  echo
  echo "=== enabled units ==="
  systemctl list-unit-files | grep -E 'zaeldryk|twitch-offline|offline-chatbot|moderation-bot' || true
  echo
  echo "=== timers ==="
  systemctl list-timers --all | grep -E 'zaeldryk|twitch' || true
  echo
  echo "=== crontab ==="
  crontab -l 2>/dev/null || true
  echo
  echo "=== tree (no secrets content) ==="
  find "$PACK/zaeldryk" -type f | sed "s|$PACK/||" | sort
} > "$PACK/manifest/INVENTORY.txt"

cat > "$PACK/RESTORE.md" << 'MD'
# Restauration zaeldryk sur un nouveau VPS

## 1. Prérequis
- Ubuntu 22.04+ (ou similaire)
- User `ubuntu` avec sudo
- Paquets: `python3`, `python3-aiohttp` (ou pip), `ffmpeg`, `curl`, `jq`, `rsync`

```bash
sudo apt update
sudo apt install -y python3 python3-pip ffmpeg curl jq rsync
pip3 install aiohttp discord.py  # selon besoins bots
```

## 2. Extraire
```bash
tar -xzf *_zaeldryk-vps-migration.tar.gz
cd *_vps-migration-pack/zaeldryk-migration
```

## 3. Installer le code
```bash
sudo mkdir -p /home/ubuntu
sudo rsync -a zaeldryk/ /home/ubuntu/zaeldryk/
sudo chown -R ubuntu:ubuntu /home/ubuntu/zaeldryk
```

## 4. Media offline + tokens
```bash
cp extras/thanks.mp4 /home/ubuntu/thanks.mp4
# Remettre le token Twitch au chemin indiqué dans extras/tokens/PATH.txt
mkdir -p "$(dirname "$(cat extras/tokens/PATH.txt | cut -d= -f2)")"
cp extras/tokens/* "$(dirname "$(cat extras/tokens/PATH.txt | cut -d= -f2)")/" 2>/dev/null || true
```

## 5. Systemd
```bash
sudo cp systemd/*.service systemd/*.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now zaeldryk-live.service zaeldryk-discord.service \
  moderation-bot.service offline-chatbot.service twitch-offline.service \
  zaeldryk-news.timer zaeldryk-freegames.timer zaeldryk-games-prompt.timer \
  zaeldryk-discord-dump.timer zaeldryk-watchdog.timer
```

## 6. Cron
```bash
crontab cron/ubuntu.crontab
```

## 7. Vérifier les secrets
Fichiers critiques (ne jamais commit / partager publiquement) :
- `zaeldryk/config/discord.env` — token bot Discord
- `zaeldryk/config/twitch.env` — API Twitch + stream
- `zaeldryk/config/stream.env` — clé RTMP si présente
- tokens Twitch refresh

## 8. Checks
```bash
systemctl status zaeldryk-live zaeldryk-discord --no-pager
systemctl list-timers 'zaeldryk-*' --no-pager
crontab -l
tail -20 /home/ubuntu/zaeldryk/logs/live-orchestrator.log
```

## Notes
- Les dumps Discord récents sont optionnels (`/home/ubuntu/backups/discord-dumps`).
- X est désactivé (`X_ENABLED=0`) — pas bloquant.
- Après migration : refresh token Twitch + test live + test bot Discord.
MD

echo "==> Archive"
tar -C "$OUT_ROOT" -czf "$ARCHIVE" zaeldryk-migration
chmod 600 "$ARCHIVE"
ls -lh "$ARCHIVE"
echo "ARCHIVE=$ARCHIVE"
echo "DIR=$OUT_ROOT"
sha256sum "$ARCHIVE" | tee "$OUT_ROOT/SHA256.txt"
