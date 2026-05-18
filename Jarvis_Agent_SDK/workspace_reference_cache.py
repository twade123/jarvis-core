"""
Workspace Reference Cache System

This module implements a high-performance caching system for storing and retrieving
successful workspace execution patterns. It maintains a fixed-size cache of the
best-performing workspace examples to use as references for future similar requests.

Key features:
- Maintains only the highest-scoring workspace examples (1000-2000 entries)
- Uses vector embeddings for fast similarity search
- Stores execution paths, handler selections, and performance metrics
- Automatically evicts lower-performing examples when better ones are found
- Provides fast lookup for similar past requests to optimize new executions

Usage:
    cache = WorkspaceReferenceCache()
    
    # Store a successful workspace execution
    cache.store_workspace_reference(
        task_text="Check my calendar for tomorrow and send an email", 
        workspace_id="workspace_12345", 
        execution_plan=execution_plan,
        performance_metrics=metrics
    )
    
    # Find similar workspaces for a new request
    similar_workspaces = cache.find_similar_workspaces(
        "Look at my calendar and email the details"
    )
"""

import os
import sys
import json
import time
import sqlite3
import logging
import hashlib
import threading
import numpy as np
import asyncio
import copy
import contextlib
from typing import Dict, List, Any, Optional, Tuple, Union, Callable
from pathlib import Path
from datetime import datetime
from collections import OrderedDict

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def safe_json_serialize(obj, max_depth=5, current_depth=0, exclude_keys=None):
    """
    Create a safe copy of an object for JSON serialization, removing circular references.
    
    Args:
        obj: The object to sanitize
        max_depth: Maximum nesting depth
        current_depth: Current recursion depth
        exclude_keys: Keys to exclude from dictionaries
        
    Returns:
        A sanitized copy safe for JSON serialization
    """
    # Default exclude keys that often cause circular references
    if exclude_keys is None:
        exclude_keys = {'self', 'board_room', 'boardroom', '_boardroom_instance', 'workspace_cache', 'nlp'}
    
    # Max depth check
    if current_depth > max_depth:
        if isinstance(obj, (dict, list, tuple, set)):
            return f"[Object truncated, max depth ({max_depth}) exceeded]"
        return str(obj)[:100]
    
    # Handle basic types that are JSON-serializable
    if obj is None or isinstance(obj, (bool, int, float, str)):
        return obj
    
    # Handle lists, tuples, and sets
    if isinstance(obj, (list, tuple, set)):
        return [safe_json_serialize(item, max_depth, current_depth + 1, exclude_keys) 
                for item in list(obj)[:100]]  # Limit to 100 items for safety
    
    # Handle dictionaries (most common source of circular references)
    if isinstance(obj, dict):
        result = {}
        # Limit to 100 items for safety
        for i, (key, value) in enumerate(obj.items()):
            if i >= 100:
                break
                
            # Skip excluded keys that might cause circular references
            if key in exclude_keys:
                continue
                
            # Ensure key is serializable by converting to string if needed
            safe_key = str(key)
            
            # Recursively sanitize values
            result[safe_key] = safe_json_serialize(value, max_depth, current_depth + 1, exclude_keys)
        return result
    
    # For other types, convert to string
    return str(obj)[:100]

