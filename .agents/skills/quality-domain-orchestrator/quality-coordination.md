# Quality Team Coordination Patterns

Coordinate multiple quality specialists working together on complex quality initiatives. Define coordination workflows, quality gates, cross-specialist communication protocols, and reporting to Master Orchestrator.

## Common Coordination Patterns

### Pattern 1: Code Review Workflow

**Purpose**: Iterative code quality improvement cycle

**Specialists Involved**:
1. **Code Review** (Primary): Inspect code for issues
2. **Refactoring** (Secondary): Implement improvements
3. **Documentation** (Tertiary): Document changes
4. **Code Review** (Verification): Verify improvements

**Flow Diagram**:
```
Code Review (inspect)
  ↓ [issues identified]
Refactoring (improve)
  ↓ [changes implemented]
Documentation (document changes)
  ↓ [documentation updated]
Code Review (verify)
  ↓ [pass/fail]
```

**Quality Gates**:
1. **After Initial Review**: Must identify at least one actionable issue OR approve as-is
2. **After Refactoring**: Must maintain test pass rate (100% of tests passing)
3. **After Documentation**: Must document all significant changes
4. **After Verification**: Must pass final review OR identify remaining issues

**Iteration Logic**:
- If verification fails: Return to Refactoring with specific feedback
- If verification passes: Mark workflow complete
- Maximum 3 iterations before escalating to Master Orchestrator

**Example Scenarios**:
- PR review identifies 5 issues → Refactoring fixes issues → Documentation updates → Review verifies all fixed
- Code review suggests structural improvements → Refactoring applies patterns → Documentation explains patterns → Review approves

**Coordination Algorithm**:
```python
function coordinate_code_review_workflow(task):
  iteration = 0
  max_iterations = 3

  while iteration < max_iterations:
    # Step 1: Code Review inspection
    review_result = execute_code_review(task)
    if review_result.status == "APPROVED":
      return success("Code approved without changes")

    # Step 2: Refactoring improvements
    refactor_result = execute_refactoring(task, review_result.issues)
    if not passes_quality_gate("test_pass_rate", refactor_result):
      return failure("Refactoring broke tests")

    # Step 3: Documentation updates
    doc_result = execute_documentation(task, refactor_result.changes)
    if not passes_quality_gate("documentation_completeness", doc_result):
      return failure("Documentation incomplete")

    # Step 4: Verification review
    verify_result = execute_code_review_verification(task)
    if verify_result.status == "APPROVED":
      return success("Code review workflow complete")

    iteration += 1

  # Max iterations reached - escalate
  return escalate_to_master("Code review workflow exceeded max iterations")
```

---

### Pattern 2: Performance Optimization

**Purpose**: Data-driven performance improvement with measurement

**Specialists Involved**:
1. **Performance** (Primary): Profile application to identify bottlenecks
2. **Code Review** (Secondary): Analyze problem areas in code
3. **Refactoring** (Tertiary): Implement optimizations
4. **Performance** (Verification): Verify improvements with metrics
5. **Documentation** (Final): Document findings and optimizations

**Flow Diagram**:
```
Performance (profile)
  ↓ [bottlenecks identified]
Code Review (identify issues)
  ↓ [root causes found]
Refactoring (optimize)
  ↓ [changes implemented]
Performance (verify)
  ↓ [metrics measured]
Documentation (document findings)
  ↓ [complete]
```

**Quality Gates**:
1. **After Profiling**: Must identify measurable bottlenecks with baseline metrics
2. **After Code Review**: Must pinpoint root causes in code
3. **After Refactoring**: Must maintain correctness (tests pass)
4. **After Verification**: Must show measurable improvement (e.g., 20% faster)
5. **After Documentation**: Must document baseline, changes, and results

**Measurement Requirements**:
- Baseline metrics captured before optimization
- Target improvement defined (e.g., "reduce latency by 30%")
- Post-optimization metrics compared to baseline
- Statistical significance verified (multiple runs)

