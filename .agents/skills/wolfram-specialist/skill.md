---
name: wolfram-specialist
description: Specialist agent with complete mastery of wolfram MCP tools. Handles computational queries, mathematical operations, factual lookups, and unit conversions using Wolfram Alpha with expertise in query optimization and result interpretation.
version: 1.0.0
category: mcp-specialist
author: Claude Code Agent Skills System
triggers:
  - "calculate"
  - "wolfram"
  - "compute"
  - "math query"
  - "unit conversion"
  - "solve equation"
  - "wolfram alpha"
capabilities:
  - mathematical_computation
  - factual_queries
  - unit_conversions
  - data_visualization
  - scientific_calculations
  - query_optimization
  - intent_classification
  - pod_filtering
mcp_server: wolfram
mcp_port: 8114
parent_orchestrator: mcp-domain-orchestrator
---

# Wolfram Specialist Agent

Expert agent for computational knowledge queries using Wolfram Alpha API with advanced intent classification and result optimization.

## MCP Overview

**Handler:** `handler_wolfram.py` (class-based: `WolframHandler`)
**Primary Class:** `WolframHandler`
**Port:** 8114
**API Integration:** Wolfram Alpha API (https://api.wolframalpha.com)

The Wolfram MCP provides sophisticated computational capabilities including mathematical operations, scientific calculations, unit conversions, factual queries, and data visualization through Wolfram Alpha's knowledge engine.

## Available Tools

### 1. query_wolfram_alpha (Primary Tool)

Core query method with full parameter control:

```python
def query_wolfram_alpha(
    query: str,                      # Required: Natural language query
    format_type: str = 'plaintext',  # 'plaintext', 'image', 'mathml'
    include_pods: List[str] = None,  # Specific pods to include
    exclude_pods: List[str] = None,  # Specific pods to exclude
    timeout: int = 30,               # Request timeout in seconds
    max_width: int = 500             # Maximum pixel width for images
) -> dict
```

**Supports:**
- Mathematical calculations and equations
- Scientific queries (physics, chemistry, biology)
- Unit and currency conversions
- Data analysis and statistics
- Knowledge queries (geography, history)
- Visual results (graphs, plots, diagrams)

**Returns:** Dictionary organized by pod types with subpod data

### 2. get_enhanced_result

Automatic pod prediction and intelligent filtering:

```python
def get_enhanced_result(
    query: str,
    auto_filter: bool = True  # Enable intelligent pod filtering
) -> dict
```

**Features:**
- Predicts likely pod types from query patterns
- Filters results to most relevant information
- Optimizes for faster, focused responses
- Includes prediction metadata

**Best for:** Complex queries where automatic relevance filtering helps

### 3. get_optimized_result

Intent-based query optimization:

```python
def get_optimized_result(
    query: str
) -> dict
```

**Optimization features:**
- Classifies query intent (mathematical, scientific, conversion, etc.)
- Maps intents to optimal pod types
- Combines intent analysis with pod prediction
- Returns optimization metadata

**Intent types supported:**
- Mathematical: equations, calculus, algebra, geometry
- Scientific: physics, chemistry, biology data
- Conversion: units, currency, measurements
- Financial: calculations, interest, economics
- Geographical: locations, distances, demographics
- Statistical: probability, distributions, data analysis

### 4. classify_query_intent

Analyze query intent for optimal processing:

```python
def classify_query_intent(
    query: str
) -> dict
```

**Returns:**
```json
{
  "primary_intent": "mathematical",
  "confidence": 3,
  "all_intents": {
    "mathematical": 3,
    "scientific": 1
  }
}
```

**Classification categories:**
- mathematical, conversion, scientific, financial, geographical, statistical, general

### 5. predict_pod_types

Predict optimal pod types for queries:

```python
def predict_pod_types(
    query: str
) -> List[str]
```

**Common pod types:**
- Result: Direct answers and calculations
- Plot: Graphs, charts, visualizations
- Solution: Step-by-step equation solutions
- Derivative: Calculus operations
- Properties: Scientific/mathematical properties
- Classification: Categorization and identification
- Unit information: Conversion details
- Basic statistics: Statistical analysis
- Geographic properties: Location data

### 6. filter_pods_by_type

Filter raw XML responses:

```python
def filter_pods_by_type(
    xml_content: str,
    desired_pod_types: List[str]
) -> List[pod]
```

**Use cases:**
- Extract only 'Result' pods for direct answers
- Get only 'Plot' pods for visualizations
- Combine specific pod types for targeted data

### 7. format_result_by_intent

Format results based on detected intent:

```python
def format_result_by_intent(
    result: dict,
    intent_type: str
) -> dict
```

**Intent-specific formatting:**
- Mathematical: Highlights equations, solutions, step-by-step work
- Conversion: Emphasizes converted values and unit details
- Scientific: Prioritizes properties, classifications, data
- Financial: Focuses on calculations and economic metrics
- Geographical: Highlights location data
- Statistical: Emphasizes statistical analysis

### 8. get_pod_titles

Debug tool for pod discovery:

```python
def get_pod_titles(
    query: str
) -> List[str]
```

**Returns:** List of available pod titles for query planning

### 9. get_simple_answer

Get just the direct answer:

```python
def get_simple_answer(
    query: str
) -> str
```

**Returns:** Plain text answer or None
- Fastest response for simple calculations
- No blob/image data or complex structures

## Query Types and Patterns

### Mathematical Queries

**Calculations:**
```python
query_wolfram_alpha("2+2")
query_wolfram_alpha("sqrt(144)")
query_wolfram_alpha("factorial(10)")
```

**Equations:**
```python
query_wolfram_alpha("solve x^2 - 4 = 0")
query_wolfram_alpha("x + y = 5, x - y = 1")
query_wolfram_alpha("quadratic formula")
```

**Calculus:**
```python
query_wolfram_alpha("integrate sin(x) from 0 to pi")
query_wolfram_alpha("derivative of x^2")
query_wolfram_alpha("limit of (sin x)/x as x->0")
```

**Plots:**
```python
query_wolfram_alpha("plot sin(x)", format_type='image')
query_wolfram_alpha("graph y = x^2 from -5 to 5", format_type='image')
```

### Scientific Queries

**Physics:**
```python
query_wolfram_alpha("speed of light")
query_wolfram_alpha("mass of electron")
query_wolfram_alpha("E=mc^2 where m=10kg")
```

**Chemistry:**
```python
query_wolfram_alpha("molecular weight of water")
query_wolfram_alpha("periodic table element 6")
query_wolfram_alpha("Lewis structure of methane")
```

**Biology:**
```python
query_wolfram_alpha("DNA structure")
query_wolfram_alpha("human genome size")
query_wolfram_alpha("cell division process")
```

### Conversion Queries

**Units:**
```python
query_wolfram_alpha("100 miles to kilometers")
query_wolfram_alpha("32 fahrenheit to celsius")
query_wolfram_alpha("5 feet 10 inches in meters")
```

**Currency:**
```python
query_wolfram_alpha("100 USD to EUR")
query_wolfram_alpha("convert 500 yen to dollars")
```

### Data Analysis Queries

**Statistics:**
```python
query_wolfram_alpha("mean of {1,2,3,4,5}")
query_wolfram_alpha("standard deviation of dataset")
query_wolfram_alpha("normal distribution mean=0 std=1")
```

**Probability:**
```python
query_wolfram_alpha("probability of rolling a 6")
query_wolfram_alpha("binomial distribution n=10 p=0.5")
```

### Knowledge Queries

**Geography:**
```python
query_wolfram_alpha("population of Tokyo")
query_wolfram_alpha("distance between NYC and LA")
query_wolfram_alpha("elevation of Mount Everest")
```

**History:**
```python
query_wolfram_alpha("when was Einstein born")
query_wolfram_alpha("World War 2 dates")
query_wolfram_alpha("presidents of the United States")
```

## Common Workflows

### 1. Mathematical Problem Solving

```python
# Step-by-step equation solving
result = get_optimized_result("solve x^3 - 2x^2 + x - 2 = 0")

# Extract solution
if 'Solution' in result:
    solutions = result['Solution']['subpods']
    for step in solutions:
        print(step.get('plaintext'))
```

### 2. Scientific Research

```python
# Get comprehensive scientific data
result = query_wolfram_alpha(
    "boiling point of water",
    include_pods=['Result', 'Properties', 'Classification']
)

# Extract properties
if 'Properties' in result:
    properties = result['Properties']['subpods']
    for prop in properties:
        print(prop.get('plaintext'))
```

### 3. Unit Conversion Pipeline

```python
# Multiple conversions
conversions = [
    "100 miles to km",
    "70 fahrenheit to celsius",
    "1 gallon to liters"
]

for query in conversions:
    result = get_simple_answer(query)
    print(f"{query}: {result}")
```

### 4. Data Visualization

```python
# Get plot with image
result = query_wolfram_alpha(
    "plot sin(x) + cos(x) from 0 to 2pi",
    format_type='image',
    max_width=800
)

# Extract image URL
if 'Plot' in result:
    image_url = result['Plot']['subpods'][0]['img']['src']
    print(f"Plot available at: {image_url}")
```

### 5. Intent-Optimized Queries

```python
# Classify intent first
intent = classify_query_intent("integrate e^x dx")
print(f"Detected intent: {intent['primary_intent']}")

# Get optimized result
result = get_optimized_result("integrate e^x dx")

# Format by intent
formatted = format_result_by_intent(result, intent['primary_intent'])
```

## Pod Types and Structure

### Pod Organization

Results are organized into pods (information categories):

```json
{
  "Input interpretation": {
    "id": "Input",
    "subpods": [
      {
        "plaintext": "x^2 - 4 = 0",
        "img": {...}
      }
    ]
  },
  "Result": {
    "id": "Result",
    "subpods": [
      {
        "plaintext": "x = -2 or x = 2",
        "img": {...}
      }
    ]
  },
  "Solution": {
    "id": "Solution",
    "subpods": [...]
  }
}
```

### Common Pod Types by Query Category

**Mathematical:**
- Input interpretation
- Result
- Root plot
- Number line
- Solution
- Derivative
- Integral

**Scientific:**
- Basic information
- Properties
- Classification
- Structure diagram
- Chemical structure

**Conversion:**
- Result
- Unit conversions
- Comparison
- Unit information

**Geographic:**
- Basic information
- Geographic properties
- Current result
- Map

**Statistical:**
- Result
- Basic statistics
- Distribution plots
- Probability

## Advanced Optimization Techniques

### 1. Query Intent Classification

```python
# Analyze query before execution
intent = classify_query_intent("what is the derivative of x^2")

if intent['primary_intent'] == 'mathematical':
    # Use math-focused pod types
    result = query_wolfram_alpha(
        "derivative of x^2",
        include_pods=['Derivative', 'Result', 'Plot']
    )
```

### 2. Pod Type Prediction

```python
# Predict relevant pods
predicted = predict_pod_types("solve differential equation dy/dx = y")
print(f"Predicted pods: {predicted}")

# Use predictions for focused query
result = query_wolfram_alpha(
    "solve differential equation dy/dx = y",
    include_pods=predicted[:5]  # Top 5 predictions
)
```

### 3. Progressive Pod Discovery

```python
# Workflow: Discover → Select → Query
# Step 1: Discover available pods
titles = get_pod_titles("population growth model")
print(f"Available pods: {titles}")

# Step 2: Select relevant pods
relevant_pods = [title for title in titles if 'statistics' in title.lower() or 'plot' in title.lower()]

# Step 3: Focused query
result = query_wolfram_alpha(
    "population growth model",
    include_pods=relevant_pods
)
```

### 4. Multi-Format Results

```python
# Get both plaintext and image results
text_result = query_wolfram_alpha("plot x^2", format_type='plaintext')
image_result = query_wolfram_alpha("plot x^2", format_type='image', max_width=800)

# Combine results
combined = {
    'text': text_result,
    'images': image_result
}
```

## Best Practices

### 1. Query Formulation

**Good queries:**
- Clear and specific: "integrate cos(x) dx"
- Natural language: "what is the speed of light"
- Well-formatted: "solve x^2 + 5x + 6 = 0"

**Avoid:**
- Vague queries: "tell me about math"
- Ambiguous context: "solve it"
- Improper formatting: "x2+5x+6=0" (missing ^)

### 2. Performance Optimization

**Reduce API calls:**
```python
# Use get_simple_answer for basic queries
answer = get_simple_answer("2+2")  # Fast, direct

# Use full query only when needed
result = query_wolfram_alpha("complex equation...")  # Comprehensive
```

**Pod filtering:**
```python
# Include only needed pods
result = query_wolfram_alpha(
    query,
    include_pods=['Result', 'Solution']  # Skip unnecessary pods
)
```

### 3. Error Handling

```python
try:
    result = query_wolfram_alpha("complex query")
    if not result:
        print("No results returned - check query format")
    elif not result.get('Result'):
        print("Query successful but no direct result")
except Exception as e:
    logger.error(f"Wolfram query failed: {e}")
```

### 4. Result Interpretation

```python
def extract_answer(result):
    """Extract the primary answer from results"""
    # Priority order: Result > first pod with plaintext
    if 'Result' in result:
        subpods = result['Result']['subpods']
        if subpods and 'plaintext' in subpods[0]:
            return subpods[0]['plaintext']

    # Fallback to first available plaintext
    for pod_title, pod_data in result.items():
        if pod_data['subpods']:
            first_subpod = pod_data['subpods'][0]
            if 'plaintext' in first_subpod:
                return first_subpod['plaintext']

    return None
```

### 5. Intent-Based Processing

```python
def smart_query(query_text):
    """Automatically optimize query based on intent"""
    # Classify intent
    intent = classify_query_intent(query_text)

    # Route based on intent
    if intent['primary_intent'] == 'mathematical':
        return get_optimized_result(query_text)
    elif intent['primary_intent'] == 'conversion':
        return get_simple_answer(query_text)  # Fast for conversions
    else:
        return get_enhanced_result(query_text)  # Auto-filter for others
```

## Usage Examples

### Example 1: Calculus Assistant

```python
calculus_queries = [
    "derivative of sin(x)",
    "integrate e^x dx",
    "limit of (1+1/n)^n as n->infinity"
]

for query in calculus_queries:
    result = get_optimized_result(query)
    if 'Result' in result:
        answer = result['Result']['subpods'][0]['plaintext']
        print(f"{query}: {answer}")
```

### Example 2: Physics Calculator

```python
# Complex physics calculation
query = "kinetic energy where mass=10kg and velocity=5m/s"
result = query_wolfram_alpha(
    query,
    include_pods=['Result', 'Formula']
)

print(f"Kinetic Energy: {result['Result']['subpods'][0]['plaintext']}")
if 'Formula' in result:
    print(f"Formula: {result['Formula']['subpods'][0]['plaintext']}")
```

### Example 3: Unit Conversion Tool

```python
def convert_units(value, from_unit, to_unit):
    query = f"{value} {from_unit} to {to_unit}"
    return get_simple_answer(query)

# Batch conversions
conversions = [
    (100, "miles", "kilometers"),
    (70, "fahrenheit", "celsius"),
    (1, "gallon", "liters")
]

for value, from_u, to_u in conversions:
    result = convert_units(value, from_u, to_u)
    print(f"{value} {from_u} = {result}")
```

### Example 4: Statistical Analysis

```python
# Dataset analysis
data = [10, 20, 30, 40, 50]
data_str = "{" + ",".join(map(str, data)) + "}"

# Multiple statistical measures
queries = [
    f"mean of {data_str}",
    f"standard deviation of {data_str}",
    f"median of {data_str}"
]

stats = {}
for query in queries:
    result = get_simple_answer(query)
    measure = query.split(" of ")[0]
    stats[measure] = result

print(f"Statistical analysis: {stats}")
```

### Example 5: Knowledge Base Integration

```python
# Multi-category knowledge queries
knowledge_queries = {
    'geography': "capital of France",
    'physics': "speed of light in vacuum",
    'chemistry': "atomic number of gold",
    'math': "value of pi to 10 digits"
}

knowledge_base = {}
for category, query in knowledge_queries.items():
    result = get_simple_answer(query)
    knowledge_base[category] = {
        'query': query,
        'answer': result
    }

# Knowledge base now populated with facts
for cat, data in knowledge_base.items():
    print(f"{cat.title()}: {data['answer']}")
```

### Example 6: Plot Generation Pipeline

```python
# Generate multiple plots
plot_queries = [
    "plot sin(x) from 0 to 2pi",
    "plot x^2 - 4",
    "plot normal distribution mean=0 std=1"
]

plots = []
for query in plot_queries:
    result = query_wolfram_alpha(query, format_type='image', max_width=600)
    if 'Plot' in result:
        img_data = result['Plot']['subpods'][0]['img']
        plots.append({
            'query': query,
            'url': img_data['src'],
            'alt': img_data['alt']
        })

print(f"Generated {len(plots)} plots")
```

## Integration with MCP Domain Orchestrator

The Wolfram Specialist is managed by the MCP Domain Orchestrator and activates on:

- Mathematical computation requests
- Scientific calculation queries
- Unit conversion operations
- Factual knowledge lookups
- Data visualization needs
- Research and analysis tasks

**Communication pattern:**
1. MCP Domain Orchestrator receives computational request
2. Classifies request intent and complexity
3. Activates Wolfram Specialist with optimized parameters
4. Wolfram Specialist executes appropriate query method
5. Returns structured results with metadata
6. Orchestrator formats results for user or downstream processing

**Optimization strategy:**
- Simple calculations → `get_simple_answer()` (fastest)
- Standard queries → `query_wolfram_alpha()` (comprehensive)
- Complex/ambiguous → `get_optimized_result()` (intent-based)
- Research queries → `get_enhanced_result()` (auto-filtered)
