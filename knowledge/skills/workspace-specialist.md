---
name: workspace-specialist
version: 1.0.0
author: Agent Skills System
description: Expert in workspace management with complete mastery of workspace MCP tools including project organization, hierarchical structures, access control, and team collaboration
trigger_domain: mcp
trigger_keywords:
  - workspace management
  - workspace organization
  - workspace hierarchy
  - workspace sharing
  - access control
  - team collaboration
  - project workspace
  - workspace lifecycle
  - workspace permissions
  - parallel workspaces
  - sequential workspaces
tools_required:
  - workspace (MCP Handler)
progressive_disclosure:
  - level: 1
    content: workspace_overview
  - level: 2
    content: workspace_management_tools
  - level: 3
    content: workspace_hierarchy
  - level: 4
    content: workspace_sharing
  - level: 5
    content: workspace_metadata
  - level: 6
    content: workspace_patterns
  - level: 7
    content: workspace_examples
---

# Workspace Specialist Agent

## Overview

This agent specializes in **workspace management** using the Workspace MCP Handler. It provides expert-level capabilities for creating, organizing, and managing project workspaces with hierarchical structures, role-based access control, and team collaboration features.

**Primary Database:** `boardroom.db`
**MCP Handler:** `workspace` (115 methods with auto-discovery)
**Core Class:** `WorkspaceSharing`

---

## Workspace Management Tools

### 1. Workspace CRUD Operations

#### Create Workspace
```python
workspace_id = create_workspace(
    name="Project Alpha Development",
    description="Main development workspace for Project Alpha",
    created_by=user_id,
    parent_workspace_id=None,  # Top-level workspace
    project_id=project_id,
    is_project_workspace=True
)
```

**Parameters:**
- `name`: Workspace name (TEXT, required)
- `description`: Workspace purpose/details (TEXT, optional)
- `created_by`: User ID creating workspace (INTEGER, required)
- `parent_workspace_id`: Parent workspace ID for hierarchy (INTEGER, optional)
- `project_id`: Associated project ID (INTEGER, optional)
- `is_project_workspace`: Project-level workspace flag (BOOLEAN, default False)

#### Read Workspace
```python
workspace = get_workspace(workspace_id)
# Returns: {
#     "id": 42,
#     "name": "Project Alpha Development",
#     "description": "Main development workspace",
#     "created_by": 1,
#     "created_at": "2026-02-04T10:30:00Z",
#     "metadata": {...},
#     "parent_workspace_id": None,
#     "project_id": 7,
#     "is_project_workspace": True,
#     "completion_percentage": 0.65
# }
```

#### Update Workspace
```python
update_workspace(
    workspace_id=42,
    name="Project Alpha - Phase 2",
    description="Updated for Phase 2 development",
    completion_percentage=0.85
)
```

**Updatable Fields:**
- `name`: Workspace name
- `description`: Workspace details
- `completion_percentage`: Progress (0.0 to 1.0)
- `metadata`: Custom JSON metadata

#### Delete/Archive Workspace
```python
# Archive workspace (preserves data)
archive_workspace(workspace_id=42)

# Permanently delete (use with caution)
delete_workspace(workspace_id=42)
```

**Archive vs Delete:**
- **Archive**: Marks workspace as inactive, preserves all data for debugging/analysis
- **Delete**: Removes workspace permanently, cascades to child workspaces

### 2. Workspace Relationships

#### Create Hierarchical Structure
```python
# Create parent workspace
parent_id = create_workspace(
    name="Master Orchestrator Workspace",
    created_by=orchestrator_id
)

# Create child workspace with relationship
child_id = create_workspace(
    name="Frontend Domain Workspace",
    parent_workspace_id=parent_id,
    created_by=orchestrator_id
)

# Define relationship type
create_workspace_relationship(
    parent_workspace_id=parent_id,
    child_workspace_id=child_id,
    relationship_type="parallel"  # or "sequential"
)
```

**Relationship Types:**
- **parallel**: Child workspaces can execute simultaneously
- **sequential**: Child workspaces must execute in order

