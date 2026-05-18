# Serving — MLX (the current production stack)

## The five seats

Source of truth: `~/Jarvis/scripts/mlx_servers.sh`.

```
CRO   | 11500 | mlx-community/Qwen3.5-9B-4bit              | lm_lenient | adapter: validator_35b
CTO   | 11501 | mlx-community/DeepSeek-R1-Distill-Qwen-14B-4bit | lm    | no adapter
CSO   | 11502 | mlx-community/Qwen3.5-35B-A3B-4bit          | lm_lenient | adapter: combined_35b
CDO   | 11503 | mlx-community/Qwen2.5-7B-Instruct-4bit      | lm        | no adapter
Coder | 11504 | mlx-community/Qwen2.5-Coder-32B-Instruct-4bit | lm      | no adapter (on-demand)
```

## Server types

- **`lm`** → `python -m mlx_lm.server` (stock text-only)
- **`lm_lenient`** → `scripts/mlx_lm_server_lenient.py` (text-only with KV cache cap, enables tool calling)
- **`vlm`** → `python -m mlx_vlm.server` (pure vision, model per-request)
- **`vlm_with_tools`** → `scripts/mlx_vlm_server_with_tools.py` (vision + tool calling, OpenAI-shape routes)

The CSO (35B) currently runs `lm_lenient` — text path with adapter. The `vlm_with_tools` variant exists for when the 35B needs to handle both vision AND tools in one request. To switch CSO to `vlm_with_tools`, edit `SEAT_CONFIG` in `mlx_servers.sh`.

## Commands

```bash
# Full status
bash ~/Jarvis/scripts/mlx_servers.sh status

# Start one seat
bash ~/Jarvis/scripts/mlx_servers.sh start CSO

# Start all 4 resident seats (CRO CTO CSO CDO — Coder excluded by default)
bash ~/Jarvis/scripts/mlx_servers.sh start

# Stop one seat
bash ~/Jarvis/scripts/mlx_servers.sh stop CSO

# Restart all
bash ~/Jarvis/scripts/mlx_servers.sh restart
```

Logs: `~/jarvis/Logs/mlx/{CRO,CTO,CSO,CDO,Coder}.log`

## Health signals

Each seat exposes `/health` and `/v1/models`. Startup waits up to 120s for `/health` before declaring failure.

```bash
curl -sf http://127.0.0.1:11502/health
curl -s http://127.0.0.1:11502/v1/models | jq
```

Use `scripts/health_check.sh` in this skill for a one-shot matrix probe.

## The `lm_lenient` server (`mlx_lm_server_lenient.py`)

What it patches vs stock `mlx_lm.server`:
- **KV cache cap via RotatingKVCache** — prevents unbounded accumulation across requests
- `strict=False` for adapter loading no longer needed since mlx_lm ≥ 0.31.1 — patch removed in 2026-03-21 migration
- Honors `--chat-template-args` for `enable_thinking=false`
- `--prompt-cache-size 2` for warm-cache reuse

## The `vlm_with_tools` server (`mlx_vlm_server_with_tools.py`)

What it does beyond `mlx_vlm.server`:
1. Strips `--model` / `--adapter-path` / `--max-kv-size` from `sys.argv` before calling `mlx_vlm.server.main()` (upstream argparse doesn't know them)
2. Patches `get_cached_model` to pin model + adapter at launch regardless of what each request's `model` field says
3. Registers `/v1/chat/completions` and `/v1/models` (upstream uses bare paths; OpenAI clients need `/v1/` prefix)
4. Accepts `role="tool"`, `role="function"`, `content=None` and normalizes
5. Injects tools list into Qwen3.5 system prompt (`<tools>...</tools>` block)
6. Parses Qwen3.5 `<tool_call>...</tool_call>` output blocks into OpenAI `tool_calls` format
7. Calls `gc.collect()` + `mx.metal.clear_cache()` after each request (mlx_vlm leaks KV buffers in Metal allocator)

## Adapter loading

Per seat in `mlx_servers.sh`:
```zsh
typeset -A SEAT_ADAPTER
SEAT_ADAPTER["CRO"]="${ADAPTER_ROOT}/validator_35b"
SEAT_ADAPTER["CSO"]="${ADAPTER_ROOT}/combined_35b"
SEAT_ADAPTER["CTO"]=""
SEAT_ADAPTER["CDO"]=""
```

When set and the directory contains `.safetensors` files, the server launches with `--adapter-path <dir>` and logs `🎯 Loading LoRA adapter`.

## Stale-process guards

`mlx_servers.sh` start checks:
1. TCP port already LISTENing → skip spawn
2. `pgrep -f "mlx_.*--port ${port}"` → skip spawn
3. Different server type on the same port → kill stale process with SIGKILL

This prevents the common "I restarted but it's still serving the old adapter" problem.

## MLX vs Ollama (why we dropped Ollama)

- Ollama returned inaccurate / missing token counts (`prompt_tokens=0`) → broke OpenClaw compaction timing
- Ollama streaming doesn't emit `tool_calls` delta chunks → tool calls silently fail, compaction silently fails
- MLX returns accurate `usage` data

**Don't reintroduce Ollama for serving.** GGUF pipeline is kept at `~/Jarvis/models/gguf/` as a cold export tool for future non-Apple deployment, not for local serving.

## Upgrading mlx-lm

- mlx_lm 0.30.7 → 0.31.1 in the 2026-03-21 migration (removed `strict=False` patch)
- transformers 4.57.6 → 5.3.0 in the same migration
- When bumping mlx-lm: re-test `mlx_lm_server_lenient.py` (KV cache cap uses internal APIs that shift between versions)
