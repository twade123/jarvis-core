---
type: improvement
created: 2026-03-22
tags: [vault, toc, agents, visibility, floor-chat]
agent: log
decomposed_from: agents/claude-code/log/2026-03.md
---

## 📈 Built Vault TOC system — agents see what knowledge is available, LLM reasoning decides what to pull
**Date:** 2026-03-22T15:48:42
**Type:** improvement
**Tags:** vault, toc, agents, visibility, floor-chat

> [!success] IMPROVEMENT
> vault_toc.py generates lightweight TOC (~376 words) scoped by workspace+agent. Shows: agent's own knowledge, team agents, education library (10 files with descriptions), collective memory, 206 teaching images, 32 skills. Auto-included in system prompt via VaultKnowledgeLoader.load_system_prompt(include_toc=True). Cached 5min. Also wired floor_chat.py to assemble data package (intelligence, indicators, pair history) before calling validator on user chart submissions.

---
