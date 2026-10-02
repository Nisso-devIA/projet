#!/usr/bin/env bash
# Déploie Wado-Osny sur le VPS (sans toucher Miina)
# Usage :
#   export VPS_HOST=57.128.177.132
#   export VPS_USER=ubuntu
#   export SSH_KEY="chemin/vers/cle"
#   bash scripts/deploy-vps.sh
set -euo pipefail

VPS_HOST="${VPS_HOST:?Définis VPS_HOST}"
VPS_USER="${VPS_USER:-ubuntu}"
APP_DIR="${APP_DIR:-/var/www/wado-osny}"
PORT="${PORT:-3003}"
REMOTE="${VPS_USER}@${VPS_HOST}"
SSH_OPTS=(-o StrictHostKeyChecking=no)
if [[ -n "${SSH_KEY:-}" ]]; then
  SSH_OPTS+=(-i "$SSH_KEY")
fi

echo "==> Sync code → ${REMOTE}:${APP_DIR}"
rsync -avz --delete \
  -e "ssh ${SSH_OPTS[*]}" \
  --exclude node_modules \
  --exclude .next \
  --exclude .git \
  --exclude .env \
  --exclude .vercel \
  --exclude _ref \
  ./ "${REMOTE}:${APP_DIR}/"

echo "==> Build + PM2 (port ${PORT})"
ssh "${SSH_OPTS[@]}" "$REMOTE" "bash -lc '
  set -e
  cd ${APP_DIR}
  npm ci
  npm run build
  if pm2 describe wado-osny >/dev/null 2>&1; then
    PORT=${PORT} pm2 restart wado-osny --update-env
  else
    PORT=${PORT} pm2 start npm --name wado-osny -- start
    pm2 save
  fi
'"

echo "==> Déployé sur le port ${PORT}."