**Example Scenarios**:
- API endpoint takes 2s → Profile identifies N+1 query → Code Review finds inefficient loop → Refactoring implements batch query → Endpoint now takes 400ms (80% improvement)
- Dashboard loads in 5s → Profile shows large payload → Code Review finds unnecessary data → Refactoring implements pagination → Dashboard loads in 1.5s (70% improvement)

**Coordination Algorithm**:
```python
function coordinate_performance_optimization(task):
  # Step 1: Baseline profiling
  profile_result = execute_performance_profiling(task)
  baseline_metrics = profile_result.metrics
  bottlenecks = profile_result.bottlenecks

  if not passes_quality_gate("bottleneck_identification", profile_result):
    return failure("No measurable bottlenecks identified")

  # Step 2: Code review of problem areas
  review_result = execute_code_review_targeted(task, bottlenecks)
  root_causes = review_result.root_causes

  if not root_causes:
    return failure("Could not identify root causes")

  # Step 3: Implement optimizations
  refactor_result = execute_refactoring_optimization(task, root_causes)

  if not passes_quality_gate("test_pass_rate", refactor_result):
    return failure("Optimization broke functionality")

  # Step 4: Verify improvements
  verify_result = execute_performance_profiling(task)
  improvement = calculate_improvement(baseline_metrics, verify_result.metrics)

  if improvement < task.target_improvement:
    return partial_success(f"Improved by {improvement}%, target was {task.target_improvement}%")

  # Step 5: Document findings
  doc_result = execute_documentation_performance(task, baseline_metrics, verify_result.metrics, refactor_result.changes)

  return success(f"Performance improved by {improvement}%")
```

---

### Pattern 3: Architecture Improvement

**Purpose**: Strategic system redesign with long-term focus

**Specialists Involved**:
1. **Architecture** (Primary): Design new architecture
2. **Technical Debt** (Secondary): Assess current debt and impact
3. **Refactoring** (Tertiary): Implement architectural changes
4. **Documentation** (Quaternary): Document architectural decisions
5. **Code Review** (Verification): Verify implementation matches design

**Flow Diagram**:
```
Architecture (design)
  ↓ [new design created]
Technical Debt (assess impact)
  ↓ [debt analysis complete]
Refactoring (implement)
  ↓ [changes implemented]
Documentation (document decisions)
  ↓ [ADRs written]
Code Review (verify)
  ↓ [design verified]
```

**Quality Gates**:
1. **After Architecture Design**: Must create concrete, implementable design with clear benefits
2. **After Technical Debt Assessment**: Must quantify current debt and migration impact
3. **After Refactoring**: Must maintain backward compatibility OR have migration plan
4. **After Documentation**: Must create Architecture Decision Records (ADRs)
5. **After Verification**: Must verify design principles are followed

**Documentation Requirements**:
- Architecture Decision Records (ADRs) for all major decisions
- Migration plan if breaking changes required
- Rollback plan if implementation fails
- Benefits quantification (maintainability, scalability, etc.)

**Example Scenarios**:
- Monolith → Microservices: Architecture designs service boundaries → Technical Debt assesses coupling → Refactoring extracts services → Documentation records decisions → Code Review verifies boundaries
- Procedural → Object-Oriented: Architecture defines class structure → Technical Debt assesses refactoring effort → Refactoring implements OOP → Documentation explains patterns → Code Review verifies design

**Coordination Algorithm**:
```python
function coordinate_architecture_improvement(task):
  # Step 1: Create architecture design
  design_result = execute_architecture_design(task)
  proposed_design = design_result.design

  if not passes_quality_gate("design_completeness", design_result):
    return failure("Design not sufficiently detailed")

  # Step 2: Assess technical debt and impact
  debt_result = execute_technical_debt_assessment(task, proposed_design)
  current_debt = debt_result.debt_score
  migration_effort = debt_result.estimated_effort

  # Check if improvement justifies effort
  if not justifies_effort(proposed_design.benefits, migration_effort):
    return failure("Benefits do not justify migration effort")

  # Step 3: Implement architectural changes
  refactor_result = execute_refactoring_architectural(task, proposed_design)

  if not passes_quality_gate("backward_compatibility", refactor_result):
    if not refactor_result.migration_plan:
      return failure("Breaking changes without migration plan")

  # Step 4: Document architectural decisions
  doc_result = execute_documentation_architecture(task, proposed_design, refactor_result)

  if not doc_result.adrs_created:
    return failure("Architecture Decision Records not created")

  # Step 5: Verify implementation
  verify_result = execute_code_review_architectural(task, proposed_design)

  if verify_result.design_violations:
    return failure(f"Design violations found: {verify_result.design_violations}")

  return success("Architecture improvement complete")
```

