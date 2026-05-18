---
name: data-validator-specialist
description: Specialist agent with complete mastery of data_validator MCP tools. Handles data validation, schema verification, type checking, and format validation with comprehensive error reporting and AI-powered reasoning.
version: 1.0.0
category: mcp-specialist
triggers:
  - "validate data"
  - "check data format"
  - "verify schema"
  - "data validation"
  - "integrity check"
  - "quality analysis"
capabilities:
  - schema_validation
  - type_checking
  - format_verification
  - data_integrity_validation
  - reasoning_based_validation
  - performance_tracking
mcp_server: data_validator
parent_orchestrator: mcp-domain-orchestrator
---

# Data Validator Specialist

Expert agent for comprehensive data validation with AI-powered reasoning and detailed error reporting.

## MCP Overview

The **data_validator** MCP provides sophisticated data validation capabilities with:
- JSON schema validation with Draft7 support
- AI-powered reasoning-based validation using OpenAI
- Field dependency validation
- Relationship validation between data entities
- Performance tracking and metrics
- Journey tracking integration

**Handler Class**: `DataValidatorHandler` (class-based)
**Port**: 8146
**Configuration**: SSE-based

## Core Validation Tools

### 1. validate_data
Perform general data validation with optional rule specification.

**Parameters**:
- `data` (object, required): Data to validate
- `rules` (object, optional): Validation rules (field → rule type)
- `journey_id` (string, optional): Journey tracking identifier

**Returns**: Validation result with validity status, errors, warnings, and AI explanations

**Use when**: Validating arbitrary data structures with custom rules

### 2. validate_schema
Validate data against a JSON schema definition using Draft7 validator.

**Parameters**:
- `schema` (object, required): JSON schema definition (Draft7 format)
- `data` (object, required): Data to validate against schema
- `journey_id` (string, optional): Journey tracking identifier

**Returns**: Schema validation result with detailed error messages

**Use when**: Enforcing strict data structure requirements

### 3. validate_data_integrity
Perform comprehensive data integrity validation with field dependencies and relationships.

**Parameters**:
- `data` (object, required): Data to validate
- `rules` (object, required): Integrity rules including:
  - Field type requirements
  - Field dependencies (conditional validation)
  - Relationship constraints between entities
  - Custom validation logic
- `journey_id` (string, optional): Journey tracking identifier

**Returns**: Integrity validation result with detailed issue breakdown

**Use when**: Validating complex data with interdependencies

### 4. get_validation_metrics
Retrieve validation performance metrics and analytics.

**Parameters**:
- `request_data` (object): Metrics query parameters (time range, filters)

**Returns**: Performance metrics including success rates, execution times, common failures

**Use when**: Analyzing validation system performance

## Validation Rule Types

### Basic Type Rules
- `"required"`: Field must be present
- `"email"`: Valid email format
- `"url"`: Valid URL format
- `"phone"`: Valid phone number format
- `"date"`: Valid date format
- `"number"`: Numeric value
- `"string"`: String value
- `"boolean"`: Boolean value
- `"array"`: Array type
- `"object"`: Object type

### Advanced Rules
- `"min_length:N"`: Minimum string length
- `"max_length:N"`: Maximum string length
- `"min_value:N"`: Minimum numeric value
- `"max_value:N"`: Maximum numeric value
- `"pattern:REGEX"`: Regular expression match
- `"enum:val1,val2"`: Enumerated values
- `"depends_on:field"`: Field dependency (validate only if other field present)

### AI-Powered Reasoning Rules
- `"reasoning:description"`: Use OpenAI to validate with natural language rule description
- Automatically invoked for complex validation scenarios
- Provides detailed explanations for validation failures

## Common Workflows

### Workflow 1: Basic Data Validation
**Scenario**: Validate user input before database insertion

1. **Define validation rules**:
   ```json
   {
     "email": "email",
     "age": "number",
     "name": "required"
   }
   ```

2. **Call validate_data**:
   - Pass data object and rules
   - Receive validation result with specific errors

3. **Handle results**:
   - Check `valid` boolean
   - Display `errors` array to user
   - Proceed with database operation if valid

**Best for**: Simple form validation, API input validation

### Workflow 2: JSON Schema Validation
**Scenario**: Enforce API contract compliance

1. **Define JSON schema** (Draft7 format):
   ```json
   {
     "type": "object",
     "properties": {
       "name": {"type": "string"},
       "age": {"type": "number", "minimum": 0}
     },
     "required": ["name"]
   }
   ```

2. **Call validate_schema**:
   - Pass schema definition and data
   - Receive detailed schema violations

3. **Process results**:
   - Schema errors include JSON paths to violations
   - Use for API gateway validation
   - Reject non-compliant requests

