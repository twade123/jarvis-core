"""Tests for get_file_context() in knowledge/indexer.py."""

import json
import sqlite3
import tempfile
import os
import pytest

from knowledge.indexer import get_file_context


SCHEMA_SQL = """
CREATE TABLE files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    path TEXT NOT NULL UNIQUE,
    title TEXT,
    file_type TEXT,
    workspace_id TEXT,
    agent_id TEXT,
    user_id TEXT,
    status TEXT DEFAULT 'active',
    content_hash TEXT,
    frontmatter TEXT,
    source TEXT DEFAULT 'vault',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_file_id INTEGER NOT NULL,
    target_path TEXT NOT NULL,
    target_file_id INTEGER,
    link_text TEXT,
    display_text TEXT,
    link_type TEXT DEFAULT 'wiki_link'
);
"""


def make_db():
    """Create a temporary SQLite DB with the correct schema. Returns (conn, path)."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    conn = sqlite3.connect(tmp.name)
    conn.executescript(SCHEMA_SQL)
    conn.commit()
    return conn, tmp.name


def teardown_db(conn, path):
    conn.close()
    os.unlink(path)


# ---------------------------------------------------------------------------
# Test 1: importers (reverse code_import edges)
# ---------------------------------------------------------------------------

def test_get_file_context_returns_importers():
    """Reverse code_import edges become importers in the result."""
    conn, db_path = make_db()
    try:
        # Insert target file
        conn.execute(
            "INSERT INTO files (path, title, source) VALUES (?, ?, ?)",
            ("Handler/handler_base.py", "handler_base", "code"),
        )
        target_id = conn.execute(
            "SELECT id FROM files WHERE path=?", ("Handler/handler_base.py",)
        ).fetchone()[0]

        # Insert two files that import handler_base.py
        conn.execute(
            "INSERT INTO files (path, title, source) VALUES (?, ?, ?)",
            ("Handler/handler_trading_team.py", "handler_trading_team", "code"),
        )
        importer1_id = conn.execute(
            "SELECT id FROM files WHERE path=?", ("Handler/handler_trading_team.py",)
        ).fetchone()[0]

        conn.execute(
            "INSERT INTO files (path, title, source) VALUES (?, ?, ?)",
            ("Handler/handler_swarm.py", "handler_swarm", "code"),
        )
        importer2_id = conn.execute(
            "SELECT id FROM files WHERE path=?", ("Handler/handler_swarm.py",)
        ).fetchone()[0]

        # Insert code_import links: importer → target
        conn.execute(
            "INSERT INTO links (source_file_id, target_path, target_file_id, link_type) "
            "VALUES (?, ?, ?, ?)",
            (importer1_id, "Handler/handler_base.py", target_id, "code_import"),
        )
        conn.execute(
            "INSERT INTO links (source_file_id, target_path, target_file_id, link_type) "
            "VALUES (?, ?, ?, ?)",
            (importer2_id, "Handler/handler_base.py", target_id, "code_import"),
        )
        conn.commit()

        result = get_file_context("Handler/handler_base.py", db_path=db_path)

        assert result["file_path"] == "Handler/handler_base.py"
        assert set(result["importers"]) == {
            "Handler/handler_trading_team.py",
            "Handler/handler_swarm.py",
        }
        assert result["imports"] == []
    finally:
        teardown_db(conn, db_path)


# ---------------------------------------------------------------------------
# Test 2: vault_notes (wiki_link edges from vault-source files)
# ---------------------------------------------------------------------------

def test_get_file_context_returns_vault_notes():
    """wiki_link edges from vault-source files are returned as vault_notes."""
    conn, db_path = make_db()
    try:
        # Insert target code file
        conn.execute(
            "INSERT INTO files (path, title, source) VALUES (?, ?, ?)",
            ("Handler/handler_base.py", "handler_base", "code"),
        )
        target_id = conn.execute(
            "SELECT id FROM files WHERE path=?", ("Handler/handler_base.py",)
        ).fetchone()[0]

        # Insert a vault note that references the code file
        conn.execute(
            "INSERT INTO files (path, title, source) VALUES (?, ?, ?)",
            ("agents/claude-code/log/fix.md", "fix", "vault"),
        )
        note_id = conn.execute(
            "SELECT id FROM files WHERE path=?", ("agents/claude-code/log/fix.md",)
        ).fetchone()[0]

        # Insert wiki_link: note → handler_base.py
        conn.execute(
            "INSERT INTO links (source_file_id, target_path, target_file_id, link_type) "
            "VALUES (?, ?, ?, ?)",
            (note_id, "Handler/handler_base.py", target_id, "wiki_link"),
        )

        # Insert a code_import link (should NOT appear in vault_notes)
        conn.execute(
            "INSERT INTO files (path, title, source) VALUES (?, ?, ?)",
            ("Handler/other.py", "other", "code"),
        )
        other_id = conn.execute(
            "SELECT id FROM files WHERE path=?", ("Handler/other.py",)
        ).fetchone()[0]
        conn.execute(
            "INSERT INTO links (source_file_id, target_path, target_file_id, link_type) "
            "VALUES (?, ?, ?, ?)",
            (other_id, "Handler/handler_base.py", target_id, "code_import"),
        )
        conn.commit()

        result = get_file_context("Handler/handler_base.py", db_path=db_path)

        assert result["vault_notes"] == ["agents/claude-code/log/fix.md"]
    finally:
        teardown_db(conn, db_path)


# ---------------------------------------------------------------------------
# Test 3: hub_score and change_frequency from frontmatter
# ---------------------------------------------------------------------------

def test_get_file_context_returns_hub_score():
    """hub_score and change_frequency are derived from frontmatter JSON."""
    conn, db_path = make_db()
    try:
        fm = json.dumps({"hub_score": 0.92, "change_count": 45})
        conn.execute(
            "INSERT INTO files (path, title, source, frontmatter) VALUES (?, ?, ?, ?)",
            ("Handler/handler_base.py", "handler_base", "code", fm),
        )
        conn.commit()

        result = get_file_context("Handler/handler_base.py", db_path=db_path)

        assert result["hub_score"] == pytest.approx(0.92)
        assert result["change_frequency"] == "high"  # 45 >= 30
    finally:
        teardown_db(conn, db_path)


def test_get_file_context_change_frequency_medium():
    """change_count 10-29 maps to 'medium'."""
    conn, db_path = make_db()
    try:
        fm = json.dumps({"hub_score": 0.5, "change_count": 15})
        conn.execute(
            "INSERT INTO files (path, title, source, frontmatter) VALUES (?, ?, ?, ?)",
            ("some/file.py", "file", "code", fm),
        )
        conn.commit()

        result = get_file_context("some/file.py", db_path=db_path)

        assert result["change_frequency"] == "medium"
    finally:
        teardown_db(conn, db_path)


def test_get_file_context_change_frequency_low():
    """change_count 1-9 maps to 'low'."""
    conn, db_path = make_db()
    try:
        fm = json.dumps({"hub_score": 0.1, "change_count": 3})
        conn.execute(
            "INSERT INTO files (path, title, source, frontmatter) VALUES (?, ?, ?, ?)",
            ("some/file.py", "file", "code", fm),
        )
        conn.commit()

        result = get_file_context("some/file.py", db_path=db_path)

        assert result["change_frequency"] == "low"
    finally:
        teardown_db(conn, db_path)


def test_get_file_context_change_frequency_unknown():
    """Missing change_count maps to 'unknown'."""
    conn, db_path = make_db()
    try:
        fm = json.dumps({"hub_score": 0.3})
        conn.execute(
            "INSERT INTO files (path, title, source, frontmatter) VALUES (?, ?, ?, ?)",
            ("some/file.py", "file", "code", fm),
        )
        conn.commit()

        result = get_file_context("some/file.py", db_path=db_path)

        assert result["change_frequency"] == "unknown"
    finally:
        teardown_db(conn, db_path)


# ---------------------------------------------------------------------------
# Test 4: unknown file returns empty result
# ---------------------------------------------------------------------------

def test_get_file_context_unknown_file():
    """Non-existent file returns empty lists and hub_score=0."""
    conn, db_path = make_db()
    try:
        conn.commit()
        result = get_file_context("does/not/exist.py", db_path=db_path)

        assert result["file_path"] == "does/not/exist.py"
        assert result["importers"] == []
        assert result["imports"] == []
        assert result["vault_notes"] == []
        assert result["hub_score"] == 0
        assert result["change_frequency"] == "unknown"
    finally:
        teardown_db(conn, db_path)


# ---------------------------------------------------------------------------
# Test 5: imports (forward code_import edges)
# ---------------------------------------------------------------------------

def test_get_file_context_returns_imports():
    """Forward code_import edges are returned as imports."""
    conn, db_path = make_db()
    try:
        # The file under test
        conn.execute(
            "INSERT INTO files (path, title, source) VALUES (?, ?, ?)",
            ("Handler/handler_trading_team.py", "handler_trading_team", "code"),
        )
        source_id = conn.execute(
            "SELECT id FROM files WHERE path=?", ("Handler/handler_trading_team.py",)
        ).fetchone()[0]

        # Files it imports
        conn.execute(
            "INSERT INTO files (path, title, source) VALUES (?, ?, ?)",
            ("Handler/handler_base.py", "handler_base", "code"),
        )
        dep_id = conn.execute(
            "SELECT id FROM files WHERE path=?", ("Handler/handler_base.py",)
        ).fetchone()[0]

        conn.execute(
            "INSERT INTO links (source_file_id, target_path, target_file_id, link_type) "
            "VALUES (?, ?, ?, ?)",
            (source_id, "Handler/handler_base.py", dep_id, "code_import"),
        )
        conn.commit()

        result = get_file_context("Handler/handler_trading_team.py", db_path=db_path)

        assert result["imports"] == ["Handler/handler_base.py"]
        assert result["importers"] == []
    finally:
        teardown_db(conn, db_path)
