# Bottleneck Detection Algorithms

Identify when domain orchestrators are overloaded and require additional instances to maintain system responsiveness.

---

## 1. Detection Algorithm Overview

### Purpose
Determine when a domain orchestrator needs an additional instance spawned to handle increased load and prevent task queuing delays.

### Inputs
Real-time metrics from @./monitoring-metrics.md:
- Queue depth (current and historical)
- Average response time (current and trend)
- Active agent count (current utilization)
- Task complexity scores
- Throughput rate
- Error rate

### Output
**Boolean decision**: Spawn new instance (true/false)
**Severity score**: 1-10 scale indicating bottleneck severity

### Execution Frequency
Run detection algorithm every 30 seconds for continuous monitoring of all domain orchestrator instances.

### Integration Point
Master Orchestrator runs detection algorithm as part of its core monitoring loop. Detection output feeds into spawning-algorithms.md decision process.

---

## 2. Primary Detection Algorithm

### Algorithm Pseudocode

```python
function detect_bottleneck(domain_orchestrator):
    """
    Detect if domain orchestrator is bottlenecked and needs additional instance.

    Args:
        domain_orchestrator: Domain orchestrator instance or aggregate metrics

    Returns:
        (bottleneck_detected: bool, severity: int 1-10)
    """
    # Step 1: Gather current metrics
    metrics = get_metrics(domain_orchestrator)

    # Step 2: Check core thresholds
    queue_exceeded = metrics.queue_depth > 10
    response_exceeded = metrics.avg_response_time > 30  # seconds
    agent_exceeded = metrics.active_agent_count > 15

    # Step 3: Count how many thresholds exceeded
    threshold_count = sum([queue_exceeded, response_exceeded, agent_exceeded])

    # Step 4: Multi-metric confirmation (require at least 2 of 3)
    if threshold_count < 2:
        # Single metric spike - not confirmed bottleneck
        return False, 0

    # Step 5: Check sustained threshold (must persist 2+ minutes)
    if not sustained_threshold(domain_orchestrator, threshold_count, duration=120):
        # Temporary spike - not sustained bottleneck
        return False, 0

    # Step 6: Check trend (metrics must be worsening, not stable)
    if not worsening_trend(domain_orchestrator):
        # Stable at threshold - orchestrator handling load
        return False, 0

    # Step 7: Check cooldown (no recent spawn in last 5 minutes)
    if in_cooldown_period(domain_orchestrator, cooldown=300):
        # Recent spawn - wait for new instance to stabilize system
        return False, 0

    # Step 8: Calculate severity score (1-10 scale)
    severity = calculate_severity(metrics)

    # Bottleneck confirmed - spawn required
    return True, severity
```

### Key Decision Points

**Multi-Metric Confirmation** (Step 4):
- Prevents false positives from single metric spikes
- At least 2 of 3 core metrics must exceed threshold
- Examples:
  - Queue 15 + Response 35s → confirmed (even if agents normal)
  - Queue 15 only → not confirmed (single metric)
  - All three exceeded → severe bottleneck

**Sustained Threshold** (Step 5):
- Prevents spawning for temporary bursts
- Metrics must exceed threshold for 2+ minutes (4 consecutive measurements)
- Implementation: 3 of last 4 measurements must exceed threshold

**Worsening Trend** (Step 6):
- Prevents spawning when orchestrator is handling load at capacity
- Recent metrics (last 2 min) must exceed baseline (previous 3 min) by 10%+
- Stable metrics at threshold → no spawn

**Cooldown Period** (Step 7):
- Prevents cascade spawning
- 5-minute wait after spawning to allow new instance to stabilize load
- Exception: Severity 10 (critical) bypasses cooldown

---

## 3. Severity Scoring Algorithm

### Scoring Pseudocode

