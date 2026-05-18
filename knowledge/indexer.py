#!/usr/bin/env python3
"""Index the knowledge vault into _index.db (Obsidian-style wiki links, FTS, tags)."""

import fcntl
import hashlib
import json
import os
import re
import sqlite3
import sys

VAULT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(VAULT_DIR, "_index.db")

WIKI_LINK_RE = re.compile(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]")
# Valid wiki-link targets are paths: word chars, slashes, hyphens, dots, spaces.
# Excludes bash conditionals like [[ $VAR == "x" ]], [[ ! -f ... ]], [[ $N -gt 0 ]]
_WIKI_LINK_VALID = re.compile(r"^[\w/\-\.\s]+$")
FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)

# Simple YAML-enough parser (no dependency needed for flat frontmatter)
def parse_frontmatter(text):
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    raw = m.group(1)
    fm = {}
    for line in raw.splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if val.startswith("[") and val.endswith("]"):
                val = [v.strip().strip('"').strip("'") for v in val[1:-1].split(",") if v.strip()]
            fm[key] = val
    body = text[m.end():]
    return fm, body


def content_hash(text):
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def infer_file_type(fm, rel_path):
    if ft := fm.get("type"):
        return ft
    parts = rel_path.split("/")
    if len(parts) > 1:
        folder = parts[0].rstrip("s")  # profiles -> profile
        if folder in ("profile", "workspace", "agent", "decision", "conversation", "pattern", "task"):
            return folder
    return "note"


def _resolve_link_target(cur, target: str):
    """
    Resolve a wiki-link target to a file ID.

    Resolution order:
    1. Exact path match
    2. Path + .md
    3. Directory index files (learnings.md, README.md, profile.md)
    4. Basename match anywhere in vault
    5. Alias match (if aliases table exists)
    """
    # 1-2: exact or with .md
    for candidate in [target, target + ".md"]:
        r = cur.execute("SELECT id FROM files WHERE path=?", (candidate,)).fetchone()
        if r:
            return r[0]

    # 3: directory index — target is a directory, look for default files inside
    for index_file in ["learnings.md", "README.md", "profile.md", "index.md"]:
        candidate = f"{target}/{index_file}"
        r = cur.execute("SELECT id FROM files WHERE path=?", (candidate,)).fetchone()
        if r:
            return r[0]

    # 4: basename match
    r = cur.execute("SELECT id FROM files WHERE path LIKE ?", (f"%/{target}.md",)).fetchone()
    if r:
        return r[0]

    # 5: alias match (if table exists)
    try:
        r = cur.execute(
            "SELECT file_id FROM aliases WHERE alias_name=? COLLATE NOCASE", (target,)
        ).fetchone()
        if r:
            return r[0]
    except sqlite3.OperationalError:
        pass  # aliases table doesn't exist yet

    return None


def _log_search_results(db_path, paths):
    """Log which vault entries were returned in search results."""
    if not paths:
        return
    try:
        conn = sqlite3.connect(str(db_path))
        conn.executemany(
            "INSERT INTO search_log (path) VALUES (?)",
            [(p,) for p in paths]
        )
        conn.commit()
        conn.close()
    except Exception:
        pass  # Never fail vault operations due to logging


def get_backlinks(note_path: str, db_path: str = DB_PATH) -> list:
    """
    Return all vault files that link TO the given path.
    Accepts paths with or without .md extension.
    """
    if not os.path.exists(db_path):
        return []

    targets = [note_path]
    if note_path.endswith(".md"):
        targets.append(note_path[:-3])
    else:
        targets.append(note_path + ".md")

    conn = sqlite3.connect(db_path, isolation_level=None)
    try:
        ph = ",".join("?" * len(targets))
        rows = conn.execute(
            f"""
            SELECT DISTINCT f.path, l.link_text
            FROM links l
            JOIN files f ON f.id = l.source_file_id
            WHERE l.target_path IN ({ph})
               OR l.target_file_id IN (
                   SELECT id FROM files WHERE path IN ({ph})
               )
            ORDER BY f.path
            """,
            targets + targets,
        ).fetchall()
    finally:
        conn.close()

    return [{"source_path": r[0], "link_text": r[1]} for r in rows]


