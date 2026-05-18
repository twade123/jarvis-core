#!/usr/bin/env python3
"""
BoardRoom Data Poller - Missing Flag System Implementation

This module provides the missing database polling mechanism that retrieves
BoardRoom conversation data and sends it to the UI via SSE events.

The system polls the BoardRoom database for new messages from Claude, GPT, and Trevor
and emits them as SSE events to update the UI containers.
"""

import sqlite3
import json
import time
import threading
import logging
import requests
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import os

from Database.v2.db_helper import connection as v2_connection

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BoardroomDataPoller:
    """
    Polls the BoardRoom database for new conversation data and sends updates to the UI.
    
    This is the missing component that bridges the database persistence layer
    with the lightweight UI layer via the flag/heartbeat system.
    """
    
    def __init__(self, db_path: str = None,
                 ui_server_url: str = "http://localhost:8765",
                 poll_interval: int = 2):
        """
        Initialize the BoardRoom data poller.

        Args:
            db_path: Ignored — kept for backward-compat signature.
                     All connections now go through v2_connection.
            ui_server_url: URL of the UI server for SSE events
            poll_interval: Polling interval in seconds
        """
        self.db_path = db_path or "~/Jarvis/Database/v2/conversations.db"
        self.ui_server_url = ui_server_url
        self.poll_interval = poll_interval
        self.running = False
        self.poll_thread = None

        # Initialize last poll times
        self.last_poll_time = {
            'conversation_messages': time.time() - 300,  # Start 5 minutes ago
            'natural_language_communications': time.time() - 300,
            'agent_communication': time.time() - 300,
            'journey_steps': time.time() - 300
        }

        logger.info(f"BoardRoom Data Poller initialized - V2 pool, UI: {ui_server_url}")

    def poll_conversation_messages(self) -> List[Dict[str, Any]]:
        """
        Poll the conversation_messages table for new BoardRoom messages.

        Returns:
            List of new conversation messages
        """
        try:
            with v2_connection("conversations") as conn:
                cursor = conn.cursor()

                last_time = self.last_poll_time['conversation_messages']
                last_time_str = datetime.fromtimestamp(last_time).isoformat()

                query = """
                    SELECT conversation_id, message_id, role, content, tool_calls, tool_results, created_at
                    FROM conversation_messages
                    WHERE created_at > ?
                    AND role IN ('claude', 'gpt', 'assistant', 'system')
                    ORDER BY created_at ASC
                """

                cursor.execute(query, (last_time_str,))
                results = cursor.fetchall()

                messages = []
                for row in results:
                    message = {
                        'conversation_id': row['conversation_id'],
                        'message_id': row['message_id'],
                        'role': row['role'],
                        'content': row['content'],
                        'tool_calls': row['tool_calls'],
                        'tool_results': row['tool_results'],
                        'created_at': row['created_at'],
                        'timestamp': time.time(),
                        'source': 'conversation_messages'
                    }
                    messages.append(message)

            if messages:
                self.last_poll_time['conversation_messages'] = time.time()
                logger.info(f"Found {len(messages)} new conversation messages")

            return messages

        except Exception as e:
            logger.error(f"Error polling conversation_messages: {e}")
            return []

    def poll_agent_communications(self) -> List[Dict[str, Any]]:
        """
        Poll the agent_communication table for agent-to-agent messages.

        Returns:
            List of new agent communication messages
        """
        try:
            with v2_connection("conversations") as conn:
                cursor = conn.cursor()

                last_time = self.last_poll_time['agent_communication']

                query = """
                    SELECT sender_agent_name, receiver_agent_name, message_id, task_id,
                           message_type, content, metadata, journey_id, timestamp, workspace_id
                    FROM agent_communication
                    WHERE timestamp > ?
                    AND sender_agent_name IN ('claude', 'gpt', 'trevor', 'Claude', 'GPT', 'Trevor')
                    ORDER BY timestamp ASC
                """

                cursor.execute(query, (last_time,))
                results = cursor.fetchall()

                messages = []
                for row in results:
                    message = {
                        'role': row['sender_agent_name'].lower(),
                        'content': row['content'],
                        'message_id': row['message_id'],
                        'task_id': row['task_id'],
                        'message_type': row['message_type'],
                        'metadata': row['metadata'],
                        'journey_id': row['journey_id'],
                        'workspace_id': row['workspace_id'],
                        'timestamp': row['timestamp'],
                        'created_at': datetime.fromtimestamp(row['timestamp']).isoformat(),
                        'source': 'agent_communication'
                    }
                    messages.append(message)

            if messages:
                self.last_poll_time['agent_communication'] = time.time()
                logger.info(f"Found {len(messages)} new agent communications")

            return messages

        except Exception as e:
            logger.error(f"Error polling agent_communication: {e}")
            return []

    def poll_natural_language_communications(self) -> List[Dict[str, Any]]:
        """
        Poll the natural_language_communications table for BoardRoom conversations.

        Returns:
            List of new natural language communications
        """
        try:
            with v2_connection("conversations") as conn:
                cursor = conn.cursor()

                last_time = self.last_poll_time['natural_language_communications']

                query = """
                    SELECT journey_id, from_agent, to_agent, communication_type, message,
                           timestamp, context, direction, is_response, correlation_id,
                           intent, sentiment, task_id, metadata
                    FROM natural_language_communications
                    WHERE timestamp > ?
                    AND from_agent IN ('claude', 'gpt', 'trevor', 'Claude', 'GPT', 'Trevor')
                    ORDER BY timestamp ASC
                """

                cursor.execute(query, (last_time,))
                results = cursor.fetchall()

                messages = []
                for row in results:
                    message = {
                        'role': row['from_agent'].lower(),
                        'content': row['message'],
                        'journey_id': row['journey_id'],
                        'to_agent': row['to_agent'],
                        'communication_type': row['communication_type'],
                        'context': row['context'],
                        'direction': row['direction'],
                        'is_response': bool(row['is_response']),
                        'correlation_id': row['correlation_id'],
                        'intent': row['intent'],
                        'sentiment': row['sentiment'],
                        'task_id': row['task_id'],
                        'metadata': row['metadata'],
                        'timestamp': row['timestamp'],
                        'created_at': datetime.fromtimestamp(row['timestamp']).isoformat(),
                        'source': 'natural_language_communications'
                    }
                    messages.append(message)

            if messages:
                self.last_poll_time['natural_language_communications'] = time.time()
                logger.info(f"Found {len(messages)} new natural language communications")

            return messages

        except Exception as e:
            logger.error(f"Error polling natural_language_communications: {e}")
            return []

    def poll_journey_steps(self) -> List[Dict[str, Any]]:
        """
        Poll the journey_steps table for execution steps and feedback requests.

        Returns:
            List of new journey steps that represent feedback or execution plans
        """
        try:
            with v2_connection("journeys") as conn:
                cursor = conn.cursor()

                last_time = self.last_poll_time['journey_steps']

                query = """
                    SELECT journey_id, step_type, step_name, description, input_data,
                           output_data, error, timestamp, duration, status, metadata
                    FROM journey_steps
                    WHERE timestamp > ?
                    AND (step_type LIKE '%feedback%' OR step_type LIKE '%execution%' OR step_type LIKE '%plan%')
                    ORDER BY timestamp ASC
                """

                cursor.execute(query, (last_time,))
                results = cursor.fetchall()

                messages = []
                for row in results:
                    is_feedback = 'feedback' in row['step_type'].lower()
                    is_execution_plan = any(keyword in row['step_type'].lower()
                                           for keyword in ['execution', 'plan', 'summary'])

                    message = {
                        'role': 'system',
                        'content': row['description'] or row['step_name'],
                        'journey_id': row['journey_id'],
                        'step_type': row['step_type'],
                        'step_name': row['step_name'],
                        'input_data': row['input_data'],
                        'output_data': row['output_data'],
                        'error': row['error'],
                        'duration': row['duration'],
                        'status': row['status'],
                        'metadata': row['metadata'],
                        'timestamp': row['timestamp'],
                        'created_at': datetime.fromtimestamp(row['timestamp']).isoformat(),
                        'source': 'journey_steps',
                        'is_feedback': is_feedback,
                        'is_execution_plan': is_execution_plan
                    }
                    messages.append(message)

            if messages:
                self.last_poll_time['journey_steps'] = time.time()
                logger.info(f"Found {len(messages)} new journey steps")

            return messages

        except Exception as e:
            logger.error(f"Error polling journey_steps: {e}")
            return []

    def send_sse_message(self, message: Dict[str, Any]) -> bool:
        """
        Send a message to the UI server via SSE.
        
        Args:
            message: Message data to send
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Prepare the SSE message payload
            sse_payload = {
                'event_type': 'boardroom_update',
                'data': {
                    'role': message.get('role', 'system'),
                    'content': message.get('content', ''),
                    'timestamp': message.get('timestamp', time.time()),
                    'message_id': message.get('message_id'),
                    'journey_id': message.get('journey_id'),
                    'task_id': message.get('task_id'),
                    'metadata': message.get('metadata'),
                    'source': message.get('source'),
                    'is_feedback': message.get('is_feedback', False),
                    'is_execution_plan': message.get('is_execution_plan', False),
                    'is_boardroom': True,
                    'is_conversation': True
                }
            }
            
            # Send to the UI server's SSE endpoint
            response = requests.post(
                f"{self.ui_server_url}/api/send",
                json=sse_payload,
                headers={'Content-Type': 'application/json'},
                timeout=5
            )
            
            if response.status_code == 200:
                logger.debug(f"Successfully sent SSE message: {message.get('role')} - {message.get('content', '')[:50]}...")
                return True
            else:
                logger.warning(f"Failed to send SSE message: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending SSE message: {e}")
            return False

    def poll_all_sources(self):
        """Poll all data sources and send updates to UI."""
        try:
            # Collect all new messages
            all_messages = []
            
            # Poll conversation messages
            all_messages.extend(self.poll_conversation_messages())
            
            # Poll agent communications
            all_messages.extend(self.poll_agent_communications())
            
            # Poll natural language communications
            all_messages.extend(self.poll_natural_language_communications())
            
            # Poll journey steps for feedback/execution plans
            all_messages.extend(self.poll_journey_steps())
            
            # Sort by timestamp
            all_messages.sort(key=lambda x: x.get('timestamp', 0))
            
            # Send each message to the UI
            for message in all_messages:
                self.send_sse_message(message)
                
            if all_messages:
                logger.info(f"Processed {len(all_messages)} new BoardRoom messages")
                
        except Exception as e:
            logger.error(f"Error in poll_all_sources: {e}")

    def polling_loop(self):
        """Main polling loop that runs in a separate thread."""
        logger.info("BoardRoom polling loop started")
        
        while self.running:
            try:
                self.poll_all_sources()
                time.sleep(self.poll_interval)
                
            except Exception as e:
                logger.error(f"Error in polling loop: {e}")
                time.sleep(self.poll_interval)
        
        logger.info("BoardRoom polling loop stopped")

    def start(self):
        """Start the BoardRoom data polling."""
        if self.running:
            logger.warning("BoardRoom poller is already running")
            return
            
        self.running = True
        self.poll_thread = threading.Thread(target=self.polling_loop, daemon=True)
        self.poll_thread.start()
        logger.info("BoardRoom data poller started")

    def stop(self):
        """Stop the BoardRoom data polling."""
        if not self.running:
            logger.warning("BoardRoom poller is not running")
            return
            
        self.running = False
        if self.poll_thread:
            self.poll_thread.join(timeout=10)
        logger.info("BoardRoom data poller stopped")

    def get_status(self) -> Dict[str, Any]:
        """Get the current status of the poller."""
        return {
            'running': self.running,
            'db_path': self.db_path,
            'ui_server_url': self.ui_server_url,
            'poll_interval': self.poll_interval,
            'last_poll_times': self.last_poll_time.copy()
        }


def main():
    """Main function to run the BoardRoom data poller as a standalone service."""
    import argparse
    
    parser = argparse.ArgumentParser(description='BoardRoom Data Poller Service')
    parser.add_argument('--db-path', default='~/Jarvis/Database/v2/conversations.db',
                       help='Path to BoardRoom database (ignored — uses V2 pool)')
    parser.add_argument('--ui-server', default='http://localhost:8765',
                       help='UI server URL')
    parser.add_argument('--poll-interval', type=int, default=2,
                       help='Polling interval in seconds')
    parser.add_argument('--log-level', default='INFO',
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       help='Logging level')
    
    args = parser.parse_args()
    
    # Configure logging
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    # Create and start the poller
    poller = BoardroomDataPoller(
        db_path=args.db_path,
        ui_server_url=args.ui_server,
        poll_interval=args.poll_interval
    )
    
    try:
        poller.start()
        logger.info("BoardRoom Data Poller running. Press Ctrl+C to stop.")
        
        # Keep the main thread alive
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
        poller.stop()
        logger.info("BoardRoom Data Poller stopped")


if __name__ == "__main__":
    main()