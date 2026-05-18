# MCP Multi-Agent Coordination Patterns

**Domain:** MCP Domain Orchestrator
**Purpose:** Algorithms and patterns for coordinating multiple MCP agents to fulfill complex tasks
**Patterns Covered:** Sequential, Parallel, Conditional, Iterative coordination

---

## Overview

Coordinate multiple MCP agents when single agent insufficient for task completion. Execute agents in proper sequence, handle data flow between agents, aggregate results, and recover from failures.

---

## Coordination Pattern Types

### Pattern 1: Sequential Coordination (A → B → C)

Execute agents in order, passing outputs as inputs to next agent.

**When to Use:**
- Task has clear sequential steps
- Output of Agent A required as input for Agent B
- Dependencies between operations (must complete A before starting B)

**Example Scenarios:**
- "Get calendar event details and send email confirmation"
  - Flow: `calendar` (retrieve event) → `email` (send with event details)
- "Search Drive for document and upload to file sharing service"
  - Flow: `google_workspace` (find document) → `file_sharing` (upload and share)
- "Check weather and if cold, create reminder in calendar"
  - Flow: `weather` (get forecast) → decision → `calendar` (create reminder)

**Data Flow:**
```
Agent A Input: Original task
Agent A Output: Result 1

Agent B Input: Result 1 from Agent A
Agent B Output: Result 2

Agent C Input: Result 2 from Agent B
Agent C Output: Final result
```

**Algorithm:**
```
function sequential_coordination(agents, task):
  results = []
  current_input = task

  for agent in agents:
    # Execute agent with cumulative context
    agent_result = execute_agent(agent, current_input, previous_results=results)

    if agent_result.status == FAILURE:
      # Handle failure (see Error Recovery section)
      handle_sequential_failure(agent, agent_result, results)
      break

    results.append(agent_result)
    current_input = prepare_next_input(agent_result, task)

  return aggregate_sequential_results(results)
```

**Execution Steps:**
1. Execute Agent A with original task
2. Check Agent A success/failure
3. If success, extract output and prepare as input for Agent B
4. Execute Agent B with Agent A's output
5. Repeat until all agents completed
6. Aggregate and return final results

---

### Pattern 2: Parallel Coordination (A + B + C → Aggregate)

Execute agents simultaneously, aggregate results after all complete.

**When to Use:**
- Agents operate independently (no dependencies)
- Task requires information from multiple sources
- Speed optimization (parallel faster than sequential)
- Partial success acceptable (some agents can fail without blocking others)

**Example Scenarios:**
- "Search Gmail and Google Drive for 'Q4 budget'"
  - Flow: [`google_workspace.gmail_search`, `google_workspace.drive_search`] → merge results
- "Get weather forecast and latest tech news"
  - Flow: [`weather`, `news`] → combine outputs
- "Search for files across local filesystem and cloud storage"
  - Flow: [`finder`, `google_workspace.drive`, `microsoft_365.onedrive`] → deduplicate and merge

**Data Flow:**
```
All agents start simultaneously with same original task

Agent A Output: Result A
Agent B Output: Result B
Agent C Output: Result C

Aggregation: Combine [Result A, Result B, Result C] → Final result
```

**Algorithm:**
```
function parallel_coordination(agents, task):
  # Launch all agents concurrently
  futures = []

  for agent in agents:
    future = execute_agent_async(agent, task)
    futures.append({
      agent: agent,
      future: future
    })

  # Wait for all agents to complete (with timeout)
  results = []
  for item in futures:
    try:
      result = await_with_timeout(item.future, timeout=30)
      results.append({
        agent: item.agent,
        result: result,
        status: SUCCESS
      })
    except TimeoutError:
      results.append({
        agent: item.agent,
        result: None,
        status: TIMEOUT
      })
    except Exception as e:
      results.append({
        agent: item.agent,
        result: None,
        status: FAILURE,
        error: e
      })

  return aggregate_parallel_results(results)
```

**Execution Steps:**
1. Launch all agents concurrently
2. Each agent executes independently with original task
3. Collect results as agents complete (with timeout)
4. Handle partial failures (some succeed, some fail)
5. Aggregate successful results
6. Report which agents failed (if any)

---