def get_unlinked_mentions(term: str, db_path: str = DB_PATH) -> list:
    """
    Find notes that mention `term` in content but don't wiki-link to it.
    Like Obsidian's "Unlinked mentions" panel.
    """
    if not os.path.exists(db_path):
        return []

    conn = sqlite3.connect(db_path, isolation_level=None)
    try:
        # Get files that mention the term via FTS
        fts_rows = conn.execute(
            "SELECT path FROM fts_content WHERE fts_content MATCH ?", (term,)
        ).fetchall()
        mentioned_paths = {r[0] for r in fts_rows if r[0]}

        # Get files that already link to this term
        linked_sources = set()
        for row in conn.execute(
            "SELECT f.path FROM links l JOIN files f ON f.id = l.source_file_id "
            "WHERE l.target_path LIKE ?", (f"%{term}%",)
        ).fetchall():
            linked_sources.add(row[0])

        # Unlinked = mentioned but not linked
        unlinked = sorted(mentioned_paths - linked_sources)
    finally:
        conn.close()

    _log_search_results(db_path, list(mentioned_paths))
    return [{"path": p, "term": term} for p in unlinked]


def get_graph(note_path: str = None, db_path: str = DB_PATH) -> dict:
    """
    Export graph data as JSON {nodes: [...], edges: [...]}.
    If note_path is given, return local graph (1-hop connections).
    If None, return global graph.
    """
    if not os.path.exists(db_path):
        return {"nodes": [], "edges": []}

    conn = sqlite3.connect(db_path, isolation_level=None)
    try:
        if note_path:
            # Local graph: this note + direct connections
            # Normalise path — try exact, +.md, and directory index files
            targets = [note_path]
            if note_path.endswith(".md"):
                targets.append(note_path[:-3])
            else:
                targets.append(note_path + ".md")
                for idx_file in ["learnings.md", "README.md", "profile.md", "index.md"]:
                    targets.append(f"{note_path}/{idx_file}")

            ph = ",".join("?" * len(targets))

            # Get the file ID
            file_row = conn.execute(
                f"SELECT id, path, title, file_type FROM files WHERE path IN ({ph})",
                targets
            ).fetchone()
            if not file_row:
                return {"nodes": [], "edges": []}

            fid, fpath, ftitle, ftype = file_row
            node_ids = {fid}
            nodes = [{"id": fid, "path": fpath, "title": ftitle, "type": ftype, "center": True}]
            edges = []

            # Outgoing links
            for row in conn.execute(
                "SELECT l.target_file_id, l.link_text, f2.path, f2.title, f2.file_type "
                "FROM links l LEFT JOIN files f2 ON f2.id = l.target_file_id "
                "WHERE l.source_file_id=? AND l.target_file_id IS NOT NULL", (fid,)
            ).fetchall():
                tid, ltext, tpath, ttitle, ttype = row
                if tid not in node_ids:
                    nodes.append({"id": tid, "path": tpath, "title": ttitle, "type": ttype})
                    node_ids.add(tid)
                edges.append({"source": fid, "target": tid, "label": ltext})

            # Incoming links (backlinks)
            for row in conn.execute(
                "SELECT l.source_file_id, l.link_text, f2.path, f2.title, f2.file_type "
                "FROM links l JOIN files f2 ON f2.id = l.source_file_id "
                "WHERE l.target_file_id=?", (fid,)
            ).fetchall():
                sid, ltext, spath, stitle, stype = row
                if sid not in node_ids:
                    nodes.append({"id": sid, "path": spath, "title": stitle, "type": stype})
                    node_ids.add(sid)
                edges.append({"source": sid, "target": fid, "label": ltext})

        else:
            # Global graph: all files + all resolved links
            nodes = []
            for row in conn.execute("SELECT id, path, title, file_type FROM files").fetchall():
                nodes.append({"id": row[0], "path": row[1], "title": row[2], "type": row[3]})

            edges = []
            for row in conn.execute(
                "SELECT source_file_id, target_file_id, link_text FROM links "
                "WHERE target_file_id IS NOT NULL"
            ).fetchall():
                edges.append({"source": row[0], "target": row[1], "label": row[2]})
    finally:
        conn.close()

    return {"nodes": nodes, "edges": edges}


