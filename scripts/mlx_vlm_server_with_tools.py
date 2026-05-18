#!/usr/bin/env python3
"""
MLX VLM server with tool calling + memory management + OpenAI /v1/ routing.

What this script does before calling mlx_vlm.server.main():

  1. Strips --model / --adapter-path / --max-kv-size from sys.argv so mlx_vlm's
     argparse doesn't reject them (it only knows --host / --port / --trust-remote-code).

  2. Patches get_cached_model to pin the model+adapter set at launch time,
     regardless of what each request's 'model' field says.

  3. Registers /v1/chat/completions and /v1/models routes (mlx_vlm uses bare
     paths; OpenAI clients expect /v1/ prefix).

  4. The /v1/chat/completions handler:
       - Accepts role="tool", role="function", content=None (OpenAI tool-calling pattern)
       - Normalizes those to what mlx_vlm expects (string content, standard roles)
       - Injects tools list into Qwen3.5 system prompt format when present
       - Calls gc.collect() + mx.metal.clear_cache() after each request to free
         KV cache buffers that mlx_vlm leaves in the Metal allocator

  5. Parses Qwen3.5 <tool_call>...</tool_call> output blocks into OpenAI tool_calls format.

Usage:
  python3 mlx_vlm_server_with_tools.py \\
      --model mlx-community/Qwen3.5-35B-A3B-4bit \\
      --port 11502 --host 127.0.0.1 \\
      [--adapter-path /path/to/adapter]
"""

import argparse
import gc
import json
import re
import sys
import uuid
from typing import Any, List, Optional

# ── 1. Parse our args before mlx_vlm.server.main() sees sys.argv ─────────────
_our_parser = argparse.ArgumentParser(add_help=False)
_our_parser.add_argument("--model", type=str, default=None)
_our_parser.add_argument("--adapter-path", type=str, default=None)
_our_parser.add_argument("--max-kv-size", type=int, default=None)  # accepted, ignored
_our_args, _remaining = _our_parser.parse_known_args()
sys.argv = [sys.argv[0]] + _remaining

_MODEL_PATH = _our_args.model
_ADAPTER_PATH = getattr(_our_args, "adapter_path", None)

# ── 2. Pin model+adapter in get_cached_model ─────────────────────────────────
import mlx.core as mx
import mlx_vlm.server as _vlm_server

_orig_get_cached_model = _vlm_server.get_cached_model


def _preloaded_get_cached_model(model_path: str, adapter_path: Optional[str] = None):
    effective_model = _MODEL_PATH if _MODEL_PATH else model_path
    effective_adapter = _ADAPTER_PATH if _ADAPTER_PATH else adapter_path
    return _orig_get_cached_model(effective_model, effective_adapter)


_vlm_server.get_cached_model = _preloaded_get_cached_model

# ── Patch: Disable mlx_vlm's auto tool-parser detection ──────────────────────
# 2026-05-02: mlx_vlm.server._infer_tool_parser inspects the chat template and
# returns "qwen3_coder" for any template containing <tool_call> markers. But
# qwen3_coder parser expects <function=name><parameter=k>v</parameter></function>
# (Qwen3-CODER format). Base Qwen3.5-35B-A3B emits JSON-style
# <tool_call>{"name":"...","arguments":{...}}</tool_call>. The mismatch makes
# qwen3_coder.parse_tool_call() raise ValueError; mlx_vlm catches it AND strips
# the <tool_call> block from the remaining content via re.sub. Result: empty
# content, empty tool_calls — 21 tokens of valid JSON tool call evaporate.
# Force tool_parser_type = None so mlx_vlm leaves model output intact, and our
# _parse_tool_calls_in_response handles the JSON format below.
_vlm_server._infer_tool_parser = lambda *_a, **_kw: None

# ── Patch: Fix enable_thinking=False for vision requests ─────────────────────
# mlx_vlm.prompt_utils.apply_chat_template silently drops enable_thinking kwarg.
# For Qwen3.5 vision requests, the formatted prompt ends with "<think>\n"
# (thinking mode ON). We need it to end with "<think>\n\n</think>\n\n"
# (empty think block = thinking mode OFF → produces JSON not prose).
_orig_apply_chat_template = None
try:
    from mlx_vlm import prompt_utils as _pu
    _orig_apply_chat_template = _pu.apply_chat_template

    def _patched_apply_chat_template(*args, **kwargs):
        result = _orig_apply_chat_template(*args, **kwargs)
        if isinstance(result, str) and result.endswith("<think>\n"):
            result += "\n</think>\n\n"
        return result

    _pu.apply_chat_template = _patched_apply_chat_template
    _vlm_server.apply_chat_template = _patched_apply_chat_template
