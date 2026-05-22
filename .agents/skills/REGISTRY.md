# Skills Registry — `.agents/skills/`

145 skills covering AI engineering, marketing, sales, legal, finance, support, product, data, healthcare, and tool specialists. Each skill is a self-contained capability the orchestrator can load on demand.

**How skills work in Jarvis:** every skill lives once at `.agents/skills/{name}/SKILL.md` (or `.md` at the top level for orchestrator skills). Five different surfaces read from the same source: Claude Code, OpenClaw (local-Claude-Code-style agent), Trevor's swarm, sub-agents, and the knowledge vault. Edit a skill once, every system picks it up. This is the "One Brain" pattern — see jarvis-core README.

**Reading this file:** skills are grouped by *capability cluster*, not by where they're physically used. A skill can be relevant to multiple clusters (e.g., `analytics-tracking` is both Marketing and Data) — it's listed under its primary cluster with cross-references where useful.

---

## 1. Agent / Plugin / Skill Engineering

Building, registering, orchestrating, and reasoning about agents themselves. The meta-layer that makes the rest of the system extensible.

| Skill | One-line role |
|---|---|
| `agent-builder-specialist` | Expert in dynamic agent creation via the agent_builder MCP — definition, capability config, deployment |
| `agent-development` | Guide to creating sub-agents (frontmatter, descriptions, tool selection, examples) |
| `agent-registry-specialist` | Expert on the Agent Registry MCP — cataloging, discovery, version mgmt, capability-based search |
| `agent-s-specialist` | Expert on the Agent S Handler MCP — UI automation, desktop control, lifecycle |
| `claude-automation-recommender` | Analyze a codebase and recommend Claude Code automations (hooks, subagents, skills, plugins) |
| `claude-md-improver` | Audit and improve `CLAUDE.md` files in repositories |
| `claude-opus-4-5-migration` | Migrate prompts and code from Sonnet 4.0/4.5 / Opus 4.1 to Opus 4.5 |
| `command-development` | Create slash commands — frontmatter, args, AskUserQuestion patterns |
| `cookbook-audit` | Audit an Anthropic Cookbook notebook against a rubric |
| `cowork-plugin-customizer` | Customize/personalize a Claude Code plugin for a specific org's tools and workflows |
| `hook-development` | Create PreToolUse/PostToolUse/Stop hooks for event-driven automation |
| `master-orchestrator` | Top-level coordinator that breaks user requests into domain tasks and dispatches |
| `mcp-integration` | Add MCP servers to a plugin, configure `.mcp.json`, connect external services |
| `mcp-domain-orchestrator` | Orchestrator for 34 MCP specialist agents — routes MCP tasks to correct agents |
| `multi-agent-specialist` | Coordinate agent teams, distribute tasks, parallel agent execution |
| `plugin-settings` | Plugin configuration patterns — `.local.md` files, YAML frontmatter, per-project state |
| `plugin-structure` | Scaffold a plugin — `plugin.json`, `${CLAUDE_PLUGIN_ROOT}`, commands/agents/skills/hooks |
| `prompt-master-critique` | Critique, iterate, and empirically optimize LLM system prompts (local 35B + Anthropic) |
| `prompt-registry-specialist` | Expert on prompt_registry MCP — versioning, templates, performance opt |
| `skill-development` | Guide to creating skills — progressive disclosure, structure, best practices |
| `structured-agent-specialist` | Create workflows with structured outputs, schema validation, multi-step processes |
| `swarm-specialist` | Multi-agent coordination via swarm MCP — orchestration, consensus, task distribution |
| `task-comments-specialist` | task_comments MCP — threaded discussions, mentions, notifications |
| `template-skill` | Template stub for new skills |
| `vault-keeper-expert` | Maintain the Jarvis knowledge vault — read, consolidate, prune, reorganize |
| `writing-hookify-rules` | Create hookify rules — syntax, patterns |
| **Domain orchestrators** | |
| `backend-domain-orchestrator` | Manages backend specialists (API, DB, auth, business logic, microservices, testing) |
| `frontend-domain-orchestrator` | Manages frontend specialists (React/Vue/Angular, CSS, UI/UX, accessibility) |
| `infrastructure-domain-orchestrator` | Manages DevOps specialists (CI/CD, Docker, cloud, monitoring, IaC) |
| `quality-domain-orchestrator` | Manages quality specialists (code review, refactoring, architecture, perf) |

## 2. Local LLM Operations (Jarvis-specific)

The local-model stack: serving, deploying, troubleshooting Qwen / DeepSeek / Whisper.

