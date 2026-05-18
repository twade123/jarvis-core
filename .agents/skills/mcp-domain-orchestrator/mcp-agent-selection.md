# MCP Agent Selection Logic

**Domain:** MCP Domain Orchestrator
**Purpose:** Comprehensive agent selection algorithms for routing tasks to the correct MCP specialist agents
**Agents Covered:** All 34 MCP agents (24 handlers + 10 standalone)

---

## Overview

Select the optimal MCP agent(s) for each task based on keyword matching, capability alignment, and confidence scoring. Handle single-agent selection, multi-agent coordination detection, and fallback escalation.

## Selection Algorithm

### Input-Output Contract

**Input:**
- Task description (user request as natural language)
- Task keywords (extracted from description)
- Task intent (what user wants to accomplish)
- Required capabilities (operations needed to fulfill task)
- Context (previous agent selections, user preferences)

**Output:**
- Selected MCP agent(s) with confidence scores
- Coordination flag (single-agent vs multi-agent)
- Reasoning (why this agent selected)
- Fallback recommendations (if primary selection fails)

### Algorithm Steps

**Step 1: Extract Task Features**
```
function extract_task_features(task_description):
  keywords = extract_keywords(task_description)
  intent = classify_intent(task_description)
  capabilities = identify_required_capabilities(task_description)

  return {
    keywords: keywords,
    intent: intent,
    capabilities: capabilities,
    coordination_indicators: check_multi_agent_indicators(keywords)
  }
```

**Step 2: Score All MCP Agents**
```
function score_all_agents(task_features):
  scores = []

  for mcp in all_34_mcps:
    keyword_score = calculate_keyword_overlap(task_features.keywords, mcp.keywords)
    capability_score = calculate_capability_match(task_features.capabilities, mcp.capabilities)

    # Weighted combination: keywords 60%, capabilities 40%
    total_score = (keyword_score * 0.6) + (capability_score * 0.4)

    scores.append({
      mcp: mcp,
      score: total_score,
      keyword_matches: keyword_score,
      capability_matches: capability_score
    })

  return sorted(scores, reverse=True)  # Highest score first
```

**Step 3: Make Selection Decision**
```
function select_agents(sorted_scores):
  best = sorted_scores[0]

  if best.score > 0.7:
    # High confidence: single best agent
    return {
      type: "single",
      agent: best.mcp,
      confidence: best.score,
      reasoning: f"Strong match on {best.keyword_matches} keywords and {best.capability_matches} capabilities"
    }

  elif best.score > 0.4:
    # Medium confidence: potential coordination needed
    top_candidates = sorted_scores[:3]
    return {
      type: "multi_candidate",
      agents: [c.mcp for c in top_candidates],
      confidence: best.score,
      reasoning: "Multiple possible agents, may need coordination or clarification"
    }

  else:
    # Low confidence: escalate to Master
    return {
      type: "escalate",
      agent: None,
      confidence: best.score,
      reasoning: "No strong MCP match, task may belong to different domain"
    }
```

---

## Handler MCP Selection Patterns (24 Agents)

### Communication & Productivity Handlers (7 Agents)

#### email Handler
**Keywords:** `email`, `send message`, `inbox`, `gmail`, `mail`, `compose`, `recipient`, `attachment`, `reply`, `forward`

**Capabilities:**
- Send email with attachments
- Read/search inbox with filters
- Manage folders (create, delete, organize)
- Reply to and forward messages

**Example Matches:**
- "Send email to john@example.com" → score: 0.95
- "Check my inbox for messages from Sarah" → score: 0.90
- "Forward that email to the team" → score: 0.85

**Conflicts:**
- `google_workspace` also handles Gmail → Prefer `email` for general email operations, `google_workspace` for Google-specific features

---

#### calendar Handler
**Keywords:** `calendar`, `event`, `meeting`, `schedule`, `appointment`, `reminder`, `book`, `availability`, `time slot`, `recurring`

**Capabilities:**
- Create calendar events with details
- List upcoming events with filters
- Update existing events
- Delete cancelled events
- Set reminders and notifications

