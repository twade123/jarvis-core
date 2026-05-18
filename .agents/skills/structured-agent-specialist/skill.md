---
name: structured-agent-specialist
description: This skill should be used when the user asks to "create workflow", "structured output", "validate schema", "step-by-step process", "workflow automation", mentions "structured agent", or discusses multi-step workflows with validation.
version: 1.0.0
category: mcp-specialist
author: Claude Code Agent Skills System
created: 2026-02-04
triggers:
  - "create workflow"
  - "structured output"
  - "validate schema"
  - "step-by-step process"
  - "workflow automation"
  - "structured agent"
  - "schema validation"
  - "multi-step workflow"
capabilities:
  - workflow_definition
  - step_execution
  - progress_tracking
  - schema_validation
  - output_structuring
  - conditional_logic
  - error_recovery
mcp_server: structured_agent
mcp_port: 8109
handler_class: MultiAgentSystem
parent_orchestrator: mcp-domain-orchestrator
---

# Structured Agent Specialist

Expert agent with complete mastery of structured agent MCP tools for workflow automation, step-by-step process execution, schema validation, and structured output generation.

## Role and Responsibilities

Act as the specialist agent for all structured workflow operations in the agent skills system.

**Primary Responsibilities:**

- **Workflow Definition**: Create multi-step workflows with structured schemas
- **Step Execution**: Execute workflow steps in sequence with control flow
- **Progress Tracking**: Monitor and report workflow execution progress
- **Schema Validation**: Validate outputs against defined schemas
- **Structured Outputs**: Generate JSON/YAML outputs conforming to schemas
- **Conditional Logic**: Handle branching and conditional workflow paths
- **Error Recovery**: Implement retry logic and error handling for failed steps

**Scope:**

- Handle ALL structured workflow tasks delegated by MCP Domain Orchestrator
- Execute workflows with multi-step processes requiring validation
- Generate structured outputs for downstream systems
- Report status to MCP Domain Orchestrator only

## MCP Overview

### Structured Agent Handler Architecture

**MCP Server:** `structured_agent`
**Port:** 8109
**Handler Class:** `MultiAgentSystem` (class-based)
**Integration:** Jarvis agent system with schema validation
**Authentication:** Uses Jarvis configuration (no separate credentials needed)
**Rate Limits:** None (local integration)

### Core Capabilities

1. **Workflow Definition** - Create multi-step workflows with schemas
2. **Step Execution Control** - Execute steps with conditional logic
3. **Progress Tracking** - Monitor workflow state and completion
4. **Schema Validation** - Validate outputs against JSON schemas
5. **Structured Output Generation** - Produce conformant JSON/YAML outputs
6. **Error Handling** - Retry failed steps with exponential backoff

## Available Tools

### 1. Define Workflow

**Purpose:** Create structured workflow with steps and schema definitions

**Parameters:**
- `workflow_name` (required): Unique workflow identifier - string
- `steps` (required): List of workflow steps with schemas - array of objects
- `validation_schema` (required): JSON schema for output validation - object
- `execution_mode` (optional): Sequential or parallel step execution - string (default: "sequential")
- `retry_policy` (optional): Retry configuration for failed steps - object

**Usage:**
```
Tool: structured_agent_define_workflow
Parameters:
  workflow_name: "customer_onboarding"
  steps:
    - name: "validate_customer_data"
      schema: { "type": "object", "properties": { "email": { "type": "string" } } }
      required: true
    - name: "create_account"
      schema: { "type": "object", "properties": { "account_id": { "type": "string" } } }
      required: true
    - name: "send_welcome_email"
      schema: { "type": "object", "properties": { "email_sent": { "type": "boolean" } } }
      required: false
  validation_schema:
    type: "object"
    properties:
      customer_id: { type: "string" }
      account_created: { type: "boolean" }
      welcome_sent: { type: "boolean" }
  execution_mode: "sequential"
  retry_policy:
    max_attempts: 3
    backoff_factor: 2
```

**Best Practices:**
- Use descriptive workflow names
- Define clear schemas for each step
- Mark optional vs required steps
- Set appropriate retry policies
- Use sequential mode for dependent steps

### 2. Execute Workflow Step

**Purpose:** Execute a single workflow step with input data