| Skill | One-line role |
|---|---|
| `local-llm-operations` | Operate Jarvis's local AI models — Qwen3.5 35B/9B, Kronos, DeepSeek-R1, Whisper |
| `context-compactor` | Proactive context mgmt for local Ollama models — estimate tokens, compact before overflow |
| `memory-management` | Two-tier memory: `CLAUDE.md` for working memory, `memory/` for persistent shorthand/acronyms |
| `trade-audit-repair` | Diagnostics for the forex trading system (real-time, on-demand audit, scheduled nightly) |

## 3. Knowledge, Memory & Search

The vault layer and how agents reason over stored knowledge.

| Skill | One-line role |
|---|---|
| `vault-keeper-expert` | (also in Cluster 1) Maintenance of the knowledge vault |
| `vault-cli` | CLI for writing to / reading from the vault |
| `knowledge-synthesis` | Combine search results across multiple sources into deduplicated answers w/ source attribution |
| `knowledge-management` | Write and maintain KB articles from resolved issues |
| `task-management` | Simple task tracking using a shared `TASKS.md` file |
| `nexus-mapper` | Generate persistent `.nexus-map/` knowledge base of codebase architecture |
| `nexus-query` | Instant code structure queries — dependencies, impact radius, refactoring safety |
| `doc-coauthoring` | Structured workflow for co-authoring docs, PRDs, technical specs |
| `data-context-extractor` | Bootstrap company-specific data analysis skills from analyst tribal knowledge |

## 4. Marketing

One cluster, one team. The 7-agent marketing system: a top-level strategy + orchestrator, six sub-orchestrators (one per sub-team), and the specialists each sub-team draws on.

### 4a. Strategy & top-level orchestration

| Skill | One-line role |
|---|---|
| `marketing-orchestrator` | **Top of the marketing tree** — coordinates the 7-agent marketing team across SEO / CRO / Content / Paid / Growth / Sales / Strategy |
| `marketing-strategy` | Strategic marketing direction — what to do and why |
| `marketing-ideas` | Marketing ideas, inspiration, growth tactics for SaaS / software |
| `marketing-psychology` | Apply cognitive biases, behavioral science, mental models to marketing |
| `campaign-planning` | Plan marketing campaigns — objectives, segmentation, channels, calendars, metrics |
| `launch-strategy` | Plan product launches — Product Hunt, GTM, waitlists, feature announcements |
| `product-marketing-context` | Create / maintain product marketing context docs (positioning, audience, value) |

### 4b. Content, Copy & SEO — sub-team

| Skill | One-line role |
|---|---|
| `marketing-content-copy` | **Sub-orchestrator** — content + copy team coordinator |
| `marketing-seo-content` | **Sub-orchestrator** — SEO + content team coordinator |
| `copywriting` | Write / rewrite marketing copy for any page (home, landing, pricing, features) |
| `copy-editing` | Edit, review, polish existing copy |
| `content-creation` | Draft cross-channel content (blog, social, email, landing pages, press, case studies) |
| `content-strategy` | Plan content strategy — what to write about, topic clusters, blog strategy |
| `ad-creative` | Generate ad creative — headlines, descriptions, primary text, variations for paid platforms |
| `brand-voice` | Apply / enforce brand voice + style guide across content |
| `cold-email` | Write B2B cold emails + follow-up sequences |
| `email-sequence` | Drip campaigns, nurture sequences, onboarding emails, lifecycle programs |
| `social-content` | Social content for LinkedIn, X, Instagram, TikTok, Facebook |
| `ai-seo` | Optimize content for AI search (AEO, GEO, LLMO) — get cited by LLMs |
| `seo-audit` | Audit / diagnose SEO issues — technical, on-page, Core Web Vitals, rankings |
| `programmatic-seo` | Create SEO pages at scale via templates + data |
| `schema-markup` | Add / fix structured data (JSON-LD, FAQ schema, product schema, rich snippets) |
| `site-architecture` | Plan / restructure page hierarchy, navigation, URL structure, internal linking |

### 4c. Paid, Analytics & Experimentation — sub-team

| Skill | One-line role |
|---|---|
| `marketing-paid-measurement` | **Sub-orchestrator** — paid + measurement team coordinator |
| `paid-ads` | Manage campaigns on Google / Meta / LinkedIn / X — PPC, ROAS, CPA, retargeting |
| `analytics-tracking` | Set up / audit GA4, conversion tracking, event tracking, UTM, GTM |
| `ab-test-setup` | Plan / design / implement A/B tests + experiments |
| `performance-analytics` | Analyze marketing performance, trends, channel metrics, recommendations |

### 4d. Growth & Retention — sub-team

| Skill | One-line role |
|---|---|
| `marketing-growth-retention` | **Sub-orchestrator** — growth + retention team coordinator |
| `churn-prevention` | Reduce churn — cancellation flows, save offers, dunning, retention |
| `lead-magnets` | Plan / optimize lead magnets — gated content, ebooks, checklists, templates |
| `referral-program` | Build / optimize referral, affiliate, ambassador, viral-loop programs |
| `free-tool-strategy` | Engineering-as-marketing — calculators, generators, free tools for lead gen |

