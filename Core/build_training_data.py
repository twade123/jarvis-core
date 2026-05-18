#!/usr/bin/env python3
"""
Training Data Builder — Extracts training examples from ALL Jarvis data sources.

Produces unified JSONL files in Alpaca and ShareGPT formats for fine-tuning.
Designed to run periodically (weekly) to grow the training dataset.

Sources (in priority order):
1. Opus corrections from vault (highest value — teacher corrections)
2. Pattern files (18K hand-crafted intent examples, 45 files)
3. Intelligence gateway logs (real routing decisions + outcomes)
4. Request logger (LLM call logs with outcomes)
5. Trading team execution logs (domain-specific)
6. Conversation history (real user interactions)

Usage:
    python build_training_data.py
    python build_training_data.py --format alpaca --output training/
    python build_training_data.py --since 2026-02-01 --min-quality 0.8
"""

import argparse
import glob
import json
import os
import sqlite3
import sys
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger("TrainingDataBuilder")
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

BASE_DIR = Path(__file__).parent.parent.resolve()
OUTPUT_DIR = BASE_DIR / "training_data"
INTELLIGENCE_DB = BASE_DIR / "Database" / "intelligence.db"
KNOWLEDGE_DIR = BASE_DIR / "knowledge"
PATTERN_DIR = BASE_DIR / "Core" / "intents"
INTENTS_DIR = BASE_DIR / "Intents"


