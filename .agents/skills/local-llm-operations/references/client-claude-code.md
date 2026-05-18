# Client — Claude Code CLI → local model

## The key insight

Claude Code (the `claude` CLI) respects `ANTHROPIC_BASE_URL`. Setting it swaps the backend from `api.anthropic.com` to whatever you point at — IF that endpoint speaks the Anthropic Messages API.

vLLM ≥ recent versions implements the Anthropic Messages API natively when you enable the right flags. That's why Claude Code → vLLM works. MLX does NOT currently expose Anthropic Messages routes, so Claude Code → MLX does NOT work directly. Use vLLM for this pathway.

## End-to-end setup

### 1. Serve the model with vLLM

See `serving-vllm.md` for full details. Minimum:

```bash
vllm serve ~/Jarvis/models/merged/qwen3.5-35b-jarvis \
  --port 8000 \
  --enable-auto-tool-choice \
  --tool-call-parser qwen3_coder \
  --reasoning-parser qwen3
```

### 2. Point Claude Code at it

```bash
export ANTHROPIC_BASE_URL=http://localhost:8000/v1
export ANTHROPIC_AUTH_TOKEN=local-vllm      # vLLM doesn't validate, but Claude Code requires it
claude
```

Or use the wrapper script: `source scripts/claude_code_local.sh`.

### 3. Verify

Inside Claude Code, try a simple tool call:
> "List the files in the current directory"

Expected: Claude Code emits a `Bash` tool call, vLLM returns it, Claude Code executes. If you see it hang or return empty, check the gotchas below.

## Gotcha #1 — Attribution Header kills KV cache (90% slowdown)

Claude Code prepends a proprietary **Attribution Header** to every request. vLLM treats it as part of the prompt, which invalidates the prefix KV cache. Every request re-computes the entire context from scratch.

Symptoms:
- First response is reasonable speed
- Subsequent responses take 5-10x longer
- `asitop` shows the GPU doing full prefill on every turn

Fix: strip the header with a tiny proxy. Reference implementation: `unsloth.ai/docs/basics/claude-code`. Pattern:

```python
# header_stripper.py — runs on a different port, forwards to vLLM
import httpx
from fastapi import FastAPI, Request

app = FastAPI()
VLLM_URL = "http://localhost:8000"

@app.post("/{path:path}")
async def proxy(path: str, request: Request):
    body = await request.body()
    headers = dict(request.headers)
    # Strip the attribution header — check your vLLM logs for the exact key name
    headers.pop("x-claude-attribution", None)
    headers.pop("anthropic-attribution", None)
    async with httpx.AsyncClient() as client:
        r = await client.post(f"{VLLM_URL}/{path}", content=body, headers=headers)
        return r.json()
```

Then point Claude Code at the proxy: `export ANTHROPIC_BASE_URL=http://localhost:8001/v1`.

`scripts/attribution_header_check.sh` in this skill probes vLLM logs for the header.

## Gotcha #2 — Enable thinking must be false

Same as OpenClaw — if the model is in thinking mode, answers go to `reasoning` instead of `content`, and Claude Code sees empty responses.

The `--reasoning-parser qwen3` flag on vLLM handles extraction, but the underlying chat template should still be set to `enable_thinking=false` via the request's `chat_template_kwargs`. Check your vLLM launch config.

## Gotcha #3 — Max context alignment

If vLLM's `--max-model-len` is smaller than Claude Code's session buffer, Claude Code can trigger endless context-overflow retries. Match `--max-model-len 131072` to the model's actual window.

## Gotcha #4 — Auth token is required even though vLLM ignores it

Claude Code refuses to start without `ANTHROPIC_AUTH_TOKEN` set. Any non-empty string works.

## Subagents in Claude Code

When Claude Code spawns subagents (via the `Agent` tool), they inherit the `ANTHROPIC_BASE_URL`. Subagents will also use the local 35B. Per our architecture: **that's correct — subagents stay on 35B until 9B is distilled for that role**.

If you want subagents to use a different model (e.g., test the 9B), you'd need a proxy that routes based on request metadata. Not currently implemented.

## Verifying tool calling works

```bash
python3 .agents/skills/local-llm-operations/scripts/tool_call_smoke_test.py \
  --endpoint anthropic \
  --port 8000
```

Tests an Anthropic-shape tool_use round trip against vLLM. See `scripts/tool_call_smoke_test.py`.

## When to use this pathway

- Testing whether the distilled 35B can drop-in replace Opus for Claude Code workflows
- Long coding sessions where the Max plan cost matters
- Offline / air-gapped work
- Prompt caching experiments (vLLM supports prefix cache; Claude Code rate-limits are irrelevant)

## When NOT to use this pathway

- Quick one-shot queries — Max plan Claude Code is faster to spin up
- Vision-heavy work — MLX's VLM tool-calling server is better tested for that
- Production agent workloads — go through OpenClaw
