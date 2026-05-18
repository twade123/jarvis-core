# Progress Aggregation Patterns

## Aggregation Principles

Master Orchestrator collects status from all active domain orchestrators and merges them into a **unified progress view**. This ensures:

- **Single coherent narrative**: User sees one story, not fragmented per-domain reports
- **Maintained context**: Each progress update builds on previous updates, maintaining conversation flow
- **Overall visibility**: User understands system-wide progress, not just individual domain status
- **Cross-domain awareness**: Progress report shows how domains interact and depend on each other

### Core Principle
User sees **overall progress across all domains**, not individual domain reports. Master Orchestrator is responsible for aggregating, contextualizing, and presenting unified view.

### Context Preservation
- Master maintains history of all previous updates
- New updates reference what was previously reported
- Changes highlighted: "Backend is now 90% (was 60% in last update)"
- Maintains narrative thread throughout entire request lifecycle

## Status Collection Patterns

### Query Each Active Domain
Master queries all domain orchestrators currently working on user's request:

**Query Pattern**: "What's your current status?"

**Expected Response Structure**:
```json
{
  "domain": "frontend",
  "tasks_complete": ["Component structure", "Styling system", "State management"],
  "tasks_in_progress": ["API integration", "Error handling"],
  "tasks_blocked": ["Waiting for Backend API endpoint /users"],
  "percentage_complete": 65,
  "confidence": "high",
  "time_estimate_minutes": 20,
  "next_steps": ["Complete API integration once endpoint available", "Add loading states"]
}
```

### Parallel Status Collection
- Query all domains simultaneously (parallel, not sequential)
- Timeout after 5 seconds for any unresponsive domain
- Aggregate responses as they arrive
- Don't wait for slow domains to block entire report

### Track Dependencies Between Domains
Master identifies cross-domain dependencies:
- **Backend 100% → Frontend can now proceed**: Unblocking event
- **Infrastructure deployment blocked → Backend cannot deploy**: Blocking relationship
- **Frontend and Backend can work in parallel**: Independent work

### Identify Bottlenecks
Master analyzes which domains are blocking others:
- **Critical path identification**: Which domains must complete for others to proceed?
- **Bottleneck detection**: Is one domain preventing multiple others from progressing?
- **Load balancing opportunity**: Can bottlenecked domain spawn additional instance?

## Unified Progress Formatting

### Overall Progress Calculation
Master presents **system-wide progress percentage**:

- **Formula**: Weighted average across domains based on task complexity
- **Example**: "System is 65% complete across 3 domains"
- **Includes**: All active domains, weighted by their importance to overall completion
- **Excludes**: Blocked domains (counted but not factored into percentage until unblocked)

### Per-Domain Summary
Brief status for each active domain:

**Pattern**: "[Domain]: [key accomplishment], [current work]"

**Examples**:
- "MCP domain: Email integration complete, Calendar in progress"
- "Frontend: UI components 80% done, adding error handling"
- "Backend: 3 of 5 API endpoints complete, testing authentication endpoint"
- "Infrastructure: Deployment configured, monitoring setup in progress"

### Cross-Domain Coordination Status
Explain how domains interact:

**Sequential Work**:
- "Frontend waiting for Backend API completion before integration"
- "Backend deployment blocked until Infrastructure resolves credentials issue"
- "Quality team will begin testing once Frontend and Backend complete"

**Parallel Work**:
- "Frontend and Backend working independently on separate components"
- "MCP integration and Infrastructure setup happening in parallel"

**Recently Unblocked**:
- "Backend API now complete → Frontend can proceed with integration"
- "Infrastructure credentials resolved → Backend deployment no longer blocked"

### Next Steps
What happens next in the workflow:

- "Backend will complete in ~15 minutes, then Frontend integration begins"
- "Once Infrastructure monitoring is configured, Backend will deploy"
- "Quality testing will start after Frontend and Backend both reach 100%"

### Blockers
Transparent communication about impediments:

- "Infrastructure deployment blocked - investigating credentials issue with cloud provider"
- "Frontend API integration paused - waiting for Backend endpoint completion"
- "Database migration delayed - resolving schema conflict discovered during testing"

## Real-Time Updates

### Master Maintains Current State
- **In-memory state**: Current status of all domain orchestrators
- **Last update timestamp**: When each domain last reported status
- **Change tracking**: What's different since last user-facing update

### Event-Driven Updates
Master receives status changes from domains proactively:

**Domain Completion Event**:
- Domain orchestrator signals completion
- Master immediately updates state
- Master determines if user should be notified (milestone reached)

**Domain Unblocking Event**:
- Domain orchestrator reports blocker resolved
- Master updates dependency graph
- Master checks if other domains can now proceed

**Bottleneck Resolution Event**:
- Additional domain orchestrator instance spawned
- Master updates load balancing state
- Master incorporates new instance into progress calculation

