# Client — OpenClaw → local model

## The hard constraint

**OpenClaw's `anthropic` provider is hardwired to `api.anthropic.com`.** No `baseUrl` override exists. You CANNOT point the `anthropic` provider at a local vLLM.

To replace Opus in OpenClaw with the local 35B, OpenClaw MUST talk to the local model via `openai-completions` shape. This is documented in `/opt/homebrew/lib/node_modules/openclaw/docs/providers/anthropic.md`: "OpenClaw only injects Anthropic service tiers for direct `api.anthropic.com` requests."

## Current working config

From `~/.openclaw/openclaw.json`:

```json5
"models": {
  "providers": {
    "mlx": {
      "baseUrl": "http://127.0.0.1:11502/v1",
      "apiKey": "local",
      "api": "openai-completions",
      "models": [{
        "id": "mlx-community/Qwen3.5-35B-A3B-4bit",
        "name": "Qwen 3.5 35B (MLX Local)",
        "reasoning": false,
        "input": ["text"],
        "cost": { "input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0 },
        "contextWindow": 131072,
        "maxTokens": 8192
      }]
    }
  }
}
```

And the key settings that make this actually work:

```json5
"agents": {
  "defaults": {
    "contextTokens": 131072,              // MUST be set — otherwise OpenClaw defaults to 200K/1M and compacts instantly
    "bootstrapMaxChars": 20000,
    "bootstrapTotalMaxChars": 150000,
    "bootstrapPromptTruncationWarning": "always",
    "model": {
      "primary": "mlx/mlx-community/Qwen3.5-35B-A3B-4bit",
      "fallbacks": []
    },
    "models": {
      "mlx/mlx-community/Qwen3.5-35B-A3B-4bit": {
        "params": {
          "think": false,
          "chat_template_kwargs": { "enable_thinking": false }
        }
      }
    },
    "timeoutSeconds": 600,
    "subagents": {
      "maxConcurrent": 8,
      "model": { "primary": "mlx/mlx-community/Qwen3.5-35B-A3B-4bit" }  // subagents also go to 35B
    }
  }
}
```

## Tool calling via OpenClaw

OpenClaw sends OpenAI-shape `tools` + `tool_choice` in the chat completion request. Our `mlx_vlm_server_with_tools.py` (port 11502):
1. Injects the tools list into Qwen3.5's system-prompt `<tools>...</tools>` block
2. Lets the model respond with `<tool_call>{"name": ..., "arguments": {...}}</tool_call>` in content
3. Parses that block back into OpenAI `tool_calls` format before returning

OpenClaw sees standard OpenAI `tool_calls` in the response and dispatches as normal.

## History — why we don't use Ollama

Prior iteration used Ollama. Problems found (2026-03-20 audit):
- Ollama streaming doesn't emit `tool_calls` delta chunks → tool calls silently fail
- Ollama returns `prompt_tokens=0` → OpenClaw compaction timing breaks
- Ollama's think-mode plumbing required patching OpenClaw's JS bundle (`reply-Bm8VrLQh.js`) to inject `think:false`

MLX with `openai-completions` is the fix. **Don't revert.**

## The `anthropic:default` auth profile

Your `~/.openclaw/openclaw.json` still has the anthropic auth profile. That's because your Opus calls went through it when `model.primary` was `anthropic/claude-opus-4-6`. Leave it — it's used by:
- Compaction A/B tests (if you ever set `compaction.model: "anthropic/claude-sonnet-4-6"`)
- Manual `/model` overrides in a session
- Emergency fallback if MLX goes down

## The `acpx` plugin

Your config enables `acpx` (Agent Client Protocol for Claude Code). This delegates specific coding tasks from OpenClaw → Claude Code via your Max subscription. Separate from the local-model path. Relevant flags:

```json5
"acpx": {
  "enabled": true,
  "config": {
    "cwd": "~/Jarvis",
    "permissionMode": "approve-all",
    "nonInteractivePermissions": "deny",
    "timeoutSeconds": 300
  }
}
```

When OpenClaw dispatches to Claude Code via acpx, Claude Code uses the Max plan (real Anthropic). Not related to the local 35B.

## Related docs

- `openclaw-settings.md` — compaction, bootstrap, memoryFlush knobs
- `client-claude-code.md` — the OTHER way to reach the local model (via `ANTHROPIC_BASE_URL` + vLLM)
- `tool-calling.md` — the three tool-call shapes