### Pattern 3: Conditional Coordination (A → if X then B else C)

Execute decision agent, then execute action agent based on decision output.

**When to Use:**
- Task outcome depends on condition
- Decision point requires agent execution (not simple if-statement)
- Different actions for different conditions

**Example Scenarios:**
- "Check weather, if rain > 70% send umbrella reminder email"
  - Flow: `weather` (decision) → if rainy: `email` (action) else: no action
- "Search for document, if found share it, if not found create it"
  - Flow: `finder` (decision) → if found: `file_sharing` else: `document`
- "Get calendar availability, if busy send decline, if free send accept"
  - Flow: `calendar` (decision) → if busy: `email.decline` else: `email.accept`

**Data Flow:**
```
Decision Agent Input: Original task
Decision Agent Output: Decision result (with condition evaluation)

if condition_met(Decision Result):
  Action Agent B Input: Decision result
  Action Agent B Output: Final result
else:
  Action Agent C Input: Decision result
  Action Agent C Output: Final result
```

**Algorithm:**
```
function conditional_coordination(decision_agent, condition_fn, then_agent, else_agent, task):
  # Execute decision agent
  decision_result = execute_agent(decision_agent, task)

  if decision_result.status == FAILURE:
    return handle_decision_failure(decision_result)

  # Evaluate condition based on decision result
  condition_met = condition_fn(decision_result)

  # Execute appropriate action agent
  if condition_met:
    action_result = execute_agent(then_agent, task, context=decision_result)
    return {
      decision: decision_result,
      action_taken: then_agent.name,
      result: action_result
    }
  else:
    action_result = execute_agent(else_agent, task, context=decision_result)
    return {
      decision: decision_result,
      action_taken: else_agent.name,
      result: action_result
    }
```

**Execution Steps:**
1. Execute decision agent (e.g., `weather`, `calendar`, `finder`)
2. Extract decision data from agent output
3. Evaluate condition function on decision data
4. If condition true, execute "then" agent
5. If condition false, execute "else" agent
6. Return both decision and action results

**Condition Evaluation Examples:**
```
# Weather example
def is_rainy(weather_result):
  return weather_result.precipitation_probability > 0.7

# Calendar example
def is_busy(calendar_result):
  return len(calendar_result.events) > 0

# File existence example
def file_found(finder_result):
  return finder_result.file_count > 0
```

---

### Pattern 4: Iterative Coordination (repeat A → B until done)

Loop through agents repeatedly until task completion criteria met.

**When to Use:**
- Task requires processing multiple items
- Batch operations (process each item with same agent sequence)
- Unknown number of iterations (depends on data)
- Continuous processing until completion condition met

**Example Scenarios:**
- "Process all unread emails, save attachments to Drive"
  - Flow: LOOP { `email.get_next_unread` → `google_workspace.drive_upload` } until no more emails
- "For each contact in CRM, send personalized email"
  - Flow: LOOP { `gohighlevel.get_next_contact` → `email.send_personalized` } until all contacts processed
- "Check calendar every hour, send reminder 30 minutes before each event"
  - Flow: LOOP { `calendar.get_upcoming` → `email.send_reminder` → wait 1 hour } continuous

**Data Flow:**
```
Iteration 1:
  Agent A Output: Item 1
  Agent B Input: Item 1
  Agent B Output: Result 1

Iteration 2:
  Agent A Output: Item 2
  Agent B Input: Item 2
  Agent B Output: Result 2

... continue until completion_condition_met()

Final: Aggregate [Result 1, Result 2, ..., Result N]
```

**Algorithm:**
```
function iterative_coordination(agents, task, completion_condition):
  iteration_results = []
  iteration_count = 0
  max_iterations = 1000  # Safety limit

  while not completion_condition(iteration_results) and iteration_count < max_iterations:
    iteration_count += 1

    # Execute agent sequence for this iteration
    iteration_input = prepare_iteration_input(task, iteration_results, iteration_count)

    current_result = iteration_input
    for agent in agents:
      agent_result = execute_agent(agent, current_result)

      if agent_result.status == FAILURE:
        # Handle failure but continue to next iteration
        handle_iteration_failure(agent, agent_result, iteration_count)
        break  # Skip rest of agents for this iteration

      current_result = agent_result

    iteration_results.append(current_result)

  return {
    iterations_completed: iteration_count,
    results: iteration_results,
    final_aggregation: aggregate_iteration_results(iteration_results)
  }
```

