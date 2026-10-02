#!/bin/bash

CLIENT_ID="j2eaj1gxokr77a3lrzso63tr6wvk22"
ACCESS_TOKEN=$(cat /home/ubuntu/twitch_token.txt)
SERVICE="twitch-offline.service"
LOG="/home/ubuntu/offline-watchdog.log"

# Vérifie si la chaîne est en vrai live
IS_LIVE=$(curl -s -H "Client-ID: $CLIENT_ID" \
               -H "Authorization: Bearer $ACCESS_TOKEN" \
               "https://api.twitch.tv/helix/streams?user_login=zaeldryk" | jq -r '.data | length')

if [ "$IS_LIVE" -gt 0 ]; then
  # On regarde le titre pour savoir si c'est un vrai live ou l'offline
  TITLE=$(curl -s -H "Client-ID: $CLIENT_ID" \
               -H "Authorization: Bearer $ACCESS_TOKEN" \
               "https://api.twitch.tv/helix/streams?user_login=zaeldryk" | jq -r '.data[0].title // ""' | tr '[:upper:]' '[:lower:]')

  if echo "$TITLE" | grep -qE "offline|ending|brb|fin de live|hors ligne"; then
    # C'est l'offline → on laisse tourner
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Mode offline détecté → OK" >> $LOG
  else
    # Vrai live → on s'assure que le service offline est arrêté
    if systemctl is-active --quiet $SERVICE; then
      echo "$(date '+%Y-%m-%d %H:%M:%S') - Vrai LIVE détecté → Arrêt du service offline" >> $LOG
      sudo systemctl stop $SERVICE
    fi
  fi
  exit 0
fi

# La chaîne n'est pas en live du tout → on s'assure que le service offline tourne
if ! systemctl is-active --quiet $SERVICE; then
  echo "$(date '+%Y-%m-%d %H:%M:%S') - Chaîne hors ligne + service arrêté → Relance" >> $LOG
  sudo systemctl start $SERVICE
else
  echo "$(date '+%Y-%m-%d %H:%M:%S') - Chaîne hors ligne + service OK" >> $LOG
fi
