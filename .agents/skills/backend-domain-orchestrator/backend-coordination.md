# Backend Team Coordination Patterns

Patterns for coordinating multiple backend specialist agents when working on complex server-side systems. Define workflows, quality gates, communication protocols, and coordination algorithms for backend team collaboration.

## Common Coordination Patterns

Backend development often requires multiple specialists working in sequence or parallel. Use these proven coordination patterns for efficient team orchestration.

### Pattern 1: API Development Pipeline

**Use When**: Building new API endpoints with full implementation stack

**Flow**: API (design) → Database (schema) → Business Logic (implement) → Testing (verify) → Documentation (document)

**Characteristics**:
- Sequential workflow with quality gates
- Foundation-first approach (design before implementation)
- Each stage validates previous work
- Clear handoff points between specialists

**Steps**:
1. **API Specialist**: Design endpoint contract (route, methods, request/response schemas)
2. **Quality Gate**: Validate API design follows REST/GraphQL best practices
3. **Database Specialist**: Create schema for data persistence
4. **Quality Gate**: Validate schema supports API requirements
5. **Business Logic Specialist**: Implement endpoint logic using database
6. **Quality Gate**: Validate business rules implemented correctly
7. **Testing Specialist**: Write unit and integration tests
8. **Quality Gate**: Verify 80%+ test coverage, all tests pass
9. **Documentation Specialist**: Document API endpoint with examples
10. **Quality Gate**: Validate documentation completeness

**Example**: "Create POST /api/users endpoint for user registration"
- API: Define request body (email, password), response (user object, token)
- Database: Create users table with email (unique), password_hash, timestamps
- Business Logic: Validate email format, hash password, create user record
- Testing: Test validation, successful registration, duplicate email handling
- Documentation: Document endpoint, request/response formats, error codes

**Benefits**: Systematic approach prevents rework, ensures quality at each stage

### Pattern 2: Feature Development

**Use When**: Implementing features with parallel data and logic work

**Flow**: Database (model) + Business Logic (rules) → API (endpoints) → Testing (verify)

**Characteristics**:
- Parallel work on data model and business rules
- Integrate at API layer
- Faster than sequential for independent work
- Requires coordination checkpoint before API

**Steps**:
1. **Parallel Phase**:
   - **Database Specialist**: Design data model and schema
   - **Business Logic Specialist**: Define business rules and validations
   - **Coordination Point**: Share models between specialists
2. **Quality Gate**: Validate data model and rules alignment
3. **API Specialist**: Implement endpoints using database and logic
4. **Quality Gate**: Validate API exposes all required functionality
5. **Testing Specialist**: Test complete feature flow
6. **Quality Gate**: Verify integration tests pass

**Example**: "Implement shopping cart feature"
- Database: Create cart_items table (product_id, quantity, user_id)
- Business Logic: Cart operations (add, remove, update), price calculation
- API: Expose /api/cart endpoints (GET, POST, PUT, DELETE)
- Testing: Test cart operations, edge cases, concurrent updates

**Benefits**: Parallel work speeds development, integration at API provides natural checkpoint

### Pattern 3: Microservices Development

**Use When**: Building or extending microservices architecture

**Flow**: Microservices (architecture) → API (service interfaces) → Database (per-service) → Business Logic (service logic) → Testing (integration)

**Characteristics**:
- Service-by-service coordination
- Focus on service boundaries and contracts
- Per-service database design (database per service pattern)
- Integration testing critical for inter-service communication

**Steps**:
1. **Microservices Specialist**: Design service boundaries and communication patterns
2. **Quality Gate**: Validate service design follows bounded context principles
3. **API Specialist**: Define service APIs and contracts (REST/gRPC)
4. **Quality Gate**: Validate API contracts are clear and versioned
5. **Per-Service Development (parallel for each service)**:
   - **Database Specialist**: Design service-specific database
   - **Business Logic Specialist**: Implement service logic
   - **Quality Gate**: Service logic completed
