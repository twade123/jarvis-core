#!/usr/bin/env python3
"""
Knowledge Distillation Engine
=============================
Runs downloaded models against real tasks, has Opus judge the outputs,
and produces training data to fine-tune trevor-domain (our custom model).

Pipeline:
  1. Load task bank (real requests from gateway_log, training data, vault)
  2. Send each task to all teacher models (parallel via MLX servers)
  3. Opus scores and picks best answer + explains why
  4. Best answers → training JSONL (Alpaca format for MLX LoRA)
  5. Periodic fine-tune trigger when enough new data accumulates

Usage:
  python distillation_engine.py --run          # Run distillation batch
  python distillation_engine.py --status       # Check progress
  python distillation_engine.py --finetune     # Trigger fine-tune from accumulated data
"""

import json
import os
import sys
import time
import sqlite3
import asyncio
import aiohttp
from datetime import datetime, timezone
from pathlib import Path
import re
from typing import Optional

# Paths
JARVIS_ROOT = Path(__file__).parent.parent
DB_DIR = JARVIS_ROOT / "Database" / "v2"
TRAINING_DIR = JARVIS_ROOT / "training_data"
DISTILL_DIR = TRAINING_DIR / "distillation"
DISTILL_DB = DISTILL_DIR / "distillation.db"
TASK_BANK = DISTILL_DIR / "task_bank.jsonl"
OUTPUT_FILE = DISTILL_DIR / "distilled_training.jsonl"
STATS_FILE = DISTILL_DIR / "distill_stats.json"

# Model config — MLX backend (updated Phase 7B, Mar 2026)
# MLX servers managed by scripts/mlx_servers.sh
MLX_SERVERS = {
    "CRO": {"port": 11500, "repo": "mlx-community/Qwen2.5-7B-Instruct-4bit"},
    "CTO": {"port": 11501, "repo": "mlx-community/DeepSeek-R1-Distill-Qwen-14B-4bit"},
    "CSO": {"port": 11502, "repo": "mlx-community/Qwen3.5-35B-A3B-4bit"},
    "CDO": {"port": 11503, "repo": "mlx-community/Qwen2.5-7B-Instruct-4bit"},
}
TEACHER_MODELS = {
    "mlx/CTO": {
        "role": "reasoning",
        "url": "http://localhost:11501/v1",
        "strengths": ["architecture", "logic", "debugging", "system design"],
        "weight": 1.0,
    },
    "mlx/CSO": {
        "role": "coding",
        "url": "http://localhost:11502/v1",
        "strengths": ["code generation", "strategy", "analysis", "MoE reasoning"],
        "weight": 1.0,
    },
    "mlx/CRO": {
        "role": "general",
        "url": "http://localhost:11500/v1",
        "strengths": ["routing", "classification", "summarization", "quick tasks"],
        "weight": 0.7,
    },
}
# MLX servers are the only backend — no Ollama fallback.
# GGUF pipeline (fuse_and_load_ollama.sh) kept as cold export for non-Apple deployment.

# Opus judge config
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
OPUS_MODEL = "claude-opus-4-20250514"

# Distillation config
BATCH_SIZE = 10           # Tasks per batch
MAX_TOKENS_TEACHER = 2048  # Max output per teacher
MAX_TOKENS_JUDGE = 1024    # Max output from Opus judge
FINETUNE_THRESHOLD = 500   # Trigger fine-tune after this many examples
COST_PER_JUDGE_CALL = 0.03  # Estimated Opus cost per judgment (~1K in + 1K out)


