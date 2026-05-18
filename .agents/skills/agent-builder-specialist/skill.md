---
name: agent-builder-specialist
version: 1.0.0
author: Agent Skills System
description: Expert in dynamic agent creation with complete mastery of agent_builder MCP tools including agent definition, capability configuration, template management, and deployment workflows
trigger_domain: mcp
trigger_keywords:
  - agent creation
  - dynamic agent
  - agent builder
  - agent configuration
  - agent template
  - agent deployment
  - create agent
  - custom agent
  - agent definition
  - agent capabilities
tools_required:
  - agent_builder (MCP Handler)
progressive_disclosure:
  - level: 1
    content: agent_builder_overview
  - level: 2
    content: creation_tools
  - level: 3
    content: template_management
  - level: 4
    content: configuration_patterns
  - level: 5
    content: deployment_workflows
  - level: 6
    content: agent_builder_examples
---

# Agent Builder Specialist Agent

## Overview

This agent specializes in **dynamic agent creation and configuration** using the Agent Builder MCP Handler. It provides expert-level capabilities for defining custom agents, configuring their capabilities, using templates for rapid deployment, and managing the complete agent lifecycle from creation to production deployment.

**MCP Handler:** `agent_builder` (class-based handler)
**Core Class:** `AgentBuilderHandler`
**Port:** 8137
**Configuration:** SSE via Jarvis native handler

---

## Creation Tools

### 1. Agent Definition and Creation

#### Create Agent from Scratch
```python
agent_id = create_agent(
    agent_name="CustomerSupportAgent",
    description="AI agent specialized in customer support interactions",
    agent_type="custom",
    system_prompt="""You are a customer support specialist.
    Your role is to help customers with their questions and issues.
    Be empathetic, clear, and solution-focused.""",
    model="claude-sonnet-4-5-20250929",
    capabilities=[
        "email_management",
        "ticket_creation",
        "knowledge_base_search"
    ],
    tools=[
        {"name": "email", "config": {"max_attachments": 5}},
        {"name": "ticketing", "config": {"auto_assign": True}},
        {"name": "search", "config": {"index": "kb_index"}}
    ],
    metadata={
        "department": "customer_service",
        "priority": "high",
        "version": "1.0.0"
    }
)
```

**Parameters:**
- `agent_name`: Unique agent identifier (TEXT, required)
- `description`: Agent purpose and context (TEXT, optional)
- `agent_type`: Agent type - "custom", "template", "specialized" (TEXT, required)
- `system_prompt`: Behavioral instructions for agent (TEXT, required)
- `model`: AI model to use (TEXT, default: "claude-sonnet-4-5-20250929")
- `capabilities`: List of capability identifiers (LIST, required)
- `tools`: List of tool configurations (LIST, optional)
- `metadata`: Custom agent metadata (JSON, optional)

#### Get Agent Configuration
```python
config = get_agent_config(agent_id)
# Returns: {
#     "agent_id": 42,
#     "agent_name": "CustomerSupportAgent",
#     "description": "AI agent specialized in customer support interactions",
#     "agent_type": "custom",
#     "system_prompt": "You are a customer support specialist...",
#     "model": "claude-sonnet-4-5-20250929",
#     "capabilities": ["email_management", "ticket_creation", "knowledge_base_search"],
#     "tools": [...],
#     "status": "active",
#     "created_at": "2026-02-04T10:30:00Z",
#     "version": "1.0.0"
# }
```

#### Update Agent Configuration
```python
update_agent(
    agent_id=42,
    system_prompt="Updated prompt with new guidelines...",
    capabilities=["email_management", "ticket_creation", "knowledge_base_search", "sentiment_analysis"],
    model="claude-opus-4-5-20251101",  # Upgrade to Opus
    metadata={"version": "1.1.0"}
)
```

#### Delete/Deactivate Agent
```python
# Deactivate agent (preserves configuration)
deactivate_agent(agent_id=42)

# Permanently delete agent
delete_agent(agent_id=42, confirm=True)
```

### 2. Capability Configuration

