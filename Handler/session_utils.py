#!/usr/bin/env python3
"""
Session & Workspace Utilities — Extracted from claude_interface.py (Phase 4).

These are the conversation/workspace management functions that other modules
depend on. Everything else in claude_interface.py (terminal UI, REPL loop,
input handling) is replaced by OpenClaw.

Architecture:
- Every user conversation gets a workspace_id at creation
- Workspace stays with the conversation as it grows into a project
- Conversation aggregator finds/connects related workspaces
- Boardroom monitors workspaces, never creates them

Functions:
- generate_workspace_id(): Create unique workspace ID from user request
- get_user_primary_workspace(): Find user's most recent workspace
- create_workspace_in_database(): Persist workspace to shard DB
- save_conversation_to_workspace(): Save conversation turn to workspace
- get_conversation_history(): Load conversation history for context
- save_conversation_messages(): Batch save conversation messages
"""

import hashlib
import json
import logging
import os
import re
import sqlite3
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger("session_utils")

# Database paths
DATABASE_DIR = os.path.expanduser("~/jarvis/Database")
SHARD_COUNT = 4


def generate_workspace_id(user_request: str, user_id: int) -> str:
    """
    Generate unique workspace_id from natural language request.
    Format: ws_<key_terms>_<hash>_<timestamp>
    
    Example: "analyze EUR_USD trading data" → ws_analyze_eur_usd_a8f3d512_1727856000
    """
    try:
        content_hash = hashlib.md5(user_request.encode()).hexdigest()[:8]
        
        words = re.findall(r'\b[a-z]{3,}\b', user_request.lower())
        stopwords = {'the', 'and', 'for', 'with', 'from', 'that', 'this', 'have', 
                     'will', 'can', 'need', 'want', 'about', 'into', 'than', 'them',
                     'then', 'some', 'make', 'like', 'time', 'when', 'what', 'which',
                     'their', 'would', 'there', 'could', 'should', 'our', 'out', 'all'}
        key_terms = [w for w in words if w not in stopwords][:3]
        term_slug = '_'.join(key_terms) if key_terms else 'workspace'
        timestamp = int(time.time())
        
        workspace_id = f"ws_{term_slug}_{content_hash}_{timestamp}"
        logger.info(f"Created workspace_id: {workspace_id} for user_id={user_id}")
        return workspace_id
        
    except Exception as e:
        logger.warning(f"Failed to generate workspace_id: {e}")
        return f"ws_fallback_{int(time.time())}"


