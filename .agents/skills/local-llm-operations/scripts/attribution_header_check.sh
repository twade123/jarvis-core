#!/usr/bin/env bash
# attribution_header_check.sh — detect Claude Code Attribution Header in vLLM logs.
#
# Background: Claude Code prepends a proprietary header to every request.
# vLLM treats it as part of the prompt, invalidating KV cache → 90% speed drop.
# See references/client-claude-code.md for the fix.
#
# Usage: bash attribution_header_check.sh [path/to/vllm.log]

LOG_PATH="${1:-/tmp/vllm.log}"
CANDIDATES=(
  "$LOG_PATH"
  "${HOME}/vllm.log"
  "${HOME}/Jarvis/Logs/vllm.log"
  "/tmp/vllm.log"
)

LOG=""
for c in "${CANDIDATES[@]}"; do
  if [ -f "$c" ]; then
    LOG="$c"
    break
  fi
done

if [ -z "$LOG" ]; then
  echo "No vLLM log found. Checked:"
  printf '  %s\n' "${CANDIDATES[@]}"
  echo ""
  echo "If vLLM is running with stderr piped elsewhere, pass the path:"
  echo "  bash attribution_header_check.sh /path/to/log"
  exit 1
fi

echo "Scanning: $LOG"
echo ""

PATTERNS=(
  "x-claude-attribution"
  "anthropic-attribution"
  "claude-code-session"
  "user-agent: claude-cli"
  "user-agent: anthropic"
)

found=0
for p in "${PATTERNS[@]}"; do
  count=$(grep -ci "$p" "$LOG" 2>/dev/null || echo 0)
  if [ "$count" -gt 0 ]; then
    printf "  \033[33m%-40s\033[0m %s occurrences\n" "$p" "$count"
    found=$((found + 1))
  fi
done

echo ""
if [ "$found" -gt 0 ]; then
  echo "⚠️  Attribution headers detected in vLLM requests."
  echo "    This invalidates the KV cache on every turn → 90% slowdown."
  echo ""
  echo "    Fix: strip the header with a proxy. See:"
  echo "      references/client-claude-code.md"
  echo "      unsloth.ai/docs/basics/claude-code"
else
  echo "✓ No attribution headers found in this log window."
  echo "  (If Claude Code is still slow, check for header with a fresher log tail:"
  echo "   tail -n 1000 $LOG | grep -i 'attribution\\|user-agent')"
fi
