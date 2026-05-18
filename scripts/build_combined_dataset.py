#!/usr/bin/env python3
"""
build_combined_dataset.py — Assemble the single combined 35B training dataset.

Sources (in priority order):
  1. session_training.db   — Trevor (openclaw) + Claude Code sessions
  2. cc_extracted.jsonl    — older Claude Code extraction (deduped against above)
  3. by_domain/*.jsonl     — trading, coding, architecture, analysis, system
  4. flight_recorder.db    — trading team event chains (workflow_findings + trade_phases)
  5. distillation.db       — Opus teacher chain-of-thought responses
  6. knowledge/_index.db   — vault docs: decisions, patterns, trading knowledge, boardroom

Output:
  ~/jarvis/training_data/sessions/_lora_combined_35b/train.jsonl
  ~/jarvis/training_data/sessions/_lora_combined_35b/valid.jsonl

Deduplication: MD5 hash of (first_user_turn + first_assistant_turn).
Validation split: 5% held out, min 200 examples.

Usage:
  python3 build_combined_dataset.py [--dry-run] [--verbose]
"""

import argparse
import hashlib
import json
import os
import random
import sqlite3
from datetime import datetime
from pathlib import Path

JARVIS = Path.home() / "jarvis"
OUT_DIR = JARVIS / "training_data/sessions/_lora_combined_35b"
VALID_SPLIT = 0.05
MIN_USER_LEN = 10
MIN_ASST_LEN = 20
RANDOM_SEED = 42


def _hash(msgs: list) -> str:
    user = next((m.get("content", "") for m in msgs if m.get("role") == "user"), "")
    asst = next((m.get("content", "") for m in msgs if m.get("role") == "assistant"), "")
    return hashlib.md5((user + asst).encode()).hexdigest()


def _valid(msgs: list) -> bool:
    if not msgs or len(msgs) < 2:
        return False
    user = next((m.get("content", "") or "" for m in msgs if m.get("role") == "user"), "")
    asst = next((m.get("content", "") or "" for m in msgs if m.get("role") == "assistant"), "")
    return len(user.strip()) >= MIN_USER_LEN and len(asst.strip()) >= MIN_ASST_LEN


def _normalize(rec: dict) -> list | None:
    """Return normalized messages list or None if unusable."""
    if "messages" in rec:
        return rec["messages"]
    if "conversation" in rec:
        return rec["conversation"]
    if "prompt" in rec and "completion" in rec:
        return [
            {"role": "user", "content": rec["prompt"]},
            {"role": "assistant", "content": rec["completion"]},
        ]
    if "instruction" in rec and "output" in rec:
        content = rec["instruction"]
        if rec.get("input"):
            content += "\n\n" + rec["input"]
        return [
            {"role": "user", "content": content},
            {"role": "assistant", "content": rec["output"]},
        ]
    return None


# ── Source collectors ─────────────────────────────────────────────────────────

def collect_session_db(seen: set, verbose: bool) -> list:
    """session_training.db — Trevor openclaw + Claude Code pairs."""
    db = JARVIS / "training_data/sessions/session_training.db"
    if not db.exists():
        print(f"  [SKIP] {db} not found")
        return []
    results = []
    conn = sqlite3.connect(db)
    rows = conn.execute(
        "SELECT instruction, response, source, domain FROM training_pairs "
        "WHERE instruction IS NOT NULL AND response IS NOT NULL"
    ).fetchall()
    conn.close()
    for instruction, response, source, domain in rows:
        msgs = [
            {"role": "user", "content": instruction},
            {"role": "assistant", "content": response},
        ]
        if not _valid(msgs):
            continue
        h = _hash(msgs)
        if h in seen:
            continue
        seen.add(h)
        results.append({"messages": msgs, "_source": f"session_db/{source or 'unknown'}"})
    if verbose:
        print(f"  session_training.db: {len(results)} pairs")
    return results