def init_db():
    """Create distillation tracking database."""
    DISTILL_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DISTILL_DB))
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_text TEXT NOT NULL,
            category TEXT,  -- coding, reasoning, trading, general
            source TEXT,    -- gateway_log, training_data, vault, manual
            created_at TEXT DEFAULT (datetime('now')),
            status TEXT DEFAULT 'pending',  -- pending, in_progress, complete, failed
            UNIQUE(task_text)
        );
        
        CREATE TABLE IF NOT EXISTS teacher_responses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER REFERENCES tasks(id),
            model_name TEXT NOT NULL,
            response TEXT,
            latency_ms INTEGER,
            created_at TEXT DEFAULT (datetime('now'))
        );
        
        CREATE TABLE IF NOT EXISTS judgments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER REFERENCES tasks(id),
            best_model TEXT,          -- Which teacher won
            best_response TEXT,       -- The winning response
            opus_reasoning TEXT,      -- Why Opus picked this one
            opus_improved TEXT,       -- Opus's own improved version (optional)
            scores JSON,             -- {"deepseek-r1:32b": 8, "qwen2.5-coder:32b": 9, ...}
            quality_tier TEXT,       -- excellent, good, acceptable, poor
            cost_usd REAL,
            created_at TEXT DEFAULT (datetime('now'))
        );
        
        CREATE TABLE IF NOT EXISTS finetune_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            examples_count INTEGER,
            base_model TEXT,
            output_model TEXT,
            started_at TEXT DEFAULT (datetime('now')),
            completed_at TEXT,
            status TEXT DEFAULT 'running',
            metrics JSON
        );
        
        CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
        CREATE INDEX IF NOT EXISTS idx_tasks_category ON tasks(category);
        CREATE INDEX IF NOT EXISTS idx_judgments_quality ON judgments(quality_tier);
    """)
    conn.close()


def load_task_bank(conn: sqlite3.Connection, limit: int = 100) -> int:
    """
    Populate task bank from multiple sources:
    1. gateway_log — real user requests
    2. existing training data — intent examples  
    3. knowledge vault — documented patterns
    4. coding tasks from handler/module code
    """
    loaded = 0
    
    # Source 1: Gateway log (real requests)
    intel_db = DB_DIR / "intelligence.db"
    if intel_db.exists():
        try:
            src = sqlite3.connect(str(intel_db))
            rows = src.execute("""
                SELECT DISTINCT request_text FROM gateway_log 
                WHERE request_text IS NOT NULL 
                AND length(request_text) > 20
                ORDER BY created_at DESC LIMIT ?
            """, (limit,)).fetchall()
            for (text,) in rows:
                try:
                    conn.execute(
                        "INSERT OR IGNORE INTO tasks (task_text, category, source) VALUES (?, ?, ?)",
                        (text, classify_task(text), "gateway_log")
                    )
                    loaded += 1
                except sqlite3.IntegrityError:
                    pass
            src.close()
        except Exception as e:
            print(f"  Warning: gateway_log load failed: {e}")
    
    # Source 2: Existing training data
    training_file = TRAINING_DIR / "training_alpaca.jsonl"
    if training_file.exists():
        with open(training_file) as f:
            for i, line in enumerate(f):
                if i >= limit:
                    break
                try:
                    item = json.loads(line)
                    instruction = item.get("instruction", "")
                    if len(instruction) > 20:
                        conn.execute(
                            "INSERT OR IGNORE INTO tasks (task_text, category, source) VALUES (?, ?, ?)",
                            (instruction, classify_task(instruction), "training_data")
                        )
                        loaded += 1
                except (json.JSONDecodeError, sqlite3.IntegrityError):
                    pass
    
    # Source 3: Generate coding tasks from our actual codebase
    coding_tasks = generate_coding_tasks()
    for task in coding_tasks[:limit]:
        try:
            conn.execute(
                "INSERT OR IGNORE INTO tasks (task_text, category, source) VALUES (?, ?, ?)",
                (task, "coding", "generated")
            )
            loaded += 1
        except sqlite3.IntegrityError:
            pass
    
    # Source 4: Trading-specific tasks
    trading_tasks = generate_trading_tasks()
    for task in trading_tasks[:limit]:
        try:
            conn.execute(
                "INSERT OR IGNORE INTO tasks (task_text, category, source) VALUES (?, ?, ?)",
                (task, "trading", "generated")
            )
            loaded += 1
        except sqlite3.IntegrityError:
            pass
    
    conn.commit()
    return loaded


def classify_task(text: str) -> str:
    """Quick classification of task type."""
    text_lower = text.lower()
    if any(w in text_lower for w in ["code", "function", "class", "import", "debug", "refactor", "python", "script"]):
        return "coding"
    elif any(w in text_lower for w in ["trade", "forex", "oanda", "ema", "rsi", "confluence", "backtest"]):
        return "trading"
    elif any(w in text_lower for w in ["architecture", "design", "system", "database", "schema", "pipeline"]):
        return "reasoning"
    return "general"


def generate_coding_tasks() -> list:
    """Generate coding tasks based on our actual codebase patterns."""
    return [
        # Handler pattern tasks
        "Write a Python handler class that inherits from BaseHandler with handle() method, input validation, and HandlerResult return type.",
        "Refactor this function to use the LLMRouter abstraction so it works with both Anthropic API and local Ollama models.",
        "Write a SQLite database migration that adds a new column with a default value and backfills existing rows.",
        "Create a Python async function that calls the OANDA API to fetch candlestick data for EUR_USD on the H1 timeframe.",
        "Write error handling for an API call that retries 3 times with exponential backoff and logs failures to SQLite.",
        "Build a Python class that manages model loading/unloading for Ollama, tracking memory usage and swapping models when needed.",
        "Write a confluence scoring function that takes indicator values (RSI, Stochastic, Bollinger Bands, EMA separation) and returns a score 0-100.",
        "Create a FastAPI endpoint that serves trading dashboard data from SQLite with proper error handling and CORS.",
        "Write a Python decorator that logs function execution time and arguments to a SQLite table.",
        "Build a workspace provisioner that clones agent configurations and creates isolated database tables per user.",
        "Write a knowledge vault indexer that reads markdown files with YAML frontmatter and builds an FTS5 search index.",
        "Create a training data formatter that converts conversation logs into Alpaca JSONL format for fine-tuning.",
        "Write a graduation system that tracks model performance scores and automatically promotes/demotes based on thresholds.",
        "Build a sequential deliberation protocol where multiple LLM agents take turns responding, each reading previous responses.",
        "Write a resource manager that monitors system RAM and GPU memory, queuing model loads when resources are scarce.",
        # Bug fix patterns
        "Fix a circular import in Python where module A imports from module B and module B imports from module A.",
        "Debug why a SQLite query returns 0 rows when the data exists — the column uses natural language names but the query uses codes.",
        "Fix a race condition where two async tasks write to the same SQLite database simultaneously.",
        # Testing patterns
        "Write unit tests for a trade validator that checks confluence score, session timing, and risk parameters.",
        "Create an integration test that verifies the full trading pipeline: scout → analyst → validator → orchestrator.",
    ]


def generate_trading_tasks() -> list:
    """Generate trading-domain specific tasks."""
    return [
        "Analyze EUR_USD H1 candles: EMA(21) at 1.0850, EMA(55) at 1.0830, RSI(14) at 28, Stochastic(14,3,3) at 15/20. Is this a valid mean reversion entry?",
        "Given a fan state of 'decelerating' with velocity 0.004%/bar and trend_health 45, should we look for counter-trend setups?",
        "The validator received a BEAR thesis but the scout found a BUY signal with confluence score 78. What's wrong and how should it be handled?",
        "Calculate position size for EUR_USD with $100K account, 1% risk per trade, stop loss at 25 pips, and current spread of 1.2 pips.",
        "Write the logic for a dynamic exit system that monitors EMA separation velocity and Bollinger Band width to determine when to close a trade.",
        "Evaluate this trade setup: S15_RANGING regime, RSI divergence detected, ADX at 22, London session, BB width 0.0045. Pass or fail?",
        "Design a watch condition that triggers when EUR_USD RSI crosses below 30 while EMA fan is decelerating and session is London-NY overlap.",
        "Explain why a trade with 88% historical win rate and 9000+ sample size should still be rejected by the validator.",
        "Compare the risk profile of trading during Asian session vs London-NY overlap for mean reversion setups on GBP_USD.",
        "Write a market narrative for: EMA fan expanding, velocity 0.008%/bar, trend_health 85, E100 showing rejection candle pattern.",
    ]


async def query_teacher(session: aiohttp.ClientSession, model: str, task: str) -> dict:
    """Send a task to a local MLX model via OpenAI-compatible endpoint."""
    start = time.time()
    
    # Get the MLX server URL for this model
    model_config = TEACHER_MODELS.get(model, {})
    base_url = model_config.get("url", "http://localhost:11502/v1")
    
    try:
        async with session.post(
            f"{base_url}/chat/completions",
            json={
                "messages": [
                    {"role": "system", "content": "You are a helpful AI assistant. Provide clear, accurate, and well-structured responses."},
                    {"role": "user", "content": task}
                ],
                "max_tokens": MAX_TOKENS_TEACHER,
                "temperature": 0.7,
            },
            timeout=aiohttp.ClientTimeout(total=300)  # 5 min max per model
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                # Extract response from OpenAI-compatible format
                choices = data.get("choices", [])
                if choices:
                    msg = choices[0].get("message", {})
                    # Handle thinking models (reasoning_content in content field may be empty)
                    content = msg.get("content", "")
                    reasoning = msg.get("reasoning", "") or msg.get("reasoning_content", "")
                    # Strip <think>...</think> blocks from content (Qwen3 embeds these)
                    if content and "<think>" in content:
                        stripped = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
                        if stripped:
                            content = stripped
                    response_text = content if content else reasoning
                else:
                    response_text = ""
                return {
                    "model": model,
                    "response": response_text,
                    "latency_ms": int((time.time() - start) * 1000),
                    "success": bool(response_text),
                }
            else:
                error_text = await resp.text()
                return {"model": model, "response": "", "latency_ms": 0, "success": False, "error": f"HTTP {resp.status}: {error_text[:100]}"}
    except Exception as e:
        return {"model": model, "response": "", "latency_ms": 0, "success": False, "error": str(e)}


async def judge_with_opus(task: str, responses: list, api_key: str) -> dict:
    """Have Opus judge teacher responses and pick the best."""
    
    # Build comparison prompt
    response_text = ""
    for i, r in enumerate(responses):
        if r["success"] and r["response"]:
            response_text += f"\n\n--- Response from {r['model']} ---\n{r['response'][:3000]}"
    
    if not response_text:
        return {"success": False, "error": "No valid teacher responses"}
    
    judge_prompt = f"""You are judging AI model responses for training data quality. 
    
