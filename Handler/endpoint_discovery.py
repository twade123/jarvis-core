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
from Handler.pattern_intent_mapper import PatternIntentMapper
from Handler.handler_analyzer_database import EndpointDiscovery as DatabaseHandler

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

class EndpointDiscovery:
    
    def __init__(self, db_connection):
        # Use centralized database handler
        self.db_handler = DatabaseHandler(db_connection)
        
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
        # Initialize pattern intent mapper
        self.pattern_mapper = PatternIntentMapper(db_connection=self.db_handler.conn)
        
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
        pass
        
    def __del__(self):
        """Clean up database connection."""
        pass
        
    def discover_endpoints(self, handler_path: str) -> Dict:
        """Discover endpoints in a handler file."""
        try:
            with open(handler_path, 'r') as f:
                content = f.read()
                
            # Extract the category from filename
            category = os.path.basename(handler_path).replace("handler_", "").replace(".py", "")
            
            # Handle different handler types
            if category == "<healthcare>":
                return self._discover_<healthcare>_endpoints(content)
            elif category == "ghl_requests":
                return self._discover_ghl_endpoints(content)
            elif category == "calendar":
                return self._discover_calendar_endpoints(content)
            elif category == "wolfram":
                return self._discover_wolfram_endpoints(content)
            else:
                # Default endpoint discovery
                return {
                    'rest_endpoints': self._discover_rest_endpoints(content),
                    'graphql_endpoints': self._discover_graphql_endpoints(content),
                    'dynamic_endpoints': self._discover_dynamic_endpoints(content),
                    'base_urls': self._discover_base_urls(content)
                }
            
        except Exception as e:
            logging.error(f"Error discovering endpoints in {handler_path}: {e}")
            return {}
        
    def _discover_<healthcare>_endpoints(self, content: str) -> Dict:
        """Discover <healthcare-platform>-specific endpoints."""
        try:
            # Extract <healthcare-platform> patterns
            <healthcare>_patterns = self._extract_<healthcare>_patterns(content)
            
            return {
                'rest_endpoints': set(),
                'graphql_endpoints': <healthcare>_patterns.get('endpoints', set()),
                'dynamic_endpoints': (
                    <healthcare>_patterns.get('queries', set()) |
                    <healthcare>_patterns.get('mutations', set()) |
                    <healthcare>_patterns.get('operations', set())
                ),
                'base_urls': <healthcare>_patterns.get('base_urls', set())
            }
        
        except Exception as e:
            logging.error(f"Error discovering <healthcare-platform> endpoints: {e}")
            return {}
        
    def _discover_ghl_endpoints(self, content: str) -> Dict:
        """Discover GHL-specific endpoints."""
        try:
            # Extract GHL patterns
            ghl_patterns = self._extract_ghl_patterns(content)
            
            # Process patterns into endpoint categories
            endpoints = {
                'rest_endpoints': set(),
                'graphql_endpoints': set(),
                'dynamic_endpoints': set(),
                'base_urls': {GHL_BASE_URL} if GHL_BASE_URL else set()
            }
            
            for pattern in ghl_patterns:
                if pattern.get('endpoint'):
                    endpoints['rest_endpoints'].add(
                        f"{pattern['method']} {pattern['endpoint']}"
                    )
                if pattern.get('operation'):
                    endpoints['dynamic_endpoints'].add(
                        f"ghl_{pattern['operation']}"
                    )
                    
            return endpoints
        
        except Exception as e:
            logging.error(f"Error discovering GHL endpoints: {e}")
            return {}
        
    def _discover_calendar_endpoints(self, content: str) -> Dict:
        """Discover Calendar-specific endpoints and patterns."""
        try:
            calendar_patterns = {
                'commands': set(),
                'properties': set(),
                'calendar_types': set(),
                'dynamic_endpoints': set()
            }

            # Extract calendar command patterns
            command_pattern = re.compile(r'command\s*==\s*["\']([^"\']+)["\']')
            commands = command_pattern.findall(content)
            calendar_patterns['commands'].update(commands)

            # Extract event property patterns
            property_pattern = re.compile(r'event_details\[["\']([^"\']+)["\']\]')
            properties = property_pattern.findall(content)
            calendar_patterns['properties'].update(properties)

            # Extract calendar types
            type_pattern = re.compile(r'app\.lower\(\)\s*==\s*["\']([^"\']+)["\']')
            types = type_pattern.findall(content)
            calendar_patterns['calendar_types'].update(types)

            # Extract dynamic patterns from AppleScript and Outlook commands
            script_pattern = re.compile(r'set\s+([^\s]+)\s+of\s+([^\s]+)\s+to')
            dynamic_patterns = script_pattern.findall(content)
            calendar_patterns['dynamic_endpoints'].update(
                f"{prop} of {obj}" for prop, obj in dynamic_patterns
            )

            return {
                'rest_endpoints': set(),  # Calendar doesn't use REST
                'graphql_endpoints': set(),  # Calendar doesn't use GraphQL
                'dynamic_endpoints': calendar_patterns['dynamic_endpoints'],
                'base_urls': set(),  # Calendar doesn't use URLs
                'calendar_commands': calendar_patterns['commands'],
                'calendar_properties': calendar_patterns['properties'],
                'calendar_types': calendar_patterns['calendar_types']
            }

        except Exception as e:
            logging.error(f"Error discovering calendar endpoints: {e}")
            return {}
            
    def _extract_patterns(self, content: str) -> Dict[str, Set[str]]:
        """Extract patterns from handler content and map them to intents."""
        patterns = {
            'rest': set(),
            'graphql': set(),
            'dynamic': set(),
            'python': set(),
            'applescript': set(),
            'base_urls': set()
        }
        
        try:
            logging.debug("Parsing content into AST")
            # Parse the content into an AST
            tree = ast.parse(content)
            
            # Extract patterns from AST
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    patterns['python'].add(node.name)
                    logging.debug(f"Extracted Python function: {node.name}")
                    
                elif isinstance(node, ast.Str):
                    value = node.s.strip()
                    if value:
                        # Check for AppleScript
                        if 'tell application' in value:
                            patterns['applescript'].add(value)
                            logging.debug(f"Extracted AppleScript: {value}")
                            # Extract operations from AppleScript
                            operations = [
                                'make new outgoing message',
                                'send',
                                'delete',
                                'move',
                                'set read status',
                                'set flagged status',
                                'synchronize',
                                'search'
                            ]
                            for op in operations:
                                if op in value:
                                    patterns['dynamic'].add(f"applescript_{op.replace(' ', '_')}")
                                    logging.debug(f"Extracted dynamic operation: {op}")
                        # Check for REST endpoints
                        elif any(x in value.lower() for x in ['http', 'api', 'endpoint']):
                            patterns['rest'].add(value)
                            logging.debug(f"Extracted REST endpoint: {value}")
                        # Check for GraphQL
                        elif any(x in value.lower() for x in ['query', 'mutation', 'graphql']):
                            patterns['graphql'].add(value)
                            logging.debug(f"Extracted GraphQL: {value}")
                        # Check for base URLs
                        elif urlparse(value).netloc:
                            patterns['base_urls'].add(value)
                            logging.debug(f"Extracted base URL: {value}")
                elif isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name):
                        patterns['python'].add(node.func.id)
                        logging.debug(f"Extracted Python call: {node.func.id}")
                    elif isinstance(node.func, ast.Attribute):
                        patterns['python'].add(node.func.attr)
                        logging.debug(f"Extracted Python attribute call: {node.func.attr}")
            
            # Map patterns to intents using PatternIntentMapper
            for pattern_type, pattern_set in patterns.items():
                for pattern in pattern_set:
                    mapped_intents = self.pattern_mapper.map_pattern_to_intents(pattern, pattern_type)
                    logging.info(f"Pattern: {pattern}, Mapped Intents: {mapped_intents}")
            
            return patterns
            
        except Exception as e:
            logging.error(f"Error extracting patterns: {e}")
            return patterns
            
    def _extract_<healthcare>_patterns(self, content: str) -> Dict[str, Set[str]]:
        """Extract <healthcare-platform>-specific patterns from handler code."""
        patterns = {
            'queries': set(),
            'mutations': set(),
            'fields': set(),
            'endpoints': set(),
            'operations': set(),
            'base_urls': set()
        }
        
        try:
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                # Extract GraphQL queries and mutations from string literals
                if isinstance(node, ast.Str):
                    value = node.s.strip()
                    if value.startswith('query '):
                        patterns['queries'].add(value)
                        patterns['operations'].add(value)
                    elif value.startswith('mutation '):
                        patterns['mutations'].add(value)
                        patterns['operations'].add(value)
                    elif 'https://api.get<healthcare>.com' in value:
                        patterns['base_urls'].add(value)
                
                # Extract field names from dictionary keys and variable assignments
                elif isinstance(node, (ast.Name, ast.Attribute)):
                    field_name = None
                    if isinstance(node, ast.Name):
                        field_name = node.id
                    else:
                        field_name = node.attr
                        
                    if field_name and any(field_name.endswith(suffix) for suffix in ['_field', '_fields']):
                        patterns['fields'].add(field_name.replace('_field', '').replace('_fields', ''))
                
                # Extract operation names from function definitions
                elif isinstance(node, ast.FunctionDef):
                    if any(node.name.startswith(prefix) for prefix in ['query_', 'mutation_']):
                        operation_type = 'queries' if node.name.startswith('query_') else 'mutations'
                        patterns[operation_type].add(node.name)
                        patterns['operations'].add(node.name)
                
                # Extract endpoints from decorated functions
                elif isinstance(node, ast.FunctionDef) and node.decorator_list:
                    for decorator in node.decorator_list:
                        if isinstance(decorator, ast.Call):
                            if hasattr(decorator.func, 'id') and decorator.func.id in ['query', 'mutation']:
                                patterns['endpoints'].add(node.name)
                
            return patterns
            
        except Exception as e:
            logging.error(f"Error extracting <healthcare-platform> patterns: {e}")
            return patterns
            
    def _extract_ghl_patterns(self, content: str) -> List[Dict[str, str]]:
        """Extract GHL-specific patterns."""
        patterns = []
        
        try:
            # Parse the content into an AST
            tree = ast.parse(content)
            
            # Extract patterns from AST
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # Extract operation name
                    patterns.append({
                        'operation': node.name,
                        'type': 'function'
                    })
                    
                elif isinstance(node, ast.Str):
                    value = node.s.strip()
                    if value:
                        # Check for API endpoints
                        if value.startswith(('/v1/', 'https://rest.gohighlevel.com')):
                            patterns.append({
                                'endpoint': value,
                                'method': 'GET',  # Default to GET
                                'type': 'endpoint'
                            })
                            
            return patterns
        
        except Exception as e:
            logging.error(f"Error extracting GHL patterns: {e}")
            return patterns
        
    def _extract_calendar_patterns(self, content: str) -> Dict:
        """Extract calendar-specific patterns from the handler content."""
        try:
            patterns = {
                'commands': set(),
                'properties': set(),
                'calendar_types': set(),
                'operations': set()
            }

            # Extract command patterns (create_event, delete_event, etc.)
            for match in re.finditer(r'if\s+command\s*==\s*["\']([^"\']+)["\']', content):
                patterns['commands'].add(match.group(1))

            # Extract property patterns (title, start_time, etc.)
            for match in re.finditer(r'["\']([^"\']+)["\']\s*in\s*event_details', content):
                patterns['properties'].add(match.group(1))

            # Extract calendar type patterns
            for match in re.finditer(r'app\.lower\(\)\s*==\s*["\']([^"\']+)["\']', content):
                patterns['calendar_types'].add(match.group(1))

            # Extract operation patterns from AppleScript commands
            script_ops = re.finditer(r'tell\s+application\s*["\']([^"\']+)["\']', content)
            for match in script_ops:
                patterns['operations'].add(f"tell_application_{match.group(1).lower()}")

            return patterns

        except Exception as e:
            logging.error(f"Error extracting calendar patterns: {e}")
            return {}
        
    def load_patterns(self, pattern_dir: str) -> Dict[str, int]:
        """Load patterns from Python pattern files."""
        pattern_counts = {}
        total_patterns = 0
        unique_patterns = set()
        
        try:
            pattern_files = list(Path(pattern_dir).glob('patterns_*.py'))
            logging.warning(f"Found {len(pattern_files)} pattern files")  # Changed to warning
            
            for pattern_file in pattern_files:
                if pattern_file.name == 'patterns_all.py':
                    continue
                    
                try:
                    # Import the pattern module
                    module_name = pattern_file.stem
                    spec = importlib.util.spec_from_file_location(module_name, pattern_file)
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    # Get patterns from the module
                    patterns = getattr(module, 'patterns', [])
                    pattern_strings = [json.dumps(p) for p in patterns]
                    unique_patterns.update(pattern_strings)
                    
                    count = len(patterns)
                    pattern_counts[module_name] = count
                    total_patterns += count
                    
                    # Store patterns by category
                    category = pattern_file.stem.replace('patterns_', '')
                    self.loaded_patterns[category] = patterns
                    
                    logging.warning(f"Loaded {count} patterns from {pattern_file.name}")  # Changed to warning
                    
                except Exception as e:
                    logging.error(f"Error loading {pattern_file}: {str(e)}")
                    continue
                
            logging.warning(f"Total patterns loaded: {total_patterns}")  # Changed to warning
            return pattern_counts
        
        except Exception as e:
            logging.error(f"Error loading patterns: {e}")
            return {}
        
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

    def load_intents(self, intent_dir: str) -> Tuple[int, int, int]:
        """Load intents from JSON intent files using parallel processing and batch operations."""
        try:
            # Find all intent JSON files
            intent_files = glob.glob(os.path.join(intent_dir, "intents_*.json"))
            logging.warning(f"Found {len(intent_files)} intent files")  # Changed to warning for visibility
            
            # Clear loaded intents
            self.loaded_intents = {}
            self.intents_by_category = {}
            
            # Process files in parallel
            with ThreadPoolExecutor(max_workers=4) as executor:
                file_results = list(executor.map(self.process_intent_file, intent_files))
            
            # Log file results
            logging.warning(f"Processed {len(file_results)} intent files")
            
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
            
            logging.warning(f"Merged {len(all_intents)} total intents")
            
            # Prepare batch inserts
            intent_values = []
            example_values = []
            action_values = []
            
            # Build batch insert data
            cursor = self.db_handler.conn.cursor()
            
            # First, clear existing data
            cursor.execute("DELETE FROM actions")
            cursor.execute("DELETE FROM examples")
            cursor.execute("DELETE FROM intents")
            self.db_handler.conn.commit()
            
            for intent_name, intent_data in all_intents.items():
                try:
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
                except Exception as e:
                    logging.error(f"Error processing intent {intent_name}: {e}")
                    continue
            
            logging.warning(f"Prepared {len(example_values)} examples and {len(action_values)} actions")
            
            # Batch insert examples and actions
            if example_values:
                cursor.executemany(
                    "INSERT INTO examples (intent_id, text) VALUES (?, ?)",
                    example_values
                )
            if action_values:
                cursor.executemany(
                    "INSERT INTO actions (intent_id, name) VALUES (?, ?)",
                    action_values
                )
            
            self.db_handler.conn.commit()
            
            total_intents = len(all_intents)
            total_examples = len(example_values)
            total_actions = len(action_values)
            
            logging.warning(f"Loaded {total_intents} intents, {total_examples} examples, and {total_actions} actions")
            logging.warning(f"Loaded intents for categories: {list(self.loaded_intents.keys())}")
            return total_intents, total_examples, total_actions
            
        except Exception as e:
            logging.error(f"Error loading intents: {str(e)}")
            logging.error(traceback.format_exc())  # Add stack trace
            return 0, 0, 0

    def extract_handler_patterns(self, handler_content: str, handler_type: str) -> List[Dict]:
        """Extract natural language patterns from handler code."""
        patterns = []
        try:
            # Parse AST
            tree = ast.parse(handler_content)
            
            # Track command metadata
            command_metadata = {}
            
            # First pass: collect command metadata
            for node in ast.walk(tree):
                if isinstance(node, ast.If):
                    if isinstance(node.test, ast.Compare):
                        if isinstance(node.test.left, ast.Name) and node.test.left.id == "command":
                            if isinstance(node.test.comparators[0], ast.Str):
                                command = node.test.comparators[0].s
                                command_metadata[command] = {
                                    'required_params': set(),
                                    'optional_params': set(),
                                    'error_conditions': set(),
                                    'operations': set()
                                }
                                
                                # Extract parameters from function definition
                                func_def = None
                                for parent in ast.walk(tree):
                                    if isinstance(parent, ast.FunctionDef):
                                        for arg in parent.args.args:
                                            if arg.arg not in ['self', 'command']:
                                                command_metadata[command]['optional_params'].add(arg.arg)
                                
                                # Extract required parameters from error checks
                                for check in ast.walk(node):
                                    if isinstance(check, ast.If):
                                        test_str = ast.unparse(check.test)
                                        if "not" in test_str:
                                            for param in command_metadata[command]['optional_params']:
                                                if f"not {param}" in test_str:
                                                    command_metadata[command]['required_params'].add(param)
                                                    command_metadata[command]['error_conditions'].add(f"{param}_required")
                                
                                # Extract AppleScript operations
                                for str_node in ast.walk(node):
                                    if isinstance(str_node, ast.Str):
                                        script = str_node.s
                                        if 'tell application "Mail"' in script:
                                            operations = [
                                                'make new outgoing message',
                                                'send',
                                                'delete',
                                                'move',
                                                'set read status',
                                                'set flagged status',
                                                'synchronize',
                                                'search'
                                            ]
                                            for op in operations:
                                                if op in script:
                                                    command_metadata[command]['operations'].add(op)
            
            # Second pass: create natural language patterns
            for command, metadata in command_metadata.items():
                # Base pattern from command name
                base_pattern = self._command_to_pattern(command)
                
                # Add patterns for each combination of required parameters
                param_patterns = self._generate_param_patterns(metadata['required_params'])
                
                for param_pattern in param_patterns:
                    pattern = {
                        'label': command.upper(),
                        'pattern': base_pattern + param_pattern,
                        'priority': 1,
                        'required_params': list(metadata['required_params']),
                        'optional_params': list(metadata['optional_params'] - metadata['required_params']),
                        'error_conditions': list(metadata['error_conditions']),
                        'operations': list(metadata['operations']),
                        'handler_type': handler_type
                    }
                    patterns.append(pattern)
                    
                    # Add variations with optional parameters
                    for optional_param in metadata['optional_params'] - metadata['required_params']:
                        opt_pattern = pattern.copy()
                        opt_pattern['pattern'] = base_pattern + param_pattern + self._param_to_pattern(optional_param)
                        patterns.append(opt_pattern)
            
            return patterns
            
        except Exception as e:
            logging.error(f"Error extracting patterns: {e}")
            return patterns

    def _command_to_pattern(self, command: str) -> List[Dict]:
        """Convert command name to spaCy pattern tokens."""
        pattern = []
        words = command.split('_')
        
        # Handle special cases
        if words[0] in ['send', 'read', 'delete', 'archive']:
            pattern.extend([
                {'LOWER': words[0]},
                {'LOWER': 'an' if words[1][0] in 'aeiou' else 'a'},
                {'LOWER': words[1]}
            ])
        elif words[0] == 'mark':
            pattern.extend([
                {'LOWER': 'mark'},
                {'LOWER': 'the'},
                {'LOWER': words[-1]},
                {'LOWER': 'as'},
                {'LOWER': words[2]}
            ])
        elif words[0] == 'move':
            pattern.extend([
                {'LOWER': 'move'},
                {'LOWER': 'the'},
                {'LOWER': words[1]},
                {'LOWER': 'to'},
                {'LOWER': 'folder'}
            ])
        else:
            # Default case: just split and convert
            for word in words:
                pattern.append({'LOWER': word})
                
        return pattern

    def _param_to_pattern(self, param: str) -> List[Dict]:
        """Convert parameter name to pattern tokens."""
        prepositions = {
            'recipient': 'to',
            'subject': 'with subject',
            'content': 'containing',
            'mailbox': 'in mailbox',
            'folder_name': 'to folder',
            'search_keyword': 'containing'
        }
        
        pattern = []
        if param in prepositions:
            for prep_word in prepositions[param].split():
                pattern.append({'LOWER': prep_word})
        pattern.append({'TEXT': '{' + param + '}'})
        return pattern

    def _generate_param_patterns(self, params: Set[str]) -> List[List[Dict]]:
        """Generate common combinations of parameter patterns."""
        if not params:
            return [[]]
            
        patterns = []
        
        # Common parameter groups
        common_groups = {
            'email_search': {'subject', 'content', 'search_keyword'},
            'email_action': {'subject', 'content', 'mailbox'},
            'folder_action': {'folder_name', 'mailbox'},
            'send_action': {'recipient', 'subject', 'content'}
        }
        
        # Add individual parameters
        for param in params:
            patterns.append(self._param_to_pattern(param))
            
        # Add common parameter combinations
        for group_name, group_params in common_groups.items():
            group_params = group_params & params  # Only use params that exist
            if group_params:
                combined = []
                for param in group_params:
                    combined.extend(self._param_to_pattern(param))
                patterns.append(combined)
                
        return patterns

    def match_patterns_to_intents(self, patterns: List[Dict], handler_type: str):
        """Match patterns to intents with category-specific handling."""
        matches = []
        total_patterns = len(patterns)
        
        try:
            # Map handler_type to intent category if needed
            intent_category = handler_type
            if handler_type == 'ghl_requests':
                intent_category = 'ghl'
            
            # Set threshold based on handler type
            similarity_threshold = 0.3 if handler_type == 'finder' else 0.5
            
            # Use already loaded intents for this category
            category_intents = self.loaded_intents.get(intent_category, [])
            logging.info(f"=== Matching Patterns for {handler_type} ===")
            logging.info(f"Found {len(category_intents)} loaded intents for category {intent_category}")
            logging.info(f"Processing {total_patterns} patterns with threshold {similarity_threshold}")
            # Add logging to capture details about patterns and handler types
            logging.info(f"Processing {total_patterns} patterns for handler type: {handler_type}")
            logging.info(f"Loaded intents for category {intent_category}: {len(category_intents)}")
        
            # Match each pattern against intents
            for i, pattern in enumerate(patterns, 1):
                logging.info(f"Pattern {i}: {pattern}")
                # Handle both list and dict pattern formats
                if isinstance(pattern, list):
                    pattern_text = ' '.join([token.get('LOWER', '') if isinstance(token, dict) else str(token) for token in pattern])
                else:
                    pattern_text = pattern.get('pattern', '') if isinstance(pattern, dict) else str(pattern)
                
                if not pattern_text:
                    continue
                    
                # Normalize pattern text based on handler type
                normalized_pattern = pattern_text
                if handler_type == 'finder':
                    normalized_pattern = normalized_pattern.replace('{path}', 'Documents')
                    normalized_pattern = normalized_pattern.replace('{destination}', 'Desktop')
                    normalized_pattern = normalized_pattern.replace('{new_name}', 'NewFolder')
                elif handler_type == 'email':
                    normalized_pattern = normalized_pattern.replace('{mailbox}', 'Inbox')
                    normalized_pattern = normalized_pattern.replace('{search_keyword}', 'report')
                
                best_match = None
                best_score = 0
                
                # First try exact matches for command patterns
                if 'COMMAND' in pattern_text.upper():
                    for intent in category_intents:
                        if not isinstance(intent, dict) or 'intent' not in intent:
                            continue
                        
                        # Try exact command match first
                        if any(example.lower() == normalized_pattern.lower() for example in intent.get('examples', [])):
                            best_match = {
                                'pattern': pattern,
                                'intent': intent['intent'],
                                'example': normalized_pattern,
                                'score': 1.0,
                                'category': intent_category,
                                'created_at': current_time
                            }
                            logging.info(f"Found exact match with intent: {intent['intent']}")
                            matches.append(best_match)
                            break

                # If no exact match, proceed with similarity matching
                if not best_match:
                    for intent in category_intents:
                        if not isinstance(intent, dict) or 'intent' not in intent:
                            continue
                            
                        for example in intent.get('examples', []):
                            # Calculate base similarity
                            score = self._calculate_similarity(normalized_pattern, example)
                            
                            # Apply pattern type weights if pattern is a dict
                            if isinstance(pattern, dict):
                                if pattern.get('type') == 'COMMAND':
                                    score *= 1.2  # Boost command patterns
                                elif pattern.get('type') == 'FUNCTION':
                                    score *= 1.1  # Boost function patterns
                                
                                # Apply category-specific weights
                                if handler_type == pattern.get('category'):
                                    score *= 1.15  # Boost patterns from same category
                            
                            if score > best_score and score >= similarity_threshold:
                                best_score = score
                                best_match = {
                                    'pattern': pattern,
                                    'intent': intent['intent'],
                                    'example': example,
                                    'score': score,
                                    'category': intent_category,
                                    'created_at': current_time
                                }
                                # Log the best match details in a readable format
                                logging.info(f"Best match: Intent: {best_match['intent']}, Example: {best_match['example']}, Score: {best_match['score']:.2f}")
                                if isinstance(pattern, dict):
                                    logging.info(f"  Pattern Label: {pattern.get('label', 'unknown')}")
                                    if pattern.get('category'):
                                        logging.info(f"  Category: {pattern.get('category')}")
                                    if pattern.get('pod_type'):
                                        logging.info(f"  Pod Type: {pattern.get('pod_type')}")
                                else:
                                    logging.info(f"  Pattern: {str(pattern)}")
                
                if best_match:
                    matches.append(best_match)
                    
                    # Store the match in the database with timestamp
                    try:
                        cursor = self.db_handler.conn.cursor()
                        pattern_value = pattern.get('pattern', '') if isinstance(pattern, dict) else str(pattern)
                        cursor.execute('''
                            INSERT INTO intent_mappings (
                                intent_id, pattern_id, handler_id, score, created_at
                            ) VALUES (
                                (SELECT id FROM intents WHERE name = ?),
                                (SELECT id FROM pattern_mapping WHERE pattern_value = ?),
                                (SELECT id FROM handlers WHERE handler_type = ?),
                                ?,
                                ?
                            )
                        ''', (
                            best_match['intent'],
                            pattern_value,
                            handler_type,
                            best_match['score'],
                            current_time
                        ))
                        self.db_handler.conn.commit()
                    except Exception as e:
                        logging.error(f"Error saving match to database: {e}")
        
            logging.info(f"\nTotal matches found: {len(matches)}")
            if matches:
                logging.info("\nTop matches:")
                sorted_matches = sorted(matches, key=lambda x: x['score'], reverse=True)
                for i, match in enumerate(sorted_matches[:10], 1):
                    logging.info(f"{i}. Intent: {match['intent']}")
                    pattern = match['pattern']
                    if isinstance(pattern, dict):
                        logging.info(f"   Pattern: {pattern.get('label', 'unknown')} - {match['example']}")
                        if pattern.get('category'):
                            logging.info(f"   Category: {pattern.get('category')}")
                        if pattern.get('pod_type'):
                            logging.info(f"   Pod Type: {pattern.get('pod_type')}")
                    else:
                        logging.info(f"   Pattern: {str(pattern)} - {match['example']}")
                    logging.info(f"   Score: {match['score']:.2f}")
                if len(matches) > 10:
                    logging.info(f"... and {len(matches)-10} more matches")
            return matches
        
        except Exception as e:
            logging.error(f"Error matching patterns to intents: {e}")
            logging.error(traceback.format_exc())  # Add stack trace
            return []

    def _store_handler_metrics(self, handler_name: str, patterns: List[Dict], handler_data: Dict) -> None:
        """Store metrics for a handler in the database."""
        try:
            cursor = self.db_handler.conn.cursor()
            current_time = datetime.now().isoformat()
            
            # Count different pattern types
            rest_patterns = sum(1 for p in patterns if p.get('type', '').startswith('REST_'))
            graphql_patterns = sum(1 for p in patterns if p.get('type', '').startswith('GRAPHQL_'))
            dynamic_patterns = sum(1 for p in patterns if p.get('type', '').startswith('DYNAMIC_'))
            python_patterns = sum(1 for p in patterns if p.get('type', '').startswith('PYTHON_'))
            applescript_patterns = sum(1 for p in patterns if p.get('type', '').startswith('APPLESCRIPT_'))
            
            # Count base URLs
            base_urls = len(handler_data.get('base_urls', set()))
            
            # <healthcare-platform> specific metrics
            <healthcare>_queries = len(handler_data.get('queries', set()))
            <healthcare>_mutations = len(handler_data.get('mutations', set()))
            <healthcare>_fields = len(handler_data.get('fields', set()))
            <healthcare>_endpoints = len(handler_data.get('endpoints', set()))
            <healthcare>_base_urls = len(handler_data.get('base_urls', set()))
            <healthcare>_parameters = len(handler_data.get('parameters', set()))
            <healthcare>_api_errors = len(handler_data.get('error_messages', set()))
            <healthcare>_validation_errors = len(handler_data.get('validation_errors', set()))
            <healthcare>_operations = len(handler_data.get('operations', set()))
            
            # GraphQL specific metrics
            graphql_queries = len(handler_data.get('graphql_queries', set()))
            graphql_mutations = len(handler_data.get('graphql_mutations', set()))
            graphql_fields = len(handler_data.get('fields', set()))
            graphql_types = len(handler_data.get('types', set()))
            graphql_fragments = len(handler_data.get('fragments', set()))
            graphql_interfaces = len(handler_data.get('interfaces', set()))
            graphql_unions = len(handler_data.get('unions', set()))
            graphql_inputs = len(handler_data.get('inputs', set()))
            graphql_directives = len(handler_data.get('directives', set()))
            graphql_subscriptions = len(handler_data.get('subscriptions', set()))
            
            # Insert metrics into database with timestamp
            cursor.execute('''
                INSERT INTO metrics (
                    handler_id, total_patterns, rest_patterns, graphql_patterns,
                    dynamic_patterns, python_patterns, applescript_patterns,
                    base_urls, <healthcare>_specific_queries, <healthcare>_specific_mutations,
                    <healthcare>_specific_fields, <healthcare>_specific_endpoints,
                    <healthcare>_specific_base_urls, <healthcare>_specific_parameters,
                    <healthcare>_specific_api_errors, <healthcare>_specific_validation_errors,
                    <healthcare>_specific_operations, graphql_queries, graphql_mutations,
                    graphql_fields, graphql_types, graphql_fragments,
                    graphql_interfaces, graphql_unions, graphql_inputs,
                    graphql_directives, graphql_subscriptions, created_at
                ) VALUES (
                    (SELECT id FROM handlers WHERE handler_name = ? ORDER BY created_at DESC LIMIT 1),
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
            ''', (
                handler_name, len(patterns), rest_patterns, graphql_patterns,
                dynamic_patterns, python_patterns, applescript_patterns,
                base_urls, <healthcare>_queries, <healthcare>_mutations,
                <healthcare>_fields, <healthcare>_endpoints, <healthcare>_base_urls,
                <healthcare>_parameters, <healthcare>_api_errors, <healthcare>_validation_errors,
                <healthcare>_operations, graphql_queries, graphql_mutations,
                graphql_fields, graphql_types, graphql_fragments,
                graphql_interfaces, graphql_unions, graphql_inputs,
                graphql_directives, graphql_subscriptions, current_time
            ))
            
            self.db_handler.conn.commit()
            logging.info(f"Stored metrics for handler: {handler_name}")
            
        except Exception as e:
            logging.error(f"Error storing metrics for {handler_name}: {e}")
            logging.error(f"Patterns: {patterns}")
            logging.error(f"Handler data: {handler_data}")

    def analyze_handler(self, handler_file: str) -> Tuple[str, List[Dict], List[Dict]]:
        """Analyze a handler file and match patterns to intents."""
        try:
            # Get handler type
            handler_type = self._get_handler_type(handler_file)
            if not handler_type:
                logging.warning(f"No handler type found for {os.path.basename(handler_file)}")
                return "", [], []
            
            logging.info(f"=== Analyzing {handler_type.upper()} Handler ===")
            logging.info(f"Reading file: {handler_file}")
            
            # Read handler content
            with open(handler_file, 'r') as f:
                content = f.read()
            logging.info(f"Read {len(content)} bytes from file")
            
            # Step 1: Collect handler-specific data
            logging.info("=== Collecting Handler Data ===")
            handler_data = None
            if handler_type == 'wolfram':
                handler_data = self._collect_wolfram_data(handler_file)
                if handler_data:
                    logging.info(f"Wolfram Data:")
                    for category, queries in handler_data.get('query_types', {}).items():
                        logging.info(f"{category}: {len(queries)} queries")
                        for query in queries:
                            logging.info(f"  - {query}")
                    
                    logging.info(f"Operations found: {len(handler_data.get('operations', []))}")
                    for op in handler_data.get('operations', []):
                        logging.info(f"  - {op}")
                    
                    logging.info(f"Pod Types found: {len(handler_data.get('pod_types', []))}")
                    for pod_type in handler_data.get('pod_types', []):
                        logging.info(f"  - {pod_type}")
                    
                    logging.info(f"Special Functions found: {len(handler_data.get('special_functions', []))}")
                    for func in handler_data.get('special_functions', []):
                        logging.info(f"  - {func}")
            elif handler_type == '<healthcare>':
                handler_data = self._collect_<healthcare>_data(handler_file)
                if handler_data:
                    logging.info(f"<healthcare-platform> Data:")
                    logging.info(f"- Queries: {len(handler_data.get('queries', []))} items")
                    for query in list(handler_data.get('queries', []))[:10]:  # Convert set to list before slicing
                        logging.info(f"  - {query}")
                    logging.info(f"- Mutations: {len(handler_data.get('mutations', []))} items")
                    for mutation in list(handler_data.get('mutations', []))[:10]:  # Convert set to list before slicing
                        logging.info(f"  - {mutation}")
                    logging.info(f"- Fields: {len(handler_data.get('fields', []))} items")
                    logging.info(f"- Endpoints: {len(handler_data.get('endpoints', []))} items")
            elif handler_type == 'ghl':
                handler_data = self._collect_ghl_data(handler_file)
                if handler_data:
                    logging.info(f"GHL Data:")
                    logging.info(f"- REST Endpoints: {len(handler_data.get('rest_endpoints', []))} items")
                    for endpoint in handler_data.get('rest_endpoints', []):
                        logging.info(f"  - {endpoint}")
                    logging.info(f"- Base URLs: {len(handler_data.get('base_urls', []))} items")
                    for url in handler_data.get('base_urls', []):
                        logging.info(f"  - {url}")
                    logging.info(f"- Operations: {len(handler_data.get('operations', []))} items")
                    for op in handler_data.get('operations', []):
                        logging.info(f"  - {op}")
                    logging.info(f"- Parameters: {len(handler_data.get('parameters', []))} items")
                    for param in handler_data.get('parameters', []):
                        logging.info(f"  - {param}")
            elif handler_type == 'calendar':
                handler_data = self._collect_calendar_data(handler_file)
                if handler_data:
                    logging.info(f"Calendar Data:")
                    logging.info(f"- Events: {len(handler_data.get('events', []))} items")
                    for event in handler_data.get('events', []):
                        logging.info(f"  - {event}")
                    logging.info(f"- Operations: {len(handler_data.get('operations', []))} items")
                    for op in handler_data.get('operations', []):
                        logging.info(f"  - {op}")
                    logging.info(f"- Parameters: {len(handler_data.get('parameters', []))} items")
                    for param in handler_data.get('parameters', []):
                        logging.info(f"  - {param}")
            elif handler_type == 'email':
                handler_data = self._collect_email_data(handler_file)
                if handler_data:
                    logging.info(f"Email Data:")
                    logging.info(f"- Commands: {len(handler_data.get('commands', []))} items")
                    for cmd in handler_data.get('commands', []):
                        logging.info(f"  - {cmd}")
                    logging.info(f"- Operations: {len(handler_data.get('operations', []))} items")
                    for op in handler_data.get('operations', []):
                        logging.info(f"  - {op}")
                    logging.info(f"- Parameters: {len(handler_data.get('parameters', []))} items")
                    for param in handler_data.get('parameters', []):
                        logging.info(f"  - {param}")
            
            if not handler_data:
                logging.warning(f"No data collected for {handler_file}")
                return handler_type, [], []
            
            # Step 2: Generate patterns from collected data
            logging.info("=== Generating Patterns ===")
            patterns = []
            if handler_type == 'wolfram':
                patterns = self._generate_wolfram_patterns(handler_data)
                if patterns:
                    logging.info(f"Generated {len(patterns)} Wolfram patterns")
                    # Only show a few examples
                    for i, pattern in enumerate(patterns[:5], 1):
                        logging.info(f"  {i}. {pattern.get('label', 'unknown')}: {pattern.get('pattern', '')}")
                    if len(patterns) > 5:
                        logging.info(f"  ... and {len(patterns) - 5} more")
            elif handler_type == '<healthcare>':
                patterns = self._generate_<healthcare>_patterns(handler_data)
            elif handler_type == 'ghl':
                patterns = self._generate_ghl_patterns(handler_data)
            elif handler_type == 'calendar':
                patterns = self._generate_calendar_patterns(handler_data)
            elif handler_type == 'email':
                patterns = self._generate_email_patterns(handler_data)
                
            if not patterns:
                logging.warning(f"No patterns generated for {handler_file}")
                return handler_type, [], []
            
            # Step 3: Store patterns
            logging.info("=== Storing Patterns ===")
            try:
                self._process_handler_patterns(handler_type, patterns)
            except Exception as e:
                logging.error(f"Error processing patterns for {handler_type}: {e}")
            
            # Step 4: Match patterns to intents using global mapper
            logging.info("=== Matching Patterns to Intents ===")
            
            # Map patterns using the global mapper
            intent_matches = self.pattern_mapper.map_patterns_to_intents(
                patterns=patterns,
                loaded_intents=self.loaded_intents,
                handler_type=handler_type
            )
            
            if intent_matches:
                logging.info(f"Found {len(intent_matches)} intent matches")
                # Show matches grouped by match type
                exact_matches = [m for m in intent_matches if m['match_type'] == 'exact']
                semantic_matches = [m for m in intent_matches if m['match_type'] == 'semantic']
                
                if exact_matches:
                    logging.info("\nExact Matches:")
                    for i, match in enumerate(exact_matches[:5], 1):
                        logging.info(f"  {i}. Intent: {match['intent']}")
                        logging.info(f"     Pattern: {match['pattern'].get('label', 'unknown')}")
                        if match['pattern'].get('category'):
                            logging.info(f"     Category: {match['pattern']['category']}")
                        if match['pattern'].get('pod_type'):
                            logging.info(f"     Pod Type: {match['pattern']['pod_type']}")
                    if len(exact_matches) > 5:
                        logging.info(f"  ... and {len(exact_matches)-5} more exact matches")
                
                if semantic_matches:
                    logging.info("\nSemantic Matches:")
                    sorted_semantic = sorted(semantic_matches, key=lambda x: x['score'], reverse=True)
                    for i, match in enumerate(sorted_semantic[:5], 1):
                        logging.info(f"  {i}. Intent: {match['intent']} (score: {match['score']:.2f})")
                        logging.info(f"     Pattern: {match['pattern'].get('label', 'unknown')}")
                        if match['pattern'].get('category'):
                            logging.info(f"     Category: {match['pattern']['category']}")
                        if match['pattern'].get('pod_type'):
                            logging.info(f"     Pod Type: {match['pattern']['pod_type']}")
                    if len(semantic_matches) > 5:
                        logging.info(f"  ... and {len(semantic_matches)-5} more semantic matches")
            
            return handler_type, patterns, intent_matches
            
        except Exception as e:
            logging.error(f"Error analyzing handler {handler_file}: {str(e)}")
            logging.error(traceback.format_exc())
            return "", [], []

    def _get_handler_type(self, handler_file: str) -> str:
        """Get the type of handler from the file name using mapping."""
        try:
            # Define supported handlers (same as in main)
            handlers = {
                'handler_<healthcare>_sdk2.py': '<healthcare>',
                'handler_ghl_requests.py': 'ghl',
                'handler_calendar.py': 'calendar',
                'handler_wolfram.py': 'wolfram',
                'handler_email.py': 'email'
            }
            
            # Get mapped type from our handlers dictionary
            handler_name = os.path.basename(handler_file)
            mapped_type = handlers.get(handler_name)
            
            if mapped_type:
                logging.info(f"Found handler type {mapped_type} for {handler_name}")
                return mapped_type
                
            logging.warning(f"No handler type mapping found for {handler_name}")
            return None
            
        except Exception as e:
            logging.error(f"Error getting handler type from {handler_file}: {e}")
            return None

    def _map_<healthcare>_patterns_to_intents(self, patterns: Dict[str, Set[str]]) -> Dict[str, List[Dict]]:
        """Map <healthcare-platform> patterns to intents using spaCy similarity with pre-defined patterns."""
        mappings = {}
        
        try:
            # Get all intents from database
            cursor = self.db_handler.conn.cursor()
            cursor.execute('''
                SELECT i.id, i.name, i.category, e.text 
                FROM intents i 
                LEFT JOIN examples e ON i.id = e.intent_id
            ''')
            intent_data = cursor.fetchall()
            
            # Group by intent
            intents = {}
            for row in intent_data:
                intent_id, intent_name, category, example = row
                if intent_id not in intents:
                    intents[intent_id] = {
                        'name': intent_name,
                        'category': category,
                        'examples': []
                    }
                if example:
                    intents[intent_id]['examples'].append(example)

            # Get pre-defined <healthcare-platform> patterns
            predefined_patterns = self.loaded_patterns.get('<healthcare>', [])
            
            # Create a mapping of predefined patterns to intents
            pattern_to_intent = {}
            for pattern in predefined_patterns:
                if 'label' in pattern:
                    pattern_text = ' '.join([token.get('LOWER', '') for token in pattern['pattern']])
                    pattern_to_intent[pattern_text] = pattern['label']

            # Process each handler pattern
            for pattern_type, pattern_set in patterns.items():
                for pattern in pattern_set:
                    pattern_str = str(pattern)
                    pattern_doc = self.nlp(pattern_str)
                    best_match = None
                    best_score = 0
                    
                    # First try to match with predefined patterns
                    for pred_pattern, intent_label in pattern_to_intent.items():
                        pred_doc = self.nlp(pred_pattern)
                        score = pattern_doc.similarity(pred_doc)
                        
                        # Higher weight for predefined pattern matches
                        score = score * 1.2  # 20% boost for predefined patterns
                        
                        if score > best_score and score > 0.7:
                            best_score = score
                            # Find the intent ID for this label
                            for intent_id, intent_info in intents.items():
                                if intent_info['name'] == intent_label:
                                    best_match = intent_id
                                    break
                    
                    # If no good match with predefined patterns, try direct intent matching
                    if not best_match:
                        for intent_id, intent_info in intents.items():
                            # Check intent name similarity
                            intent_doc = self.nlp(intent_info['name'])
                            score = pattern_doc.similarity(intent_doc)
                            
                            # Check examples similarity
                            for example in intent_info['examples']:
                                example_doc = self.nlp(example)
                                example_score = pattern_doc.similarity(example_doc)
                                score = max(score, example_score)
                            
                            if score > best_score and score > 0.7:
                                best_score = score
                                best_match = intent_id
                    
                    # Store the mapping
                    if best_match:
                        if pattern_type not in mappings:
                            mappings[pattern_type] = []
                        mappings[pattern_type].append({
                            'pattern': pattern_str,
                            'intent_id': best_match,
                            'score': best_score,
                            'intent_name': intents[best_match]['name']
                        })
            
            return mappings

        except Exception as e:
            logging.error(f"Error mapping patterns to intents: {e}")
            return {}

    def _count_patterns(self, patterns: Dict[str, Any]) -> int:
        """Count total number of patterns."""
        total = 0
        if not patterns:
            return total
            
        for pattern_type, pattern_set in patterns.items():
            if isinstance(pattern_set, (set, list)):
                total += len(pattern_set)
            elif isinstance(pattern_set, dict):
                total += sum(len(v) for v in pattern_set.values() if isinstance(v, (set, list)))
        
        return total

    def _extract_email_patterns(self, content: str) -> Dict[str, Set[str]]:
        """Extract email-specific patterns from handler code."""
        patterns = {
            'commands': set(),
            'applescript_operations': set(),
            'required_params': set(),
            'optional_params': set(),
            'mailboxes': set(),
            'error_conditions': set(),
            'response_messages': set(),
            'message_properties': set(),
            'message_operations': set()
        }
        
        try:
            logging.info("Starting email pattern extraction...")
            tree = ast.parse(content)
            
            # Extract patterns from AST
            for node in ast.walk(tree):
                try:
                    # Extract command patterns from if/elif statements
                    if isinstance(node, ast.If):
                        self._extract_if_statement_patterns(node, patterns)
                    
                    # Extract AppleScript operations
                    elif isinstance(node, ast.Call):
                        self._extract_applescript_operations(node, patterns)
                        
                    # Extract string literals that might be mailboxes or operations
                    elif isinstance(node, ast.Str):
                        self._extract_string_patterns(node, patterns)
                        
                except Exception as node_error:
                    logging.error(f"Error processing AST node: {str(node_error)}")
                    continue
            
            logging.info(f"Completed email pattern extraction. Found {sum(len(p) for p in patterns.values())} total patterns")
            return patterns
            
        except SyntaxError as se:
            logging.error(f"Syntax error in email handler: {str(se)}")
            return patterns
        except Exception as e:
            logging.error(f"Error in email pattern extraction: {str(e)}")
            return patterns
            
    def _extract_if_statement_patterns(self, node: ast.If, patterns: Dict[str, Set[str]]):
        """Extract patterns from if statements."""
        if isinstance(node.test, ast.Compare):
            if isinstance(node.test.left, ast.Name) and node.test.left.id == "command":
                if isinstance(node.test.comparators[0], ast.Str):
                    command = node.test.comparators[0].s
                    patterns['commands'].add(command)
                    logging.info(f"Found command pattern: {command}")
                    
                    # Extract required parameters and error conditions
                    for check in ast.walk(node):
                        if isinstance(check, ast.If):
                            test_str = ast.unparse(check.test)
                            if "not" in test_str:
                                vars_checked = re.findall(r'not\s+(\w+)', test_str)
                                patterns['required_params'].update(vars_checked)
                                patterns['error_conditions'].update(f"{var}_required" for var in vars_checked)
                                logging.info(f"Found required params: {vars_checked}")
                                
    def _extract_applescript_operations(self, node: ast.Call, patterns: Dict[str, Set[str]]):
        """Extract AppleScript operations from function calls."""
        try:
            if isinstance(node.func, ast.Name) and 'applescript' in node.func.id.lower():
                for arg in node.args:
                    if isinstance(arg, ast.Str):
                        patterns['applescript_operations'].add(arg.s)
                        logging.info(f"Found AppleScript operation: {arg.s}")
        except Exception as e:
            logging.error(f"Error extracting AppleScript operation: {str(e)}")
            
    def _extract_string_patterns(self, node: ast.Str, patterns: Dict[str, Set[str]]):
        """Extract patterns from string literals."""
        try:
            value = node.s.lower()
            if 'mailbox' in value or 'folder' in value:
                patterns['mailboxes'].add(node.s)
            elif any(op in value for op in ['read', 'send', 'move', 'delete', 'forward', 'reply']):
                patterns['message_operations'].add(node.s)
        except Exception as e:
            logging.error(f"Error extracting string pattern: {str(e)}")

    def _generate_<healthcare>_patterns(self, <healthcare>_data: Dict) -> List[Dict]:
        """Generate patterns for <healthcare-platform> operations using collected data."""
        patterns = []
        pattern_count = 0  # Add counter
        MAX_PATTERNS = 2500  # Add limit
        
        if not <healthcare>_data:
            logging.warning("No <healthcare-platform> data available for pattern generation")
            return patterns
            
        try:
            # Process queries
            for query in <healthcare>_data.get('queries', []):
                if pattern_count >= MAX_PATTERNS:  # Check limit
                    break
                pattern_count += 1  # Increment counter
                # Base command pattern with GraphQL endpoint mapping
                base_pattern = {
                    'type': f"QUERY_{query.upper()}",
                    'category': '<healthcare>',
                    'command': query,
                    'pattern': query.replace('_', ' '),
                    'is_graphql': True,
                    'graphql_type': 'query',
                    'endpoint': f"query_{query}",
                    'fields': [field for field in <healthcare>_data.get('fields', []) if field.lower() in query.lower()]
                }
                patterns.append(base_pattern)
                
                # Add natural language variations with endpoint mapping
                nl_patterns = []
                if 'client' in query or 'patient' in query:
                    nl_patterns.extend([
                        f'Get {query.replace("_", " ")}',
                        f'Show patient {query.replace("client_", "").replace("_", " ")}',
                        f'Display {query.replace("_", " ")}',
                        f'Find {query.replace("_", " ")}',
                        f'Retrieve {query.replace("_", " ")}'
                    ])
                elif 'appointment' in query:
                    nl_patterns.extend([
                        f'Check {query.replace("_", " ")}',
                        f'Show {query.replace("_", " ")}',
                        f'Get {query.replace("_", " ")}',
                        f'Display {query.replace("_", " ")}',
                        f'Find {query.replace("_", " ")}'
                    ])
                elif 'metric' in query:
                    nl_patterns.extend([
                        f'Show {query.replace("_", " ")}',
                        f'Get {query.replace("_", " ")}',
                        f'Check {query.replace("_", " ")}',
                        f'Display {query.replace("_", " ")}',
                        f'Find {query.replace("_", " ")}'
                    ])
                
                # Add natural language patterns with endpoint mapping
                for nl_pattern in nl_patterns:
                    nl_dict = base_pattern.copy()
                    nl_dict['pattern'] = nl_pattern
                    nl_dict['is_natural'] = True
                    patterns.append(nl_dict)
            
            # Process additional queries from <healthcare>_query.py
            for query in <healthcare>_data.get('additional_queries', []):
                base_pattern = {
                    'type': f"QUERY_{query.upper()}",
                    'category': '<healthcare>',
                    'command': query,
                    'pattern': query.replace('_', ' '),
                    'is_graphql': True,
                    'graphql_type': 'query',
                    'endpoint': f"query_{query}",
                    'fields': [field for field in <healthcare>_data.get('fields', []) if field.lower() in query.lower()]
                }
                patterns.append(base_pattern)
                
                # Add natural language variations
                nl_patterns = [
                    f'Get {query.replace("_", " ")}',
                    f'Show {query.replace("_", " ")}',
                    f'Display {query.replace("_", " ")}',
                    f'Find {query.replace("_", " ")}',
                    f'Retrieve {query.replace("_", " ")}'
                ]
                
                for nl_pattern in nl_patterns:
                    nl_dict = base_pattern.copy()
                    nl_dict['pattern'] = nl_pattern
                    nl_dict['is_natural'] = True
                    patterns.append(nl_dict)
            
            # Process mutations
            for mutation in <healthcare>_data.get('mutations', []):
                # Base command pattern with GraphQL endpoint mapping
                base_pattern = {
                    'type': f"MUTATION_{mutation.upper()}",
                    'category': '<healthcare>',
                    'command': mutation,
                    'pattern': mutation.replace('_', ' '),
                    'is_graphql': True,
                    'graphql_type': 'mutation',
                    'endpoint': f"mutation_{mutation}",
                    'fields': [field for field in <healthcare>_data.get('fields', []) if field.lower() in mutation.lower()]
                }
                patterns.append(base_pattern)
            
                # Add natural language variations with endpoint mapping
                nl_patterns = []
                if mutation.startswith('create'):
                    resource = mutation.replace('create_', '')
                    nl_patterns.extend([
                        f'Create new {resource.replace("_", " ")}',
                        f'Add new {resource.replace("_", " ")}',
                        f'Make new {resource.replace("_", " ")}',
                        f'Set up new {resource.replace("_", " ")}',
                        f'Start new {resource.replace("_", " ")}'
                    ])
                elif mutation.startswith('update'):
                    resource = mutation.replace('update_', '')
                    nl_patterns.extend([
                        f'Update {resource.replace("_", " ")}',
                        f'Modify {resource.replace("_", " ")}',
                        f'Change {resource.replace("_", " ")}',
                        f'Edit {resource.replace("_", " ")}',
                        f'Revise {resource.replace("_", " ")}'
                    ])
                elif mutation.startswith('delete'):
                    resource = mutation.replace('delete_', '')
                    nl_patterns.extend([
                        f'Delete {resource.replace("_", " ")}',
                        f'Remove {resource.replace("_", " ")}',
                        f'Cancel {resource.replace("_", " ")}',
                        f'End {resource.replace("_", " ")}',
                        f'Stop {resource.replace("_", " ")}'
                    ])
                
                # Add natural language patterns with endpoint mapping
                for nl_pattern in nl_patterns:
                    nl_dict = base_pattern.copy()
                    nl_dict['pattern'] = nl_pattern
                    nl_dict['is_natural'] = True
                    patterns.append(nl_dict)
            
            # Process fields and nested fields
            for field in <healthcare>_data.get('fields', []):
                field_pattern = {
                    'type': f"FIELD_{field.upper()}",
                    'category': '<healthcare>',
                    'field': field,
                    'pattern': field.replace('_', ' '),
                    'is_field': True,
                    'related_queries': [q for q in <healthcare>_data.get('queries', []) if field.lower() in q.lower()],
                    'related_mutations': [m for m in <healthcare>_data.get('mutations', []) if field.lower() in m.lower()]
                }
                patterns.append(field_pattern)
            
            for nested_field in <healthcare>_data.get('nested_fields', []):
                nested_pattern = {
                    'type': f"NESTED_FIELD_{nested_field.upper()}",
                    'category': '<healthcare>',
                    'field': nested_field,
                    'pattern': nested_field.replace('_', ' '),
                    'is_nested_field': True,
                    'related_queries': [q for q in <healthcare>_data.get('queries', []) if nested_field.lower() in q.lower()],
                    'related_mutations': [m for m in <healthcare>_data.get('mutations', []) if nested_field.lower() in m.lower()]
                }
                patterns.append(nested_pattern)
            
            return patterns
            
        except Exception as e:
            logging.error(f"Error generating <healthcare-platform> patterns: {e}")
            return patterns
        
    def _generate_ghl_patterns(self, ghl_data: Dict) -> List[Dict]:
        """Generate natural language patterns for GHL operations."""
        patterns = []
        
        try:
            # Process mutations and queries
            for mutation in ghl_data['mutations']:
                # Base pattern
                pattern = {
                    'type': f"MUTATION_{mutation.upper()}",
                    'pattern': mutation.replace('_', ' '),
                    'category': 'ghl',
                    'operation_type': 'mutation',
                    'handler_type': 'ghl'
                }
                patterns.append(pattern)
                
                # Add natural language variations
                nl_patterns = []
                if 'create' in mutation:
                    resource = mutation.replace('create_', '')
                    nl_patterns.extend([
                        f'Create new {resource.replace("_", " ")}',
                        f'Add new {resource.replace("_", " ")}',
                        f'Make new {resource.replace("_", " ")}',
                        f'Set up new {resource.replace("_", " ")}',
                        f'Start new {resource.replace("_", " ")}'
                    ])
                elif 'update' in mutation:
                    resource = mutation.replace('update_', '')
                    nl_patterns.extend([
                        f'Update {resource.replace("_", " ")}',
                        f'Modify {resource.replace("_", " ")}',
                        f'Change {resource.replace("_", " ")}',
                        f'Edit {resource.replace("_", " ")}',
                        f'Revise {resource.replace("_", " ")}',
                        f'Alter {resource.replace("_", " ")}',
                        f'Adjust {resource.replace("_", " ")}',
                        f'Update existing {resource.replace("_", " ")}',
                        f'Modify current {resource.replace("_", " ")}',
                        f'Change details of {resource.replace("_", " ")}',
                        f'Edit information for {resource.replace("_", " ")}'
                    ])
                elif 'delete' in mutation:
                    resource = mutation.replace('delete_', '')
                    nl_patterns.extend([
                        f'Delete {resource.replace("_", " ")}',
                        f'Remove {resource.replace("_", " ")}',
                        f'Cancel {resource.replace("_", " ")}',
                        f'Erase {resource.replace("_", " ")}',
                        f'Eliminate {resource.replace("_", " ")}',
                        f'Get rid of {resource.replace("_", " ")}',
                        f'Destroy {resource.replace("_", " ")}',
                        f'Delete existing {resource.replace("_", " ")}',
                        f'Remove current {resource.replace("_", " ")}',
                        f'Cancel this {resource.replace("_", " ")}',
                        f'Remove this {resource.replace("_", " ")}'
                    ])
                
                # Add ID-based variations
                if any(x in mutation for x in ['contact', 'task', 'appointment', 'campaign', 'form', 'opportunity', 'pipeline', 'tag']):
                    resource = next(x for x in ['contact', 'task', 'appointment', 'campaign', 'form', 'opportunity', 'pipeline', 'tag'] if x in mutation)
                    if 'create' in mutation:
                        nl_patterns.extend([
                            f'Create {resource} with details',
                            f'Add {resource} with information',
                            f'Make {resource} using data',
                            f'Create new {resource} with provided information',
                            f'Add {resource} with these details',
                            f'Set up {resource} with following data'
                        ])
                    elif 'update' in mutation:
                        nl_patterns.extend([
                            f'Update {resource} with ID',
                            f'Modify {resource} number',
                            f'Change {resource} details for ID',
                            f'Update {resource} with specific ID',
                            f'Modify {resource} with given ID',
                            f'Change details of {resource} ID',
                            f'Edit {resource} with ID number'
                        ])
                    elif 'delete' in mutation:
                        nl_patterns.extend([
                            f'Delete {resource} with ID',
                            f'Remove {resource} number',
                            f'Cancel {resource} by ID',
                            f'Delete {resource} with specific ID',
                            f'Remove {resource} with given ID',
                            f'Delete specific {resource} ID',
                            f'Remove {resource} by ID number'
                        ])
                
                for nl_pattern in nl_patterns:
                    patterns.append({
                        'type': f"MUTATION_{mutation.upper()}",
                        'pattern': nl_pattern,
                        'category': 'ghl',
                        'operation_type': 'mutation',
                        'handler_type': 'ghl',
                        'is_natural': True
                    })
            
            for query in ghl_data['queries']:
                # Base pattern
                pattern = {
                    'type': f"QUERY_{query.upper()}",
                    'pattern': query.replace('_', ' '),
                    'category': 'ghl',
                    'operation_type': 'query',
                    'handler_type': 'ghl'
                }
                patterns.append(pattern)
                
                # Add natural language variations
                nl_patterns = []
                if 'find' in query or 'get' in query:
                    resource = query.replace('find_', '').replace('get_', '')
                    nl_patterns.extend([
                        f'Find {resource.replace("_", " ")}',
                        f'Get {resource.replace("_", " ")}',
                        f'Show {resource.replace("_", " ")}',
                        f'Display {resource.replace("_", " ")}',
                        f'Retrieve {resource.replace("_", " ")}',
                        f'Fetch {resource.replace("_", " ")}',
                        f'Look up {resource.replace("_", " ")}',
                        f'Find a specific {resource.replace("_", " ")}',
                        f'Get details of {resource.replace("_", " ")}',
                        f'Show information for {resource.replace("_", " ")}',
                        f'Look up specific {resource.replace("_", " ")}'
                    ])
                elif 'list' in query:
                    resource = query.replace('list_', '')
                    nl_patterns.extend([
                        f'List all {resource.replace("_", " ")}',
                        f'Show all {resource.replace("_", " ")}',
                        f'Display all {resource.replace("_", " ")}',
                        f'Get all {resource.replace("_", " ")}',
                        f'Retrieve all {resource.replace("_", " ")}',
                        f'Fetch all {resource.replace("_", " ")}',
                        f'Show me all {resource.replace("_", " ")}',
                        f'List available {resource.replace("_", " ")}',
                        f'Show existing {resource.replace("_", " ")}',
                        f'Get list of {resource.replace("_", " ")}',
                        f'Display available {resource.replace("_", " ")}'
                    ])
                elif 'search' in query:
                    resource = query.replace('search_', '')
                    nl_patterns.extend([
                        f'Search for {resource.replace("_", " ")}',
                        f'Find matching {resource.replace("_", " ")}',
                        f'Look for {resource.replace("_", " ")}',
                        f'Search {resource.replace("_", " ")}',
                        f'Query {resource.replace("_", " ")}',
                        f'Find {resource.replace("_", " ")}',
                        f'Locate {resource.replace("_", " ")}',
                        f'Search through {resource.replace("_", " ")}',
                        f'Find all matching {resource.replace("_", " ")}',
                        f'Look up matching {resource.replace("_", " ")}',
                        f'Search available {resource.replace("_", " ")}'
                    ])
                
                # Add specific patterns for special queries
                if 'find_contact_by_email' in query:
                    nl_patterns.extend([
                        'Find contact using email',
                        'Search for contact by email address',
                        'Look up contact with email',
                        'Get contact details from email',
                        'Find person by email',
                        'Search contact using email address',
                        'Find contact with email address',
                        'Look up person using email',
                        'Get contact information by email',
                        'Search for person using email address',
                        'Find contact details with email'
                    ])
                elif 'find_contact_by_phone' in query:
                    nl_patterns.extend([
                        'Find contact using phone number',
                        'Search for contact by phone',
                        'Look up contact with phone number',
                        'Get contact details from phone',
                        'Find person by phone number',
                        'Search contact using phone',
                        'Find contact with phone number',
                        'Look up person using phone',
                        'Get contact information by phone',
                        'Search for person using phone number',
                        'Find contact details with phone'
                    ])
                elif 'get_analytics' in query:
                    nl_patterns.extend([
                        'Get analytics data',
                        'Show analytics report',
                        'Display analytics information',
                        'Retrieve analytics stats',
                        'Get analytics metrics',
                        'Show analytics dashboard',
                        'View analytics report',
                        'Get analytics overview',
                        'Show analytics summary',
                        'Display analytics metrics',
                        'Get analytics statistics'
                    ])
                
                for nl_pattern in nl_patterns:
                    patterns.append({
                        'type': f"QUERY_{query.upper()}",
                        'pattern': nl_pattern,
                        'category': 'ghl',
                        'operation_type': 'query',
                        'handler_type': 'ghl',
                        'is_natural': True
                    })
            
            # Process endpoints to generate additional patterns
            for endpoint in ghl_data.get('endpoints', set()):
                if isinstance(endpoint, str) and ' ' in endpoint:
                    method, path = endpoint.split(' ', 1)
                    
                    # Extract resource type and ID parameters
                    parts = path.split('/')
                    resource_type = next((part for part in parts if part in [
                        'contacts', 'tags', 'pipelines', 'opportunities', 
                        'tasks', 'appointments', 'forms', 'emails', 
                        'email-campaigns', 'analytics', 'custom-fields', 
                        'locations', 'timezones'
                    ]), None)
                    
                    if resource_type:
                        # Generate patterns based on endpoint structure
                        base_resource = resource_type.rstrip('s')  # Convert plural to singular
                        
                        if '{' in path and '}' in path:
                            # Endpoint with parameters
                            param_patterns = [
                                f'{method.capitalize()} {base_resource} by ID',
                                f'{method.capitalize()} specific {base_resource}',
                                f'{method.capitalize()} {base_resource} with identifier',
                                f'Use ID to {method.lower()} {base_resource}',
                                f'{method.capitalize()} {base_resource} using ID',
                                f'Perform {method.lower()} operation on {base_resource}',
                                f'{method.capitalize()} operation for {base_resource}',
                                f'{method.lower()} specific {base_resource} by ID',
                                f'Execute {method.lower()} on {base_resource}',
                                f'{method.capitalize()} {base_resource} with given ID'
                            ]
                        else:
                            # Endpoint without parameters
                            param_patterns = [
                                f'{method.capitalize()} {base_resource}',
                                f'{method.capitalize()} all {resource_type}',
                                f'{method.lower()} {resource_type} list',
                                f'{method.capitalize()} multiple {resource_type}',
                                f'Bulk {method.lower()} {resource_type}',
                                f'Perform {method.lower()} on {resource_type}',
                                f'{method.capitalize()} operation for {resource_type}',
                                f'Execute {method.lower()} for {resource_type}',
                                f'{method.capitalize()} all available {resource_type}',
                                f'Bulk {method.lower()} operation for {resource_type}'
                            ]
                        
                        for pattern_text in param_patterns:
                            patterns.append({
                                'type': f"ENDPOINT_{method}_{resource_type.upper()}",
                                'pattern': pattern_text,
                                'category': 'ghl',
                                'operation_type': 'endpoint',
                                'handler_type': 'ghl',
                                'method': method,
                                'resource': resource_type,
                                'is_natural': True
                            })
            
            # Process nested resources (e.g., tasks within contacts)
            nested_resources = [
                ('contacts', 'tasks'),
                ('contacts', 'appointments'),
                ('contacts', 'forms'),
                ('contacts', 'email-campaigns')
            ]
            
            for parent, child in nested_resources:
                parent_singular = parent.rstrip('s')
                child_singular = child.rstrip('s')
                
                nested_patterns = [
                    f'Manage {child} for {parent_singular}',
                    f'Handle {child} of {parent_singular}',
                    f'{parent_singular} {child} operations',
                    f'Work with {parent_singular} {child}',
                    f'Process {parent_singular} {child}',
                    f'Manage {parent_singular} {child}',
                    f'Handle {child} for specific {parent_singular}',
                    f'Perform {child} operations for {parent_singular}',
                    f'Execute {child} actions for {parent_singular}',
                    f'Manage {child} related to {parent_singular}'
                ]
                
                for pattern_text in nested_patterns:
                    patterns.append({
                        'type': f"NESTED_{parent.upper()}_{child.upper()}",
                        'pattern': pattern_text,
                        'category': 'ghl',
                        'operation_type': 'nested',
                        'handler_type': 'ghl',
                        'parent_resource': parent,
                        'child_resource': child,
                        'is_natural': True
                    })
            
            return patterns
            
        except Exception as e:
            logging.error(f"Error generating GHL patterns: {e}")
            return patterns
        
    def _query_to_pattern(self, query: str) -> List[Dict]:
        """Convert a GraphQL query to a natural language pattern."""
        # Remove GraphQL syntax
        query = re.sub(r'[{}\(\)]', '', query)
        query = re.sub(r'\s+', ' ', query).strip()
        
        # Convert to pattern tokens
        return [{'LOWER': word.lower()} for word in query.split()]

    def _mutation_to_pattern(self, mutation: str) -> List[Dict]:
        """Convert a GraphQL mutation to a natural language pattern."""
        # Remove GraphQL syntax
        mutation = re.sub(r'[{}\(\)]', '', mutation)
        mutation = re.sub(r'\s+', ' ', mutation).strip()
        
        # Convert to pattern tokens
        return [{'LOWER': word.lower()} for word in mutation.split()]

    def _endpoint_to_pattern(self, operation: Dict) -> List[Dict]:
        """Convert a REST endpoint to a natural language pattern."""
        method = operation['method'].lower()
        endpoint = operation['endpoint'].replace('/', ' ').strip()
        
        # Convert to pattern tokens
        pattern = [{'LOWER': method}]
        pattern.extend({'LOWER': word.lower()} for word in endpoint.split())
        return pattern

    def _operation_to_pattern(self, operation: Dict) -> List[Dict]:
        """Convert a GHL operation to a natural language pattern."""
        op_text = operation['operation'].replace('_', ' ').lower()
        
        # Convert to pattern tokens
        return [{'LOWER': word.lower()} for word in op_text.split()]

    def _setup_database(self):
        """Set up the SQLite database tables if they don't exist."""
        cursor = self.db_handler.conn.cursor()
        
        # Create patterns table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                pattern_type TEXT NOT NULL,
                pattern TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create intents table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS intents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
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
        
        # Create pattern mapping table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pattern_mapping (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                handler_name TEXT NOT NULL,
                pattern_type TEXT NOT NULL,
                pattern_value TEXT NOT NULL,
                similarity_score REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        self.db_handler.conn.commit()
        
    def _load_patterns(self):
        """Load existing patterns from the database."""
        try:
            cursor = self.db_handler.conn.cursor()
            # Load from handler_patterns and pattern_mapping tables instead
            cursor.execute('''
                SELECT hp.pattern_category as category, 
                       hp.pattern_type, 
                       hp.pattern_text as pattern
                FROM handler_patterns hp
                JOIN handlers h ON hp.handler_id = h.id
            ''')
            
            for row in cursor.fetchall():
                category, pattern_type, pattern = row
                try:
                    pattern_data = json.loads(pattern)
                except:
                    pattern_data = pattern  # If not JSON, use as is
                # Add default priority if missing
                if isinstance(pattern_data, dict) and 'priority' not in pattern_data:
                    pattern_data['priority'] = 1
                self.patterns[category].append({
                    'type': pattern_type,
                    'pattern': pattern_data,
                    'priority': 1 if not isinstance(pattern_data, dict) else pattern_data.get('priority', 1)
                })
        except sqlite3.OperationalError as e:
            if "no such table" in str(e):
                logging.warning("No existing patterns found in database - will process handlers to generate patterns")
            else:
                raise
        except Exception as e:
            logging.error(f"Error loading patterns: {str(e)}")
            raise

    def _generate_finder_patterns(self, finder_data: Dict) -> List[Dict]:
        """Generate patterns for Finder operations using collected data."""
        patterns = []
        
        if not finder_data:
            logging.warning("No Finder data available for pattern generation")
            return patterns
            
        try:
            # Generate command-based patterns
            for command in finder_data['commands']:
                # Get required params for this command
                required_params = []
                if isinstance(finder_data['required_params'], dict):
                    required_params = finder_data['required_params'].get(command, [])
                elif isinstance(finder_data['required_params'], set):
                    required_params = list(finder_data['required_params'])
                
                # Base command pattern with priority
                base_pattern = {
                    'type': command.upper(),
                    'category': 'finder',
                    'command': command,
                    'pattern': command.replace('_', ' '),
                    'required_params': required_params,
                    'priority': 1  # Add default priority
                }
                patterns.append(base_pattern)
                
                # Add natural language variations based on command type with priority
                nl_patterns = []
                if 'open' in command:
                    nl_patterns.extend([
                        {'pattern': 'Open the file at {path}', 'priority': 2},
                        {'pattern': 'Open {path}', 'priority': 1},
                        {'pattern': 'Show me the file {path}', 'priority': 2}
                    ])
                elif 'search' in command:
                    nl_patterns.extend([
                        'Search for files containing {search_keyword}',
                        'Find files with name {search_keyword}',
                        'Look for files matching {search_keyword}'
                    ])
                elif 'copy' in command:
                    nl_patterns.extend([
                        'Copy {path} to {destination}',
                        'Make a copy of {path} in {destination}',
                        'Duplicate {path} to {destination}',
                        'Create a copy of {path} in {destination}'
                    ])
                elif 'move' in command:
                    nl_patterns.extend([
                        'Move {path} to {destination}',
                        'Transfer {path} to {destination}',
                        'Relocate {path} to {destination}',
                        'Put {path} in {destination}'
                    ])
                elif 'delete' in command:
                    nl_patterns.extend([
                        'Delete {path}',
                        'Remove {path}',
                        'Move {path} to trash',
                        'Get rid of {path}'
                    ])
                elif 'create' in command:
                    nl_patterns.extend([
                        'Create a new folder named {new_name}',
                        'Make a new folder called {new_name}',
                        'Create directory {new_name}'
                    ])
                elif 'rename' in command:
                    nl_patterns.extend([
                        'Rename {path} to {new_name}',
                        'Change name of {path} to {new_name}',
                        'Give {path} the new name {new_name}'
                    ])
                
                # Add natural language patterns
                for nl_pattern in nl_patterns:
                    nl_dict = base_pattern.copy()
                    nl_dict['pattern'] = nl_pattern
                    nl_dict['is_natural'] = True
                    patterns.append(nl_dict)
            
            # Add error patterns
            for error in finder_data['error_messages']:
                error_pattern = {
                    'type': 'ERROR',
                    'category': 'finder',
                    'pattern': error,
                    'is_error': True
                }
                patterns.append(error_pattern)
            
            # Add operation patterns
            for operation in finder_data['operations']:
                operation_pattern = {
                    'type': 'OPERATION',
                    'category': 'finder',
                    'pattern': operation,
                    'is_operation': True
                }
                patterns.append(operation_pattern)
            
            return patterns
            
        except Exception as e:
            logging.error(f"Error generating Finder patterns: {e}")
            return patterns

    def _extract_set_values(self, node: ast.AST) -> Set[str]:
        """Extract values from a set literal in the AST."""
        values = set()
        try:
            if isinstance(node, ast.Assign):
                if isinstance(node.value, ast.Set):
                    for elt in node.value.elts:
                        if isinstance(elt, ast.Constant):
                            values.add(elt.value)
                        elif isinstance(elt, ast.Str):  # For older Python versions
                            values.add(elt.s)
                elif isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name) and node.value.func.id == 'set':
                    if node.value.args:
                        arg = node.value.args[0]
                        if isinstance(arg, ast.List):
                            for elt in arg.elts:
                                if isinstance(elt, ast.Constant):
                                    values.add(elt.value)
                                elif isinstance(elt, ast.Str):  # For older Python versions
                                    values.add(elt.s)
        except Exception as e:
            logging.error(f"Error extracting set values: {e}")
        return values

    def _collect_email_data(self, handler_file: str) -> Dict:
        """Collect data from email handler file."""
        try:
            logging.info("\n=== COLLECTING EMAIL HANDLER DATA ===")
            
            with open(handler_file, 'r') as f:
                content = f.read()
                
            # Use the existing email pattern extraction
            email_data = self._extract_email_patterns(content)
            
            # Log the collected data
            for category, items in email_data.items():
                if isinstance(items, (set, list)):
                    logging.info(f"\n{category}: {len(items)} items")
                    for item in sorted(items):
                        logging.info(f"  - {item}")
                elif isinstance(items, dict):
                    logging.info(f"\n{category}: {len(items)} items")
                    for key, value in sorted(items.items()):
                        logging.info(f"  - {key}: {value}")
                else:
                    logging.info(f"\n{category}: {items}")
            
            logging.info("\n=== EMAIL HANDLER DATA COLLECTION COMPLETE ===\n")
            return email_data
            
        except Exception as e:
            logging.error(f"Error collecting email data: {e}")
            return {}
            
    def _collect_finder_data(self, handler_file: str) -> Dict:
        """Collect data from finder handler file."""
        try:
            logging.info("\n=== COLLECTING FINDER HANDLER DATA ===")
            
            with open(handler_file, 'r') as f:
                content = f.read()
                
            # Parse the file
            tree = ast.parse(content)
            
            # Initialize data structure
            finder_data = {
                'commands': set(),
                'applescript_commands': set(),
                'required_params': {},  # Changed to dict to match email handler
                'optional_params': set(),
                'error_messages': set(),
                'success_messages': set(),
                'operations': set()
            }
            
            # Extract data using AST traversal
            for node in ast.walk(tree):
                # Extract command patterns from if/elif statements
                if isinstance(node, ast.If):
                    if isinstance(node.test, ast.Compare):
                        if isinstance(node.test.left, ast.Name) and node.test.left.id == "command":
                            if isinstance(node.test.comparators[0], ast.Str):
                                command = node.test.comparators[0].s
                                finder_data['commands'].add(command)
                                
                                # Extract required parameters and error conditions from error checks
                                required_params = set()
                                for check in ast.walk(node):
                                    if isinstance(check, ast.If):
                                        test_str = ast.unparse(check.test)
                                        if "not" in test_str:
                                            # Extract all variables being checked
                                            vars_checked = re.findall(r'not\s+(\w+)', test_str)
                                            required_params.update(vars_checked)
                                            finder_data['error_messages'].update(f"{var}_required" for var in vars_checked)
                                
                                if required_params:
                                    finder_data['required_params'][command] = list(required_params)
                                    
                                # Extract error and success messages
                                for check in ast.walk(node):
                                    if isinstance(check, ast.Return):
                                        if isinstance(check.value, ast.Dict):
                                            for key, value in zip(check.value.keys, check.value.values):
                                                if isinstance(key, ast.Str) and key.s == "error" and isinstance(value, ast.Str):
                                                    finder_data['error_messages'].add(value.s)
                                        elif isinstance(check.value, ast.Str):
                                            finder_data['success_messages'].add(check.value.s)
                
                # Extract AppleScript operations and patterns from string literals
                elif isinstance(node, ast.Str):
                    value = node.s.strip()
                    if 'tell application "Finder"' in value:
                        # Extract all operations
                        operations = re.findall(r'(?:^|\n)\s*((?:set|make|move|delete|open|get|return|repeat)\s+[^\n]+)', value)
                        finder_data['applescript_commands'].update(op.strip() for op in operations)
                        
                        # Extract file operations
                        file_ops = re.findall(r'(?:open|delete|move|duplicate|make|set)\s+(?:POSIX file|folder|disk|alias file)', value)
                        finder_data['operations'].update(op.strip() for op in file_ops)
                        
                        # Extract success messages
                        success_msgs = re.findall(r'return\s+"([^"]+)"', value)
                        finder_data['success_messages'].update(success_msgs)
                        
                        # Extract error messages
                        error_msgs = re.findall(r'return\s+{"error":\s*"([^"]+)"}', value)
                        finder_data['error_messages'].update(error_msgs)
                
                # Extract optional parameters from function definition
                elif isinstance(node, ast.FunctionDef):
                    if node.name == 'handle_apple_finder_intent':
                        # Get all parameters except self and command
                        for arg in node.args.args:
                            if arg.arg not in ['self', 'command']:
                                finder_data['optional_params'].add(arg.arg)
            
            # Log the collected data
            for category, items in finder_data.items():
                if isinstance(items, (set, list)):
                    logging.info(f"\n{category}: {len(items)} items")
                    for item in sorted(items):
                        logging.info(f"  - {item}")
                elif isinstance(items, dict):
                    logging.info(f"\n{category}: {len(items)} items")
                    for key, value in sorted(items.items()):
                        logging.info(f"  - {key}: {value}")
                else:
                    logging.info(f"\n{category}: {items}")
            
            logging.info("\n=== FINDER HANDLER DATA COLLECTION COMPLETE ===\n")
            return finder_data
            
        except Exception as e:
            logging.error(f"Error collecting finder data: {e}")
            return {}

    def _generate_email_patterns(self, email_data: Dict) -> List[Dict]:
        """Generate patterns for email operations using collected data."""
        patterns = []
        
        if not email_data:
            logging.warning("No email data available for pattern generation")
            return patterns
            
        try:
            # Initialize missing fields if needed
            if 'error_messages' not in email_data:
                email_data['error_messages'] = set()
            if 'success_messages' not in email_data:
                email_data['success_messages'] = set()
            if 'response_messages' not in email_data:
                email_data['response_messages'] = set()
                
            # Add response messages to success messages
            email_data['success_messages'].update(email_data.get('response_messages', set()))
            
            # Generate command-based patterns
            for command in email_data['commands']:
                # Base command pattern
                base_pattern = {
                    'type': command.upper(),
                    'category': 'email',
                    'command': command,
                    'pattern': command.replace('_', ' '),
                    'required_params': list(email_data['required_params']) if isinstance(email_data['required_params'], set) else []
                }
                patterns.append(base_pattern)
                
                # Add natural language variations based on command type
                nl_patterns = []
                if 'send' in command:
                    nl_patterns.extend([
                        'Send an email to {recipient}',
                        'Send email with subject {subject}',
                        'Send a message to {recipient}',
                        'Compose and send an email to {recipient}',
                        'Write an email to {recipient}',
                        'Draft an email to {recipient}'
                    ])
                elif 'read' in command:
                    nl_patterns.extend([
                        'Read my emails',
                        'Check my inbox',
                        'Show me my emails',
                        'Display my messages',
                        'Show unread emails',
                        'Check for new emails'
                    ])
                elif 'delete' in command:
                    nl_patterns.extend([
                        'Delete the email',
                        'Remove the email',
                        'Delete message with subject {subject}',
                        'Remove email from {mailbox}',
                        'Delete emails matching {search_keyword}',
                        'Remove messages containing {content}'
                    ])
                elif 'archive' in command:
                    nl_patterns.extend([
                        'Archive the email',
                        'Move email to archive',
                        'Archive message with subject {subject}',
                        'Archive emails from {mailbox}',
                        'Archive emails matching {search_keyword}'
                    ])
                elif 'flag' in command:
                    nl_patterns.extend([
                        'Flag the email',
                        'Mark email as important',
                        'Flag message with subject {subject}',
                        'Mark emails as flagged',
                        'Flag emails matching {search_keyword}'
                    ])
                elif 'mark' in command:
                    nl_patterns.extend([
                        'Mark as read',
                        'Mark as unread',
                        'Mark email as read',
                        'Mark message as unread',
                        'Mark emails matching {search_keyword} as read'
                    ])
                elif 'move' in command:
                    nl_patterns.extend([
                        'Move email to {mailbox}',
                        'Move message to folder {mailbox}',
                        'Move emails matching {search_keyword} to {mailbox}',
                        'Transfer email to {mailbox}',
                        'Relocate message to {mailbox}'
                    ])
                elif 'search' in command:
                    nl_patterns.extend([
                        'Search for emails containing {search_keyword}',
                        'Find emails with subject {subject}',
                        'Search messages in {mailbox}',
                        'Look for emails about {search_keyword}',
                        'Find messages matching {search_keyword}'
                    ])
                
                # Add natural language patterns
                for nl_pattern in nl_patterns:
                    nl_dict = base_pattern.copy()
                    nl_dict['pattern'] = nl_pattern
                    nl_dict['is_natural'] = True
                    patterns.append(nl_dict)
            
            # Add error patterns
            for error in email_data['error_messages']:
                error_pattern = {
                    'type': 'ERROR',
                    'category': 'email',
                    'pattern': error,
                    'is_error': True
                }
                patterns.append(error_pattern)
            
            # Add success patterns
            for success in email_data['success_messages']:
                success_pattern = {
                    'type': 'SUCCESS',
                    'category': 'email',
                    'pattern': success,
                    'is_success': True
                }
                patterns.append(success_pattern)
            
            return patterns
            
        except Exception as e:
            logging.error(f"Error generating email patterns: {e}")
            return patterns

    def _match_patterns_to_intents(self, pattern_text: str, intents: List[Tuple]) -> List[Dict]:
        """Match a pattern against intents using Jaccard similarity and category-specific handling."""
        try:
            matches = []
            best_score = 0
            best_match = None
            
            # Determine category-specific threshold
            handler_type = self._get_handler_type(pattern_text)
            similarity_threshold = 0.3 if handler_type == 'finder' else 0.5
            
            # First try exact matches for command patterns
            if 'COMMAND' in pattern_text.upper():
                for intent in intents:
                    if not isinstance(intent, dict) or 'intent' not in intent:
                        continue
                    
                    # Try exact command match first
                    if any(example.lower() == pattern_text.lower() for example in intent.get('examples', [])):
                        best_match = {
                            'intent': intent['intent'],
                            'score': 1.0,
                            'category': intent[2]
                        }
                        logging.info(f"Found exact match with intent: {intent['intent']}")
                        matches.append(best_match)
                        break

            # If no exact match, proceed with similarity matching
            if not best_match:
                for intent in intents:
                    similarity = self._calculate_similarity(pattern_text, intent[1])
                    
                    # Apply pattern type weights
                    if 'COMMAND' in pattern_text.upper():
                        similarity *= 1.2  # Boost command patterns
                    elif 'FUNCTION' in pattern_text.upper():
                        similarity *= 1.1  # Boost function patterns
                    
                    # Apply category-specific weights
                    if handler_type == intent[2]:
                        similarity *= 1.15  # Boost patterns from same category
                    
                    if similarity > best_score:
                        best_score = similarity
                        best_match = intent
                    
                    # Add match if score is above threshold
                    if similarity >= similarity_threshold:
                        matches.append({
                            'intent': intent[1],
                            'score': similarity,
                            'category': intent[2]
                        })
            
            return sorted(matches, key=lambda x: x['score'], reverse=True)[:3]  # Return top 3 matches
            
        except Exception as e:
            logging.error(f"Error matching pattern '{pattern_text}': {str(e)}")
            return []

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two texts, handling empty vectors."""
        try:
            # Convert texts to spaCy docs
            doc1 = self.nlp(str(text1))
            doc2 = self.nlp(str(text2))
            
            # Check if either doc has vector representation
            if not doc1.has_vector or not doc2.has_vector:
                return 0.0
                
            # Calculate similarity
            similarity = doc1.similarity(doc2)
            
            # Boost score for exact command matches
            if any(word.text in doc2.text for word in doc1):
                similarity += 0.2
            
            # Cap at 1.0
            return min(similarity, 1.0)
            
        except Exception as e:
            logging.error(f"Error calculating similarity: {e}")
            return 0.0

    def _collect_calendar_data(self, handler_file: str) -> Dict:
        """Collect calendar-specific data from handler code."""
        data = {
            'commands': set(),
            'applescript_commands': set(),
            'required_params': {},
            'optional_params': set(),
            'error_messages': set(),
            'success_messages': set(),
            'operations': set()
        }
        
        try:
            with open(handler_file, 'r') as f:
                content = f.read()
                
            tree = ast.parse(content)
            
            # Extract patterns from AST
            for node in ast.walk(tree):
                # Extract command patterns from if/elif statements
                if isinstance(node, ast.If):
                    if isinstance(node.test, ast.Compare):
                        if isinstance(node.test.left, ast.Name) and node.test.left.id == "command":
                            if isinstance(node.test.comparators[0], ast.Str):
                                command = node.test.comparators[0].s
                                data['commands'].add(command)
                                data['required_params'][command] = set()
                                
                                # Extract required parameters and error conditions from error checks
                                for check in ast.walk(node):
                                    if isinstance(check, ast.If):
                                        test_str = ast.unparse(check.test)
                                        if "not" in test_str:
                                            # Extract parameters from conditions like "not event_details or 'title' not in event_details"
                                            params = re.findall(r'"(\w+)"\s+not\s+in', test_str)
                                            data['required_params'][command].update(params)
                                    
                                    # Extract error and success messages
                                    if isinstance(check, ast.Return):
                                        if isinstance(check.value, ast.Str):
                                            msg = check.value.s
                                            if "required" in msg.lower() or "Error" in msg:
                                                data['error_messages'].add(msg)
                                            else:
                                                data['success_messages'].add(msg)
                
                # Extract AppleScript operations and patterns from string literals
                elif isinstance(node, ast.Str):
                    value = node.s.strip()
                    if 'tell application "Calendar"' in value or 'tell application "Microsoft Outlook"' in value:
                        # Extract operations
                        operations = [
                            'make new event',
                            'delete event',
                            'set summary',
                            'set subject',
                            'set start date',
                            'set start time',
                            'set end date',
                            'set duration'
                        ]
                        for op in operations:
                            if op.lower() in value.lower():
                                data['operations'].add(op)
                                
                        # Extract AppleScript commands
                        script_commands = re.findall(r'(?:^|\n)\s*((?:set|make|delete|get|return|repeat)[^\n]+)', value)
                        data['applescript_commands'].update(cmd.strip() for cmd in script_commands)
                
                # Extract optional parameters from function definition
                elif isinstance(node, ast.FunctionDef):
                    if node.name in ["handle_apple_calendar", "handle_outlook_calendar", "handle_calendar_intent"]:
                        for arg in node.args.args:
                            if arg.arg not in ['self', 'command', 'app']:
                                if arg.arg not in [param for params in data['required_params'].values() for param in params]:
                                    data['optional_params'].add(arg.arg)
            
            logging.info("\n=== COLLECTING CALENDAR HANDLER DATA ===\n")
            for category, items in data.items():
                if isinstance(items, (set, list)):
                    logging.info(f"{category}: {len(items)} items")
                    for item in sorted(items):
                        logging.info(f"  - {item}")
                elif isinstance(items, dict):
                    logging.info(f"{category}: {len(items)} items")
                    for key, value in sorted(items.items()):
                        logging.info(f"  - {key}: {value}")
            logging.info("\n=== CALENDAR HANDLER DATA COLLECTION COMPLETE ===\n")
            
            return data
            
        except Exception as e:
            logging.error(f"Error collecting calendar data: {e}")
            return data

    def _generate_calendar_patterns(self, calendar_data: Dict) -> List[Dict]:
        """Generate natural language patterns for calendar operations."""
        patterns = []
        
        try:
            # Only generate patterns for actual commands
            for command in calendar_data['commands']:
                pattern = {
                    'type': command.upper(),
                    'pattern': self._command_to_pattern(command),
                    'required_params': list(calendar_data['required_params'].get(command, [])),
                    'optional_params': list(calendar_data['optional_params']),
                    'handler_type': 'calendar'
                }
                patterns.append(pattern)

                # Add natural language variations based on command type
                nl_patterns = []
                if 'create' in command:
                    nl_patterns.extend([
                        'Create a new calendar event titled {title}',
                        'Schedule an event for {start_time}',
                        'Add event {title} to calendar',
                        'Create meeting titled {title}'
                    ])
                elif 'delete' in command:
                    nl_patterns.extend([
                        'Delete event {title}',
                        'Remove event {title} from calendar',
                        'Cancel the event {title}',
                        'Delete meeting {title}'
                    ])
                elif 'list' in command:
                    nl_patterns.extend([
                        'Show all calendar events',
                        'List my events',
                        'Display calendar events',
                        'Show my schedule'
                    ])
                elif 'update' in command:
                    nl_patterns.extend([
                        'Update event {title}',
                        'Change event {title} to {new_title}',
                        'Modify event {title}',
                        'Rename event {title}'
                    ])

                # Add natural language patterns
                for nl_pattern in nl_patterns:
                    nl_dict = pattern.copy()
                    nl_dict['pattern'] = nl_pattern
                    nl_dict['is_natural'] = True
                    patterns.append(nl_dict)
            
            logging.info("Generating patterns...")
            logging.info(f"Generated {len(patterns)} patterns")
            logging.info("Pattern Types:")
            pattern_types = defaultdict(int)
            for p in patterns:
                pattern_types[p.get('type', 'unknown')] += 1
            for ptype, count in pattern_types.items():
                logging.info(f"  - {ptype}: {count}")
            
            return patterns
            
        except Exception as e:
            logging.error(f"Error generating calendar patterns: {e}")
            return patterns

    def _collect_<healthcare>_data(self, handler_file: str) -> Dict:
        """Collect data from <healthcare-platform> handler file and related modules."""
        try:
            logging.info("\n=== COLLECTING HEALTHIE HANDLER DATA ===")
            
            <healthcare>_data = {
                'queries': set(),
                'additional_queries': set(),  # For queries from <healthcare>_query.py
                'mutations': set(),
                'fields': set(),
                'nested_fields': set(),  # For nested field structures
                'operations': set(),
                'base_urls': set(),
                'error_messages': set(),
                'success_messages': set()
            }
            
            # First collect from handler_<healthcare>.py
            with open(handler_file, 'r') as f:
                content = f.read()
                
            # Parse the content
            tree = ast.parse(content)
            
            # Extract patterns from AST
            for node in ast.walk(tree):
                # Extract queries from QUERY_NAMES list
                if isinstance(node, ast.Assign):
                    if isinstance(node.targets[0], ast.Name) and node.targets[0].id == 'QUERY_NAMES':
                        if isinstance(node.value, ast.List):
                            for elt in node.value.elts:
                                if isinstance(elt, ast.Str):
                                    <healthcare>_data['queries'].add(elt.s)
                                    <healthcare>_data['operations'].add(f"query_{elt.s}")
                
                # Extract mutations from MUTATION_OPERATIONS list
                if isinstance(node, ast.Assign):
                    if isinstance(node.targets[0], ast.Name) and node.targets[0].id == 'MUTATION_OPERATIONS':
                        if isinstance(node.value, ast.List):
                            for elt in node.value.elts:
                                if isinstance(elt, ast.Str):
                                    <healthcare>_data['mutations'].add(elt.s)
                                    <healthcare>_data['operations'].add(f"mutation_{elt.s}")
                
                # Extract fields from DEFAULT_FIELDS dictionary
                if isinstance(node, ast.Assign):
                    if isinstance(node.targets[0], ast.Name) and node.targets[0].id == 'DEFAULT_FIELDS':
                        if isinstance(node.value, ast.Dict):
                            for key in node.value.keys:
                                if isinstance(key, ast.Str):
                                    <healthcare>_data['fields'].add(key.s)
                
                # Extract base URLs
                if isinstance(node, ast.Str):
                    if 'api.get<healthcare>.com' in node.s:
                        <healthcare>_data['base_urls'].add(node.s)
                
                # Extract error messages from error handling
                if isinstance(node, ast.Raise):
                    if isinstance(node.exc, ast.Call):
                        if isinstance(node.exc.args[0], ast.Str):
                            <healthcare>_data['error_messages'].add(node.exc.args[0].s)

            # Now collect additional queries from <healthcare>_query.py
            <healthcare>_query_path = os.path.join(os.path.dirname(handler_file), '..', '<healthcare-platform>', '<healthcare>_query.py')
            if os.path.exists(<healthcare>_query_path):
                with open(<healthcare>_query_path, 'r') as f:
                    query_content = f.read()
                query_tree = ast.parse(query_content)
                
                for node in ast.walk(query_tree):
                    if isinstance(node, ast.Assign):
                        if isinstance(node.targets[0], ast.Name) and node.targets[0].id == 'QUERY_NAMES':
                            if isinstance(node.value, ast.List):
                                for elt in node.value.elts:
                                    if isinstance(elt, ast.Str):
                                        <healthcare>_data['additional_queries'].add(elt.s)

            # Collect all fields including nested ones from <healthcare>_fields.py
            <healthcare>_fields_path = os.path.join(os.path.dirname(handler_file), '..', '<healthcare-platform>', '<healthcare>_fields.py')
            if os.path.exists(<healthcare>_fields_path):
                with open(<healthcare>_fields_path, 'r') as f:
                    fields_content = f.read()
                fields_tree = ast.parse(fields_content)
                
                def extract_nested_fields(field_str):
                    fields = set()
                    # Split by spaces and handle nested structures
                    parts = field_str.split()
                    for part in parts:
                        # Handle nested fields in curly braces
                        if '{' in part:
                            nested = re.findall(r'{([^}]+)}', part)
                            for n in nested:
                                fields.update(extract_nested_fields(n))
                        # Add base field
                        clean_field = re.sub(r'[{}\s]', '', part)
                        if clean_field:
                            fields.add(clean_field)
                    return fields

                for node in ast.walk(fields_tree):
                    if isinstance(node, ast.Assign):
                        if isinstance(node.targets[0], ast.Name) and node.targets[0].id == 'DEFAULT_FIELDS':
                            if isinstance(node.value, ast.Dict):
                                for key, value in zip(node.value.keys, node.value.values):
                                    if isinstance(key, ast.Str) and isinstance(value, ast.Str):
                                        # Add base field
                                        <healthcare>_data['fields'].add(key.s)
                                        # Extract and add nested fields
                                        nested = extract_nested_fields(value.s)
                                        <healthcare>_data['nested_fields'].update(nested)
            
            # Log the collected data
            logging.info("\n==================================================")
            logging.info("HEALTHIE DATA")
            logging.info("==================================================\n")
            
            # Log core endpoints (from handler_<healthcare>.py)
            logging.info("CORE ENDPOINTS:")
            logging.info(f"Queries: {len(<healthcare>_data['queries'])}")
            for query in sorted(<healthcare>_data['queries']):
                logging.info(f"  {query}")
            
            logging.info(f"\nMutations: {len(<healthcare>_data['mutations'])}")
            for mutation in sorted(<healthcare>_data['mutations']):
                logging.info(f"  {mutation}")
            
            # Log additional queries (from <healthcare>_query.py)
            logging.info("\nADDITIONAL QUERIES:")
            logging.info(f"Total: {len(<healthcare>_data['additional_queries'])}")
            for query in sorted(<healthcare>_data['additional_queries']):
                logging.info(f"  {query}")
            
            # Log fields
            logging.info("\nFIELDS:")
            logging.info(f"Base Fields: {len(<healthcare>_data['fields'])}")
            for field in sorted(<healthcare>_data['fields']):
                logging.info(f"  {field}")
            
            logging.info(f"\nNested Fields: {len(<healthcare>_data['nested_fields'])}")
            for field in sorted(<healthcare>_data['nested_fields']):
                logging.info(f"  {field}")
            
            # Log summary
            logging.info("\n=== HEALTHIE DATA SUMMARY ===")
            logging.info(f"Core Queries from handler_<healthcare>.py: {len(<healthcare>_data['queries'])}")
            logging.info(f"Additional Queries from <healthcare>_query.py: {len(<healthcare>_data['additional_queries'])}")
            logging.info(f"Mutations from handler_<healthcare>.py: {len(<healthcare>_data['mutations'])}")
            logging.info(f"Total Core Endpoints: {len(<healthcare>_data['queries']) + len(<healthcare>_data['mutations'])}")
            logging.info(f"Base Fields: {len(<healthcare>_data['fields'])}")
            logging.info(f"Nested Fields: {len(<healthcare>_data['nested_fields'])}")
            logging.info(f"Total Fields: {len(<healthcare>_data['fields']) + len(<healthcare>_data['nested_fields'])}")
            logging.info("=== END HEALTHIE DATA SUMMARY ===\n")
            
            return <healthcare>_data
            
        except Exception as e:
            logging.error(f"Error collecting <healthcare-platform> data: {e}")
            return {}

    def _collect_ghl_data(self, handler_file: str) -> Dict:
        """Collect data from GHL handler file."""
        try:
            logging.info("\n=== COLLECTING GHL HANDLER DATA ===")
            
            ghl_data = {
                'endpoints': set(),
                'operations': set(),
                'methods': set(),
                'base_urls': set(),
                'error_messages': set(),
                'success_messages': set(),
                'parameters': set(),
                'mutations': set(),
                'queries': set(),
                'graphql_queries': set(),
                'graphql_mutations': set(),
                'categories': {
                    'contact': {'mutations': set(), 'queries': set(), 'operations': set()},
                    'tag': {'mutations': set(), 'queries': set(), 'operations': set()},
                    'pipeline': {'mutations': set(), 'queries': set(), 'operations': set()},
                    'opportunity': {'mutations': set(), 'queries': set(), 'operations': set()},
                    'task': {'mutations': set(), 'queries': set(), 'operations': set()},
                    'appointment': {'mutations': set(), 'queries': set(), 'operations': set()},
                    'form': {'mutations': set(), 'queries': set(), 'operations': set()},
                    'email': {'mutations': set(), 'queries': set(), 'operations': set()},
                    'utility': {'mutations': set(), 'queries': set(), 'operations': set()}
                }
            }
            
            with open(handler_file, 'r') as f:
                content = f.read()
                
            tree = ast.parse(content)
            
            # First pass: collect all possible actions from if/elif conditions
            for node in ast.walk(tree):
                if isinstance(node, ast.If):
                    if isinstance(node.test, ast.Compare):
                        if isinstance(node.test.left, ast.Name) and node.test.left.id == "action":
                            if isinstance(node.test.comparators[0], (ast.Str, ast.Constant)):
                                action = node.test.comparators[0].s if isinstance(node.test.comparators[0], ast.Str) else node.test.comparators[0].value
                                if isinstance(action, str):
                                    # Add to operations
                                    ghl_data['operations'].add(action)
                                    
                                    # Categorize action
                                    if any(action.startswith(prefix) for prefix in ('create_', 'update_', 'delete_')):
                                        ghl_data['mutations'].add(action)
                                    else:
                                        # Add opportunity-specific queries
                                        if 'opportunity' in action:
                                            if action in ['get_opportunity', 'list_opportunities', 'search_opportunities']:
                                                ghl_data['queries'].add(action)
                                        else:
                                            ghl_data['queries'].add(action)
                                    
                                    # Extract endpoint from the request call
                                    for child in ast.walk(node):
                                        if isinstance(child, ast.Call):
                                            if isinstance(child.func, ast.Attribute):
                                                if child.func.attr in ['get', 'post', 'put', 'delete']:
                                                    method = child.func.attr.upper()
                                                    ghl_data['methods'].add(method)
                                                    
                                                    # Extract URL and format string components
                                                    for arg in child.args:
                                                        if isinstance(arg, (ast.Str, ast.Constant)):
                                                            url = arg.s if isinstance(arg, ast.Str) else arg.value
                                                            if isinstance(url, str):
                                                                if 'BASE_URL' in url:
                                                                    url = url.replace('{BASE_URL}', 'https://rest.gohighlevel.com/v1')
                                                                # Skip incomplete endpoints
                                                                if not any(param in url for param in ['/contactId', '/email', '/phone', '/taskId']):
                                                                    # Clean up analytics endpoint
                                                                    if '/analytics' in url and '{type}' not in url:
                                                                        url = url + '/{type}'
                                                                    endpoint = f"{method} {url}"
                                                                    ghl_data['endpoints'].add(endpoint)
                                                        elif isinstance(arg, ast.JoinedStr):  # Handle f-strings
                                                            url_parts = []
                                                            for value in arg.values:
                                                                if isinstance(value, ast.Str):
                                                                    url_parts.append(value.s)
                                                                elif isinstance(value, ast.FormattedValue):
                                                                    if isinstance(value.value, ast.Name):
                                                                        url_parts.append(f"{{{value.value.id}}}")
                                                            url = ''.join(url_parts)
                                                            if 'BASE_URL' in url:
                                                                url = url.replace('{BASE_URL}', 'https://rest.gohighlevel.com/v1')
                                                            endpoint = f"{method} {url}"
                                                            ghl_data['endpoints'].add(endpoint)
                                                        elif isinstance(arg, ast.BinOp):  # Handle string concatenation
                                                            if isinstance(arg.left, ast.Str) and isinstance(arg.right, ast.Str):
                                                                url = arg.left.s + arg.right.s
                                                                if 'BASE_URL' in url:
                                                                    url = url.replace('{BASE_URL}', 'https://rest.gohighlevel.com/v1')
                                                                endpoint = f"{method} {url}"
                                                                ghl_data['endpoints'].add(endpoint)
                                                    
                                                    # Extract request body for GraphQL operations
                                                    if child.keywords:
                                                        for keyword in child.keywords:
                                                            if keyword.arg == 'json' and isinstance(keyword.value, (ast.Dict, ast.Call)):
                                                                for key_node in ast.walk(keyword.value):
                                                                    if isinstance(key_node, ast.Str):
                                                                        if 'query' in key_node.s.lower():
                                                                            ghl_data['graphql_queries'].add(key_node.s)
                                                                        elif 'mutation' in key_node.s.lower():
                                                                            ghl_data['graphql_mutations'].add(key_node.s)
                                    
                                    # Categorize by type
                                    category = None
                                    if 'contact' in action:
                                        category = 'contact'
                                    elif 'tag' in action:
                                        category = 'tag'
                                    elif 'pipeline' in action:
                                        category = 'pipeline'
                                    elif 'opportunity' in action:
                                        category = 'opportunity'
                                        # Add specific opportunity queries if not already present
                                        if action == 'get_opportunity':
                                            ghl_data['queries'].add('get_opportunity')
                                            ghl_data['endpoints'].add('GET https://rest.gohighlevel.com/v1/opportunities/{id}')
                                        elif action == 'list_opportunities':
                                            ghl_data['queries'].add('list_opportunities')
                                            ghl_data['endpoints'].add('GET https://rest.gohighlevel.com/v1/opportunities')
                                        elif action == 'search_opportunities':
                                            ghl_data['queries'].add('search_opportunities')
                                            ghl_data['endpoints'].add('GET https://rest.gohighlevel.com/v1/opportunities/search')
                                    elif 'task' in action:
                                        category = 'task'
                                    elif 'appointment' in action:
                                        category = 'appointment'
                                    elif 'form' in action:
                                        category = 'form'
                                    elif 'email' in action or 'campaign' in action:
                                        category = 'email'
                                    else:
                                        category = 'utility'
                                    
                                    if category:
                                        ghl_data['categories'][category]['operations'].add(action)
                                        if any(action.startswith(prefix) for prefix in ('create_', 'update_', 'delete_')):
                                            ghl_data['categories'][category]['mutations'].add(action)
                                        else:
                                            ghl_data['categories'][category]['queries'].add(action)
                                    
                                    # Handle incomplete endpoints by ensuring proper formatting
                                    if endpoint and any(param in endpoint for param in ['{contactId}', '{email}', '{phone}', '{taskId}', '{analytics_type}']):
                                        if 'analytics' in endpoint:
                                            endpoint = endpoint.replace('{analytics_type}', 'general')  # Default analytics type
                                        ghl_data['endpoints'].add(endpoint)
            
            # Extract parameters from function arguments
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    for arg in node.args.args:
                        if arg.arg not in ['self', 'action']:
                            ghl_data['parameters'].add(arg.arg)
                
                # Extract error messages
                elif isinstance(node, ast.Return):
                    if isinstance(node.value, ast.Dict):
                        for key, value in zip(node.value.keys, node.value.values):
                            if isinstance(key, ast.Str) and key.s == 'error':
                                if isinstance(value, ast.Str):
                                    ghl_data['error_messages'].add(value.s)
            
            # Add base URLs
            ghl_data['base_urls'].add('https://rest.gohighlevel.com/v1')
            
            # Log the collected data
            logging.info("\n=== GHL HANDLER DATA SUMMARY ===")
            
            logging.info(f"\nTotal Mutations: {len(ghl_data['mutations'])}")
            logging.info(f"Total Queries: {len(ghl_data['queries'])}")
            logging.info(f"Total GraphQL Mutations: {len(ghl_data['graphql_mutations'])}")
            logging.info(f"Total GraphQL Queries: {len(ghl_data['graphql_queries'])}")
            logging.info(f"Total Endpoints: {len(ghl_data['endpoints'])}")
            
            logging.info("\nEndpoints by Category:")
            for category, data in ghl_data['categories'].items():
                if data['operations']:
                    logging.info(f"\n{category.upper()}:")
                    logging.info(f"  Mutations ({len(data['mutations'])}):")
                    for mutation in sorted(data['mutations']):
                        logging.info(f"    - {mutation}")
                    logging.info(f"  Queries ({len(data['queries'])}):")
                    for query in sorted(data['queries']):
                        logging.info(f"    - {query}")
            
            logging.info("\nEndpoints:")
            for endpoint in sorted(ghl_data['endpoints']):
                logging.info(f"  - {endpoint}")
            
            logging.info("\nHTTP Methods:")
            for method in sorted(ghl_data['methods']):
                logging.info(f"  - {method}")
            
            logging.info("\nParameters:")
            for param in sorted(ghl_data['parameters']):
                logging.info(f"  - {param}")
            
            logging.info("\nError Messages:")
            for msg in sorted(ghl_data['error_messages']):
                logging.info(f"  - {msg}")
            
            logging.info("\n=== GHL HANDLER DATA COLLECTION COMPLETE ===\n")
            return ghl_data
            
        except Exception as e:
            logging.error(f"Error collecting GHL data: {e}")
            return {}

    def _map_ghl_patterns_to_intents(self, patterns: Dict[str, Set[str]]) -> Dict[str, List[Dict]]:
        """Map GHL patterns to intents using spaCy similarity with pre-defined patterns."""
        mappings = {}
        
        try:
            # Get all intents from database
            cursor = self.db_handler.conn.cursor()
            cursor.execute('''
                SELECT i.id, i.name, i.category, e.text 
                FROM intents i 
                LEFT JOIN examples e ON i.id = e.intent_id
            ''')
            intent_data = cursor.fetchall()
            
            # Group by intent
            intents = {}
            for row in intent_data:
                intent_id, intent_name, category, example = row
                if intent_id not in intents:
                    intents[intent_id] = {
                        'name': intent_name,
                        'category': category,
                        'examples': []
                    }
                if example:
                    intents[intent_id]['examples'].append(example)

            # Get pre-defined GHL patterns
            predefined_patterns = self.loaded_patterns.get('ghl', [])
            
            # Create a mapping of predefined patterns to intents
            pattern_to_intent = {}
            for pattern in predefined_patterns:
                if 'label' in pattern:
                    pattern_text = ' '.join([token.get('LOWER', '') for token in pattern['pattern']])
                    pattern_to_intent[pattern_text] = pattern['label']

            # Process each handler pattern
            for pattern_type, pattern_set in patterns.items():
                for pattern in pattern_set:
                    pattern_str = str(pattern)
                    pattern_doc = self.nlp(pattern_str)
                    best_match = None
                    best_score = 0
                    
                    # First try to match with predefined patterns
                    for pred_pattern, intent_label in pattern_to_intent.items():
                        pred_doc = self.nlp(pred_pattern)
                        score = pattern_doc.similarity(pred_doc)
                        
                        # Higher weight for predefined pattern matches
                        score = score * 1.2  # 20% boost for predefined patterns
                        
                        if score > best_score and score > 0.7:
                            best_score = score
                            # Find the intent ID for this label
                            for intent_id, intent_info in intents.items():
                                if intent_info['name'] == intent_label:
                                    best_match = intent_id
                                    break
                    
                    # If no good match with predefined patterns, try direct intent matching
                    if not best_match:
                        for intent_id, intent_info in intents.items():
                            # Check intent name similarity
                            intent_doc = self.nlp(intent_info['name'])
                            score = pattern_doc.similarity(intent_doc)
                            
                            # Check examples similarity
                            for example in intent_info['examples']:
                                example_doc = self.nlp(example)
                                example_score = pattern_doc.similarity(example_doc)
                                score = max(score, example_score)
                            
                            if score > best_score and score > 0.7:
                                best_score = score
                                best_match = intent_id
                    
                    # Store the mapping
                    if best_match:
                        if pattern_type not in mappings:
                            mappings[pattern_type] = []
                        mappings[pattern_type].append({
                            'pattern': pattern_str,
                            'intent_id': best_match,
                            'score': best_score,
                            'intent_name': intents[best_match]['name']
                        })
            
            return mappings

        except Exception as e:
            logging.error(f"Error mapping GHL patterns to intents: {e}")
            return {}

    def _collect_wolfram_data(self, handler_file: str) -> Dict:
        """Collect data from Wolfram handler file."""
        try:
            logging.warning("\n=== COLLECTING WOLFRAM DATA ===")
            
            # Import test data from test_wolfram_pods
            test_file = os.path.join(os.path.dirname(handler_file), 'test_wolfram_pods.py')
            if os.path.exists(test_file):
                # Add handler directory to path temporarily
                sys.path.insert(0, os.path.dirname(handler_file))
                from test_wolfram_pods import TEST_QUERIES, collect_pod_types
                # Remove the path after import
                sys.path.pop(0)
                
                # Initialize wolfram data structure
                wolfram_data = {
                    'query_types': defaultdict(list),
                    'operations': set(),
                    'pod_types': set(),
                    'special_functions': set()
                }
                
                # Read the Wolfram handler file for operations and functions
                with open(handler_file, 'r') as f:
                    content = f.read()
                
                # Extract operations (function definitions)
                function_pattern = r'def\s+(\w+)\s*\((.*?)\):'
                for match in re.finditer(function_pattern, content):
                    func_name = match.group(1)
                    if 'wolfram' in func_name.lower():
                        wolfram_data['operations'].add(func_name)
                
                # Extract pod types and handling
                pod_pattern = r'(?:\'|\")([^\'\"]+?)(?:\'|\"):\s*pod'
                pod_matches = re.finditer(pod_pattern, content)
                for match in pod_matches:
                    wolfram_data['pod_types'].add(match.group(1))
                
                # Extract special Wolfram functions
                special_pattern = r'(?:def\s+handle_(\w+)_pod|process_(\w+)_pod)'
                for match in re.finditer(special_pattern, content):
                    func_type = match.group(1) or match.group(2)
                    if func_type:
                        wolfram_data['special_functions'].add(func_type)
                
                # Process TEST_QUERIES to organize by category
                current_category = None
                for query in TEST_QUERIES:
                    if isinstance(query, str):  # Skip empty strings and comments
                        if query.strip().startswith('#'):
                            # Extract category name from comment
                            current_category = query.strip('# ').lower()
                        elif current_category and query.strip():
                            # Add query to current category
                            wolfram_data['query_types'][current_category].append(query.strip())
                
                # Try to collect pod types using the collect_pod_types function
                try:
                    pod_types = collect_pod_types()
                    if pod_types:
                        for pod_title, queries in pod_types.items():
                            wolfram_data['pod_types'].add(pod_title)
                except Exception as e:
                    logging.warning(f"Could not collect pod types: {e}")
                
                # Print summary
                logging.warning("\nWolfram Data Summary:")
                for category, queries in wolfram_data['query_types'].items():
                    logging.warning(f"\n{category}: {len(queries)} queries")
                    for query in queries:
                        logging.warning(f"  - {query}")
                
                logging.warning(f"\nOperations found: {len(wolfram_data['operations'])}")
                for op in wolfram_data['operations']:
                    logging.warning(f"  - {op}")
                
                logging.warning(f"\nPod Types found: {len(wolfram_data['pod_types'])}")
                for pod in wolfram_data['pod_types']:
                    logging.warning(f"  - {pod}")
                
                logging.warning(f"\nSpecial Functions found: {len(wolfram_data['special_functions'])}")
                for func in wolfram_data['special_functions']:
                    logging.warning(f"  - {func}")
                
                logging.warning("\n=== WOLFRAM DATA COLLECTION COMPLETE ===\n")
                return wolfram_data
            else:
                logging.warning(f"Test file not found: {test_file}")
                return {}
                
        except Exception as e:
            logging.error(f"Error collecting Wolfram data: {e}")
            return {}

    def _generate_wolfram_patterns(self, wolfram_data: Dict) -> List[Dict]:
        """Generate patterns for Wolfram handler operations."""
        patterns = []
        
        try:
            # Generate patterns from all query types in wolfram_data
            if 'query_types' in wolfram_data:
                for category, queries in wolfram_data['query_types'].items():
                    # Add category-specific variations
                    category_variations = {
                        'math': [
                            'solve', 'calculate', 'compute', 'evaluate', 'find', 'determine',
                            'what is', 'show me', 'tell me', 'help me with', 'work out',
                            'figure out', 'get the answer for', 'solve for'
                        ],
                        'physics': [
                            'calculate', 'compute', 'find', 'determine', 'what is',
                            'measure', 'analyze', 'show me', 'tell me about',
                            'explain', 'help me understand'
                        ],
                        'chemistry': [
                            'find', 'calculate', 'what is', 'determine', 'analyze',
                            'show me', 'tell me about', 'explain', 'get information about',
                            'look up', 'search for'
                        ],
                        'biology': [
                            'explain', 'describe', 'what is', 'tell me about',
                            'show me', 'help me understand', 'give me information about',
                            'find information about', 'look up', 'search for'
                        ],
                        'geography': [
                            'find', 'where is', 'what is', 'show me', 'tell me about',
                            'get information about', 'look up', 'search for',
                            'give me details about', 'locate'
                        ],
                        'finance': [
                            'calculate', 'compute', 'find', 'what is', 'determine',
                            'analyze', 'show me', 'tell me about', 'get data for',
                            'look up', 'check', 'get current'
                        ],
                        'unit conversion': [
                            'convert', 'change', 'transform', 'what is', 'how many',
                            'show me', 'tell me', 'calculate', 'find equivalent of'
                        ],
                        'statistics': [
                            'calculate', 'compute', 'find', 'determine', 'analyze',
                            'what is', 'show me', 'tell me about', 'evaluate',
                            'get statistics for', 'analyze data for'
                        ]
                    }
                    
                    default_variations = [
                        'what is', 'find', 'calculate', 'compute', 'show me',
                        'tell me', 'help me with', 'determine', 'look up'
                    ]
                    
                    # Get variations for this category or use defaults
                    variations = category_variations.get(category, default_variations)
                    
                    for query in queries:
                        # Create base pattern from query
                        base_pattern = [{"LOWER": word} for word in query.split()]
                        patterns.append({
                            "label": f"WOLFRAM_{category.upper()}_QUERY",
                            "pattern": json.dumps(base_pattern),
                            "priority": 1,
                            "category": category
                        })
                        
                        # Add variations with action verbs
                        for verb in variations:
                            verb_pattern = [{"LOWER": word} for word in verb.split()]
                            patterns.append({
                                "label": f"WOLFRAM_{category.upper()}_QUERY",
                                "pattern": json.dumps(verb_pattern + base_pattern),
                                "priority": 1,
                                "category": category
                            })
                            
                            # Add more natural variations
                            if 'what is' not in verb:
                                patterns.append({
                                    "label": f"WOLFRAM_{category.upper()}_QUERY",
                                    "pattern": json.dumps(verb_pattern + [{"LOWER": "the"}] + base_pattern),
                                    "priority": 1,
                                    "category": category
                                })
                            
                            # Add question variations
                            patterns.append({
                                "label": f"WOLFRAM_{category.upper()}_QUERY",
                                "pattern": json.dumps([{"LOWER": "can"}, {"LOWER": "you"}] + verb_pattern + base_pattern),
                                "priority": 1,
                                "category": category
                            })
                            
                            patterns.append({
                                "label": f"WOLFRAM_{category.upper()}_QUERY",
                                "pattern": json.dumps([{"LOWER": "could"}, {"LOWER": "you"}] + verb_pattern + base_pattern),
                                "priority": 1,
                                "category": category
                            })

            # Add pod-specific patterns with variations
            if 'pod_types' in wolfram_data:
                pod_variations = [
                    'show', 'display', 'get', 'find', 'calculate', 'what is',
                    'tell me', 'give me', 'i want', 'i need', 'can you show',
                    'could you show', 'please show', 'please give me'
                ]
                
                for pod_type in wolfram_data['pod_types']:
                    # Convert pod type to a more natural language form
                    natural_pod = pod_type.replace('_', ' ').lower()
                    base_pattern = [{"LOWER": word} for word in natural_pod.split()]
                    
                    # Add base pattern
                    patterns.append({
                        "label": "WOLFRAM_POD_QUERY",
                        "pattern": json.dumps(base_pattern),
                        "priority": 2,
                        "pod_type": pod_type
                    })
                    
                    # Add variations
                    for verb in pod_variations:
                        verb_pattern = [{"LOWER": word} for word in verb.split()]
                        
                        # Basic variation
                        patterns.append({
                            "label": "WOLFRAM_POD_QUERY",
                            "pattern": json.dumps(verb_pattern + [{"LOWER": "the"}] + base_pattern),
                            "priority": 2,
                            "pod_type": pod_type
                        })
                        
                        # Question variation
                        patterns.append({
                            "label": "WOLFRAM_POD_QUERY",
                            "pattern": json.dumps([{"LOWER": "can"}, {"LOWER": "you"}] + verb_pattern + [{"LOWER": "the"}] + base_pattern),
                            "priority": 2,
                            "pod_type": pod_type
                        })

            # Add special function patterns with variations
            if 'special_functions' in wolfram_data:
                function_variations = [
                    'run', 'execute', 'perform', 'do', 'calculate', 'compute',
                    'process', 'handle', 'apply', 'use'
                ]
                
                for func in wolfram_data['special_functions']:
                    natural_func = func.replace('_', ' ').lower()
                    base_pattern = [{"LOWER": word} for word in natural_func.split()]
                    
                    # Add base pattern
                    patterns.append({
                        "label": "WOLFRAM_SPECIAL",
                        "pattern": json.dumps(base_pattern),
                        "priority": 2,
                        "function": func
                    })
                    
                    # Add variations
                    for verb in function_variations:
                        verb_pattern = [{"LOWER": word} for word in verb.split()]
                        patterns.append({
                            "label": "WOLFRAM_SPECIAL",
                            "pattern": json.dumps(verb_pattern + [{"LOWER": "the"}] + base_pattern),
                            "priority": 2,
                            "function": func
                        })

            # Add conversion patterns with more variations
            conversion_variations = [
                'convert', 'change', 'transform', 'switch', 'translate',
                'what is', 'how many', 'turn', 'make'
            ]
            
            for verb in conversion_variations:
                verb_pattern = [{"LOWER": word} for word in verb.split()]
                patterns.extend([
                    {
                        "label": "WOLFRAM_CONVERSION",
                        "pattern": json.dumps(verb_pattern + [
                            {"IS_NUMBER": True},
                            {"IS_ANY": True},
                            {"LOWER": "to"},
                            {"IS_ANY": True}
                        ]),
                        "priority": 1
                    },
                    {
                        "label": "WOLFRAM_CONVERSION",
                        "pattern": json.dumps([
                            {"LOWER": "can"},
                            {"LOWER": "you"}
                        ] + verb_pattern + [
                            {"IS_NUMBER": True},
                            {"IS_ANY": True},
                            {"LOWER": "to"},
                            {"IS_ANY": True}
                        ]),
                        "priority": 1
                    }
                ])

            logging.warning(f"\nGenerated {len(patterns)} Wolfram patterns")
            print("Pattern examples:")
            for idx, pattern in enumerate(patterns[:5], 1):
                if isinstance(pattern, list):
                    readable_text = ' '.join([token.get('LOWER', '') for token in pattern])
                elif isinstance(pattern, dict) and 'pattern' in pattern:
                    readable_text = pattern['pattern']
                else:
                    readable_text = str(pattern)
                print(f"  {idx}. {readable_text}")
            if len(patterns) > 5:
                print(f"  ... and {len(patterns)-5} more\n")
            
            return patterns
            
        except Exception as e:
            logging.error(f"Error generating Wolfram patterns: {e}")
            return patterns

    def vectorize_patterns(self, patterns: List[str]) -> Dict[str, Any]:
        """Vectorize all patterns at once for faster matching."""
        docs = list(self.nlp.pipe(patterns))  # Process all patterns in a batch
        return {pattern: doc.vector for pattern, doc in zip(patterns, docs)}
        
    def batch_match_patterns(self, text: str, patterns: List[str]) -> List[Tuple[float, str]]:
        """Match text against multiple patterns at once using vectorization."""
        if not patterns:
            return []
            
        # Get text vector once
        text_doc = self.nlp(text)
        text_vector = text_doc.vector
        
        print(f"\n=== Pattern Matching Details ===")
        print(f"Input text: {text}")
        
        # Get or compute pattern vectors and store matches
        matches = []
        for pattern in patterns:
            try:
                if pattern not in self.pattern_vectors:
                    pattern_doc = self.nlp(pattern)
                    self.pattern_vectors[pattern] = pattern_doc.vector
                pattern_vector = self.pattern_vectors[pattern]
                
                # Calculate cosine similarity
                similarity = text_vector.dot(pattern_vector) / (max(1e-8, (text_vector**2).sum() * (pattern_vector**2).sum()) ** 0.5)
                
                # Store match with detailed info
                matches.append((similarity, pattern))
                
                # Print detailed scoring for high matches
                if similarity > 0.5:
                    print(f"\nHigh scoring match found:")
                    print(f"Pattern: {pattern}")
                    print(f"Score: {similarity:.4f}")
                    
                    # Show token overlap
                    text_tokens = set(token.lower_ for token in text_doc)
                    pattern_tokens = set(token.lower_ for token in self.nlp(pattern))
                    overlap = text_tokens & pattern_tokens
                    if overlap:
                        print(f"Matching tokens: {', '.join(overlap)}")
                    
            except Exception as e:
                print(f"Error matching pattern '{pattern}': {str(e)}")
                continue
        
        # Sort by score
        matches.sort(reverse=True)
        
        # Print summary of top matches
        if matches:
            print(f"\nTop 5 matches:")
            for score, pattern in matches[:5]:
                print(f"Score: {score:.4f} | Pattern: {pattern}")
        
        return matches
        
    def process_intent_matches(self, text: str, category: str) -> List[Dict[str, Any]]:
        """Process intent matches in batches for better performance."""
        logging.info(f"\n=== Processing Intent Matches ===")
        logging.info(f"Text: {text}")
        logging.info(f"Category: {category}")
        logging.info(f"Loaded intents categories: {list(self.loaded_intents.keys())}")
        
        if category not in self.loaded_intents:
            logging.error(f"No intents found for category: {category}")
            return []
            
        # Collect all examples for this category
        all_examples = []
        intent_map = {}  # Map examples back to their intents
        
        for intent_data in self.loaded_intents[category]:
            for example in intent_data['examples']:
                all_examples.append(example)
                intent_map[example] = intent_data['intent']
        
        # Batch process all examples at once
        matches = self.batch_match_patterns(text, all_examples)
        
        # Convert matches to intent results
        results = []
        seen_intents = set()
        
        for score, example in matches:
            intent_name = intent_map[example]
            if intent_name not in seen_intents:
                seen_intents.add(intent_name)
                results.append({
                    'intent': intent_name,
                    'score': score,
                    'matched_example': example
                })
                
        return results

    def _convert_sets_to_lists(self, obj):
        """Recursively convert sets to lists in a dictionary."""
        if isinstance(obj, dict):
            return {key: self._convert_sets_to_lists(value) for key, value in obj.items()}
        elif isinstance(obj, set):
            return list(obj)
        elif isinstance(obj, list):
            return [self._convert_sets_to_lists(item) for item in obj]
        return obj

    def save_handler_data(self, handler_name, analysis_data, patterns_count=0, api_endpoints_count=0, python_calls_count=0, applescript_commands_count=0, semantic_matches_count=0):
        """Save handler analysis data to database."""
        logging.info(f"\n=== Saving Handler Data ===")
        logging.info(f"Handler: {handler_name}")
        logging.info(f"Patterns Count: {patterns_count}")
        logging.info(f"API Endpoints: {api_endpoints_count}")
        logging.info(f"Python Calls: {python_calls_count}")
        logging.info(f"AppleScript Commands: {applescript_commands_count}")
        logging.info(f"Semantic Matches: {semantic_matches_count}")
        
        try:
            # Convert sets to lists before JSON serialization
            serializable_data = self._convert_sets_to_lists(analysis_data)
            
            cursor = self.db_handler.conn.cursor()
            # Insert new record with current timestamp
            cursor.execute("""
                INSERT INTO handler_analysis (
                    handler_name, patterns_count,
                    api_endpoints_count, python_calls_count, applescript_commands_count,
                    semantic_matches_count, training_data, status, weight, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                handler_name, patterns_count, api_endpoints_count, python_calls_count,
                applescript_commands_count, semantic_matches_count,
                json.dumps(serializable_data), 'active', 0.9,
                datetime.now().isoformat()
            ))
            self.db_handler.conn.commit()
            logging.info("✓ Successfully saved handler data to database")
        except Exception as e:
            logging.error(f"Error saving handler data: {str(e)}")
            raise

    def save_pattern(self, handler_name, pattern_type, pattern_value, similarity_score=None):
        """Save pattern to database with versioning."""
        logging.info(f"\n=== Saving Pattern ===")
        logging.info(f"Handler: {handler_name}")
        logging.info(f"Type: {pattern_type}")
        logging.info(f"Value: {pattern_value[:100]}...")  # Truncate long patterns
        logging.info(f"Similarity Score: {similarity_score}")
        
        try:
            cursor = self.db_handler.conn.cursor()
            # Get handler_id
            cursor.execute("""
                SELECT id FROM handlers 
                WHERE handler_name = ? OR handler_type = ?
                ORDER BY created_at DESC LIMIT 1
            """, (handler_name, handler_name))
            result = cursor.fetchone()
            
            # If handler doesn't exist, create it
            if not result:
                logging.info(f"Creating new handler for {handler_name}")
                cursor.execute("""
                    INSERT INTO handlers (
                        handler_name, handler_type, handler_category, file_path
                    ) VALUES (?, ?, ?, ?)
                """, (handler_name, handler_name, 'sdk', os.path.join(HANDLER_DIR, f"{handler_name}.py")))
                handler_id = cursor.lastrowid
                self.db_handler.conn.commit()
                logging.info(f"Created new handler with ID {handler_id}")
            else:
                handler_id = result[0]
            
            # Insert new pattern with timestamp
            cursor.execute("""
                INSERT INTO pattern_mapping (
                    handler_id, pattern_type, pattern_value, similarity_score, created_at
                ) VALUES (?, ?, ?, ?, ?)
            """, (handler_id, pattern_type, pattern_value, similarity_score, datetime.now().isoformat()))
            pattern_id = cursor.lastrowid
            self.db_handler.conn.commit()
            logging.info("✓ Successfully saved pattern to database")
            return pattern_id
        except Exception as e:
            logging.error(f"Error saving pattern: {str(e)}")
            raise

    def save_intent_mapping(self, intent_id, pattern_id, score):
        """Save intent mapping to database with versioning."""
        logging.info(f"\n=== Saving Intent Mapping ===")
        logging.info(f"Intent ID: {intent_id}")
        logging.info(f"Pattern ID: {pattern_id}")
        logging.info(f"Score: {score}")
        
        try:
            cursor = self.db_handler.conn.cursor()
            # Get handler_id from pattern_id
            cursor.execute("SELECT handler_id FROM pattern_mapping WHERE id = ?", (pattern_id,))
            result = cursor.fetchone()
            if not result:
                logging.error(f"No handler found for pattern_id {pattern_id}")
                return
            handler_id = result[0]
            
            # Insert new mapping with timestamp
            cursor.execute("""
                INSERT INTO intent_mappings (
                    intent_id, pattern_id, handler_id, score, created_at
                ) VALUES (?, ?, ?, ?, ?)
            """, (intent_id, pattern_id, handler_id, score, datetime.now().isoformat()))
            self.db_handler.conn.commit()
            logging.info("✓ Successfully saved intent mapping to database")
        except Exception as e:
            logging.error(f"Error saving intent mapping: {str(e)}")
            raise

    def _discover_rest_endpoints(self, content: str) -> Set[str]:
        """Discover REST endpoints in handler content."""
        endpoints = set()
        try:
            # Parse the content into an AST
            tree = ast.parse(content)
            
            # Look for requests calls
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    # Check for requests.method() calls
                    if isinstance(node.func, ast.Attribute):
                        if node.func.attr.lower() in ['get', 'post', 'put', 'delete', 'patch']:
                            # Get the URL argument
                            if node.args:
                                url_arg = node.args[0]
                                if isinstance(url_arg, ast.Str):
                                    endpoints.add(f"{node.func.attr.upper()} {url_arg.s}")
                                elif isinstance(url_arg, ast.JoinedStr):  # f-strings
                                    # Try to reconstruct the URL pattern
                                    url_parts = []
                                    for value in url_arg.values:
                                        if isinstance(value, ast.Str):
                                            url_parts.append(value.s)
                                        elif isinstance(value, ast.FormattedValue):
                                            url_parts.append(f"{{{value.value.id}}}")
                                    endpoints.add(f"{node.func.attr.upper()} {''.join(url_parts)}")
            
            return endpoints
            
        except Exception as e:
            logging.error(f"Error discovering REST endpoints: {e}")
            return endpoints

    def _discover_graphql_endpoints(self, content: str) -> Set[str]:
        """Discover GraphQL endpoints in handler content."""
        endpoints = set()
        try:
            # Parse the content into an AST
            tree = ast.parse(content)
            
            # Look for GraphQL queries and mutations
            for node in ast.walk(tree):
                if isinstance(node, ast.Assign):
                    # Look for string assignments that contain GraphQL keywords
                    for target in node.targets:
                        if isinstance(target, ast.Name) and isinstance(node.value, ast.Str):
                            value = node.value.s.lower()
                            if 'query' in value or 'mutation' in value:
                                endpoints.add(node.value.s)
                elif isinstance(node, ast.Call):
                    # Look for execute_graphql or similar function calls
                    if isinstance(node.func, ast.Name) and 'graphql' in node.func.id.lower():
                        for arg in node.args:
                            if isinstance(arg, ast.Str):
                                endpoints.add(arg.s)
            
            return endpoints
            
        except Exception as e:
            logging.error(f"Error discovering GraphQL endpoints: {e}")
            return endpoints

    def _discover_dynamic_endpoints(self, content: str) -> Set[str]:
        """Discover dynamically constructed endpoints in handler content."""
        endpoints = set()
        try:
            # Parse the content into an AST
            tree = ast.parse(content)
            
            # Look for URL construction patterns
            for node in ast.walk(tree):
                if isinstance(node, ast.Assign):
                    # Look for URL assignments
                    for target in node.targets:
                        if isinstance(target, ast.Name) and 'url' in target.id.lower():
                            if isinstance(node.value, ast.Str):
                                endpoints.add(node.value.s)
                            elif isinstance(node.value, ast.JoinedStr):  # f-strings
                                url_parts = []
                                for value in node.value.values:
                                    if isinstance(value, ast.Str):
                                        url_parts.append(value.s)
                                    elif isinstance(value, ast.FormattedValue):
                                        url_parts.append(f"{{{value.value.id}}}")
                                endpoints.add(''.join(url_parts))
                            elif isinstance(node.value, ast.BinOp):  # String concatenation
                                if isinstance(node.value.left, ast.Str) and isinstance(node.value.right, ast.Str):
                                    endpoints.add(node.value.left.s + node.value.right.s)
            
            return endpoints
            
        except Exception as e:
            logging.error(f"Error discovering dynamic endpoints: {e}")
            return endpoints

    def _discover_base_urls(self, content: str) -> Set[str]:
        """Discover base URLs in handler content."""
        base_urls = set()
        try:
            # Parse the content into an AST
            tree = ast.parse(content)
            
            # Look for base URL assignments
            for node in ast.walk(tree):
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name) and any(term in target.id.lower() for term in ['base_url', 'baseurl', 'api_url', 'apiurl']):
                            if isinstance(node.value, ast.Str):
                                url = node.value.s
                                if url.startswith(('http://', 'https://')):
                                    base_urls.add(url)
            
            return base_urls
            
        except Exception as e:
            logging.error(f"Error discovering base URLs: {e}")
            return base_urls

    def _process_handler_patterns(self, handler_type: str, patterns: List[Dict], batch_size: int = 50) -> None:
        """Process handler patterns in batches."""
        try:
            total_patterns = len(patterns)
            logging.info(f"\n=== Processing Patterns for {handler_type} ===")
            logging.info(f"Found {total_patterns} patterns to process")

            # Get intents for this handler type
            cursor = self.db_handler.conn.cursor()
            cursor.execute('SELECT * FROM intents WHERE category = ?', (handler_type,))
            intents = cursor.fetchall()
            
            if not intents:
                logging.info(f"No intents found for category {handler_type}")
                return

            for i in range(0, total_patterns, batch_size):
                batch = patterns[i:i + batch_size]
                batch_num = (i // batch_size) + 1
                total_batches = (total_patterns + batch_size - 1) // batch_size
                
                logging.info(f"\nProcessing batch {batch_num} of {total_batches}")
                logging.info("\nPattern Examples from Current Batch:")
                
                # Show first 5 patterns in human-readable format
                for j, pattern in enumerate(batch[:5], 1):
                    pattern_text = self._get_readable_text(pattern)
                    logging.info(f"{j}. {pattern_text}")
                
                if len(batch) > 5:
                    logging.info(f"...and {len(batch) - 5} more examples in this batch")
                
                logging.info("\nAnalyzing matches...")
                
                # Process each pattern in the batch
                batch_matches = []
                for pattern in batch:
                    pattern_text = self._get_readable_text(pattern)
                    matches = self._match_patterns_to_intents(pattern_text, intents)
                    
                    if matches:
                        for match in matches:
                            batch_matches.append({
                                'pattern': pattern_text,
                                'intent': match['intent'],
                                'score': match['score'],
                                'category': match['category']
                            })
                
                # Display batch matches
                if batch_matches:
                    logging.info("\nIntent matches for this batch:")
                    for match in batch_matches:
                        logging.info(f"\nPattern: {match['pattern']}")
                        logging.info(f"Intent:  {match['intent']}")
                        logging.info(f"Score:   {match['score']:.2f}")
                        logging.info(f"Category: {match['category']}")
                
                logging.info(f"\n✓ Processed batch {batch_num} - Found {len(batch_matches)} matches")
                
            logging.info(f"\nTotal patterns processed: {total_patterns}")
            
        except Exception as e:
            logging.error(f"Error processing patterns: {str(e)}")

    def _get_readable_text(self, pattern: Union[List, Dict]) -> str:
        """Convert pattern to human-readable text."""
        try:
            if isinstance(pattern, list):
                return " ".join(token.get('LOWER', '') for token in pattern if isinstance(token, dict))
            elif isinstance(pattern, dict):
                return pattern.get('pattern', '')
            return str(pattern)
        except Exception as e:
            logging.error(f"Error converting pattern to text: {str(e)}")
            return str(pattern)

    def generate_patterns_for_handlers(self):
        """Generate patterns for handlers defined in handler_analyzer2_custom.py."""
        for handler_file, pattern_file in self.handler_to_pattern_mapping.items():
            logging.info(f"Generating patterns for handler: {handler_file}")
            handler_data = self._load_handler_data(handler_file)
            patterns = self._generate_generic_patterns(handler_data)
            # Process patterns using shared method
            self._process_handler_patterns(handler_file, patterns)

    def _load_handler_data(self, handler_file: str) -> Dict:
        """Load handler data for pattern generation."""
        # Implement logic to load handler data
        with open(handler_file, 'r') as file:
            content = file.read()
        return {'content': content}

    def _generate_generic_patterns(self, handler_data: Dict) -> List[Dict]:
        """Generate generic patterns from handler data."""
        patterns = []
        # Implement logic for generating patterns from functions, classes, etc.
        # Example: Extract function names and convert to patterns
        # This is a placeholder for actual pattern generation logic
        return patterns

    def _process_patterns_for_category(self, patterns: List[Dict], category: str):
        """Process patterns for a specific category."""
        # Implement logic to process patterns for the given category
        # Example: Store patterns in a database or file
        pass

    def process_patterns_in_batches(self, patterns: List[Dict], handler_type: str, batch_size: int = 100):
        """Process patterns in batches to improve performance for large data sets."""
        total_patterns = len(patterns)
        for start in range(0, total_patterns, batch_size):
            end = min(start + batch_size, total_patterns)
            batch = patterns[start:end]
            logging.info(f"Processing batch {start // batch_size + 1} of {total_patterns // batch_size + 1}")
            self.match_patterns_to_intents(batch, handler_type)

    # Re-adding custom Wolfram endpoint extraction logic
    def _discover_wolfram_endpoints(self, content: str) -> Dict:
        """Discover custom endpoints for Wolfram handlers using specialized logic."""
        try:
            import re
            # Custom extraction logic for Wolfram: adjust regex patterns as needed
            rest_endpoints = re.findall(r'GET\s+(\w+)', content)
            graphql_endpoints = re.findall(r'(http[s]?://api\.wolframalpha\.com/\S+)', content)
            dynamic_endpoints = []  # add dynamic extraction logic if applicable
            base_urls = re.findall(r'BASE_URL:\s*(\S+)', content)
            return {
                'rest_endpoints': rest_endpoints,
                'graphql_endpoints': graphql_endpoints,
                'dynamic_endpoints': dynamic_endpoints,
                'base_urls': base_urls
            }
        except Exception as e:
            logging.error(f"Error discovering Wolfram endpoints: {e}")
            return {}

class PerformanceMetrics:
    def __init__(self):
        self.metrics = defaultdict(lambda: {
            'count': 0,
            'total_duration': 0,
            'errors': 0,
            'avg_duration': 0
        })
        self.system_metrics = {
            'cpu_percent': 0,
            'memory_percent': 0,
            'disk_usage': 0
        }
        
    def update_system_metrics(self):
        """Update system-level metrics."""
        try:
            self.system_metrics['cpu_percent'] = psutil.cpu_percent()
            self.system_metrics['memory_percent'] = psutil.virtual_memory().percent
            self.system_metrics['disk_usage'] = psutil.disk_usage('/').percent
        except Exception as e:
            logging.error(f"Error updating system metrics: {str(e)}")
            
    def update_handler_metrics(self, handler_name: str, duration: float, error: bool = False):
        """Update metrics for a specific handler."""
        try:
            metrics = self.metrics[handler_name]
            metrics['count'] += 1
            metrics['total_duration'] += duration
            if error:
                metrics['errors'] += 1
            metrics['avg_duration'] = metrics['total_duration'] / metrics['count']
        except Exception as e:
            logging.error(f"Error updating handler metrics: {str(e)}")

def setup_logging():
    """Configure logging to output to both file and console."""
    # Create logs directory if it doesn't exist
    if not os.path.exists('logs'):
        os.makedirs('logs')
        
    # Set up root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    
    # Clear any existing handlers
    root_logger.handlers = []
    
    # Console handler - show everything
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter('%(message)s')
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # File handler
    file_handler = logging.FileHandler('logs/handler_analyzer_debug.log')
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)
    
    logging.info("Logging configured successfully")