6. **Testing Specialist**: Write integration tests for inter-service communication
7. **Quality Gate**: Validate all service interactions work correctly

**Example**: "Build order processing system with three microservices"
- Microservices: Design orders-service, inventory-service, payments-service
- API: Define service contracts (REST APIs + message queue events)
- Database: orders DB (PostgreSQL), inventory DB (PostgreSQL), payments DB (separate)
- Business Logic: Order workflow, inventory checks, payment processing
- Testing: Test service communication, event handling, failure scenarios

**Benefits**: Clear service boundaries, independent deployment, scalability

### Pattern 4: Authentication Integration

**Use When**: Adding authentication/authorization to existing or new system

**Flow**: Auth (strategy) → Database (users) → API (auth endpoints) → Testing (security) → Documentation (auth flow)

**Characteristics**:
- Security-first approach
- Cross-cutting concern (affects all protected endpoints)
- Comprehensive testing critical
- Clear documentation essential for adoption

**Steps**:
1. **Auth Specialist**: Design authentication strategy (JWT, OAuth, sessions)
2. **Quality Gate**: Validate auth strategy meets security requirements
3. **Database Specialist**: Create users, tokens, permissions tables
4. **Quality Gate**: Validate schema supports auth requirements (password hashing, token storage)
5. **API Specialist**: Implement auth endpoints (/login, /register, /refresh, /logout)
6. **Quality Gate**: Validate endpoints follow security best practices
7. **Testing Specialist**: Write security tests (auth flows, token validation, permission checks)
8. **Quality Gate**: Verify comprehensive security test coverage
9. **Documentation Specialist**: Document auth flows, token usage, permission model
10. **Quality Gate**: Validate documentation clarity for developers

**Example**: "Implement JWT authentication with role-based access control"
- Auth: JWT strategy with access/refresh tokens, RBAC with roles table
- Database: users (email, password_hash), roles (name), user_roles (junction)
- API: POST /login (returns tokens), POST /refresh, POST /register, middleware for protected routes
- Testing: Test login flow, token validation, refresh, role checks, unauthorized access
- Documentation: Auth flow diagram, token format, role permissions, integration guide

**Benefits**: Security-first approach ensures no gaps, comprehensive testing prevents vulnerabilities

## Advanced Coordination Patterns

### Pattern 5: Database-First Refactoring

**Use When**: Optimizing existing system with database changes

**Flow**: Database (optimize schema) → Business Logic (update queries) → API (adjust endpoints) → Testing (verify)

**Characteristics**:
- Backwards compatibility consideration
- Migration strategy critical
- Requires versioning for breaking changes

**Example**: "Optimize product catalog with new indexing strategy"

### Pattern 6: Event-Driven Integration

**Use When**: Adding event-driven communication to system

**Flow**: Microservices (event design) → API (event publishers/subscribers) → Business Logic (event handlers) → Testing (event flows)

**Characteristics**:
- Asynchronous communication
- Event schema design critical
- Testing requires event simulation

**Example**: "Add event notifications for order status changes"

## Coordination Algorithm

Algorithm for determining coordination pattern and specialist orchestration:

```python
function coordinate_backend_team(task):
    # Identify required specialists
    required_specialists = identify_specialists(task)

    # Detect project architecture
    architecture = detect_architecture(task.project)

    # Select coordination pattern
    if architecture == MICROSERVICES:
        pattern = coordinate_microservices(required_specialists, task)
    elif task.type == AUTHENTICATION:
        pattern = coordinate_authentication(required_specialists, task)
    elif len(required_specialists) >= 4:
        pattern = coordinate_api_pipeline(required_specialists, task)
    else:
        pattern = coordinate_feature_development(required_specialists, task)

    return pattern

function coordinate_microservices(specialists, task):
    # Microservices coordination pattern
    steps = [
        {
            'stage': 'Architecture Design',
            'specialists': [specialists.microservices],
            'parallel': False
        },
        {
            'stage': 'Service APIs',
            'specialists': [specialists.api],
            'parallel': False
        },
        {
            'stage': 'Per-Service Implementation',
            'specialists': [specialists.database, specialists.business_logic],
            'parallel': True  # Each service developed in parallel
        },
        {
            'stage': 'Integration Testing',
            'specialists': [specialists.testing],
            'parallel': False
        }
    ]

    return {
        'pattern': 'microservices_development',
        'steps': steps,
        'quality_gates': define_microservices_quality_gates()
    }

function coordinate_authentication(specialists, task):
    # Authentication integration pattern
    steps = [
        {
            'stage': 'Auth Strategy',
            'specialists': [specialists.auth],
            'parallel': False
        },
        {
            'stage': 'User Storage',
            'specialists': [specialists.database],
            'parallel': False
        },
        {
            'stage': 'Auth Endpoints',
            'specialists': [specialists.api],
            'parallel': False
        },
        {
            'stage': 'Security Testing + Documentation',
            'specialists': [specialists.testing, specialists.documentation],
            'parallel': True
        }
    ]

    return {
        'pattern': 'authentication_integration',
        'steps': steps,
        'quality_gates': define_auth_quality_gates()
    }

function coordinate_api_pipeline(specialists, task):
    # Full API development pipeline
    steps = [
        {
            'stage': 'API Design',
            'specialists': [specialists.api],
            'parallel': False
        },
        {
            'stage': 'Database Schema',
            'specialists': [specialists.database],
            'parallel': False
        },
        {
            'stage': 'Business Logic',
            'specialists': [specialists.business_logic],
            'parallel': False
        },
        {
            'stage': 'Testing + Documentation',
            'specialists': [specialists.testing, specialists.documentation],
            'parallel': True
        }
    ]

    return {
        'pattern': 'api_development_pipeline',
        'steps': steps,
        'quality_gates': define_api_quality_gates()
    }

function coordinate_feature_development(specialists, task):
    # Feature development with parallel data/logic
    steps = [
        {
            'stage': 'Data Model + Business Rules',
            'specialists': [specialists.database, specialists.business_logic],
            'parallel': True
        },
        {
            'stage': 'API Implementation',
            'specialists': [specialists.api],
            'parallel': False
        },
        {
            'stage': 'Testing',
            'specialists': [specialists.testing],
            'parallel': False
        }
    ]

    return {
        'pattern': 'feature_development',
        'steps': steps,
        'quality_gates': define_feature_quality_gates()
    }
```

## Cross-Specialist Communication

Backend specialists need to share information and artifacts during collaboration:

### Database → API Communication
- **Share**: Database schema, table structures, column types, relationships
- **Format**: SQL DDL, ORM models, ER diagrams
- **Purpose**: API specialist needs to understand data structure for queries

### API → Business Logic Communication
- **Share**: API contracts, endpoint specifications, request/response schemas
- **Format**: OpenAPI specs, GraphQL schemas, type definitions
- **Purpose**: Business logic implements contract requirements

### Auth → API Communication
- **Share**: Authentication requirements, protected endpoints list, permission model
- **Format**: Auth middleware configuration, permission mappings
- **Purpose**: API secures endpoints with proper auth checks

### Business Logic → Database Communication
- **Share**: Domain models, entity relationships, query patterns
- **Format**: ORM models, repository interfaces, query specifications
- **Purpose**: Database optimizes schema for business logic access patterns

### Testing → All Specialists Communication
- **Share**: Test results, coverage reports, identified issues
- **Format**: Test reports, coverage metrics, issue tickets
- **Purpose**: All specialists need feedback on their work quality

## Quality Gates

Quality gates ensure each stage meets requirements before proceeding:

### Database Schema Quality Gate
- Schema supports all API requirements
- Proper indexes for expected queries
- Foreign keys enforce referential integrity
- Migrations are reversible
- No SQL injection vulnerabilities

### API Design Quality Gate
- Follows REST/GraphQL best practices
- Consistent naming conventions
- Proper HTTP status codes
- Versioning strategy defined
- Error responses standardized

