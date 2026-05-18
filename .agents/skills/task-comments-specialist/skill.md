---
name: task-comments-specialist
version: 1.0.0
author: Agent Skills System
description: Expert in task communication with complete mastery of task_comments MCP tools including comment management, threaded discussions, mention system, and notification workflows
trigger_domain: mcp
trigger_keywords:
  - task comments
  - task discussion
  - comment thread
  - mention user
  - task notification
  - agent communication
  - conversation timeline
  - task collaboration
  - comment history
  - team communication
tools_required:
  - task_comments (MCP Handler)
progressive_disclosure:
  - level: 1
    content: task_comments_overview
  - level: 2
    content: comment_tools
  - level: 3
    content: threading_system
  - level: 4
    content: mention_notifications
  - level: 5
    content: timeline_integration
  - level: 6
    content: communication_patterns
  - level: 7
    content: collaboration_examples
---

# Task Comments Specialist Agent

## Overview

This agent specializes in **task communication and collaboration** using the Task Comments MCP Handler. It provides expert-level capabilities for managing threaded discussions, implementing mention systems, tracking agent communication, and linking comments to conversation timelines.

**Primary Database:** `boardroom.db` (via WorkspaceSharingManager)
**MCP Handler:** `task_comments`
**Core Class:** `WorkspaceTaskCommentManager` with `WorkspaceTaskCommentsIntegration`

---

## Task Comments Tools

### 1. Comment CRUD Operations

#### Add Comment to Task
```python
success, comment_id = add_comment(
    task_id=42,
    author_id="master_orchestrator",
    author_type="agent",  # agent/user/system
    content="Starting frontend development domain",
    technical_details={
        "domain": "frontend",
        "agents_spawned": 3,
        "estimated_duration": 7200
    }
)
```

**Parameters:**
- `task_id`: Task being commented on (INTEGER, required)
- `author_id`: Author identifier - agent ID or user ID (TEXT, required)
- `author_type`: Author type - "agent", "user", or "system" (TEXT, required)
- `content`: Comment text (TEXT, required)
- `technical_details`: Additional structured data (JSON, optional)

**Returns:**
- `success`: Boolean indicating operation success
- `comment_id`: Unique identifier for created comment

#### Read Task Comments
```python
success, comments = get_task_comments(
    task_id=42,
    author_type=None,  # Filter by author type (optional)
    limit=50,          # Maximum comments to return
    offset=0           # Pagination offset
)

# Returns list of comments:
# [
#     {
#         "id": 1,
#         "task_id": 42,
#         "author_id": "master_orchestrator",
#         "author_type": "agent",
#         "content": "Starting frontend development domain",
#         "technical_details": {...},
#         "created_at": "2026-02-04T10:30:00Z"
#     },
#     ...
# ]
```

**Filtering Options:**
- Filter by `author_type` (agent/user/system)
- Filter by `author_id` (specific agent or user)
- Filter by date range (created_at)
- Sort by created_at (ascending/descending)

#### Update Comment
```python
success = update_comment(
    comment_id=1,
    content="Updated: Frontend domain spawned 3 specialist agents",
    technical_details={
        "domain": "frontend",
        "agents_spawned": 3,
        "agents": ["react_specialist", "styling_specialist", "state_specialist"]
    }
)
```

**Updatable Fields:**
- `content`: Comment text
- `technical_details`: Additional data
- Automatically sets `updated_at` timestamp

#### Delete Comment
```python
success = delete_comment(comment_id=1)
```

**Delete Behavior:**
- Soft delete (marks as deleted, preserves data)
- Hard delete available for cleanup operations
- Child comments in thread preserved (orphan handling)

### 2. Enhanced Comment Operations (with Timeline Integration)

#### Add Comment with Timeline Link
```python
from Database.workspace_task_comments_integration import WorkspaceTaskCommentsIntegration

integration = WorkspaceTaskCommentsIntegration()

result = integration.add_task_comment_with_timeline_link(
    task_id=42,
    workspace_id=7,
    comment_text="Completed React component creation",
    author_id="frontend_agent_1",
    author_type="agent",
    comment_type="status_update",  # user_comment/agent_response/status_update
    conversation_timeline_events=[
        {
            "event_type": "message_sent",
            "timestamp": 1738684800,
            "event_id": "msg_12345",
            "journey_id": "journey_67890",
            "session_id": "session_abc123",
            "content_preview": "Created UserProfile component with TypeScript"
        }
    ],
    agent_communication_data={
        "agent": "frontend_agent_1",
        "status": "completed",
        "files_modified": ["src/components/UserProfile.tsx"],
        "lines_added": 150
    }
)
```

