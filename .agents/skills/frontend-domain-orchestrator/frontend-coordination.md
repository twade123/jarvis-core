# Frontend Team Coordination Patterns

## Overview

Complex frontend projects require multiple specialists working together. This document defines coordination patterns, workflows, and algorithms for orchestrating frontend development teams.

## Coordination Principles

### Core Concepts

1. **Sequential Workflows**: Specialists work one after another, each building on previous work
2. **Parallel Execution**: Multiple specialists work simultaneously on independent parts
3. **Quality Gates**: Each specialist validates output before passing to next
4. **Integration Points**: Handoffs between specialists with clear deliverables

### When to Coordinate Multiple Specialists

- **Component architecture** affects multiple layers (structure, style, behavior, tests)
- **Design implementation** requires design-to-code translation and accessibility
- **Feature development** needs state management, UI, and testing
- **System-level changes** impact component library, design system, or shared patterns

## Common Coordination Patterns

### Pattern 1: Component Development Pipeline

**Description**: Standard workflow for creating a new component from scratch

**Flow**: Component Architect (design) → Framework (implement) → Styling (style) → Testing (test) → Accessibility (audit)

**Execution**: Sequential with quality gates

**Workflow Details**:

```
Phase 1: Architecture (Component Architect)
- Design component API (props, events, slots)
- Plan component hierarchy
- Define reusability requirements
- Document component interface
- Quality Gate: Architecture review

Phase 2: Implementation (Framework Specialist)
- Implement component logic
- Add framework-specific patterns (hooks, lifecycle)
- Implement props and events
- Add basic structure
- Quality Gate: Component renders correctly

Phase 3: Styling (Styling Specialist)
- Apply design system tokens
- Implement responsive behavior
- Add visual polish
- Optimize CSS performance
- Quality Gate: Matches design specification

Phase 4: Testing (Testing Specialist)
- Write unit tests for logic
- Add integration tests
- Test edge cases
- Document test coverage
- Quality Gate: 80%+ coverage

Phase 5: Accessibility (Accessibility Specialist)
- Add ARIA attributes
- Implement keyboard navigation
- Test with screen readers
- Validate WCAG compliance
- Quality Gate: WCAG 2.1 AA compliance
```

**Use Cases**:
- Creating new component library components
- Building complex reusable components
- Implementing design system primitives

**Coordination Requirements**:
- Clear handoff between phases
- Each specialist validates previous work
- Final component passes all quality gates

### Pattern 2: Feature Development (Parallel)

**Description**: Building a feature with logic and design work happening simultaneously

**Flow**: Framework (logic) + Styling (design) → State (integrate) → Testing (verify)

**Execution**: Parallel initial work, then sequential integration

**Workflow Details**:

```
Phase 1: Parallel Development
┌─ Framework Specialist ─┐     ┌─ Styling Specialist ─┐
│ - Build component shell │     │ - Create design mockup│
│ - Add business logic    │     │ - Design system tokens│
│ - Implement interactions│     │ - Responsive layouts  │
│ - Prepare state hooks   │     │ - Visual components   │
└────────────────────────┘     └──────────────────────┘
         ↓                              ↓
         └──────────── Merge ───────────┘
                        ↓
Phase 2: Integration (State Management)
- Connect components to state
- Implement data fetching
- Add loading/error states
- Optimize re-renders
Quality Gate: State flows correctly

Phase 3: Verification (Testing)
- E2E feature tests
- Integration tests
- Performance testing
- User flow validation
Quality Gate: All scenarios pass
```

**Use Cases**:
- Building user-facing features
- Adding new pages or views
- Implementing user workflows

**Coordination Requirements**:
- Framework and Styling specialists need initial requirements
- Integration point requires both specialists to complete
- Testing validates entire feature

### Pattern 3: Design System Implementation

**Description**: Building or updating a design system with full quality assurance

**Flow**: UI/UX (spec) → Styling (tokens/variables) → Component (primitives) → Accessibility (audit) → Testing (document)

**Execution**: Sequential with iterative refinement

**Workflow Details**:

```
Phase 1: Specification (UI/UX Specialist)
- Define design principles
- Create design tokens
- Document component patterns
- Plan component hierarchy
- Quality Gate: Design spec complete

Phase 2: Token Implementation (Styling Specialist)
- Implement design tokens (colors, spacing, typography)
- Create theme system
- Build CSS architecture
- Set up token management
- Quality Gate: Tokens applied consistently

Phase 3: Component Primitives (Component Architect + Framework)
- Build base components (Button, Input, Card)
- Implement composition patterns
- Add variant support
- Document component APIs
- Quality Gate: Primitives functional

Phase 4: Accessibility Audit (Accessibility Specialist)
- WCAG compliance check
- Screen reader testing
- Keyboard navigation
- Focus management
- Quality Gate: WCAG 2.1 AA compliance

Phase 5: Documentation (Testing Specialist + Component Architect)
- Storybook stories for each component
- Usage examples
- API documentation
- Accessibility guidelines
- Quality Gate: Complete documentation
```

**Use Cases**:
- Creating new design system
- Updating existing design system
- Standardizing component library

**Coordination Requirements**:
- Iterative refinement between phases
- All specialists review design system
- Focus on consistency and reusability

### Pattern 4: Complex Page Development

**Description**: Building a complex page with multiple concerns (layout, data, interactions, quality)

**Flow**: UI/UX (layout) → Component (structure) + State (data) + Framework (logic) → Styling (polish) → Testing + Accessibility (quality)

**Execution**: Mixed parallel and sequential with multiple integration points

**Workflow Details**:

```
Phase 1: Layout Design (UI/UX Specialist)
- Plan page layout
- Design user flows
- Create wireframes
- Define interaction patterns
- Quality Gate: Layout approved

Phase 2: Parallel Development
┌─ Component Architect ─┐ ┌─ State Management ─┐ ┌─ Framework ─┐
│ - Page structure      │ │ - Data requirements│ │ - Page logic │
│ - Component hierarchy │ │ - API integration  │ │ - Routing    │
│ - Layout components   │ │ - Cache strategy   │ │ - Navigation │
└──────────────────────┘ └───────────────────┘ └─────────────┘
         ↓                        ↓                    ↓
         └──────────────── Integration ───────────────┘
                            ↓
Phase 3: Visual Polish (Styling Specialist)
- Apply design system
- Responsive behavior
- Animations/transitions
- Visual refinement
Quality Gate: Design specification met

Phase 4: Quality Assurance
┌─ Testing Specialist ──┐     ┌─ Accessibility ─┐
│ - E2E page tests      │     │ - WCAG audit    │
│ - Performance testing │     │ - Screen reader │
│ - User flow tests     │     │ - Keyboard nav  │
└──────────────────────┘     └─────────────────┘
         ↓                            ↓
         └───────── Final Review ─────┘
```

**Use Cases**:
- Building complex dashboards
- Creating multi-section pages
- Implementing feature-rich interfaces

**Coordination Requirements**:
- Multiple parallel work streams
- Clear integration checkpoints
- Final quality assurance phase

## Coordination Algorithm

```python
function coordinate_frontend_team(task):
  # Step 1: Identify required specialists
  required_specialists = identify_specialists(task)

  # Step 2: Map dependencies between specialists
  dependencies = map_dependencies(required_specialists, task.type)

  # Step 3: Topological sort for execution order
  execution_plan = topological_sort(dependencies)

  # Step 4: Execute with parallelism where possible
  results = []
  for wave in execution_plan:
    if len(wave) == 1:
      # Sequential execution
      result = execute_specialist(wave[0], task, results)
      results.append(result)
    else:
      # Parallel execution
      parallel_results = execute_parallel(wave, task, results)
      results.extend(parallel_results)

    # Quality gate check after each wave
    if not validate_quality_gate(results[-1]):
      return retry_or_escalate(task, results)

  # Step 5: Aggregate and return results
  return aggregate_frontend_results(results)

function map_dependencies(specialists, task_type):
  dependencies = {}

  if "component" in task_type:
    # Component development pipeline
    dependencies = {
      "component_architect": [],
      "framework": ["component_architect"],
      "styling": ["framework"],
      "testing": ["styling"],
      "accessibility": ["styling"]
    }
  elif "feature" in task_type:
    # Feature development pattern
    dependencies = {
      "framework": [],
      "styling": [],
      "state": ["framework", "styling"],
      "testing": ["state"]
    }
  elif "design_system" in task_type:
    # Design system pattern
    dependencies = {
      "uiux": [],
      "styling": ["uiux"],
      "components": ["styling"],
      "accessibility": ["components"],
      "testing": ["accessibility"]
    }

  return dependencies

function topological_sort(dependencies):
  # Convert dependencies to execution waves
  waves = []
  remaining = set(dependencies.keys())

  while remaining:
    # Find specialists with no pending dependencies
    wave = [s for s in remaining if all(dep not in remaining for dep in dependencies[s])]
    if not wave:
      raise CircularDependencyError()

    waves.append(wave)
    remaining -= set(wave)

  return waves
```

