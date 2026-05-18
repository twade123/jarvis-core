"""
Tests for NexusBridge — imports code dependency data from .nexus-map/ into _index.db.

Uses in-memory SQLite with a minimal schema matching the real database.
"""

import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

# Ensure the knowledge package is importable
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from knowledge.nexus_bridge import NexusBridge


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

MINIMAL_AST = {
    "languages": {},
    "stats": {},
    "nodes": [
        {"id": "Handler.handler_base", "type": "Module", "label": "handler_base",
         "path": "Handler/handler_base.py", "lines": 180, "lang": "python"},
        {"id": "Handler.handler_trading_team", "type": "Module", "label": "handler_trading_team",
         "path": "Handler/handler_trading_team.py", "lines": 245, "lang": "python"},
        {"id": "Handler.handler_base.BaseClass", "type": "Class", "label": "BaseClass",
         "path": "Handler/handler_base.py", "lines": 50, "lang": "python"},
    ],
    "edges": [
        # Internal import — both IDs are project nodes
        {"source": "Handler.handler_trading_team", "target": "Handler.handler_base", "type": "imports"},
        # External import — target is NOT a project node
        {"source": "Handler.handler_trading_team", "target": "json", "type": "imports"},
        {"source": "Handler.handler_trading_team", "target": "os", "type": "imports"},
        # contains edge — should be ignored
        {"source": "Handler.handler_base", "target": "Handler.handler_base.BaseClass", "type": "contains"},
    ],
    "warnings": [],
}

MINIMAL_GIT = {
    "analysis_period_days": 90,
    "stats": {},
    "hotspots": [
        {"path": "Handler/handler_trading_team.py", "changes": 42, "risk": "high"},
    ],
    "coupling_pairs": [],
}


def _make_db(tmp_path: Path) -> Path:
    """Create a minimal _index.db in tmp_path matching the real schema."""
    db_path = tmp_path / "_index.db"
    conn = sqlite3.connect(str(db_path))
    conn.executescript("""
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
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            source TEXT DEFAULT 'vault'
        );
        CREATE TABLE links (
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
        CREATE INDEX idx_links_type ON links(link_type);
        CREATE INDEX idx_files_source ON files(source);
    """)
    conn.commit()
    conn.close()
    return db_path


def _make_nexus_dir(tmp_path: Path, ast_data=None, git_data=None) -> Path:
    """Create a fake .nexus-map/ directory with fixture data."""
    nexus_dir = tmp_path / ".nexus-map"
    raw_dir = nexus_dir / "raw"
    raw_dir.mkdir(parents=True)

    ast_payload = ast_data if ast_data is not None else MINIMAL_AST
    git_payload = git_data if git_data is not None else MINIMAL_GIT

    (raw_dir / "ast_nodes.json").write_text(json.dumps(ast_payload))
    (raw_dir / "git_stats.json").write_text(json.dumps(git_payload))
    return nexus_dir


def _run_bridge(tmp_path: Path, ast_data=None, git_data=None) -> NexusBridge:
    """Helper: build nexus dir + db, run bridge, return bridge instance."""
    nexus_dir = _make_nexus_dir(tmp_path, ast_data, git_data)
    db_path = _make_db(tmp_path)
    bridge = NexusBridge(nexus_dir=str(nexus_dir), db_path=str(db_path))
    bridge.run()
    return bridge


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestNexusBridgeModuleRegistration(unittest.TestCase):
    """Module nodes should be registered as files with source='code'."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.bridge = _run_bridge(self.tmp)

    def test_bridge_registers_module_nodes(self):
        """Module nodes appear in files table with source='code'."""
        conn = sqlite3.connect(str(self.tmp / "_index.db"))
        rows = conn.execute(
            "SELECT path, source, file_type FROM files WHERE source='code'"
        ).fetchall()
        conn.close()

        paths = {r[0] for r in rows}
        self.assertIn("Handler/handler_base.py", paths)
        self.assertIn("Handler/handler_trading_team.py", paths)
        # All code rows must have source='code'
        for path, source, file_type in rows:
            self.assertEqual(source, "code")

    def test_bridge_sets_file_type_to_code(self):
        """Registered module nodes have file_type='code'."""
        conn = sqlite3.connect(str(self.tmp / "_index.db"))
        rows = conn.execute(
            "SELECT file_type FROM files WHERE source='code'"
        ).fetchall()
        conn.close()
        for (ft,) in rows:
            self.assertEqual(ft, "code")


class TestNexusBridgeClassNodesSkipped(unittest.TestCase):
    """Class-type nodes must NOT be registered as separate files."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        _run_bridge(self.tmp)
        self.conn = sqlite3.connect(str(self.tmp / "_index.db"))

    def tearDown(self):
        self.conn.close()

    def test_bridge_skips_class_nodes(self):
        """Class nodes (BaseClass) do not appear as separate file rows."""
        rows = self.conn.execute(
            "SELECT COUNT(*) FROM files WHERE source='code'"
        ).fetchone()[0]
        # Only 2 Module nodes should be registered (handler_base + handler_trading_team)
        self.assertEqual(rows, 2)


