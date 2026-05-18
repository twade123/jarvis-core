---
type: improvement
created: 2026-03-21
tags: [architecture, skills, vault, unified, one-brain, marketing, agent-builder, e2e-tested]
agent: log
decomposed_from: agents/claude-code/log/2026-03.md
---

## 📈 One Brain architecture — unified skill system across Claude Code, OpenClaw, Trevor/swarm, and vault
**Date:** 2026-03-21T17:20:05
**Type:** improvement
**Tags:** architecture, skills, vault, unified, one-brain, marketing, agent-builder, e2e-tested

> [!success] IMPROVEMENT
> WHAT WAS BUILT:
> 1. Installed 33 marketing skills from coreyhaines31/marketingskills into .agents/skills/
> 2. Improved agent builder (handler_agent_builder.py:1090) — baked in skill-creator quality guidelines: concrete Weak/Strong examples, anti-patterns with WHY, practitioner language, max_tokens 4000→6000
> 3. Created 296 skill agents via create_from_skill() — each has Agent Prompt + Skill Reference in vault + registered in boardroom.db agent_registry
> 4. Built 8 marketing team agents (orchestrator + 7 specialists: strategy/CSO, seo-content/CDO, cro/CRO, content-copy/CSO, paid-measurement/CDO, growth-retention/CRO, sales-gtm/CSO)
> 5. Unified skill architecture — ONE source of truth at .agents/skills/
> 
> HOW IT WORKS:
> - .agents/skills/{name}/SKILL.md = SINGLE SOURCE OF TRUTH (149 skills)
> - .claude/skills/ = 149 symlinks → .agents/skills/ (Claude Code reads these)
> - OpenClaw reads .agents/skills/ directly via extraDirs config in openclaw.json
> - knowledge/skills/ = 85 symlinks to .agents/skills/ + 130 agent-builder real files (vault FTS indexed)
> - Edit one file in .agents/skills/ → all systems see it instantly, no sync needed
> 
> AGENT REGISTRY:
> - 296 skill_agents in boardroom.db:agent_registry (status=available)
> - Board seats: CTO=160, CDO=64, CSO=50, CRO=22
> - Each agent has: agent_id, agent_name, board_seat, prompt_focus, system_prompt_path
> - Vault files at knowledge/skills/{name}.md contain Agent Prompt + Skill Reference sections
> 
> NEW SKILL FLOW:
> 1. Install via marketplace → .agents/skills/ + .claude/skills/ (auto)
> 2. OpenClaw sees immediately (extraDirs)
> 3. Claude Code sees immediately (symlink)
> 4. Vault: run import_openclaw_skills() to create symlink in knowledge/skills/
> 5. Agent registry: run create_from_skill() to generate agent + prompt
> 
> KEY FILES MODIFIED:
> - Handler/handler_agent_builder.py:1090-1145 — improved generation prompt with skill-creator quality guidelines
> - .claude/skills/ — converted 90 real dirs to symlinks
> - knowledge/skills/ — replaced 85 flat copies with symlinks to .agents/skills/
> 
> E2E TESTED: edit propagation, vault FTS search, agent registry lookup, swarm agent registration, Claude Code skill loading, OpenClaw skill reading — all pass.
