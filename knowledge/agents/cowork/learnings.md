# Cowork Agent Learnings

## 📝 Cowork distillation run — 2026-04-19 (second pass)
**Date:** 2026-04-19T23:55:00Z
**Type:** note
**Tags:** distillation, training-data, cowork

> Extracted 4 additional pairs (3 with CoT) from 4 sessions beyond the earlier 2026-04-19 run. Domains: system (3), trading (1). Total cowork pairs in DB: 88 (81 with CoT, 92.0%). Script found 0 new JSONL transcripts (56 already processed) — same recurring sandbox scoping issue. Today's total: 5 pairs (connection-doctor/OANDA SSL, nightly-sentry/BLACK-zone retrace_state bug, skills-bisect/binary-shuttling pivot, setup-cowork onboarding, plus earlier plugin-bisect row). Session keys use `cowork-2026-04-19-*` form.

### Sessions captured (this pass):
- **connection-doctor-oanda-ssl** (quality 0.95): Repair #285 OANDA SSL handshake timeout — re-verified with fresh TLSv1.3 handshake (60ms) matching the transient pattern from incident #257; FUSE-mount SQLite workaround (synchronous=OFF) documented again.
- **nightly-learning-sentry-black-zone** (quality 1.0): P0 retraction — EUR_CHF 7572 and AUD_JPY 7582 both show identical BLACK-zone suppression pattern tied to retrace_state gate. Earlier "guardian_leak / JPY under-weighting" hypothesis retracted; unified root cause = guardian_override_bug. Recommended hotfix: bypass retrace_state when threat_score >= 90 AND reasons contain explicit structural-break strings.
- **skills-bisect-binary-shuttling** (quality 0.90): Pivoted plugin-install bisect after osascript + base64 payload tripped a Usage Policy classifier; staged three .plugin files in `.cowork-transfer/` for manual Finder install, starting with smallest/most-suspect test-all-agents (0.57 MB, 360 auto-generated agents).
- **setup-cowork-onboarding** (quality 0.60): New-user Cowork setup flow intro — role picker widget first, plugin suggestion after.

### Recurring sandbox/FUSE pattern (3rd consecutive day):
Both `session_training.db` and `connection_doctor.db` hit `disk I/O error` because virtiofs bindfs blocks `unlink()`, leaving stale SQLite rollback journals. Consistent workaround across today's runs: `nolock=1` URI + `PRAGMA journal_mode=OFF` + `synchronous=OFF`. Worth a permanent FUSE-compatible writer mode in `Core/cowork_distiller.py` and `knowledge/indexer.py`, or move Cowork scheduled distills host-side with a sandbox-side import path.

## 📝 Cowork distillation run — 2026-03-31
**Date:** 2026-03-31T23:30:00-07:00
**Type:** note
**Tags:** distillation, training-data, cowork

> Extracted 4 pairs (4 with CoT) from 4 sessions. Domains: trading (3), system (1). Total cowork pairs in DB: 37. Script found 0 new JSONL transcripts (27 already processed); pairs extracted manually from live session transcripts via list_sessions/read_transcript.

### Sessions captured:
- **trade-audit** (quality 0.95): Deep debugging of emergency_threat bypassing grace cap — traced kill chain through score_threat() else-block ordering bug
- **nightly-sentry** (quality 0.85): 22 trades, 59.1% WR, P0 finding_id regression, GBP_JPY churning
- **scout-report** (quality 0.80): 21 trades, 57% WR, risk:reward inversion analysis
- **connection-doctor** (quality 0.70): Database corruption diagnosis, all-zeros header recovery

## 📝 Cowork distillation run — 2026-04-01
**Date:** 2026-04-01T23:30:00-07:00
**Type:** note
**Tags:** distillation, training-data, cowork

> Extracted 5 pairs (5 with CoT) from 5 sessions. Domains: trading (1), coding (1), analysis (2), system (1). Total cowork pairs in DB: 42. Script unavailable in sandbox; pairs extracted manually from live session transcripts via list_sessions/read_transcript.

