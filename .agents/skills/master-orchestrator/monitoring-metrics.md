# Monitoring Metrics for Domain Orchestrator Performance

Track performance metrics across all domain orchestrator instances to enable bottleneck detection and capacity planning.

---

## 1. Core Metrics Tracked Per Domain Orchestrator

### Queue Depth
**Definition**: Number of tasks currently waiting for domain orchestrator coordination.

**Measurement**: Count of tasks in orchestrator's coordination queue (not yet delegated to worker agents).

**Significance**: Direct indicator of coordination backlog. High queue depth means orchestrator cannot delegate tasks fast enough.

### Response Time
**Definition**: Time from task assignment to domain orchestrator delegation to worker agent.

**Measurement**: Duration in seconds from when Master Orchestrator assigns task to domain orchestrator, until domain orchestrator delegates to specific worker agent.

**Significance**: Measures coordination overhead. Slow response indicates orchestrator is overwhelmed with management duties.

### Active Agent Count
**Definition**: Number of worker agents currently managed by the domain orchestrator.

**Measurement**: Count of agents in "active" state (working on tasks or recently communicated).

**Significance**: Cognitive capacity indicator. Managing many agents increases coordination overhead.

### Task Complexity Score
**Definition**: Weighted complexity of tasks currently in orchestrator's queue.

**Measurement**: Sum of complexity scores (1-10 scale) for all queued tasks.

**Significance**: Queue of 5 complex tasks may be worse than queue of 10 simple tasks. Provides context for queue depth.

### Throughput
**Definition**: Rate of task delegation from domain orchestrator to worker agents.

**Measurement**: Count of tasks delegated per minute (rolling average).

**Significance**: Measures orchestrator productivity. Declining throughput indicates coordination bottleneck.

### Error Rate
**Definition**: Failed delegations or coordination errors per hour.

**Measurement**: Count of delegation failures, agent spawn failures, or communication errors per hour.

**Significance**: High error rate indicates orchestrator is struggling (overloaded or encountering systemic issues).

---

## 2. Metric Collection Patterns

### Real-Time Tracking
**When**: Metrics updated immediately when domain orchestrator reports status.

**Events that trigger updates**:
- Task assigned to orchestrator → queue depth +1
- Task delegated to worker → queue depth -1, response time recorded
- Agent spawned → active agent count +1
- Agent completed → active agent count -1
- Delegation error → error rate +1

**Storage**: Current metric values stored in domain orchestrator's workspace metadata.

### Historical Data
**Retention**: Maintain rolling window of last 15 minutes for trend analysis.

**Granularity**: Store metric snapshot every 30 seconds (30 snapshots in 15-minute window).

**Purpose**: Enables trend detection (metrics worsening vs. stable) and sustained threshold detection.

**Storage**: Time-series data in workspace history logs.

### Per-Instance Tracking
**Scope**: Each domain orchestrator instance tracked separately with unique instance ID.

**Example**: `mcp-orchestrator-instance-1`, `mcp-orchestrator-instance-2`, `mcp-orchestrator-instance-3` all have independent metric tracking.

**Purpose**: Identify which specific instance is bottlenecked vs. aggregate domain health.

### Aggregated View
**Scope**: Overall health per domain type (sum across all instances).

**Calculation**: Aggregate metrics (sum queue depth, average response time, sum agent count) across all instances of same domain type.

**Purpose**: Bottleneck detection runs on aggregate to determine if domain needs additional capacity.

**Example**: If 2 MCP orchestrator instances each have queue depth 7, aggregate queue depth is 14 (exceeds threshold of 10).

---

## 3. Metric Analysis Methods

### Queue Depth Analysis

**Current Queue Size vs. Historical Average**:
- Compare current queue depth to rolling average over last 5 minutes
- Significant if current > average by 50% or more
- Example: Average queue 4, current queue 8 → 100% increase → concerning

**Queue Growth Rate**:
- Tasks added per minute vs. tasks delegated per minute
- Positive growth rate (more added than delegated) → queue accumulating
- Formula: `growth_rate = tasks_added_per_min - tasks_delegated_per_min`
- Sustained positive growth rate indicates bottleneck forming

**Queue Age**:
- How long oldest task has been waiting in queue
- Threshold: Oldest task waiting > 2 minutes → coordination delay
- Combines with queue depth: Large queue with old tasks is worse than large queue with new tasks

### Response Time Analysis

**Current Average Response Time vs. Baseline**:
- Compare current average to 30-second threshold
- Significant if current > 30 seconds
- Example: Average response time 45 seconds → exceeds baseline → bottleneck indicator

**P95 Response Time** (95th percentile):
- Catches outliers that inflate average
- 95% of tasks delegated within this time
- More robust than simple average for spiky workloads
- Threshold: P95 > 60 seconds → severe coordination delay

**Trend Analysis**:
- Is response time increasing or stable over time?
- Compare last 2 minutes to previous 3 minutes
- Increasing trend more concerning than stable at threshold
- Stable at threshold may indicate orchestrator is handling load (just at capacity)

### Agent Count Analysis

**Current Active Agents vs. Capacity Threshold**:
- Compare current count to threshold of 15 agents
- Significant if current > 15
- Example: 18 active agents → exceeds capacity → cognitive overload

**Agent Utilization Rate**:
- Percentage of agents actively working vs. idle
- Formula: `utilization = (working_agents / total_agents) * 100`
- High utilization (>80%) with many agents indicates both high demand and high coordination load

**Cognitive Load Estimation**:
- Complex tasks count heavier than simple tasks for agent management
- Formula: `cognitive_load = sum(agent_complexity_scores)`
- Example: 10 agents on complex tasks (score 8 each) = 80 load
           15 agents on simple tasks (score 2 each) = 30 load