**Example Matches:**
- "Add meeting to calendar for tomorrow at 2pm" → score: 0.95
- "Show me my schedule for next week" → score: 0.90
- "Cancel the 3pm appointment" → score: 0.85

**Conflicts:**
- `google_workspace` also has Google Calendar operations → Prefer `google_workspace` for Google-specific calendar features, `calendar` for general calendar operations

---

#### news Handler
**Keywords:** `news`, `headlines`, `articles`, `current events`, `latest`, `breaking`, `story`, `report`, `journalism`, `press`

**Capabilities:**
- Fetch latest news headlines
- Search news by topic/keyword
- Filter by category (tech, business, sports, etc.)
- Retrieve full article content

**Example Matches:**
- "Get latest tech news" → score: 0.95
- "Find articles about artificial intelligence" → score: 0.90
- "Show breaking news headlines" → score: 0.95

---

#### browser Handler
**Keywords:** `web`, `browse`, `search online`, `open url`, `website`, `scrape`, `extract`, `html`, `webpage`, `internet`

**Capabilities:**
- Open and navigate web pages
- Extract data from websites
- Web scraping and automation
- Search online content

**Example Matches:**
- "Open https://example.com" → score: 0.95
- "Search Google for Python tutorials" → score: 0.85
- "Extract product prices from this website" → score: 0.90

---

#### finder Handler
**Keywords:** `find file`, `locate`, `search filesystem`, `file location`, `directory`, `folder`, `path`, `file search`, `where is`

**Capabilities:**
- Search filesystem for files/folders
- Locate files by name or content
- Get file metadata (size, date, permissions)
- Navigate directory structures

**Example Matches:**
- "Find all PDF files in Documents" → score: 0.95
- "Where is my tax_return.xlsx file?" → score: 0.90
- "Search for files containing 'budget'" → score: 0.85

---

#### weather Handler
**Keywords:** `weather`, `forecast`, `temperature`, `rain`, `sunny`, `cloudy`, `precipitation`, `humidity`, `wind`, `storm`, `climate`

**Capabilities:**
- Get current weather conditions
- Retrieve weather forecasts (hourly, daily, weekly)
- Check precipitation probability
- Get temperature, humidity, wind speed

**Example Matches:**
- "What's the weather like today?" → score: 0.95
- "Will it rain tomorrow?" → score: 0.95
- "Show me the weekly forecast" → score: 0.90

---

#### wolfram Handler
**Keywords:** `calculation`, `math`, `compute`, `scientific query`, `solve`, `formula`, `equation`, `statistics`, `convert units`, `knowledge`

**Capabilities:**
- Perform mathematical calculations
- Solve equations and formulas
- Unit conversions
- Scientific and statistical computations
- Knowledge base queries (facts, data)

**Example Matches:**
- "Calculate 15% of 240" → score: 0.95
- "Solve for x: 2x + 5 = 15" → score: 0.95
- "Convert 100 miles to kilometers" → score: 0.90
- "Population of France in 2023" → score: 0.85

---

### System & Data Management Handlers (5 Agents)

#### terminal Handler
**Keywords:** `command`, `shell`, `execute`, `run script`, `bash`, `terminal`, `cli`, `script`, `system command`, `process`

**Capabilities:**
- Execute shell commands
- Run scripts (bash, python, etc.)
- File operations via command line
- System information retrieval
- Process management

**Example Matches:**
- "Run ls -la command" → score: 0.95
- "Execute Python script analyze_data.py" → score: 0.90
- "Check system disk usage" → score: 0.85

---

#### spreadsheet Handler
**Keywords:** `excel`, `csv`, `spreadsheet`, `data table`, `rows`, `columns`, `cells`, `workbook`, `sheet`, `formula`

**Capabilities:**
- Create spreadsheets (Excel, CSV)
- Read and write spreadsheet data
- Manipulate rows, columns, cells
- Apply formulas and calculations

