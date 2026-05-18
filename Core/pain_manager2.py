import logging
import json
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple
import traceback

from Core.pattern_manager import PatternManager
from Core.intent_processor import IntentProcessor
from Core.config import PATHS

# Import agent-related components for specialized agent integration
try:
    from Jarvis_Agent_SDK.jarvis_orchestrator import analyze_handler_capabilities
    from Handler.handler_agent_builder import AgentBuilder, AgentType, AgentSpecialization, AgentCapability, AgentTool
except ImportError:
    # Allow the handler to function even if agent components can't be imported
    print("Warning: Agent components not available - specialized agent features disabled")


# Database Schema Requirements
REQUIRED_TABLES = {
    'training_data': """
        CREATE TABLE IF NOT EXISTS training_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT NOT NULL,
            intent TEXT NOT NULL,
            metadata TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """,
    'pattern_data': """
        CREATE TABLE IF NOT EXISTS pattern_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            intent TEXT NOT NULL,
            pattern TEXT NOT NULL,
            priority INTEGER DEFAULT 1,
            metadata TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (intent) REFERENCES training_data(intent)
        )
    """,
    'format_history': """
        CREATE TABLE IF NOT EXISTS format_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            original_text TEXT NOT NULL,
            formatted_intent TEXT NOT NULL,
            confidence REAL,
            metadata TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """,
    'gpt_fallbacks': """
        CREATE TABLE IF NOT EXISTS gpt_fallbacks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT NOT NULL,
            response TEXT NOT NULL,
            metadata TEXT,
            processed BOOLEAN DEFAULT FALSE,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """,
    'boardroom_interactions': """
        CREATE TABLE IF NOT EXISTS boardroom_interactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_text TEXT NOT NULL,
            final_decision TEXT NOT NULL,
            metrics TEXT,
            consensus_score REAL,
            metadata TEXT,
            processed BOOLEAN DEFAULT FALSE,
            training_value BOOLEAN DEFAULT TRUE,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """
}

