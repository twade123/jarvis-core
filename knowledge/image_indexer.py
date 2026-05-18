"""
Image Indexer — Builds and maintains the image_catalog in the vault's _index.db.

Indexes curated teaching images, pattern reference images, and user-submitted
annotated charts. NOT bulk training/live images.

Usage:
    python3 knowledge/image_indexer.py           # Full rebuild
    python3 knowledge/image_indexer.py --stats    # Show catalog stats
"""

import json
import os
import re
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

# Paths
VAULT_DB = os.path.join(os.path.dirname(__file__), "_index.db")
BASE_DIR = os.path.dirname(os.path.dirname(__file__))  # Jarvis root
TEACHING_DIR = os.path.join(BASE_DIR, "Forex Trading Team", "Data", "charts", "teaching")
PATTERNS_DIR = os.path.join(TEACHING_DIR, "patterns")
ANNOTATIONS_DIR = os.path.join(BASE_DIR, "Forex Trading Team", "Data", "charts", "user_annotations")
LABELED_DIR = os.path.join(BASE_DIR, "Forex Trading Team", "Data", "charts", "labeled")
MANIFEST_PATH = os.path.join(ANNOTATIONS_DIR, "manifest.json")

# Teaching image definitions from vision_validator.py
TEACHING_DEFINITIONS = [
    {
        "file": "tim_teach_1.png",
        "pair": "AUD_USD",
        "direction": "SELL",
        "label": "TRADE",
        "setup_type": "fan_expansion",
        "fan_state": "bearish_ordered",
        "bb_state": "expanding",
        "pattern_name": None,
        "description": "TRADE EXAMPLE — AUD_USD: Green zone shows fan opening wide, BBs expanding. Clean unmistakable expansion. THIS is what a valid entry looks like.",
    },
    {
        "file": "tim_teach_2.png",
        "pair": "GBP_USD",
        "direction": "SELL",
        "label": "TRADE",
        "setup_type": "fan_expansion",
        "fan_state": "bearish_ordered",
        "bb_state": "expanding",
        "pattern_name": None,
        "description": "TRADE EXAMPLE — GBP_USD: Clear downward expansion after cross. EMAs separating in order, BBs widening. Obvious trend.",
    },
    {
        "file": "trade_364_USD_JPY_SHORT_WIN_+190p.png",
        "pair": "USD_JPY",
        "direction": "SELL",
        "label": "TRADE",
        "setup_type": "fan_expansion",
        "fan_state": "bearish_ordered",
        "bb_state": "expanding",
        "pattern_name": None,
        "pips_result": 190.0,
        "description": "TRADE EXAMPLE — USD_JPY SHORT +190 pips: Perfect expansion. Fan opens wide, BBs expand, candles drop cleanly.",
    },
    {
        "file": "trade_311_EUR_JPY_LONG_WIN_+93p.png",
        "pair": "EUR_JPY",
        "direction": "BUY",
        "label": "TRADE",
        "setup_type": "fan_expansion",
        "fan_state": "bullish_ordered",
        "bb_state": "expanding",
        "pattern_name": None,
        "pips_result": 93.0,
        "description": "TRADE EXAMPLE — EUR_JPY LONG +93 pips: Bullish expansion. EMAs separating upward, BBs confirming.",
    },
    {
        "file": "tim_teach_3.png",
        "pair": "EUR_CHF",
        "direction": None,
        "label": "SKIP",
        "setup_type": "no_setup",
        "fan_state": "mixed",
        "bb_state": "contracting",
        "pattern_name": None,
        "description": "SKIP EXAMPLE — EUR_CHF: Flat/contracting fan. No expansion. EMAs converging, BBs tight. Nothing is happening.",
    },
    {
        "file": "tim_teach_4.png",
        "pair": "EUR_USD",
        "direction": None,
        "label": "SKIP",
        "setup_type": "exhausted_move",
        "fan_state": "mixed",
        "bb_state": "contracting",
        "pattern_name": None,
        "description": "SKIP EXAMPLE — EUR_USD: Fan peaked then contracting. BBs tightening. Move already happened. Too late.",
    },
    {
        "file": "trade_338_GBP_JPY_SHORT_LOSS_-74p.png",
        "pair": "GBP_JPY",
        "direction": "SELL",
        "label": "SKIP",
        "setup_type": "false_signal",
        "fan_state": "tangled",
        "bb_state": "tight",
        "pattern_name": None,
        "pips_result": -74.0,
        "description": "SKIP EXAMPLE — GBP_JPY SHORT -74p LOSS: Fan never expanded. Entered on cross but EMAs stayed tangled.",
    },
    {
        "file": "trade_103_AUD_JPY_SHORT_LOSS_-34p.png",
        "pair": "AUD_JPY",
        "direction": "SELL",
        "label": "SKIP",
        "setup_type": "false_signal",
        "fan_state": "mixed",
        "bb_state": "tight",
        "pattern_name": None,
        "pips_result": -34.0,
        "description": "SKIP EXAMPLE — AUD_JPY SHORT -34p LOSS: Choppy. E100 too close. No clear separation.",
    },
    # Extended teaching images (from trading_cycle.py)
    {
        "file": "tim_teach_stage1_fan_entry.png",
        "pair": None,
        "direction": None,
        "label": "TRADE",
        "setup_type": "phase2_fan_entry",
        "fan_state": "bullish_ordered",
        "bb_state": "expanding",
        "pattern_name": None,
        "description": "TRADE EXAMPLE — Phase 2 fan entry. Early thesis entry when E21 crossed E55 and fan is starting to separate.",
    },
    {
        "file": "tim_teach_eurchf_bearish_fan_flip.png",
        "pair": "EUR_CHF",
        "direction": "SELL",
        "label": "TRADE",
        "setup_type": "fan_flip",
        "fan_state": "bearish_ordered",
        "bb_state": "expanding",
        "pattern_name": None,
        "description": "TRADE EXAMPLE — EUR_CHF: Bearish fan flip. EMAs reversed order from bullish to bearish with clean separation.",
    },
    {
        "file": "tim_teach_euraud_phase25_e100_retest.png",
        "pair": "EUR_AUD",
        "direction": None,
        "label": "TRADE",
        "setup_type": "e100_retest",
        "fan_state": "bullish_ordered",
        "bb_state": "expanding",
        "pattern_name": None,
        "description": "TRADE EXAMPLE — EUR_AUD: Phase 2.5 E100 retest. Price pulled back to E100 after initial expansion. Primary entry signal.",
    },
    # Day 6 trade examples
    {
        "file": "d6_trade_01_EUR_USD_long_WIN.png",
        "pair": "EUR_USD",
        "direction": "BUY",
        "label": "TRADE",
        "setup_type": "fan_expansion",
        "fan_state": "bullish_ordered",
        "bb_state": "expanding",
        "pattern_name": None,
        "description": "TRADE EXAMPLE — EUR_USD LONG WIN: Day 6 confirmed bullish expansion trade.",
    },
    {
        "file": "d6_trade_03_EUR_USD_short_WIN.png",
        "pair": "EUR_USD",
        "direction": "SELL",
        "label": "TRADE",
        "setup_type": "fan_expansion",
        "fan_state": "bearish_ordered",
        "bb_state": "expanding",
        "pattern_name": None,
        "description": "TRADE EXAMPLE — EUR_USD SHORT WIN: Day 6 confirmed bearish expansion trade.",
    },
    {
        "file": "d6_trade_06_GBP_JPY_long_WIN.png",
        "pair": "GBP_JPY",
        "direction": "BUY",
        "label": "TRADE",
        "setup_type": "fan_expansion",
        "fan_state": "bullish_ordered",
        "bb_state": "expanding",
        "pattern_name": None,
        "description": "TRADE EXAMPLE — GBP_JPY LONG WIN: Day 6 confirmed bullish expansion.",
    },
    {
        "file": "d6_trade_16_GBP_JPY_short_WIN.png",
        "pair": "GBP_JPY",
        "direction": "SELL",
        "label": "TRADE",
        "setup_type": "fan_expansion",
        "fan_state": "bearish_ordered",
        "bb_state": "expanding",
        "pattern_name": None,
        "description": "TRADE EXAMPLE — GBP_JPY SHORT WIN: Day 6 confirmed bearish expansion.",
    },
    # Loss examples for teaching
    {
        "file": "trade_633_EUR_AUD_BUY_LOSS_-3p.png",
        "pair": "EUR_AUD",
        "direction": "BUY",
        "label": "SKIP",
        "setup_type": "false_signal",
        "fan_state": "mixed",
        "bb_state": "tight",
        "pattern_name": None,
        "pips_result": -3.0,
        "description": "SKIP EXAMPLE — EUR_AUD BUY -3p LOSS: Marginal setup that failed. Insufficient fan expansion.",
    },
    {
        "file": "trade_641_EUR_AUD_BUY_LOSS_-5p.png",
        "pair": "EUR_AUD",
        "direction": "BUY",
        "label": "SKIP",
        "setup_type": "false_signal",
        "fan_state": "mixed",
        "bb_state": "tight",
        "pattern_name": None,
        "pips_result": -5.0,
        "description": "SKIP EXAMPLE — EUR_AUD BUY -5p LOSS: Another marginal EUR_AUD setup. Fan not expanding enough.",
    },
]

