#!/usr/bin/env python3
"""
vault_cli.py -- Universal vault interface (read + write).

Any agent, sub-agent, Claude Code session, or shell script calls this.
No imports needed. No class setup. Just run it.

WRITE (original):
    python3 ~/jarvis/knowledge/vault_cli.py \\
        --agent "validator" --type "discovery" \\
        --summary "EUR_CHF SELL conf=7 fired" \\
        --context "Fan bearish/expanding." --tags "eurjpy,win" --universal

VALIDATE:
    python3 ~/jarvis/knowledge/vault_cli.py --validate

BACKLINKS:
    python3 ~/jarvis/knowledge/vault_cli.py --backlinks "agents/scout/learnings.md"

UNLINKED MENTIONS:
    python3 ~/jarvis/knowledge/vault_cli.py --unlinked-mentions "scout"

GRAPH:
    python3 ~/jarvis/knowledge/vault_cli.py --graph                      # global
    python3 ~/jarvis/knowledge/vault_cli.py --graph "agents/scout"       # local

QUERY (Dataview-style):
    python3 ~/jarvis/knowledge/vault_cli.py --query "type=discovery AND agent=scout"

BOOKMARKS:
    python3 ~/jarvis/knowledge/vault_cli.py --bookmarks

NEW (from template):
    python3 ~/jarvis/knowledge/vault_cli.py --new daily "2026-03-21"
    python3 ~/jarvis/knowledge/vault_cli.py --new decision "Circuit breaker threshold"
    python3 ~/jarvis/knowledge/vault_cli.py --daily-note
    python3 ~/jarvis/knowledge/vault_cli.py --weekly-note

EMBED (resolve transclusion):
    python3 ~/jarvis/knowledge/vault_cli.py --resolve-embeds "path/to/file.md"

Types: discovery | correction | failure | improvement | note
--universal flag also writes to collective/patterns/ (shared across ALL agents)
"""

import argparse
import json
import sys
import os
from datetime import datetime, timedelta

# Always resolve vault relative to this file's location
VAULT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(VAULT_DIR))

from knowledge.vault_writer import VaultWriter
from knowledge import indexer


def cmd_write(args):
    """Write a learning to the vault."""
    tags = [t.strip() for t in args.tags.split(",") if t.strip()]
    writer = VaultWriter(VAULT_DIR)
    path = writer.record_agent_learning(
        agent_name=args.agent,
        learning={
            "type":      args.type,
            "summary":   args.summary,
            "context":   args.context,
            "evidence":  args.evidence,
            "tags":      tags,
            "universal": args.universal,
        },
        workspace=args.workspace or None,
    )
    print(f"Vault write OK -> {path}")


def cmd_validate(args):
    """Validate vault links and report issues."""
    # Re-index first to get fresh data
    indexer.run()
    result = indexer.validate_links()

    if result.get("broken_count", 0) == 0:
        print(f"\nAll {result['total_links']} links resolve correctly.")
    else:
        print(f"\n{result['broken_count']} broken links out of {result['total_links']} total.")

    # Also check for orphaned files (no incoming links)
    db_path = os.path.join(VAULT_DIR, "_index.db")
    if os.path.exists(db_path):
        import sqlite3
        conn = sqlite3.connect(db_path, isolation_level=None)
        try:
            total_files = conn.execute("SELECT COUNT(*) FROM files").fetchone()[0]
            linked = conn.execute(
                "SELECT COUNT(DISTINCT target_file_id) FROM links WHERE target_file_id IS NOT NULL"
            ).fetchone()[0]
            orphan_files = total_files - linked
            total_tags = conn.execute("SELECT COUNT(*) FROM tags").fetchone()[0]
            alias_count = 0
            try:
                alias_count = conn.execute("SELECT COUNT(*) FROM aliases").fetchone()[0]
            except sqlite3.OperationalError:
                pass
        finally:
            conn.close()

        print(f"\nVault Stats:")
        print(f"  Files:    {total_files}")
        print(f"  Links:    {result['total_links']}")
        print(f"  Tags:     {total_tags}")
        print(f"  Aliases:  {alias_count}")
        print(f"  Orphan files (no incoming links): {orphan_files}")


def cmd_backlinks(args):
    """Show what links TO a given note."""
    results = indexer.get_backlinks(args.backlinks)
    if not results:
        print(f"No backlinks found for: {args.backlinks}")
        return
    print(f"Backlinks to {args.backlinks}:")
    for r in results:
        print(f"  {r['source_path']} (link text: {r['link_text']})")