- Provides context for agent count metric

---

## 4. Threshold Definitions

*From orchestrator_architecture_patterns.md research (Phase 1)*:

### Queue Depth Threshold: > 10 tasks
**Rationale**: Queue of 10+ tasks indicates orchestrator cannot delegate fast enough to keep up with incoming work.

**Action**: Potential bottleneck detected when sustained.

### Response Time Threshold: > 30 seconds
**Rationale**: Coordination should be near-instantaneous. Response time > 30s indicates orchestrator is spending excessive time on management overhead.

**Action**: Coordination overhead too high when sustained.

### Agent Count Threshold: > 15 agents
**Rationale**: Managing 15+ agents approaches cognitive capacity limit. Each agent requires coordination, status tracking, and communication.

**Action**: Approaching cognitive capacity when sustained.

### Combined Score Threshold
**Formula**: `combined_score = (queue_depth/10) + (response_time/30) + (agent_count/15)`

**Interpretation**:
- Score < 1.0: All metrics below threshold (healthy)
- Score 1.0-2.0: One metric at/above threshold (watch)
- Score 2.0-3.0: Multiple metrics at/above threshold (bottleneck likely)
- Score > 3.0: All metrics above threshold (severe bottleneck)

**Action**: Combined score > 2.0 sustained for 2+ minutes → trigger bottleneck detection.

---

## 5. Metric Reporting Protocol

### Domain Orchestrator Reporting Events

**Task Assignment** (Master → Domain):
- Update: `queue_depth += 1`
- Timestamp: Record time of assignment
- Complexity: Store task complexity score with queue entry

**Task Delegation** (Domain → Worker):
- Update: `queue_depth -= 1`
- Calculate: `response_time = delegation_time - assignment_time`
- Record: Add response time to rolling history
- Update: `throughput` (recalculate tasks per minute)

**Agent Spawn**:
- Update: `active_agent_count += 1`
- Record: Agent instance ID and spawn timestamp
- Track: Agent assignment (which task delegated to new agent)

**Agent Completion**:
- Update: `active_agent_count -= 1`
- Record: Agent completion timestamp and outcome
- Calculate: Agent session duration for capacity planning

**Delegation Error**:
- Update: `error_rate += 1`
- Record: Error type, timestamp, context
- Log: Full error details for debugging

### Master Orchestrator Aggregation

**Frequency**: Aggregate metrics every 30 seconds across all domain orchestrator instances.

**Process**:
1. Query each domain orchestrator instance for current metrics
2. Sum queue depths across all instances of same domain type
3. Average response times across instances
4. Sum active agent counts across instances
5. Store aggregate metrics in Master Orchestrator workspace metadata

**Usage**: Aggregated metrics used for bottleneck detection (not per-instance metrics).

### Workspace Metadata Storage

**Location**: Each domain orchestrator stores metrics in its workspace metadata table.

**Schema**:
```
workspace_id: {domain}-orchestrator-{instance}
metrics_timestamp: 2026-02-04T14:24:15Z
queue_depth: 12
avg_response_time: 35.2
active_agent_count: 18
task_complexity_score: 84
throughput: 1.8
error_rate: 0.5
```

**Historical Snapshots**: Store last 30 snapshots (15 minutes at 30s intervals) for trend analysis.

---

## 6. False Positive Prevention

### Sustained Threshold Requirement
**Rule**: Metric must exceed threshold for 2+ minutes (not just single spike).

**Implementation**: Check that at least 3 of 4 measurements (in 2-minute window) exceed threshold.

**Rationale**: Prevents false positives from temporary task bursts. Brief spike in queue → no spawn. Sustained overload → spawn triggered.

**Example**:
- Measurement 1: Queue 15 (exceeds)
- Measurement 2: Queue 8 (below)
- Measurement 3: Queue 12 (exceeds)
- Measurement 4: Queue 14 (exceeds)
- Result: 3 of 4 exceed → sustained threshold met → bottleneck confirmed

### Multi-Metric Confirmation
**Rule**: At least 2 of 3 core metrics must indicate bottleneck.

**Rationale**: Single metric spike may not represent true bottleneck. Multiple metrics aligning confirms overload.

**Examples**:
- Queue 15 + Response 35s → both exceed → bottleneck (even if agent count normal)
- Queue 15 only (response 20s, agents 10) → single metric → not bottleneck
- Queue 15 + Response 35s + Agents 18 → all three → severe bottleneck

### Trend Analysis Requirement
**Rule**: Metrics must be worsening (not stable at threshold).

**Implementation**: Compare recent 2-minute average to previous 3-minute baseline. Recent must exceed baseline by 10%+.

**Rationale**: Stable metrics at threshold may indicate orchestrator is handling load (just at capacity). Worsening trend indicates orchestrator losing battle with incoming work.

**Example**:
- Baseline (minutes 0-3): Average queue 11
- Recent (minutes 3-5): Average queue 11
- Result: Stable at threshold → no spawn (orchestrator handling it)

- Baseline (minutes 0-3): Average queue 9
- Recent (minutes 3-5): Average queue 13
- Result: Worsening by 44% → spawn (orchestrator losing ground)

### Cooldown Period
**Rule**: 5-minute cooldown after spawning new instance before detecting new bottleneck.

**Rationale**: New instance needs time to accept tasks and reduce aggregate load. Immediate re-detection would cause cascade of unnecessary spawns.

**Implementation**: Track last spawn timestamp per domain type. Skip bottleneck detection if within 5 minutes of last spawn.

**Exception**: Severity 10 (critical bottleneck) bypasses cooldown and triggers immediate spawn.

---

*Referenced by @./bottleneck-detection.md for detection algorithms*