#### Query Workspace Hierarchy
```python
# Get all child workspaces
children = get_child_workspaces(parent_workspace_id=parent_id)

# Get parent workspace
parent = get_parent_workspace(workspace_id=child_id)

# Get full workspace tree
tree = get_workspace_tree(root_workspace_id=parent_id)
# Returns hierarchical structure with all descendants
```

### 3. Workspace Sharing and Access Control

#### Share Workspace with User
```python
share_workspace(
    workspace_id=42,
    user_id=user_id,
    role="editor",  # owner/admin/editor/viewer
    shared_by=owner_id,
    expiry_date="2026-12-31T23:59:59Z"  # Optional
)
```

**Workspace Roles:**
- **owner**: Full control (delete, transfer ownership)
- **admin**: Management capabilities (sharing, configuration)
- **editor**: Edit content (create tasks, update status)
- **viewer**: Read-only access (view but not modify)

#### Share Workspace with Team
```python
# First create or get team
team_id = create_team(
    name="Frontend Development Team",
    created_by=team_lead_id,
    description="Team responsible for frontend development"
)

# Share workspace with entire team
share_workspace_with_team(
    workspace_id=42,
    team_id=team_id,
    role="editor",
    shared_by=owner_id
)
```

#### Manage Access Permissions
```python
# Update user role
update_workspace_access(
    workspace_id=42,
    user_id=user_id,
    new_role="admin"
)

# Revoke access
revoke_workspace_access(
    workspace_id=42,
    user_id=user_id
)

# Get all users with access
users = get_workspace_users(workspace_id=42)
# Returns list of users with their roles
```

### 4. Workspace Metadata Management

#### Set Custom Metadata
```python
set_workspace_metadata(
    workspace_id=42,
    metadata={
        "tech_stack": ["React", "TypeScript", "Node.js"],
        "deadline": "2026-06-30",
        "priority": "high",
        "domain": "frontend",
        "orchestrator_instance": 1,
        "custom_fields": {
            "repository": "github.com/org/repo",
            "deployment_env": "staging"
        }
    }
)
```

**Recommended Metadata Fields:**
- `domain`: Domain type (frontend, backend, infrastructure, quality, mcp)
- `orchestrator_instance`: Instance number for spawned orchestrators
- `tech_stack`: Technologies used in workspace
- `priority`: Workspace priority (high/medium/low)
- `deadline`: Project deadline (ISO 8601 format)
- `custom_fields`: Any additional project-specific data

#### Query Metadata
```python
# Get workspace metadata
metadata = get_workspace_metadata(workspace_id=42)

# Search workspaces by metadata
workspaces = search_workspaces_by_metadata(
    filter_criteria={"domain": "frontend", "priority": "high"}
)
```

---

## Workspace Hierarchy

### Three-Tier Hierarchical Model

The workspace system implements a **three-tier hierarchical structure** to prevent bottlenecks and enable specialization:

```
Level 0: Master Orchestrator Workspace
    │
    ├─ Level 1: Domain Orchestrator Workspace (Frontend)
    │       │
    │       ├─ Level 2: Worker Agent Workspace (React Components)
    │       └─ Level 2: Worker Agent Workspace (State Management)
    │
    ├─ Level 1: Domain Orchestrator Workspace (Backend)
    │       │
    │       ├─ Level 2: Worker Agent Workspace (API Endpoints)
    │       └─ Level 2: Worker Agent Workspace (Database Schema)
    │
    └─ Level 1: Domain Orchestrator Workspace (Infrastructure)
            │
            ├─ Level 2: Worker Agent Workspace (CI/CD Pipeline)
            └─ Level 2: Worker Agent Workspace (Docker Configuration)
```

### Hierarchical Benefits

#### 1. Scalability
- **No single bottleneck**: Domain orchestrators can spawn in parallel
- **Dynamic scaling**: More domains = more orchestrators = more capacity
- **Load distribution**: Each domain handles subset of total workload