#### Define Agent Capabilities
```python
# Configure capabilities with granular permissions
configure_agent_capabilities(
    agent_id=42,
    capabilities={
        "email_management": {
            "send_email": True,
            "read_email": True,
            "delete_email": False,  # Restricted
            "max_recipients": 10,
            "allowed_domains": ["company.com", "support.company.com"]
        },
        "ticket_creation": {
            "create_ticket": True,
            "update_ticket": True,
            "close_ticket": True,
            "priority_levels": ["low", "medium", "high"],
            "auto_assignment": True
        },
        "knowledge_base_search": {
            "search_index": "customer_support_kb",
            "max_results": 20,
            "include_summaries": True,
            "relevance_threshold": 0.75
        }
    }
)
```

#### Add Capability to Existing Agent
```python
add_agent_capability(
    agent_id=42,
    capability="sentiment_analysis",
    configuration={
        "model": "sentiment_v2",
        "threshold": 0.80,
        "languages": ["en", "es", "fr"],
        "output_format": "detailed"
    }
)
```

#### Remove Capability
```python
remove_agent_capability(
    agent_id=42,
    capability="knowledge_base_search",
    reason="Migrating to new search system"
)
```

### 3. Tool Assignment and Configuration

#### Assign Tools to Agent
```python
assign_tools_to_agent(
    agent_id=42,
    tools=[
        {
            "tool_name": "email",
            "mcp_server": "email_handler",
            "enabled": True,
            "configuration": {
                "smtp_server": "smtp.company.com",
                "from_address": "support@company.com",
                "signature_template": "support_signature"
            },
            "permissions": {
                "send": True,
                "read": True,
                "delete": False,
                "admin": False
            }
        },
        {
            "tool_name": "ticketing",
            "mcp_server": "jira_integration",
            "enabled": True,
            "configuration": {
                "project_key": "SUP",
                "default_priority": "medium",
                "auto_assign_team": "support_team_1"
            },
            "permissions": {
                "create": True,
                "update": True,
                "comment": True,
                "close": True,
                "delete": False
            }
        }
    ]
)
```

#### Configure Tool Parameters
```python
configure_tool_parameters(
    agent_id=42,
    tool_name="email",
    parameters={
        "rate_limit": {
            "max_per_hour": 100,
            "max_per_day": 500,
            "burst_limit": 10
        },
        "validation": {
            "require_subject": True,
            "min_body_length": 50,
            "prohibited_keywords": ["spam", "urgent"],
            "require_signature": True
        },
        "templates": {
            "welcome": "template_001",
            "followup": "template_002",
            "resolution": "template_003"
        }
    }
)
```

#### Get Tool Usage Statistics
```python
stats = get_tool_usage_stats(
    agent_id=42,
    tool_name="email",
    time_range="last_7_days"
)
# Returns: {
#     "tool_name": "email",
#     "total_calls": 1543,
#     "successful_calls": 1521,
#     "failed_calls": 22,
#     "average_duration": 1.2,  # seconds
#     "rate_limit_hits": 3,
#     "most_used_operation": "send_email",
#     "operations": {
#         "send_email": 1200,
#         "read_email": 300,
#         "search_email": 43
#     }
# }
```

---

## Template Management

### 1. Agent Templates

#### List Available Templates
```python
templates = list_agent_templates()
# Returns: [
#     {
#         "template_id": "customer_support_v1",
#         "name": "Customer Support Agent",
#         "description": "Pre-configured customer support agent",
#         "capabilities": ["email", "ticketing", "knowledge_search"],
#         "model": "claude-sonnet-4-5-20250929",
#         "version": "1.0.0",
#         "created_by": "system",
#         "use_count": 45
#     },
#     {
#         "template_id": "data_analyst_v2",
#         "name": "Data Analysis Agent",
#         "description": "Specialized in data analysis and visualization",
#         "capabilities": ["data_processing", "statistical_analysis", "visualization"],
#         "model": "claude-opus-4-5-20251101",
#         "version": "2.0.0",
#         "created_by": "admin",
#         "use_count": 23
#     }
# ]
```

#### Create Agent from Template
```python
agent_id = create_agent_from_template(
    template_id="customer_support_v1",
    agent_name="SupportAgent_Team2",
    customizations={
        "system_prompt_additions": "Focus on enterprise customer accounts.",
        "additional_capabilities": ["crm_integration"],
        "metadata": {
            "team": "enterprise_support",
            "region": "north_america"
        }
    }
)
```

