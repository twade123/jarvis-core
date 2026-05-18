# Frontend Agent Selection Logic

## Overview

This document defines the selection algorithm for choosing the correct frontend specialist agent based on task characteristics. The Frontend Domain Orchestrator uses this logic to route frontend development tasks to the most appropriate specialist or coordinate teams of specialists.

## Selection Algorithm

The agent selection process follows these steps:

```
Input: Frontend task description (text, keywords, context)
Output: Selected specialist(s) with confidence scores

Process:
1. Extract keywords and technologies from task description
2. Score each specialist type based on keyword matches
3. Apply technology alignment scoring
4. Apply project context scoring
5. Select specialist(s) with highest scores
6. Determine if multi-specialist coordination is needed
```

## Specialist Selection Patterns

### 1. Framework Specialist (React/Vue/Angular)

**Primary Keywords**:
- React, Vue, Angular, Svelte, Next.js, Nuxt, SvelteKit
- component lifecycle, hooks, JSX, template, directive
- useState, useEffect, computed, reactive
- componentDidMount, render, setup, composition API

**Technology Indicators**:
- File extensions: `.jsx`, `.tsx`, `.vue`, `.svelte`
- Imports: `from 'react'`, `from 'vue'`, `from '@angular/core'`
- Package dependencies in package.json

**Task Types**:
- Core framework implementation
- Component structure and patterns
- Framework-specific APIs and methods
- Component lifecycle management
- Props and event handling
- Framework routing and navigation

**Coordinates With**:
- Component Architect (for structure)
- State Management (for data)
- Testing Specialist (for tests)

**Selection Confidence**: HIGH when framework name appears in task

**Example Tasks**:
- "Create React component with hooks"
- "Implement Vue composition API logic"
- "Build Angular service with dependency injection"

### 2. Styling Specialist (CSS/Tailwind/Styled)

**Primary Keywords**:
- CSS, SCSS, Sass, Less, Stylus
- Tailwind, Bootstrap, Material-UI, Chakra UI
- Styled Components, Emotion, CSS Modules
- flexbox, grid, layout, responsive
- design system, theme, styling, visual

**Technology Indicators**:
- File extensions: `.css`, `.scss`, `.sass`, `.less`
- Style libraries in dependencies
- CSS-in-JS patterns

**Task Types**:
- Visual styling implementation
- Design system architecture
- Responsive layout design
- CSS optimization and performance
- Design token implementation
- Theme management

**Coordinates With**:
- UI/UX Specialist (for design translation)
- Component Architect (for component styling)
- Accessibility Specialist (for visual accessibility)

**Selection Confidence**: HIGH when styling technology explicitly mentioned

**Example Tasks**:
- "Style login form with Tailwind"
- "Create responsive navigation with CSS Grid"
- "Implement design system tokens with Styled Components"

### 3. UI/UX Specialist

**Primary Keywords**:
- UI, UX, design, user experience, user interface
- interaction, animation, transition
- wireframe, mockup, prototype, Figma
- user flow, journey, persona
- usability, user-centered

**Technology Indicators**:
- Design file references (Figma, Sketch)
- Animation libraries (Framer Motion, GSAP)
- Interaction patterns

**Task Types**:
- Design translation to code
- User experience optimization
- Interaction pattern implementation
- Animation and transition design
- User flow implementation
- Responsive design adaptation

**Coordinates With**:
- Styling Specialist (for visual implementation)
- Accessibility Specialist (for inclusive design)
- Framework Specialist (for interaction logic)

**Selection Confidence**: HIGH when "design", "UX", or "user experience" mentioned

**Example Tasks**:
- "Implement Figma design for dashboard"
- "Create smooth page transition animations"
- "Optimize user flow for checkout process"

### 4. Component Architect

**Primary Keywords**:
- component, architecture, structure, pattern
- composition, reusable, modular
- design pattern, architectural pattern
- component library, component system
- atomic design, component hierarchy