**Example Matches:**
- "Create Excel spreadsheet with sales data" → score: 0.95
- "Read CSV file and summarize totals" → score: 0.90
- "Update cell B5 with new value" → score: 0.85

**Conflicts:**
- `google_workspace` (Sheets) and `microsoft_365` (Excel) → Prefer those for cloud-based spreadsheets, `spreadsheet` for local files

---

#### document Handler
**Keywords:** `document`, `text file`, `word doc`, `pdf`, `create document`, `format`, `paragraph`, `heading`, `page`

**Capabilities:**
- Create text documents
- Format documents (headings, paragraphs, lists)
- Convert between formats
- Basic document editing

**Example Matches:**
- "Create Word document with meeting notes" → score: 0.95
- "Format this text as a report" → score: 0.85
- "Convert PDF to text" → score: 0.80

**Conflicts:**
- `google_workspace` (Docs) and `microsoft_365` (Word) → Prefer those for cloud documents, `document` for local files

---

#### file_sharing Handler
**Keywords:** `share file`, `upload`, `download`, `file transfer`, `send file`, `receive file`, `link`, `attachment share`

**Capabilities:**
- Upload files to sharing service
- Download files from URLs/services
- Generate shareable links
- Transfer files between locations

**Example Matches:**
- "Upload report.pdf and get shareable link" → score: 0.95
- "Download file from this URL" → score: 0.90
- "Share presentation.pptx with team" → score: 0.85

---

#### tv_movies Handler
**Keywords:** `movie`, `tv show`, `watch`, `entertainment`, `film`, `series`, `actor`, `director`, `genre`, `imdb`, `tmdb`

**Capabilities:**
- Search movies and TV shows
- Get movie/show details and ratings
- Find recommendations based on preferences
- Actor and director information

**Example Matches:**
- "Find movies starring Tom Hanks" → score: 0.95
- "Recommend sci-fi TV shows" → score: 0.90
- "Get details about Inception movie" → score: 0.95

---

### Healthcare Integration Handlers (2 Agents)

#### <healthcare>_sdk2 Handler
**Keywords:** `patient`, `appointment`, `<healthcare>`, `healthcare`, `medical`, `provider`, `booking`, `ehr`, `chart note`

**Capabilities:**
- Patient management (create, search, update)
- Appointment scheduling and management
- Healthcare provider operations
- EHR integration via <healthcare-platform> platform

**Example Matches:**
- "Schedule patient appointment for next Tuesday" → score: 0.95
- "Search for patient John Smith in <healthcare-platform>" → score: 0.95
- "Update patient chart with new vitals" → score: 0.90

---

#### <healthcare>_task_management Handler
**Keywords:** `<healthcare> task`, `care plan`, `patient task`, `healthcare task`, `treatment task`, `task assignment`

**Capabilities:**
- Create and assign healthcare tasks
- Track care plan progress
- Manage treatment task lists
- Task completion monitoring

**Example Matches:**
- "Create care plan task for medication adherence" → score: 0.95
- "Assign task to patient for daily blood pressure log" → score: 0.90
- "Check completion status of patient tasks" → score: 0.85

---

### Data & Validation Handlers (2 Agents)

#### data_validator Handler
**Keywords:** `validate`, `check data`, `verify format`, `data quality`, `validation rules`, `schema`, `integrity`, `compliance`

**Capabilities:**
- Validate data against schemas
- Check data quality and integrity
- Verify format compliance
- Run validation rules

**Example Matches:**
- "Validate email addresses in this CSV" → score: 0.95
- "Check data quality for customer records" → score: 0.90
- "Verify JSON schema compliance" → score: 0.95

---

#### prompt_registry Handler
**Keywords:** `prompt template`, `system prompt`, `ai prompt`, `prompt library`, `prompt version`, `save prompt`, `retrieve prompt`

**Capabilities:**
- Store prompts in registry
- Retrieve prompts by ID or category
- Version control for prompts
- Prompt template management

**Example Matches:**
- "Save this prompt as 'data-analysis-v1'" → score: 0.95
- "Retrieve prompt template for code review" → score: 0.90
- "List all prompts in customer-service category" → score: 0.85