```python
function calculate_severity(metrics):
    """
    Calculate bottleneck severity on 1-10 scale.

    Higher severity indicates more urgent need for additional capacity.

    Args:
        metrics: Current metric values from domain orchestrator

    Returns:
        severity: int 1-10
    """
    # Step 1: Calculate base scores per metric (0-3 points each)

    # Queue depth score: 0 at threshold (10), 3 at 3x threshold (30)
    queue_score = min(3.0, metrics.queue_depth / 10.0)

    # Response time score: 0 at threshold (30s), 3 at 3x threshold (90s)
    response_score = min(3.0, metrics.avg_response_time / 30.0)

    # Agent count score: 0 at threshold (15), 3 at 3x threshold (45)
    agent_score = min(3.0, metrics.active_agent_count / 15.0)

    # Step 2: Calculate growth rate multiplier (1.0-1.5x)
    # Amplifies severity if queue is growing rapidly
    if metrics.queue_growth_rate > 0:
        # Positive growth rate (more tasks arriving than delegating)
        growth_multiplier = 1.0 + min(0.5, metrics.queue_growth_rate / 10.0)
    else:
        # Negative or zero growth rate (handling load)
        growth_multiplier = 1.0

    # Step 3: Calculate raw score (0-13.5 theoretical max)
    # Base max: 3+3+3 = 9, with 1.5x multiplier = 13.5
    raw_score = (queue_score + response_score + agent_score) * growth_multiplier

    # Step 4: Normalize to 1-10 scale
    severity = min(10, max(1, round(raw_score)))

    return severity
```

### Severity Interpretation

**1-3: Minor Bottleneck (Watch)**
- Metrics slightly above thresholds
- No immediate action required
- Monitor for worsening trend
- Example: Queue 12, Response 32s, Agents 16 → Severity 2

**4-6: Moderate Bottleneck (Spawn Soon)**
- Metrics moderately above thresholds
- Spawn recommended within next monitoring cycle
- Impacts user experience if not addressed
- Example: Queue 18, Response 45s, Agents 20 → Severity 5

**7-9: Severe Bottleneck (Spawn Immediately)**
- Metrics significantly above thresholds
- Immediate spawn required to prevent service degradation
- User experience already impacted
- Example: Queue 25, Response 60s, Agents 22 → Severity 8

**10: Critical Bottleneck (Emergency Spawn)**
- All metrics at 2x+ threshold
- Bypass cooldown period
- Consider spawning multiple instances
- User experience severely degraded
- Example: Queue 35, Response 90s, Agents 30 → Severity 10

### Severity Score Examples

| Queue | Response | Agents | Growth | Calculation | Severity |
|-------|----------|--------|--------|-------------|----------|
| 12 | 32s | 16 | 0 | (1.2+1.07+1.07)*1.0 = 3.3 | 3 |
| 18 | 45s | 20 | 2 | (1.8+1.5+1.33)*1.2 = 5.6 | 6 |
| 25 | 60s | 22 | 5 | (2.5+2.0+1.47)*1.5 = 9.0 | 9 |
| 35 | 90s | 30 | 8 | (3.0+3.0+2.0)*1.5 = 12.0 | 10 |

---

## 4. Sustained Threshold Detection

### Purpose
Prevent false positives from temporary task bursts or metric spikes.

### Implementation

**Rolling Window**: Maintain last 4 measurements (2 minutes at 30-second intervals).

**Threshold Rule**: At least 3 of 4 measurements must exceed threshold.

**Measurement Storage**:
```python
# Example metric history structure
metric_history = [
    {"timestamp": "14:20:00", "queue": 15, "response": 35, "agents": 18},
    {"timestamp": "14:20:30", "queue": 8,  "response": 25, "agents": 16},
    {"timestamp": "14:21:00", "queue": 12, "response": 38, "agents": 19},
    {"timestamp": "14:21:30", "queue": 14, "response": 42, "agents": 20}
]
```

### Algorithm Pseudocode

```python
function sustained_threshold(domain_orchestrator, threshold_count, duration=120):
    """
    Check if threshold exceedance is sustained over time period.

    Args:
        domain_orchestrator: Orchestrator to check
        threshold_count: Number of thresholds currently exceeded (0-3)
        duration: Time period in seconds (default 120 = 2 minutes)

    Returns:
        bool: True if sustained, False if temporary spike
    """
    # Get last N measurements covering duration
    # Duration 120s at 30s intervals = 4 measurements
    measurements_needed = duration / 30
    history = get_metric_history(domain_orchestrator, last_n=measurements_needed)

    # Count how many measurements show threshold_count >= 2
    exceeded_count = 0
    for measurement in history:
        # Recompute threshold_count for this historical point
        q_exceeded = measurement.queue_depth > 10
        r_exceeded = measurement.avg_response_time > 30
        a_exceeded = measurement.active_agent_count > 15

        measurement_threshold_count = sum([q_exceeded, r_exceeded, a_exceeded])

        if measurement_threshold_count >= 2:
            exceeded_count += 1

    # Require 3 of 4 measurements to show threshold exceedance
    sustained = exceeded_count >= 3

    return sustained
```