## Cross-Specialist Communication

Specialists communicate through shared artifacts:

### 1. Component Interfaces

**Passed from Component Architect to Framework Specialist**:
```typescript
interface ButtonProps {
  variant: 'primary' | 'secondary' | 'ghost';
  size: 'sm' | 'md' | 'lg';
  disabled?: boolean;
  onClick: () => void;
  children: React.ReactNode;
}
```

### 2. Styling Tokens

**Passed from Styling Specialist to Component Architect**:
```css
:root {
  --color-primary: #3b82f6;
  --color-secondary: #64748b;
  --spacing-sm: 0.5rem;
  --spacing-md: 1rem;
  --spacing-lg: 1.5rem;
}
```

### 3. State Structure

**Passed from State Management to Framework Specialist**:
```typescript
interface UserState {
  user: User | null;
  loading: boolean;
  error: Error | null;
}

const actions = {
  fetchUser: () => Promise<User>;
  updateUser: (user: User) => void;
  logout: () => void;
}
```

### 4. Accessibility Requirements

**Passed from Accessibility Specialist to all**:
```markdown
- All interactive elements must have aria-label
- Keyboard navigation: Tab, Enter, Escape
- Focus indicators visible on all focusable elements
- Screen reader announcements for dynamic content
- WCAG 2.1 AA contrast ratios required
```

## Quality Gates

Each coordination phase has quality gates:

### Gate 1: Architecture Review
- Component API documented
- Dependencies identified
- Reusability plan defined
- **Validator**: Component Architect + Domain Orchestrator

### Gate 2: Implementation Complete
- Component renders without errors
- Props and events work correctly
- Basic functionality operational
- **Validator**: Framework Specialist + Testing Specialist

### Gate 3: Design Specification Met
- Visual design matches mockup
- Responsive behavior correct
- Design tokens applied consistently
- **Validator**: Styling Specialist + UI/UX Specialist

### Gate 4: Test Coverage Adequate
- Unit tests cover core logic
- Integration tests validate workflows
- E2E tests cover user scenarios
- Coverage >= 80%
- **Validator**: Testing Specialist

### Gate 5: Accessibility Compliant
- WCAG 2.1 AA compliance achieved
- Screen reader compatible
- Keyboard navigation functional
- **Validator**: Accessibility Specialist

**Quality Gate Failure Response**:
1. Identify which gate failed
2. Report failure to Domain Orchestrator
3. Route back to specialist who failed gate
4. Provide specific remediation requirements
5. Re-validate after fixes

## Performance Optimization

### Parallel Execution Strategy

Execute specialists in parallel when no dependencies exist:

```python
function execute_parallel(specialists, task, prior_results):
  futures = []

  for specialist in specialists:
    # Spawn specialist in separate workspace
    future = spawn_specialist_async(specialist, task, prior_results)
    futures.append(future)

  # Wait for all specialists to complete
  results = wait_all(futures)

  # Validate all results
  for result in results:
    if not validate_result(result):
      handle_failure(result)

  return results
```

### Caching Strategy

Cache component designs and patterns for reuse:

```python
cache = ComponentCache()

function execute_specialist(specialist, task, prior_results):
  # Check cache first
  cache_key = generate_cache_key(specialist, task)
  cached_result = cache.get(cache_key)

  if cached_result and is_valid(cached_result):
    return cached_result

  # Execute specialist
  result = specialist.execute(task, prior_results)

  # Cache result
  cache.set(cache_key, result, ttl=3600)

  return result
```