def collect_jsonl(path: Path, source_label: str, seen: set, verbose: bool) -> list:
    """Generic JSONL collector."""
    if not path.exists():
        if verbose:
            print(f"  [SKIP] {path} not found")
        return []
    results = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except Exception:
                continue
            msgs = _normalize(rec)
            if not msgs or not _valid(msgs):
                continue
            h = _hash(msgs)
            if h in seen:
                continue
            seen.add(h)
            results.append({"messages": msgs, "_source": source_label})
    if verbose:
        print(f"  {source_label}: {len(results)} pairs")
    return results


def collect_by_domain(seen: set, verbose: bool) -> list:
    """by_domain/*.jsonl — trading, coding, architecture, analysis, system."""
    domain_dir = JARVIS / "training_data/sessions/by_domain"
    if not domain_dir.exists():
        return []
    results = []
    for f in sorted(domain_dir.glob("*.jsonl")):
        chunk = collect_jsonl(f, f"by_domain/{f.stem}", seen, verbose)
        results.extend(chunk)
    return results


def collect_flight_recorder(seen: set, verbose: bool) -> list:
    """flight_recorder.db — workflow_findings and trade_phases as Q&A pairs."""
    db = JARVIS / "Forex Trading Team/Source/flight_recorder.db"
    if not db.exists():
        print(f"  [SKIP] flight_recorder.db not found")
        return []
    results = []
    conn = sqlite3.connect(db)

    # workflow_findings: pair + category + message + details
    try:
        rows = conn.execute(
            "SELECT pair, category, severity, message, details FROM workflow_findings "
            "WHERE message IS NOT NULL AND length(message) > 20"
        ).fetchall()
        for pair, category, severity, message, details in rows:
            user = f"[Trading Event — {pair or 'unknown'} | {category or 'event'} | {severity or 'INFO'}]"
            asst = message
            if details:
                try:
                    import json as _j
                    d = _j.loads(details)
                    asst += "\n\nDetails: " + _j.dumps(d, indent=2)
                except Exception:
                    asst += f"\n\nDetails: {details}"
            msgs = [{"role": "user", "content": user}, {"role": "assistant", "content": asst}]
            if not _valid(msgs):
                continue
            h = _hash(msgs)
            if h in seen:
                continue
            seen.add(h)
            results.append({"messages": msgs, "_source": "flight_recorder/workflow"})
    except Exception as e:
        print(f"  [WARN] flight_recorder workflow_findings: {e}")

    # trade_phases: structured phase transitions with market state
    try:
        rows = conn.execute(
            "SELECT pair, direction, phase, from_phase, pnl_pips, action_taken, note FROM trade_phases "
            "WHERE note IS NOT NULL AND length(note) > 10"
        ).fetchall()
        for pair, direction, phase, from_phase, pnl_pips, action_taken, note in rows:
            transition = f"{from_phase} → {phase}" if from_phase else phase
            user = (f"[Trade Phase: {pair or 'unknown'} {direction or ''} | "
                    f"{transition} | pnl={pnl_pips}p]")
            asst = note
            if action_taken:
                asst += f"\nAction taken: {action_taken}"
            msgs = [{"role": "user", "content": user}, {"role": "assistant", "content": asst}]
            if not _valid(msgs):
                continue
            h = _hash(msgs)
            if h in seen:
                continue
            seen.add(h)
            results.append({"messages": msgs, "_source": "flight_recorder/trade_phases"})
    except Exception as e:
        print(f"  [WARN] flight_recorder trade_phases: {e}")

    conn.close()
    if verbose:
        print(f"  flight_recorder: {len(results)} pairs")
    return results


def collect_distillation(seen: set, verbose: bool) -> list:
    """distillation.db — Opus teacher chain-of-thought responses."""
    db = JARVIS / "training_data/distillation/distillation.db"
    if not db.exists():
        return []
    results = []
    conn = sqlite3.connect(db)
    try:
        rows = conn.execute(
            "SELECT t.task_text, r.response, t.category FROM teacher_responses r "
            "JOIN tasks t ON t.id = r.task_id "
            "WHERE r.response IS NOT NULL AND t.task_text IS NOT NULL"
        ).fetchall()
        for prompt, response, category in rows:
            msgs = [{"role": "user", "content": prompt}, {"role": "assistant", "content": response}]
            if not _valid(msgs):
                continue
            h = _hash(msgs)
            if h in seen:
                continue
            seen.add(h)
            results.append({"messages": msgs, "_source": "distillation/opus"})
    except Exception as e:
        print(f"  [WARN] distillation.db: {e}")
    conn.close()
    if verbose:
        print(f"  distillation/opus: {len(results)} pairs")
    return results


