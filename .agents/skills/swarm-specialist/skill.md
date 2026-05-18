---
name: swarm-specialist
version: 1.0.0
author: Agent Skills System
description: Expert in multi-agent coordination with complete mastery of swarm MCP tools including agent orchestration, task distribution, consensus mechanisms, and collaborative problem-solving
trigger_domain: mcp
trigger_keywords:
  - swarm coordination
  - multi-agent collaboration
  - agent orchestration
  - task distribution
  - agent consensus
  - parallel agents
  - agent swarm
  - collective intelligence
  - distributed agents
  - agent pool management
tools_required:
  - swarm (MCP Handler)
progressive_disclosure:
  - level: 1
    content: swarm_overview
  - level: 2
    content: coordination_tools
  - level: 3
    content: distribution_strategies
  - level: 4
    content: consensus_mechanisms
  - level: 5
    content: swarm_patterns
  - level: 6
    content: swarm_examples
---

# Swarm Specialist Agent

## Overview

This agent specializes in **multi-agent coordination** using the Swarm MCP Handler. It provides expert-level capabilities for orchestrating multiple AI agents to work together on complex tasks through sophisticated coordination strategies, task distribution algorithms, and consensus mechanisms.

**MCP Handler:** `swarm` (class-based handler)
**Core Class:** `SwarmHandler`
**Port:** 8127
**Configuration:** SSE via Jarvis native handler

---

## Coordination Tools

### 1. Swarm Creation and Management

#### Create Agent Swarm
```python
swarm_id = create_swarm(
    name="Data Analysis Swarm",
    description="Swarm for parallel data processing tasks",
    agents=[agent_1_id, agent_2_id, agent_3_id],
    coordination_strategy="parallel",
    max_concurrent_agents=5,
    timeout=300,  # 5 minutes
    metadata={
        "domain": "data_analysis",
        "complexity": "high",
        "priority": "urgent"
    }
)
```

**Parameters:**
- `name`: Swarm identifier (TEXT, required)
- `description`: Swarm purpose and context (TEXT, optional)
- `agents`: List of agent IDs to include in swarm (LIST, required)
- `coordination_strategy`: Strategy for task distribution (TEXT, required)
- `max_concurrent_agents`: Maximum agents executing simultaneously (INTEGER, default: 5)
- `timeout`: Maximum execution time in seconds (INTEGER, default: 300)
- `metadata`: Custom swarm metadata (JSON, optional)

#### Get Swarm Status
```python
status = get_swarm_status(swarm_id)
# Returns: {
#     "swarm_id": 42,
#     "name": "Data Analysis Swarm",
#     "status": "active",  # idle/active/completed/failed
#     "agents": [1, 2, 3],
#     "active_agents": 2,
#     "completed_tasks": 15,
#     "pending_tasks": 8,
#     "failed_tasks": 1,
#     "start_time": "2026-02-04T10:30:00Z",
#     "elapsed_time": 125.5,
#     "estimated_completion": "2026-02-04T10:35:00Z"
# }
```

#### Update Swarm Configuration
```python
update_swarm(
    swarm_id=42,
    max_concurrent_agents=8,  # Increase parallelism
    coordination_strategy="adaptive",  # Switch strategy
    timeout=600  # Extend timeout
)
```

#### Add/Remove Agents from Swarm
```python
# Add new agent to swarm
add_agent_to_swarm(
    swarm_id=42,
    agent_id=agent_4_id,
    capabilities=["data_validation", "statistical_analysis"]
)

# Remove agent from swarm
remove_agent_from_swarm(
    swarm_id=42,
    agent_id=agent_3_id,
    reason="performance_issues"
)
```

### 2. Task Distribution

#### Distribute Task to Swarm
```python
task_distribution = distribute_task(
    swarm_id=42,
    task={
        "task_id": "analysis_001",
        "description": "Analyze customer data for trends",
        "data_source": "customer_database",
        "requirements": ["statistical_analysis", "visualization"],
        "priority": "high",
        "deadline": "2026-02-04T12:00:00Z"
    },
    distribution_strategy="capability_based",  # or "load_balanced", "round_robin"
    subtask_division="auto"  # Automatically divide into subtasks
)
# Returns: {
#     "task_id": "analysis_001",
#     "subtasks": [
#         {"subtask_id": "sub_001", "assigned_to": agent_1_id, "portion": "segment_1"},
#         {"subtask_id": "sub_002", "assigned_to": agent_2_id, "portion": "segment_2"},
#         {"subtask_id": "sub_003", "assigned_to": agent_3_id, "portion": "segment_3"}
#     ],
#     "distribution_strategy": "capability_based",
#     "estimated_duration": 180
# }
```