except Exception:
    pass  # non-fatal — ghost replay uses direct calls as fallback

# ── Tool calling helpers ──────────────────────────────────────────────────────

def _build_qwen_tools_system(tools: List[Any]) -> str:
    """Format tools list into Qwen3.5's expected system prompt block."""
    tool_descs = []
    for t in tools:
        fn = t.get("function") if t.get("type") == "function" else (t if "name" in t else None)
        if fn:
            tool_descs.append(json.dumps(fn, ensure_ascii=False))
    if not tool_descs:
        return ""
    return (
        "You are a helpful assistant with access to the following tools:\n\n"
        "<tools>\n" + "\n".join(tool_descs) + "\n</tools>\n\n"
        "When you need to call a tool, respond with:\n"
        "<tool_call>\n{\"name\": \"<tool_name>\", \"arguments\": {<args>}}\n</tool_call>\n"
        "You may call multiple tools sequentially. "
        "When you have all needed information, provide your final answer."
    )


_TOOL_CALL_RE = re.compile(r'<tool_call>\s*(.*?)\s*</tool_call>', re.DOTALL)
# Qwen3-Coder XML format inside <tool_call>: <function=NAME><parameter=K>V</parameter>...</function>
# Our 35b_mlx LoRA adapter emits this format under load (32 tools + long context)
# even though the base Qwen3.5 model emits JSON in simpler cases.
_CODER_FUNC_RE = re.compile(r'<function=([^>]+)>(.*?)</function>', re.DOTALL)
_CODER_PARAM_RE = re.compile(r'<parameter=([^>]+)>(.*?)</parameter>', re.DOTALL)


def _parse_one_tool_call_block(raw: str) -> Optional[dict]:
    """Try to parse a single <tool_call> body. Handles two formats:

      1. JSON:  {"name": "...", "arguments": {...}}
      2. Coder: <function=NAME><parameter=K>V</parameter>...</function>

    Returns an OpenAI-format tool_call dict, or None if neither parses.
    """
    raw = raw.strip()
    # Format 1: JSON (used by base Qwen3.5)
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict) and "name" in parsed:
            return {
                "id": f"call_{uuid.uuid4().hex[:8]}",
                "type": "function",
                "function": {
                    "name": parsed.get("name", ""),
                    "arguments": json.dumps(parsed.get("arguments", {})),
                },
            }
    except (json.JSONDecodeError, ValueError):
        pass
    # Format 2: Coder XML (used by 35b_mlx adapter under load)
    fn_match = _CODER_FUNC_RE.search(raw)
    if fn_match:
        fn_name = fn_match.group(1).strip()
        body = fn_match.group(2)
        args = {}
        for pname, pval in _CODER_PARAM_RE.findall(body):
            args[pname.strip()] = pval.strip()
        return {
            "id": f"call_{uuid.uuid4().hex[:8]}",
            "type": "function",
            "function": {
                "name": fn_name,
                "arguments": json.dumps(args),
            },
        }
    return None


def _parse_tool_calls_in_response(response: Any) -> Any:
    """Parse Qwen <tool_call> blocks (JSON or Coder XML) into OpenAI tool_calls."""
    try:
        choices = response.get("choices", []) if isinstance(response, dict) else getattr(response, "choices", [])
        for choice in choices:
            if isinstance(choice, dict):
                msg = choice.get("message", {})
                content = msg.get("content", "") or ""
            else:
                msg = getattr(choice, "message", None)
                content = getattr(msg, "content", "") or ""

            matches = _TOOL_CALL_RE.findall(content)
            if not matches:
                continue

            tool_calls = []
            for raw in matches:
                tc = _parse_one_tool_call_block(raw)
                if tc is not None:
                    tool_calls.append(tc)

            if not tool_calls:
                continue

            clean_content = _TOOL_CALL_RE.sub("", content).strip() or None
            if isinstance(choice, dict):
                choice["message"]["content"] = clean_content
                choice["message"]["tool_calls"] = tool_calls
                choice["finish_reason"] = "tool_calls"
            else:
                if msg:
                    msg.content = clean_content
                    msg.tool_calls = tool_calls
                choice.finish_reason = "tool_calls"
    except Exception:
        pass
    return response