TASK: {task}

RESPONSES:{response_text}

Score each response 1-10 on: accuracy, completeness, code quality (if applicable), and practical usefulness.

Respond in this exact JSON format:
{{
    "scores": {{"model_name": score, ...}},
    "best_model": "model_name",
    "quality_tier": "excellent|good|acceptable|poor",
    "reasoning": "Brief explanation of why the best response won",
    "improved_response": "Your improved version combining the best elements (optional, only if you can meaningfully improve on the best response)"
}}"""

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                ANTHROPIC_URL,
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": OPUS_MODEL,
                    "max_tokens": MAX_TOKENS_JUDGE,
                    "messages": [{"role": "user", "content": judge_prompt}],
                },
                timeout=aiohttp.ClientTimeout(total=120)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    content = data["content"][0]["text"]
                    # Parse JSON from response
                    try:
                        # Try to extract JSON from response
                        json_start = content.find("{")
                        json_end = content.rfind("}") + 1
                        if json_start >= 0 and json_end > json_start:
                            judgment = json.loads(content[json_start:json_end])
                            judgment["success"] = True
                            return judgment
                    except json.JSONDecodeError:
                        pass
                    return {"success": False, "error": "Could not parse Opus response"}
                else:
                    error_text = await resp.text()
                    return {"success": False, "error": f"HTTP {resp.status}: {error_text[:200]}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def run_distillation_batch(batch_size: int = BATCH_SIZE, api_key: str = ""):
    """Run one batch of distillation: query teachers → judge → save training data."""
    
    conn = sqlite3.connect(str(DISTILL_DB))
    
    # Get pending tasks
    tasks = conn.execute(
        "SELECT id, task_text, category FROM tasks WHERE status = 'pending' ORDER BY RANDOM() LIMIT ?",
        (batch_size,)
    ).fetchall()
    
    if not tasks:
        print("No pending tasks. Load more with --load-tasks")
        conn.close()
        return 0
    
    print(f"\n{'='*60}")
    print(f"Distillation batch: {len(tasks)} tasks")
    print(f"Teachers: {', '.join(TEACHER_MODELS.keys())}")
    print(f"Judge: {OPUS_MODEL}")
    print(f"Estimated Opus cost: ~${len(tasks) * COST_PER_JUDGE_CALL:.2f}")
    print(f"{'='*60}\n")
    
    completed = 0
    
    async with aiohttp.ClientSession() as session:
        for task_id, task_text, category in tasks:
            print(f"\nTask {task_id} [{category}]: {task_text[:80]}...")
            
            # Mark in progress
            conn.execute("UPDATE tasks SET status = 'in_progress' WHERE id = ?", (task_id,))
            conn.commit()
            
            # Query all teachers (sequentially to manage memory — only 1 model loaded at a time)
            responses = []
            for model_name in TEACHER_MODELS:
                print(f"  Asking {model_name}...", end=" ", flush=True)
                result = await query_teacher(session, model_name, task_text)
                responses.append(result)
                
                if result["success"]:
                    print(f"✓ ({result['latency_ms']}ms, {len(result['response'])} chars)")
                    conn.execute(
                        "INSERT INTO teacher_responses (task_id, model_name, response, latency_ms) VALUES (?, ?, ?, ?)",
                        (task_id, model_name, result["response"], result["latency_ms"])
                    )
                else:
                    print(f"✗ ({result.get('error', 'unknown')})")
            
            # Judge with Opus
            valid_responses = [r for r in responses if r["success"] and r["response"]]
            if valid_responses:
                print(f"  Opus judging {len(valid_responses)} responses...", end=" ", flush=True)
                judgment = await judge_with_opus(task_text, responses, api_key)
                
                if judgment.get("success"):
                    best_model = judgment.get("best_model", "")
                    quality = judgment.get("quality_tier", "unknown")
                    print(f"✓ Winner: {best_model} ({quality})")
                    
                    # Get the best response text
                    best_response = judgment.get("improved_response", "")
                    if not best_response:
                        for r in responses:
                            if r["model"] == best_model:
                                best_response = r["response"]
                                break
                    
                    # Save judgment
                    conn.execute("""
                        INSERT INTO judgments (task_id, best_model, best_response, opus_reasoning, 
                                            opus_improved, scores, quality_tier, cost_usd)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        task_id, best_model, best_response,
                        judgment.get("reasoning", ""),
                        judgment.get("improved_response", ""),
                        json.dumps(judgment.get("scores", {})),
                        quality,
                        COST_PER_JUDGE_CALL
                    ))
                    
                    # Write training example (Alpaca format)
                    if quality in ("excellent", "good"):
                        training_example = {
                            "instruction": task_text,
                            "input": "",
                            "output": best_response,
                            "metadata": {
                                "source_model": best_model,
                                "quality": quality,
                                "category": category,
                                "scores": judgment.get("scores", {}),
                                "distilled_at": datetime.now(timezone.utc).isoformat(),
                            }
                        }
                        with open(OUTPUT_FILE, "a") as f:
                            f.write(json.dumps(training_example) + "\n")
                    
                    conn.execute("UPDATE tasks SET status = 'complete' WHERE id = ?", (task_id,))
                    completed += 1
                else:
                    print(f"✗ Judge failed: {judgment.get('error', 'unknown')}")
                    conn.execute("UPDATE tasks SET status = 'failed' WHERE id = ?", (task_id,))
            else:
                print("  No valid teacher responses, skipping judgment")
                conn.execute("UPDATE tasks SET status = 'failed' WHERE id = ?", (task_id,))
            
            conn.commit()
    
    # Update stats
    total_complete = conn.execute("SELECT COUNT(*) FROM judgments WHERE quality_tier IN ('excellent', 'good')").fetchone()[0]
    total_cost = conn.execute("SELECT COALESCE(SUM(cost_usd), 0) FROM judgments").fetchone()[0]
    
    stats = {
        "total_training_examples": total_complete,
        "total_opus_cost": round(total_cost, 2),
        "last_batch": datetime.now(timezone.utc).isoformat(),
        "batch_completed": completed,
        "finetune_ready": total_complete >= FINETUNE_THRESHOLD,
    }
    with open(STATS_FILE, "w") as f:
        json.dump(stats, f, indent=2)
    
    print(f"\n{'='*60}")
    print(f"Batch complete: {completed}/{len(tasks)} tasks")
    print(f"Total training examples: {total_complete}")
    print(f"Total Opus cost: ${total_cost:.2f}")
    if total_complete >= FINETUNE_THRESHOLD:
        print(f"🎯 FINETUNE READY! Run with --finetune")
    else:
        print(f"Need {FINETUNE_THRESHOLD - total_complete} more examples before fine-tune")
    print(f"{'='*60}")
    
    conn.close()
    return completed


