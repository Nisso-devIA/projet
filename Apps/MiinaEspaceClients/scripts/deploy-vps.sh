#!/usr/bin/env bash
# Déploie miinarecettesclients sur le VPS
# Usage (Git Bash / WSL) :
#   export VPS_HOST=57.128.177.132
#   export VPS_USER=ubuntu
#   bash scripts/deploy-vps.sh
set -euo pipefail

VPS_HOST="${VPS_HOST:?Définis VPS_HOST}"
VPS_USER="${VPS_USER:-ubuntu}"
APP_DIR="${APP_DIR:-/var/www/miinarecettesclients}"
REMOTE="${VPS_USER}@${VPS_HOST}"
SSH_OPTS="${SSH_OPTS:-}"

echo "==> Sync code → ${REMOTE}:${APP_DIR}"
rsync -avz --delete \
  --exclude node_modules \
  --exclude .next \
  --exclude .git \
  --exclude .env \
  --exclude .env.* \
  --exclude data \
  --exclude 'data/**' \
  ./ "${REMOTE}:${APP_DIR}/"

echo "==> Build + restart PM2"
ssh ${SSH_OPTS} "$REMOTE" "bash -lc '
  set -e
  cd ${APP_DIR}
  test -f .env || { echo \"ERREUR: .env manquant\"; exit 1; }
  npm ci
  npm run build
  pm2 describe miinarecettesclients >/dev/null 2>&1 \\
    && pm2 restart miinarecettesclients \\
    || pm2 start npm --name miinarecettesclients -- start
  pm2 save
'"

echo "==> Déployé : ${APP_DIR}"
