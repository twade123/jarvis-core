# Tool Calling — Three shapes, one model

The same local model (Qwen3.5 35B/9B) sees tool calls in THREE different formats depending on who's asking. Understanding the hops is the difference between "it works" and "silently returns empty content."

## The three shapes

### 1. Anthropic Messages API — `tool_use` / `tool_result` content blocks

```json
{
  "role": "assistant",
  "content": [
    { "type": "text", "text": "I'll check the weather." },
    { "type": "tool_use", "id": "toolu_01", "name": "get_weather",
      "input": { "city": "SF" } }
  ]
}
```

Response from tool:
```json
{
  "role": "user",
  "content": [
    { "type": "tool_result", "tool_use_id": "toolu_01", "content": "72°F" }
  ]
}
```

**Who speaks this**: Claude Code CLI, Anthropic SDK, any direct Claude API consumer.

### 2. OpenAI Chat Completions — `tool_calls` array + `role: "tool"` messages

```json
{
  "role": "assistant",
  "content": null,
  "tool_calls": [
    { "id": "call_01", "type": "function",
      "function": { "name": "get_weather",
                    "arguments": "{\"city\":\"SF\"}" } }
  ]
}
```

Response:
```json
{ "role": "tool", "tool_call_id": "call_01", "content": "72°F" }
```

**Who speaks this**: OpenClaw (to MLX), our direct handler HTTP calls to MLX, any OpenAI SDK consumer.

### 3. Qwen native — `<tool_call>` XML blocks inside content

```
<tool_call>
{"name": "get_weather", "arguments": {"city": "SF"}}
</tool_call>
```

Response (fed back as a system/user turn):
```
<tool_response>72°F</tool_response>
```

**Who speaks this**: The Qwen3.5 model itself. This is what actually goes into and comes out of the model's tokenizer.

## The translation hops

```
┌──────────────────┐
│  Claude Code     │  Anthropic tool_use
│  (ANTHROPIC_     │─────────────┐
│  BASE_URL)       │             │
└──────────────────┘             ▼
                          ┌──────────────┐
                          │  vLLM        │
                          │  --tool-call-│  parses Anthropic ↔ Qwen via qwen3_coder
                          │  parser      │
                          │  qwen3_coder │
                          └───────┬──────┘
                                  │  Qwen native <tool_call>
                                  ▼
                          ┌──────────────┐
┌──────────────────┐      │  35B model   │
│  OpenClaw        │      │              │
│  (openai-        │      │  always sees │
│  completions)    │      │  native      │
└────────┬─────────┘      └──────┬───────┘
         │  OpenAI tool_calls    │  Qwen native <tool_call>
         ▼                       │
┌──────────────────────────┐     │
│  mlx_vlm_server_with_    │◀────┘
│  tools.py                │  parses Qwen <tool_call> ↔ OpenAI tool_calls
└──────────────────────────┘
```

**The model always sees its native format.** Translation happens at the serving boundary — either in vLLM (`qwen3_coder` parser) or in our `mlx_vlm_server_with_tools.py`.

This is why our distillation training data uses `<tool_use>/<tool_result>` tags directly in content — it teaches Qwen its native format, and the server translates as needed. We do NOT need to train separately for Anthropic and OpenAI shapes.

## Who to use when

| Client | Serving stack | Tool-call shape at the wire |
|---|---|---|
| OpenClaw | MLX port 11502 (`mlx_vlm_server_with_tools.py`) | OpenAI `tool_calls` |
| Claude Code CLI (with `ANTHROPIC_BASE_URL`) | vLLM port 8000 | Anthropic `tool_use` |
| Handler code (handler_data_validator, handler_swarm) | MLX port 11502 direct HTTP | OpenAI `tool_calls` |
| Python testing / scripts | MLX port 11502 direct HTTP | OpenAI `tool_calls` |

## Tool-call schema cost

Tools show up in context TWO ways:
1. **Tool list text** in system prompt (human-readable)
2. **Tool schemas (JSON)** passed to the model (machine-readable, counts toward context)

Per-tool schemas can be significant — OpenClaw's `browser` tool schema alone is ~2500 tokens. In-session: run `/context detail` to see which tool schemas dominate. Our typical OpenClaw session spends ~8K tokens on tool schemas before any conversation.

## Common tool-calling failures (and fixes)

### Empty `content` field, nothing else

**Cause**: model is in thinking mode → answer goes to `reasoning` field which some clients don't read. Content is empty.

**Fix**: `enable_thinking: false` in both the `--chat-template-args` at server launch AND in the request `chat_template_kwargs` param.

### Tool call parsed but `arguments` is a string, not object

**Cause**: OpenAI format serializes `arguments` as a JSON string. Consumers must JSON-parse it.

**Fix**: `json.loads(tool_call["function"]["arguments"])` before use.

### `role: "tool"` message rejected by mlx_vlm

**Cause**: upstream `mlx_vlm.server` doesn't natively accept `role: "tool"`. 

**Fix**: already patched in `mlx_vlm_server_with_tools.py` — normalizes tool messages into plain strings the model can handle. If you see the error, confirm you're running our patched server, not stock `mlx_vlm.server`.

### Claude Code says "tool use failed" but vLLM logs show a successful response

**Cause**: Attribution Header corrupted the prefix → model produced malformed `<tool_call>` block → `qwen3_coder` parser failed silently.

**Fix**: strip the Attribution Header (see `client-claude-code.md`).

### `tool_calls` field has items but `content` is also non-empty

**Cause**: Qwen emitted text AND a tool call. OpenAI spec says `content: null` when tool_calls are present, but MLX passes through what the model produced.

**Fix**: clients should tolerate both being present. If strict, set a higher `temperature` or re-prompt the model to not narrate before calling tools.

## Testing tool calls end-to-end

```bash
# Test OpenAI shape (what OpenClaw uses) on port 11502
python3 .agents/skills/local-llm-operations/scripts/tool_call_smoke_test.py --endpoint openai --port 11502

# Test Anthropic shape (what Claude Code uses) on vLLM port 8000
python3 .agents/skills/local-llm-operations/scripts/tool_call_smoke_test.py --endpoint anthropic --port 8000
```

Both should make a single tool call, receive a mock result, and produce a final text response.

## Related

- `thinking-mode.md` — why `enable_thinking: false` matters for tool calls
- `client-openclaw.md` — the OpenAI-shape path
- `client-claude-code.md` — the Anthropic-shape path including Attribution Header
- `serving-mlx.md` — details of `mlx_vlm_server_with_tools.py`
- `serving-vllm.md` — `--tool-call-parser qwen3_coder`
- `distillation.md` — why we train on Qwen native `<tool_use>/<tool_result>`, not Anthropic format
