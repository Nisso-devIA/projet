#!/usr/bin/env bash
set -euo pipefail

STAMP="${1:?stamp required}"
B="/home/ubuntu/backups/${STAMP}_cyber-hardening"
mkdir -p "$B"
sudo cp -a /etc/nginx "$B/nginx"
sudo cp -a /etc/ssh/sshd_config "$B/sshd_config"
crontab -l > "$B/crontab.txt" 2>/dev/null || true
pm2 save >/dev/null
cp -a /home/ubuntu/.pm2/dump.pm2 "$B/pm2-dump.pm2" || true
ss -tlnp > "$B/ports-before.txt"
sudo cp /etc/nginx/sites-available/miina "$B/miina.conf"
sudo cp /etc/nginx/sites-available/wado-osny "$B/wado-osny.conf"
echo "BACKUP_OK $B"

cat > /var/www/miina/ecosystem.config.cjs <<'EOF'
module.exports = {
  apps: [{
    name: 'miina',
    cwd: '/var/www/miina',
    script: 'node_modules/next/dist/bin/next',
    args: 'start -H 127.0.0.1 -p 3000',
    env: {
      NODE_ENV: 'production',
      PORT: '3000',
      HOSTNAME: '127.0.0.1',
    },
  }],
};
EOF

cp /tmp/ecosystem.config.cjs /var/www/wado-osny/ecosystem.config.cjs
cp /tmp/next.config.ts /var/www/wado-osny/next.config.ts

echo '==> restart miina on 127.0.0.1:3000'
pm2 delete miina || true
pm2 start /var/www/miina/ecosystem.config.cjs
sleep 2
curl -sI http://127.0.0.1:3000/ | head -n 5

echo '==> rebuild + restart wado'
cd /var/www/wado-osny
npm run build
pm2 delete wado-osny || true
pm2 start /var/www/wado-osny/ecosystem.config.cjs
sleep 2
curl -sI http://127.0.0.1:3003/ | head -n 8
pm2 save

echo '==== listen ports ===='
ss -tlnp | grep -E ':(3000|3003)\s' || true