#### Create Custom Template
```python
template_id = create_agent_template(
    template_name="SalesAssistant_v1",
    description="AI agent for sales team assistance",
    base_config={
        "agent_type": "specialized",
        "model": "claude-sonnet-4-5-20250929",
        "system_prompt": """You are a sales assistant.
        Help sales team with prospect research, email drafting, and meeting preparation.
        Focus on being helpful, accurate, and professional.""",
        "capabilities": [
            "email_management",
            "calendar_integration",
            "crm_access",
            "research"
        ],
        "tools": [
            {"name": "email", "config": {"template_mode": "sales"}},
            {"name": "calendar", "config": {"booking_enabled": True}},
            {"name": "salesforce", "config": {"read_only": False}},
            {"name": "web_search", "config": {"max_results": 10}}
        ]
    },
    configuration_schema={
        "required_customizations": ["team_name", "sales_region"],
        "optional_customizations": ["quota_tracking", "pipeline_stage_filters"],
        "version": "1.0.0"
    }
)
```

#### Update Template
```python
update_agent_template(
    template_id="SalesAssistant_v1",
    updates={
        "model": "claude-opus-4-5-20251101",  # Upgrade model
        "capabilities": ["email_management", "calendar_integration", "crm_access", "research", "sentiment_analysis"],
        "version": "1.1.0"
    }
)
```

### 2. Template Validation

#### Validate Template Configuration
```python
validation_result = validate_template(
    template_id="customer_support_v1"
)
# Returns: {
#     "valid": True,
#     "checks": {
#         "system_prompt": {"status": "valid", "length": 450},
#         "capabilities": {"status": "valid", "count": 3, "all_available": True},
#         "tools": {"status": "valid", "count": 3, "all_configured": True},
#         "model": {"status": "valid", "available": True},
#         "required_fields": {"status": "valid", "all_present": True}
#     },
#     "warnings": [],
#     "errors": []
# }
```

#### Test Template Before Deployment
```python
test_result = test_agent_template(
    template_id="customer_support_v1",
    test_scenarios=[
        {
            "scenario": "email_response",
            "input": "Customer asks about refund policy",
            "expected_capabilities": ["email_management", "knowledge_base_search"]
        },
        {
            "scenario": "ticket_creation",
            "input": "Customer reports bug in application",
            "expected_capabilities": ["ticket_creation", "bug_tracking"]
        }
    ]
)
# Returns test results with success/failure for each scenario
```

---

## Configuration Patterns

### Pattern 1: Tiered Agent Configuration

**Use Case:** Different permission levels for agents in same role

```python
# Junior Support Agent (Limited Permissions)
junior_agent = create_agent(
    agent_name="JuniorSupportAgent_001",
    agent_type="tiered",
    tier="junior",
    capabilities={
        "email_management": {
            "send_email": True,
            "read_email": True,
            "delete_email": False,
            "max_recipients": 5,  # Limited
            "requires_approval": True  # Needs senior review
        },
        "ticket_creation": {
            "create_ticket": True,
            "update_ticket": True,
            "close_ticket": False,  # Cannot close
            "escalate": True
        }
    }
)

# Senior Support Agent (Full Permissions)
senior_agent = create_agent(
    agent_name="SeniorSupportAgent_001",
    agent_type="tiered",
    tier="senior",
    capabilities={
        "email_management": {
            "send_email": True,
            "read_email": True,
            "delete_email": True,
            "max_recipients": 50,  # Higher limit
            "requires_approval": False
        },
        "ticket_creation": {
            "create_ticket": True,
            "update_ticket": True,
            "close_ticket": True,
            "escalate": True,
            "reassign": True,
            "bulk_operations": True
        },
        "approval_queue": {
            "review_junior_emails": True,
            "approve_actions": True
        }
    }
)
```

### Pattern 2: Role-Based Configuration

**Use Case:** Agents specialized for different business functions