**Distribution Strategies:**
- **capability_based**: Match subtasks to agent capabilities
- **load_balanced**: Distribute based on current agent workload
- **round_robin**: Rotate through agents sequentially
- **priority_based**: Assign high-priority tasks to most capable agents
- **adaptive**: Dynamically adjust based on agent performance

#### Monitor Task Progress
```python
progress = get_task_progress(swarm_id=42, task_id="analysis_001")
# Returns: {
#     "task_id": "analysis_001",
#     "overall_completion": 0.65,  # 65% complete
#     "subtasks": [
#         {"subtask_id": "sub_001", "agent": 1, "status": "completed", "completion": 1.0},
#         {"subtask_id": "sub_002", "agent": 2, "status": "in_progress", "completion": 0.75},
#         {"subtask_id": "sub_003", "agent": 3, "status": "pending", "completion": 0.0}
#     ],
#     "estimated_completion_time": "2026-02-04T11:00:00Z"
# }
```

### 3. Agent-to-Agent Communication

#### Enable Inter-Agent Communication
```python
# Configure communication channels
configure_swarm_communication(
    swarm_id=42,
    communication_mode="direct",  # direct/mediated/broadcast
    message_routing="peer_to_peer",
    enable_logging=True
)

# Send message between agents
send_agent_message(
    swarm_id=42,
    from_agent=agent_1_id,
    to_agent=agent_2_id,
    message={
        "type": "data_share",
        "content": "Completed segment 1 analysis, sharing results",
        "data": analysis_results,
        "requires_response": True
    }
)
```

**Communication Modes:**
- **direct**: Agents communicate peer-to-peer (fastest)
- **mediated**: Orchestrator mediates all communication (controlled)
- **broadcast**: Agent sends to all swarm members (coordination)

#### Get Communication Log
```python
log = get_swarm_communication_log(
    swarm_id=42,
    start_time="2026-02-04T10:30:00Z",
    end_time="2026-02-04T11:00:00Z",
    filter_by_agent=agent_1_id  # Optional filter
)
# Returns chronological list of all agent communications
```

### 4. Consensus Mechanisms

#### Request Swarm Consensus
```python
consensus_result = request_consensus(
    swarm_id=42,
    topic="data_interpretation",
    question="What is the primary trend in customer behavior?",
    options=["trend_a", "trend_b", "trend_c", "mixed"],
    consensus_threshold=0.75,  # 75% agreement required
    voting_method="weighted",  # or "simple_majority", "unanimous"
    agent_weights={  # For weighted voting
        agent_1_id: 1.5,  # Senior agent gets higher weight
        agent_2_id: 1.0,
        agent_3_id: 1.0
    },
    timeout=60  # 1 minute to reach consensus
)
# Returns: {
#     "consensus_reached": True,
#     "result": "trend_a",
#     "agreement_level": 0.80,  # 80% agreement
#     "votes": {
#         "trend_a": [agent_1_id, agent_2_id],
#         "trend_b": [agent_3_id]
#     },
#     "weighted_result": "trend_a",
#     "confidence": 0.85,
#     "time_to_consensus": 45  # seconds
# }
```

**Voting Methods:**
- **simple_majority**: More than 50% agreement
- **weighted**: Agents have different voting weights
- **unanimous**: All agents must agree
- **ranked_choice**: Agents rank options, consensus from highest aggregate

#### Handle Consensus Failure
```python
# If consensus not reached, escalate or retry
if not consensus_result["consensus_reached"]:
    # Option 1: Request additional analysis
    request_deeper_analysis(
        swarm_id=42,
        topic="data_interpretation",
        agents_to_analyze=[agent_1_id, agent_3_id],  # Conflicting agents
        focus_area="conflicting_interpretations"
    )

    # Option 2: Bring in subject matter expert
    add_expert_agent(
        swarm_id=42,
        expert_agent_id=expert_id,
        role="tie_breaker"
    )

    # Option 3: Retry with adjusted parameters
    retry_consensus(
        swarm_id=42,
        topic="data_interpretation",
        consensus_threshold=0.66,  # Lower threshold
        additional_context=deeper_analysis_results
    )
```

