---
type: improvement
created: 2026-03-21
tags: [architecture, skills, vault, unified, symlinks]
agent: log
decomposed_from: agents/claude-code/log/2026-03.md
---

## 📈 Unified skill architecture: .agents/skills as single source, .claude/skills all symlinks, vault indexes via symlinks
**Date:** 2026-03-21T17:07:03
**Type:** improvement
**Tags:** architecture, skills, vault, unified, symlinks

> [!success] IMPROVEMENT
> Completed One Brain architecture: (1) .claude/skills/ — 149 symlinks, 0 real dirs, all point to .agents/skills/. (2) knowledge/skills/ — 85 symlinks to .agents/skills/SKILL.md + 130 real agent-builder files. (3) OpenClaw reads .agents/skills via extraDirs. Single edit in .agents/skills propagates everywhere instantly. No more manual sync needed for existing skills. Agent registry: 296 skill agents. Improved agent builder with skill-creator quality guidelines baked in.
