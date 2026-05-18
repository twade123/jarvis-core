---
name: context-compactor
description: Proactive context management for local Ollama models. Estimates token usage client-side and compacts before context overflows. Use when working with large data, multi-step tasks, or long sessions with trevor-base.
---

# Context Compactor

Local models like trevor-base don't report token counts reliably enough for OpenClaw's built-in compaction to trigger in time. This skill compacts proactively.

## When to compact

Compact before starting ANY of these:
- Reading training data files or knowledge stores
- Multi-step tasks (3+ tool calls planned)
- Pulling flight recorder, trade history, or DB records
- After finishing a major task block, before starting the next

## How to compact

**Step 1 — Estimate current context size**
Count the rough token usage from this session mentally:
- Each tool call result: ~500–5000 tokens depending on output size
- Each message exchange: ~200–500 tokens
- If you've done 5+ tool calls or the session feels long: compact now

**Step 2 — Write memory before compacting**

Write to short-term memory first:
```bash
# Overwrite with current state
cat > ~/.openclaw/workspace/memory/short-term.md << 'EOF'
[Write: what task is active, what was found, what's next]
EOF
```

Append to today's daily log:
```bash
date_str=$(date +%Y-%m-%d)
cat >> ~/.openclaw/workspace/memory/${date_str}.md << 'EOF'

## [HH:MM] Session block
- [What was worked on]
- [Key findings]
- [Changes made]
EOF
```

**Step 3 — Save to knowledge vault if anything notable happened**
```bash
source ~/myenv/bin/activate && python3 ~/Jarvis/knowledge/vault_cli.py \
  --agent "trevor" \
  --type "note" \
  --summary "[one-line summary]" \
  --context "[what happened, what was found or fixed]" \
  --tags "session"
```

**Step 4 — Summarize and continue**

After writing memory, produce a 3–5 line summary of everything important from this session so far, then continue the task fresh with that summary as your working context.

## Rules for large data requests

Before calling ANY function that reads training data, flight records, or DB tables:
1. Add `limit=50` or `LIMIT 50` to the query
2. Never call `extract_validator_pairs()` without a limit
3. Never call `backfill_from_history()` in a chat session — it's for offline batch runs only
4. Use `get_today_summary()` for flight recorder, not raw table queries
5. Use `get_training_stats()` to check dataset size before reading training data

## Trigger phrases

Compact immediately when you think or say any of these:
- "let me pull all the training data"
- "let me check the full history"
- "let me read all the records"
- "let me look through everything"

Instead, always scope the query first: most recent N, today only, or stats summary.
