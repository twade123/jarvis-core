"""Module for enhanced pattern-to-intent mapping functionality."""

import logging
import spacy
import sqlite3
import json
import os
from typing import Dict, List, Set, Tuple, Any, Union
from collections import defaultdict
import traceback
from Handler.database_utils import DatabaseConnection

# Import agent-related components for specialized agent integration
try:
  from Jarvis_Agent_SDK.jarvis_orchestrator import analyze_handler_capabilities
  from Handler.handler_agent_builder import AgentBuilder, AgentType, AgentSpecialization, AgentCapability, AgentTool
except ImportError:
  # Allow the handler to function even if agent components can't be imported
  print("Warning: Agent components not available - specialized agent features disabled")

logging.basicConfig(
    filename='handler_analyzer_debug.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class PatternIntentMapper(DatabaseConnection):
    """Handles advanced pattern to intent mapping with layered matching."""
    
    def __init__(self, db_connection):
        """Initialize the mapper with spaCy model and database connection."""
        super().__init__(db_connection)
        
        try:
            self.nlp = spacy.load('en_core_web_md')
            self.similarity_cache = {}
            self.intent_cache = {}
            self.similarity_thresholds = {
                'exact': 1.0,
                'high': 0.8,
                'medium': 0.6,
                'low': 0.4
            }
            
            # Initialize empty pattern lists
            self.docstring_patterns = []
            self.docstring_intents = []
            
            if self.conn:
                logging.info("Connected to database successfully")
                self._load_docstring_data()
                
        except Exception as e:
            logging.error(f"Error initializing PatternIntentMapper: {e}")
            raise
        
    def _load_docstring_patterns(self) -> List[Dict[str, Any]]:
        """Load patterns from docstrings"""
        try:
            self.cursor.execute('''
                SELECT d.id, d.file_path, d.module_docstring, d.class_docstrings, 
                       d.function_docstrings, d.patterns, d.capabilities, d.examples
                FROM docstrings d
            ''')
            docstring_data = self.cursor.fetchall()
            
            patterns = []
            for (doc_id, file_path, module_doc, class_docs, func_docs, 
                 pattern_text, capabilities, examples) in docstring_data:
                
                # Get handler name from file path
                handler_name = os.path.basename(file_path).replace('handler_', '').replace('.py', '')
                
                # Process module docstring
                if module_doc:
                    try:
                        doc_json = json.loads(module_doc)
                        if isinstance(doc_json, dict) and 'title' in doc_json:
                            for title_data in doc_json['title']:
                                patterns.append({
                                    'text': title_data['text'],
                                    'type': 'module_description',
                                    'source': handler_name,
                                    'weight': title_data.get('weight', 1.0)
                                })
                    except json.JSONDecodeError:
                        logging.warning(f"Could not parse module docstring JSON for {file_path}")
                
                # Process capabilities
                if capabilities:
                    try:
                        cap_list = json.loads(capabilities)
                        for cap in cap_list:
                            patterns.append({
                                'text': cap,
                                'type': 'capability',
                                'source': handler_name,
                                'weight': 1.5  # High weight for capabilities
                            })
                    except json.JSONDecodeError:
                        logging.warning(f"Could not parse capabilities JSON for {file_path}")
                
                # Process patterns
                if pattern_text:
                    try:
                        pattern_list = json.loads(pattern_text)
                        for pat in pattern_list:
                            patterns.append({
                                'text': pat,
                                'type': 'pattern',
                                'source': handler_name,
                                'weight': 1.4  # High weight for explicit patterns
                            })
                    except json.JSONDecodeError:
                        logging.warning(f"Could not parse patterns JSON for {file_path}")
                
                # Process examples
                if examples:
                    try:
                        example_list = json.loads(examples)
                        for ex in example_list:
                            patterns.append({
                                'text': ex,
                                'type': 'example',
                                'source': handler_name,
                                'weight': 1.1  # Medium weight for examples
                            })
                    except json.JSONDecodeError:
                        logging.warning(f"Could not parse examples JSON for {file_path}")
            
            logging.info(f"Loaded {len(patterns)} patterns from docstrings")
            return patterns
            
        except Exception as e:
            logging.error(f"Error loading docstring patterns: {e}")
            logging.error(traceback.format_exc())
            return []
        
    def _load_handler_patterns(self) -> List[Dict[str, Any]]:
        """Load patterns from handlers"""
        try:
            self.cursor.execute('''
                SELECT p.id, p.handler_name, p.pattern_type, p.pattern
                FROM pattern_mapping p
            ''')
            pattern_data = self.cursor.fetchall()
            
            patterns = []
            for pat_id, handler, pat_type, pattern in pattern_data:
                patterns.append({
                    'text': pattern,
                    'type': pat_type,
                    'source': handler,
                    'weight': 1.0
                })
            
            return patterns
            
        except Exception as e:
            logging.error(f"Error loading handler patterns: {e}")
            return []
        
    def _load_intent_patterns(self) -> List[Dict[str, Any]]:
        """Load patterns from intents"""
        try:
            self.cursor.execute('''
                SELECT i.id, i.name, i.category, e.text
                FROM intents i
                LEFT JOIN examples e ON e.intent_id = i.id
            ''')
            intent_data = self.cursor.fetchall()
            
            patterns = []
            for int_id, name, category, example in intent_data:
                # Add intent name as pattern
                patterns.append({
                    'text': name.replace('_', ' ').lower(),
                    'type': 'intent_name',
                    'source': category,
                    'weight': 1.2
                })
                
                # Add example if exists
                if example:
                    patterns.append({
                        'text': example,
                        'type': 'intent_example',
                        'source': name,
                        'weight': 1.0
                    })
            
            return patterns
            
        except Exception as e:
            logging.error(f"Error loading intent patterns: {e}")
            return []

    def _load_docstring_data(self):
        """Load docstring patterns and intents from the database."""
        try:
            logging.info("Starting to load docstring data from database")
            
            # Get intents data
            self.cursor.execute('''
                SELECT i.name, i.category, e.text as example
                FROM intents i
                LEFT JOIN examples e ON e.intent_id = i.id
                ORDER BY i.category, i.name
            ''')
            intent_data = self.cursor.fetchall()
            
            logging.info(f"Found {len(intent_data)} intent entries in database")
            
            self.docstring_patterns = []
            self.docstring_intents = []
            
            # Group examples by intent
            intent_examples = defaultdict(list)
            for name, category, example in intent_data:
                if example:
                    intent_examples[name].append(example)
            
            # Process intents
            for name, category, _ in intent_data:
                if name not in self.docstring_intents:  # Avoid duplicates
                    intent = {
                        'name': name,
                        'category': category,
                        'examples': intent_examples.get(name, []),
                        'type': 'docstring'
                    }
                    self.docstring_intents.append(intent)
                    
                    # Create pattern from name
                    pattern = {
                        'pattern': name.replace('_', ' ').lower(),
                        'type': 'docstring',
                        'category': category
                    }
                    self.docstring_patterns.append(pattern)
            
            logging.info(f"Successfully loaded {len(self.docstring_patterns)} docstring patterns and {len(self.docstring_intents)} docstring intents")
            
        except Exception as e:
            logging.error(f"Error loading docstring data: {e}")
            logging.error(traceback.format_exc())
            self.docstring_patterns = []
            self.docstring_intents = []

    def _extract_pattern_text(self, pattern: Union[str, Dict, List]) -> str:
        """Extract text from a pattern, handling various formats."""
        if isinstance(pattern, str):
            return pattern
        elif isinstance(pattern, list):
            # Join list elements if they're strings
            if all(isinstance(x, str) for x in pattern):
                return ' '.join(pattern)
            # Handle spaCy token patterns
            return ' '.join(token.get('TEXT', token.get('LOWER', '')) 
                          for token in pattern if isinstance(token, dict))
        elif isinstance(pattern, dict):
            # Try common pattern keys
            for key in ['pattern', 'text', 'string']:
                if key in pattern:
                    value = pattern[key]
                    if isinstance(value, (str, list)):
                        return self._extract_pattern_text(value)
            return str(pattern)
        return str(pattern)

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two texts, handling empty vectors."""
        cache_key = (text1, text2)
        if cache_key in self.similarity_cache:
            return self.similarity_cache[cache_key]

        try:
            # Process texts with spaCy
            doc1 = self.nlp(text1)
            doc2 = self.nlp(text2)

            # If either document has no vector, fall back to token overlap
            if not doc1.vector_norm or not doc2.vector_norm:
                tokens1 = set(token.lower_ for token in doc1)
                tokens2 = set(token.lower_ for token in doc2)
                if not tokens1 or not tokens2:
                    return 0.0
                overlap = len(tokens1 & tokens2)
                similarity = overlap / max(len(tokens1), len(tokens2))
            else:
                similarity = doc1.similarity(doc2)

            self.similarity_cache[cache_key] = similarity
            return similarity
        except Exception as e:
            logging.error(f"Error calculating similarity: {e}")
            return 0.0

    def map_patterns_to_intents(self, patterns: List[Union[str, Dict]], loaded_intents: Dict[str, Dict] = None, loaded_patterns: List[Dict] = None, handler_type: str = None) -> List[Dict]:
        logging.info("Starting pattern-to-intent mapping")
        matches = []
        patterns_to_map = loaded_patterns if loaded_patterns is not None else patterns
        
        # Add docstring patterns to patterns_to_map if they match handler_type
        if handler_type:
            patterns_to_map.extend([
                p for p in self.docstring_patterns 
                if p.get('category', '').lower() == handler_type.lower()
            ])
        
        # Convert string patterns to dict format
        normalized_patterns = []
        for pattern in patterns_to_map:
            if isinstance(pattern, str):
                normalized_patterns.append({
                    'type': 'GENERIC',
                    'pattern': pattern,
                    'category': handler_type
                })
            else:
                normalized_patterns.append(pattern)
        
        all_intents = {}
        if loaded_intents:
            # Convert list of intents to dictionary
            for intent in loaded_intents:
                if isinstance(intent, dict) and 'intent' in intent:
                    all_intents[intent['intent']] = intent
        for intent in self.docstring_intents:
            if handler_type and intent.get('category', '').lower() == handler_type.lower():
                all_intents[intent['name']] = intent

        logging.info(f"Available handler types: {list(all_intents.keys())}")

        for pattern in normalized_patterns:
            try:
                pattern_text = self._extract_pattern_text(pattern)
                logging.debug(f"Pattern to map: {pattern_text}")
                
                exact_matches = self._find_exact_matches(pattern_text, all_intents)
                if exact_matches:
                    for intent_name in exact_matches:
                        logging.info(f"Exact match found: {intent_name} for pattern: {pattern_text}")
                        matches.append({
                            'pattern': pattern,
                            'intent': intent_name,
                            'score': 1.0,
                            'match_type': 'exact'
                        })
                    continue

                semantic_matches = self._find_semantic_matches(pattern_text, all_intents)
                if semantic_matches:
                    for intent_name, score in semantic_matches:
                        logging.info(f"Semantic match found: {intent_name} with score: {score} for pattern: {pattern_text}")
                        if score >= self.similarity_thresholds['medium']:
                            matches.append({
                                'pattern': pattern,
                                'intent': intent_name,
                                'score': score,
                                'match_type': 'semantic'
                            })
                    continue

                pattern_matches = self._find_pattern_matches(pattern_text, all_intents)
                if pattern_matches:
                    for intent_name, score in pattern_matches:
                        logging.info(f"Pattern match found: {intent_name} with score: {score} for pattern: {pattern_text}")
                        if score >= self.similarity_thresholds['low']:
                            matches.append({
                                'pattern': pattern,
                                'intent': intent_name,
                                'score': score,
                                'match_type': 'pattern'
                            })

            except Exception as e:
                logging.error(f"Error processing pattern {pattern}: {e}")
                continue

        logging.info(f"Completed pattern-to-intent mapping with {len(matches)} matches found")
        return matches

    def _find_exact_matches(self, pattern_text: str, intents: Dict[str, Dict]) -> List[str]:
        """Find exact matches between pattern text and intents."""
        matches = []
        pattern_text = pattern_text.lower()
        
        for intent_name, intent_data in intents.items():
            # Check intent name
            if intent_name.lower() == pattern_text:
                matches.append(intent_name)
                continue
                
            # Check examples
            examples = intent_data.get('examples', [])
            if isinstance(examples, list):
                for example in examples:
                    if isinstance(example, str) and example.lower() == pattern_text:
                        matches.append(intent_name)
                        break
                    elif isinstance(example, dict) and example.get('text', '').lower() == pattern_text:
                        matches.append(intent_name)
                        break
        
        return matches

    def _find_semantic_matches(self, pattern_text: str, intents: Dict[str, Dict]) -> List[Tuple[str, float]]:
        """Find semantic matches between pattern text and intents."""
        matches = []
        
        for intent_name, intent_data in intents.items():
            best_score = 0.0
            
            # Compare with intent name
            score = self._calculate_similarity(pattern_text, intent_name)
            best_score = max(best_score, score)
            
            # Compare with description
            description = intent_data.get('description', '')
            if description:
                score = self._calculate_similarity(pattern_text, description)
                best_score = max(best_score, score)
            
            # Compare with examples
            examples = intent_data.get('examples', [])
            if isinstance(examples, list):
                for example in examples:
                    if isinstance(example, str):
                        score = self._calculate_similarity(pattern_text, example)
                    elif isinstance(example, dict):
                        score = self._calculate_similarity(pattern_text, example.get('text', ''))
                    best_score = max(best_score, score)
            
            if best_score > 0:
                matches.append((intent_name, best_score))
        
        return sorted(matches, key=lambda x: x[1], reverse=True)

    def _find_pattern_matches(self, pattern_text: str, intents: Dict[str, Dict]) -> List[Tuple[str, float]]:
        """Find pattern-based matches using token overlap."""
        matches = []
        pattern_tokens = set(token.lower_ for token in self.nlp(pattern_text))
        
        for intent_name, intent_data in intents.items():
            best_score = 0.0
            
            # Get all text to compare
            texts_to_compare = [
                intent_name,
                intent_data.get('description', ''),
                *[ex if isinstance(ex, str) else ex.get('text', '')
                  for ex in intent_data.get('examples', [])
                  if isinstance(ex, (str, dict))]
            ]
            
            for text in texts_to_compare:
                text_tokens = set(token.lower_ for token in self.nlp(text))
                if text_tokens:
                    overlap = len(pattern_tokens & text_tokens)
                    score = overlap / max(len(pattern_tokens), len(text_tokens))
                    best_score = max(best_score, score)
            
            if best_score > 0:
                matches.append((intent_name, best_score))
        
        return sorted(matches, key=lambda x: x[1], reverse=True)

    def map_pattern_to_intents(self, pattern: str, pattern_type: str) -> List[Dict[str, Any]]:
        """Map a given pattern to potential intents based on similarity."""
        try:
            logging.debug(f"Mapping pattern: {pattern} of type: {pattern_type}")
            # Implement logic to map pattern to intents
            # This is a placeholder for actual mapping logic
            mapped_intents = []  # Replace with actual mapping logic
            logging.debug(f"Mapped intents: {mapped_intents}")
            return mapped_intents
        except Exception as e:
            logging.error(f"Error mapping pattern to intents: {e}")
            return [] 