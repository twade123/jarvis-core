#!/bin/bash
# notify_deliver.sh — Zero-AI notification delivery
# Scans ~/jarvis/notifications/*.json, sends each message to Telegram, deletes the file.
# No Claude. No API credits. Pure curl.

NOTIFY_DIR="$HOME/jarvis/notifications"
BOT_TOKEN="8588745151:AAEt1nRdUD1yUER94r2MQJ5sPOgMLAzzzdI"
CHAT_ID="6368550107"
TG_URL="https://api.telegram.org/bot${BOT_TOKEN}/sendMessage"

# Nothing to do if dir is empty
shopt -s nullglob
files=("$NOTIFY_DIR"/*.json)
[[ ${#files[@]} -eq 0 ]] && exit 0

for f in "${files[@]}"; do
    # Extract the message field (requires python3 or jq)
    if command -v jq &>/dev/null; then
        msg=$(jq -r '.message // .text // .msg // empty' "$f" 2>/dev/null)
    else
        msg=$(python3 -c "import json,sys; d=json.load(open('$f')); print(d.get('message') or d.get('text') or d.get('msg',''))" 2>/dev/null)
    fi

    [[ -z "$msg" ]] && { echo "WARN: no message field in $f, skipping"; continue; }

    # Send to Telegram
    resp=$(curl -s -X POST "$TG_URL" \
        -H "Content-Type: application/json" \
        -d "{\"chat_id\": \"${CHAT_ID}\", \"text\": $(python3 -c "import json,sys; print(json.dumps(sys.argv[1]))" "$msg"), \"parse_mode\": \"HTML\"}" \
        2>/dev/null)

    ok=$(echo "$resp" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('ok','false'))" 2>/dev/null)

    if [[ "$ok" == "True" ]]; then
        rm -f "$f"
        echo "OK: sent and deleted $f"
    else
        echo "WARN: Telegram rejected $f — $resp"
        # Don't delete — leave it for retry
    fi
done