**Execution Steps:**
1. Initialize iteration counter and results list
2. Check completion condition (if met, exit loop)
3. Prepare input for current iteration
4. Execute agent sequence for this iteration
5. Store iteration result
6. Increment counter and repeat
7. Aggregate all iteration results

**Completion Condition Examples:**
```
# Process all emails
def all_emails_processed(results):
  return len(results) > 0 and results[-1].no_more_emails == True

# Fixed number of items
def fixed_count_completed(results):
  return len(results) >= 50

# Time-based completion
def time_limit_reached(results, start_time):
  return (now() - start_time) > 3600  # 1 hour

# Error threshold reached
def too_many_errors(results):
  error_count = count_errors(results)
  return error_count > 10
```

---

## Coordination Algorithm Selection

Determine which pattern to use based on task characteristics:

```
function determine_coordination_pattern(task, required_agents):
  # Check for sequential dependencies
  if has_data_dependencies(required_agents):
    return SEQUENTIAL

  # Check for iteration indicators
  if has_iteration_keywords(task) or requires_batch_processing(task):
    return ITERATIVE

  # Check for conditional logic
  if has_conditional_keywords(task):
    return CONDITIONAL

  # Default to parallel if agents independent
  if agents_are_independent(required_agents):
    return PARALLEL

  # Fallback to sequential for safety
  return SEQUENTIAL
```

**Dependency Detection:**
```
function has_data_dependencies(agents):
  # Check if Agent B needs output from Agent A
  for i, agent_a in enumerate(agents):
    for agent_b in agents[i+1:]:
      if agent_b.required_inputs intersects agent_a.outputs:
        return True
  return False
```

**Keyword Detection:**
```
iteration_keywords = ["each", "all", "every", "batch", "process multiple", "for each", "loop"]
conditional_keywords = ["if", "when", "unless", "in case", "depending on", "based on"]

function has_iteration_keywords(task):
  return any(keyword in task.description.lower() for keyword in iteration_keywords)

function has_conditional_keywords(task):
  return any(keyword in task.description.lower() for keyword in conditional_keywords)
```

---

## Data Flow Management

### Sequential Data Flow

Pass output from previous agent as context to next agent:

```
function prepare_next_input(previous_result, original_task):
  return {
    original_task: original_task,
    previous_agent: previous_result.agent_name,
    previous_output: previous_result.data,
    context: merge_contexts(original_task.context, previous_result.context)
  }
```

### Parallel Data Aggregation

Merge outputs from multiple agents:

```
function aggregate_parallel_results(results):
  successful = [r for r in results if r.status == SUCCESS]
  failed = [r for r in results if r.status == FAILURE]

  return {
    total_agents: len(results),
    successful_count: len(successful),
    failed_count: len(failed),
    combined_data: merge_agent_outputs(successful),
    errors: [r.error for r in failed]
  }
```

### Conditional Context Passing

Include decision data in action agent context:

```
function prepare_action_context(decision_result, original_task):
  return {
    original_task: original_task,
    decision_agent: decision_result.agent_name,
    decision_data: decision_result.data,
    condition_evaluation: decision_result.condition_met,
    reason: decision_result.reasoning
  }
```

### Iterative State Tracking

Maintain state across iterations:

```
function prepare_iteration_input(original_task, previous_iterations, iteration_count):
  return {
    original_task: original_task,
    iteration_number: iteration_count,
    previous_results: previous_iterations,
    items_processed: sum(len(r.items) for r in previous_iterations),
    accumulated_data: accumulate_data(previous_iterations)
  }
```

---

## Error Recovery in Coordination

### Sequential Coordination Error Handling

When agent fails in sequential chain:

**Strategy 1: Stop and Report**
- Abort remaining agents
- Return partial results from completed agents
- Report which agent failed and why

**Strategy 2: Skip and Continue**
- Mark failed agent as skipped
- Continue to next agent with best-effort input
- Report partial success with warnings

**Strategy 3: Retry with Fallback**
- Retry failed agent up to 3 times
- If still fails, try alternative agent
- Continue chain with fallback result