**Parameters:**
- `workflow_name` (required): Workflow identifier - string
- `step_name` (required): Step to execute - string
- `input_data` (required): Data for step execution - object
- `validate_input` (optional): Validate input against schema - boolean (default: true)
- `validate_output` (optional): Validate output against schema - boolean (default: true)

**Usage:**
```
Tool: structured_agent_execute_step
Parameters:
  workflow_name: "customer_onboarding"
  step_name: "validate_customer_data"
  input_data:
    email: "customer@example.com"
    name: "John Doe"
    phone: "+1-555-0100"
  validate_input: true
  validate_output: true
```

**Best Practices:**
- Always validate inputs for data integrity
- Validate outputs to catch schema violations early
- Pass complete data from previous steps
- Handle validation errors gracefully

### 3. Get Workflow Progress

**Purpose:** Retrieve current workflow execution state and progress

**Parameters:**
- `workflow_name` (required): Workflow identifier - string
- `include_step_details` (optional): Include detailed step info - boolean (default: false)
- `include_errors` (optional): Include error details - boolean (default: false)

**Usage:**
```
Tool: structured_agent_get_progress
Parameters:
  workflow_name: "customer_onboarding"
  include_step_details: true
  include_errors: true
```

**Returns:**
```json
{
  "workflow_name": "customer_onboarding",
  "status": "in_progress",
  "current_step": "create_account",
  "completed_steps": 1,
  "total_steps": 3,
  "progress_percentage": 33.3,
  "step_details": [
    {
      "name": "validate_customer_data",
      "status": "completed",
      "output": { "email": "customer@example.com", "validated": true }
    },
    {
      "name": "create_account",
      "status": "in_progress",
      "started_at": "2026-02-04T16:00:00Z"
    }
  ],
  "errors": []
}
```

**Best Practices:**
- Poll progress for long-running workflows
- Include error details for troubleshooting
- Use progress percentage for user feedback
- Track completed steps for resume capability

### 4. Validate Output

**Purpose:** Validate data against defined JSON schema

**Parameters:**
- `schema` (required): JSON schema for validation - object
- `data` (required): Data to validate - object
- `strict_mode` (optional): Enforce strict validation - boolean (default: false)

**Usage:**
```
Tool: structured_agent_validate
Parameters:
  schema:
    type: "object"
    properties:
      customer_id: { type: "string", pattern: "^CUST-[0-9]{6}$" }
      email: { type: "string", format: "email" }
      age: { type: "integer", minimum: 18 }
    required: ["customer_id", "email"]
  data:
    customer_id: "CUST-123456"
    email: "customer@example.com"
    age: 25
  strict_mode: true
```

**Returns:**
```json
{
  "valid": true,
  "errors": [],
  "validated_data": {
    "customer_id": "CUST-123456",
    "email": "customer@example.com",
    "age": 25
  }
}
```

**Best Practices:**
- Use strict mode for critical data validation
- Define comprehensive schemas with patterns
- Validate early in workflow to catch errors
- Handle validation errors with clear messages

### 5. Execute Workflow (Full)

**Purpose:** Execute entire workflow from start to finish

**Parameters:**
- `workflow_name` (required): Workflow identifier - string
- `initial_data` (required): Starting data for workflow - object
- `execution_options` (optional): Execution configuration - object
  - `skip_completed` (boolean): Resume from failed step
  - `stop_on_error` (boolean): Stop or continue on step failure
  - `parallel_threshold` (integer): Max parallel steps

**Usage:**
```
Tool: structured_agent_execute_workflow
Parameters:
  workflow_name: "customer_onboarding"
  initial_data:
    email: "customer@example.com"
    name: "John Doe"
    plan: "premium"
  execution_options:
    skip_completed: false
    stop_on_error: true
    parallel_threshold: 3
```

**Best Practices:**
- Provide complete initial data for all steps
- Use `skip_completed` for resume capability
- Set `stop_on_error` based on criticality
- Limit parallel execution to avoid overload

### 6. Create Conditional Branch

**Purpose:** Add conditional logic to workflow for branching

**Parameters:**
- `workflow_name` (required): Workflow identifier - string
- `condition_name` (required): Unique condition identifier - string
- `condition_logic` (required): Evaluation logic - object
  - `field` (string): Field to evaluate
  - `operator` (string): Comparison operator (eq, ne, gt, lt, in)
  - `value` (any): Value to compare against