### Examples

**Example 1: Temporary Spike (Not Sustained)**
```
14:20:00 → Queue 18, Response 35s, Agents 20 → 3 thresholds exceeded
14:20:30 → Queue 7,  Response 22s, Agents 12 → 0 thresholds exceeded
14:21:00 → Queue 9,  Response 28s, Agents 14 → 0 thresholds exceeded
14:21:30 → Queue 8,  Response 25s, Agents 13 → 0 thresholds exceeded

Result: Only 1 of 4 measurements exceeded → NOT sustained → No spawn
```

**Example 2: Sustained Overload (Spawn Required)**
```
14:20:00 → Queue 18, Response 35s, Agents 20 → 3 thresholds exceeded
14:20:30 → Queue 16, Response 38s, Agents 19 → 3 thresholds exceeded
14:21:00 → Queue 14, Response 32s, Agents 18 → 3 thresholds exceeded
14:21:30 → Queue 19, Response 41s, Agents 21 → 3 thresholds exceeded

Result: 4 of 4 measurements exceeded → Sustained → Spawn triggered
```

---

## 5. Trend Analysis Algorithm

### Purpose
Distinguish between orchestrator at stable capacity vs. orchestrator losing battle with incoming load.

### Algorithm Pseudocode

```python
function worsening_trend(domain_orchestrator):
    """
    Determine if metrics are worsening (increasing) over time.

    Stable metrics at threshold → orchestrator handling load (no spawn)
    Worsening metrics → orchestrator losing ground (spawn needed)

    Args:
        domain_orchestrator: Orchestrator to analyze

    Returns:
        bool: True if trend is worsening, False if stable/improving
    """
    # Get 5 minutes of history (10 measurements at 30s intervals)
    history = get_metric_history(domain_orchestrator, last_minutes=5)

    # Split into baseline (first 3 minutes) and recent (last 2 minutes)
    baseline_measurements = history[0:6]  # First 6 measurements (3 minutes)
    recent_measurements = history[6:10]   # Last 4 measurements (2 minutes)

    # Calculate average combined metric for each period
    baseline_avg = calculate_combined_metric_avg(baseline_measurements)
    recent_avg = calculate_combined_metric_avg(recent_measurements)

    # Trend is "worsening" if recent exceeds baseline by 10%+
    threshold_increase = 1.1  # 10% increase required

    is_worsening = recent_avg > (baseline_avg * threshold_increase)

    return is_worsening


function calculate_combined_metric_avg(measurements):
    """Calculate average combined metric score across measurements."""
    total = 0
    for m in measurements:
        # Normalize each metric to 0-1 scale
        queue_norm = m.queue_depth / 10.0
        response_norm = m.avg_response_time / 30.0
        agent_norm = m.active_agent_count / 15.0

        # Sum normalized metrics
        combined = queue_norm + response_norm + agent_norm
        total += combined

    avg = total / len(measurements)
    return avg
```

### Example: Stable at Threshold (No Spawn)

```
Baseline (minutes 0-3):
  14:16:00 → Queue 11, Response 31s, Agents 16 → Combined 1.13
  14:16:30 → Queue 10, Response 30s, Agents 15 → Combined 1.00
  14:17:00 → Queue 12, Response 32s, Agents 17 → Combined 1.20
  14:17:30 → Queue 11, Response 31s, Agents 16 → Combined 1.13
  14:18:00 → Queue 10, Response 30s, Agents 15 → Combined 1.00
  14:18:30 → Queue 11, Response 31s, Agents 16 → Combined 1.13
  Baseline Average: 1.10

Recent (minutes 3-5):
  14:19:00 → Queue 11, Response 32s, Agents 16 → Combined 1.17
  14:19:30 → Queue 10, Response 30s, Agents 15 → Combined 1.00
  14:20:00 → Queue 12, Response 33s, Agents 17 → Combined 1.23
  14:20:30 → Queue 11, Response 31s, Agents 16 → Combined 1.13
  Recent Average: 1.13

Comparison: 1.13 / 1.10 = 1.03 (3% increase)
Result: Below 10% threshold → Trend is STABLE → No spawn
Interpretation: Orchestrator is handling load consistently at capacity
```

