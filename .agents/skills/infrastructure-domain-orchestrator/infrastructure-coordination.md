# Infrastructure Team Coordination Patterns

Coordinate multiple infrastructure specialists to accomplish complex deployment, maintenance, and incident response tasks.

## Common Coordination Patterns

### Pattern 1: Initial Deployment Setup

**Scenario**: Setup complete production infrastructure from scratch

**Required Specialists**:
1. IaC Specialist - Define infrastructure
2. Cloud Specialist - Provision resources
3. Docker Specialist - Containerize application
4. CI/CD Specialist - Automate deployment
5. Monitoring Specialist - Setup observability
6. Security Specialist - Audit and secure

**Workflow Type**: Sequential foundation-first approach

**Coordination Flow**:
```
1. IaC Specialist
   ├─ Define infrastructure in Terraform/CloudFormation
   ├─ Create resource definitions
   ├─ Setup state management
   └─ Output: Infrastructure code ready for provisioning

2. Cloud Specialist
   ├─ Review IaC definitions
   ├─ Provision cloud resources
   ├─ Configure networking
   └─ Output: Cloud infrastructure ready for deployment

3. Docker Specialist
   ├─ Analyze application requirements
   ├─ Create Dockerfile
   ├─ Build container image
   └─ Output: Containerized application ready for orchestration

4. CI/CD Specialist
   ├─ Configure build pipeline
   ├─ Setup automated testing
   ├─ Create deployment workflow
   └─ Output: Automated deployment pipeline operational

5. Monitoring Specialist
   ├─ Setup monitoring dashboards
   ├─ Configure log aggregation
   ├─ Implement alerting rules
   └─ Output: Full observability infrastructure

6. Security Specialist
   ├─ Perform security audit
   ├─ Run vulnerability scans
   ├─ Configure security policies
   └─ Output: Security baseline established
```

**Dependencies**: Each layer builds on previous layer foundation

**Estimated Duration**: 4-8 hours for complete setup

**Failure Handling**: If any specialist fails, pause and resolve before continuing

### Pattern 2: CI/CD Pipeline Creation

**Scenario**: Create automated build and deployment pipeline

**Required Specialists**:
1. Docker Specialist - Containerize application
2. CI/CD Specialist - Configure pipeline
3. Cloud Specialist - Setup deployment targets
4. Monitoring Specialist - Track pipeline metrics

**Workflow Type**: Sequential with parallel testing phases

**Coordination Flow**:
```
1. Docker Specialist
   ├─ Create Dockerfile
   ├─ Optimize container image
   ├─ Setup multi-stage builds
   └─ Output: Production-ready container

2. CI/CD Specialist
   ├─ Configure build workflow
   ├─ Setup automated tests (parallel)
   │  ├─ Unit tests
   │  ├─ Integration tests
   │  └─ E2E tests
   ├─ Create deployment stages
   └─ Output: Complete CI/CD pipeline

3. Cloud Specialist (parallel with testing)
   ├─ Setup staging environment
   ├─ Setup production environment
   ├─ Configure deployment targets
   └─ Output: Cloud environments ready

4. Monitoring Specialist
   ├─ Track build metrics
   ├─ Monitor deployment success rate
   ├─ Setup pipeline alerts
   └─ Output: Pipeline observability
```

**Dependencies**: Docker → CI/CD → Deployment, with parallel cloud setup

**Estimated Duration**: 2-4 hours

**Failure Handling**: Failed builds trigger rollback, failed deploys keep previous version

### Pattern 3: Infrastructure Update

**Scenario**: Update production infrastructure with new components

**Required Specialists**:
1. IaC Specialist - Update infrastructure definition
2. Security Specialist - Security review
3. Cloud Specialist - Apply changes
4. Monitoring Specialist - Verify changes

**Workflow Type**: Safety-first with rollback capability

**Coordination Flow**:
```
1. IaC Specialist
   ├─ Update infrastructure code
   ├─ Plan infrastructure changes
   ├─ Review change impact
   └─ Output: Infrastructure update ready

2. Security Specialist (review phase)
   ├─ Review infrastructure changes
   ├─ Check for security implications
   ├─ Verify compliance requirements
   └─ Output: Security approval or concerns

   If concerns raised:
   └─ Return to IaC Specialist for revision

3. Cloud Specialist
   ├─ Create backup/snapshot
   ├─ Apply infrastructure changes
   ├─ Verify resource state
   └─ Output: Infrastructure updated

   If update fails:
   └─ Execute rollback procedure

4. Monitoring Specialist
   ├─ Verify metrics after update
   ├─ Check for anomalies
   ├─ Confirm system health
   └─ Output: Update verification complete
```

**Dependencies**: Sequential with safety checks at each stage

**Estimated Duration**: 1-3 hours depending on complexity

**Failure Handling**: Automatic rollback on failure, preserve previous state

### Pattern 4: Incident Response

**Scenario**: Production outage or critical issue