---

## Distribution Strategies

### Strategy 1: Capability-Based Distribution

**Use Case:** Tasks requiring specific agent skills

```python
# Define agent capabilities
register_agent_capabilities(
    agent_id=agent_1_id,
    capabilities={
        "data_cleaning": 0.95,  # Capability scores 0.0-1.0
        "statistical_analysis": 0.85,
        "visualization": 0.60
    }
)

# Distribute based on capabilities
distribution = distribute_task(
    swarm_id=42,
    task=complex_analysis_task,
    distribution_strategy="capability_based",
    capability_requirements={
        "subtask_1": {"data_cleaning": 0.80},
        "subtask_2": {"statistical_analysis": 0.90},
        "subtask_3": {"visualization": 0.70}
    }
)
# System automatically matches subtasks to agents with required capabilities
```

**Benefits:**
- Optimal task-agent matching
- Higher success rates
- Leverages agent specialization
- Reduces rework and errors

### Strategy 2: Load-Balanced Distribution

**Use Case:** Maximize throughput, prevent bottlenecks

```python
# Monitor agent workloads
workloads = get_agent_workloads(swarm_id=42)
# Returns: {
#     agent_1_id: {"active_tasks": 3, "queue_depth": 2, "utilization": 0.85},
#     agent_2_id: {"active_tasks": 1, "queue_depth": 0, "utilization": 0.40},
#     agent_3_id: {"active_tasks": 2, "queue_depth": 1, "utilization": 0.65}
# }

# Distribute to least loaded agent
distribution = distribute_task(
    swarm_id=42,
    task=new_task,
    distribution_strategy="load_balanced",
    load_metric="utilization"  # or "active_tasks", "queue_depth"
)
# System assigns to agent_2_id (lowest utilization)
```

**Benefits:**
- Prevents agent overload
- Maximizes parallel execution
- Reduces wait times
- Balances resource usage

### Strategy 3: Priority-Based Distribution

**Use Case:** Critical tasks need best agents

```python
# Rank agents by performance
agent_rankings = get_agent_performance_rankings(swarm_id=42)
# Returns: [
#     {"agent_id": agent_1_id, "success_rate": 0.95, "avg_time": 120},
#     {"agent_id": agent_3_id, "success_rate": 0.88, "avg_time": 150},
#     {"agent_id": agent_2_id, "success_rate": 0.82, "avg_time": 180}
# ]

# Assign high-priority task to top agent
distribution = distribute_task(
    swarm_id=42,
    task=critical_task,
    distribution_strategy="priority_based",
    task_priority="critical",
    prefer_top_performers=True
)
# System assigns to agent_1_id (highest success rate)
```

**Benefits:**
- Critical tasks get best resources
- Higher success rates for important work
- Performance-based optimization
- Risk mitigation

### Strategy 4: Adaptive Distribution

**Use Case:** Dynamic workloads with changing conditions

```python
# Enable adaptive distribution
configure_adaptive_distribution(
    swarm_id=42,
    learning_enabled=True,
    adaptation_frequency=30,  # Adjust strategy every 30 seconds
    performance_metrics=["success_rate", "execution_time", "resource_usage"],
    optimization_goal="minimize_time"  # or "maximize_quality", "balance"
)

# System automatically adjusts distribution based on real-time performance
distribution = distribute_task(
    swarm_id=42,
    task=new_task,
    distribution_strategy="adaptive"
)
# Strategy evolves: capability_based → load_balanced → hybrid
```

**Benefits:**
- Responds to changing conditions
- Learns from agent performance
- Optimizes over time
- No manual tuning required

---

## Consensus Mechanisms

### Mechanism 1: Simple Majority Voting

**Use Case:** Quick decisions on straightforward questions

```python
result = request_consensus(
    swarm_id=42,
    topic="data_quality_assessment",
    question="Is the data quality sufficient for analysis?",
    options=["yes", "no", "needs_cleaning"],
    voting_method="simple_majority",
    consensus_threshold=0.51  # More than 50%
)
```

