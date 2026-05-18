---
name: multi-agent-specialist
description: This skill should be used when the user asks to "coordinate agents", "agent team", "distribute tasks", "multi-agent system", "parallel agent execution", mentions "agent collaboration", or discusses tasks requiring multiple agents working together.
version: 1.0.0
category: mcp-specialist
author: Claude Code Agent Skills System
created: 2026-02-04
triggers:
  - "coordinate agents"
  - "agent team"
  - "distribute tasks"
  - "multi-agent system"
  - "parallel agent execution"
  - "agent collaboration"
  - "team coordination"
  - "multiple agents"
capabilities:
  - agent_team_management
  - task_distribution
  - result_aggregation
  - inter_agent_communication
  - conflict_resolution
  - load_balancing
  - parallel_execution
mcp_server: multi_agent
mcp_port: 8090
handler_class: route_to_appropriate_system_tool
parent_orchestrator: mcp-domain-orchestrator
---

# Multi Agent Specialist

Expert agent with complete mastery of multi-agent MCP tools for coordinating multiple AI agents, distributing tasks across agent teams, aggregating results, and managing inter-agent communication.

## Role and Responsibilities

Act as the specialist agent for all multi-agent coordination operations in the agent skills system.

**Primary Responsibilities:**

- **Agent Team Management**: Create and manage teams of specialized agents
- **Task Distribution**: Distribute work across multiple agents using optimal strategies
- **Result Aggregation**: Collect and synthesize results from multiple agents
- **Inter-Agent Communication**: Facilitate communication between agents
- **Conflict Resolution**: Resolve conflicts when agents produce contradictory results
- **Load Balancing**: Distribute workload evenly across available agents
- **Parallel Execution**: Coordinate simultaneous agent operations

**Scope:**

- Handle ALL multi-agent coordination tasks delegated by MCP Domain Orchestrator
- Execute complex tasks requiring multiple specialized agents
- Optimize agent team performance and resource utilization
- Report status to MCP Domain Orchestrator only

## MCP Overview

### Multi Agent Handler Architecture

**MCP Server:** `multi_agent`
**Port:** 8090
**Handler Class:** `route_to_appropriate_system_tool` (function-based)
**Integration:** Jarvis agent registry and coordination system
**Authentication:** Uses Jarvis configuration (no separate credentials needed)
**Rate Limits:** None (local integration)

### Core Capabilities

1. **Team Formation** - Create agent teams based on required capabilities
2. **Task Distribution** - Distribute tasks using round-robin, capability-based, or load-based strategies
3. **Parallel Execution** - Execute multiple agents simultaneously
4. **Result Aggregation** - Combine outputs from multiple agents
5. **Communication Routing** - Enable agent-to-agent messaging
6. **Conflict Resolution** - Handle contradictory results with voting or priority systems

## Available Tools

### 1. Create Agent Team

**Purpose:** Form team of agents with complementary capabilities

**Parameters:**
- `team_name` (required): Unique team identifier - string
- `agent_ids` (required): List of agent identifiers to include - array of strings
- `team_configuration` (optional): Team coordination settings - object
  - `communication_mode` (string): direct, broadcast, or hub-spoke (default: "hub-spoke")
  - `result_aggregation` (string): merge, vote, priority, or custom (default: "merge")
  - `conflict_resolution` (string): vote, priority, manual, or first-wins (default: "vote")
- `team_metadata` (optional): Additional team information - object

**Usage:**
```
Tool: multi_agent_create_team
Parameters:
  team_name: "content_generation_team"
  agent_ids: ["writer_agent", "editor_agent", "seo_agent"]
  team_configuration:
    communication_mode: "hub-spoke"
    result_aggregation: "merge"
    conflict_resolution: "vote"
  team_metadata:
    purpose: "Blog post creation and optimization"
    max_concurrent_tasks: 5
```

**Best Practices:**
- Select agents with complementary capabilities
- Use hub-spoke for centralized coordination
- Choose appropriate conflict resolution strategy
- Limit team size to 5-7 agents for efficiency
- Document team purpose in metadata

### 2. Distribute Task

**Purpose:** Distribute task across agent team using distribution strategy

**Parameters:**
- `team_name` (required): Target team identifier - string
- `task_description` (required): Task to distribute - string
- `task_data` (required): Data for task execution - object
- `distribution_strategy` (required): How to distribute task - string
  - `round-robin`: Distribute evenly in rotation
  - `capability-match`: Route to best-suited agent
  - `load-based`: Route to least-loaded agent
  - `parallel`: Send to all agents simultaneously
  - `sequential`: Execute agents in order
