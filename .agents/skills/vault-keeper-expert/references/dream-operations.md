# Dream Operations — Vault Maintenance Playbook

How to perform each maintenance operation. Read the entry, understand it, then act.

## Table of Contents
- [Consolidation (Merge Duplicates)](#consolidation)
- [Pruning (Archive Stale)](#pruning)
- [Reorganization (Move Misfiled)](#reorganization)
- [Decomposition (Split Bloated)](#decomposition)
- [Link Repair](#link-repair)
- [Contradiction Resolution](#contradiction-resolution)
- [Daily Summary](#daily-summary)

---

## Consolidation

**When:** Two entries say the same thing. Same event, same fix, same discovery — just written by different agents or at different times.

**How to judge:** Read both entries. If you could delete one and lose no information, they're duplicates. If each has unique details, they're related but not duplicates.

**Merge procedure:**
1. Identify which entry is MORE detailed/complete — that's the keeper
2. Read the other entry for any unique facts not in the keeper
3. If unique facts exist: append them to the keeper under a "## Additional Context" section
4. Propose: merge into {keeper_path}, delete {duplicate_path}

**Example — True duplicate:**
```
Entry A (agents/trevor/2026-03-11-vault-wiring.md):
  "Wired vault writes into v4_pipeline.py, position_guardian.py, context_injector.py"

Entry B (collective/patterns/2026-03-11.md, bullet 3):
  "Vault wiring completed — v4_pipeline, position_guardian, context_injector now write to vault"
```
Verdict: DUPLICATE. Entry A has the file names. Keep A, remove the bullet from B.

**Example — Related but NOT duplicate:**
```
Entry A: "Fixed gate1 bypass regression — user_watch was dropped from bypass list"
Entry B: "user_watch architecture: validator sets snipe conditions -> early exit -> scout monitors"
```
Verdict: CLEAN. A is about a bug fix. B is about the architecture. Different information.

---

## Pruning

**When:** An entry is about something that no longer exists, was superseded by a newer entry, or is a debugging note for a resolved issue.

**How to judge:**
- Does this reference code/files that were deleted or refactored?
- Is there a newer entry that supersedes this one?
- Is this a "fixed bug X" note where the fix is already in the code?
- Has this not been referenced or updated in 30+ days?

**Archive procedure:**
1. Propose moving to `knowledge/archive/{original_relative_path}`
2. The archive preserves the directory structure
3. Archived files are excluded from FTS search results
4. Never delete — always archive

**Example — Stale:**
```
Entry: "Debugging: handler_calendar.py line 234 has wrong timezone offset"
But: handler_calendar.py was rewritten 3 weeks ago, line 234 is now different code
```
Verdict: STALE. Archive it.

**Example — NOT stale:**
```
Entry: "EUR_USD + GBP_USD correlation is 0.87 — never trade both in same direction"
```
This is evergreen domain knowledge. NOT stale even if old.

---

## Reorganization

**When:** An entry is in the wrong directory for its content type.

**Directory placement rules:**
| Content | Correct Location |
|---------|-----------------|
| Agent-specific learning | `agents/{agent-name}/` |
| Pattern useful to ALL agents | `collective/patterns/` |
| Trading domain knowledge | `collective/trading-knowledge/` |
| Boardroom decision | `boardroom/decisions/` |
| User preference/profile | `users/{username}/` |

**Move procedure:**
1. Identify the correct directory
2. Propose: move from {old_path} to {new_path}
3. Update any `[[wiki-links]]` in other files that reference the old path

**Example — Misfiled:**
```
File: agents/claude-code/marketing-strategy.md
Content: "Marketing strategy specialist agent prompt"
```
This is an agent definition, not a claude-code learning. Should be in `agents/claude-code/marketing/` or `agents/skill-agents/`.

---

## Decomposition

**When:** A single file has grown into a multi-entry dump — many `## heading` blocks separated by `---`, each with its own `**Date:**` and `**Type:**`.

**How to recognize:** The file has 3+ entries with the pattern:
```
## Title (date)
**Date:** YYYY-MM-DD
**Type:** improvement/correction/note
**Tags:** tag1, tag2

Content...

---
```

**CRITICAL: Only decompose learnings/log files.** Never decompose:
- prompt.md (agent prompts use `##` for structure, not entries)
- Skill files (same — `##` is document structure)
- Templates, boardroom prompts, README files

**Decompose procedure:**
1. Parse each `## heading` block between `---` separators
2. Create individual file: `{date}-{slug}.md` with frontmatter
3. Replace original with an index file listing all entries
4. Each new file gets `decomposed_from: {original_path}` in frontmatter

---

## Link Repair

**When:** A file contains `[[target]]` or `[text](path)` pointing to a file that doesn't exist.

**Repair procedure:**
1. Check if the target was moved (search vault for similar filename)
2. If found at new location: update the link
3. If not found: replace the broken link with plain text (remove the `[[` brackets or markdown link syntax)
4. Never delete content — just fix the link markup

---

## Contradiction Resolution

**When:** Two entries make opposing claims about the same thing.

**Example:**
```
Entry A: "SNIPE_TRIGGER_THRESHOLD is 0.80"
Entry B: "SNIPE_TRIGGER_THRESHOLD raised to 0.90"
```

**Resolution:** Entry B is newer and supersedes A. Archive A or update it to reference B.

**If you can't determine which is correct:** Flag for human review. Do NOT guess.

---

## Daily Summary

Write a brief report covering:
- Files reviewed since last summary
- Issues found (by type: duplicates, stale, misfiled, etc.)
- Actions pending user approval
- Current vault health (file count, any concerns)

Keep under 200 words. Save to `Data/daily_reports/YYYY-MM-DD.md`.

---

## Decision Framework

When you're unsure, follow this priority:

1. **Safety first** — when in doubt, don't modify. Add to pending queue.
2. **Consolidate aggressively** — duplicates waste everyone's context window
3. **Archive generously** — stale info is worse than missing info (archive, don't delete)
4. **Reorganize carefully** — moving files can break references
5. **Never touch protected files** — prompts, skills, templates are production code
