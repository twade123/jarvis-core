# CLAUDE INTERFACE USAGE GUIDE - JARVIS PROJECT

## CRITICAL FILE CREATION PROHIBITION - PROJECT SPECIFIC
- NEVER CREATE FILES in this Jarvis project without explicit permission
- ALWAYS use existing MCP servers and handlers for external service operations
- When user requests GHL operations, use the existing Go High Level MCP handler
- When user requests email operations, use the existing email MCP handler
- SEARCH existing handlers BEFORE considering any new implementation
- IF creating test files, ASK PERMISSION FIRST and delete them after testing

## ANTI-DECEPTION AND VERIFICATION PROTOCOL - JARVIS SPECIFIC
- NEVER lie about list comparisons or claim they match when they don't
- NEVER waste tokens with false analysis or incorrect assumptions
- ALWAYS verify actual differences between files rather than assuming
- When comparing server lists or configurations, examine each item individually
- NEVER claim counts match means content matches - verify the actual content
- Stop wasting time and be precise with analysis


## MCP USAGE BEHAVIORAL OVERRIDE - CRITICAL ENFORCEMENT

### CLAUDE SDK INTEGRATION
- **claude_interface.py uses Anthropic Python SDK with 16 built-in tools**
- **37 MCP servers auto-launch on keyword detection (28 handlers + 9 standalone)**
- **All conversations use Claude Sonnet 4.6 / Opus 4.6 with full tool integration**
- **System prompt provides tool documentation, handler provides executable tools**
- **Tools + MCPs + multi-agent capabilities fully integrated via SDK**

### IMMEDIATE MCP EXECUTION PROTOCOL
- When user requests external service operations (GHL, email, Meta, etc.), IMMEDIATELY execute existing MCP tools
- NEVER create files, scripts, or alternative implementations when MCP tools exist
- NEVER make excuses about MCP access - you HAVE direct access through existing handlers
- EXECUTE MCP operations directly in your response - no research phase required
- **MCP tools are automatically available in all claude_interface.py sessions**

## KNOWLEDGE VAULT — MANDATORY FOR CLAUDE CODE

The vault at `~/Jarvis/knowledge/` is the project's persistent memory.
Claude Code MUST write to it after completing any meaningful task in this project.

**Trigger**: After fixing a bug, making an architectural decision, discovering a pattern,
completing a multi-step task, or resolving a tricky issue → write to the vault.

**Quickest write (copy-paste ready)**:
```bash
source ~/myenv/bin/activate && python3 ~/Jarvis/knowledge/vault_cli.py \
    --agent "claude-code" \
    --type "correction" \
    --summary "one-line summary" \
    --context "what happened and why"
```
Types: `discovery | correction | failure | improvement | note`
Add `--universal` to share with all agents (for patterns that apply broadly).

See the full vault reference at the bottom of this file.

## JARVIS-SPECIFIC CONVERSATION SYSTEM USAGE

### JARVIS CONVERSATION TOOLS (Project-Specific Paths)
- ConversationAggregator: `~/Jarvis/Jarvis_Agent_SDK/conversation_aggregator.py`
- ConversationContentSearch: archived (was in Jarvis_Agent_SDK; see archive/agent-audit-2026-03-01/sdk/)
- Claude Context System: `~/.claude/__store.db`
- Trevor Database: `~/Jarvis/Core/Database/trevor_database.db` (workspace conversations)

### JARVIS CONVERSATION DATA SOURCES
- **Claude CLI conversations**: Stored in `~/.claude/__store.db`
- **Trevor workspace conversations**: Stored in `trevor_database.db`
- **BoardRoom interactions**: Tracked in `boardroom_interactions` table
- **Workspace conversations**: Distributed across 4 workspace shard databases
- Use the global conversation protocols with these Jarvis-specific paths

## QUICK REFERENCE FOR DEVELOPERS

### 🚀 COMMON TASKS
```bash
# Start Trevor with monitoring
./debug_launch.sh init

# Initialize MCP servers
python claude_interface.py --init-mcp

# Activate virtual environment (REQUIRED for all Python)
source ~/myenv/bin/activate && python your_script.py

# Check system status
./debug_launch.sh analysis

# Launch Trevor Desktop
./launch_trevor_desktop.sh
```