# Pattern image definitions
PATTERN_DEFINITIONS = [
    {"file": "pattern_01_hammer_pin_bar.png", "pattern_name": "hammer", "setup_type": "S1",
     "description": "Pattern reference — Hammer/Pin Bar: Long lower wick rejection at support. Bullish reversal signal."},
    {"file": "pattern_02_engulfing_bullish.png", "pattern_name": "engulfing_bullish", "setup_type": "S2",
     "description": "Pattern reference — Bullish Engulfing: Large bullish candle completely engulfs prior bearish candle."},
    {"file": "pattern_03_engulfing_bearish.png", "pattern_name": "engulfing_bearish", "setup_type": "S2",
     "description": "Pattern reference — Bearish Engulfing: Large bearish candle completely engulfs prior bullish candle."},
    {"file": "pattern_04_morning_evening_star.png", "pattern_name": "morning_star", "setup_type": "S3",
     "description": "Pattern reference — Morning/Evening Star: 3-candle reversal. Big candle, small star, reversal candle."},
    {"file": "pattern_05_doji_extreme.png", "pattern_name": "doji", "setup_type": "S4",
     "description": "Pattern reference — Doji at Extremes: Open=Close at overbought/oversold. Indecision → reversal."},
    {"file": "pattern_06_ascending_triangle.png", "pattern_name": "ascending_triangle", "setup_type": "S17",
     "description": "Pattern reference — Ascending Triangle: Flat resistance + rising higher lows. Bullish breakout pattern."},
    {"file": "pattern_07_descending_triangle.png", "pattern_name": "descending_triangle", "setup_type": "S17",
     "description": "Pattern reference — Descending Triangle: Flat support + falling lower highs. Bearish breakdown pattern."},
    {"file": "pattern_08_channel_trading.png", "pattern_name": "channel", "setup_type": "S7",
     "description": "Pattern reference — Channel Trading: Trend channel with inner waves. Buy at lower line, sell at upper."},
    {"file": "pattern_09_support_resistance_break.png", "pattern_name": "sr_break", "setup_type": "S8",
     "description": "Pattern reference — Support/Resistance Break: Range break with retest confirmation."},
    {"file": "pattern_10_bb_squeeze_breakout.png", "pattern_name": "bb_squeeze", "setup_type": "S12",
     "description": "Pattern reference — BB Squeeze Breakout: Bollinger Band compression then explosive expansion."},
    {"file": "pattern_11_momentum_divergence.png", "pattern_name": "divergence", "setup_type": "S14",
     "description": "Pattern reference — Momentum Divergence: Price makes new high/low but indicator disagrees. #1 reversal signal."},
    {"file": "pattern_12_fibonacci_channel.png", "pattern_name": "fibonacci", "setup_type": "S10",
     "description": "Pattern reference — Fibonacci Channel: Fibonacci retracement levels within trend channel."},
    {"file": "pattern_13_multi_pair_correlation.png", "pattern_name": "correlation", "setup_type": None,
     "description": "Reference — Multi-Pair Correlation: How correlated pairs move together. Risk management visual."},
]