def get_file_context(file_path: str, db_path: str = DB_PATH) -> dict:
    """Return unified code + knowledge context for a file.

    Args:
        file_path: Relative path like 'Handler/handler_base.py'
        db_path: Path to _index.db

    Returns:
        {
            'file_path': 'Handler/handler_base.py',
            'importers': ['Handler/handler_trading_team.py', ...],
            'imports': ['some/other.py', ...],
            'vault_notes': ['agents/claude-code/log/fix.md', ...],
            'hub_score': 0.92,
            'change_frequency': 'high',  # high(>=30), medium(>=10), low(>0), unknown
        }
    """
    empty = {
        "file_path": file_path,
        "importers": [],
        "imports": [],
        "vault_notes": [],
        "hub_score": 0,
        "change_frequency": "unknown",
    }

    if not os.path.exists(db_path):
        return empty

    conn = sqlite3.connect(db_path, isolation_level=None)
    try:
        # 1. Look up the file record and its frontmatter
        row = conn.execute(
            "SELECT id, frontmatter FROM files WHERE path=?", (file_path,)
        ).fetchone()

        if not row:
            return empty

        file_id, fm_json = row

        # Parse hub_score and change_count from frontmatter
        try:
            fm = json.loads(fm_json) if fm_json else {}
        except (json.JSONDecodeError, TypeError):
            fm = {}

        hub_score = float(fm.get("hub_score", 0) or 0)
        change_count = fm.get("change_count")
        try:
            change_count = int(change_count) if change_count is not None else None
        except (ValueError, TypeError):
            change_count = None

        if change_count is None:
            change_frequency = "unknown"
        elif change_count >= 30:
            change_frequency = "high"
        elif change_count >= 10:
            change_frequency = "medium"
        elif change_count > 0:
            change_frequency = "low"
        else:
            change_frequency = "unknown"

        # 2. Importers: other code files that code_import → this file
        importer_rows = conn.execute(
            """
            SELECT DISTINCT f.path
            FROM links l
            JOIN files f ON f.id = l.source_file_id
            WHERE l.target_file_id = ?
              AND l.link_type = 'code_import'
            ORDER BY f.path
            """,
            (file_id,),
        ).fetchall()
        importers = [r[0] for r in importer_rows]

        # 3. Imports: files this file code_imports
        import_rows = conn.execute(
            """
            SELECT DISTINCT l.target_path
            FROM links l
            WHERE l.source_file_id = ?
              AND l.link_type = 'code_import'
            ORDER BY l.target_path
            """,
            (file_id,),
        ).fetchall()
        imports = [r[0] for r in import_rows]

        # 4. Vault notes: vault-source files that wiki_link → this file
        vault_note_rows = conn.execute(
            """
            SELECT DISTINCT f.path
            FROM links l
            JOIN files f ON f.id = l.source_file_id
            WHERE l.target_file_id = ?
              AND l.link_type = 'wiki_link'
              AND f.source = 'vault'
            ORDER BY f.path
            """,
            (file_id,),
        ).fetchall()
        vault_notes = [r[0] for r in vault_note_rows]

    finally:
        conn.close()

    return {
        "file_path": file_path,
        "importers": importers,
        "imports": imports,
        "vault_notes": vault_notes,
        "hub_score": hub_score,
        "change_frequency": change_frequency,
    }


