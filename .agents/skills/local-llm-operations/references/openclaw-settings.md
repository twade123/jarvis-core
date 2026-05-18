# OpenClaw — Settings for local-model serving

Authoritative source: `/opt/homebrew/lib/node_modules/openclaw/docs/concepts/compaction.md` and `reference/session-management-compaction.md`. This file documents **our current settings** and why they're set the way they are.

## Current production settings (as of this skill's writing)

```json5
{
  "agents": {
    "defaults": {
      "contextTokens": 131072,
      "bootstrapMaxChars": 20000,
      "bootstrapTotalMaxChars": 150000,
      "bootstrapPromptTruncationWarning": "always",
      "model": {
        "primary": "mlx/mlx-community/Qwen3.5-35B-A3B-4bit"
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
      "contextPruning": { "mode": "cache-ttl", "ttl": "1h" },
      "compaction": {
        "mode": "default",
        "reserveTokens": 20000,
        "reserveTokensFloor": 20000,
        "keepRecentTokens": 24000,
        "identifierPolicy": "strict",
        "postCompactionSections": ["memory/short-term.md"],
        "memoryFlush": {
          "enabled": true,
          "softThresholdTokens": 10000,
          "forceFlushTranscriptBytes": "200kb",
          "prompt": "...(see config)...",
          "systemPrompt": "..."
        }
      },
      "heartbeat": { "every": "4m" },
      "maxConcurrent": 4,
      "subagents": {
        "maxConcurrent": 8,
        "model": { "primary": "mlx/mlx-community/Qwen3.5-35B-A3B-4bit" }
      }
    }
  }
}
```

## Setting-by-setting rationale

### `contextTokens: 131072`

**Must be set explicitly.** Without this, OpenClaw defaults to 200K / 1M and compaction triggers instantly for openai-completions providers that return unusual `usage` data. This value matches our KV cache cap of 131072 tokens (10 GB on the 35B).

### `bootstrapMaxChars: 20000`, `bootstrapTotalMaxChars: 150000`