# ── 3+4+5. Register /v1/ routes with full OpenAI compatibility ────────────────
from fastapi import Request as _FastAPIRequest
from mlx_vlm.server import (
    app as _app,
    chat_completions_endpoint as _orig_chat_completions,
    models_endpoint,
    ChatRequest as _OrigChatRequest,
)


async def _v1_chat_completions(request: _FastAPIRequest):
    """
    /v1/chat/completions — full OpenAI compatibility layer.

    Handles what mlx_vlm's ChatRequest rejects:
      - role="tool" / role="function" messages (→ normalized to "user")
      - content=None on assistant tool_call messages (→ normalized to string)
      - tools/tool_choice fields (→ injected into Qwen3.5 system prompt)

    Also calls gc.collect() + mx.metal.clear_cache() after every request
    to free KV cache buffers from the Metal allocator (mlx_vlm has no
    RotatingKVCache, so without this memory grows unbounded).
    """
    body = await request.json()

    # 2026-05-03: TRADING-TEAM PASSTHROUGH.
    # Pre-May-2 (when this wrapper's route was registered second and effectively
    # dead code), trading-team requests went straight to mlx_vlm's native
    # chat_completions_endpoint. They have NO tools and NO streaming. After we
    # added the route override on May 2, all my preprocessing started running
    # for these requests too — and validator/TA output regressed (avg conditions
    # 6.8 → 2.7, prices missing from chart_reads, structured re_entry_conditions
    # going empty). To restore pre-May-2 behavior for the trading team without
    # losing the OpenClaw fixes, short-circuit non-tool/non-stream requests
    # straight to native handling. Only OpenClaw / tool-calling / streaming
    # requests fall through to the wrapper's full preprocessing below.
    if not body.get("tools") and not body.get("stream", False):
        try:
            _native_req = _OrigChatRequest(**body)
            return await _orig_chat_completions(_native_req)
        finally:
            gc.collect()
            mx.metal.clear_cache()

    # Inject tools into system prompt
    tools = body.get("tools")
    if tools:
        tools_block = _build_qwen_tools_system(tools)
        if tools_block:
            msgs = list(body.get("messages", []))
            injected = False
            for i, msg in enumerate(msgs):
                if msg.get("role") == "system":
                    msgs[i] = {**msg, "content": tools_block + "\n\n" + (msg.get("content") or "")}
                    injected = True
                    break
            if not injected:
                msgs.insert(0, {"role": "system", "content": tools_block})
            body = {**body, "messages": msgs}

    # Normalize messages
    normalized = []
    for msg in body.get("messages", []):
        role = msg.get("role", "user")
        content = msg.get("content")

        if role == "tool" or role == "function":
            # Qwen3.5 distillation trained on native <tool_response> tags.
            # Prior prose format "[Tool result for call_X]: ..." caused the model
            # to loop-call the same tool (observed 2026-04-23 on validator/validate_full).
            _tool_content = str(content or "")
            # Detect error/empty results and append a terminal hint so the model
            # doesn't retry the same tool with different args. Matches the
            # behavior Opus's prompt teaches: on error, note it and proceed.
            _lc = _tool_content.lower()
            _is_error = (
                not _tool_content.strip()
                or _tool_content.strip() in ("{}", "null", "[]")
                or '"error"' in _lc
                or "no such table" in _lc
                or "no such column" in _lc
                or '"not found"' in _lc
                or "traceback" in _lc
            )
            if _is_error:
                _tool_content = (
                    f"{_tool_content}\n\n"
                    "NOTE: This tool returned an error or empty data. "
                    "The underlying data is unavailable — do NOT retry this tool. "
                    "Proceed with your verdict using the chart + context data you already have."
                )
            normalized.append({
                "role": "user",
                "content": f"<tool_response>\n{_tool_content}\n</tool_response>",
            })
        else:
            if content is None:
                tcs = msg.get("tool_calls", [])
                content = "[Calling tools: {}]".format(
                    ", ".join(tc.get("function", {}).get("name", "?") for tc in tcs)
                ) if tcs else ""
            # Convert Anthropic image format → OpenAI image_url format
            # Swarm sends: {"type": "image", "source": {"type": "base64", "media_type": "...", "data": "..."}}
            # mlx_vlm expects: {"type": "image_url", "image_url": {"url": "data:image/png;base64,..."}}
            if isinstance(content, list):
                converted = []
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "image":
                        src = block.get("source", {})
                        if src.get("type") == "base64" and src.get("data"):
                            mt = src.get("media_type", "image/png")
                            converted.append({
                                "type": "image_url",
                                "image_url": {"url": f"data:{mt};base64,{src['data']}"},
                            })
                        else:
                            converted.append(block)
                    else:
                        converted.append(block)
                content = converted
            normalized.append({**msg, "content": content})

    # Pass chat_template_kwargs through — critical for Qwen3.5 thinking mode control.
    # When enable_thinking=False, the template injects an empty <think></think> block
    # that tells the model to skip reasoning and go straight to the answer.
    # Without this, Qwen3.5 burns all max_tokens on thinking and never produces JSON.
    _chat_kwargs = body.get("chat_template_kwargs", {})

    # 2026-05-02: resolve enable_thinking for THIS request.
    # ChatRequest exposes enable_thinking as a top-level field (verified via
    # ChatRequest.model_fields). The chat_template_kwargs mechanism the
    # wrapper used previously gets silently dropped by mlx_vlm's chat-template
    # rendering for some request shapes. Passing enable_thinking as a top-level
    # field bypasses that drop and is what the model actually reads at template
    # render time.
    _enable_thinking = _chat_kwargs.get("enable_thinking", False) if _chat_kwargs else False
    if "enable_thinking" in body:
        _enable_thinking = bool(body["enable_thinking"])

    # 2026-05-03: build kwargs from body, ONLY including fields the client
    # explicitly provided (with non-null values). For fields the client omits,
    # let ChatRequest's Pydantic defaults handle them — this matches how the
    # native mlx_vlm.server endpoint behaves and avoids silent default drift.
    #
    # Why this matters: my earlier wrapper substituted temperature=0.7,
    # top_p=0.8 which diverged from native ChatRequest defaults (0.0, 1.0).
    # The validator sends temperature=0 explicitly but omits top_p; pre-route-
    # override (when wrapper was dead code), validator hit native endpoint and
    # got top_p=1.0. After route override, my wrapper forced top_p=0.8 — a
    # subtle behavioral change that correlated with validator output regression.
    #
    # Fields we DO actively control:
    #   - stream: always False upstream (the SSE-wrap branch handles client streaming)
    #   - enable_thinking: tool-calling and structured output need this False on Qwen3.5
    #   - model: pinned at launch time
    _kwargs = {
        "model": body.get("model", _MODEL_PATH or ""),
        "messages": normalized,
        "stream": False,
        "enable_thinking": _enable_thinking,
    }
    for _field in ("max_tokens", "temperature", "top_p", "top_k",
                   "min_p", "repetition_penalty", "seed"):
        if _field in body and body[_field] is not None:
            _kwargs[_field] = body[_field]

    vlm_request = _OrigChatRequest(**_kwargs)

    # 2026-05-03: RESTORED — attach tools as attribute on vlm_request so
    # mlx_vlm's apply_chat_template renders the proper Qwen tool block at
    # chat-template render time. Yesterday's removal broke validator (and
    # other tool-using agents): manual <tools> system-prompt injection alone
    # is insufficient — the model is trained to recognize the chat-template
    # tool block format, and without it produces shorter/less structured
    # output (validator avg conditions dropped 6.8 → 2.7 on 2026-05-03 vs
    # 2026-05-01).
    #
    # Why this is safe now: _infer_tool_parser=None above prevents mlx_vlm's
    # broken qwen3_coder auto-parser from running. The model emits either
    # JSON-format or Coder-format <tool_call> blocks depending on context;
    # _parse_tool_calls_in_response handles BOTH formats (added 2026-05-02).
    if tools:
        try:
            vlm_request.tools = tools
        except Exception:
            pass
        if body.get("tool_choice"):
            try:
                vlm_request.tool_choice = body.get("tool_choice")
            except Exception:
                pass

    # Inject chat_template_kwargs if the ChatRequest supports it
    if _chat_kwargs and hasattr(vlm_request, 'chat_template_kwargs'):
        vlm_request.chat_template_kwargs = _chat_kwargs
    elif _chat_kwargs:
        # Fallback: set as attribute even if not in schema
        try:
            vlm_request.chat_template_kwargs = _chat_kwargs
        except Exception:
            pass

    # 2026-05-02: track client's stream preference. Upstream call is always
    # non-streaming (preserves the long-prefill protection above), but if the
    # client asked for stream:true we wrap the result as a single-chunk SSE
    # response. OpenClaw and other OpenAI SSE clients expect text/event-stream
    # with `data: {...}\n\ndata: [DONE]\n\n`; without this they treat a JSON
    # body as "empty response detected" and silently retry/timeout.
    _client_wants_stream = bool(body.get("stream", False))

    try:
        response = await _orig_chat_completions(vlm_request)
        response = _parse_tool_calls_in_response(response)
        # Convert to dict and ensure OpenAI-compatible format.
        # mlx_vlm returns Pydantic models missing 'index', 'id', 'object', 'created'
        # which lm-evaluation-harness and other OpenAI clients expect.
        import time as _t
        try:
            resp_dict = response.model_dump() if hasattr(response, "model_dump") else (
                response.dict() if hasattr(response, "dict") else response
            )
        except Exception:
            resp_dict = response if isinstance(response, dict) else {"choices": []}
        if isinstance(resp_dict, dict):
            for i, choice in enumerate(resp_dict.get("choices", [])):
                if isinstance(choice, dict):
                    choice.setdefault("index", i)
            resp_dict.setdefault("id", f"chatcmpl-{uuid.uuid4().hex[:12]}")
            resp_dict.setdefault("object", "chat.completion")
            resp_dict.setdefault("created", int(_t.time()))
            # 2026-05-02: rename usage keys to OpenAI-standard names so OpenClaw's
            # token tracker can read them. mlx_vlm emits input_tokens/output_tokens
            # (Anthropic-ish); OpenAI spec requires prompt_tokens/completion_tokens.
            usage = resp_dict.get("usage")
            if isinstance(usage, dict):
                if "input_tokens" in usage and "prompt_tokens" not in usage:
                    usage["prompt_tokens"] = usage.pop("input_tokens")
                if "output_tokens" in usage and "completion_tokens" not in usage:
                    usage["completion_tokens"] = usage.pop("output_tokens")

        if _client_wants_stream:
            # Wrap the non-streaming response as a single-chunk SSE so OpenAI
            # SSE clients (OpenClaw embedded agent, etc.) get the format they
            # asked for.
            from fastapi.responses import StreamingResponse as _StreamingResponse

            chunk_obj = {
                "id": resp_dict.get("id", ""),
                "object": "chat.completion.chunk",
                "created": resp_dict.get("created", int(_t.time())),
                "model": resp_dict.get("model", body.get("model", "")),
                "choices": [],
            }
            for choice in resp_dict.get("choices", []):
                msg = choice.get("message", {}) or {}
                delta = {"role": "assistant"}
                if msg.get("content") is not None:
                    delta["content"] = msg.get("content", "")
                if msg.get("tool_calls"):
                    delta["tool_calls"] = msg["tool_calls"]
                chunk_obj["choices"].append({
                    "index": choice.get("index", 0),
                    "delta": delta,
                    "finish_reason": choice.get("finish_reason"),
                })
            usage_for_chunk = resp_dict.get("usage")
            if isinstance(usage_for_chunk, dict):
                chunk_obj["usage"] = usage_for_chunk

            async def _sse_one_shot():
                yield f"data: {json.dumps(chunk_obj)}\n\n"
                yield "data: [DONE]\n\n"

            return _StreamingResponse(
                _sse_one_shot(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                },
            )
        return resp_dict
    finally:
        gc.collect()
        mx.metal.clear_cache()


# 2026-05-02: REMOVE the original /v1/chat/completions route registered by
# mlx_vlm.server before adding our wrapper. FastAPI dispatches in route-order;
# the first matching route wins. Without removal, our wrapper is dead code
# and the original mlx_vlm endpoint handles requests directly — meaning our
# tool-call parsing, usage-key rename, and stream-force never execute.
# NOTE: app.routes is a read-only property; we must mutate app.router.routes
# (the underlying Starlette router's list, which is a regular list).
_app.router.routes[:] = [
    r for r in _app.router.routes
    if not (
        getattr(r, "path", None) == "/v1/chat/completions"
        and "POST" in (getattr(r, "methods", set()) or set())
    )
]
_app.router.routes[:] = [
    r for r in _app.router.routes
    if not (
        getattr(r, "path", None) == "/v1/models"
        and "GET" in (getattr(r, "methods", set()) or set())
    )
]
_app.add_api_route("/v1/chat/completions", _v1_chat_completions, methods=["POST"], response_model=None)
_app.add_api_route("/v1/models", models_endpoint, methods=["GET"])

# ── Run the standard mlx_vlm server ──────────────────────────────────────────
from mlx_vlm.server import main
main()