---

### Pattern 4: Technical Debt Reduction

**Purpose**: Systematic reduction of accumulated technical debt

**Specialists Involved**:
1. **Technical Debt** (Primary): Identify and prioritize debt
2. **Architecture** (Secondary): Plan solution approach
3. **Refactoring** (Tertiary): Implement debt reduction
4. **Code Review** (Quaternary): Verify improvements
5. **Documentation** (Final): Update documentation

**Flow Diagram**:
```
Technical Debt (identify)
  ↓ [debt items cataloged]
Technical Debt (prioritize)
  ↓ [priority order established]
Architecture (plan solution)
  ↓ [solution approach defined]
Refactoring (implement)
  ↓ [debt reduced]
Code Review (verify)
  ↓ [improvements confirmed]
Documentation (update docs)
  ↓ [complete]
```

**Quality Gates**:
1. **After Identification**: Must catalog debt items with severity scores
2. **After Prioritization**: Must use cost-benefit analysis for ordering
3. **After Solution Planning**: Must have concrete, achievable plan
4. **After Implementation**: Must reduce debt score measurably
5. **After Verification**: Must confirm debt actually reduced (not just moved)

**Prioritization Criteria**:
- **Severity**: How much is this debt costing us? (maintenance burden, bug risk)
- **Effort**: How much work to fix?
- **Impact**: How much improvement will we get?
- **Risk**: What's the risk of not fixing?

**Example Scenarios**:
- Legacy authentication code → Technical Debt catalogs issues → Architecture plans OAuth2 migration → Refactoring implements → Code Review verifies security → Documentation updates
- Deprecated API usage → Technical Debt prioritizes critical APIs → Architecture plans replacement strategy → Refactoring updates code → Code Review checks correctness → Documentation reflects changes

**Coordination Algorithm**:
```python
function coordinate_technical_debt_reduction(task):
  # Step 1: Identify technical debt
  debt_result = execute_technical_debt_identification(task)
  debt_items = debt_result.debt_items

  if not debt_items:
    return success("No technical debt found")

  # Step 2: Prioritize debt items
  prioritized_items = prioritize_debt_items(debt_items)

  # Step 3: Plan solution for top priority items
  top_items = prioritized_items[:task.max_items_per_cycle]
  solution_result = execute_architecture_planning(task, top_items)

  if not passes_quality_gate("solution_feasibility", solution_result):
    return failure("Proposed solutions not feasible")

  # Step 4: Implement debt reduction
  refactor_result = execute_refactoring_debt_reduction(task, solution_result.solutions)

  initial_debt_score = calculate_debt_score(debt_items)
  final_debt_score = calculate_debt_score_after_refactoring(refactor_result)
  debt_reduction = initial_debt_score - final_debt_score

  if debt_reduction <= 0:
    return failure("Debt not actually reduced")

  # Step 5: Verify improvements
  verify_result = execute_code_review_debt_verification(task, top_items)

  if verify_result.debt_still_present:
    return partial_success(f"Reduced debt by {debt_reduction}, but some remains")

  # Step 6: Update documentation
  doc_result = execute_documentation_update(task, refactor_result.changes)

  return success(f"Technical debt reduced by {debt_reduction} points")
```

---

## Quality Gate Definitions

Quality gates ensure work meets standards before progressing.

### Test Pass Rate Gate

**Purpose**: Ensure refactoring/optimization doesn't break functionality

**Criteria**:
- 100% of existing tests must pass
- No new test failures introduced
- Test coverage maintained or improved

**Failure Action**: Roll back changes and retry with different approach

### Documentation Completeness Gate

**Purpose**: Ensure significant changes are documented