```python
# Sales Agent Configuration
sales_agent = create_agent_from_template(
    template_id="sales_assistant_v1",
    agent_name="SalesAgent_EMEA",
    customizations={
        "capabilities": {
            "crm_integration": {
                "platform": "salesforce",
                "region": "EMEA",
                "pipeline_access": ["prospecting", "qualification", "proposal"],
                "can_create_opportunities": True
            },
            "email_management": {
                "templates": ["cold_outreach", "followup", "meeting_request"],
                "signature": "sales_emea_signature"
            },
            "calendar_integration": {
                "booking_windows": ["9am-5pm GMT"],
                "auto_send_invites": True,
                "meeting_types": ["discovery", "demo", "closing"]
            }
        }
    }
)

# Marketing Agent Configuration
marketing_agent = create_agent_from_template(
    template_id="marketing_assistant_v1",
    agent_name="MarketingAgent_Content",
    customizations={
        "capabilities": {
            "content_creation": {
                "formats": ["blog_post", "social_media", "email_campaign"],
                "tone": "professional_friendly",
                "brand_guidelines": "brand_guide_2026"
            },
            "social_media_integration": {
                "platforms": ["linkedin", "twitter", "facebook"],
                "posting_schedule": "auto",
                "approval_required": True
            },
            "analytics_access": {
                "platforms": ["google_analytics", "social_insights"],
                "metrics": ["engagement", "reach", "conversions"]
            }
        }
    }
)
```

### Pattern 3: Environment-Specific Configuration

**Use Case:** Different configurations for dev, staging, production

```python
# Development Agent
dev_agent = create_agent(
    agent_name="CustomerSupportAgent_Dev",
    environment="development",
    capabilities={
        "email_management": {
            "smtp_server": "smtp.dev.company.com",
            "test_mode": True,
            "recipients_whitelist": ["*@company.com"],  # Internal only
            "log_all_emails": True
        },
        "ticketing": {
            "jira_project": "SUP-DEV",
            "mock_external_apis": True
        }
    }
)

# Production Agent
prod_agent = create_agent(
    agent_name="CustomerSupportAgent_Prod",
    environment="production",
    capabilities={
        "email_management": {
            "smtp_server": "smtp.company.com",
            "test_mode": False,
            "rate_limiting": {
                "max_per_hour": 500,
                "max_per_day": 2000
            },
            "monitoring": {
                "alert_on_failure": True,
                "escalation_channel": "slack_support_ops"
            }
        },
        "ticketing": {
            "jira_project": "SUP",
            "sla_tracking": True,
            "auto_escalation": True
        }
    }
)
```

### Pattern 4: Multi-Language Agent Configuration

**Use Case:** Agents serving different language markets

```python
# English Support Agent
en_agent = create_agent(
    agent_name="SupportAgent_EN",
    language_config={
        "primary_language": "en",
        "supported_languages": ["en"],
        "detection_mode": "explicit",
        "translation": False
    },
    system_prompt="You are an English-speaking customer support agent..."
)

# Multi-Language Support Agent
multilang_agent = create_agent(
    agent_name="SupportAgent_Global",
    language_config={
        "primary_language": "en",
        "supported_languages": ["en", "es", "fr", "de", "ja", "zh"],
        "detection_mode": "auto",
        "translation": True,
        "translation_service": "google_translate_api",
        "localization": {
            "currency_format": "auto",
            "date_format": "locale_specific",
            "timezone": "customer_timezone"
        }
    },
    capabilities={
        "language_detection": {
            "confidence_threshold": 0.90,
            "fallback_language": "en"
        },
        "cultural_adaptation": {
            "greeting_styles": "locale_appropriate",
            "formality_level": "auto_adjust"
        }
    }
)
```

---

## Deployment Workflows

### 1. Development to Production Pipeline

#### Stage 1: Development
```python
# Create and test in development
dev_agent = create_agent(
    agent_name="NewFeatureAgent_Dev",
    environment="development",
    capabilities=["feature_x", "feature_y"],
    metadata={"pipeline_stage": "dev"}
)

# Test agent functionality
test_results = run_agent_tests(
    agent_id=dev_agent,
    test_suite="comprehensive",
    test_environment="dev"
)

# Validate test results
if test_results["success_rate"] >= 0.95:
    promote_to_staging(dev_agent)
```

#### Stage 2: Staging
```python
# Clone to staging environment
staging_agent = clone_agent(
    source_agent_id=dev_agent,
    target_environment="staging",
    agent_name="NewFeatureAgent_Staging",
    configuration_overrides={
        "rate_limiting": {"max_per_hour": 100},
        "monitoring": {"detailed_logging": True}
    }
)

# Run integration tests
integration_results = run_integration_tests(
    agent_id=staging_agent,
    test_scenarios=["user_workflow_1", "user_workflow_2", "edge_cases"]
)

# Performance testing
performance_results = run_performance_tests(
    agent_id=staging_agent,
    load_profile="expected_production_load",
    duration_minutes=30
)

# If all tests pass, prepare for production
if integration_results["all_passed"] and performance_results["meets_sla"]:
    prepare_production_deployment(staging_agent)
```

