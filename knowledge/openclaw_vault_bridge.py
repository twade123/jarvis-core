#!/usr/bin/env python3
"""
openclaw_vault_bridge.py — Bidirectional sync between OpenClaw and the Jarvis Knowledge Vault.

1. generate_context() — Builds VAULT_CONTEXT.md for OpenClaw bootstrap (vault → OpenClaw)
2. sync_daily_logs() — Syncs OpenClaw daily memory logs to vault (OpenClaw → vault)

Run periodically or on OpenClaw startup via hooks.

Usage:
    # Generate vault context for OpenClaw bootstrap
    python3 ~/Jarvis/knowledge/openclaw_vault_bridge.py --generate-context

    # Sync OpenClaw daily logs to vault
    python3 ~/Jarvis/knowledge/openclaw_vault_bridge.py --sync-logs

    # Both
    python3 ~/Jarvis/knowledge/openclaw_vault_bridge.py --all
"""

import os
import sys
import json
import sqlite3
import argparse
from datetime import datetime, timedelta
from pathlib import Path

VAULT_DIR = os.path.dirname(os.path.abspath(__file__))
INDEX_DB = os.path.join(VAULT_DIR, "_index.db")
OPENCLAW_WORKSPACE = os.path.expanduser("~/.openclaw/workspace")
OPENCLAW_MEMORY = os.path.join(OPENCLAW_WORKSPACE, "memory")
VAULT_CONTEXT_PATH = os.path.join(OPENCLAW_WORKSPACE, "VAULT_CONTEXT.md")

sys.path.insert(0, os.path.dirname(VAULT_DIR))


def generate_context():
    """
    Build VAULT_CONTEXT.md for OpenClaw bootstrap.
    Pulls recent learnings, patterns, and decisions from the vault.
    OpenClaw loads this via bootstrap-extra-files at session start.
    """
    sections = []

    sections.append("# Jarvis Knowledge Vault — Session Context")
    sections.append(f"*Auto-generated: {datetime.now().isoformat(timespec='seconds')}*")
    sections.append("")
    sections.append("This is shared memory from the Jarvis Knowledge Vault.")
    sections.append("All agents (scout, validator, guardian, trevor, claude-code) contribute.")
    sections.append("Use this context to avoid repeating solved problems.")
    sections.append("")

    # 1. Recent collective patterns (last 5 days)
    patterns_dir = os.path.join(VAULT_DIR, "collective", "patterns")
    if os.path.isdir(patterns_dir):
        pattern_files = sorted(
            [f for f in os.listdir(patterns_dir) if f.endswith(".md")],
            reverse=True
        )[:5]
        if pattern_files:
            sections.append("## Recent Collective Patterns")
            for pf in pattern_files:
                with open(os.path.join(patterns_dir, pf), 'r') as f:
                    content = f.read()
                # Strip frontmatter
                if content.startswith("---"):
                    parts = content.split("---", 2)
                    if len(parts) >= 3:
                        content = parts[2].strip()
                # Truncate to last 500 chars per file
                if len(content) > 500:
                    content = "..." + content[-500:]
                sections.append(f"### {pf}")
                sections.append(content)
                sections.append("")

    # 2. Recent boardroom decisions (last 3 days)
    decisions_dir = os.path.join(VAULT_DIR, "boardroom", "decisions")
    if os.path.isdir(decisions_dir):
        decision_files = sorted(
            [f for f in os.listdir(decisions_dir) if f.endswith(".md")],
            reverse=True
        )[:3]
        if decision_files:
            sections.append("## Recent Boardroom Decisions")
            for df in decision_files:
                with open(os.path.join(decisions_dir, df), 'r') as f:
                    content = f.read()
                if content.startswith("---"):
                    parts = content.split("---", 2)
                    if len(parts) >= 3:
                        content = parts[2].strip()
                if len(content) > 400:
                    content = content[:400] + "..."
                sections.append(f"### {df}")
                sections.append(content)
                sections.append("")

    # 3. Key agent learnings (last 3 entries per agent, top agents only)
    key_agents = ["claude-code", "scout", "validator", "guardian", "trevor"]
    sections.append("## Agent Learnings (Recent)")
    for agent in key_agents:
        learnings_path = os.path.join(VAULT_DIR, "agents", agent, "learnings.md")
        if os.path.exists(learnings_path):
            with open(learnings_path, 'r') as f:
                content = f.read()
            entries = content.split("\n## ")[1:]  # skip header
            recent = entries[-3:] if len(entries) > 3 else entries
            if recent:
                sections.append(f"### {agent}")
                for entry in recent:
                    # Just the summary line + date
                    lines = entry.strip().split("\n")
                    summary = lines[0] if lines else "?"
                    date_line = ""
                    for line in lines[:5]:
                        if line.startswith("**Date:**"):
                            date_line = line
                            break
                    sections.append(f"- {summary}")
                    if date_line:
                        sections.append(f"  {date_line}")
                sections.append("")

    # 4. Vault search reminder
    sections.append("## Vault Search")
    sections.append("Before starting any task, search the vault for prior work:")
    sections.append("```bash")
    sections.append('sqlite3 ~/Jarvis/knowledge/_index.db "SELECT path FROM fts_content WHERE fts_content MATCH \'<keywords>\' LIMIT 5"')
    sections.append("```")
    sections.append("")
    sections.append("After completing meaningful work, write to the vault:")
    sections.append("```bash")
    sections.append('source ~/myenv/bin/activate && python3 ~/Jarvis/knowledge/vault_cli.py --agent "trevor" --type "<type>" --summary "<summary>" --context "<context>"')
    sections.append("```")
    sections.append("Types: discovery | correction | failure | improvement | note")

    # Write the file
    output = "\n".join(sections)
    with open(VAULT_CONTEXT_PATH, 'w') as f:
        f.write(output)

    print(f"Generated VAULT_CONTEXT.md ({len(output)} bytes) -> {VAULT_CONTEXT_PATH}")
    return VAULT_CONTEXT_PATH