class TrainingDataBuilder:
    """Build unified training datasets from all Jarvis data sources."""
    
    def __init__(self, output_dir: str = None, since: str = None):
        self.output_dir = Path(output_dir) if output_dir else OUTPUT_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.since = since  # ISO date filter
        self.examples = []
        self.stats = {"sources": {}, "total": 0, "by_type": {}}
    
    def build_all(self) -> Dict:
        """Run all extraction steps and produce output files."""
        logger.info("Building training data from all sources...")
        
        self._extract_opus_corrections()
        self._extract_intent_json_files()
        self._extract_pattern_intents()
        self._extract_gateway_logs()
        self._extract_request_logs()
        self._extract_vault_learnings()
        
        # Deduplicate
        seen = set()
        unique = []
        for ex in self.examples:
            key = (ex.get("input", "")[:100], ex.get("output", "")[:100])
            if key not in seen:
                seen.add(key)
                unique.append(ex)
        
        dedup_removed = len(self.examples) - len(unique)
        self.examples = unique
        self.stats["total"] = len(self.examples)
        self.stats["deduplicated"] = dedup_removed
        
        # Write outputs
        self._write_alpaca()
        self._write_sharegpt()
        self._write_jsonl()
        self._write_stats()
        
        logger.info(f"Done! {self.stats['total']} examples ({dedup_removed} duplicates removed)")
        return self.stats
    
    # ------------------------------------------------------------------
    # Source 1: Opus Corrections (highest value)
    # ------------------------------------------------------------------
    
    def _extract_opus_corrections(self):
        """Extract Opus QC corrections as training data."""
        training_dir = KNOWLEDGE_DIR / "collective" / "training-data"
        if not training_dir.exists():
            return
        
        count = 0
        for jsonl_file in sorted(training_dir.glob("opus-corrections-*.jsonl")):
            with open(jsonl_file) as f:
                for line in f:
                    try:
                        ex = json.loads(line)
                        if self.since and ex.get("timestamp", "") < self.since:
                            continue
                        
                        self.examples.append({
                            "instruction": f"You are {ex.get('agent', 'an AI assistant')}. Complete this task.",
                            "input": ex.get("task", ""),
                            "output": ex.get("opus_correction", ex.get("local_output", "")),
                            "source": "opus_correction",
                            "category": ex.get("category", "general"),
                            "quality": 1.0,  # Opus corrections are highest quality
                        })
                        count += 1
                    except json.JSONDecodeError:
                        pass
        
        self.stats["sources"]["opus_corrections"] = count
        logger.info(f"  Opus corrections: {count} examples")
    
    # ------------------------------------------------------------------
    # Source 2a: JSON Intent Files (45 files, ~18K examples)
    # ------------------------------------------------------------------
    
    def _extract_intent_json_files(self):
        """Extract intent examples from Intents/*.json files."""
        if not INTENTS_DIR.exists():
            logger.info(f"  Intents dir not found: {INTENTS_DIR}")
            return
        
        count = 0
        for json_file in sorted(INTENTS_DIR.glob("intents_*.json")):
            try:
                # Category from filename: intents_weather.json → weather
                category = json_file.stem.replace("intents_", "")
                handler = f"handler_{category}"
                
                with open(json_file) as f:
                    intents = json.load(f)
                
                for intent_name, intent_data in intents.items():
                    examples = intent_data.get("examples", [])
                    actions = intent_data.get("actions", [])
                    description = intent_data.get("description", "")
                    
                    # Each example phrase is a training example
                    for example in examples:
                        if isinstance(example, str) and len(example) > 3:
                            self.examples.append({
                                "instruction": "Classify this user request. Return the handler and intent.",
                                "input": example,
                                "output": json.dumps({
                                    "handler": handler,
                                    "intent": intent_name,
                                    "category": category,
                                    "description": description[:100],
                                }),
                                "source": "intent_json",
                                "category": category,
                                "quality": 0.95,  # hand-crafted, high quality
                            })
                            count += 1
                    
                    # Actions as additional examples
                    for action in actions:
                        if isinstance(action, str) and len(action) > 3:
                            self.examples.append({
                                "instruction": "Classify this user request. Return the handler and intent.",
                                "input": action,
                                "output": json.dumps({
                                    "handler": handler,
                                    "intent": intent_name,
                                    "category": category,
                                }),
                                "source": "intent_json_action",
                                "category": category,
                                "quality": 0.85,
                            })
                            count += 1
                            
            except (json.JSONDecodeError, Exception) as e:
                logger.debug(f"Error processing {json_file}: {e}")
        
        self.stats["sources"]["intent_json"] = count
        logger.info(f"  Intent JSON files: {count} examples from {len(list(INTENTS_DIR.glob('intents_*.json')))} files")
    
    # ------------------------------------------------------------------
    # Source 2b: Pattern Files (hand-crafted intents)
    # ------------------------------------------------------------------
    
    def _extract_pattern_intents(self):
        """Extract intent classification examples from pattern files."""
        if not PATTERN_DIR.exists():
            logger.info(f"  Pattern dir not found: {PATTERN_DIR}")
            return
        
        count = 0
        for pattern_file in sorted(PATTERN_DIR.glob("*.py")):
            try:
                # Pattern files contain lists of example phrases per intent
                with open(pattern_file) as f:
                    content = f.read()
                
                # Extract category from filename
                category = pattern_file.stem.replace("_intents", "").replace("_patterns", "")
                
                # Find pattern dictionaries — they look like:
                # {"label": "INTENT_NAME", "pattern": [{"LOWER": "word"}]}
                # or text examples in lists
                import ast
                try:
                    tree = ast.parse(content)
                    for node in ast.walk(tree):
                        if isinstance(node, ast.Dict):
                            # Try to extract label/pattern pairs
                            keys = [getattr(k, 'value', None) or getattr(k, 's', None) for k in node.keys if hasattr(k, 'value') or hasattr(k, 's')]
                            if 'label' in keys or 'intent' in keys:
                                pass  # Complex extraction — skip for now
                        
                        elif isinstance(node, ast.List):
                            # Lists of example strings
                            for elt in node.elts:
                                if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                                    text = elt.value
                                    if len(text) > 5 and len(text) < 200:
                                        self.examples.append({
                                            "instruction": "Classify this user request into a handler category.",
                                            "input": text,
                                            "output": json.dumps({"handler": f"handler_{category}", "category": category}),
                                            "source": "pattern_file",
                                            "category": category,
                                            "quality": 0.9,
                                        })
                                        count += 1
                except SyntaxError:
                    pass
                    
            except Exception as e:
                logger.debug(f"Error processing {pattern_file}: {e}")
        
        self.stats["sources"]["pattern_intents"] = count
        logger.info(f"  Pattern intents: {count} examples")
    
    # ------------------------------------------------------------------
    # Source 3: Intelligence Gateway Logs
    # ------------------------------------------------------------------
    
    def _extract_gateway_logs(self):
        """Extract successful routing decisions from gateway_log."""
        if not INTELLIGENCE_DB.exists():
            return
        
        count = 0
        try:
            conn = sqlite3.connect(str(INTELLIGENCE_DB))
            conn.row_factory = sqlite3.Row
            
            query = """
                SELECT request_text, handler, intent, category, confidence, gate, outcome
                FROM gateway_log 
                WHERE confidence >= 0.7 AND handler IS NOT NULL
            """
            params = []
            if self.since:
                query += " AND timestamp >= ?"
                params.append(self.since)
            
            for row in conn.execute(query, params).fetchall():
                outcome = json.loads(row["outcome"]) if row["outcome"] else {}
                success = outcome.get("success", True)  # assume success if no outcome recorded
                
                if not success:
                    continue  # skip failed routes
                
                self.examples.append({
                    "instruction": "Route this user request to the appropriate handler.",
                    "input": row["request_text"],
                    "output": json.dumps({
                        "handler": row["handler"],
                        "intent": row["intent"],
                        "category": row["category"],
                    }),
                    "source": "gateway_log",
                    "category": row["category"] or "unknown",
                    "quality": min(1.0, row["confidence"] + 0.1),  # boost for confirmed success
                })
                count += 1
            
            conn.close()
        except Exception as e:
            logger.warning(f"Error extracting gateway logs: {e}")
        
        self.stats["sources"]["gateway_logs"] = count
        logger.info(f"  Gateway logs: {count} examples")
    
    # ------------------------------------------------------------------
    # Source 4: Request Logger (LLM call logs)
    # ------------------------------------------------------------------
    
    def _extract_request_logs(self):
        """Extract from Handler/modules/request_logger's database."""
        request_log_db = BASE_DIR / "Database" / "intelligence.db"
        if not request_log_db.exists():
            return
        
        count = 0
        try:
            conn = sqlite3.connect(str(request_log_db))
            conn.row_factory = sqlite3.Row
            
            # request_log table from request_logger.py
            try:
                rows = conn.execute("""
                    SELECT request_text, intent_classified, handler_routed, 
                           outcome, response_text
                    FROM request_log 
                    WHERE outcome = 'success' AND request_text IS NOT NULL
                    LIMIT 5000
                """).fetchall()
                
                for row in rows:
                    if row["request_text"] and row["response_text"]:
                        self.examples.append({
                            "instruction": "Respond to this user request helpfully.",
                            "input": row["request_text"][:500],
                            "output": row["response_text"][:2000],
                            "source": "request_log",
                            "category": row["intent_classified"] or "general",
                            "quality": 0.7,
                        })
                        count += 1
            except sqlite3.OperationalError:
                pass  # table doesn't exist yet
            
            conn.close()
        except Exception as e:
            logger.debug(f"Error extracting request logs: {e}")
        
        self.stats["sources"]["request_logs"] = count
        logger.info(f"  Request logs: {count} examples")
    
    # ------------------------------------------------------------------
    # Source 5: Vault Learnings
    # ------------------------------------------------------------------
    
    def _extract_vault_learnings(self):
        """Extract agent learnings as domain knowledge examples."""
        agents_dir = KNOWLEDGE_DIR / "agents"
        if not agents_dir.exists():
            return
        
        count = 0
        for agent_dir in sorted(agents_dir.iterdir()):
            if not agent_dir.is_dir():
                continue
            
            learnings_file = agent_dir / "learnings.md"
            if not learnings_file.exists():
                continue
            
            content = learnings_file.read_text()
            # Extract individual learning entries
            sections = content.split("\n## ")[1:]  # skip header
            
            for section in sections:
                lines = section.strip().split("\n")
                if not lines:
                    continue
                
                summary = lines[0]
                body = "\n".join(lines[1:])
                
                if "No learnings recorded yet" in summary:
                    continue
                
                self.examples.append({
                    "instruction": f"As {agent_dir.name}, apply your learnings to analyze this situation.",
                    "input": f"Context: {summary}",
                    "output": body[:1000],
                    "source": "vault_learnings",
                    "category": agent_dir.name,
                    "quality": 0.8,
                })
                count += 1
        
        self.stats["sources"]["vault_learnings"] = count
        logger.info(f"  Vault learnings: {count} examples")
    
    # ------------------------------------------------------------------
    # Output Writers
    # ------------------------------------------------------------------
    
    def _write_alpaca(self):
        """Write Alpaca format (instruction/input/output)."""
        path = self.output_dir / "training_alpaca.jsonl"
        with open(path, 'w') as f:
            for ex in self.examples:
                f.write(json.dumps({
                    "instruction": ex["instruction"],
                    "input": ex["input"],
                    "output": ex["output"],
                }) + "\n")
        logger.info(f"  Written: {path} ({len(self.examples)} examples)")
    
    def _write_sharegpt(self):
        """Write ShareGPT format (conversations)."""
        path = self.output_dir / "training_sharegpt.jsonl"
        with open(path, 'w') as f:
            for ex in self.examples:
                conv = {
                    "conversations": [
                        {"from": "system", "value": ex["instruction"]},
                        {"from": "human", "value": ex["input"]},
                        {"from": "gpt", "value": ex["output"]},
                    ]
                }
                f.write(json.dumps(conv) + "\n")
        logger.info(f"  Written: {path}")
    
    def _write_jsonl(self):
        """Write raw format with all metadata."""
        path = self.output_dir / "training_full.jsonl"
        with open(path, 'w') as f:
            for ex in self.examples:
                f.write(json.dumps(ex) + "\n")
        logger.info(f"  Written: {path}")
    
    def _write_stats(self):
        """Write build statistics."""
        path = self.output_dir / "build_stats.json"
        self.stats["built_at"] = datetime.now().isoformat()
        self.stats["by_source"] = {}
        for ex in self.examples:
            src = ex.get("source", "unknown")
            self.stats["by_source"][src] = self.stats["by_source"].get(src, 0) + 1
        
        self.stats["by_category"] = {}
        for ex in self.examples:
            cat = ex.get("category", "unknown")
            self.stats["by_category"][cat] = self.stats["by_category"].get(cat, 0) + 1
        
        with open(path, 'w') as f:
            json.dump(self.stats, f, indent=2)
        logger.info(f"  Stats: {path}")


def main():
    parser = argparse.ArgumentParser(description="Build training data from Jarvis sources")
    parser.add_argument("--output", default=str(OUTPUT_DIR), help="Output directory")
    parser.add_argument("--since", default=None, help="Only include data after this date (ISO)")
    parser.add_argument("--format", default="all", choices=["all", "alpaca", "sharegpt"])
    args = parser.parse_args()
    
    builder = TrainingDataBuilder(output_dir=args.output, since=args.since)
    stats = builder.build_all()
    
    print(f"\n{'='*50}")
    print(f"Training data built: {stats['total']} examples")
    for source, count in stats.get("sources", {}).items():
        print(f"  {source}: {count}")
    print(f"  Duplicates removed: {stats.get('deduplicated', 0)}")
    print(f"Output: {args.output}")


if __name__ == "__main__":
    main()