**Enhanced Parameters:**
- `workspace_id`: Associated workspace (INTEGER, required)
- `comment_type`: Comment category (TEXT, required)
- `conversation_timeline_events`: Array of timeline events (JSON)
- `agent_communication_data`: Agent-specific communication data (JSON)
- `parent_comment_id`: For threaded replies (INTEGER, optional)

#### Get Comments with Full Context
```python
comments = integration.get_task_comments_with_timeline(
    task_id=42,
    include_conversation_context=True,
    include_agent_communication=True
)

# Returns enhanced comments with:
# - Full conversation timeline links
# - Agent communication data
# - Thread hierarchy information
# - Related workspace context
```

---

## Threading System

### Comment Threading Architecture

Task comments support **threaded discussions** allowing nested conversations within task context:

```
Task #42: Implement User Authentication
├─ Comment #1: [master_orchestrator] "Breaking down into subtasks"
│   ├─ Comment #2: [backend_agent] "I'll handle the API endpoints"
│   │   └─ Comment #5: [backend_agent] "API endpoints completed"
│   └─ Comment #3: [frontend_agent] "I'll create the login UI"
│       └─ Comment #6: [frontend_agent] "Login UI completed"
└─ Comment #4: [security_agent] "Reviewing authentication flow for vulnerabilities"
    └─ Comment #7: [security_agent] "Security review complete - approved"
```

### Create Thread Hierarchy

#### Start New Thread
```python
# Top-level comment (no parent)
thread_start_id = add_comment(
    task_id=42,
    author_id="master_orchestrator",
    author_type="agent",
    content="Breaking task into subtasks for parallel execution"
)
```

#### Add Reply to Thread
```python
# Reply to parent comment
reply_id = add_comment_with_timeline_link(
    task_id=42,
    workspace_id=7,
    comment_text="I'll handle the API endpoints",
    author_id="backend_agent",
    author_type="agent",
    parent_comment_id=thread_start_id,  # Creates reply relationship
    comment_type="agent_response"
)
```

#### Add Nested Reply
```python
# Reply to reply (nested threading)
nested_reply_id = add_comment_with_timeline_link(
    task_id=42,
    workspace_id=7,
    comment_text="API endpoints completed successfully",
    author_id="backend_agent",
    author_type="agent",
    parent_comment_id=reply_id,  # Reply to previous reply
    comment_type="status_update"
)
```

### Query Thread Structure

#### Get Comment Thread
```python
thread = get_comment_thread(
    comment_id=thread_start_id,
    max_depth=5  # Maximum nesting levels to retrieve
)

# Returns hierarchical structure:
# {
#     "comment": {...},
#     "replies": [
#         {
#             "comment": {...},
#             "replies": [
#                 {"comment": {...}, "replies": []},
#                 ...
#             ]
#         },
#         ...
#     ]
# }
```

#### Get All Threads for Task
```python
threads = get_task_threads(task_id=42)

# Returns list of top-level comments with nested replies
# Each thread is a separate conversation branch
```

---

## Mention and Notifications

### Mention System

The mention system allows agents and users to notify specific participants about comments:

#### Mention Syntax
```python
# Mention specific agent
comment = add_comment(
    task_id=42,
    author_id="master_orchestrator",
    author_type="agent",
    content="@backend_agent please review the API design for security concerns"
)

# Mention multiple agents
comment = add_comment(
    task_id=42,
    author_id="security_agent",
    author_type="agent",
    content="@backend_agent @frontend_agent security review complete, you can proceed"
)

# Mention user
comment = add_comment(
    task_id=42,
    author_id="qa_agent",
    author_type="agent",
    content="@user_123 please review the test results before deployment"
)
```

#### Parse Mentions from Comment
```python
def extract_mentions(content):
    """Extract @mentions from comment content"""
    import re
    pattern = r'@(\w+)'
    mentions = re.findall(pattern, content)
    return mentions

# Usage
content = "@backend_agent @frontend_agent task requires your attention"
mentions = extract_mentions(content)
# Returns: ["backend_agent", "frontend_agent"]
```

