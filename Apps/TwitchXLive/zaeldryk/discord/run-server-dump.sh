#!/bin/bash
set -euo pipefail
ZAEL_ROOT="${ZAEL_ROOT:-/home/ubuntu/zaeldryk}"
exec /usr/bin/python3 "$ZAEL_ROOT/discord/server-dump.py"
