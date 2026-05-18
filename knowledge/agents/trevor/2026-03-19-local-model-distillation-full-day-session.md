---
type: note
created: 2026-03-19
tags: [local-model, distillation, ollama, training, gguf-conversion]
agent: trevor
decomposed_from: agents/trevor/learnings.md
---

## 📝 Local model distillation — full day session 2026-03-19
**Date:** 2026-03-19T12:30:00
**Type:** note
**Tags:** local-model, distillation, ollama, training, gguf-conversion

Built 9,509 pair combined dataset from all sources (Trevor sessions, Claude Code, trading outcomes, vault, flight recorder, annotated charts). Trained LoRA adapter on MLX 4-bit Qwen3.5-35B-A3B. Attempted MLX→GGUF conversion multiple ways — all failed due to MLX quantization format incompatibility with llama.cpp converter. Base qwen3.5:35b-a3b-q4_K_M now running in Ollama as primary OpenClaw model. Adapter (combined_35b_peft) exists but requires Ollama LoRA runtime support (not yet available). Architecture decision: 35B for validator/reasoning, 9B for all sub-agents. Conversation capture wired into floor_chat and boardroom. DO NOT train HF float16 on M1 Max — always OOMs (GPU cap 55GB, model needs 70GB).