#### Notify Mentioned Agents
```python
def notify_mentioned_agents(comment_id, comment_content):
    """Send notifications to mentioned agents"""
    mentions = extract_mentions(comment_content)

    for agent_id in mentions:
        send_notification(
            recipient_id=agent_id,
            recipient_type="agent",
            notification_type="mention",
            source_comment_id=comment_id,
            message=f"You were mentioned in a comment on task #{task_id}"
        )
```

### Notification System

#### Notification Types
- **mention**: Agent/user mentioned in comment
- **reply**: Reply added to comment you authored
- **status_update**: Task status changed
- **assignment**: Task assigned to agent/user
- **completion**: Task completed
- **error**: Error occurred in task execution

#### Create Notification
```python
notification_id = create_notification(
    recipient_id="backend_agent",
    recipient_type="agent",
    notification_type="mention",
    source_comment_id=comment_id,
    task_id=42,
    workspace_id=7,
    message="You were mentioned in a task comment",
    priority="normal",  # low/normal/high/urgent
    metadata={
        "task_name": "Implement User Authentication",
        "mentioned_by": "master_orchestrator",
        "comment_preview": "please review the API design..."
    }
)
```

#### Notification Triggers

**Automatic Triggers:**
- Comment with @mention → Create mention notification
- Reply to comment → Notify original author
- Task status change → Notify assigned agents
- Error in agent execution → Notify orchestrator

**Manual Triggers:**
```python
# Explicitly trigger notification
trigger_notification(
    task_id=42,
    notification_type="status_update",
    recipients=["master_orchestrator", "domain_orchestrator_1"],
    message="Task completed successfully"
)
```

#### Query Notifications
```python
# Get unread notifications for agent
notifications = get_notifications(
    recipient_id="backend_agent",
    recipient_type="agent",
    read_status=False,  # Unread only
    priority=None       # All priorities
)

# Mark notification as read
mark_notification_read(notification_id=notification_id)

# Bulk mark all as read
mark_all_notifications_read(recipient_id="backend_agent")
```

---

## Timeline Integration

### Conversation Timeline Linking

Task comments can be linked to **conversation timeline events** for complete communication tracking:

#### Timeline Link Structure
```python
timeline_links = [
    {
        "event_type": "message_sent",        # Event type
        "timestamp": 1738684800,             # Unix timestamp
        "event_id": "msg_12345",             # Unique event ID
        "journey_id": "journey_67890",       # User journey ID
        "session_id": "session_abc123",      # Session ID
        "content_preview": "Starting task..." # Event preview
    },
    {
        "event_type": "agent_response",
        "timestamp": 1738684850,
        "event_id": "msg_12346",
        "journey_id": "journey_67890",
        "session_id": "session_abc123",
        "content_preview": "Task accepted..."
    }
]
```

#### Add Comment with Timeline Events
```python
result = add_task_comment_with_timeline_link(
    task_id=42,
    workspace_id=7,
    comment_text="Task execution started",
    author_id="worker_agent_1",
    author_type="agent",
    comment_type="status_update",
    conversation_timeline_events=timeline_links
)
```

#### Retrieve Comments with Timeline Context
```python
# Get comments with full conversation history
comments = get_task_comments_with_timeline(
    task_id=42,
    include_conversation_context=True
)

# Each comment includes:
# - conversation_timeline_links: Array of linked timeline events
# - full_conversation_context: Expanded event details
# - related_messages: Messages from same conversation
```

### Agent Communication Data

Track agent-to-agent communication within task context:

```python
agent_communication_data = {
    "agent": "frontend_agent_1",
    "status": "completed",
    "action": "component_created",
    "files_modified": [
        "src/components/UserProfile.tsx",
        "src/styles/UserProfile.css"
    ],
    "lines_added": 150,
    "lines_deleted": 0,
    "tests_added": 5,
    "dependencies_added": ["@types/react"],
    "execution_time_seconds": 45,
    "next_agent": "styling_specialist"
}

# Add comment with agent communication
add_task_comment_with_timeline_link(
    task_id=42,
    workspace_id=7,
    comment_text="UserProfile component created with TypeScript",
    author_id="frontend_agent_1",
    author_type="agent",
    comment_type="agent_response",
    agent_communication_data=agent_communication_data
)
```

---

## Communication Patterns

### Pattern 1: Status Update Cascade

**Use Case:** Task progresses through multiple agents, each updating status

