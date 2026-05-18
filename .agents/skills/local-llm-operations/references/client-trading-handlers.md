# Client — Trading / handler code → local models

## The current split

Trading pipeline uses **Anthropic + 9B + Kronos**. Every file below speaks whatever shape matches the target.

| Layer | Target | Shape |
|---|---|---|
| `handler_data_validator.py` validator pass | Anthropic (Opus/Sonnet) | Anthropic Messages API (official SDK) |
| `handler_data_validator.py` TA pass | Qwen3.5 9B on port 11500 | OpenAI-completions via raw HTTP |
| `handler_data_validator.py` ghost validator | Qwen3.5 35B on port 11502 | OpenAI-completions via raw HTTP |
| `handler_swarm.py` local model path | Qwen3.5 35B on port 11502 | OpenAI-completions via raw HTTP |
| `kronos_inference.py` / `kronos_runtime.py` | Kronos via MPS | in-process Python (no HTTP) |

**OpenAI-format is only used at the OpenClaw ↔ MLX boundary and for direct handler HTTP calls to MLX servers.** It's not an architectural choice — it's what MLX exposes.

## `LOCAL_MODEL_ENABLED` flag

Introduced in 2026-03-22 (`handler_data_validator.py` phase 4): a feature flag that routes the TA / ghost-validator pass to the local 9B / 35B while keeping the primary validator on Anthropic. Default: enabled.

## `LOCAL_MODEL_PORT`

Constant in `handler_data_validator.py`. Originally 11501 (DeepSeek), corrected to **11502** (35B) in 2026-04-13 when ghost validator was added. If you rearrange ports in `mlx_servers.sh`, update this constant.

## Ghost validator pattern

Every Anthropic validator call fires 35B in a background thread. Both verdicts parse; comparison logged to `ghost_verdicts` table in `boardroom.db`. Fields: `verdict_match`, `direction_match`, `confidence_delta`.

Target: 95%+ match rate over 50+ comparisons before routing primary validator to local.

## `handler_swarm.py` null-guard

35B returns `content: null` occasionally (especially under load). Without a null-guard, downstream code crashes. Fix applied 2026-04-14:

```python
content = response["choices"][0]["message"].get("content")
if content is None:
    logger.warning("35B returned null content; treating as empty response")
    content = ""
```

If you see `TypeError: NoneType has no attribute ...` in swarm logs, re-check that this guard is still in place.

## Timeout defaults

- TA pass → 120s
- Ghost validator → 300s (raised from 180s in 2026-04-14 because 35B VLM is slower with vision enabled)
- Kronos forecast → 60s per single forecast, 30s batched

Logged in `handler_data_validator.py` constants and `flight_recorder.db`.

## Chart vision for TA (9B)

TA narratives use chart vision. The 9B CRO seat runs `lm_lenient`, not `vlm_with_tools`. Chart vision is done by:
1. Loading the chart PNG
2. Base64-encoding it
3. Sending as an `image_url` content block in the OpenAI-shape request

Confirmed working in production as of 2026-04.

## Kronos loader reads TUNING

`kronos_inference.py::_default_model_loader()`:

```python
from tuning_config import TUNING
model_name = TUNING["kronos.model_name"]["value"]
tokenizer_path = TUNING.get("kronos.tokenizer_path", {}).get("value",
                                                             "NeoQuasar/Kronos-Tokenizer-base")
tokenizer = KronosTokenizer.from_pretrained(tokenizer_path)
model = Kronos.from_pretrained(model_name)
```

This is the gold-standard single-pointer pattern. Swapping Kronos versions is one `TUNING` row update.

## Graceful degradation

- **Kronos**: if load fails, `is_ready()` returns False; `forecast()` returns None. Trading continues normally.
- **Local 9B/35B**: if the server is down, handlers fall back to Anthropic (slower, costs money, but trading continues).
- **Anthropic**: if API fails, validator pass can fall back to ghost verdict from local 35B (configurable).

## Not to do

- Don't reach into MLX servers from trading code via Anthropic SDK — they speak OpenAI-completions
- Don't mix Anthropic SDK client with MLX URLs — the auth flow and request shape don't match
- Don't bypass the ghost validator to "test" local verdicts in production — use ghost mode explicitly via the `/api/trading/ghost-mode` endpoint

## Related

- `client-openclaw.md` — the OpenClaw side of the OpenAI bridge
- `tool-calling.md` — full explanation of the three tool-call shapes
- `models/kronos-base.md` — Kronos runtime details
- `memory-integration.md` — how handlers can read/write vault + nexus