**Technology Indicators**:
- References to component patterns
- Mentions of architectural decisions
- Component library frameworks (Storybook)

**Task Types**:
- Component structure design
- Architectural decision-making
- Pattern implementation (Container/Presenter, HOC, Render Props)
- Component library architecture
- Reusability optimization
- Component composition strategies

**Coordinates With**:
- Framework Specialist (for implementation)
- State Management (for data architecture)
- Testing Specialist (for test structure)

**Selection Confidence**: HIGH when "architecture", "structure", or "pattern" emphasized

**Example Tasks**:
- "Design component hierarchy for form system"
- "Implement compound component pattern"
- "Architect reusable table component library"

### 5. State Management Specialist

**Primary Keywords**:
- state, Redux, Context, Zustand, MobX, Recoil
- store, reducer, action, dispatch
- global state, local state, shared state
- state management, state architecture
- data flow, flux pattern

**Technology Indicators**:
- State library imports
- State management file patterns
- Store configuration files

**Task Types**:
- State architecture design
- State management implementation
- Data flow optimization
- State synchronization
- Cache management
- Optimistic updates

**Coordinates With**:
- Framework Specialist (for integration)
- Component Architect (for state structure)
- Backend Specialist (for API state, via Master)

**Selection Confidence**: HIGH when state management library explicitly mentioned

**Example Tasks**:
- "Implement Redux store for user data"
- "Add Context API for theme switching"
- "Optimize state updates with Zustand"

### 6. Testing Specialist

**Primary Keywords**:
- test, testing, Jest, Vitest, Playwright, Cypress
- unit test, integration test, E2E test
- test coverage, test suite, test case
- Testing Library, enzyme
- mock, spy, stub, snapshot

**Technology Indicators**:
- Test file patterns (`.test.js`, `.spec.js`)
- Testing library imports
- Test configuration files

**Task Types**:
- Unit test implementation
- Integration test creation
- E2E scenario testing
- Test coverage improvement
- Test refactoring
- Test performance optimization

**Coordinates With**:
- Framework Specialist (for component tests)
- Component Architect (for structure tests)
- State Management (for state tests)

**Selection Confidence**: HIGH when "test" or testing framework mentioned

**Example Tasks**:
- "Write Jest tests for login component"
- "Create E2E tests with Playwright"
- "Increase test coverage to 80%"

### 7. Accessibility Specialist

**Primary Keywords**:
- accessibility, a11y, WCAG, ADA
- screen reader, ARIA, semantic HTML
- keyboard navigation, focus management
- alt text, label, role, aria-label
- inclusive design, accessible

**Technology Indicators**:
- ARIA attributes in code
- Accessibility testing tools
- WCAG compliance references

**Task Types**:
- Accessibility audit and compliance
- ARIA implementation
- Keyboard navigation implementation
- Screen reader optimization
- Semantic HTML refactoring
- Focus management

**Coordinates With**:
- UI/UX Specialist (for accessible design)
- Component Architect (for accessible structure)
- Testing Specialist (for a11y tests)

**Selection Confidence**: HIGH when "accessibility", "a11y", or "WCAG" mentioned

**Example Tasks**:
- "Add ARIA labels to navigation"
- "Implement keyboard navigation for modal"
- "Audit dashboard for WCAG 2.1 AA compliance"

## Multi-Specialist Scenarios

Many frontend tasks require multiple specialists working together:

### Scenario 1: Create Login Form
**Required Specialists**: Framework + Styling + Accessibility
**Workflow**:
1. Framework Specialist: Build form component with React
2. Styling Specialist: Style form with Tailwind
3. Accessibility Specialist: Add ARIA labels and keyboard support
**Parallel Execution**: Framework and Styling can work in parallel, then Accessibility audits