def query_frontmatter(filter_expr: str, db_path: str = DB_PATH) -> list:
    """
    Query vault files by frontmatter fields (Dataview-style).

    Supports: field=value, field>value, field<value, connected with AND/OR.
    Example: "type=discovery AND agent=scout"
    """
    if not os.path.exists(db_path):
        return []

    conn = sqlite3.connect(db_path, isolation_level=None)
    try:
        rows = conn.execute("SELECT path, title, file_type, frontmatter FROM files").fetchall()
    finally:
        conn.close()

    # Parse filter expression
    conditions = _parse_filter_expr(filter_expr)
    results = []

    for path, title, file_type, fm_json in rows:
        try:
            fm = json.loads(fm_json) if fm_json else {}
        except (json.JSONDecodeError, TypeError):
            fm = {}

        if _matches_conditions(fm, conditions):
            results.append({"path": path, "title": title, "type": file_type, "frontmatter": fm})

    return results


def _parse_filter_expr(expr: str) -> list:
    """Parse 'field=value AND field>value OR field<value' into condition groups."""
    # Split on AND/OR, preserving the operator
    parts = re.split(r'\s+(AND|OR)\s+', expr, flags=re.IGNORECASE)

    conditions = []
    current_op = "AND"

    for part in parts:
        part = part.strip()
        if part.upper() in ("AND", "OR"):
            current_op = part.upper()
            continue

        # Parse individual condition
        for op in [">=", "<=", "!=", "=", ">", "<"]:
            if op in part:
                field, _, value = part.partition(op)
                conditions.append({
                    "field": field.strip(),
                    "op": op,
                    "value": value.strip(),
                    "join": current_op
                })
                break

    return conditions


def _matches_conditions(fm: dict, conditions: list) -> bool:
    """Check if frontmatter matches all/any conditions."""
    if not conditions:
        return True

    results = []
    for cond in conditions:
        field_val = fm.get(cond["field"], "")
        # Handle list fields (e.g., tags)
        if isinstance(field_val, list):
            field_val = ",".join(str(v) for v in field_val)
        field_val = str(field_val)
        target = cond["value"]

        op = cond["op"]
        if op == "=":
            match = target.lower() in field_val.lower()
        elif op == "!=":
            match = target.lower() not in field_val.lower()
        elif op == ">":
            try:
                match = float(field_val) > float(target)
            except ValueError:
                match = field_val > target
        elif op == "<":
            try:
                match = float(field_val) < float(target)
            except ValueError:
                match = field_val < target
        elif op == ">=":
            try:
                match = float(field_val) >= float(target)
            except ValueError:
                match = field_val >= target
        elif op == "<=":
            try:
                match = float(field_val) <= float(target)
            except ValueError:
                match = field_val <= target
        else:
            match = False

        results.append((match, cond.get("join", "AND")))

    # Evaluate: AND reduces, OR expands
    result = results[0][0]
    for i in range(1, len(results)):
        match, join = results[i]
        if join == "AND":
            result = result and match
        else:  # OR
            result = result or match
    return result


def resolve_embeds(content: str, vault_dir: str = VAULT_DIR) -> str:
    """
    Expand ![[ref]] and ![[ref#section]] embed syntax (Obsidian transclusion).
    Returns content with embeds replaced by the referenced content.
    """
    embed_re = re.compile(r"!\[\[([^\]#]+)(?:#([^\]]+))?\]\]")

    def _replace_embed(match):
        ref = match.group(1).strip()
        section = match.group(2)

        # Try to find the file
        for candidate in [ref, ref + ".md"]:
            full_path = os.path.join(vault_dir, candidate)
            if os.path.exists(full_path):
                with open(full_path, 'r') as f:
                    text = f.read()

                # Strip frontmatter
                fm_match = FRONTMATTER_RE.match(text)
                if fm_match:
                    text = text[fm_match.end():]

                if section:
                    # Extract specific section
                    section_re = re.compile(
                        rf"^(#{1,6})\s+{re.escape(section)}\s*\n(.*?)(?=\n#{1,6}\s|\Z)",
                        re.MULTILINE | re.DOTALL
                    )
                    sec_match = section_re.search(text)
                    if sec_match:
                        return sec_match.group(0).strip()
                    return f"> *Section '{section}' not found in {ref}*"

                return text.strip()

        return f"> *Embed not found: {ref}*"

    return embed_re.sub(_replace_embed, content)


