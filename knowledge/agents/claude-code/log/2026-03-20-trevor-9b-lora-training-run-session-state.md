---
type: note
created: 2026-03-20
tags: [training, lora, 9b, trevor, distillation]
agent: log
decomposed_from: agents/claude-code/log/2026-03.md
---

## 📝 trevor-9b LoRA training run — session state 2026-03-20
**Date:** 2026-03-20T07:38:44
**Type:** note
**Tags:** training, lora, 9b, trevor, distillation

Training run in progress: 6 layers, 2000 iters, lr 3e-5, filtered dataset (8428 examples, removed 606 long-sequence dumps). At iter 1750/2000 as of writing. Peak mem 42.976GB stable. Previous crashes were caused by: (1) unfiltered data had 219 examples with 16k+ tokens causing Metal GPU command buffer timeouts, (2) resume-adapter-file destabilizes Metal allocator — always start fresh. Filtered data path: ~/jarvis/training_data/sessions/_lora_filtered_9b/. Adapter saves every 200 iters to ~/jarvis/models/adapters/ta_9b/. After training: run --skip-train to fuse adapter and load into Ollama as trevor-9b. Test before wiring as subagent model.