def show_status():
    """Show distillation progress."""
    if not DISTILL_DB.exists():
        print("No distillation database found. Run --load-tasks first.")
        return
    
    conn = sqlite3.connect(str(DISTILL_DB))
    
    total_tasks = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
    pending = conn.execute("SELECT COUNT(*) FROM tasks WHERE status = 'pending'").fetchone()[0]
    complete = conn.execute("SELECT COUNT(*) FROM tasks WHERE status = 'complete'").fetchone()[0]
    failed = conn.execute("SELECT COUNT(*) FROM tasks WHERE status = 'failed'").fetchone()[0]
    
    total_judgments = conn.execute("SELECT COUNT(*) FROM judgments").fetchone()[0]
    excellent = conn.execute("SELECT COUNT(*) FROM judgments WHERE quality_tier = 'excellent'").fetchone()[0]
    good = conn.execute("SELECT COUNT(*) FROM judgments WHERE quality_tier = 'good'").fetchone()[0]
    
    # Model win rates
    wins = conn.execute("""
        SELECT best_model, COUNT(*) as wins 
        FROM judgments 
        GROUP BY best_model 
        ORDER BY wins DESC
    """).fetchall()
    
    total_cost = conn.execute("SELECT COALESCE(SUM(cost_usd), 0) FROM judgments").fetchone()[0]
    training_examples = excellent + good
    
    # Fine-tune history
    finetunes = conn.execute("SELECT * FROM finetune_runs ORDER BY id DESC LIMIT 3").fetchall()
    
    print(f"\n{'='*60}")
    print(f"  DISTILLATION ENGINE STATUS")
    print(f"{'='*60}")
    print(f"\n  Tasks: {total_tasks} total | {pending} pending | {complete} complete | {failed} failed")
    print(f"  Judgments: {total_judgments} | {excellent} excellent | {good} good")
    print(f"  Training examples (excellent+good): {training_examples}")
    print(f"  Opus cost so far: ${total_cost:.2f}")
    print(f"  Fine-tune ready: {'✅ YES' if training_examples >= FINETUNE_THRESHOLD else f'❌ Need {FINETUNE_THRESHOLD - training_examples} more'}")
    
    if wins:
        print(f"\n  Model Win Rates:")
        for model, count in wins:
            pct = (count / total_judgments * 100) if total_judgments > 0 else 0
            print(f"    {model}: {count} wins ({pct:.0f}%)")
    
    # Category breakdown
    cats = conn.execute("""
        SELECT t.category, COUNT(*) 
        FROM tasks t JOIN judgments j ON t.id = j.task_id 
        GROUP BY t.category
    """).fetchall()
    if cats:
        print(f"\n  Category Breakdown:")
        for cat, count in cats:
            print(f"    {cat}: {count} examples")
    
    if finetunes:
        print(f"\n  Recent Fine-tune Runs:")
        for ft in finetunes:
            print(f"    #{ft[0]}: {ft[2]} examples, status={ft[5]}, {ft[3]}")
    
    print(f"\n{'='*60}")
    conn.close()