#### Stage 3: Production
```python
# Deploy to production with gradual rollout
prod_agent = deploy_to_production(
    source_agent_id=staging_agent,
    agent_name="NewFeatureAgent_Prod",
    deployment_strategy="canary",
    rollout_config={
        "initial_percentage": 5,  # Start with 5% of traffic
        "increment_percentage": 10,
        "increment_interval_minutes": 30,
        "success_criteria": {
            "error_rate_max": 0.01,
            "response_time_p95_max": 2000  # milliseconds
        },
        "rollback_on_failure": True
    }
)

# Monitor deployment
monitor_deployment(
    agent_id=prod_agent,
    metrics=["error_rate", "response_time", "user_satisfaction"],
    alert_thresholds={
        "error_rate": 0.02,
        "response_time_p95": 3000
    }
)
```

### 2. Blue-Green Deployment

```python
# Current production agent (Blue)
blue_agent = get_agent_by_name("CustomerSupportAgent_Prod")

# Create new version (Green)
green_agent = create_agent(
    agent_name="CustomerSupportAgent_Prod_v2",
    agent_type="production",
    environment="production",
    capabilities=["updated_capabilities"],
    metadata={
        "deployment_type": "blue_green",
        "version": "2.0.0",
        "replaces": blue_agent.id
    }
)

# Test green agent with shadow traffic
shadow_test_results = run_shadow_test(
    primary_agent=blue_agent,
    shadow_agent=green_agent,
    duration_minutes=60,
    traffic_percentage=100  # All traffic goes to both, but only blue responses returned
)

# If shadow tests pass, switch traffic
if shadow_test_results["green_performance"] >= shadow_test_results["blue_performance"]:
    # Instant cutover
    switch_traffic(
        from_agent=blue_agent,
        to_agent=green_agent,
        cutover_type="instant"
    )

    # Keep blue agent warm for quick rollback
    set_agent_status(blue_agent, status="standby", ttl_hours=24)
else:
    # Rollback to blue, investigate green issues
    deactivate_agent(green_agent)
    analyze_test_failures(shadow_test_results)
```

### 3. A/B Testing Deployment

```python
# Create variant agents
agent_a = create_agent(
    agent_name="SupportAgent_Variant_A",
    system_prompt="Variant A: Formal, detailed responses...",
    capabilities=["email", "ticketing", "knowledge_search"],
    metadata={"ab_test": "response_style", "variant": "A"}
)

agent_b = create_agent(
    agent_name="SupportAgent_Variant_B",
    system_prompt="Variant B: Casual, concise responses...",
    capabilities=["email", "ticketing", "knowledge_search"],
    metadata={"ab_test": "response_style", "variant": "B"}
)

# Configure A/B test
ab_test = configure_ab_test(
    test_name="response_style_experiment",
    variants=[
        {"agent_id": agent_a, "traffic_percentage": 50},
        {"agent_id": agent_b, "traffic_percentage": 50}
    ],
    success_metrics=["customer_satisfaction", "resolution_time", "followup_rate"],
    test_duration_days=14,
    minimum_sample_size=1000
)

# Monitor A/B test results
results = get_ab_test_results(ab_test.id)
# After test completes, choose winner
if results["winner"] == "variant_a":
    promote_to_production(agent_a)
    deactivate_agent(agent_b)
```

---

## Agent Builder Examples

### Example 1: Complete Customer Support Agent

