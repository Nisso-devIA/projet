#!/usr/bin/env bash
set -euo pipefail

STAMP="$(date +%Y-%m-%d_%H%M)"
B="/home/ubuntu/backups/${STAMP}_ssh-password-off"
mkdir -p "$B"
sudo cp -a /etc/ssh/sshd_config "$B/"
sudo cp -a /etc/ssh/sshd_config.d "$B/sshd_config.d"

echo "==== before ===="
sudo sshd -T | grep -E '^(passwordauthentication|pubkeyauthentication|permitrootlogin) '
echo "==== 50-cloud-init.conf ===="
sudo cat /etc/ssh/sshd_config.d/50-cloud-init.conf || true

# OpenSSH uses first-obtained value; put our rule first
echo 'PasswordAuthentication no' | sudo tee /etc/ssh/sshd_config.d/00-disable-password.conf >/dev/null

if sudo test -f /etc/ssh/sshd_config.d/50-cloud-init.conf; then
  if sudo grep -q '^PasswordAuthentication' /etc/ssh/sshd_config.d/50-cloud-init.conf; then
    sudo sed -i 's/^PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config.d/50-cloud-init.conf
  else
    echo 'PasswordAuthentication no' | sudo tee -a /etc/ssh/sshd_config.d/50-cloud-init.conf >/dev/null
  fi
fi

sudo sshd -t
sudo systemctl reload ssh || sudo systemctl reload sshd

echo "==== after ===="
sudo sshd -T | grep -E '^(passwordauthentication|pubkeyauthentication|permitrootlogin) '
echo "BACKUP $B"
echo DONE