---

### Agent Systems Handlers (6 Agents)

#### swarm Handler
**Keywords:** `agent swarm`, `multi-agent collaboration`, `agent coordination`, `swarm intelligence`, `distributed agents`

**Capabilities:**
- Coordinate multiple agents simultaneously
- Distribute tasks across agent swarm
- Aggregate results from swarm execution
- Manage agent collaboration patterns

**Example Matches:**
- "Run swarm of agents to analyze data from multiple sources" → score: 0.95
- "Coordinate agent team for parallel processing" → score: 0.90

---

#### agent_builder Handler
**Keywords:** `create agent`, `build agent`, `agent definition`, `configure agent`, `agent specification`, `custom agent`

**Capabilities:**
- Create new agent definitions
- Configure agent capabilities and parameters
- Build custom agents for specific tasks
- Agent template management

**Example Matches:**
- "Create new agent for sentiment analysis" → score: 0.95
- "Build custom agent with these specifications" → score: 0.90

---

#### agent_s_handler Handler
**Keywords:** `agent s`, `specialized agent`, `agent s operations`, `s agent management`

**Capabilities:**
- Manage Agent S specialized operations
- Agent S-specific task handling
- Coordinate with Agent S instances

**Example Matches:**
- "Run Agent S for this specialized task" → score: 0.95

---

#### agent_registry Handler
**Keywords:** `register agent`, `agent catalog`, `agent discovery`, `agent capabilities`, `agent lookup`, `agent directory`

**Capabilities:**
- Register new agents in registry
- Discover available agents
- Query agent capabilities
- Maintain agent catalog

**Example Matches:**
- "Register new agent with these capabilities" → score: 0.95
- "Find agents that can handle data validation" → score: 0.90
- "List all agents in registry" → score: 0.85

---

#### structured_agent Handler
**Keywords:** `structured workflow`, `step-by-step agent`, `structured output`, `schema validation`, `format enforcement`

**Capabilities:**
- Execute structured workflows
- Generate outputs matching schemas
- Enforce format compliance
- Step-by-step task execution

**Example Matches:**
- "Generate structured JSON output for this data" → score: 0.95
- "Run step-by-step workflow for data processing" → score: 0.90

---

#### multi_agent Handler
**Keywords:** `multiple agents`, `agent coordination`, `parallel agents`, `agent routing`, `multi-agent system`

**Capabilities:**
- Coordinate multiple agents for complex tasks
- Route tasks to appropriate agent combinations
- Manage agent orchestration
- Handle parallel agent execution

**Example Matches:**
- "Coordinate multiple agents to handle this complex request" → score: 0.95
- "Route task to appropriate agent system" → score: 0.85

---

### Workspace Management Handlers (2 Agents)

#### workspace Handler
**Keywords:** `workspace`, `project space`, `collaboration area`, `shared workspace`, `team space`, `organize`, `115 methods`

**Capabilities:**
- Create and manage workspaces
- Share workspaces with team members
- Organize workspace resources
- 115 comprehensive workspace methods

**Example Matches:**
- "Create new workspace for Q1 2024 project" → score: 0.95
- "Share workspace with team@example.com" → score: 0.90
- "List all my workspaces" → score: 0.85

---

#### task_comments Handler
**Keywords:** `task comment`, `task note`, `task discussion`, `comment on task`, `task feedback`, `collaborate on task`

**Capabilities:**
- Add comments to tasks
- Track task discussions
- Team collaboration on tasks
- Comment notifications

**Example Matches:**
- "Add comment to task #1234: 'Reviewed and approved'" → score: 0.95
- "Show comments for this task" → score: 0.90
- "Reply to task comment" → score: 0.85

---

## Standalone MCP Selection Patterns (10 Agents)

### Creative & Design Tools (2 Agents)

#### claude MCP
**Keywords:** `claude`, `anthropic`, `ai assistant`, `claude sdk`, `claude code`, `reasoning`, `analysis`

