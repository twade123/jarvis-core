"""
Terminal Handler Schema Definitions for Orchestrator Integration

This module contains JSON schema definitions for the terminal handler's function calls,
making it easier for the orchestrator agent to integrate with terminal operations.
"""

import json

# Schema for executing Python code
PYTHON_EXECUTION_SCHEMA = {
    "name": "execute_python",
    "description": "Executes Python code directly or from a file with options for environment and output handling",
    "parameters": {
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": "Python code to execute directly (use either code or file_path)"
            },
            "file_path": {
                "type": "string",
                "description": "Path to Python file to execute (use either code or file_path)"
            },
            "arguments": {
                "type": "string",
                "description": "Command-line arguments to pass to the Python script"
            },
            "use_venv": {
                "type": "boolean",
                "description": "Whether to use a virtual environment",
                "default": True
            },
            "venv_path": {
                "type": "string",
                "description": "Path to the virtual environment to use",
                "default": "~/myenv"
            },
            "working_dir": {
                "type": "string",
                "description": "Working directory for execution"
            },
            "capture_output": {
                "type": "boolean",
                "description": "Whether to capture and return the output",
                "default": True
            },
            "timeout": {
                "type": "integer",
                "description": "Timeout in seconds for execution",
                "default": 30
            }
        },
        "required": []  # Either code or file_path should be provided, but we'll validate manually
    }
}

# Schema for executing AppleScript
APPLESCRIPT_EXECUTION_SCHEMA = {
    "name": "execute_applescript",
    "description": "Executes AppleScript code directly or from a file",
    "parameters": {
        "type": "object",
        "properties": {
            "script": {
                "type": "string",
                "description": "AppleScript code to execute directly (use either script or file_path)"
            },
            "file_path": {
                "type": "string",
                "description": "Path to AppleScript file to execute (use either script or file_path)"
            },
            "target_app": {
                "type": "string",
                "description": "Target application for the AppleScript (e.g., 'Mail', 'Finder')"
            },
            "parameters": {
                "type": "object",
                "description": "Dictionary of parameters to substitute in the script (using $parameter_name format)"
            },
            "capture_output": {
                "type": "boolean",
                "description": "Whether to capture and return the output",
                "default": True
            },
            "timeout": {
                "type": "integer",
                "description": "Timeout in seconds for execution",
                "default": 30
            }
        },
        "required": []  # Either script or file_path should be provided, but we'll validate manually
    }
}

# Schema for Python with terminal integration
PYTHON_TERMINAL_SCHEMA = {
    "name": "python_terminal_integration",
    "description": "Execute Python code that interacts with the terminal or system functionality",
    "parameters": {
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": "Python code to execute"
            },
            "use_venv": {
                "type": "boolean",
                "description": "Whether to use a virtual environment",
                "default": True
            },
            "venv_path": {
                "type": "string",
                "description": "Path to the virtual environment to use",
                "default": "~/myenv"
            },
            "terminal_session_id": {
                "type": "string",
                "description": "ID of terminal session to use (if integrating with existing session)"
            },
            "capture_output": {
                "type": "boolean",
                "description": "Whether to capture and return the output",
                "default": True
            },
            "system_access": {
                "type": "array",
                "description": "List of system components the script needs access to",
                "items": {
                    "type": "string",
                    "enum": ["filesystem", "network", "subprocess", "environment"]
                }
            }
        },
        "required": ["code"]
    }
}

# Schema for AppleScript with system integration
APPLESCRIPT_SYSTEM_SCHEMA = {
    "name": "applescript_system_integration",
    "description": "Execute AppleScript code with system integration and safety features",
    "parameters": {
        "type": "object",
        "properties": {
            "script": {
                "type": "string",
                "description": "AppleScript code to execute"
            },
            "target_app": {
                "type": "string",
                "description": "Target application for the AppleScript"
            },
            "user_interaction": {
                "type": "boolean",
                "description": "Whether the script requires user interaction",
                "default": False
            },
            "parameters": {
                "type": "object",
                "description": "Dictionary of parameters to substitute in the script"
            },
            "security_level": {
                "type": "string",
                "description": "Security level of the script execution",
                "enum": ["minimal", "standard", "elevated"],
                "default": "standard"
            }
        },
        "required": ["script"]
    }
}