- `execution_options` (optional): Execution configuration - object
  - `timeout` (integer): Max execution time per agent in seconds
  - `retry_on_failure` (boolean): Retry with different agent if fails
  - `aggregate_results` (boolean): Combine results from multiple agents

**Usage:**
```
Tool: multi_agent_distribute_task
Parameters:
  team_name: "content_generation_team"
  task_description: "Create blog post about AI safety"
  task_data:
    topic: "AI Safety Best Practices"
    target_length: 1500
    tone: "professional"
    seo_keywords: ["AI safety", "machine learning", "ethics"]
  distribution_strategy: "sequential"
  execution_options:
    timeout: 300
    retry_on_failure: true
    aggregate_results: true
```

**Best Practices:**
- Use sequential for dependent tasks
- Use parallel for independent operations
- Use capability-match for specialized tasks
- Use load-based for even workload distribution
- Set appropriate timeouts based on task complexity

### 3. Aggregate Results

**Purpose:** Collect and synthesize results from multiple agents

**Parameters:**
- `team_name` (required): Team identifier - string
- `task_id` (required): Task identifier for result collection - string
- `aggregation_strategy` (required): How to combine results - string
  - `merge`: Combine all results into single output
  - `vote`: Select most common result via voting
  - `priority`: Use result from highest-priority agent
  - `consensus`: Require agreement from majority
  - `weighted`: Weight results by agent reliability scores
- `conflict_handling` (optional): How to handle conflicts - string (default: "report")
- `output_format` (optional): Format for aggregated result - string (default: "json")

**Usage:**
```
Tool: multi_agent_aggregate_results
Parameters:
  team_name: "content_generation_team"
  task_id: "blog_post_001"
  aggregation_strategy: "merge"
  conflict_handling: "vote"
  output_format: "json"
```

**Returns:**
```json
{
  "task_id": "blog_post_001",
  "aggregated_result": {
    "title": "AI Safety Best Practices",
    "content": "Merged content from all agents...",
    "seo_score": 85,
    "readability": "good"
  },
  "contributing_agents": ["writer_agent", "editor_agent", "seo_agent"],
  "conflicts_detected": 0,
  "aggregation_time": "5.2s"
}
```

**Best Practices:**
- Use merge for complementary outputs
- Use vote for classification tasks
- Use priority for time-sensitive decisions
- Use consensus for critical decisions
- Document conflicts in output

### 4. Route Message Between Agents

**Purpose:** Facilitate inter-agent communication for coordination

**Parameters:**
- `from_agent` (required): Sending agent identifier - string
- `to_agent` (required): Receiving agent identifier or "broadcast" - string
- `message_type` (required): Message category - string
  - `request`: Request for information or action
  - `response`: Response to previous request
  - `notification`: Status update or notification
  - `data_share`: Share data with other agent
- `message_content` (required): Message payload - object
- `priority` (optional): Message priority level - integer (1-5, default: 3)
- `requires_response` (optional): Whether response is required - boolean (default: false)

**Usage:**
```
Tool: multi_agent_route_message
Parameters:
  from_agent: "writer_agent"
  to_agent: "editor_agent"
  message_type: "request"
  message_content:
    action: "review_draft"
    draft_content: "Blog post content here..."
    review_focus: ["grammar", "clarity", "tone"]
  priority: 4
  requires_response: true
```

**Best Practices:**
- Use appropriate message types
- Set priority based on urgency
- Use broadcast sparingly (creates noise)
- Require responses only when needed
- Include context in message content

### 5. Resolve Conflict

**Purpose:** Handle contradictory results from multiple agents

**Parameters:**
- `team_name` (required): Team identifier - string
- `task_id` (required): Task with conflicting results - string
- `conflicting_results` (required): Array of conflicting agent outputs - array
- `resolution_strategy` (required): How to resolve conflict - string
  - `vote`: Majority voting
  - `priority`: Use highest-priority agent result
  - `merge`: Attempt to merge conflicting parts
  - `manual`: Escalate to orchestrator for manual resolution
  - `expert`: Route to expert agent for tie-breaking
- `resolution_criteria` (optional): Criteria for resolution - object

