# Troubleshooting — symptom → cause → fix

## MLX server

### "address already in use" on startup
- Stale process holding the port → `lsof -i TCP:11502 -sTCP:LISTEN` then `kill -9 <pid>`
- `mlx_servers.sh` has guards but sometimes misses edge cases

### Server starts, `/health` never passes 120s wait
- Likely loading the adapter (log shows "🎯 Loading LoRA adapter") — wait longer or check `~/jarvis/Logs/mlx/<seat>.log`
- If log shows MLX model download progress → first launch, let it finish

### `mlx_lm.server` exits immediately with argparse error
- You're passing `--chat-template-args` or `--adapter-path` to stock `mlx_lm.server` instead of `mlx_lm_server_lenient.py` / `mlx_vlm_server_with_tools.py`
- Fix: confirm `mlx_servers.sh` is invoking the right script per seat

### Responses are slow, `asitop` shows re-prefill every turn
- KV cache eviction. For MLX `lm_lenient`: check `--prompt-cache-size` value; default is 2, too low if many concurrent sessions
- For vLLM with Claude Code: Attribution Header (see `client-claude-code.md`)

## Tool calling

### `content: null`, `tool_calls: null` — both empty
- Thinking mode is ON → answer went to `reasoning` field
- Fix: `--chat-template-args '{"enable_thinking":false}'` at server launch AND `chat_template_kwargs.enable_thinking: false` in OpenClaw model params
- Verify: `curl .../v1/chat/completions` with a simple prompt, check response body for `reasoning` field

### Tool call fires but model keeps calling the same tool in a loop
- Tool result message isn't being appended correctly — check the role/content format
- For OpenClaw with MLX: `role: "tool"` messages must have `tool_call_id` matching the prior `tool_calls[*].id`
- For Claude Code with vLLM: `tool_result` blocks must reference `tool_use_id`

### `<tool_call>` block appears verbatim in final response content
- `mlx_vlm_server_with_tools.py` failed to parse — check server logs
- Usually caused by the model emitting a malformed `<tool_call>` block (missing closing tag, invalid JSON)
- Fix: higher temperature can sometimes help; re-prompt the model

### Tool schemas take 8K+ tokens in context
- Normal. Check `/context detail` in OpenClaw.
- To reduce: disable unused tools via `tools.<name>.enabled: false` in openclaw.json

## OpenClaw

### `contextTokens: 1000000` immediately after first message
- OpenClaw token tracking bug for openai-completions providers
- Mitigation in place: explicit `contextTokens: 131072` + `contextWindow: 131072` in config
- If you see 1,000,000 again: check that both keys are set and model is properly listed in `models.providers.mlx.models`

### Compaction fires on every message
- `reserveTokens` is too high for the model's context window
- Or `softThresholdTokens` is set too low — compaction fires before enough context builds
- Our settings: `reserveTokens: 20000`, `softThresholdTokens: 10000` — safe for 131K context

### OpenClaw silently falls back to Anthropic after a while
- Local MLX server died or is slow → fallback kicks in
- Check `~/jarvis/Logs/mlx/CSO.log`
- Check `openclaw config get agents.defaults.model.fallbacks` — should be `[]` unless you want Anthropic fallback

### Bootstrap files truncated without warning
- Our setting `bootstrapPromptTruncationWarning: "always"` should surface this
- Check `/context list` in session → shows raw vs injected sizes + TRUNCATED flag
- Fix: trim the bootstrap file, or raise `bootstrapMaxChars` / `bootstrapTotalMaxChars`

### Memory flush doesn't seem to fire
- Check `sessions.json` for `memoryFlushAt` and `memoryFlushCompactionCount`
- Flush runs **once per compaction cycle** — if compaction hasn't happened, flush hasn't either
- Workspace must be writable — if `workspaceAccess: "ro"`, flush is skipped

## Claude Code with vLLM

### First response fast, subsequent responses 5-10× slower
- Attribution Header killing KV cache
- Fix: header-stripping proxy (see `client-claude-code.md`)
- Verify: `scripts/attribution_header_check.sh`

### Claude Code refuses to start: "ANTHROPIC_AUTH_TOKEN not set"
- Set any non-empty string: `export ANTHROPIC_AUTH_TOKEN=local-vllm`

### Tool calls work but model gets stuck in "thinking" forever
- vLLM reasoning parser getting confused — ensure `--reasoning-parser qwen3` is set
- Enable thinking at model level: `enable_thinking: false` in chat_template_kwargs

### Claude Code shows "network error" repeatedly
- vLLM died or OOM'd. Check `nvidia-smi` / `asitop` and vLLM logs
- Restart vLLM

## Memory pressure

### 9B crashes when 35B is running vision
- 40 + 16 GB > 64 GB — expected
- Fix: stop 35B or stop 9B. They can't coexist with VLM enabled

### Coder seat makes the system thrash
- 35B (40 GB) + Coder (20 GB) = 60 GB → tight. Adding 9B pushes over
- Fix: stop 9B before starting Coder, or use Anthropic for whichever task Coder is doing

### `asitop` shows GPU at 100%, system sluggish
- Look for training processes (`ps aux | grep train_lora`) — never train + serve on the same machine
- Look for background Kronos batch jobs — `kronos_hunter.py` can spike MPS

## Kronos

### `forecast()` returns None
- Model loader failed. Check process startup logs for `"Kronos model failed to load"`
- Verify TUNING: `kronos.model_name` points at a valid path with `basemodel/best_model/`
- Verify MPS: `python -c "import torch; print(torch.backends.mps.is_available())"`

### MPS memory grows over time, system slows down
- Missing `torch.mps.empty_cache(); gc.collect()` between forecasts
- `kronos_inference.py` has this — if you wrote a new Kronos caller, replicate it

### Forecast values look wrong (all same price, flat line)
- Input candles not normalized to match what the model was trained on
- Current production `forex_m15_pip_norm_refined` expects pip-normalized OHLC + EMA sep + BB width
- Fix: check `kronos_runtime.py` for the normalization pipeline, confirm it matches training config

## Distillation / training

### "Metal ImpactingInteractivity" crash during 9B training
- NOT OOM. macOS killed the GPU command buffer for taking too long
- Fix: filter training data to ≤4000 chars
- Don't reduce layers as a workaround — the sequence length is the root cause

### RunPod 35B training stalled
- Check pod status; if dead, resume from latest checkpoint (every 500 steps)
- Do NOT use `--resume-adapter-file` in MLX — doesn't restore optimizer state, destabilizes training
- Start fresh from last checkpoint instead

### Merged model produces garbage
- Adapter incompatible with base — verify base version matches training config
- Verify merge command used the right `--base` and `--adapter` paths
- Re-run smoke test: generate a short response, compare to base-only output

## Vault / memory integration

### `sqlite3 ... "SELECT ..."` returns nothing
- FTS5 syntax error? `.schema` and `.tables` are dot-commands that don't work in `-c`. Use `-cmd '.schema'`
- Index stale? Try `knowledge/vault_writer.py` rebuild method

### `ast_nodes.json` missing
- Run `nexus-mapper` skill to regenerate
- Then run `python -c "from knowledge.nexus_bridge import NexusBridge; print(NexusBridge().run())"` to import into `_index.db`

### VAULT_CONTEXT.md is stale
- Run `python3 ~/Jarvis/knowledge/openclaw_vault_bridge.py --all`
- This is also triggered automatically by the OpenClaw `memoryFlush` prompt

## Related

- Each reference file covers its area in depth
- `scripts/health_check.sh` is the first stop for "is everything running?"
