#!/usr/bin/env bash
# Quan ly 2 bot: bot.py (lenh) + notify_bot.py (thong bao)
# Ctrl+C: tat seaclean + pkill; boot: chay nền tu dong
set -uo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG="$DIR/logs/bot.log"
mkdir -p "$DIR/logs" "$DIR/data"

cleanup() {
    pkill -f "${DIR}/bot.py" 2>/dev/null || true
    pkill -f "${DIR}/notify_bot.py" 2>/dev/null || true
    sleep 1
    echo "[$(date '+%H:%M:%S')] STOP bot." >> "$LOG"
    exit 0
}
trap cleanup INT TERM

echo "[$(date '+%H:%M:%S')] START AI Agent News Bot..." >> "$LOG"

python3 "$DIR/validate.py" || { echo "CONFIG INVALID"; exit 1; }

while true; do
    pgrep -f "${DIR}/notify_bot.py" >/dev/null 2>&1 || { python3 "${DIR}/notify_bot.py" >> "$LOG" 2>&1 & }
    pgrep -f "${DIR}/bot.py" >/dev/null 2>&1 || { python3 "${DIR}/bot.py" >> "$LOG" 2>&1 & }
    sleep 15
done
