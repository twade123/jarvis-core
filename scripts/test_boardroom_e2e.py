#!/usr/bin/env python3
"""
End-to-end boardroom deliberation test.

Loads board members from DB via load_boardroom_into_swarm,
runs each through a topic, collects responses.

Usage:
    python3 scripts/test_boardroom_e2e.py
    python3 scripts/test_boardroom_e2e.py --seats CRO,CDO   # test specific seats
    python3 scripts/test_boardroom_e2e.py --with-tools       # enable MCP tools
"""
import sys, os, json, asyncio, time, argparse, logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s: %(message)s")
logging.getLogger("Jarvis_Agent_SDK.database_directory").setLevel(logging.WARNING)
logging.getLogger("Handler.modules.claude_client").setLevel(logging.WARNING)


TOPIC = (
    "We need to decide: should we add WebSocket real-time data feeds to the trading "
    "dashboard, or keep HTTP polling? The trading team runs on H1 candles so data isn't "
    "ultra-time-sensitive, but the dashboard feels sluggish. Budget is tight — we want "
    "zero additional API cost. Analyze from your perspective."
)


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seats", default="CRO,CTO,CSO,CDO",
                        help="Comma-separated seats to test")
    parser.add_argument("--with-tools", action="store_true",
                        help="Enable MCP tools (slower, tests full pipeline)")
    parser.add_argument("--topic", default=TOPIC, help="Deliberation topic")
    args = parser.parse_args()

    requested_seats = [s.strip() for s in args.seats.split(",")]
    tool_rounds = 3 if args.with_tools else 0

    from Handler.handler_swarm import SwarmHandler
    from Handler.boardroom_template import load_boardroom_into_swarm

    swarm = SwarmHandler()

    # Load boardroom from DB
    print("\n" + "=" * 60)
    print("BOARDROOM E2E TEST")
    print("=" * 60)

    print("\n📋 Loading boardroom from DB...")
    result = await load_boardroom_into_swarm(swarm, user_id=2)
    print(f"   Workspace: {result['workspace_id']}")
    print(f"   Members loaded: {result['members']}")
    print(f"   Registered in swarm: {list(swarm.agents.keys())}")

    # Verify MLX server availability for each seat
    import urllib.request
    # mlx_vlm servers use /models; mlx_lm servers use /v1/models
    MLX_PORTS = {"CRO": 11500, "CTO": 11501, "CSO": 11502, "CDO": 11503}
    VLM_SEATS = {"CRO", "CSO"}  # mlx_vlm.server — no /v1/ prefix
    print("\n🔌 Checking MLX servers...")
    available_seats = []
    for seat in requested_seats:
        port = MLX_PORTS.get(seat)
        if not port:
            print(f"   ⚠️  {seat}: no MLX port configured")
            continue
        # Try the correct endpoint for each server type, with fallback
        endpoints = ["/models", "/v1/models"] if seat in VLM_SEATS else ["/v1/models", "/models"]
        found = False
        for endpoint in endpoints:
            try:
                req = urllib.request.Request(f"http://127.0.0.1:{port}{endpoint}")
                with urllib.request.urlopen(req, timeout=3) as resp:
                    data = json.loads(resp.read())
                    model_id = data["data"][0]["id"]
                    server_type = "vlm" if seat in VLM_SEATS else "lm"
                    print(f"   ✅ {seat} ({server_type}): port {port} → {model_id}")
                    available_seats.append(seat)
                    found = True
                    break
            except Exception:
                continue
        if not found:
            print(f"   ❌ {seat}: port {port} not responding")

    if not available_seats:
        print("\n❌ No MLX servers running. Start them with: ./scripts/mlx_servers.sh start")
        return

    # Run deliberation
    print(f"\n📢 Topic: {args.topic[:100]}...")
    print(f"   Tool rounds: {tool_rounds}")
    print()

    results = {}
    total_time = 0
    for seat in available_seats:
        if seat not in swarm.agents:
            print(f"⚠️  {seat} not in swarm agents, skipping")
            continue

        agent = swarm.agents[seat]
        print(f"{'─' * 60}")
        print(f"🎙️  {seat} ({agent.model}) deliberating...")

        t0 = time.time()
        r = await swarm.execute_agent_task(
            agent_name=seat,
            task=args.topic,
            max_tool_rounds=tool_rounds,
        )
        elapsed = time.time() - t0
        total_time += elapsed

        # execute_agent_task returns a plain dict (not an object)
        success = r.get("success", False) if isinstance(r, dict) else getattr(r, "success", False)
        if success:
            data = r if isinstance(r, dict) else (r.data or {})
            resp = data.get("response", "") or ""
            tokens_out = data.get("output_tokens", data.get("usage", {}).get("output_tokens", "?"))
            tool_calls = data.get("tool_calls", [])
            print(f"   ⏱️  {elapsed:.1f}s | {tokens_out} tokens | {len(tool_calls)} tool calls")
            print(f"   📝 Response ({len(resp)} chars):")
            for line in resp[:500].split("\n"):
                print(f"      {line}")
            if len(resp) > 500:
                print(f"      ... ({len(resp) - 500} more chars)")
            results[seat] = {"response": resp, "time": elapsed, "tokens": tokens_out}
        else:
            error = r.get("error", "Unknown error") if isinstance(r, dict) else getattr(r, "error", "Unknown error")
            print(f"   ❌ Failed ({elapsed:.1f}s): {error}")
            results[seat] = {"error": str(error), "time": elapsed}

    # Summary
    print(f"\n{'=' * 60}")
    print("SUMMARY")
    print(f"{'=' * 60}")
    for seat, data in results.items():
        if "error" in data:
            print(f"  ❌ {seat}: FAILED ({data['time']:.1f}s) — {data['error'][:80]}")
        else:
            print(f"  ✅ {seat}: {len(data['response'])} chars in {data['time']:.1f}s ({data['tokens']} tokens)")
    print(f"\n  Total time: {total_time:.1f}s")
    print(f"  Seats tested: {len(results)}/{len(requested_seats)}")

    success_count = sum(1 for d in results.values() if "error" not in d)
    if success_count == len(available_seats):
        print(f"\n🎉 ALL {success_count} SEATS PASSED")
    else:
        print(f"\n⚠️  {success_count}/{len(available_seats)} seats passed")


if __name__ == "__main__":
    asyncio.run(main())
