# Infrastructure Agent Selection Logic

Select the correct infrastructure specialist agent based on task characteristics, keywords, and platform requirements.

## Specialist Selection Patterns

### CI/CD Pipeline Specialist

**Trigger Keywords**:
- "CI/CD", "pipeline", "continuous integration", "continuous deployment"
- "GitHub Actions", "GitLab CI", "Jenkins", "CircleCI", "Travis CI"
- "build automation", "automated testing", "deployment automation"
- "build server", "release pipeline", "automated deployment"

**Task Types**:
- Configure CI/CD pipelines
- Setup automated builds
- Implement automated testing
- Create deployment workflows
- Manage build artifacts
- Setup release automation
- Configure test runners
- Implement pre-commit hooks

**Coordinates With**:
- Docker Specialist: For containerized builds
- Cloud Specialist: For deployment targets
- Monitoring Specialist: For pipeline observability

**Selection Scoring**:
- Keyword match weight: 0.5
- Platform compatibility: 0.3
- Task complexity: 0.2

### Docker/Containerization Specialist

**Trigger Keywords**:
- "Docker", "container", "containerize", "containerization"
- "Kubernetes", "K8s", "kubectl", "pod", "deployment"
- "container orchestration", "container registry"
- "Docker Compose", "docker-compose", "Dockerfile"
- "image", "container image", "base image"

**Task Types**:
- Containerize applications
- Create Dockerfiles
- Setup Docker environments
- Configure Kubernetes clusters
- Manage container orchestration
- Optimize container images
- Setup container registries
- Configure container networking

**Coordinates With**:
- CI/CD Specialist: For automated container builds
- Cloud Specialist: For container deployment
- Monitoring Specialist: For container metrics

**Selection Scoring**:
- Keyword match weight: 0.5
- Existing containerization: 0.3
- Platform requirements: 0.2

### Cloud Deployment Specialist

**Trigger Keywords**:
- "deploy", "deployment", "hosting", "server", "cloud"
- "AWS", "Amazon Web Services", "EC2", "Lambda", "S3"
- "Vercel", "Netlify", "Railway", "Fly.io", "Render"
- "Azure", "Google Cloud", "GCP", "DigitalOcean"
- "scaling", "load balancer", "CDN", "edge network"

**Task Types**:
- Deploy applications to cloud
- Configure cloud services
- Setup load balancing
- Manage scaling policies
- Configure CDN and edge
- Setup cloud networking
- Manage cloud databases
- Optimize cloud costs

**Coordinates With**:
- Docker Specialist: For containerized deployments
- Monitoring Specialist: For cloud observability
- IaC Specialist: For infrastructure provisioning
- Security Specialist: For cloud security

**Selection Scoring**:
- Platform match weight: 0.4
- Keyword relevance: 0.3
- Existing infrastructure: 0.3

### Monitoring & Logging Specialist

**Trigger Keywords**:
- "monitoring", "observability", "metrics", "logs", "logging"
- "Datadog", "Sentry", "New Relic", "CloudWatch", "Grafana"
- "alerts", "alerting", "notifications", "uptime"
- "performance tracking", "APM", "error tracking"
- "dashboards", "visualization", "log aggregation"

**Task Types**:
- Setup monitoring dashboards
- Configure log aggregation
- Implement alerting systems
- Track performance metrics
- Setup error tracking
- Configure uptime monitoring
- Create visualization dashboards
- Setup anomaly detection

**Coordinates With**:
- Cloud Specialist: For cloud service monitoring
- CI/CD Specialist: For pipeline monitoring
- Security Specialist: For security event monitoring

**Selection Scoring**:
- Keyword match weight: 0.5
- Integration complexity: 0.3
- Alert criticality: 0.2

### Security & Compliance Specialist

**Trigger Keywords**:
- "security", "secure", "vulnerability", "audit"
- "compliance", "HIPAA", "SOC2", "GDPR", "PCI"
- "secrets", "credentials", "certificates", "SSL", "HTTPS"
- "authentication", "authorization", "access control"
- "encryption", "firewall", "penetration test", "security scan"