### Example: Worsening Trend (Spawn Required)

```
Baseline (minutes 0-3):
  14:16:00 → Queue 9,  Response 28s, Agents 14 → Combined 0.87
  14:16:30 → Queue 10, Response 29s, Agents 15 → Combined 0.97
  14:17:00 → Queue 11, Response 30s, Agents 16 → Combined 1.07
  14:17:30 → Queue 12, Response 32s, Agents 17 → Combined 1.20
  14:18:00 → Queue 11, Response 31s, Agents 16 → Combined 1.13
  14:18:30 → Queue 12, Response 33s, Agents 18 → Combined 1.30
  Baseline Average: 1.09

Recent (minutes 3-5):
  14:19:00 → Queue 14, Response 36s, Agents 19 → Combined 1.60
  14:19:30 → Queue 16, Response 39s, Agents 21 → Combined 1.90
  14:20:00 → Queue 15, Response 38s, Agents 20 → Combined 1.77
  14:20:30 → Queue 17, Response 42s, Agents 22 → Combined 2.07
  Recent Average: 1.84

Comparison: 1.84 / 1.09 = 1.69 (69% increase)
Result: Exceeds 10% threshold → Trend is WORSENING → Spawn required
Interpretation: Orchestrator is losing battle with incoming work
```

---

## 6. Cooldown Period Management

### Purpose
Prevent cascade spawning where new instances haven't had time to stabilize load before additional detection triggers.

### Rules

**Cooldown Duration**: 5 minutes (300 seconds) after spawning new instance.

**Scope**: Cooldown applies per domain type (not per instance).

**During Cooldown**: Bottleneck detection disabled for that domain type.

**Exception**: Severity 10 (critical bottleneck) bypasses cooldown for emergency spawning.

### Implementation Pseudocode

```python
function in_cooldown_period(domain_orchestrator, cooldown=300):
    """
    Check if domain type is in cooldown period after recent spawn.

    Args:
        domain_orchestrator: Orchestrator or domain type to check
        cooldown: Cooldown duration in seconds (default 300 = 5 minutes)

    Returns:
        bool: True if in cooldown, False if cooldown expired
    """
    domain_type = get_domain_type(domain_orchestrator)

    # Get timestamp of last spawn for this domain type
    last_spawn_time = get_last_spawn_timestamp(domain_type)

    if last_spawn_time is None:
        # No previous spawn for this domain
        return False

    # Calculate time elapsed since last spawn
    current_time = get_current_timestamp()
    elapsed = current_time - last_spawn_time

    # Check if still within cooldown period
    in_cooldown = elapsed < cooldown

    return in_cooldown
```

### Cooldown Tracking

**Storage**: Master Orchestrator maintains cooldown state for each domain type.

**Data Structure**:
```python
cooldown_state = {
    "mcp": {
        "last_spawn_time": "2026-02-04T14:20:00Z",
        "instance_count": 3
    },
    "development": {
        "last_spawn_time": "2026-02-04T14:15:00Z",
        "instance_count": 2
    },
    "specialized": {
        "last_spawn_time": None,
        "instance_count": 1
    }
}
```

### Cooldown Rationale

**Why 5 minutes?**
- New instance needs time to start accepting tasks (30-60 seconds)
- Tasks need time to be redistributed by load balancer (1-2 minutes)
- Aggregate metrics need time to reflect new capacity (2-3 minutes)
- Total: 4-6 minutes for stabilization → 5 minutes provides safety margin

**Why Severity 10 bypasses cooldown?**
- Critical bottleneck (all metrics at 2x+ threshold) indicates emergency
- System is severely degraded and cannot wait 5 minutes
- Immediate capacity needed even if last spawn was recent
- Risk of cascade spawning accepted vs. risk of system failure