def collect_vault(seen: set, verbose: bool) -> list:
    """knowledge/_index.db — vault docs as system knowledge pairs."""
    db = JARVIS / "knowledge/_index.db"
    if not db.exists():
        return []
    results = []
    conn = sqlite3.connect(db)

    # Pull full text content via FTS table
    try:
        rows = conn.execute(
            "SELECT path, title, content FROM fts_content "
            "WHERE content IS NOT NULL AND length(content) > 100"
        ).fetchall()
        for path, title, content in rows:
            if not content or len(content.strip()) < 50:
                continue
            # Format as: "What do you know about X?" → content
            label = title or Path(path).stem if path else "this topic"
            user = f"What do you know about: {label}?"
            asst = content.strip()
            msgs = [{"role": "user", "content": user}, {"role": "assistant", "content": asst}]
            if not _valid(msgs):
                continue
            h = _hash(msgs)
            if h in seen:
                continue
            seen.add(h)
            results.append({"messages": msgs, "_source": f"vault/{path or 'unknown'}"})
    except Exception as e:
        print(f"  [WARN] vault fts_content: {e}")

    # Also pull opus_comparisons — these are quality judgments
    try:
        rows = conn.execute(
            "SELECT category, agent, notes FROM opus_comparisons "
            "WHERE notes IS NOT NULL AND length(notes) > 50"
        ).fetchall()
        for category, agent, notes in rows:
            user = f"[Quality Assessment — {category}/{agent}] What was learned?"
            msgs = [{"role": "user", "content": user}, {"role": "assistant", "content": notes}]
            if not _valid(msgs):
                continue
            h = _hash(msgs)
            if h in seen:
                continue
            seen.add(h)
            results.append({"messages": msgs, "_source": "vault/opus_comparisons"})
    except Exception as e:
        print(f"  [WARN] vault opus_comparisons: {e}")

    conn.close()
    if verbose:
        print(f"  vault: {len(results)} pairs")
    return results


