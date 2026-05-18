"""
Image Vault — Query interface for the curated teaching image catalog.

Used by the validator to find relevant teaching/reference images based on
what it sees on a chart (setup type, pattern, fan state, direction, pair).

Usage:
    from knowledge.image_vault import ImageVault
    iv = ImageVault()
    images = iv.find_for_setup("fan_expansion", direction="SELL", pair="EUR_USD")
    images = iv.find_for_pattern("engulfing_bullish")
    images = iv.search("bearish fan expansion E100 retest")
"""

import os
import sqlite3
from typing import Dict, List, Optional

VAULT_DB = os.path.join(os.path.dirname(__file__), "_index.db")


class ImageVault:
    """Search the curated teaching image catalog."""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or VAULT_DB

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, isolation_level=None)
        conn.row_factory = sqlite3.Row
        return conn

    def find_for_setup(
        self,
        setup_type: str,
        direction: str = None,
        pair: str = None,
        label: str = None,
        limit: int = 3,
    ) -> List[Dict]:
        """Find teaching images matching a setup type.

        Args:
            setup_type: S1-S20, fan_expansion, e100_retest, etc.
            direction: BUY or SELL (optional filter)
            pair: EUR_USD, GBP_JPY, etc. (optional, prefers matching pair)
            label: TRADE, SKIP, REFERENCE (optional filter)
            limit: Max results

        Returns:
            List of dicts with image_id, file_path, description, and metadata
        """
        conn = self._get_conn()
        conditions = ["setup_type = ?"]
        params = [setup_type]

        if direction:
            conditions.append("(direction = ? OR direction IS NULL)")
            params.append(direction)
        if label:
            conditions.append("label = ?")
            params.append(label)

        where = " AND ".join(conditions)

        # Prefer matching pair, then any pair
        query = f"""
            SELECT *, CASE WHEN pair = ? THEN 1 ELSE 0 END AS pair_match
            FROM image_catalog
            WHERE {where}
            ORDER BY pair_match DESC, source ASC
            LIMIT ?
        """
        params.insert(0, pair or "")
        params.append(limit)

        rows = conn.execute(query, params).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def find_for_pattern(
        self,
        pattern_name: str,
        limit: int = 3,
    ) -> List[Dict]:
        """Find teaching images showing a specific candle/chart pattern.

        Args:
            pattern_name: hammer, engulfing_bullish, morning_star, doji,
                          ascending_triangle, bb_squeeze, divergence, etc.
            limit: Max results
        """
        conn = self._get_conn()
        rows = conn.execute("""
            SELECT * FROM image_catalog
            WHERE pattern_name = ? OR tags LIKE ?
            ORDER BY source ASC
            LIMIT ?
        """, (pattern_name, f"%{pattern_name}%", limit)).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def search(self, query: str, limit: int = 5) -> List[Dict]:
        """Full-text search across all indexed image descriptions.

        Args:
            query: Natural language search (e.g., "bearish fan expansion EUR_USD")
            limit: Max results
        """
        conn = self._get_conn()
        try:
            rows = conn.execute("""
                SELECT ic.* FROM image_fts
                JOIN image_catalog ic ON image_fts.rowid = ic.image_id
                WHERE image_fts MATCH ?
                LIMIT ?
            """, (query, limit)).fetchall()
        except Exception:
            # Fallback to LIKE search if FTS query syntax is invalid
            words = query.split()
            conditions = " AND ".join(
                ["(description LIKE ? OR tags LIKE ?)"] * len(words)
            )
            params = []
            for w in words:
                params.extend([f"%{w}%", f"%{w}%"])
            params.append(limit)
            rows = conn.execute(f"""
                SELECT * FROM image_catalog
                WHERE {conditions}
                LIMIT ?
            """, params).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_teaching_images(
        self,
        label: str = None,
        limit: int = 8,
    ) -> List[Dict]:
        """Get teaching images (the curated set for vision validator).

        Args:
            label: TRADE or SKIP to filter, None for all
            limit: Max results
        """
        conn = self._get_conn()
        if label:
            rows = conn.execute("""
                SELECT * FROM image_catalog
                WHERE source = 'teaching' AND label = ?
                ORDER BY image_id
                LIMIT ?
            """, (label, limit)).fetchall()
        else:
            rows = conn.execute("""
                SELECT * FROM image_catalog
                WHERE source = 'teaching'
                ORDER BY image_id
                LIMIT ?
            """, (limit,)).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_user_chart_feedback(
        self,
        user_id: int = None,
        pair: str = None,
    ) -> List[Dict]:
        """Get user's annotated charts with linked outcomes.

        Returns charts with any linked trade outcomes for feedback/grading.
        """
        conn = self._get_conn()
        conditions = ["source = 'user_annotation'"]
        params = []

        if pair:
            conditions.append("pair = ?")
            params.append(pair)

        where = " AND ".join(conditions)
        rows = conn.execute(f"""
            SELECT * FROM image_catalog
            WHERE {where}
            ORDER BY created_at DESC
        """, params).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_stats(self) -> Dict:
        """Get catalog statistics."""
        conn = self._get_conn()
        stats = {
            "total": conn.execute("SELECT COUNT(*) FROM image_catalog").fetchone()[0],
            "by_source": dict(conn.execute(
                "SELECT source, COUNT(*) FROM image_catalog GROUP BY source"
            ).fetchall()),
            "by_label": dict(conn.execute(
                "SELECT label, COUNT(*) FROM image_catalog GROUP BY label"
            ).fetchall()),
        }
        conn.close()
        return stats
