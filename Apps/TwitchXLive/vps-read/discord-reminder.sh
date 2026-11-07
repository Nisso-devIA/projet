#!/bin/bash

CLIENT_ID="j2eaj1gxokr77a3lrzso63tr6wvk22"
ACCESS_TOKEN=$(cat /home/ubuntu/twitch_token.txt)
BROADCASTER_ID="426411773"
MESSAGE="⚔️ Rejoins le Discord ZAELDRYK → https://discord.gg/3vH2u7pme5"
LOG="/home/ubuntu/discord-reminder.log"

# Récupère les infos du stream
RESPONSE=$(curl -s -H "Client-ID: $CLIENT_ID" \
                 -H "Authorization: Bearer $ACCESS_TOKEN" \
                 "https://api.twitch.tv/helix/streams?user_id=$BROADCASTER_ID")

IS_LIVE=$(echo "$RESPONSE" | jq -r '.data | length')
TITLE=$(echo "$RESPONSE" | jq -r '.data[0].title // ""' | tr '[:upper:]' '[:lower:]')

# Si pas en live → on sort
if [ "$IS_LIVE" -eq 0 ]; then
  echo "$(date '+%Y-%m-%d %H:%M:%S') - Pas en live" >> $LOG
  exit 0
fi

# Si le titre contient un mot offline → on n'envoie pas
if echo "$TITLE" | grep -qE "offline|ending|brb|fin de live|hors ligne"; then
  echo "$(date '+%Y-%m-%d %H:%M:%S') - Titre offline détecté ($TITLE) → pas de rappel Discord" >> $LOG
  exit 0
fi

# Sinon on envoie le rappel
curl -s -X POST "https://api.twitch.tv/helix/chat/messages" \
  -H "Client-ID: $CLIENT_ID" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"broadcaster_id\": \"$BROADCASTER_ID\",
    \"sender_id\": \"$BROADCASTER_ID\",
    \"message\": \"$MESSAGE\"
  }" > /dev/null

echo "$(date '+%Y-%m-%d %H:%M:%S') - Message Discord envoyé" >> $LOG