### Sessions captured:
- **trade-audit** (quality 0.90): Deep system health check — scout pipeline (767 scans), snipe pipeline (4 triggers, pair_cooldown blocked), validator verdicts analysis
- **guardian-scout-fix** (quality 0.90): 4-location code fix in position_guardian.py to extend grace period to scout trades
- **nightly-sentry** (quality 0.80): 29 trades, 56% WR, -53.2p net, 72.8% preventable losses, cooldown gate failure
- **scout-report** (quality 0.80): BB width boolean problem day 2, USD_CHF triple-entry bug, outlier loss destruction analysis
- **connection-doctor** (quality 0.90): 11 repair items triaged, connection_doctor.db rebuilt from schema, sandbox sqlite write limitation discovered

## 📝 Cowork distillation run — 2026-04-02
**Date:** 2026-04-02T22:00:00-07:00
**Type:** note
**Tags:** distillation, training-data, cowork

> Extracted 0 new pairs from 0 new sessions. No new user-interactive Cowork transcripts found — all 36 previously discovered transcripts already processed. Today's sessions were all automated scheduled tasks (connection-doctor, scout-report, nightly-sentry, trade-audit). Total cowork pairs in DB: 42 (40 with CoT). Pending export: 42.

## 📝 Cowork distillation run — 2026-04-03
**Date:** 2026-04-03T22:00:00-07:00
**Type:** note
**Tags:** distillation, training-data, cowork

> Extracted 4 pairs (2 with CoT) from 3 sessions. Domains: trading (3), system (1). Total cowork pairs in DB: 46. Script unavailable in sandbox; pairs extracted manually from live session transcripts via list_sessions/read_transcript.

### Sessions captured:
- **trade-audit** (quality 0.90, 2 pairs): Deep root-cause analysis of GBP_JPY #4507 — Dynamic SL jumped 32.3 pips in single tick due to missing safeguards in trending/continuing branch. Two fixes: universal 50% SL floor + 30% per-tick rate limit. Replay confirmed trade survives.
- **scout-report** (quality 0.80, 1 pair): 5 trades, 3W/2L, +$83.16. Scout attribution broken (all finding_id=NULL). Oscillator gate blocked 73 bad entries. Fewer trades = more profit.
- **connection-doctor** (quality 0.65, 1 pair): Health check — 101 healthy DBs, 4 repair items skipped (on-demand servers + CLAUDE.md stale refs). 4 incidents resolved.

## 📝 Cowork distillation run — 2026-04-04
**Date:** 2026-04-04T22:00:00-07:00
**Type:** note
**Tags:** distillation, training-data, cowork