**Capabilities:**
- Claude SDK functionality
- Direct Anthropic API integration
- Advanced reasoning and analysis
- Claude Code operations

**Example Matches:**
- "Use Claude to analyze this codebase" → score: 0.95
- "Run Claude SDK operation" → score: 0.90

---

#### canva_mcp MCP
**Keywords:** `design`, `canva`, `graphics`, `visual`, `create design`, `template`, `brand kit`, `export design`, `asset`

**Capabilities:**
- Design creation and manipulation (11 tools)
- Template search and application
- Asset management (upload, add elements)
- Brand kit application
- Design export and sharing
- OAuth integration for Canva

**Example Matches:**
- "Create Instagram post design in Canva" → score: 0.95
- "Search Canva templates for presentation" → score: 0.90
- "Apply brand kit to design" → score: 0.85

---

### Business Productivity Platforms (2 Agents)

#### google_workspace MCP
**Keywords:** `gmail`, `drive`, `docs`, `sheets`, `calendar` (specifically Google), `google`, `g suite`, `forms`, `slides`, `chat`

**Capabilities:**
- Gmail operations (send, search, profile) - 15 tools total
- Google Drive (list, upload, download files)
- Google Calendar (list, create events)
- Google Docs (create documents)
- Google Sheets (create, read spreadsheets)
- Google Forms (create forms)
- Google Slides (create presentations)
- Google Chat (send messages)
- OAuth authentication for Google

**Example Matches:**
- "Send email via Gmail" → score: 0.90 (prefer over generic `email` for Google-specific)
- "Upload file to Google Drive" → score: 0.95
- "Create Google Docs document" → score: 0.95
- "Schedule event in Google Calendar" → score: 0.90

---

#### microsoft_365 MCP
**Keywords:** `outlook`, `onedrive`, `teams`, `office 365`, `microsoft`, `word`, `excel`, `powerpoint`, `sharepoint`

**Capabilities:**
- Teams app creation and management (12 tools total)
- Copilot agent building
- Adaptive cards management
- Microsoft 365 app development
- Graph API access
- Office document management
- Outlook integration
- OneDrive operations
- OAuth for Microsoft

**Example Matches:**
- "Create Microsoft Teams app" → score: 0.95
- "Build Copilot agent" → score: 0.95
- "Access OneDrive files" → score: 0.90
- "Manage Outlook calendar" → score: 0.85

---

### CRM & Marketing Platforms (3 Agents)

#### gohighlevel MCP
**Keywords:** `ghl`, `crm`, `go high level`, `marketing`, `contact management`, `pipeline`, `workflow`, `campaign`, `sms`, `opportunity`

**Capabilities:**
- Comprehensive CRM (200+ tools across 20 categories)
- Contact management (32 tools)
- Messaging (SMS, email, conversations) - 20 tools
- Blog management (7 tools)
- Opportunity pipeline management (10 tools)
- Calendar and appointments (14 tools)
- Email marketing campaigns (5 tools)
- Social media posting (14 tools)
- Custom objects and associations
- Workflow automation
- Store and product management
- Payment and invoicing

**Example Matches:**
- "Add contact to GHL CRM" → score: 0.95
- "Create opportunity in pipeline" → score: 0.95
- "Send SMS campaign to contacts" → score: 0.90
- "Create workflow automation" → score: 0.85

---

#### meta_business_sdk MCP
**Keywords:** `facebook ads`, `instagram`, `meta advertising`, `facebook campaign`, `ad creative`, `audience targeting`, `meta business`

**Capabilities:**
- Facebook/Instagram advertising (18 tools across 7 categories)
- Campaign management (get, create, update campaigns)
- Ad set creation with targeting
- Ad management and creative specs
- Creative management with brand safety
- Asset uploads (images, videos)
- Custom audience creation and lookalikes
- Ad insights and reporting
- Account and business management

**Example Matches:**
- "Create Facebook ad campaign" → score: 0.95
- "Target Instagram audience aged 25-34" → score: 0.90
- "Get ad performance metrics" → score: 0.85
- "Upload video for Meta ads" → score: 0.90

