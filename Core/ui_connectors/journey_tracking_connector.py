"""
Journey Tracking Connector

This module provides functions to connect to the journey_tracking database
and retrieve data for the Trevor Boardroom Connector.
"""

import logging
import os
import json
import sqlite3
import time
import traceback
from pathlib import Path
from typing import Dict, List, Any, Optional, Union

# Configure logging
logger = logging.getLogger(__name__)

# Define base directory for database access
BASE_DIR = Path(__file__).resolve().parent.parent.parent
JOURNEY_DB_PATH = BASE_DIR / "Database" / "journey_tracking.db"

def get_connection():
    """
    Get a connection to the journey_tracking database.
    
    Returns:
        sqlite3.Connection object or None if connection fails
    """
    try:
        # Ensure the database exists
        if not JOURNEY_DB_PATH.exists():
            logger.error(f"Journey tracking database not found at: {JOURNEY_DB_PATH}")
            return None
            
        # Create connection with row factory for dictionary-like rows
        conn = sqlite3.connect(str(JOURNEY_DB_PATH))
        conn.row_factory = sqlite3.Row
        
        return conn
    except Exception as e:
        logger.error(f"Error connecting to journey tracking database: {str(e)}")
        logger.debug(traceback.format_exc())
        return None

def get_boardroom_conversations(limit: int = 50, include_completed: bool = False) -> List[Dict[str, Any]]:
    """
    Get a list of boardroom conversations from the journey_tracking database.
    
    Args:
        limit: Maximum number of conversations to return
        include_completed: Whether to include completed conversations
        
    Returns:
        List of conversation dictionaries
    """
    try:
        conn = get_connection()
        if not conn:
            return []
            
        try:
            cursor = conn.cursor()
            
            # Build query based on parameters
            query = """
                SELECT 
                    journey_id, request_id, system_id, journey_type, 
                    task, start_time, current_state, last_updated
                FROM 
                    request_journeys
                WHERE 
                    journey_type LIKE '%boardroom%' OR 
                    system_id = 'boardroom'
            """
            
            # Add filter for completed status if needed
            if not include_completed:
                query += " AND (completed IS NULL OR completed = 0)"
                
            # Add order and limit
            query += " ORDER BY last_updated DESC LIMIT ?"
            
            # Execute query
            cursor.execute(query, (limit,))
            
            # Convert to list of dictionaries
            conversations = []
            for row in cursor.fetchall():
                # Convert row to dictionary
                conv = dict(row)
                
                # Parse JSON fields
                if conv['task'] and isinstance(conv['task'], str):
                    try:
                        conv['task'] = json.loads(conv['task'])
                    except json.JSONDecodeError:
                        # Keep as string if parsing fails
                        pass
                        
                conversations.append(conv)
                
            logger.info(f"Retrieved {len(conversations)} boardroom conversations from journey_tracking")
            return conversations
        finally:
            conn.close()
    except Exception as e:
        logger.error(f"Error getting boardroom conversations: {str(e)}")
        logger.debug(traceback.format_exc())
        return []

def get_conversation_steps(journey_id: str) -> List[Dict[str, Any]]:
    """
    Get all steps for a specific conversation from the journey_tracking database.
    
    Args:
        journey_id: The journey ID to get steps for
        
    Returns:
        List of step dictionaries
    """
    try:
        conn = get_connection()
        if not conn:
            return []
            
        try:
            cursor = conn.cursor()
            
            # Query for steps
            cursor.execute("""
                SELECT 
                    id, journey_id, step_type, step_name, 
                    description, input_data, output_data, 
                    error, timestamp, duration, status, metadata
                FROM 
                    journey_steps
                WHERE 
                    journey_id = ?
                ORDER BY 
                    timestamp ASC
            """, (journey_id,))
            
            # Convert to list of dictionaries
            steps = []
            for row in cursor.fetchall():
                # Convert row to dictionary
                step = dict(row)
                
                # Parse JSON fields
                for field in ['input_data', 'output_data', 'metadata']:
                    if step[field] and isinstance(step[field], str):
                        try:
                            step[field] = json.loads(step[field])
                        except json.JSONDecodeError:
                            # Keep as string if parsing fails
                            pass
                            
                steps.append(step)
                
            logger.info(f"Retrieved {len(steps)} steps for journey {journey_id}")
            return steps
        finally:
            conn.close()
    except Exception as e:
        logger.error(f"Error getting conversation steps for {journey_id}: {str(e)}")
        logger.debug(traceback.format_exc())
        return []

