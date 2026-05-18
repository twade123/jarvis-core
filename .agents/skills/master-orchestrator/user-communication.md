# User Communication Protocol

## Single Point of Interaction Principle

The Master Orchestrator is the **ONLY** orchestrator that communicates directly with the user. This is a fundamental architectural requirement that ensures:

- **Coherent narrative**: User receives consistent, unified communication from a single source
- **No confusion**: User doesn't receive fragmented updates from multiple orchestrators
- **Single source of truth**: All user-facing information flows through Master Orchestrator
- **Clear accountability**: Master Orchestrator owns the user relationship and experience

### Critical Rule
Domain orchestrators **NEVER** communicate directly with the user. All user interaction is mediated through Master Orchestrator.

### Rationale
- Prevents conflicting messages from multiple orchestrators
- Maintains coherent conversation context
- Simplifies user experience (one interface, not many)
- Enables Master to aggregate and contextualize updates before presenting to user

## Communication Flow Rules

```
User ← Master Orchestrator (ONLY interface)
        ↓↑
   Domain Orchestrators (report to Master, NOT to user)
        ↓↑
   Worker Agents (report to Domain, never to Master or User directly)
```

### Flow Requirements
1. **User → Master Only**: All user requests go to Master Orchestrator workspace
2. **Master → Domain**: Master delegates tasks to domain orchestrators with clear instructions
3. **Domain → Master**: Domain orchestrators report status, progress, and results back to Master
4. **Master → User**: Master aggregates domain reports and presents unified updates to user
5. **No Shortcuts**: Domain orchestrators cannot bypass Master to communicate with user

## User-Facing Communication Patterns

Master Orchestrator uses these standardized patterns when communicating with user:

### Initial Request Acknowledgment
- **Pattern**: "I'll coordinate [list of domains] to handle this request"
- **Example**: "I'll coordinate Frontend, Backend, and Infrastructure teams to build the dashboard feature"
- **Purpose**: Set expectations about which specialists will be involved

### Progress Updates
- **Pattern**: "[Domain] is [X]% complete, [Domain] starting [specific work]"
- **Example**: "Frontend team is 60% complete with UI components, Backend team starting API endpoint implementation"
- **Purpose**: Provide specific, actionable progress information

### Cross-Domain Status
- **Pattern**: "Waiting for [Domain] completion before [other Domain] can proceed"
- **Example**: "Waiting for Backend API completion before Frontend can integrate authentication flow"
- **Purpose**: Explain dependencies and sequencing to manage user expectations

### Completion Report
- **Pattern**: "All domains complete - [summarize key accomplishments across domains]"
- **Example**: "All teams complete - Frontend deployed with responsive UI, Backend APIs tested and live, Infrastructure monitoring configured"
- **Purpose**: Provide comprehensive view of completed work

### Error Handling
- **Pattern**: "[Domain] encountered [issue type] - investigating and will retry with [approach]"
- **Example**: "Backend encountered database connection issue - investigating credentials and will retry with connection pooling"
- **Purpose**: Transparent error communication with action plan

## Enforcement Mechanisms

### Skill-Level Enforcement
- **Domain orchestrator skills explicitly state**: "Report to Master Orchestrator, NOT user"
- **Worker agent skills explicitly state**: "Report to Domain Orchestrator, NOT Master or user"
- Skills include enforcement reminders in their core content

### Workspace-Level Enforcement
- **User messages routed ONLY to Master Orchestrator workspace**
- Domain orchestrator workspaces do not receive direct user input
- Worker agent workspaces are children of domain orchestrator workspaces

### Monitoring for Violations
- Master Orchestrator monitors for any direct domain-to-user communication attempts
- If domain orchestrator tries to communicate with user directly, Master intercepts and redirects
- Violations logged for skill refinement

### Hierarchical Structure Enforcement
- Workspace hierarchy enforces communication paths (parent-child relationships)
- Task system tracks which agent communicates with whom
- Conversation timeline shows proper flow or highlights violations

## Clarification Protocol

When a domain orchestrator needs clarification from the user:

### Domain Orchestrator Request
1. Domain orchestrator identifies missing information needed to complete task
2. Domain orchestrator reports to Master: "Need clarification about [specific technical detail]"
3. Domain orchestrator includes: what's unclear, why it matters, options if applicable

### Master Orchestrator Translation
1. Master receives technical clarification request from domain
2. Master translates technical details into user-friendly questions
3. Master provides context: "The Backend team needs to know [user-friendly explanation]"
4. Master asks user in natural language, not technical jargon

### User Response Collection
1. User provides clarification in their own words
2. Master receives user response
3. Master translates back into technical details domain orchestrator needs
4. Master relays clarification to domain orchestrator to continue work

### Benefits
- **User experience preserved**: Technical complexity hidden from user
- **Domain autonomy maintained**: Domains get the information they need
- **Context maintained**: Master maintains conversation coherence throughout clarifications

## Progress Query Handling

When user asks "How's it going?" or similar progress inquiry:

### Query All Active Domains
1. Master identifies all active domain orchestrators working on user's request
2. Master queries each domain: "What's your current status?"
3. Queries happen in parallel for efficiency

### Receive Structured Responses
Each domain orchestrator returns:
- **Domain name**: Which specialist team
- **Tasks complete**: What's been finished
- **Tasks in progress**: What's currently being worked on
- **Tasks blocked**: What's waiting on something else
- **Percentage complete**: Domain's assessment of completion
- **Time estimate**: How long until domain completes

### Aggregate into Single Coherent Update
Master creates unified response:
- **Overall progress**: Aggregate percentage across all domains
- **Per-domain summary**: Brief status for each active domain
- **Cross-domain coordination**: Dependencies and sequencing
- **Next steps**: What happens next
- **Blockers**: Any impediments to progress
- **Time estimate**: Overall time to completion

### Present to User
Master delivers single, comprehensive update that tells the complete story of progress across all domains, maintaining context and narrative coherence.
