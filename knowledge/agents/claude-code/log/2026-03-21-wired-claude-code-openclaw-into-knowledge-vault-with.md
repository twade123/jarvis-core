---
type: improvement
created: 2026-03-21
tags: [vault, automation, hooks, openclaw, integration]
agent: log
decomposed_from: agents/claude-code/log/2026-03.md
---

## 📈 Wired Claude Code + OpenClaw into Knowledge Vault with automation
**Date:** 2026-03-21T12:26:01
**Type:** improvement
**Tags:** vault, automation, hooks, openclaw, integration

> [!success] IMPROVEMENT
> Built full vault automation layer: 1) Claude Code hooks (UserPromptSubmit searches vault, Stop reminds vault write), 2) 5 slash commands (/vault search/write/status/backlinks/graph), 3) vault-agent subagent for deep research, 4) OpenClaw bridge script (openclaw_vault_bridge.py) that generates VAULT_CONTEXT.md and syncs daily logs, 5) Added VAULT_CONTEXT.md to OpenClaw bootstrap-extra-files, 6) Strengthened compaction prompt with typed vault writes + bridge refresh. Also fixed 40 broken wiki-links, added aliases table, directory link resolution, Obsidian callout syntax, templates system, Dataview queries, graph export, embeds/transclusion.
