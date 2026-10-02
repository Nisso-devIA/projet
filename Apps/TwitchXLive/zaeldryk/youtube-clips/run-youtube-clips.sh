#!/usr/bin/env bash
set -euo pipefail
ZAEL_ROOT="${ZAEL_ROOT:-/home/ubuntu/zaeldryk}"
LOCK="${ZAEL_ROOT}/state/youtube-clips.flock"
export PATH="${HOME}/.local/bin:/usr/local/bin:${PATH}"
mkdir -p "${ZAEL_ROOT}/state" "${ZAEL_ROOT}/logs"
cd "${ZAEL_ROOT}/youtube-clips"
exec flock -n "$LOCK" /usr/bin/python3 "${ZAEL_ROOT}/youtube-clips/queue_worker.py"