---

#### google_ads MCP
**Keywords:** `google ads`, `adwords`, `search advertising`, `google campaign`, `ppc`, `google advertising`, `keyword bidding`

**Capabilities:**
- Google Ads platform (36 tools across 8 categories)
- Campaign creation and management
- Keyword research and bidding
- Ad group management
- Performance reporting
- Audience targeting
- Budget management
- OAuth authentication for Google Ads

**Example Matches:**
- "Create Google Ads campaign" → score: 0.95
- "Research keywords for PPC" → score: 0.90
- "Get Google Ads performance report" → score: 0.85

---

### Video Processing Tools (2 Agents)

#### video_editing_mcp MCP
**Keywords:** `edit video`, `video processing`, `video production`, `trim video`, `merge videos`, `video effects`, `videojungle`

**Capabilities:**
- Professional video editing (11 tools)
- Video management (add, search local/remote)
- Project operations and asset management
- Generate edits from multiple or single videos
- Update existing video edits
- Local editing operations
- Video visualization (bar charts, line charts)

**Example Matches:**
- "Edit this video to remove first 10 seconds" → score: 0.95
- "Merge three videos into one" → score: 0.90
- "Create video bar chart from data" → score: 0.85

---

#### video_digest_mcp MCP
**Keywords:** `transcribe video`, `video summary`, `video analysis`, `video content`, `video transcript`, `speech to text`

**Capabilities:**
- Video transcription (4 AI services integration)
- Multi-platform video download
- Content analysis and summarization
- Speech-to-text conversion

**Example Matches:**
- "Transcribe this YouTube video" → score: 0.95
- "Get video transcript and summary" → score: 0.95
- "Analyze video content" → score: 0.85

---

### Authentication Tools (1 Agent)

#### mcp_oauth_server MCP
**Keywords:** `oauth`, `authentication`, `authorize`, `oauth flow`, `access token`, `oauth integration`, `login`

**Capabilities:**
- OAuth 2.0 integration and management
- Authentication flow handling
- Access token management
- Authorization for various services

**Example Matches:**
- "Authenticate with OAuth" → score: 0.95
- "Get OAuth access token for service" → score: 0.90
- "Handle OAuth callback" → score: 0.85

---

## Capability Scoring Algorithm

### Keyword Matching Score

Calculate keyword overlap between task and MCP:

```
function calculate_keyword_overlap(task_keywords, mcp_keywords):
  matches = 0
  total_task_keywords = length(task_keywords)

  for task_kw in task_keywords:
    for mcp_kw in mcp_keywords:
      if keyword_similar(task_kw, mcp_kw):
        matches += 1
        break

  return matches / total_task_keywords
```

**Keyword Similarity:**
- Exact match: 1.0
- Stem match (e.g., "email" vs "emailing"): 0.9
- Synonym match (e.g., "schedule" vs "calendar"): 0.8
- Related word (e.g., "inbox" for "email"): 0.7

### Capability Matching Score

Calculate capability alignment between task requirements and MCP capabilities:

```
function calculate_capability_match(required_capabilities, mcp_capabilities):
  matches = 0
  total_required = length(required_capabilities)

  for req_cap in required_capabilities:
    if req_cap in mcp_capabilities:
      matches += 1

  return matches / total_required
```

**Required Capabilities Examples:**
- Task: "Send email with attachment" → requires: ['send', 'attach_file']
- Task: "Schedule recurring meeting" → requires: ['create_event', 'set_recurring']
- Task: "Upload file and share link" → requires: ['upload', 'generate_link']

### Final Score Calculation

Combine keyword and capability scores with weights:

```
function calculate_final_score(task, mcp):
  keyword_score = calculate_keyword_overlap(task.keywords, mcp.keywords)
  capability_score = calculate_capability_match(task.required_capabilities, mcp.capabilities)

  # Weighted combination: keywords 60%, capabilities 40%
  final_score = (keyword_score * 0.6) + (capability_score * 0.4)

  return final_score
```