def sync_daily_logs():
    """
    Sync OpenClaw daily memory logs to vault collective patterns.
    Only syncs logs from the last 3 days that haven't been synced yet.
    """
    if not os.path.isdir(OPENCLAW_MEMORY):
        print(f"OpenClaw memory dir not found: {OPENCLAW_MEMORY}")
        return []

    from knowledge.vault_writer import VaultWriter
    writer = VaultWriter(VAULT_DIR)

    # Find recent daily logs (YYYY-MM-DD*.md pattern)
    synced = []
    cutoff = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")

    for fname in sorted(os.listdir(OPENCLAW_MEMORY)):
        if not fname.endswith(".md"):
            continue
        # Skip non-date files
        if not fname[:4].isdigit():
            continue
        # Skip old files
        date_prefix = fname[:10]
        if date_prefix < cutoff:
            continue
        # Skip already-synced (check vault for matching entry)
        sync_marker = f"openclaw-sync-{fname}"
        if os.path.exists(INDEX_DB):
            conn = sqlite3.connect(INDEX_DB, isolation_level=None)
            try:
                existing = conn.execute(
                    "SELECT path FROM fts_content WHERE fts_content MATCH ?",
                    (sync_marker,)
                ).fetchone()
            except Exception:
                existing = None
            finally:
                conn.close()
            if existing:
                continue

        # Read the log
        log_path = os.path.join(OPENCLAW_MEMORY, fname)
        with open(log_path, 'r') as f:
            content = f.read()

        if len(content.strip()) < 50:
            continue  # Skip near-empty logs

        # Extract a summary from the first meaningful line
        lines = [l for l in content.strip().split("\n") if l.strip() and not l.startswith("---")]
        summary = lines[0][:120] if lines else f"OpenClaw session {date_prefix}"

        # Truncate context to 2000 chars
        context = content[:2000]
        if len(content) > 2000:
            context += "\n\n... (truncated)"

        # Write to vault
        writer.record_agent_learning(
            agent_name="trevor",
            learning={
                "type": "note",
                "summary": f"[OpenClaw sync] {summary}",
                "context": f"Synced from OpenClaw daily log: {fname}\n\n{context}",
                "tags": ["openclaw", "sync", "session-log"],
                "universal": False,
            }
        )
        synced.append(fname)
        print(f"  Synced: {fname}")

    if synced:
        print(f"Synced {len(synced)} OpenClaw daily logs to vault")
    else:
        print("No new OpenClaw logs to sync")

    return synced


def main():
    parser = argparse.ArgumentParser(
        description="OpenClaw <-> Jarvis Vault bridge"
    )
    parser.add_argument("--generate-context", action="store_true",
                        help="Generate VAULT_CONTEXT.md for OpenClaw bootstrap")
    parser.add_argument("--sync-logs", action="store_true",
                        help="Sync OpenClaw daily logs to vault")
    parser.add_argument("--all", action="store_true",
                        help="Run both generate-context and sync-logs")

    args = parser.parse_args()

    if args.all or args.generate_context:
        generate_context()

    if args.all or args.sync_logs:
        sync_daily_logs()

    if not (args.generate_context or args.sync_logs or args.all):
        parser.print_help()


if __name__ == "__main__":
    main()