### Early Feedback

Provide early feedback to prevent rework:

1. **Architectural Review**: Validate component design before implementation
2. **Design Review**: Validate styling approach before full implementation
3. **Integration Check**: Validate specialist outputs are compatible
4. **Incremental Validation**: Check quality gates incrementally, not just at end

## Reporting to Master Orchestrator

Frontend Domain Orchestrator reports team coordination to Master:

### Initial Plan Report

```json
{
  "task_id": "frontend-dashboard-123",
  "coordination_plan": {
    "pattern": "complex_page_development",
    "specialists": ["uiux", "component_architect", "framework", "state", "styling", "testing", "accessibility"],
    "execution_waves": [
      ["uiux"],
      ["component_architect", "state", "framework"],
      ["styling"],
      ["testing", "accessibility"]
    ],
    "estimated_duration": "4-6 hours"
  }
}
```

### Progress Updates

```json
{
  "task_id": "frontend-dashboard-123",
  "current_wave": 2,
  "completed_specialists": ["uiux", "component_architect"],
  "active_specialists": ["state", "framework"],
  "progress_percentage": 45,
  "blockers": []
}
```

### Completion Report

```json
{
  "task_id": "frontend-dashboard-123",
  "status": "complete",
  "all_specialists_completed": true,
  "quality_gates_passed": ["architecture", "implementation", "design", "testing", "accessibility"],
  "deliverables": {
    "components": ["Dashboard", "DashboardWidget", "DataCard"],
    "tests": "87% coverage",
    "accessibility": "WCAG 2.1 AA compliant"
  }
}
```

### Blocker Escalation

When frontend work is blocked by backend dependencies:

```json
{
  "task_id": "frontend-dashboard-123",
  "status": "blocked",
  "blocking_reason": "API endpoints not available",
  "required_from": "backend_domain_orchestrator",
  "required_endpoints": ["/api/dashboard/data", "/api/user/preferences"],
  "escalate_to_master": true
}
```

## Coordination Examples

### Example 1: Simple Component

**Task**: "Create a reusable Button component with variants"

**Selected Pattern**: Component Development Pipeline

**Execution**:
1. Component Architect: Design Button props and variants (30 min)
2. Framework Specialist: Implement Button in React (45 min)
3. Styling Specialist: Style with Tailwind variants (30 min)
4. Testing Specialist: Unit and integration tests (45 min)
5. Accessibility Specialist: ARIA and keyboard support (30 min)

**Total**: ~3 hours sequential

### Example 2: Feature with Parallel Work

**Task**: "Add user profile page with edit functionality"

**Selected Pattern**: Feature Development (Parallel)

**Execution**:
1. Framework + Styling in parallel (2 hours)
   - Framework: Profile component with edit mode
   - Styling: Profile layout and styling
2. State Management: Form state and API integration (1 hour)
3. Testing: E2E profile edit flow (1 hour)

**Total**: ~4 hours with parallelism (would be 5 hours sequential)

### Example 3: Complex Dashboard

**Task**: "Build analytics dashboard with multiple widgets"

**Selected Pattern**: Complex Page Development

**Execution**:
1. UI/UX: Dashboard layout and widget design (1.5 hours)
2. Component + State + Framework in parallel (3 hours)
   - Component: Widget structure and layout
   - State: Data fetching and caching
   - Framework: Dashboard logic and routing
3. Styling: Visual polish and responsive behavior (1.5 hours)
4. Testing + Accessibility in parallel (2 hours)
   - Testing: E2E dashboard tests
   - Accessibility: WCAG compliance audit

**Total**: ~8 hours with parallelism (would be 12 hours sequential)

## Summary

Frontend team coordination maximizes efficiency through:
- **Pattern-based workflows** for common scenarios
- **Parallel execution** where dependencies allow
- **Quality gates** ensure work quality
- **Clear communication** between specialists
- **Proactive reporting** to Master Orchestrator
- **Early feedback** prevents rework

These patterns enable the Frontend Domain Orchestrator to coordinate complex UI development with multiple specialists working together efficiently.
