import ast
import collections
from datetime import datetime
import hashlib
import inspect
import importlib.util
import json
import logging
import os
from pathlib import Path
import re
import sqlite3
import traceback
from typing import Dict, List, Set, Tuple, Any, Union
from collections import defaultdict
from urllib.parse import urlparse
import glob
import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
import itertools
import sys
import psutil
import signal
from contextlib import contextmanager

# Third-party imports
import spacy

# Custom imports
from Handler.database_utils import DatabaseConnection
from Handler.pattern_intent_mapper import PatternIntentMapper

# Import agent-related components for specialized agent integration
try:
    from Jarvis_Agent_SDK.jarvis_orchestrator import analyze_handler_capabilities
    from Handler.handler_agent_builder import AgentBuilder, AgentType, AgentSpecialization, AgentCapability, AgentTool
except ImportError:
    # Allow the handler to function even if agent components can't be imported
    print("Warning: Agent components not available - specialized agent features disabled")

# Import the AIPatternAnalyzer class from test_ai_execute.py

logging.basicConfig(
    filename='handler_analyzer_debug.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

"""Handler analyzer module for discovering and analyzing endpoints in handler files."""

# Database configuration
WORKSPACE_ROOT = os.getcwd()
HANDLER_DIR = os.path.join(WORKSPACE_ROOT, 'Handler')
HANDLER_DB_PATH = os.path.join(HANDLER_DIR, 'handler_analysis.db')

# Ensure Handler directory exists
if not os.path.exists(HANDLER_DIR):
    os.makedirs(HANDLER_DIR)

class EndpointDiscovery(DatabaseConnection):
    """Handles endpoint discovery and database operations."""
    
    def __init__(self, db_connection):
        """Initialize with database connection."""
        super().__init__(db_connection)
        
        # Initialize spaCy
        try:
            self.nlp = spacy.load('en_core_web_lg')
        except OSError:
            spacy.cli.download('en_core_web_lg')
            self.nlp = spacy.load('en_core_web_lg')
            
        # Initialize handlers with proper mappings
        self.handlers = {
            'handler_wolfram.py': 'wolfram',
            'handler_ghl_requests.py': 'ghl',
            'handler_calendar.py': 'calendar',
            'handler_email.py': 'email',
            'handler_<healthcare>_sdk2.py': '<healthcare>'
        }
        logging.info("Handlers initialized: %s", self.handlers)
        
        # Initialize missing attributes
        self.intents_by_category = {}
        self.loaded_patterns = {}
        self.loaded_intents = {}
        
        # Initialize pattern intent mapper with the database connection
        self.pattern_mapper = PatternIntentMapper(db_connection=self.conn)
        
        # Load intents and patterns
        logging.info("Connected to database successfully")
        logging.info("Starting to load docstring data from database")
        
        # Load intents from the database
        intent_dir = os.path.join(WORKSPACE_ROOT, 'Intents')
        if os.path.exists(intent_dir):
            total_intents, total_examples, total_actions = self.load_intents(intent_dir)
            logging.info(f"Found {total_intents} intent entries in database")
            logging.info(f"Successfully loaded {total_intents} docstring patterns and {total_intents} docstring intents")
        
        # Load patterns
        pattern_dir = os.path.join(WORKSPACE_ROOT, 'Patterns')
        if os.path.exists(pattern_dir):
            self.loaded_patterns = self.load_patterns(pattern_dir)
        
        # Retain unique handler logic
        self.handler_to_pattern_mapping = {
            'handler_wolfram.py': 'wolfram_patterns.json',
            'handler_ghl_requests.py': 'ghl_patterns.json',
            'handler_calendar.py': 'calendar_patterns.json',
            'handler_email.py': 'email_patterns.json',
            'handler_<healthcare>_sdk2.py': '<healthcare>_patterns.json'
        }
        logging.info("Endpoint discovery system initialized with custom handlers")

    def init_database(self):
        """Initialize the database schema."""
        cursor = self.conn.cursor()
        
        # Create handler_analysis table if it doesn't exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS handler_analysis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                handler_name TEXT NOT NULL,
                training_data TEXT,
                status TEXT DEFAULT 'active',
                weight REAL DEFAULT 0.9,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create handlers table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS handlers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                handler_name TEXT NOT NULL,
                handler_type TEXT NOT NULL,
                handler_category TEXT NOT NULL,
                file_path TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create handler_patterns table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS handler_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                handler_id INTEGER NOT NULL,
                pattern_type TEXT NOT NULL,
                pattern_text TEXT NOT NULL,
                pattern_category TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (handler_id) REFERENCES handlers(id)
            )
        ''')
        
        # Create pattern_mapping table for compatibility
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pattern_mapping (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                handler_id INTEGER NOT NULL,
                pattern_type TEXT NOT NULL,
                pattern_value TEXT NOT NULL,
                similarity_score REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (handler_id) REFERENCES handlers(id)
            )
        ''')
        
        # Create intents table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS intents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create examples table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS examples (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                intent_id INTEGER NOT NULL,
                text TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (intent_id) REFERENCES intents(id)
            )
        ''')
        
        # Create actions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                intent_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (intent_id) REFERENCES intents(id)
            )
        ''')
        
        # Create intent_mappings table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS intent_mappings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                intent_id INTEGER NOT NULL,
                pattern_id INTEGER NOT NULL,
                handler_id INTEGER NOT NULL,
                score REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (intent_id) REFERENCES intents(id),
                FOREIGN KEY (pattern_id) REFERENCES pattern_mapping(id),
                FOREIGN KEY (handler_id) REFERENCES handlers(id)
            )
        ''')
        
        self.conn.commit()
        
    def __del__(self):
        """Clean up database connection."""
        if hasattr(self, 'conn') and self.conn:
            try:
                self.conn.close()
            except Exception as e:
                logging.error(f"Error closing database connection: {str(e)}")
        
    def discover_endpoints(self, handler_path: str) -> Dict:
        try:
            with open(handler_path, 'r') as f:
                content = f.read()
                logging.info(f"Discovering endpoints: category={os.path.basename(handler_path).replace('handler_', '').replace('.py', '')}, content_length={len(content)}")
            
            # Extract the category from filename
            category = os.path.basename(handler_path).replace("handler_", "").replace(".py", "")
            
            result = None
            # Handle different handler types using substring matching
            if "<healthcare>" in category:
                result = self._discover_<healthcare>_endpoints(content)
            elif "ghl" in category:
                result = self._discover_ghl_endpoints(content)
            elif "calendar" in category:
                result = self._discover_calendar_endpoints(content)
            else:
                # Default endpoint discovery
                result = {
                    'rest_endpoints': self._discover_rest_endpoints(content),
                    'graphql_endpoints': self._discover_graphql_endpoints(content),
                    'dynamic_endpoints': self._discover_dynamic_endpoints(content),
                    'base_urls': self._discover_base_urls(content)
                }
            
            if result is None:
                result = {}
            return result
            
        except Exception as e:
            logging.error(f"Error discovering endpoints in {handler_path}: {e}")
            return {}
        
    def load_intents(self, intent_dir: str) -> Tuple[int, int, int]:
        """Load intents from JSON intent files using parallel processing and batch operations."""
        try:
            # Find all intent JSON files
            intent_files = glob.glob(os.path.join(intent_dir, "intents_*.json"))
            logging.info(f"Found {len(intent_files)} intent files")
            
            # Clear loaded intents
            self.loaded_intents = {}
            self.intents_by_category = {}
            
            # Process files in parallel
            with ThreadPoolExecutor(max_workers=4) as executor:
                file_results = list(executor.map(self.process_intent_file, intent_files))
            
            # Merge results
            all_intents = {}
            for file_intents in file_results:
                for intent_name, intent_data in file_intents.items():
                    if intent_name not in all_intents:
                        all_intents[intent_name] = intent_data
                    else:
                        # Merge with existing intent
                        all_intents[intent_name]['examples'].update(intent_data['examples'])
                        all_intents[intent_name]['actions'].extend(intent_data['actions'])
            
            # Prepare batch inserts
            intent_values = []
            example_values = []
            action_values = []
            
            # Build batch insert data
            cursor = self.conn.cursor()
            for intent_name, intent_data in all_intents.items():
                # Insert intent
                cursor.execute(
                    "INSERT INTO intents (name, category) VALUES (?, ?)",
                    (intent_name, intent_data['category'])
                )
                intent_id = cursor.lastrowid
                
                # Store in loaded_intents and intents_by_category
                category = intent_data['category']
                if category not in self.loaded_intents:
                    self.loaded_intents[category] = []
                if category not in self.intents_by_category:
                    self.intents_by_category[category] = []
                    
                intent_obj = {
                    'intent': intent_name,
                    'examples': list(intent_data['examples']),
                    'actions': intent_data['actions'],
                    'description': intent_data['description'],
                    'temporal_info': intent_data.get('temporal_info', {}),
                    'entities': intent_data.get('entities', {}),
                    'sub_intents': intent_data.get('sub_intents', [])
                }
                
                self.loaded_intents[category].append(intent_obj)
                self.intents_by_category[category].append(intent_obj)
                
                # Collect example values
                example_values.extend((intent_id, example) for example in intent_data['examples'])
                
                # Collect action values
                action_values.extend((intent_id, json.dumps(action)) for action in intent_data['actions'])
            
            # Batch insert examples and actions
            cursor.executemany(
                "INSERT INTO examples (intent_id, text) VALUES (?, ?)",
                example_values
            )
            cursor.executemany(
                "INSERT INTO actions (intent_id, name) VALUES (?, ?)",
                action_values
            )
            
            self.conn.commit()
            
            total_intents = len(all_intents)
            total_examples = len(example_values)
            total_actions = len(action_values)
            
            logging.info(f"Loaded {total_intents} intents, {total_examples} examples, and {total_actions} actions")
            logging.info(f"Loaded intents for categories: {list(self.loaded_intents.keys())}")
            return total_intents, total_examples, total_actions
            
        except Exception as e:
            logging.error(f"Error loading intents: {str(e)}")
            return 0, 0, 0
  
    def process_intent_file(self, file_path: str) -> dict:
        """Process a single intent file and return its intents."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                intent_data = json.load(f)
                
            # Extract category from filename
            category = os.path.basename(file_path).replace("intents_", "").replace(".json", "")
            logging.info(f"Processing intents from category: {category}")
            
            file_intents = {}
            
            if isinstance(intent_data, dict):
                # Dict format - process all intents at once
                for intent_name, intent_info in intent_data.items():
                    examples = set()
                    # Process all examples at once
                    for example in intent_info.get('examples', []):
                        # Handle both string and dict examples
                        if isinstance(example, dict):
                            examples.add(example.get('text', ''))
                        else:
                            examples.add(str(example))
                        
                    file_intents[intent_name] = {
                        'category': category,
                        'examples': examples,
                        'actions': intent_info.get('actions', []),
                        'description': intent_info.get('description', ''),
                        'temporal_info': intent_info.get('temporal_info', {}),
                        'entities': intent_info.get('entities', {}),
                        'sub_intents': intent_info.get('sub_intents', [])
                    }
            elif isinstance(intent_data, list):
                # List format - process all intents at once
                for intent in intent_data:
                    # Skip if not a dict or missing required fields
                    if not isinstance(intent, dict) or 'name' not in intent:
                        continue
                        
                    intent_name = intent["name"]
                    examples = set()
                    # Process all examples at once
                    for example in intent.get('examples', []):
                        # Handle both string and dict examples
                        if isinstance(example, dict):
                            examples.add(example.get('text', ''))
                        else:
                            examples.add(str(example))
                        
                    file_intents[intent_name] = {
                        'category': category,
                        'examples': examples,
                        'actions': intent.get('actions', []),
                        'description': intent.get('description', ''),
                        'temporal_info': intent.get('temporal_info', {}),
                        'entities': intent.get('entities', {}),
                        'sub_intents': intent.get('sub_intents', [])
                    }
                    
            return file_intents
        except Exception as e:
            logging.error(f"Error processing intent file {file_path}: {str(e)}")
            return {}

    def load_patterns(self, pattern_dir: str) -> Dict:
        """Load patterns from JSON pattern files."""
        patterns = {}
        for pattern_file in glob.glob(os.path.join(pattern_dir, "patterns_*.json")):
            with open(pattern_file, 'r') as f:
                pattern_data = json.load(f)
                pattern_name = os.path.basename(pattern_file).replace("patterns_", "").replace(".json", "")
                patterns[pattern_name] = pattern_data
        return patterns

    def _discover_<healthcare>_endpoints(self, content: str) -> Dict:
        return {"dummy_<healthcare>": "extracted"}

    def _discover_ghl_endpoints(self, content: str) -> Dict:
        return {"dummy_ghl": "extracted"}

    def _discover_calendar_endpoints(self, content: str) -> Dict:
        return {"dummy_calendar": "extracted"}

    def _discover_rest_endpoints(self, content: str) -> Dict:
        # Implementation of _discover_rest_endpoints method
        pass

    def _discover_graphql_endpoints(self, content: str) -> Dict:
        # Implementation of _discover_graphql_endpoints method
        pass

    def _discover_dynamic_endpoints(self, content: str) -> Dict:
        # Implementation of _discover_dynamic_endpoints method
        pass

    def _discover_base_urls(self, content: str) -> Dict:
        # Implementation of _discover_base_urls method
        pass

    def analyze_handler(self, handler_file):
        """Analyze a handler file to discover endpoints and patterns."""
        try:
            # Get absolute path but keep it relative to workspace root
            workspace_root = os.getcwd()
            handler_path = os.path.join(workspace_root, handler_file)
            
            if not os.path.exists(handler_path):
                logging.error(f"Handler file not found: {handler_path}")
                return None

            # Get the handler type from filename
            handler_type = os.path.basename(handler_file).replace("handler_", "").replace(".py", "")
            
            logging.info(f"\nAnalyzing handler {handler_file} as type {handler_type}")
            
            # Read the handler file content
            with open(handler_path, 'r') as f:
                content = f.read()
            
            # Discover endpoints based on handler type
            if handler_type == "<healthcare>":
                endpoints = self._discover_<healthcare>_endpoints(content)
            elif handler_type == "ghl":
                endpoints = self._discover_ghl_endpoints(content)
            elif handler_type == "calendar":
                endpoints = self._discover_calendar_endpoints(content)
            else:
                # Default endpoint discovery
                endpoints = {
                    'rest_endpoints': self._discover_rest_endpoints(content),
                    'graphql_endpoints': self._discover_graphql_endpoints(content),
                    'dynamic_endpoints': self._discover_dynamic_endpoints(content),
                    'base_urls': self._discover_base_urls(content)
                }
            
            # Extract patterns based on handler type
            if handler_type == "<healthcare>":
                patterns = self._extract_<healthcare>_patterns(content)
            elif handler_type == "ghl":
                patterns = self._extract_ghl_patterns(content)
            elif handler_type == "calendar":
                patterns = self._extract_calendar_patterns(content)
            else:
                patterns = self._extract_patterns(content)
            
            # Match patterns to intents
            intent_matches = []
            if patterns:
                intent_matches = self.pattern_mapper.map_patterns_to_intents(patterns, handler_type)
            
            logging.info(f"✓ Successfully analyzed {handler_type}")
            logging.info(f"  - Found {len(patterns)} patterns")
            if intent_matches:
                logging.info(f"  - Matched {len(intent_matches)} intents")
            
            return handler_type, patterns, intent_matches
            
        except Exception as e:
            logging.error(f"Error analyzing {handler_file}: {e}")
            logging.error(traceback.format_exc())  # Add stack trace
            return None

    def _extract_patterns(self, content: str) -> List[Dict]:
        """Extract basic patterns from handler content."""
        patterns = []
        try:
            # Parse the content into an AST
            tree = ast.parse(content)
            
            # Extract patterns from module docstring
            if ast.get_docstring(tree):
                docstring = ast.get_docstring(tree)
                # Extract patterns section from docstring
                if 'Patterns:' in docstring:
                    patterns_section = docstring.split('Patterns:')[1].split('\n')
                    for line in patterns_section:
                        if line.strip().startswith('-'):
                            pattern = line.strip('- ').strip('"\'')
                            if pattern:
                                patterns.append({
                                    'type': 'DOCSTRING_PATTERN',
                                    'pattern': pattern
                                })
            
            # Extract function definitions and their patterns
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # Get function parameters
                    params = []
                    for arg in node.args.args:
                        if arg.arg != 'self':  # Skip self parameter
                            params.append(arg.arg)
                    
                    # Add function pattern
                    patterns.append({
                        'type': 'FUNCTION',
                        'pattern': ' '.join(node.name.split('_')),
                        'function': node.name,
                        'params': params,
                        'is_async': isinstance(node, ast.AsyncFunctionDef)
                    })
                    
                    # Extract patterns from function docstring
                    if ast.get_docstring(node):
                        docstring = ast.get_docstring(node)
                        patterns.append({
                            'type': 'FUNCTION_DOCSTRING',
                            'pattern': docstring,
                            'function': node.name
                        })
            
            return patterns
            
        except Exception as e:
            logging.error(f"Error extracting patterns: {e}")
            return patterns

    def _extract_<healthcare>_patterns(self, content: str) -> List[Dict]:
        """Extract <healthcare-platform>-specific patterns."""
        patterns = []
        try:
            # Parse the content into an AST
            tree = ast.parse(content)
            
            # Extract GraphQL queries and mutations
            for node in ast.walk(tree):
                if isinstance(node, ast.Assign):
                    if isinstance(node.targets[0], ast.Name):
                        var_name = node.targets[0].id
                        if isinstance(node.value, ast.Str):
                            if var_name.endswith('_QUERY'):
                                patterns.append({
                                    'type': 'GRAPHQL_QUERY',
                                    'pattern': node.value.s
                                })
                            elif var_name.endswith('_MUTATION'):
                                patterns.append({
                                    'type': 'GRAPHQL_MUTATION',
                                    'pattern': node.value.s
                                })
            
            return patterns
            
        except Exception as e:
            logging.error(f"Error extracting <healthcare-platform> patterns: {e}")
            return patterns

    def _extract_ghl_patterns(self, content: str) -> List[Dict]:
        """Extract GHL-specific patterns."""
        patterns = []
        try:
            # Parse the content into an AST
            tree = ast.parse(content)
            
            # Extract REST endpoints and API calls
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Attribute):
                        if node.func.attr in ['get', 'post', 'put', 'delete']:
                            # Extract URL from first argument if it exists
                            if node.args and isinstance(node.args[0], ast.Str):
                                patterns.append({
                                    'type': 'REST_ENDPOINT',
                                    'pattern': node.args[0].s,
                                    'method': node.func.attr.upper()
                                })
            
            return patterns
            
        except Exception as e:
            logging.error(f"Error extracting GHL patterns: {e}")
            return patterns

    def _extract_calendar_patterns(self, content: str) -> List[Dict]:
        """Extract Calendar-specific patterns."""
        patterns = []
        try:
            # Parse the content into an AST
            tree = ast.parse(content)
            
            # Extract AppleScript commands and calendar operations
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name) and node.func.id == 'osascript':
                        if node.args and isinstance(node.args[0], ast.Str):
                            patterns.append({
                                'type': 'APPLESCRIPT_COMMAND',
                                'pattern': node.args[0].s
                            })
                elif isinstance(node, ast.FunctionDef):
                    if any(cal_op in node.name.lower() for cal_op in ['event', 'calendar', 'reminder', 'schedule']):
                        patterns.append({
                            'type': 'CALENDAR_OPERATION',
                            'pattern': ' '.join(node.name.split('_')),
                            'function': node.name
                        })
            
            return patterns
            
        except Exception as e:
            logging.error(f"Error extracting Calendar patterns: {e}")
            return patterns
        