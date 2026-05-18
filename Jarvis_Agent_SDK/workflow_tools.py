"""
Workflow Tools for Integrated Task Processing

This module provides workflow tools that combine capabilities from different systems for
integrated task processing.
"""

import json
import logging
from typing import Dict, Any, Optional, List, Union, Callable

# Import common utilities and boardroom connector to avoid circular dependencies
from .common_utils import (
    generate_request_id, 
    analyze_task_capabilities
)
from .boardroom_connector import (
    track_request_journey,
    update_journey_state,
    complete_journey,
    get_boardroom
)

# Constants for response management
MAX_RESPONSE_LENGTH = 50000  # Maximum length for analysis results
MAX_TOKENS_PER_BATCH = 4000  # Maximum tokens per analysis batch
TOPIC_DRIFT_THRESHOLD = 0.7  # Similarity threshold for topic drift detection

# Import get_or_create_boardroom at runtime to avoid circular dependencies

async def execute_validated_analysis_workflow(
    task: Dict[str, Any],
    workspace_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Execute a workflow that combines data validation and analysis.
    
    This workflow:
    1. Validates input data against provided rules
    2. If valid, performs the requested analysis
    3. Returns combined validation and analysis results
    
    Args:
        task: Dictionary containing:
            - data: The data to validate and analyze
            - validation_rules: Rules to validate against
            - analysis_type: Type of analysis to perform
            - max_response_length: Optional override for max response length
            - batch_size: Optional override for batch processing size
        workspace_id: Optional workspace ID for tracking
            
    Returns:
        Dict containing validation and analysis results
    """
    # Get BoardRoom instance from boardroom_connector
    boardroom = get_boardroom()
    
    # Generate request ID
    request_id = generate_request_id(task)
    
    if workspace_id is None:
        workspace_id = f"workflow_{request_id}"
    
    # Try to register workflow in BoardRoom if the method exists
    system_id = "ValidatedAnalysisWorkflow"
    try:
        if hasattr(boardroom, 'register_system'):
            system_id = boardroom.register_system(
                system_name="ValidatedAnalysisWorkflow",
                system_type="integrated_workflow",
                capabilities=["data_validation", "data_analysis"],
                workspace_id=workspace_id
            )
    except Exception as e:
        logging.warning(f"Could not register system in BoardRoom: {str(e)}")
        system_id = "ValidatedAnalysisWorkflow"
    
    # Start tracking journey
    journey_id = track_request_journey(
        request_id=request_id,
        task=task,
        system_id=system_id,
        journey_type="validated_analysis"
    )
    
    try:
        # Store original task for drift detection
        original_task = task.copy()
        
        # Extract task components
        data = task.get("data", {})
        validation_rules = task.get("validation_rules", [])
        analysis_type = task.get("analysis_type", "general")
        
        # Get response management settings
        max_response_length = task.get("max_response_length", MAX_RESPONSE_LENGTH)
        batch_size = task.get("batch_size", MAX_TOKENS_PER_BATCH)
        
        # Update journey state
        update_journey_state(
            journey_id=journey_id,
            state="validation_started",
            message="Starting data validation",
            metrics={
                "validation_rules_count": len(validation_rules),
                "max_response_length": max_response_length,
                "batch_size": batch_size
            }
        )
        
        # Step 1: Validate data
        try:
            # Import data validator dynamically to avoid circular imports
            from Handler.handler_data_validator import DataValidator
            validator = DataValidator()
            
            # Execute validation
            validation_result = await validator.validate_data(
                data=data,
                rules=validation_rules
            )
            
            # Update journey state
            update_journey_state(
                journey_id=journey_id,
                state="validation_completed",
                message="Data validation completed",
                metrics={"validation_result": validation_result}
            )
            
            # Check if validation passed
            if not validation_result.get("valid", False):
                # If validation failed, return early with validation errors
                result = {
                    "success": False,
                    "validation_result": validation_result,
                    "error": "Data validation failed",
                    "analysis_result": None
                }
                
                complete_journey(
                    journey_id=journey_id,
                    status="failed",
                    metadata={
                        "error": "Data validation failed",
                        "validation_result": validation_result
                    }
                )
                
                return result
                
        except Exception as e:
            error_message = f"Validation failed: {str(e)}"
            logging.error(error_message)
            
            result = {
                "success": False,
                "error": error_message,
                "validation_result": None,
                "analysis_result": None
            }
            
            complete_journey(
                journey_id=journey_id,
                status="failed",
                metadata={
                    "error": error_message
                }
            )
            
            return result
        
        # Check for topic drift before analysis
        current_state = {
            "current_task_type": "data_analysis",
            "active_capabilities": ["data_validation", "data_analysis"],
            "current_objectives": [f"Analyze {analysis_type} data"],
            "progress_markers": [f"Validated data with {len(validation_rules)} rules"]
        }
        
        drift_check = check_topic_drift(original_task, current_state)
        if drift_check["has_drift"]:
            logging.warning(f"Topic drift detected: {drift_check}")
            update_journey_state(
                journey_id=journey_id,
                state="drift_detected",
                message="Task may have drifted from original focus",
                metrics=drift_check
            )
            
            # Add drift warning to results
            result = {
                "success": True,
                "validation_result": validation_result,
                "warning": "Task drift detected",
                "drift_analysis": drift_check
            }
            
            complete_journey(
                journey_id=journey_id,
                status="completed_with_warning",
                metadata=result
            )
            
            return result
        
        # Update journey state
        update_journey_state(
            journey_id=journey_id,
            state="analysis_started",
            message=f"Starting data analysis of type: {analysis_type}",
            metrics={
                "analysis_type": analysis_type,
                "data_size": len(str(data)),
                "batch_size": batch_size
            }
        )
        
        # Step 2: Analyze validated data with response management
        try:
            # Import structured outputs agent dynamically
            from Handler.handler_structured_outputs import StructuredOutputsAgent
            analyzer = StructuredOutputsAgent()
            
            # Prepare analysis task with response management
            analysis_task = {
                "data": data,
                "analysis_type": analysis_type,
                "output_format": task.get("output_format", "json"),
                "max_tokens": batch_size,
                "max_response_length": max_response_length
            }
            
            # Execute analysis
            analysis_result = await analyzer.analyze_data(analysis_task)
            
            # Check response length and truncate if necessary
            if isinstance(analysis_result, dict) and "result" in analysis_result:
                result_str = str(analysis_result["result"])
                if len(result_str) > max_response_length:
                    analysis_result["result"] = result_str[:max_response_length] + "... [truncated]"
                    analysis_result["truncated"] = True
                    analysis_result["original_length"] = len(result_str)
            
            # Update journey state
            update_journey_state(
                journey_id=journey_id,
                state="analysis_completed",
                message="Data analysis completed",
                metrics={
                    "analysis_completed": True,
                    "response_length": len(str(analysis_result)),
                    "truncated": analysis_result.get("truncated", False)
                }
            )
            
        except Exception as e:
            error_message = f"Analysis failed: {str(e)}"
            logging.error(error_message)
            
            result = {
                "success": False,
                "error": error_message,
                "validation_result": validation_result,
                "analysis_result": None
            }
            
            complete_journey(
                journey_id=journey_id,
                status="failed",
                metadata={
                    "error": error_message,
                    "validation_result": validation_result
                }
            )
            
            return result
        
        # Combine results
        result = {
            "success": True,
            "validation_result": validation_result,
            "analysis_result": analysis_result,
            "metrics": {
                "response_length": len(str(analysis_result)),
                "truncated": analysis_result.get("truncated", False),
                "batch_size_used": batch_size
            }
        }
        
        # Complete journey
        complete_journey(
            journey_id=journey_id,
            status="completed",
            metadata=result
        )
        
        return result
        
    except Exception as e:
        error_message = f"Workflow execution failed: {str(e)}"
        logging.error(error_message)
        
        result = {
            "success": False,
            "error": error_message
        }
        
        complete_journey(
            journey_id=journey_id,
            status="failed",
            metadata={
                "error": error_message
            }
        )
        
        return result

def route_to_appropriate_system(
    task: Union[str, Dict[str, Any]],
    workspace_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Route a task to the appropriate system based on its type and requirements.
    
    Args:
        task: The task to route (string or dictionary)
        workspace_id: Optional workspace ID for tracking
        
    Returns:
        Dict containing routing result and system selection information
    """
    # Get BoardRoom instance
    boardroom = get_boardroom()
    
    # Generate request ID
    request_id = generate_request_id(task)
    
    if workspace_id is None:
        workspace_id = f"router_{request_id}"
    
    # Try to register router in BoardRoom if the method exists
    system_id = "TaskRouter"
    try:
        if hasattr(boardroom, 'register_system'):
            system_id = boardroom.register_system(
                system_name="TaskRouter",
                system_type="router",
                capabilities=["task_routing", "system_selection"],
                workspace_id=workspace_id
            )
    except Exception as e:
        logging.warning(f"Could not register system in BoardRoom: {str(e)}")
        system_id = "TaskRouter"
    
    # Start tracking journey
    journey_id = track_request_journey(
        request_id=request_id,
        task=task,
        system_id=system_id,
        journey_type="task_routing"
    )
    
    try:
        # Convert string task to dictionary if needed
        if isinstance(task, str):
            task_dict = {
                "task_type": "natural_language",
                "content": task
            }
        else:
            task_dict = task
        
        # Analyze task capabilities using common_utils
        required_capabilities = analyze_task_capabilities(task_dict)
        
        # Update journey state with capabilities
        update_journey_state(
            journey_id=journey_id,
            state="analyzing_task",
            message=f"Analyzing task capabilities",
            metrics={"required_capabilities": required_capabilities}
        )
        
        # Define system mapping based on capabilities
        system_mapping = {
            "DATA_VALIDATION": {
                "system": "DataValidator",
                "handler": "Handler.handler_data_validator",
                "class": "DataValidator",
                "method": "validate_data"
            },
            "DATA_ANALYSIS": {
                "system": "StructuredOutputs",
                "handler": "Handler.handler_structured_outputs",
                "class": "StructuredOutputsAgent",
                "method": "analyze_data"
            },
            "TECHNICAL": {
                "system": "TerminalHandler",
                "handler": "Handler.handler_terminal",
                "class": "TerminalHandler",
                "method": "execute"
            },
            "MANAGEMENT": {
                "system": "StructuredAgentSystem",
                "handler": "Handler.handler_structured_agent_system",
                "class": "StructuredAgentSystem",
                "method": "process_task"
            }
        }
        
        # Select appropriate system based on capabilities
        selected_system = None
        for capability in required_capabilities:
            if capability in system_mapping:
                selected_system = system_mapping[capability]
                break
        
        # Default to Handler Swarm if no specific system matches
        if not selected_system:
            selected_system = {
                "system": "HandlerSwarm",
                "handler": "Handler.handler_swarm",
                "class": "HandlerSwarm",
                "method": "process_request"
            }
        
        # Update journey state with selection
        update_journey_state(
            journey_id=journey_id,
            state="system_selected",
            message=f"Selected system: {selected_system['system']}",
            metrics={
                "selected_system": selected_system['system'],
                "handler_module": selected_system['handler']
            }
        )
        
        # Prepare routing result
        result = {
            "success": True,
            "selected_system": selected_system['system'],
            "handler_info": {
                "module": selected_system['handler'],
                "class": selected_system['class'],
                "method": selected_system['method']
            },
            "task": task_dict,
            "capabilities": required_capabilities,
            "workspace_id": workspace_id
        }
        
        # Complete journey
        complete_journey(
            journey_id=journey_id,
            status="completed",
            metadata=result
        )
        
        return result
        
    except Exception as e:
        error_message = f"Task routing failed: {str(e)}"
        logging.error(error_message)
        
        result = {
            "success": False,
            "error": error_message,
            "workspace_id": workspace_id
        }
        
        complete_journey(
            journey_id=journey_id,
            status="failed",
            metadata={
                "error": error_message
            }
        )
        
        return result

# Create tool functions for the orchestrator agent

async def execute_validated_analysis_workflow_tool(
    data: Dict[str, Any],
    validation_rules: List[str],
    analysis_type: str,
    output_format: str = "json"
) -> Dict[str, Any]:
    """
    Tool for the orchestrator agent to execute the validated analysis workflow.
    
    Args:
        data: The data to validate and analyze
        validation_rules: Rules to validate against
        analysis_type: Type of analysis to perform
        output_format: Format for the output (default: "json")
            
    Returns:
        Dict containing validation and analysis results
    """
    import logging
    
    try:
        # Prepare task
        task = {
            "data": data,
            "validation_rules": validation_rules,
            "analysis_type": analysis_type,
            "output_format": output_format
        }
        
        # Execute workflow with proper await
        result = await execute_validated_analysis_workflow(task)
        return result
    except Exception as e:
        logging.error(f"Error executing validated analysis workflow: {str(e)}")
        return {
            "success": False,
            "error": f"Tool execution failed: {str(e)}",
            "validation_result": None,
            "analysis_result": None
        }

async def route_to_appropriate_system_tool(
    task_content: str,
    task_type: Optional[str] = None
) -> Dict[str, Any]:
    """
    Tool for the orchestrator agent to route a task to the appropriate system.
    
    Args:
        task_content: The content of the task
        task_type: Optional explicit task type
        
    Returns:
        Dict containing routing result and system selection information
    """
    import logging
    
    try:
        # Prepare task
        if task_type:
            task = {
                "task_type": task_type,
                "content": task_content
            }
        else:
            task = task_content
        
        # Execute routing
        result = route_to_appropriate_system(task)
        return result
    except Exception as e:
        logging.error(f"Error routing task to appropriate system: {str(e)}")
        return {
            "success": False,
            "error": f"Tool execution failed: {str(e)}",
            "selected_system": None
        }

def check_topic_drift(original_task: Dict[str, Any], current_state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Check if the current state has drifted from the original task focus.
    
    Args:
        original_task: The original task definition
        current_state: Current execution state
        
    Returns:
        Dict containing drift analysis:
            - has_drift: Boolean indicating if drift detected
            - drift_score: Similarity score (1.0 = perfect alignment)
            - original_focus: Key aspects of original task
            - current_focus: Key aspects of current state
    """
    try:
        # Extract key aspects to compare
        original_focus = {
            "task_type": original_task.get("task_type"),
            "capabilities": original_task.get("capabilities", []),
            "objectives": original_task.get("objectives", []),
            "constraints": original_task.get("constraints", [])
        }
        
        current_focus = {
            "task_type": current_state.get("current_task_type"),
            "capabilities": current_state.get("active_capabilities", []),
            "objectives": current_state.get("current_objectives", []),
            "progress": current_state.get("progress_markers", [])
        }
        
        # Calculate similarity score
        similarity_score = _calculate_task_similarity(original_focus, current_focus)
        
        # Detect drift
        has_drift = similarity_score < TOPIC_DRIFT_THRESHOLD
        
        return {
            "has_drift": has_drift,
            "drift_score": similarity_score,
            "original_focus": original_focus,
            "current_focus": current_focus,
            "threshold": TOPIC_DRIFT_THRESHOLD
        }
    except Exception as e:
        logging.warning(f"Error in topic drift detection: {str(e)}")
        return {
            "has_drift": False,
            "error": str(e)
        }

def _calculate_task_similarity(original: Dict, current: Dict) -> float:
    """
    Calculate similarity score between original task and current state.
    
    Args:
        original: Original task focus points
        current: Current state focus points
        
    Returns:
        Float between 0.0 and 1.0 (1.0 = perfect match)
    """
    try:
        # Check task type alignment
        type_match = original["task_type"] == current["task_type"]
        
        # Check capability overlap
        capability_overlap = len(
            set(original["capabilities"]) & 
            set(current["capabilities"])
        ) / max(
            len(original["capabilities"]), 
            len(current["capabilities"]), 
            1
        )
        
        # Check objective alignment
        objective_similarity = _compare_objectives(
            original["objectives"],
            current.get("objectives", []) + current.get("progress", [])
        )
        
        # Weight the components
        weights = {
            "task_type": 0.3,
            "capabilities": 0.3,
            "objectives": 0.4
        }
        
        similarity = (
            (type_match * weights["task_type"]) +
            (capability_overlap * weights["capabilities"]) +
            (objective_similarity * weights["objectives"])
        )
        
        return round(similarity, 2)
        
    except Exception as e:
        logging.warning(f"Error calculating task similarity: {str(e)}")
        return 1.0  # Default to no drift on error

def _compare_objectives(original_objectives: List, current_objectives: List) -> float:
    """Compare objective lists for similarity."""
    if not original_objectives or not current_objectives:
        return 1.0
        
    try:
        # Convert to sets for comparison
        original_set = set(str(obj).lower() for obj in original_objectives)
        current_set = set(str(obj).lower() for obj in current_objectives)
        
        # Calculate Jaccard similarity
        intersection = len(original_set & current_set)
        union = len(original_set | current_set)
        
        return intersection / union if union > 0 else 1.0
        
    except Exception as e:
        logging.warning(f"Error comparing objectives: {str(e)}")
        return 1.0 