class TestNexusBridgeImportEdges(unittest.TestCase):
    """Import edges between project modules should be stored as code_import links."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        _run_bridge(self.tmp)
        self.conn = sqlite3.connect(str(self.tmp / "_index.db"))

    def tearDown(self):
        self.conn.close()

    def test_bridge_creates_internal_import_edges(self):
        """Internal imports are stored with link_type='code_import'."""
        rows = self.conn.execute(
            "SELECT COUNT(*) FROM links WHERE link_type='code_import'"
        ).fetchone()[0]
        # Only 1 internal import edge (trading_team → handler_base)
        self.assertEqual(rows, 1)

    def test_import_edge_references_correct_files(self):
        """The code_import link connects the right source and target file IDs."""
        # Get file IDs
        src_id = self.conn.execute(
            "SELECT id FROM files WHERE path='Handler/handler_trading_team.py'"
        ).fetchone()[0]
        tgt_id = self.conn.execute(
            "SELECT id FROM files WHERE path='Handler/handler_base.py'"
        ).fetchone()[0]
        link = self.conn.execute(
            "SELECT source_file_id, target_file_id FROM links WHERE link_type='code_import'"
        ).fetchone()
        self.assertEqual(link[0], src_id)
        self.assertEqual(link[1], tgt_id)


class TestNexusBridgeExternalImportsSkipped(unittest.TestCase):
    """Imports targeting stdlib/third-party packages must be ignored."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        _run_bridge(self.tmp)
        self.conn = sqlite3.connect(str(self.tmp / "_index.db"))

    def tearDown(self):
        self.conn.close()

    def test_bridge_skips_external_imports(self):
        """Imports to 'json', 'os', etc. produce no code_import links."""
        # There are only 2 external imports in the fixture (json, os).
        # Total code_import links must equal internal imports only (1).
        count = self.conn.execute(
            "SELECT COUNT(*) FROM links WHERE link_type='code_import'"
        ).fetchone()[0]
        self.assertEqual(count, 1)

    def test_no_external_package_files_registered(self):
        """External package names ('json', 'os') are not added to files table."""
        count = self.conn.execute(
            "SELECT COUNT(*) FROM files WHERE path IN ('json', 'os')"
        ).fetchone()[0]
        self.assertEqual(count, 0)


class TestNexusBridgeHubData(unittest.TestCase):
    """Hub scores from git_stats hotspots should be stored in frontmatter."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        _run_bridge(self.tmp)
        self.conn = sqlite3.connect(str(self.tmp / "_index.db"))

    def tearDown(self):
        self.conn.close()

    def test_bridge_stores_hub_data(self):
        """Files with git hotspot data have non-null frontmatter with change_count."""
        row = self.conn.execute(
            "SELECT frontmatter FROM files WHERE path='Handler/handler_trading_team.py'"
        ).fetchone()
        self.assertIsNotNone(row)
        self.assertIsNotNone(row[0])
        fm = json.loads(row[0])
        self.assertIn("change_count", fm)
        self.assertEqual(fm["change_count"], 42)

    def test_bridge_stores_hub_score(self):
        """hub_score field is present in frontmatter (fan-in count or git-based)."""
        row = self.conn.execute(
            "SELECT frontmatter FROM files WHERE path='Handler/handler_base.py'"
        ).fetchone()
        self.assertIsNotNone(row[0])
        fm = json.loads(row[0])
        # handler_base is imported by handler_trading_team — fan-in = 1
        self.assertIn("hub_score", fm)
        self.assertGreaterEqual(fm["hub_score"], 1)


class TestNexusBridgeIdempotent(unittest.TestCase):
    """Running the bridge twice must produce the same final state (no duplicates)."""

    def test_bridge_is_idempotent(self):
        tmp = Path(tempfile.mkdtemp())
        nexus_dir = _make_nexus_dir(tmp)
        db_path = _make_db(tmp)

        for _ in range(2):
            bridge = NexusBridge(nexus_dir=str(nexus_dir), db_path=str(db_path))
            bridge.run()

        conn = sqlite3.connect(str(db_path))
        file_count = conn.execute(
            "SELECT COUNT(*) FROM files WHERE source='code'"
        ).fetchone()[0]
        link_count = conn.execute(
            "SELECT COUNT(*) FROM links WHERE link_type='code_import'"
        ).fetchone()[0]
        conn.close()

        self.assertEqual(file_count, 2, "Duplicate module rows on second run")
        self.assertEqual(link_count, 1, "Duplicate link rows on second run")


class TestNexusBridgeMissingGitStats(unittest.TestCase):
    """Bridge should succeed even when git_stats.json has no matching hotspots."""

    def test_missing_git_stats_file(self):
        """Bridge runs without git_stats.json (uses fan-in hub_score only)."""
        tmp = Path(tempfile.mkdtemp())
        nexus_dir = tmp / ".nexus-map"
        raw_dir = nexus_dir / "raw"
        raw_dir.mkdir(parents=True)
        (raw_dir / "ast_nodes.json").write_text(json.dumps(MINIMAL_AST))
        # No git_stats.json
        db_path = _make_db(tmp)

        bridge = NexusBridge(nexus_dir=str(nexus_dir), db_path=str(db_path))
        bridge.run()  # Must not raise

        conn = sqlite3.connect(str(db_path))
        count = conn.execute("SELECT COUNT(*) FROM files WHERE source='code'").fetchone()[0]
        conn.close()
        self.assertEqual(count, 2)


if __name__ == "__main__":
    unittest.main()