def run():
    # File lock prevents concurrent reindex runs from corrupting FTS5 tables
    lock_path = os.path.join(VAULT_DIR, "_index.lock")
    lock_fd = open(lock_path, 'w')
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except (OSError, IOError):
        print("⚠ Another indexer is running — skipping")
        lock_fd.close()
        return

    try:
        _run_locked(lock_fd)
    finally:
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        lock_fd.close()


def _run_locked(lock_fd):
    db = sqlite3.connect(DB_PATH, isolation_level=None)
    db.execute("PRAGMA journal_mode=DELETE")
    db.execute("PRAGMA mmap_size=0")
    db.execute("PRAGMA foreign_keys=ON")
    db.execute("PRAGMA busy_timeout=10000")
    cur = db.cursor()

    # Ensure aliases table exists (Phase 3: Obsidian-style aliases)
    cur.execute("""CREATE TABLE IF NOT EXISTS aliases (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        file_id INTEGER NOT NULL,
        alias_name TEXT NOT NULL,
        FOREIGN KEY (file_id) REFERENCES files(id),
        UNIQUE(file_id, alias_name)
    )""")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_aliases_name ON aliases (alias_name COLLATE NOCASE)")

    # Search logging table (tracks which vault entries are returned in searches)
    cur.execute("""CREATE TABLE IF NOT EXISTS search_log (
        path TEXT,
        queried_at TEXT DEFAULT (datetime('now'))
    )""")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_search_log_path ON search_log(path)")

    # Schema migration: add link_type to links (idempotent)
    try:
        cur.execute("ALTER TABLE links ADD COLUMN link_type TEXT DEFAULT 'wiki_link'")
    except sqlite3.OperationalError:
        pass  # Column already exists

    # Schema migration: add source to files (idempotent)
    try:
        cur.execute("ALTER TABLE files ADD COLUMN source TEXT DEFAULT 'vault'")
    except sqlite3.OperationalError:
        pass  # Column already exists

    # Indexes for new columns
    cur.execute("CREATE INDEX IF NOT EXISTS idx_links_type ON links(link_type)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_files_source ON files(source)")

    md_files = {}  # rel_path -> abs_path
    for root, _, files in os.walk(VAULT_DIR):
        for f in files:
            if f.endswith(".md"):
                abs_path = os.path.join(root, f)
                rel = os.path.relpath(abs_path, VAULT_DIR)
                md_files[rel] = abs_path

    stats = {"indexed": 0, "links": 0, "broken": 0, "tags": 0}

    # Pass 1: upsert files
    for rel, abs_path in md_files.items():
        text = open(abs_path).read()
        h = content_hash(text)

        # Check if unchanged
        existing = cur.execute("SELECT id, content_hash FROM files WHERE path=?", (rel,)).fetchone()
        if existing and existing[1] == h:
            stats["indexed"] += 1
            continue

        fm, body = parse_frontmatter(text)
        file_type = infer_file_type(fm, rel)
        title = fm.get("title", os.path.splitext(os.path.basename(rel))[0])
        status = fm.get("status", "active")

        if existing:
            fid = existing[0]
            cur.execute("""UPDATE files SET title=?, file_type=?, workspace_id=?, agent_id=?, user_id=?,
                           updated_at=CURRENT_TIMESTAMP, status=?, frontmatter=?, content_hash=? WHERE id=?""",
                        (title, file_type, fm.get("workspace"), fm.get("agent"), fm.get("user"),
                         status, json.dumps(fm), h, fid))
            # Update FTS
            cur.execute("DELETE FROM fts_content WHERE path=?", (rel,))
            cur.execute("INSERT INTO fts_content(path, title, content, file_type) VALUES (?,?,?,?)",
                        (rel, title, body, file_type))
        else:
            cur.execute("""INSERT INTO files (path, title, file_type, workspace_id, agent_id, user_id,
                           status, frontmatter, content_hash) VALUES (?,?,?,?,?,?,?,?,?)""",
                        (rel, title, file_type, fm.get("workspace"), fm.get("agent"), fm.get("user"),
                         status, json.dumps(fm), h))
            fid = cur.lastrowid
            cur.execute("INSERT INTO fts_content(path, title, content, file_type) VALUES (?,?,?,?)",
                        (rel, title, body, file_type))

        # Tags
        tags = fm.get("tags", [])
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",") if t.strip()]
        cur.execute("DELETE FROM file_tags WHERE file_id=?", (fid,))
        for tag in tags:
            cur.execute("INSERT OR IGNORE INTO tags (tag_name) VALUES (?)", (tag,))
            tid = cur.execute("SELECT id FROM tags WHERE tag_name=?", (tag,)).fetchone()[0]
            cur.execute("INSERT OR IGNORE INTO file_tags (file_id, tag_id) VALUES (?,?)", (fid, tid))
            stats["tags"] += 1

        # Aliases (Obsidian-style alternative names)
        aliases = fm.get("aliases", [])
        if isinstance(aliases, str):
            aliases = [a.strip() for a in aliases.split(",") if a.strip()]
        cur.execute("DELETE FROM aliases WHERE file_id=?", (fid,))
        for alias in aliases:
            cur.execute("INSERT OR IGNORE INTO aliases (file_id, alias_name) VALUES (?,?)",
                        (fid, alias))

        # Links
        cur.execute("DELETE FROM links WHERE source_file_id=?", (fid,))
        for match in WIKI_LINK_RE.finditer(text):
            target, display = match.group(1).strip(), match.group(2)
            if not _WIKI_LINK_VALID.match(target):
                continue  # skip bash conditionals like [[ $VAR == "x" ]]
            cur.execute("INSERT INTO links (source_file_id, target_path, link_text) VALUES (?,?,?)",
                        (fid, target, display or target))
            stats["links"] += 1

        stats["indexed"] += 1

    # Pass 2: resolve link targets
    for row in cur.execute("SELECT id, target_path FROM links WHERE target_file_id IS NULL").fetchall():
        lid, target = row
        resolved = _resolve_link_target(cur, target)
        if resolved:
            cur.execute("UPDATE links SET target_file_id=? WHERE id=?", (resolved, lid))
        else:
            stats["broken"] += 1

    db.commit()
    db.close()

    print(f"✅ Indexed {stats['indexed']} files, {stats['links']} links, {stats['tags']} tags, {stats['broken']} broken links")