```
function handle_sequential_failure(failed_agent, error, completed_results):
  # Attempt retry
  for attempt in range(1, 4):
    retry_result = execute_agent(failed_agent, input, retry_attempt=attempt)
    if retry_result.status == SUCCESS:
      return retry_result  # Continue chain

  # Try fallback agent
  fallback = get_fallback_agent(failed_agent)
  if fallback:
    fallback_result = execute_agent(fallback, input)
    if fallback_result.status == SUCCESS:
      return fallback_result  # Continue chain with fallback

  # If retries and fallback fail, stop chain
  return {
    status: PARTIAL_SUCCESS,
    completed_agents: completed_results,
    failed_agent: failed_agent.name,
    error: error,
    remaining_agents: get_remaining_agents()
  }
```

### Parallel Coordination Error Handling

When some agents fail in parallel execution:

**Strategy: Accept Partial Success**
- Parallel operations designed for partial success
- Aggregate results from successful agents
- Report failures but don't block overall task

```
function aggregate_parallel_results(results):
  successful = [r for r in results if r.status == SUCCESS]
  failed = [r for r in results if r.status != SUCCESS]

  # Partial success if at least one agent succeeded
  if len(successful) > 0:
    return {
      status: PARTIAL_SUCCESS if len(failed) > 0 else SUCCESS,
      successful_agents: [r.agent for r in successful],
      failed_agents: [r.agent for r in failed],
      combined_data: merge_results(successful),
      warnings: [f"{r.agent} failed: {r.error}" for r in failed]
    }
  else:
    # Total failure if all agents failed
    return {
      status: FAILURE,
      error: "All parallel agents failed",
      agent_errors: [(r.agent, r.error) for r in failed]
    }
```

### Conditional Coordination Error Handling

When decision agent or action agent fails:

**Decision Agent Failure:**
- Cannot make decision without decision data
- Abort coordination and report to Master
- Request manual decision or clarification

**Action Agent Failure:**
- Retry action agent up to 3 times
- Try alternative action agent if available
- Report conditional result with action failure

```
function handle_conditional_failure(failed_component, error, decision_result):
  if failed_component == DECISION_AGENT:
    # Cannot proceed without decision
    return {
      status: FAILURE,
      error: "Decision agent failed, cannot determine action",
      failed_agent: decision_result.agent_name,
      recommendation: "Manual decision required"
    }
  else:
    # Action agent failed, try alternatives
    for attempt in range(1, 4):
      retry_result = execute_agent(failed_agent, input, retry_attempt=attempt)
      if retry_result.status == SUCCESS:
        return success_result(decision_result, retry_result)

    return {
      status: PARTIAL_SUCCESS,
      decision: decision_result,
      action_attempted: failed_agent.name,
      action_result: FAILURE,
      error: error
    }
```

### Iterative Coordination Error Handling

When agent fails during iteration:

**Strategy: Continue with Next Iteration**
- Log failure for current iteration
- Continue to next iteration
- Report summary with failure count at end

```
function handle_iteration_failure(failed_agent, error, iteration_number):
  log_iteration_error({
    iteration: iteration_number,
    agent: failed_agent.name,
    error: error,
    timestamp: now()
  })

  # Continue to next iteration (don't let one failure stop entire batch)
  return {
    iteration_result: FAILURE,
    continue_processing: True
  }

# At end of iterative coordination:
function summarize_iteration_results(iteration_results):
  successful = count_successful(iteration_results)
  failed = count_failed(iteration_results)

  return {
    total_iterations: len(iteration_results),
    successful_count: successful,
    failed_count: failed,
    success_rate: successful / len(iteration_results),
    errors: extract_errors(iteration_results)
  }
```

---

## Performance Optimization

### Parallel Execution Optimization

**Batch Parallel Operations:**
- Group independent agents for parallel execution
- Reduce total execution time

```
function optimize_parallel_execution(agents):
  # Execute agents in parallel with concurrency limit
  max_concurrent = 5
  results = []

  for batch in chunk(agents, max_concurrent):
    batch_results = execute_parallel_batch(batch)
    results.extend(batch_results)

  return results
```