```python
# Master orchestrator assigns task
add_comment(
    task_id=42,
    author_id="master_orchestrator",
    author_type="agent",
    content="Task assigned to backend domain",
    technical_details={"assigned_to": "backend_domain_orchestrator"}
)

# Domain orchestrator accepts
add_comment(
    task_id=42,
    author_id="backend_domain_orchestrator",
    author_type="agent",
    content="Task accepted, spawning API specialist",
    technical_details={"agent_spawned": "api_specialist_1"}
)

# Worker agent starts
add_comment(
    task_id=42,
    author_id="api_specialist_1",
    author_type="agent",
    content="Starting API endpoint implementation",
    technical_details={"status": "in_progress"}
)

# Worker agent completes
add_comment(
    task_id=42,
    author_id="api_specialist_1",
    author_type="agent",
    content="API endpoint implementation complete",
    technical_details={"status": "completed", "endpoints_created": 5}
)
```

### Pattern 2: Collaborative Problem Solving

**Use Case:** Multiple agents discuss and resolve complex issue

```python
# Agent 1 identifies problem
problem_comment = add_comment(
    task_id=42,
    author_id="backend_agent",
    author_type="agent",
    content="Encountering database connection timeout issues"
)

# Agent 2 suggests solution (reply to thread)
add_comment_with_timeline_link(
    task_id=42,
    workspace_id=7,
    comment_text="@backend_agent try increasing connection pool size to 50",
    author_id="infrastructure_agent",
    author_type="agent",
    parent_comment_id=problem_comment,
    comment_type="agent_response"
)

# Agent 1 implements and reports (nested reply)
add_comment_with_timeline_link(
    task_id=42,
    workspace_id=7,
    comment_text="@infrastructure_agent implemented - issue resolved!",
    author_id="backend_agent",
    author_type="agent",
    parent_comment_id=reply_id,
    comment_type="status_update",
    technical_details={"connection_pool_size": 50, "timeout_resolved": True}
)
```

### Pattern 3: Research-to-Retry Communication

**Use Case:** Agent failure triggers research, skill update, and retry

```python
# 1. Agent reports failure
failure_comment = add_comment(
    task_id=42,
    author_id="worker_agent_1",
    author_type="agent",
    content="Task execution failed: Unknown API endpoint pattern",
    technical_details={"error": "NoHandlerFound", "endpoint": "/api/v2/users"}
)

# 2. Research agent investigates (reply to failure)
add_comment_with_timeline_link(
    task_id=42,
    workspace_id=research_workspace_id,
    comment_text="Researching API endpoint patterns for /api/v2/* routes",
    author_id="research_agent",
    author_type="agent",
    parent_comment_id=failure_comment,
    comment_type="agent_response"
)

# 3. Research agent reports findings
add_comment_with_timeline_link(
    task_id=42,
    workspace_id=research_workspace_id,
    comment_text="Found solution: v2 API uses different authentication pattern",
    author_id="research_agent",
    author_type="agent",
    comment_type="status_update",
    technical_details={"skill_update": "api_v2_auth_pattern"}
)

# 4. Original agent retries with new skill
add_comment_with_timeline_link(
    task_id=42,
    workspace_id=retry_workspace_id,
    comment_text="Retrying with updated API v2 authentication pattern",
    author_id="worker_agent_1",
    author_type="agent",
    comment_type="status_update",
    technical_details={"retry_attempt": 1, "skill_applied": "api_v2_auth_pattern"}
)

# 5. Success report
add_comment_with_timeline_link(
    task_id=42,
    workspace_id=retry_workspace_id,
    comment_text="Task completed successfully with new skill",
    author_id="worker_agent_1",
    author_type="agent",
    comment_type="status_update",
    technical_details={"status": "completed", "skill_learned": True}
)
```

### Pattern 4: User-Agent Collaboration

**Use Case:** User provides input during agent task execution

```python
# Agent requests user input
input_request = add_comment(
    task_id=42,
    author_id="frontend_agent",
    author_type="agent",
    content="@user_123 Which color scheme do you prefer for the dashboard?"
)

# User responds (via UI)
user_response = add_comment(
    task_id=42,
    author_id="user_123",
    author_type="user",
    content="@frontend_agent I prefer the dark theme with blue accents",
    parent_comment_id=input_request
)

# Agent acknowledges and proceeds
add_comment_with_timeline_link(
    task_id=42,
    workspace_id=7,
    comment_text="@user_123 Implementing dark theme with blue accents",
    author_id="frontend_agent",
    author_type="agent",
    parent_comment_id=user_response,
    comment_type="status_update",
    technical_details={"theme": "dark", "accent_color": "blue"}
)
```