# Schema for Claude Code execution
CLAUDE_CODE_EXECUTION_SCHEMA = {
    "name": "execute_claude_code",
    "description": """Launches Claude Code in a terminal window for interactive AI assistance with coding tasks.
    
    Claude Code is a CLI tool that provides access to Claude's advanced code understanding and generation capabilities.
    
    When executed in a container environment:
    1. Uses subprocess.Popen to execute the Claude CLI command
    2. Can interact with the terminal via AppleScript to find existing windows or create new ones
    3. Can send text input directly to the terminal window
    4. Supports both natural language prompts and structured JSON input
    5. Can handle file operations via dedicated methods (safe_edit_file, search_and_replace, etc.)
    6. Can maintain persistent sessions for multi-step interactions
    
    Core capabilities:
    - Code analysis and explanation
    - File editing with automatic backups
    - Debugging assistance
    - Code generation
    - Path exploration and search
    - Project understanding
    
    The orchestrator agent should route requests appropriately:
    - Natural language requests from BoardRoom → Properly formatted Claude Code CLI commands
    - File operation requests → Dedicated handler methods (safe_edit_file, duplicate_file, etc.)
    - Search/grep requests → Appropriate search methods
    """,
    "parameters": {
        "type": "object",
        "properties": {
            "prompt": {
                "type": "string",
                "description": "The prompt or instructions to send to Claude Code"
            },
            "directory": {
                "type": "string",
                "description": "The directory to analyze or work in with Claude Code",
                "default": "~/Jarvis"
            },
            "verbose": {
                "type": "boolean",
                "description": "Whether to use verbose mode in Claude Code",
                "default": True
            },
            "use_json": {
                "type": "boolean",
                "description": "Whether to use JSON structured input for Claude Code",
                "default": False
            },
            "json_input": {
                "type": "object",
                "description": "JSON structure for Claude Code input (when use_json is True)"
            },
            "monitor_output": {
                "type": "boolean",
                "description": "Whether to monitor output in real-time",
                "default": False
            },
            "timeout": {
                "type": "integer",
                "description": "Maximum execution time in seconds",
                "default": 60
            },
            "reuse_session": {
                "type": "boolean",
                "description": "Whether to reuse existing Claude Code sessions",
                "default": True
            },
            "session_id": {
                "type": "string",
                "description": "Specific session ID to reuse (if available)"
            },
            "interactive": {
                "type": "boolean",
                "description": "Whether to maintain an interactive session with Claude Code",
                "default": True
            },
            "show_terminal": {
                "type": "boolean",
                "description": "Whether to make the terminal window visible during execution",
                "default": True
            },
            "capture_output": {
                "type": "boolean", 
                "description": "Whether to capture and return output from the Claude Code session",
                "default": True
            },
            "dynamic_request": {
                "type": "object",
                "description": "Structured information about the request for better routing"
            }
        },
        "required": ["prompt"]
    }
}

# Schema for codebase analysis using Claude Code
ANALYZE_CODEBASE_SCHEMA = {
    "name": "analyze_codebase",
    "description": """Analyzes a codebase using Claude Code in a terminal window.
    
    This function specializes in project-wide analysis using Claude Code CLI. When running in a container:
    
    1. It will use subprocess and AppleScript to interact with the Claude Code CLI
    2. Can optionally show visible terminal window during analysis
    3. Can create pre-filtered file lists using glob patterns before sending to Claude
    4. Is particularly effective for understanding large codebases
    
    The analysis capabilities include:
    - Architecture understanding
    - Dependency analysis
    - Identifying design patterns
    - Finding bugs or potential issues
    - Suggesting improvements or refactorings
    
    Example prompt format for effective analysis:
    "Analyze the codebase and explain the key components and how they interact."
    "Identify potential performance bottlenecks in this code structure."
    "Explain how error handling works across the project."
    """,
    "parameters": {
        "type": "object",
        "properties": {
            "directory": {
                "type": "string",
                "description": "The directory containing the codebase to analyze",
                "default": "~/Jarvis" 
            },
            "file_types": {
                "type": "array",
                "description": "List of file types to include in analysis (e.g. [\"*.py\", \"*.js\"])",
                "items": {
                    "type": "string"
                },
                "default": ["*"]
            },
            "prompt": {
                "type": "string",
                "description": "Custom prompt for Claude Code analysis (if not provided, a default one is used)"
            },
            "interactive": {
                "type": "boolean",
                "description": "Whether to maintain an interactive session with Claude Code after analysis",
                "default": True
            },
            "timeout": {
                "type": "integer",
                "description": "Maximum execution time in seconds",
                "default": 120
            },
            "show_terminal": {
                "type": "boolean",
                "description": "Whether to show the terminal window during analysis",
                "default": True
            },
            "capture_output": {
                "type": "boolean",
                "description": "Whether to capture and return output from the analysis",
                "default": True
            },
            "focus_areas": {
                "type": "array",
                "description": "Specific areas of focus for the analysis (e.g. [\"performance\", \"security\"])",
                "items": {
                    "type": "string"
                }
            }
        },
        "required": []
    }
}