**Timeout Management:**
- Set reasonable timeouts for each agent
- Don't let slow agents block others

```
function execute_with_timeout(agent, task, timeout=30):
  try:
    return execute_agent_async(agent, task).get(timeout=timeout)
  except TimeoutError:
    return {
      status: TIMEOUT,
      agent: agent.name,
      error: f"Agent exceeded {timeout}s timeout"
    }
```

### Caching Optimization

**Cache Intermediate Results:**
- Avoid re-executing same agent with same input
- Significant speedup for repetitive operations

```
function execute_agent_with_cache(agent, input):
  cache_key = generate_cache_key(agent, input)

  cached_result = check_cache(cache_key)
  if cached_result:
    return cached_result

  result = execute_agent(agent, input)
  store_cache(cache_key, result, ttl=300)  # 5 minute cache
  return result
```

### Early Exit Optimization

**Stop When Sufficient:**
- For parallel searches, stop when first result found (if appropriate)
- For iterative processing, stop when completion criteria met

```
function parallel_search_with_early_exit(agents, task):
  futures = [execute_agent_async(agent, task) for agent in agents]

  # Return as soon as first agent succeeds
  for future in as_completed(futures):
    result = future.result()
    if result.status == SUCCESS and result.found:
      cancel_remaining(futures)  # Cancel other agents
      return result

  return {status: FAILURE, error: "No agents found result"}
```

### Lazy Execution Optimization

**Execute Only When Needed:**
- For conditional coordination, don't execute "else" branch if "then" branch taken
- For iterative coordination, don't prepare next iteration if completion criteria met

```
function lazy_conditional_execution(decision_agent, condition_fn, then_agent, else_agent, task):
  decision_result = execute_agent(decision_agent, task)

  # Only execute one branch (not both)
  if condition_fn(decision_result):
    return execute_agent(then_agent, task, context=decision_result)
  else:
    return execute_agent(else_agent, task, context=decision_result)
```

---

## Reporting to Master Orchestrator

### Pre-Execution Report

Before starting coordination, report plan:

```
Report to Master:
"Coordinating MCP agents for task: {task_description}
Pattern: {pattern_type}
Agents: {agent_list}
Estimated duration: {estimate}
Starting execution..."
```

### Progress Reports

During execution, report milestones:

```
# Sequential coordination
Report to Master:
"Coordination progress: Agent {n} of {total} completed
Current agent: {agent_name}
Status: {status}
Proceeding to next agent..."

# Parallel coordination
Report to Master:
"Parallel execution progress: {completed}/{total} agents completed
Completed: {completed_agents}
In progress: {active_agents}"

# Iterative coordination
Report to Master:
"Iteration {n} completed
Items processed: {count}
{remaining} items remaining..."
```

### Completion Report

After coordination finishes, report results:

```
Report to Master:
"Multi-agent coordination completed
Pattern: {pattern_type}
Agents executed: {agent_list}
Status: {SUCCESS | PARTIAL_SUCCESS | FAILURE}
Duration: {execution_time}
Results: {summary}
{Warnings/errors if any}"
```

---

## Example Coordination Scenarios

### Example 1: Email + Calendar Sequential

**Task:** "Add meeting to my calendar and email the attendees"

**Coordination Plan:**
- Pattern: Sequential (calendar → email)
- Agent 1: `calendar` - Create event, get event details
- Agent 2: `email` - Send to attendees with event info

**Execution:**
```
1. Execute calendar.create_event({
     title: "Team Sync",
     date: "2024-03-15",
     time: "14:00",
     attendees: ["alice@example.com", "bob@example.com"]
   })

   Result: {
     event_id: "evt_123",
     title: "Team Sync",
     date: "2024-03-15 14:00",
     attendees: ["alice@example.com", "bob@example.com"],
     ical_link: "https://cal.example.com/evt_123.ics"
   }

2. Execute email.send({
     to: ["alice@example.com", "bob@example.com"],
     subject: "Meeting Invitation: Team Sync",
     body: "You're invited to Team Sync on March 15 at 2:00 PM. Calendar link: {ical_link}",
     attachments: [event.ical_file]
   })

   Result: {
     status: "sent",
     message_id: "msg_456",
     recipients_sent: 2
   }

Final Report to Master:
"Sequential coordination completed successfully. Created calendar event and sent email to 2 attendees."
```

