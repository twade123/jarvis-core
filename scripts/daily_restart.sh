#!/bin/bash
# Daily restart of trade_scout at 00:05 UTC
# Clears WAL files, zombie tasks, accumulated state
LOG=~/jarvis/logs/daily_restart.log
echo "$(date -u): Daily restart starting" >> "$LOG"

pkill -f trade_scout || true
sleep 5

# Checkpoint SQLite WAL files to keep DB sizes sane
for db in ~/jarvis/Database/*.db \
           "~/jarvis/Forex Trading Team/Source"/*.db; do
    if [ -f "${db}-wal" ]; then
        sqlite3 "$db" "PRAGMA wal_checkpoint(TRUNCATE);" 2>/dev/null
    fi
done

cd "~/jarvis/Forex Trading Team/Source"
~/myenv/bin/python -m trade_scout >> "$LOG" 2>&1 &

echo "$(date -u): trade_scout restarted (PID $!)" >> "$LOG"
