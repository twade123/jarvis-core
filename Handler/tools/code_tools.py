from typing import Dict, List
from dataclasses import dataclass

@dataclass
class CodeTool:
    """Base class for code-related tools"""
    name: str
    description: str
    parameters: Dict
    strict: bool = True
    required: List[str] = None

# Code Development Tools
CODE_TOOLS = {
    "execute_code": CodeTool(
        name="execute_code",
        description="Execute and test code snippets with advanced error handling and performance optimization",
        parameters={
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Code to execute"},
                "language": {"type": "string", "description": "Programming language"},
                "test_cases": {"type": "array", "description": "Test cases to run"},
                "performance_metrics": {"type": "boolean", "description": "Whether to include performance analysis"},
                "security_check": {"type": "boolean", "description": "Whether to perform security analysis"},
                "environment": {"type": "string", "description": "Execution environment (dev, test, prod)"}
            },
            "required": ["code", "language"]
        }
    ),
    
    "review_code": CodeTool(
        name="review_code",
        description="Perform comprehensive code review including architecture, security, and performance analysis",
        parameters={
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Code to review"},
                "review_type": {"type": "string", "description": "Type of review (security, performance, style, architecture)"},
                "depth": {"type": "string", "enum": ["basic", "detailed", "comprehensive"]},
                "include_metrics": {"type": "boolean", "description": "Include code quality metrics"},
                "framework": {"type": "string", "description": "Framework or technology stack"},
                "best_practices": {"type": "array", "description": "Specific best practices to check"}
            },
            "required": ["code"]
        }
    ),
    
    "optimize_code": CodeTool(
        name="optimize_code",
        description="Optimize code for performance, memory usage, and efficiency",
        parameters={
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Code to optimize"},
                "optimization_target": {"type": "string", "enum": ["speed", "memory", "both"]},
                "architecture": {"type": "string", "description": "Target architecture"},
                "constraints": {"type": "object", "description": "Resource constraints"},
                "scalability": {"type": "boolean", "description": "Consider scalability in optimization"},
                "cloud_platform": {"type": "string", "description": "Target cloud platform if applicable"}
            },
            "required": ["code", "optimization_target"]
        }
    ),
    
    "debug_code": CodeTool(
        name="debug_code",
        description="Advanced debugging with root cause analysis and fix suggestions",
        parameters={
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Code to debug"},
                "error_message": {"type": "string", "description": "Error message if available"},
                "stack_trace": {"type": "string", "description": "Stack trace if available"},
                "environment": {"type": "string", "description": "Environment where error occurred"},
                "reproduction_steps": {"type": "array", "description": "Steps to reproduce the issue"}
            },
            "required": ["code"]
        }
    ),
    
    "generate_tests": CodeTool(
        name="generate_tests",
        description="Generate comprehensive test suites for code",
        parameters={
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Code to test"},
                "test_framework": {"type": "string", "description": "Testing framework to use"},
                "coverage_target": {"type": "number", "description": "Target code coverage percentage"},
                "test_types": {"type": "array", "description": "Types of tests to generate"},
                "include_edge_cases": {"type": "boolean", "description": "Whether to include edge cases"}
            },
            "required": ["code", "test_framework"]
        }
    )
}

def get_code_tool(tool_name: str) -> CodeTool:
    """Get a specific code tool by name"""
    return CODE_TOOLS.get(tool_name)

def get_all_code_tools() -> List[CodeTool]:
    """Get all available code tools"""
    return list(CODE_TOOLS.values()) 