def cmd_unlinked_mentions(args):
    """Find notes mentioning a term but not linking to it."""
    results = indexer.get_unlinked_mentions(args.unlinked_mentions)
    if not results:
        print(f"No unlinked mentions found for: {args.unlinked_mentions}")
        return
    print(f"Unlinked mentions of '{args.unlinked_mentions}':")
    for r in results:
        print(f"  {r['path']}")


def cmd_graph(args):
    """Export graph data as JSON."""
    note = args.graph if args.graph != "__GLOBAL__" else None
    result = indexer.get_graph(note)
    print(json.dumps(result, indent=2))


def cmd_query(args):
    """Query vault by frontmatter fields (Dataview-style)."""
    results = indexer.query_frontmatter(args.query)
    if not results:
        print(f"No results for query: {args.query}")
        return
    print(f"Query: {args.query}")
    print(f"Results: {len(results)}")
    for r in results:
        fm_summary = {k: v for k, v in r['frontmatter'].items()
                      if k in ('type', 'agent', 'tags', 'created', 'status')}
        print(f"  {r['path']}  [{r['type']}]  {fm_summary}")


def cmd_bookmarks(args):
    """List bookmarked notes (bookmarked: true in frontmatter)."""
    results = indexer.query_frontmatter("bookmarked=true")
    if not results:
        print("No bookmarked notes found. Add 'bookmarked: true' to frontmatter.")
        return
    print("Bookmarked notes:")
    for r in results:
        print(f"  {r['path']}  [{r['type']}]  {r['title']}")


def cmd_new(args):
    """Create a new note from a template."""
    template_name = args.new
    title = args.title or datetime.now().strftime("%Y-%m-%d")

    templates_dir = os.path.join(VAULT_DIR, "templates")
    template_path = os.path.join(templates_dir, f"{template_name}.md")

    if not os.path.exists(template_path):
        available = [f[:-3] for f in os.listdir(templates_dir) if f.endswith(".md")] if os.path.isdir(templates_dir) else []
        print(f"Template '{template_name}' not found.")
        if available:
            print(f"Available templates: {', '.join(available)}")
        return

    with open(template_path, 'r') as f:
        template = f.read()

    # Variable substitution
    now = datetime.now()
    variables = {
        "{{date}}": now.strftime("%Y-%m-%d"),
        "{{datetime}}": now.isoformat(timespec='seconds'),
        "{{title}}": title,
        "{{agent}}": args.agent or "claude-code",
        "{{workspace}}": args.workspace or "",
        "{{year}}": now.strftime("%Y"),
        "{{month}}": now.strftime("%m"),
        "{{week}}": now.strftime("%W"),
        "{{day}}": now.strftime("%A"),
    }

    content = template
    for var, val in variables.items():
        content = content.replace(var, val)

    # Determine output path based on template type
    slug = title.lower().replace(" ", "-")[:60]
    output_map = {
        "daily": f"agents/{args.agent or 'claude-code'}/daily/{now.strftime('%Y-%m-%d')}.md",
        "weekly": f"agents/{args.agent or 'claude-code'}/weekly/{now.strftime('%Y-W%W')}.md",
        "decision": f"boardroom/decisions/{now.strftime('%Y-%m-%d')}-{slug}.md",
        "learning": f"agents/{args.agent or 'claude-code'}/learnings-{slug}.md",
        "retrospective": f"collective/scout-retrospective/{now.strftime('%Y-%m-%d')}.md",
    }

    output_path = output_map.get(template_name,
                                  f"agents/{args.agent or 'claude-code'}/{slug}.md")
    full_path = os.path.join(VAULT_DIR, output_path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)

    if os.path.exists(full_path):
        print(f"Note already exists: {output_path}")
        return

    with open(full_path, 'w') as f:
        f.write(content)

    # Reindex
    indexer.run()
    print(f"Created: {output_path}")


def cmd_daily_note(args):
    """Shortcut for --new daily."""
    args.new = "daily"
    args.title = datetime.now().strftime("%Y-%m-%d")
    cmd_new(args)


def cmd_weekly_note(args):
    """Shortcut for --new weekly."""
    args.new = "weekly"
    args.title = datetime.now().strftime("%Y-W%W")
    cmd_new(args)


def cmd_resolve_embeds(args):
    """Resolve ![[embed]] syntax in a file and print result."""
    file_path = os.path.join(VAULT_DIR, args.resolve_embeds)
    if not os.path.exists(file_path):
        print(f"File not found: {args.resolve_embeds}")
        return

    with open(file_path, 'r') as f:
        content = f.read()

    resolved = indexer.resolve_embeds(content, VAULT_DIR)
    print(resolved)


