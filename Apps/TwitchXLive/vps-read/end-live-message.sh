#!/bin/bash

CLIENT_ID="j2eaj1gxokr77a3lrzso63tr6wvk22"
ACCESS_TOKEN=$(cat /home/ubuntu/twitch_token.txt)
BROADCASTER_ID="426411773"
LOG="/home/ubuntu/end-live.log"
STATE_FILE="/tmp/live_state_end.txt"
MODE_FILE="/tmp/live_mode_end.txt"

PREV_LIVE=$(cat $STATE_FILE 2>/dev/null || echo "0")
PREV_MODE=$(cat $MODE_FILE 2>/dev/null || echo "none")

RESPONSE=$(curl -s -H "Client-ID: $CLIENT_ID" \
                 -H "Authorization: Bearer $ACCESS_TOKEN" \
                 "https://api.twitch.tv/helix/streams?user_id=$BROADCASTER_ID")

IS_LIVE=$(echo "$RESPONSE" | jq -r '.data | length')
TITLE=$(echo "$RESPONSE" | jq -r '.data[0].title // ""' | tr '[:upper:]' '[:lower:]')

# Détermine le mode actuel
if [ "$IS_LIVE" = "0" ]; then
  CURRENT_MODE="offline"
elif echo "$TITLE" | grep -qE "offline|ending|brb|fin de live|hors ligne"; then
  CURRENT_MODE="ending"
else
  CURRENT_MODE="live"
fi

# Sauvegarde
echo "$IS_LIVE" > $STATE_FILE
echo "$CURRENT_MODE" > $MODE_FILE

# On n'envoie le message de fin QUE si on passait d'un vrai LIVE à offline
if [ "$PREV_MODE" = "live" ] && [ "$CURRENT_MODE" = "offline" ]; then

  MESSAGE="Merci d'avoir regardé ! 🙏 À très bientôt 👋"

  curl -s -X POST "https://api.twitch.tv/helix/chat/messages" \
    -H "Client-ID: $CLIENT_ID" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{
      \"broadcaster_id\": \"$BROADCASTER_ID\",
      \"sender_id\": \"$BROADCASTER_ID\",
      \"message\": \"$MESSAGE\"
    }" > /dev/null

  echo "$(date '+%Y-%m-%d %H:%M:%S') - Vrai fin de live → Message envoyé" >> $LOG

else
  echo "$(date '+%Y-%m-%d %H:%M:%S') - Pas de message (prev=$PREV_MODE → current=$CURRENT_MODE)" >> $LOG
fi