def collect_trade_outcomes(seen: set, verbose: bool) -> list:
    """trevor_database.db — live trades, decisions, exit learning, backtest outcomes."""
    db = JARVIS / "Database/trevor_database.db"
    if not db.exists():
        return []
    results = []
    conn = sqlite3.connect(db)

    # live_trades joined to trade_decisions — full entry context + outcome
    try:
        rows = conn.execute("""
            SELECT lt.pair, lt.direction, lt.setup, lt.entry_price, lt.exit_price,
                   lt.pips, lt.pips, lt.exit_reason,
                   td.market_agent_data, lt.regime
            FROM live_trades lt
            LEFT JOIN trade_decisions td ON td.decision_id = lt.decision_id
            WHERE lt.exit_price IS NOT NULL AND lt.pips IS NOT NULL
        """).fetchall()
        for pair, direction, setup, entry, exit_p, pl_usd, pl_pips, exit_reason, market_data, regime in rows:
            result = "WIN" if (pl_usd or 0) > 0 else "LOSS"
            user = (f"[Live Trade — {pair} {direction} | {setup or 'snipe'} | "
                    f"regime={regime or 'unknown'}]\n"
                    f"Entry: {entry} | Exit: {exit_p} | Exit reason: {exit_reason or 'unknown'}")
            asst = (f"Result: {result} | P&L: {pl_usd:+.2f} USD / {pl_pips:+.1f} pips\n"
                    f"Setup: {setup or 'snipe'} | Direction: {direction}")
            if market_data:
                try:
                    md = json.loads(market_data) if isinstance(market_data, str) else market_data
                    if isinstance(md, dict):
                        asst += f"\nMarket context: {json.dumps(md)[:300]}"
                except Exception:
                    pass
            msgs = [{"role": "user", "content": user}, {"role": "assistant", "content": asst}]
            if not _valid(msgs):
                continue
            h = _hash(msgs)
            if h in seen:
                continue
            seen.add(h)
            results.append({"messages": msgs, "_source": "trades/live"})
    except Exception as e:
        print(f"  [WARN] live_trades: {e}")

    # exit_learning — full entry/exit context with what the model learned
    try:
        rows = conn.execute("""
            SELECT pair, direction, setup_name, regime, entry_type,
                   entry_price, initial_sl, initial_sl, exit_price,
                   pnl_pips, pnl_usd, exit_reason, primary_exit_signal
            FROM exit_learning
            WHERE exit_price IS NOT NULL AND pnl_pips IS NOT NULL
        """).fetchall()
        for (pair, direction, setup, regime, entry_type, entry, isl, fsl,
             exit_p, pnl_pips, pnl_usd, exit_reason, lessons) in rows:
            result = "WIN" if (pnl_usd or 0) > 0 else "LOSS"
            user = (f"[Exit Learning — {pair} {direction} | {setup or 'unknown'} | "
                    f"{entry_type or 'standard'} entry | regime={regime or 'unknown'}]\n"
                    f"Entry: {entry} | Initial SL: {isl} | Final SL: {fsl} | "
                    f"Exit: {exit_p} | Reason: {exit_reason or 'unknown'}")
            asst = f"Result: {result} | {pnl_usd:+.2f} USD / {pnl_pips:+.1f} pips"
            if lessons:
                asst += f"\nLessons: {lessons}"
            msgs = [{"role": "user", "content": user}, {"role": "assistant", "content": asst}]
            if not _valid(msgs):
                continue
            h = _hash(msgs)
            if h in seen:
                continue
            seen.add(h)
            results.append({"messages": msgs, "_source": "trades/exit_learning"})
    except Exception as e:
        print(f"  [WARN] exit_learning: {e}")

    # thesis_backtest_trades — 9,413 backtested trades with outcome
    try:
        rows = conn.execute("""
            SELECT pair, direction, entry_time, entry_price, entry_price,
                   pips, result, exit_reason, mfe_pips
            FROM thesis_backtest_trades
            WHERE result IS NOT NULL
            LIMIT 5000
        """).fetchall()
        for pair, direction, entry_time, entry, exit_p, pips, result, exit_reason, mfe in rows:
            user = (f"[Backtest Trade — {pair} {direction}]\n"
                    f"Entry: {entry} | Exit: {exit_p} | MFE: {mfe} pips | "
                    f"Exit reason: {exit_reason or 'unknown'}")
            asst = f"Result: {result.upper()} | P&L: {pips:+.1f} pips"
            msgs = [{"role": "user", "content": user}, {"role": "assistant", "content": asst}]
            if not _valid(msgs):
                continue
            h = _hash(msgs)
            if h in seen:
                continue
            seen.add(h)
            results.append({"messages": msgs, "_source": "trades/backtest"})
    except Exception as e:
        print(f"  [WARN] thesis_backtest_trades: {e}")

    # setup_revenue — per-setup performance stats
    try:
        rows = conn.execute("""
            SELECT setup_name, pair, total_trades, wins, losses,
                   total_pips, total_usd, best_trade_usd, worst_trade_usd
            FROM setup_revenue WHERE total_trades > 0
        """).fetchall()
        for setup, pair, total, wins, losses, total_pips, total_usd, best, worst in rows:
            wr = wins / total * 100 if total else 0
            user = f"[Setup Performance — {setup} on {pair}]"
            asst = (f"Total trades: {total} | Win rate: {wr:.1f}% ({wins}W/{losses}L)\n"
                    f"Total: {total_pips:+.1f} pips / {total_usd:+.2f} USD\n"
                    f"Best trade: +{best:.2f} USD | Worst: {worst:.2f} USD")
            msgs = [{"role": "user", "content": user}, {"role": "assistant", "content": asst}]
            if not _valid(msgs):
                continue
            h = _hash(msgs)
            if h in seen:
                continue
            seen.add(h)
            results.append({"messages": msgs, "_source": "trades/setup_revenue"})
    except Exception as e:
        print(f"  [WARN] setup_revenue: {e}")

    conn.close()
    if verbose:
        print(f"  trade_outcomes: {len(results)} pairs")
    return results