#### 2. Specialization
- **Domain expertise**: Frontend orchestrator knows frontend patterns
- **Focused learning**: Each domain learns from its own successes/failures
- **Specialized agents**: Workers can be hyper-specialized within domain

#### 3. Failure Isolation
- **Contained failures**: Domain failure doesn't crash master
- **Independent recovery**: Domain can research and retry independently
- **Graceful degradation**: Other domains continue while one recovers

#### 4. Organization
- **Clear hierarchy**: Master → Domain → Worker
- **Easy tracking**: Parent-child relationships in database
- **Progress rollup**: Domain progress aggregates to master completion

### Workspace Lifecycle Management

#### 1. Creation Phase
```python
# Master orchestrator creates workspace
workspace_id = create_workspace(
    name="Feature Development: User Authentication",
    parent_workspace_id=master_workspace_id,
    relationship_type="parallel",
    created_by=orchestrator_id,
    metadata={"domain": "backend", "feature": "auth"}
)
```

#### 2. Active Usage Phase
- Agents communicate within shared workspace
- Communication logged to conversation timeline
- Task status updates propagated through hierarchy
- Real-time collaboration via WebSocket

#### 3. Archival Phase
```python
# Mark workspace as completed
update_workspace(
    workspace_id=workspace_id,
    completion_percentage=1.0
)

# Archive workspace
archive_workspace(workspace_id=workspace_id)
```

**Archival Properties:**
- Completed tasks archived with metadata
- Workspace marked as inactive
- Historical data preserved for learning
- Conversation timeline maintained

#### 4. Cleanup Phase
```python
# Garbage collection of expired access
cleanup_expired_access(workspace_id=workspace_id)

# Remove orphaned workspaces
cleanup_orphaned_workspaces()
```

---

## Workspace Sharing

### Team Management

#### Create and Manage Teams
```python
# Create team
team_id = create_team(
    name="Backend Development Team",
    created_by=team_lead_id,
    description="Team responsible for API and database development",
    metadata={"department": "engineering", "specialization": "backend"}
)

# Add team members
add_team_member(team_id=team_id, user_id=developer_id, role="member")
add_team_member(team_id=team_id, user_id=senior_dev_id, role="lead")

# Update team
update_team(team_id=team_id, name="Backend & Infrastructure Team")

# Remove team member
remove_team_member(team_id=team_id, user_id=developer_id)
```

### Access Control Patterns

#### Time-Limited Access
```python
# Grant temporary access for contractor
share_workspace(
    workspace_id=42,
    user_id=contractor_id,
    role="editor",
    shared_by=owner_id,
    expiry_date="2026-03-31T23:59:59Z"  # Access expires end of March
)
```

#### Role-Based Permissions
```python
# Owner can:
# - Delete workspace
# - Transfer ownership
# - Manage all settings

# Admin can:
# - Share workspace with others
# - Modify workspace configuration
# - Manage team access

# Editor can:
# - Create and modify tasks
# - Add comments
# - Update content

# Viewer can:
# - View workspace contents
# - Read tasks and comments
# - No modification permissions
```

### Audit Trail

```python
# Get access change history
audit_log = get_workspace_audit_log(workspace_id=42)
# Returns: [
#     {
#         "timestamp": "2026-02-04T10:30:00Z",
#         "action": "access_granted",
#         "user_id": 5,
#         "role": "editor",
#         "performed_by": 1
#     },
#     {
#         "timestamp": "2026-02-04T11:15:00Z",
#         "action": "role_updated",
#         "user_id": 5,
#         "old_role": "editor",
#         "new_role": "admin",
#         "performed_by": 1
#     }
# ]
```

---

## Workspace Patterns

### Pattern 1: Master-Domain-Worker Coordination

**Use Case:** Large multi-domain project requiring coordinated effort

