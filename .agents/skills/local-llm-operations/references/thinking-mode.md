# Thinking / Reasoning Mode

## The rule

For tool-calling workloads on Qwen3.5, **`enable_thinking: false` is mandatory**.

For reasoning-only workloads (no tool calls, just text generation where CoT is valuable), `enable_thinking: true` can be left default.

## Why it matters

Qwen3.5 with thinking enabled splits its output:
- `reasoning` field → the chain-of-thought
- `content` field → the final answer

**With limited `max_tokens`, the thinking budget eats the answer budget.** The `content` field returns empty. OpenClaw and Claude Code only read `content`, see nothing, and silently fail.

This was the #1 cause of "OpenClaw is broken" symptoms in the 2026-03-20 audit.

## Where to set it

### MLX server launch (for 35B CSO and 9B CRO)

In `scripts/mlx_servers.sh`:

```bash
nohup python3 "$LENIENT_SCRIPT" \
  --model "$model" \
  --port "$port" \
  --host 127.0.0.1 \
  --chat-template-args '{"enable_thinking":false}' \
  ...
```

The `--chat-template-args` flag passes directly to the chat template during tokenization. This is the baseline setting.

### OpenClaw config (belt-and-suspenders)

In `~/.openclaw/openclaw.json`:

```json5
"agents": {
  "defaults": {
    "models": {
      "mlx/mlx-community/Qwen3.5-35B-A3B-4bit": {
        "params": {
          "think": false,
          "chat_template_kwargs": { "enable_thinking": false }
        }
      }
    }
  }
}
```

Both keys: `think: false` is OpenClaw's own param hint; `chat_template_kwargs.enable_thinking: false` is passed through to the model.

### vLLM server launch

vLLM handles this differently — use `--reasoning-parser qwen3`:

```bash
vllm serve ... --reasoning-parser qwen3
```

vLLM then extracts reasoning blocks and puts them in a separate response field that Claude Code handles correctly. You don't need to disable thinking at the model level in this path.

## When thinking IS wanted

### DeepSeek-R1-Distill-Qwen-14B (CTO seat)

DeepSeek-R1 is specifically distilled for reasoning. Its `<think>` blocks are the POINT. Don't disable thinking on the CTO seat. `mlx_servers.sh` doesn't pass `--chat-template-args` for CTO — correct.

### Qwen3.5 in reasoning-only tasks

If you want the 35B or 9B to do CoT for a non-tool-calling task, you can enable thinking per-request by overriding `chat_template_kwargs` in a single request. But if you're using OpenClaw or Claude Code with tools, leave it disabled globally.

## OpenClaw's `/think` directive

Users can send `/think:off`, `/think:low`, `/think:medium`, `/think:high`, `/think:adaptive` per message or per session. From `/opt/homebrew/lib/node_modules/openclaw/docs/tools/thinking.md`:

| Level | Mapping |
|---|---|
| `off` | No thinking |
| `minimal` | "think" |
| `low` | "think hard" |
| `medium` | "think harder" |
| `high` | "ultrathink" (max budget) |
| `adaptive` | provider-managed (Anthropic Claude 4.6 only) |

For the local 35B/9B: the `/think` directive currently has no effect — our `enable_thinking: false` override wins. If you want to respect `/think` on local models, you'd need to conditionally enable thinking per request, which OpenClaw doesn't natively do for custom `openai-completions` providers.

## Reasoning visibility (`/reasoning`)

Separate from thinking. Controls whether the reasoning trace is surfaced to the user in a separate "Reasoning:" message. Default: off. For local 35B/9B with thinking disabled, this has no effect. For DeepSeek-R1 it does.

## Symptoms and fixes

### Empty `content`, request returns successfully

Thinking mode is active. Check:
1. Is `--chat-template-args '{"enable_thinking":false}'` on the `mlx_lm_server_lenient.py` launch command? → `ps aux | grep lenient`
2. Is `chat_template_kwargs.enable_thinking: false` in the OpenClaw model params? → `openclaw config get 'agents.defaults.models.mlx/mlx-community/Qwen3.5-35B-A3B-4bit.params.chat_template_kwargs'`

### Responses are slow with long pauses

Thinking mode likely active and burning tokens on CoT before answering. Same fix as above.

### Tool calls never emit

Thinking mode puts the `<tool_call>` block inside the `reasoning` field, not `content`. Servers parse from content, so the call is lost. Same fix.

## Related

- `tool-calling.md` — why empty content + thinking mode break tool calling
- `client-openclaw.md` — the MLX provider config where thinking params live
- `models/deepseek-r1-14b.md` — the one seat where thinking is desired