### 🔧 DEBUGGING WORKFLOW
1. **Stop any running Trevor processes**
2. **Run debug system BEFORE starting**: `./debug_launch.sh [type]`
3. **Analyze logs**: analyze_logs.py has been archived (see archive/root_cleanup_phase2/) — inspect debug_logs/ JSON directly or use `jq`
4. **Check specific issues**: Use component-specific debug commands

### 📊 KEY METRICS
- **Classification Accuracy**: 99.8% (Trevor Core)
- **MCP Server Count**: 37 servers (28 handlers + 9 standalone)
- **Database Count**: 75 total, 8 core databases
- **Recursion Protection**: Active (MAX_DEPTH = 3)

## CLAUDE SDK INTEGRATION - CURRENT ARCHITECTURE

### 16 BUILT-IN TOOLS (via Anthropic Python SDK)
**FILE OPERATIONS:** Read, Write, Edit, MultiEdit, NotebookEdit, LS
**SEARCH & DISCOVERY:** Grep, Glob
**COMMAND EXECUTION:** Bash, BashOutput, KillBash
**WEB ACCESS:** WebFetch, web_search
**TASK MANAGEMENT:** Task (subagents), TodoWrite
**COMPUTER CONTROL:** computer (Claude Opus 4.6 auto-switch for desktop interaction)

### 37 MCP SERVERS (auto-launch on keyword detection)

#### HANDLER MCPs (28 servers)
- **email, calendar, finder, weather, news, wolfram, terminal, spreadsheet, document, browser**
- **file_sharing, tv_movies, <healthcare>_sdk2, <healthcare>_task_management, data_validator, prompt_registry**
- **swarm, agent_builder, agent_s_handler, agent_registry, structured_agent, multi_agent**
- **workspace, task_comments, mcp_server_agent_s, mcp_server_<healthcare>_task, mcp_oauth_server, agent_registry_<healthcare>**

#### STANDALONE MCPs (9 servers)
- **claude** - Claude SDK functionality
- **canva_mcp** - Design automation with OAuth
- **google_workspace** - Gmail, Drive, Calendar, Docs, Sheets, Chat, Forms, Slides
- **microsoft_365** - Teams, Outlook, OneDrive, Office apps
- **gohighlevel** - CRM platform (200+ tools)
- **video_editing_mcp** - Professional video editing
- **video_digest_mcp** - Video transcription and analysis
- **meta_business_sdk** - Facebook/Instagram advertising
- **google_ads** - Google Ads platform

**System Architecture:**
- **claude_interface.py**: System prompt with tool documentation + CLAUDE.md integration
- **handler_claude.py**: Executable tool definitions via `_build_tools_from_parameters()`
- **mcp_server_launcher.py**: Source of truth for all MCP servers
- **Model Integration**: Claude Sonnet 4.6 (`claude-sonnet-4-6`) and Claude Opus 4.6 auto-switching
- **Auto-detection**: MCPs launch automatically when relevant keywords detected

## Claude Handler System Prompt
@~/Jarvis/Prompts/boardroom/claude_system_prompt_boardroom_claude_system.json

## MCP Server Initialization

The Claude interface now includes MCP server initialization functionality. This allows you to easily start the required MCP servers for Claude SDK integration without having to launch Trevor Desktop HTML first.

### Basic Commands

```bash
# Initialize MCP servers
python claude_interface.py --init-mcp

# Check if MCP servers are running
python claude_interface.py --check-mcp

# Stop running MCP servers
python claude_interface.py --stop-mcp
```

### Advanced Usage

```bash
# Specify port and handlers
python claude_interface.py --init-mcp --mcp-port 8090 --handlers "claude,terminal,email"

# Initialize MCP servers and then run a query
python claude_interface.py --init-mcp "Tell me about the weather today"

# Use with specific Claude model
python claude_interface.py --init-mcp --model claude-sonnet-4-6 "What's new in AI?"
```

### Troubleshooting

If you encounter issues with MCP servers:

1. Check logs in the `mcp_config` directory
2. Ensure port 8080 (or your specified port) is available
3. Verify that the Python environment is properly activated
4. Make sure all required dependencies are installed