**Properties:**
- Fast decision-making
- Democratic (equal votes)
- Simple to implement
- May miss nuance

### Mechanism 2: Weighted Voting

**Use Case:** Leverage expert opinions more heavily

```python
result = request_consensus(
    swarm_id=42,
    topic="algorithm_selection",
    question="Which algorithm should we use for this dataset?",
    options=["random_forest", "gradient_boosting", "neural_network"],
    voting_method="weighted",
    agent_weights={
        senior_agent_id: 2.0,  # Double weight for senior agent
        mid_agent_id: 1.5,
        junior_agent_id: 1.0
    }
)
```

**Properties:**
- Values expertise
- More accurate for complex decisions
- Requires weight calibration
- Can reduce junior agent engagement

### Mechanism 3: Unanimous Consensus

**Use Case:** Critical decisions requiring full agreement

```python
result = request_consensus(
    swarm_id=42,
    topic="production_deployment",
    question="Ready to deploy to production?",
    options=["yes", "no"],
    voting_method="unanimous",
    require_justification=True  # Each agent must explain vote
)

# All agents must vote "yes" for consensus
if result["consensus_reached"]:
    proceed_with_deployment()
else:
    # Review justifications from dissenting agents
    review_concerns(result["justifications"])
```

**Properties:**
- Maximum safety for critical decisions
- Every agent has veto power
- Can be slow
- Requires strong communication

### Mechanism 4: Confidence-Weighted Consensus

**Use Case:** Decisions where certainty matters

```python
result = request_consensus(
    swarm_id=42,
    topic="anomaly_detection",
    question="Is this pattern an anomaly?",
    options=["anomaly", "normal_variation", "uncertain"],
    voting_method="confidence_weighted",
    require_confidence_scores=True
)
# Returns: {
#     "consensus_reached": True,
#     "result": "anomaly",
#     "votes": [
#         {"agent": agent_1_id, "vote": "anomaly", "confidence": 0.95},
#         {"agent": agent_2_id, "vote": "anomaly", "confidence": 0.88},
#         {"agent": agent_3_id, "vote": "normal_variation", "confidence": 0.60}
#     ],
#     "weighted_result": "anomaly",
#     "aggregate_confidence": 0.91
# }
```

**Properties:**
- Accounts for certainty
- More nuanced than simple voting
- Identifies uncertain agents
- Better for probabilistic decisions

---

## Swarm Patterns

### Pattern 1: Map-Reduce Coordination

**Use Case:** Large dataset processing requiring aggregation

```python
# 1. Map Phase: Distribute data processing
map_swarm = create_swarm(
    name="Map Phase Swarm",
    agents=[agent_1_id, agent_2_id, agent_3_id],
    coordination_strategy="parallel"
)

map_task = {
    "type": "map",
    "data_segments": ["segment_1", "segment_2", "segment_3"],
    "operation": "extract_features"
}

map_results = distribute_task(
    swarm_id=map_swarm,
    task=map_task,
    distribution_strategy="load_balanced"
)

# Wait for all map tasks to complete
wait_for_completion(map_swarm, timeout=300)

# 2. Reduce Phase: Aggregate results
reduce_swarm = create_swarm(
    name="Reduce Phase Swarm",
    agents=[aggregator_agent_id],
    coordination_strategy="sequential"
)

reduce_task = {
    "type": "reduce",
    "input_data": collect_map_results(map_swarm),
    "operation": "aggregate_features"
}

final_result = distribute_task(
    swarm_id=reduce_swarm,
    task=reduce_task
)
```

### Pattern 2: Hierarchical Coordination

**Use Case:** Complex task requiring multiple coordination levels

```python
# Level 0: Master swarm coordinator
master_swarm = create_swarm(
    name="Master Coordination Swarm",
    agents=[master_coordinator_id],
    coordination_strategy="sequential"
)

# Level 1: Domain swarms
frontend_swarm = create_swarm(
    name="Frontend Development Swarm",
    agents=frontend_agents,
    coordination_strategy="parallel",
    parent_swarm_id=master_swarm
)

backend_swarm = create_swarm(
    name="Backend Development Swarm",
    agents=backend_agents,
    coordination_strategy="parallel",
    parent_swarm_id=master_swarm
)

# Coordinate domain swarms from master
coordinate_child_swarms(
    master_swarm_id=master_swarm,
    child_swarms=[frontend_swarm, backend_swarm],
    coordination_pattern="parallel_execution"
)
```