### Scenario 2: Build Data Table Component
**Required Specialists**: Framework + Component Architect + State + Testing
**Workflow**:
1. Component Architect: Design table component structure
2. Framework Specialist: Implement table with React
3. State Management: Handle sorting, filtering, pagination state
4. Testing Specialist: Write comprehensive tests
**Sequential with Parallel**: Architecture first, then Framework + State in parallel, then Testing

### Scenario 3: Implement Design System
**Required Specialists**: Styling + Component Architect + Accessibility
**Workflow**:
1. Styling Specialist: Create design tokens and theme
2. Component Architect: Design primitive component library
3. Styling Specialist: Style primitives
4. Accessibility Specialist: Audit for WCAG compliance
5. Testing Specialist: Document in Storybook with tests
**Mixed**: Tokens first, then Component + Styling collaborate, then Accessibility + Testing

### Scenario 4: Add User Dashboard
**Required Specialists**: Framework + UI/UX + State + Testing
**Workflow**:
1. UI/UX Specialist: Plan layout and user experience
2. Framework Specialist: Implement dashboard shell
3. State Management: Add data fetching and caching
4. UI/UX + Styling: Refine visual design
5. Testing Specialist: E2E tests for dashboard flows
**Complex Coordination**: Sequential → Parallel → Sequential pattern

## Selection Confidence Scoring

Calculate confidence score for each specialist:

```python
function score_frontend_specialist(task, specialist):
  # Keyword matching (50% weight)
  keyword_score = count_keyword_matches(task.description, specialist.keywords)
  keyword_weight = keyword_score / max_keywords * 0.5

  # Technology alignment (30% weight)
  tech_score = detect_technology_alignment(task.context, specialist.technologies)
  tech_weight = tech_score * 0.3

  # Project context (20% weight)
  context_score = check_recent_specialists(task.project_id, specialist.type)
  context_weight = context_score * 0.2

  # Total confidence
  total_score = keyword_weight + tech_weight + context_weight

  return total_score

# Selection threshold
if total_score >= 0.7:
  return SELECTED
elif total_score >= 0.4:
  return POSSIBLE
else:
  return NOT_SELECTED
```

### Scoring Factors

1. **Keyword Matching**: Direct keywords in task description
2. **Technology Alignment**: Technologies in project context
3. **Project Context**: Recently used specialists for this project

## Framework-Specific Routing

Detect framework from codebase and route appropriately:

### React Detection
- Indicators: `package.json` has `react`, `.jsx`/`.tsx` files, `import React`
- Route to: React-specialized Framework Specialist

### Vue Detection
- Indicators: `package.json` has `vue`, `.vue` files, `<template>` syntax
- Route to: Vue-specialized Framework Specialist

### Angular Detection
- Indicators: `package.json` has `@angular/core`, `.component.ts` files, decorators
- Route to: Angular-specialized Framework Specialist

### Framework Consistency
- Maintain framework consistency within a project
- Default to primary framework if detected
- Warn if mixing frameworks without explicit justification

## Fallback Patterns

When specialist selection is unclear:

### Ambiguous Tasks
- **Escalate to Master Orchestrator** for clarification
- Request more specific task description
- Ask for technology preference

### Default Routing
- **General frontend work** → Framework Specialist (most versatile)
- **Architectural decisions** → Component Architect
- **Design questions** → UI/UX Specialist

### Multi-Specialist Default
- When multiple specialists score similarly → Coordinate team
- When task is complex → Default to team approach
- When in doubt → Framework + Testing minimum

## Selection Output Format

```json
{
  "primary_specialist": "framework",
  "additional_specialists": ["styling", "accessibility"],
  "confidence_scores": {
    "framework": 0.85,
    "styling": 0.72,
    "accessibility": 0.68
  },
  "coordination_pattern": "sequential",
  "estimated_complexity": "medium",
  "rationale": "React component creation requires framework specialist primarily, with styling and accessibility support"
}
```

This selection output is used by the coordination module to orchestrate the frontend team.