**Rationale for Weights:**
- Keywords (60%): Natural language matching is primary signal
- Capabilities (40%): Ensures technical feasibility

---

## Conflict Resolution Patterns

### When Multiple MCPs Could Handle Task

**Scenario 1: Generic vs Specific Service**
- Example: Both `calendar` and `google_workspace` can handle Google Calendar
- Resolution: Prefer more specific (`google_workspace`) when service explicitly mentioned
- Fallback: Use generic (`calendar`) if specific service fails

**Scenario 2: Handler vs Standalone for Same Service**
- Example: Both `email` handler and `google_workspace` can send Gmail
- Resolution: Prefer handler for simple operations, standalone for advanced features
- Decision factors: Task complexity, required features, authentication availability

**Scenario 3: Multiple Services in Different Domains**
- Example: Task mentions both "calendar" (MCP) and "UI component" (Frontend)
- Resolution: Identify as multi-domain task, escalate to Master for cross-domain coordination
- MCP Domain handles only MCP portion after Master breaks down task

### Tie-Breaking Rules

When scores are identical (within 0.05):

1. **Recency**: Prefer MCP used in recent tasks (affinity routing)
2. **Performance**: Prefer MCP with better historical success rate
3. **Availability**: Prefer MCP with lower current load
4. **Specificity**: Prefer more specialized MCP over generic
5. **User preference**: Prefer MCP from user's configured preferences

---

## Fallback and Escalation Patterns

### When to Escalate to Master

**Low Confidence (< 0.4):**
- No MCP agent scores above threshold
- Task may belong to different domain (Frontend, Backend, Infrastructure, Quality)
- Master re-routes to appropriate domain orchestrator

**Ambiguous Task:**
- Multiple high-scoring MCPs with no clear winner
- Task description too vague to determine intent
- Master requests clarification from user

**Cross-Domain Task:**
- Task requires both MCP and non-MCP work
- Example: "Build React component and integrate with Calendar API"
- Master coordinates across multiple domains

### Fallback Agent Selection

When primary agent fails:

1. **Retry primary**: Attempt same agent up to 3 times
2. **Try alternative**: Select next-highest scoring MCP
3. **Use generic**: Fall back to generic handler if specialized fails (e.g., `calendar` if `google_workspace` fails)
4. **Report failure**: If all fallbacks fail, report to Master with error details

---

## Learning and Improvement

### Track Selection Accuracy

Record outcomes for continuous improvement:

```
function record_selection_outcome(task, selected_mcp, outcome):
  log_entry = {
    task_keywords: task.keywords,
    task_description: task.description,
    selected_mcp: selected_mcp.name,
    selection_score: selected_mcp.score,
    outcome: outcome,  # success | failure | fallback_used
    execution_time: duration,
    timestamp: now()
  }

  save_to_learning_database(log_entry)
```

### Adjust Scoring Based on History

Use historical data to refine selection:

```
function adjust_score_from_history(mcp, task, base_score):
  historical_successes = count_successful_tasks(mcp, similar_keywords(task.keywords))
  historical_failures = count_failed_tasks(mcp, similar_keywords(task.keywords))

  success_rate = historical_successes / (historical_successes + historical_failures)

  # Boost or penalize score based on historical performance
  if success_rate > 0.8:
    return base_score * 1.1  # 10% boost
  elif success_rate < 0.5:
    return base_score * 0.9  # 10% penalty
  else:
    return base_score  # No adjustment
```

---

## Summary

This agent selection logic provides:

- ✅ Comprehensive keyword patterns for all 34 MCP agents
- ✅ Scoring algorithm combining keywords (60%) and capabilities (40%)
- ✅ Confidence thresholds for single-agent, multi-agent, and escalation decisions
- ✅ Conflict resolution for overlapping MCP capabilities
- ✅ Fallback strategies when primary agent fails
- ✅ Learning system for continuous improvement

Use this logic to route every MCP task to the optimal agent(s) with high accuracy and appropriate fallback handling.