def validate_links(db_path: str = DB_PATH) -> dict:
    """
    Detect orphaned wiki links — [[references]] whose target file doesn't exist.

    Obsidian highlights these automatically; we replicate that here.
    Run after any vault write to catch link rot early.

    Returns:
        {
            "orphaned": [{"source_path": str, "link_text": str, "target_path": str}, ...],
            "total_links": int,
            "broken_count": int,
        }
    """
    if not os.path.exists(db_path):
        return {"orphaned": [], "total_links": 0, "broken_count": 0, "error": "index DB not found"}

    db = sqlite3.connect(db_path, isolation_level=None)
    try:
        total = db.execute("SELECT COUNT(*) FROM links").fetchone()[0]
        rows = db.execute(
            """
            SELECT f.path, l.link_text, l.target_path
            FROM links l
            JOIN files f ON f.id = l.source_file_id
            WHERE l.target_file_id IS NULL
            ORDER BY f.path
            """
        ).fetchall()
    finally:
        db.close()

    orphaned = [{"source_path": r[0], "link_text": r[1], "target_path": r[2]} for r in rows]
    broken = len(orphaned)

    if broken:
        print(f"⚠️  {broken} orphaned links found (out of {total} total):")
        for o in orphaned:
            print(f"   {o['source_path']} → [[{o['target_path']}]]")
    else:
        print(f"✅ All {total} links resolve correctly. No orphaned references.")

    return {"orphaned": orphaned, "total_links": total, "broken_count": broken}