**Task Types**:
- Perform security audits
- Run vulnerability scans
- Manage secrets and certificates
- Implement compliance checks
- Configure security policies
- Setup access controls
- Implement encryption
- Configure firewalls

**Coordinates With**:
- Cloud Specialist: For cloud security
- CI/CD Specialist: For pipeline security
- IaC Specialist: For security-as-code

**Selection Scoring**:
- Security risk level: 0.4
- Compliance requirements: 0.3
- Keyword match: 0.3

### Infrastructure as Code Specialist

**Trigger Keywords**:
- "IaC", "Infrastructure as Code", "infrastructure code"
- "Terraform", "CloudFormation", "Pulumi", "CDK"
- "provision", "provisioning", "resource management"
- "infrastructure definition", "infrastructure automation"
- "state management", "infrastructure versioning"

**Task Types**:
- Define infrastructure as code
- Automate resource provisioning
- Manage infrastructure state
- Version control infrastructure
- Implement infrastructure testing
- Setup infrastructure modules
- Manage infrastructure dependencies
- Implement infrastructure validation

**Coordinates With**:
- Cloud Specialist: For cloud provisioning
- Security Specialist: For security-as-code
- Monitoring Specialist: For observability-as-code

**Selection Scoring**:
- Keyword match weight: 0.5
- Automation requirements: 0.3
- Infrastructure complexity: 0.2

## Multi-Specialist Scenarios

Complex infrastructure tasks often require multiple specialists working in coordination:

### Full Production Deployment Setup

**Task**: "Setup production deployment with monitoring and security"

**Required Specialists**:
1. IaC Specialist (define infrastructure)
2. Cloud Specialist (provision resources)
3. Docker Specialist (containerize application)
4. CI/CD Specialist (automate deployment)
5. Monitoring Specialist (setup observability)
6. Security Specialist (audit and secure)

**Coordination Flow**: Sequential with dependencies

### CI/CD Pipeline Creation

**Task**: "Create automated deployment pipeline"

**Required Specialists**:
1. Docker Specialist (containerize application)
2. CI/CD Specialist (configure pipeline)
3. Cloud Specialist (setup deployment target)
4. Monitoring Specialist (track pipeline metrics)

**Coordination Flow**: Sequential with parallel testing

### Infrastructure Update

**Task**: "Update production infrastructure with new database"

**Required Specialists**:
1. IaC Specialist (update infrastructure definition)
2. Security Specialist (security review)
3. Cloud Specialist (apply changes)
4. Monitoring Specialist (verify changes)

**Coordination Flow**: Sequential with safety checks

### Incident Response

**Task**: "Production outage - database connection issues"

**Required Specialists**:
1. Monitoring Specialist (detect and diagnose)
2. Cloud Specialist (check cloud resources)
3. Security Specialist (rule out security incident)
4. CI/CD Specialist (deploy hotfix if needed)

**Coordination Flow**: Parallel investigation, sequential remediation

## Platform Detection

Automatically detect target platforms to optimize specialist selection:

### Cloud Platforms
- **AWS**: EC2, Lambda, S3, RDS, CloudFormation
- **Vercel**: Serverless, Edge Functions, Next.js optimization
- **Railway**: Container-based, PostgreSQL integration
- **Fly.io**: Global edge deployment, distributed systems
- **Netlify**: Static sites, serverless functions, edge

**Detection Strategy**: Analyze existing infrastructure, project configuration files, and user preferences

### CI/CD Platforms
- **GitHub Actions**: .github/workflows/, GitHub repository
- **GitLab CI**: .gitlab-ci.yml, GitLab repository
- **Jenkins**: Jenkinsfile, Jenkins server
- **CircleCI**: .circleci/config.yml

**Detection Strategy**: Check for configuration files, repository platform, existing pipelines

### Container Platforms
- **Docker**: Dockerfile, docker-compose.yml
- **Kubernetes**: K8s manifests, helm charts
- **Docker Swarm**: Swarm configuration

**Detection Strategy**: Scan for container configuration files, existing container infrastructure

## Selection Algorithm

