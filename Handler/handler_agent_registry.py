"""
Agent Registry Handler

This handler manages the registration and retrieval of agents between the file system and database.
It acts as a critical bridge between:

1. File-based agent storage in Handler/Agents/ directory
   - Where AgentBuilder stores agent configurations as files

2. Database-based agent storage in agents.db (v2)
   - Used for agent tracking, performance monitoring, and integration

Core Functionality:
- Register module agents in both storage systems
- Retrieve agent information from either source
- Update agent metadata and status
- Track agent performance metrics
- Enable agent discovery across the system

This handler solves the synchronization problem between file-based and database-based
agent storage, ensuring that agents created in one system are available in the other.
"""

import os
import json
import time
import sqlite3
import logging
import uuid
from typing import Dict, List, Optional, Any, Union
import pathlib
import asyncio
import inspect
import traceback

from Handler.handler_base import BaseHandler, HandlerResult
# BoardRoom was archived (Phase 3). Agent registration writes directly to v2/agents.db.
from Database.v2.db_helper import connection as v2_connection

# Import generate_request_id from Jarvis_Agent_SDK
try:
    from Jarvis_Agent_SDK.import_helper import generate_request_id, generate_simple_id
except ImportError:
    # Fallback implementation if the import fails
    def generate_request_id(task=None):
        """Generate a unique request ID"""
        return str(uuid.uuid4())
    
    def generate_simple_id(prefix="id"):
        """Generate a simple unique ID with the given prefix"""
        return f"{prefix}_{int(time.time())}_{uuid.uuid4().hex[:8]}"

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AgentRegistryHandler(BaseHandler):
    """
    Handler for agent registration and management between file system and database.
    """
    
    def __init__(self, app_name="AgentRegistry", app_version="1.0", db_path=None):
        """Initialize the AgentRegistryHandler."""
        # Default database path if not provided
        if not db_path:
            db_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Database")
            db_path = os.path.join(db_dir, "v2", "agents.db")
            
        super().__init__(app_name=app_name, app_version=app_version, db_path=db_path)
        
        # Set file paths
        self.agents_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Agents")
        
        # Ensure directories exist
        os.makedirs(self.agents_dir, exist_ok=True)
        
        # BoardRoom was archived (Phase 3). Tracking now in handler_swarm.py.
        # Agent registration writes directly to agents.db (v2) — no BoardRoom instance needed.
        self.board_room = None
        
        # Ensure agent registry table exists
        self._ensure_agent_registry_table()
        
    def _ensure_agent_registry_table(self):
        """Ensure the agent_registry and agent_skills tables exist in the database."""
        try:
            # Create the agent_registry table if it doesn't exist
            query = '''
            CREATE TABLE IF NOT EXISTS agent_registry (
                id TEXT PRIMARY KEY,
                agent_id TEXT,
                agent_name TEXT,
                agent_type TEXT,
                module_name TEXT,
                capabilities TEXT,
                status TEXT DEFAULT 'active',
                created_at REAL,
                updated_at REAL,
                metadata TEXT,
                version TEXT DEFAULT '1.0.0',
                compatibility_version TEXT,
                last_success_time REAL,
                success_count INTEGER DEFAULT 0,
                failure_count INTEGER DEFAULT 0,
                avg_response_time REAL DEFAULT 0,
                total_requests INTEGER DEFAULT 0
            )
            '''

            self.db_manager.execute_query(query)

            # Add team_id column if not present
            try:
                cols = [r[1] for r in self.db_manager.execute_query(
                    "PRAGMA table_info(agent_registry)")]
                if 'team_id' not in cols:
                    self.db_manager.execute_query(
                        "ALTER TABLE agent_registry ADD COLUMN team_id TEXT")
                    self.db_manager.get_connection().commit()
            except Exception:
                pass

            # Create the agent_skills table
            self.db_manager.execute_query('''
            CREATE TABLE IF NOT EXISTS agent_skills (
                id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                skill_name TEXT NOT NULL,
                skill_version INTEGER DEFAULT 1,
                skill_type TEXT NOT NULL CHECK(skill_type IN ('mcp_tool', 'python_callable', 'prompt_template')),
                definition_json TEXT NOT NULL,
                performance_score REAL DEFAULT 0.0,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (agent_id) REFERENCES agent_registry(agent_id)
            )
            ''')
            self.db_manager.execute_query(
                'CREATE INDEX IF NOT EXISTS idx_skills_agent ON agent_skills(agent_id)'
            )
            self.db_manager.execute_query(
                'CREATE INDEX IF NOT EXISTS idx_skills_name ON agent_skills(skill_name, skill_version)'
            )
            self.db_manager.get_connection().commit()

            logger.info("Agent registry and agent_skills tables initialized successfully")

        except Exception as e:
            logger.error(f"Error initializing agent registry tables: {str(e)}")
    
    # Action dispatch table for all supported operations
    SUPPORTED_ACTIONS = {
        # Existing actions
        "register_module_agent", "get_agent_performance_report",
        "update_agent_performance", "find_best_agent_version",
        "execute_with_best_agent",
        # Team tracking actions
        "create_team", "get_team_members", "list_teams",
        # Agent skills actions
        "register_skill", "get_agent_skills",
        "update_skill_performance", "get_best_skill_version",
    }

    async def handle(self, task_description: Dict) -> HandlerResult:
        """
        Handle agent registry operations.

        Args:
            task_description: Details of the task to perform

        Returns:
            HandlerResult with the outcome
        """
        action = task_description.get('action')
        parameters = task_description.get('parameters', {})

        if not action:
            return self.create_error_result("No action specified")

        # Forward to the appropriate method
        try:
            if hasattr(self, action):
                method = getattr(self, action)
                if parameters:
                    result = await method(**parameters)
                else:
                    result = await method()
                return result
            else:
                return self.create_error_result(f"Unknown action: {action}")
        except Exception as e:
            return self.create_error_result(f"Error handling task: {str(e)}")
    
    async def register_module_agent(self, agent_id: str, agent_name: str, 
                            agent_type: str, module_name: str,
                            capabilities: List[str] = None, 
                            metadata: Dict = None,
                            version: str = "1.0.0",
                            compatibility_version: str = None,
                            model: str = None,
                            system_prompt_path: str = None) -> HandlerResult:
        """
        Register a module agent in the database with advanced versioning support.
        
        Args:
            agent_id: Unique identifier for the agent
            agent_name: Human-readable name of the agent
            agent_type: Type of agent (e.g., "orchestrator_bridge")
            module_name: Name of the module the agent belongs to
            capabilities: List of agent capabilities
            metadata: Additional agent metadata
            version: Semantic version of the agent (e.g., "1.0.0")
            compatibility_version: Minimum compatibility version required (e.g., "0.9.0")
            
        Returns:
            HandlerResult indicating success or failure
        """
        try:
            # Validate semantic versioning format
            if not self._validate_semantic_version(version):
                return self.create_error_result(f"Invalid semantic version format: {version}. Use format: X.Y.Z")
                
            # Prepare agent data
            agent_data = {
                "agent_id": agent_id,
                "agent_name": agent_name,
                "agent_type": agent_type,
                "module_name": module_name,
                "capabilities": capabilities or [],
                "created_at": time.time(),
                "updated_at": time.time(),
                "status": "active",
                "metadata": metadata or {},
                "version": version,
                "compatibility_version": compatibility_version or version.split('.')[0] + ".0.0",
                "last_success_time": None,
                "success_count": 0,
                "failure_count": 0,
                "avg_response_time": 0,
                "total_requests": 0
            }
            
            # Store model and prompt path for DB columns
            if model:
                agent_data["model"] = model
            if system_prompt_path:
                agent_data["system_prompt_path"] = system_prompt_path

            # Save to database
            db_saved = await self._save_agent_to_database(agent_data)
            
            # Register with BoardRoom if available
            br_registered = await self._register_with_boardroom(agent_data)
            
            if db_saved:
                return self.create_success_result({
                    "agent_id": agent_id,
                    "db_saved": db_saved,
                    "boardroom_registered": br_registered
                })
            else:
                return self.create_error_result("Failed to save agent in database")
                
        except Exception as e:
            logger.error(f"Error registering module agent: {str(e)}")
            return self.create_error_result(f"Error registering module agent: {str(e)}")
    
    async def _save_agent_to_file(self, agent_data: Dict) -> bool:
        """
        Save agent data to the file system.
        
        Args:
            agent_data: Agent data to save
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Create directory for module if it doesn't exist
            module_dir = os.path.join(self.agents_dir, agent_data["module_name"])
            os.makedirs(module_dir, exist_ok=True)
            
            # Create agent file path
            agent_file = os.path.join(module_dir, f"{agent_data['agent_id']}.json")
            
            # Save agent data to file
            with open(agent_file, 'w') as f:
                json.dump(agent_data, f, indent=2)
                
            logger.info(f"Saved agent {agent_data['agent_id']} to file system at {agent_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving agent to file: {str(e)}")
            return False
    
    async def _save_agent_to_database(self, agent_data: Dict) -> bool:
        """
        Save agent data to the database with version management.
        
        Args:
            agent_data: Agent data to save
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Check if agent already exists
            check_query = "SELECT agent_id FROM agent_registry WHERE agent_id = ?"
            cursor = self.db_manager.execute_query(check_query, (agent_data["agent_id"],))
            existing = cursor.fetchone()
            
            capabilities_json = json.dumps(agent_data["capabilities"])
            metadata_json = json.dumps(agent_data["metadata"])
            
            # Get version information from metadata if available
            version_info = agent_data.get("metadata", {}).get("version", "1.0.0")
            
            if existing:
                update_query = """
                UPDATE agent_registry 
                SET agent_name = ?, agent_type = ?, module_name = ?, 
                    capabilities = ?, updated_at = ?, status = ?, metadata = ?,
                    model = ?, system_prompt_path = ?
                WHERE agent_id = ?
                """
                    
                self.db_manager.execute_query(
                    update_query, 
                    (
                        agent_data["agent_name"],
                        agent_data["agent_type"],
                        agent_data["module_name"],
                        capabilities_json,
                        time.time(),
                        "active",
                        metadata_json,
                        agent_data.get("model"),
                        agent_data.get("system_prompt_path"),
                        agent_data["agent_id"]
                    )
                )
                    
                self.db_manager.get_connection().commit()
                logger.info(f"Updated agent {agent_data['agent_id']} in database")
            else:
                # Insert new agent with all fields
                # Insert as new with unique ID
                db_id = str(uuid.uuid4())
                        
                insert_query = """
                INSERT INTO agent_registry
                (id, agent_id, agent_name, agent_type, module_name, capabilities, 
                 created_at, updated_at, status, metadata, model, system_prompt_path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                
                self.db_manager.execute_query(
                    insert_query,
                    (
                        db_id,
                        agent_data["agent_id"],
                        agent_data["agent_name"],
                        agent_data["agent_type"],
                        agent_data["module_name"],
                        capabilities_json,
                        agent_data["created_at"],
                        agent_data["updated_at"],
                        "active",
                        metadata_json,
                        agent_data.get("model"),
                        agent_data.get("system_prompt_path"),
                    )
                )
                
                self.db_manager.get_connection().commit()
                logger.info(f"Created new agent {agent_data['agent_id']} in database")
                
            return True
            
        except Exception as e:
            logger.error(f"Error saving agent to database: {str(e)}")
            traceback.print_exc()
            return False
            
    async def _record_agent_version_history(self, agent_id: str, version: str) -> bool:
        """
        Record an agent version in the version history table.
        
        Args:
            agent_id: The agent ID
            version: The version being recorded
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Ensure the version history table exists
            self.db_manager.execute_query('''
            CREATE TABLE IF NOT EXISTS agent_version_history (
                id TEXT PRIMARY KEY,
                agent_id TEXT,
                version TEXT,
                recorded_at REAL,
                performance_data TEXT
            )
            ''')
            
            # Get the current agent data to preserve performance metrics
            query = "SELECT success_count, failure_count, avg_response_time, total_requests FROM agent_registry WHERE agent_id = ?"
            cursor = self.db_manager.execute_query(query, (agent_id,))
            performance_row = cursor.fetchone()
            
            if performance_row:
                performance_data = {
                    "success_count": performance_row[0],
                    "failure_count": performance_row[1],
                    "avg_response_time": performance_row[2],
                    "total_requests": performance_row[3],
                    "recorded_at": time.time()
                }
                
                # Insert into version history
                history_id = str(uuid.uuid4())
                insert_query = """
                INSERT INTO agent_version_history
                (id, agent_id, version, recorded_at, performance_data)
                VALUES (?, ?, ?, ?, ?)
                """
                
                self.db_manager.execute_query(
                    insert_query,
                    (
                        history_id,
                        agent_id,
                        version,
                        time.time(),
                        json.dumps(performance_data)
                    )
                )
                
                self.db_manager.get_connection().commit()
                logger.info(f"Recorded version history for agent {agent_id} version {version}")
                return True
            else:
                logger.warning(f"No performance data found for agent {agent_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error recording agent version history: {str(e)}")
            return False
    
    async def _register_with_boardroom(self, agent_data: Dict) -> bool:
        """
        Register the agent with BoardRoom for performance tracking.
        
        Args:
            agent_data: Agent data to register
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not self.board_room:
                return False  # BoardRoom archived — agent registration is direct DB write
                
            # Check if the BoardRoom has register_agent method
            if hasattr(self.board_room, 'register_agent'):
                # Get workspace_id from metadata if available
                workspace_id = agent_data.get("metadata", {}).get("workspace_id", "default")
                
                # Determine role based on agent_type
                is_orchestrator = "orchestrator" in agent_data["agent_type"].lower()
                role = "orchestrator" if is_orchestrator else "assistant"
                
                # Prepare capabilities based on agent_type
                capabilities = agent_data["capabilities"]
                if is_orchestrator and "bidirectional_communication" not in capabilities:
                    capabilities.append("bidirectional_communication")
                
                # Register the agent
                success = await self.board_room.register_agent(
                    agent_id=agent_data["agent_id"],
                    agent_name=agent_data["agent_name"],
                    agent_type=agent_data["agent_type"],
                    role=role,
                    workspace_id=workspace_id
                )
                
                if success:
                    logger.info(f"Registered agent {agent_data['agent_id']} with BoardRoom")
                    
                    # Additional setup for orchestrator agents
                    if is_orchestrator:
                        # Register orchestrator specifically with the Jarvis system
                        await self._register_orchestrator_agent(agent_data)
                    
                    return True
                else:
                    logger.warning(f"Failed to register agent {agent_data['agent_id']} with BoardRoom")
                    return False
            else:
                logger.warning("BoardRoom does not have register_agent method")
                return False
                
        except Exception as e:
            logger.error(f"Error registering agent with BoardRoom: {str(e)}")
            return False
    
    async def _register_orchestrator_agent(self, agent_data: Dict) -> bool:
        """
        Register an orchestrator agent with the Jarvis orchestrator for bidirectional communication.
        
        Args:
            agent_data: Agent data for the orchestrator to register
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logger.info(f"Setting up orchestrator agent {agent_data['agent_id']} for bidirectional communication")
            
            # Import the necessary components from Jarvis_Agent_SDK
            try:
                from Jarvis_Agent_SDK.import_helper import get_communication_manager
                from Jarvis_Agent_SDK.jarvis_orchestrator import register_system_in_boardroom
            except ImportError as e:
                logger.error(f"Failed to import required modules for orchestrator registration: {str(e)}")
                return False
            
            # Get the communication manager
            comm_manager = get_communication_manager()
            if not comm_manager:
                logger.warning("Communication manager not available for orchestrator registration")
                return False
            
            # Register the system with detailed description
            system_description = f"Orchestrator agent for {agent_data['module_name']} system with bidirectional communication capabilities"
            
            # Create a list of agent capabilities for registration
            agent_list = [{
                "agent_id": agent_data["agent_id"],
                "agent_name": agent_data["agent_name"],
                "agent_type": agent_data["agent_type"],
                "capabilities": agent_data["capabilities"]
            }]
            
            # Attempt to register with the boardroom/orchestrator
            try:
                result = await register_system_in_boardroom(
                    system_name=agent_data["agent_name"],
                    system_description=system_description,
                    agent_list=agent_list
                )
                
                if result:
                    logger.info(f"Successfully registered orchestrator agent {agent_data['agent_id']} with Jarvis orchestrator")
                    return True
                else:
                    logger.warning(f"Failed to register orchestrator agent with Jarvis orchestrator")
                    return False
                    
            except Exception as e:
                logger.error(f"Error during orchestrator registration with Jarvis: {str(e)}")
                traceback.print_exc()
                return False
                
        except Exception as e:
            logger.error(f"Error in orchestrator agent registration: {str(e)}")
            traceback.print_exc()
            return False
    
    async def get_agent(self, agent_id: str) -> HandlerResult:
        """
        Get an agent by ID from database.
        
        Args:
            agent_id: The agent ID to retrieve
            
        Returns:
            HandlerResult containing agent data or error
        """
        try:
            # Get from database
            db_agent = await self._get_agent_from_database(agent_id)
            
            if db_agent:
                return self.create_success_result(db_agent)
                
            # Agent not found
            return self.create_error_result(f"Agent not found: {agent_id}")
            
        except Exception as e:
            return self.create_error_result(f"Error retrieving agent: {str(e)}")
    
    async def _get_agent_from_database(self, agent_id: str) -> Optional[Dict]:
        """
        Get agent data from the database.
        
        Args:
            agent_id: The agent ID to retrieve
            
        Returns:
            Dict with agent data or None if not found
        """
        try:
            query = "SELECT * FROM agent_registry WHERE agent_id = ?"
            cursor = self.db_manager.execute_query(query, (agent_id,))
            row = cursor.fetchone()
            
            if row:
                # Convert row to dict
                agent_data = dict(zip([column[0] for column in cursor.description], row))
                
                # Parse JSON fields
                agent_data["capabilities"] = json.loads(agent_data["capabilities"])
                agent_data["metadata"] = json.loads(agent_data["metadata"])
                
                return agent_data
            
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving agent from database: {str(e)}")
            return None
    
    async def list_agents(self, module_name: Optional[str] = None, 
                  agent_type: Optional[str] = None) -> HandlerResult:
        """
        List agents matching the provided filters from database.
        
        Args:
            module_name: Optional module name to filter by
            agent_type: Optional agent type to filter by
            
        Returns:
            HandlerResult containing list of matching agents
        """
        try:
            # Get agents from database
            db_agents = await self._list_agents_from_database(module_name, agent_type)
            return self.create_success_result(db_agents)
            
        except Exception as e:
            return self.create_error_result(f"Error listing agents: {str(e)}")
    
    async def _list_agents_from_database(self, module_name: Optional[str] = None,
                               agent_type: Optional[str] = None) -> List[Dict]:
        """
        List agents from the database matching filters.
        
        Args:
            module_name: Optional module name to filter by
            agent_type: Optional agent type to filter by
            
        Returns:
            List of matching agent data dictionaries
        """
        try:
            query = "SELECT * FROM agent_registry WHERE status = 'active'"
            params = []
            
            if module_name:
                query += " AND module_name = ?"
                params.append(module_name)
                
            if agent_type:
                query += " AND agent_type = ?"
                params.append(agent_type)
                
            cursor = self.db_manager.execute_query(query, tuple(params) if params else None)
            rows = cursor.fetchall()
            
            result = []
            for row in rows:
                # Convert row to dict
                agent_data = dict(zip([column[0] for column in cursor.description], row))
                
                # Parse JSON fields
                agent_data["capabilities"] = json.loads(agent_data["capabilities"])
                agent_data["metadata"] = json.loads(agent_data["metadata"])
                
                result.append(agent_data)
                
            return result
            
        except Exception as e:
            logger.error(f"Error listing agents from database: {str(e)}")
            return []
    
    async def update_agent_status(self, agent_id: str, status: str) -> HandlerResult:
        """
        Update an agent's status in the database.
        
        Args:
            agent_id: The agent ID to update
            status: New status ('active', 'inactive', 'deleted')
            
        Returns:
            HandlerResult indicating success or failure
        """
        try:
            # Update in database
            db_updated = await self._update_agent_status_in_db(agent_id, status)
            
            if db_updated:
                return self.create_success_result({
                    "agent_id": agent_id,
                    "status": status,
                    "db_updated": db_updated
                })
            else:
                return self.create_error_result(f"Failed to update agent status: {agent_id}")
                
        except Exception as e:
            return self.create_error_result(f"Error updating agent status: {str(e)}")
    
    async def _update_agent_status_in_db(self, agent_id: str, status: str) -> bool:
        """
        Update an agent's status in the database.
        
        Args:
            agent_id: The agent ID to update
            status: New status
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            query = "UPDATE agent_registry SET status = ?, updated_at = ? WHERE agent_id = ?"
            self.db_manager.execute_query(query, (status, time.time(), agent_id))
            self.db_manager.get_connection().commit()
            
            # Check if any rows were affected
            if self.db_manager.get_connection().total_changes > 0:
                logger.info(f"Updated agent {agent_id} status to {status} in database")
                return True
            else:
                logger.warning(f"No agent {agent_id} found in database to update status")
                return False
                
        except Exception as e:
            logger.error(f"Error updating agent status in database: {str(e)}")
            return False
    
    async def find_agents_by_capability(self, capability: str) -> List[Dict]:
        """
        Find all agents that have a specific capability.
        
        Args:
            capability: The capability to search for
            
        Returns:
            List of agent data dictionaries
        """
        try:
            query = """
            SELECT * FROM agent_registry
            WHERE JSON_EXTRACT(capabilities, '$') LIKE '%' || ? || '%'
            AND status = 'active'
            """
            
            cursor = self.db_manager.execute_query(query, (capability,))
            rows = cursor.fetchall()
            
            results = []
            for row in rows:
                agent_data = dict(zip([column[0] for column in cursor.description], row))
                agent_data["capabilities"] = json.loads(agent_data["capabilities"])
                agent_data["metadata"] = json.loads(agent_data["metadata"])
                results.append(agent_data)
                
            return results
            
        except Exception as e:
            logger.error(f"Error finding agents by capability: {str(e)}")
            return []
            
    async def find_agents_by_capabilities(self, capabilities: List[str]) -> List[Dict]:
        """
        Find all agents that have all of the specified capabilities.
        
        Args:
            capabilities: List of capabilities to search for
            
        Returns:
            List of agent data dictionaries
        """
        try:
            # Build a query that checks for all capabilities
            # Fixed: Using proper SQLite JSON operations instead of json_array_contains
            conditions = " AND ".join(["JSON_EXTRACT(capabilities, '$') LIKE '%' || ? || '%'" for _ in capabilities])
            query = f"""
            SELECT * FROM agent_registry
            WHERE {conditions}
            AND status = 'active'
            """
            
            cursor = self.db_manager.execute_query(query, tuple(capabilities))
            rows = cursor.fetchall()
            
            results = []
            for row in rows:
                agent_data = dict(zip([column[0] for column in cursor.description], row))
                agent_data["capabilities"] = json.loads(agent_data["capabilities"])
                agent_data["metadata"] = json.loads(agent_data["metadata"])
                results.append(agent_data)
                
            return results
            
        except Exception as e:
            logger.error(f"Error finding agents by capabilities: {str(e)}")
            return []
            
    def _validate_semantic_version(self, version_str: str) -> bool:
        """
        Validate that a string follows semantic versioning format.
        
        Args:
            version_str: Version string to validate (e.g., "1.0.0")
            
        Returns:
            bool: True if valid semantic version, False otherwise
        """
        try:
            # Basic pattern check for X.Y.Z format where X, Y, Z are integers
            parts = version_str.split('.')
            if len(parts) != 3:
                return False
                
            # Ensure all parts are integers
            for part in parts:
                int(part)
                
            return True
        except:
            return False
    
    def _is_version_higher(self, version1: str, version2: str) -> bool:
        """
        Compare two semantic versions and determine if version1 is higher than version2.
        
        Args:
            version1: First version string (e.g., "1.2.3")
            version2: Second version string (e.g., "1.2.0")
            
        Returns:
            bool: True if version1 is higher than version2, False otherwise
        """
        if not self._validate_semantic_version(version1) or not self._validate_semantic_version(version2):
            return False
            
        v1_parts = [int(x) for x in version1.split('.')]
        v2_parts = [int(x) for x in version2.split('.')]
        
        # Compare major, minor, patch versions in order
        for i in range(3):
            if v1_parts[i] > v2_parts[i]:
                return True
            elif v1_parts[i] < v2_parts[i]:
                return False
                
        # If we get here, versions are equal
        return False
        
    async def update_agent_performance(self, agent_id: str, success: bool, 
                                   response_time: float) -> HandlerResult:
        """
        Update performance metrics for an agent.
        
        Args:
            agent_id: ID of the agent to update
            success: Whether the agent operation was successful
            response_time: Response time in seconds
            
        Returns:
            HandlerResult indicating success or failure
        """
        try:
            # Get current agent metrics
            query = """
            SELECT success_count, failure_count, avg_response_time, total_requests
            FROM agent_registry WHERE agent_id = ?
            """
            cursor = self.db_manager.execute_query(query, (agent_id,))
            row = cursor.fetchone()
            
            if not row:
                return self.create_error_result(f"Agent {agent_id} not found")
                
            success_count, failure_count, avg_response_time, total_requests = row
            
            # Calculate new metrics
            total_requests += 1
            if success:
                success_count += 1
            else:
                failure_count += 1
                
            # Update average response time using weighted average
            if total_requests > 1:
                avg_response_time = ((avg_response_time * (total_requests - 1)) + response_time) / total_requests
            else:
                avg_response_time = response_time
                
            # Update the metrics in the database
            update_query = """
            UPDATE agent_registry 
            SET success_count = ?, failure_count = ?, avg_response_time = ?, 
                total_requests = ?, last_success_time = ?
            WHERE agent_id = ?
            """
            
            last_success_time = time.time() if success else None
            
            self.db_manager.execute_query(
                update_query,
                (success_count, failure_count, avg_response_time, total_requests, 
                 last_success_time, agent_id)
            )
            self.db_manager.get_connection().commit()
            
            logger.info(f"Updated performance metrics for agent {agent_id}")

            # Propagate performance to skill scores (feedback loop)
            try:
                success_rate = success_count / total_requests if total_requests > 0 else 0.0
                skills_query = "SELECT id, performance_score FROM agent_skills WHERE agent_id = ?"
                skills_cursor = self.db_manager.execute_query(skills_query, (agent_id,))
                skills_rows = skills_cursor.fetchall()
                for skill_row in skills_rows:
                    skill_id, old_score = skill_row
                    # Exponential moving average: 70% old, 30% latest
                    new_score = 0.7 * (old_score or 0.0) + 0.3 * success_rate
                    self.db_manager.execute_query(
                        "UPDATE agent_skills SET performance_score = ?, updated_at = datetime('now') WHERE id = ?",
                        (new_score, skill_id)
                    )
                if skills_rows:
                    self.db_manager.get_connection().commit()
                    logger.info(f"Propagated performance to {len(skills_rows)} skills for agent {agent_id}")
            except Exception as skill_err:
                logger.warning(f"Could not propagate performance to skills: {skill_err}")

            # Return the updated metrics
            return self.create_success_result({
                "agent_id": agent_id,
                "success_count": success_count,
                "failure_count": failure_count,
                "avg_response_time": avg_response_time,
                "total_requests": total_requests,
                "success_rate": success_count / total_requests if total_requests > 0 else 0
            })

        except Exception as e:
            logger.error(f"Error updating agent performance: {str(e)}")
            return self.create_error_result(f"Error updating agent performance: {str(e)}")
            
    # ── Team Tracking Methods ──────────────────────────────────────────

    async def create_team(self, team_name: str, agent_ids: list) -> HandlerResult:
        """
        Create a team from a set of agents.

        Args:
            team_name: Human-readable team name (stored in metadata)
            agent_ids: List of agent_id values to group

        Returns:
            HandlerResult with team_id
        """
        try:
            team_id = str(uuid.uuid4())
            placeholders = ",".join(["?"] * len(agent_ids))
            update_query = f"UPDATE agent_registry SET team_id = ? WHERE agent_id IN ({placeholders})"
            self.db_manager.execute_query(update_query, (team_id, *agent_ids))
            self.db_manager.get_connection().commit()
            logger.info(f"Created team {team_id} ({team_name}) with {len(agent_ids)} agents")
            return self.create_success_result({
                "team_id": team_id,
                "team_name": team_name,
                "agent_count": len(agent_ids)
            })
        except Exception as e:
            logger.error(f"Error creating team: {e}")
            return self.create_error_result(f"Error creating team: {e}")

    async def get_team_members(self, team_id: str) -> HandlerResult:
        """
        Get all agents belonging to a team.

        Args:
            team_id: The team identifier

        Returns:
            HandlerResult with list of agent dicts
        """
        try:
            query = "SELECT * FROM agent_registry WHERE team_id = ?"
            cursor = self.db_manager.execute_query(query, (team_id,))
            rows = cursor.fetchall()
            columns = [col[0] for col in cursor.description]
            members = []
            for row in rows:
                member = dict(zip(columns, row))
                # Parse JSON fields
                if "capabilities" in member and isinstance(member["capabilities"], str):
                    member["capabilities"] = json.loads(member["capabilities"])
                if "metadata" in member and isinstance(member["metadata"], str):
                    member["metadata"] = json.loads(member["metadata"])
                members.append(member)
            return self.create_success_result({"team_id": team_id, "members": members})
        except Exception as e:
            logger.error(f"Error getting team members: {e}")
            return self.create_error_result(f"Error getting team members: {e}")

    async def list_teams(self) -> HandlerResult:
        """
        List all teams with member counts.

        Returns:
            HandlerResult with list of teams
        """
        try:
            query = """
            SELECT team_id, COUNT(*) as member_count
            FROM agent_registry
            WHERE team_id IS NOT NULL
            GROUP BY team_id
            """
            cursor = self.db_manager.execute_query(query)
            rows = cursor.fetchall()
            teams = [{"team_id": row[0], "member_count": row[1]} for row in rows]
            return self.create_success_result({"teams": teams})
        except Exception as e:
            logger.error(f"Error listing teams: {e}")
            return self.create_error_result(f"Error listing teams: {e}")

    # ── Agent Skills Methods ─────────────────────────────────────────

    async def register_skill(self, agent_id: str, skill_name: str,
                             skill_type: str, definition_json: str) -> HandlerResult:
        """
        Register a skill for an agent.  Auto-increments version if
        skill_name already exists for this agent.

        Args:
            agent_id: Owner agent
            skill_name: Name of the skill
            skill_type: One of 'mcp_tool', 'python_callable', 'prompt_template'
            definition_json: JSON string with skill definition

        Returns:
            HandlerResult with skill_id and version
        """
        try:
            # Determine next version
            ver_query = """
            SELECT MAX(skill_version) FROM agent_skills
            WHERE agent_id = ? AND skill_name = ?
            """
            cursor = self.db_manager.execute_query(ver_query, (agent_id, skill_name))
            row = cursor.fetchone()
            next_version = (row[0] or 0) + 1

            skill_id = str(uuid.uuid4())
            insert_query = """
            INSERT INTO agent_skills
            (id, agent_id, skill_name, skill_version, skill_type, definition_json)
            VALUES (?, ?, ?, ?, ?, ?)
            """
            self.db_manager.execute_query(
                insert_query,
                (skill_id, agent_id, skill_name, next_version, skill_type, definition_json)
            )
            self.db_manager.get_connection().commit()
            logger.info(f"Registered skill {skill_name} v{next_version} for agent {agent_id}")
            return self.create_success_result({
                "skill_id": skill_id,
                "skill_name": skill_name,
                "skill_version": next_version
            })
        except Exception as e:
            logger.error(f"Error registering skill: {e}")
            return self.create_error_result(f"Error registering skill: {e}")

    async def get_agent_skills(self, agent_id: str) -> HandlerResult:
        """
        Get all skills for an agent, ordered by name then version descending.

        Args:
            agent_id: The agent to query

        Returns:
            HandlerResult with list of skill dicts
        """
        try:
            query = """
            SELECT id, agent_id, skill_name, skill_version, skill_type,
                   definition_json, performance_score, created_at, updated_at
            FROM agent_skills
            WHERE agent_id = ?
            ORDER BY skill_name, skill_version DESC
            """
            cursor = self.db_manager.execute_query(query, (agent_id,))
            rows = cursor.fetchall()
            columns = [col[0] for col in cursor.description]
            skills = [dict(zip(columns, row)) for row in rows]
            return self.create_success_result({"agent_id": agent_id, "skills": skills})
        except Exception as e:
            logger.error(f"Error getting agent skills: {e}")
            return self.create_error_result(f"Error getting agent skills: {e}")

    async def update_skill_performance(self, skill_id: str,
                                       performance_score: float) -> HandlerResult:
        """
        Update the performance score for a specific skill.

        Args:
            skill_id: The skill to update
            performance_score: New performance score

        Returns:
            HandlerResult indicating success
        """
        try:
            self.db_manager.execute_query(
                "UPDATE agent_skills SET performance_score = ?, updated_at = datetime('now') WHERE id = ?",
                (performance_score, skill_id)
            )
            self.db_manager.get_connection().commit()
            return self.create_success_result({
                "skill_id": skill_id,
                "performance_score": performance_score
            })
        except Exception as e:
            logger.error(f"Error updating skill performance: {e}")
            return self.create_error_result(f"Error updating skill performance: {e}")

    async def get_best_skill_version(self, agent_id: str,
                                     skill_name: str) -> HandlerResult:
        """
        Get the best-performing version of a skill for an agent.

        Args:
            agent_id: The agent owner
            skill_name: The skill to look up

        Returns:
            HandlerResult with the best skill dict
        """
        try:
            query = """
            SELECT id, agent_id, skill_name, skill_version, skill_type,
                   definition_json, performance_score, created_at, updated_at
            FROM agent_skills
            WHERE agent_id = ? AND skill_name = ?
            ORDER BY performance_score DESC
            LIMIT 1
            """
            cursor = self.db_manager.execute_query(query, (agent_id, skill_name))
            row = cursor.fetchone()
            if not row:
                return self.create_error_result(
                    f"No skill '{skill_name}' found for agent {agent_id}"
                )
            columns = [col[0] for col in cursor.description]
            skill = dict(zip(columns, row))
            return self.create_success_result(skill)
        except Exception as e:
            logger.error(f"Error getting best skill version: {e}")
            return self.create_error_result(f"Error getting best skill version: {e}")

    async def get_agent_performance_report(self, agent_id: str = None,
                                      module_name: str = None, top_n: int = 10) -> HandlerResult:
        """
        Get a performance report for agents.
        
        Args:
            agent_id: Optional specific agent ID to report on
            module_name: Optional module name to filter by
            top_n: Number of top agents to include in the report
            
        Returns:
            HandlerResult with performance metrics
        """
        try:
            results = {
                "timestamp": time.time(),
                "report_type": "agent_performance"
            }
            
            # Specific agent report
            if agent_id:
                query = """
                SELECT agent_id, agent_name, version, module_name, 
                       success_count, failure_count, avg_response_time, total_requests,
                       CASE WHEN total_requests > 0 
                            THEN CAST(success_count AS REAL) / total_requests 
                            ELSE 0 
                       END AS success_rate
                FROM agent_registry
                WHERE agent_id = ? AND status = 'active'
                """
                cursor = self.db_manager.execute_query(query, (agent_id,))
                row = cursor.fetchone()
                
                if not row:
                    return self.create_error_result(f"Agent {agent_id} not found or inactive")
                    
                agent_metrics = dict(zip([column[0] for column in cursor.description], row))
                
                # Get version history
                agent_metrics["version_history"] = await self._get_agent_version_history(agent_id)
                
                results["agent"] = agent_metrics
                
            # Module or general report
            else:
                query = """
                SELECT agent_id, agent_name, version, module_name, 
                       success_count, failure_count, avg_response_time, total_requests,
                       CASE WHEN total_requests > 0 
                            THEN CAST(success_count AS REAL) / total_requests 
                            ELSE 0 
                       END AS success_rate
                FROM agent_registry
                WHERE status = 'active'
                """
                
                params = None
                if module_name:
                    query += " AND module_name = ?"
                    params = (module_name,)
                    results["module_name"] = module_name
                    
                # Add sorting and limit
                query += " ORDER BY success_rate DESC, total_requests DESC LIMIT ?"
                if params:
                    params = params + (top_n,)
                else:
                    params = (top_n,)
                    
                cursor = self.db_manager.execute_query(query, params)
                rows = cursor.fetchall()
                
                agent_metrics = []
                for row in rows:
                    metrics = dict(zip([column[0] for column in cursor.description], row))
                    agent_metrics.append(metrics)
                    
                results["top_agents"] = agent_metrics
                results["total_agents"] = len(agent_metrics)
                
                # Calculate summary statistics if we have agents
                if agent_metrics:
                    total_success = sum(a.get("success_count", 0) for a in agent_metrics)
                    total_failure = sum(a.get("failure_count", 0) for a in agent_metrics)
                    total_requests = sum(a.get("total_requests", 0) for a in agent_metrics)
                    
                    # Calculate weighted average response time
                    weighted_times = sum(a.get("avg_response_time", 0) * a.get("total_requests", 0) 
                                        for a in agent_metrics)
                    overall_avg_time = weighted_times / total_requests if total_requests > 0 else 0
                    
                    results["summary"] = {
                        "total_success": total_success,
                        "total_failure": total_failure,
                        "total_requests": total_requests,
                        "overall_success_rate": total_success / total_requests if total_requests > 0 else 0,
                        "overall_avg_response_time": overall_avg_time
                    }
            
            return self.create_success_result(results)
            
        except Exception as e:
            logger.error(f"Error generating agent performance report: {str(e)}")
            traceback.print_exc()
            return self.create_error_result(f"Error generating agent performance report: {str(e)}")
            
    async def _get_agent_version_history(self, agent_id: str) -> List[Dict]:
        """
        Get version history for an agent.
        
        Args:
            agent_id: The agent ID
            
        Returns:
            List of version history entries
        """
        try:
            query = """
            SELECT agent_id, version, recorded_at, performance_data
            FROM agent_version_history
            WHERE agent_id = ?
            ORDER BY recorded_at DESC
            """
            
            cursor = self.db_manager.execute_query(query, (agent_id,))
            rows = cursor.fetchall()
            
            history = []
            for row in rows:
                entry = {
                    "agent_id": row[0],
                    "version": row[1],
                    "recorded_at": row[2],
                    "performance_data": json.loads(row[3])
                }
                history.append(entry)
                
            return history
            
        except Exception as e:
            logger.error(f"Error retrieving agent version history: {str(e)}")
            return []
            
    async def find_best_agent_version(self, base_agent_id: str, 
                                 min_requests: int = 5,
                                 capability_requirements: List[str] = None) -> HandlerResult:
        """
        Find the best performing version of an agent based on performance metrics.
        
        This method analyzes all versions of an agent and returns the one with the 
        best performance based on success rate and response time.
        
        Args:
            base_agent_id: The base agent ID to find the best version for
            min_requests: Minimum number of requests an agent version should have handled
                          to be considered in the analysis (default: 5)
            capability_requirements: List of capabilities the agent must have (optional)
            
        Returns:
            HandlerResult containing the best agent version data or error
            
        Example:
            ```python
            result = await agent_registry.find_best_agent_version("weather_agent", min_requests=5)
            if result.success:
                best_agent_id = result.result["agent_id"]
                # Use this agent ID for task execution
            ```
        """
        try:
            # First, find all versions of this agent
            # We need to consider both the base agent ID and any versioned variants
            pattern = f"{base_agent_id}%"
            
            query = """
            SELECT agent_id, agent_name, version, capabilities,
                   success_count, failure_count, avg_response_time, total_requests,
                   CASE WHEN total_requests >= ? 
                        THEN CAST(success_count AS REAL) / total_requests 
                        ELSE 0 
                   END AS success_rate
            FROM agent_registry
            WHERE (agent_id = ? OR agent_id LIKE ?)
            AND status = 'active'
            AND total_requests >= ?
            """
            
            params = (min_requests, base_agent_id, pattern, min_requests)
                
            cursor = self.db_manager.execute_query(query, params)
            rows = cursor.fetchall()
            
            if not rows:
                return self.create_error_result(
                    f"No agent versions found for {base_agent_id} with at least {min_requests} requests"
                )
                
            # Convert rows to dictionaries for easier manipulation
            columns = [column[0] for column in cursor.description]
            agent_versions = []
            for row in rows:
                agent_data = dict(zip(columns, row))
                
                # Parse JSON fields
                agent_data["capabilities"] = json.loads(agent_data["capabilities"])
                
                # Check capability requirements if specified
                if capability_requirements:
                    has_all_capabilities = all(cap in agent_data["capabilities"] for cap in capability_requirements)
                    if not has_all_capabilities:
                        continue
                        
                agent_versions.append(agent_data)
                
            if not agent_versions:
                error_message = f"No agent versions found for {base_agent_id}"
                if capability_requirements:
                    error_message += f" with required capabilities: {', '.join(capability_requirements)}"
                return self.create_error_result(error_message)
                
            # Define a scoring function that balances success rate and response time
            # This gives 70% weight to success rate and 30% weight to response time
            def calculate_score(agent):
                # Normalize response time (lower is better)
                # We use an upper bound of 10 seconds for normalization
                # This means a response time of 10+ seconds will score 0 on the time component
                normalized_time_score = max(0, 1 - (agent["avg_response_time"] / 10))
                
                # Calculate the combined score
                return (agent["success_rate"] * 0.7) + (normalized_time_score * 0.3)
                
            # Calculate scores for each agent version
            for agent in agent_versions:
                agent["score"] = calculate_score(agent)
                
            # Find the version with the highest score
            best_agent = max(agent_versions, key=lambda x: x["score"])
            
            # Return the best agent version with additional metadata
            result = {
                "agent_id": best_agent["agent_id"],
                "agent_name": best_agent["agent_name"],
                "version": best_agent["version"],
                "success_rate": best_agent["success_rate"],
                "avg_response_time": best_agent["avg_response_time"],
                "total_requests": best_agent["total_requests"],
                "score": best_agent["score"],
                "capabilities": best_agent["capabilities"],
                "comparison": {
                    "total_versions_analyzed": len(agent_versions),
                    "score_components": {
                        "success_rate_weight": 0.7,
                        "response_time_weight": 0.3
                    }
                }
            }
            
            logger.info(
                f"Found best agent version for {base_agent_id}: "
                f"version {best_agent['version']} with score {best_agent['score']:.2f}"
            )
            
            return self.create_success_result(result)
                
        except Exception as e:
            logger.error(f"Error finding best agent version: {str(e)}")
            traceback.print_exc()
            return self.create_error_result(f"Error finding best agent version: {str(e)}")
            
    async def execute_with_best_agent(self, base_agent_id: str, task_parameters: Dict,
                               min_requests: int = 5,
                               capability_requirements: List[str] = None,
                               fallback_to_latest: bool = True) -> HandlerResult:
        """
        Execute a task using the best performing version of an agent.
        
        This method automatically selects the best version of an agent based on
        performance metrics and executes the task with that agent. If no agent
        version meets the minimum requirements, it can optionally fall back to
        the latest version.
        
        Args:
            base_agent_id: The base agent ID to find the best version for
            task_parameters: Parameters to pass to the agent for execution
            min_requests: Minimum number of requests an agent should have handled (default: 5)
            capability_requirements: List of capabilities the agent must have (optional)
            fallback_to_latest: Whether to use the latest version if no version meets
                                the minimum requirements (default: True)
            
        Returns:
            HandlerResult containing the execution result and metadata
            
        Example:
            ```python
            result = await agent_registry.execute_with_best_agent(
                "weather_agent", 
                {"location": "New York", "days": 3},
                min_requests=5
            )
            ```
        """
        try:
            start_time = time.time()
            
            # First try to find the best performing agent version
            best_version_result = await self.find_best_agent_version(
                base_agent_id, 
                min_requests=min_requests,
                capability_requirements=capability_requirements
            )
            
            agent_id_to_use = None
            version_used = None
            selection_method = None
            
            if best_version_result.success:
                # We found a best-performing version, use it
                agent_id_to_use = best_version_result.result["agent_id"]
                version_used = best_version_result.result["version"]
                selection_method = "performance_based"
                logger.info(f"Using best performing agent version: {agent_id_to_use} (v{version_used})")
            elif fallback_to_latest:
                # Try to get the latest version as fallback
                query = """
                SELECT agent_id, version FROM agent_registry
                WHERE (agent_id = ? OR agent_id LIKE ?) AND status = 'active'
                ORDER BY created_at DESC LIMIT 1
                """
                
                pattern = f"{base_agent_id}%"
                cursor = self.db_manager.execute_query(query, (base_agent_id, pattern))
                latest = cursor.fetchone()
                
                if latest:
                    agent_id_to_use = latest[0]
                    version_used = latest[1]
                    selection_method = "latest_version_fallback"
                    logger.info(f"Falling back to latest agent version: {agent_id_to_use} (v{version_used})")
                else:
                    return self.create_error_result(
                        f"No versions found for agent {base_agent_id}"
                    )
            else:
                # Return the error from find_best_agent_version
                return best_version_result
                
            # Now execute the task with the selected agent
            # First, we need to find which module this agent belongs to
            agent_data = await self._get_agent_from_database(agent_id_to_use)
            if not agent_data:
                return self.create_error_result(f"Failed to retrieve agent data for {agent_id_to_use}")
                
            module_name = agent_data["module_name"]
            
            # Use the execute_any_handler utility to execute the task
            try:
                # Import the execute_any_handler function dynamically to avoid circular imports
                from Jarvis_Agent_SDK.import_helper import execute_any_handler
                
                # Execute the task with the selected agent
                execution_result = await execute_any_handler(
                    module_name,
                    "handle",  # Standard handler interface
                    {"agent_id": agent_id_to_use, **task_parameters}
                )
                
                # Calculate response time
                response_time = time.time() - start_time
                
                # Update performance metrics based on execution result
                success = execution_result.get("success", False) if isinstance(execution_result, dict) else False
                await self.update_agent_performance(agent_id_to_use, success, response_time)
                
                # Add metadata to the result
                if isinstance(execution_result, dict):
                    execution_result["__meta"] = {
                        "agent_id": agent_id_to_use,
                        "version": version_used,
                        "selection_method": selection_method,
                        "response_time": response_time
                    }
                    
                return self.create_success_result(execution_result)
                
            except Exception as e:
                logger.error(f"Error executing task with agent {agent_id_to_use}: {str(e)}")
                traceback.print_exc()
                
                # Still update performance metrics (as a failure)
                response_time = time.time() - start_time
                await self.update_agent_performance(agent_id_to_use, False, response_time)
                
                return self.create_error_result(f"Error executing task: {str(e)}")
                
        except Exception as e:
            logger.error(f"Error in execute_with_best_agent: {str(e)}")
            traceback.print_exc()
            return self.create_error_result(f"Error in execute_with_best_agent: {str(e)}")

# Local implementation to avoid circular imports
def run_async_safely(coro):
    """
    Run an async coroutine safely from a sync context.
    
    Args:
        coro: The coroutine to run
        
    Returns:
        The result of the coroutine
    """
    try:
        import asyncio
        import traceback
        
        # Get the current event loop or create a new one
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            # Create a new event loop if none exists
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # Check if we're already in an event loop
        try:
            running_loop = asyncio.get_running_loop() if hasattr(asyncio, 'get_running_loop') else None
            if running_loop:
                # We're already in an event loop, use a different approach
                new_loop = asyncio.new_event_loop()
                try:
                    return new_loop.run_until_complete(coro)
                finally:
                    new_loop.close()
        except RuntimeError:
            # We're not in an event loop, continue normally
            pass
        
        # If the loop is running (but we're not in it), or we need a fresh loop
        if loop.is_running():
            # Create a new event loop for this thread
            new_loop = asyncio.new_event_loop()
            try:
                return new_loop.run_until_complete(coro)
            finally:
                new_loop.close()
        else:
            # We can safely run the coroutine in this loop
            return loop.run_until_complete(coro)
    except Exception as e:
        logger.error(f"Error executing async coroutine: {str(e)}")
        traceback.print_exc()
        return {"status": "error", "message": f"Error executing async action: {str(e)}"}

# Lazy instantiation to avoid circular imports
handler = None

def get_handler():
    """Get the agent registry handler instance, creating it if needed."""
    global handler
    if handler is None:
        handler = AgentRegistryHandler()
    return handler

def execute_action(action, parameters=None):
    """
    Execute an action on the agent registry.
    
    This is the main entry point for executing agent registry actions
    from other modules via the orchestrator.
    
    Args:
        action: The action to perform
        parameters: The parameters for the action
        
    Returns:
        The result of the action
    """
    try:
        handler_instance = get_handler()
        method = getattr(handler_instance, action, None)
        
        if method is None:
            return {"status": "error", "message": f"Unknown action: {action}"}
            
        if inspect.iscoroutinefunction(method):
            # Handle async methods properly
            if parameters is None:
                parameters = {}
                
            # Use run_async_safely to execute the async function
            result = run_async_safely(method(**parameters))
            return result
        else:
            # Regular synchronous methods
            if parameters is None:
                result = method()
            else:
                result = method(**parameters)
            return result
    except Exception as e:
        tb = traceback.format_exc()
        return {"status": "error", "message": f"Error executing async action: {str(e)}", "traceback": tb}

def execute_with_best_agent_version(base_agent_id, task_parameters, min_requests=5, 
                                   capability_requirements=None, fallback_to_latest=True):
    """
    Convenience function to execute a task with the best performing agent version.
    
    This is a synchronous wrapper around the async execute_with_best_agent method,
    making it easier to use from non-async code.
    
    Args:
        base_agent_id: The base agent ID to find the best version for
        task_parameters: Parameters to pass to the agent for execution
        min_requests: Minimum number of requests an agent should have handled (default: 5)
        capability_requirements: List of capabilities the agent must have (optional)
        fallback_to_latest: Whether to use the latest version if no version meets
                           the minimum requirements (default: True)
        
    Returns:
        The execution result with metadata
        
    Example:
        ```python
        result = execute_with_best_agent_version(
            "weather_agent", 
            {"location": "New York", "days": 3}
        )
        print(f"Executed with agent {result['__meta']['agent_id']} v{result['__meta']['version']}")
        ```
    """
    parameters = {
        "base_agent_id": base_agent_id,
        "task_parameters": task_parameters,
        "min_requests": min_requests,
        "capability_requirements": capability_requirements,
        "fallback_to_latest": fallback_to_latest
    }
    
    return execute_action("execute_with_best_agent", parameters)

def _make_json_serializable(obj):
    """
    Convert an object to a JSON-serializable format
    
    Args:
        obj: The object to convert
        
    Returns:
        A JSON-serializable representation of the object
    """
    if hasattr(obj, 'success') and hasattr(obj, 'result'):
        # It's likely a HandlerResult object, convert to dict
        return {
            "success": obj.success,
            "result": obj.result,
            "error": getattr(obj, 'error', None)
        }
    elif asyncio.iscoroutine(obj):
        # It's a coroutine, make it serializable
        return {
            "status": "async_pending",
            "message": "Async operation scheduled but not awaited",
            "coroutine_str": str(obj)
        }
    elif isinstance(obj, dict):
        # Check if all values in the dict are JSON serializable
        try:
            json.dumps(obj)
            return obj
        except (TypeError, OverflowError):
            # If not, convert each value
            return {k: _make_json_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        # Check if all items in the list are JSON serializable
        try:
            json.dumps(obj)
            return obj
        except (TypeError, OverflowError):
            # If not, convert each item
            return [_make_json_serializable(item) for item in obj]
    elif hasattr(obj, '__dict__'):
        # For other objects with a __dict__, convert to dict
        return {k: _make_json_serializable(v) for k, v in obj.__dict__.items()}
    else:
        # For everything else, convert to string
        try:
            json.dumps(obj)
            return obj
        except (TypeError, OverflowError):
            return str(obj) 