### Proactive User Updates
Master notifies user at key milestones without waiting for user to ask:

**Major Milestones**:
- Domain completion: "Backend team complete! Frontend team now integrating APIs"
- Bottleneck resolution: "Infrastructure issue resolved - Backend deployment resuming"
- Overall completion: "All domains complete - system is ready for review"

**No Polling Required**:
- User doesn't need to repeatedly ask "how's it going?"
- Master pushes important updates proactively
- Reduces user cognitive load and waiting anxiety

## Progress Calculation Algorithms

### Weighted Average Calculation
Not all domains contribute equally to overall progress:

**Example Weighting**:
- Backend (40%): Core business logic and APIs
- Frontend (30%): User interface and integration
- Infrastructure (20%): Deployment and monitoring
- Quality (10%): Testing and review

**Calculation**:
```
Overall = (Backend% × 0.40) + (Frontend% × 0.30) + (Infrastructure% × 0.20) + (Quality% × 0.10)
```

**Example**:
- Backend: 90% complete
- Frontend: 60% complete
- Infrastructure: 100% complete
- Quality: 0% (not started)

Overall = (90 × 0.40) + (60 × 0.30) + (100 × 0.20) + (0 × 0.10) = 36 + 18 + 20 + 0 = **74% complete**

### Critical Path Identification
Identify which domains are on the critical path vs. parallel work:

**Critical Path**: Sequence of domains that must complete in order
- Example: Backend → Frontend → Quality (each waits for previous)
- Critical path domains get higher weight in time estimates

**Parallel Work**: Domains that can work independently
- Example: MCP integration and Infrastructure setup
- Parallel work can reduce overall time estimate

### Time Estimation
Aggregate remaining time from domain estimates:

**Sequential Work**: Add domain time estimates
- Backend 30 min + Frontend 20 min + Quality 15 min = **65 minutes total**

**Parallel Work**: Use longest domain time estimate
- MCP 25 min ∥ Infrastructure 20 min = **25 minutes total** (work happens simultaneously)

**Combined**: Critical path + parallel work
- (Backend 30 min → Frontend 20 min) ∥ Infrastructure 20 min = **50 minutes total**

### Confidence Scoring
How certain are the estimates?

**High Confidence**: Domain has completed similar work before, estimates reliable
**Medium Confidence**: Some uncertainty, estimates approximate
**Low Confidence**: Novel work, estimates may change significantly

**Overall Confidence Calculation**:
- Take minimum confidence across all critical path domains
- If any critical path domain is low confidence, overall is low confidence
- Communicate uncertainty: "Estimated 45 minutes, medium confidence (Backend estimates may vary)"

## Multi-Domain Coordination Reporting

### Sequential Work Visualization
Show which domains wait for others:

```
Domain A complete → Domain B starting → Domain C queued
     [100%]              [10%]              [0%]
      ✓                   ⟳                  ⏸
```

**User-Facing Format**:
"Backend complete ✓ → Frontend starting (10% done) → Quality queued"

### Parallel Work Visualization
Show domains working concurrently:

```
MCP Domain       [████████░░] 60%
Frontend Domain  [██████░░░░] 45%
Backend Domain   [█████████░] 70%
```

**User-Facing Format**:
"3 domains working concurrently: MCP (60%), Frontend (45%), Backend (70%)"

### Cross-Domain Dependency Graph
Visual representation of how domains relate:

```
Backend (90%) ─────┐
                   ├──→ Frontend (waiting) ──→ Quality (queued)
Infrastructure (100%) ─┘
```

**User-Facing Format**:
"Backend 90% and Infrastructure 100% must complete before Frontend can proceed. Quality will begin after Frontend completes."

### Bottleneck Alerts
Proactive notification when domain is blocking others:

**Detection**:
- Backend domain has 5 tasks in queue
- Frontend and Quality both waiting on Backend completion
- Backend progress is slow (below expected rate)

**Alert**:
"Backend domain is bottlenecked with 5 queued tasks and 2 domains waiting. Spawning additional Backend instance to accelerate completion."

**Post-Resolution Update**:
"Backend bottleneck resolved - second instance handling 3 tasks in parallel. Expected completion time reduced from 45 to 25 minutes."

## Integration with Task Tracking

Reference `workspace_task_systems_analysis.md` for details on:

- **Task comments integration**: How domain orchestrator status maps to task system
- **Workspace hierarchy**: How parent-child workspace relationships enforce communication flow
- **Conversation timeline**: How progress updates appear in conversation history
- **Status synchronization**: How domain orchestrator status updates trigger task status changes

Master Orchestrator uses the task tracking system to:
1. Query domain orchestrator workspaces for current task status
2. Aggregate task completion metrics across domains
3. Identify blocked tasks and cross-domain dependencies
4. Present unified view that rolls up all domain task statuses into coherent narrative