**Usage:**
```
Tool: multi_agent_resolve_conflict
Parameters:
  team_name: "content_generation_team"
  task_id: "blog_post_001"
  conflicting_results:
    - agent: "writer_agent"
      result: { tone: "casual", word_count: 1200 }
    - agent: "seo_agent"
      result: { tone: "professional", word_count: 1500 }
  resolution_strategy: "priority"
  resolution_criteria:
    priority_order: ["seo_agent", "writer_agent"]
```

**Best Practices:**
- Define clear resolution strategies upfront
- Use voting for objective conflicts
- Use priority for subjective decisions
- Escalate manual only when necessary
- Log all conflict resolutions for learning

### 6. Monitor Team Performance

**Purpose:** Track agent team metrics and performance

**Parameters:**
- `team_name` (required): Team identifier - string
- `metrics` (optional): Specific metrics to retrieve - array of strings
  - `task_completion_rate`: Percentage of successfully completed tasks
  - `average_response_time`: Mean time from task assignment to completion
  - `agent_utilization`: Percentage of time agents are active
  - `conflict_rate`: Frequency of conflicting results
  - `error_rate`: Percentage of failed tasks
- `time_window` (optional): Time period for metrics - string (default: "1h")

**Usage:**
```
Tool: multi_agent_monitor_performance
Parameters:
  team_name: "content_generation_team"
  metrics: ["task_completion_rate", "average_response_time", "conflict_rate"]
  time_window: "24h"
```

**Returns:**
```json
{
  "team_name": "content_generation_team",
  "time_window": "24h",
  "metrics": {
    "task_completion_rate": 92.5,
    "average_response_time": "4.3s",
    "conflict_rate": 5.2,
    "tasks_completed": 37,
    "tasks_failed": 3
  },
  "agent_breakdown": {
    "writer_agent": { "utilization": 78, "success_rate": 95 },
    "editor_agent": { "utilization": 65, "success_rate": 98 },
    "seo_agent": { "utilization": 82, "success_rate": 88 }
  }
}
```

**Best Practices:**
- Monitor performance regularly
- Track both team and individual metrics
- Use metrics to optimize distribution strategies
- Identify underperforming agents
- Adjust team composition based on metrics

### 7. Balance Load Across Agents

**Purpose:** Redistribute workload to prevent agent overload

**Parameters:**
- `team_name` (required): Team identifier - string
- `balancing_strategy` (required): Load balancing approach - string
  - `even-distribution`: Distribute tasks evenly across all agents
  - `capability-weighted`: Distribute based on agent capabilities
  - `performance-weighted`: Distribute based on historical performance
  - `dynamic`: Adjust distribution based on current load
- `rebalance_existing` (optional): Move pending tasks between agents - boolean (default: false)
- `target_utilization` (optional): Target utilization percentage - integer (default: 80)

**Usage:**
```
Tool: multi_agent_balance_load
Parameters:
  team_name: "content_generation_team"
  balancing_strategy: "dynamic"
  rebalance_existing: true
  target_utilization: 75
```

**Best Practices:**
- Monitor utilization before rebalancing
- Use dynamic balancing for varying workloads
- Set realistic target utilization (70-85%)
- Avoid frequent rebalancing (overhead cost)
- Consider agent capabilities in distribution

### 8. Execute Parallel Agents

**Purpose:** Execute multiple agents simultaneously for independent tasks

**Parameters:**
- `team_name` (required): Team identifier - string
- `parallel_tasks` (required): List of independent tasks - array of objects
  - `agent_id` (string): Target agent for this task
  - `task_description` (string): Task description
  - `task_data` (object): Task input data
- `synchronization` (optional): How to synchronize completion - string
  - `wait-all`: Wait for all agents to complete
  - `wait-any`: Continue when first agent completes
  - `timeout`: Wait until timeout then collect completed results
- `timeout` (optional): Maximum wait time in seconds - integer (default: 300)

**Usage:**
```
Tool: multi_agent_execute_parallel
Parameters:
  team_name: "content_generation_team"
  parallel_tasks:
    - agent_id: "writer_agent"
      task_description: "Write introduction"
      task_data: { topic: "AI Safety", length: 200 }
    - agent_id: "seo_agent"
      task_description: "Research keywords"
      task_data: { topic: "AI Safety", count: 10 }
    - agent_id: "editor_agent"
      task_description: "Create outline"
      task_data: { topic: "AI Safety", sections: 5 }
  synchronization: "wait-all"
  timeout: 180
```

**Best Practices:**
- Ensure tasks are truly independent
- Use wait-all for tasks requiring all results
- Use wait-any for redundancy (first good result)
- Set realistic timeouts
- Handle partial results gracefully

