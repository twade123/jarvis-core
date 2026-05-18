---
type: discovery
created: 2026-03-21
tags: [agent-builder, quality, skill-creator, prompts, improvement]
agent: log
decomposed_from: agents/claude-code/log/2026-03.md
---

## 💡 Agent builder quality upgrade — skill-creator guidelines produce Weak/Strong examples and practitioner-level domain knowledge
**Date:** 2026-03-21T17:20:22
**Type:** discovery
**Tags:** agent-builder, quality, skill-creator, prompts, improvement

> [!tip] DISCOVERY
> The agent builder's create_from_skill() at Handler/handler_agent_builder.py:1090 was producing generic skill references (no concrete examples, corporate language). Fixed by: (1) Loading skill-creator/SKILL.md instead of skill-development/SKILL.md for quality guidelines. (2) Adding explicit requirements: 3+ concrete before/after examples using Weak/Strong format, practitioner domain language, anti-patterns with WHY they fail, actionable checklists over abstract frameworks, imperative form. (3) Including a quality reference snippet from page-cro skill as a writing style example. (4) Increasing max_tokens from 4000 to 6000. Before: 'Action-oriented CTA copy' (generic). After: 'Weak: Submit, Sign Up / Strong: Start Free Trial, Get My Quote — WHY: specific value exchange vs vague action.' All 296 agents created with improved prompts.