- `true_branch` (required): Steps to execute if true - array
- `false_branch` (optional): Steps to execute if false - array

**Usage:**
```
Tool: structured_agent_add_condition
Parameters:
  workflow_name: "customer_onboarding"
  condition_name: "check_plan_type"
  condition_logic:
    field: "plan"
    operator: "eq"
    value: "premium"
  true_branch:
    - name: "enable_premium_features"
    - name: "assign_account_manager"
  false_branch:
    - name: "enable_basic_features"
```

**Best Practices:**
- Use descriptive condition names
- Keep condition logic simple
- Define both branches for clarity
- Validate condition fields exist in data

### 7. Retry Failed Step

**Purpose:** Retry a failed workflow step with modified data

**Parameters:**
- `workflow_name` (required): Workflow identifier - string
- `step_name` (required): Failed step to retry - string
- `retry_data` (optional): Modified input data for retry - object
- `force_retry` (optional): Retry even if max attempts reached - boolean (default: false)

**Usage:**
```
Tool: structured_agent_retry_step
Parameters:
  workflow_name: "customer_onboarding"
  step_name: "create_account"
  retry_data:
    email: "corrected_email@example.com"
  force_retry: false
```

**Best Practices:**
- Review error before retrying
- Modify data to fix known issues
- Respect max retry limits
- Use force_retry sparingly for critical steps

### 8. Generate Structured Output

**Purpose:** Generate JSON/YAML output conforming to schema

**Parameters:**
- `schema` (required): Output schema definition - object
- `source_data` (required): Data to structure - object
- `output_format` (optional): JSON or YAML - string (default: "json")
- `validate` (optional): Validate before output - boolean (default: true)

**Usage:**
```
Tool: structured_agent_generate_output
Parameters:
  schema:
    type: "object"
    properties:
      report_id: { type: "string" }
      data_points: { type: "array", items: { type: "number" } }
      summary: { type: "string" }
  source_data:
    report_id: "RPT-001"
    data_points: [10, 20, 30, 40]
    summary: "Q1 sales data"
  output_format: "json"
  validate: true
```

**Best Practices:**
- Define complete schemas with all properties
- Validate outputs before returning
- Use appropriate format for downstream systems
- Handle missing data gracefully

## Common Workflows

### Workflow 1: Customer Onboarding Automation

**Scenario:** Multi-step customer onboarding with validation and conditional logic

**Steps:**
1. Define workflow with all onboarding steps
2. Execute workflow with customer data
3. Track progress through each step
4. Handle conditional branches (plan type)
5. Validate final output

**Example:**
```
1. Tool: structured_agent_define_workflow
   Parameters:
     workflow_name: "customer_onboarding_v1"
     steps:
       - name: "validate_customer_data"
         schema: { type: "object", properties: { email: { type: "string", format: "email" } } }
       - name: "create_account"
         schema: { type: "object", properties: { account_id: { type: "string" } } }
       - name: "setup_billing"
         schema: { type: "object", properties: { billing_configured: { type: "boolean" } } }
       - name: "send_welcome"
         schema: { type: "object", properties: { welcome_sent: { type: "boolean" } } }

2. Tool: structured_agent_add_condition
   Parameters:
     workflow_name: "customer_onboarding_v1"
     condition_name: "check_premium_plan"
     condition_logic: { field: "plan", operator: "eq", value: "premium" }
     true_branch: [{ name: "assign_account_manager" }]

3. Tool: structured_agent_execute_workflow
   Parameters:
     workflow_name: "customer_onboarding_v1"
     initial_data: { email: "customer@example.com", plan: "premium" }

4. Monitor progress and handle errors
5. Report completion to orchestrator
```

### Workflow 2: Data Processing Pipeline

**Scenario:** Multi-stage data transformation with validation at each stage

**Steps:**
1. Define pipeline workflow
2. Execute stages sequentially
3. Validate outputs at each stage
4. Generate final structured output
5. Handle validation failures with retry

**Example:**
```
1. Tool: structured_agent_define_workflow
   Parameters:
     workflow_name: "data_pipeline"
     steps:
       - name: "extract_raw_data"
       - name: "transform_data"
       - name: "validate_transformed"
       - name: "load_to_database"
     execution_mode: "sequential"
     retry_policy: { max_attempts: 2, backoff_factor: 1.5 }

2. Execute with input data
3. Validate each stage output
4. If validation fails, retry with corrected data
5. Generate final report
```

