# Claude Code subagents + local model

How Claude Code subagents interact with the local 35B backend when `ANTHROPIC_BASE_URL` points at vLLM.

## What a subagent is

Claude Code's `Agent` tool spawns a sub-session with its own context. The main agent delegates a task, subagent runs independently, returns a summary. Main agent's context doesn't see subagent's intermediate tool calls — just the final summary.

## Subagents inherit `ANTHROPIC_BASE_URL`

When you launch `claude` with `ANTHROPIC_BASE_URL=http://localhost:8000/v1`, subagents spawned via the `Agent` tool also hit that URL. They use the same local 35B backend.

This is correct behavior: our distillation strategy is "35B for everything agent-shaped, including subagents, until 9B is distilled for subagent role."

## Context isolation between main + subagent

Each subagent gets:
- Its own session transcript
- Its own KV cache on the vLLM side
- Its own compaction state
- Independent tool-calling history

Main agent context is preserved through the subagent call — the main agent sees:
- Its own history up to the `Agent` tool call
- The subagent's final returned summary
- NOT the subagent's tool-calling intermediate state

## Memory interaction — the subtle point

OpenClaw's `memoryFlush` applies to the primary session, not to subagents. Claude Code CLI is a different harness and its memory layer is different. Key facts:

1. **vLLM prefix KV cache is per-session** — subagents start cold unless the exact prompt prefix matches a cached one. In practice: subagent ≠ cached, expect cold-start cost.

2. **Attribution Header still breaks KV cache on subagents** — same 90% slowdown issue applies. If you use header stripping, it helps both main and subagent traffic.

3. **Subagent tool schemas fill up independently** — if the main agent has 15 tools and the subagent inherits them, subagent's context also has ~8K tokens of schema overhead from turn 1.

4. **Vault + memory integration** — subagents can call `vault_search.py` or `vault_cli.py` same as main agent. They have the same skill access (via .claude/skills symlinks). When a subagent writes to vault, other agents (including the main agent) can find it later.

## Resource impact

**Concurrent subagents double memory pressure on vLLM.** Each spawned subagent = another session in vLLM's KV cache management. With max_model_len 131072 and multiple subagents, vLLM may evict caches aggressively.

Symptom: subagents start snappy, then noticeably slow after a few parallel spawns.

Mitigation:
- Limit concurrent subagents (Claude Code has a `maxConcurrent` equivalent for spawning)
- Run vLLM with `--gpu-memory-utilization 0.95` if you're not using the host GPU for anything else
- Use `--num-scheduler-steps 8` (default is 1) for throughput over latency

## When subagents should route elsewhere (future)

When the 9B v2 distillation completes and passes tool-calling gates:
- Main agent stays on 35B (port 11502 via OpenClaw's MLX or vLLM 8000 for Claude Code)
- Subagents could route to 9B (lighter, faster for small tasks)
- Requires a **model-routing proxy** — not yet implemented

Potential proxy shape: request header like `X-Jarvis-Role: subagent` → proxy picks 9B port. Would live between Claude Code and the actual model server.

**Current state**: no routing. All subagents use 35B. Keep it simple until 9B v2 proves out.

## Debugging subagent issues

### Subagent hangs or times out
- Check vLLM health: `curl http://127.0.0.1:8000/v1/models`
- Check vLLM memory: `asitop` or `nvidia-smi`. KV cache eviction storm looks like constant high GPU util with no throughput
- Claude Code timeout is typically 300s for an Agent tool call; if exceeded, subagent is killed

### Subagent returns garbage
- Attribution Header issue — see `references/client-claude-code.md`
- Enable thinking leaked on — check that vLLM has `--reasoning-parser qwen3`
- Model mismatch — verify vLLM is actually serving the distilled 35B, not a different model

### Subagent can't find a skill
- `.claude/skills/` symlinks to `.agents/skills/` — if broken, subagent sees fewer skills
- Check `ls -la ~/Jarvis/.claude/skills/`
- All entries should be symlinks (`->`), not real dirs

### Subagent writes to vault but main agent can't find it
- FTS index needs rebuild after new writes — happens automatically via `VaultWriter`
- If live-rebuild lags: `python3 -c "from knowledge.vault_writer import VaultWriter; VaultWriter('~/Jarvis/knowledge').reindex()"`

## Subagent prompt overhead

Each subagent spawn includes:
- System prompt (~6 KB in Claude Code's case)
- Tool schemas (~8 KB for the full set)
- Optional injected skill list (~2 KB)
- The task description (1-3 KB typical)

Total: ~17-20 KB of context before any model output. At 131K context window, there's plenty of room but this overhead repeats per-subagent — spawning 10 subagents in parallel costs ~170 KB of prompt processing.

## Not covered here

- OpenClaw subagents (different mechanism — handled by OpenClaw's own subagent plugin config)
- Claude Code's `Task` tool (same as `Agent` — alias)
- Cross-machine subagents (not configured)

## Related

- `client-claude-code.md` — ANTHROPIC_BASE_URL setup + Attribution Header fix
- `serving-vllm.md` — vLLM launch flags
- `tool-calling.md` — tool-call format when a subagent dispatches tools
- Distillation roadmap: Qwen 9B v2 is the potential subagent backend, see `collective/models/qwen3.5-9b/08-v2-retrain-plan.md`