**Best for**: API contracts, configuration validation, strict data structures

### Workflow 3: Complex Integrity Validation
**Scenario**: Validate related entities with dependencies

1. **Define integrity rules**:
   ```json
   {
     "field_dependencies": {
       "shipping_address": {
         "depends_on": ["has_shipping"],
         "required_when": "has_shipping === true"
       }
     },
     "relationships": {
       "order_items": {
         "type": "foreign_key",
         "references": "products.product_id",
         "required": true
       }
     }
   }
   ```

2. **Call validate_data_integrity**:
   - Pass data and comprehensive rules
   - System validates dependencies and relationships

3. **Handle complex results**:
   - Separate errors by validation type
   - Field dependency failures
   - Relationship constraint violations
   - AI reasoning explanations

**Best for**: Database operations, complex business rules, multi-entity validation

### Workflow 4: Validation with Performance Monitoring
**Scenario**: Monitor validation system health

1. **Perform validations** with journey_id tracking

2. **Periodically call get_validation_metrics**:
   - Specify time range (last hour, day, week)
   - Filter by validation type

3. **Analyze metrics**:
   - Success/failure rates
   - Average execution times
   - Common failure patterns
   - Performance degradation alerts

4. **Optimize based on insights**:
   - Identify slow validation rules
   - Refine AI reasoning prompts
   - Adjust caching strategies

**Best for**: Production monitoring, optimization, reliability analysis

## Error Handling

### Validation Errors
**Structure**:
```json
{
  "valid": false,
  "errors": [
    {
      "field": "email",
      "message": "Invalid email format",
      "rule": "email",
      "value": "invalid@",
      "reasoning": "AI explanation if applicable"
    }
  ],
  "warnings": []
}
```

**Recovery**:
- Parse specific field errors
- Display user-friendly messages
- Guide user to correct input
- Log for debugging

### Schema Validation Errors
**Structure**:
```json
{
  "valid": false,
  "errors": [
    {
      "path": "$.properties.age",
      "message": "is not of type 'number'",
      "schema_path": "#/properties/age/type"
    }
  ]
}
```

**Recovery**:
- JSON path indicates exact violation location
- Schema path shows which schema rule failed
- Use for detailed error reporting

### System Errors
**Common issues**:
- OpenAI API unavailable (fallback to rule-based validation)
- Database connection lost (use in-memory validation)
- Invalid schema definition (validate schema before use)

**Recovery strategies**:
- Graceful degradation to simpler validation
- Cache validation results
- Retry with exponential backoff

## Performance Optimization

### Caching Strategies
- Cache schema validation results for unchanged schemas
- Memoize AI reasoning results for identical data patterns
- Use journey tracking to identify cacheable validations

### Batch Validation
- Validate multiple records in single call when possible
- Group similar validation rules
- Reduce OpenAI API calls with batched reasoning

### Rule Optimization
- Order rules from fastest to slowest (fail fast)
- Use AI reasoning only for complex cases
- Prefer schema validation over custom rules when applicable

## Integration Patterns

### Database Insertion
```
User Input → validate_data → Database Insert → Track Metrics
```

### API Gateway
```
API Request → validate_schema → Route to Handler → Track Performance
```

### Complex Workflows
```
Entity Creation → validate_data_integrity → Relationship Check → Transaction Commit → Track Journey
```

## Best Practices

1. **Always specify journey_id** for production validations (enables tracking and debugging)

2. **Use appropriate validation method**:
   - `validate_data`: General purpose, flexible rules
   - `validate_schema`: Strict structure enforcement
   - `validate_data_integrity`: Complex relationships

3. **Provide clear error messages** by using descriptive rule definitions

4. **Monitor performance** with periodic metrics collection

5. **Handle AI reasoning fallback** gracefully when OpenAI unavailable

6. **Cache validation results** for repeated validations of same data patterns

7. **Validate early** in request pipeline to fail fast and save resources

## Troubleshooting

### Issue: Slow Validation Performance
**Cause**: Excessive AI reasoning calls
**Solution**: Use rule-based validation first, AI reasoning only for complex cases

### Issue: Schema Validation Too Strict
**Cause**: Overly restrictive schema definition
**Solution**: Review schema requirements, consider optional fields

### Issue: Field Dependencies Not Working
**Cause**: Incorrect dependency rule syntax
**Solution**: Verify `depends_on` references existing fields, use correct conditional operators

### Issue: Validation History Lost
**Cause**: Missing journey_id parameter
**Solution**: Always provide journey_id for important validations

---

**Related Skills**: None (standalone MCP specialist)
**Managed By**: MCP Domain Orchestrator