def collect_research_docs(seen: set, verbose: bool) -> list:
    """Research/*.md — candle patterns, setup catalog, visual knowledge, strategy docs."""
    research_dir = JARVIS / "Forex Trading Team/Research"
    if not research_dir.exists():
        return []
    results = []
    # All .md files in Research (not subdirs)
    for f in sorted(research_dir.glob("*.md")):
        try:
            content = f.read_text(encoding="utf-8", errors="ignore").strip()
            if len(content) < 100:
                continue
            user = f"What do you know about: {f.stem.replace('-', ' ').replace('_', ' ')}?"
            asst = content
            msgs = [{"role": "user", "content": user}, {"role": "assistant", "content": asst}]
            if not _valid(msgs):
                continue
            h = _hash(msgs)
            if h in seen:
                continue
            seen.add(h)
            results.append({"messages": msgs, "_source": f"research_docs/{f.stem}"})
        except Exception:
            continue
    if verbose:
        print(f"  research_docs: {len(results)} pairs")
    return results


def collect_annotated_chart_responses(seen: set, verbose: bool) -> list:
    """User-submitted annotated charts + validator responses from manifest."""
    manifest_path = (JARVIS / "Forex Trading Team/Data/charts/user_annotations/manifest.json")
    if not manifest_path.exists():
        return []
    results = []
    try:
        manifest = json.loads(manifest_path.read_text())
    except Exception:
        return []

    for entry in manifest:
        thesis = (entry.get("thesis") or "").strip()
        validator_resp = (entry.get("validator_response") or "").strip()
        pair = entry.get("pair", "unknown")
        timeframe = entry.get("timeframe", "M15")
        notes = (entry.get("notes") or "").strip()

        # Need at least thesis or validator response to be useful
        if not thesis and not validator_resp:
            continue

        user_parts = [f"[Chart Review — {pair} {timeframe}]"]
        if thesis:
            user_parts.append(f"Thesis: {thesis}")
        if notes:
            user_parts.append(f"Notes: {notes}")
        user = "\n".join(user_parts)

        # Use validator response if available, otherwise thesis as self-label
        asst = validator_resp if validator_resp else f"Chart analysis: {thesis}"

        msgs = [{"role": "user", "content": user}, {"role": "assistant", "content": asst}]
        if not _valid(msgs):
            continue
        h = _hash(msgs)
        if h in seen:
            continue
        seen.add(h)
        results.append({"messages": msgs, "_source": "charts/annotated"})

    if verbose:
        print(f"  annotated_charts: {len(results)} pairs")
    return results


def collect_conversation_capture(seen: set, verbose: bool) -> list:
    """conversations_capture.db — live floor chat + boardroom turns captured at runtime."""
    db = JARVIS / "training_data/conversations_capture.db"
    if not db.exists():
        if verbose:
            print(f"  conversation_capture: 0 pairs (DB not yet created)")
        return []
    results = []
    try:
        import sys as _sys
        _sys.path.insert(0, str(JARVIS / "scripts"))
        from conversation_capture import get_unexported_as_pairs, mark_exported
        pairs = get_unexported_as_pairs(min_turns=2)
        exported_ids = []
        for p in pairs:
            msgs = p["messages"]
            if not _valid(msgs):
                continue
            h = _hash(msgs)
            if h in seen:
                continue
            seen.add(h)
            results.append({"messages": msgs, "_source": "conversation_capture"})
            exported_ids.append(p["session_id"])
        mark_exported(exported_ids)
    except Exception as e:
        print(f"  [WARN] conversation_capture: {e}")
    if verbose:
        print(f"  conversation_capture: {len(results)} pairs")
    return results