---

## 7. Multi-Instance Consideration

### Aggregate Metric Calculation

When multiple instances of same domain type exist, aggregate metrics across all instances for bottleneck detection.

**Example: 2 MCP Orchestrator Instances**
```
Instance 1:
  Queue: 7
  Response: 28s
  Agents: 12

Instance 2:
  Queue: 6
  Response: 25s
  Agents: 11

Aggregate:
  Total Queue: 7 + 6 = 13 (exceeds threshold of 10)
  Avg Response: (28 + 25) / 2 = 26.5s (below threshold of 30)
  Total Agents: 12 + 11 = 23 (exceeds threshold of 15)

Analysis: 2 of 3 thresholds exceeded → Potential bottleneck at aggregate level
```

### Why Aggregate vs. Per-Instance?

**Rationale**: Bottleneck detection determines if **domain as a whole** needs more capacity, not whether individual instance is overloaded.

**Scenario**: Two instances each at 70% capacity (neither individually bottlenecked).
- Per-instance: No bottleneck detected → no spawn
- Aggregate: Domain at 140% capacity (both instances busy) → bottleneck detected → spawn

**Result**: Aggregate approach correctly identifies that domain needs additional capacity even when no single instance is critically overloaded.

### Load Balancing Impact

After spawn is triggered:
1. New instance created and registered with load balancer
2. Load balancer redistributes incoming tasks across all instances (including new one)
3. Aggregate metrics gradually improve as load spreads
4. Example: 3 instances at 70% capacity each → better than 2 at 100% each

---

## 8. Edge Cases & Handling

### Maximum Instances Reached

**Scenario**: All allowed instances for domain type already spawned (e.g., 5 MCP orchestrator instances configured as maximum).

**Detection**: Check instance count against configured maximum before triggering spawn.

**Action**:
- Log warning: "Domain {type} at maximum capacity ({count} instances). Cannot spawn additional instance."
- Continue monitoring (bottleneck will persist in metrics)
- Alert system administrators for manual intervention
- Consider rejecting new tasks for this domain (fail gracefully vs. degrading all tasks)

### Bottleneck Clears During Detection

**Scenario**: Between bottleneck detection and spawn execution, load decreases and metrics return to normal.

**Detection**: Re-check metrics immediately before spawn execution.

**Action**:
- If metrics no longer indicate bottleneck → cancel spawn
- Log: "Bottleneck resolved before spawn. Spawn cancelled."
- Avoids spawning unnecessary instance that would sit idle

### Multiple Domains Bottlenecked Simultaneously

**Scenario**: Both MCP and Development domain orchestrators detect bottlenecks at same time.

**Priority**: Spawn for highest severity score first.

**Sequencing**:
1. Calculate severity for each bottlenecked domain
2. Sort by severity (highest first)
3. Spawn instances sequentially with 10-second delay between spawns
4. Delay prevents resource contention during instance startup

**Example**:
```
MCP domain: Severity 8 → Spawn first
Development domain: Severity 5 → Spawn 10 seconds later
Specialized domain: Severity 3 → Monitor (below urgent threshold)
```

### Rapid Load Increase (Severity 10)

**Scenario**: Sudden traffic spike causes critical bottleneck (severity 10).

**Special Handling**:
- **Bypass cooldown**: Spawn immediately even if recent spawn occurred
- **Multiple spawns**: Consider spawning 2 instances for severity 10 (if below maximum)
- **Alert**: Notify system administrators of emergency spawn
- **Fast-track**: Prioritize resource allocation for new instances

**Rationale**: Critical severity indicates system is severely degraded. Normal safeguards (cooldown, single spawn) are insufficient. Aggressive response required to restore service.

### Oscillating Load

**Scenario**: Load alternates between high and low (e.g., queue spikes every 3 minutes).

**Detection**: Trend analysis will show alternating increase/decrease patterns.

**Handling**: Sustained threshold requirement (3 of 4 measurements) prevents spawning on single spike. Oscillating load will not maintain sustained threshold.

**Result**: No spawn triggered for oscillating load (system is handling bursts).

---

*Uses metrics from @./monitoring-metrics.md for all detection inputs*

*Detection output feeds into @./spawning-algorithms.md for instance creation*