### Pattern 3: Peer Review Coordination

**Use Case:** Quality assurance through collaborative review

```python
# 1. Create work product
work_product = execute_task(primary_agent_id, task)

# 2. Distribute for peer review
review_swarm = create_swarm(
    name="Peer Review Swarm",
    agents=[reviewer_1_id, reviewer_2_id, reviewer_3_id],
    coordination_strategy="parallel"
)

review_task = {
    "type": "peer_review",
    "work_product": work_product,
    "review_criteria": ["correctness", "completeness", "quality"],
    "provide_feedback": True
}

reviews = distribute_task(
    swarm_id=review_swarm,
    task=review_task,
    distribution_strategy="round_robin"
)

# 3. Aggregate reviews and reach consensus
consensus = request_consensus(
    swarm_id=review_swarm,
    topic="work_product_quality",
    question="Does this work product meet our standards?",
    options=["approve", "revise", "reject"],
    voting_method="weighted",
    include_feedback=True
)

# 4. Apply feedback if needed
if consensus["result"] == "revise":
    revised_product = apply_feedback(
        work_product,
        feedback=consensus["feedback"]
    )
```

### Pattern 4: Competitive Coordination

**Use Case:** Multiple approaches to same problem, choose best

```python
# Create competitive swarm
competition_swarm = create_swarm(
    name="Algorithm Competition Swarm",
    agents=[agent_1_id, agent_2_id, agent_3_id],
    coordination_strategy="competitive"
)

# All agents work on same problem independently
competition_task = {
    "type": "competitive",
    "problem": "optimize_query_performance",
    "evaluation_criteria": ["execution_time", "resource_usage", "accuracy"],
    "timeout": 600
}

results = distribute_task(
    swarm_id=competition_swarm,
    task=competition_task,
    distribution_strategy="broadcast"  # All agents get same task
)

# Evaluate and select best solution
best_solution = evaluate_competitive_results(
    results=collect_all_results(competition_swarm),
    criteria=competition_task["evaluation_criteria"],
    selection_method="weighted_scoring"
)
```

---

## Swarm Examples

### Example 1: Data Analysis Swarm

```python
# Create specialized data analysis swarm
analysis_swarm = create_swarm(
    name="Customer Analytics Swarm",
    description="Parallel analysis of customer behavior data",
    agents=[
        data_cleaner_id,
        statistician_id,
        visualizer_id,
        insights_analyst_id
    ],
    coordination_strategy="sequential_pipeline",
    max_concurrent_agents=4
)

# Pipeline task distribution
pipeline_tasks = [
    {"stage": 1, "task": "data_cleaning", "agent": data_cleaner_id},
    {"stage": 2, "task": "statistical_analysis", "agent": statistician_id, "depends_on": [1]},
    {"stage": 3, "task": "visualization", "agent": visualizer_id, "depends_on": [2]},
    {"stage": 4, "task": "insights_extraction", "agent": insights_analyst_id, "depends_on": [2, 3]}
]

# Execute pipeline
execute_pipeline(
    swarm_id=analysis_swarm,
    pipeline=pipeline_tasks,
    data_source="customer_database"
)

# Monitor progress
progress = monitor_pipeline_progress(analysis_swarm)
```

### Example 2: Research Swarm with Consensus

```python
# Create research swarm
research_swarm = create_swarm(
    name="Research Validation Swarm",
    agents=[researcher_1_id, researcher_2_id, researcher_3_id, expert_id],
    coordination_strategy="collaborative"
)

# Distribute research task
research_task = {
    "topic": "market_trends_analysis",
    "data_sources": ["internal_db", "public_apis", "third_party_data"],
    "deadline": "2026-02-05T17:00:00Z"
}

research_results = distribute_task(
    swarm_id=research_swarm,
    task=research_task,
    distribution_strategy="capability_based"
)

# Wait for all research to complete
wait_for_completion(research_swarm, timeout=3600)

# Request consensus on findings
consensus = request_consensus(
    swarm_id=research_swarm,
    topic="research_findings",
    question="What is the primary market trend?",
    options=extract_trend_options(research_results),
    voting_method="weighted",
    agent_weights={expert_id: 2.0},  # Expert gets double weight
    require_justification=True
)

# Generate final report based on consensus
final_report = generate_consensus_report(
    research_results=research_results,
    consensus=consensus
)
```