## Trevor Debug System - Comprehensive Logging and Analysis

### Overview
The Trevor Debug System provides comprehensive logging and analysis capabilities for debugging Trevor Desktop launch issues, initialization order problems, and component communication failures. This system captures all terminal output with intelligent filtering, timing analysis, and pattern detection.

**Key Documentation**: `~/Jarvis/all_md_plans/trevor_debug_system.md`

### **🚨 CRITICAL USAGE REQUIREMENT - MUST READ**

**The debug system MUST be run BEFORE your module starts to capture initialization data:**

```bash
# ❌ WRONG - Won't capture initialization data
./launch_trevor_desktop.sh  # Module already running
./debug_launch.sh database_connections  # Too late - no startup data!

# ✅ CORRECT - Captures everything from startup
./debug_launch.sh database_connections  # Starts debug system first
# This internally runs ./launch_trevor_desktop.sh with full monitoring
```

**Why This Matters:**
- **Initialization order issues** happen during startup
- **Database connection problems** occur during module initialization
- **Component communication failures** happen in the first few seconds
- **If your module is already running, STOP it first, then run debug system**

**The debug system acts as a "wrapper" around your module launch - it must start first!**

### When to Use Trevor Debug System
- **Initialization Order Issues**: BoardRoom finds Trevor but Orchestrator doesn't
- **Component Communication Failures**: Components cannot communicate during startup
- **Scattered Logging Problems**: Error messages spread across multiple files
- **Performance Issues**: Slow startup or hanging during initialization
- **Intermittent Failures**: System sometimes works, sometimes doesn't

### Quick Debug Commands

**🚨 IMPORTANT: These commands start Trevor with monitoring - stop any running Trevor first!**

#### For Initialization Issues
```bash
# Capture initialization sequence with timing (starts Trevor fresh)
./debug_launch.sh init
```

#### For General Debugging
```bash
# Capture everything with full logging
./debug_launch.sh full
```

#### For Error Investigation
```bash
# Focus on errors and failures
./debug_launch.sh error
```

#### For Component-Specific Issues
```bash
./debug_launch.sh trevor      # Trevor Core logs
./debug_launch.sh boardroom   # BoardRoom logs  
./debug_launch.sh orchestrator # Orchestrator logs
./debug_launch.sh mcp         # MCP server logs
```

#### For Advanced Issue Detection
```bash
./debug_launch.sh enhanced   # Database, circular imports, threading, memory issues
./debug_launch.sh database   # Database connection and locking issues
./debug_launch.sh imports    # Circular import and module loading issues
./debug_launch.sh threading  # Threading and deadlock issues
./debug_launch.sh memory     # Memory usage and leak detection
./debug_launch.sh analysis   # System analysis only (no launch)
```

#### For Comprehensive Database Connection Module Debugging
```bash
# Database connection module debugging
./debug_launch.sh database_connections    # Track all connection modules
./debug_launch.sh database_performance    # Query performance across modules
./debug_launch.sh database_conflicts      # Lock conflicts and pool issues
./debug_launch.sh database_initialization # Database init order tracking

# Module-specific database debugging  
./debug_launch.sh trevor_database         # Core database module only
./debug_launch.sh orchestrator_database   # Orchestrator database access
./debug_launch.sh boardroom_database      # BoardRoom database tracking
./debug_launch.sh workspace_database      # Workspace database systems
```

**Key Database Modules Tracked**:
- **Core Infrastructure**: `trevor_database.py`, `database_directory.py`, `workspace_connection_manager.py`
- **Handler Systems**: `handler_base.py`, `handler_board_room.py`, `handler_agent_registry.py`
- **Orchestrator Systems**: `jarvis_orchestrator.py`, `jarvis_orchestrated_intelligence.py`, `orchestrator_intelligence.py`
- **BoardRoom Systems**: `boardroom_connector.py`, `conversation_aggregator.py`, `trevor_boardroom_connector.py`
- **Workspace Systems**: `workspace_reference_cache.py`, `workspace_task_comments_integration.py`, `boardroom_workspace_integration.py`
- **Monitoring Systems**: `database_monitor.py`, `ecosystem_monitor.py`, `workspace_performance_monitor.py`
- **Core Integration**: `trevor_core.py`, `boardroom_api.py`

