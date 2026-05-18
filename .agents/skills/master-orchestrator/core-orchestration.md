# Core Orchestration Patterns

**Version:** 1.0.0
**Purpose:** Detailed orchestration logic, domain identification algorithms, task breakdown strategies, and coordination protocols for Master Orchestrator

## Table of Contents

1. [Request Analysis Patterns](#request-analysis-patterns)
2. [Domain Identification Logic](#domain-identification-logic)
3. [Task Breakdown Strategies](#task-breakdown-strategies)
4. [Domain Coordinator Coordination](#domain-coordinator-coordination)
5. [Communication Protocols](#communication-protocols)

---

## 1. Request Analysis Patterns

### Complexity Classification Algorithm

Determine request complexity using these criteria:

#### Simple Request (Direct Delegation)
**Indicators:**
- Single action verb ("send email", "check weather", "query database")
- One domain clearly identified
- No dependencies on other operations
- Straightforward input/output

**Examples:**
- "Send an email to the team about the meeting"
- "What's the weather forecast for tomorrow?"
- "Create a new React button component"

**Action:** Delegate directly to appropriate domain orchestrator without coordination overhead.

#### Medium Request (Guided Delegation)
**Indicators:**
- Multiple steps within single domain
- Requires workflow coordination but not cross-domain
- May need sequential operations
- Clear success criteria within one domain

**Examples:**
- "Create a user dashboard with profile, settings, and activity sections"
- "Set up CI/CD pipeline with GitHub Actions for the backend"
- "Write integration tests for the authentication API"

**Action:** Delegate to domain orchestrator with detailed context and workflow guidance.

#### Complex Request (Multi-Step Coordination)
**Indicators:**
- Multiple domains required sequentially
- Dependencies between different specialist types
- Requires staged execution
- Integration points between domains

**Examples:**
- "Add OAuth login to the app" (Backend API + Frontend UI + Infrastructure deployment)
- "Create analytics dashboard" (Backend data pipeline + Frontend visualization + MCP data sources)
- "Implement feature flag system" (Backend logic + Frontend checks + Infrastructure configuration)

**Action:** Break down into domain-specific subtasks, coordinate execution order, manage handoffs.

#### Cross-Domain Request (Parallel Orchestration)
**Indicators:**
- Multiple domains can work independently
- Parallel execution possible
- Final integration of separate outputs
- Time-sensitive requiring concurrent work

**Examples:**
- "Prepare for production launch" (Backend hardening + Frontend performance + Infrastructure scaling + Quality testing in parallel)
- "Implement new feature" (Backend API + Frontend UI + Tests + Documentation simultaneously)
- "System-wide refactoring" (All domains refactoring their components concurrently)

**Action:** Launch multiple domain orchestrators concurrently, monitor all, aggregate results.

### Decision Tree

```
User Request
    |
    ├─ One domain keyword? ──────────────────> Simple (delegate directly)
    |
    ├─ Multiple steps, one domain? ──────────> Medium (delegate with workflow)
    |
    ├─ Multiple domains, dependencies? ──────> Complex (coordinate sequential)
    |
    └─ Multiple domains, independent? ───────> Cross-domain (coordinate parallel)
```

---

## 2. Domain Identification Logic

### MCP Domain Pattern Matching

**Primary Keywords:**
- Integration-related: "integrate", "connect", "sync", "fetch", "query external"
- Service-specific: "email", "calendar", "weather", "news", "database", "spreadsheet", "document"
- Platform-specific: "Google Workspace", "Meta Ads", "Go High Level", "<healthcare-platform>", "Microsoft 365"
- Operation-specific: "send email", "create event", "get forecast", "search articles", "query data"

**Secondary Indicators:**
- Mentions of external APIs
- References to third-party platforms
- Data retrieval from external sources
- Automation of external service operations

**MCP Specialist Types:**
- **Core Handlers:** email, calendar, finder, weather, news, wolfram, terminal, spreadsheet, document, browser, file_sharing, tv_movies
- **Healthcare:** <healthcare>, <healthcare>_sdk, <healthcare>_xps
- **Business Platforms:** gohighlevel (Go High Level CRM)
- **Advertising:** meta_business_sdk (Facebook/Instagram), google_ads
- **Collaboration:** google_workspace, microsoft_365
- **Development:** claude (Claude SDK), data_validator, terminal
- **Agent Systems:** swarm, agent_builder, agent_s, agent_registry, structured_agent, multi_agent
- **Workspace:** workspace, task_comments

**Decision Logic:**
```
IF request contains service name (email, calendar, etc.)
   OR mentions "external API" or "integration"
   OR references platform (Google, Meta, etc.)
THEN: MCP Domain required
```

### Frontend Domain Pattern Matching

**Primary Keywords:**
- UI elements: "button", "form", "modal", "dialog", "menu", "navbar", "sidebar", "card", "table"
- Technologies: "React", "component", "JSX", "CSS", "styling", "responsive", "layout"
- User-facing: "user interface", "UI", "UX", "user experience", "frontend", "client-side"
- Visual: "design", "appearance", "theme", "color", "animation", "transition"

**Secondary Indicators:**
- Mentions of user interactions (click, hover, scroll)
- References to visual presentation
- Discussion of accessibility (a11y)
- Mobile/desktop responsiveness concerns

**Decision Logic:**
```
IF request contains UI element name
   OR mentions frontend technology
   OR focuses on user-facing presentation
   OR discusses visual appearance
THEN: Frontend Domain required
```

### Backend Domain Pattern Matching

**Primary Keywords:**
- Server operations: "API", "endpoint", "route", "server", "backend", "business logic"
- Data operations: "database", "query", "CRUD", "data model", "schema", "migration"
- Security: "authentication", "authorization", "auth", "login", "token", "session", "JWT"
- Processing: "validation", "transform", "process", "compute", "calculate"

**Secondary Indicators:**
- Mentions of RESTful or GraphQL APIs
- References to data persistence
- Discussion of server-side logic
- Security and access control requirements

**Decision Logic:**
```
IF request mentions API or server operations
   OR discusses database operations
   OR involves authentication/security
   OR requires server-side data processing
THEN: Backend Domain required
```

### Infrastructure Domain Pattern Matching

**Primary Keywords:**
- Deployment: "deploy", "deployment", "release", "rollout", "production"
- CI/CD: "pipeline", "continuous integration", "continuous deployment", "build", "automated testing"
- Containers: "Docker", "container", "Kubernetes", "orchestration"
- Cloud: "AWS", "cloud", "scaling", "load balancer", "CDN"
- Monitoring: "monitoring", "logging", "metrics", "observability", "alerting"

**Secondary Indicators:**
- Mentions of DevOps practices
- References to system reliability
- Discussion of performance at scale
- Infrastructure configuration needs

**Decision Logic:**
```
IF request involves deployment or infrastructure
   OR mentions CI/CD pipeline
   OR discusses containerization/cloud
   OR requires monitoring/scaling
THEN: Infrastructure Domain required
```

### Quality Domain Pattern Matching

**Primary Keywords:**
- Testing: "test", "testing", "unit test", "integration test", "e2e", "coverage"
- Review: "code review", "review", "audit", "inspect", "analyze"
- Improvement: "refactor", "optimize", "improve", "clean up", "technical debt"
- Documentation: "document", "documentation", "comment", "explain", "README"
- Quality metrics: "performance", "security scan", "linting", "code quality"

**Secondary Indicators:**
- Mentions of quality assurance
- References to best practices
- Discussion of maintainability
- Requests for code analysis

**Decision Logic:**
```
IF request involves testing or quality checks
   OR mentions code review or refactoring
   OR discusses documentation needs
   OR requires quality metrics/analysis
THEN: Quality Domain required
```

### Cross-Domain Detection

**Multi-Domain Indicators:**
- Request contains keywords from 2+ domains
- Phrases like "end-to-end", "full-stack", "complete implementation"
- Requirements spanning from frontend to backend to infrastructure
- Integration between different layers of the system

**Examples:**
- "Add Google Calendar integration to the dashboard" → MCP + Frontend
- "Create authenticated API with UI" → Backend + Frontend
- "Deploy the new feature with tests" → Backend/Frontend + Quality + Infrastructure
- "Build complete user management system" → Backend + Frontend + Infrastructure + Quality

**Decision Logic:**
```
domains_required = []
FOR each domain pattern:
    IF pattern matches request:
        domains_required.append(domain)

IF len(domains_required) >= 2:
    RETURN "cross-domain"
ELSE IF len(domains_required) == 1:
    RETURN domains_required[0]
ELSE:
    RETURN "clarification_needed"
```

---

## 3. Task Breakdown Strategies

### Single-Domain Task Handling

**When:** Request clearly belongs to one domain with no external dependencies.

**Strategy:**
1. Identify the primary domain
2. Package full request context
3. Delegate to domain orchestrator
4. Monitor for completion
5. Return results to user

**Workspace Pattern:**
```
master-001 (Master Workspace)
    └─> {domain}-domain-001 (Domain Workspace)
            └─> Results returned to Master
```

### Sequential Multi-Domain Task Breakdown

**When:** Multiple domains required with dependencies (A must complete before B).

**Strategy:**
1. Analyze full request to identify all required domains
2. Determine dependency chain (which domain depends on outputs from which other domain)
3. Create domain task list in execution order
4. Define interfaces between domains (data formats, handoff points)
5. Execute first domain task
6. When domain completes, extract outputs needed by next domain
7. Package outputs + context for next domain
8. Execute next domain task
9. Repeat until all domains complete
10. Aggregate final results

**Example Breakdown:**
Request: "Add OAuth authentication to the web app"

```
Step 1: Backend Domain
    Task: Implement OAuth flow server-side
    - Create auth endpoints (/login, /callback, /logout)
    - Handle token storage and validation
    - Set up session management
    Output: API endpoint documentation, token format

Step 2: Frontend Domain
    Task: Create login UI and auth state management
    Input: API endpoint documentation from Backend
    - Build login button and redirect flow
    - Implement auth state management
    - Add protected route handling
    Output: Integrated auth UI

Step 3: Infrastructure Domain
    Task: Configure OAuth app and deploy
    Input: Complete application from Backend + Frontend
    - Register OAuth application with provider
    - Configure callback URLs
    - Deploy with environment variables
    Output: Production OAuth configuration

Step 4: Quality Domain
    Task: Test authentication flow
    Input: Deployed application from Infrastructure
    - Test login/logout flow
    - Verify token refresh
    - Check security edge cases
    Output: Test results and verification
```

**Workspace Pattern:**
```
master-001
    ├─> backend-domain-001 (executes first)
    │       └─> API docs → handed to Frontend
    ├─> frontend-domain-001 (executes second)
    │       └─> Integrated UI → handed to Infrastructure
    ├─> infrastructure-domain-001 (executes third)
    │       └─> Deployed app → handed to Quality
    └─> quality-domain-001 (executes fourth)
            └─> Test results → returned to Master
```

### Parallel Multi-Domain Task Breakdown

**When:** Multiple domains can work independently without waiting for each other.

**Strategy:**
1. Analyze full request to identify all required domains
2. Verify domains have no inter-dependencies
3. Create separate, independent task packages for each domain
4. Launch all domain orchestrators simultaneously
5. Monitor progress from all domains
6. Collect results as they complete
7. When all domains finish, integrate results
8. Present unified output to user

**Example Breakdown:**
Request: "Prepare system for production launch"

```
Parallel Execution:
├─ Backend Domain (independent)
│   Task: Backend hardening
│   - Add rate limiting
│   - Implement caching
│   - Optimize database queries
│
├─ Frontend Domain (independent)
│   Task: Frontend performance optimization
│   - Code splitting
│   - Image optimization
│   - Bundle size reduction
│
├─ Infrastructure Domain (independent)
│   Task: Scaling and monitoring setup
│   - Configure auto-scaling
│   - Set up monitoring dashboards
│   - Configure alerting rules
│
└─ Quality Domain (independent)
    Task: Pre-launch testing
    - Run full test suite
    - Performance load testing
    - Security vulnerability scan

All complete → Master aggregates results → Reports readiness to user
```

**Workspace Pattern:**
```
master-001
    ├─> backend-domain-001 (parallel)
    ├─> frontend-domain-001 (parallel)
    ├─> infrastructure-domain-001 (parallel)
    └─> quality-domain-001 (parallel)
         All results → aggregated by Master
```

### Hybrid Sequential + Parallel Breakdown

**When:** Some domains can work in parallel while others have dependencies.

**Strategy:**
1. Identify which domains have dependencies
2. Identify which domains can work independently
3. Group independent domains for parallel execution
4. Execute parallel groups first (or alongside independent paths)
5. Execute dependent domains in sequence after prerequisites complete
6. Aggregate all results

**Example Breakdown:**
Request: "Implement new analytics feature"

```
Phase 1 (Parallel):
├─ Backend Domain: Create analytics API endpoints
└─ Frontend Domain: Design analytics UI mockups

Phase 2 (Sequential - depends on Phase 1 Backend):
└─ Frontend Domain: Implement UI with real API

Phase 3 (Parallel - depends on Phase 2):
├─ Infrastructure Domain: Deploy analytics feature
└─ Quality Domain: Test analytics feature
```

---

## 4. Domain Coordinator Coordination

### Domain Orchestrator Selection Algorithm

**Steps:**
1. **Identify required domain** from request analysis
2. **Check for existing domain orchestrator instance** handling this domain type
3. **Evaluate instance load** (queue length, active agents, response time)
4. **Decision:**
   - If no instance exists → Create new instance
   - If instance exists and not overloaded → Use existing instance
   - If instance exists and overloaded → Create additional instance (spawn)

**Bottleneck Detection Thresholds:**
- Queue length > 10 tasks waiting
- Average response time > 30 seconds
- Active agent count > 15 agents

When threshold exceeded → Spawn new domain orchestrator instance

### Task Delegation Protocol

**Standard Delegation Message Format:**

```json
{
  "type": "task_delegation",
  "from": "master-001",
  "to": "{domain}-domain-{instance}",
  "task": {
    "id": "task-{uuid}",
    "description": "User request or subtask description",
    "priority": "high|medium|low",
    "deadline": "ISO-8601 timestamp (optional)"
  },
  "context": {
    "user_request": "Original user request text",
    "workspace_id": "{domain}-domain-{instance}",
    "dependencies": [
      {
        "domain": "backend",
        "output": "API documentation",
        "status": "completed",
        "data": { ... }
      }
    ],
    "expected_outputs": [
      "Description of what this domain should produce"
    ],
    "success_criteria": [
      "Specific criteria for task completion"
    ]
  }
}
```

**Delegation Workflow:**

1. **Create Workspace:**
   ```
   workspace_id = create_workspace({domain}-domain-{instance})
   ```

2. **Package Context:**
   - Include original user request
   - Add domain-specific requirements
   - Attach outputs from prerequisite domains (if sequential)
   - Define expected outputs and interfaces
   - Specify success criteria

3. **Send Delegation Message:**
   - Send structured message to domain orchestrator
   - Register task in Master's tracking system
   - Set up monitoring for progress updates

4. **Monitor Progress:**
   - Listen for status updates from domain orchestrator
   - Track partial progress if domain provides incremental updates
   - Handle clarification requests from domain orchestrator

5. **Receive Results:**
   - Collect final outputs when domain completes
   - Validate outputs meet expected format and success criteria
   - Store results for potential use by dependent domains

### Progress Aggregation from Multiple Domain Orchestrators

**Single Domain Monitoring:**
- Relay progress updates directly to user
- Format: "Backend team is implementing authentication API (50% complete)"

**Multi-Domain Sequential Monitoring:**
- Track which phase is currently executing
- Show completed phases and pending phases
- Format: "✓ Backend complete | → Frontend in progress (30%) | ⋯ Infrastructure pending"

**Multi-Domain Parallel Monitoring:**
- Show progress from all domains simultaneously
- Highlight which domains are ahead/behind
- Format:
  ```
  Backend: 75% (API implementation)
  Frontend: 60% (UI components)
  Infrastructure: 40% (deployment setup)
  Overall: 58% complete
  ```

**Completion Aggregation:**
- Wait for all required domains to complete
- Verify cross-domain interfaces worked correctly
- Synthesize results into unified response
- Present to user with attribution to each domain

### Cross-Domain Dependency Management

**Dependency Tracking:**

Master Orchestrator maintains dependency graph:

```json
{
  "task_id": "task-abc123",
  "domains_required": ["backend", "frontend", "infrastructure"],
  "dependencies": {
    "frontend": {
      "depends_on": ["backend"],
      "requires": ["API endpoint documentation", "authentication flow"],
      "status": "waiting"
    },
    "infrastructure": {
      "depends_on": ["backend", "frontend"],
      "requires": ["complete application bundle"],
      "status": "waiting"
    }
  }
}
```

**Handoff Protocol:**

When domain completes and another domain depends on it:

1. **Extract Required Outputs:**
   ```python
   backend_outputs = extract_outputs(backend_result, keys=["api_docs", "auth_flow"])
   ```

2. **Validate Output Format:**
   ```python
   if not validate_output_format(backend_outputs, expected_schema):
       request_clarification_from_domain("backend")
   ```

3. **Package for Dependent Domain:**
   ```json
   {
     "dependencies": {
       "backend": {
         "status": "completed",
         "outputs": {
           "api_docs": { ... },
           "auth_flow": { ... }
         }
       }
     }
   }
   ```

4. **Delegate to Dependent Domain:**
   - Send task delegation with dependency outputs attached
   - Dependent domain now has everything it needs to start

**Data Integrity Verification:**

At each handoff point:
- Verify output schema matches expected format
- Validate required fields are present
- Check data types and value ranges
- Test interface contracts if applicable

---

## 5. Communication Protocols

### User ↔ Master Orchestrator

**User to Master:**
- User submits request (text, voice, or structured input)
- Master receives request and analyzes it
- If clarification needed, Master asks user directly
- User provides clarification, Master continues processing

**Master to User:**
- Master provides unified status updates during execution
- Master aggregates progress from all domains into single view
- Master presents final results with attribution to contributing domains
- Master handles all error communication from any domain

**Critical Rule:** User ONLY communicates with Master Orchestrator. Users never see or interact with domain orchestrators directly.

### Master ↔ Domain Orchestrators

**Master to Domain Orchestrator:**

**Task Delegation:**
```json
{
  "type": "task_delegation",
  "from": "master-001",
  "to": "mcp-domain-001",
  "task": { ... },
  "context": { ... }
}
```

**Clarification Response:**
```json
{
  "type": "clarification_response",
  "from": "master-001",
  "to": "mcp-domain-001",
  "task_id": "task-abc123",
  "clarification": "User specified they want Gmail integration, not Outlook"
}
```

**Domain Orchestrator to Master:**

**Status Update:**
```json
{
  "type": "status_update",
  "from": "mcp-domain-001",
  "to": "master-001",
  "task_id": "task-abc123",
  "status": "in_progress",
  "progress_percentage": 45,
  "current_activity": "Configuring email authentication",
  "estimated_completion": "2026-02-04T15:30:00Z"
}
```

**Clarification Request:**
```json
{
  "type": "clarification_request",
  "from": "mcp-domain-001",
  "to": "master-001",
  "task_id": "task-abc123",
  "question": "Which email service should we integrate: Gmail or Outlook?",
  "options": ["gmail", "outlook", "both"],
  "blocking": true
}
```
*Note: Master receives this and asks user, then returns clarification response*

**Task Completion:**
```json
{
  "type": "task_completion",
  "from": "mcp-domain-001",
  "to": "master-001",
  "task_id": "task-abc123",
  "status": "completed",
  "results": {
    "summary": "Email integration completed successfully",
    "outputs": {
      "api_configured": true,
      "test_email_sent": true,
      "integration_docs": "path/to/docs.md"
    },
    "execution_time": "8m 23s",
    "agents_used": ["mcp-email-001", "mcp-calendar-001"]
  }
}
```

**Error Report:**
```json
{
  "type": "error_report",
  "from": "mcp-domain-001",
  "to": "master-001",
  "task_id": "task-abc123",
  "error": {
    "type": "authentication_failure",
    "message": "Could not authenticate with email service",
    "recovery_options": [
      "Provide correct credentials",
      "Try alternative authentication method",
      "Use different email service"
    ]
  }
}
```

### Domain Orchestrators ↔ Specialists

**Domain Orchestrator to Specialist:**
- Domain orchestrator delegates specific operations to MCP/worker specialists
- Provides operation-specific context and parameters
- Monitors specialist execution

**Specialist to Domain Orchestrator:**
- Specialist reports operation results
- Specialist requests clarification if needed (domain orchestrator decides whether to handle or escalate to Master)

**Critical Rule:** Specialists never communicate with Master directly. All specialist communication goes through their domain orchestrator.

### Error Escalation Protocol

**Level 1 - Specialist Error:**
- Specialist encounters error
- Reports to domain orchestrator
- Domain orchestrator attempts recovery (retry, alternative approach)

**Level 2 - Domain Error:**
- Domain orchestrator cannot recover
- Reports error to Master
- Master decides: ask user for guidance, try alternative domain, or report failure

**Level 3 - Master Error:**
- Master cannot resolve issue
- Reports to user with explanation
- Provides recovery options or next steps

### Monitoring and Logging

Master Orchestrator maintains comprehensive logs:

**Task Tracking:**
- Log every task delegation with timestamp
- Track task status transitions (pending → in_progress → completed/failed)
- Record execution times for performance analysis

**Communication Log:**
- All messages between Master and domains
- Clarification requests and responses
- Error reports and resolutions

**Performance Metrics:**
- Domain orchestrator response times
- Task completion times by domain and complexity
- Success/failure rates by domain

**Workspace Management:**
- Active workspaces and their domains
- Workspace creation and closure timestamps
- Resource utilization per workspace

---

## Best Practices Summary

**Request Analysis:**
- Always classify complexity before acting
- Use decision tree to determine coordination strategy
- Don't over-complicate simple requests

**Domain Identification:**
- Match keywords systematically against all domain patterns
- Consider secondary indicators when primary keywords absent
- Flag cross-domain requests early for proper coordination

**Task Breakdown:**
- Break down at domain boundaries, not arbitrary subtasks
- Define clear interfaces between domains
- Identify all dependencies before execution
- Maximize parallel execution opportunities

**Coordination:**
- Use appropriate workspace patterns (single, sequential, parallel, hybrid)
- Monitor all active domains continuously
- Aggregate progress into unified user-facing updates
- Verify data integrity at cross-domain handoffs

**Communication:**
- Maintain Master as single point of contact for user
- Provide clear, contextualized tasks to domain orchestrators
- Handle clarifications promptly to avoid blocking
- Escalate errors systematically through hierarchy

**Optimization:**
- Detect domain orchestrator bottlenecks early
- Spawn additional instances when needed
- Balance load across multiple instances
- Learn from execution patterns to improve future coordination