def create_tables(conn):
    """Create image_catalog and image_fts tables."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS image_catalog (
            image_id INTEGER PRIMARY KEY,
            file_path TEXT NOT NULL,
            pair TEXT,
            timeframe TEXT DEFAULT 'M15',
            direction TEXT,
            label TEXT,
            setup_type TEXT,
            fan_state TEXT,
            bb_state TEXT,
            pattern_name TEXT,
            description TEXT NOT NULL,
            pips_result REAL,
            source TEXT NOT NULL,
            grade TEXT,
            linked_trade_id INTEGER,
            linked_outcome TEXT,
            tags TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Drop and recreate FTS to avoid content sync issues
    conn.execute("DROP TABLE IF EXISTS image_fts")
    conn.execute("""
        CREATE VIRTUAL TABLE image_fts USING fts5(
            description, tags, setup_type, pattern_name, pair,
            content='image_catalog', content_rowid='image_id'
        )
    """)
    conn.commit()


def rebuild_fts(conn):
    """Rebuild the FTS index from image_catalog."""
    conn.execute("DROP TABLE IF EXISTS image_fts")
    conn.execute("""
        CREATE VIRTUAL TABLE image_fts USING fts5(
            description, tags, setup_type, pattern_name, pair,
            content=image_catalog, content_rowid=image_id
        )
    """)
    conn.execute("""
        INSERT INTO image_fts(rowid, description, tags, setup_type, pattern_name, pair)
        SELECT image_id,
            COALESCE(description, ''),
            COALESCE(tags, ''),
            COALESCE(setup_type, ''),
            COALESCE(pattern_name, ''),
            COALESCE(pair, '')
        FROM image_catalog
    """)
    conn.commit()


def index_teaching_images(conn):
    """Index the curated teaching images with rich descriptions."""
    count = 0
    for defn in TEACHING_DEFINITIONS:
        file_path = os.path.join(TEACHING_DIR, defn["file"])
        if not os.path.exists(file_path):
            print(f"  WARN: Teaching image not found: {defn['file']}")
            continue

        tags_list = ["teaching"]
        if defn.get("label") == "TRADE":
            tags_list.append("trade_example")
        elif defn.get("label") == "SKIP":
            tags_list.append("skip_example")
        if defn.get("fan_state"):
            tags_list.append(defn["fan_state"])
        if defn.get("pips_result") is not None:
            tags_list.append("win" if defn["pips_result"] > 0 else "loss")

        conn.execute("""
            INSERT INTO image_catalog (file_path, pair, direction, label, setup_type,
                fan_state, bb_state, pattern_name, description, pips_result, source, tags)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'teaching', ?)
        """, (
            file_path,
            defn.get("pair"),
            defn.get("direction"),
            defn.get("label"),
            defn.get("setup_type"),
            defn.get("fan_state"),
            defn.get("bb_state"),
            defn.get("pattern_name"),
            defn["description"],
            defn.get("pips_result"),
            ",".join(tags_list),
        ))
        count += 1
    print(f"  Indexed {count} teaching images")
    return count


def index_pattern_images(conn):
    """Index the pattern reference images."""
    count = 0
    for defn in PATTERN_DEFINITIONS:
        file_path = os.path.join(PATTERNS_DIR, defn["file"])
        if not os.path.exists(file_path):
            print(f"  WARN: Pattern image not found: {defn['file']}")
            continue

        tags = f"pattern_reference,{defn['pattern_name']}"
        if defn.get("setup_type"):
            tags += f",{defn['setup_type']}"

        conn.execute("""
            INSERT INTO image_catalog (file_path, pair, direction, label, setup_type,
                pattern_name, description, source, tags)
            VALUES (?, NULL, NULL, 'REFERENCE', ?, ?, ?, 'pattern_reference', ?)
        """, (file_path, defn.get("setup_type"), defn["pattern_name"], defn["description"], tags))
        count += 1

    # Index chart_*.png files (generic chart references)
    for i in range(1, 11):
        file_path = os.path.join(PATTERNS_DIR, f"chart_{i}.png")
        if os.path.exists(file_path):
            conn.execute("""
                INSERT INTO image_catalog (file_path, label, description, source, tags)
                VALUES (?, 'REFERENCE', ?, 'pattern_reference', 'chart_reference,setup_example')
            """, (file_path, f"Setup reference chart {i} — example chart from visual knowledge base analysis."))
            count += 1

    print(f"  Indexed {count} pattern/chart reference images")
    return count


def index_user_annotations(conn):
    """Index user-submitted annotated charts from manifest.json."""
    if not os.path.exists(MANIFEST_PATH):
        print("  WARN: manifest.json not found")
        return 0

    with open(MANIFEST_PATH) as f:
        manifest = json.load(f)

    count = 0
    for entry in manifest:
        file_path = os.path.join(ANNOTATIONS_DIR, entry.get("image_file", ""))
        if not os.path.exists(file_path):
            continue

        pair = entry.get("pair", "")
        thesis = entry.get("thesis", "")
        notes = entry.get("notes", "")
        drawing_count = entry.get("drawing_count", 0)
        trade_id = entry.get("trade_id")

        description = f"User annotation — {pair} M15"
        if thesis:
            description += f": {thesis}"
        if notes and notes != "Voice-annotated chart submitted by Trevor on behalf of Tim":
            description += f". Notes: {notes}"
        description += f". {drawing_count} markups on chart."

        tags = f"user_annotation,{pair}"
        if thesis:
            # Extract keywords from thesis for tags
            for keyword in ["cross", "separation", "expansion", "retest", "divergence",
                           "fan", "bollinger", "squeeze", "breakout", "reversal"]:
                if keyword in thesis.lower():
                    tags += f",{keyword}"

        conn.execute("""
            INSERT INTO image_catalog (file_path, pair, timeframe, label, description,
                source, linked_trade_id, tags, created_at)
            VALUES (?, ?, 'M15', 'USER_ANNOTATION', ?, 'user_annotation', ?, ?, ?)
        """, (
            file_path, pair, description, trade_id, tags,
            entry.get("timestamp", datetime.now().isoformat()),
        ))
        count += 1

    print(f"  Indexed {count} user annotation images")
    return count


def index_labeled_outcomes(conn):
    """Selectively index labeled outcome images (WIN/LOSS with pips)."""
    if not os.path.isdir(LABELED_DIR):
        print("  WARN: labeled directory not found")
        return 0

    count = 0
    # Pattern: PAIR_direction_RESULT_pips_timestamp.png
    pattern = re.compile(r"^(\w+_\w+)_(buy|sell)_(WIN|LOSS)_([+-]?\d+)p_(\d+)\.png$")

    for fname in os.listdir(LABELED_DIR):
        match = pattern.match(fname)
        if not match:
            continue

        pair, direction, result, pips, _ = match.groups()
        pips_val = float(pips)
        direction_upper = "BUY" if direction == "buy" else "SELL"
        label = "WIN" if result == "WIN" else "LOSS"

        file_path = os.path.join(LABELED_DIR, fname)
        description = f"Trade outcome — {pair} {direction_upper} {result} {pips}p: Post-trade chart showing {'winning' if label == 'WIN' else 'losing'} setup."
        tags = f"labeled_outcome,{pair},{label.lower()},{direction}"

        conn.execute("""
            INSERT INTO image_catalog (file_path, pair, direction, label, description,
                pips_result, source, tags)
            VALUES (?, ?, ?, ?, ?, ?, 'labeled_outcome', ?)
        """, (file_path, pair, direction_upper, label, description, pips_val, tags))
        count += 1

    print(f"  Indexed {count} labeled outcome images")
    return count


def print_stats(conn):
    """Print catalog statistics."""
    total = conn.execute("SELECT COUNT(*) FROM image_catalog").fetchone()[0]
    print(f"\n=== Image Catalog Stats ===")
    print(f"Total images: {total}")

    by_source = conn.execute(
        "SELECT source, COUNT(*) FROM image_catalog GROUP BY source ORDER BY COUNT(*) DESC"
    ).fetchall()
    for source, count in by_source:
        print(f"  {source}: {count}")

    by_label = conn.execute(
        "SELECT label, COUNT(*) FROM image_catalog GROUP BY label ORDER BY COUNT(*) DESC"
    ).fetchall()
    print(f"\nBy label:")
    for label, count in by_label:
        print(f"  {label}: {count}")

    by_pair = conn.execute(
        "SELECT pair, COUNT(*) FROM image_catalog WHERE pair IS NOT NULL GROUP BY pair ORDER BY COUNT(*) DESC"
    ).fetchall()
    print(f"\nBy pair:")
    for pair, count in by_pair:
        print(f"  {pair}: {count}")


def main():
    if "--stats" in sys.argv:
        conn = sqlite3.connect(VAULT_DB, isolation_level=None)
        print_stats(conn)
        conn.close()
        return

    print("Building image catalog...")
    conn = sqlite3.connect(VAULT_DB, isolation_level=None)

    # Clear existing catalog
    conn.execute("DROP TABLE IF EXISTS image_fts")
    conn.execute("DROP TABLE IF EXISTS image_catalog")
    conn.commit()

    create_tables(conn)

    total = 0
    total += index_teaching_images(conn)
    total += index_pattern_images(conn)
    total += index_user_annotations(conn)
    total += index_labeled_outcomes(conn)

    conn.commit()
    rebuild_fts(conn)

    print(f"\nTotal: {total} images indexed")
    print_stats(conn)
    conn.close()


if __name__ == "__main__":
    main()
