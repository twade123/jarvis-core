# Vault Structure Reference

## Directory Map

```
knowledge/
  _index.db                    # FTS5 search index (rebuilt on every write)

  agents/                      # Per-agent learnings, prompts, profiles (383 files)
    {agent-name}/
      prompt.md                # PROTECTED — system prompt loaded at runtime
      profile.md               # PROTECTED — agent identity/capabilities
      learnings.md             # Rolling learnings (or index if decomposed)
      log/
        YYYY-MM.md             # Monthly activity log
      {date}-{topic}.md        # Individual decomposed learning entries

    claude-code/               # Claude Code agent (180 files — largest)
      gsd/                     # GSD (Get Stuff Done) subagent files
      marketing/               # Marketing team agent files
      log/                     # Monthly logs

    skill-agents/              # Agent definitions created from skills (84 files)
      skill_{name}.md          # Auto-generated agent prompts

    trevor/                    # Trevor Core learnings (88 files — decomposed)
    scout/                     # Scout trading agent
    validator/                 # Validator trading agent
    guardian/                  # Position guardian agent

  boardroom/                   # Boardroom multi-model collaboration (11 files)
    decisions/                 # Architecture and strategy decisions
      YYYY-MM-DD.md            # Dated decision records
      architecture.md          # System architecture decisions
    prompts/                   # PROTECTED — boardroom seat prompts
      boardroom_context.md     # Shared boardroom context
      cto.md, cso.md, cro.md, cdo.md  # Board seat prompts
    sessions/                  # Boardroom session transcripts

  collective/                  # Shared patterns all agents benefit from (33 files)
    patterns/                  # Date-based collective pattern files
      YYYY-MM-DD.md            # Daily pattern aggregation
      scout-learnings-*.md     # Scout retrospective summaries
    scout-retrospective/       # Weekly scout performance analysis
    trading-knowledge/         # Shared trading domain knowledge
      education/               # Trading education reference docs
        candlestick_patterns.md
        chart_patterns.md
        indicator_mastery.md
        regime_playbook.md
        etc.

  skills/                      # Skill reference docs in vault (353 files)
    {skill-name}.md            # Flat skill references
    general/                   # Organized by domain
      marketing/               # Marketing skills (26 files)
      healthcare/              # Healthcare skills (6 files)
      agent-system/            # Agent/plugin development skills
      mcp-specialists/         # MCP handler specialist skills
      legal-finance/           # Legal and finance skills
      analytics/               # Data analytics skills
      sales/                   # Sales skills
      design/                  # Design skills
      development/             # Development skills
      content/                 # Content creation skills
      seo/                     # SEO skills
      other/                   # Uncategorized skills
    trading/                   # Trading-specific skills (59 files)

  profiles/                    # User and system profiles (1 file)
    tim.md                     # Primary user profile

  templates/                   # Document templates (2 files)
    decision.md                # Decision record template
    retrospective.md           # Retrospective template

  users/                       # User data (2 files)
    tim/
      preferences.md
      profile.md

  workspaces/                  # Workspace documentation (3 files)
    forex-trading-team/README.md
    crypto-trading-team/README.md
    rmbb-health/README.md

  archive/                     # Archived/stale entries (moved here, not deleted)
```

## File Types (frontmatter `type:` field)

| Type | Count | Description |
|------|-------|-------------|
| skill_agent | 130 | Auto-generated agent prompts from skills |
| note | 70 | General notes and observations |
| improvement | 65 | System improvements and upgrades |
| correction | 61 | Bug fixes and corrections |
| pattern | 42 | Recognized patterns (collective or per-agent) |
| scout_retrospective | 12 | Weekly scout performance analysis |
| discovery | 12 | New discoveries and insights |
| agent | 10 | Agent definition files |
| collective_patterns | 9 | Daily collective pattern aggregations |
| education | 8 | Trading education reference material |
| skill_usage | 5 | Skill execution logs |
| agent_log | 4 | Monthly agent activity logs |
| workspace | 3 | Workspace README/docs |
| profile | 3 | User/agent profiles |
| index | 2 | Index files (point to decomposed entries) |

## Frontmatter Format

Every vault .md file should have YAML frontmatter:
```yaml
---
type: improvement          # See types above
created: 2026-03-11        # ISO date
updated: 2026-03-21        # Last modified (optional)
tags: [agent-name, topic]  # Searchable tags
agent: trevor              # Which agent wrote it (optional)
status: active             # active | archived
links: []                  # Wiki-links to related entries
---
```

Not all files have frontmatter (especially older ones). Missing frontmatter is not an error — just note it.

## FTS Search

Query the vault index:
```sql
SELECT path, content FROM fts_content WHERE fts_content MATCH 'search terms' LIMIT 10
```

The `fts_content` table has columns: `path`, `content`, and optional `title`, `file_type`.

## Key Rules

1. **prompt.md files are SACRED** — never propose modifying agent prompts
2. **skills/ directory is read-only** — these are symlinked from .agents/skills/
3. **collective/ is shared** — patterns here benefit all agents
4. **archive/ is the graveyard** — move stale files here, never delete from vault
5. **Decomposed files have `decomposed_from:` in frontmatter** — traces back to original
6. **Index files (type: index) are table-of-contents** — they replaced bloated originals
