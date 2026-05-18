from Handler.agents import function_tool
import json
import asyncio
import os
import sys

# Add parent directory to path to allow imports from project root
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

@function_tool
async def invoke_structured_agent_system(task: str, agent_types: list[str] = None) -> str:
    """
    Invokes the structured multi-agent system to process a complex task.
    
    Args:
        task: The task to process, formatted as a JSON string
        agent_types: Optional list of specific agent types to involve (DATA_ANALYST, COORDINATOR)
    
    Returns:
        Results from the multi-agent processing as a JSON string
    """
    from structured_agent_system import MultiAgentSystem, AgentType, AgentCapability, AgentSpecialization
    
    # Initialize the system
    system = MultiAgentSystem()
    
    # Create agent configurations based on requested types
    agent_configs = []
    
    # Configure a team with the requested agents or use defaults
    if agent_types:
        for agent_type in agent_types:
            if agent_type == "DATA_ANALYST":
                agent_configs.append({
                    "name": "data_analyst_agent",
                    "type": AgentType.DATA_ANALYST,
                    "specialization": AgentSpecialization(
                        domain="data_analysis",
                        expertise_level=9,
                        capabilities=[
                            AgentCapability.DATA_ANALYSIS,
                            AgentCapability.ANALYTICAL,
                            AgentCapability.TECHNICAL
                        ],
                        tools=[],
                        knowledge_base=["Statistical Analysis", "Data Visualization"]
                    )
                })
            elif agent_type == "COORDINATOR":
                agent_configs.append({
                    "name": "coordinator_agent",
                    "type": AgentType.COORDINATOR,
                    "specialization": AgentSpecialization(
                        domain="task_management",
                        expertise_level=9,
                        capabilities=[
                            AgentCapability.MANAGEMENT,
                            AgentCapability.COMMUNICATION
                        ],
                        tools=[],
                        knowledge_base=["Task Coordination", "Resource Management"]
                    )
                })
    else:
        # Default configuration with data analyst and coordinator
        agent_configs = [
            {
                "name": "data_analyst_agent",
                "type": AgentType.DATA_ANALYST,
                "specialization": AgentSpecialization(
                    domain="data_analysis",
                    expertise_level=9,
                    capabilities=[
                        AgentCapability.DATA_ANALYSIS,
                        AgentCapability.ANALYTICAL
                    ],
                    tools=[],
                    knowledge_base=["Statistical Analysis"]
                )
            },
            {
                "name": "coordinator_agent",
                "type": AgentType.COORDINATOR,
                "specialization": AgentSpecialization(
                    domain="task_management",
                    expertise_level=9,
                    capabilities=[
                        AgentCapability.MANAGEMENT,
                        AgentCapability.COMMUNICATION
                    ],
                    tools=[],
                    knowledge_base=["Task Coordination"]
                )
            }
        ]
    
    # Create the agent group
    team = system.create_agent_group("task_team", agent_configs)
    
    # Process the task and return results
    results = await system.process_task("task_team", task)
    return json.dumps(results, indent=2)

@function_tool
def invoke_structured_outputs_system(data: str, analysis_type: str) -> str:
    """
    Invokes the Structured Outputs Multi-Agent System for data analysis and visualization.
    
    Args:
        data: The dataset to analyze in CSV format
        analysis_type: Type of analysis (statistical, visualization, processing, or comprehensive)
    
    Returns:
        Results from the multi-agent data analysis as a JSON string
    """
    from Structured_outputs_multi_agent import handle_user_message
    
    # Construct appropriate query based on analysis type
    if analysis_type == "statistical":
        query = f"Below is some data. I want you to analyze the statistics of the data.\n\n{data}"
    elif analysis_type == "visualization":
        query = f"Below is some data. I want you to create visualizations of the data.\n\n{data}"
    elif analysis_type == "processing":
        query = f"Below is some data. I want you to clean and transform the data.\n\n{data}"
    elif analysis_type == "comprehensive":
        query = f"Below is some data. I want you to clean the data, analyze the statistics, and create appropriate visualizations.\n\n{data}"
    else:
        query = f"Below is some data. I want you to analyze it and provide insights.\n\n{data}"
    
    # Process with the multi-agent system
    results = handle_user_message(query)
    
    # Convert the results to a JSON string for return
    # The handle_user_message function returns a list, so we need to ensure it's serializable
    def convert_to_serializable(obj):
        if hasattr(obj, 'to_dict'):
            return obj.to_dict()
        return str(obj)
    
    return json.dumps(results, default=convert_to_serializable, indent=2)