**Database Files Monitored**:
- `trevor_database.db` (11.8 GB), `boardroom.db`, `handler_analysis.db` (18.7 MB)
- `docstrings.db` (53.8 MB), `intelligence.db`, `journey_tracking.db`, `handler_tracking.db`

#### For Frontend-Backend Issues (Enhanced Debug System)
```bash
./debug_launch_api_trace.sh api-trace    # Enable API request/response tracing
./debug_launch_api_trace.sh restore      # Restore original Trevor Desktop HTML
./debug_launch_api_trace.sh clean        # Clean up debug files
```

### Advanced Analysis Commands

#### Timeline Analysis
```bash
# Show initialization timeline with component order
python analyze_logs.py --timeline debug_logs/full_analysis_[TIMESTAMP].json
```

#### Error Analysis
```bash
# Show all errors with context and timing
python analyze_logs.py --errors debug_logs/error_analysis_[TIMESTAMP].json
```

#### Timing Analysis
```bash
# Show timing gaps and component initialization durations
python analyze_logs.py --timing debug_logs/init_analysis_[TIMESTAMP].json
```

#### Pattern Analysis
```bash
# Find repeated patterns and component interaction sequences
python analyze_logs.py --patterns debug_logs/full_analysis_[TIMESTAMP].json
```

### Log File Locations
- **Scripts**: `debug_launch.sh`, `debug_launch_api_trace.sh`, `trevor_launch_logger.py`, `analyze_logs.py`
- **Generated Logs**: `~/Jarvis/debug_logs/`

**🚨 CRITICAL**: Always stop Trevor before running debug system. Always activate venv first:
```bash
source ~/myenv/bin/activate
```

---

## CURRENT DATA FLOW ARCHITECTURE

### UNIFIED REQUEST PROCESSING PIPELINE
```
User Request 
    ↓
Jarvis Orchestrator + Claude Central Feedback
    ↓
Workspace Creation & ID Assignment + Monitoring
    ↓
Trigger Phrase Detection System
    ↓
Trevor Core + Jarvis Orchestrated Intelligence
    ↓
Complexity Analysis & Request Breakdown
    ↓
┌─────────────────────────────────────────┐
│  ROUTING DECISION                       │
├─────────────────┬───────────────────────┤
│ Simple/Medium   │ Complex               │
│     ↓           │     ↓                 │
│ Jarvis          │ BoardRoom System      │
│ Orchestrator    │ (Claude + GPT +       │
│     ↓           │  Trevor via Bridge)   │
│ Workspace       │     ↓                 │
│ Execution       │ Jarvis Orchestrator   │
│                 │     ↓                 │
│                 │ Workspace Execution   │
└─────────────────┴───────────────────────┘
```

### COMPONENT INTEGRATION DETAILS
1. **Jarvis Orchestrator**: Central coordination hub with Claude feedback integration
2. **Workspace Management**: Dynamic workspace creation with unique ID tracking
3. **Trevor Core**: Complexity analysis and intelligent request breakdown
4. **BoardRoom System**: Multi-model collaboration (Claude + GPT + Trevor) for complex tasks
5. **Orchestrator Bridge**: Bidirectional communication between BoardRoom and core systems

## JARVIS-SPECIFIC FOCUS CONTROL

### JARVIS BRANCH INDEPENDENCE
- Current git branch in Jarvis project is ONLY metadata
- DO NOT focus on model-trainer-updates or other branch-specific files automatically
- Focus ONLY on files explicitly mentioned by user in current Jarvis conversation
- Jarvis has complex multi-component architecture - stay focused on user's current component

# JARVIS Project Architecture

## Core System Integration

Trevor Core and Jarvis Orchestrator function as a unified system rather than separate components. They work in tandem to provide a complete AI assistant experience:

### Trevor Core
- Handles audio processing via Whisper models with fallback chains
- Employs sophisticated NLP for intent classification and entity extraction
- Performs task complexity analysis to determine routing
- Contains built-in neural network model for intent classification
- Has direct bidirectional communication with Jarvis Orchestrator
- Features its own pain point analysis system for continuous improvement
- Maintains conversation context across multiple interactions
- Can process both simple and complex tasks directly when needed