def trigger_finetune(base_model: str = "qwen2.5-coder:32b"):
    """Trigger MLX LoRA fine-tune from distilled training data."""
    if not OUTPUT_FILE.exists():
        print("No distilled training data found. Run distillation first.")
        return
    
    # Count examples
    with open(OUTPUT_FILE) as f:
        count = sum(1 for _ in f)
    
    if count < 50:
        print(f"Only {count} examples. Need at least 50 for meaningful fine-tune.")
        return
    
    print(f"\nFine-tuning trevor-domain from {count} distilled examples")
    print(f"Base model: {base_model}")
    print(f"This will take a while on Apple Silicon...")
    print(f"\nRun manually:")
    print(f"  cd {JARVIS_ROOT}")
    print(f"  bash scripts/finetune_router.sh {base_model} {OUTPUT_FILE}")
    
    # Record the run
    conn = sqlite3.connect(str(DISTILL_DB))
    conn.execute(
        "INSERT INTO finetune_runs (examples_count, base_model, output_model, status) VALUES (?, ?, ?, ?)",
        (count, base_model, "trevor-domain:latest", "pending")
    )
    conn.commit()
    conn.close()


def get_api_key() -> str:
    """Get Anthropic API key."""
    # Check environment
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if key:
        return key
    
    # Check jarvis API directory
    key_file = JARVIS_ROOT / "API" / "CLAUDE_API_KEY.txt"
    if key_file.exists():
        return key_file.read_text().strip()
    
    # Check common locations
    for path in [Path.home() / ".anthropic" / "api_key", Path.home() / ".config" / "anthropic" / "api_key"]:
        if path.exists():
            return path.read_text().strip()
    
    return ""