```python
# 1. Master creates domain workspaces
frontend_workspace = create_workspace(
    name="Frontend Development Domain",
    parent_workspace_id=master_workspace_id,
    relationship_type="parallel"
)

backend_workspace = create_workspace(
    name="Backend Development Domain",
    parent_workspace_id=master_workspace_id,
    relationship_type="parallel"
)

# 2. Domain orchestrators create worker workspaces
react_workspace = create_workspace(
    name="React Components Worker",
    parent_workspace_id=frontend_workspace,
    relationship_type="parallel"
)

api_workspace = create_workspace(
    name="API Endpoints Worker",
    parent_workspace_id=backend_workspace,
    relationship_type="sequential"
)

# 3. Track progress rollup
frontend_completion = calculate_domain_completion(frontend_workspace)
overall_completion = calculate_project_completion(master_workspace_id)
```

### Pattern 2: Sequential Task Execution

**Use Case:** Tasks with strict ordering requirements

```python
# Create sequential pipeline
pipeline_workspace = create_workspace(name="Deployment Pipeline", ...)

step1 = create_workspace(
    name="Build Stage",
    parent_workspace_id=pipeline_workspace,
    relationship_type="sequential"
)

step2 = create_workspace(
    name="Test Stage",
    parent_workspace_id=pipeline_workspace,
    relationship_type="sequential"
)

step3 = create_workspace(
    name="Deploy Stage",
    parent_workspace_id=pipeline_workspace,
    relationship_type="sequential"
)

# Enforce execution order through metadata
set_workspace_metadata(step2, {"depends_on": [step1.id]})
set_workspace_metadata(step3, {"depends_on": [step2.id]})
```

### Pattern 3: Parallel Feature Development

**Use Case:** Independent features developed simultaneously

```python
# Create parallel feature workspaces
feature_parent = create_workspace(name="Sprint 5 Features", ...)

feature1 = create_workspace(
    name="User Profile Feature",
    parent_workspace_id=feature_parent,
    relationship_type="parallel"  # Can work independently
)

feature2 = create_workspace(
    name="Search Feature",
    parent_workspace_id=feature_parent,
    relationship_type="parallel"  # Can work independently
)

# Features complete independently
# Progress aggregates to sprint workspace
```

### Pattern 4: Research-Skill-Retry Pattern

**Use Case:** Automated learning from task failures

```python
# 1. Task fails in execution workspace
try:
    execute_task(task)
except Exception as e:
    # 2. Create research workspace
    research_workspace = create_workspace(
        name="Research: Task Failure Analysis",
        parent_workspace_id=execution_workspace_id,
        relationship_type="sequential",
        metadata={
            "type": "research",
            "original_task_id": task.id,
            "error_info": str(e)
        }
    )

    # 3. Conduct research in dedicated workspace
    research_result = conduct_failure_research(research_workspace)

    # 4. Update skills based on research
    update_agent_skills(research_result.skill_updates)

    # 5. Retry with new skills in fresh workspace
    retry_workspace = create_workspace(
        name="Retry: Task Execution",
        parent_workspace_id=execution_workspace_id,
        relationship_type="sequential",
        metadata={
            "type": "retry",
            "research_workspace_id": research_workspace.id
        }
    )

    retry_result = execute_task_with_new_skills(task, retry_workspace)
```

---

## Workspace Examples

### Example 1: Complete Project Workspace Setup

```python
# Create project workspace
project_id = create_workspace(
    name="E-commerce Platform Rebuild",
    description="Complete rebuild of e-commerce platform with modern stack",
    created_by=project_manager_id,
    is_project_workspace=True,
    metadata={
        "deadline": "2026-08-31",
        "budget": 500000,
        "team_size": 12,
        "tech_stack": ["React", "Node.js", "PostgreSQL", "Redis"]
    }
)

# Create team
team_id = create_team(
    name="E-commerce Development Team",
    created_by=project_manager_id
)

# Share project with team
share_workspace_with_team(
    workspace_id=project_id,
    team_id=team_id,
    role="editor"
)

# Create domain workspaces
frontend_domain = create_workspace(
    name="Frontend Development",
    parent_workspace_id=project_id,
    relationship_type="parallel",
    metadata={"domain": "frontend"}
)

backend_domain = create_workspace(
    name="Backend Development",
    parent_workspace_id=project_id,
    relationship_type="parallel",
    metadata={"domain": "backend"}
)

infrastructure_domain = create_workspace(
    name="Infrastructure Setup",
    parent_workspace_id=project_id,
    relationship_type="sequential",  # Must complete before others
    metadata={"domain": "infrastructure"}
)
```