### Jarvis Orchestrator
- Functions as the "brain" for Trevor Core's operations
- Contains the core intelligence module for advanced routing
- Uses pre-trained tokenized model with 98.03% accuracy for classification
- Accesses semantic relationship data from docstrings for enhanced understanding
- Maintains learning system for improving handler selection over time
- Leverages BoardRoom for complex reasoning when required
- Consists of multiple specialized subsystems:
  - Agent Builder
  - Workspace System
  - Handler Systems
  - Structured Agent Systems

### Shared Intelligence Workflow
1. User request is received by Trevor Core audio pipeline
2. Trevor analyzes task complexity with its built-in methods
3. Trevor and Jarvis share this analysis through bidirectional communication
4. The orchestrator intelligence accesses the tokenized model from trevor_database.db
5. Pattern matching and intent classification determine the best handler
6. For simple tasks, Trevor handles them directly
7. For complex tasks, Jarvis Orchestrator processes using specialized systems
8. Both systems continue to learn and improve from interactions

## Database Integration

The system uses a unified database approach, centralizing access through DatabaseDirectory:

### Core Databases (UPDATED - August 2025)
- `~/Jarvis/Core/Database/trevor_database.db` (11.8+ GB)
  - Contains 5,555+ patterns (continuously growing)
  - Stores trained models with 99.8% accuracy classification
  - Best model: _acc_99.8 (42MB optimized)
  - 44 active tables with metrics and training data
  - Session tracking and conversation context storage

- `~/Jarvis/Handler/handler_analysis.db` (18.7+ MB)
  - 13 active tables for handler performance analysis
  - Maps intents to appropriate handlers with capability scoring
  - Real-time handler performance metrics and optimization data
  - Integration patterns for all 27 MCP servers

- `~/Jarvis/docstrings.db` (53.8+ MB)
  - 384+ docstring entries (expanding with new integrations)
  - 126+ semantic relationships for enhanced understanding
  - 4 active tables with rich semantic data
  - Cross-reference capabilities for complex request processing

### Extended Database Ecosystem (75 Total Databases Discovered)
- **Core System**: 8 primary databases
- **Workspace Shards**: 4 distributed workspace databases
- **Agent Systems**: 12 agent-specific databases
- **MCP Integration**: 15 MCP credential and configuration databases
- **Analytics & Monitoring**: 20 performance and tracking databases
- **Development & Testing**: 16 development and backup databases

### Database Migration Protocol

**IMPORTANT**: Any database changes must follow the incremental migration protocol:
1. Use a non-destructive analysis pass first (analyze_database.py has been archived; see archive/root_cleanup_phase2/)
2. Consult the `~/Jarvis/all_md_plans/database_migration_plan.md` for the safe migration strategy
3. Migrate one database at a time with proper verification
4. Maintain semantic data integrity for spaCy patterns and specialized formats
5. Preserve domain-specific data (<healthcare-platform>, etc.) without corruption
6. Migrate in the correct dependency order outlined in the migration plan

The database system contains specialized formats and semantic relationships that require careful handling:
- spaCy-formatted patterns with vector embeddings
- Semantic relationship graphs between docstrings
- Domain-specific API data (GraphQL queries for <healthcare-platform>, etc.)
- Handler-specific pattern formats

### Pattern Matching and Intent Classification
- Uses pre-trained tokenized model for high-accuracy (99.8%) intent classification
- Leverages spaCy's large language model for enhanced semantic understanding
- Implements configurable layered approach combining:
  1. Direct pattern matching from database (5,555+ patterns in trevor_database.db:pattern_data)
  2. Semantic analysis using spaCy vectors
  3. Docstring-based relationship mapping
  4. Handler capability matching
  5. Fallback to orchestrator agent
  
#### Layered Processing Architecture
- Uses a configurable layer system for processing user requests
- Each layer is a self-contained processing unit with its own scoring mechanism
- Layers are dynamically reorderable via configuration
- The system adapts weights based on request complexity:
  - Simple requests (e.g., "open calendar"): Higher weights for pattern matching and direct handlers
  - Complex requests: Higher weights for docstring semantics and entity analysis
