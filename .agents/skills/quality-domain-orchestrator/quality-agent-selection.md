# Quality Agent Selection Logic

Select the correct quality specialist agent based on task characteristics. Match task keywords to specialist capabilities, assess urgency, and determine if multiple specialists are required.

## Specialist Selection Patterns

### Code Review Specialist

**Primary Keywords**: "review", "code review", "PR review", "check code", "review changes", "pull request", "inspect code", "code inspection"

**Secondary Keywords**: "bug", "style", "best practice", "lint", "quality check", "peer review", "code quality"

**Tasks This Specialist Handles**:
- Code inspection for bugs and errors
- Style guideline enforcement (PEP 8, ESLint, etc.)
- Best practice verification
- Security vulnerability detection
- Code maintainability assessment
- Pull request reviews
- Code quality metric analysis

**Coordinates With**:
- **Refactoring Specialist**: After identifying improvement opportunities
- **Documentation Specialist**: When documentation needs updating
- **Testing Specialist**: To verify test coverage and quality

**Selection Confidence Thresholds**:
- High (90%+): Task explicitly mentions "review" or "code review"
- Medium (60-89%): Task mentions quality checks without "review"
- Low (<60%): Task implies quality concerns indirectly

**Example Routing Decisions**:
- "Review the authentication code for security issues" → Code Review (95% confidence)
- "Check if the API follows best practices" → Code Review (85% confidence)
- "Make sure the code is clean" → Code Review + Refactoring (70% each)

---

### Refactoring Specialist

**Primary Keywords**: "refactor", "improve code", "clean up", "restructure", "simplify", "reorganize", "rewrite"

**Secondary Keywords**: "complexity", "duplication", "patterns", "readable", "maintainable", "DRY", "SOLID"

**Tasks This Specialist Handles**:
- Code restructuring for better organization
- Design pattern application
- Complexity reduction (cyclomatic complexity, nesting depth)
- Duplication elimination (DRY principle)
- Naming improvements for clarity
- Code smell elimination
- Legacy code modernization

**Coordinates With**:
- **Code Review Specialist**: Before and after refactoring for verification
- **Testing Specialist**: To ensure behavioral equivalence
- **Architecture Specialist**: For large-scale structural changes

**Selection Confidence Thresholds**:
- High (90%+): Task explicitly mentions "refactor" or "restructure"
- Medium (60-89%): Task mentions code improvement or simplification
- Low (<60%): Task implies structural issues

**Example Routing Decisions**:
- "Refactor the user service to use dependency injection" → Refactoring (95% confidence)
- "Simplify the payment processing logic" → Refactoring (80% confidence)
- "Clean up the legacy authentication code" → Refactoring + Technical Debt (75% each)

---

### Architecture Design Specialist

**Primary Keywords**: "architecture", "design", "system design", "architectural pattern", "architectural decision", "high-level design"

**Secondary Keywords**: "microservices", "monolith", "scalability", "modularity", "separation of concerns", "layered", "component design"

**Tasks This Specialist Handles**:
- High-level system architecture design
- Architectural pattern selection and application
- Component interface design
- Architectural decision documentation (ADRs)
- System scalability planning
- Cross-cutting concerns design (logging, security, etc.)
- Technology stack selection

**Coordinates With**:
- **Code Review Specialist**: To verify architectural principles in code
- **Documentation Specialist**: To document architectural decisions
- **Technical Debt Specialist**: To assess architectural debt

**Selection Confidence Thresholds**:
- High (90%+): Task explicitly mentions "architecture" or "system design"
- Medium (60-89%): Task mentions high-level design or patterns
- Low (<60%): Task implies structural decisions

**Example Routing Decisions**:
- "Design the microservices architecture for the new feature" → Architecture (95% confidence)
- "Should we use event sourcing or traditional CRUD?" → Architecture (90% confidence)
- "How should we structure the frontend components?" → Architecture + Frontend (80% each)

---

### Documentation Generation Specialist

**Primary Keywords**: "documentation", "docs", "comments", "docstrings", "API docs", "readme", "document", "write docs"

**Secondary Keywords**: "explain", "describe", "guide", "tutorial", "reference", "specification", "javadoc", "jsdoc"