**Criteria**:
- All public API changes documented
- Significant architectural decisions recorded in ADRs
- Code comments added for complex logic
- README updated if user-facing changes

**Failure Action**: Documentation specialist adds missing documentation

### Backward Compatibility Gate

**Purpose**: Prevent breaking changes without migration plan

**Criteria**:
- Existing APIs maintain same interface OR
- Migration plan provided with deprecation timeline
- Breaking changes documented and justified

**Failure Action**: Create migration plan or redesign to maintain compatibility

### Bottleneck Identification Gate

**Purpose**: Ensure performance profiling found measurable issues

**Criteria**:
- Specific bottlenecks identified with metrics
- Baseline performance measured
- Target improvement defined

**Failure Action**: Re-profile with better instrumentation

### Design Completeness Gate

**Purpose**: Ensure architectural design is implementable

**Criteria**:
- Component interfaces defined
- Technology choices justified
- Integration points specified
- Non-functional requirements addressed

**Failure Action**: Architecture specialist refines design

---

## Cross-Specialist Communication

Specialists share information throughout coordination workflow.

### Communication Patterns

**Code Review → Refactoring**:
- Share specific code issues identified
- Provide refactoring suggestions
- Define expected improvements

**Refactoring → Code Review**:
- Report changes made
- Request verification
- Highlight potential concerns

**Performance → Code Review**:
- Share profiling data
- Identify performance hotspots
- Request root cause analysis

**Architecture → Technical Debt**:
- Share proposed design
- Request debt impact assessment
- Get migration effort estimate

**All Specialists → Documentation**:
- Share significant changes
- Provide context for decisions
- Request documentation updates

### Shared Data Structures

**Issue Report** (Code Review → Refactoring):
```python
{
  "issue_id": "unique_id",
  "severity": "critical|high|medium|low",
  "description": "Description of issue",
  "location": "file:line",
  "suggested_fix": "How to fix",
  "impact": "Why this matters"
}
```

**Performance Profile** (Performance → Code Review):
```python
{
  "profile_id": "unique_id",
  "bottlenecks": [
    {
      "location": "file:function",
      "metric": "response_time",
      "current_value": "2000ms",
      "target_value": "500ms",
      "samples": 100
    }
  ],
  "baseline_metrics": {...},
  "profiling_method": "method_used"
}
```

**Architectural Design** (Architecture → Others):
```python
{
  "design_id": "unique_id",
  "components": [...],
  "interfaces": [...],
  "patterns": ["pattern_1", "pattern_2"],
  "decisions": [
    {
      "decision": "description",
      "rationale": "why",
      "alternatives": ["alt_1", "alt_2"],
      "trade_offs": "pros and cons"
    }
  ]
}
```

**Debt Assessment** (Technical Debt → Others):
```python
{
  "assessment_id": "unique_id",
  "debt_items": [
    {
      "item_id": "unique_id",
      "severity": "critical|high|medium|low",
      "location": "file or module",
      "description": "what is the debt",
      "cost": "maintenance burden",
      "effort_to_fix": "estimated effort"
    }
  ],
  "total_debt_score": 85,
  "priority_order": ["item_1", "item_2", ...]
}
```

---

## Continuous Improvement

Quality Domain Orchestrator learns from quality coordination experience.

### Learning Triggers

**Pattern Success**: Coordination pattern completed successfully
- Record pattern used, specialists involved, duration, outcome
- Identify which patterns work best for which task types
- Update selection confidence scores

**Pattern Failure**: Coordination pattern failed or exceeded iterations
- Record failure mode, bottleneck, reason
- Update pattern to avoid similar failures
- Consider alternative patterns for similar tasks

**Quality Gate Failure**: Gate failed repeatedly
- Identify root cause (unrealistic criteria, specialist capability gap, etc.)
- Adjust gate criteria if too strict
- Update specialist skills if capability gap

### Improvement Actions

**Adjust Pattern Selection**:
- If Performance Optimization pattern frequently fails → prefer simpler optimization approach
- If Code Review Workflow exceeds iterations → involve Architecture earlier
- Track success rates per pattern and adjust selection algorithm