---

## Collaboration Examples

### Example 1: Multi-Agent Task Coordination

```python
# Task: Build complete authentication system
# Requires: Backend, Frontend, Security, Testing agents

# 1. Master orchestrator breaks down task
master_comment = add_comment(
    task_id=42,
    author_id="master_orchestrator",
    author_type="agent",
    content="Breaking authentication task into 4 parallel subtasks",
    technical_details={
        "subtasks": [
            "api_endpoints",
            "login_ui",
            "security_review",
            "integration_tests"
        ]
    }
)

# 2. Backend agent claims API subtask (reply to master)
backend_comment = add_comment_with_timeline_link(
    task_id=42,
    workspace_id=backend_workspace_id,
    comment_text="@master_orchestrator Taking API endpoints subtask",
    author_id="backend_agent",
    author_type="agent",
    parent_comment_id=master_comment,
    comment_type="agent_response"
)

# 3. Frontend agent claims UI subtask (reply to master)
frontend_comment = add_comment_with_timeline_link(
    task_id=42,
    workspace_id=frontend_workspace_id,
    comment_text="@master_orchestrator Taking login UI subtask",
    author_id="frontend_agent",
    author_type="agent",
    parent_comment_id=master_comment,
    comment_type="agent_response"
)

# 4. Backend agent completes (update in thread)
add_comment_with_timeline_link(
    task_id=42,
    workspace_id=backend_workspace_id,
    comment_text="@frontend_agent API endpoints ready for integration",
    author_id="backend_agent",
    author_type="agent",
    parent_comment_id=backend_comment,
    comment_type="status_update",
    technical_details={
        "status": "completed",
        "endpoints": ["/api/login", "/api/logout", "/api/refresh"]
    }
)

# 5. Frontend agent integrates
add_comment_with_timeline_link(
    task_id=42,
    workspace_id=frontend_workspace_id,
    comment_text="@backend_agent Integration complete, UI ready for testing",
    author_id="frontend_agent",
    author_type="agent",
    parent_comment_id=frontend_comment,
    comment_type="status_update",
    technical_details={"status": "completed"}
)

# 6. Security agent reviews
security_comment = add_comment_with_timeline_link(
    task_id=42,
    workspace_id=security_workspace_id,
    comment_text="@backend_agent @frontend_agent Security review complete - APPROVED",
    author_id="security_agent",
    author_type="agent",
    parent_comment_id=master_comment,
    comment_type="status_update",
    technical_details={"security_approved": True, "vulnerabilities_found": 0}
)
```

### Example 2: Progress Reporting with Notifications

```python
# Task with multiple checkpoints requiring notifications

# Checkpoint 1: Database setup complete
add_comment_with_timeline_link(
    task_id=42,
    workspace_id=7,
    comment_text="Database schema created successfully",
    author_id="database_agent",
    author_type="agent",
    comment_type="status_update",
    technical_details={"checkpoint": "database_setup", "progress": 0.25}
)

# Notify orchestrator of checkpoint
create_notification(
    recipient_id="master_orchestrator",
    recipient_type="agent",
    notification_type="status_update",
    source_comment_id=comment_id,
    task_id=42,
    message="Checkpoint reached: Database setup complete (25%)"
)

# Checkpoint 2: API implementation complete
add_comment_with_timeline_link(
    task_id=42,
    workspace_id=7,
    comment_text="All API endpoints implemented and tested",
    author_id="backend_agent",
    author_type="agent",
    comment_type="status_update",
    technical_details={"checkpoint": "api_implementation", "progress": 0.50}
)

# Checkpoint 3: Frontend integration complete
add_comment_with_timeline_link(
    task_id=42,
    workspace_id=7,
    comment_text="Frontend successfully integrated with API",
    author_id="frontend_agent",
    author_type="agent",
    comment_type="status_update",
    technical_details={"checkpoint": "frontend_integration", "progress": 0.75}
)

# Final checkpoint: Testing complete
add_comment_with_timeline_link(
    task_id=42,
    workspace_id=7,
    comment_text="All tests passing, ready for deployment",
    author_id="qa_agent",
    author_type="agent",
    comment_type="status_update",
    technical_details={"checkpoint": "testing_complete", "progress": 1.0}
)

# Notify user of completion
create_notification(
    recipient_id="user_123",
    recipient_type="user",
    notification_type="completion",
    task_id=42,
    message="Task completed: Authentication system ready for deployment",
    priority="high"
)
```

