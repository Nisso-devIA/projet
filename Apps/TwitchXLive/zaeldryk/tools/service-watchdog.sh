#!/bin/bash
# Alert Discord (#🖥️-vps) when critical systemd units go down / recover.
# twitch-offline is only expected UP when stream mode is offline|ending.
# DOWN alerts wait WATCHDOG_ALERT_GRACE_SECONDS (default 30) before Discord.
set -uo pipefail

ZAEL_ROOT="${ZAEL_ROOT:-/home/ubuntu/zaeldryk}"
# shellcheck disable=SC1091
source "$ZAEL_ROOT/lib/common.sh"

LOG="$ZAEL_LOGS/service-watchdog.log"
STATE_FILE="$ZAEL_STATE/service-watchdog.json"
DISCORD_ENV="${DISCORD_ENV:-$ZAEL_ROOT/config/discord.env}"

: "${WATCHDOG_ALERT_GRACE_SECONDS:=30}"

# shellcheck disable=SC1090
set -a
source "$DISCORD_ENV"
set +a

: "${DISCORD_ALERT_CHANNEL_ID:?DISCORD_ALERT_CHANNEL_ID missing in discord.env}"
: "${DISCORD_BOT_TOKEN:?DISCORD_BOT_TOKEN missing in discord.env}"

CORE_UNITS=(
  zaeldryk-live.service
  zaeldryk-discord.service
  moderation-bot.service
  offline-chatbot.service
)
OFFLINE_UNIT=twitch-offline.service

NOW_TS=$(date +%s)

declare -A ST_STATE ST_FIRST_DOWN ST_ALERT_SENT

load_state_from_file() {
  [[ -f "$STATE_FILE" ]] || return 0
  local unit val typ
  while IFS= read -r unit; do
    [[ -n "$unit" ]] || continue
    typ=$(jq -r --arg u "$unit" '.[$u] | type' "$STATE_FILE" 2>/dev/null || echo null)
    [[ "$typ" == "null" ]] && continue
    if [[ "$typ" == "string" ]]; then
      val=$(jq -r --arg u "$unit" '.[$u]' "$STATE_FILE")
      ST_STATE[$unit]=$val
      if [[ "$val" == "down" ]]; then
        ST_FIRST_DOWN[$unit]=$NOW_TS
        ST_ALERT_SENT[$unit]=0
      fi
      continue
    fi
    ST_STATE[$unit]=$(jq -r --arg u "$unit" '.[$u].state // "ok"' "$STATE_FILE")
    val=$(jq -r --arg u "$unit" '.[$u].first_down_at // empty' "$STATE_FILE")
    [[ -n "$val" ]] && ST_FIRST_DOWN[$unit]=$val
    if [[ "$(jq -r --arg u "$unit" '.[$u].alert_sent // false' "$STATE_FILE")" == "true" ]]; then
      ST_ALERT_SENT[$unit]=1
    else
      ST_ALERT_SENT[$unit]=0
    fi
  done < <(jq -r 'keys[]' "$STATE_FILE" 2>/dev/null || true)
}

maybe_alert_down() {
  local unit="$1"
  local alert_msg="$2"
  local prev="${ST_STATE[$unit]:-ok}"

  ST_STATE[$unit]=down
  if [[ "$prev" == "ok" ]]; then
    ST_FIRST_DOWN[$unit]=$NOW_TS
    ST_ALERT_SENT[$unit]=0
    return 0
  fi

  if [[ "${ST_ALERT_SENT[$unit]:-0}" == "1" ]]; then
    return 0
  fi

  local fd="${ST_FIRST_DOWN[$unit]:-$NOW_TS}"
  if (( NOW_TS - fd >= WATCHDOG_ALERT_GRACE_SECONDS )); then
    ALERTS+=("$alert_msg")
    ST_ALERT_SENT[$unit]=1
    zael_log "$LOG" "ALERT (grace ${WATCHDOG_ALERT_GRACE_SECONDS}s): $unit"
  fi
}

mark_unit_up() {
  local unit="$1"
  local recovery_msg="$2"
  local prev="${ST_STATE[$unit]:-ok}"

  ST_STATE[$unit]=ok
  unset ST_FIRST_DOWN[$unit]
  ST_ALERT_SENT[$unit]=0

  if [[ "$prev" == "down" && -n "$recovery_msg" ]]; then
    RECOVERIES+=("$recovery_msg")
  fi
}

unit_active() {
  systemctl is-active --quiet "$1"
}

unit_failed() {
  [[ "$(systemctl is-failed "$1" 2>/dev/null || true)" == "failed" ]]
}

