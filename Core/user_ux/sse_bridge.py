#!/usr/bin/env python3
"""
SSE Bridge for Boardroom Terminal

This module provides a compatibility layer to allow the boardroom_terminal.py to
send events through SSE instead of Socket.IO.
"""

import logging
import os
import sys
import time

# Configure logging
logger = logging.getLogger(__name__)

# Add parent directory to path for importing sse_endpoint
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from sse_endpoint import send_event, broadcast_event

class SocketIOBridge:
    """
    A class that mimics the Socket.IO interface but uses SSE under the hood.
    This allows the boardroom_terminal.py to continue using the socket.emit
    function without modification.
    """
    
    def __init__(self):
        """Initialize the SocketIO bridge."""
        logger.info("Initializing SocketIO to SSE bridge")
    
    def emit(self, event_type, data, room=None, callback=None):
        """
        Emit an event through SSE instead of Socket.IO.
        
        Args:
            event_type: The type of event to emit
            data: The data to send with the event
            room: The room (session_id) to send the event to (optional)
            callback: A callback function to call after the event is sent (optional)
        """
        try:
            logger.info(f"[SSE BRIDGE] Emitting {event_type} event through SSE")
            
            # If room is specified, send to that specific session
            if room:
                send_event(room, event_type, data)
            else:
                # Otherwise broadcast to all sessions
                broadcast_event(event_type, data)
            
            # Call the callback if provided
            if callback and callable(callback):
                callback()
                
            return True
        except Exception as e:
            logger.error(f"[SSE BRIDGE] Error emitting event: {e}")
            return False

# Create a singleton instance
socketio = SocketIOBridge()

# For testing
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    socketio.emit("test", {"message": "Hello from SSE Bridge!"})
    print("Test event sent through SSE Bridge")