Explicit defaults (match OpenClaw's internal defaults). Our bootstrap files are:
- `AGENTS.md`, `MEMORY.md`, `TOOLS.md`, `JARVIS_CONTEXT.md`, `VAULT_CONTEXT.md`, `memory/short-term.md`, `memory/mistakes.md`

Per-file cap: 20K chars (~5K tokens). Total cap: 150K chars (~37.5K tokens). If a file exceeds 20K it's silently truncated; if all files combined exceed 150K, some get truncated.

### `bootstrapPromptTruncationWarning: "always"`

Was `"once"` (default). Changed to `"always"` so every truncation event surfaces — helps catch when `VAULT_CONTEXT.md` or `MEMORY.md` bloats past the cap.

### `compaction.reserveTokens: 20000` + `reserveTokensFloor: 20000`

OpenClaw enforces a safety floor on `reserveTokens`: if you set a lower value, it silently bumps you to 20000. We had `16000` — OpenClaw was quietly using 20000. Setting both explicitly makes behavior predictable.

Tradeoff: higher `reserveTokens` triggers compaction earlier (smaller effective working window) but leaves more headroom for silent housekeeping turns like the memory flush.

To disable the floor: `reserveTokensFloor: 0`. We don't — the floor exists for a reason.

### `compaction.keepRecentTokens: 24000`

Higher than the doc default of 20000. Keeps more recent conversation intact after compaction — useful because our sessions have long tool-use chains that shouldn't collapse mid-sequence.

### `compaction.identifierPolicy: "strict"`

Default behavior — preserves opaque identifiers (IDs, hashes, tokens) verbatim across compaction summaries. Critical for trade IDs, workspace IDs, session keys that appear in summarized history.

### `compaction.model` — NOT SET (intentional)

OpenClaw supports routing compaction to a different model (e.g., `anthropic/claude-sonnet-4-6`). We tried it in the 2026-03-20 iteration → the claim then was that local couldn't do compaction (Ollama streaming broke it). That's resolved with MLX.

**Current principle: local 35B as compaction principal.** If compaction hallucinates or produces bad summaries, A/B test by temporarily setting `compaction.model: "anthropic/claude-sonnet-4-6"` for a session and comparing. Don't leave it set long-term unless local compaction fails repeatedly.

### `memoryFlush.softThresholdTokens: 10000`

Triggers the silent memory-flush turn when session tokens exceed `contextWindow - reserveTokens - softThresholdTokens` = 131072 - 20000 - 10000 ≈ 101000. Higher than the doc default (4000) because our flush prompt is long (writes 3 memory tiers + vault entry + refreshes VAULT_CONTEXT.md).

### `memoryFlush.forceFlushTranscriptBytes: "200kb"`

Force-triggers flush if the transcript JSONL exceeds 200 KB, independent of token count. Safety net for when token accounting diverges from actual size.

### `timeoutSeconds: 600` (10 min)

Higher than default to tolerate cold starts on the 35B and long tool-calling chains.

### `heartbeat.every: "4m"`

Polls `HEARTBEAT.md` every 4 minutes. Used by scheduled workflows. Don't disable unless you know what it costs.

### `subagents.maxConcurrent: 8`

Tight enough to not thrash the 35B's KV cache (each subagent opens a new session context).

## Known bugs / workarounds

### OpenClaw token tracking for openai-completions providers

Bug (2026-03-21): OpenClaw reports `contextTokens=1000000` after one hello message because it reads `max_position_embeddings` (262144) from the MLX model instead of actual usage from the response. Result: premature compaction trigger.

Workarounds in play:
1. `contextTokens: 131072` explicit (matches our KV cap)
2. `contextWindow: 131072` in `models.providers.mlx.models[0]`
3. `maxTokens: 8192` to bound output length

If this gets worse, track OpenClaw issue tracker — likely needs upstream fix.

### OpenClaw JS bundle patch for Ollama think-mode

Historical, dormant. File: `/opt/homebrew/lib/node_modules/openclaw/dist/reply-Bm8VrLQh.js`. Backup: `reply-Bm8VrLQh.js.backup`. Only relevant if Ollama serving comes back — since we're on MLX it doesn't apply.

**If OpenClaw updates via npm, the patch is wiped.** Re-apply only if reverting to Ollama.

## Operational slash commands (run inside any OpenClaw chat)

```
/status            — quick view: context fill, token counters, compaction count
/context list      — bootstrap file sizes, skill overhead, tool schemas
/context detail    — per-file breakdown + top tool schemas + top skills
/compact           — manually trigger compaction now
/compact Focus on decisions and open questions  — compaction with directive
/new  or /reset    — start fresh session id for this session key
```

## New OpenClaw features not yet configured

From the current docs:

1. **`session.maintenance`** — auto-prune stale `sessions.json` entries, rotate on size, enforce disk budget. Useful if `~/.openclaw/agents/*/sessions/` ever bloats.
2. **Memory plugins** (`plugins.slots.memory`) — custom backends for `memory_search` / `memory_get`. Could plug vault+aggregator here (see `memory-integration.md`). Default is `memory-core` which expects an embedding provider key we haven't set — so it runs BM25-only or disabled.
3. **QMD backend** (`memory.backend = "qmd"`) — faster hybrid search via external sidecar. Only worth it if memory corpus grows beyond a few hundred MB.

## To change settings safely

1. Back up first: `cp ~/.openclaw/openclaw.json ~/.openclaw/openclaw.json.bak.$(date +%s)`
2. Edit
3. Validate: `openclaw config get agents.defaults.compaction.reserveTokens` (reads the live parse, confirms OpenClaw accepts it — your edit might have trailing-comma issues that strict JSON parsers reject but OpenClaw's json5 accepts)
4. Restart OpenClaw gateway to pick up changes

## Related

- `client-openclaw.md` — the MLX provider block and the "no Anthropic baseUrl override" constraint
- `thinking-mode.md` — `enable_thinking: false` details
- `tool-calling.md` — how tool schemas contribute to context
- `memory-integration.md` — how to wire the vault into OpenClaw's memory layer