def get_user_primary_workspace(user_id) -> str:
    """
    Find user's most recently updated workspace across shard databases.
    Used for CONTINUING conversations, not new requests.
    
    Returns workspace_id or 'admin_workspace' as fallback.
    """
    try:
        for shard_num in range(SHARD_COUNT):
            shard_path = os.path.join(DATABASE_DIR, f"workspace_shard_0{shard_num}.db")
            if not os.path.exists(shard_path):
                continue
            try:
                conn = sqlite3.connect(shard_path, isolation_level=None)
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT workspace_id, updated_at FROM workspaces
                    WHERE owner_id = ? OR owner_id = ? OR owner_id = ?
                    ORDER BY updated_at DESC LIMIT 1
                """, (f"user_{user_id}", str(user_id), 
                      int(user_id) if isinstance(user_id, str) and str(user_id).isdigit() else user_id))
                result = cursor.fetchone()
                conn.close()
                if result:
                    logger.info(f"Found workspace '{result[0]}' for user_id={user_id} in shard {shard_num}")
                    return result[0]
            except Exception as e:
                logger.debug(f"Error checking shard {shard_num}: {e}")
                continue
        
        logger.info(f"No workspace found for user_id={user_id}, using 'admin_workspace'")
        return 'admin_workspace'
        
    except Exception as e:
        logger.warning(f"Failed to get primary workspace: {e}")
        return 'admin_workspace'


def create_workspace_in_database(workspace_id: str, user_id: int, user_request: str) -> bool:
    """
    Create workspace record in shard database.
    Called when a new conversation starts — workspace born at first message.
    """
    try:
        from Database.database_sharding_service import DatabaseShardingService
        from pathlib import Path
        import asyncio
        
        parts = workspace_id.split('_')
        workspace_name = '_'.join(parts[1:-2]) if len(parts) >= 3 else workspace_id
        
        workspace_data = {
            'workspace_id': workspace_id,
            'workspace_name': workspace_name,
            'owner_id': f"user_{user_id}" if isinstance(user_id, int) else user_id,
            'settings': {
                'created_from': 'openclaw',
                'original_request': user_request[:100],
                'workspace_type': 'conversation'
            }
        }
        
        base_path = Path(DATABASE_DIR)
        sharding_service = DatabaseShardingService(base_path)
        
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        loop.run_until_complete(sharding_service.initialize_shards(num_shards=SHARD_COUNT))
        result = loop.run_until_complete(sharding_service.create_workspace(workspace_data))
        
        if result:
            logger.info(f"✅ Created workspace: {workspace_id} for user_id={user_id}")
            return True
        else:
            logger.warning(f"⚠️ Failed to create workspace: {workspace_id}")
            return False
            
    except Exception as e:
        logger.error(f"Error creating workspace: {e}")
        return False


async def save_conversation_to_workspace(workspace_id: str, session_id: str,
                                          user_id: str, request: str, 
                                          claude_response: str,
                                          conversation_context: dict = None) -> bool:
    """
    Save a conversation turn to the workspace database.
    This is what builds up workspace history over time.
    """
    try:
        from Jarvis_Agent_SDK.database_directory import get_database_directory
        
        db_directory = get_database_directory()
        conn = db_directory.get_connection("trevor")
        if conn is None:
            logger.error("Failed to get database connection")
            return False
        
        try:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS claude_conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    workspace_id TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    user_id TEXT,
                    user_request TEXT NOT NULL,
                    claude_response TEXT NOT NULL,
                    conversation_context TEXT,
                    model_used TEXT,
                    tokens_used INTEGER,
                    timestamp TEXT DEFAULT (datetime('now')),
                    quality_score REAL
                )
            ''')
            
            cursor.execute('''
                INSERT INTO claude_conversations 
                (workspace_id, session_id, user_id, user_request, claude_response, conversation_context)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (workspace_id, session_id, str(user_id), request, claude_response,
                  json.dumps(conversation_context or {})))
            
            conn.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error saving conversation: {e}")
            return False
            
    except Exception as e:
        logger.error(f"Error in save_conversation_to_workspace: {e}")
        return False


async def get_conversation_history(workspace_id: str, session_id: str = None,
                                    limit: int = 20) -> List[Dict]:
    """
    Load conversation history for a workspace (optionally filtered by session).
    Used to build context for the next agent turn.
    """
    try:
        from Jarvis_Agent_SDK.database_directory import get_database_directory
        
        db_directory = get_database_directory()
        conn = db_directory.get_connection("trevor")
        if conn is None:
            return []
        
        cursor = conn.cursor()
        
        if session_id:
            cursor.execute('''
                SELECT user_request, claude_response, timestamp, conversation_context
                FROM claude_conversations
                WHERE workspace_id = ? AND session_id = ?
                ORDER BY timestamp DESC LIMIT ?
            ''', (workspace_id, session_id, limit))
        else:
            cursor.execute('''
                SELECT user_request, claude_response, timestamp, conversation_context
                FROM claude_conversations
                WHERE workspace_id = ?
                ORDER BY timestamp DESC LIMIT ?
            ''', (workspace_id, limit))
        
        rows = cursor.fetchall()
        return [{
            'request': r[0], 'response': r[1], 
            'timestamp': r[2], 'context': json.loads(r[3]) if r[3] else {}
        } for r in reversed(rows)]  # chronological order
        
    except Exception as e:
        logger.error(f"Error loading conversation history: {e}")
        return []


# Backward-compatible aliases for existing imports
_save_conversation_to_workspace_database = save_conversation_to_workspace
_get_conversation_history_for_claude = get_conversation_history
_generate_unique_workspace_id = generate_workspace_id
_get_user_primary_workspace = get_user_primary_workspace
_create_workspace_in_database = create_workspace_in_database
