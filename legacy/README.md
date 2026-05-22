# Legacy — the architectural journey

This directory holds code from earlier eras of Jarvis. **It's not dead weight — it's the trail of how the system got to its current shape.** Keeping it here so the architectural progression is legible to anyone landing on the repo cold.

## The journey

### Era 1 — local NLP without a local LLM (2024–early 2025)

When Jarvis started, **running a meaningfully capable LLM locally on consumer hardware wasn't an option.** Distilled local models small enough to fit in Mac Studio RAM and good enough to drive an assistant didn't exist yet (or weren't accessible). So the original architecture leaned on:

- **spaCy** for parsing, vector similarity, and entity extraction
- A hand-trained **intent classifier (PyTorch `nn.Module`)** for routing (`legacy/intent-classifier-v1/intent_classifier_v1.py` — see the `class IntentClassifier(nn.Module)` and `class TrevorCore` inside; the file was previously named `tc_test.py`)
- A library of **pattern matchers** (`Core/pattern_manager.py`, the 5,555+ rows in `trevor_database.db:pattern_data`)
- **TTS pipeline** for the voice surface (whisper input → classified intent → routed → response → TTS output)
- An older **React UI** (`Core/user_ux/frontend/`) on top of a Flask + Socket.IO backend (`Core/user_ux/boardroom_api.py`)
- A pre-distillation **pain tracking** module (`Core/pain_manager.py`, `legacy/pain-manager-v2/pain_manager_v2.py` — the v2 was a parallel rewrite that didn't ship)

The pipeline worked but was constrained by the limits of pattern-based routing — adding a new capability meant adding patterns + retraining the classifier.

### Era 2 — distilled local model arrives (mid-2025 →)

When **Qwen3.5-35B-A3B 4-bit** + LoRA fine-tuning became viable on Apple Silicon (MLX), the architecture pivoted:

- Replace the rigid pattern→intent→handler pipeline with **5-layer scoring routing** (patterns + spaCy vectors + docstring semantics + capability search + **LLM fallback**) — the new layers slot ON TOP of the legacy infrastructure rather than replacing it
- Move from a single conversation surface to **Workspaces** (forex-trading-team, marketing, etc.) — each its own daemonized product running on the shared orchestrator
- Introduce **BoardRoom** — multi-seat strategic deliberation on shared MLX servers — for genuinely complex requests
- Spin up the **FastAPI MLX gateway** with priority queueing so one Qwen 35B serves Trevor + OpenClaw + Claude Code + BoardRoom + sub-agents simultaneously
- Replace the React UI with **`trevor_desktop.html`** (vanilla JS, 234 KB, single-page) at the top of the repo

### What's here in `legacy/`

| Path | What | Why preserved |
|---|---|---|
| `intent-classifier-v1/intent_classifier_v1.py` | The pre-distillation intent routing brain — PyTorch `nn.Module` trained on the 5,555-pattern dataset. Previously misleadingly named `tc_test.py` (it's not a test). | The architectural ancestor of the current 5-layer router's Layer 1. Shows the routing problem being solved with the tools available at the time. |
| `pain-manager-v2/pain_manager_v2.py` | An unshipped rewrite of the pain-point tracking module. | Documents a fork in the road — `Core/pain_manager.py` (the v1) remained in production. |

### What's NOT in `legacy/` but is still load-bearing legacy

A few pieces of the Era 1 stack are **still used by the current architecture** — moving them would break imports. They stay where they are, with a note in their classification entries:

- `Core/pattern_manager.py` + `trevor_database.db:pattern_data` (5,555 patterns) — used as Layer 1 of the current router
- `Core/pain_manager.py` — imported by current `trevor_core.py` (line 238: `from Core.pain_manager import PainManager`); active even though it predates distillation
- `Core/user_ux/boardroom_api.py` — its `socketio` instance is referenced by `Jarvis_Agent_SDK/boardroom_connector.py` and `Handler/handler_terminal.py` for real-time UI updates. The wider `user_ux/` React frontend is no longer the primary UI (`trevor_desktop.html` superseded it), but this one module survives as the SocketIO host
- `Core/command_mapping.py` / `Core/intents.py` (if present) — pattern-driven dispatch fallbacks

### Why this matters for a reviewer

The repo's "today" is the 35B+BoardRoom+Workspaces stack. The repo's "yesterday" is right here, intact. The progression — from constrained local NLP → distilled local model → shared multi-tenant gateway → multi-seat deliberation — is the actual engineering story. **Keeping the legacy in view, not deleting it, makes that story legible.**
