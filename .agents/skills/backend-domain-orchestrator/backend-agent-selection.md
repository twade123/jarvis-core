# Backend Agent Selection Logic

Logic for selecting the correct backend specialist agent based on task characteristics. Analyze backend development tasks and route to appropriate specialists among the seven backend agent types.

## Backend Specialist Types and Selection Patterns

### 1. API Design & Implementation Specialist

**Primary Keywords:**
- Core: "API", "REST", "GraphQL", "endpoint", "route"
- HTTP: "GET", "POST", "PUT", "DELETE", "PATCH", "HTTP", "request", "response"
- Architecture: "RESTful", "REST API", "API design", "API architecture", "API versioning"
- Formats: "JSON", "XML", "API contract", "request body", "response body"

**Task Examples:**
- "Create REST endpoint for user data"
- "Design GraphQL schema for products"
- "Implement API versioning strategy"
- "Build API for mobile app"
- "Add pagination to API endpoint"

**When to Select:**
- Task mentions creating or modifying API endpoints
- Need to design API contracts or interfaces
- Implementing HTTP request/response handling
- Working on API architecture or patterns

**Coordinates With:**
- Database Specialist: API needs data access layer
- Auth Specialist: Protected endpoints require authentication
- Documentation Specialist: APIs need documentation
- Testing Specialist: APIs require integration tests

### 2. Database Architecture Specialist

**Primary Keywords:**
- SQL: "database", "SQL", "PostgreSQL", "MySQL", "SQLite", "schema", "table", "query"
- NoSQL: "MongoDB", "Redis", "NoSQL", "document database", "key-value store"
- Operations: "migration", "index", "query optimization", "ORM", "database design"
- Modeling: "data model", "entity", "relationship", "foreign key", "normalization"

**Task Examples:**
- "Design database schema for e-commerce"
- "Create PostgreSQL migration for new tables"
- "Optimize slow database queries"
- "Set up MongoDB collections"
- "Implement database caching with Redis"

**When to Select:**
- Task involves database schema design or modeling
- Need to create or modify database tables
- Optimizing database queries or performance
- Setting up database indexes or migrations
- Choosing between SQL and NoSQL solutions

**Coordinates With:**
- API Specialist: Database provides data layer for APIs
- Business Logic Specialist: Domain models map to database
- Microservices Specialist: Each service may need database
- Testing Specialist: Test databases and fixtures needed

### 3. Authentication/Authorization Specialist

**Primary Keywords:**
- Auth: "authentication", "authorization", "auth", "login", "logout", "signup"
- Tokens: "JWT", "token", "access token", "refresh token", "bearer token"
- OAuth: "OAuth", "OAuth2", "OpenID Connect", "SSO", "social login"
- Security: "password", "hash", "bcrypt", "session", "cookie", "permissions", "roles"
- Access: "RBAC", "role-based", "permission", "access control", "protected route"

**Task Examples:**
- "Implement JWT authentication"
- "Add OAuth login with Google"
- "Create user registration with password hashing"
- "Build role-based access control"
- "Implement session management"

**When to Select:**
- Task involves user authentication or authorization
- Need to implement login/logout functionality
- Working with tokens (JWT, OAuth)
- Designing permission systems or access control
- Securing API endpoints or routes

**Coordinates With:**
- API Specialist: Auth endpoints need API implementation
- Database Specialist: User credentials stored in database
- Testing Specialist: Security testing critical
- Documentation Specialist: Auth flows need clear documentation

### 4. Business Logic Specialist

**Primary Keywords:**
- Domain: "business logic", "business rules", "domain model", "domain logic"
- Processing: "validation", "processing", "workflow", "state machine", "rules engine"
- Operations: "calculate", "compute", "aggregate", "transform", "process data"
- Patterns: "service layer", "use case", "domain service", "value object"

**Task Examples:**
- "Implement order total calculation"
- "Add business validation rules"
- "Create workflow for approval process"
- "Build discount calculation logic"
- "Implement inventory management rules"

**When to Select:**
- Task involves business rules or domain logic
- Need to implement data validation beyond simple checks
- Working on workflows or state machines
- Calculating derived values or aggregations
- Implementing business processes or operations

