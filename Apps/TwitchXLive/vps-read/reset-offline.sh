#!/bin/bash

LOG="/home/ubuntu/reset-offline.log"
SERVICE="twitch-offline.service"

echo "$(date '+%Y-%m-%d %H:%M:%S') - Reset offline en cours..." >> $LOG

# Redémarre le service offline
sudo systemctl restart $SERVICE

if systemctl is-active --quiet $SERVICE; then
  echo "$(date '+%Y-%m-%d %H:%M:%S') - Service $SERVICE redémarré avec succès" >> $LOG
else
  echo "$(date '+%Y-%m-%d %H:%M:%S') - Erreur : le service n'a pas redémarré" >> $LOG
fi
ubuntu ALL=(ALL) NOPASSWD: /bin/systemctl restart twitch-offline.service

# Attendre que Twitch finalise l'ancienne VOD puis nettoyer
sleep 120
/home/ubuntu/delete-offline-vods.sh
