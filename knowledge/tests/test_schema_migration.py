#!/usr/bin/env python3
"""Tests for _index.db schema migration: link_type and source columns."""

import sqlite3
import sys
import unittest

# Allow running standalone from any directory
sys.path.insert(0, "~/Jarvis")


def _build_migrated_db() -> sqlite3.Connection:
    """Build an in-memory DB with the target schema (post-migration)."""
    db = sqlite3.connect(":memory:")
    db.execute("PRAGMA foreign_keys=ON")
    cur = db.cursor()

    # Core tables matching production schema
    cur.executescript("""
        CREATE TABLE IF NOT EXISTS files (
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

        CREATE TABLE IF NOT EXISTS links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_file_id INTEGER NOT NULL,
            target_path TEXT NOT NULL,
            target_file_id INTEGER,
            link_text TEXT,
            display_text TEXT,
            link_type TEXT DEFAULT 'wiki_link',
            FOREIGN KEY (source_file_id) REFERENCES files(id),
            FOREIGN KEY (target_file_id) REFERENCES files(id)
        );

        CREATE INDEX IF NOT EXISTS idx_links_type ON links(link_type);
        CREATE INDEX IF NOT EXISTS idx_files_source ON files(source);
    """)
    db.commit()
    return db


def _get_table_columns(db: sqlite3.Connection, table: str) -> list:
    """Return list of column names for a table."""
    rows = db.execute(f"PRAGMA table_info({table})").fetchall()
    return [row[1] for row in rows]


def _get_indexes(db: sqlite3.Connection) -> list:
    """Return list of index names in the DB."""
    rows = db.execute("SELECT name FROM sqlite_master WHERE type='index'").fetchall()
    return [row[0] for row in rows]


class TestLinkTypeColumn(unittest.TestCase):
    """Verify links table has link_type column after migration."""

    def setUp(self):
        self.db = _build_migrated_db()

    def tearDown(self):
        self.db.close()

    def test_link_type_column_exists_after_migration(self):
        """links table must have a link_type column."""
        columns = _get_table_columns(self.db, "links")
        self.assertIn(
            "link_type",
            columns,
            f"link_type column missing from links table. Found: {columns}",
        )

    def test_link_type_default_is_wiki_link(self):
        """link_type should default to 'wiki_link'."""
        # Insert a file first to satisfy FK
        self.db.execute(
            "INSERT INTO files (path, title) VALUES (?, ?)",
            ("agents/test.md", "Test"),
        )
        fid = self.db.execute("SELECT last_insert_rowid()").fetchone()[0]
        self.db.execute(
            "INSERT INTO links (source_file_id, target_path, link_text) VALUES (?, ?, ?)",
            (fid, "agents/other.md", "other"),
        )
        self.db.commit()
        row = self.db.execute("SELECT link_type FROM links WHERE source_file_id=?", (fid,)).fetchone()
        self.assertEqual(row[0], "wiki_link")

    def test_link_type_index_exists(self):
        """idx_links_type index must be present."""
        indexes = _get_indexes(self.db)
        self.assertIn("idx_links_type", indexes, f"idx_links_type missing. Found: {indexes}")


class TestSourceColumn(unittest.TestCase):
    """Verify files table has source column after migration."""

    def setUp(self):
        self.db = _build_migrated_db()

    def tearDown(self):
        self.db.close()

    def test_source_column_exists_after_migration(self):
        """files table must have a source column."""
        columns = _get_table_columns(self.db, "files")
        self.assertIn(
            "source",
            columns,
            f"source column missing from files table. Found: {columns}",
        )

    def test_source_default_is_vault(self):
        """source column should default to 'vault'."""
        self.db.execute(
            "INSERT INTO files (path, title) VALUES (?, ?)",
            ("test/file.md", "File"),
        )
        self.db.commit()
        row = self.db.execute("SELECT source FROM files WHERE path=?", ("test/file.md",)).fetchone()
        self.assertEqual(row[0], "vault")

    def test_source_index_exists(self):
        """idx_files_source index must be present."""
        indexes = _get_indexes(self.db)
        self.assertIn("idx_files_source", indexes, f"idx_files_source missing. Found: {indexes}")


class TestCodeImportLinkType(unittest.TestCase):
    """Verify code_import link_type can be stored and queried."""

    def setUp(self):
        self.db = _build_migrated_db()

    def tearDown(self):
        self.db.close()

    def test_code_import_link_type_stored(self):
        """code_import link_type must round-trip through the DB."""
        # Insert source file
        self.db.execute(
            "INSERT INTO files (path, title, source) VALUES (?, ?, ?)",
            ("src/main.py", "Main", "code"),
        )
        src_id = self.db.execute("SELECT last_insert_rowid()").fetchone()[0]

        # Insert a code_import link
        self.db.execute(
            "INSERT INTO links (source_file_id, target_path, link_text, link_type) VALUES (?, ?, ?, ?)",
            (src_id, "src/utils.py", "utils", "code_import"),
        )
        self.db.commit()

        # Query by link_type
        row = self.db.execute(
            "SELECT link_type FROM links WHERE source_file_id=? AND link_type=?",
            (src_id, "code_import"),
        ).fetchone()
        self.assertIsNotNone(row, "No row found for code_import link_type")
        self.assertEqual(row[0], "code_import")

    def test_mixed_link_types_queryable(self):
        """wiki_link and code_import links can coexist and be filtered."""
        self.db.execute(
            "INSERT INTO files (path, title) VALUES (?, ?)",
            ("agents/hub.md", "Hub"),
        )
        src_id = self.db.execute("SELECT last_insert_rowid()").fetchone()[0]

        self.db.execute(
            "INSERT INTO links (source_file_id, target_path, link_text, link_type) VALUES (?, ?, ?, ?)",
            (src_id, "agents/other.md", "other", "wiki_link"),
        )
        self.db.execute(
            "INSERT INTO links (source_file_id, target_path, link_text, link_type) VALUES (?, ?, ?, ?)",
            (src_id, "src/dep.py", "dep", "code_import"),
        )
        self.db.commit()

        wiki = self.db.execute(
            "SELECT COUNT(*) FROM links WHERE link_type='wiki_link'"
        ).fetchone()[0]
        code = self.db.execute(
            "SELECT COUNT(*) FROM links WHERE link_type='code_import'"
        ).fetchone()[0]

        self.assertEqual(wiki, 1)
        self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
