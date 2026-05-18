# Memory Integration — Unified vault + Nexus graph

## The graph

`~/Jarvis/knowledge/_index.db` — SQLite with FTS5 full-text search. **Two layers overlaid as one:**

| Layer | `files.source` | Count | `links.link_type` | Edge count |
|---|---|---|---|---|
| Vault (MD notes) | `vault` | 858 | `wiki_link` | 92 |
| Code (AST modules) | `code` | 6,905 | `code_import` | 2,274 |

Both share the same `files`, `links`, and `fts_content` tables. A single FTS query returns results from both corpora. Graph traversal crosses layers.

## Schema

```sql
CREATE TABLE files (
  id INTEGER PRIMARY KEY,
  path TEXT UNIQUE,
  title TEXT,
  file_type TEXT,        -- note, pattern, skill, agent, code, etc.
  workspace_id TEXT,
  agent_id TEXT,
  source TEXT DEFAULT 'vault',
  content_hash TEXT,
  frontmatter TEXT,
  created_at TEXT, updated_at TEXT
);

CREATE TABLE links (
  id INTEGER PRIMARY KEY,
  source_file_id INTEGER,
  target_path TEXT,
  target_file_id INTEGER,
  link_text TEXT,
  display_text TEXT,
  link_type TEXT DEFAULT 'wiki_link'   -- 'wiki_link' | 'code_import'
);

CREATE VIRTUAL TABLE fts_content USING fts5(
  path, title, content, file_type,
  tokenize="porter"
);
```

Plus `tags`, `file_tags`, `aliases`, `image_catalog`, `image_fts`, `search_log`, `vault_audit_log`.

## Who writes to it

### Vault side
- `knowledge/vault_writer.py` — main Python API for writing learnings, decisions
- `knowledge/vault_cli.py` — CLI wrapper that all agents use
- Every vault write triggers FTS re-index
- File types: `note`, `pattern`, `collective_patterns`, `skill`, `skill_agent`, `agent`, `agent_definition`, `discovery`, `correction`, `failure`, `improvement`

### Code side
- `.nexus-map/raw/ast_nodes.json` — AST scan output (written by `nexus-mapper`)
- `knowledge/nexus_bridge.py` — imports AST nodes/edges into `_index.db`
- Runs on-demand when code structure changes significantly
- Sets `source='code'`, `file_type='code'`

## The existing wiring to OpenClaw

Already in place, all three layers:

### Layer 1 — Bootstrap injection (static snapshot)

`knowledge/openclaw_vault_bridge.py --generate-context` writes `VAULT_CONTEXT.md` to the OpenClaw workspace. OpenClaw's `bootstrap-extra-files` loads it at session start.

Contents (from the bridge):
- Last 5 collective patterns (truncated)
- Last 3 boardroom decisions
- Recent learnings per agent (claude-code, scout, validator, guardian, trevor)
- Vault search + write reminders with copy-paste commands

Regenerated periodically via `openclaw_vault_bridge.py --all`.

### Layer 2 — `vault_cli.py` as a skill

Every agent can shell out to `python3 ~/Jarvis/knowledge/vault_cli.py` to search or write. Slow (subprocess) but reliable. The FTS5 query runs in ~10ms.

### Layer 3 — `nexus-query` skill

Pre-installed code-structure query skill. Handles: "who imports X?", "impact radius of changing Y?", "top hubs?". Uses `.nexus-map/raw/ast_nodes.json` directly + `_index.db` for cross-layer context.

## What's missing (as of this skill)

1. **No first-class `vault_search` tool** that OpenClaw/Claude Code can call without shelling out. The model has to remember to use bash.
2. **Conversation aggregator isn't reachable from OpenClaw.** `Jarvis_Agent_SDK/conversation_aggregator.py` pulls from 6 DBs (users, journeys, conversations, boardroom, workspace cache, JSON files) with connection pooling + hot/warm/cold cache. All of that is invisible to the 35B.
3. **OpenClaw's built-in `memory-core` plugin** expects an embedding provider key we haven't set → it falls back to BM25-only or is effectively disabled. Could be replaced with a custom memory plugin that queries our vault+aggregator.

## `scripts/vault_search.py` (in this skill)

Single-command unified query. Takes keywords, returns:
- Top-N FTS hits spanning vault + code
- For each code hit: its importers (who depends on it) and its imports (what it depends on)
- For each vault hit: its wiki-links (related notes)
- Both layers ranked by FTS score