---

### Example 2: Multi-Source Search Parallel

**Task:** "Search all my documents for 'contract'"

**Coordination Plan:**
- Pattern: Parallel (finder + google_workspace + microsoft_365)
- Agent 1: `finder` - Search local filesystem
- Agent 2: `google_workspace` - Search Google Drive
- Agent 3: `microsoft_365` - Search OneDrive

**Execution:**
```
Launch parallel:

1. finder.search({query: "contract", locations: ["/Users/me/Documents"]})
   Result: {found: 5, files: [...local files...]}

2. google_workspace.drive_search({query: "contract"})
   Result: {found: 12, files: [...drive files...]}

3. microsoft_365.onedrive_search({query: "contract"})
   Result: {found: 3, files: [...onedrive files...]}

Aggregate:
{
  total_found: 20,
  sources: {
    local: 5 files,
    google_drive: 12 files,
    onedrive: 3 files
  },
  combined_results: [...all 20 files...],
  duplicates_removed: 2
}

Final Report to Master:
"Parallel search completed. Found 20 documents across 3 sources (5 local, 12 Drive, 3 OneDrive)."
```

---

### Example 3: Weather-Based Email Conditional

**Task:** "Check weather for tomorrow and send me email reminder if rain expected"

**Coordination Plan:**
- Pattern: Conditional (weather → if rain > 70% → email)
- Decision Agent: `weather` - Get tomorrow's forecast
- Condition: precipitation_probability > 0.7
- Then Agent: `email` - Send reminder
- Else: No action

**Execution:**
```
1. Execute weather.get_forecast({location: "San Francisco", date: "tomorrow"})

   Result: {
     date: "2024-03-16",
     precipitation_probability: 0.85,
     temperature: 55,
     conditions: "Heavy rain expected"
   }

2. Evaluate condition: 0.85 > 0.7 → TRUE (rain expected)

3. Execute email.send({
     to: "user@example.com",
     subject: "Rain Reminder: Bring Umbrella",
     body: "There's an 85% chance of rain tomorrow. Don't forget your umbrella!"
   })

   Result: {status: "sent", message_id: "msg_789"}

Final Report to Master:
"Conditional coordination completed. Weather check indicated rain (85%), email reminder sent."
```

---

### Example 4: Batch Email Processing Iterative

**Task:** "Process all unread emails, save attachments to Drive"

**Coordination Plan:**
- Pattern: Iterative (email.get_next → google_workspace.upload)
- Repeat until no more unread emails
- Handle failures gracefully (continue processing)

**Execution:**
```
Iteration 1:
  1. email.get_next_unread() → {email_id: "e1", has_attachment: true, attachment: "report.pdf"}
  2. google_workspace.drive_upload({file: "report.pdf", folder: "Email Attachments"}) → {file_id: "f1"}

Iteration 2:
  1. email.get_next_unread() → {email_id: "e2", has_attachment: true, attachment: "invoice.xlsx"}
  2. google_workspace.drive_upload({file: "invoice.xlsx", folder: "Email Attachments"}) → {file_id: "f2"}

Iteration 3:
  1. email.get_next_unread() → {email_id: "e3", has_attachment: false}
  2. Skip upload (no attachment)

Iteration 4:
  1. email.get_next_unread() → {no_more_emails: true}
  2. Exit loop

Summary:
{
  iterations_completed: 4,
  emails_processed: 3,
  attachments_saved: 2,
  files_uploaded: ["report.pdf", "invoice.xlsx"],
  emails_skipped: 1 (no attachment)
}

Final Report to Master:
"Iterative coordination completed. Processed 3 unread emails, saved 2 attachments to Drive."
```

---

## Summary

This coordination document provides:

- ✅ 4 coordination patterns (sequential, parallel, conditional, iterative)
- ✅ Detailed algorithms for each pattern
- ✅ Data flow management strategies
- ✅ Error recovery for each pattern type
- ✅ Performance optimization techniques
- ✅ Reporting templates for Master Orchestrator
- ✅ Complete example scenarios demonstrating each pattern

Use these patterns to coordinate multiple MCP agents for complex tasks requiring multi-agent collaboration.