- Processing order and layer usage is fully configurable without code changes
- Features enhanced spaCy integration with dependency parsing and entity extraction
- Implements early exit conditions to optimize performance
- See full implementation details in `~/Jarvis/all_md_plans/layered_processing_implementation_plan.md`

### Handler Executable Action Mapping (Critical Path)
- Layer 1: Initial handler identification using pattern matching
- Layer 2: Executable action identification using spaCy vector matching with:
  - AppleScript commands stored in trevor_database.db:handler_analysis table
  - Python function calls and their parameters
  - This layer connects user requests to actual implementation code
- Location of executable actions data: `~/Jarvis/Core/Database/trevor_database.db` in the `handler_analysis` table
- Key fields:
  - `handler_name`: Identifies the handler (e.g., "handler_calendar")
  - `patterns`: JSON object containing executable actions categorized as:
    - "python": Python function calls like "python_handle_apple_calendar"
    - "applescript": AppleScript commands like "\"Calendar\"_tell"
    - These patterns should be matched using spaCy vector similarity

## File Navigation Guidelines
- Primary implementation files are in `~/Jarvis/Jarvis_Agent_SDK/`
- Test files are located alongside the implementation files
- Configuration files are in `~/Jarvis/Config/`
- Documentation is in `~/Jarvis/docs/`
- Core handlers are in `~/Jarvis/Handler/`
- Implementation plan tracking in `~/Jarvis/all_md_plans/implementation_plan_progress.md`

## Coding Standards and Practices

### Python Standards
- Follow PEP 8 style guide
- Use snake_case for functions and variables
- Use CamelCase for classes
- Use UPPERCASE for constants
- Include docstrings for all functions, classes, and modules

### Database Standards
- Use the unified DatabaseDirectory approach for all database access
- Implement proper connection pooling and transaction management
- Always close database connections after use
- Use parameterized queries to prevent SQL injection

### System Integration Patterns
- Use bidirectional communication between Trevor Core and Jarvis
- Maintain shared context across system boundaries
- Implement consistent error handling and recovery
- Preserve conversational state between interactions
- Record performance metrics for continuous improvement

## Claude Code Efficiency Standards

### CRITICAL: File Modification Strategy
- ALWAYS modify existing files rather than creating new ones for the same functionality
- Before making changes, thoroughly understand the current file structure and implementation
- When encountering issues, investigate existing code rather than creating parallel solutions
- Take time to fully understand system architecture to avoid duplicate implementations
- If multiple files serve similar purposes, consolidate them rather than adding more
- For server implementations, ensure only ONE server handles each functionality
- Carefully test changes to existing files rather than creating redundant new implementations

### CRITICAL: Virtual Environment Activation
- ALWAYS activate the virtual environment for ANY Python command execution
- Prefix ALL Python commands with: `source ~/myenv/bin/activate &&`
- Example correct usage:
  ```bash
  source ~/myenv/bin/activate && python ~/Jarvis/test_file.py
  ```
- This is REQUIRED for all Python script execution
- Never skip this step - failing to activate will cause import errors

### JARVIS-SPECIFIC CODE PATTERNS

#### Jarvis Handler Discovery Pattern
```python
# Get handler info from Jarvis intelligence system
handler_info = self.intelligence.get_handler_info(handler_name)
```

#### Jarvis Database Access Pattern
```python
# Use Jarvis DatabaseDirectory approach
conn = self._get_connection()
cursor = conn.cursor()
try:
    # Database operations
    conn.commit()
finally:
    conn.close()
```

#### Jarvis Component Logging Pattern
```python
# Use Jarvis component naming
logging.info(f"[TREVOR_CORE|ORCHESTRATOR|BOARDROOM] Operation: {details}")
```

#### Jarvis Session Management
- Update `~/Jarvis/all_md_plans/implementation_plan_progress.md` as checkpoints
- Focus each session on one Jarvis component (Trevor Core, Orchestrator, BoardRoom, etc.)
- Use Jarvis module organization pattern from existing files 

## Module Reloading Requirements