```python
# Step 1: Create agent from scratch
agent_id = create_agent(
    agent_name="EnterpriseCustomerSupportAgent",
    description="Dedicated support agent for enterprise customers",
    agent_type="custom",
    system_prompt="""You are an enterprise customer support specialist.
    Your customers are large businesses with mission-critical needs.

    Guidelines:
    - Be professional and technically knowledgeable
    - Prioritize quick resolution and proactive communication
    - Escalate urgent issues immediately
    - Document all interactions thoroughly
    - Maintain awareness of SLA commitments

    Tone: Professional, empathetic, solution-focused""",
    model="claude-opus-4-5-20251101",  # Use Opus for enterprise
    capabilities=[],
    metadata={
        "department": "enterprise_support",
        "tier": "premium",
        "version": "1.0.0"
    }
)

# Step 2: Configure capabilities
configure_agent_capabilities(
    agent_id=agent_id,
    capabilities={
        "email_management": {
            "send_email": True,
            "read_email": True,
            "priority_handling": True,
            "sla_tracking": True,
            "max_response_time_minutes": 30,
            "templates": ["enterprise_greeting", "sla_acknowledgment", "escalation_notice"]
        },
        "ticketing": {
            "create_ticket": True,
            "update_ticket": True,
            "close_ticket": True,
            "priority_levels": ["critical", "high", "medium", "low"],
            "auto_escalation": {
                "enabled": True,
                "critical_threshold_minutes": 15,
                "high_threshold_minutes": 60
            },
            "custom_fields": {
                "account_value": True,
                "contract_tier": True,
                "technical_owner": True
            }
        },
        "knowledge_base_search": {
            "indexes": ["enterprise_kb", "technical_docs", "sla_policies"],
            "max_results": 10,
            "relevance_threshold": 0.85,
            "include_related_articles": True
        },
        "crm_integration": {
            "platform": "salesforce",
            "read_account_data": True,
            "update_case_notes": True,
            "track_interactions": True
        },
        "escalation_management": {
            "escalation_paths": {
                "technical": "senior_technical_team",
                "business": "account_manager",
                "urgent": "enterprise_director"
            },
            "notification_channels": ["email", "slack", "pagerduty"]
        }
    }
)

# Step 3: Assign tools
assign_tools_to_agent(
    agent_id=agent_id,
    tools=[
        {
            "tool_name": "email",
            "mcp_server": "email_handler",
            "configuration": {
                "from_address": "enterprise.support@company.com",
                "signature_template": "enterprise_signature",
                "priority_flag": True
            }
        },
        {
            "tool_name": "jira",
            "mcp_server": "jira_integration",
            "configuration": {
                "project_key": "ENT-SUP",
                "issue_type": "Enterprise Support",
                "watchers": ["enterprise-team"]
            }
        },
        {
            "tool_name": "salesforce",
            "mcp_server": "salesforce_integration",
            "configuration": {
                "object_types": ["Account", "Case", "Contact"],
                "field_mappings": "enterprise_mapping"
            }
        }
    ]
)

# Step 4: Validate and test
validation = validate_agent_configuration(agent_id)
if validation["valid"]:
    # Run test scenarios
    test_results = test_agent(
        agent_id=agent_id,
        scenarios=[
            "customer_inquiry",
            "technical_issue",
            "sla_breach_warning",
            "escalation_needed"
        ]
    )

    if test_results["success_rate"] >= 0.95:
        # Deploy to production
        deploy_agent(agent_id, environment="production")
```

### Example 2: Data Analysis Agent with Custom Tools

```python
# Create specialized data analyst agent
analyst_agent = create_agent(
    agent_name="DataAnalysisAgent_Finance",
    description="Financial data analysis specialist",
    agent_type="specialized",
    system_prompt="""You are a financial data analyst.
    Your role is to analyze financial data, identify trends, and generate insights.

    Capabilities:
    - Statistical analysis
    - Data visualization
    - Trend identification
    - Anomaly detection
    - Report generation

    Always cite data sources and explain your methodology.""",
    model="claude-opus-4-5-20251101",
    capabilities=[]
)

# Configure data analysis capabilities
configure_agent_capabilities(
    agent_id=analyst_agent,
    capabilities={
        "data_processing": {
            "formats": ["csv", "json", "excel", "parquet"],
            "max_file_size_mb": 500,
            "streaming_mode": True,
            "validation": {
                "check_nulls": True,
                "check_duplicates": True,
                "check_data_types": True
            }
        },
        "statistical_analysis": {
            "methods": [
                "descriptive_statistics",
                "correlation_analysis",
                "regression_analysis",
                "time_series_analysis",
                "hypothesis_testing"
            ],
            "confidence_level": 0.95,
            "significance_threshold": 0.05
        },
        "visualization": {
            "chart_types": [
                "line_chart",
                "bar_chart",
                "scatter_plot",
                "heatmap",
                "candlestick",
                "treemap"
            ],
            "output_formats": ["png", "svg", "interactive_html"],
            "style_template": "financial_professional"
        },
        "anomaly_detection": {
            "algorithms": ["isolation_forest", "zscore", "seasonal_decomposition"],
            "sensitivity": "high",
            "alert_threshold": 3.0  # Standard deviations
        }
    }
)

# Assign specialized tools
assign_tools_to_agent(
    agent_id=analyst_agent,
    tools=[
        {
            "tool_name": "data_validator",
            "mcp_server": "data_validator",
            "configuration": {
                "validation_rules": "financial_data_rules",
                "error_handling": "strict"
            }
        },
        {
            "tool_name": "python_executor",
            "mcp_server": "code_execution",
            "configuration": {
                "allowed_libraries": ["pandas", "numpy", "matplotlib", "seaborn", "scipy"],
                "execution_timeout": 300,
                "memory_limit_mb": 2048
            }
        },
        {
            "tool_name": "database_connector",
            "mcp_server": "database",
            "configuration": {
                "connection_string": "postgresql://finance_db",
                "read_only": True,
                "query_timeout": 30
            }
        }
    ]
)
```