# ── Dream operations: read, move, archive, merge, compare, list ──────


def cmd_read(args):
    """Read and print a vault file's content."""
    rel = args.read
    full = os.path.join(VAULT_DIR, rel)
    if not os.path.exists(full):
        print(f"File not found: {rel}")
        return
    with open(full, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()
    lines = content.count('\n') + 1
    print(f"--- {rel} ({lines} lines) ---")
    print(content)


def cmd_list(args):
    """List .md files in a vault directory."""
    rel = args.list_dir
    full = os.path.join(VAULT_DIR, rel)
    if not os.path.isdir(full):
        print(f"Not a directory: {rel}")
        return
    files = sorted(f for f in os.listdir(full) if f.endswith('.md') and not f.startswith('.'))
    print(f"Directory: {rel}/ ({len(files)} .md files)")
    for f in files:
        fpath = os.path.join(full, f)
        size = os.path.getsize(fpath)
        mtime = datetime.fromtimestamp(os.path.getmtime(fpath)).strftime('%Y-%m-%d %H:%M')
        lines = sum(1 for _ in open(fpath, 'r', encoding='utf-8', errors='replace'))
        print(f"  {f:50s}  {lines:4d} lines  {size:6d}B  {mtime}")


def cmd_compare(args):
    """Read two vault files side by side for comparison."""
    path_a, path_b = args.compare
    full_a = os.path.join(VAULT_DIR, path_a)
    full_b = os.path.join(VAULT_DIR, path_b)
    for p, rel in [(full_a, path_a), (full_b, path_b)]:
        if not os.path.exists(p):
            print(f"File not found: {rel}")
            return

    with open(full_a, 'r', encoding='utf-8', errors='replace') as f:
        content_a = f.read()
    with open(full_b, 'r', encoding='utf-8', errors='replace') as f:
        content_b = f.read()

    print(f"=== FILE A: {path_a} ({content_a.count(chr(10))+1} lines) ===")
    print(content_a[:3000])
    if len(content_a) > 3000:
        print(f"[...truncated at 3000 chars, total {len(content_a)}]")
    print(f"\n=== FILE B: {path_b} ({content_b.count(chr(10))+1} lines) ===")
    print(content_b[:3000])
    if len(content_b) > 3000:
        print(f"[...truncated at 3000 chars, total {len(content_b)}]")

    # Simple similarity check
    words_a = set(content_a.lower().split())
    words_b = set(content_b.lower().split())
    if words_a and words_b:
        overlap = len(words_a & words_b) / max(len(words_a | words_b), 1)
        print(f"\nWord overlap: {overlap:.0%}")
        if overlap > 0.7:
            print("LIKELY DUPLICATE — high word overlap")
        elif overlap > 0.4:
            print("RELATED — moderate overlap, check for unique details")
        else:
            print("DIFFERENT — low overlap, probably not duplicates")


def cmd_archive(args):
    """Move a vault file to archive/ (preserving relative path). Backs up first."""
    rel = args.archive
    full = os.path.join(VAULT_DIR, rel)
    if not os.path.exists(full):
        print(f"File not found: {rel}")
        return

    # Backup first
    backup_dir = os.path.join(os.path.dirname(VAULT_DIR), "Vault Keeper", "Data", "backups")
    os.makedirs(backup_dir, exist_ok=True)
    backup_name = datetime.now().strftime('%Y%m%d_%H%M%S_') + os.path.basename(rel)
    import shutil
    shutil.copy2(full, os.path.join(backup_dir, backup_name))
    print(f"Backed up: {backup_name}")

    # Move to archive
    archive_path = os.path.join(VAULT_DIR, "archive", rel)
    os.makedirs(os.path.dirname(archive_path), exist_ok=True)
    shutil.move(full, archive_path)
    print(f"Archived: {rel} → archive/{rel}")

    # Rebuild index
    indexer.run()
    print("Index rebuilt.")


def cmd_merge(args):
    """Merge file B's unique content into file A, then archive file B."""
    path_a, path_b = args.merge
    full_a = os.path.join(VAULT_DIR, path_a)
    full_b = os.path.join(VAULT_DIR, path_b)
    for p, rel in [(full_a, path_a), (full_b, path_b)]:
        if not os.path.exists(p):
            print(f"File not found: {rel}")
            return

    # Backup both
    import shutil
    backup_dir = os.path.join(os.path.dirname(VAULT_DIR), "Vault Keeper", "Data", "backups")
    os.makedirs(backup_dir, exist_ok=True)
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    shutil.copy2(full_a, os.path.join(backup_dir, f"{ts}_{os.path.basename(path_a)}"))
    shutil.copy2(full_b, os.path.join(backup_dir, f"{ts}_{os.path.basename(path_b)}"))
    print(f"Backed up both files.")

    with open(full_a, 'r', encoding='utf-8', errors='replace') as f:
        content_a = f.read()
    with open(full_b, 'r', encoding='utf-8', errors='replace') as f:
        content_b = f.read()

    # Append B's content to A under a merge header
    merged = content_a.rstrip() + f"\n\n## Merged from {path_b}\n\n" + content_b
    with open(full_a, 'w', encoding='utf-8') as f:
        f.write(merged)
    print(f"Merged {path_b} content into {path_a}")

    # Archive B
    archive_path = os.path.join(VAULT_DIR, "archive", path_b)
    os.makedirs(os.path.dirname(archive_path), exist_ok=True)
    shutil.move(full_b, archive_path)
    print(f"Archived: {path_b} → archive/{path_b}")

    # Rebuild index
    indexer.run()
    print("Index rebuilt.")


def cmd_move(args):
    """Move a vault file to a new location within the vault."""
    src, dst = args.move
    full_src = os.path.join(VAULT_DIR, src)
    full_dst = os.path.join(VAULT_DIR, dst)
    if not os.path.exists(full_src):
        print(f"Source not found: {src}")
        return
    if os.path.exists(full_dst):
        print(f"Destination already exists: {dst}")
        return

    import shutil
    # Backup
    backup_dir = os.path.join(os.path.dirname(VAULT_DIR), "Vault Keeper", "Data", "backups")
    os.makedirs(backup_dir, exist_ok=True)
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    shutil.copy2(full_src, os.path.join(backup_dir, f"{ts}_{os.path.basename(src)}"))

    os.makedirs(os.path.dirname(full_dst), exist_ok=True)
    shutil.move(full_src, full_dst)
    print(f"Moved: {src} → {dst}")

    indexer.run()
    print("Index rebuilt.")


def cmd_recent(args):
    """Show recently modified vault files, optionally filtered by days or directory."""
    days = args.recent_days or 7
    cutoff = datetime.now().timestamp() - (days * 86400)
    subdir = args.recent or ""

    scan_path = os.path.join(VAULT_DIR, subdir) if subdir else VAULT_DIR
    if not os.path.isdir(scan_path):
        print(f"Not a directory: {subdir}")
        return

    recent = []
    for root, dirs, files in os.walk(scan_path):
        dirs[:] = [d for d in dirs if d not in ("__pycache__", ".git", "archive")]
        for fname in files:
            if not fname.endswith('.md') or fname.startswith('.'):
                continue
            fpath = os.path.join(root, fname)
            mtime = os.path.getmtime(fpath)
            if mtime >= cutoff:
                rel = os.path.relpath(fpath, VAULT_DIR)
                lines = sum(1 for _ in open(fpath, 'r', encoding='utf-8', errors='replace'))
                recent.append((mtime, rel, lines, os.path.getsize(fpath)))

    recent.sort(key=lambda x: x[0], reverse=True)

    scope = f" in {subdir}/" if subdir else ""
    print(f"Files modified in last {days} days{scope}: {len(recent)}")
    for mtime, rel, lines, size in recent[:50]:
        dt = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M')
        print(f"  {dt}  {lines:4d}L  {rel}")
    if len(recent) > 50:
        print(f"  ... and {len(recent)-50} more")


def cmd_search(args):
    """FTS search — returns paths and content preview."""
    import sqlite3 as _sq
    db = os.path.join(VAULT_DIR, "_index.db")
    if not os.path.exists(db):
        print("Index not found. Run: python indexer.py")
        return
    conn = _sq.connect(db)
    rows = conn.execute(
        "SELECT path, substr(content,1,200) FROM fts_content WHERE fts_content MATCH ? LIMIT ?",
        (args.search, args.search_limit or 10),
    ).fetchall()
    conn.close()
    if not rows:
        print(f"No results for: {args.search}")
        return
    print(f"Search: '{args.search}' ({len(rows)} results)")
    for path, preview in rows:
        preview_clean = (preview or '').replace('\n', ' ').strip()[:120]
        print(f"  {path}")
        print(f"    {preview_clean}")


def cmd_scan_code(args):
    """Run Nexus bridge to sync code dependencies into _index.db."""
    from knowledge.nexus_bridge import NexusBridge
    bridge = NexusBridge()
    bridge.run()
    print("Code dependency scan complete. Code nodes and import edges synced to _index.db.")


def main():
    parser = argparse.ArgumentParser(
        description="Jarvis Knowledge Vault CLI — Obsidian-style knowledge management"
    )

    # Write mode args
    parser.add_argument("--agent",    default="",     help="Agent name: validator, guardian, scout, etc.")
    parser.add_argument("--type",     default="note", help="Type: discovery|correction|failure|improvement|note")
    parser.add_argument("--summary",  default="",     help="One-line summary")
    parser.add_argument("--context",  default="",     help="Full context")
    parser.add_argument("--evidence", default="",     help="Supporting data/metrics")
    parser.add_argument("--tags",     default="",     help="Comma-separated tags")
    parser.add_argument("--workspace",default="",     help="Workspace context")
    parser.add_argument("--universal",action="store_true", help="Also write to collective patterns")

    # Read/query mode args
    parser.add_argument("--validate",    action="store_true", help="Validate vault links and report stats")
    parser.add_argument("--backlinks",   type=str, help="Show backlinks to a note path")
    parser.add_argument("--unlinked-mentions", type=str, help="Find unlinked mentions of a term")
    parser.add_argument("--graph",       nargs="?", const="__GLOBAL__", help="Export graph JSON (optional: note path for local graph)")
    parser.add_argument("--query",       type=str, help="Dataview-style query: 'type=discovery AND agent=scout'")
    parser.add_argument("--bookmarks",   action="store_true", help="List bookmarked notes")
    parser.add_argument("--new",         type=str, help="Create note from template: daily|weekly|decision|learning|retrospective")
    parser.add_argument("--title",       type=str, help="Title for --new template")
    parser.add_argument("--daily-note",  action="store_true", help="Create today's daily note")
    parser.add_argument("--weekly-note", action="store_true", help="Create this week's weekly note")
    parser.add_argument("--resolve-embeds", type=str, help="Resolve ![[embed]] syntax in a file")

    # Dream operations — read, list, compare, archive, merge, move, search
    parser.add_argument("--read",     type=str, help="Read and print a vault file (relative path)")
    parser.add_argument("--list-dir", type=str, help="List .md files in a vault directory")
    parser.add_argument("--compare",  nargs=2, metavar=("FILE_A", "FILE_B"), help="Compare two vault files side by side")
    parser.add_argument("--archive",  type=str, help="Move a file to archive/ (backs up first)")
    parser.add_argument("--merge",    nargs=2, metavar=("KEEPER", "DUPLICATE"), help="Merge duplicate into keeper, archive duplicate")
    parser.add_argument("--move",     nargs=2, metavar=("SRC", "DST"), help="Move a file to a new vault location")
    parser.add_argument("--search",   type=str, help="FTS full-text search with content preview")
    parser.add_argument("--search-limit", type=int, default=10, help="Max results for --search (default 10)")
    parser.add_argument("--recent",  nargs="?", const="", type=str, help="Show recently modified files (optional: subdirectory)")
    parser.add_argument("--recent-days", type=int, default=7, help="Days to look back for --recent (default 7)")
    parser.add_argument("--scan-code",   action="store_true", help="Run Nexus-skills scan and bridge code dependencies into _index.db")

    args = parser.parse_args()

    # Dispatch to appropriate command
    if args.scan_code:
        return cmd_scan_code(args)
    elif args.recent is not None:
        cmd_recent(args)
    elif args.read:
        cmd_read(args)
    elif args.list_dir:
        cmd_list(args)
    elif args.compare:
        cmd_compare(args)
    elif args.archive:
        cmd_archive(args)
    elif args.merge:
        cmd_merge(args)
    elif args.move:
        cmd_move(args)
    elif args.search:
        cmd_search(args)
    elif args.validate:
        cmd_validate(args)
    elif args.backlinks:
        cmd_backlinks(args)
    elif args.unlinked_mentions:
        cmd_unlinked_mentions(args)
    elif args.graph is not None:
        cmd_graph(args)
    elif args.query:
        cmd_query(args)
    elif args.bookmarks:
        cmd_bookmarks(args)
    elif args.new:
        cmd_new(args)
    elif args.daily_note:
        cmd_daily_note(args)
    elif args.weekly_note:
        cmd_weekly_note(args)
    elif args.resolve_embeds:
        cmd_resolve_embeds(args)
    elif args.agent and args.summary:
        cmd_write(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