### 4e. CRO (Conversion Rate Optimization) — sub-team

| Skill | One-line role |
|---|---|
| `marketing-cro` | **Sub-orchestrator** — CRO team coordinator |
| `page-cro` | Optimize any marketing page (home, landing, pricing, features, blog) for conversions |
| `signup-flow-cro` | Optimize signup, registration, account creation, trial activation |
| `onboarding-cro` | Optimize post-signup onboarding, activation, first-run, time-to-value |
| `form-cro` | Optimize non-signup forms (lead capture, contact, demo, application, survey, checkout) |
| `popup-cro` | Create / optimize popups, modals, overlays, exit intent, slide-ins, banners |
| `paywall-upgrade-cro` | Create / optimize paywalls, upgrade screens, upsell modals, feature gates |

### 4f. Sales & GTM — sub-team (lives inside the marketing cluster per Tim's org)

| Skill | One-line role |
|---|---|
| `marketing-sales-gtm` | **Sub-orchestrator** — sales + GTM team coordinator |
| `sales-enablement` | Sales collateral — pitch decks, one-pagers, objection handling, demo scripts |
| `account-research` | Research a company / person → actionable sales intel |
| `call-prep` | Prep for sales calls — account context, attendee research, suggested agenda |
| `daily-briefing` | Prioritized morning sales briefing |
| `draft-outreach` | Research prospect → personalized outreach (cold email) |
| `create-an-asset` | Generate tailored sales assets — landing pages, decks, one-pagers, workflow demos |
| `competitive-analysis` | Research competitors, positioning, messaging, content strategy, market presence |
| `competitive-intelligence` | Build interactive competitor battlecards (HTML artifact) |
| `competitor-alternatives` | Create competitor comparison / alternative pages for SEO + sales |
| `pricing-strategy` | Pricing decisions, packaging, monetization — tiers, freemium, value metric |
| `revops` | Revenue operations — lead lifecycle, MQL / SQL, pipeline stages, marketing-to-sales handoff |

## 5. Legal

| Skill | One-line role |
|---|---|
| `compliance` | Privacy regs (GDPR, CCPA), DPA review, data subject requests, cross-border transfers |
| `contract-review` | Review contracts against negotiation playbook, flag deviations, suggest redlines |
| `legal-risk-assessment` | Assess + classify legal risks (severity × likelihood + escalation criteria) |
| `nda-triage` | Screen incoming NDAs — GREEN / YELLOW / RED classification |
| `canned-responses` | Templated responses for routine legal inquiries (DSARs, vendor inquiries, NDA requests) |
| `meeting-briefing` | Structured briefings for legal-relevant meetings + action item tracking |

## 6. Finance / Accounting

| Skill | One-line role |
|---|---|
| `financial-statements` | P&L, balance sheet, cash flow — GAAP presentation + period-over-period |
| `journal-entry-prep` | Journal entries for month-end close — debits/credits + supporting docs |
| `reconciliation` | Reconcile GL to subledgers / bank / third-party — bank recs, GL-to-sub recs, intercompany |
| `variance-analysis` | Decompose financial variances into drivers — waterfall + narrative |
| `close-management` | Manage month-end close — task sequencing, dependencies, status tracking |
| `audit-support` | SOX 404 — control testing, sample selection, classification, audit prep |

## 7. Customer Support

| Skill | One-line role |
|---|---|
| `customer-research` | Search docs/KB/sources, synthesize confidence-scored answers |
| `escalation` | Structure and package support escalations with context + reproduction + business impact |
| `response-drafting` | Draft customer-facing responses adapted to situation, urgency, channel |
| `ticket-triage` | Triage tickets — categorize, prioritize (P1–P4), recommend routing |

## 8. Product Management

| Skill | One-line role |
|---|---|
| `feature-spec` | Write PRDs — problem statements, user stories, requirements, success metrics |
| `metrics-tracking` | Define / track / analyze product metrics — OKRs, dashboards, weekly reviews |
| `roadmap-management` | Plan / prioritize roadmaps — RICE, MoSCoW, ICE, Now/Next/Later |
| `user-research-synthesis` | Synthesize qual + quant user research into themes, personas, opportunity areas |
| `playground` | Build interactive HTML playgrounds — visual controls, live preview, copy-out prompt |
| `interactive-dashboard-builder` | Build self-contained interactive HTML dashboards (Chart.js + filters) |

## 9. Data, Analytics & SQL