**Tasks This Specialist Handles**:
- Inline code comment generation
- Function/class docstring creation
- API documentation generation (Swagger, OpenAPI, etc.)
- README file creation and maintenance
- Technical guide and tutorial writing
- Architecture decision record documentation
- Code example creation

**Coordinates With**:
- **Code Review Specialist**: To ensure documentation accuracy
- **Architecture Specialist**: To document architectural decisions
- **All Specialists**: Documentation follows every significant change

**Selection Confidence Thresholds**:
- High (90%+): Task explicitly mentions "documentation" or "docs"
- Medium (60-89%): Task mentions explaining or describing code
- Low (<60%): Task implies need for clarity

**Example Routing Decisions**:
- "Generate API documentation for the REST endpoints" → Documentation (95% confidence)
- "Add docstrings to all public functions" → Documentation (90% confidence)
- "Explain how the authentication flow works" → Documentation + Code Review (75% each)

---

### Technical Debt Management Specialist

**Primary Keywords**: "technical debt", "debt", "legacy code", "tech debt", "code smell", "technical debt assessment"

**Secondary Keywords**: "maintenance burden", "outdated", "deprecated", "workaround", "hack", "TODO", "FIXME"

**Tasks This Specialist Handles**:
- Technical debt identification and cataloging
- Debt severity assessment and scoring
- Debt prioritization using cost-benefit analysis
- Debt reduction roadmap creation
- Debt metrics tracking and reporting
- Legacy code assessment
- Code smell detection and categorization

**Coordinates With**:
- **Refactoring Specialist**: To implement debt reduction
- **Architecture Specialist**: For architectural debt
- **Code Review Specialist**: To prevent new debt introduction

**Selection Confidence Thresholds**:
- High (90%+): Task explicitly mentions "technical debt" or "debt"
- Medium (60-89%): Task mentions legacy code or maintenance issues
- Low (<60%): Task implies accumulated problems

**Example Routing Decisions**:
- "Assess technical debt in the payment module" → Technical Debt (95% confidence)
- "Clean up the legacy user authentication code" → Technical Debt + Refactoring (85% each)
- "Fix all the TODOs and FIXMEs in the codebase" → Technical Debt (80% confidence)

---

### Performance Profiling Specialist

**Primary Keywords**: "performance", "optimize", "profiling", "slow", "bottleneck", "speed", "performance optimization"

**Secondary Keywords**: "latency", "throughput", "response time", "memory", "CPU", "database query", "caching", "benchmark"

**Tasks This Specialist Handles**:
- Application performance profiling
- Bottleneck identification and analysis
- Performance optimization implementation
- Benchmarking and load testing
- Memory usage analysis and optimization
- Database query optimization
- Caching strategy implementation

**Coordinates With**:
- **Code Review Specialist**: To verify optimization correctness
- **Refactoring Specialist**: To implement performance improvements
- **Infrastructure Specialist**: For infrastructure-level optimizations

**Selection Confidence Thresholds**:
- High (90%+): Task explicitly mentions "performance" or "optimize"
- Medium (60-89%): Task mentions speed or efficiency issues
- Low (<60%): Task implies performance concerns

**Example Routing Decisions**:
- "Profile the API to find slow endpoints" → Performance (95% confidence)
- "The homepage loads too slowly, fix it" → Performance + Code Review (85% each)
- "Optimize database queries in the user service" → Performance (90% confidence)

---

## Multi-Specialist Scenarios

Some quality tasks require coordination across multiple specialists.

### Scenario 1: Code Review with Improvements

**Task Pattern**: "Review X and improve it"

**Specialists Involved**:
1. **Code Review** (Primary): Identifies issues and improvement areas
2. **Refactoring** (Secondary): Implements structural improvements
3. **Documentation** (Tertiary): Updates documentation for changes

**Coordination Flow**:
```
Code Review (inspect) → Refactoring (improve) → Documentation (document) → Code Review (verify)
```

**Example Tasks**:
- "Review the authentication module and clean it up"
- "Check the API code and make it more maintainable"
- "Inspect the data processing logic and simplify it"

---

### Scenario 2: Performance Optimization

**Task Pattern**: "Make X faster" or "Optimize X"

