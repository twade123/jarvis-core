# Serving — vLLM (for Claude Code's Anthropic bridge)

vLLM is **not the default serving stack** — MLX is. vLLM earns its keep specifically because it exposes the **Anthropic Messages API** with a built-in `qwen3_coder` tool-call parser. That's the only documented path to make the `claude` CLI use a local model.

## When to run vLLM

- You want Claude Code (the CLI) to talk to the local 35B
- You need the Anthropic-shape `tool_use` / `tool_result` content block protocol translated to Qwen's native `<tool_call>` format
- You're testing whether the distilled 35B can drop-in replace Opus end-to-end

## When NOT to run vLLM

- OpenClaw — use MLX on 11502 with `openai-completions` shape instead (OpenClaw's `anthropic` provider is hardwired to `api.anthropic.com`)
- Trading handlers (`handler_data_validator`, `handler_swarm`) — they call MLX directly via HTTP with OpenAI-shape or raw completion
- General batch inference — MLX is cheaper to launch and stay resident

## Install and launch

```bash
# Install (prebuilt wheels work on macOS with MPS via extra-index, or Linux with CUDA)
pip install vllm

# Serve the current 35B (base + combined_35b merged, or the direct MLX-merged path)
vllm serve ~/Jarvis/models/merged/qwen3.5-35b-jarvis \
  --port 8000 \
  --host 127.0.0.1 \
  --enable-auto-tool-choice \
  --tool-call-parser qwen3_coder \
  --reasoning-parser qwen3 \
  --max-model-len 131072
```

Key flags:
- `--enable-auto-tool-choice` — lets vLLM pick when to emit tool calls based on model output
- `--tool-call-parser qwen3_coder` — **the key flag** — translates Anthropic `tool_use` and OpenAI `tool_calls` ↔ Qwen native `<tool_call>` format
- `--reasoning-parser qwen3` — strips or exposes Qwen's reasoning blocks
- `--max-model-len 131072` — matches the model's full context; adjust if memory-constrained

## Point Claude Code at it

```bash
export ANTHROPIC_BASE_URL=http://localhost:8000/v1
# Claude Code also respects ANTHROPIC_AUTH_TOKEN but vLLM doesn't validate it
export ANTHROPIC_AUTH_TOKEN=local-vllm
claude
```

Verify:
```bash
curl http://localhost:8000/v1/models
```

## The Attribution Header KV cache gotcha

Claude Code prepends an **Attribution Header** to every request. This invalidates vLLM's KV cache → **90% speed drop**. Symptoms:
- First response is normal speed
- Every subsequent response takes ~10x longer
- `nvidia-smi` / `asitop` shows the GPU reloading weights between turns

**Fix**: see `unsloth.ai/docs/basics/claude-code`. The common workaround is a small proxy that strips the header before forwarding to vLLM.

`scripts/attribution_header_check.sh` in this skill probes vLLM logs for the header and reports.

## Training data format alignment

Our distillation flattens tool calls as `<tool_use>/<tool_result>` tags directly in message content. This teaches Qwen its NATIVE format. vLLM's `qwen3_coder` parser handles translation to/from Anthropic or OpenAI shape at request time. **No need to train on Anthropic's format specifically.**

Source: the 22,301-entry dataset includes 4,017 tool-calling arcs from 961 Claude Code sessions (210 main + 751 subagent).

## Documentation references

- `docs.vllm.ai/en/latest/serving/integrations/claude_code/`
- `unsloth.ai/docs/basics/claude-code` (Attribution Header fix)
- `alibabacloud.com/help/en/model-studio/claude-code` (Alibaba's parallel path)

## Verification after launch

```bash
# Test that tool calling actually works end-to-end
python3 .agents/skills/local-llm-operations/scripts/tool_call_smoke_test.py --endpoint anthropic --port 8000
```

## Coexistence with MLX

vLLM on 8000 and MLX on 11502 can both serve the same model simultaneously — they load independent copies though, so memory doubles. Acceptable for short-term testing; don't leave both resident long-term.

## Not in scope

- vLLM as a general serving replacement — MLX is the production choice
- Serving 9B via vLLM — 9B stays on MLX CRO seat for TA work; adding vLLM bridge for 9B would only matter if 9B becomes a Claude Code subagent backend, which isn't ready yet