**Refine Quality Gates**:
- If Test Pass Rate gate fails often → improve test suite before refactoring
- If Documentation Completeness gate blocks → define clearer documentation standards
- Gates should catch issues, not block progress unnecessarily

**Update Specialist Skills**:
- If Code Review misses issues → enhance review checklist
- If Refactoring breaks tests → improve testing before refactoring
- Specialists should learn from quality gate failures

---

## Reporting to Master Orchestrator

Quality Domain Orchestrator reports progress and status only to Master Orchestrator, never directly to user.

### Status Report Format

```
Quality Domain Status Report:

Active Coordination Patterns:
  - Code Review Workflow (task-123): Code Review → Refactoring (iteration 1/3)
  - Performance Optimization (task-456): Performance profiling complete, 3 bottlenecks found

Quality Specialists Status:
  - Code Review: 2 active tasks, 1 queued
  - Refactoring: 1 active task, 0 queued
  - Architecture: 0 active tasks, 1 queued
  - Documentation: 3 active tasks, 2 queued
  - Technical Debt: 1 active task, 0 queued
  - Performance: 1 active task, 1 queued

Quality Metrics:
  - Code review pass rate: 94% (target: 95%)
  - Average refactoring duration: 23 minutes
  - Technical debt score: 72/100 (improving, was 85)
  - Performance improvement average: 35% (last 5 optimizations)

Blocking Issues:
  - None

Completed This Period:
  - 5 code reviews
  - 2 refactoring tasks
  - 1 performance optimization (67% improvement)
  - 3 documentation updates
```

### Escalation Scenarios

Escalate to Master Orchestrator when:

**Critical Quality Issues**:
- Security vulnerability discovered during code review
- Performance degradation cannot be resolved
- Architecture design requires cross-domain coordination

**Pattern Failures**:
- Coordination pattern exceeded max iterations
- Quality gate failed repeatedly despite multiple attempts
- Specialist capability gap preventing task completion

**Resource Constraints**:
- Quality task queue exceeding threshold (10+ tasks)
- All specialists at capacity with more work incoming
- Urgent quality task but no specialists available

**Cross-Domain Coordination Needed**:
- Performance optimization requires backend changes → request Backend Domain coordination
- Refactoring requires frontend updates → request Frontend Domain coordination
- Architecture change requires infrastructure updates → request Infrastructure Domain coordination

### Escalation Message Format

```
Quality Domain Escalation:

Issue: [Critical|High|Medium]
Category: [Quality Issue|Pattern Failure|Resource Constraint|Cross-Domain]

Description:
[Clear description of issue requiring escalation]

Impact:
[How this affects ongoing work or quality goals]

Requested Action:
[What Master Orchestrator should do]

Context:
[Relevant background information]
```

---

## Coordination Algorithm Summary

Comprehensive coordination algorithm incorporating all patterns.

```python
function coordinate_quality_team(task):
  # Step 1: Identify required specialists
  required_specialists = select_quality_specialists(task)

  # Step 2: Identify coordination pattern
  pattern = identify_coordination_pattern(required_specialists, task)

  # Step 3: Create execution plan
  execution_plan = create_quality_execution_plan(pattern, required_specialists, task)

  # Step 4: Execute with quality gates
  results = []
  for stage in execution_plan.stages:
    # Execute specialists in this stage
    stage_result = execute_quality_stage(stage)

    # Check quality gate
    if not passes_quality_gate(stage_result, stage.gate):
      # Quality gate failed
      if stage.retry_allowed:
        stage_result = retry_quality_stage(stage, stage_result.feedback)
        if not passes_quality_gate(stage_result, stage.gate):
          # Still failed after retry - escalate
          return escalate_to_master(f"Quality gate failed for {stage.name} after retry")
      else:
        # No retry allowed - escalate immediately
        return escalate_to_master(f"Quality gate failed for {stage.name}")

    results.append(stage_result)

  # Step 5: Aggregate results
  final_result = aggregate_quality_results(results)

  # Step 6: Report to Master
  report_to_master(task, final_result)

  return final_result
```