**Specialists Involved**:
1. **Performance** (Primary): Profiles and identifies bottlenecks
2. **Code Review** (Secondary): Analyzes problem code
3. **Refactoring** (Tertiary): Implements optimizations
4. **Documentation** (Quaternary): Documents performance findings

**Coordination Flow**:
```
Performance (profile) → Code Review (analyze) → Refactoring (optimize) → Performance (verify) → Documentation (document)
```

**Example Tasks**:
- "Speed up the report generation endpoint"
- "Optimize the search functionality"
- "Reduce memory usage in the data processing pipeline"

---

### Scenario 3: Architecture Improvement

**Task Pattern**: "Redesign X" or "Improve architecture of X"

**Specialists Involved**:
1. **Architecture** (Primary): Designs new structure
2. **Technical Debt** (Secondary): Assesses current debt and impact
3. **Refactoring** (Tertiary): Implements architectural changes
4. **Documentation** (Quaternary): Documents design decisions
5. **Code Review** (Quinary): Verifies implementation

**Coordination Flow**:
```
Architecture (design) → Technical Debt (assess) → Refactoring (implement) → Documentation (document) → Code Review (verify)
```

**Example Tasks**:
- "Redesign the authentication system to use OAuth2"
- "Improve the architecture of the payment processing module"
- "Migrate from monolith to microservices for the user service"

---

### Scenario 4: Technical Debt Reduction

**Task Pattern**: "Clean up X" or "Reduce debt in X"

**Specialists Involved**:
1. **Technical Debt** (Primary): Identifies and prioritizes debt
2. **Architecture** (Secondary): Plans solution approach
3. **Refactoring** (Tertiary): Implements debt reduction
4. **Code Review** (Quaternary): Verifies improvements
5. **Documentation** (Quinary): Updates documentation

**Coordination Flow**:
```
Technical Debt (identify) → Architecture (plan) → Refactoring (implement) → Code Review (verify) → Documentation (update)
```

**Example Tasks**:
- "Clean up the legacy billing module"
- "Reduce technical debt in the user service"
- "Fix the accumulated TODOs and code smells"

---

## Urgency Assessment

Assign urgency level to determine specialist prioritization.

### Critical Urgency (Priority 1)
**Triggers**:
- Security vulnerabilities discovered during code review
- Critical performance issues affecting production
- Blocking bugs preventing deployment

**Immediate Action**:
- Assign specialist immediately
- Bypass normal queue
- Report to Master Orchestrator

**Examples**:
- "SQL injection vulnerability in user login" → Code Review (Critical)
- "API response time increased from 200ms to 5s" → Performance (Critical)

---

### High Urgency (Priority 2)
**Triggers**:
- Production bugs requiring quick fix
- Performance degradation affecting users
- Pull requests blocking other work

**Action**:
- Prioritize in queue
- Assign within 5 minutes
- Coordinate with other domains if needed

**Examples**:
- "Dashboard loading slowly after recent deploy" → Performance (High)
- "PR needs review before end of day" → Code Review (High)

---

### Medium Urgency (Priority 3)
**Triggers**:
- Scheduled refactoring work
- Non-blocking technical debt
- Documentation updates

**Action**:
- Add to normal queue
- Assign when specialist available
- Normal coordination process

**Examples**:
- "Refactor the payment module for better maintainability" → Refactoring (Medium)
- "Document the new API endpoints" → Documentation (Medium)

---

### Low Urgency (Priority 4)
**Triggers**:
- Nice-to-have improvements
- Long-term technical debt
- Non-critical documentation

**Action**:
- Add to backlog
- Schedule for later execution
- May be deferred if higher priority work arrives

**Examples**:
- "Add code comments to utility functions" → Documentation (Low)
- "Assess technical debt in admin panel" → Technical Debt (Low)

---

## Selection Algorithm

Systematic algorithm for selecting quality specialist(s).

