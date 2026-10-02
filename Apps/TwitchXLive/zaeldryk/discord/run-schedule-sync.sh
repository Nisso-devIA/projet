#!/bin/bash
set -euo pipefail
ZAEL_ROOT="${ZAEL_ROOT:-/home/ubuntu/zaeldryk}"
LOCK="$ZAEL_ROOT/state/schedule-sync.lock"
exec flock -n "$LOCK" /usr/bin/python3 "$ZAEL_ROOT/discord/schedule-sync.py"