| Skill | One-line role |
|---|---|
| `data-exploration` | Profile / explore datasets — shape, quality, patterns, nulls, outliers |
| `data-validation` | QA an analysis before sharing — methodology, accuracy, bias detection |
| `data-validator-specialist` | data_validator MCP expert — schema verification, type checking, format validation |
| `data-visualization` | Effective charts in Python (matplotlib/seaborn/plotly) + design principles |
| `statistical-analysis` | Descriptive stats, trend analysis, outlier detection, hypothesis testing |
| `sql-queries` | Correct, performant SQL across Snowflake, BigQuery, Databricks, Postgres |
| `search-strategy` | Query decomposition + multi-source search orchestration |
| `source-management` | Manage connected MCP sources for enterprise search |

## 10. Database Engineering

| Skill | One-line role |
|---|---|
| `db-design` | Design schemas for new projects — tables, relationships, types, indexes, normalization |
| `db-explorer` | Explore / query / inspect databases — schemas, sample data, ad-hoc queries |
| `db-migration` | Schema migrations — safe alters, backfills, rollback strategies |
| `db-troubleshoot` | Diagnose DB issues — locks, connection leaks, slow queries, corruption, WAL |

## 11. Healthcare / Bioinformatics

| Skill | One-line role |
|---|---|
| `clinical-trial-protocol-skill` | Generate clinical trial protocols for medical devices/drugs |
| `fhir-developer-skill` | FHIR API development — Patient, Observation, Encounter, Condition, MedicationRequest |
| `prior-auth-review-skill` | Automate payer review of prior authorization requests |
| `instrument-data-to-allotrope` | Convert lab instrument output (PDF/CSV/Excel) to Allotrope Simple Model JSON |
| `nextflow-development` | Run nf-core bioinformatics pipelines (rnaseq, sarek, atacseq) |
| `single-cell-rna-qc` | scRNA-seq QC using scverse best practices, MAD filtering, visualizations |
| `scvi-tools` | Deep learning for single-cell analysis — scVI/scANVI integration, PeakVI, totalVI |
| `scientific-problem-selection` | Help scientists with project ideation, troubleshooting, strategic research decisions |

## 12. Tool Specialists (one per MCP handler)

Each is a thin expert layer over a specific MCP — they encapsulate the MCP's full surface area and best-practice usage.

| Skill | MCP / Surface |
|---|---|
| `browser-specialist` | Browser automation (Safari + Chrome) — navigation, scraping, extraction |
| `calendar-specialist` | Calendar — create/check/update/delete events |
| `document-specialist` | Documents — Pages + Microsoft Word, read/write/convert |
| `email-specialist` | Email — send/check/read/organize across providers |
| `file-sharing-specialist` | File sharing — AirDrop, email, iMessage, cloud, network |
| `finder-specialist` | Finder — file system search, file ops, directory mgmt |
| `news-specialist` | News API — fetch, categorize, filter |
| `spreadsheet-specialist` | Spreadsheets — read/write/manipulate/formulas |
| `terminal-specialist` | Terminal — command execution with safety protocols |
| `tv-movies-specialist` | TMDB API — movie/show search, recs, cast/crew, streaming availability |
| `weather-specialist` | Weather — queries, forecasts, location-based, alerts |
| `wolfram-specialist` | Wolfram Alpha — computation, math, factual lookups, unit conversion |
| `workspace-specialist` | Workspace MCP — project org, hierarchies, access, collaboration |

## 13. Workspace Bootstrap & Observability

| Skill | One-line role |
|---|---|
| `workspace-onboarding` | End-to-end playbook for standing up a new Jarvis workspace |
| `stakeholder-comms` | Stakeholder updates — exec, eng, customer, x-functional — tailored by audience |
| `stripe-best-practices` | Stripe integration patterns — checkout, subs, webhooks, Connect, API |
| `flight-recorder` | Universal observability for any pipeline / workspace / agent |
| `remotion` | Create + edit videos programmatically using React + Remotion |

---

## Stats

- **145 active skills** across **13 capability clusters**
- **~30 AI / agent / plugin engineering skills** (the meta-layer)
- **~50 marketing skills** in one tree: 1 top-level orchestrator + 6 sub-orchestrators + ~40 specialists (Strategy, Content+SEO, Paid, Growth, CRO, Sales/GTM)
- **~13 tool specialists** (one per MCP handler)
- **~8 healthcare / bio skills**
- **~10 legal + finance + support skills** (business ops)

## Maintenance

When adding a new skill:
1. Create `.agents/skills/{name}/SKILL.md` with proper frontmatter (`name`, `description`)
2. Add an entry under the appropriate cluster in this registry
3. If it doesn't fit any cluster, propose a new one — don't tack onto an unrelated section

When removing a skill:
1. Verify no other skill references it (`grep -r "skill-name" .agents/skills/`)
2. Remove the directory + the registry entry

When a skill spans clusters: list under primary, cross-reference in others with "(also in Cluster N)".