### Example 2: Dynamic Orchestrator Spawning

```python
# Detect bottleneck in domain
if detect_bottleneck(domain_workspace_id):
    # Spawn additional orchestrator instance
    new_instance = spawn_domain_orchestrator(
        domain_type=domain_type,
        instance_number=current_instances + 1
    )

    # Create workspace for new instance
    new_workspace = create_workspace(
        name=f"{domain_type} Domain Instance {new_instance}",
        parent_workspace_id=master_workspace_id,
        relationship_type="parallel",
        metadata={
            "domain": domain_type,
            "orchestrator_instance": new_instance,
            "spawned_due_to": "bottleneck_detection"
        }
    )

    # Redistribute workload
    redistribute_tasks(
        from_workspace=domain_workspace_id,
        to_workspace=new_workspace.id
    )
```

### Example 3: Progress Tracking and Reporting

```python
# Calculate workspace completion
def calculate_workspace_completion(workspace_id):
    # Get all child workspaces
    children = get_child_workspaces(workspace_id)

    if not children:
        # Leaf workspace - use task completion
        return get_task_completion_percentage(workspace_id)

    # Aggregate child completions
    total_completion = sum(
        calculate_workspace_completion(child.id)
        for child in children
    )

    return total_completion / len(children)

# Update workspace with calculated completion
completion = calculate_workspace_completion(project_workspace_id)
update_workspace(
    workspace_id=project_workspace_id,
    completion_percentage=completion
)

# Generate progress report
report = generate_workspace_report(project_workspace_id)
# Returns hierarchical view with completion percentages
```

---

## Best Practices

### 1. Workspace Naming
- Use descriptive names that indicate purpose
- Include domain type for clarity
- Add instance numbers for spawned orchestrators
- Example: "Backend Domain Instance 2 - API Development"

### 2. Metadata Usage
- Always set `domain` metadata for orchestrator workspaces
- Include `orchestrator_instance` for spawned instances
- Use custom fields for project-specific tracking
- Store technical details for debugging/analysis

### 3. Hierarchical Organization
- Keep hierarchy to 3 levels maximum (Master → Domain → Worker)
- Use parallel relationships when tasks are independent
- Use sequential relationships when order matters
- Avoid deep nesting beyond 3 levels

### 4. Access Control
- Grant minimum required permissions
- Use teams for group access management
- Set expiry dates for temporary access
- Audit access changes regularly

### 5. Lifecycle Management
- Archive completed workspaces promptly
- Preserve archived data for learning
- Clean up expired access permissions
- Monitor orphaned workspaces

---

## Troubleshooting

### Issue: Workspace Creation Fails
**Causes:**
- Invalid parent_workspace_id (doesn't exist)
- Missing required fields (name, created_by)
- Database connection issues

**Solutions:**
- Verify parent workspace exists before creating child
- Validate all required parameters
- Check database connection pool status

### Issue: Slow Workspace Queries
**Causes:**
- Large number of child workspaces
- Complex metadata searches
- Connection pool exhaustion

**Solutions:**
- Use pagination for large result sets
- Index frequently queried metadata fields
- Increase connection pool size if needed
- Cache frequently accessed workspaces

### Issue: Access Control Not Working
**Causes:**
- Expired permissions
- Incorrect role assignment
- Team membership not updated

**Solutions:**
- Check expiry_date on workspace_shares
- Verify role matches required permissions
- Ensure user is active team member

---

**Workspace Specialist Agent Ready**
**Capabilities:** Complete mastery of workspace MCP with 115 methods
**Primary Focus:** Project organization, hierarchical structures, access control, team collaboration