> Extracted 2 pairs (2 with CoT) from 2 sessions. Domains: trading (1), system (1). Total cowork pairs in DB: 48. Grand total all sources: 9,989 (OpenClaw 2,417 + Claude Code 7,524 + Cowork 48). Script ran but found 0 new JSONL transcripts (sandbox can't access ~/.claude/projects); pairs confirmed present from host-side insertion.

### Sessions captured:
- **nightly-sentry** (quality 0.90, 1 pair): Post-mortem for 2026-04-03 — 5 trades, 60% WR, +3.6 pips. Critical finding: finding_id NULL on 100% of trades (91 over 7 days), indicator coverage regressed to 40%, flight recorder DB empty. GBP_JPY concentrated all losses.
- **connection-doctor** (quality 0.65, 1 pair): Routine health check — database connectivity scan, MCP server pings, stale connection cleanup. No critical issues.

## 📝 Cowork distillation run — 2026-04-05
**Date:** 2026-04-05T22:00:00-07:00
**Type:** note
**Tags:** distillation, training-data, cowork

> Extracted 4 pairs (3 with CoT) from 4 sessions. Domains: trading (3), system (1). Total cowork pairs in DB: 52. Grand total all sources: 9,993 (OpenClaw 2,417 + Claude Code 7,524 + Cowork 52). CoT rate: 90% (47/52).

### Sessions captured:
- **sl-audit** (quality 1.0, 1 pair): Deep audit of 31 losing trades — identified 10 killed by hard SL, pulled M15 candles from OANDA, proved 9/10 would survive with structural EMA-aware SL. 171.8 pips / $798.91 recoverable. Structural SL (E100+buffer) beat ATR-3x in 6/9 cases.
- **nightly-sentry-apr6** (quality 1.0, 1 pair): 79 trades 7-day rolling, 54.4% WR but -201.8 net pips (R:R inversion). finding_id NULL day 10+, V4_EARLY_WARNING worst setup at -73.5 pips, dead market entries 25% of losses.
- **nightly-sentry-apr3** (quality 0.95, 1 pair): 5 trades, 60% WR, +3.6 pips. finding_id NULL regression confirmed across 91 trades. Indicator coverage regressed to 40%. Flight recorder DB empty.
- **connection-doctor** (quality 0.65, 1 pair): Routine health check — 101/106 DBs healthy, 4 warning incidents (all expected offline services). No repairs needed.

## 📝 Cowork distillation run — 2026-04-06
**Date:** 2026-04-06T22:00:00-07:00
**Type:** note
**Tags:** distillation, training-data, cowork

> Extracted 0 new pairs from 0 sessions. No user-driven Cowork sessions today — all activity was automated scheduled tasks (connection doctor, nightly sentry, scout report). Total cowork pairs in DB: 52. Grand total all sources: 9,993 (OpenClaw 2,417 + Claude Code 7,524 + Cowork 52). CoT rate: 90% (47/52). 52 pairs pending export.

## 📝 Cowork distillation run — 2026-04-07
**Date:** 2026-04-07T23:11:00Z
**Type:** note
**Tags:** distillation, training-data, cowork

> Extracted 4 pairs (4 with CoT) from 4 sessions. Domains: trading (3), system (1). Total cowork pairs in DB: 56. Sessions: audit-massive-loss-trade-closure (SL analysis with OANDA candle data), nightly-learning-sentry (30-day metrics + condition effectiveness), daily-scout-report (pipeline conversion + phantom trades), connection-doctor (repair queue triage). All pairs quality score >= 0.8.

## 📝 Cowork distillation run — 2026-04-08
**Date:** 2026-04-08T12:00:00Z
**Type:** note
**Tags:** distillation, training-data, cowork

> Extracted 4 pairs (4 with CoT) from 3 sessions. Domains: trading (4). Total cowork pairs in DB: 60. Sessions: optimizer-v2-audit (cross-comparison of two optimizer upgrade plans — 7 divergence analysis with recommendations, Claude Code brief with 6 amendments), nightly-learning-sentry (4 trades 2W/2L, BB width as predictor, scout indicator gap), daily-scout-report (watch system disconnected 2nd day, bb_expanding as win discriminator). All pairs quality >= 0.85. Highlight: optimizer audit pair is highest-quality trading architecture CoT yet captured — detailed plan comparison with specific cap recommendations and statistical reasoning.

## 📝 Cowork distillation run — 2026-04-09
**Date:** 2026-04-09T23:15:00Z
**Type:** note
**Tags:** distillation, training-data, cowork

> Extracted 5 pairs (5 with CoT) from 5 sessions. Domains: trading (4), system (1). Total cowork pairs in DB: 69. Sessions: audit-forex-tuning (6 hardcoded gates bypassing tc_get() identified and disabled — root cause of EUR/AUD snipe blocks), audit-massive-loss-trade-closure (9/10 SL-killed trades would survive with EMA-aware structural SL — 171.8 pips / $798.91 saved), nightly-learning-sentry (perfect 7W-0L +27.1 pips, timezone bug fix, case sensitivity fix), daily-scout-report (USD_CHF blind spot — 4 winning trades with zero scout coverage, watch pipeline still disconnected), connection-doctor (journal corruption repair on 2 DBs, 101/108 databases healthy). All pairs quality 0.90 avg. Highlight: gate-disabling audit is a strong architectural CoT — vault-informed decision making with safety/quality gate classification.

## 📝 Cowork distillation run — 2026-04-12
**Date:** 2026-04-12T12:00:00Z
**Type:** note
**Tags:** distillation, training-data, cowork

> Extracted 4 pairs (4 with CoT) from 3 sessions. Domains: trading (4). Total cowork pairs in DB: 73. Sessions: audit-forex-tuning-optimization (trade 5230 root cause — guardian SL widening chain of failure, 3 protection proposals, optimizer parameter brief for ratchet_activation/max_loss/sl_widen_atr_mult), audit-massive-loss-trade-closure (31 losers audited, 10 SL-killed, 9/10 saved by structural SL — 171.8 pips/$798.91), daily-scout-report (perfect 7/7 +27.1p, USD_CHF blind spot, watch pipeline disconnect persists). All pairs quality >= 0.80 avg 0.88. Highlight: trade 5230 root cause analysis is the strongest guardian architecture CoT yet — traces exact failure chain from SL widening → ratchet threshold miss → threat scoring lag, with quantified protection proposals.

## 📝 Cowork distillation run — 2026-04-13
**Date:** 2026-04-13T00:00:00Z
**Type:** note
**Tags:** distillation, training-data, cowork

> Extracted 0 new pairs (0 with CoT) from 0 new sessions. Distiller reported 48 transcripts already processed, no new Cowork JSONLs in ~/.claude/projects/. Total cowork pairs in DB: 76 (70 with CoT, 76 pending export). Comparison: openclaw=2417 (846 pending), claude_code=7524 (3582 pending).

## 📝 Cowork distillation run — 2026-04-17
**Date:** 2026-04-17T23:15:00Z
**Type:** note
**Tags:** distillation, training-data, cowork

> Extracted 4 pairs (4 with CoT) from today's scheduled-task Cowork sessions. Domains: system (2), trading (1), architecture (1). Total cowork pairs in DB: 80. Sessions captured: scout-daily-report (4W/2L net -0.6 pips, scout→snipe promoter broken with 72 findings→0 conversions, BB-threshold propagation bug confirmed 3rd time, 18 tuning overrides shipped post-market), connection-doctor-1 (4 pending items, on_demand false-positive root cause traced to non-reloaded cycle.py), connection-doctor-2 (85 pending items processed, mlx_cro added to expected_state, FUSE/SQLite workaround applied: journal_mode=MEMORY + synchronous=OFF), connection-doctor-3 (same root cause, in-place cycle.py patch, host-side cleanup script handed off). All quality >= 0.80, avg 0.88.
>
> **Distiller issue uncovered:** `Core/cowork_distiller.py` expects a top-level `role`/`content` schema but the on-disk JSONL (`~/.claude/projects/*/*.jsonl`) uses a nested `message.role`/`message.content` schema with `type=user|assistant|queue-operation|attachment|ai-title`. The script found 1 transcript today but extracted 0 pairs because of this schema mismatch — all new extractions went through a manual fallback path. Distiller needs a format updater to handle the current Cowork transcript structure.
>
> **Sandbox note:** SQLite writes to `session_training.db` from this Cowork sandbox require `PRAGMA journal_mode=MEMORY` + `synchronous=OFF` to avoid `SQLITE_IOERR` on the FUSE mount — same root cause as the connection_doctor DB issue described in today's repair runs.

## 📝 Cowork distillation run — 2026-04-18
**Date:** 2026-04-18T23:15:00Z
**Type:** note
**Tags:** distillation, training-data, cowork

> Extracted 3 pairs (3 with CoT) from today's scheduled-task Cowork sessions. Domains: system (3). Total cowork pairs in DB: 83 (77 with CoT, 83 pending export). Sessions captured: connection-doctor-1 (4 pending → 0, fixed CLAUDE.md stale refs via docs/ → all_md_plans/ + trevor_database.db relocation + 3 archive annotations; skipped mlx/ollama API_ERRORs via on-demand-lifecycle pattern match; diagnosed virtiofs + stale rollback-journal, workaround = nolock=1 URI + journal_mode=OFF), connection-doctor-2 (empty queue, classified 7 open incidents as non-actionable by duplicate-match against last 24h repair_queue; flagged FTS index disk-I/O as watch-item even though markdown write succeeded), connection-doctor-3 (empty queue + FlightRecorderV2 disk I/O recurrence, recommended checkpoint/VACUUM if it persists). All quality >= 0.82, avg 0.88.
>
> **Distiller behavior this run:** `Core/cowork_distiller.py` scanned ~/.claude/projects/ and reported "0 new, 52 already processed" — same schema/path-filter mismatch uncovered on 2026-04-17 (script's `if 'sessions' in str(jsonl).lower()` filter matches 0 of 961 JSONLs because scheduled-task Cowork sessions live in the ephemeral sandbox, not in ~/.claude/projects/). Manual fallback (`training_data/sessions/cowork_insert_2026_04_18.py`) used to insert today's 3 pairs. `read_transcript` MCP exposes assistant-side only; instruction was reconstructed from the scheduled-task description in the scheduled-tasks registry.
>
> **System signal worth escalating:** FlightRecorderV2 (`connection_doctor/flight_recorder_v2.py`) forcing `journal_mode=DELETE` keeps blocking `snapshot()` from the Cowork sandbox — three separate runs today hit the same `disk I/O error` on the virtiofs mount. Workaround documented in connection-doctor-1 response. If Cowork-initiated connection-doctor runs are a supported path, `_open_connection()` should accept a `nolock=1` override or fall back to `journal_mode=OFF` when it detects a non-host filesystem.

## 📝 Cowork distillation run — 2026-04-19
**Date:** 2026-04-20T00:09:11Z
**Type:** note
**Tags:** distillation, training-data, cowork

> Extracted 1 new pair (1 with CoT) from today's Cowork sessions. Distiller script reported 0 new transcripts (`Core/cowork_distiller.py` scans `~/.claude/projects/` via `Path.home()` which resolves to the sandbox home, not Tim's Mac — same scoped-filter issue logged 2026-04-17/18). Manual fallback via `list_sessions` + `read_transcript` captured one high-quality CoT pair from today's "Audit and import existing skills" Cowork session: a plugin-install bisection debug with Step 1 (confirm installer works via 1KB hello-test), Step 2 (3-file small-scale category bisect — all passed), Step 3 (full-scale single-category bisect staged for Tim to install). Domain: system. Quality 0.85. Today's total: 4 cowork rows created (3 earlier connection-doctor rows + 1 plugin-bisect). Cowork total in DB: 84 (78 with CoT, 84 pending export). Grand totals: OpenClaw 2,417 (846 pending), Claude Code 7,524 (3,582 pending), Cowork 84 (84 pending). CoT rate cowork: 92.9%.
>
> **Sandbox FUSE note (recurring):** `session_training.db` writes blocked by stale rollback-journal from an earlier writer (37,448 bytes from 20:05) — `unlink()` not permitted on the virtiofs bindfs mount, `rename()` was. Workaround applied: `mv ...db-journal ...db-journal.stale` + reconnect with `nolock=1` URI + `PRAGMA journal_mode=OFF` + `synchronous=OFF`. Same pattern as 2026-04-17/18 runs. Worth escalating — every scheduled Cowork distill on this sandbox path will re-hit this unless the writer changes to WAL + nolock or the distiller runs host-side.
>
> **Schema/path gap on distiller (persistent):** `Core/cowork_distiller.py` has never successfully auto-picked up transcripts in the sandbox because (a) `Path.home()/".claude"/"projects"` points to the sandbox home, not the host, and (b) filename filter doesn't match current transcript naming. Consider a `--source-dir` flag or a scheduled host-side run paired with a sandbox-side import from `~/Jarvis/training_data/sessions/inbox/`.


## Cowork distillation run — 2026-04-20
**Date:** 2026-04-21T03:15:35+00:00
**Type:** note
**Tags:** distillation, training-data, cowork

> Extracted 4 pairs (4 with CoT) from 4 sessions (nightly_learning_sentry, connection_doctor_repair, daily_scout_report, cowork_cot_distiller). Domains: trading(2), system(1), architecture(1). Total cowork pairs in DB: 92. Pending export: 92. OpenClaw 2,417 + Claude Code 7,524 + Cowork 92 = 10,033 training pairs across all sources.