**Required Specialists**:
1. Monitoring Specialist - Detect and diagnose
2. Cloud Specialist - Check cloud resources
3. Security Specialist - Rule out security incidents
4. CI/CD Specialist - Deploy hotfix if needed

**Workflow Type**: Rapid response with parallel investigation

**Coordination Flow**:
```
1. Monitoring Specialist (incident detection)
   ├─ Identify issue from metrics/logs
   ├─ Determine severity
   ├─ Alert relevant specialists
   └─ Output: Incident classification

2. Parallel Investigation:

   Cloud Specialist:
   ├─ Check cloud service health
   ├─ Review resource utilization
   ├─ Check for cloud provider issues
   └─ Output: Cloud infrastructure status

   Security Specialist:
   ├─ Check for security events
   ├─ Review access logs
   ├─ Rule out security breach
   └─ Output: Security assessment

3. Root Cause Identified → CI/CD Specialist
   ├─ Prepare hotfix deployment
   ├─ Fast-track testing
   ├─ Deploy emergency fix
   └─ Output: Service restored

4. Monitoring Specialist (verification)
   ├─ Confirm service recovery
   ├─ Monitor for stability
   ├─ Document incident timeline
   └─ Output: Incident resolved
```

**Dependencies**: Parallel investigation, sequential remediation

**Estimated Duration**: 15 minutes to 2 hours depending on severity

**Failure Handling**: Escalate if initial fix doesn't work, implement temporary workaround

## Coordination Algorithm

```python
def coordinate_infrastructure_team(task):
    """
    Coordinate multiple infrastructure specialists for a complex task.

    Returns coordination plan with specialist assignments and workflow.
    """
    # Identify required specialists
    required_specialists = identify_specialists(task)

    # Classify task type
    task_type = classify_task(task)  # setup, update, incident, maintenance

    # Select coordination pattern
    if task_type == 'incident':
        plan = coordinate_incident_response(required_specialists, task)
    elif task_type == 'setup':
        plan = coordinate_initial_setup(required_specialists, task)
    elif task_type == 'update':
        plan = coordinate_infrastructure_update(required_specialists, task)
    else:
        plan = coordinate_standard_operation(required_specialists, task)

    return plan

def coordinate_incident_response(specialists, task):
    """
    Coordinate rapid incident response with parallel investigation.
    """
    plan = {
        'type': 'incident_response',
        'urgency': 'critical',
        'workflow': 'parallel_investigation',
        'phases': [
            {
                'name': 'detection',
                'specialists': ['monitoring'],
                'parallel': False
            },
            {
                'name': 'investigation',
                'specialists': ['cloud', 'security'],
                'parallel': True  # Investigate simultaneously
            },
            {
                'name': 'remediation',
                'specialists': ['cicd'],
                'parallel': False
            },
            {
                'name': 'verification',
                'specialists': ['monitoring'],
                'parallel': False
            }
        ],
        'rollback_plan': None,  # Incident response focuses on fix
        'estimated_duration': '15m-2h'
    }
    return plan

def coordinate_initial_setup(specialists, task):
    """
    Coordinate full infrastructure setup with sequential dependencies.
    """
    plan = {
        'type': 'initial_setup',
        'urgency': 'standard',
        'workflow': 'sequential_foundation',
        'phases': [
            {'name': 'define', 'specialists': ['iac'], 'parallel': False},
            {'name': 'provision', 'specialists': ['cloud'], 'parallel': False},
            {'name': 'containerize', 'specialists': ['docker'], 'parallel': False},
            {'name': 'automate', 'specialists': ['cicd'], 'parallel': False},
            {'name': 'observe', 'specialists': ['monitoring'], 'parallel': False},
            {'name': 'secure', 'specialists': ['security'], 'parallel': False}
        ],
        'rollback_plan': 'destroy_infrastructure',
        'estimated_duration': '4-8h'
    }
    return plan

def coordinate_infrastructure_update(specialists, task):
    """
    Coordinate infrastructure update with safety checks.
    """
    plan = {
        'type': 'infrastructure_update',
        'urgency': 'standard',
        'workflow': 'sequential_with_safety',
        'phases': [
            {'name': 'update_definition', 'specialists': ['iac'], 'parallel': False},
            {'name': 'security_review', 'specialists': ['security'], 'parallel': False},
            {'name': 'apply_changes', 'specialists': ['cloud'], 'parallel': False},
            {'name': 'verify', 'specialists': ['monitoring'], 'parallel': False}
        ],
        'rollback_plan': 'restore_previous_state',
        'estimated_duration': '1-3h'
    }
    return plan
```

## Cross-Specialist Communication

Infrastructure specialists need to share context and state throughout coordination:

### Information Sharing Patterns

**Infrastructure State**:
- Current resource inventory
- Configuration versions
- Deployment history
- Performance baselines

**Deployment Configurations**:
- Container image tags
- Environment variables
- Service dependencies
- Resource requirements

**Security Requirements**:
- Authentication mechanisms
- Encryption standards
- Compliance requirements
- Access control policies

**Monitoring Metrics**:
- Key performance indicators
- Alert thresholds
- Log retention policies
- Dashboard configurations