# Schema for sending input to an active Claude Code session
CLAUDE_INPUT_SCHEMA = {
    "name": "send_claude_input",
    "description": """Sends input to an active Claude Code session in the terminal window.
    
    This function allows continued interaction with an already open Claude Code terminal session.
    When running in a container environment:
    
    1. It uses AppleScript to find the existing Terminal window by session ID
    2. Sends the input text directly to that window using AppleScript's 'do script' command
    3. Can optionally wait for and capture Claude's response
    4. Uses subprocess.Popen to execute the AppleScript
    
    This is particularly useful for multi-turn interactions with Claude Code where context
    needs to be maintained across multiple exchanges. The session_id parameter links
    to the unique identifier created during the initial execute_claude_code call.
    
    Example workflow:
    1. Start session with execute_claude_code
    2. Get session_id from the response
    3. Send follow-up questions using send_claude_input with that session_id
    """,
    "parameters": {
        "type": "object",
        "properties": {
            "session_id": {
                "type": "string",
                "description": "ID of the active Claude Code session"
            },
            "input": {
                "type": "string",
                "description": "Text to send to Claude Code"
            },
            "wait_for_response": {
                "type": "boolean",
                "description": "Whether to wait for and return Claude's response",
                "default": True
            },
            "timeout": {
                "type": "integer",
                "description": "Maximum time to wait for response in seconds",
                "default": 30
            },
            "use_json": {
                "type": "boolean",
                "description": "Whether to format the input as JSON",
                "default": False
            },
            "show_terminal": {
                "type": "boolean",
                "description": "Whether to bring the terminal window to front",
                "default": True
            }
        },
        "required": ["session_id", "input"]
    }
}

# Combined schema collection for export
TERMINAL_SCHEMA_COLLECTION = {
    "python_execution": PYTHON_EXECUTION_SCHEMA,
    "applescript_execution": APPLESCRIPT_EXECUTION_SCHEMA,
    "python_terminal_integration": PYTHON_TERMINAL_SCHEMA,
    "applescript_system_integration": APPLESCRIPT_SYSTEM_SCHEMA,
    "execute_claude_code": CLAUDE_CODE_EXECUTION_SCHEMA,
    "analyze_codebase": ANALYZE_CODEBASE_SCHEMA,
    "send_claude_input": CLAUDE_INPUT_SCHEMA
}

def get_schema_json(schema_name=None):
    """Get schema JSON for a specific schema or all schemas"""
    if schema_name:
        return json.dumps(TERMINAL_SCHEMA_COLLECTION.get(schema_name, {}), indent=2)
    return json.dumps(TERMINAL_SCHEMA_COLLECTION, indent=2)

def validate_parameters(schema_name, parameters):
    """
    Validate parameters against schema definition
    
    Args:
        schema_name: Name of the schema to validate against
        parameters: Dictionary of parameters to validate
        
    Returns:
        tuple: (is_valid, error_message)
    """
    schema = TERMINAL_SCHEMA_COLLECTION.get(schema_name)
    
    if not schema:
        return False, f"Unknown schema: {schema_name}"
    
    # Check required parameters
    required_params = schema.get("parameters", {}).get("required", [])
    for param in required_params:
        if param not in parameters:
            return False, f"Missing required parameter: {param}"
    
    # Special validation for Python execution
    if schema_name == "python_execution":
        if "code" not in parameters and "file_path" not in parameters:
            return False, "Either 'code' or 'file_path' must be provided"
    
    # Special validation for AppleScript execution
    if schema_name == "applescript_execution":
        if "script" not in parameters and "file_path" not in parameters:
            return False, "Either 'script' or 'file_path' must be provided"
    
    return True, "" 