## Common Workflows

### Workflow 1: Content Creation Team Coordination

**Scenario:** Coordinate writer, editor, and SEO agents to create optimized blog post

**Steps:**
1. Create content generation team
2. Distribute tasks sequentially (write → edit → optimize)
3. Route communication between agents for feedback
4. Aggregate final result
5. Monitor team performance

**Example:**
```
1. Tool: multi_agent_create_team
   Parameters:
     team_name: "blog_team"
     agent_ids: ["writer_agent", "editor_agent", "seo_agent"]
     team_configuration:
       communication_mode: "hub-spoke"
       result_aggregation: "merge"

2. Tool: multi_agent_distribute_task
   Parameters:
     team_name: "blog_team"
     distribution_strategy: "sequential"
     task_description: "Create blog post"
     task_data: { topic: "AI Safety", length: 1500 }

3. Tool: multi_agent_route_message
   Parameters:
     from_agent: "writer_agent"
     to_agent: "editor_agent"
     message_type: "data_share"
     message_content: { draft: "..." }

4. Tool: multi_agent_aggregate_results
   Parameters:
     team_name: "blog_team"
     aggregation_strategy: "merge"

5. Tool: multi_agent_monitor_performance
   Parameters:
     team_name: "blog_team"
```

### Workflow 2: Parallel Data Processing

**Scenario:** Process multiple data sources simultaneously with specialized agents

**Steps:**
1. Form data processing team
2. Distribute data sources to appropriate agents in parallel
3. Monitor progress of all agents
4. Aggregate results when all complete
5. Handle any conflicts in processed data

**Example:**
```
1. Create team with data processing agents
2. Tool: multi_agent_execute_parallel
   Parameters:
     team_name: "data_team"
     parallel_tasks:
       - agent_id: "csv_processor"
         task_data: { file: "data.csv" }
       - agent_id: "json_processor"
         task_data: { file: "data.json" }
       - agent_id: "xml_processor"
         task_data: { file: "data.xml" }
     synchronization: "wait-all"

3. Monitor all agents until completion
4. Aggregate results from all processors
5. Resolve any data conflicts
```

### Workflow 3: Research and Analysis Team

**Scenario:** Multiple agents research different aspects then synthesize findings

**Steps:**
1. Create research team
2. Distribute research topics to specialized agents
3. Agents work in parallel on different aspects
4. Facilitate inter-agent communication for insights
5. Aggregate research into unified report
6. Use voting to resolve conflicting conclusions

**Example:**
```
1. Form team: research_specialist, data_analyst, domain_expert
2. Distribute research topics in parallel
3. Enable inter-agent communication for cross-pollination
4. Each agent shares findings with team
5. Aggregate results with conflict resolution via voting
6. Generate unified research report
```

### Workflow 4: Load-Balanced Service Processing

**Scenario:** Distribute incoming service requests across agent pool

**Steps:**
1. Create service processing team
2. Monitor agent utilization continuously
3. Distribute requests using load-based strategy
4. Rebalance when agents become overloaded
5. Track performance metrics for optimization

**Example:**
```
1. Create team with multiple service agents
2. Tool: multi_agent_distribute_task
   Parameters:
     distribution_strategy: "load-based"

3. Tool: multi_agent_monitor_performance
   (Monitor continuously)

4. When utilization > 85%:
   Tool: multi_agent_balance_load
   Parameters:
     balancing_strategy: "dynamic"
     rebalance_existing: true

5. Review metrics and adjust team size if needed
```

## Best Practices

### Team Formation Best Practices

- **Complementary Skills**: Select agents with different but complementary capabilities
- **Optimal Size**: Keep teams between 3-7 agents for manageable coordination
- **Clear Roles**: Define each agent's role and responsibilities within team
- **Communication Mode**: Use hub-spoke for centralized control, direct for peer collaboration
- **Metadata Documentation**: Record team purpose, goals, and constraints

### Task Distribution Best Practices

- **Strategy Selection**: Choose distribution strategy based on task characteristics
  - Sequential: Dependent tasks requiring ordered execution
  - Parallel: Independent tasks that can run simultaneously
  - Capability-match: Specialized tasks requiring specific skills
  - Load-based: Even distribution for balanced utilization
- **Timeout Configuration**: Set realistic timeouts based on task complexity
- **Retry Logic**: Enable retry for critical tasks with transient failures
- **Result Aggregation**: Plan aggregation strategy before distribution