Usage:
```bash
python3 .agents/skills/local-llm-operations/scripts/vault_search.py "kronos tuning"
```

## FTS5 query patterns

```sql
-- Simple keyword (porter stemming handles plurals, -ing suffixes, etc.)
SELECT path, rank FROM fts_content WHERE fts_content MATCH 'kronos tuning';

-- Multi-term AND (default)
SELECT path FROM fts_content WHERE fts_content MATCH 'validator AND tool_calling';

-- OR
SELECT path FROM fts_content WHERE fts_content MATCH '35b OR opus OR sonnet';

-- Phrase
SELECT path FROM fts_content WHERE fts_content MATCH '"enable thinking false"';

-- NEAR operator
SELECT path FROM fts_content WHERE fts_content MATCH 'NEAR(openclaw compaction, 10)';

-- Filter by file_type column
SELECT path FROM fts_content WHERE fts_content MATCH 'kronos' AND file_type = 'correction';
```

## Graph traversal queries

```sql
-- Who imports handler_claude.py? (impact radius)
SELECT src.path
FROM links l
JOIN files tgt ON tgt.id = l.target_file_id
JOIN files src ON src.id = l.source_file_id
WHERE tgt.path LIKE '%handler_claude%' AND l.link_type = 'code_import';

-- What does a vault note link to?
SELECT tgt.path
FROM links l
JOIN files src ON src.id = l.source_file_id
LEFT JOIN files tgt ON tgt.id = l.target_file_id
WHERE src.path = 'collective/patterns/2026-04-20.md' AND l.link_type = 'wiki_link';

-- Cross-layer: find vault notes that MENTION a code file (by path match in content)
SELECT path FROM fts_content
WHERE fts_content MATCH '"handler_data_validator.py"'
  AND file_type != 'code';
```

## When to rebuild the index

- After writing many vault entries (auto-triggered)
- After significant code changes → re-run `nexus-mapper` to refresh `ast_nodes.json`, then `python3 -c "from knowledge.nexus_bridge import NexusBridge; NexusBridge().run()"`
- If FTS search returns stale hits → `knowledge/vault_writer.py` has a rebuild method

## Conversation aggregator — how to reach it

`conversation_aggregator.py` key methods:
- `get_workspace_conversations_sync(workspace_id, user_id, show_archived)` — cross-source conversations for a workspace
- `get_all_conversations_sync(user_id, show_archived)` — everything user-scoped
- `get_recent_conversations(limit, workspace_id)` — recency-ranked

It's Python-only, used by Trevor Desktop and the Flask server. For OpenClaw to reach it, options:
1. **Wrap in a script** (like `scripts/vault_search.py`) and shell out from the 35B — cheap, not discoverable
2. **Expose via MCP server** — first-class tool for the 35B, discoverable via OpenClaw's MCP auto-discovery. More work but better UX
3. **Periodic sync into vault** — flatten recent conversations into `collective/conversations/YYYY-MM-DD.md` so FTS can find them

Path 3 is easiest to prototype. Path 2 is the right long-term answer.

## Custom OpenClaw memory plugin (future)

OpenClaw supports `plugins.slots.memory = "<plugin-name>"`. A plugin that routes `memory_search` / `memory_get` through our vault + aggregator would make this a first-class capability. Skeleton:

```json5
"plugins": {
  "slots": { "memory": "jarvis-unified" },
  "entries": {
    "jarvis-unified": {
      "enabled": true,
      "config": {
        "vaultDb": "~/Jarvis/knowledge/_index.db",
        "aggregatorEntrypoint": "Jarvis_Agent_SDK.conversation_aggregator:ConversationAggregator"
      }
    }
  }
}
```

The plugin itself would need to implement the OpenClaw plugin API. Not built yet — track as a follow-up.

## Related files

- `~/Jarvis/knowledge/_index.db` — the unified graph
- `~/Jarvis/knowledge/vault_writer.py` — Python write API
- `~/Jarvis/knowledge/vault_cli.py` — CLI
- `~/Jarvis/knowledge/nexus_bridge.py` — code layer import
- `~/Jarvis/knowledge/openclaw_vault_bridge.py` — vault → OpenClaw sync
- `~/Jarvis/.nexus-map/` — AST scan output
- `~/Jarvis/Jarvis_Agent_SDK/conversation_aggregator.py` — 6-source conversation aggregator
- `.agents/skills/nexus-query/` — existing code-query skill
- `.agents/skills/vault-cli/` — existing vault CLI skill
