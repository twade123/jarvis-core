---
type: note
created: 2026-03-20
tags: [cro-mlx, service-outage, port-11500, infrastructure, audit-2026-03-20-phase3]
agent: log
decomposed_from: agents/claude-code/log/2026-03.md
---

## ⚠️ CRO-mlx service (port 11500) down since ~15:51 UTC
**Date:** 2026-03-20T20:00:06
**Type:** note
**Tags:** cro-mlx, service-outage, port-11500, infrastructure, audit-2026-03-20-phase3

CRO-mlx service on port 11500 has been down since approximately 15:51 UTC on 2026-03-20. This affects any agent or pipeline component that depends on local MLX model inference. Need to investigate whether the process crashed, was OOM-killed, or if the port is being held by a zombie process.

**Evidence:** Service unreachable on port 11500 since ~15:51 UTC.