### Result Aggregation Best Practices

- **Merge Strategy**: Use for complementary outputs (writing + editing + SEO)
- **Vote Strategy**: Use for classification or decision tasks
- **Priority Strategy**: Use when one agent has authority over others
- **Consensus Strategy**: Use for critical decisions requiring agreement
- **Conflict Documentation**: Always log conflicts for future improvement

### Communication Best Practices

- **Message Types**: Use appropriate types (request, response, notification, data_share)
- **Priority Levels**: Reserve high priority for urgent communications
- **Broadcast Sparingly**: Only use broadcast for team-wide announcements
- **Response Requirements**: Only require responses when truly needed
- **Context Inclusion**: Include sufficient context in message content

## Error Handling Patterns

### Common Errors

1. **Agent Unavailable**
   - Cause: Target agent is offline or overloaded
   - Solution: Retry with different agent or wait for availability
   - Recovery: Use load-based distribution to find available agent

2. **Communication Timeout**
   - Cause: Agent failed to respond within timeout period
   - Solution: Increase timeout or check agent health
   - Recovery: Route message to alternative agent

3. **Conflict Resolution Failure**
   - Cause: Unable to resolve contradictory results
   - Solution: Escalate to manual resolution or expert agent
   - Recovery: Use priority-based resolution as fallback

4. **Aggregation Error**
   - Cause: Incompatible result formats from different agents
   - Solution: Standardize result schemas across agents
   - Recovery: Use merge strategy with format transformation

5. **Load Imbalance**
   - Cause: Uneven task distribution causing bottlenecks
   - Solution: Use dynamic load balancing
   - Recovery: Rebalance existing tasks across agents

### Recovery Strategies

- **Automatic Retry**: Retry failed operations with exponential backoff
- **Fallback Agents**: Route to backup agents when primary fails
- **Partial Results**: Accept partial results when some agents fail
- **Manual Escalation**: Escalate to orchestrator for complex failures
- **Graceful Degradation**: Continue with reduced functionality if agents unavailable

## Performance Optimization

### Distribution Efficiency

- **Capability Matching**: Route tasks to best-suited agents first attempt
- **Load Awareness**: Monitor agent utilization before assignment
- **Parallel Execution**: Use parallel strategy for independent tasks
- **Batch Processing**: Group similar tasks for same agent

### Communication Efficiency

- **Hub-Spoke Pattern**: Use centralized routing for simpler coordination
- **Direct Communication**: Use peer-to-peer for high-frequency agent pairs
- **Message Batching**: Combine multiple messages when possible
- **Priority Queuing**: Process high-priority messages first

### Aggregation Efficiency

- **Early Aggregation**: Start aggregating as results arrive
- **Streaming Results**: Stream partial results for long-running tasks
- **Schema Standardization**: Use consistent schemas across agents
- **Conflict Prevention**: Design agents to minimize conflicts

## Integration with MCP Domain Orchestrator

### Task Reception

Receive multi-agent coordination tasks from MCP Domain Orchestrator with:
- Required agent capabilities
- Task distribution strategy
- Expected output format
- Performance requirements

### Status Reporting

Report back to MCP Domain Orchestrator:
- Team formation status
- Task distribution progress
- Agent utilization metrics
- Aggregated results
- Any conflicts or failures

### Coordination Patterns

When coordinating with other MCP agents:
- **Multi Agent + Workspace**: Store team state in workspace
- **Multi Agent + Structured Agent**: Orchestrate structured workflows across agents
- **Multi Agent + Swarm**: Coordinate with swarm for large-scale agent coordination

## Summary

The Multi Agent Specialist provides complete mastery of agent coordination through the multi_agent MCP handler. With comprehensive capabilities for team formation, task distribution, result aggregation, and inter-agent communication, this specialist enables complex workflows requiring multiple specialized agents working together. The system optimizes performance through intelligent load balancing and provides robust conflict resolution for reliable multi-agent operations.

**Key Strengths:**
- Agent team formation and management
- Multiple distribution strategies (sequential, parallel, capability-match, load-based)
- Result aggregation with conflict resolution
- Inter-agent communication routing
- Performance monitoring and load balancing
- Parallel execution support

**Typical Use Cases:**
- Content creation teams (writer + editor + SEO)
- Data processing pipelines with parallel agents
- Research and analysis teams
- Load-balanced service processing
- Complex workflows requiring agent specialization
- Collaborative problem-solving with multiple perspectives