**Coordinates With:**
- API Specialist: Business logic exposed through API
- Database Specialist: Domain models persist to database
- Testing Specialist: Business rules need thorough testing
- Microservices Specialist: Business logic distributed across services

### 5. Microservices Architecture Specialist

**Primary Keywords:**
- Architecture: "microservice", "microservices", "service", "distributed system"
- Communication: "message queue", "event driven", "service mesh", "inter-service"
- Patterns: "saga", "CQRS", "event sourcing", "API gateway", "service discovery"
- Technologies: "Docker", "Kubernetes", "RabbitMQ", "Kafka", "gRPC", "circuit breaker"

**Task Examples:**
- "Design microservices architecture"
- "Implement event-driven communication"
- "Set up service discovery"
- "Create API gateway for microservices"
- "Build saga pattern for distributed transactions"

**When to Select:**
- Task involves microservices architecture or design
- Need to implement inter-service communication
- Working with message queues or event systems
- Designing service boundaries or contracts
- Building distributed system patterns

**Coordinates With:**
- API Specialist: Services expose APIs
- Database Specialist: Per-service databases
- Business Logic Specialist: Business logic distributed
- Infrastructure Specialist: Deployment and orchestration (via Master)
- Testing Specialist: Integration testing across services

### 6. Backend Testing Specialist

**Primary Keywords:**
- Testing: "test", "testing", "unit test", "integration test", "E2E test"
- Backend: "API test", "database test", "backend test", "server test"
- Tools: "Jest", "pytest", "Mocha", "Chai", "Supertest", "test coverage"
- Patterns: "mock", "stub", "fixture", "test data", "test database"

**Task Examples:**
- "Write unit tests for business logic"
- "Create integration tests for API"
- "Test database migrations"
- "Add E2E tests for user flow"
- "Implement test fixtures and mocks"

**When to Select:**
- Task explicitly mentions testing backend code
- Need to write unit or integration tests
- Testing API endpoints or database operations
- Setting up test fixtures or mock data
- Measuring test coverage for backend

**Coordinates With:**
- All backend specialists: Testing validates their work
- API Specialist: API integration testing
- Database Specialist: Database testing and fixtures
- Auth Specialist: Security testing
- Business Logic Specialist: Unit testing business rules

### 7. API Documentation Specialist

**Primary Keywords:**
- Documentation: "documentation", "docs", "API docs", "API documentation"
- Specs: "OpenAPI", "Swagger", "API spec", "API reference", "API schema"
- Tools: "Swagger UI", "Postman", "API Blueprint", "RAML"
- Content: "usage example", "endpoint documentation", "API guide"

**Task Examples:**
- "Create OpenAPI specification"
- "Document API endpoints"
- "Generate Swagger UI"
- "Write API usage examples"
- "Update API reference documentation"

**When to Select:**
- Task involves documenting API endpoints
- Need to create OpenAPI/Swagger specifications
- Writing API usage examples or guides
- Generating API documentation
- Maintaining API reference materials

**Coordinates With:**
- API Specialist: Documenting API design and endpoints
- Auth Specialist: Documenting authentication flows
- Testing Specialist: Examples from test cases

## Multi-Specialist Scenarios

Complex backend tasks often require multiple specialists working together. Identify primary specialist and required collaborators:

### Scenario 1: User Registration System
**Task**: "Create user registration with email and password"

**Required Specialists:**
1. Auth Specialist (lead): Design authentication strategy, password hashing
2. Database Specialist: Create users table, store credentials
3. API Specialist: Implement /register endpoint
4. Testing Specialist: Write registration tests
5. Documentation Specialist: Document registration API

**Coordination Flow**: Auth → Database → API → Testing → Documentation

**Why Multiple**: Authentication requires secure storage (database), exposed endpoint (API), validation (testing), and usage guidance (documentation).

### Scenario 2: E-Commerce Order System
**Task**: "Build order processing system with payment integration"

