#!/bin/bash
set -euo pipefail
ZAEL_ROOT="${ZAEL_ROOT:-/home/ubuntu/zaeldryk}"
LOCK="${ZAEL_ROOT}/state/news-post.flock"
mkdir -p "${ZAEL_ROOT}/state"
exec flock -n "$LOCK" /usr/bin/python3 "$ZAEL_ROOT/discord/news-post.py"