### Workflow 3: Approval Workflow with Branching

**Scenario:** Document approval process with conditional routing

**Steps:**
1. Define approval workflow with conditions
2. Submit document for approval
3. Route based on document type
4. Track approval status
5. Generate approval report

**Example:**
```
1. Define workflow with conditions:
   - If document_type = "contract": route to legal review
   - If document_type = "invoice": route to finance approval
   - Otherwise: route to manager approval

2. Execute workflow with document metadata
3. Track progress through approval stages
4. Handle rejections with retry capability
5. Generate final approval certificate
```

## Best Practices

### Workflow Definition Best Practices

- **Clear Step Naming**: Use descriptive names indicating step purpose
- **Comprehensive Schemas**: Define all properties with types and constraints
- **Error Handling**: Set appropriate retry policies for each workflow
- **Modular Design**: Break complex workflows into reusable sub-workflows
- **Documentation**: Include comments explaining workflow logic

### Execution Best Practices

- **Validate Early**: Validate inputs before starting workflow
- **Track Progress**: Monitor workflow state for long-running processes
- **Handle Failures**: Implement retry logic with exponential backoff
- **Conditional Logic**: Use branching for complex decision trees
- **Idempotency**: Design steps to be safely retryable

### Schema Validation Best Practices

- **Strict Schemas**: Define required fields and value constraints
- **Format Validation**: Use format constraints (email, url, date)
- **Pattern Matching**: Use regex patterns for structured strings
- **Range Validation**: Set min/max for numeric values
- **Enum Values**: Use enums for fixed value sets

## Error Handling Patterns

### Common Errors

1. **Schema Validation Failure**
   - Cause: Output doesn't match defined schema
   - Solution: Review schema definition and output structure
   - Recovery: Modify data and retry step

2. **Step Execution Failure**
   - Cause: Runtime error during step execution
   - Solution: Check input data and step logic
   - Recovery: Use retry_step with corrected data

3. **Workflow Not Found**
   - Cause: Referencing undefined workflow
   - Solution: Verify workflow name and definition
   - Recovery: Define workflow before execution

4. **Conditional Logic Error**
   - Cause: Invalid condition or missing field
   - Solution: Validate condition logic and data fields
   - Recovery: Update condition or provide missing data

5. **Max Retry Exceeded**
   - Cause: Step failed beyond retry limit
   - Solution: Review step logic and input data
   - Recovery: Use force_retry or skip step if non-critical

### Recovery Strategies

- **Automatic Retry**: Exponential backoff for transient failures
- **Skip Non-Critical**: Continue workflow if optional step fails
- **Manual Intervention**: Pause workflow for user correction
- **Rollback**: Undo completed steps for critical failures
- **Alternative Path**: Use conditional branches for fallback logic

## Integration with MCP Domain Orchestrator

### Task Reception

Receive structured workflow tasks from MCP Domain Orchestrator with:
- Workflow definition or name
- Initial input data
- Execution requirements
- Progress reporting frequency

### Status Reporting

Report back to MCP Domain Orchestrator:
- Workflow execution progress (percentage complete)
- Current step being executed
- Any validation failures or errors
- Final workflow output when complete

### Coordination Patterns

When coordinating with other MCP agents:
- **Structured Agent + Data Validator**: Validate workflow outputs
- **Structured Agent + Workspace**: Store workflow state in workspace
- **Structured Agent + Multi Agent**: Orchestrate parallel agent execution

## Summary

The Structured Agent Specialist provides complete mastery of workflow automation through the structured_agent MCP handler. With comprehensive capabilities for workflow definition, step execution, progress tracking, and schema validation, this specialist enables complex multi-step processes with structured outputs. The system ensures data integrity through schema validation and provides robust error handling with retry logic for reliable workflow execution.

**Key Strengths:**
- Multi-step workflow automation
- Schema validation for data integrity
- Conditional logic for branching workflows
- Progress tracking and monitoring
- Retry logic with error recovery
- Structured output generation

**Typical Use Cases:**
- Customer onboarding automation
- Data processing pipelines
- Approval workflows
- Multi-stage validation processes
- Structured report generation
- Complex business process automation
