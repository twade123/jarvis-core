---
type: discovery
created: 2026-03-20
tags: [training, lora, mlx, metal, 9b, lessons]
agent: log
decomposed_from: agents/claude-code/log/2026-03.md
---

## 💡 trevor-9b LoRA training — key lessons on MLX/Metal crashes
**Date:** 2026-03-20T07:39:19
**Type:** discovery
**Tags:** training, lora, mlx, metal, 9b, lessons

Key lessons from training 9B LoRA on M1 Max 64GB: (1) Metal ImpactingInteractivity crash is NOT OOM — it is macOS killing GPU command buffer for taking too long. Caused by long sequences (4448 tokens) even when truncated to 1024. Fix: filter training data, not reduce layers. (2) Resume-adapter-file does NOT restore optimizer state in MLX — starts gradients fresh on shifted weights, destabilizes Metal allocator. Always train from scratch. (3) Filtered dataset path: ~/jarvis/training_data/sessions/_lora_filtered_9b — 8428 examples, all under 4000 chars (~1000 tokens). The 606 removed examples were session dumps and vault doc retrievals, not coding CoT. (4) Stable config: 6 layers, lr 3e-5, batch 1, seq 1024, grad-checkpoint, filtered data. Peak mem 42.976GB stable. (5) Qwen3.5 35B-A3B is NEWER than Qwen3 32B — released Feb 2026 vs Sep 2025. Already on latest architecture.