expected_offline_up() {
  # Filler offline stream désactivé → ne jamais alerter s'il est down
  [[ "${OFFLINE_STREAM_ENABLED}" == "1" ]] || return 1
  local mode
  mode=$(zael_read_mode)
  [[ "$mode" == "offline" || "$mode" == "ending" ]]
}

send_discord() {
  local content="$1"
  local payload
  payload=$(jq -nc --arg c "$content" '{content:$c}')
  local code
  code=$(curl -s -o /tmp/zael-watchdog-discord.out -w "%{http_code}" \
    -X POST "https://discord.com/api/v10/channels/${DISCORD_ALERT_CHANNEL_ID}/messages" \
    -H "Authorization: Bot ${DISCORD_BOT_TOKEN}" \
    -H "User-Agent: DiscordBot (https://zaelrys.local/watchdog, 1.0)" \
    -H "Content-Type: application/json" \
    -d "$payload")
  if [[ "$code" != "200" ]]; then
    zael_log "$LOG" "Discord alert HTTP $code: $(head -c 200 /tmp/zael-watchdog-discord.out 2>/dev/null || true)"
    return 1
  fi
  return 0
}

save_state_file() {
  local tmp="$STATE_FILE.tmp"
  local first=1
  local all_units=("${CORE_UNITS[@]}" "$OFFLINE_UNIT")
  {
    echo -n "{"
    for unit in "${all_units[@]}"; do
      local s="${ST_STATE[$unit]:-ok}"
      [[ $first -eq 1 ]] || echo -n ","
      first=0
      if [[ "$s" == "down" ]]; then
        local fd="${ST_FIRST_DOWN[$unit]:-null}"
        local as=false
        [[ "${ST_ALERT_SENT[$unit]:-0}" == "1" ]] && as=true
        if [[ -n "${ST_FIRST_DOWN[$unit]:-}" ]]; then
          printf '"%s":{"state":"down","first_down_at":%s,"alert_sent":%s}' "$unit" "$fd" "$as"
        else
          printf '"%s":{"state":"down","first_down_at":null,"alert_sent":%s}' "$unit" "$as"
        fi
      else
        printf '"%s":{"state":"ok"}' "$unit"
      fi
    done
    echo "}"
  } > "$tmp"
  mv "$tmp" "$STATE_FILE"
}

ALERTS=()
RECOVERIES=()

load_state_from_file

check_core() {
  local unit="$1"
  local short="${unit%.service}"
  if unit_active "$unit"; then
    mark_unit_up "$unit" "✅ **$short** est de nouveau UP"
  else
    local detail
    detail=$(systemctl is-active "$unit" 2>/dev/null || echo unknown)
    maybe_alert_down "$unit" "🚨 **$short** est DOWN (état: \`$detail\`)"
  fi
}

check_offline() {
  local unit="$OFFLINE_UNIT"
  local short="${unit%.service}"

  if zael_watchdog_offline_silenced; then
    mark_unit_up "$unit" ""
    return 0
  fi

  if unit_failed "$unit"; then
    maybe_alert_down "$unit" "🚨 **$short** est en échec (\`failed\`)"
    return 0
  fi

  if expected_offline_up; then
    if unit_active "$unit"; then
      mark_unit_up "$unit" "✅ **$short** est de nouveau UP (mode offline/ending)"
    else
      local mode
      mode=$(zael_read_mode)
      maybe_alert_down "$unit" "🚨 **$short** devrait tourner (mode \`$mode\`) mais est DOWN"
    fi
  else
    mark_unit_up "$unit" ""
  fi
}

for u in "${CORE_UNITS[@]}"; do
  check_core "$u"
done
check_offline

save_state_file

if ((${#ALERTS[@]})); then
  msg=$'⚠️ **Alerte VPS Zaelrys**\n'
  for a in "${ALERTS[@]}"; do
    msg+="$a"$'\n'
  done
  msg+=$'\n_hôte: '"$(hostname)"_
  zael_log "$LOG" "ALERT: ${ALERTS[*]}"
  send_discord "$msg" || true
fi

if ((${#RECOVERIES[@]})); then
  msg=$'💚 **Récupération VPS Zaelrys**\n'
  for r in "${RECOVERIES[@]}"; do
    [[ -n "$r" ]] && msg+="$r"$'\n'
  done
  msg+=$'\n_hôte: '"$(hostname)"_
  zael_log "$LOG" "RECOVERY: ${RECOVERIES[*]}"
  send_discord "$msg" || true
fi

exit 0
