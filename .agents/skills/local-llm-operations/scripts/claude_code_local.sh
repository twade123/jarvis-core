#!/usr/bin/env bash
# claude_code_local.sh — point Claude Code CLI at the local vLLM server.
#
# Usage:   source claude_code_local.sh   (to export vars into current shell)
#    or:   bash claude_code_local.sh      (to launch claude directly)
#
# Requires vLLM running on port 8000 with --tool-call-parser qwen3_coder.
# See references/serving-vllm.md for setup.

VLLM_HOST="${VLLM_HOST:-127.0.0.1}"
VLLM_PORT="${VLLM_PORT:-8000}"
VLLM_URL="http://${VLLM_HOST}:${VLLM_PORT}/v1"

# Verify vLLM is up before exporting
if ! curl -sf "${VLLM_URL}/models" >/dev/null 2>&1; then
  echo "ERROR: vLLM not reachable at ${VLLM_URL}" >&2
  echo "Start it first:" >&2
  echo "  vllm serve ~/Jarvis/models/merged/qwen3.5-35b-jarvis \\" >&2
  echo "    --port 8000 --enable-auto-tool-choice --tool-call-parser qwen3_coder --reasoning-parser qwen3" >&2
  return 1 2>/dev/null || exit 1
fi

# If called via `bash claude_code_local.sh`, also check for header-stripper proxy
# (see references/client-claude-code.md). If the 90% slowdown symptoms appear,
# set ANTHROPIC_BASE_URL to the proxy port instead.

export ANTHROPIC_BASE_URL="${VLLM_URL}"
export ANTHROPIC_AUTH_TOKEN="${ANTHROPIC_AUTH_TOKEN:-local-vllm}"

echo "✓ ANTHROPIC_BASE_URL=${ANTHROPIC_BASE_URL}"
echo "✓ ANTHROPIC_AUTH_TOKEN=${ANTHROPIC_AUTH_TOKEN}"
echo ""
echo "If sourced: env vars exported. Run: claude"
echo "If run directly: launching claude..."

# Only launch claude if not sourced
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  exec claude "$@"
fi
