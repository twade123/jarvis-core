"""
NexusBridge — imports code dependency data from .nexus-map/ into _index.db.

Data sources:
  .nexus-map/raw/ast_nodes.json  — Module/Class nodes + import edges
  .nexus-map/raw/git_stats.json  — hotspot change counts (optional)

What gets written:
  files table  — one row per Module node, source='code', file_type='code'
  links table  — internal import edges as link_type='code_import'

The bridge is idempotent: re-running overwrites file rows and replaces
all code_import links rather than appending duplicates.
"""

import json
import logging
import sqlite3
from collections import defaultdict
from pathlib import Path

logger = logging.getLogger(__name__)


class NexusBridge:
    """Read Nexus-skills AST output and populate _index.db with code nodes/edges."""

    DEFAULT_NEXUS_DIR = "~/Jarvis/.nexus-map"
    DEFAULT_DB_PATH = "~/Jarvis/knowledge/_index.db"

    def __init__(self, nexus_dir: str = None, db_path: str = None):
        self.nexus_dir = Path(nexus_dir or self.DEFAULT_NEXUS_DIR)
        self.db_path = Path(db_path or self.DEFAULT_DB_PATH)

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def run(self) -> dict:
        """Execute the full import pipeline and return a summary dict."""
        logger.info("[NexusBridge] Starting import from %s", self.nexus_dir)

        ast_data = self._load_ast_nodes()
        git_data = self._load_git_stats()

        module_nodes = [n for n in ast_data.get("nodes", []) if n.get("type") == "Module"]
        all_node_ids = {n["id"] for n in ast_data.get("nodes", [])}
        import_edges = [e for e in ast_data.get("edges", []) if e.get("type") == "imports"]

        # Internal imports: both source and target are project node IDs
        internal_edges = [
            e for e in import_edges
            if e["source"] in all_node_ids and e["target"] in all_node_ids
        ]

        # fan-in count: how many internal imports point at each node id
        fan_in: dict[str, int] = defaultdict(int)
        for e in internal_edges:
            fan_in[e["target"]] += 1

        # hotspot map: path → change count
        hotspot_map: dict[str, int] = {}
        for h in git_data.get("hotspots", []):
            if "path" in h and "changes" in h:
                hotspot_map[h["path"]] = h["changes"]

        conn = sqlite3.connect(str(self.db_path))
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=30000")

            files_upserted = self._upsert_module_files(
                conn, module_nodes, fan_in, hotspot_map
            )
            # Build id → db file_id mapping after upsert
            id_to_file_id = self._build_id_map(conn, module_nodes)
            links_inserted = self._replace_import_links(conn, internal_edges, id_to_file_id)

            conn.commit()
        finally:
            conn.close()

        summary = {
            "module_nodes": len(module_nodes),
            "files_upserted": files_upserted,
            "internal_edges": len(internal_edges),
            "links_inserted": links_inserted,
        }
        logger.info("[NexusBridge] Done: %s", summary)
        return summary

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------

    def _load_ast_nodes(self) -> dict:
        ast_path = self.nexus_dir / "raw" / "ast_nodes.json"
        if not ast_path.exists():
            raise FileNotFoundError(f"ast_nodes.json not found at {ast_path}")
        with open(ast_path, encoding="utf-8") as f:
            return json.load(f)

    def _load_git_stats(self) -> dict:
        git_path = self.nexus_dir / "raw" / "git_stats.json"
        if not git_path.exists():
            logger.warning("[NexusBridge] git_stats.json not found — skipping hotspot data")
            return {}
        with open(git_path, encoding="utf-8") as f:
            return json.load(f)

    # ------------------------------------------------------------------
    # Database operations
    # ------------------------------------------------------------------

    def _upsert_module_files(
        self,
        conn: sqlite3.Connection,
        module_nodes: list[dict],
        fan_in: dict[str, int],
        hotspot_map: dict[str, int],
    ) -> int:
        """Insert or replace Module nodes into the files table."""
        count = 0
        for node in module_nodes:
            path = node.get("path", "")
            if not path:
                continue

            node_id = node["id"]
            title = node.get("label", path.split("/")[-1])

            # Build frontmatter from available signals
            fm: dict = {
                "hub_score": fan_in.get(node_id, 0),
                "lines": node.get("lines", 0),
                "lang": node.get("lang", ""),
                "nexus_id": node_id,
            }
            if path in hotspot_map:
                fm["change_count"] = hotspot_map[path]
                fm["risk"] = "high" if hotspot_map[path] >= 20 else "medium"

            frontmatter_json = json.dumps(fm)

            conn.execute(
                """
                INSERT INTO files (path, title, file_type, source, frontmatter)
                VALUES (?, ?, 'code', 'code', ?)
                ON CONFLICT(path) DO UPDATE SET
                    title = excluded.title,
                    file_type = excluded.file_type,
                    source = excluded.source,
                    frontmatter = excluded.frontmatter,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (path, title, frontmatter_json),
            )
            count += 1

        return count

    def _build_id_map(
        self, conn: sqlite3.Connection, module_nodes: list[dict]
    ) -> dict[str, int]:
        """Return mapping of node_id → files.id for all registered modules."""
        path_to_id: dict[str, int] = {}
        rows = conn.execute("SELECT id, path FROM files WHERE source='code'").fetchall()
        for file_id, path in rows:
            path_to_id[path] = file_id

        id_map: dict[str, int] = {}
        for node in module_nodes:
            path = node.get("path", "")
            node_id = node.get("id", "")
            if path and node_id and path in path_to_id:
                id_map[node_id] = path_to_id[path]

        return id_map

    def _replace_import_links(
        self,
        conn: sqlite3.Connection,
        internal_edges: list[dict],
        id_to_file_id: dict[str, int],
    ) -> int:
        """Delete existing code_import links then insert current set."""
        conn.execute("DELETE FROM links WHERE link_type='code_import'")

        count = 0
        for edge in internal_edges:
            src_id = id_to_file_id.get(edge["source"])
            tgt_id = id_to_file_id.get(edge["target"])
            if src_id is None or tgt_id is None:
                continue

            # Resolve target path from file_id
            tgt_path_row = conn.execute(
                "SELECT path FROM files WHERE id=?", (tgt_id,)
            ).fetchone()
            if not tgt_path_row:
                continue

            conn.execute(
                """
                INSERT INTO links (source_file_id, target_path, target_file_id, link_type)
                VALUES (?, ?, ?, 'code_import')
                """,
                (src_id, tgt_path_row[0], tgt_id),
            )
            count += 1

        return count


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    """Run the bridge with defaults and print a summary."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    bridge = NexusBridge()
    summary = bridge.run()
    print("\nNexusBridge import complete:")
    for key, val in summary.items():
        print(f"  {key}: {val:,}")


if __name__ == "__main__":
    main()
