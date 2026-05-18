#!/usr/bin/env python3
"""vault_search.py — unified FTS + graph traversal over vault + Nexus code index.

Single query returns:
  * FTS5 hits spanning both layers (vault notes + code files)
  * For each CODE hit: who imports it (impact radius) and what it imports
  * For each VAULT hit: wiki-linked related notes

Usage:
  python3 vault_search.py "kronos tuning"
  python3 vault_search.py "handler_data_validator local model"
  python3 vault_search.py "openclaw compaction" --limit 20
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
import textwrap
from pathlib import Path


DB_PATH = Path.home() / "Jarvis" / "knowledge" / "_index.db"
VAULT_ROOT = Path.home() / "Jarvis" / "knowledge"


def search(conn: sqlite3.Connection, query: str, limit: int) -> list[tuple[str, str, float]]:
    """FTS5 search across the unified index. Returns (path, file_type, rank)."""
    rows = conn.execute(
        """
        SELECT path, file_type, rank
        FROM fts_content
        WHERE fts_content MATCH ?
        ORDER BY rank
        LIMIT ?
        """,
        (query, limit),
    ).fetchall()
    return rows


def code_impact(conn: sqlite3.Connection, path: str) -> dict:
    """For a code file, return who imports it and what it imports."""
    importers = conn.execute(
        """
        SELECT src.path
        FROM links l
        JOIN files tgt ON tgt.id = l.target_file_id
        JOIN files src ON src.id = l.source_file_id
        WHERE tgt.path = ? AND l.link_type = 'code_import'
        LIMIT 10
        """,
        (path,),
    ).fetchall()

    imports = conn.execute(
        """
        SELECT tgt.path
        FROM links l
        JOIN files src ON src.id = l.source_file_id
        LEFT JOIN files tgt ON tgt.id = l.target_file_id
        WHERE src.path = ? AND l.link_type = 'code_import'
        LIMIT 10
        """,
        (path,),
    ).fetchall()

    return {
        "importers": [r[0] for r in importers if r[0]],
        "imports": [r[0] for r in imports if r[0]],
    }


def vault_links(conn: sqlite3.Connection, path: str) -> dict:
    """For a vault note, return wiki-linked related notes (out + in)."""
    links_out = conn.execute(
        """
        SELECT tgt.path
        FROM links l
        JOIN files src ON src.id = l.source_file_id
        LEFT JOIN files tgt ON tgt.id = l.target_file_id
        WHERE src.path = ? AND l.link_type = 'wiki_link'
        LIMIT 10
        """,
        (path,),
    ).fetchall()

    links_in = conn.execute(
        """
        SELECT src.path
        FROM links l
        JOIN files tgt ON tgt.id = l.target_file_id
        JOIN files src ON src.id = l.source_file_id
        WHERE tgt.path = ? AND l.link_type = 'wiki_link'
        LIMIT 10
        """,
        (path,),
    ).fetchall()

    return {
        "links_out": [r[0] for r in links_out if r[0]],
        "links_in": [r[0] for r in links_in if r[0]],
    }


def snippet(path: str, max_chars: int = 240) -> str:
    """Best-effort content snippet for preview."""
    full_path = VAULT_ROOT / path
    if not full_path.exists():
        full_path = Path(path)
    try:
        if full_path.exists() and full_path.is_file():
            text = full_path.read_text(encoding="utf-8", errors="replace")
            # Skip frontmatter
            if text.startswith("---"):
                parts = text.split("---", 2)
                if len(parts) >= 3:
                    text = parts[2]
            text = text.strip().replace("\n", " ")
            return text[:max_chars] + ("…" if len(text) > max_chars else "")
    except Exception:
        pass
    return ""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("query", help="FTS5 query (supports AND/OR/NEAR, phrase, file_type: filter)")
    ap.add_argument("--limit", type=int, default=10)
    ap.add_argument("--no-graph", action="store_true", help="Skip graph traversal (faster)")
    args = ap.parse_args()

    if not DB_PATH.exists():
        print(f"ERROR: index not found at {DB_PATH}", file=sys.stderr)
        return 1

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = None

    try:
        hits = search(conn, args.query, args.limit)
    except sqlite3.OperationalError as e:
        print(f"ERROR: FTS5 query failed: {e}", file=sys.stderr)
        print("Try simpler terms or quote phrases.", file=sys.stderr)
        return 1

    if not hits:
        print(f"no hits for query: {args.query!r}")
        return 0

    print(f"=== {len(hits)} hits for: {args.query!r} ===\n")

    for path, file_type, rank in hits:
        is_code = file_type == "code"
        layer = "CODE" if is_code else "VAULT"
        print(f"[{layer}] {path}  (type={file_type}, rank={rank:.2f})")

        preview = snippet(path)
        if preview:
            print(f"  {textwrap.shorten(preview, width=200, placeholder='…')}")

        if args.no_graph:
            print()
            continue

        if is_code:
            ctx = code_impact(conn, path)
            if ctx["importers"]:
                print(f"  ← imported by ({len(ctx['importers'])}): {', '.join(ctx['importers'][:5])}")
            if ctx["imports"]:
                print(f"  → imports ({len(ctx['imports'])}): {', '.join(ctx['imports'][:5])}")
        else:
            links = vault_links(conn, path)
            if links["links_out"]:
                print(f"  → links to: {', '.join(links['links_out'][:5])}")
            if links["links_in"]:
                print(f"  ← linked from: {', '.join(links['links_in'][:5])}")
        print()

    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