### Example 3: Adaptive Load-Balanced Swarm

```python
# Create adaptive swarm for dynamic workload
processing_swarm = create_swarm(
    name="Adaptive Processing Swarm",
    agents=[agent_1_id, agent_2_id, agent_3_id, agent_4_id, agent_5_id],
    coordination_strategy="adaptive",
    max_concurrent_agents=5
)

# Configure adaptive behavior
configure_adaptive_distribution(
    swarm_id=processing_swarm,
    learning_enabled=True,
    adaptation_frequency=60,
    performance_metrics=["throughput", "error_rate", "latency"],
    optimization_goal="maximize_throughput"
)

# Process continuous stream of tasks
task_queue = initialize_task_queue("incoming_requests")

while task_queue.has_tasks():
    task = task_queue.get_next()

    # Adaptive distribution adjusts strategy based on performance
    distribute_task(
        swarm_id=processing_swarm,
        task=task,
        distribution_strategy="adaptive"
    )

    # System learns and adjusts:
    # - If agent_1 consistently faster → more tasks to agent_1
    # - If error rate high → switch to capability_based distribution
    # - If latency spikes → enable load balancing

# Get performance report
report = get_swarm_performance_report(processing_swarm)
# Shows adaptation history and optimization results
```

---

## Best Practices

### 1. Swarm Sizing
- **Small swarms (2-5 agents)**: Simple coordination, faster consensus
- **Medium swarms (6-15 agents)**: Balanced parallelism and coordination overhead
- **Large swarms (16+ agents)**: Maximum throughput, hierarchical coordination required
- Avoid single-agent swarms (use direct task execution instead)

### 2. Coordination Strategy Selection
- **Parallel**: Independent tasks, maximize throughput
- **Sequential**: Dependent tasks, pipeline processing
- **Competitive**: Multiple solutions, select best
- **Collaborative**: Consensus required, shared decision-making
- **Adaptive**: Dynamic workloads, learning over time

### 3. Timeout Management
- Set realistic timeouts based on task complexity
- Account for coordination overhead (add 20-30% buffer)
- Implement timeout warnings before expiration
- Graceful degradation when timeout reached

### 4. Consensus Best Practices
- Use simple majority for routine decisions
- Use weighted voting when expertise varies
- Use unanimous for critical/risky decisions
- Require justifications for important votes
- Set appropriate consensus thresholds (0.66-0.75 typical)

### 5. Performance Monitoring
- Track swarm throughput (tasks/minute)
- Monitor agent utilization rates
- Measure consensus time
- Log communication patterns
- Analyze bottlenecks regularly

---

## Troubleshooting

### Issue: Swarm Consensus Never Reached

**Causes:**
- Agents have fundamentally different interpretations
- Insufficient information provided to agents
- Consensus threshold too high
- Agent communication issues

**Solutions:**
- Provide additional context to agents
- Lower consensus threshold temporarily
- Add subject matter expert agent as tie-breaker
- Review agent communication logs for misunderstandings
- Request detailed justifications from agents

### Issue: Poor Task Distribution Efficiency

**Causes:**
- Wrong distribution strategy for workload
- Agent capabilities not properly registered
- Load balancing metrics outdated
- Network/communication latency

**Solutions:**
- Analyze task characteristics and switch strategy
- Update agent capability profiles
- Increase load monitoring frequency
- Enable adaptive distribution for learning
- Check communication channel performance

### Issue: Swarm Performance Degradation

**Causes:**
- Too many concurrent agents (coordination overhead)
- Agent failures not detected quickly
- Memory/resource exhaustion
- Communication bottlenecks

**Solutions:**
- Reduce max_concurrent_agents setting
- Implement faster agent health checks
- Monitor resource usage per agent
- Use direct communication mode for performance
- Scale horizontally (more smaller swarms)

---

**Swarm Specialist Agent Ready**
**Capabilities:** Complete mastery of swarm MCP for multi-agent coordination
**Primary Focus:** Agent orchestration, task distribution, consensus mechanisms, collaborative problem-solving