async def main():
    import argparse
    parser = argparse.ArgumentParser(description="Knowledge Distillation Engine")
    parser.add_argument("--run", action="store_true", help="Run distillation batch")
    parser.add_argument("--load-tasks", action="store_true", help="Load task bank from sources")
    parser.add_argument("--status", action="store_true", help="Show distillation progress")
    parser.add_argument("--finetune", action="store_true", help="Trigger fine-tune")
    parser.add_argument("--batch-size", type=int, default=BATCH_SIZE, help=f"Tasks per batch (default {BATCH_SIZE})")
    parser.add_argument("--continuous", action="store_true", help="Run continuously until all tasks done")
    args = parser.parse_args()
    
    init_db()
    
    if args.status:
        show_status()
        return
    
    if args.load_tasks:
        conn = sqlite3.connect(str(DISTILL_DB))
        loaded = load_task_bank(conn, limit=200)
        total = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
        print(f"Loaded {loaded} new tasks. Total in bank: {total}")
        conn.close()
        return
    
    if args.finetune:
        trigger_finetune()
        return
    
    if args.run:
        api_key = get_api_key()
        if not api_key:
            print("ERROR: No Anthropic API key found.")
            print("Set ANTHROPIC_API_KEY env var or create ~/jarvis/API/ANTHROPIC_API_KEY.txt")
            return
        
        if args.continuous:
            print("Running continuous distillation (Ctrl+C to stop)...")
            while True:
                completed = await run_distillation_batch(args.batch_size, api_key)
                if completed == 0:
                    print("All tasks complete!")
                    break
                await asyncio.sleep(5)  # Brief pause between batches
        else:
            await run_distillation_batch(args.batch_size, api_key)
        return
    
    parser.print_help()


if __name__ == "__main__":
    asyncio.run(main())