@function_tool
def read_file(path: str) -> str:
    """
    Reads a file from the project and returns its content.
    
    Args:
        path: The file path relative to the project root
    
    Returns:
        The content of the file as a string
    """
    try:
        with open(path, 'r') as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {str(e)}"

@function_tool
def search_codebase(query: str, file_patterns: list[str] = None) -> str:
    """
    Searches the codebase for specific patterns or functionality.
    
    Args:
        query: The search pattern or term
        file_patterns: Optional list of file glob patterns to search within
    
    Returns:
        The search results as a string
    """
    import os
    import re
    import fnmatch
    
    results = []
    
    # Start from the project root
    root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    for root, dirs, files in os.walk(root_dir):
        # Skip hidden directories and virtual env
        dirs[:] = [d for d in dirs if not d.startswith('.') and d != 'myenv']
        
        for filename in files:
            # Skip hidden files and non-code files
            if filename.startswith('.') or not (filename.endswith('.py') or filename.endswith('.json')):
                continue
                
            # Check file pattern match if patterns were provided
            if file_patterns:
                if not any(fnmatch.fnmatch(filename, pattern) for pattern in file_patterns):
                    continue
            
            filepath = os.path.join(root, filename)
            try:
                with open(filepath, 'r') as f:
                    content = f.read()
                    
                    # Search for the query in the file content
                    if re.search(query, content, re.IGNORECASE):
                        rel_path = os.path.relpath(filepath, root_dir)
                        
                        # Get the matching lines
                        lines = content.split('\n')
                        matches = []
                        for i, line in enumerate(lines):
                            if re.search(query, line, re.IGNORECASE):
                                matches.append(f"Line {i+1}: {line.strip()}")
                        
                        results.append({
                            "file": rel_path,
                            "matches": matches[:5]  # Limit to 5 matches per file
                        })
            except Exception:
                # Skip files that can't be read
                pass
    
    if not results:
        return "No matches found."
    
    # Format the results
    output = "Search results:\n"
    for result in results[:10]:  # Limit to 10 files
        output += f"\nFile: {result['file']}\n"
        for match in result["matches"]:
            output += f"  {match}\n"
    
    if len(results) > 10:
        output += f"\n...and {len(results) - 10} more files with matches."
    
    return output

@function_tool
def analyze_architecture(files: list[str] = None) -> str:
    """
    Analyzes the architecture of specified files or key project components.
    
    Args:
        files: Optional list of files to analyze. If not provided, analyzes key system files.
    
    Returns:
        A description of the architecture as a string
    """
    import importlib
    import inspect
    import os
    
    if not files:
        # Default to analyzing the key system files
        files = [
            "structured_agent_system.py",
            "Structured_outputs_multi_agent.py"
        ]
    
    analysis = "Architecture Analysis:\n\n"
    
    for file in files:
        try:
            analysis += f"## File: {file}\n\n"
            
            # Read the file content
            with open(file, 'r') as f:
                content = f.read()
            
            # Basic file information
            lines = content.split('\n')
            analysis += f"- Lines of code: {len(lines)}\n"
            
            # Extract docstring if present
            docstring_match = re.search(r'"""(.*?)"""', content, re.DOTALL)
            if docstring_match:
                docstring = docstring_match.group(1).strip()
                analysis += f"- Description: {docstring[:300]}...\n" if len(docstring) > 300 else f"- Description: {docstring}\n"
            
            # Identify classes and functions
            class_matches = re.findall(r'class\s+(\w+)', content)
            function_matches = re.findall(r'def\s+(\w+)', content)
            
            analysis += f"- Classes ({len(class_matches)}): {', '.join(class_matches)}\n"
            analysis += f"- Functions ({len(function_matches)}): {', '.join(function_matches[:10])}"
            if len(function_matches) > 10:
                analysis += f" and {len(function_matches) - 10} more"
            analysis += "\n\n"
            
        except Exception as e:
            analysis += f"Error analyzing {file}: {str(e)}\n\n"
    
    return analysis 