#!/bin/bash

CLIENT_ID="j2eaj1gxokr77a3lrzso63tr6wvk22"
ACCESS_TOKEN=$(cat /home/ubuntu/twitch_token.txt)
BROADCASTER_ID="426411773"
LOG="/home/ubuntu/smart-live.log"
STATE_FILE="/tmp/live_state.txt"

PREV_LIVE=$(cat $STATE_FILE 2>/dev/null || echo "0")

RESPONSE=$(curl -s -H "Client-ID: $CLIENT_ID" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  "https://api.twitch.tv/helix/streams?user_login=zaeldryk")

IS_LIVE=$(echo $RESPONSE | jq -r '.data | length')
TITLE=$(echo $RESPONSE | jq -r '.data[0].title // ""')
GAME=$(echo $RESPONSE | jq -r '.data[0].game_name // "Jeu non spécifié"')

if [ "$IS_LIVE" -gt 0 ] && [ "$PREV_LIVE" = "0" ]; then
    if echo "$TITLE" | grep -qi "Offline"; then
        echo "$(date '+%Y-%m-%d %H:%M:%S') - Ending détecté → Pas de notification" >> $LOG
    else
        echo "$(date '+%Y-%m-%d %H:%M:%S') - VRAI LIVE détecté → $TITLE ($GAME)" >> $LOG

        # Message sur une seule ligne avec \n pour les retours à la ligne
        MESSAGE="🚨 LIVE EN COURS 🚨\\nJe stream, passe faire un check 👀\\n🎮 $GAME\\n📌 $TITLE"

        curl -s -X POST "https://api.twitch.tv/helix/chat/messages" \
          -H "Client-ID: $CLIENT_ID" \
          -H "Authorization: Bearer $ACCESS_TOKEN" \
          -H "Content-Type: application/json" \
          -d "{\"broadcaster_id\":\"$BROADCASTER_ID\",\"sender_id\":\"$BROADCASTER_ID\",\"message\":\"$MESSAGE\"}" >> $LOG

        echo "$(date '+%Y-%m-%d %H:%M:%S') - Notification envoyée dans le chat" >> $LOG
    fi
fi

echo "$IS_LIVE" > $STATE_FILE