def collect_boardroom(seen: set, verbose: bool) -> list:
    """knowledge/boardroom/ — boardroom session chain-of-thought."""
    boardroom_dir = JARVIS / "knowledge/boardroom"
    if not boardroom_dir.exists():
        return []
    results = []
    for f in boardroom_dir.rglob("*.json"):
        try:
            with open(f) as fh:
                data = json.load(fh)
            # Handle list of session records or single record
            if isinstance(data, list):
                records = data
            elif isinstance(data, dict):
                records = [data]
            else:
                continue
            for rec in records:
                msgs = _normalize(rec)
                if not msgs or not _valid(msgs):
                    continue
                h = _hash(msgs)
                if h in seen:
                    continue
                seen.add(h)
                results.append({"messages": msgs, "_source": f"boardroom/{f.stem}"})
        except Exception:
            continue
    # Also check for JSONL files
    for f in boardroom_dir.rglob("*.jsonl"):
        chunk = collect_jsonl(f, f"boardroom/{f.stem}", seen, verbose=False)
        results.extend(chunk)
    if verbose:
        print(f"  boardroom: {len(results)} pairs")
    return results


# ── Main ──────────────────────────────────────────────────────────────────────

def build(dry_run: bool = False, verbose: bool = True):
    print(f"\n{'='*60}")
    print(f"Building combined 35B training dataset")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"{'='*60}\n")

    seen: set = set()
    all_records: list = []

    print("Collecting sources...")
    all_records.extend(collect_session_db(seen, verbose))
    all_records.extend(collect_jsonl(
        JARVIS / "training_data/sessions/cc_extracted.jsonl",
        "cc_extracted", seen, verbose
    ))
    all_records.extend(collect_by_domain(seen, verbose))
    all_records.extend(collect_flight_recorder(seen, verbose))
    all_records.extend(collect_distillation(seen, verbose))
    all_records.extend(collect_vault(seen, verbose))
    all_records.extend(collect_boardroom(seen, verbose))
    all_records.extend(collect_trade_outcomes(seen, verbose))
    all_records.extend(collect_research_docs(seen, verbose))
    all_records.extend(collect_annotated_chart_responses(seen, verbose))
    all_records.extend(collect_conversation_capture(seen, verbose))

    print(f"\nTotal unique pairs: {len(all_records)}")

    if len(all_records) < 100:
        print("ERROR: Too few pairs to train. Something is wrong.")
        return

    # Source breakdown
    source_counts: dict = {}
    for r in all_records:
        src = r.get("_source", "unknown").split("/")[0]
        source_counts[src] = source_counts.get(src, 0) + 1
    print("\nSource breakdown:")
    for src, count in sorted(source_counts.items(), key=lambda x: -x[1]):
        print(f"  {src}: {count}")

    # Shuffle + split
    random.seed(RANDOM_SEED)
    random.shuffle(all_records)
    n_valid = max(200, int(len(all_records) * VALID_SPLIT))
    valid_records = all_records[:n_valid]
    train_records = all_records[n_valid:]
    print(f"\nSplit: {len(train_records)} train / {len(valid_records)} valid")

    if dry_run:
        print("\n[DRY RUN] No files written.")
        return

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # Strip internal _source key before writing
    def _clean(rec):
        return {"messages": rec["messages"]}

    train_path = OUT_DIR / "train.jsonl"
    valid_path = OUT_DIR / "valid.jsonl"

    with open(train_path, "w") as f:
        for rec in train_records:
            f.write(json.dumps(_clean(rec)) + "\n")

    with open(valid_path, "w") as f:
        for rec in valid_records:
            f.write(json.dumps(_clean(rec)) + "\n")

    print(f"\nWrote:")
    print(f"  {train_path}  ({len(train_records)} examples)")
    print(f"  {valid_path}  ({len(valid_records)} examples)")
    print("\nDone. Ready to run lora_trainer.py train combined_35b")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build combined 35B training dataset")
    parser.add_argument("--dry-run", action="store_true", help="Count and report without writing")
    parser.add_argument("--verbose", action="store_true", default=True)
    args = parser.parse_args()
    build(dry_run=args.dry_run, verbose=args.verbose)