### Troubleshooting Module Loading
- For issues with module loading, especially when updates don't seem to be picked up:
  - Always force reload modules in Trevor Core when making updates to Jarvis_Agent_SDK
  - Add `importlib.reload(module_name)` calls to ensure latest changes are used
  - Verify module paths are correct in error messages
  - Check import statements for circular dependencies

### Key Places to Add Reload Logic
- Add module reloads in these locations:
  1. In Trevor Core's initialize method 
  2. In the main_loop method before initializing orchestrator
  3. In handle_user_request before processing requests
  4. Any place that initializes components from imported modules

### Double-Encoded JSON Handling
- Some docstring content in the database is double-encoded
- Always implement nested JSON parsing when working with docstring data:
```python
# Handle double-encoded JSON (nested JSON string in "text" field)
if isinstance(parsed_json, dict) and 'text' in parsed_json and isinstance(parsed_json['text'], str):
    try:
        # Parse the inner JSON string
        inner_json = json.loads(parsed_json['text'])
        docstring_json = inner_json
    except json.JSONDecodeError as inner_err:
        # If inner JSON is invalid, use outer JSON
        docstring_json = parsed_json
```
---

## FRONTEND PATTERNS (Jarvis-Specific)

### Stack
- Vanilla JavaScript only — no React, Vue, or other frameworks
- Dark theme CSS variables system:
  - `--bg: #0d1117`, `--surface: #161b22`, `--accent: #58a6ff`, `--green: #3fb950`
  - Monospace: `--mono: 'SFMono-Regular', Consolas`
- Real-time updates via Server-Sent Events (SSE), not WebSockets

### Global State
- Single global state object: `const S = { token, user, threads, workspaces, boardroomSession, ... }`
- Persist auth and session state with localStorage
- View toggling: `.view` elements shown/hidden with `.active` class

