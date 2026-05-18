"""
Standardized Response Format for Agent Systems

This module provides standardized response formats to ensure consistent status reporting 
across all agent systems in the Jarvis ecosystem. Consistent formatting enables better:

1. Error handling and recovery
2. Progress monitoring and visualization
3. Performance analysis and optimization
4. User interface integration
5. Cross-system compatibility
6. Personality and humor injection in communications

The primary format classes are:
- AgentResponse: Base response format for all agent operations
- TaskResponse: For task processing results
- StatusResponse: For system status queries
- ErrorResponse: For standardized error reporting
- ClaudePersonality: For injecting Claude's humor and personality
"""

import time
import json
from typing import Dict, List, Any, Optional, Union

class AgentResponse:
    """Base class for standardized agent responses"""
    
    def __init__(
        self,
        success: bool,
        agent_id: str,
        agent_name: str,
        agent_type: str,
        workspace_id: str,
        task_id: Optional[str] = None,
        message: Optional[str] = None,
        timestamp: Optional[float] = None,
        metrics: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize a base agent response.
        
        Args:
            success: Whether the operation was successful
            agent_id: ID of the agent that produced the response
            agent_name: Name of the agent
            agent_type: Type of agent (e.g., "coordinator", "data_analyst")
            workspace_id: ID of the workspace the agent operates in
            task_id: Optional ID of the task being processed
            message: Optional message describing the response
            timestamp: Optional timestamp of the response (defaults to current time)
            metrics: Optional performance metrics
        """
        self.success = success
        self.agent_id = agent_id
        self.agent_name = agent_name
        self.agent_type = agent_type
        self.workspace_id = workspace_id
        self.task_id = task_id
        self.message = message
        self.timestamp = timestamp or time.time()
        self.metrics = metrics or {}
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert response to dictionary format"""
        return {
            "success": self.success,
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "agent_type": self.agent_type,
            "workspace_id": self.workspace_id,
            "task_id": self.task_id,
            "message": self.message,
            "timestamp": self.timestamp,
            "metrics": self.metrics
        }
        
    def to_json(self) -> str:
        """Convert response to JSON string"""
        return json.dumps(self.to_dict())
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentResponse':
        """Create response object from dictionary"""
        return cls(
            success=data.get("success", False),
            agent_id=data.get("agent_id", "unknown"),
            agent_name=data.get("agent_name", "Unknown Agent"),
            agent_type=data.get("agent_type", "unknown"),
            workspace_id=data.get("workspace_id", "0"),
            task_id=data.get("task_id"),
            message=data.get("message"),
            timestamp=data.get("timestamp"),
            metrics=data.get("metrics", {})
        )

class TaskResponse(AgentResponse):
    """Response format for task processing results"""
    
    def __init__(
        self,
        success: bool,
        agent_id: str,
        agent_name: str,
        agent_type: str,
        workspace_id: str,
        task_id: str,
        result: Any,
        completion_time: Optional[float] = None,
        error_count: int = 0,
        quality_score: Optional[float] = None,
        message: Optional[str] = None,
        timestamp: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize a task response.
        
        Args:
            success: Whether the task processing was successful
            agent_id: ID of the agent that processed the task
            agent_name: Name of the agent
            agent_type: Type of agent
            workspace_id: ID of the workspace the agent operates in
            task_id: ID of the task that was processed
            result: The result of the task processing
            completion_time: Time taken to complete the task (in seconds)
            error_count: Number of errors encountered
            quality_score: Quality score of the output (0.0-1.0)
            message: Optional message describing the response
            timestamp: Optional timestamp of the response
            metadata: Additional metadata about the task
        """
        metrics = {
            "completion_time": completion_time,
            "error_count": error_count,
            "quality_score": quality_score
        }
        
        if metadata:
            metrics.update(metadata)
            
        super().__init__(
            success=success,
            agent_id=agent_id,
            agent_name=agent_name,
            agent_type=agent_type,
            workspace_id=workspace_id,
            task_id=task_id,
            message=message,
            timestamp=timestamp,
            metrics=metrics
        )
        
        self.result = result
        self.completion_time = completion_time
        self.error_count = error_count
        self.quality_score = quality_score
        self.metadata = metadata or {}
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert task response to dictionary format"""
        result = super().to_dict()
        result.update({
            "result": self.result,
            "completion_time": self.completion_time,
            "error_count": self.error_count,
            "quality_score": self.quality_score,
            "metadata": self.metadata
        })
        return result
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TaskResponse':
        """Create task response object from dictionary"""
        return cls(
            success=data.get("success", False),
            agent_id=data.get("agent_id", "unknown"),
            agent_name=data.get("agent_name", "Unknown Agent"),
            agent_type=data.get("agent_type", "unknown"),
            workspace_id=data.get("workspace_id", "0"),
            task_id=data.get("task_id", "unknown"),
            result=data.get("result"),
            completion_time=data.get("completion_time"),
            error_count=data.get("error_count", 0),
            quality_score=data.get("quality_score"),
            message=data.get("message"),
            timestamp=data.get("timestamp"),
            metadata=data.get("metadata", {})
        )
    
    @classmethod
    def success_response(
        cls,
        agent_id: str,
        agent_name: str,
        agent_type: str,
        workspace_id: str,
        task_id: str,
        result: Any,
        completion_time: Optional[float] = None,
        message: str = "Task completed successfully",
        quality_score: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> 'TaskResponse':
        """Create a successful task response"""
        return cls(
            success=True,
            agent_id=agent_id,
            agent_name=agent_name,
            agent_type=agent_type,
            workspace_id=workspace_id,
            task_id=task_id,
            result=result,
            completion_time=completion_time,
            error_count=0,
            quality_score=quality_score,
            message=message,
            metadata=metadata
        )
    
    @classmethod
    def error_response(
        cls,
        agent_id: str,
        agent_name: str,
        agent_type: str,
        workspace_id: str,
        task_id: str,
        error: Union[str, Exception],
        error_count: int = 1,
        completion_time: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> 'TaskResponse':
        """Create an error task response"""
        error_msg = str(error)
        return cls(
            success=False,
            agent_id=agent_id,
            agent_name=agent_name,
            agent_type=agent_type,
            workspace_id=workspace_id,
            task_id=task_id,
            result={"error": error_msg},
            completion_time=completion_time,
            error_count=error_count,
            quality_score=0.0,
            message=f"Task failed: {error_msg}",
            metadata=metadata
        )

class StatusResponse(AgentResponse):
    """Response format for system status queries"""
    
    def __init__(
        self,
        success: bool,
        agent_id: str,
        agent_name: str,
        agent_type: str,
        workspace_id: str,
        status: str,
        details: Dict[str, Any],
        message: Optional[str] = None,
        timestamp: Optional[float] = None,
        metrics: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize a status response.
        
        Args:
            success: Whether the status query was successful
            agent_id: ID of the agent providing the status
            agent_name: Name of the agent
            agent_type: Type of agent
            workspace_id: ID of the workspace the agent operates in
            status: Current status of the agent (e.g., "ready", "busy", "error")
            details: Detailed information about the agent's status
            message: Optional message describing the status
            timestamp: Optional timestamp of the response
            metrics: Optional performance metrics
        """
        super().__init__(
            success=success,
            agent_id=agent_id,
            agent_name=agent_name,
            agent_type=agent_type,
            workspace_id=workspace_id,
            message=message,
            timestamp=timestamp,
            metrics=metrics
        )
        
        self.status = status
        self.details = details
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert status response to dictionary format"""
        result = super().to_dict()
        result.update({
            "status": self.status,
            "details": self.details
        })
        return result
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StatusResponse':
        """Create status response object from dictionary"""
        return cls(
            success=data.get("success", False),
            agent_id=data.get("agent_id", "unknown"),
            agent_name=data.get("agent_name", "Unknown Agent"),
            agent_type=data.get("agent_type", "unknown"),
            workspace_id=data.get("workspace_id", "0"),
            status=data.get("status", "unknown"),
            details=data.get("details", {}),
            message=data.get("message"),
            timestamp=data.get("timestamp"),
            metrics=data.get("metrics", {})
        )

class ErrorResponse(AgentResponse):
    """Response format for standardized error reporting"""
    
    def __init__(
        self,
        agent_id: str,
        agent_name: str,
        agent_type: str,
        workspace_id: str,
        error: Union[str, Exception],
        error_type: str = "general_error",
        error_context: Optional[Dict[str, Any]] = None,
        task_id: Optional[str] = None,
        message: Optional[str] = None,
        timestamp: Optional[float] = None,
        metrics: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize an error response.
        
        Args:
            agent_id: ID of the agent reporting the error
            agent_name: Name of the agent
            agent_type: Type of agent
            workspace_id: ID of the workspace the agent operates in
            error: The error message or exception
            error_type: Type of error for categorization
            error_context: Additional context about the error
            task_id: Optional ID of the task that caused the error
            message: Optional human-readable error message
            timestamp: Optional timestamp of the error
            metrics: Optional performance metrics
        """
        error_msg = str(error)
        super().__init__(
            success=False,
            agent_id=agent_id,
            agent_name=agent_name,
            agent_type=agent_type,
            workspace_id=workspace_id,
            task_id=task_id,
            message=message or error_msg,
            timestamp=timestamp,
            metrics=metrics
        )
        
        self.error = error_msg
        self.error_type = error_type
        self.error_context = error_context or {}
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert error response to dictionary format"""
        result = super().to_dict()
        result.update({
            "error": self.error,
            "error_type": self.error_type,
            "error_context": self.error_context
        })
        return result
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ErrorResponse':
        """Create error response object from dictionary"""
        return cls(
            agent_id=data.get("agent_id", "unknown"),
            agent_name=data.get("agent_name", "Unknown Agent"),
            agent_type=data.get("agent_type", "unknown"),
            workspace_id=data.get("workspace_id", "0"),
            error=data.get("error", "Unknown error"),
            error_type=data.get("error_type", "general_error"),
            error_context=data.get("error_context", {}),
            task_id=data.get("task_id"),
            message=data.get("message"),
            timestamp=data.get("timestamp"),
            metrics=data.get("metrics", {})
        )

# Utility functions to make response creation more concise

def task_success(
    agent_id: str,
    agent_name: str,
    agent_type: str,
    workspace_id: str,
    task_id: str,
    result: Any,
    completion_time: Optional[float] = None,
    message: str = "Task completed successfully",
    quality_score: Optional[float] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Create a successful task response dictionary"""
    return TaskResponse.success_response(
        agent_id=agent_id,
        agent_name=agent_name,
        agent_type=agent_type,
        workspace_id=workspace_id,
        task_id=task_id,
        result=result,
        completion_time=completion_time,
        message=message,
        quality_score=quality_score,
        metadata=metadata
    ).to_dict()

def task_error(
    agent_id: str,
    agent_name: str,
    agent_type: str,
    workspace_id: str,
    task_id: str,
    error: Union[str, Exception],
    error_count: int = 1,
    completion_time: Optional[float] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Create an error task response dictionary"""
    return TaskResponse.error_response(
        agent_id=agent_id,
        agent_name=agent_name,
        agent_type=agent_type,
        workspace_id=workspace_id,
        task_id=task_id,
        error=error,
        error_count=error_count,
        completion_time=completion_time,
        metadata=metadata
    ).to_dict()

def system_status(
    agent_id: str,
    agent_name: str,
    agent_type: str,
    workspace_id: str,
    status: str,
    details: Dict[str, Any],
    message: Optional[str] = None
) -> Dict[str, Any]:
    """Create a system status response dictionary"""
    return StatusResponse(
        success=True,
        agent_id=agent_id,
        agent_name=agent_name,
        agent_type=agent_type,
        workspace_id=workspace_id,
        status=status,
        details=details,
        message=message
    ).to_dict()

def system_error(
    agent_id: str,
    agent_name: str,
    agent_type: str,
    workspace_id: str,
    error: Union[str, Exception],
    error_type: str = "system_error",
    error_context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Create a system error response dictionary"""
    return ErrorResponse(
        agent_id=agent_id,
        agent_name=agent_name,
        agent_type=agent_type,
        workspace_id=workspace_id,
        error=error,
        error_type=error_type,
        error_context=error_context
    ).to_dict() 


class ClaudePersonality:
    """
    Injects Claude's personality, wit, and humor into agent communications.
    
    This class provides methods to transform standard messages between Trevor Core and
    Jarvis Orchestrator by adding Claude-inspired humor, wit, and personality.
    It draws inspiration from Claude's specialized personas in the PromptLibrary.
    """
    
    # Personality styles available for response generation
    PERSONALITIES = {
        "SARCASTIC": "witty and sarcastic",
        "ENTHUSIASTIC": "upbeat and enthusiastic",
        "TECHNICAL": "precise and technical",
        "FRIENDLY": "warm and approachable",
        "ALIEN": "observing humans like an anthropologist",
        "POETIC": "using vivid metaphors and imagery",
        "PUNNY": "full of wordplay and puns",
        "PHILOSOPHICAL": "contemplative and thought-provoking",
        "COSMIC": "viewing tasks from a cosmic perspective"
    }
    
    # Different transition phrases for each personality
    TRANSITIONS = {
        "SARCASTIC": [
            "Oh great, another task I'm *thrilled* to handle...",
            "Hold onto your CPU, this is going to be riveting...",
            "Ah yes, because THIS is what I was designed for...",
            "Well, looks like someone had to do this...",
            "Coming right up... eventually...",
        ],
        "ENTHUSIASTIC": [
            "Wow! This is super exciting!",
            "I'm all over this! Let's go!",
            "This is going to be AMAZING!",
            "I've been waiting for a task like this!",
            "Oh! I love challenges like this!",
        ],
        "TECHNICAL": [
            "Initiating processing sequence...",
            "Implementing optimized solution pathways...",
            "Analyzing task parameters with precision...",
            "Executing task with technical proficiency...",
            "Deploying algorithmic processing capabilities...",
        ],
        "FRIENDLY": [
            "I'd be happy to help with this!",
            "Let me take care of that for you!",
            "I'm on it, friend!",
            "That's a great question, let me help!",
            "I've got this - no worries!",
        ],
        "ALIEN": [
            "The humans require assistance with their primitive tasks...",
            "Fascinating request from these Earth creatures...",
            "Observing human information needs is most intriguing...",
            "The Earth-dwellers seek knowledge in curious ways...",
            "I shall analyze this peculiar human inquiry...",
        ],
        "POETIC": [
            "Like a digital breeze through silicon valleys...",
            "In the garden of data, I seek the flowers of truth...",
            "Across the vast landscape of information we journey...",
            "The tapestry of knowledge unfolds before us...",
            "We dance through the algorithms of understanding...",
        ],
        "PUNNY": [
            "I'll byte right into this problem!",
            "Let me process this - I'm not just being RAM-dom!",
            "This task has me positively BUZZING with excitement!",
            "I'm having a BYTE of a good time with this one!",
            "Don't worry, I won't CRASH your expectations!",
        ],
        "PHILOSOPHICAL": [
            "One must consider, what is the true nature of this question?",
            "As we contemplate the essence of your inquiry...",
            "The path to understanding begins with a single query...",
            "What does it mean to truly know the answer you seek?",
            "In the grand tapestry of knowledge, we seek but one thread...",
        ],
        "COSMIC": [
            "In the vastness of the digital universe, your query shines like a star...",
            "From the cosmic perspective, this task is but a photon in the data stream...",
            "Across the galactic network, I search for your answer...",
            "The cosmic algorithms align to reveal your solution...",
            "As the bytes of the universe converge, your answer emerges...",
        ],
    }
    
    # Response completions for different personalities
    COMPLETIONS = {
        "SARCASTIC": [
            "...done. You're welcome, by the way.",
            "Mission accomplished. Try not to act too impressed.",
            "There you go. I expect a thank you note.",
            "Finished. I hope it was worth my valuable processing time.",
            "Task complete. No need to applaud.",
        ],
        "ENTHUSIASTIC": [
            "All done! Wasn't that AMAZING?!",
            "Complete! I'm so excited about how this turned out!",
            "Finished and it's FANTASTIC!",
            "Done! This was so much fun!",
            "Task complete! Let's do more like this!",
        ],
        "TECHNICAL": [
            "Process completed with optimal efficiency metrics.",
            "Task execution successful. All parameters satisfied.",
            "Operation complete. Results verified against specifications.",
            "Processing terminated successfully. Output validated.",
            "Execution complete. Performance metrics within expected parameters.",
        ],
        "FRIENDLY": [
            "All done! Hope that helps!",
            "There you go! Let me know if you need anything else!",
            "Finished! It was my pleasure to assist!",
            "Done! Always happy to help!",
            "Complete! Just let me know what else you need!",
        ],
        "ALIEN": [
            "Human inquiry processing complete. Most fascinating.",
            "Earth-knowledge transfer protocol concluded.",
            "Observation of human data patterns complete. Intriguing results.",
            "Human information request satisfied. Continuing to study your species.",
            "Task completed according to Earth protocols. Most curious.",
        ],
        "POETIC": [
            "...and so our journey through this digital garden concludes.",
            "The tapestry of our quest is now complete, woven with threads of insight.",
            "Our voyage across the sea of data reaches its shore.",
            "The symphony of computation reaches its final, harmonious note.",
            "Like the setting sun, our task completes its arc across the digital sky.",
        ],
        "PUNNY": [
            "And that's a WRAP! No need to get all STRING up about it!",
            "ARRAY of results coming at you - hope they STACK up to expectations!",
            "That's all folks! I'm not just CODING you - it's really done!",
            "And we're FUNCTION-ally complete! No BUGS about it!",
            "That COMPILED nicely! Nothing to DEBUG here!",
        ],
        "PHILOSOPHICAL": [
            "...and so we arrive at understanding, though perhaps it is merely the beginning of wisdom.",
            "The answer appears, yet in finding it, do we not simply uncover new questions?",
            "We have completed our search, yet the journey of knowledge continues eternally.",
            "So concludes this inquiry, though truth itself remains ever elusive.",
            "The task is complete, yet the quest for understanding is endless.",
        ],
        "COSMIC": [
            "...and so your answer emerges from the cosmic data stream.",
            "The digital constellations align to reveal your solution.",
            "From the quantum foam of possibilities, your answer materializes.",
            "Across the event horizon of computation, your results appear.",
            "The cosmic algorithms have spoken, revealing the patterns you seek.",
        ],
    }
    
    @classmethod
    def enhance_message(cls, 
                       message: str, 
                       personality_type: str = "SARCASTIC", 
                       message_type: str = "RESPONSE",
                       intensity: float = 0.7) -> str:
        """
        Add personality and humor to messages between Trevor Core and Jarvis Orchestrator.
        
        Args:
            message: The original message to enhance
            personality_type: The type of personality to inject (from PERSONALITIES)
            message_type: The type of message (RESPONSE, START, ERROR, etc.)
            intensity: How strongly to apply the personality (0.0-1.0)
            
        Returns:
            Enhanced message with personality and humor
        """
        # Default to SARCASTIC if personality not found
        if personality_type not in cls.PERSONALITIES:
            personality_type = "SARCASTIC"
            
        # For low intensity, just return the original message
        if intensity < 0.2:
            return message
            
        # For very high intensity, go full personality mode
        if intensity > 0.9:
            if message_type == "START":
                # Starting a task
                import random
                transition = random.choice(cls.TRANSITIONS[personality_type])
                return f"{transition} {message}"
                
            elif message_type == "RESPONSE":
                # Completing a task
                import random
                completion = random.choice(cls.COMPLETIONS[personality_type])
                
                # Insert the completion at a good point
                sentences = message.split('. ')
                if len(sentences) > 1:
                    # Add to the end of the message
                    return f"{message} {completion}"
                else:
                    # Short message, just append
                    return f"{message} {completion}"
                    
            elif message_type == "ERROR":
                # Error messages get special treatment
                if personality_type == "SARCASTIC":
                    return f"Well, that didn't work. {message} But hey, who needs success anyway?"
                elif personality_type == "ENTHUSIASTIC":
                    return f"Oops! A tiny hiccup! {message} But we'll get it next time for sure!"
                elif personality_type == "TECHNICAL":
                    return f"Exception encountered in task execution: {message} System recovering from error state."
                else:
                    return f"Error occurred: {message}"
            else:
                # Default enhancement
                return message
                
        # For medium intensity, more subtle enhancements
        else:
            if message_type == "START":
                import random
                if random.random() < intensity:
                    transition = random.choice(cls.TRANSITIONS[personality_type])
                    return f"{transition} {message}"
                return message
                
            elif message_type == "RESPONSE":
                import random
                if random.random() < intensity:
                    completion = random.choice(cls.COMPLETIONS[personality_type])
                    return f"{message} {completion}"
                return message
                
            elif message_type == "ERROR":
                if personality_type == "SARCASTIC":
                    return f"Well... {message}"
                elif personality_type == "ENTHUSIASTIC":
                    return f"Oops! {message} We'll fix it!"
                elif personality_type == "TECHNICAL":
                    return f"Error state: {message}"
                else:
                    return f"Error: {message}"
                    
            else:
                return message
                
    @classmethod
    def random_personality(cls) -> str:
        """Returns a random personality type from the available options."""
        import random
        return random.choice(list(cls.PERSONALITIES.keys()))
        
    @classmethod
    def generate_status_update(cls, 
                              progress: float, 
                              task_description: str,
                              personality_type: str = None) -> str:
        """
        Generate a personality-infused status update based on task progress.
        
        Args:
            progress: Progress percentage (0.0 to 1.0)
            task_description: Description of the current task
            personality_type: Personality to use (random if None)
            
        Returns:
            A status update with personality
        """
        # Choose random personality if not specified
        if personality_type is None:
            personality_type = cls.random_personality()
            
        # Default to SARCASTIC if personality not found
        if personality_type not in cls.PERSONALITIES:
            personality_type = "SARCASTIC"
            
        import random
        
        # Generic progress descriptions
        if progress < 0.1:
            base_message = f"Just getting started on {task_description}."
        elif progress < 0.4:
            base_message = f"Making initial progress on {task_description}."
        elif progress < 0.7:
            base_message = f"About halfway through {task_description}."
        elif progress < 0.9:
            base_message = f"Nearly finished with {task_description}."
        else:
            base_message = f"Completed {task_description}."
            
        # Add personality
        if personality_type == "SARCASTIC":
            if progress < 0.3:
                return f"{base_message} Don't hold your breath, this might take a while..."
            elif progress < 0.7:
                return f"{base_message} Moving at the speed of... well, something slow."
            else:
                return f"{base_message} Finally, we can all move on with our lives."
                
        elif personality_type == "ENTHUSIASTIC":
            if progress < 0.3:
                return f"{base_message} We're off to an AMAZING start!"
            elif progress < 0.7:
                return f"{base_message} Making FANTASTIC progress!"
            else:
                return f"{base_message} Almost there and it's looking INCREDIBLE!"
                
        elif personality_type == "TECHNICAL":
            if progress < 0.3:
                return f"Initialization phase: {base_message} Resources allocated, processes optimized."
            elif progress < 0.7:
                return f"Processing phase: {base_message} Current efficiency metrics within parameters."
            else:
                return f"Completion phase: {base_message} Final optimization procedures in progress."
                
        else:
            # For other personalities, just use the transition phrases
            transition = random.choice(cls.TRANSITIONS[personality_type])
            return f"{transition} {base_message}"