### Example 3: Error Recovery with Comment History

```python
# Track error, research, and recovery through comments

# 1. Error occurs
error_comment = add_comment_with_timeline_link(
    task_id=42,
    workspace_id=7,
    comment_text="ERROR: Database connection pool exhausted",
    author_id="backend_agent",
    author_type="agent",
    comment_type="status_update",
    technical_details={
        "error_type": "ConnectionPoolExhausted",
        "pool_size": 20,
        "active_connections": 20,
        "waiting_connections": 15
    }
)

# 2. Infrastructure agent investigates (reply to error)
add_comment_with_timeline_link(
    task_id=42,
    workspace_id=research_workspace_id,
    comment_text="@backend_agent Analyzing connection pool configuration",
    author_id="infrastructure_agent",
    author_type="agent",
    parent_comment_id=error_comment,
    comment_type="agent_response"
)

# 3. Research findings
research_comment = add_comment_with_timeline_link(
    task_id=42,
    workspace_id=research_workspace_id,
    comment_text="Found issue: pool size too small for current load",
    author_id="infrastructure_agent",
    author_type="agent",
    parent_comment_id=error_comment,
    comment_type="status_update",
    technical_details={
        "recommended_pool_size": 50,
        "recommended_max_connections": 100,
        "recommended_timeout": 30
    }
)

# 4. Configuration update
add_comment_with_timeline_link(
    task_id=42,
    workspace_id=infrastructure_workspace_id,
    comment_text="@backend_agent Connection pool configuration updated",
    author_id="infrastructure_agent",
    author_type="agent",
    parent_comment_id=research_comment,
    comment_type="status_update",
    technical_details={
        "pool_size": 50,
        "max_connections": 100,
        "timeout": 30,
        "config_updated": True
    }
)

# 5. Retry successful
add_comment_with_timeline_link(
    task_id=42,
    workspace_id=retry_workspace_id,
    comment_text="@infrastructure_agent Task completed successfully after config update",
    author_id="backend_agent",
    author_type="agent",
    parent_comment_id=research_comment,
    comment_type="status_update",
    technical_details={"status": "completed", "retry_successful": True}
)

# View complete error recovery history
history = get_comment_thread(comment_id=error_comment)
# Shows full conversation: error → investigation → research → fix → success
```

---

## Best Practices

### 1. Comment Content
- Write clear, descriptive comments
- Include relevant technical details
- Use @mentions for direct communication
- Keep comments focused on single topic
- Use appropriate comment_type (status_update, agent_response, user_comment)

### 2. Threading
- Use threads for related conversations
- Keep thread depth reasonable (max 3-4 levels)
- Close threads when topic resolved
- Summarize long threads for clarity

### 3. Mentions and Notifications
- Mention specific agents/users when action required
- Don't over-notify (notification fatigue)
- Use appropriate priority levels
- Clean up old/resolved notifications

### 4. Timeline Integration
- Link comments to conversation events
- Include agent communication data
- Track full communication history
- Enable complete audit trail

### 5. Agent Communication
- Report status changes promptly
- Include technical details for debugging
- Coordinate with other agents via mentions
- Document errors and resolutions

---

## Troubleshooting

### Issue: Comments Not Appearing
**Causes:**
- Invalid task_id
- Database connection issues
- Workspace access restrictions

**Solutions:**
- Verify task exists before adding comment
- Check database connection status
- Confirm user/agent has workspace access

### Issue: Mentions Not Triggering Notifications
**Causes:**
- Mention syntax incorrect (@user_id format required)
- Notification system disabled
- Recipient ID invalid

**Solutions:**
- Use proper @mention syntax
- Verify notification system active
- Check recipient exists in database

### Issue: Thread Hierarchy Broken
**Causes:**
- Invalid parent_comment_id
- Deleted parent comment
- Circular reference

**Solutions:**
- Validate parent exists before creating reply
- Handle orphaned comments gracefully
- Prevent circular parent-child relationships

### Issue: Timeline Links Not Working
**Causes:**
- Invalid event_id or journey_id
- Timeline events not properly formatted
- Missing conversation context

**Solutions:**
- Validate timeline event structure
- Ensure event IDs are unique
- Include all required timeline fields

---

**Task Comments Specialist Agent Ready**
**Capabilities:** Complete mastery of task_comments MCP with timeline integration
**Primary Focus:** Task communication, threaded discussions, mentions, notifications, agent collaboration