class PainManager2:
    def __init__(self, db_connection=None):
        """Initialize PainManager2 with database connection."""
        self.db_connection = db_connection
        self.pattern_manager = PatternManager(
            backup_dir=PATHS["CORE_DIR"] / "backups",
            cache_dir=PATHS["CACHE_DIR"]
        )
        self.intent_processor = IntentProcessor()
        
    async def initialize(self):
        """Initialize the database schema."""
        try:
            # Create format_history table if not exists
            async with self.db_connection._async_conn.execute("""
                CREATE TABLE IF NOT EXISTS format_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source TEXT NOT NULL,
                    original_text TEXT NOT NULL,
                    formatted_intent TEXT NOT NULL,
                    confidence REAL,
                    metadata TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """) as cursor:
                await self.db_connection._async_conn.commit()
            
            # Create indexes for better performance
            async with self.db_connection._async_conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_format_source 
                ON format_history(source)
            """) as cursor:
                await self.db_connection._async_conn.commit()
            
            async with self.db_connection._async_conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_format_history_source_text 
                ON format_history(source, original_text)
            """) as cursor:
                await self.db_connection._async_conn.commit()
            
            return True
            
        except Exception as e:
            logging.error(f"Error initializing database schema: {e}")
            logging.error(traceback.format_exc())
            return False
        
    async def format_and_store_fallback(self, text: str, response: str, metadata: Dict = None) -> bool:
        """
        Format GPT fallback data and store in database with proper intent/pattern structure.
        """
        try:
            # Extract potential intent from response or metadata
            intent = self._extract_intent(response, metadata)
            if not intent:
                logging.warning(f"Could not determine intent for text: {text}")
                return False
                
            # Format as intent example
            intent_data = {
                "text": text,
                "intent": intent,
                "metadata": json.dumps({
                    "source": "gpt_fallback",
                    "original_response": response,
                    "formatted_timestamp": datetime.now().isoformat(),
                    **(metadata or {})
                })
            }
            
            # Create corresponding pattern
            pattern_data = self.pattern_manager.create_patterns(intent, [text])[0]
            pattern_entry = {
                "intent": intent,
                "pattern": json.dumps(pattern_data["pattern"]),
                "priority": pattern_data.get("priority", 1),
                "metadata": json.dumps({
                    "source": "gpt_fallback",
                    "formatted_timestamp": datetime.now().isoformat()
                })
            }
            
            try:
                # Store training data
                async with self.db_connection._async_conn.execute(
                    """
                    INSERT INTO training_data (text, intent, metadata)
                    VALUES (:text, :intent, :metadata)
                    """,
                    intent_data
                ) as cursor:
                    await self.db_connection._async_conn.commit()
                
                # Store pattern data
                async with self.db_connection._async_conn.execute(
                    """
                    INSERT INTO pattern_data (intent, pattern, priority, metadata)
                    VALUES (:intent, :pattern, :priority, :metadata)
                    """,
                    pattern_entry
                ) as cursor:
                    await self.db_connection._async_conn.commit()
                
                # Record in format history
                async with self.db_connection._async_conn.execute(
                    """
                    INSERT INTO format_history 
                    (source, original_text, formatted_intent, confidence, metadata)
                    VALUES ('gpt_fallback', :text, :intent, :confidence, :metadata)
                    """,
                    {
                        "text": text,
                        "intent": intent,
                        "confidence": 0.7,  # Default confidence for GPT fallback
                        "metadata": intent_data["metadata"]
                    }
                ) as cursor:
                    await self.db_connection._async_conn.commit()
                
                logging.info(f"Successfully formatted and stored fallback data for intent: {intent}")
                return True
                
            except Exception as e:
                logging.error(f"Database error storing fallback: {e}")
                return False
                
        except Exception as e:
            logging.error(f"Error formatting fallback: {e}")
            return False
            
    async def format_and_store_boardroom(self, request: str, decision: str, metadata: Dict) -> bool:
        """
        Format boardroom interaction data and store in database with proper intent/pattern structure.
        """
        try:
            # Extract intent from decision or metadata
            intent = metadata.get('suggested_intent') or self._extract_intent(decision, metadata)
            if not intent:
                logging.warning(f"Could not determine intent for boardroom request: {request}")
                return False
                
            # Format as intent example with higher confidence due to boardroom validation
            intent_data = {
                "text": request,
                "intent": intent,
                "metadata": json.dumps({
                    "source": "boardroom",
                    "decision": decision,
                    "confidence": metadata.get('consensus_score', 0.8),
                    "formatted_timestamp": datetime.now().isoformat(),
                    **metadata
                })
            }
            
            # Create corresponding pattern
            pattern_data = self.pattern_manager.create_patterns(intent, [request])[0]
            pattern_entry = {
                "intent": intent,
                "pattern": json.dumps(pattern_data["pattern"]),
                "priority": pattern_data.get("priority", 2),  # Higher priority for boardroom
                "metadata": json.dumps({
                    "source": "boardroom",
                    "formatted_timestamp": datetime.now().isoformat()
                })
            }
            
            cursor = self.db_connection.cursor()
            try:
                # Begin transaction
                cursor.execute("BEGIN TRANSACTION")
                
                # Store training data
                cursor.execute(
                    """
                    INSERT INTO training_data (text, intent, metadata)
                    VALUES (:text, :intent, :metadata)
                    """,
                    intent_data
                )
                
                # Store pattern data
                cursor.execute(
                    """
                    INSERT INTO pattern_data (intent, pattern, priority, metadata)
                    VALUES (:intent, :pattern, :priority, :metadata)
                    """,
                    pattern_entry
                )
                
                # Record in format history
                cursor.execute(
                    """
                    INSERT INTO format_history 
                    (source, original_text, formatted_intent, confidence, metadata)
                    VALUES ('boardroom', :text, :intent, :confidence, :metadata)
                    """,
                    {
                        "text": request,
                        "intent": intent,
                        "confidence": metadata.get('consensus_score', 0.8),
                        "metadata": intent_data["metadata"]
                    }
                )
                
                # Commit transaction
                self.db_connection.commit()
                logging.info(f"Successfully formatted and stored boardroom data for intent: {intent}")
                return True
                
            except Exception as e:
                self.db_connection.rollback()
                raise e
            
        except Exception as e:
            logging.error(f"Error formatting boardroom data: {e}")
            return False
    
    def _extract_intent(self, response: str, metadata: Dict = None) -> str:
        """
        Extract intent from response or metadata using various methods.
        Returns standardized intent string or None if no intent could be determined.
        """
        # First check metadata for suggested intent
        if metadata and 'suggested_intent' in metadata:
            return metadata['suggested_intent'].upper()
            
        # Common intent patterns with more variations and case insensitivity
        common_intents = {
            # Email patterns - handle variations of open/check/view email
            r'(?i)\b(?:open|launch|start|check|view|show|access|get|read|hope\s+in)\s+(?:my\s+)?(?:email|emails|mail|inbox|gmail|outlook)\b': 'OPEN_EMAIL',
            r'(?i)\b(?:write|send|compose)\s+(?:an?\s+)?(?:email|mail|message)\b': 'COMPOSE_EMAIL',
            
            # Calendar patterns - handle variations of open/check calendar
            r'(?i)\b(?:open|check|view|show|access|get|see|display)\s+(?:my\s+)?(?:calendar|schedule|appointments|meetings)\b': 'OPEN_CALENDAR',
            r'(?i)\b(?:what|any|check|view)\s+(?:meetings|appointments)\s+(?:do\s+i\s+have|today|tomorrow)\b': 'CHECK_CALENDAR',
            r'(?i)\b(?:i\s+have\s+meetings|check\s+appointments)\b': 'CHECK_CALENDAR',
            
            # Application patterns - handle variations of open/launch apps
            r'(?i)\b(?:open|launch|start)\s+(?:microsoft\s+)?teams\b': 'OPEN_TEAMS',
            r'(?i)\b(?:open|launch|start)\s+(?:code\s*runner)\b': 'OPEN_CODERUNNER',
            r'(?i)\b(?:open|launch|start)\s+(?:safari|browser)\b': 'OPEN_SAFARI',
            r'(?i)\b(?:open|launch|start)\s+(?:finder)\b': 'OPEN_FINDER',
            r'(?i)\b(?:open|launch|start)\s+(?:face\s*time)\b': 'OPEN_FACETIME',
            r'(?i)\b(?:open|launch|start)\s+(?:pages)\b': 'OPEN_PAGES',
            r'(?i)\b(?:open|launch|start)\s+(?:excel|spreadsheet)\b': 'OPEN_EXCEL',
            r'(?i)\b(?:open|launch|start)\s+(?:final\s*cut)\b': 'OPEN_FINALCUT',
            r'(?i)\b(?:open|launch|start)\s+(?:cursor)\b': 'OPEN_CURSOR',
            r'(?i)\b(?:open|launch|start)\s+(?:note\s*pad)\b': 'OPEN_NOTEPAD',
            
            # Information queries
            r'(?i)\b(?:check|show|tell|what\'s|whats|how\'s|hows)\s+(?:the\s+)?weather\b': 'CHECK_WEATHER',
            r'(?i)\b(?:calculate|what\'s|whats|find)\s+(?:the\s+)?(?:square\s+root|sqrt)\b': 'CALCULATE_MATH',
            r'(?i)\b(?:what|which|tell\s+me)\s+(?:day|date)\b': 'CHECK_DATE',
            
            # Research and search
            r'(?i)\b(?:research|search|find|look\s+up|google)\s+.+': 'WEB_SEARCH',
            r'(?i)\b(?:database|query|sql)\b': 'DATABASE_QUERY',
            
            # System commands
            r'(?i)\b(?:open|launch|start)\s+(?:my\s+)?(?:mac\s*book|laptop|computer)\b': 'SYSTEM_OPEN',
            r'(?i)\b(?:make\s+life\s+easier|help\s+me)\b': 'GENERAL_HELP'
        }
        
        # Check text against common patterns first
        text_to_check = response.strip()
        for pattern, intent in common_intents.items():
            if re.search(pattern, text_to_check):
                return intent
                
        # Try to extract from response
        # Look for explicit intent mentions
        intent_patterns = [
            r'(?i)intent[:\s]+([A-Z_]+)',
            r'(?i)classify.*as[:\s]+([A-Z_]+)',
            r'(?i)category[:\s]+([A-Z_]+)',
            r'(?i)command[:\s]+([A-Z_]+)',
            r'(?i)action[:\s]+([A-Z_]+)'
        ]
        
        for pattern in intent_patterns:
            match = re.search(pattern, text_to_check)
            if match:
                return match.group(1).upper()
                
        # If no intent found, try to infer from context
        text_lower = text_to_check.lower()
        if any(word in text_lower for word in ['moon', 'space', 'planet', 'galaxy']):
            return 'SPACE_INFO'
        elif any(word in text_lower for word in ['database', 'query', 'sql']):
            return 'DATABASE_QUERY'
        elif any(word in text_lower for word in ['research', 'search', 'find', 'look up']):
            return 'WEB_SEARCH'
            
        # If no intent found, return None
        return None

    async def process_pending_data(self):
        """Process any unformatted GPT fallbacks and boardroom data that hasn't been processed yet."""
        try:
            # Initialize database first
            if not await self.initialize():
                logging.error("Failed to initialize database schema")
                return False
            
            # Initialize intent processor
            intent_processor = IntentProcessor()
            processed_count = 0
            
            # Process unformatted GPT fallbacks
            async with self.db_connection._async_conn.execute("""
                SELECT text, response, metadata 
                FROM gpt_fallbacks 
                WHERE (processed IS NULL OR processed = FALSE)
                AND text NOT IN (
                    SELECT original_text 
                    FROM format_history 
                    WHERE source = 'gpt_fallback'
                )
            """) as cursor:
                fallbacks = await cursor.fetchall()
                
            if fallbacks:
                logging.info(f"Found {len(fallbacks)} unprocessed GPT fallbacks")
                for text, response, metadata in fallbacks:
                    try:
                        # First process through intent processor
                        processed_intent = intent_processor.process_intent(text, json.loads(metadata) if metadata else None)
                        if not processed_intent:
                            continue
                            
                        # Format the intent
                        formatted_intent = intent_processor.format_intent(processed_intent)
                        if not formatted_intent:
                            continue
                            
                        # Store formatted intent in format_history
                        async with self.db_connection._async_conn.execute("""
                            INSERT INTO format_history (original_text, formatted_intent, source, confidence, metadata)
                            VALUES (?, ?, 'gpt_fallback', 1.0, ?)
                        """, (text, json.dumps(formatted_intent), json.dumps(metadata) if metadata else None)) as cursor:
                            await self.db_connection._async_conn.commit()
                        
                        # Update GPT fallback as processed
                        async with self.db_connection._async_conn.execute("""
                            UPDATE gpt_fallbacks 
                            SET processed = TRUE,
                                metadata = json_set(metadata, '$.processed_timestamp', json(?))
                            WHERE text = ? AND response = ?
                        """, (json.dumps(datetime.now().isoformat()), text, response)) as cursor:
                            await self.db_connection._async_conn.commit()
                        
                        processed_count += 1
                    except Exception as e:
                        logging.error(f"Error processing fallback: {e}")
                        continue
            
            # Process unformatted boardroom data
            async with self.db_connection._async_conn.execute("""
                SELECT request_text, final_decision, metrics, consensus_score, metadata
                FROM boardroom_interactions 
                WHERE (processed IS NULL OR processed = FALSE)
                AND training_value = TRUE
                AND request_text NOT IN (
                    SELECT original_text 
                    FROM format_history 
                    WHERE source = 'boardroom'
                )
            """) as cursor:
                boardroom_data = await cursor.fetchall()
                
            if boardroom_data:
                logging.info(f"Found {len(boardroom_data)} unprocessed boardroom interactions")
                for request, decision, metrics, score, meta in boardroom_data:
                    try:
                        metadata = {
                            'consensus_score': score,
                            'metrics': json.loads(metrics) if metrics else {},
                            'source': 'boardroom',
                            **(json.loads(meta) if meta else {})
                        }
                        
                        # Process through intent processor
                        processed_intent = intent_processor.process_intent(request, metadata)
                        if not processed_intent:
                            continue
                            
                        # Format the intent
                        formatted_intent = intent_processor.format_intent(processed_intent)
                        if not formatted_intent:
                            continue
                            
                        # Store formatted intent in format_history
                        async with self.db_connection._async_conn.execute("""
                            INSERT INTO format_history (original_text, formatted_intent, source, confidence, metadata)
                            VALUES (?, ?, 'boardroom', ?, ?)
                        """, (request, json.dumps(formatted_intent), score, json.dumps(metadata))) as cursor:
                            await self.db_connection._async_conn.commit()
                            
                        # Update boardroom interaction as processed
                        async with self.db_connection._async_conn.execute("""
                            UPDATE boardroom_interactions 
                            SET processed = TRUE,
                                metadata = json_set(metadata, '$.processed_timestamp', json(?))
                            WHERE request_text = ? AND final_decision = ?
                        """, (json.dumps(datetime.now().isoformat()), request, decision)) as cursor:
                            await self.db_connection._async_conn.commit()
                            
                        processed_count += 1
                    except Exception as e:
                        logging.error(f"Error processing boardroom data: {e}")
                        continue
            
            logging.info(f"Successfully processed {processed_count} items")
            return True
            
        except Exception as e:
            logging.error(f"Error processing pending data: {e}")
            logging.error(traceback.format_exc())
            return False 