class WorkspaceReferenceCache:
    """
    High-performance caching system for workspace references.
    
    Maintains a fixed-size cache of the best-performing workspace examples,
    using vector embeddings for similarity search and intelligent reference retrieval.
    """
    
    def __init__(self, max_entries: int = 2000, db_path: Optional[str] = None):
        """
        Initialize the workspace reference cache.
        
        Args:
            max_entries: Maximum number of entries to keep in the cache
            db_path: Path to the database file for persistent storage
        """
        self.max_entries = max_entries
        self.cache = OrderedDict()  # {task_hash: workspace_reference}
        self.embeddings = {}  # {task_hash: embedding_vector}
        self.lock = threading.RLock()
        self.db_path = db_path or os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 
            "workspace_reference_cache.db"
        )
        self.initialized = False
        self.nlp = None
        self.embedding_available = False
        
        # Initialize database
        self._initialize_db()
        
    async def initialize(self):
        """
        Asynchronously initialize the workspace reference cache.
        This ensures that spaCy model loading and database operations
        are properly awaited before processing embeddings.
        
        Returns:
            self: The initialized cache instance
        """
        if self.initialized:
            return self
            
        # Initialize embedding model
        try:
            # Try to import spaCy for embeddings
            import spacy
            # Use asyncio.to_thread for CPU-intensive spaCy loading to avoid blocking
            if hasattr(asyncio, 'to_thread'):
                # Python 3.9+ has to_thread
                self.nlp = await asyncio.to_thread(spacy.load, "en_core_web_lg")
            else:
                # Fallback for older Python versions
                loop = asyncio.get_event_loop()
                self.nlp = await loop.run_in_executor(None, lambda: spacy.load("en_core_web_lg"))
            
            self.embedding_available = True
            logger.info("Successfully loaded spaCy model for embeddings")
        except Exception as e:
            logger.warning(f"Could not load spaCy model, using fallback embedding: {e}")
            self.nlp = None
            self.embedding_available = False
        
        # Load existing data from database - using await to ensure completion
        await asyncio.to_thread(self._load_from_db) if hasattr(asyncio, 'to_thread') else \
            await asyncio.get_event_loop().run_in_executor(None, self._load_from_db)
        
        # Mark as initialized
        self.initialized = True
        logger.info("Workspace reference cache fully initialized with spaCy models and database data")
        return self
        
    def _initialize_db(self):
        """Initialize the SQLite database for persistent storage."""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path, isolation_level=None)
            cursor = conn.cursor()
            
            # Create workspace_reference table if it doesn't exist
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS workspace_reference (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_hash TEXT UNIQUE,
                task_text TEXT,
                workspace_id TEXT,
                execution_plan TEXT,
                performance_score REAL,
                timestamp INTEGER,
                embedding BLOB,
                agent_team TEXT,
                team_interaction_data TEXT,
                boardroom_session_id TEXT,
                conversation_summary TEXT,
                conversation_pointers TEXT
            )
            ''')
            
            # Add new columns to existing tables if they don't exist (migration)
            try:
                cursor.execute('ALTER TABLE workspace_reference ADD COLUMN conversation_summary TEXT')
                logger.info("Added conversation_summary column to workspace_reference table")
            except sqlite3.OperationalError:
                # Column already exists
                pass
                
            try:
                cursor.execute('ALTER TABLE workspace_reference ADD COLUMN conversation_pointers TEXT')
                logger.info("Added conversation_pointers column to workspace_reference table")
            except sqlite3.OperationalError:
                # Column already exists
                pass
            
            # Create index for fast similarity search
            cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_task_hash ON workspace_reference(task_hash)
            ''')
            
            # Create index for performance score
            cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_performance_score ON workspace_reference(performance_score)
            ''')
            
            conn.commit()
            logger.info(f"Initialized workspace reference database at {self.db_path}")
            
        except Exception as e:
            logger.error(f"Error initializing workspace reference database: {e}")
            import traceback
            logger.debug(traceback.format_exc())
        finally:
            # Always close the connection in finally block
            try:
                if conn:
                    conn.close()
                    conn = None
            except Exception as close_e:
                logger.warning(f"Error closing database connection: {str(close_e)}")
    
    def _load_from_db(self):
        """Load the highest-performing entries from the database into the cache."""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path, isolation_level=None)
            cursor = conn.cursor()
            
            # Load the top entries sorted by performance score
            cursor.execute(f'''
            SELECT task_hash, task_text, workspace_id, execution_plan, performance_score, timestamp, embedding, 
                   agent_team, team_interaction_data, boardroom_session_id, conversation_summary, conversation_pointers
            FROM workspace_reference
            ORDER BY performance_score DESC
            LIMIT {self.max_entries}
            ''')
            
            rows = cursor.fetchall()
            
            # Make a copy of the rows before closing the connection
            rows_copy = list(rows)
            
            with self.lock:
                for row in rows_copy:
                    task_hash, task_text, workspace_id, execution_plan_json, performance_score, timestamp, embedding_blob, agent_team, team_interaction_data, boardroom_session_id, conversation_summary, conversation_pointers = row
                    
                    execution_plan = json.loads(execution_plan_json)
                    
                    # Parse agent team and interaction data if available
                    agent_team_data = json.loads(agent_team) if agent_team else []
                    team_interactions = json.loads(team_interaction_data) if team_interaction_data else {}
                    
                    # Parse conversation data if available
                    conversation_summary_data = json.loads(conversation_summary) if conversation_summary else {}
                    conversation_pointers_data = json.loads(conversation_pointers) if conversation_pointers else {}
                    
                    self.cache[task_hash] = {
                        "task_text": task_text,
                        "workspace_id": workspace_id,
                        "execution_plan": execution_plan,
                        "performance_score": performance_score,
                        "timestamp": timestamp,
                        "agent_team": agent_team_data,
                        "team_interaction_data": team_interactions,
                        "boardroom_session_id": boardroom_session_id,
                        "conversation_summary": conversation_summary_data,
                        "conversation_pointers": conversation_pointers_data
                    }
                    
                    if embedding_blob:
                        self.embeddings[task_hash] = np.frombuffer(embedding_blob, dtype=np.float32)
            
            logger.info(f"Loaded {len(rows_copy)} workspace references from database")
            
        except Exception as e:
            logger.error(f"Error loading workspace references from database: {e}")
            import traceback
            logger.debug(traceback.format_exc())
        finally:
            # Always close the connection in finally block
            try:
                if conn:
                    conn.close()
                    conn = None
            except Exception as close_e:
                logger.warning(f"Error closing database connection: {str(close_e)}")
    
    def _create_embedding(self, text: str) -> np.ndarray:
        """
        Create a vector embedding for the given text.
        
        Args:
            text: The text to create an embedding for
            
        Returns:
            A numpy array containing the embedding vector
        """
        global _cache_initializer
        
        # Check current initialization state from the global initializer
        init_state = _cache_initializer.init_state if hasattr(_cache_initializer, 'init_state') else CACHE_UNINITIALIZED
        
        # If we're uninitialized and this is the first embedding request, try to initialize
        if init_state == CACHE_UNINITIALIZED and not hasattr(self, '_attempted_lazy_init'):
            self._attempted_lazy_init = True
            logger.info("First embedding request with uninitialized cache, attempting lazy initialization...")
            try:
                # Load database synchronously as a minimum initialization
                self._load_from_db()
                if len(self.cache) > 0:
                    logger.info(f"Lazy initialization loaded {len(self.cache)} entries from database")
                    # Mark as partially initialized since we only have database but no spaCy
                    if hasattr(_cache_initializer, 'init_state'):
                        _cache_initializer.init_state = CACHE_PARTIALLY_INITIALIZED
            except Exception as e:
                logger.warning(f"Lazy initialization failed: {str(e)}")
            
        # Try to use spaCy embeddings if available
        if self.embedding_available and self.nlp:
            try:
                # Use spaCy for embeddings
                doc = self.nlp(text)
                # Verify vector is valid
                if doc.vector.shape[0] > 0 and not np.isnan(doc.vector).any():
                    return doc.vector
                else:
                    logger.warning("spaCy returned invalid vector, falling back to hash-based embedding")
                    # Fall through to fallback
            except Exception as e:
                logger.warning(f"Error creating spaCy embedding: {str(e)}")
                # Fall through to fallback
        else:
            # Log informative message based on state 
            in_test_env = self.db_path.endswith("test_workspace_cache.db")
            
            if not in_test_env:
                if init_state == CACHE_UNINITIALIZED:
                    logger.info("Using fallback embeddings: Cache is not yet initialized")
                elif init_state == CACHE_INITIALIZING:
                    logger.info("Using fallback embeddings: Cache initialization is in progress")
                elif init_state == CACHE_PARTIALLY_INITIALIZED:
                    # Only log this once per session
                    if not hasattr(self, '_fallback_warning_logged'):
                        logger.warning("Using fallback embeddings: spaCy model not available in partially initialized cache")
                        self._fallback_warning_logged = True
                elif not self.nlp:
                    # Only log this once per session
                    if not hasattr(self, '_no_nlp_warning_logged'):
                        logger.warning("Using fallback embeddings: No spaCy model available")
                        self._no_nlp_warning_logged = True
                        
        # Fallback to a consistent hash-based embedding when spaCy is not available
        # This produces deterministic vectors for identical texts
        hash_vals = []
        for i in range(10):
            h = hashlib.md5(f"{text}_{i}".encode()).digest()
            hash_vals.extend([float(b) / 255.0 for b in h])
        return np.array(hash_vals, dtype=np.float32)
    
    def _calculate_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """
        Calculate cosine similarity between two embeddings.
        
        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
            
        Returns:
            Similarity score between 0 and 1
        """
        if len(embedding1) == 0 or len(embedding2) == 0:
            return 0.0
        
        # Check for dimension mismatch
        if embedding1.shape[0] != embedding2.shape[0]:
            logger.warning(f"Embedding dimension mismatch: {embedding1.shape[0]} vs {embedding2.shape[0]}")
            
            # Option 1: Use smaller dimension by truncating the larger vector
            min_dim = min(embedding1.shape[0], embedding2.shape[0])
            embedding1_trunc = embedding1[:min_dim]
            embedding2_trunc = embedding2[:min_dim]
            
            # Recalculate with truncated vectors
            dot_product = np.dot(embedding1_trunc, embedding2_trunc)
            norm1 = np.linalg.norm(embedding1_trunc)
            norm2 = np.linalg.norm(embedding2_trunc)
        else:
            # Normal case - dimensions match
            dot_product = np.dot(embedding1, embedding2)
            norm1 = np.linalg.norm(embedding1)
            norm2 = np.linalg.norm(embedding2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
            
        return dot_product / (norm1 * norm2)
    
    def _calculate_team_effectiveness(self, agent_team: List[Dict[str, Any]]) -> float:
        """
        Calculate the effectiveness score for a team of agents.
        
        This evaluates how well the agents worked together based on:
        1. Team composition diversity
        2. Role clarity
        3. Contribution balance
        4. Specialization appropriateness
        
        Args:
            agent_team: List of agent data dictionaries
            
        Returns:
            Team effectiveness score between 0 and 1
        """
        if not agent_team or len(agent_team) == 0:
            return 0.5  # Default middle score for no team data
            
        # Calculate team diversity (different agent types)
        unique_agent_types = len(set(agent.get('agent_id', '') for agent in agent_team))
        diversity_score = min(1.0, unique_agent_types / max(4, len(agent_team)))
        
        # Calculate role clarity (agents with defined roles)
        role_clarity = sum(1 for agent in agent_team if agent.get('role') in 
                          ['primary', 'secondary', 'specialist', 'coordinator']) / len(agent_team)
        
        # Calculate contribution balance
        contribution_scores = [agent.get('contribution_score', 0) for agent in agent_team]
        if contribution_scores:
            # Variance should be low for balanced contributions
            mean_contribution = sum(contribution_scores) / len(contribution_scores)
            variance = sum((score - mean_contribution) ** 2 for score in contribution_scores) / len(contribution_scores)
            balance_score = max(0, 1.0 - (variance * 3))  # Lower variance gives higher score
        else:
            balance_score = 0.5
            
        # Evaluate specialization appropriateness
        specialization_score = 0.5
        for agent in agent_team:
            if agent.get('role') == 'specialist' and agent.get('domain_match_score', 0) > 0.7:
                specialization_score += 0.1
            if agent.get('role') == 'primary' and agent.get('contribution_score', 0) > 0.6:
                specialization_score += 0.1
                
        specialization_score = min(1.0, specialization_score)
        
        # Calculate weighted team effectiveness score
        team_score = (
            0.3 * diversity_score +
            0.25 * role_clarity +
            0.25 * balance_score +
            0.2 * specialization_score
        )
        
        return min(1.0, team_score)
        
    def _calculate_performance_score(self, metrics: Dict[str, Any], agent_team: List[Dict[str, Any]] = None,
                                   conversation_summary: Dict[str, Any] = None) -> float:
        """
        Calculate a single performance score from multiple metrics, including conversation quality.
        
        Higher scores represent better performance. This is used to rank and
        maintain only the best examples in the cache.
        
        Args:
            metrics: Dictionary of performance metrics
            agent_team: Optional list of agent data for team effectiveness calculation
            conversation_summary: Optional conversation summary for quality assessment
            
        Returns:
            A single performance score between 0 and 1
        """
        # Extract metrics with reasonable defaults if missing
        success_rate = metrics.get("success_rate", 0.5)
        completion_time = metrics.get("completion_time", 10.0)
        quality_score = metrics.get("quality_score", 0.5)
        accuracy = metrics.get("accuracy", 0.5)
        efficiency = metrics.get("efficiency", 0.5)
        
        # Normalize completion time (lower is better)
        max_time = 60.0  # Consider 60 seconds as the maximum reasonable time
        time_score = max(0, 1.0 - (completion_time / max_time))
        
        # Calculate team effectiveness if agent team data is available
        team_effectiveness = self._calculate_team_effectiveness(agent_team) if agent_team else 0.5
        
        # Calculate conversation quality score if conversation data is available
        conversation_quality = self._calculate_conversation_quality_score(conversation_summary) if conversation_summary else 0.5
        
        # Calculate weighted score, now including team effectiveness and conversation quality
        weights = {
            "success_rate": 0.25,           # Reduced to make room for conversation quality
            "time_score": 0.08,
            "quality_score": 0.12,
            "accuracy": 0.12,
            "efficiency": 0.08,
            "team_effectiveness": 0.20,
            "conversation_quality": 0.15    # New weight for conversation quality
        }
        
        score = (
            weights["success_rate"] * success_rate +
            weights["time_score"] * time_score +
            weights["quality_score"] * quality_score +
            weights["accuracy"] * accuracy +
            weights["efficiency"] * efficiency +
            weights["team_effectiveness"] * team_effectiveness +
            weights["conversation_quality"] * conversation_quality
        )
        
        return score
    
    def _calculate_conversation_quality_score(self, conversation_summary: Dict[str, Any]) -> float:
        """
        Calculate conversation quality score from conversation summary data.
        
        Args:
            conversation_summary: Dictionary containing conversation analysis
            
        Returns:
            Conversation quality score between 0 and 1
        """
        if not conversation_summary:
            return 0.5
        
        try:
            # Extract performance indicators
            perf_indicators = conversation_summary.get("performance_indicators", {})
            
            # Get key metrics
            completion_rate = perf_indicators.get("completion_rate", 0.0)
            collaboration_effectiveness = perf_indicators.get("collaboration_effectiveness", 0.0)
            timeline_efficiency = perf_indicators.get("timeline_efficiency", 0.0)
            
            # Get conversation metadata
            workspace_summary = conversation_summary.get("workspace_summary", {})
            total_conversations = workspace_summary.get("total_conversations", 0)
            timeline_events = workspace_summary.get("timeline_events", 0)
            
            conversation_phases = len(conversation_summary.get("conversation_phases", []))
            key_participants = len(conversation_summary.get("key_participants", {}))
            decision_points = len(conversation_summary.get("decision_points", []))
            
            # Calculate quality components
            
            # 1. Completion Quality (40% weight)
            completion_quality = completion_rate
            
            # 2. Collaboration Quality (30% weight)
            collaboration_quality = collaboration_effectiveness
            
            # 3. Efficiency Quality (20% weight)
            efficiency_quality = timeline_efficiency
            
            # 4. Engagement Quality (10% weight) - based on participant and decision point density
            engagement_score = 0.0
            if total_conversations > 0:
                participant_density = min(key_participants / max(total_conversations, 1), 1.0)
                decision_density = min(decision_points / max(timeline_events, 1), 1.0)
                engagement_score = (participant_density + decision_density) / 2
            
            # Calculate weighted conversation quality score
            conversation_quality = (
                0.40 * completion_quality +
                0.30 * collaboration_quality +
                0.20 * efficiency_quality +
                0.10 * engagement_score
            )
            
            # Normalize to 0-1 range
            conversation_quality = max(0.0, min(1.0, conversation_quality))
            
            logger.debug(f"[WORKSPACE_CACHE] Calculated conversation quality: {conversation_quality:.3f} "
                        f"(completion: {completion_quality:.2f}, collaboration: {collaboration_quality:.2f}, "
                        f"efficiency: {efficiency_quality:.2f}, engagement: {engagement_score:.2f})")
            
            return conversation_quality
            
        except Exception as e:
            logger.warning(f"[WORKSPACE_CACHE] Error calculating conversation quality score: {str(e)}")
            return 0.5
    
    async def store_workspace_reference(self, task_text: str, workspace_id: str, 
                                        execution_plan: Dict[str, Any], 
                                        performance_metrics: Dict[str, Any],
                                        agent_team: List[Dict[str, Any]] = None,
                                        team_interaction_data: Dict[str, Any] = None,
                                        boardroom_session_id: str = None,
                                        conversation_summary: Dict[str, Any] = None,
                                        conversation_pointers: Dict[str, Any] = None) -> bool:
        """
        Store a workspace reference in the cache.
        
        Args:
            task_text: The original task text
            workspace_id: The ID of the workspace
            execution_plan: The execution plan used for the task
            performance_metrics: Performance metrics for the execution
            agent_team: List of agents that participated in the workspace, with their roles and contributions
                        Format: [{"agent_id": "email_agent", "role": "primary", "contribution_score": 0.8}, ...]
            team_interaction_data: Dictionary containing interaction patterns between agents
                        Format: {"communication_flow": [...], "handoffs": [...], "collaborations": [...]}
            boardroom_session_id: ID of the BoardRoom session if the workspace used BoardRoom
            conversation_summary: Dictionary containing conversation summaries across all systems
                        Format: {"phases": [...], "key_decisions": [...], "participant_summary": {...}}
            conversation_pointers: Dictionary containing pointers to full conversation data
                        Format: {"boardroom_conversations": [...], "user_conversations": [...], "agent_conversations": [...]}
            
        Returns:
            True if the reference was stored, False otherwise
        """
        conn = None
        try:
            # Calculate task hash
            task_hash = hashlib.md5(task_text.encode()).hexdigest()
            
            # Auto-generate conversation summaries and pointers if not provided
            if conversation_summary is None or conversation_pointers is None:
                try:
                    from conversation_aggregator import ConversationAggregator
                    aggregator = ConversationAggregator()
                    
                    # Generate conversation summary and pointers
                    auto_summary, auto_pointers = await self._generate_conversation_data(
                        aggregator, workspace_id, task_text, boardroom_session_id
                    )
                    
                    if conversation_summary is None:
                        conversation_summary = auto_summary
                    if conversation_pointers is None:
                        conversation_pointers = auto_pointers
                        
                    logger.info(f"[WORKSPACE_CACHE] Auto-generated conversation data for workspace {workspace_id}")
                    
                except Exception as e:
                    logger.warning(f"[WORKSPACE_CACHE] Failed to auto-generate conversation data: {str(e)}")
                    conversation_summary = conversation_summary or {}
                    conversation_pointers = conversation_pointers or {}
            
            # Calculate performance score including team effectiveness and conversation quality
            # (Done after conversation generation so we can include conversation quality)
            performance_score = self._calculate_performance_score(
                performance_metrics, agent_team, conversation_summary
            )
            
            # Create embedding
            embedding = self._create_embedding(task_text)
            
            # Prepare cache entry
            entry = {
                "task_text": task_text,
                "workspace_id": workspace_id,
                "execution_plan": execution_plan,
                "performance_score": performance_score,
                "timestamp": int(time.time()),
                "agent_team": agent_team or [],
                "team_interaction_data": team_interaction_data or {},
                "boardroom_session_id": boardroom_session_id,
                "conversation_summary": conversation_summary or {},
                "conversation_pointers": conversation_pointers or {}
            }
            
            # Check if we already have this task or a similar one with better performance
            with self.lock:
                if task_hash in self.cache:
                    existing_score = self.cache[task_hash]["performance_score"]
                    if performance_score <= existing_score:
                        logger.debug(f"Ignoring workspace reference with lower score: {performance_score} vs {existing_score}")
                        return False
                
                # Add to cache
                self.cache[task_hash] = entry
                self.embeddings[task_hash] = embedding
                
                # Maintain max size by removing lowest-scoring entries
                if len(self.cache) > self.max_entries:
                    # Find the lowest-scoring entry
                    lowest_hash, lowest_score = min(
                        [(h, data["performance_score"]) for h, data in self.cache.items()],
                        key=lambda x: x[1]
                    )
                    
                    # Only remove if the new entry has a higher score
                    if performance_score > lowest_score:
                        self.cache.pop(lowest_hash)
                        self.embeddings.pop(lowest_hash, None)
                        
                        # Also remove from database - use separate connection with proper cleanup
                        try:
                            db_conn = sqlite3.connect(self.db_path, isolation_level=None)
                            db_cursor = db_conn.cursor()
                            db_cursor.execute("DELETE FROM workspace_reference WHERE task_hash = ?", (lowest_hash,))
                            db_conn.commit()
                        except Exception as db_e:
                            logger.warning(f"Error removing lowest-scoring entry from database: {str(db_e)}")
                        finally:
                            try:
                                if db_conn:
                                    db_conn.close()
                            except Exception:
                                pass
            
            # Store in database - use a new connection with proper cleanup
            conn = sqlite3.connect(self.db_path, isolation_level=None)
            cursor = conn.cursor()
            
            # Sanitize data for storage using our safe serialization helper
            try:
                # Create safe copies of all complex objects to prevent circular references
                safe_execution_plan = safe_json_serialize(execution_plan)
                safe_agent_team = safe_json_serialize(agent_team or [])
                safe_team_interaction = safe_json_serialize(team_interaction_data or {})
                safe_conversation_summary = safe_json_serialize(conversation_summary or {})
                safe_conversation_pointers = safe_json_serialize(conversation_pointers or {})
                
                # Serialize to JSON with the safe objects
                execution_plan_json = json.dumps(safe_execution_plan)
                agent_team_json = json.dumps(safe_agent_team)
                team_interaction_json = json.dumps(safe_team_interaction)
                conversation_summary_json = json.dumps(safe_conversation_summary)
                conversation_pointers_json = json.dumps(safe_conversation_pointers)
                
                logger.debug(f"Successfully sanitized data for storage in database")
            except Exception as e:
                logger.warning(f"Error during data sanitization: {str(e)}, using fallbacks")
                # Fallback to minimal data if serialization fails
                execution_plan_json = json.dumps({"error": "Could not serialize execution plan safely"})
                agent_team_json = json.dumps([])
                team_interaction_json = json.dumps({})
                conversation_summary_json = json.dumps({})
                conversation_pointers_json = json.dumps({})
            
            cursor.execute('''
            INSERT OR REPLACE INTO workspace_reference
            (task_hash, task_text, workspace_id, execution_plan, performance_score, timestamp, embedding,
             agent_team, team_interaction_data, boardroom_session_id, conversation_summary, conversation_pointers)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                task_hash,
                task_text,
                workspace_id,
                execution_plan_json,
                performance_score,
                entry["timestamp"],
                embedding.tobytes() if embedding is not None else None,
                agent_team_json,
                team_interaction_json,
                boardroom_session_id,
                conversation_summary_json,
                conversation_pointers_json
            ))
            
            conn.commit()
            logger.debug(f"Stored workspace reference for '{task_text[:30]}...' with score {performance_score:.4f}")
            return True
            
        except Exception as e:
            logger.error(f"Error storing workspace reference: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return False
        finally:
            # Always close the connection in finally block
            try:
                if conn:
                    conn.close()
                    conn = None
            except Exception as close_e:
                logger.warning(f"Error closing database connection: {str(close_e)}")
    
    async def store_agent_s_data(self, workspace_id: str, task_description: str, 
                                execution_data: Dict[str, Any]) -> bool:
        """
        Store Agent-S execution data in workspace reference cache.
        
        Args:
            workspace_id: The workspace ID where Agent-S was used
            task_description: Description of the task Agent-S performed
            execution_data: Data captured by Agent-S including screenshots, UI patterns, etc.
            
        Returns:
            True if data was stored successfully, False otherwise
        """
        try:
            # Prepare Agent-S specific data structure
            agent_s_team_entry = {
                "agent_id": "agent_s",
                "agent_type": "agent_s_handler", 
                "role": "gap_filler",
                "workspace_role": "visual_automation",
                "contribution_score": 1.0,  # Full contribution for gap filling
                "data_captured": execution_data.get("data_captured", []),
                "ui_patterns_learned": execution_data.get("ui_patterns_learned", []),
                "application_insights": execution_data.get("application_insights", []),
                "execution_timestamp": datetime.now().isoformat()
            }
            
            # Create team interaction data for Agent-S
            agent_s_interaction_data = {
                "agent_s_integration": {
                    "gaps_filled": execution_data.get("gaps_filled", []),
                    "visual_data_captured": len(execution_data.get("data_captured", [])),
                    "ui_patterns_learned": len(execution_data.get("ui_patterns_learned", [])),
                    "workspace_feedback_provided": execution_data.get("workspace_context_updated", False),
                    "integration_method": "seamless_handoff",
                    "communication_pattern": "workspace_feedback_loop"
                },
                "coordination_flow": [
                    "coordinator → agent_s (gap task assignment)",
                    "agent_s → ui_automation (visual execution)",
                    "agent_s → workspace_cache (data capture)",
                    "agent_s → coordinator (completion notification)"
                ]
            }
            
            # Prepare execution plan for Agent-S tasks
            agent_s_execution_plan = {
                "task_type": "agent_s_gap_filling",
                "original_task": task_description,
                "execution_method": "ui_automation",
                "gaps_addressed": execution_data.get("gaps_filled", []),
                "data_capture_successful": execution_data.get("workspace_context_updated", False),
                "integration_pattern": "hybrid_workspace_team"
            }
            
            # Create performance metrics for Agent-S execution
            performance_metrics = {
                "execution_success": execution_data.get("workspace_context_updated", False),
                "data_quality_score": min(1.0, len(execution_data.get("data_captured", [])) * 0.2),
                "ui_patterns_score": min(1.0, len(execution_data.get("ui_patterns_learned", [])) * 0.3),
                "integration_score": 1.0 if execution_data.get("workspace_context_updated", False) else 0.5,
                "agent_s_specific": True
            }
            
            # Store using the standard workspace reference method
            success = self.store_workspace_reference(
                task_text=f"Agent-S Gap Filling: {task_description}",
                workspace_id=workspace_id,
                execution_plan=agent_s_execution_plan,
                performance_metrics=performance_metrics,
                agent_team=[agent_s_team_entry],
                team_interaction_data=agent_s_interaction_data
            )
            
            if success:
                logger.info(f"Successfully stored Agent-S data for workspace {workspace_id}")
                logger.debug(f"Agent-S captured {len(execution_data.get('data_captured', []))} data items, "
                           f"learned {len(execution_data.get('ui_patterns_learned', []))} UI patterns")
            
            return success
            
        except Exception as e:
            logger.error(f"Error storing Agent-S data: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return False
    
    def get_agent_s_patterns_for_task(self, task_description: str, app_name: str = None) -> List[Dict[str, Any]]:
        """
        Retrieve Agent-S UI patterns that could help with a similar task.
        
        Args:
            task_description: Description of the task to find patterns for
            app_name: Optional specific application name to filter patterns
            
        Returns:
            List of relevant UI patterns learned by Agent-S
        """
        try:
            # Find similar workspaces that used Agent-S
            similar_workspaces = self.find_similar_workspaces(
                task_description, 
                top_k=5,
                agent_filter="agent_s"
            )
            
            patterns = []
            for workspace in similar_workspaces:
                agent_team = workspace.get("agent_team", [])
                for agent in agent_team:
                    if agent.get("agent_id") == "agent_s":
                        ui_patterns = agent.get("ui_patterns_learned", [])
                        for pattern in ui_patterns:
                            # Filter by application if specified
                            if app_name and pattern.get("application", "").lower() != app_name.lower():
                                continue
                            
                            # Add relevance score based on workspace similarity
                            pattern_with_score = pattern.copy()
                            pattern_with_score["relevance_score"] = workspace.get("similarity_score", 0.0)
                            pattern_with_score["source_workspace"] = workspace.get("workspace_id")
                            patterns.append(pattern_with_score)
            
            # Sort by relevance score and success rate
            patterns.sort(key=lambda p: (p.get("relevance_score", 0), p.get("success_rate", 0)), reverse=True)
            
            logger.info(f"Found {len(patterns)} Agent-S UI patterns for task: {task_description[:50]}...")
            return patterns
            
        except Exception as e:
            logger.error(f"Error retrieving Agent-S patterns: {e}")
            return []
    
    async def find_similar_workspaces_async(self, query: str, top_k: int = 3, 
                                      min_similarity: float = 0.7,
                                      agent_filter: str = None,
                                      require_team: bool = False) -> List[Dict[str, Any]]:
        """
        Asynchronously find similar workspaces based on query similarity.
        
        This method will ensure the cache is fully initialized before processing,
        which is recommended for production use.
        
        Args:
            query: The task text to find similar workspaces for
            top_k: Maximum number of similar workspaces to return
            min_similarity: Minimum similarity score threshold
            agent_filter: Optional agent ID to filter results (only returns workspaces using this agent)
            require_team: If True, only return workspaces that used multiple agents (teams)
            
        Returns:
            List of similar workspace references, sorted by similarity
        """
        # Ensure initialization is complete
        if not self.initialized:
            # Use the dedicated initialization method
            initialized = await self.ensure_initialization()
            if initialized:
                logger.info("Cache initialization completed successfully")
            else:
                logger.warning("Cache initialization failed, proceeding with limited functionality")
        
        # Create embedding asynchronously for better performance
        if self.embedding_available and self.nlp:
            try:
                # Process the embedding in a non-blocking way
                if hasattr(asyncio, 'to_thread'):
                    query_embedding = await asyncio.to_thread(
                        lambda q: self.nlp(q).vector if self.nlp else None, query
                    )
                else:
                    loop = asyncio.get_event_loop()
                    query_embedding = await loop.run_in_executor(
                        None, lambda q=query: self.nlp(q).vector if self.nlp else None
                    )
                
                # Check if we got a valid embedding back
                if query_embedding is not None and len(query_embedding) > 0:
                    # Use our async implementation with pre-computed embedding
                    return await self._find_similar_workspaces_with_embedding(
                        query, query_embedding, top_k, min_similarity, agent_filter, require_team
                    )
            except Exception as e:
                logger.warning(f"Error in async embedding creation: {str(e)}")
                # Fall through to synchronous method
                
        # Fallback to synchronous method if async embedding failed
        return self.find_similar_workspaces(query, top_k, min_similarity, agent_filter, require_team)
        
    async def _find_similar_workspaces_with_embedding(
        self, query: str, query_embedding: np.ndarray, 
        top_k: int = 3, min_similarity: float = 0.7,
        agent_filter: str = None, require_team: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Find similar workspaces using pre-computed embedding (internal async implementation).
        
        Args:
            query: The original query text (for logging)
            query_embedding: Pre-computed embedding vector
            top_k: Maximum number of similar workspaces to return
            min_similarity: Minimum similarity score threshold
            agent_filter: Optional agent ID to filter results
            require_team: If True, only return workspaces that used multiple agents
            
        Returns:
            List of similar workspace references, sorted by similarity
        """
        try:
            # Calculate similarity with all cache entries
            similarities = []
            
            with self.lock:
                for task_hash, embedding in self.embeddings.items():
                    if task_hash in self.cache:
                        cache_entry = self.cache[task_hash]
                        
                        # Check if entry meets team-based filtering criteria
                        if require_team and (not cache_entry.get("agent_team") or len(cache_entry.get("agent_team", [])) < 2):
                            continue
                            
                        # Check if entry contains the specific agent we're filtering for
                        if agent_filter:
                            agent_team = cache_entry.get("agent_team", [])
                            # Get agent IDs with more reliable error handling
                            agent_ids = []
                            for agent in agent_team:
                                if isinstance(agent, dict):
                                    agent_id = agent.get("agent_id")
                                    if agent_id:
                                        agent_ids.append(agent_id)
                                        
                            # Log what we're filtering and what we found
                            logger.debug(f"Agent filter: {agent_filter}, agents in entry: {agent_ids}")
                            
                            # Skip if the agent isn't in the team
                            if not agent_ids or agent_filter not in agent_ids:
                                logger.debug(f"Skipping entry, agent {agent_filter} not found in {agent_ids}")
                                continue
                        
                        # Calculate similarity if it passes filters
                        similarity = self._calculate_similarity(query_embedding, embedding)
                        if similarity >= min_similarity:
                            # Add additional boost for team-based entries if we're requiring teams
                            if require_team and len(cache_entry.get("agent_team", [])) > 2:
                                similarity += 0.05  # Small boost for larger teams
                            
                            similarities.append((task_hash, similarity))
            
            # Sort by similarity (highest first)
            similarities.sort(key=lambda x: x[1], reverse=True)
            
            # Get top-k results
            results = []
            for task_hash, similarity in similarities[:top_k]:
                entry = self.cache[task_hash].copy()
                entry["similarity"] = similarity
                
                # Include team information in the result
                if "agent_team" in entry and entry["agent_team"]:
                    entry["team_size"] = len(entry["agent_team"])
                    entry["primary_agent"] = next((agent.get("agent_id") for agent in entry["agent_team"] 
                                                if agent.get("role") == "primary"), None)
                else:
                    entry["team_size"] = 0
                    entry["primary_agent"] = None
                    
                results.append(entry)
            
            return results
            
        except Exception as e:
            logger.error(f"Error in async workspace similarity search: {str(e)}")
            import traceback
            logger.debug(traceback.format_exc())
            return []
    
    async def ensure_initialization(self) -> bool:
        """
        Ensure the cache is initialized before being used.
        If not already initialized, performs initialization using the global initializer.
        
        Returns:
            bool: True if initialization succeeded, False otherwise
        """
        global _cache_initializer
        
        # If already initialized in this instance, return immediately
        if self.initialized:
            return True
            
        logger.info("Cache not initialized, using global initializer...")
        try:
            # Use the global initializer with a short timeout (10 seconds)
            # This is shorter than the full initialization timeout to avoid blocking
            # but still gives time for a partial initialization
            await _cache_initializer.initialize_cache(timeout=10)
            
            # Check if initialization was successful based on the global state
            if _cache_initializer.init_state in [CACHE_FULLY_INITIALIZED, CACHE_PARTIALLY_INITIALIZED]:
                # Update local state based on global state
                self.initialized = True
                logger.info(f"Cache initialized through global initializer. State: {_cache_initializer.init_state}")
                
                # Copy other properties from global initializer's cache instance if we're not that instance
                if self is not _cache_initializer.cache_instance:
                    global_cache = _cache_initializer.cache_instance
                    # Copy important properties for consistency
                    self.nlp = global_cache.nlp
                    self.embedding_available = global_cache.embedding_available
                    
                    # Only reload database entries if our cache is empty
                    if len(self.cache) == 0 and len(global_cache.cache) > 0:
                        # Copy cache entries from global instance (shallow copy is sufficient)
                        self.cache = global_cache.cache.copy()
                        self.embeddings = global_cache.embeddings.copy()
                        logger.info(f"Copied {len(self.cache)} entries from global cache instance")
                
                return True
            else:
                # If global initialization is still in progress, just rely on what we have
                if _cache_initializer.init_state == CACHE_INITIALIZING:
                    logger.info("Global initialization is still in progress, continuing with limited functionality")
                    return False
                
                # If global initialization failed entirely, try a minimal local initialization
                logger.warning("Global initialization failed, attempting minimal local initialization...")
                
                # Attempt minimal database loading only
                if len(self.cache) == 0:
                    await asyncio.to_thread(self._load_from_db) if hasattr(asyncio, 'to_thread') else \
                        await asyncio.get_event_loop().run_in_executor(None, self._load_from_db)
                    
                    # Mark as partially initialized if we have data
                    if len(self.cache) > 0:
                        self.initialized = True
                        logger.info(f"Cache partially initialized with {len(self.cache)} entries (no spaCy)")
                        return True
                
                return self.initialized
        except Exception as e:
            logger.error(f"Error during on-demand initialization: {str(e)}")
            import traceback
            logger.debug(traceback.format_exc())
            return False

    def find_similar_workspaces(self, query: str, top_k: int = 3, 
                               min_similarity: float = 0.7,
                               agent_filter: str = None,
                               require_team: bool = False,
                               include_conversation_metadata: bool = True) -> List[Dict[str, Any]]:
        """
        Find similar workspaces based on query similarity with enhanced conversation metadata.
        
        Note: For production use, prefer find_similar_workspaces_async to ensure
        the cache is fully initialized before processing.
        
        Args:
            query: The task text to find similar workspaces for
            top_k: Maximum number of similar workspaces to return
            min_similarity: Minimum similarity score threshold
            agent_filter: Optional agent ID to filter results (only returns workspaces using this agent)
            require_team: If True, only return workspaces that used multiple agents (teams)
            include_conversation_metadata: If True, includes rich conversation metadata in results
            
        Returns:
            List of similar workspace references with conversation metadata, sorted by similarity
        """
        try:
            # Check if we're in a test environment to control warning behavior
            in_test_env = self.db_path.endswith("test_workspace_cache.db")
            
            # Attempt synchronous preparation if not initialized
            if not self.initialized:
                # Log issue but continue with potentially reduced functionality
                # Don't log warning in test environments
                if not in_test_env:
                    logger.warning("Finding similar workspaces before full initialization. Results may be less accurate.")
                
                # Load data from database synchronously if it wasn't loaded yet
                if len(self.cache) == 0:
                    logger.info("Cache empty, loading existing data from database")
                    self._load_from_db()
            
            # Create embedding for the query
            query_embedding = self._create_embedding(query)
            
            # Calculate similarity with all cache entries
            similarities = []
            
            with self.lock:
                for task_hash, embedding in self.embeddings.items():
                    if task_hash in self.cache:
                        cache_entry = self.cache[task_hash]
                        
                        # Check if entry meets team-based filtering criteria
                        if require_team and (not cache_entry.get("agent_team") or len(cache_entry.get("agent_team", [])) < 2):
                            continue
                            
                        # Check if entry contains the specific agent we're filtering for
                        if agent_filter:
                            agent_team = cache_entry.get("agent_team", [])
                            # Get agent IDs with more reliable error handling
                            agent_ids = []
                            for agent in agent_team:
                                if isinstance(agent, dict):
                                    agent_id = agent.get("agent_id")
                                    if agent_id:
                                        agent_ids.append(agent_id)
                                        
                            # Log what we're filtering and what we found
                            logger.debug(f"Agent filter: {agent_filter}, agents in entry: {agent_ids}")
                            
                            # Skip if the agent isn't in the team
                            if not agent_ids or agent_filter not in agent_ids:
                                logger.debug(f"Skipping entry, agent {agent_filter} not found in {agent_ids}")
                                continue
                        
                        # Calculate similarity if it passes filters
                        similarity = self._calculate_similarity(query_embedding, embedding)
                        if similarity >= min_similarity:
                            # Add additional boost for team-based entries if we're requiring teams
                            if require_team and len(cache_entry.get("agent_team", [])) > 2:
                                similarity += 0.05  # Small boost for larger teams
                            
                            similarities.append((task_hash, similarity))
            
            # Sort by similarity (highest first)
            similarities.sort(key=lambda x: x[1], reverse=True)
            
            # Get top-k results with enhanced conversation metadata
            results = []
            for task_hash, similarity in similarities[:top_k]:
                entry = self.cache[task_hash].copy()
                entry["similarity"] = similarity
                
                # Include team information in the result
                if "agent_team" in entry and entry["agent_team"]:
                    entry["team_size"] = len(entry["agent_team"])
                    entry["primary_agent"] = next((agent.get("agent_id") for agent in entry["agent_team"] 
                                                if agent.get("role") == "primary"), None)
                else:
                    entry["team_size"] = 0
                    entry["primary_agent"] = None
                
                # Add conversation metadata to cache lookup results
                if include_conversation_metadata:
                    conversation_summary = entry.get("conversation_summary", {})
                    conversation_pointers = entry.get("conversation_pointers", {})
                    
                    # Add conversation quality metrics
                    if conversation_summary:
                        perf_indicators = conversation_summary.get("performance_indicators", {})
                        workspace_summary = conversation_summary.get("workspace_summary", {})
                        
                        entry["conversation_metadata"] = {
                            "total_conversations": workspace_summary.get("total_conversations", 0),
                            "timeline_events": workspace_summary.get("timeline_events", 0),
                            "conversation_phases": len(conversation_summary.get("conversation_phases", [])),
                            "key_participants": len(conversation_summary.get("key_participants", {})),
                            "decision_points": len(conversation_summary.get("decision_points", [])),
                            "completion_rate": perf_indicators.get("completion_rate", 0.0),
                            "collaboration_effectiveness": perf_indicators.get("collaboration_effectiveness", 0.0),
                            "timeline_efficiency": perf_indicators.get("timeline_efficiency", 0.0),
                            "has_conversation_data": True
                        }
                        
                        # Add conversation type breakdown from pointers
                        if conversation_pointers:
                            entry["conversation_breakdown"] = {
                                "boardroom_conversations": len(conversation_pointers.get("boardroom_conversations", [])),
                                "user_conversations": len(conversation_pointers.get("user_conversations", [])),
                                "journey_conversations": len(conversation_pointers.get("journey_conversations", [])),
                                "workspace_references": len(conversation_pointers.get("workspace_references", [])),
                                "timeline_summary": conversation_pointers.get("timeline_summary", {})
                            }
                    else:
                        # Provide default metadata for entries without conversation data
                        entry["conversation_metadata"] = {
                            "total_conversations": 0,
                            "timeline_events": 0,
                            "conversation_phases": 0,
                            "key_participants": 0,
                            "decision_points": 0,
                            "completion_rate": 0.0,
                            "collaboration_effectiveness": 0.0,
                            "timeline_efficiency": 0.0,
                            "has_conversation_data": False
                        }
                        entry["conversation_breakdown"] = {
                            "boardroom_conversations": 0,
                            "user_conversations": 0,
                            "journey_conversations": 0,
                            "workspace_references": 0,
                            "timeline_summary": {}
                        }
                    
                    # Add conversation quality score if available
                    entry["conversation_quality_score"] = self._calculate_conversation_quality_score(conversation_summary)
                    
                results.append(entry)
            
            return results
            
        except Exception as e:
            logger.error(f"Error finding similar workspaces: {e}")
            return []
    
    def get_workspace_reference(self, task_hash: str) -> Optional[Dict[str, Any]]:
        """
        Get a workspace reference by its task hash.
        
        Args:
            task_hash: The hash of the task text
            
        Returns:
            The workspace reference, or None if not found
        """
        with self.lock:
            return self.cache.get(task_hash)
    
    def clear_cache(self) -> bool:
        """
        Clear the cache and optionally the database.
        
        Returns:
            True if successful, False otherwise
        """
        conn = None
        try:
            with self.lock:
                self.cache.clear()
                self.embeddings.clear()
            
            conn = sqlite3.connect(self.db_path, isolation_level=None)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM workspace_reference")
            conn.commit()
            
            logger.info("Cleared workspace reference cache")
            return True
            
        except Exception as e:
            logger.error(f"Error clearing workspace reference cache: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return False
        finally:
            # Always close the connection in finally block
            try:
                if conn:
                    conn.close()
                    conn = None
            except Exception as close_e:
                logger.warning(f"Error closing database connection: {str(close_e)}")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary of cache statistics
        """
        with self.lock:
            # Calculate average performance score
            avg_score = sum(entry["performance_score"] for entry in self.cache.values()) / max(1, len(self.cache))
            
            # Get time range
            timestamps = [entry["timestamp"] for entry in self.cache.values()]
            oldest = min(timestamps) if timestamps else 0
            newest = max(timestamps) if timestamps else 0
            
            return {
                "entries": len(self.cache),
                "max_entries": self.max_entries,
                "avg_performance_score": avg_score,
                "oldest_entry": datetime.fromtimestamp(oldest).isoformat() if oldest else None,
                "newest_entry": datetime.fromtimestamp(newest).isoformat() if newest else None,
                "embedding_available": self.embedding_available
            }

    async def _generate_conversation_data(self, aggregator, workspace_id: str, task_text: str, 
                                         boardroom_session_id: str = None) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Generate conversation summary and pointers using ConversationAggregator.
        
        Args:
            aggregator: ConversationAggregator instance
            workspace_id: The workspace ID to generate conversation data for
            task_text: The task text for context
            boardroom_session_id: Optional BoardRoom session ID
            
        Returns:
            Tuple of (conversation_summary, conversation_pointers)
        """
        try:
            # Get all workspace conversations
            conversations = await aggregator.get_workspace_conversations(workspace_id)
            
            # Get conversation timeline
            timeline = await aggregator.get_conversation_timeline(workspace_id)
            
            # Create context for summary generation
            summary_context = {
                "workspace_id": workspace_id,
                "task_text": task_text,
                "boardroom_session_id": boardroom_session_id,
                "total_conversations": sum([
                    len(conversations.get("user_conversations", [])),
                    len(conversations.get("boardroom_conversations", [])),
                    len(conversations.get("agent_communications", [])),
                    len(conversations.get("task_comments", [])),
                    len(conversations.get("journey_conversations", [])),
                    len(conversations.get("workspace_references", []))
                ]),
                "timeline_events": len(timeline)
            }
            
            # Generate conversation summary
            conversation_summary = {
                "workspace_summary": summary_context,
                "conversation_phases": self._extract_conversation_phases(timeline),
                "key_participants": self._extract_key_participants(conversations),
                "decision_points": self._extract_decision_points(timeline),
                "performance_indicators": {
                    "completion_rate": self._calculate_completion_rate(conversations),
                    "collaboration_effectiveness": self._calculate_collaboration_score(conversations),
                    "timeline_efficiency": self._calculate_timeline_efficiency(timeline)
                },
                "generated_at": datetime.now().isoformat()
            }
            
            # Generate conversation pointers
            conversation_pointers = {
                "boardroom_conversations": [
                    {
                        "conversation_id": conv.get("id"),
                        "journey_id": conv.get("journey_id"),
                        "start_time": conv.get("start_time"),
                        "message_count": conv.get("message_count", 0),
                        "status": conv.get("status")
                    }
                    for conv in conversations.get("boardroom_conversations", [])
                ],
                "user_conversations": [
                    {
                        "conversation_id": conv.get("id"),
                        "session_id": conv.get("session_id"),
                        "title": conv.get("title"),
                        "created_at": conv.get("created_at"),
                        "message_count": conv.get("message_count", 0)
                    }
                    for conv in conversations.get("user_conversations", [])
                ],
                "journey_conversations": [
                    {
                        "journey_id": conv.get("journey_id"),
                        "task": conv.get("task"),
                        "completed": conv.get("completed"),
                        "success": conv.get("success"),
                        "step_count": conv.get("step_count", 0)
                    }
                    for conv in conversations.get("journey_conversations", [])
                ],
                "workspace_references": [
                    {
                        "reference_id": ref.get("id"),
                        "task_hash": ref.get("task_hash"),
                        "performance_score": ref.get("performance_score"),
                        "timestamp": ref.get("timestamp")
                    }
                    for ref in conversations.get("workspace_references", [])
                ],
                "timeline_summary": {
                    "total_events": len(timeline),
                    "event_types": list(set([event.get("type") for event in timeline])),
                    "time_span": {
                        "start": min([event.get("timestamp") for event in timeline]) if timeline else None,
                        "end": max([event.get("timestamp") for event in timeline]) if timeline else None
                    }
                }
            }
            
            logger.info(f"[WORKSPACE_CACHE] Generated conversation summary with {len(timeline)} timeline events and {conversation_summary['workspace_summary']['total_conversations']} conversations")
            
            return conversation_summary, conversation_pointers
            
        except Exception as e:
            logger.error(f"[WORKSPACE_CACHE] Error generating conversation data: {str(e)}")
            return {}, {}
    
    def _extract_conversation_phases(self, timeline: List[Dict]) -> List[Dict]:
        """Extract conversation phases from timeline events"""
        phases = []
        current_phase = None
        
        for event in timeline:
            event_type = event.get("type", "unknown")
            
            if event_type in ["conversation_start", "user_request"]:
                if current_phase:
                    phases.append(current_phase)
                current_phase = {
                    "phase": "initiation",
                    "start_time": event.get("timestamp"),
                    "events": [event]
                }
            elif event_type in ["model_exchange", "agent_communication"]:
                if current_phase:
                    current_phase["phase"] = "processing"
                    current_phase["events"].append(event)
            elif event_type in ["resolution", "completion"]:
                if current_phase:
                    current_phase["phase"] = "resolution"
                    current_phase["end_time"] = event.get("timestamp")
                    current_phase["events"].append(event)
                    phases.append(current_phase)
                    current_phase = None
        
        if current_phase:
            phases.append(current_phase)
        
        return phases
    
    def _extract_key_participants(self, conversations: Dict) -> Dict:
        """Extract key participants from conversations"""
        participants = {}
        
        # Extract from user conversations
        for conv in conversations.get("user_conversations", []):
            user_id = conv.get("user_id", "unknown_user")
            participants[user_id] = participants.get(user_id, 0) + 1
        
        # Extract from agent communications
        for comm in conversations.get("agent_communications", []):
            agent_id = comm.get("agent_id", "unknown_agent")
            participants[agent_id] = participants.get(agent_id, 0) + 1
        
        return participants
    
    def _extract_decision_points(self, timeline: List[Dict]) -> List[Dict]:
        """Extract decision points from timeline"""
        decision_points = []
        
        for event in timeline:
            if event.get("type") in ["decision", "consensus", "escalation"]:
                decision_points.append({
                    "timestamp": event.get("timestamp"),
                    "type": event.get("type"),
                    "content": event.get("content", "")[:100] + "..." if len(event.get("content", "")) > 100 else event.get("content", "")
                })
        
        return decision_points
    
    def _calculate_completion_rate(self, conversations: Dict) -> float:
        """Calculate completion rate from conversations"""
        total_conversations = sum([
            len(conversations.get("user_conversations", [])),
            len(conversations.get("boardroom_conversations", [])),
            len(conversations.get("journey_conversations", []))
        ])
        
        completed_conversations = sum([
            len([c for c in conversations.get("boardroom_conversations", []) if c.get("status") == "completed"]),
            len([c for c in conversations.get("journey_conversations", []) if c.get("completed")])
        ])
        
        return completed_conversations / total_conversations if total_conversations > 0 else 0.0
    
    def _calculate_collaboration_score(self, conversations: Dict) -> float:
        """Calculate collaboration effectiveness score"""
        agent_comms = len(conversations.get("agent_communications", []))
        task_comments = len(conversations.get("task_comments", []))
        total_conversations = sum([len(v) for v in conversations.values() if isinstance(v, list)])
        
        if total_conversations == 0:
            return 0.0
        
        collaboration_ratio = (agent_comms + task_comments) / total_conversations
        return min(collaboration_ratio, 1.0)
    
    def _calculate_timeline_efficiency(self, timeline: List[Dict]) -> float:
        """Calculate timeline efficiency score"""
        if not timeline:
            return 0.0
        
        # Simple efficiency metric based on event density
        time_span = 0
        if len(timeline) > 1:
            timestamps = [event.get("timestamp") for event in timeline if event.get("timestamp")]
            if timestamps:
                time_span = max(timestamps) - min(timestamps)
        
        if time_span == 0:
            return 1.0 if len(timeline) == 1 else 0.5
        
        # Events per unit time (normalized)
        efficiency = len(timeline) / (time_span / 3600)  # Events per hour
        return min(efficiency / 10, 1.0)  # Normalize to 0-1 scale

# Cache initialization states
CACHE_UNINITIALIZED = "UNINITIALIZED"
CACHE_INITIALIZING = "INITIALIZING" 
CACHE_PARTIALLY_INITIALIZED = "PARTIALLY_INITIALIZED"
CACHE_FULLY_INITIALIZED = "FULLY_INITIALIZED"

# Resource tracking for dependencies
class ResourceStatus:
    """Tracks the status of a cache resource."""
    
    def __init__(self, name, is_critical=False, dependencies=None):
        self.name = name
        self.status = "not_loaded"  # not_loaded, loading, loaded, failed
        self.start_time = None
        self.end_time = None
        self.attempt_count = 0
        self.error = None
        self.is_critical = is_critical  # Whether this resource is critical for functionality
        self.dependencies = dependencies or []  # List of resources this one depends on
        self.load_duration = None  # Total time spent loading
        self.waiters = []  # Async events waiting for this resource
        self.lock = threading.RLock()  # Lock for thread safety
        
    def mark_loading(self):
        """Mark resource as currently loading."""
        with self.lock:
            self.status = "loading"
            self.start_time = time.time()
            self.attempt_count += 1
        
    def mark_loaded(self):
        """Mark resource as successfully loaded."""
        with self.lock:
            self.status = "loaded"
            self.end_time = time.time()
            if self.start_time:
                self.load_duration = self.end_time - self.start_time
            
            # Notify any waiters
            for event in self.waiters:
                event.set()
        
    def mark_failed(self, error=None):
        """Mark resource as failed to load."""
        with self.lock:
            self.status = "failed"
            self.end_time = time.time()
            self.error = error
            if self.start_time:
                self.load_duration = self.end_time - self.start_time
                
            # Notify waiters even on failure
            for event in self.waiters:
                event.set()
        
    def is_loaded(self):
        """Check if resource is loaded."""
        with self.lock:
            return self.status == "loaded"
    
    def is_loading(self):
        """Check if resource is currently loading."""
        with self.lock:
            return self.status == "loading"
    
    def is_failed(self):
        """Check if resource failed to load."""
        with self.lock:
            return self.status == "failed"
        
    def get_load_time(self):
        """Get loading time if complete."""
        with self.lock:
            return self.load_duration
    
    def get_status_dict(self):
        """Get resource status as a dictionary for logging and monitoring."""
        with self.lock:
            return {
                "name": self.name,
                "status": self.status,
                "critical": self.is_critical,
                "attempts": self.attempt_count,
                "duration": self.load_duration,
                "dependencies": self.dependencies,
                "error": str(self.error) if self.error else None
            }
    
    async def wait_until_loaded(self, timeout=None):
        """
        Wait until this resource is loaded or failed.
        
        Args:
            timeout: Maximum time to wait in seconds. None means wait indefinitely.
            
        Returns:
            True if resource loaded successfully, False if it failed or timed out
        """
        # If already loaded, return immediately
        if self.is_loaded():
            return True
            
        # If already failed, return immediately
        if self.is_failed():
            return False
            
        # Create an event to wait on
        event = asyncio.Event()
        
        # Add our event to the waiters list
        with self.lock:
            self.waiters.append(event)
            
        try:
            # Wait with optional timeout
            if timeout is not None:
                try:
                    await asyncio.wait_for(event.wait(), timeout=timeout)
                except asyncio.TimeoutError:
                    return False
            else:
                await event.wait()
                
            # Return success based on final status
            return self.is_loaded()
        finally:
            # Remove our event from the waiters list to avoid memory leaks
            with self.lock:
                if event in self.waiters:
                    self.waiters.remove(event)

# Resource dependency graph for initialization
class ResourceDependencyGraph:
    """
    Manages dependencies between resources and coordinates loading.
    
    This class handles the loading order based on dependencies and
    provides wait/notification mechanisms for resource readiness.
    """
    
    def __init__(self):
        self.resources = {}
        self.lock = threading.RLock()
        
    def register_resource(self, name, is_critical=False, dependencies=None):
        """Register a resource in the dependency graph."""
        with self.lock:
            if name not in self.resources:
                self.resources[name] = ResourceStatus(name, is_critical, dependencies)
            return self.resources[name]
                
    def get_resource(self, name):
        """Get a resource by name."""
        with self.lock:
            return self.resources.get(name)
            
    def get_loading_order(self):
        """
        Get the optimal loading order based on dependencies.
        Uses a simple topological sort to ensure dependencies are loaded first.
        """
        with self.lock:
            # Build dependency graph
            graph = {name: res.dependencies for name, res in self.resources.items()}
            
            # Find all resources without dependencies (roots)
            roots = [name for name, deps in graph.items() if not deps]
            
            # Topological sort
            result = []
            while roots:
                # Remove a root from the graph
                node = roots.pop(0)
                result.append(node)
                
                # Find all resources that depend on this one
                for name, deps in list(graph.items()):
                    if node in deps:
                        # Remove this dependency
                        graph[name].remove(node)
                        
                        # If no more dependencies, add to roots
                        if not graph[name]:
                            roots.append(name)
                            
            # Check for cycles
            if len(result) < len(self.resources):
                logger.warning(f"Circular dependencies detected in resource graph: {set(self.resources.keys()) - set(result)}")
                
                # Add remaining resources (those with circular dependencies)
                for name in self.resources:
                    if name not in result:
                        result.append(name)
                        
            return result
    
    def get_critical_resources(self):
        """Get list of critical resources that must be loaded."""
        with self.lock:
            return [name for name, res in self.resources.items() if res.is_critical]
            
    def get_status_summary(self):
        """Get a summary of all resource statuses."""
        with self.lock:
            loaded = [name for name, res in self.resources.items() if res.is_loaded()]
            loading = [name for name, res in self.resources.items() if res.is_loading()]
            failed = [name for name, res in self.resources.items() if res.is_failed()]
            not_loaded = [name for name, res in self.resources.items() 
                          if not res.is_loaded() and not res.is_loading() and not res.is_failed()]
            
            return {
                "total": len(self.resources),
                "loaded": loaded,
                "loading": loading,
                "failed": failed,
                "not_loaded": not_loaded,
                "critical_loaded": all(self.resources[name].is_loaded() 
                                     for name in self.get_critical_resources()),
                "resources": {name: res.get_status_dict() for name, res in self.resources.items()}
            }
            
    async def wait_for_resource(self, name, timeout=None):
        """
        Wait for a specific resource to be loaded.
        
        Args:
            name: Name of the resource to wait for
            timeout: Maximum time to wait in seconds
            
        Returns:
            True if resource loaded, False otherwise
        """
        resource = self.get_resource(name)
        if not resource:
            logger.warning(f"Cannot wait for unknown resource: {name}")
            return False
            
        return await resource.wait_until_loaded(timeout=timeout)
        
    async def wait_for_critical_resources(self, timeout=None):
        """
        Wait for all critical resources to be loaded.
        
        Args:
            timeout: Maximum time to wait in seconds
            
        Returns:
            True if all critical resources loaded, False otherwise
        """
        critical_resources = self.get_critical_resources()
        if not critical_resources:
            return True
            
        # Calculate timeout per resource if specified
        per_resource_timeout = timeout / len(critical_resources) if timeout else None
        
        # Wait for each critical resource
        results = []
        for name in critical_resources:
            result = await self.wait_for_resource(name, timeout=per_resource_timeout)
            results.append(result)
            
        # All critical resources must be loaded
        return all(results)
        
    async def wait_for_all_resources(self, timeout=None):
        """
        Wait for all resources to be loaded.
        
        Args:
            timeout: Maximum time to wait in seconds
            
        Returns:
            True if all resources loaded, False otherwise
        """
        all_resources = list(self.resources.keys())
        if not all_resources:
            return True
            
        # Calculate timeout per resource if specified
        per_resource_timeout = timeout / len(all_resources) if timeout else None
        
        # Wait for each resource
        results = []
        for name in all_resources:
            result = await self.wait_for_resource(name, timeout=per_resource_timeout)
            results.append(result)
            
        # Return the proportion of successfully loaded resources
        return sum(results) / len(results) if results else 1.0

class CacheInitializer:
    """
    Handles initialization of the workspace reference cache system.
    
    This class is responsible for coordinating the initialization of all
    cache resources and tracking their status. It maintains the state machine
    for cache initialization with the following states:
    
    1. UNINITIALIZED: No initialization attempted yet
    2. INITIALIZING: Initialization in progress
    3. PARTIALLY_INITIALIZED: Database loaded, but some resources may be missing
    4. FULLY_INITIALIZED: All resources successfully loaded
    
    The system can function with partial initialization by using fallback mechanisms
    for missing resources (like embedding generation).
    """
    
    def __init__(self):
        self.init_lock = threading.RLock()
        self.init_state = CACHE_UNINITIALIZED
        self.init_complete_event = threading.Event()
        
        # Create resource dependency graph
        self.dependency_graph = ResourceDependencyGraph()
        
        # Register resources with their dependencies
        # Database is critical and has no dependencies
        self.dependency_graph.register_resource("database", is_critical=True)
        
        # SpaCy model is not critical (we have fallbacks) and has no dependencies
        self.dependency_graph.register_resource("spacy_model", is_critical=False)
        
        # Embeddings depend on either spaCy or fallback mechanism, not critical by itself
        self.dependency_graph.register_resource("embeddings", is_critical=False, 
                                              dependencies=["spacy_model"])
        
        # Register additional resources that might be needed
        self.dependency_graph.register_resource("agent_registry", is_critical=False)
        self.dependency_graph.register_resource("docstrings", is_critical=False)
        
        # Performance tracking
        self.initialization_start_time = None
        self.initialization_end_time = None
        self.performance_metrics = {
            "total_time": None,
            "database_time": None,
            "spacy_time": None,
            "embedding_time": None,
            "wait_time": None,
            "resource_times": {}
        }
        
        # Cache instance
        self.cache_instance = None
        
        # Initialize a cancellation token system for initialization
        self.cancellation_requested = False
        
    def get_cache_instance(self):
        """Get the workspace reference cache instance, creating it if needed."""
        if self.cache_instance is None:
            with self.init_lock:
                if self.cache_instance is None:
                    self.cache_instance = WorkspaceReferenceCache()
                    logger.info("Created new WorkspaceReferenceCache instance")
        return self.cache_instance
        
    def get_initialization_status(self):
        """Get the current initialization status as a dictionary."""
        # Get status from dependency graph
        graph_status = self.dependency_graph.get_status_summary()
        
        return {
            "state": self.init_state,
            "resources_loaded": f"{len(graph_status['loaded'])}/{graph_status['total']}",
            "critical_loaded": graph_status['critical_loaded'],
            "resources": graph_status['resources'],
            "initialization_time": (self.initialization_end_time - self.initialization_start_time 
                                   if self.initialization_start_time and self.initialization_end_time 
                                   else None),
            "performance": self.performance_metrics
        }
    
    def request_cancellation(self):
        """Request cancellation of initialization."""
        self.cancellation_requested = True
        logger.info("Initialization cancellation requested")
        
    def _check_cancellation(self):
        """Check if cancellation has been requested."""
        return self.cancellation_requested
        
    async def initialize_cache(self, timeout=60):
        """
        Fully initialize the workspace reference cache.
        
        This method coordinates loading all required resources and handles
        resource dependencies, timeouts, and partial initialization states.
        
        Args:
            timeout: Maximum time in seconds to wait for initialization
            
        Returns:
            The initialized cache instance
        """
        logger.info(f"Starting initialize_cache with timeout {timeout}")
        
        cache = self.get_cache_instance()
        
        # If already fully initialized, return immediately
        if self.init_state == CACHE_FULLY_INITIALIZED:
            print("🚨 CACHE INIT: Already fully initialized, returning immediately")
            logger.info("Cache already fully initialized, returning immediately")
            return cache
            
        # If partially initialized, we can still use database entries
        if self.init_state == CACHE_PARTIALLY_INITIALIZED:
            print("🚨 CACHE INIT: Already partially initialized, continuing")
            logger.info("Cache already partially initialized, will continue with available resources")
            
        # Reset cancellation flag
        self.cancellation_requested = False
        
        # Use a lock to prevent multiple initializations
        print("🚨 CACHE INIT: About to acquire async lock")
        async with self._async_lock():
            print("🚨 CACHE INIT: Acquired async lock successfully")
            # If initialization is already in progress, wait for it to complete
            if self.init_state == CACHE_INITIALIZING:
                print("🚨 CACHE INIT: Already initializing, waiting for completion")
                logger.info("Cache initialization already in progress, waiting for completion")
            else:
                print("🚨 CACHE INIT: Starting new initialization")
                # Start initialization
                self.init_state = CACHE_INITIALIZING
                self.initialization_start_time = time.time()
                logger.info(f"Starting workspace reference cache initialization at {self.initialization_start_time}")
                
                # Get the optimal loading order based on dependencies
                loading_order = self.dependency_graph.get_loading_order()
                print(f"🚨 CACHE INIT: Resource loading order: {loading_order}")
                logger.info(f"Resource loading order: {loading_order}")
                
                # Initialize resources in order
                for resource_name in loading_order:
                    print(f"🚨 CACHE INIT: Starting to load resource: {resource_name}")
                    # Skip if cancellation requested
                    if self._check_cancellation():
                        print("🚨 CACHE INIT: Initialization cancelled by request")
                        logger.warning("Initialization cancelled by request")
                        break
                        
                    # Load the resource
                    resource_start = time.time()
                    if resource_name == "database":
                        print("🚨 CACHE INIT: About to initialize database...")
                        await self._initialize_database(cache)
                        print("🚨 CACHE INIT: Database initialization completed")
                    elif resource_name == "spacy_model":
                        print("🚨 CACHE INIT: About to initialize spaCy model...")
                        await self._initialize_spacy_model(cache)
                        print("🚨 CACHE INIT: spaCy model initialization completed")
                    elif resource_name == "embeddings":
                        print("🚨 CACHE INIT: About to initialize embeddings...")
                        await self._initialize_embeddings(cache)
                        print("🚨 CACHE INIT: Embeddings initialization completed")
                    elif resource_name == "agent_registry":
                        print("🚨 CACHE INIT: About to initialize agent registry...")
                        await self._initialize_agent_registry(cache)
                        print("🚨 CACHE INIT: Agent registry initialization completed")
                    elif resource_name == "docstrings":
                        print("🚨 CACHE INIT: About to initialize docstrings...")
                        await self._initialize_docstrings(cache)
                        print("🚨 CACHE INIT: Docstrings initialization completed")
                    
                    # Record performance metric
                    resource_end = time.time()
                    self.performance_metrics["resource_times"][resource_name] = resource_end - resource_start
                    print(f"🚨 CACHE INIT: Resource {resource_name} took {resource_end - resource_start:.2f} seconds")
                
                # After all resources are initialized or failed, determine the final state
                self._determine_initialization_state(cache)
                
                # Set the event to signal completion
                self.init_complete_event.set()
                
                # Record end time
                self.initialization_end_time = time.time()
                self.performance_metrics["total_time"] = self.initialization_end_time - self.initialization_start_time
                logger.info(f"Cache initialization completed in {self.performance_metrics['total_time']:.2f} seconds with state: {self.init_state}")
        
        # If we didn't initiate the initialization, wait for it to complete with timeout
        if not self.init_complete_event.is_set():
            logger.info(f"Waiting for cache initialization to complete (timeout: {timeout}s)")
            
            # Start wait timer
            wait_start = time.time()
            
            # Wait for critical resources with timeout (always at least wait for database)
            try:
                # Wait for critical resources first
                critical_wait_result = await self.dependency_graph.wait_for_critical_resources(timeout=timeout)
                
                if critical_wait_result:
                    logger.info("All critical resources loaded successfully")
                    
                    # If database is loaded, mark as partially initialized at minimum
                    database_resource = self.dependency_graph.get_resource("database")
                    if database_resource and database_resource.is_loaded():
                        if self.init_state != CACHE_FULLY_INITIALIZED:
                            self.init_state = CACHE_PARTIALLY_INITIALIZED
                            cache.initialized = True
                            logger.info("Cache marked as partially initialized with critical resources")
                else:
                    logger.warning("Failed to load all critical resources within timeout")
                    
                    # Try to force load database as a last resort
                    if not self.dependency_graph.get_resource("database").is_loaded():
                        logger.info("Loading database entries after timeout as fallback")
                        await self._initialize_database_fallback(cache)
            except Exception as e:
                logger.error(f"Error waiting for resource initialization: {str(e)}")
                
                # Try to force load database as a last resort
                if not self.dependency_graph.get_resource("database").is_loaded():
                    logger.info("Loading database entries after exception as fallback")
                    await self._initialize_database_fallback(cache)
            
            # Record wait time
            wait_end = time.time()
            self.performance_metrics["wait_time"] = wait_end - wait_start
            
        # Log final state with detailed resource status
        status = self.get_initialization_status()
        logger.info(f"Cache initialization final status: {status['state']} with {status['resources_loaded']} resources loaded")
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"Detailed resource status: {json.dumps(status['resources'], indent=2)}")
        
        return cache
    
    @contextlib.asynccontextmanager
    async def _async_lock(self):
        """Async context manager for the initialization lock."""
        # Acquire the lock
        self.init_lock.acquire()
        try:
            # Yield control back to the caller
            yield
        finally:
            # Release the lock
            self.init_lock.release()
        
    async def _initialize_database(self, cache):
        """Initialize database entries."""
        print("🚨 DB INIT: Starting database initialization")
        resource = self.dependency_graph.get_resource("database")
        resource.mark_loading()
        
        try:
            print("🚨 DB INIT: About to load database entries...")
            logger.info("Loading database entries...")
            start_time = time.time()
            
            # Use asyncio.to_thread for better async handling
            if hasattr(asyncio, 'to_thread'):
                print("🚨 DB INIT: Using asyncio.to_thread for database loading...")
                await asyncio.to_thread(cache._load_from_db)
                print("🚨 DB INIT: asyncio.to_thread completed")
            else:
                print("🚨 DB INIT: Using run_in_executor for database loading...")
                await asyncio.get_event_loop().run_in_executor(None, cache._load_from_db)
                print("🚨 DB INIT: run_in_executor completed")
                
            end_time = time.time()
            self.performance_metrics["database_time"] = end_time - start_time
            
            resource.mark_loaded()
            logger.info(f"Successfully loaded {len(cache.cache)} database entries in {end_time - start_time:.2f}s")
            return True
        except Exception as e:
            resource.mark_failed(error=str(e))
            logger.error(f"Failed to load database entries: {str(e)}")
            import traceback
            logger.debug(traceback.format_exc())
            return False
    
    async def _initialize_database_fallback(self, cache):
        """Last-resort fallback for loading database entries."""
        try:
            # Force loading database entries directly
            cache._load_from_db()
            
            # Mark resource as loaded
            resource = self.dependency_graph.get_resource("database")
            resource.mark_loaded()
            
            # Mark cache as partially initialized
            if len(cache.cache) > 0:
                self.init_state = CACHE_PARTIALLY_INITIALIZED
                cache.initialized = True
                logger.info(f"Loaded {len(cache.cache)} entries from database via fallback")
            return True
        except Exception as e:
            logger.error(f"Failed to load database entries via fallback: {str(e)}")
            return False
            
    async def _initialize_spacy_model(self, cache):
        """Initialize spaCy model for embeddings."""
        print("🚨 SPACY INIT: Starting spaCy model initialization")
        resource = self.dependency_graph.get_resource("spacy_model")
        resource.mark_loading()
        
        try:
            print("🚨 SPACY INIT: About to load spaCy model...")
            logger.info("Loading spaCy model for embeddings...")
            start_time = time.time()
            
            # Try to import spaCy
            print("🚨 SPACY INIT: Importing spaCy module...")
            import spacy
            print("🚨 SPACY INIT: spaCy module imported successfully")
            
            # Use asyncio.to_thread for better async handling
            if hasattr(asyncio, 'to_thread'):
                print("🚨 SPACY INIT: About to load en_core_web_lg model using asyncio.to_thread...")
                cache.nlp = await asyncio.to_thread(spacy.load, "en_core_web_lg")
                print("🚨 SPACY INIT: en_core_web_lg model loaded successfully")
            else:
                print("🚨 SPACY INIT: About to load en_core_web_lg model using run_in_executor...")
                cache.nlp = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: spacy.load("en_core_web_lg"))
                print("🚨 SPACY INIT: en_core_web_lg model loaded successfully via executor")
            
            end_time = time.time()
            self.performance_metrics["spacy_time"] = end_time - start_time
                    
            cache.embedding_available = True
            resource.mark_loaded()
            logger.info(f"Successfully loaded spaCy model for embeddings in {end_time - start_time:.2f}s")
            
            return True
        except Exception as e:
            resource.mark_failed(error=str(e))
            logger.warning(f"Failed to load spaCy model: {str(e)}")
            # This is non-critical, we can continue with fallback embeddings
            cache.nlp = None
            cache.embedding_available = False
            return False
            
    async def _initialize_embeddings(self, cache):
        """Initialize embedding system."""
        resource = self.dependency_graph.get_resource("embeddings")
        resource.mark_loading()
        
        start_time = time.time()
        
        # Check if spaCy is loaded
        spacy_resource = self.dependency_graph.get_resource("spacy_model")
        if spacy_resource and spacy_resource.is_loaded():
            # Use spaCy embeddings
            resource.mark_loaded()
            logger.info("Using spaCy for embeddings")
        else:
            # Use fallback embeddings
            logger.info("Using fallback hash-based embeddings")
            # Mark as loaded but note it's using fallbacks
            resource.mark_loaded()
            # Track in cache instance
            cache.embedding_available = False
        
        end_time = time.time()
        self.performance_metrics["embedding_time"] = end_time - start_time
        
        return True
    
    async def _initialize_agent_registry(self, cache):
        """Initialize agent registry connection."""
        resource = self.dependency_graph.get_resource("agent_registry")
        resource.mark_loading()
        
        try:
            # Check if agent registry is available
            # This is a lightweight check, just to see if we can import
            logger.info("Checking agent registry availability...")
            
            try:
                # Try to import but catch ModuleNotFoundError specifically
                import sys
                sys.path.append("~/Jarvis")
                
                # Test import only, don't actually load
                from Handler.handler_agent_registry import handler as agent_registry
                
                # If we get here, the import succeeded
                resource.mark_loaded()
                logger.info("Agent registry is available")
                return True
            except ModuleNotFoundError:
                # Module not found, mark as failed but non-critical
                resource.mark_failed(error="Agent registry module not found")
                logger.warning("Agent registry module not found, will use fallbacks")
                return False
            except Exception as e:
                # Other import error
                resource.mark_failed(error=str(e))
                logger.warning(f"Error checking agent registry: {str(e)}")
                return False
                
        except Exception as e:
            resource.mark_failed(error=str(e))
            logger.warning(f"Failed to initialize agent registry: {str(e)}")
            return False
    
    async def _initialize_docstrings(self, cache):
        """Initialize docstrings for semantic search."""
        resource = self.dependency_graph.get_resource("docstrings")
        resource.mark_loading()
        
        try:
            # Check if docstrings.db exists
            import os
            docstrings_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "docstrings.db")
            
            if os.path.exists(docstrings_path):
                # Just check if the file exists, don't actually load it
                # This avoids circular imports with agent_self_documentation
                resource.mark_loaded()
                logger.info(f"Docstrings database found at {docstrings_path}")
                return True
            else:
                resource.mark_failed(error=f"Docstrings database not found at {docstrings_path}")
                logger.warning(f"Docstrings database not found at {docstrings_path}")
                return False
                
        except Exception as e:
            resource.mark_failed(error=str(e))
            logger.warning(f"Failed to initialize docstrings: {str(e)}")
            return False
            
    def _determine_initialization_state(self, cache):
        """Determine the final initialization state based on loaded resources."""
        # Check if critical resources are loaded
        critical_resources_loaded = all(
            self.dependency_graph.get_resource(name).is_loaded() 
            for name in self.dependency_graph.get_critical_resources()
        )
        
        # Check specific important resources
        database_loaded = self.dependency_graph.get_resource("database").is_loaded()
        spacy_loaded = self.dependency_graph.get_resource("spacy_model").is_loaded()
        
        if critical_resources_loaded and spacy_loaded:
            self.init_state = CACHE_FULLY_INITIALIZED
            cache.initialized = True
            logger.info("Cache fully initialized with all resources")
        elif critical_resources_loaded:
            self.init_state = CACHE_PARTIALLY_INITIALIZED
            cache.initialized = True
            logger.info("Cache partially initialized (critical resources only)")
        elif database_loaded:
            self.init_state = CACHE_PARTIALLY_INITIALIZED
            cache.initialized = True
            logger.info("Cache partially initialized (database only)")
        else:
            self.init_state = CACHE_UNINITIALIZED
            cache.initialized = False
            logger.warning("Cache initialization failed for critical resources")

# Global initializer instance
_cache_initializer = CacheInitializer()


def get_workspace_reference_cache() -> WorkspaceReferenceCache:
    """
    Get or create the global workspace reference cache instance.
    
    This function returns the cache instance without waiting for full initialization.
    For operations requiring spaCy or loaded data, use initialize_workspace_reference_cache.
    """
    global _cache_initializer
    return _cache_initializer.get_cache_instance()

async def initialize_workspace_reference_cache(timeout=30) -> WorkspaceReferenceCache:
    """
    Get and fully initialize the workspace reference cache.
    
    This async function ensures the cache is properly initialized with spaCy
    and all data is loaded before returning.
    
    Args:
        timeout: Maximum time in seconds to wait for initialization
    
    Returns:
        WorkspaceReferenceCache: The fully initialized cache
    """
    global _cache_initializer
    
    # Log current initialization state
    logger.info(f"Starting workspace reference cache initialization with current state: {_cache_initializer.init_state}")
    
    # Use the improved initializer
    return await _cache_initializer.initialize_cache(timeout=timeout)


def ensure_cache_initialized(timeout=5):
    """
    Ensure the workspace reference cache is at least partially initialized.
    
    This synchronous function checks if the cache is already initialized, and if not,
    attempts a synchronous initialization to ensure basic functionality.
    
    Args:
        timeout: Maximum time to wait in seconds for initialization
        
    Returns:
        bool: True if initialization succeeded (at least partially), False otherwise
    """
    global _cache_initializer
    
    # Get the current state
    current_state = _cache_initializer.init_state
    
    # If already at least partially initialized, return True
    if current_state in [CACHE_FULLY_INITIALIZED, CACHE_PARTIALLY_INITIALIZED]:
        logger.info(f"Cache already initialized with state {current_state}")
        return True
        
    # Get the cache instance
    cache = get_workspace_reference_cache()
    
    # Check if we already have data in the cache
    if len(cache.cache) > 0 and not getattr(cache, 'initialized', False):
        cache.initialized = True
        # Update state to partially initialized
        _cache_initializer.init_state = CACHE_PARTIALLY_INITIALIZED
        logger.info(f"Cache marked as partially initialized with {len(cache.cache)} entries")
        return True
    
    # Try to initialize by loading from database
    start_time = time.time()
    try:
        # Update state to initializing
        _cache_initializer.init_state = CACHE_INITIALIZING
        
        # Load database data (this is synchronous)
        cache._load_from_db()
        
        # If we loaded data, mark as partially initialized
        if len(cache.cache) > 0:
            cache.initialized = True
            _cache_initializer.init_state = CACHE_PARTIALLY_INITIALIZED
            logger.info(f"Cache synchronously initialized with {len(cache.cache)} entries from database")
            return True
            
        # No data loaded, still uninitialized
        _cache_initializer.init_state = CACHE_UNINITIALIZED
        elapsed = time.time() - start_time
        logger.warning(f"Cache initialization failed - no data loaded (took {elapsed:.2f}s)")
        return False
    except Exception as e:
        # Error during initialization
        _cache_initializer.init_state = CACHE_UNINITIALIZED
        elapsed = time.time() - start_time
        logger.error(f"Error during cache initialization: {str(e)} (took {elapsed:.2f}s)")
        return False

async def integrate_with_agent_registry(task_text: str, workspace_id: str, 
                                       execution_plan: Dict[str, Any], 
                                       performance_metrics: Dict[str, Any],
                                       agent_team: List[Dict[str, Any]] = None,
                                       team_interaction_data: Dict[str, Any] = None,
                                       boardroom_session_id: str = None) -> bool:
    """
    Integrate workspace reference cache with the agent registry system.
    
    This function stores workspace reference data and also updates the agent registry
    with performance metrics for each agent in the team.
    
    Args:
        task_text: The original task text
        workspace_id: The ID of the workspace
        execution_plan: The execution plan used for the task
        performance_metrics: Performance metrics for the execution
        agent_team: List of agents that participated in the workspace, with their roles and contributions
        team_interaction_data: Dictionary containing interaction patterns between agents
        boardroom_session_id: ID of the BoardRoom session if the workspace used BoardRoom
        
    Returns:
        bool: True if the integration was successful, False otherwise
    """
    try:
        # Get the workspace reference cache
        cache = get_workspace_reference_cache()
        
        # Store the workspace reference
        cache_stored = cache.store_workspace_reference(
            task_text=task_text,
            workspace_id=workspace_id,
            execution_plan=execution_plan,
            performance_metrics=performance_metrics,
            agent_team=agent_team,
            team_interaction_data=team_interaction_data,
            boardroom_session_id=boardroom_session_id
        )
        
        # If we have agent team data, update the agent registry with performance metrics
        if agent_team and len(agent_team) > 0:
            try:
                # Import the handler agent registry
                import sys
                sys.path.append("~/Jarvis")
                
                from Handler.handler_agent_registry import handler as agent_registry
                
                # Import the tracking function from boardroom_connector instead of boardroom_utils
                from Jarvis_Agent_SDK.boardroom_connector import track_agent_performance
                
                # Update performance metrics for each agent in the team
                for agent in agent_team:
                    agent_id = agent.get("agent_id", "")
                    role = agent.get("role", "participant")
                    contribution_score = agent.get("contribution_score", 0.5)
                    
                    # Scale the team performance metrics by the agent's contribution
                    agent_metrics = {
                        "success_rate": performance_metrics.get("success_rate", 0.5) * contribution_score,
                        "completion_time": performance_metrics.get("completion_time", 0.0),
                        "quality_score": performance_metrics.get("quality_score", 0.5) * contribution_score,
                    }
                    
                    # Track performance in both systems
                    await track_agent_performance(
                        agent_id=agent_id,
                        agent_name=agent_id,  # Use agent_id as name if not provided
                        agent_type="team_member",
                        workspace_id=workspace_id,
                        task_id=workspace_id,  # Use workspace_id as task_id for correlation
                        success=performance_metrics.get("success_rate", 0.5) > 0.7,
                        completion_time=performance_metrics.get("completion_time", 0.0),
                        quality_score=contribution_score,
                        metadata={
                            "role": role,
                            "contribution_score": contribution_score,
                            "task_text": task_text,
                            "team_size": len(agent_team)
                        }
                    )
                    
                    # Update agent registry with performance data
                    agent_registry.execute_action(
                        "update_agent_performance",
                        {
                            "agent_id": agent_id,
                            "success": performance_metrics.get("success_rate", 0.5) > 0.7,
                            "response_time": performance_metrics.get("completion_time", 0.0)
                        }
                    )
                
                return True
            except Exception as e:
                import logging
                logging.error(f"Error updating agent registry: {str(e)}")
                # Return True anyway since we still stored the workspace reference
                return cache_stored
        
        return cache_stored
        
    except Exception as e:
        import logging
        logging.error(f"Error integrating with agent registry: {str(e)}")
        return False