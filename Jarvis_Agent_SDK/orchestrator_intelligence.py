"""
Jarvis Orchestrator Intelligence Module

This module creates a bridge between Trevor Core's intelligence capabilities and the 
Jarvis orchestrator agent ecosystem. It leverages Trevor Core's existing learning 
mechanisms while focusing on mapping requests to the appropriate orchestrator agents 
based on their capabilities and past performance.

Core Features:
- Orchestrator agent capability discovery and mapping
- Integration with Trevor Core's learning mechanisms
- Natural language request weighting and performance tracking
- Intelligent orchestration based on historical performance
- Advanced tokenization and semantic pattern matching
"""

import os
import time
import json
import logging
import asyncio
import hashlib
import inspect
import traceback
import importlib
import re
import numpy as np
from typing import Dict, List, Optional, Any, Union, Callable, Tuple, TypeVar
from datetime import datetime, timedelta
from collections import Counter
import uuid
import ast
import sqlite3
import threading
import sys
import types

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize flags for available components
TREVOR_CORE_AVAILABLE = False
NLP_AVAILABLE = False
EMBEDDINGS_AVAILABLE = False
DATABASE_AVAILABLE = False

logger.info("[INTELLIGENCE] Starting initialization of intelligence components...")

# Try to import database utilities
try:
    logger.info("[INTELLIGENCE] Attempting to import database utilities...")
    from Jarvis_Agent_SDK.import_helper import get_unified_database
    from Jarvis_Agent_SDK.database import SQLiteDatabase
    from Jarvis_Agent_SDK.base import DatabaseBase
    DATABASE_AVAILABLE = True
except ImportError:
    logger.warning("Unable to import unified database, falling back to local database")
    get_unified_database = None
    DATABASE_AVAILABLE = False

# Try to import Trevor Core components
try:
    # Make sure Jarvis path is in sys.path
    jarvis_path = "~/Jarvis"
    
    # Only add Jarvis path, NOT the Core path - Trevor Core should come from jarvis_orchestrated_intelligence.py
    if jarvis_path not in sys.path and os.path.exists(jarvis_path):
        sys.path.insert(0, jarvis_path)
        logger.info(f"Added {jarvis_path} to sys.path")
    
    # Check the Python path for debugging
    logger.info(f"Python path: {sys.path}")
    
    # DO NOT import TrevorCore directly in this module
    # It should only be imported and initialized in jarvis_orchestrated_intelligence.py
    TREVOR_CORE_AVAILABLE = False  # Set to False by default
    logger.info("⚠️ orchestrator_intelligence.py is NOT importing or creating Trevor Core instances")
    logger.info("⚠️ Trevor Core should ONLY be imported and created in jarvis_orchestrated_intelligence.py")
except Exception as e:
    logger.error(f"Trevor Core not available, intelligence capabilities will be limited: {str(e)}")
    logger.error(traceback.format_exc())
    TREVOR_CORE_AVAILABLE = False

# ---- LAZY NLP INITIALIZATION ----
# spaCy, NLTK, and sentence_transformers are loaded on first use, not on import.
# This prevents 3-4s delay every time any handler is imported.

NLP_MODEL = None
NLP_AVAILABLE = False
STOP_WORDS = set()
LEMMATIZER = None
EMBEDDINGS_AVAILABLE = False
_nlp_initialized = False
_embeddings_initialized = False

def _ensure_nlp_loaded():
    """Lazy-load spaCy and NLTK on first use."""
    global NLP_MODEL, NLP_AVAILABLE, STOP_WORDS, LEMMATIZER, _nlp_initialized
    if _nlp_initialized:
        return
    _nlp_initialized = True
    
    try:
        import spacy
        logger.info("[INTELLIGENCE] Loading spaCy (lazy init)...")
        
        import nltk
        from nltk.stem import WordNetLemmatizer
        from nltk.corpus import stopwords
        
        # Download required NLTK resources if not already present
        for resource, path in [('tokenizers/punkt', 'punkt'), 
                               ('corpora/stopwords', 'stopwords'),
                               ('corpora/wordnet', 'wordnet')]:
            try:
                nltk.data.find(resource)
            except LookupError:
                nltk.download(path, quiet=True)
        
        # Try to load spaCy model with fallbacks
        for model_name in ["en_core_web_lg", "en_core_web_md", "en_core_web_sm"]:
            try:
                NLP_MODEL = spacy.load(model_name)
                logger.info(f"[INTELLIGENCE] Loaded spaCy model: {model_name}")
                break
            except Exception:
                continue
        
        NLP_AVAILABLE = (NLP_MODEL is not None)
        if NLP_AVAILABLE:
            STOP_WORDS = set(stopwords.words('english'))
            LEMMATIZER = WordNetLemmatizer()
        
        if not NLP_AVAILABLE:
            logger.warning("[INTELLIGENCE] Failed to load any spaCy model")
            
    except ImportError as e:
        logger.warning(f"NLP libraries not available: {str(e)}")

def _ensure_embeddings_loaded():
    """Lazy-load sentence transformers on first use."""
    global EMBEDDINGS_AVAILABLE, _embeddings_initialized
    if _embeddings_initialized:
        return
    _embeddings_initialized = True
    
    try:
        from sentence_transformers import SentenceTransformer
        EMBEDDINGS_AVAILABLE = True
    except ImportError:
        logger.warning("Sentence transformers not available")
        EMBEDDINGS_AVAILABLE = False
    # Simple fallback for embeddings
    class SimpleEmbedding:
        def __init__(self):
            self.model = None
            
        def encode(self, text):
            _ensure_nlp_loaded()
            # Simple word-based embedding
            if NLP_AVAILABLE:
                from nltk.tokenize import word_tokenize
                words = word_tokenize(text.lower())
                words = [LEMMATIZER.lemmatize(w) for w in words if w not in STOP_WORDS]
                import numpy as _np
                return _np.array([hash(w) for w in words], dtype=_np.float32)
            else:
                # Basic character-based embedding if NLP not available
                import numpy as _np
                return _np.array([ord(c) for c in text.lower()], dtype=_np.float32)
    
    SentenceTransformer = SimpleEmbedding

# Database tables and schema
ORCHESTRATOR_REQUEST_MAPPING_TABLE = """
CREATE TABLE IF NOT EXISTS orchestrator_request_mapping (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_text TEXT NOT NULL,
    request_hash TEXT NOT NULL,
    agent_id TEXT,
    response TEXT,
    success INTEGER DEFAULT 0,
    execution_time REAL,
    journey_id TEXT,
    workspace_id TEXT DEFAULT 'default',
    confidence REAL DEFAULT 0.0,
    timestamp REAL,
    embedding_vector BLOB
)
"""

ORCHESTRATOR_AGENT_PERFORMANCE_TABLE = """
CREATE TABLE IF NOT EXISTS orchestrator_agent_performance (
    agent_id TEXT PRIMARY KEY,
    requests INTEGER DEFAULT 0,
    successes INTEGER DEFAULT 0,
    failures INTEGER DEFAULT 0,
    total_time REAL DEFAULT 0.0,
    avg_time REAL DEFAULT 0.0,
    success_rate REAL DEFAULT 0.0,
    workspace_id TEXT DEFAULT 'default',
    last_updated REAL
)
"""

ORCHESTRATOR_CAPABILITY_MAPPING_TABLE = """
CREATE TABLE IF NOT EXISTS orchestrator_capability_mapping (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id TEXT NOT NULL,
    capability TEXT NOT NULL,
    embedding_vector BLOB,
    workspace_id TEXT DEFAULT 'default',
    timestamp REAL
)
"""

# Indexes for performance
ORCHESTRATOR_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_request_mapping_hash ON orchestrator_request_mapping (request_hash)",
    "CREATE INDEX IF NOT EXISTS idx_request_mapping_agent ON orchestrator_request_mapping (agent_id)",
    "CREATE INDEX IF NOT EXISTS idx_request_mapping_workspace ON orchestrator_request_mapping (workspace_id)",
    "CREATE INDEX IF NOT EXISTS idx_performance_workspace ON orchestrator_agent_performance (workspace_id)",
    "CREATE INDEX IF NOT EXISTS idx_capability_agent ON orchestrator_capability_mapping (agent_id)",
    "CREATE INDEX IF NOT EXISTS idx_capability_workspace ON orchestrator_capability_mapping (workspace_id)"
]