### Example 3: Rapid Deployment Using Template

```python
# Quick deployment of multiple support agents using template
agents = []

for team in ["team_1", "team_2", "team_3"]:
    agent_id = create_agent_from_template(
        template_id="customer_support_v1",
        agent_name=f"SupportAgent_{team}",
        customizations={
            "metadata": {
                "team": team,
                "region": "north_america",
                "shift": "24x7"
            },
            "capabilities": {
                "email_management": {
                    "signature": f"{team}_signature",
                    "from_name": f"Support Team {team.split('_')[1]}"
                }
            }
        }
    )
    agents.append(agent_id)

# Configure shared load balancer
configure_load_balancer(
    agent_pool=agents,
    strategy="round_robin",
    health_check_interval=30,
    failover_enabled=True
)
```

---

## Best Practices

### 1. Agent Naming Conventions
- Use descriptive names indicating purpose: "CustomerSupportAgent_Enterprise"
- Include environment suffix: "_Dev", "_Staging", "_Prod"
- Version agents: "Agent_v1.0", "Agent_v2.0"
- Use team/region identifiers: "SupportAgent_EMEA_Team1"

### 2. System Prompt Design
- Be specific about agent role and responsibilities
- Include guidelines for tone and style
- Define boundaries (what agent should NOT do)
- Provide examples of ideal responses
- Reference relevant policies or documentation
- Keep prompts under 2000 tokens for optimal performance

### 3. Capability Configuration
- Start minimal, add capabilities incrementally
- Use role-based capabilities for consistency
- Document why each capability is enabled
- Set appropriate permission levels
- Monitor capability usage for optimization

### 4. Tool Assignment
- Only assign tools agent actually needs
- Configure tool-specific rate limits
- Set appropriate timeouts
- Use environment-specific configurations
- Monitor tool usage and costs

### 5. Testing Before Deployment
- Test all capabilities individually
- Run integration tests with real-world scenarios
- Test edge cases and error handling
- Validate performance under load
- Test in staging environment before production

### 6. Version Management
- Use semantic versioning (MAJOR.MINOR.PATCH)
- Document changes between versions
- Maintain rollback capability
- Test upgrades in staging first
- Keep previous version on standby for 24-48 hours

---

## Troubleshooting

### Issue: Agent Creation Fails

**Causes:**
- Invalid system prompt (too long or empty)
- Capability conflicts
- Tool configuration errors
- Missing required parameters

**Solutions:**
- Validate system prompt length (< 2000 tokens)
- Check capability compatibility matrix
- Verify tool configurations against schema
- Use `validate_agent_configuration()` before creation

### Issue: Agent Performance Degradation

**Causes:**
- Too many capabilities enabled
- Tool timeouts
- Model selection inappropriate for task
- Rate limiting triggered

**Solutions:**
- Audit and remove unused capabilities
- Increase tool timeouts or optimize tool usage
- Consider upgrading to Opus for complex tasks
- Review and adjust rate limits

### Issue: Template Deployment Inconsistencies

**Causes:**
- Template version mismatch
- Environment-specific configuration missing
- Capability availability varies by environment

**Solutions:**
- Lock template versions for deployments
- Maintain environment-specific configuration overrides
- Validate capabilities exist in target environment before deployment

---

**Agent Builder Specialist Agent Ready**
**Capabilities:** Complete mastery of agent_builder MCP for dynamic agent creation
**Primary Focus:** Agent definition, capability configuration, template management, deployment workflows