### Communication Protocol

```
Specialist A (upstream):
├─ Complete task phase
├─ Generate output artifacts
├─ Document state changes
└─ Notify downstream specialist

Specialist B (downstream):
├─ Receive notification
├─ Load context from upstream
├─ Validate input artifacts
├─ Begin task phase
```

## Safety and Rollback Procedures

Every infrastructure operation must have a rollback plan:

### Blue-Green Deployment Pattern

**Approach**: Maintain two identical production environments

**Process**:
1. Deploy new version to inactive environment (green)
2. Test green environment thoroughly
3. Switch traffic from blue to green
4. Keep blue as instant rollback option
5. After stability confirmed, update blue to match green

**Rollback**: Instant traffic switch back to blue

### Canary Release Pattern

**Approach**: Gradual rollout to subset of users

**Process**:
1. Deploy new version to canary infrastructure (5% traffic)
2. Monitor canary metrics vs baseline
3. If healthy, increase to 25% traffic
4. If healthy, increase to 50% traffic
5. If healthy, complete rollout to 100%

**Rollback**: Route canary traffic back to stable version at any point

### Infrastructure Snapshot Pattern

**Approach**: Create point-in-time snapshots before changes

**Process**:
1. Create snapshot of current infrastructure state
2. Apply infrastructure changes
3. Verify changes successful
4. Keep snapshot for recovery window (24-72 hours)

**Rollback**: Restore from snapshot to previous state

### Automated Rollback Triggers

Monitor for these conditions and trigger automatic rollback:

- Error rate > 5% above baseline
- Response time > 2x baseline
- Service availability < 99%
- Critical alerts firing
- Health check failures

## Performance Optimization

Optimize infrastructure coordination for speed and efficiency:

### Parallel Execution

Execute specialists in parallel when safe:

**Safe to Parallelize**:
- Cloud environment setup while Docker containerizes
- Monitoring configuration while CI/CD pipeline builds
- Security scanning while tests run

**Must Be Sequential**:
- IaC definition before cloud provisioning
- Cloud provisioning before application deployment
- Deployment before monitoring verification

### State Caching

Cache infrastructure state to avoid repeated queries:

- Cache resource inventory for 5 minutes
- Cache configuration versions for 10 minutes
- Cache deployment history for 30 minutes
- Invalidate cache on state changes

### Incremental Updates

Apply changes incrementally rather than full replacement:

- Update only changed resources
- Preserve unchanged infrastructure
- Minimize deployment disruption
- Reduce update duration

## Reporting to Master Orchestrator

Infrastructure Domain Orchestrator reports all progress to Master:

### Status Report Format

```python
status_report = {
    'orchestrator': 'infrastructure-domain',
    'instance_id': 'infra-001',
    'task_id': 'deploy-prod-123',
    'status': 'in_progress',
    'progress': 0.6,  # 60% complete
    'active_specialists': ['docker', 'cicd', 'monitoring'],
    'completed_phases': ['define', 'provision', 'containerize'],
    'current_phase': 'automate',
    'estimated_completion': '2026-02-04T16:30:00Z',
    'critical_alerts': [],
    'coordination_pattern': 'initial_setup'
}
```

### Update Frequency

- **Regular updates**: Every 5 minutes during active coordination
- **Phase completion**: Immediate update when phase completes
- **Critical alerts**: Immediate notification
- **Task completion**: Final summary report

### Critical Alert Escalation

Immediately notify Master Orchestrator for:

- Deployment failures
- Security incidents
- Service outages
- Resource exhaustion
- Specialist failures

## Example Coordination Scenarios

### Scenario 1: Deploy New Microservice

**Task**: "Deploy new user-service microservice to production"

**Coordination Plan**:
1. Docker Specialist: Containerize user-service
2. Cloud Specialist: Setup service infrastructure
3. CI/CD Specialist: Configure deployment pipeline
4. Monitoring Specialist: Setup service monitoring
5. Security Specialist: Security audit

**Workflow**: Sequential setup with parallel monitoring configuration

**Estimated Duration**: 2-3 hours

### Scenario 2: Database Migration

**Task**: "Migrate database from PostgreSQL 12 to PostgreSQL 15"

**Coordination Plan**:
1. IaC Specialist: Define new database infrastructure
2. Cloud Specialist: Provision new database
3. Monitoring Specialist: Setup migration monitoring
4. Security Specialist: Review migration security
5. CI/CD Specialist: Deploy migration scripts

**Workflow**: Sequential with extensive testing and rollback capability

**Estimated Duration**: 4-6 hours

### Scenario 3: Scale Infrastructure

**Task**: "Scale infrastructure to handle 10x traffic increase"

**Coordination Plan**:
1. Monitoring Specialist: Analyze current capacity
2. IaC Specialist: Update scaling definitions
3. Cloud Specialist: Implement auto-scaling
4. Monitoring Specialist: Verify scaling behavior

**Workflow**: Analysis → Definition → Implementation → Verification

**Estimated Duration**: 1-2 hours