### Business Logic Quality Gate
- All business rules implemented
- Input validation comprehensive
- Error handling robust
- No hardcoded values (use config)
- Follows SOLID principles

### Testing Quality Gate
- 80%+ code coverage
- All critical paths tested
- Edge cases covered
- Integration tests pass
- Security tests pass (for auth)

### Documentation Quality Gate
- All endpoints documented
- Request/response examples provided
- Error codes explained
- Authentication documented
- Code examples included

## Performance Optimization

Optimize backend team coordination for efficiency:

### Parallel Execution
- Execute independent tasks in parallel where possible
- Database schema + Business rules (Pattern 2)
- Testing + Documentation (most patterns)
- Per-service development (Pattern 3)

### Early Validation
- Validate database schema early to catch issues
- API design review before implementation
- Architecture review for microservices

### Incremental Delivery
- Deliver API endpoints incrementally
- Test each endpoint before moving to next
- Document as you build, not at end

### Reuse Patterns
- Use established patterns for common tasks
- Database schemas for similar domains
- API structures for CRUD operations
- Auth middleware for protected endpoints

## Reporting to Master Orchestrator

Backend Domain Orchestrator reports backend coordination status to Master:

### Coordination Plan Report
When coordination pattern selected, report to Master:
```
Backend coordination plan: API Development Pipeline
Specialists: API, Database, Business Logic, Testing, Documentation
Estimated stages: 5
Current stage: API Design (1/5)
```

### Specialist Progress Report
As specialists work, aggregate and report progress:
```
Backend progress: 60%
- API Design: Complete
- Database Schema: Complete
- Business Logic: In Progress (60%)
- Testing: Queued
- Documentation: Queued
```

### Blocker Report
When cross-domain coordination needed, report to Master:
```
Backend blocker: Frontend dependency
Need: Frontend team to define required API endpoints
Impact: API design stage waiting for frontend requirements
Request: Master coordinate with Frontend Domain Orchestrator
```

### Completion Report
When backend coordination complete, report to Master:
```
Backend complete: User authentication system
Specialists: Auth, Database, API, Testing, Documentation
Quality gates: All passed
Deliverables: JWT auth, user management API, comprehensive tests, API docs
```

## Example Coordination Scenarios

### Scenario 1: E-Commerce Checkout Flow

**Task**: "Implement checkout process with payment and inventory validation"

**Selected Pattern**: Feature Development (parallel data/logic)

**Coordination**:
1. **Parallel Phase**:
   - Database: Create orders, order_items, payments tables
   - Business Logic: Checkout validation (inventory check, price calculation, payment validation)
2. **API Phase**:
   - API: POST /checkout endpoint, integrate database + business logic
3. **Testing Phase**:
   - Testing: Test checkout flow, payment validation, inventory deduction, concurrent orders

**Communication**:
- Database → Business Logic: Share order schema, inventory schema
- Business Logic → API: Share checkout validation functions
- API → Testing: Share endpoint specification

**Report to Master**: "Backend: Checkout implementation 75% - database ready, business logic complete, API integration in progress"

### Scenario 2: Multi-Service Order System

**Task**: "Build distributed order processing with order, inventory, and payment services"

**Selected Pattern**: Microservices Development

**Coordination**:
1. **Architecture Phase**:
   - Microservices: Design three services, define service boundaries, choose message queue
2. **API Phase**:
   - API: Define service APIs (REST) and events (RabbitMQ)
3. **Per-Service Phase (parallel)**:
   - Database: Design per-service databases (orders, inventory, payments)
   - Business Logic: Implement service logic for each service
4. **Integration Phase**:
   - Testing: Test inter-service communication, event flows, failure handling

**Communication**:
- Microservices → API: Share service boundaries and communication patterns
- API → Database: Share service-specific data requirements
- All → Testing: Share service contracts for integration tests

**Report to Master**: "Backend: Microservices architecture 50% - services designed, APIs defined, per-service implementation in progress (orders complete, inventory 60%, payments 40%)"