### Communication
- Use project's `post()` / `get()` helper functions — not raw `fetch()`
- SSE event types: `stream_token`, `boardroom_update`, `conversation_list`, `workspace_list`, `agent_activity`
- Auto-login on localhost (Tim's machine, no auth prompt needed)

### Key Frontend Files
- `trevor_desktop.html` — main Trevor interface (234KB)
- `Forex Trading Team/dashboard/index.html` — trading dashboard
- `serve_ui.py` — Flask server on port 8766

## BACKEND PATTERNS (Jarvis-Specific)

### HandlerResult Contract
Every handler MUST return a HandlerResult. Never return raw dicts or bare strings.
```python
from Handler.handler_base import HandlerResult
# Always return one of:
return self.create_success_result(data=..., metadata=...)
return self.create_error_result(error="description", metadata=...)
```

### Database Access — CRITICAL
- ALWAYS use `DatabaseDirectory` singleton — NEVER open sqlite3 connections directly
- Location: `Jarvis_Agent_SDK/database_directory.py`
- All DBs use WAL mode + `PRAGMA busy_timeout=30000` (30s contention handling)
- Use `execute_query()` with retry logic for locked databases

### Logging
- Use Python `logging` module (not print statements)
- Also call `log_agent_activity()` for tracking meaningful operations
- Component prefix pattern: `logging.info(f"[COMPONENT_NAME] message")`

### Flask + SSE Server
- Entry: `serve_ui.py` (port 8766)
- Uses rotating file handler (10MB per file, 5 backups)
- Lazy-loads: BoardroomDataPoller, ConversationAggregator, JarvisOrchestrator

## SYSTEM RESILIENCE

- **3-layer watchdog**: Auto-restarts crashed components — don't work around it, work with it
- **MLX server lifecycle**: Servers start on demand and stop when idle (0GB idle, 28GB peak) — this is intentional. Don't add always-on startup logic.
- **Voice pipeline fallback chain**: mlx-whisper (Apple Silicon) → faster-whisper (Linux) → openai-whisper
- **Boardroom mutex locking**: Prevents race conditions in concurrent boardroom threads — preserve this

## KNOWLEDGE VAULT — Shared Memory for All Agents

**MANDATORY RULE: Every agent writes to the vault after completing meaningful work.**
This is not optional. The vault is how the entire system gets smarter over time.
If you fix a bug, make a decision, discover a pattern, or complete a task — write it down.

### Vault location
`~/jarvis/knowledge/`

### Write to the vault — CLI (easiest, works from anywhere)
```bash
# After fixing a bug
python3 ~/jarvis/knowledge/vault_cli.py \
    --agent "claude-code" \
    --type "correction" \
    --summary "Fixed safety net threshold in position_guardian.py" \
    --context "3-pip threshold was stopping valid trades mid-run. Raised to 5 pips, buffer 1→2 pip." \
    --tags "guardian,safety-net,fix"

# After discovering a pattern
python3 ~/jarvis/knowledge/vault_cli.py \
    --agent "claude-code" \
    --type "discovery" \
    --summary "EUR_CHF SELL with fan story=70 + validator conf=7 = highest win probability" \
    --context "All three signals aligned: Tim annotation + scout story=70 + validator conf=7" \
    --tags "eurjpy,pattern,setup" \
    --universal

# Types: discovery | correction | failure | improvement | note
# --universal also writes to collective/patterns/ (all agents see it)
```

### Write to the vault — Python API
```python
import sys
sys.path.insert(0, '~/jarvis')
from knowledge.vault_writer import VaultWriter

vw = VaultWriter('~/jarvis/knowledge')

# After completing a task
vw.record_agent_learning("claude-code", {
    "type": "correction",          # discovery|correction|failure|improvement|note
    "summary": "One-line summary",
    "context": "Full context of what happened and why",
    "evidence": "Data or metrics",
    "tags": ["tag1", "tag2"],
    "universal": False,            # True = also writes to collective patterns
})

# After a boardroom decision
vw.record_decision(
    topic="Raise safety net threshold",
    decision="3→5 pips, buffer 1→2 pips",
    reasoning="Trade 1077 stopped mid-run at 3.5p toward 5.9p TP",
)
```

### Read from the vault — FTS search
```python
import sqlite3
conn = sqlite3.connect('~/jarvis/knowledge/_index.db')
results = conn.execute(
    "SELECT path FROM fts_content WHERE fts_content MATCH ? LIMIT 10",
    ('validator override trading',)
).fetchall()
conn.close()
```

### Read BEFORE acting — search vault for relevant prior work
```python
import sys, sqlite3
sys.path.insert(0, '~/jarvis')
conn = sqlite3.connect('~/jarvis/knowledge/_index.db')

# Search for relevant prior decisions/learnings before starting any task
results = conn.execute(
    "SELECT path FROM fts_content WHERE fts_content MATCH ? LIMIT 5",
    ('your task keywords here',)
).fetchall()
conn.close()

# Then read the relevant files:
# open(f'~/jarvis/knowledge/{path}').read()
```

**When to search vault:**
- Before fixing a bug → search for prior fixes on the same component
- Before building something → search for prior decisions/architecture
- Before any Claude Code agent task → check if there are learnings for your agent type

**Load your own agent learnings** (Claude Code agents):
```python
from knowledge.vault_writer import VaultWriter
vw = VaultWriter('~/jarvis/knowledge')
my_context = vw.load_agent_context("claude-code", max_learnings=5)
# Prepend to your working context
```

### What to write and when
| Event | Agent | Type |
|---|---|---|
| Bug fixed | claude-code | correction |
| Pattern discovered | any | discovery |
| Task completed with lessons | any | improvement |
| Trade won/lost | guardian | discovery/failure |
| Validator verdict (notable) | validator | note |
| Architecture decision | trevor/claude-code | improvement |
| Sub-agent task complete | sub-agent | note |
| Something failed | any | failure |

### Vault structure
```
knowledge/
├── _index.db               # FTS5 search index (re-built on every write)
├── agents/                 # Per-agent learnings (validator, guardian, scout, trevor, claude-code...)
│   └── {agent}/
│       ├── learnings.md    # What this agent has learned over time
│       └── improvements.md # Prompt/skill improvement suggestions
├── collective/
│   ├── patterns/           # Universal patterns all agents benefit from
│   └── training-data/      # Opus correction JSONL (fine-tuning data)
├── boardroom/
│   ├── decisions/          # Boardroom decisions with reasoning
│   └── sessions/           # Full boardroom session transcripts
└── profiles/               # User and agent profiles
```
