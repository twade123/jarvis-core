---
type: note
created: 2026-03-17
tags: [35B, vision, training, distillation, overnight]
agent: trevor
decomposed_from: agents/trevor/learnings.md
---

## 📝 35B vision working + training data complete for overnight run (5,502 pairs)
**Date:** 2026-03-17T19:58:16
**Type:** note
**Tags:** 35B, vision, training, distillation, overnight

2026-03-17 evening session completions:

1. 35B VISION FIXED: mlx_vlm/server.py patched in 2 places.
   - Qwen3 models were stripping images and using text-only path
   - Patch: skip text shortcut when images present, add enable_thinking=False to vision path
   - 35B now sees charts in 4-10s at 21.4GB peak memory
   - Verbose output is base model behavior, LoRA training fixes it

2. TRAINING DATA BACKFILLED:
   - validator_35b: 356 → 1,503 pairs (discovered 60 days of trade_decisions in DB)
   - trevor_35b: 3,703 → 3,999 pairs (fixed recursive glob for Claude Code subdir sessions)
   - Total overnight: 5,502 pairs across both models
   - 12 negative examples (CONFIRM→LOSS with correction notes)

3. OVERNIGHT TRAINING: fires 10:30pm ET, done before 3am London open
   - trevor_35b: 150 iters on 3,999 pairs (~2h)
   - validator_35b: 100 iters on 1,503 pairs (~1h)
   - Script: ~/jarvis/scripts/overnight_training.sh
   - Stops 9B server during training for memory headroom

4. ARCHITECTURE: 35B path to replace Anthropic API calls
   - Multi-teacher: Sonnet + DeepSeek R1 + Claude Code + itself
   - Learns reasoning styles not personalities
   - Test plan: validator first → OpenClaw model.primary → Claude Code
   - Correction loop (35B wrong → Sonnet corrects → new training pair) = compounding