def update_single_file(rel_path: str, vault_dir: str = VAULT_DIR):
    """Surgically update FTS + files table for ONE file. No full scan.

    Called by vault_writer after each write instead of full reindex().
    Uses a file lock to prevent concurrent FTS corruption.
    """
    abs_path = os.path.join(vault_dir, rel_path)
    if not os.path.exists(abs_path):
        return

    db_path = os.path.join(vault_dir, "_index.db")
    if not os.path.exists(db_path):
        return  # No index DB yet — full reindex needed first

    # File lock (shared with run() to prevent concurrent access)
    lock_path = os.path.join(vault_dir, "_index.lock")
    lock_fd = open(lock_path, 'w')
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX)  # Blocking — wait for full reindex to finish
    except (OSError, IOError):
        lock_fd.close()
        return

    try:
        text = open(abs_path).read()
        h = content_hash(text)

        db = sqlite3.connect(db_path, isolation_level=None)
        db.execute("PRAGMA journal_mode=DELETE")
        db.execute("PRAGMA mmap_size=0")
        db.execute("PRAGMA busy_timeout=10000")
        cur = db.cursor()

        # Check if unchanged
        existing = cur.execute("SELECT id, content_hash FROM files WHERE path=?", (rel_path,)).fetchone()
        if existing and existing[1] == h:
            db.close()
            return  # No change — skip

        fm, body = parse_frontmatter(text)
        file_type = infer_file_type(fm, rel_path)
        title = fm.get("title", os.path.splitext(os.path.basename(rel_path))[0])
        status = fm.get("status", "active")

        if existing:
            fid = existing[0]
            cur.execute(
                """UPDATE files SET title=?, file_type=?, workspace_id=?, agent_id=?, user_id=?,
                   updated_at=CURRENT_TIMESTAMP, status=?, frontmatter=?, content_hash=? WHERE id=?""",
                (title, file_type, fm.get("workspace"), fm.get("agent"), fm.get("user"),
                 status, json.dumps(fm), h, fid)
            )
            cur.execute("DELETE FROM fts_content WHERE path=?", (rel_path,))
            cur.execute("INSERT INTO fts_content(path, title, content, file_type) VALUES (?,?,?,?)",
                        (rel_path, title, body, file_type))
        else:
            cur.execute(
                """INSERT INTO files (path, title, file_type, workspace_id, agent_id, user_id,
                   status, frontmatter, content_hash) VALUES (?,?,?,?,?,?,?,?,?)""",
                (rel_path, title, file_type, fm.get("workspace"), fm.get("agent"), fm.get("user"),
                 status, json.dumps(fm), h)
            )
            fid = cur.lastrowid
            cur.execute("INSERT INTO fts_content(path, title, content, file_type) VALUES (?,?,?,?)",
                        (rel_path, title, body, file_type))

        # Tags for this file only
        tags = fm.get("tags", [])
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",") if t.strip()]
        cur.execute("DELETE FROM file_tags WHERE file_id=?", (fid,))
        for tag in tags:
            cur.execute("INSERT OR IGNORE INTO tags (tag_name) VALUES (?)", (tag,))
            tid = cur.execute("SELECT id FROM tags WHERE tag_name=?", (tag,)).fetchone()[0]
            cur.execute("INSERT OR IGNORE INTO file_tags (file_id, tag_id) VALUES (?,?)", (fid, tid))

        db.commit()
        db.close()
    except Exception as e:
        # Don't crash the caller — vault write already succeeded on disk
        import logging
        logging.getLogger(__name__).warning("update_single_file(%s) failed: %s", rel_path, e)
    finally:
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        lock_fd.close()


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "validate":
        validate_links()
    else:
        run()