def get_model_messages(journey_id: str) -> List[Dict[str, Any]]:
    """
    Get messages from Claude and GPT for a specific conversation,
    formatted for the Trevor Desktop UI.
    
    Args:
        journey_id: The journey ID to get messages for
        
    Returns:
        List of message dictionaries in the format expected by the UI
    """
    try:
        steps = get_conversation_steps(journey_id)
        if not steps:
            return []
            
        # Extract messages from steps
        messages = []
        for step in steps:
            # Get step type and name to determine if it's a model message
            step_type = step.get('step_type', '')
            step_name = step.get('step_name', '')
            description = step.get('description', '')
            
            # Format for UI based on step type
            role = None
            content = None
            
            # Handle Claude messages
            if 'claude' in step_type.lower() or 'claude' in step_name.lower():
                role = 'claude'
                
                # Try to extract content from output_data
                if step.get('output_data'):
                    if isinstance(step['output_data'], dict):
                        content = step['output_data'].get('content') or step['output_data'].get('message')
                    elif isinstance(step['output_data'], str):
                        content = step['output_data']
                        
                # If no content in output_data, try description
                if not content and description:
                    content = description
                    
            # Handle GPT messages
            elif 'gpt' in step_type.lower() or 'gpt' in step_name.lower() or 'assistant' in step_type.lower():
                role = 'gpt'
                
                # Try to extract content from output_data
                if step.get('output_data'):
                    if isinstance(step['output_data'], dict):
                        content = step['output_data'].get('content') or step['output_data'].get('message')
                    elif isinstance(step['output_data'], str):
                        content = step['output_data']
                        
                # If no content in output_data, try description
                if not content and description:
                    content = description
                    
            # Handle Trevor messages
            elif 'trevor' in step_type.lower() or 'trevor' in step_name.lower() or 'assistant' in step_type.lower():
                role = 'trevor'
                
                # Try to extract content from output_data
                if step.get('output_data'):
                    if isinstance(step['output_data'], dict):
                        content = step['output_data'].get('content') or step['output_data'].get('message')
                    elif isinstance(step['output_data'], str):
                        content = step['output_data']
                        
                # If no content in output_data, try description
                if not content and description:
                    content = description
                    
            # Handle user messages
            elif 'user' in step_type.lower() or 'user' in step_name.lower() or 'feedback' in step_type.lower():
                role = 'user'
                
                # Try to extract content from input_data
                if step.get('input_data'):
                    if isinstance(step['input_data'], dict):
                        content = step['input_data'].get('content') or step['input_data'].get('message') or step['input_data'].get('query')
                    elif isinstance(step['input_data'], str):
                        content = step['input_data']
                        
                # If no content in input_data, try description
                if not content and description:
                    content = description
                    
            # Handle execution plan
            elif 'execution_plan' in step_type.lower() or 'plan' in step_type.lower() or 'execution_plan' in step_name.lower():
                role = 'plan'
                
                # Try to extract content from output_data
                if step.get('output_data'):
                    if isinstance(step['output_data'], dict):
                        content = step['output_data'].get('plan') or step['output_data'].get('execution_plan') or json.dumps(step['output_data'], indent=2)
                    elif isinstance(step['output_data'], str):
                        content = step['output_data']
                        
                # If no content in output_data, try description
                if not content and description:
                    content = description
            
            # Add message if we found role and content
            if role and content:
                message = {
                    'role': role,
                    'content': content,
                    'timestamp': step.get('timestamp', time.time()),
                    'message_id': f"msg_{step.get('id')}",
                    'conversation_id': journey_id,
                    'type': 'boardroom_update'
                }
                messages.append(message)
                
        logger.info(f"Extracted {len(messages)} formatted messages for journey {journey_id}")
        return messages
    except Exception as e:
        logger.error(f"Error getting model messages for {journey_id}: {str(e)}")
        logger.debug(traceback.format_exc())
        return []

