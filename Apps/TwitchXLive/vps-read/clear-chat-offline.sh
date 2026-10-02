#!/bin/bash

CLIENT_ID="j2eaj1gxokr77a3lrzso63tr6wvk22"
ACCESS_TOKEN=$(cat /home/ubuntu/twitch_token.txt)
BROADCASTER_ID="426411773"
MODERATOR_ID="426411773"
LOG="/home/ubuntu/clear-chat.log"

# Récupère le titre actuel
RESPONSE=$(curl -s -H "Client-ID: $CLIENT_ID" \
                 -H "Authorization: Bearer $ACCESS_TOKEN" \
                 "https://api.twitch.tv/helix/streams?user_id=$BROADCASTER_ID")

TITLE=$(echo "$RESPONSE" | jq -r '.data[0].title // ""' | tr '[:upper:]' '[:lower:]')

# Si le titre ne contient pas offline/ending/brb → on sort
if ! echo "$TITLE" | grep -qE "offline|ending|brb|fin de live|hors ligne"; then
  echo "$(date '+%Y-%m-%d %H:%M:%S') - Pas en mode offline → pas de clear" >> $LOG
  exit 0
fi

# On est en offline → on vide le chat
echo "$(date '+%Y-%m-%d %H:%M:%S') - Mode offline détecté → Clear chat" >> $LOG

curl -s -X DELETE "https://api.twitch.tv/helix/moderation/chat?broadcaster_id=$BROADCASTER_ID&moderator_id=$MODERATOR_ID" \
  -H "Client-ID: $CLIENT_ID" \
  -H "Authorization: Bearer $ACCESS_TOKEN" >> $LOG

echo "$(date '+%Y-%m-%d %H:%M:%S') - Chat vidé" >> $LOG