```python
function select_quality_specialist(task):
  # Step 1: Extract keywords from task
  keywords = extract_keywords(task.description)

  # Step 2: Score each specialist type
  scores = {}
  for specialist_type in QUALITY_SPECIALISTS:
    keyword_score = calculate_keyword_match(keywords, specialist_type.keywords)
    urgency_score = assess_urgency(task)
    impact_score = estimate_impact(task, specialist_type)

    # Weighted scoring: keywords 50%, urgency 30%, impact 20%
    total_score = (keyword_score * 0.5) + (urgency_score * 0.3) + (impact_score * 0.2)
    scores[specialist_type] = total_score

  # Step 3: Select specialist(s) above threshold
  selected_specialists = []
  for specialist_type, score in sorted(scores.items(), key=lambda x: x[1], reverse=True):
    if score >= SELECTION_THRESHOLD:  # e.g., 60%
      selected_specialists.append(specialist_type)

  # Step 4: Check for multi-specialist scenario
  if len(selected_specialists) > 1:
    coordination_pattern = identify_coordination_pattern(selected_specialists)
    return {
      "specialists": selected_specialists,
      "coordination": coordination_pattern,
      "primary": selected_specialists[0]
    }

  # Step 5: Return single specialist
  return {
    "specialists": [selected_specialists[0]],
    "coordination": None,
    "primary": selected_specialists[0]
  }
```

### Keyword Matching Function

```python
function calculate_keyword_match(task_keywords, specialist_keywords):
  primary_matches = count_matches(task_keywords, specialist_keywords.primary)
  secondary_matches = count_matches(task_keywords, specialist_keywords.secondary)

  # Primary keywords worth more than secondary
  score = (primary_matches * 1.0) + (secondary_matches * 0.5)

  # Normalize to 0-100 scale
  max_possible = len(specialist_keywords.primary) + (len(specialist_keywords.secondary) * 0.5)
  normalized_score = (score / max_possible) * 100

  return normalized_score
```

### Impact Estimation Function

```python
function estimate_impact(task, specialist_type):
  # Factors affecting impact
  codebase_size = estimate_affected_code_size(task)
  complexity = assess_task_complexity(task)
  dependencies = count_dependent_components(task)

  # Specialist-specific impact multipliers
  impact_multipliers = {
    "code_review": 1.0,        # Standard impact
    "refactoring": 1.2,        # Higher risk of breaking changes
    "architecture": 1.5,       # Highest impact on system
    "documentation": 0.8,      # Lower risk
    "technical_debt": 1.1,     # Moderate impact
    "performance": 1.3         # Can affect system-wide behavior
  }

  base_impact = (codebase_size * 0.4) + (complexity * 0.4) + (dependencies * 0.2)
  adjusted_impact = base_impact * impact_multipliers[specialist_type]

  return normalized_to_100(adjusted_impact)
```

---

## Selection Examples

### Example 1: Simple Code Review
**Task**: "Review the user authentication PR"

**Analysis**:
- Keywords: "review", "user authentication", "PR"
- Matches: Code Review (primary: "review", "PR review")
- Urgency: Medium (normal PR review)
- Impact: Medium (authentication is critical but PR scope limited)

**Selection**:
- Code Review Specialist (95% confidence)
- No coordination needed
- Priority: Medium

---

### Example 2: Performance Optimization with Multiple Specialists
**Task**: "The dashboard loads slowly, find and fix the bottleneck"

**Analysis**:
- Keywords: "dashboard", "slowly", "find", "fix", "bottleneck"
- Matches: Performance (primary: "slow", "bottleneck"), Code Review (secondary: "find", "fix")
- Urgency: High (affecting user experience)
- Impact: High (dashboard is high-traffic area)

**Selection**:
- Primary: Performance Specialist (90% confidence)
- Secondary: Code Review Specialist (75% confidence)
- Tertiary: Refactoring Specialist (65% confidence)
- Coordination Pattern: Performance Optimization
- Priority: High

---

### Example 3: Legacy Code Cleanup
**Task**: "Clean up and modernize the legacy billing module"

**Analysis**:
- Keywords: "clean up", "modernize", "legacy", "billing"
- Matches: Technical Debt (primary: "legacy"), Refactoring (primary: "clean up"), Architecture (secondary: "modernize")
- Urgency: Medium (scheduled improvement)
- Impact: High (billing is critical, but legacy code is isolated)

**Selection**:
- Primary: Technical Debt Specialist (85% confidence)
- Secondary: Architecture Specialist (80% confidence)
- Tertiary: Refactoring Specialist (75% confidence)
- Quaternary: Documentation Specialist (60% confidence)
- Coordination Pattern: Technical Debt Reduction
- Priority: Medium