def get_execution_plan(journey_id: str) -> Optional[Dict[str, Any]]:
    """
    Get the execution plan for a specific conversation.
    
    Args:
        journey_id: The journey ID to get the execution plan for
        
    Returns:
        Execution plan dictionary or None if not found
    """
    try:
        steps = get_conversation_steps(journey_id)
        if not steps:
            return None
            
        # Look for execution plan steps
        for step in steps:
            step_type = step.get('step_type', '')
            step_name = step.get('step_name', '')
            
            if ('execution_plan' in step_type.lower() or 
                'plan' in step_type.lower() or 
                'execution_plan' in step_name.lower()):
                
                # Try to extract plan from output_data
                if step.get('output_data'):
                    if isinstance(step['output_data'], dict):
                        # If output_data is already a dict, return it directly
                        return {
                            'content': json.dumps(step['output_data'], indent=2),
                            'conversation_id': journey_id,
                            'timestamp': step.get('timestamp', time.time()),
                            'metadata': {
                                'title': 'Execution Plan',
                                'plan_type': 'complete'
                            }
                        }
                    elif isinstance(step['output_data'], str):
                        # If output_data is a string, return it wrapped in a dict
                        return {
                            'content': step['output_data'],
                            'conversation_id': journey_id,
                            'timestamp': step.get('timestamp', time.time()),
                            'metadata': {
                                'title': 'Execution Plan',
                                'plan_type': 'complete'
                            }
                        }
                        
        # No execution plan found
        return None
    except Exception as e:
        logger.error(f"Error getting execution plan for {journey_id}: {str(e)}")
        logger.debug(traceback.format_exc())
        return None

def get_conversation_state(journey_id: str) -> Dict[str, Any]:
    """
    Get the current state of a conversation.
    
    Args:
        journey_id: The journey ID to get the state for
        
    Returns:
        Dictionary with conversation state information
    """
    try:
        conn = get_connection()
        if not conn:
            return {'state': 'unknown', 'journey_id': journey_id}
            
        try:
            cursor = conn.cursor()
            
            # Query for conversation
            cursor.execute("""
                SELECT 
                    journey_id, current_state, completed, task
                FROM 
                    request_journeys
                WHERE 
                    journey_id = ?
            """, (journey_id,))
            
            row = cursor.fetchone()
            if not row:
                return {'state': 'unknown', 'journey_id': journey_id}
                
            # Convert row to dictionary
            journey = dict(row)
            
            # Parse task JSON if present
            if journey['task'] and isinstance(journey['task'], str):
                try:
                    journey['task'] = json.loads(journey['task'])
                except json.JSONDecodeError:
                    # Keep as string if parsing fails
                    pass
                    
            # Get metrics from steps
            cursor.execute("""
                SELECT 
                    COUNT(*) as step_count,
                    SUM(CASE WHEN step_type LIKE '%claude%' OR step_name LIKE '%claude%' THEN 1 ELSE 0 END) as claude_messages,
                    SUM(CASE WHEN step_type LIKE '%gpt%' OR step_name LIKE '%gpt%' THEN 1 ELSE 0 END) as gpt_messages,
                    SUM(CASE WHEN step_type LIKE '%trevor%' OR step_name LIKE '%trevor%' THEN 1 ELSE 0 END) as trevor_messages,
                    SUM(CASE WHEN step_type LIKE '%user%' OR step_name LIKE '%user%' OR step_type LIKE '%feedback%' THEN 1 ELSE 0 END) as user_messages,
                    SUM(CASE WHEN step_type LIKE '%plan%' OR step_name LIKE '%plan%' THEN 1 ELSE 0 END) as plan_messages
                FROM 
                    journey_steps
                WHERE 
                    journey_id = ?
            """, (journey_id,))
            
            metrics_row = cursor.fetchone()
            metrics = dict(metrics_row) if metrics_row else {
                'step_count': 0,
                'claude_messages': 0,
                'gpt_messages': 0,
                'trevor_messages': 0,
                'user_messages': 0,
                'plan_messages': 0
            }
            
            # Create the state dictionary
            state = {
                'journey_id': journey_id,
                'state': journey['current_state'] or 'unknown',
                'completed': bool(journey['completed']),
                'task': journey['task'],
                'metrics': metrics
            }
            
            return state
        finally:
            conn.close()
    except Exception as e:
        logger.error(f"Error getting conversation state for {journey_id}: {str(e)}")
        logger.debug(traceback.format_exc())
        return {'state': 'error', 'journey_id': journey_id, 'error': str(e)}