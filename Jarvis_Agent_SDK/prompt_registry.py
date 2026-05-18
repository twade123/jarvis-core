#!/usr/bin/env python3
"""
Prompt Registry System

A comprehensive registry for managing prompts across different models and agents.
This system provides:

1. Centralized prompt storage and retrieval
2. Version management for prompts
3. Performance tracking and optimization
4. Model compatibility awareness
5. Integration with agent registry
6. JSON validation for prompt files
7. Variable substitution for template prompts
8. A/B testing capabilities

Usage:
    registry = PromptRegistry()
    prompt = registry.load_prompt("boardroom_claude_system")
    filled_prompt = registry.fill_prompt_template(prompt_id, variables)
    registry.track_performance(prompt_id, success=True, response_time=1.2)
"""

import os
import sys
import json
import time
import uuid
import glob
import logging
import sqlite3
import re
import jsonschema
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Tuple
import traceback

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PromptRegistry:
    """
    Registry for managing prompts across different models and agents.
    
    This class provides a comprehensive system for prompt management including:
    - Loading prompts from JSON files and database
    - Tracking prompt performance
    - Version management
    - Model compatibility
    - Template filling with variables
    """
    
    def __init__(self, db_path=None, prompts_dir=None, schema_path=None):
        """
        Initialize the prompt registry with database and directory paths.
        
        Args:
            db_path: Path to the prompts database
            prompts_dir: Directory containing prompt JSON files
            schema_path: Path to the JSON schema for validating prompts
        """
        # Get base directory
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # Set database path
        if not db_path:
            db_dir = os.path.join(base_dir, "Database")
            self.db_path = os.path.join(db_dir, "v2", "prompts.db")
        else:
            self.db_path = db_path
            
        # Set prompts directory
        if not prompts_dir:
            self.prompts_dir = os.path.join(base_dir, "Prompts")
        else:
            self.prompts_dir = prompts_dir
            
        # Set schema path
        if not schema_path:
            schema_dir = os.path.join(base_dir, "schema")
            self.schema_path = os.path.join(schema_dir, "prompt_schema_relaxed.json")
        else:
            self.schema_path = schema_path
            
        # Ensure directories exist
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        os.makedirs(self.prompts_dir, exist_ok=True)
        
        # Initialize database connection
        self.conn = None
        self._init_db_connection()
        
        # Load schema for validation
        self.schema = self._load_schema()
        
        # Cache for prompt lookups
        self._prompt_cache = {}
        self._version_cache = {}
        
        # Initialize cache from database
        self._init_cache()
        
    def _init_db_connection(self):
        """Initialize the database connection."""
        try:
            self.conn = sqlite3.connect(self.db_path, timeout=30, isolation_level=None)
            self.conn.execute("PRAGMA busy_timeout = 30000")
            self.conn.execute("PRAGMA journal_mode=DELETE")
            self.conn.row_factory = sqlite3.Row  # Enable row_factory for easier column access
            logger.info(f"Connected to database at {self.db_path}")
            return True
        except Exception as e:
            logger.error(f"Error connecting to database: {str(e)}")
            return False
            
    def _load_schema(self):
        """Load the JSON schema for prompt validation."""
        try:
            if os.path.exists(self.schema_path):
                with open(self.schema_path, 'r') as f:
                    schema = json.load(f)
                logger.info(f"Loaded JSON schema from {self.schema_path}")
                return schema
            else:
                logger.warning(f"Schema file not found at {self.schema_path}")
                return None
        except Exception as e:
            logger.error(f"Error loading schema: {str(e)}")
            return None
            
    def _init_cache(self):
        """Initialize the cache from the database."""
        try:
            if not self.conn:
                self._init_db_connection()
                if not self.conn:
                    logger.error("Cannot initialize cache: database connection failed")
                    return False
                    
            # Clear existing cache
            self._prompt_cache = {}
            self._version_cache = {}
            
            # Load prompts from database
            cursor = self.conn.cursor()
            cursor.execute('''
            SELECT pr.*, pv.version, pv.content
            FROM prompt_registry pr
            LEFT JOIN prompt_versions pv ON pr.prompt_id = pv.prompt_id AND pr.current_version = pv.version
            WHERE pr.is_active = 1
            ''')
            
            for row in cursor.fetchall():
                prompt_id = row['prompt_id']
                
                # Convert row to dictionary
                prompt_data = {
                    'id': row['id'],
                    'prompt_id': prompt_id,
                    'name': row['name'],
                    'description': row['description'],
                    'version': row['version'],
                    'content': row['content'],
                    'created_at': row['created_at'],
                    'updated_at': row['updated_at'],
                    'author': row['author'],
                    'prompt_family': row['prompt_family'],
                    'metadata': json.loads(row['metadata']) if row['metadata'] else {}
                }
                
                # Add to cache
                self._prompt_cache[prompt_id] = prompt_data
                
            # Load prompt versions
            cursor.execute('''
            SELECT * FROM prompt_versions
            WHERE is_active = 1
            ''')
            
            for row in cursor.fetchall():
                prompt_id = row['prompt_id']
                version = row['version']
                
                if prompt_id not in self._version_cache:
                    self._version_cache[prompt_id] = {}
                    
                # Convert row to dictionary
                version_data = {
                    'id': row['id'],
                    'prompt_id': prompt_id,
                    'version': version,
                    'content': row['content'],
                    'created_at': row['created_at'],
                    'author': row['author'],
                    'changelog': row['changelog']
                }
                
                # Add to version cache
                self._version_cache[prompt_id][version] = version_data
                
            logger.info(f"Initialized cache with {len(self._prompt_cache)} prompts and {sum(len(versions) for versions in self._version_cache.values())} versions")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing cache: {str(e)}")
            return False
    
    def load_prompts_from_directory(self, directory=None):
        """
        Load all prompt JSON files from the specified directory.
        
        Args:
            directory: Optional directory path, uses self.prompts_dir if None
            
        Returns:
            Dict with stats about the loading process
        """
        stats = {
            "loaded": 0,
            "skipped": 0,
            "errors": []
        }
        
        try:
            # Use provided directory or default
            dir_path = directory or self.prompts_dir
            
            # Find all JSON files in the directory and subdirectories
            json_files = glob.glob(os.path.join(dir_path, "**/*.json"), recursive=True)
            logger.info(f"Found {len(json_files)} JSON files in {dir_path}")
            
            # Process each file
            for file_path in json_files:
                try:
                    # Load JSON file
                    with open(file_path, 'r') as f:
                        prompt_data = json.load(f)
                    
                    # Apply transformations and default values BEFORE validation
                    prompt_data = self._add_default_values(prompt_data)
                    
                    # Validate against schema
                    if self.schema:
                        try:
                            jsonschema.validate(instance=prompt_data, schema=self.schema)
                        except jsonschema.exceptions.ValidationError as e:
                            logger.warning(f"Validation error for {file_path}: {str(e)}")
                            stats["errors"].append(f"Validation error for {file_path}: {str(e)}")
                            stats["skipped"] += 1
                            continue
                    
                    # Register prompt
                    result = self.register_prompt(prompt_data, file_path)
                    if result:
                        stats["loaded"] += 1
                    else:
                        stats["skipped"] += 1
                        
                except Exception as e:
                    logger.error(f"Error processing {file_path}: {str(e)}")
                    stats["errors"].append(f"Error processing {file_path}: {str(e)}")
                    stats["skipped"] += 1
            
            logger.info(f"Loaded {stats['loaded']} prompts from directory, skipped {stats['skipped']}")
            return stats
            
        except Exception as e:
            logger.error(f"Error loading prompts from directory: {str(e)}")
            stats["errors"].append(f"Error loading prompts from directory: {str(e)}")
            return stats
    
    def load_prompt(self, prompt_id, version=None):
        """
        Load a specific prompt by ID and optional version.
        
        Args:
            prompt_id: Unique identifier for the prompt
            version: Optional specific version to load
            
        Returns:
            Dict with prompt data or None if not found
        """
        try:
            # Check cache first
            if prompt_id in self._prompt_cache:
                prompt_data = self._prompt_cache[prompt_id]
                
                # If specific version requested and available in version cache
                if version and prompt_id in self._version_cache and version in self._version_cache[prompt_id]:
                    version_data = self._version_cache[prompt_id][version]
                    # Update content with specific version
                    prompt_data = prompt_data.copy()
                    prompt_data['content'] = version_data['content']
                    prompt_data['version'] = version
                    
                return prompt_data
                
            # Not in cache, try database
            if not self.conn:
                self._init_db_connection()
                if not self.conn:
                    logger.error("Cannot load prompt: database connection failed")
                    return None
                    
            cursor = self.conn.cursor()
            
            if version:
                # Load specific version
                cursor.execute('''
                SELECT pr.*, pv.version, pv.content
                FROM prompt_registry pr
                JOIN prompt_versions pv ON pr.prompt_id = pv.prompt_id
                WHERE pr.prompt_id = ? AND pv.version = ?
                AND pr.is_active = 1 AND pv.is_active = 1
                ''', (prompt_id, version))
            else:
                # Load current version
                cursor.execute('''
                SELECT pr.*, pv.version, pv.content
                FROM prompt_registry pr
                LEFT JOIN prompt_versions pv ON pr.prompt_id = pv.prompt_id AND pr.current_version = pv.version
                WHERE pr.prompt_id = ? AND pr.is_active = 1
                ''', (prompt_id,))
                
            row = cursor.fetchone()
            if row:
                # Convert row to dictionary
                prompt_data = {
                    'id': row['id'],
                    'prompt_id': prompt_id,
                    'name': row['name'],
                    'description': row['description'],
                    'version': row['version'],
                    'content': row['content'],
                    'created_at': row['created_at'],
                    'updated_at': row['updated_at'],
                    'author': row['author'],
                    'prompt_family': row['prompt_family'],
                    'metadata': json.loads(row['metadata']) if row['metadata'] else {}
                }
                
                # Add to cache
                self._prompt_cache[prompt_id] = prompt_data
                
                return prompt_data
                
            # Not found in database, try to load from file
            return self._load_prompt_from_file(prompt_id)
            
        except Exception as e:
            logger.error(f"Error loading prompt {prompt_id}: {str(e)}")
            return None
    
    def _load_prompt_from_file(self, prompt_id):
        """
        Load a prompt from JSON file.
        
        Args:
            prompt_id: Unique identifier for the prompt
            
        Returns:
            Dict with prompt data or None if not found
        """
        try:
            # Try to find prompt file in the prompts directory
            for root, dirs, files in os.walk(self.prompts_dir):
                for file in files:
                    if file.endswith('.json'):
                        file_path = os.path.join(root, file)
                        try:
                            with open(file_path, 'r') as f:
                                prompt_data = json.load(f)
                                
                            if prompt_data.get('prompt_id') == prompt_id:
                                # Found the prompt, register it in the database
                                result = self.register_prompt(prompt_data, file_path)
                                if result:
                                    return self.load_prompt(prompt_id)  # Reload from database
                        except:
                            pass
                            
            logger.warning(f"Prompt {prompt_id} not found in files")
            return None
            
        except Exception as e:
            logger.error(f"Error loading prompt from file: {str(e)}")
            return None
    
    def search_prompts(self, agent_type=None, tags=None, models=None, prompt_family=None, limit=None, min_performance_score=None):
        """
        Search for prompts matching specific criteria.
        
        Args:
            agent_type: Optional agent type to filter by
            tags: Optional list of tags to filter by
            models: Optional list of compatible models
            prompt_family: Optional prompt family to filter by
            limit: Optional maximum number of results to return
            min_performance_score: Optional minimum performance score (0.0-1.0)
            
        Returns:
            List of matching prompt dictionaries
        """
        try:
            if not self.conn:
                self._init_db_connection()
                if not self.conn:
                    logger.error("Cannot search prompts: database connection failed")
                    return []
                    
            cursor = self.conn.cursor()
            
            # Base query
            query = '''
            SELECT DISTINCT pr.prompt_id
            FROM prompt_registry pr
            '''
            
            # Add joins based on filters
            joins = []
            where_clauses = ["pr.is_active = 1"]
            params = []
            
            if agent_type:
                joins.append("LEFT JOIN agent_compatibility ac ON pr.prompt_id = ac.prompt_id")
                where_clauses.append("ac.agent_type = ?")
                params.append(agent_type)
                
            if tags and len(tags) > 0:
                joins.append("LEFT JOIN prompt_tags pt ON pr.prompt_id = pt.prompt_id")
                placeholders = ", ".join(["?" for _ in range(len(tags))])
                where_clauses.append(f"pt.tag IN ({placeholders})")
                params.extend(tags)
                
            if models and len(models) > 0:
                joins.append("LEFT JOIN model_compatibility mc ON pr.prompt_id = mc.prompt_id")
                placeholders = ", ".join(["?" for _ in range(len(models))])
                where_clauses.append(f"mc.model_id IN ({placeholders})")
                params.extend(models)
                
            if prompt_family:
                where_clauses.append("pr.prompt_family = ?")
                params.append(prompt_family)
                
            # Add performance score filtering
            if min_performance_score is not None:
                joins.append("LEFT JOIN prompt_performance pp ON pr.prompt_id = pp.prompt_id")
                where_clauses.append("pp.quality_score >= ?")
                params.append(min_performance_score)
                
            # Combine everything
            query += " " + " ".join(joins)
            if where_clauses:
                query += " WHERE " + " AND ".join(where_clauses)
                
            # Add limit if specified
            if limit is not None:
                query += " LIMIT ?"
                params.append(limit)
                
            # Execute query
            cursor.execute(query, params)
            prompt_ids = [row[0] for row in cursor.fetchall()]
            
            # Load full prompt data for each ID
            results = []
            for prompt_id in prompt_ids:
                prompt_data = self.load_prompt(prompt_id)
                if prompt_data:
                    results.append(prompt_data)
                    
            return results
            
        except Exception as e:
            logger.error(f"Error searching prompts: {str(e)}")
            return []
    
    def _add_default_values(self, prompt_data):
        """
        Add default values for missing fields in prompt data and transform legacy formats.
        
        Args:
            prompt_data: Original prompt data dictionary
            
        Returns:
            Updated prompt data with default values and transformed formats
        """
        # Create a copy to avoid modifying the original
        data = prompt_data.copy()
        
        # TRANSFORM LEGACY FORMATS FIRST
        
        # Transform model_compatibility array to models object
        if 'model_compatibility' in data and 'models' not in data:
            model_list = data.pop('model_compatibility')
            data['models'] = {
                'compatible': model_list if isinstance(model_list, list) else ['claude', 'gpt'],
                'preferred': model_list[0] if isinstance(model_list, list) and model_list else 'claude'
            }
        
        # Transform variables array to object (empty array becomes empty object)
        if 'variables' in data and isinstance(data['variables'], list):
            if len(data['variables']) == 0:
                data['variables'] = {}
            else:
                # Convert array of variable definitions to object format
                # This handles cases where variables might be stored as array
                variables_obj = {}
                for var in data['variables']:
                    if isinstance(var, dict) and 'name' in var:
                        var_name = var.pop('name')
                        variables_obj[var_name] = var
                    elif isinstance(var, str):
                        variables_obj[var] = {'description': '', 'required': False, 'type': 'string'}
                data['variables'] = variables_obj
        
        # ADD DEFAULT VALUES FOR MISSING FIELDS
        
        # Add default version if missing
        if 'version' not in data:
            data['version'] = '1.0.0'
            
        # Add default timestamps if missing
        current_time = time.time()
        if 'created_at' not in data:
            data['created_at'] = current_time
        if 'updated_at' not in data:
            data['updated_at'] = current_time
            
        # Add default author if missing
        if 'author' not in data:
            data['author'] = 'system'
            
        # Add default models if missing (after transformation check)
        if 'models' not in data:
            data['models'] = {
                'compatible': ['claude-3-haiku', 'claude-3-sonnet', 'claude-3-opus'],
                'preferred': 'claude-3-sonnet'
            }
            
        # Add default agent compatibility if missing
        if 'agent_compatibility' not in data:
            data['agent_compatibility'] = {
                'agent_types': ['claude'],
                'handler_modules': ['handler_claude']
            }
            
        # Add default usage context if missing
        if 'usage' not in data:
            data['usage'] = {
                'context': ['general'],
                'workflow_stages': ['processing']
            }
            
        # Add default variables if missing (after transformation check)
        if 'variables' not in data:
            data['variables'] = {}
            
        # Add default performance metrics if missing
        if 'performance' not in data:
            data['performance'] = {
                'avg_tokens': 0,
                'expected_response_tokens': 0,
                'success_rate': 0.5,
                'avg_response_time': 0,
                'usage_count': 0
            }
            
        # Add default tags if missing
        if 'tags' not in data:
            data['tags'] = []
            
        # Add default related prompts if missing
        if 'related_prompts' not in data:
            data['related_prompts'] = []
            
        # Add default prompt family if missing
        if 'prompt_family' not in data:
            data['prompt_family'] = ''
            
        # Add default metadata if missing
        if 'metadata' not in data:
            data['metadata'] = {}
            
        return data
    
    def register_prompt(self, prompt_data, file_path=None):
        """
        Register a new prompt or update an existing one.
        
        Args:
            prompt_data: Prompt data dictionary
            file_path: Optional file path to read prompt from
            
        Returns:
            Prompt ID if successful, None otherwise
        """
        try:
            # Add default values for missing fields
            prompt_data = self._add_default_values(prompt_data)
            
            # Validate required fields (relaxed requirements)
            required_fields = ['prompt_id', 'name', 'description', 'content']
            for field in required_fields:
                if field not in prompt_data:
                    logger.warning(f"Missing required field '{field}' in prompt data")
                    return None
                    
            # Extract main fields
            prompt_id = prompt_data['prompt_id']
            name = prompt_data['name']
            description = prompt_data['description']
            content = prompt_data['content']
            version = prompt_data['version']
            created_at = prompt_data.get('created_at', time.time())
            updated_at = prompt_data.get('updated_at', time.time())
            author = prompt_data.get('author', 'system')
            prompt_family = prompt_data.get('prompt_family', '')
            
            # Extract additional data
            models = prompt_data.get('models', {})
            agent_compatibility = prompt_data.get('agent_compatibility', {})
            usage = prompt_data.get('usage', {})
            variables = prompt_data.get('variables', {})
            performance = prompt_data.get('performance', {})
            tags = prompt_data.get('tags', [])
            related_prompts = prompt_data.get('related_prompts', [])
            metadata = prompt_data.get('metadata', {})
            
            # Add file path to metadata if provided
            if file_path:
                metadata['file_path'] = file_path
                
            # Check if database connection is available
            if not self.conn:
                self._init_db_connection()
                if not self.conn:
                    logger.error("Cannot register prompt: database connection failed")
                    return None
                    
            cursor = self.conn.cursor()
            
            # Check if prompt already exists
            cursor.execute("SELECT id, current_version FROM prompt_registry WHERE prompt_id = ?", (prompt_id,))
            existing = cursor.fetchone()
            
            if existing:
                # Update existing prompt
                current_version = existing['current_version']
                
                # Check if this is a new version
                if version != current_version:
                    # Add new version
                    self._add_prompt_version(prompt_id, version, content, author)
                    
                    # Update registry with new version
                    cursor.execute('''
                    UPDATE prompt_registry
                    SET name = ?, description = ?, current_version = ?, 
                        updated_at = ?, author = ?, prompt_family = ?, metadata = ?
                    WHERE prompt_id = ?
                    ''', (name, description, version, updated_at, author, 
                          prompt_family, json.dumps(metadata), prompt_id))
                else:
                    # Just update the existing version
                    cursor.execute('''
                    UPDATE prompt_registry
                    SET name = ?, description = ?, updated_at = ?, 
                        author = ?, prompt_family = ?, metadata = ?
                    WHERE prompt_id = ?
                    ''', (name, description, updated_at, author, 
                          prompt_family, json.dumps(metadata), prompt_id))
                    
                    # Update version content if needed
                    cursor.execute('''
                    UPDATE prompt_versions
                    SET content = ?, author = ?
                    WHERE prompt_id = ? AND version = ?
                    ''', (json.dumps(content) if isinstance(content, dict) else content, 
                          author, prompt_id, version))
            else:
                # Create new prompt
                db_id = str(uuid.uuid4())
                
                # Insert into registry
                cursor.execute('''
                INSERT INTO prompt_registry
                (id, prompt_id, name, description, current_version, 
                 created_at, updated_at, author, prompt_family, metadata, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                ''', (db_id, prompt_id, name, description, version, 
                      created_at, updated_at, author, prompt_family, json.dumps(metadata)))
                
                # Add initial version
                self._add_prompt_version(prompt_id, version, content, author)
            
            # Update tags
            if tags:
                # Remove existing tags
                cursor.execute("DELETE FROM prompt_tags WHERE prompt_id = ?", (prompt_id,))
                
                # Add new tags
                for tag in tags:
                    cursor.execute('''
                    INSERT INTO prompt_tags (prompt_id, tag)
                    VALUES (?, ?)
                    ''', (prompt_id, tag))
            
            # Update model compatibility
            if models and isinstance(models, dict):
                # Remove existing compatibility
                cursor.execute("DELETE FROM model_compatibility WHERE prompt_id = ?", (prompt_id,))
                
                # Add compatible models
                compatible_models = models.get('compatible', [])
                preferred_model = models.get('preferred', '')
                min_compatibility = models.get('min_compatibility', '')
                
                for model_id in compatible_models:
                    is_preferred = 1 if model_id == preferred_model else 0
                    cursor.execute('''
                    INSERT INTO model_compatibility 
                    (prompt_id, model_id, is_preferred, min_model_version)
                    VALUES (?, ?, ?, ?)
                    ''', (prompt_id, model_id, is_preferred, min_compatibility))
            
            # Update agent compatibility
            if agent_compatibility and isinstance(agent_compatibility, dict):
                # Remove existing compatibility
                cursor.execute("DELETE FROM agent_compatibility WHERE prompt_id = ?", (prompt_id,))
                
                # Add agent types
                agent_types = agent_compatibility.get('agent_types', [])
                handler_modules = agent_compatibility.get('handler_modules', [])
                
                for agent_type in agent_types:
                    for handler_module in handler_modules:
                        cursor.execute('''
                        INSERT INTO agent_compatibility 
                        (prompt_id, agent_type, handler_module)
                        VALUES (?, ?, ?)
                        ''', (prompt_id, agent_type, handler_module))
            
            # Update variables
            if variables and isinstance(variables, dict):
                # Remove existing variables
                cursor.execute("DELETE FROM prompt_variables WHERE prompt_id = ?", (prompt_id,))
                
                # Add variables
                for var_name, var_info in variables.items():
                    if isinstance(var_info, dict):
                        description = var_info.get('description', '')
                        is_required = 1 if var_info.get('required', False) else 0
                        var_type = var_info.get('type', 'string')
                        default_value = json.dumps(var_info.get('default', None))
                        
                        cursor.execute('''
                        INSERT INTO prompt_variables 
                        (prompt_id, variable_name, description, is_required, variable_type, default_value)
                        VALUES (?, ?, ?, ?, ?, ?)
                        ''', (prompt_id, var_name, description, is_required, var_type, default_value))
            
            # Update usage context
            if usage and isinstance(usage, dict):
                # Remove existing context
                cursor.execute("DELETE FROM usage_context WHERE prompt_id = ?", (prompt_id,))
                
                # Add context
                context_types = usage.get('context', [])
                workflow_stages = usage.get('workflow_stages', [])
                
                for context_type in context_types:
                    for workflow_stage in workflow_stages:
                        cursor.execute('''
                        INSERT INTO usage_context 
                        (prompt_id, context_type, workflow_stage)
                        VALUES (?, ?, ?)
                        ''', (prompt_id, context_type, workflow_stage))
            
            # Update examples
            if metadata and 'examples' in metadata:
                examples = metadata.get('examples', [])
                
                # Remove existing examples
                cursor.execute("DELETE FROM prompt_examples WHERE prompt_id = ?", (prompt_id,))
                
                # Add examples
                for example in examples:
                    if isinstance(example, dict):
                        input_text = example.get('input', '')
                        expected_output = example.get('expected_output', '')
                        context = json.dumps(example.get('context', {}))
                        
                        cursor.execute('''
                        INSERT INTO prompt_examples 
                        (prompt_id, input, expected_output, context)
                        VALUES (?, ?, ?, ?)
                        ''', (prompt_id, input_text, expected_output, context))
            
            # Update performance metrics
            if performance and isinstance(performance, dict):
                # Check if performance metrics exist
                cursor.execute("SELECT id FROM prompt_performance WHERE prompt_id = ?", (prompt_id,))
                existing_perf = cursor.fetchone()
                
                avg_tokens = performance.get('avg_tokens', 0)
                expected_response_tokens = performance.get('expected_response_tokens', 0)
                success_rate = performance.get('success_rate', 0)
                avg_response_time = performance.get('avg_response_time', 0)
                usage_count = performance.get('usage_count', 0)
                
                # Calculate quality score
                quality_score = success_rate * 0.7 + (1.0 - min(avg_response_time / 10.0, 1.0)) * 0.3
                
                if existing_perf:
                    # Update existing metrics
                    cursor.execute('''
                    UPDATE prompt_performance
                    SET avg_tokens = ?, expected_response_tokens = ?, 
                        success_count = ?, avg_response_time = ?, 
                        usage_count = ?, quality_score = ?,
                        last_used_at = ?
                    WHERE prompt_id = ?
                    ''', (avg_tokens, expected_response_tokens, 
                          int(success_rate * usage_count), avg_response_time, 
                          usage_count, quality_score, time.time(), prompt_id))
                else:
                    # Insert new metrics
                    perf_id = str(uuid.uuid4())
                    cursor.execute('''
                    INSERT INTO prompt_performance
                    (id, prompt_id, version, avg_tokens, expected_response_tokens, 
                     success_count, failure_count, avg_response_time, 
                     usage_count, last_used_at, quality_score)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (perf_id, prompt_id, version, avg_tokens, expected_response_tokens, 
                          int(success_rate * usage_count), int((1 - success_rate) * usage_count), 
                          avg_response_time, usage_count, time.time(), quality_score))
            
            # Update relationships
            if related_prompts:
                # Remove existing relationships
                cursor.execute("DELETE FROM prompt_relationships WHERE source_prompt_id = ?", (prompt_id,))
                
                # Add new relationships
                for related_id in related_prompts:
                    cursor.execute('''
                    INSERT INTO prompt_relationships
                    (source_prompt_id, target_prompt_id, relationship_type, created_at)
                    VALUES (?, ?, ?, ?)
                    ''', (prompt_id, related_id, 'related', time.time()))
            
            # Commit all changes
            self.conn.commit()
            
            # Update cache
            self._init_cache()
            
            logger.info(f"Successfully registered prompt {prompt_id} (version {version})")
            return prompt_id
            
        except Exception as e:
            logger.error(f"Error registering prompt: {str(e)}")
            traceback.print_exc()
            if self.conn:
                self.conn.rollback()
            return None
    
    def _add_prompt_version(self, prompt_id, version, content, author):
        """
        Add a new version of a prompt.
        
        Args:
            prompt_id: Prompt ID
            version: Version string
            content: Prompt content
            author: Author of the version
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not self.conn:
                self._init_db_connection()
                if not self.conn:
                    logger.error("Cannot add prompt version: database connection failed")
                    return False
                    
            cursor = self.conn.cursor()
            
            # Check if version already exists
            cursor.execute('''
            SELECT id FROM prompt_versions 
            WHERE prompt_id = ? AND version = ?
            ''', (prompt_id, version))
            
            existing = cursor.fetchone()
            
            if existing:
                # Update existing version
                cursor.execute('''
                UPDATE prompt_versions
                SET content = ?, author = ?
                WHERE prompt_id = ? AND version = ?
                ''', (json.dumps(content) if isinstance(content, dict) else content, 
                      author, prompt_id, version))
            else:
                # Create new version
                version_id = str(uuid.uuid4())
                cursor.execute('''
                INSERT INTO prompt_versions
                (id, prompt_id, version, content, created_at, author, is_active)
                VALUES (?, ?, ?, ?, ?, ?, 1)
                ''', (version_id, prompt_id, version, 
                      json.dumps(content) if isinstance(content, dict) else content, 
                      time.time(), author))
                
            # Success
            return True
            
        except Exception as e:
            logger.error(f"Error adding prompt version: {str(e)}")
            return False
    
    def track_performance(self, prompt_id, success=True, response_time=None, tokens=None):
        """
        Track performance metrics for a prompt.
        
        Args:
            prompt_id: Prompt ID to track
            success: Whether the prompt was successful
            response_time: Time taken to generate response
            tokens: Number of tokens in the response
            
        Returns:
            Updated performance metrics
        """
        try:
            if not self.conn:
                self._init_db_connection()
                if not self.conn:
                    logger.error("Cannot track performance: database connection failed")
                    return None
                    
            cursor = self.conn.cursor()
            
            # Check if prompt exists
            cursor.execute("SELECT current_version FROM prompt_registry WHERE prompt_id = ?", (prompt_id,))
            row = cursor.fetchone()
            
            if not row:
                logger.warning(f"Cannot track performance: prompt {prompt_id} not found")
                return None
                
            version = row['current_version']
            
            # Check if performance metrics exist
            cursor.execute('''
            SELECT id, success_count, failure_count, avg_response_time, usage_count, avg_tokens
            FROM prompt_performance WHERE prompt_id = ?
            ''', (prompt_id,))
            
            row = cursor.fetchone()
            
            if row:
                # Update existing metrics
                perf_id = row['id']
                success_count = row['success_count'] + (1 if success else 0)
                failure_count = row['failure_count'] + (0 if success else 1)
                
                # Update response time
                if response_time:
                    current_avg_time = row['avg_response_time'] or 0
                    usage_count = row['usage_count'] or 0
                    
                    if usage_count > 0:
                        # Weighted average
                        new_avg_time = ((current_avg_time * usage_count) + response_time) / (usage_count + 1)
                    else:
                        new_avg_time = response_time
                else:
                    new_avg_time = row['avg_response_time'] or 0
                
                # Update token count
                if tokens:
                    current_avg_tokens = row['avg_tokens'] or 0
                    usage_count = row['usage_count'] or 0
                    
                    if usage_count > 0:
                        # Weighted average
                        new_avg_tokens = ((current_avg_tokens * usage_count) + tokens) / (usage_count + 1)
                    else:
                        new_avg_tokens = tokens
                else:
                    new_avg_tokens = row['avg_tokens'] or 0
                
                # Update usage count
                new_usage_count = (row['usage_count'] or 0) + 1
                
                # Calculate success rate
                success_rate = success_count / (success_count + failure_count) if (success_count + failure_count) > 0 else 0
                
                # Calculate quality score
                quality_score = success_rate * 0.7 + (1.0 - min(new_avg_time / 10.0, 1.0)) * 0.3
                
                # Update metrics
                cursor.execute('''
                UPDATE prompt_performance
                SET success_count = ?, failure_count = ?, 
                    avg_response_time = ?, usage_count = ?, 
                    avg_tokens = ?, last_used_at = ?,
                    quality_score = ?
                WHERE id = ?
                ''', (success_count, failure_count, 
                      new_avg_time, new_usage_count, 
                      new_avg_tokens, time.time(),
                      quality_score, perf_id))
                
                self.conn.commit()
                
                # Return updated metrics
                return {
                    'success_rate': success_rate,
                    'avg_response_time': new_avg_time,
                    'usage_count': new_usage_count,
                    'avg_tokens': new_avg_tokens,
                    'quality_score': quality_score
                }
            else:
                # Create new metrics
                perf_id = str(uuid.uuid4())
                success_count = 1 if success else 0
                failure_count = 0 if success else 1
                
                # Calculate success rate
                success_rate = 1.0 if success else 0.0
                
                # Calculate quality score
                quality_score = success_rate * 0.7 + (1.0 - min((response_time or 0) / 10.0, 1.0)) * 0.3
                
                # Insert new metrics
                cursor.execute('''
                INSERT INTO prompt_performance
                (id, prompt_id, version, success_count, failure_count, 
                 avg_response_time, usage_count, avg_tokens, 
                 last_used_at, quality_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (perf_id, prompt_id, version, success_count, failure_count, 
                      response_time or 0, 1, tokens or 0, 
                      time.time(), quality_score))
                
                self.conn.commit()
                
                # Return initial metrics
                return {
                    'success_rate': success_rate,
                    'avg_response_time': response_time or 0,
                    'usage_count': 1,
                    'avg_tokens': tokens or 0,
                    'quality_score': quality_score
                }
                
        except Exception as e:
            logger.error(f"Error tracking performance for {prompt_id}: {str(e)}")
            if self.conn:
                self.conn.rollback()
            return None
    
    def get_best_prompt(self, agent_type, task_description, models=None):
        """
        Get the best performing prompt for a specific task.
        
        Args:
            agent_type: Type of agent requesting the prompt
            task_description: Description of the task
            models: Optional list of compatible models
            
        Returns:
            Best matching prompt dictionary
        """
        try:
            # Search for prompts matching the agent type and models
            prompts = self.search_prompts(agent_type=agent_type, models=models)
            
            if not prompts:
                logger.warning(f"No prompts found for agent_type={agent_type}")
                return None
                
            # Score prompts based on performance and relevance
            scored_prompts = []
            for prompt in prompts:
                # Get performance metrics
                cursor = self.conn.cursor()
                cursor.execute('''
                SELECT quality_score, usage_count 
                FROM prompt_performance 
                WHERE prompt_id = ?
                ''', (prompt['prompt_id'],))
                
                row = cursor.fetchone()
                performance_score = row['quality_score'] if row else 0.5
                usage_count = row['usage_count'] if row else 0
                
                # Calculate usage weight (more usage = more confidence)
                usage_weight = min(usage_count / 100.0, 1.0)
                
                # TODO: Implement semantic similarity scoring with task description
                # For now, use a placeholder relevance score
                relevance_score = 0.5
                
                # Calculate final score
                final_score = (performance_score * 0.6 * usage_weight) + (relevance_score * 0.4)
                
                scored_prompts.append((prompt, final_score))
                
            # Sort by score
            scored_prompts.sort(key=lambda x: x[1], reverse=True)
            
            # Return best prompt
            if scored_prompts:
                return scored_prompts[0][0]
            else:
                return None
                
        except Exception as e:
            logger.error(f"Error getting best prompt: {str(e)}")
            return None
        
    def validate_prompt(self, prompt_data):
        """
        Validate prompt data structure and content.
        
        Args:
            prompt_data: Prompt data to validate
            
        Returns:
            (bool, str): Tuple of (is_valid, error_message)
        """
        try:
            # Check if schema is available
            if not self.schema:
                logger.warning("No schema available for validation")
                return True, "No schema available for validation"
                
            # Validate against schema
            jsonschema.validate(instance=prompt_data, schema=self.schema)
            return True, ""
            
        except jsonschema.exceptions.ValidationError as e:
            return False, str(e)
        except Exception as e:
            return False, f"Validation error: {str(e)}"
    
    def fill_prompt_template(self, prompt_id, variables, version=None):
        """
        Fill a prompt template with the provided variables.
        
        Args:
            prompt_id: ID of the prompt template
            variables: Dictionary of variables to fill
            version: Optional specific version to use
            
        Returns:
            Filled prompt text
        """
        try:
            # Load the prompt
            prompt_data = self.load_prompt(prompt_id, version)
            if not prompt_data:
                logger.warning(f"Cannot fill template: prompt {prompt_id} not found")
                return None
                
            content = prompt_data['content']
            
            # Check if content is a dictionary with different stages
            if isinstance(content, dict):
                # Handle different content types/stages
                filled_content = {}
                for key, text in content.items():
                    filled_content[key] = self._fill_template_text(text, variables)
                return filled_content
            else:
                # Simple string content
                return self._fill_template_text(content, variables)
                
        except Exception as e:
            logger.error(f"Error filling prompt template: {str(e)}")
            return None
    
    def _fill_template_text(self, template_text, variables):
        """
        Fill a template text with the provided variables.
        
        Args:
            template_text: Template text with {{variable}} placeholders
            variables: Dictionary of variables to fill
            
        Returns:
            Filled text
        """
        if not template_text:
            return ""
            
        if not variables:
            return template_text
            
        result = template_text
        
        # First find all template variables in the text
        template_vars = re.findall(r'\{\{\s*([\w\.]+)\s*\}\}', result)
        
        # Process each template variable
        for var_path in template_vars:
            # Handle nested variables with dot notation (e.g., agent.name)
            if '.' in var_path:
                parts = var_path.split('.')
                # Navigate through the nested structure
                current_value = variables
                valid_path = True
                
                for part in parts:
                    if isinstance(current_value, dict) and part in current_value:
                        current_value = current_value[part]
                    else:
                        valid_path = False
                        break
                        
                if valid_path:
                    # Format the value appropriately
                    if isinstance(current_value, (dict, list)):
                        var_str = json.dumps(current_value, indent=2)
                    else:
                        var_str = str(current_value)
                        
                    # Replace in the template
                    pattern = r'\{\{\s*' + re.escape(var_path) + r'\s*\}\}'
                    result = re.sub(pattern, var_str, result)
            else:
                # Handle regular variables (no dots)
                if var_path in variables:
                    var_value = variables[var_path]
                    
                    # Format the value appropriately
                    if isinstance(var_value, (dict, list)):
                        var_str = json.dumps(var_value, indent=2)
                    else:
                        var_str = str(var_value)
                        
                    # Replace in the template
                    pattern = r'\{\{\s*' + re.escape(var_path) + r'\s*\}\}'
                    result = re.sub(pattern, var_str, result)
            
        return result
    
    def get_prompt_versions(self, prompt_id):
        """
        Get all versions of a prompt.
        
        Args:
            prompt_id: ID of the prompt
            
        Returns:
            List of version dictionaries
        """
        try:
            if not self.conn:
                self._init_db_connection()
                if not self.conn:
                    logger.error("Cannot get prompt versions: database connection failed")
                    return []
                    
            cursor = self.conn.cursor()
            cursor.execute('''
            SELECT id, version, created_at, author, changelog
            FROM prompt_versions
            WHERE prompt_id = ? AND is_active = 1
            ORDER BY created_at DESC
            ''', (prompt_id,))
            
            versions = []
            for row in cursor.fetchall():
                versions.append({
                    'id': row['id'],
                    'version': row['version'],
                    'created_at': row['created_at'],
                    'author': row['author'],
                    'changelog': row['changelog']
                })
                
            return versions
            
        except Exception as e:
            logger.error(f"Error getting prompt versions: {str(e)}")
            return []
    
    def delete_prompt(self, prompt_id):
        """
        Delete a prompt from the registry.
        
        Args:
            prompt_id: ID of the prompt to delete
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not self.conn:
                self._init_db_connection()
                if not self.conn:
                    logger.error("Cannot delete prompt: database connection failed")
                    return False
                    
            # Mark as inactive rather than actually deleting
            cursor = self.conn.cursor()
            cursor.execute('''
            UPDATE prompt_registry
            SET is_active = 0
            WHERE prompt_id = ?
            ''', (prompt_id,))
            
            cursor.execute('''
            UPDATE prompt_versions
            SET is_active = 0
            WHERE prompt_id = ?
            ''', (prompt_id,))
            
            self.conn.commit()
            
            # Update cache
            if prompt_id in self._prompt_cache:
                del self._prompt_cache[prompt_id]
                
            if prompt_id in self._version_cache:
                del self._version_cache[prompt_id]
                
            logger.info(f"Deleted prompt {prompt_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting prompt: {str(e)}")
            if self.conn:
                self.conn.rollback()
            return False
    
    def get_prompt_stats(self):
        """
        Get statistics about the prompt registry.
        
        Returns:
            Dict with statistics
        """
        try:
            if not self.conn:
                self._init_db_connection()
                if not self.conn:
                    logger.error("Cannot get prompt stats: database connection failed")
                    return {}
                    
            cursor = self.conn.cursor()
            
            # Get total prompt count
            cursor.execute("SELECT COUNT(*) FROM prompt_registry WHERE is_active = 1")
            prompt_count = cursor.fetchone()[0]
            
            # Get version count
            cursor.execute("SELECT COUNT(*) FROM prompt_versions WHERE is_active = 1")
            version_count = cursor.fetchone()[0]
            
            # Get top performers
            cursor.execute('''
            SELECT pr.prompt_id, pr.name, pp.quality_score, pp.usage_count
            FROM prompt_performance pp
            JOIN prompt_registry pr ON pp.prompt_id = pr.prompt_id
            WHERE pr.is_active = 1
            ORDER BY pp.quality_score DESC
            LIMIT 5
            ''')
            
            top_performers = []
            for row in cursor.fetchall():
                top_performers.append({
                    'prompt_id': row['prompt_id'],
                    'name': row['name'],
                    'quality_score': row['quality_score'],
                    'usage_count': row['usage_count']
                })
                
            # Get model stats
            cursor.execute('''
            SELECT model_id, COUNT(*) as count
            FROM model_compatibility
            GROUP BY model_id
            ORDER BY count DESC
            ''')
            
            model_stats = {}
            for row in cursor.fetchall():
                model_stats[row['model_id']] = row['count']
                
            # Get agent type stats
            cursor.execute('''
            SELECT agent_type, COUNT(*) as count
            FROM agent_compatibility
            GROUP BY agent_type
            ORDER BY count DESC
            ''')
            
            agent_stats = {}
            for row in cursor.fetchall():
                agent_stats[row['agent_type']] = row['count']
                
            return {
                'total_prompts': prompt_count,
                'total_versions': version_count,
                'top_performers': top_performers,
                'model_stats': model_stats,
                'agent_stats': agent_stats
            }
            
        except Exception as e:
            logger.error(f"Error getting prompt stats: {str(e)}")
            return {}
    
    def get_all_prompt_ids(self) -> List[str]:
        """
        Get list of all prompt IDs in the registry.
        
        Returns:
            List of all available prompt IDs
        """
        try:
            if not self.conn:
                self._init_db_connection()
                if not self.conn:
                    logger.error("Cannot get prompt IDs: database connection failed")
                    return []
                    
            cursor = self.conn.cursor()
            cursor.execute("SELECT prompt_id FROM prompt_registry WHERE is_active = 1")
            return [row[0] for row in cursor.fetchall()]
            
        except Exception as e:
            logger.error(f"Error getting all prompt IDs: {str(e)}")
            return []
    
    def _load_all_prompts(self) -> Dict[str, Any]:
        """
        Load all prompts from the directory and return loading results.
        
        Returns:
            Dictionary with 'loaded' and 'failed' prompt collections
        """
        try:
            results = {
                'loaded': {},
                'failed': {}
            }
            
            # Get all prompt files
            prompt_files = glob.glob(os.path.join(self.prompts_dir, "**/*.json"), recursive=True)
            
            for file_path in prompt_files:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        prompt_data = json.load(f)
                        
                    # Add default values and validate
                    prompt_data = self._add_default_values(prompt_data)
                    
                    # Validate against schema if available
                    if self.schema:
                        try:
                            jsonschema.validate(prompt_data, self.schema)
                        except jsonschema.ValidationError as ve:
                            results['failed'][prompt_data.get('prompt_id', file_path)] = f"Validation error: {str(ve)}"
                            continue
                    
                    # Store in loaded results
                    prompt_id = prompt_data.get('prompt_id', os.path.basename(file_path))
                    results['loaded'][prompt_id] = prompt_data
                    
                except Exception as e:
                    file_name = os.path.basename(file_path)
                    results['failed'][file_name] = str(e)
                    
            return results
            
        except Exception as e:
            logger.error(f"Error loading all prompts: {str(e)}")
            return {'loaded': {}, 'failed': {}}

    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
            logger.info("Closed database connection")

# Helper function to get a singleton instance
_prompt_registry_instance = None

def get_prompt_registry(db_path=None, prompts_dir=None, schema_path=None):
    """
    Get or create a singleton instance of the PromptRegistry.
    
    Args:
        db_path: Optional database path
        prompts_dir: Optional prompts directory
        schema_path: Optional schema path
        
    Returns:
        PromptRegistry instance
    """
    global _prompt_registry_instance
    
    if _prompt_registry_instance is None:
        _prompt_registry_instance = PromptRegistry(db_path, prompts_dir, schema_path)
        
    return _prompt_registry_instance

if __name__ == "__main__":
    # Example usage
    registry = PromptRegistry()
    stats = registry.load_prompts_from_directory()
    print(f"Loaded {stats['loaded']} prompts")
    print(f"Prompt stats: {registry.get_prompt_stats()}")