def main():
    try:
        # Initialize database and tables
        db_manager = DatabaseHandler(HANDLER_DB_PATH)
        db_manager.init_database()  # Ensure tables are created
        
        # Initialize analyzer with correct database
        analyzer = EndpointDiscovery(db_connection=db_manager.conn)
        
        # Create an instance of AIPatternAnalyzer with the database connection
        ai_analyzer = AIPatternAnalyzer(db_connection=db_manager.conn)
        
        # Define supported handlers in processing order
        supported_handlers = [
            ('handler_wolfram.py', 'wolfram'),
            ('handler_ghl_requests.py', 'ghl'),
            ('handler_calendar.py', 'calendar'),
            ('handler_email.py', 'email'),
            ('handler_<healthcare>_sdk2.py', '<healthcare>')
        ]
        
        logging.warning("\n=== PROCESSING HANDLERS IN SEQUENCE ===")
        
        successful = 0
        skipped = 0
        failed = 0
        
        # Process each handler in sequence
        for handler_file, handler_type in supported_handlers:
            try:
                handler_path = os.path.join("Handler", handler_file)
                if not os.path.exists(handler_path):
                    logging.warning(f"Handler file not found: {handler_path}")
                    skipped += 1
                    continue
                
                logging.warning(f"\n=== PROCESSING {handler_type.upper()} HANDLER ===")
                logging.warning(f"Reading file: {handler_path}")
                
                # Use AIPatternAnalyzer methods
                logging.debug("Extracting basic patterns")
                handler_data = ai_analyzer._extract_basic_patterns(handler_path)
                logging.debug(f"Extracted handler data: {handler_data}")
                
                logging.debug("Generating generic patterns")
                patterns = ai_analyzer._generate_generic_patterns(handler_data)
                logging.debug(f"Generated patterns: {patterns}")
                
                logging.debug("Matching patterns to intents")
                intent_matches = ai_analyzer.match_patterns_to_intents(patterns, handler_type)
                logging.debug(f"Intent matches: {intent_matches}")
                
                # Log results
                logging.warning(f"✓ Successfully processed {handler_type} - Found {len(patterns)} patterns")
                if intent_matches:
                    logging.warning(f"✓ Matched {len(intent_matches)} intents")
                successful += 1
            
            except Exception as e:
                logging.error(f"Error processing handler {handler_file}: {e}")
                failed += 1
                continue
        
        logging.warning(f"\nProcessing complete:")
        logging.warning(f"Successful: {successful}")
        logging.warning(f"Skipped: {skipped}")
        logging.warning(f"Failed: {failed}")
        
        return 0 if failed == 0 else 1
        
    except Exception as e:
        logging.error(f"Error in main: {e}")
        logging.error(traceback.format_exc())
        return 1

if __name__ == "__main__":
    setup_logging()
    sys.exit(main())