"""
Session Manager — Conversation history, session tracking, and context management.

Extracted from handler_claude.py. Manages:
- Session lifecycle (create, track, cleanup)
- Conversation history storage and retrieval  
- Context building from conversation aggregator data
- Conversation search tool definitions
- Workspace session lookup

All methods are standalone functions or a SessionManager class.
The ClaudeHandler facade delegates to these.
"""

import logging
import os
import re
import sqlite3
import sys
import uuid
from typing import Any, Dict, List, Optional

# Ensure project root is on path for Database.v2 imports
_project_root = os.path.join(os.path.dirname(__file__), '..', '..')
if os.path.abspath(_project_root) not in sys.path:
    sys.path.insert(0, os.path.abspath(_project_root))

from Database.v2.db_helper import connection as v2_connection, DB_PATHS

logger = logging.getLogger(__name__)

# Database path — now points to V2 conversations database
DEFAULT_DB_PATH = DB_PATHS["conversations"]


class SessionManager:
    """Manages conversation sessions, history, and context.
    
    Extracted from ClaudeHandler session-related methods.
    Standalone — does not depend on ClaudeHandler.
    """
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or DEFAULT_DB_PATH
        self.conversation_history: Dict[str, List[Dict]] = {}
        self.session_context: Dict[str, Dict] = {}
        self.active_sessions: set = set()
    
    def generate_session_id(self) -> str:
        """Generate unique session ID."""
        return str(uuid.uuid4())
    
    def get_active_sessions(self) -> List[str]:
        """Get list of active session IDs."""
        return list(self.active_sessions)
    
    def add_message(self, session_id: str, role: str, content: str):
        """Add a message to session history."""
        if session_id not in self.conversation_history:
            self.conversation_history[session_id] = []
        self.conversation_history[session_id].append({
            "role": role,
            "content": content,
        })
        self.active_sessions.add(session_id)
    
    def get_history(self, session_id: str, limit: int = 50) -> List[Dict]:
        """Get conversation history for a session."""
        history = self.conversation_history.get(session_id, [])
        return history[-limit:]
    
    def build_conversation_context_prompt(self, parameters: Dict[str, Any]) -> str:
        """Build conversation context prompt with WORKSPACE-FIRST priority.
        
        Context Priority Layers:
        1. Current workspace conversation (highest)
        2. Role & expertise context
        3. Conversation progress state
        4. Broader history (only for explicit historical requests)
        5. Capability description
        """
        try:
            conversation_aggregator_data = parameters.get('conversation_aggregator_data', {})
            if not conversation_aggregator_data:
                return ""

            workspace_context = parameters.get('workspace_context', {})
            current_workspace_id = workspace_context.get('workspace_id', 'default')
            conversation_state = parameters.get('conversation_state')
            conversation_metadata = parameters.get('conversation_metadata', {})

            sections = []

            # Layer 1: Current workspace conversation
            workspace_conversations = conversation_aggregator_data.get('workspace_conversations', [])
            if workspace_conversations:
                sections.append("=== CURRENT WORKSPACE CONVERSATION CONTEXT ===")
                sections.append(f"Continuing conversation in workspace: {current_workspace_id}")
                for conv in workspace_conversations[-3:]:
                    if isinstance(conv, dict):
                        ts = conv.get('timestamp', 'recently')
                        content = conv.get('content', conv.get('user_input', ''))[:100]
                        sections.append(f"- {ts}: {content}...")

            # Layer 2: Role context
            if conversation_metadata:
                role = conversation_metadata.get('assigned_role', '')
                domain = conversation_metadata.get('primary_domain', '')
                if role and domain:
                    sections.append(f"\n=== YOUR ROLE & EXPERTISE ===")
                    sections.append(f"Acting as: {role}, Domain: {domain}")

            # Layer 3: Conversation progress
            if conversation_state and hasattr(conversation_state, 'context_gathered'):
                cg = conversation_state.context_gathered
                sections.append(f"\n=== CONVERSATION PROGRESS ===")
                if cg.get('primary_goals'):
                    sections.append(f"Goals: {', '.join(cg['primary_goals'][:3])}")
                if cg.get('requirements'):
                    sections.append(f"Requirements: {', '.join(cg['requirements'][:3])}")

            # Layer 4: Historical context (only on explicit triggers)
            user_request = parameters.get('prompt', '').lower()
            historical_triggers = ['last week', 'the other day', 'previously', 'before', 'earlier', 'history', 'past']
            recent_conversations = conversation_aggregator_data.get('recent_conversations', [])
            
            if any(t in user_request for t in historical_triggers) and recent_conversations:
                sections.append(f"\n=== BROADER CONVERSATION HISTORY ===")
                for conv in recent_conversations[-2:]:
                    if isinstance(conv, dict):
                        ts = conv.get('timestamp', 'recently')
                        content = conv.get('content', conv.get('message', ''))[:80]
                        sections.append(f"- {ts}: {content}...")

            return "\n".join(sections)
        except Exception as e:
            logger.warning(f"Failed to build conversation context: {e}")
            return ""
    
    def extract_context_handoffs(self, response_text: str) -> Dict[str, Any]:
        """Extract context handoffs between subtasks from response."""
        handoffs = {}
        simple_pattern = r'<context_handoff>(.*?)</context_handoff>'
        matches = re.findall(simple_pattern, response_text, re.DOTALL)
        subtask_ids = re.findall(r'<subtask\s+id=["\'](\d+)["\']>', response_text)
        
        for i, data in enumerate(matches):
            if i < len(subtask_ids) - 1:
                from_id = subtask_ids[i]
                to_id = subtask_ids[i + 1]
                handoffs[f"{from_id}→{to_id}"] = {
                    'from_subtask': int(from_id),
                    'to_subtask': int(to_id),
                    'data': data.strip(),
                }
        return handoffs
    
    def create_conversation_summary(self, messages: List[Dict]) -> str:
        """Create concise summary of conversation messages to prevent token overflow."""
        if not messages:
            return ""
        
        topics, actions, files = [], [], []
        
        for msg in messages:
            content = msg.get('content', '')
            role = msg.get('role', '')
            
            # Extract file mentions
            for pattern in [r'`([^`]+\.[a-zA-Z0-9]+)`', r'file[:\s]+([^\s\n,]+)']:
                files.extend(re.findall(pattern, content.lower()))
            
            if role == 'user':
                cl = content.lower()
                if any(w in cl for w in ['create', 'make', 'build', 'write']): actions.append('creation')
                if any(w in cl for w in ['read', 'show', 'view']): actions.append('reading')
                if any(w in cl for w in ['edit', 'modify', 'change']): actions.append('editing')
                if any(w in cl for w in ['search', 'find', 'grep']): actions.append('search')
                if any(w in cl for w in ['fix', 'debug', 'error']): topics.append('debugging')
        
        parts = []
        if topics: parts.append(f"Topics: {', '.join(set(topics))}")
        if actions: parts.append(f"Actions: {', '.join(set(actions))}")
        if files:
            parts.append(f"Files: {', '.join(list(set(files))[:5])}")
        
        return '; '.join(parts)[:200]
    
    def get_most_recent_session_from_workspace(self, workspace_id: int) -> Optional[str]:
        """Get most recent session ID from workspace database (V2 conversations)."""
        try:
            if not workspace_id:
                return None
            with v2_connection("conversations") as conn:
                row = conn.execute("""
                    SELECT session_id FROM conversations
                    WHERE workspace_id = ? ORDER BY created_at DESC LIMIT 1
                """, (workspace_id,)).fetchone()
                return row[0] if row else None
        except Exception as e:
            logger.error(f"Error getting recent session: {e}")
            return None
    
    def detect_mcp_from_conversation_context(self, parameters: Dict, mcp_patterns: Dict) -> Optional[str]:
        """Check conversation history for MCP context references."""
        conversation_messages = parameters.get('conversation_messages', [])
        if not conversation_messages:
            return None
        
        recent = conversation_messages[-5:]
        for message in reversed(recent):
            if not isinstance(message, dict):
                continue
            content = message.get('content', '')
            if not isinstance(content, str):
                continue
            
            content_lower = content.lower()
            for server_name, patterns in mcp_patterns.items():
                for pattern in patterns:
                    if pattern in content_lower:
                        return server_name
        return None


def build_conversation_search_tools() -> List[Dict]:
    """Build conversation search tool schemas.
    
    Returns tool definitions for ConversationSearch and WorkspaceConversationHistory.
    These can be added to any ToolKit.
    """
    return [
        {
            "name": "ConversationSearch",
            "description": "Search conversation history for previous discussions.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "search_query": {"type": "string", "description": "Search terms"},
                    "workspace_scope": {"type": "string", "enum": ["current", "all"]},
                    "time_range": {"type": "string", "enum": ["recent", "week", "month", "all"]},
                },
                "required": ["search_query"],
            },
        },
        {
            "name": "WorkspaceConversationHistory",
            "description": "Get conversation history for the current workspace.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "detail_level": {"type": "string", "enum": ["summary", "detailed", "full"]},
                    "include_context": {"type": "boolean"},
                },
            },
        },
    ]
