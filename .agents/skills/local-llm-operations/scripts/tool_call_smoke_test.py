#!/usr/bin/env python3
"""tool_call_smoke_test.py — end-to-end tool-calling smoke test for local models.

Tests that the local 35B can:
  1. See a tool schema
  2. Emit a tool call
  3. Receive a tool result
  4. Produce a final text response

Supports two endpoint shapes:
  --endpoint openai     (MLX server on 11502 — what OpenClaw uses)
  --endpoint anthropic  (vLLM server on 8000 — what Claude Code uses)

Usage:
  python3 tool_call_smoke_test.py --endpoint openai --port 11502
  python3 tool_call_smoke_test.py --endpoint anthropic --port 8000
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.request
import urllib.error


MOCK_WEATHER_TOOL_OPENAI = {
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "Get current weather for a city",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "City name"}
            },
            "required": ["city"],
        },
    },
}

MOCK_WEATHER_TOOL_ANTHROPIC = {
    "name": "get_weather",
    "description": "Get current weather for a city",
    "input_schema": {
        "type": "object",
        "properties": {
            "city": {"type": "string"}
        },
        "required": ["city"],
    },
}


def post_json(url: str, payload: dict, headers: dict) -> dict:
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"  ERROR {e.code}: {body[:500]}", file=sys.stderr)
        raise


def test_openai(port: int, model: str) -> bool:
    url = f"http://127.0.0.1:{port}/v1/chat/completions"
    print(f"→ POST {url}  [OpenAI shape, model={model}]")

    # Turn 1: give tool schema, expect tool_call back
    resp = post_json(url, {
        "model": model,
        "messages": [{"role": "user", "content": "What's the weather in San Francisco?"}],
        "tools": [MOCK_WEATHER_TOOL_OPENAI],
        "tool_choice": "auto",
        "max_tokens": 256,
        "chat_template_kwargs": {"enable_thinking": False},
    }, headers={"Authorization": "Bearer local"})

    msg = resp["choices"][0]["message"]
    tool_calls = msg.get("tool_calls") or []
    if not tool_calls:
        content = msg.get("content") or ""
        print(f"  ✗ no tool_calls. content={content[:200]!r}")
        return False

    tc = tool_calls[0]
    fn = tc.get("function") or {}
    print(f"  ✓ tool_call: {fn.get('name')}({fn.get('arguments')})")

    # Turn 2: feed tool result, expect final answer
    resp = post_json(url, {
        "model": model,
        "messages": [
            {"role": "user", "content": "What's the weather in San Francisco?"},
            {"role": "assistant", "content": None, "tool_calls": tool_calls},
            {"role": "tool", "tool_call_id": tc["id"], "content": "72°F and sunny"},
        ],
        "tools": [MOCK_WEATHER_TOOL_OPENAI],
        "max_tokens": 256,
        "chat_template_kwargs": {"enable_thinking": False},
    }, headers={"Authorization": "Bearer local"})

    final = resp["choices"][0]["message"].get("content") or ""
    if not final.strip():
        print("  ✗ final response empty")
        return False
    print(f"  ✓ final: {final[:200]!r}")
    return True


def test_anthropic(port: int, model: str) -> bool:
    url = f"http://127.0.0.1:{port}/v1/messages"
    print(f"→ POST {url}  [Anthropic shape, model={model}]")

    resp = post_json(url, {
        "model": model,
        "max_tokens": 256,
        "messages": [{"role": "user", "content": "What's the weather in San Francisco?"}],
        "tools": [MOCK_WEATHER_TOOL_ANTHROPIC],
    }, headers={
        "x-api-key": "local-vllm",
        "anthropic-version": "2023-06-01",
    })

    content_blocks = resp.get("content") or []
    tool_use = None
    for block in content_blocks:
        if block.get("type") == "tool_use":
            tool_use = block
            break
    if not tool_use:
        print(f"  ✗ no tool_use block. content={content_blocks}")
        return False
    print(f"  ✓ tool_use: {tool_use.get('name')}({tool_use.get('input')})")

    # Turn 2
    resp = post_json(url, {
        "model": model,
        "max_tokens": 256,
        "messages": [
            {"role": "user", "content": "What's the weather in San Francisco?"},
            {"role": "assistant", "content": content_blocks},
            {"role": "user", "content": [{
                "type": "tool_result",
                "tool_use_id": tool_use["id"],
                "content": "72°F and sunny",
            }]},
        ],
        "tools": [MOCK_WEATHER_TOOL_ANTHROPIC],
    }, headers={"x-api-key": "local-vllm", "anthropic-version": "2023-06-01"})

    text = ""
    for block in resp.get("content") or []:
        if block.get("type") == "text":
            text += block.get("text") or ""
    if not text.strip():
        print("  ✗ final text empty")
        return False
    print(f"  ✓ final: {text[:200]!r}")
    return True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--endpoint", choices=["openai", "anthropic"], default="openai")
    ap.add_argument("--port", type=int, default=None)
    ap.add_argument("--model", default=None)
    args = ap.parse_args()

    if args.endpoint == "openai":
        port = args.port or 11502
        model = args.model or "mlx-community/Qwen3.5-35B-A3B-4bit"
        ok = test_openai(port, model)
    else:
        port = args.port or 8000
        model = args.model or "qwen3.5-35b-jarvis"
        ok = test_anthropic(port, model)

    print("\nRESULT:", "PASS ✓" if ok else "FAIL ✗")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