class OrchestratorIntelligence:
    """
    Intelligence module for Jarvis Orchestrator managing orchestrator agents and learning.
    
    This module integrates with Trevor Core's intelligence capabilities while focusing on
    discovering, mapping, and optimizing requests to orchestrator agents.
    """
    
    def get_handler_info(self, handler_name):
        """
        Get information about a specific handler.
        
        Args:
            handler_name: Name of the handler to get info for
            
        Returns:
            Dict containing handler information
        """
        # Try to get handler data from database, or return empty dict if not available
        try:
            handler_data = self.get_handler_data_from_db() if hasattr(self, 'get_handler_data_from_db') else {}
            return handler_data.get(handler_name, {})
        except Exception as e:
            logger.error(f"Error getting handler info for {handler_name}: {str(e)}")
            return {}
    
    def __init__(self, 
                 cache_dir: str = None,
                 trevor_core_instance: Any = None,
                 confidence_threshold: float = 0.85,
                 workspace_id: str = None,
                 workspace_root: str = None):
        """Initialize the OrchestratorIntelligence instance.
        
        Args:
            cache_dir: Directory for caching embeddings and other data
            trevor_core_instance: Optional TrevorCore instance for embeddings
            confidence_threshold: Confidence threshold for matches
            workspace_id: Unique workspace identifier
            workspace_root: Root directory of the current workspace
        """
        # Flag to track if initialization has already happened
        self.initialization_complete = False
        
        # Initialize workspace info
        self.workspace_id = workspace_id if workspace_id else "default"
        self.workspace_root = workspace_root
        
        # Set up logging for this instance
        self.logger = logging.getLogger(__name__)
        
        self.cache_dir = cache_dir
        self.confidence_threshold = confidence_threshold
        
        # Trevor bridge attributes
        self.trevor_bridge_initialized = False
        self.trevor_bridge_active = False
        self.trevor_shared_context = {}
        
        # If we don't have a Trevor Core instance yet, try to create one
        # since we've imported the TrevorCore class at the module level
        if trevor_core_instance is None and TREVOR_CORE_AVAILABLE:
            try:
                # Create a new TrevorCore instance
                trevor_core_instance = TrevorCore()
                logger.info(f"Created new TrevorCore instance: {id(trevor_core_instance)}")
            except Exception as e:
                logger.error(f"Error creating TrevorCore instance: {str(e)}")
                trevor_core_instance = None
        
        # Store the Trevor Core instance
        self.trevor_core = trevor_core_instance
        
        # If we have a Trevor Core instance, share it with the bridge
        if self.trevor_core is not None:
            try:
                # Import the bridge module dynamically to avoid circular imports
                import importlib
                bridge_module = importlib.import_module("Jarvis_Agent_SDK.boardroom_orchestrator_bridge")
                
                # Register the Trevor Core instance with the bridge
                if hasattr(bridge_module, 'set_trevor_core_instance'):
                    success = bridge_module.set_trevor_core_instance(self.trevor_core)
                    logger.info(f"Shared TrevorCore instance with bridge: {success}")
                else:
                    logger.warning("Bridge module doesn't have set_trevor_core_instance method")
            except Exception as e:
                logger.warning(f"Error sharing TrevorCore instance with bridge: {str(e)}")
        
        # Database connection
        self.connection = None
        self.db = None
        
        # Initialize embeddings (lazy — loaded on first use)
        _ensure_embeddings_loaded()
        self.embedding_model = SentenceTransformer('paraphrase-MiniLM-L6-v2') if EMBEDDINGS_AVAILABLE else SimpleEmbedding()
        self.embeddings = {}
        self.reverse_index = {}
        
        # Initialize agent tracking
        self.orchestrator_agents = {}
        self.integration_points = {}  # Initialize as dictionary instead of list
        
        # Initialize database using singleton
        logger.info("Initializing database using singleton pattern")
        from Jarvis_Agent_SDK.database_directory import get_database_directory
        self.db_directory = get_database_directory()
        if cache_dir:
            logger.info(f"Cache directory provided: {cache_dir}")
            self._ensure_tables_exist()
        else:
            logger.info("No cache directory provided, using default database directory")
        
        # Initialize embedding model if TrevorCore is available
        if self.trevor_core:
            try:
                logger.info("Initializing embedding model from TrevorCore")
                self.embedding_model = self.trevor_core.get_embedding_model()
                logger.info("Embedding model initialized successfully")
            except Exception as e:
                logger.error(f"Error initializing embedding model: {str(e)}")
        else:
            logger.warning("TrevorCore not provided, embedding functionality will be unavailable")
        
        # Initialize NLP components using lazy singleton
        _ensure_nlp_loaded()
        if NLP_AVAILABLE and NLP_MODEL is not None:
            self.nlp_processor = NLP_MODEL
            logger.info("Using lazy-initialized spaCy model")
        else:
            self.nlp_processor = None
            logger.warning("NLP not initialized. Using heuristic analysis instead.")
        
        # Initialize agent discovery cache
        self.discovered_agents = {}
        
        # Initialize discovered_agents cache
        self.discovered_agents = {}
        
        # Initialize NLP components
        self.use_advanced_nlp = NLP_AVAILABLE
        
        # Define regex patterns for intent extraction
        self.intent_patterns = {
            'send_message': [
                r'send (an?|the) (email|message) to (?P<recipient>[\w\s@.]+)',
                r'email (?P<recipient>[\w\s@.]+)',
                r'message (?P<recipient>[\w\s@.]+)'
            ],
            'schedule_meeting': [
                r'schedule (a |an |the )?meeting with (?P<attendees>[\w\s,@.]+)',
                r'set up (a |an |the )?meeting with (?P<attendees>[\w\s,@.]+)',
                r'create (a |an |the )?calendar event with (?P<attendees>[\w\s,@.]+)'
            ],
            'search_documents': [
                r'search for (?P<query>[\w\s]+) in (my |the )?(documents|files)',
                r'find (?P<query>[\w\s]+) in (my |the )?(documents|files)',
                r'look for (?P<query>[\w\s]+) in (my |the )?(documents|files)'
            ],
            'execute_code': [
                r'run (this |the )?(code|script)',
                r'execute (this |the )?(code|script)',
                r'evaluate (this |the )?(code|script)'
            ]
        }
    
    def tokenize_text(self, text: str) -> List[str]:
        """
        Tokenize text with advanced NLP processing if available.
        
        Args:
            text: Input text to tokenize
            
        Returns:
            List of processed tokens
        """
        if not text:
            return []
            
        # Normalize text
        text = text.lower().strip()
        
        if self.use_advanced_nlp:
            # Use NLTK for advanced tokenization
            from nltk.tokenize import word_tokenize
            tokens = word_tokenize(text)
            
            # Remove stopwords and lemmatize
            _ensure_nlp_loaded()
            tokens = [LEMMATIZER.lemmatize(token) for token in tokens 
                     if token.isalnum() and token not in STOP_WORDS]
            
            return tokens
        else:
            # Basic tokenization fallback
            # Remove punctuation and split by whitespace
            clean_text = re.sub(r'[^\w\s]', ' ', text)
            return [token for token in clean_text.split() if token]
    
    def extract_intent_keywords(self, text: str) -> List[str]:
        """
        Extract intent-focused keywords from text.
        
        Args:
            text: Input text
            
        Returns:
            List of intent keywords
        """
        if not text:
            return []
            
        keywords = []
        
        # Apply intent patterns to extract the core intent phrases
        for pattern in self.intent_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            keywords.extend(matches)
        
        # Fall back to full text tokenization if no patterns matched
        if not keywords:
            return self.tokenize_text(text)
        
        # Tokenize the extracted intent phrases
        all_tokens = []
        for phrase in keywords:
            all_tokens.extend(self.tokenize_text(phrase))
        
        return all_tokens
    
    def compute_text_embedding(self, text: str) -> Optional[np.ndarray]:
        """
        Compute embedding vector for text using sentence transformers.
        
        Args:
            text: Input text
            
        Returns:
            Numpy array of embedding vector or None if not available
        """
        if not self.embedding_model or not text:
            return None
            
        try:
            # Generate embedding
            embedding = self.embedding_model.encode(text, show_progress_bar=False)
            return embedding
        except Exception as e:
            logger.error(f"Error computing embedding: {str(e)}")
            return None
    
    def compute_embedding_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """
        Compute cosine similarity between two embedding vectors.
        
        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
            
        Returns:
            Similarity score between 0 and 1
        """
        if embedding1 is None or embedding2 is None:
            return 0.0
            
        # Compute cosine similarity
        dot_product = np.dot(embedding1, embedding2)
        norm1 = np.linalg.norm(embedding1)
        norm2 = np.linalg.norm(embedding2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
            
        cosine_similarity = dot_product / (norm1 * norm2)
        return float(cosine_similarity)
    
    # Agent discovery and capability extraction
    
    def analyze_handler_with_orchestrator(self, handler_name: str) -> Dict[str, Any]:
        """
        Use the jarvis_orchestrator's analyze_handler_capabilities function to extract
        handler capabilities directly, leveraging the existing handler-orchestrator connection.
        
        Args:
            handler_name: Name of the handler to analyze
            
        Returns:
            Dictionary of handler capabilities and metadata
        """
        try:
            # Try to import the analyzer function from jarvis_orchestrator
            from Jarvis_Agent_SDK.jarvis_orchestrator import analyze_handler_capabilities
            
            # Use the function to analyze the handler
            handler_info = analyze_handler_capabilities(handler_name)
            
            if handler_info:
                logger.info(f"Successfully analyzed handler {handler_name} using orchestrator tools")
                
                # Extract capabilities if available
                capabilities = []
                
                if isinstance(handler_info, dict):
                    # Check for capabilities field
                    if "capabilities" in handler_info:
                        caps = handler_info["capabilities"]
                        if isinstance(caps, list):
                            capabilities.extend(caps)
                        elif isinstance(caps, str):
                            capabilities.append(caps)
                    
                    # Check for actions field
                    if "actions" in handler_info:
                        actions = handler_info["actions"]
                        if isinstance(actions, list):
                            for action in actions:
                                if isinstance(action, dict) and "name" in action and "description" in action:
                                    capabilities.append(f"{action['name']}: {action['description']}")
                                elif isinstance(action, str):
                                    capabilities.append(action)
                    
                    # Add handler name as a capability
                    capabilities.append(f"Handle {handler_name} operations")
                    
                    # Try to get orchestrator agent class information
                    try:
                        # Dynamically import the handler module
                        module_name = f"Handler.handler_{handler_name}"
                        try:
                            handler_module = importlib.import_module(module_name)
                            
                            # Look for orchestrator agent class
                            for attr_name in dir(handler_module):
                                if attr_name.endswith("OrchestratorAgent"):
                                    orchestrator_class = getattr(handler_module, attr_name)
                                    
                                    # Add class info to handler_info
                                    handler_info["orchestrator_agent_class"] = attr_name
                                    handler_info["orchestrator_agent_docstring"] = inspect.getdoc(orchestrator_class)
                                    
                                    # Extract additional capabilities from docstring
                                    doc_capabilities = self._extract_capabilities_from_docstring(
                                        handler_info["orchestrator_agent_docstring"]
                                    )
                                    capabilities.extend(doc_capabilities)
                        except ImportError:
                            logger.warning(f"Could not import handler module {module_name}")
                    except Exception as e:
                        logger.error(f"Error analyzing orchestrator agent class: {str(e)}")
                
                # Add capabilities to handler_info if not already present
                handler_info["capabilities"] = list(set(capabilities))  # Remove duplicates
                
                return handler_info
            else:
                logger.warning(f"No handler info returned for {handler_name}")
                return {"error": f"No information available for handler {handler_name}"}
                
        except ImportError:
            logger.warning("analyze_handler_capabilities not available from jarvis_orchestrator")
            return {"error": "analyze_handler_capabilities not available"}
        except Exception as e:
            logger.error(f"Error analyzing handler with orchestrator: {str(e)}")
            return {"error": str(e)}

    def extract_agent_builder_capabilities(self) -> Dict[str, List[str]]:
        """
        Extract capabilities from AgentBuilder classes to enhance agent understanding.
        
        Returns:
            Dictionary mapping agent types to capabilities
        """
        agent_capabilities = {}
        
        try:
            # Try to import agent builder components
            from Handler.handler_agent_builder import AgentBuilder, AgentType, AgentSpecialization, AgentCapability, AgentTool
            
            # Extract capabilities from AgentType enum
            if hasattr(AgentType, "__members__"):
                for agent_type_name, agent_type in AgentType.__members__.items():
                    agent_capabilities[agent_type_name] = [
                        f"Agent type: {agent_type_name}",
                        f"Specialized in {agent_type_name.lower()} operations"
                    ]
            
            # Extract capabilities from AgentSpecialization enum
            if hasattr(AgentSpecialization, "__members__"):
                for spec_name, spec in AgentSpecialization.__members__.items():
                    if spec_name not in agent_capabilities:
                        agent_capabilities[spec_name] = []
                    
                    agent_capabilities[spec_name].extend([
                        f"Specialization: {spec_name}",
                        f"Expert in {spec_name.lower()} tasks"
                    ])
            
            # Extract capabilities from AgentCapability enum if available
            if hasattr(AgentCapability, "__members__"):
                for cap_name, cap in AgentCapability.__members__.items():
                    if cap_name not in agent_capabilities:
                        agent_capabilities[cap_name] = []
                    
                    agent_capabilities[cap_name].append(f"Capability: {cap_name}")
            
            # Try to get agent builder instance to extract more information
            try:
                agent_builder = AgentBuilder()
                
                # If agent_builder has any methods to list agents or templates
                if hasattr(agent_builder, "list_agent_templates"):
                    templates = agent_builder.list_agent_templates()
                    for template in templates:
                        if isinstance(template, dict) and "name" in template:
                            template_name = template["name"]
                            if template_name not in agent_capabilities:
                                agent_capabilities[template_name] = []
                                
                            agent_capabilities[template_name].append(f"Agent template: {template_name}")
                            
                            if "description" in template:
                                agent_capabilities[template_name].append(template["description"])
            except Exception as e:
                logger.warning(f"Error extracting agent builder templates: {str(e)}")
            
            return agent_capabilities
            
        except ImportError:
            logger.warning("AgentBuilder components not available - could not extract capabilities")
            return {}
        except Exception as e:
            logger.error(f"Error extracting agent builder capabilities: {str(e)}")
            return {}

    def discover_orchestrator_agents(self) -> Dict[str, Any]:
        """
        Scan for orchestrator agents, extract their capabilities, and store the results.
        
        This function:
        1. Scans all Python files in the Handler directory and any other directories
           that might contain orchestrator agents
        2. Looks for classes that contain specific patterns indicating they are orchestrator agents
        3. Extracts capabilities from their docstrings and code
        4. Returns a dictionary with agent information
        
        Returns:
            Dict mapping agent IDs to agent information
        """
        start_time = time.time()
        logging.info("Discovering orchestrator agents...")
        
        # Check if we have cached results first
        if hasattr(self, 'discovered_agents') and self.discovered_agents:
            agent_count = len(self.discovered_agents)
            logging.info(f"Using cached orchestrator agents: {agent_count} entries")
            if agent_count > 0:
                return self.discovered_agents
        
        # Initialize empty results
        discovered_agents = {}
        
        try:
            # Scan the Handler directory first
            handler_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "Handler")
            if os.path.exists(handler_dir) and os.path.isdir(handler_dir):
                handler_files = [f for f in os.listdir(handler_dir) if f.endswith('.py') and not f.startswith('__')]
                self._process_directory_files(handler_dir, handler_files, discovered_agents)
            
            # Scan the main directory for additional orchestrator agents
            main_dir = os.path.dirname(os.path.dirname(__file__))
            if os.path.exists(main_dir) and os.path.isdir(main_dir):
                main_files = [f for f in os.listdir(main_dir) if f.endswith('.py') and not f.startswith('__')]
                # Use empty prefix for main directory files
                self._process_directory_files(main_dir, main_files, discovered_agents, module_prefix="")
            
            # Process subdirectories of the Jarvis_Agent_SDK
            sdk_dir = os.path.dirname(__file__)
            if os.path.exists(sdk_dir) and os.path.isdir(sdk_dir):
                sdk_files = [f for f in os.listdir(sdk_dir) if f.endswith('.py') and not f.startswith('__')]
                # Use Jarvis_Agent_SDK prefix for SDK files
                self._process_directory_files(sdk_dir, sdk_files, discovered_agents, module_prefix="Jarvis_Agent_SDK.")
            
            # Store the results for future use
            self.discovered_agents = discovered_agents
            
            # Log the discovery results
            agent_count = len(discovered_agents)
            elapsed_time = time.time() - start_time
            logging.info(f"Discovered {agent_count} orchestrator agents in {elapsed_time:.2f}s")
            
            # Additional debugging info
            if agent_count == 0:
                logging.warning("No orchestrator agents discovered")
            else:
                for agent_id, agent_info in list(discovered_agents.items())[:5]:  # Show first 5 only
                    capabilities = agent_info.get('capabilities', [])
                    capability_count = len(capabilities)
                    logging.debug(f"Agent {agent_id}: {capability_count} capabilities")
                
                if agent_count > 5:
                    logging.debug(f"... and {agent_count - 5} more agents")
            
            # Update the database with capabilities
            for agent_id, agent_info in discovered_agents.items():
                capabilities = agent_info.get('capabilities', [])
                if capabilities:
                    self.store_agent_capabilities(agent_id, capabilities)
            
            return discovered_agents
            
        except Exception as e:
            logging.error(f"Error discovering orchestrator agents: {str(e)}")
            traceback.print_exc()
            # Don't completely fail - return whatever we found
            self.discovered_agents = discovered_agents
            return discovered_agents
    
    def _process_directory_files(self, directory: str, files: List[str], discovered_agents: Dict, module_prefix: str = "Handler.") -> None:
        """
        Process a list of files in a directory to find orchestrator agents.
        
        Args:
            directory: Base directory path
            files: List of filenames to process
            discovered_agents: Dictionary to store discovered agents
            module_prefix: Prefix to use for module import (e.g., "Handler." for handler modules)
        """
        for filename in files:
            try:
                # Skip __init__.py and other non-handler files in Handler directory
                if module_prefix == "Handler." and (filename.startswith('__') or not filename.startswith('handler_')):
                    continue
                
                # Extract module name without .py extension
                module_name = filename[:-3] if filename.endswith('.py') else filename
                
                # For handler directory, extract handler name from filename
                if module_prefix == "Handler.":
                    handler_name = module_name[8:] if module_name.startswith('handler_') else module_name
                else:
                    # For main directory, use module name as handler name
                    handler_name = module_name
                
                logger.debug(f"Processing potential module: {module_name} from file {filename}")
                
                # First try analyzing handler capabilities using analyzer
                try:
                    # Use local function to avoid circular import with jarvis_orchestrator
                    from Jarvis_Agent_SDK.import_helper import safe_import
                    analyze_func = safe_import('Jarvis_Agent_SDK.jarvis_orchestrator', 'analyze_handler_capabilities')
                    
                    if analyze_func and module_prefix == "Handler.":  # Only use analyzer for handler modules
                        logger.debug(f"Using analyzer to check {handler_name}")
                        handler_info = analyze_func(handler_name)
                        
                        if handler_info and "error" not in handler_info:
                            # Create agent entry from handler info
                            agent_id = f"{handler_name}_orchestrator"
                            
                            if "orchestrator_agent_class" in handler_info:
                                agent_name = handler_info["orchestrator_agent_class"]
                            else:
                                agent_name = f"{handler_name.capitalize()}OrchestratorAgent"
                            
                            # Check for bidirectional communication methods in handler_info
                            bidirectional_communication = False
                            if handler_info.get("has_send_message_to_jarvis"):
                                bidirectional_communication = True
                                logger.debug(f"Handler {handler_name} has send_message_to_jarvis method")
                            if handler_info.get("has_receive_message_from_jarvis"):
                                bidirectional_communication = True
                                logger.debug(f"Handler {handler_name} has receive_message_from_jarvis method")
                            
                            if agent_id not in discovered_agents:
                                discovered_agents[agent_id] = {
                                    "agent_id": agent_id,
                                    "agent_name": agent_name,
                                    "agent_type": "orchestrator_agent",
                                    "system_name": handler_name,
                                    "capabilities": handler_info.get("capabilities", []),
                                    "metadata": {
                                        "handler_name": handler_name,
                                        "handler_info": handler_info
                                    },
                                    "is_orchestrator": True,
                                    "bidirectional_communication": bidirectional_communication,
                                    "source": "orchestrator_analysis"
                                }
                                logger.info(f"Discovered orchestrator agent using analyzer: {agent_name} (bidirectional={bidirectional_communication})")
                            continue
                
                except Exception as e:
                    logger.debug(f"Analyzer approach failed for {module_name}: {str(e)}")
                
                # Fallback to dynamic import approach
                full_module_name = f"{module_prefix}{module_name}" if module_prefix else module_name
                logger.debug(f"Attempting dynamic import for {full_module_name}")
                
                try:
                    # Attempt to import the module
                    module = importlib.import_module(full_module_name)
                    
                    # Look for orchestrator agent classes
                    for attr_name in dir(module):
                        if attr_name.endswith('OrchestratorAgent'):
                            try:
                                # Get the attribute
                                attr = getattr(module, attr_name)
                                
                                # Check if it's a class
                                if inspect.isclass(attr):
                                    logger.debug(f"Found potential orchestrator agent class: {attr_name}")
                                    
                                    # Check for orchestrator agent methods
                                    has_send_message = hasattr(attr, 'send_message_to_jarvis')
                                    has_receive_message = hasattr(attr, 'receive_message_from_jarvis')
                                    
                                    # Extra debug output
                                    if has_send_message:
                                        logger.debug(f"Class {attr_name} has send_message_to_jarvis method")
                                    if has_receive_message:
                                        logger.debug(f"Class {attr_name} has receive_message_from_jarvis method")
                                    
                                    # Only consider it an orchestrator agent if it has at least one of these methods
                                    bidirectional_communication = has_send_message or has_receive_message
                                    
                                    # Extract capabilities
                                    capabilities = []
                                    if hasattr(attr, 'get_capabilities'):
                                        try:
                                            agent_instance = attr()
                                            capabilities = agent_instance.get_capabilities()
                                        except:
                                            # Skip if instantiation fails
                                            pass
                                    
                                    # Create an agent ID
                                    agent_id = f"{handler_name}_{attr_name}"
                                    
                                    if agent_id not in discovered_agents:
                                        discovered_agents[agent_id] = {
                                            "agent_id": agent_id,
                                            "agent_name": attr_name,
                                            "agent_type": "orchestrator_agent",
                                            "system_name": handler_name,
                                            "capabilities": capabilities,
                                            "metadata": {
                                                "handler_name": handler_name,
                                                "module_name": full_module_name,
                                                "class_name": attr_name,
                                                "has_send_message_to_jarvis": has_send_message,
                                                "has_receive_message_from_jarvis": has_receive_message
                                            },
                                            "is_orchestrator": True,
                                            "bidirectional_communication": bidirectional_communication,
                                            "source": "dynamic_discovery"
                                        }
                                        logger.info(f"Discovered orchestrator agent from module: {attr_name} (bidirectional={bidirectional_communication})")
                            except Exception as e:
                                logger.debug(f"Error processing attribute {attr_name}: {str(e)}")
                except Exception as e:
                    logger.error(f"Error importing module {full_module_name}: {str(e)}")
            except Exception as e:
                logger.error(f"Error processing file {filename}: {str(e)}")
    
    def _extract_capabilities_from_docstring(self, docstring: str) -> List[str]:
        """
        Extract capabilities from a docstring.
        
        Args:
            docstring: The docstring to parse
            
        Returns:
            List of capabilities
        """
        if not docstring:
            return []
        
        capabilities = []
        
        # Look for capability-related keywords
        capability_patterns = [
            r"capabilities?:?\s*(.*?)(?:\n\n|\Z)",
            r"(?:handles|supports|provides):?\s*(.*?)(?:\n\n|\Z)",
            r"(?:can|able to):?\s*(.*?)(?:\n\n|\Z)"
        ]
        
        for pattern in capability_patterns:
            matches = re.findall(pattern, docstring, re.IGNORECASE | re.DOTALL)
            for match in matches:
                # Split by commas, bullet points, or newlines
                items = re.split(r'[,•\n]+', match)
                for item in items:
                    item = item.strip()
                    if item and len(item) > 3:  # Minimum length to be meaningful
                        capabilities.append(item)
        
        # Also extract any bullet points
        bullet_matches = re.findall(r'[•-]\s*(.*?)(?:\n|$)', docstring)
        for match in bullet_matches:
            match = match.strip()
            if match and len(match) > 3:
                capabilities.append(match)
        
        return capabilities

    async def process_request(self, request_data: Any, journey_id: str = None) -> Dict[str, Any]:
        """
        Process a request using intelligence and orchestrator mapping.
        
        This method:
        1. Checks database cache for similar requests
        2. Uses Trevor Core if available
        3. Identifies the best agent based on capabilities
        4. Routes the request to the appropriate agent
        
        Args:
            request_data: Request data (string or dictionary)
            journey_id: Optional journey ID for tracking
            
        Returns:
            Dictionary with standard response format
        """
        start_time = time.time()
        
        # Generate a journey ID if not provided for tracking
        if not journey_id:
            journey_id = f"journey_{int(time.time())}_{uuid.uuid4().hex[:8]}"
        
        try:
            # Only discover orchestrator agents once
            if not self.initialization_complete:
                logger.info("First-time orchestrator initialization. Discovering agents and capabilities...")
                # Discover agents and their capabilities
                await self.discover_orchestrator_agents()
                self.initialization_complete = True
                logger.info("Orchestrator initialization complete. Agents and capabilities loaded.")
            
            # Convert request to text for processing
            request_text = self._extract_text_from_request(request_data)
            
            # Generate unique request ID for tracking
            request_hash = hashlib.md5(request_text.encode()).hexdigest()
            
            # Step 1: Check database cache for identical or very similar requests
            if self.db:
                cached_response = await self._check_database_cache(request_text, request_hash)
                if cached_response:
                    logger.info(f"Found cached response in database with confidence {cached_response.get('confidence', 0):.2f}")
                    return {
                        "success": True,
                        "source": "database_cache",
                        "response": cached_response.get("response"),
                        "agent_id": cached_response.get("agent_id"),
                        "confidence": cached_response.get("confidence", 1.0),
                        "execution_time": time.time() - start_time
                    }
            
            # Step 2: Try Trevor Core's capabilities if available
            trevor_intent = None
            entities = None
            
            if self.trevor_bridge_initialized and self.trevor_core:
                try:
                    # Get intent classification from Trevor
                    intent_result = await self.connect_trevor_intent_classification(request_text)
                    if intent_result and intent_result.get("success", False):
                        trevor_intent = intent_result.get("intent")
                        logger.info(f"Trevor classified intent: {trevor_intent}")
                        
                        # If Trevor returned entities, use them
                        if "entities" in intent_result and intent_result["entities"]:
                            entities = intent_result.get("entities")
                        else:
                            # Extract entities using Trevor's NLP
                            entity_result = await self.extract_entities_with_trevor(request_text)
                            if entity_result and entity_result.get("success", False):
                                entities = entity_result.get("entities")
                                logger.info(f"Trevor extracted {len(entities)} entities")
                    
                    # Try to handle the request directly with Trevor if it can
                    if hasattr(self.trevor_core, 'handle_user_request'):
                        # Use Trevor Core to handle the request
                        trevor_success = await self.trevor_core.handle_user_request(request_text)
                        
                        if trevor_success:
                            logger.info(f"Request successfully handled by Trevor Core")
                            return {
                                "success": True,
                                "source": "trevor_core",
                                "execution_time": time.time() - start_time,
                                "intent": trevor_intent,
                                "entities": entities
                            }
                        
                        # If Trevor Core didn't handle it, continue with orchestrator mapping
                        logger.info("Trevor Core unable to handle request, proceeding with orchestrator mapping")
                    
                except Exception as e:
                    logger.error(f"Error using Trevor Core: {str(e)}")
            
            # Step 3: Extract capabilities from the request
            extracted_capabilities = self._extract_capabilities_from_text(request_text)
            logger.info(f"Extracted capabilities from request: {extracted_capabilities}")
            
            # If we have a Trevor intent, add it to our capabilities for better matching
            if trevor_intent:
                enhanced_capabilities = extracted_capabilities + [trevor_intent]
                logger.info(f"Enhanced capabilities with Trevor intent: {enhanced_capabilities}")
            else:
                enhanced_capabilities = extracted_capabilities
            
            # Step 4: Identify best orchestrator agent based on capabilities and request
            best_agent, confidence = await self._find_agent_by_capabilities(enhanced_capabilities)
            
            if best_agent and confidence >= self.confidence_threshold:
                logger.info(f"Found best orchestrator agent {best_agent.get('agent_name', 'unknown')} with confidence {confidence:.2f}")
                
                # Return orchestrator routing suggestion
                return {
                    "success": True,
                    "source": "orchestrator_intelligence",
                    "routing": "orchestrator_agent",
                    "agent": best_agent,
                    "confidence": confidence,
                    "execution_time": time.time() - start_time,
                    "request_hash": request_hash,
                    "intent": trevor_intent,
                    "entities": entities,
                    "capabilities_matched": enhanced_capabilities
                }
            
            # Step 5: If no suitable agent found with high confidence, try with original capabilities
            if not best_agent and trevor_intent:
                # Try again with just the extracted capabilities
                best_agent, confidence = await self._find_agent_by_capabilities(extracted_capabilities)
                
                if best_agent and confidence >= self.confidence_threshold:
                    logger.info(f"Found best agent {best_agent.get('agent_name', 'unknown')} with original capabilities, confidence {confidence:.2f}")
                    return {
                        "success": True,
                        "source": "orchestrator_intelligence",
                        "routing": "orchestrator_agent",
                        "agent": best_agent,
                        "confidence": confidence,
                        "execution_time": time.time() - start_time,
                        "request_hash": request_hash,
                        "intent": trevor_intent,
                        "entities": entities,
                        "capabilities_matched": extracted_capabilities
                    }
            
            # Step 6: If still no suitable agent, look for similar requests in database
            similar_request = await self._find_similar_request_in_db(request_text)
            if similar_request and "agent_id" in similar_request:
                agent_id = similar_request["agent_id"]
                if agent_id in self.orchestrator_agents:
                    similarity = similar_request.get("confidence", 0.7)
                    logger.info(f"Found similar request with confidence {similarity:.2f}")
                    return {
                        "success": True,
                        "source": "similar_request",
                        "routing": "orchestrator_agent",
                        "agent": self.orchestrator_agents[agent_id],
                        "confidence": similarity,
                        "execution_time": time.time() - start_time,
                        "request_hash": request_hash,
                        "intent": trevor_intent,
                        "entities": entities,
                        "similar_to": similar_request.get("request_text", "")
                    }
            
            # Step 7: If still no suitable agent, return standard routing
            return {
                "success": True,
                "source": "orchestrator_intelligence",
                "routing": "standard",
                "confidence": max(0.3, confidence) if confidence else 0.3,  # Set a minimum confidence
                "execution_time": time.time() - start_time,
                "request_hash": request_hash,
                "intent": trevor_intent,
                "entities": entities
            }
            
        except Exception as e:
            logger.error(f"Error processing request: {str(e)}")
            logger.error(traceback.format_exc())
            return {
                "success": False,
                "source": "orchestrator_intelligence",
                "error": str(e),
                "execution_time": time.time() - start_time
            }

    def get_agent_capabilities_from_db(self, agent_id: str = None) -> Dict[str, List[str]]:
        """
        Load agent capabilities from database
        
        Args:
            agent_id: Optional agent ID to filter by
            
        Returns:
            Dictionary mapping agent IDs to capabilities
        """
        if not self.db:
            return {}
        
        try:
            if agent_id:
                query = """
                SELECT agent_id, capability FROM orchestrator_capability_mapping
                WHERE agent_id = ? AND workspace_id = ?
                """
                result = self.db.execute_query(query, (agent_id, self.workspace_id))
            else:
                query = """
                SELECT agent_id, capability FROM orchestrator_capability_mapping
                WHERE workspace_id = ?
                """
                result = self.db.execute_query(query, (self.workspace_id,))
            
            rows = result.fetchall()
            
            capabilities = {}
            for row in rows:
                agent_id = row["agent_id"]
                capability = row["capability"]
                
                if agent_id not in capabilities:
                    capabilities[agent_id] = []
                
                capabilities[agent_id].append(capability)
            
            return capabilities
            
        except Exception as e:
            logger.error(f"Error loading agent capabilities: {str(e)}")
            return {}

    def cleanup_old_requests(self, days_to_keep: int = 30) -> bool:
        """
        Clean up old request mappings to prevent database bloat
        
        Args:
            days_to_keep: Number of days of data to keep
            
        Returns:
            Boolean indicating success
        """
        if not self.db:
            return False
        
        try:
            cutoff_time = time.time() - (days_to_keep * 24 * 60 * 60)
            
            with self.db.transaction():
                # First count how many records will be deleted
                count_query = """
                SELECT COUNT(*) as count FROM orchestrator_request_mapping
                WHERE timestamp < ? AND success = 1
                """
                result = self.db.execute_query(count_query, (cutoff_time,))
                row = result.fetchone()
                count = row["count"] if row else 0
                
                if count > 0:
                    # Delete old records but keep ones with high confidence as training data
                    delete_query = """
                    DELETE FROM orchestrator_request_mapping
                    WHERE timestamp < ? 
                    AND success = 1
                    AND confidence < 0.9
                    """
                    self.db.execute_query(delete_query, (cutoff_time,))
                    
                    logger.info(f"Cleaned up {count} old request mappings from database")
            
            return True
            
        except Exception as e:
            logger.error(f"Error cleaning up old requests: {str(e)}")
            return False

    def establish_direct_handler_connection(self, handler_name: str) -> Dict[str, Any]:
        """
        Establish a direct connection to a handler module through its orchestrator agent.
        This uses the import system to create a communication channel between the
        orchestrator intelligence and the handler module.
        
        Args:
            handler_name: Name of the handler to connect to
            
        Returns:
            Dictionary with connection status and agent reference if successful
        """
        try:
            # Try to dynamically import the handler module
            module_name = f"Handler.handler_{handler_name}"
            handler_module = importlib.import_module(module_name)
            
            # Look for orchestrator agent class
            orchestrator_class = None
            for attr_name in dir(handler_module):
                if attr_name.endswith("OrchestratorAgent"):
                    orchestrator_class = getattr(handler_module, attr_name)
                    break
            
            if not orchestrator_class:
                return {
                    "success": False,
                    "error": f"No orchestrator agent class found in {module_name}"
                }
            
            # Create instance of the orchestrator agent
            orchestrator_instance = None
            try:
                # First try with system_name parameter only
                orchestrator_instance = orchestrator_class(system_name=f"{handler_name}_system")
            except Exception as e:
                logger.warning(f"Could not initialize orchestrator with system_name only: {str(e)}")
                
                try:
                    # See if we can find a handler class
                    handler_class = None
                    for attr_name in dir(handler_module):
                        if attr_name.endswith("Handler") and not attr_name.endswith("OrchestratorAgent"):
                            handler_class = getattr(handler_module, attr_name)
                            break
                    
                    if handler_class:
                        # Try to initialize handler
                        handler_instance = handler_class()
                        
                        # Try to initialize orchestrator with handler instance
                        orchestrator_instance = orchestrator_class(handler_instance)
                except Exception as nested_e:
                    logger.error(f"Could not initialize handler and orchestrator: {str(e)}, {str(nested_e)}")
                    return {
                        "success": False,
                        "error": f"Could not initialize orchestrator agent: {str(e)}, {str(nested_e)}"
                    }
            
            if not orchestrator_instance:
                return {
                    "success": False,
                    "error": "Failed to create orchestrator instance"
                }
            
            # Store the instance for later use
            self.connected_handlers[handler_name] = {
                "orchestrator_instance": orchestrator_instance,
                "orchestrator_class": orchestrator_class,
                "module": handler_module,
                "connection_time": time.time()
            }
            
            # Extract capabilities and metadata from the instance
            capabilities = []
            metadata = {}
            
            # Try to get capabilities from docstring
            if inspect.getdoc(orchestrator_class):
                capabilities.extend(self._extract_capabilities_from_docstring(inspect.getdoc(orchestrator_class)))
            
            # Check if instance has get_info method
            if hasattr(orchestrator_instance, "get_info"):
                try:
                    info = orchestrator_instance.get_info()
                    if isinstance(info, dict):
                        metadata.update(info)
                        
                        # Extract capabilities from info
                        if "capabilities" in info:
                            if isinstance(info["capabilities"], list):
                                capabilities.extend(info["capabilities"])
                            elif isinstance(info["capabilities"], str):
                                capabilities.append(info["capabilities"])
                except Exception as e:
                    logger.warning(f"Error getting info from orchestrator: {str(e)}")
            
            # Check if instance has orchestrator_agent property or attribute
            nested_agent = None
            if hasattr(orchestrator_instance, "orchestrator_agent"):
                try:
                    nested_agent = orchestrator_instance.orchestrator_agent
                    
                    # Extract capabilities from nested agent
                    if hasattr(nested_agent, "get_capabilities"):
                        try:
                            nested_caps = nested_agent.get_capabilities()
                            if isinstance(nested_caps, list):
                                capabilities.extend(nested_caps)
                        except Exception as e:
                            logger.warning(f"Error getting capabilities from nested agent: {str(e)}")
                except Exception as e:
                    logger.warning(f"Error accessing orchestrator_agent property: {str(e)}")
            
            # Return success
            return {
                "success": True,
                "handler_name": handler_name,
                "orchestrator_class": orchestrator_class.__name__,
                "capabilities": list(set(capabilities)),  # Remove duplicates
                "metadata": metadata,
                "nested_agent": nested_agent is not None
            }
        
        except ImportError as e:
            logger.error(f"Could not import handler module {module_name}: {str(e)}")
            return {
                "success": False,
                "error": f"Could not import handler module: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Error establishing direct handler connection: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    def send_message_to_handler(self, handler_name: str, message: str, 
                              message_type: str = "query", context: Dict = None) -> Dict[str, Any]:
        """
        Send a message to a handler module through its orchestrator agent.
        
        Args:
            handler_name: Name of the handler to send the message to
            message: Message content to send
            message_type: Type of message (query, command, etc.)
            context: Additional context information
            
        Returns:
            Dictionary with response information
        """
        # First check if we have a connection to this handler
        if handler_name not in self.connected_handlers:
            # Try to establish connection
            connection_result = self.establish_direct_handler_connection(handler_name)
            if not connection_result.get("success", False):
                return {
                    "success": False,
                    "error": f"Could not establish connection to handler: {connection_result.get('error')}"
                }
        
        # Get the orchestrator instance
        handler_info = self.connected_handlers[handler_name]
        orchestrator_instance = handler_info.get("orchestrator_instance")
        
        if not orchestrator_instance:
            return {
                "success": False,
                "error": "No orchestrator instance available"
            }
        
        # Check if the orchestrator has the right method
        if not hasattr(orchestrator_instance, "send_message_to_jarvis") and not hasattr(orchestrator_instance, "receive_message_from_jarvis"):
            return {
                "success": False,
                "error": "Orchestrator does not have required messaging methods"
            }
        
        # Generate journey ID if not in context
        journey_id = None
        if context and "journey_id" in context:
            journey_id = context["journey_id"]
        else:
            journey_id = f"intel_{int(time.time())}_{handler_name}"
            if context is None:
                context = {}
            context["journey_id"] = journey_id
        
        try:
            # Try to send message
            response = None
            
            # First check if instance has receive_message_from_jarvis
            if hasattr(orchestrator_instance, "receive_message_from_jarvis"):
                if asyncio.iscoroutinefunction(orchestrator_instance.receive_message_from_jarvis):
                    # Handle async method - create and run a coroutine in sync context
                    try:
                        loop = asyncio.get_event_loop()
                        response = loop.run_until_complete(orchestrator_instance.receive_message_from_jarvis(
                            message=message,
                            context=context,
                            message_type=message_type
                        ))
                    except RuntimeError:
                        # If no event loop, create one
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        response = loop.run_until_complete(orchestrator_instance.receive_message_from_jarvis(
                            message=message,
                            context=context,
                            message_type=message_type
                        ))
                else:
                    # Call synchronous method
                    response = orchestrator_instance.receive_message_from_jarvis(
                        message=message,
                        context=context,
                        message_type=message_type
                    )
            
            # If no response yet, try send_message_to_jarvis
            if response is None and hasattr(orchestrator_instance, "send_message_to_jarvis"):
                if asyncio.iscoroutinefunction(orchestrator_instance.send_message_to_jarvis):
                    # Handle async method
                    try:
                        loop = asyncio.get_event_loop()
                        response = loop.run_until_complete(orchestrator_instance.send_message_to_jarvis(
                            message=message,
                            context=context,
                            message_type=message_type
                        ))
                    except RuntimeError:
                        # If no event loop, create one
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        response = loop.run_until_complete(orchestrator_instance.send_message_to_jarvis(
                            message=message,
                            context=context,
                            message_type=message_type
                        ))
                else:
                    # Call synchronous method
                    response = orchestrator_instance.send_message_to_jarvis(
                        message=message,
                        context=context,
                        message_type=message_type
                    )
            
            # Process response
            if response is None:
                return {
                    "success": False,
                    "error": "No response received from handler"
                }
            
            # Return response
            return {
                "success": True,
                "handler_name": handler_name,
                "response": response,
                "journey_id": journey_id
            }
        
        except Exception as e:
            logger.error(f"Error sending message to handler {handler_name}: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "journey_id": journey_id
            }

    def integrate_with_jarvis_orchestrator(self) -> bool:
        """
        Enhance the Jarvis orchestrator's route_task_to_appropriate_system function
        with the intelligence capabilities provided by this module.
        
        Returns:
            bool indicating success or failure of integration
        """
        try:
            # Import the necessary functions from jarvis_orchestrator
            from Jarvis_Agent_SDK.jarvis_orchestrator import route_task_to_appropriate_system
            from Jarvis_Agent_SDK.jarvis_orchestrator import track_request_journey, get_board_room
            
            # Define enhanced version of the route_task function that uses intelligence
            async def intelligence_enhanced_route_task(task_data):
                """Enhanced version of route_task that uses orchestrator intelligence"""
                # Get original task data
                task_text = task_data.get("task", "")
                task_type = task_data.get("type", "natural_language")
                journey_id = task_data.get("journey_id", f"intel_journey_{int(time.time())}")
                is_test = task_data.get("test", False)
                
                # Log the start of intelligent routing
                logger.info(f"Intelligence-enhanced routing for task: {task_text[:50]}... (journey: {journey_id})")
                
                try:
                    # Process the request with intelligence
                    intelligence_result = self.process_request(task_text)
                    
                    # If we have a recommended agent, use it
                    if intelligence_result and intelligence_result.get("best_agent") and not is_test:
                        recommended_agent = intelligence_result.get("best_agent")
                        confidence = intelligence_result.get("confidence", 0)
                        capabilities = intelligence_result.get("extracted_capabilities", [])
                        
                        # Log the recommendation
                        logger.info(f"Intelligence recommends {recommended_agent} with confidence {confidence}")
                        
                        # Track this recommendation
                        await track_request_journey(
                            journey_id=journey_id,
                            step_name="intelligence_recommendation",
                            step_data={
                                "recommended_agent": recommended_agent,
                                "confidence": confidence,
                                "extracted_capabilities": capabilities
                            }
                        )
                        
                        # For high confidence recommendations, directly route to the agent
                        if confidence >= 0.75:
                            # Add intelligence data to task data
                            task_data["intelligence_data"] = intelligence_result
                            
                            # Return the handler details
                            return {
                                "handler": recommended_agent,
                                "confidence": confidence,
                                "source": "orchestrator_intelligence",
                                "journey_id": journey_id
                            }
                    
                    # If test mode or no high-confidence recommendation, fall back to standard routing
                    # but add the intelligence data to help with analysis
                    if intelligence_result:
                        task_data["intelligence_data"] = intelligence_result
                        
                        # Log fallback
                        if not is_test:
                            logger.info("Falling back to standard routing with intelligence augmentation")
                            
                            # Track fallback decision
                            await track_request_journey(
                                journey_id=journey_id,
                                step_name="intelligence_fallback",
                                step_data={
                                    "reason": "low_confidence" if intelligence_result.get("best_agent") else "no_agent",
                                    "extracted_capabilities": intelligence_result.get("extracted_capabilities", [])
                                }
                            )
                        else:
                            logger.info("Test mode - would use intelligence recommendation")
                    
                except Exception as intel_error:
                    # Log error but continue with standard routing
                    logger.error(f"Error in intelligence routing: {str(intel_error)}")
                    task_data["intelligence_error"] = str(intel_error)
                
                # Fall back to standard routing
                return await route_task_to_appropriate_system(task_data)
            
            # Make the enhanced function available in the jarvis_orchestrator module
            import sys
            sys.modules["Jarvis_Agent_SDK.jarvis_orchestrator"].intelligence_enhanced_route_task = intelligence_enhanced_route_task
            
            # Log success
            logger.info("Successfully integrated with jarvis_orchestrator")
            self.integrated_with_orchestrator = True
            return True
            
        except ImportError as e:
            logger.error(f"Could not import from jarvis_orchestrator: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error integrating with jarvis_orchestrator: {str(e)}")
            return False

    def get_agent_metrics(self) -> Dict[str, Dict[str, Any]]:
        """
        Get performance metrics for all agents.
        
        Returns:
            Dict mapping agent_id to metrics
        """
        metrics = {}
        
        # Return cached performance metrics if available
        if hasattr(self, "agent_performance") and self.agent_performance:
            return self.agent_performance
        
        # Otherwise load from database
        if self.db:
            try:
                query = """
                SELECT * FROM orchestrator_agent_performance
                """
                result = self.db.execute_query(query)
                rows = result.fetchall()
                
                for row in rows:
                    agent_id = row.get("agent_id")
                    if agent_id:
                        metrics[agent_id] = {
                            "agent_id": agent_id,
                            "requests": row.get("requests", 0),
                            "successes": row.get("successes", 0),
                            "failures": row.get("failures", 0),
                            "total_time": row.get("total_time", 0),
                            "avg_time": row.get("avg_time", 0),
                            "success_rate": row.get("success_rate", 0),
                            "last_updated": row.get("last_updated", 0)
                        }
            except Exception as e:
                logger.error(f"Error retrieving agent metrics: {str(e)}")
        
        return metrics

   
    
    def identify_best_agent_for_request(self, request_data: Any) -> Tuple[Optional[Dict], float]:
        """
        Identify the best orchestrator agent for a request.
        
        Args:
            request_data: The request to route
            
        Returns:
            Tuple of (agent_info, confidence_score)
        """
        if not self.orchestrator_agents:
            # Discover agents if not already done
            self.discover_orchestrator_agents()
            
            if not self.orchestrator_agents:
                logger.warning("No orchestrator agents discovered")
                return None, 0.0
        
        try:
            # Convert request to text for matching
            request_text = request_data
            if isinstance(request_data, dict):
                if "text" in request_data:
                    request_text = request_data["text"]
                elif "query" in request_data:
                    request_text = request_data["query"]
                elif "message" in request_data:
                    request_text = request_data["message"]
                else:
                    # Extract all string values
                    text_values = []
                    for key, value in request_data.items():
                        if isinstance(value, str):
                            text_values.append(value)
                    request_text = " ".join(text_values)
            
            if not isinstance(request_text, str):
                request_text = str(request_text)
            
            # First check if we have any previous mappings for similar requests
            if self.db:
                similar_request = self._find_similar_request_in_db(request_text)
                if similar_request and "agent_id" in similar_request:
                    agent_id = similar_request["agent_id"]
                    if agent_id in self.orchestrator_agents:
                        similarity = self._calculate_text_similarity(
                            request_text, similar_request["request_text"]
                        )
                        if similarity > 0.8:  # High confidence threshold
                            return self.orchestrator_agents[agent_id], similarity
            
            # Calculate text similarity scores against agent capabilities
            agent_scores = {}
            for agent_id, agent_info in self.orchestrator_agents.items():
                capabilities = self.agent_capabilities.get(agent_id, [])
                agent_score = 0.0
                
                # Calculate similarity to each capability
                for capability in capabilities:
                    similarity = self._calculate_text_similarity(request_text, capability)
                    agent_score = max(agent_score, similarity)
                
                # Factor in past performance if available
                if agent_id in self.agent_performance:
                    perf = self.agent_performance[agent_id]
                    success_rate = perf.get("success_rate", 0.5)
                    
                    # Weight score by success rate but keep it above a minimum
                    agent_score = agent_score * (0.3 + 0.7 * success_rate)
                
                agent_scores[agent_id] = agent_score
            
            # Find best agent
            if agent_scores:
                best_agent_id = max(agent_scores, key=agent_scores.get)
                best_score = agent_scores[best_agent_id]
                
                if best_score > 0:
                    return self.orchestrator_agents[best_agent_id], best_score
            
            return None, 0.0
            
        except Exception as e:
            logger.error(f"Error identifying best agent: {str(e)}")
            return None, 0.0

    def _extract_text_from_request(self, request_data: Any) -> str:
        """
        Extract text content from various request data formats.
        
        Args:
            request_data: The request data to extract text from
            
        Returns:
            Extracted text content
        """
        if isinstance(request_data, str):
            return request_data
            
        if isinstance(request_data, dict):
            # Try common fields for text content
            for field in ["text", "query", "message", "request", "content", "prompt"]:
                if field in request_data and isinstance(request_data[field], str):
                    return request_data[field]
            
            # If there's no specific text field, try to extract all string values
            text_values = []
            for key, value in request_data.items():
                if isinstance(value, str) and len(value) > 5:  # Only meaningful text
                    text_values.append(value)
            
            if text_values:
                return " ".join(text_values)
        
        # For list-like objects, try to join string items
        if hasattr(request_data, "__iter__") and not isinstance(request_data, dict):
            text_values = []
            for item in request_data:
                if isinstance(item, str):
                    text_values.append(item)
                elif isinstance(item, dict) and "text" in item:
                    text_values.append(item["text"])
            
            if text_values:
                return " ".join(text_values)
        
        # Fall back to string representation if nothing else works
        return str(request_data)
    
    def _check_database_cache(self, request_text: str, request_hash: str) -> Optional[Dict]:
        """
        Check if we have a cached response for a similar request.
        
        Args:
            request_text: The text of the request
            request_hash: The hash of the request
            
        Returns:
            Cached response if found, None otherwise
        """
        if not self.db:
            return None
            
        try:
            # First try exact hash match
            cursor = self.execute_query(
                "SELECT request_text, agent_id, response, success, confidence FROM orchestrator_request_mapping WHERE request_hash = ?",
                (request_hash,)
            )
            
            row = cursor.fetchone()
            if row:
                return {
                    "request_text": row[0],
                    "agent_id": row[1],
                    "response": row[2],
                    "success": bool(row[3]),
                    "confidence": row[4]
                }
            
            # If no exact match, try finding a similar request
            return self._find_similar_request_in_db(request_text)
            
        except Exception as e:
            logger.error(f"Error checking cache: {str(e)}")
            return None
    
    def _extract_capabilities_from_text(self, text: str) -> List[str]:
        """
        Extract capability keywords from text.
        
        Args:
            text: Input text
            
        Returns:
            List of capability keywords
        """
        # Simple approach: use intent keywords
        return self.extract_intent_keywords(text)
    
    def _find_agent_by_capabilities(self, capabilities: List[str]) -> Tuple[Optional[Dict], float]:
        """
        Find the best agent for a set of capabilities.
        
        Args:
            capabilities: List of required capabilities
            
        Returns:
            Tuple of (agent_info, confidence)
        """
        if not capabilities or not self.orchestrator_agents:
            return None, 0.0
        
        best_score = 0.0
        best_agent = None
        
        # For each agent, calculate how well it matches the requested capabilities
        for agent_id, agent_info in self.orchestrator_agents.items():
            # Get agent capabilities
            agent_capabilities = self.agent_capabilities.get(agent_id, [])
            if not agent_capabilities:
                continue
            
            # Calculate capability matching score
            agent_score = 0.0
            matches = 0
            
            for extracted_cap in capabilities:
                cap_score = 0.0
                for agent_cap in agent_capabilities:
                    # Calculate similarity between extracted and agent capability
                    sim_score = self._calculate_text_similarity(extracted_cap, agent_cap)
                    cap_score = max(cap_score, sim_score)
                
                if cap_score > 0.6:  # Consider it a match if similarity is high enough
                    matches += 1
                
                agent_score += cap_score
            
            # Normalize by number of capabilities
            if capabilities:
                agent_score /= len(capabilities)
            
            # Bonus for matching multiple capabilities
            if matches > 1:
                agent_score *= (1.0 + (matches / len(capabilities)))
            
            # Factor in past performance if available
            if agent_id in self.agent_performance:
                perf = self.agent_performance[agent_id]
                success_rate = perf.get("success_rate", 0.5)
                
                # Weight by success rate
                agent_score = agent_score * (0.5 + 0.5 * success_rate)
            
            # Update best match
            if agent_score > best_score:
                best_score = agent_score
                best_agent = agent_info
        
        return best_agent, best_score
    
    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate similarity between two texts.
        
        Uses embedding similarity if available, else falls back to token overlap.
        
        Args:
            text1: First text
            text2: Second text
            
        Returns:
            Similarity score between 0.0 and 1.0
        """
        if not text1 or not text2:
            return 0.0
        
        # Try using embeddings if available
        embedding1 = self.compute_text_embedding(text1)
        embedding2 = self.compute_text_embedding(text2)
        
        if embedding1 is not None and embedding2 is not None:
            # Use embedding similarity
            return self.compute_embedding_similarity(embedding1, embedding2)
        
        # Fall back to token overlap
        tokens1 = set(self.tokenize_text(text1))
        tokens2 = set(self.tokenize_text(text2))
        
        if not tokens1 or not tokens2:
            return 0.0
        
        # Calculate Jaccard similarity
        intersection = tokens1.intersection(tokens2)
        union = tokens1.union(tokens2)
        
        return len(intersection) / len(union) if union else 0.0
    


    def record_request_mapping(self, request_text, response, agent_id, success=True):
        """
        Record a request-to-agent mapping in the database.
        
        Args:
            request_text: Original request text
            response: Response data (JSON string or dict)
            agent_id: ID of the agent that handled the request
            success: Whether the mapping was successful
        """
        if not self.db:
            return
            
        try:
            # Convert response to string if it's a dict
            if isinstance(response, dict):
                response = json.dumps(response)
                
            # Create a hash of the request text for faster lookups
            request_hash = hashlib.md5(request_text.encode()).hexdigest()
            
            # Compute request embedding if possible
            embedding_vector = None
            embedding = self.compute_text_embedding(request_text)
            if embedding is not None:
                embedding_vector = embedding.tobytes()
                
            # Calculate timestamp
            timestamp = time.time()
            
            # Insert the mapping
            self.execute_query(
                """
                INSERT INTO orchestrator_request_mapping 
                (request_text, request_hash, agent_id, response, success, timestamp, embedding_vector, workspace_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    request_text, 
                    request_hash,
                    agent_id,
                    response,
                    1 if success else 0,
                    timestamp,
                    embedding_vector,
                    self.workspace_id
                )
            )
            
            # Commit the changes
            self.commit()
            
            # Update agent performance statistics
            if agent_id:
                cursor = self.execute_query(
                    "SELECT * FROM orchestrator_agent_performance WHERE agent_id = ?",
                    (agent_id,)
                )
                
                row = cursor.fetchone()
                if row:
                    # Update existing entry
                    requests = row[1] + 1
                    successes = row[2] + (1 if success else 0)
                    failures = row[3] + (0 if success else 1)
                    
                    success_rate = successes / requests if requests > 0 else 0.0
                    
                    self.execute_query(
                        """
                        UPDATE orchestrator_agent_performance
                        SET requests = ?, successes = ?, failures = ?, success_rate = ?, last_updated = ?
                        WHERE agent_id = ?
                        """,
                        (requests, successes, failures, success_rate, timestamp, agent_id)
                    )
                else:
                    # Create new entry
                    self.execute_query(
                        """
                        INSERT INTO orchestrator_agent_performance
                        (agent_id, requests, successes, failures, success_rate, workspace_id, last_updated)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            agent_id,
                            1,
                            1 if success else 0,
                            0 if success else 1,
                            1.0 if success else 0.0,
                            self.workspace_id,
                            timestamp
                        )
                    )
                
                # Commit again after updating performance
                self.commit()
                
            return True
            
        except Exception as e:
            logger.error(f"Error recording request mapping: {str(e)}")
            return False
    
    # Database methods
    
    def _ensure_tables_exist(self):
        """Ensure that all required database tables exist."""
        if not self.db:
            return
            
        try:
            # Create the request mapping table
            self.execute_query(ORCHESTRATOR_REQUEST_MAPPING_TABLE)
            
            # Create the agent performance table
            self.execute_query(ORCHESTRATOR_AGENT_PERFORMANCE_TABLE)
            
            # Create the capability mapping table
            self.execute_query(ORCHESTRATOR_CAPABILITY_MAPPING_TABLE)
            
            # Create indexes for better performance
            for index_query in ORCHESTRATOR_INDEXES:
                self.execute_query(index_query)
                
            # Create schema tables if needed
            self.execute_query("""
                CREATE TABLE IF NOT EXISTS orchestrator_schemas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    module_name TEXT NOT NULL,
                    function_name TEXT NOT NULL,
                    schema TEXT NOT NULL,
                    success_count INTEGER DEFAULT 0,
                    failure_count INTEGER DEFAULT 0,
                    success_rate REAL DEFAULT 0.0,
                    last_updated REAL,
                    UNIQUE(module_name, function_name)
                )
            """)
            
            self.execute_query("""
                CREATE INDEX IF NOT EXISTS idx_schemas_module ON orchestrator_schemas (module_name)
            """)
            
            self.execute_query("""
                CREATE INDEX IF NOT EXISTS idx_schemas_function ON orchestrator_schemas (function_name)
            """)
            
            self.execute_query("""
                CREATE INDEX IF NOT EXISTS idx_schemas_success_rate ON orchestrator_schemas (success_rate)
            """)
            
            # Commit changes
            self.commit()
            
        except Exception as e:
            logger.error(f"Error ensuring tables exist: {str(e)}")
    
    def load_agent_performance(self) -> Dict[str, Dict]:
        """
        Load agent performance metrics from database
        
        Returns:
            Dictionary of agent performance metrics
        """
        if not self.db:
            return {}
        
        try:
            # First query for current workspace
            query = """
            SELECT * FROM orchestrator_agent_performance
            WHERE workspace_id = ?
            """
            result = self.db.execute_query(query, (self.workspace_id,))
            rows = result.fetchall()
            
            performance = {}
            for row in rows:
                agent_id = row["agent_id"]
                performance[agent_id] = {
                    "requests": row["requests"],
                    "successes": row["successes"],
                    "failures": row["failures"],
                    "total_time": row["total_time"],
                    "avg_time": row["avg_time"],
                    "success_rate": row["success_rate"],
                    "workspace_id": row["workspace_id"]
                }
            
            # If no results for current workspace, get cross-workspace data
            if not performance:
                query = "SELECT * FROM orchestrator_agent_performance"
                result = self.db.execute_query(query)
                rows = result.fetchall()
                
                for row in rows:
                    agent_id = row["agent_id"]
                    if agent_id not in performance:  # Don't override workspace-specific data
                        performance[agent_id] = {
                            "requests": row["requests"],
                            "successes": row["successes"],
                            "failures": row["failures"],
                            "total_time": row["total_time"],
                            "avg_time": row["avg_time"],
                            "success_rate": row["success_rate"],
                            "workspace_id": row["workspace_id"]
                        }
            
            self.agent_performance = performance
            return performance
            
        except Exception as e:
            logger.error(f"Error loading agent performance: {str(e)}")
            return {}

    def store_agent_capabilities(self, agent_id: str, capabilities: List[str]) -> bool:
        """
        Store agent capabilities in the database with embeddings.
        
        Args:
            agent_id: ID of the agent
            capabilities: List of capability strings
            
        Returns:
            Whether storage was successful
        """
        if not self.db or not capabilities:
            return False
        
        try:
            with self.db.transaction():
                # First remove existing capabilities for this agent
                self.db.execute_query(
                    "DELETE FROM orchestrator_capability_mapping WHERE agent_id = ? AND workspace_id = ?",
                    (agent_id, self.workspace_id)
                )
                
                # Store each capability with its embedding
                for capability in capabilities:
                    # Compute embedding if model is available
                    embedding_vector = None
                    if self.embedding_model is not None:
                        embedding = self.compute_text_embedding(capability)
                        if embedding is not None:
                            embedding_vector = embedding.tobytes()
                    
                    # Insert capability
                    self.db.execute_query(
                        """
                        INSERT INTO orchestrator_capability_mapping
                        (agent_id, capability, embedding_vector, workspace_id, timestamp)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (
                            agent_id,
                            capability,
                            embedding_vector,
                            self.workspace_id,
                            time.time()
                        )
                    )
            
            return True
            
        except Exception as e:
            logger.error(f"Error storing agent capabilities: {str(e)}")
            return False

    
    

    def intelligence_enhanced_route_task(self, task_data, journey_id=None):
        """
        Enhanced task routing with intelligence capabilities.
        
        Args:
            task_data: The task data to route
            journey_id: Optional journey ID for tracking
            
        Returns:
            Routing result
        """
        if not journey_id:
            journey_id = f"journey_{int(time.time())}_{uuid.uuid4().hex[:8]}"
            
        logger.info(f"Intelligence enhanced routing for task: {task_data.get('task', '')[:50]}...")
        
        try:
            # Extract task text
            task_text = task_data.get('task', '')
            if not task_text and isinstance(task_data, str):
                task_text = task_data
                
            if not task_text:
                return {
                    "success": False,
                    "error": "No task text provided",
                    "journey_id": journey_id
                }
            
            # Analyze task complexity
            complexity_score = self._analyze_task_complexity(task_text)
            
            # Extract task requirements
            requirements = self._extract_task_requirements(task_text)
            
            # Determine task category
            category = self._determine_task_category(task_text)
            
            # For complex AI/ML tasks, try to determine if we should use a specialized agent
            if complexity_score > 0.7 and category in ["data_analysis", "visualization", "machine_learning"]:
                # Generate a schema for the appropriate agent type
                output_schema = self._generate_output_schema(category, task_text)
                
                # Create routing data
                routing_data = {
                    "success": True,
                    "selected_system": {
                        "handler": f"{category}_handler",
                        "action": "process_task",
                        "parameters": {
                            "task": task_text,
                            "schema": output_schema,
                            "journey_id": journey_id
                        }
                    },
                    "journey_id": journey_id,
                    "task_data": task_data,
                    "task_analysis": {
                        "complexity": complexity_score,
                        "category": category,
                        "requirements": requirements
                    }
                }
                
                logger.info(f"Routing to specialized agent for {category} task (complexity: {complexity_score:.2f})")
                return routing_data
                
            # For regular tasks, use the standard agent selection
            agent_info, confidence = self.identify_best_agent_for_request(task_text)
            
            if agent_info and confidence >= 0.7:  # Lower threshold for routing
                agent_id = agent_info.get("id")
                handler_match = re.search(r'(\w+)_handler', agent_id, re.IGNORECASE)
                
                if handler_match:
                    handler_name = handler_match.group(1).lower() + "_handler"
                    
                    # Create routing data
                    routing_data = {
                        "success": True,
                        "selected_system": {
                            "handler": handler_name,
                            "action": "process_request",
                            "parameters": {
                                "request": task_text,
                                "journey_id": journey_id
                            }
                        },
                        "journey_id": journey_id,
                        "confidence": confidence,
                        "task_data": task_data,
                        "task_analysis": {
                            "complexity": complexity_score,
                            "category": category,
                            "requirements": requirements
                        }
                    }
                    
                    logger.info(f"Routing to {handler_name} (confidence: {confidence:.2f})")
                    return routing_data
            
            # If no agent found or low confidence, let the orchestrator decide
            logger.info("No suitable agent found, letting orchestrator decide")
            return {
                "success": False,
                "error": "No suitable agent found",
                "journey_id": journey_id,
                "task_analysis": {
                    "complexity": complexity_score,
                    "category": category,
                    "requirements": requirements
                }
            }
            
        except Exception as e:
            logger.error(f"Error in intelligence enhanced routing: {str(e)}")
            logger.error(traceback.format_exc())
            
            return {
                "success": False,
                "error": f"Error in intelligence enhanced routing: {str(e)}",
                "journey_id": journey_id
            }
    
    def _analyze_task_complexity(self, task_text):
        """
        Analyze task complexity on a scale from 0 to 1.
        
        Args:
            task_text: The task text
            
        Returns:
            Complexity score (0.0 to 1.0)
        """
        if not task_text:
            return 0.0
            
        # Simple length-based complexity
        if len(task_text) < 50:
            return 0.3
        elif len(task_text) > 500:
            return 0.8
            
        # Count technical terms
        technical_terms = [
            "analyze", "data", "train", "model", "visualize", "classification",
            "regression", "clustering", "algorithm", "optimization", "parameter"
        ]
        
        tech_term_count = sum(1 for term in technical_terms if term in task_text.lower())
        
        # Count question marks and requirements
        question_count = task_text.count('?')
        
        # Check for complex logic indicators
        complex_indicators = [
            "if", "else", "when", "then", "but only if", "except when",
            "for each", "all of", "every", "step by step"
        ]
        
        complexity_indicator_count = sum(1 for term in complex_indicators if term in task_text.lower())
        
        # Calculate complexity based on factors
        complexity = 0.4  # Base complexity
        complexity += min(0.3, tech_term_count * 0.05)  # Technical complexity
        complexity += min(0.2, question_count * 0.05)   # Question complexity
        complexity += min(0.2, complexity_indicator_count * 0.04)  # Logical complexity
        
        # Adjust for known task types
        if "create a visualization" in task_text.lower():
            complexity = max(complexity, 0.6)
        if "train a model" in task_text.lower():
            complexity = max(complexity, 0.8)
        if "analyze the data" in task_text.lower():
            complexity = max(complexity, 0.7)
            
        return min(1.0, complexity)  # Cap at 1.0
    
    def _extract_task_requirements(self, task_text):
        """
        Extract key requirements from the task text.
        
        Args:
            task_text: The task text
            
        Returns:
            List of requirements
        """
        requirements = []
        
        # Simple keyword-based extraction
        if "visualization" in task_text.lower() or "visualize" in task_text.lower() or "chart" in task_text.lower() or "plot" in task_text.lower():
            requirements.append("visualization")
            
        if "data" in task_text.lower() or "dataset" in task_text.lower() or "csv" in task_text.lower():
            requirements.append("data_handling")
            
        if "model" in task_text.lower() or "train" in task_text.lower() or "predict" in task_text.lower():
            requirements.append("machine_learning")
            
        if "analyze" in task_text.lower() or "analysis" in task_text.lower() or "insights" in task_text.lower():
            requirements.append("analysis")
            
        # Add general requirements based on complexity
        complexity = self._analyze_task_complexity(task_text)
        if complexity > 0.7:
            requirements.append("complex_processing")
            
        return requirements
    
    def _determine_task_category(self, task_text):
        """
        Determine the main category of the task.
        
        Args:
            task_text: The task text
            
        Returns:
            Task category string
        """
        text = task_text.lower()
        
        # Check for data visualization tasks
        viz_terms = ["visualization", "visualize", "chart", "plot", "graph", "dashboard"]
        if any(term in text for term in viz_terms):
            return "visualization"
            
        # Check for data analysis tasks
        analysis_terms = ["analyze", "analysis", "insights", "patterns", "trends", "statistics"]
        if any(term in text for term in analysis_terms):
            return "data_analysis"
            
        # Check for machine learning tasks
        ml_terms = ["model", "train", "predict", "machine learning", "classification", "regression"]
        if any(term in text for term in ml_terms):
            return "machine_learning"
            
        # Check for information retrieval tasks
        info_terms = ["find", "search", "look up", "retrieve", "get information", "tell me about"]
        if any(term in text for term in info_terms):
            return "information_retrieval"
            
        # Check for code generation tasks
        code_terms = ["code", "function", "script", "program", "development", "implement"]
        if any(term in text for term in code_terms):
            return "code_generation"
            
        # Default to general task
        return "general_task"
    
    def _generate_output_schema(self, agent_type, task_text):
        """
        Generate an output schema for a specific agent type.
        
        Args:
            agent_type: Type of agent (visualization, data_analysis, etc.)
            task_text: The task text
            
        Returns:
            JSON schema for the agent
        """
        if agent_type == "visualization":
            # Schema for visualization agent
            return {
                "type": "object",
                "properties": {
                    "visualization_type": {
                        "type": "string",
                        "description": "Type of visualization to create",
                        "enum": ["bar_chart", "line_chart", "scatter_plot", "pie_chart", "heatmap", "histogram"]
                    },
                    "data_source": {
                        "type": "string",
                        "description": "Source of the data for visualization"
                    },
                    "title": {
                        "type": "string",
                        "description": "Title for the visualization"
                    },
                    "description": {
                        "type": "string",
                        "description": "Description of the visualization"
                    },
                    "x_axis": {
                        "type": "string",
                        "description": "X-axis field name"
                    },
                    "y_axis": {
                        "type": "string",
                        "description": "Y-axis field name"
                    },
                    "additional_parameters": {
                        "type": "object",
                        "description": "Additional parameters for the visualization"
                    }
                },
                "required": ["visualization_type", "data_source"]
            }
        elif agent_type == "data_analysis":
            # Schema for data analysis agent
            return {
                "type": "object",
                "properties": {
                    "analysis_type": {
                        "type": "string",
                        "description": "Type of analysis to perform",
                        "enum": ["descriptive", "exploratory", "statistical", "predictive", "categorical"]
                    },
                    "data_source": {
                        "type": "string",
                        "description": "Source of the data for analysis"
                    },
                    "target_fields": {
                        "type": "array",
                        "description": "Fields to analyze",
                        "items": {
                            "type": "string"
                        }
                    },
                    "methods": {
                        "type": "array",
                        "description": "Analysis methods to use",
                        "items": {
                            "type": "string"
                        }
                    },
                    "output_format": {
                        "type": "string",
                        "description": "Format for analysis output",
                        "enum": ["text", "json", "table", "visualization"]
                    }
                },
                "required": ["analysis_type", "data_source"]
            }
        elif agent_type == "machine_learning":
            # Schema for machine learning agent
            return {
                "type": "object",
                "properties": {
                    "model_type": {
                        "type": "string",
                        "description": "Type of machine learning model",
                        "enum": ["classification", "regression", "clustering", "nlp", "vision", "time_series"]
                    },
                    "data_source": {
                        "type": "string",
                        "description": "Source of the data for training/prediction"
                    },
                    "target_field": {
                        "type": "string",
                        "description": "Target field for supervised learning"
                    },
                    "feature_fields": {
                        "type": "array",
                        "description": "Feature fields for model",
                        "items": {
                            "type": "string"
                        }
                    },
                    "model_parameters": {
                        "type": "object",
                        "description": "Parameters for the model"
                    },
                    "evaluation_metrics": {
                        "type": "array",
                        "description": "Metrics to evaluate the model",
                        "items": {
                            "type": "string"
                        }
                    }
                },
                "required": ["model_type", "data_source"]
            }
        else:
            # Generic schema for other agent types
            return {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "description": "Action to perform"
                    },
                    "parameters": {
                        "type": "object",
                        "description": "Parameters for the action"
                    },
                    "output_format": {
                        "type": "string",
                        "description": "Format for the output"
                    }
                },
                "required": ["action"]
            }

    def test(self, test_file_path=None):
        """
        Run tests on the orchestrator intelligence system.
        
        Args:
            test_file_path (str, optional): Path to a specific file to test for schema validation.
                If not provided, a general test of the system will be performed.
                
        Returns:
            dict: Test results with detailed information about the test outcomes
        """
        start_time = time.time()
        
        print("Orchestrator Intelligence: Running tests...")
        test_results = {
            "success": True,
            "timestamp": time.time(),
            "errors": [],
            "database_connected": False,
            "embedding_model_available": False,
            "agents_discovered": 0,
            "schemas": {
                "total_schemas": 0,
                "valid_schemas": 0,
                "executable_schemas": 0,
                "has_applescript": 0,
                "has_subprocess": 0,
                "has_shell_commands": 0
            },
            "tests_run": [],
        }
        
        # Test 1: Check database connection
        try:
            self._ensure_tables_exist()
            test_results["database_connected"] = True
            test_results["tests_run"].append("database_connection")
            print("✓ Database connection successful")
        except Exception as e:
            test_results["success"] = False
            test_results["errors"].append(f"Database test error: {str(e)}")
            print(f"✗ Database test error: {str(e)}")
        
        # Test 2: Check embedding model
        try:
            test_embedding = self.compute_text_embedding("Test embedding computation")
            test_results["embedding_model_available"] = True
            test_results["tests_run"].append("embedding_model")
            print("✓ Embedding model test successful")
        except Exception as e:
            test_results["success"] = False
            test_results["errors"].append(f"Embedding model test error: {str(e)}")
            print(f"✗ Embedding model test error: {str(e)}")
        
        # Test 3: Discover orchestrator agents
        try:
            agents = self.discover_orchestrator_agents()
            test_results["agents_discovered"] = len(agents)
            test_results["tests_run"].append("agent_discovery")
            print(f"✓ Discovered {len(agents)} orchestrator agents")
        except Exception as e:
            test_results["success"] = False
            test_results["errors"].append(f"Agent discovery test error: {str(e)}")
            print(f"✗ Agent discovery test error: {str(e)}")
        
        # Test 4: Test schema validation with a specific file
        if test_file_path:
            try:
                print(f"\nTesting schema validation on: {test_file_path}")
                test_results["tests_run"].append("schema_validation")
                
                # Extract executable code
                executable_code = self.extract_executable_code(test_file_path)
                test_results["schemas"]["has_applescript"] = len(executable_code.get("applescript", []))
                test_results["schemas"]["has_subprocess"] = len(executable_code.get("subprocess", []))
                test_results["schemas"]["has_shell_commands"] = len(executable_code.get("shell_commands", []))
                
                print(f"  AppleScript snippets: {test_results['schemas']['has_applescript']}")
                print(f"  Subprocess calls: {test_results['schemas']['has_subprocess']}")
                print(f"  Shell commands: {test_results['schemas']['has_shell_commands']}")
                
                # Parse the file using AST
                import ast
                
                try:
                    # Read file content
                    with open(test_file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                    # Parse the file
                    tree = ast.parse(content)
                    
                    # Extract functions
                    functions = []
                    for node in ast.walk(tree):
                        if isinstance(node, ast.FunctionDef):
                            functions.append(node)
                    
                    print(f"\n  Found {len(functions)} functions in {test_file_path}")
                    
                    # Create schemas for each function
                    for function in functions:
                        try:
                            # Create schema
                            schema = self._create_function_schema(function, test_file_path)
                            
                            test_results["schemas"]["total_schemas"] += 1
                            
                            # Validate schema format
                            valid, validation_msg = self.validate_schema_format(schema)
                            if valid:
                                test_results["schemas"]["valid_schemas"] += 1
                                
                                # Test executability
                                function_name = function.name
                                rel_path = os.path.relpath(test_file_path, self.workspace_root) if self.workspace_root else test_file_path
                                module_name = os.path.splitext(rel_path)[0].replace('/', '.').replace('\\', '.')
                                
                                executable, exec_msg = self.validate_schema_executability(module_name, function_name, schema)
                                if executable:
                                    test_results["schemas"]["executable_schemas"] += 1
                                    print(f"  ✓ {function_name}: Valid & executable schema")
                                else:
                                    print(f"  ⚠ {function_name}: Valid schema but not executable: {exec_msg}")
                            else:
                                print(f"  ✗ {function.name}: Invalid schema: {validation_msg}")
                        except Exception as e:
                            print(f"  ✗ {function.name}: Error creating schema: {str(e)}")
                            
                except SyntaxError as e:
                    test_results["success"] = False
                    test_results["errors"].append(f"Syntax error in {test_file_path}: {str(e)}")
                    print(f"  ✗ Syntax error in {test_file_path}: {str(e)}")
                
            except Exception as e:
                test_results["success"] = False
                test_results["errors"].append(f"Schema validation test error: {str(e)}")
                print(f"✗ Schema validation test error: {str(e)}")
        
        # Test 5: Test JSON schema export
        try:
            # Export schemas to file
            test_export_path = os.path.join(self.cache_dir, "test_schemas.json") if self.cache_dir else "test_schemas.json"
            export_success = self.export_schemas_to_file(export_path=test_export_path)
            
            test_results["tests_run"].append("schema_export")
            if export_success:
                print(f"✓ Successfully exported schemas to {test_export_path}")
            else:
                print("⚠ Schema export completed but with warnings")
        except Exception as e:
            test_results["success"] = False
            test_results["errors"].append(f"Schema export test error: {str(e)}")
            print(f"✗ Schema export test error: {str(e)}")
        
        # Calculate test duration
        duration = time.time() - start_time
        test_results["duration_seconds"] = duration
        print(f"\nTests completed in {duration:.2f} seconds")
        
        return test_results
        
    def scan_codebase_for_agent_imports(self, root_dir=None):
        """
        Scan the codebase for imports of agent-related modules.
        
        This helps discover which files are using agent components.
        
        Args:
            root_dir: Root directory to start scanning from, defaults to workspace_root
            
        Returns:
            Dictionary of files and their agent imports
        """
        if not root_dir:
            root_dir = self.workspace_root
            
        if not root_dir:
            logger.warning("No root directory specified for scanning")
            return {}
            
        results = {}
        agent_modules = [
            "Jarvis_Agent_SDK.jarvis_orchestrator",
            "Jarvis_Agent_SDK.agent_builder",
            "Jarvis_Agent_SDK.orchestrator_intelligence",
            "Jarvis_Agent_SDK.structured_outputs_multi",
            "Jarvis_Agent_SDK.workspace_sharing",
            "Jarvis_Agent_SDK.board_room",
            "BoardRoom.board_room",
            "Handler."
        ]
        
        # Walk through directory
        for dirpath, dirnames, filenames in os.walk(root_dir):
            # Skip virtual environments and hidden directories
            if any(part.startswith('.') for part in dirpath.split(os.sep)) or \
               "venv" in dirpath or "env" in dirpath or "__pycache__" in dirpath:
                continue
                
            # Check Python files
            for filename in filenames:
                if filename.endswith('.py'):
                    filepath = os.path.join(dirpath, filename)
                    
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            content = f.read()
                            
                        # Look for imports
                        file_imports = []
                        lines = content.split('\n')
                        for line in lines:
                            # Check for import statements
                            if any(module in line for module in agent_modules) and \
                               ("import " in line or "from " in line):
                                file_imports.append(line.strip())
                                
                        if file_imports:
                            rel_path = os.path.relpath(filepath, root_dir)
                            results[rel_path] = file_imports
                            logger.debug(f"Found agent imports in {filepath}")
                            
                    except Exception as e:
                        logger.debug(f"Error scanning file {filepath}: {str(e)}")
        
        return results
        
    def _create_function_schema(self, function_info, file_path=None):
        """
        Create a JSON schema for a function based on its AST node or signature.
        
        Args:
            function_info: Either an AST FunctionDef node or a dictionary with function details
            file_path: Optional path to the source file for context
            
        Returns:
            JSON schema for the function
        """
        import ast
        import inspect
        
        result = {
            "type": "object",
            "properties": {},
            "required": []
        }
        
        function_name = None
        docstring = None
        parameters = []
        
        # Extract information based on what kind of input we have
        if isinstance(function_info, ast.FunctionDef):
            # From AST node
            function_name = function_info.name
            
            # Extract docstring
            if (len(function_info.body) > 0 and 
                isinstance(function_info.body[0], ast.Expr) and 
                isinstance(function_info.body[0].value, ast.Str)):
                docstring = function_info.body[0].value.s
                
            # Extract parameters
            for arg in function_info.args.args:
                if arg.arg == 'self' or arg.arg == 'cls':
                    continue
                    
                param = {"name": arg.arg}
                
                # Extract type annotation if available
                if hasattr(arg, 'annotation') and arg.annotation:
                    param["type"] = self._extract_type_annotation(arg.annotation)
                    
                parameters.append(param)
                
            # Extract default values
            defaults = function_info.args.defaults
            if defaults:
                for i, default in enumerate(defaults):
                    idx = len(parameters) - len(defaults) + i
                    if idx >= 0 and idx < len(parameters):
                        if isinstance(default, ast.Str):
                            parameters[idx]["default"] = default.s
                        elif isinstance(default, ast.Num):
                            parameters[idx]["default"] = default.n
                        elif isinstance(default, ast.NameConstant):
                            parameters[idx]["default"] = default.value
                        elif isinstance(default, ast.List):
                            parameters[idx]["default"] = []
                        elif isinstance(default, ast.Dict):
                            parameters[idx]["default"] = {}
                
        elif isinstance(function_info, dict):
            # From dictionary
            function_name = function_info.get("name")
            docstring = function_info.get("docstring")
            parameters = function_info.get("parameters", [])
        elif inspect.isfunction(function_info):
            # From actual function object
            function_name = function_info.__name__
            docstring = function_info.__doc__
            sig = inspect.signature(function_info)
            
            for name, param in sig.parameters.items():
                if name in ['self', 'cls']:
                    continue
                    
                param_info = {"name": name}
                
                # Extract type hint
                if param.annotation != inspect.Parameter.empty:
                    param_info["type"] = str(param.annotation).replace('<class ', '').replace('>', '').replace("'", "")
                    
                # Extract default
                if param.default != inspect.Parameter.empty:
                    param_info["default"] = param.default
                    
                parameters.append(param_info)
        else:
            raise ValueError(f"Unsupported function_info type: {type(function_info)}")
            
        if not function_name:
            raise ValueError("Could not determine function name")
            
        # Set schema title and description
        result["title"] = function_name
        
        # Extract description from docstring
        if docstring:
            result["description"] = self._extract_description_from_docstring(docstring)
            param_descriptions = self._extract_param_descriptions_from_docstring(docstring)
        else:
            result["description"] = f"Function {function_name}"
            param_descriptions = {}
            
        # Add parameters to schema
        for param in parameters:
            name = param.get("name")
            if not name:
                continue
                
            # Create property for this parameter
            param_schema = {}
            
            # Add description from docstring if available
            if name in param_descriptions:
                param_schema["description"] = param_descriptions[name]
            else:
                param_schema["description"] = f"Parameter {name}"
                
            # Set type based on annotation or default value
            param_type = param.get("type")
            if param_type:
                if "str" in param_type:
                    param_schema["type"] = "string"
                elif "int" in param_type:
                    param_schema["type"] = "integer"
                elif "float" in param_type:
                    param_schema["type"] = "number"
                elif "bool" in param_type:
                    param_schema["type"] = "boolean"
                elif "list" in param_type or "List" in param_type:
                    param_schema["type"] = "array"
                    param_schema["items"] = {"type": "string"}
                elif "dict" in param_type or "Dict" in param_type:
                    param_schema["type"] = "object"
                else:
                    param_schema["type"] = "string"
            else:
                # Infer type from default value
                default = param.get("default")
                if default is not None:
                    if isinstance(default, str):
                        param_schema["type"] = "string"
                    elif isinstance(default, int):
                        param_schema["type"] = "integer"
                    elif isinstance(default, float):
                        param_schema["type"] = "number"
                    elif isinstance(default, bool):
                        param_schema["type"] = "boolean"
                    elif isinstance(default, list):
                        param_schema["type"] = "array"
                        param_schema["items"] = {"type": "string"}
                    elif isinstance(default, dict):
                        param_schema["type"] = "object"
                    else:
                        param_schema["type"] = "string"
                else:
                    # Default to string if no type information available
                    param_schema["type"] = "string"
            
            # Add to properties
            result["properties"][name] = param_schema
            
            # Add to required parameters if no default value
            if "default" not in param:
                result["required"].append(name)
                
        # Add file path as metadata if provided
        if file_path:
            result["meta"] = {"file_path": file_path}
            
        return result

# Singleton instance
_intelligence_instance = None

def get_orchestrator_intelligence(cache_dir=None, trevor_core_instance=None, 
                                confidence_threshold=0.85, workspace_id=None):
    """Get or create the singleton orchestrator intelligence instance"""
    global _intelligence_instance
    
    if _intelligence_instance is None:
        _intelligence_instance = OrchestratorIntelligence(
            cache_dir=cache_dir,
            trevor_core_instance=trevor_core_instance,
            confidence_threshold=confidence_threshold,
            workspace_id=workspace_id
        )
    
    return _intelligence_instance

def init_orchestrator_intelligence(
    cache_dir=None, 
    trevor_core_instance=None, 
    confidence_threshold=0.85, 
    workspace_id=None,
    workspace_root=None,
    auto_discover=True,
    auto_connect_handlers=True,
    specific_handlers=None,
    integrate_with_orchestrator=True,
    auto_export_schemas=True,
    auto_update_schemas=True,
    schema_update_interval=3600,
    init_trevor_bridge=True  # New parameter to initialize Trevor bridge
):
    """Initialize the orchestrator intelligence module
    
    This function initializes the orchestrator intelligence module with the given parameters,
    discovers agents and handlers, and integrates with various components of the Jarvis system.
    
    Args:
        cache_dir: Directory for caching embedding vectors and database
        trevor_core_instance: Optional TrevorCore instance
        confidence_threshold: Confidence threshold for matches (default: 0.85)
        workspace_id: Optional workspace ID for integration with the workspace system
        workspace_root: Root directory of the workspace for file-based agent discovery
        auto_discover: Whether to automatically discover agents in the system
        auto_connect_handlers: Whether to automatically connect to handler agents
        specific_handlers: List of specific handlers to connect to (all if None)
        integrate_with_orchestrator: Whether to integrate with the jarvis_orchestrator
        auto_export_schemas: Whether to automatically export schemas to file
        auto_update_schemas: Whether to automatically update schema weights
        schema_update_interval: Interval in seconds for updating schema weights
        init_trevor_bridge: Whether to initialize the Trevor bridge
        
    Returns:
        OrchestratorIntelligence: The initialized intelligence module
    """
    global _intelligence_instance
    
    # If instance already exists, return it
    if _intelligence_instance is not None:
        return _intelligence_instance

    try:
        # Create an OrchestratorIntelligence instance
        intelligence = OrchestratorIntelligence(
            cache_dir=cache_dir, 
            trevor_core_instance=trevor_core_instance,
            confidence_threshold=confidence_threshold,
            workspace_id=workspace_id,
            workspace_root=workspace_root
        )
        
        # Auto-discover agents if enabled
        if auto_discover:
            try:
                logger.info("Auto-discovering orchestrator agents")
                agents = intelligence.discover_orchestrator_agents()
                logger.info(f"Discovered {len(agents)} orchestrator agents")
            except Exception as e:
                logger.error(f"Error auto-discovering agents: {str(e)}")
                logger.error(traceback.format_exc())
        
        # Auto-connect to handlers if enabled
        if auto_connect_handlers:
            handlers_to_connect = specific_handlers
            if not handlers_to_connect:
                # Try to get handlers from orchestrator, fall back to auto-discovery
                try:
                    from Jarvis_Agent_SDK.jarvis_orchestrator import load_handlers_async
                    import asyncio
                    handlers = asyncio.run(load_handlers_async())
                    handlers_to_connect = list(handlers.keys()) if handlers else []
                except Exception as e:
                    logger.error(f"Could not load handlers from orchestrator: {str(e)}")
                    handlers_to_connect = []
            
            if handlers_to_connect:
                logger.info(f"Auto-connecting to handlers: {handlers_to_connect}")
                for handler_name in handlers_to_connect:
                    try:
                        handler_info = intelligence.establish_direct_handler_connection(handler_name)
                        logger.info(f"Connected to handler {handler_name}: {handler_info.get('status', 'unknown')}")
                    except Exception as e:
                        logger.error(f"Error connecting to handler {handler_name}: {str(e)}")
        
        # Integrate with orchestrator if enabled
        if integrate_with_orchestrator:
            try:
                logger.info("Integrating with jarvis_orchestrator")
                result = intelligence.integrate_with_jarvis_orchestrator()
                logger.info(f"Integration with jarvis_orchestrator: {'success' if result else 'failed'}")
            except Exception as e:
                logger.error(f"Error integrating with jarvis_orchestrator: {str(e)}")
                logger.error(traceback.format_exc())
        
        # Initialize Trevor bridge if enabled
        if init_trevor_bridge:
            try:
                logger.info("Initializing Trevor bridge")
                import asyncio
                # CRITICAL FIX: Wait for Trevor initialization to complete before continuing
                # This ensures Trevor Core is properly registered before the system starts processing requests
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(intelligence.initialize_trevor_bridge())
                    logger.info("✅ Trevor bridge initialization completed successfully")
                finally:
                    loop.close()
            except Exception as e:
                logger.error(f"❌ Error initializing Trevor bridge: {str(e)}")
                logger.error(traceback.format_exc())
        
        # Export schemas if enabled
        if auto_export_schemas:
            try:
                logger.info("Exporting schemas to file")
                export_path = os.path.join(cache_dir, "schemas.json") if cache_dir else None
                intelligence.export_schemas_to_file(export_path=export_path)
            except Exception as e:
                logger.error(f"Error exporting schemas: {str(e)}")
        
        # Set up schema updating if enabled
        if auto_update_schemas:
            try:
                logger.info(f"Setting up schema weight updates every {schema_update_interval} seconds")
                intelligence.update_schema_weights_periodically(interval_seconds=schema_update_interval)
            except Exception as e:
                logger.error(f"Error setting up schema updates: {str(e)}")
        
        # Store the instance
        _intelligence_instance = intelligence
        
        return intelligence
        
    except Exception as e:
        logger.error(f"Error initializing orchestrator intelligence: {str(e)}")
        logger.error(traceback.format_exc())
        return None

# For testing
async def test_intelligence(test_integration=True):
    """
    Run a basic test of the intelligence system.
    
    Args:
        test_integration: Whether to test integration with Jarvis orchestrator
        
    Returns:
        Test result data
    """
    try:
        # Initialize with integration if requested
        intelligence = init_orchestrator_intelligence(
            integrate_with_orchestrator=test_integration
        )
        
        # Discover agents
        agents = intelligence.discover_orchestrator_agents()
        logger.info(f"Discovered {len(agents)} orchestrator agents")
        
        # Test request processing
        test_request = "Can you help me create a new swarm agent?"
        result = intelligence.process_request(test_request)
        logger.info(f"Test request processing result: {result}")
        
        # If testing integration and integration is available
        if test_integration and intelligence.integrated_with_orchestrator:
            # Get the integrated route_task function
            try:
                from Jarvis_Agent_SDK.jarvis_orchestrator import intelligence_enhanced_route_task
                
                # Test with the same request
                test_routing_result = intelligence_enhanced_route_task({
                    "task": test_request,
                    "type": "natural_language",
                    "test": True
                })
                
                logger.info(f"Test routing integration result: {test_routing_result}")
                
                # Return combined results
                return {
                    "process_request_result": result,
                    "routing_result": test_routing_result,
                    "agent_metrics": intelligence.get_agent_metrics(),
                    "integration_status": intelligence.integrated_with_orchestrator
                }
            except (ImportError, AttributeError) as e:
                logger.warning(f"Integration test failed: {str(e)}")
                
                # Return basic results
                return {
                    "process_request_result": result,
                    "agent_metrics": intelligence.get_agent_metrics(),
                    "integration_status": False,
                    "integration_error": str(e)
                }
        
        # Return basic results
        return {
            "process_request_result": result,
            "agent_metrics": intelligence.get_agent_metrics(),
            "integration_status": getattr(intelligence, "integrated_with_orchestrator", False)
        }
        
    except Exception as e:
        logger.error(f"Test intelligence error: {str(e)}")
        traceback.print_exc()
        return {"error": str(e)}

def test_intelligence(test_integration=True):
    """
    Test the orchestrator intelligence system with a sample request.
    
    Args:
        test_integration: Whether to test integration with the Jarvis orchestrator
        
    Returns:
        Dict with test results
    """
    try:
        # Initialize intelligence system
        intelligence = OrchestratorIntelligence()
        
        # Test agent discovery
        agents = intelligence.discover_orchestrator_agents()
        
        # Group agents by their source for better reporting
        grouped_agents = {}
        for agent_id, agent_info in agents.items():
            source = agent_info.get("source", "unknown")
            if source not in grouped_agents:
                grouped_agents[source] = []
            grouped_agents[source].append(agent_info)
            
        # Print detailed discovery report
        print("\n===== ORCHESTRATOR AGENT DISCOVERY REPORT =====")
        print(f"Total discovered agents: {len(agents)}")
        
        # Count agents with specific properties
        orchestrator_count = len([a for a in agents.values() if a.get("is_orchestrator", False)])
        bidirectional_count = len([a for a in agents.values() if a.get("bidirectional_communication", False)])
        
        print(f"Agents identified as orchestrators: {orchestrator_count}")
        print(f"Agents with bidirectional communication: {bidirectional_count}")
        
        # Print agents grouped by source
        for source, agent_list in grouped_agents.items():
            print(f"\n-- Source: {source} ({len(agent_list)} agents) --")
            
            for agent in agent_list:
                orchestrator_status = "✓" if agent.get("is_orchestrator", False) else "✗"
                bidirectional_status = "✓" if agent.get("bidirectional_communication", False) else "✗"
                system = agent.get("system_name", "Unknown")
                
                print(f"  • {agent['agent_name']} (System: {system})")
                print(f"    - Orchestrator: {orchestrator_status} | Bidirectional: {bidirectional_status}")
                
                # Print capabilities if any
                capabilities = agent.get("capabilities", [])
                if capabilities:
                    print(f"    - Capabilities ({len(capabilities)}):")
                    for capability in capabilities[:5]:  # Limit to 5 capabilities to avoid too much output
                        print(f"      ∘ {capability}")
                    if len(capabilities) > 5:
                        print(f"      ∘ ... and {len(capabilities) - 5} more")
        
        print("\n============================================")
        
        # If testing integration, integrate with the Jarvis orchestrator
        if test_integration:
            integration_success = intelligence.integrate_with_jarvis_orchestrator()
            if integration_success:
                logger.info("Successfully integrated with Jarvis orchestrator!")
            else:
                logger.warning("Failed to integrate with Jarvis orchestrator")
        
        # Test request processing
        test_request = "Can you help me create a new swarm agent?"
        result = intelligence.process_request(test_request)
        logger.info(f"Test request processing result: {result}")
        
        # Test results
        test_result = {
            "process_request_result": result,
            "agent_metrics": intelligence.agent_performance,
            "integration_status": intelligence.integrated_with_orchestrator,
            "discovered_agents": {
                "total": len(agents),
                "orchestrators": orchestrator_count,
                "bidirectional": bidirectional_count,
                "by_source": {source: len(agent_list) for source, agent_list in grouped_agents.items()}
            }
        }
        
        return test_result
    except Exception as e:
        logger.error(f"Error testing intelligence: {str(e)}")
        return {"error": str(e)}

if __name__ == "__main__":
    """Run tests when executed directly"""
    test_result = test_intelligence()
    print(f"Test results: {test_result}")