```python
def score_infrastructure_specialist(task, specialist):
    """
    Score a specialist's fit for a given infrastructure task.

    Returns float between 0.0 and 1.0
    """
    # Keyword matching (50% weight)
    keyword_score = count_keyword_matches(task.keywords, specialist.trigger_keywords)
    keyword_weight = 0.5

    # Platform compatibility (30% weight)
    platform_score = detect_platform_fit(task, specialist)
    platform_weight = 0.3

    # Urgency and complexity (20% weight)
    urgency_score = assess_task_urgency(task)
    urgency_weight = 0.2

    # Calculate weighted total
    total_score = (
        (keyword_score * keyword_weight) +
        (platform_score * platform_weight) +
        (urgency_score * urgency_weight)
    )

    return total_score

def select_infrastructure_specialists(task):
    """
    Select one or more specialists for an infrastructure task.

    Returns list of specialist identifiers.
    """
    all_specialists = [
        'cicd', 'docker', 'cloud', 'monitoring', 'security', 'iac'
    ]

    # Score each specialist
    specialist_scores = {}
    for specialist in all_specialists:
        score = score_infrastructure_specialist(task, specialist)
        specialist_scores[specialist] = score

    # Filter specialists with score above threshold
    threshold = 0.3
    selected = [
        specialist for specialist, score in specialist_scores.items()
        if score >= threshold
    ]

    # Sort by score (highest first)
    selected.sort(key=lambda s: specialist_scores[s], reverse=True)

    return selected

def count_keyword_matches(task_keywords, specialist_keywords):
    """
    Count and normalize keyword matches between task and specialist.

    Returns float between 0.0 and 1.0
    """
    if not task_keywords:
        return 0.0

    matches = sum(
        1 for keyword in task_keywords
        if any(keyword.lower() in sk.lower() for sk in specialist_keywords)
    )

    # Normalize by task keyword count
    return min(matches / len(task_keywords), 1.0)

def detect_platform_fit(task, specialist):
    """
    Assess how well specialist matches target platform.

    Returns float between 0.0 and 1.0
    """
    # Extract platform hints from task
    platforms = extract_platforms(task)

    # Check specialist platform compatibility
    compatibility_score = 0.0

    for platform in platforms:
        if specialist.supports_platform(platform):
            compatibility_score += 1.0 / len(platforms)

    return compatibility_score

def assess_task_urgency(task):
    """
    Assess task urgency based on keywords and context.

    Returns float between 0.0 and 1.0
    """
    urgency_keywords = ['urgent', 'critical', 'incident', 'outage', 'down', 'broken']

    urgency_level = sum(
        1 for keyword in urgency_keywords
        if keyword in task.description.lower()
    )

    # Normalize
    return min(urgency_level / 2.0, 1.0)
```

## Selection Decision Tree

```
1. Analyze task keywords
   ├─ Single specialist match (score >= 0.7)
   │  └─ Assign to that specialist
   │
   ├─ Multiple specialists (2-3 with score >= 0.5)
   │  └─ Create coordination plan
   │
   └─ Complex deployment (4+ specialists needed)
      └─ Create full deployment workflow

2. Check platform requirements
   ├─ Platform detected
   │  └─ Adjust specialist priorities
   │
   └─ No platform specified
      └─ Request clarification or use defaults

3. Assess urgency
   ├─ Incident/urgent
   │  └─ Prioritize fastest specialists
   │
   └─ Standard task
      └─ Optimize for quality

4. Return specialist selection(s)
```

## Example Selections

**Task**: "Setup GitHub Actions for automated testing"
- **Primary**: CI/CD Specialist (score: 0.9)
- **Secondary**: Docker Specialist (score: 0.4 - for containerized tests)

**Task**: "Deploy containerized app to AWS with monitoring"
- **Team**: Docker (0.9) → Cloud (0.9) → Monitoring (0.8)
- **Coordination**: Sequential deployment workflow

**Task**: "Security audit of production infrastructure"
- **Primary**: Security Specialist (score: 1.0)
- **Secondary**: Cloud Specialist (score: 0.5 - for cloud security)

**Task**: "Terraform script to provision Kubernetes cluster"
- **Primary**: IaC Specialist (score: 0.95)
- **Secondary**: Cloud Specialist (score: 0.7)
- **Tertiary**: Docker Specialist (score: 0.6 - K8s expertise)