**Required Specialists:**
1. Business Logic Specialist (lead): Order workflow, inventory, pricing
2. Database Specialist: Orders, products, inventory tables
3. API Specialist: Order creation, status endpoints
4. Auth Specialist: Protect order endpoints
5. Testing Specialist: Test order flows

**Coordination Flow**: Business Logic + Database (parallel) → API → Auth → Testing

**Why Multiple**: Orders involve complex business rules (business logic), data persistence (database), API exposure (API), security (auth), and validation (testing).

### Scenario 3: Payment Processing Flow
**Task**: "Implement payment processing with Stripe"

**Required Specialists:**
1. API Specialist (lead): Stripe API integration, webhook endpoints
2. Business Logic Specialist: Payment validation, order updates
3. Database Specialist: Payment transactions table
4. Auth Specialist: Secure payment endpoints
5. Testing Specialist: Payment flow testing

**Coordination Flow**: API → Business Logic → Database → Auth → Testing

**Why Multiple**: Payment processing requires external API integration (API), business validation (business logic), transaction recording (database), security (auth), and comprehensive testing.

### Scenario 4: Microservices E-Commerce Platform
**Task**: "Design microservices architecture for e-commerce platform"

**Required Specialists:**
1. Microservices Specialist (lead): Service boundaries, communication patterns
2. API Specialist: Service APIs and gateway
3. Database Specialist: Per-service databases
4. Business Logic Specialist: Business logic distribution
5. Auth Specialist: Distributed authentication
6. Testing Specialist: Integration testing

**Coordination Flow**: Microservices → API → Database + Business Logic (parallel) → Auth → Testing

**Why Multiple**: Microservices require architectural design (microservices), service APIs (API), data isolation (database), distributed logic (business logic), security (auth), and integration testing.

### Scenario 5: Analytics Dashboard Backend
**Task**: "Create backend API for analytics dashboard with real-time metrics"

**Required Specialists:**
1. API Specialist (lead): REST API for dashboard data
2. Database Specialist: Optimize queries for analytics
3. Business Logic Specialist: Metrics calculation and aggregation
4. Testing Specialist: Performance testing
5. Documentation Specialist: API documentation

**Coordination Flow**: Database (optimization) → Business Logic (calculations) → API (exposure) → Testing + Documentation (parallel)

**Why Multiple**: Analytics require query optimization (database), metric calculations (business logic), API exposure (API), performance validation (testing), and clear documentation.

## Technology Detection

Detect project architecture and technology choices to guide specialist selection:

### SQL vs NoSQL Detection
**SQL Indicators:**
- Project uses: PostgreSQL, MySQL, SQLite
- Code references: migrations, foreign keys, joins, transactions
- Need: ACID guarantees, complex relationships, structured data

**NoSQL Indicators:**
- Project uses: MongoDB, Redis, DynamoDB, Cassandra
- Code references: collections, documents, key-value, distributed
- Need: Flexibility, scalability, unstructured data

**Selection Impact**: Route database tasks to specialist with matching SQL/NoSQL expertise.

### REST vs GraphQL Detection
**REST Indicators:**
- Code references: `/api/`, HTTP methods, status codes, RESTful routes
- Multiple endpoints for different resources
- Traditional request/response patterns

**GraphQL Indicators:**
- Code references: `graphql`, resolvers, queries, mutations, schemas
- Single endpoint with query language
- Type system and introspection

**Selection Impact**: Route API tasks to specialist with matching REST/GraphQL expertise.

### Monolith vs Microservices Detection
**Monolith Indicators:**
- Single codebase, shared database
- Direct function calls between modules
- Simpler deployment (single service)

**Microservices Indicators:**
- Multiple services/repos, separate databases
- Message queues, event systems, service discovery
- Docker, Kubernetes, distributed deployment

**Selection Impact**: Choose Microservices Specialist for distributed architecture, Business Logic Specialist for monolith.

## Selection Algorithm

Scoring algorithm to select the best backend specialist for a task:

```python
function score_backend_specialist(task, specialist):
    # Keyword matching (50% weight)
    keyword_score = count_keyword_matches(task.description, specialist.keywords)
    keyword_normalized = keyword_score / max_possible_keywords

    # Architecture fit (30% weight)
    architecture = detect_architecture(task, project)
    architecture_score = calculate_architecture_fit(specialist, architecture)

    # Dependency score (20% weight)
    required_specialists = identify_required_specialists(task)
    dependency_score = check_specialist_dependencies(specialist, required_specialists)

    # Weighted total
    total_score = (keyword_normalized * 0.5) + (architecture_score * 0.3) + (dependency_score * 0.2)

    return total_score

function select_backend_specialists(task):
    scores = []

    for specialist in backend_specialists:
        score = score_backend_specialist(task, specialist)
        scores.append((specialist, score))

    # Sort by score descending
    scores.sort(reverse=True)

    # Primary specialist is highest score
    primary = scores[0][0]

    # Collaborators are specialists above threshold (0.3)
    collaborators = [s for s, score in scores[1:] if score > 0.3]

    return {
        'primary': primary,
        'collaborators': collaborators,
        'coordination_pattern': determine_pattern(primary, collaborators)
    }
```

### Keyword Matching Detail

Count how many of specialist's keywords appear in task description:

```python
def count_keyword_matches(task_description, specialist_keywords):
    matches = 0
    task_lower = task_description.lower()

    for keyword in specialist_keywords:
        if keyword.lower() in task_lower:
            matches += 1

    return matches
```

### Architecture Fit Calculation

Determine if specialist matches project architecture:

```python
def calculate_architecture_fit(specialist, architecture):
    fit_scores = {
        'api': {
            'rest': 1.0,
            'graphql': 1.0,
            'monolith': 0.8,
            'microservices': 0.8
        },
        'database': {
            'sql': 1.0,
            'nosql': 1.0,
            'monolith': 1.0,
            'microservices': 0.9
        },
        'microservices': {
            'microservices': 1.0,
            'distributed': 1.0,
            'monolith': 0.2
        },
        # ... other specialists
    }

    return fit_scores.get(specialist.type, {}).get(architecture.type, 0.5)
```

### Dependency Score Calculation

Check if specialist is needed based on task dependencies:

```python
def check_specialist_dependencies(specialist, required_specialists):
    # If specialist is in required list, high score
    if specialist in required_specialists:
        return 1.0

    # If specialist commonly works with required specialists, medium score
    common_collaborations = get_collaboration_frequency(specialist, required_specialists)
    if common_collaborations > 0.5:
        return 0.7

    # Otherwise low score
    return 0.3
```

## Selection Examples

### Example 1: Simple API Task

**Task**: "Create GET endpoint to retrieve user profile"

**Analysis**:
- Keywords: "endpoint", "GET", "user"
- Architecture: REST API (detected)
- Dependencies: Database (user data), possibly Auth (protected endpoint)

**Scoring**:
- API Specialist: 0.85 (high keyword match, perfect REST fit)
- Database Specialist: 0.45 (user data dependency)
- Auth Specialist: 0.35 (might need protection)

**Selection**: API Specialist (primary), Database + Auth (collaborators)

### Example 2: Complex Business Logic

**Task**: "Implement order discount calculation with multiple rules"

**Analysis**:
- Keywords: "calculation", "rules", "order"
- Architecture: Monolith (detected)
- Dependencies: Database (order data), API (expose calculation)

**Scoring**:
- Business Logic Specialist: 0.90 (perfect fit for rules/calculation)
- Database Specialist: 0.50 (order data access)
- API Specialist: 0.40 (expose calculation)

**Selection**: Business Logic Specialist (primary), Database + API (collaborators)

### Example 3: Microservices Architecture

**Task**: "Design event-driven communication between order and inventory services"

**Analysis**:
- Keywords: "event-driven", "services", "communication"
- Architecture: Microservices (detected)
- Dependencies: API (service interfaces), Message Queue (events)

**Scoring**:
- Microservices Specialist: 0.95 (perfect match for microservices)
- API Specialist: 0.55 (service APIs)
- Business Logic Specialist: 0.40 (service logic)

**Selection**: Microservices Specialist (primary), API + Business Logic (collaborators)
