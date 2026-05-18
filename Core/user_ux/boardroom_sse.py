#!/usr/bin/env python3
"""
SSE Functions for Boardroom Terminal

This module provides direct access to the SSE (Server-Sent Events) functions 
for the boardroom_terminal.py script, replacing the Socket.IO implementation.
"""

import os
import sys
import logging
import traceback

# Configure logging
logger = logging.getLogger(__name__)

# Flag to check if we've imported SSE from sse_endpoint
_sse_imported = False
_send_event = None
_broadcast_event = None

# Function to get SSE functions from sse_endpoint for direct updates
def get_sse_functions():
    """
    Try to import send_event and broadcast_event from sse_endpoint for direct updates.
    Returns tuple of (send_event, broadcast_event) functions if successful, (None, None) otherwise.
    """
    global _sse_imported, _send_event, _broadcast_event
    
    # If we've already tried to import and failed, don't retry
    if _sse_imported and (_send_event is None or _broadcast_event is None):
        return None, None
        
    # If we've already imported successfully, return the cached functions
    if _send_event is not None and _broadcast_event is not None:
        return _send_event, _broadcast_event
        
    try:
        # Mark that we've attempted import to avoid repeated failures
        _sse_imported = True
        
        # First try to import from relative path
        try:
            from Core.user_ux.sse_endpoint import send_event, broadcast_event
            _send_event = send_event
            _broadcast_event = broadcast_event
            logger.info(f"[BOARDROOM] Successfully imported SSE functions from Core.user_ux.sse_endpoint")
        except ImportError:
            # Try different import path
            try:
                # Add Core/user_ux to path
                current_dir = os.path.dirname(os.path.abspath(__file__))
                ux_path = os.path.join(current_dir, "Core", "user_ux")
                if os.path.exists(ux_path):
                    if ux_path not in sys.path:
                        sys.path.append(ux_path)
                    
                # Try the import again
                from sse_endpoint import send_event, broadcast_event
                _send_event = send_event
                _broadcast_event = broadcast_event
                logger.info(f"[BOARDROOM] Successfully imported SSE functions from sse_endpoint")
            except ImportError:
                # One final attempt with a different path structure
                try:
                    # Find the Core/user_ux directory relative to the Jarvis root
                    jarvis_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                    ux_path = os.path.join(jarvis_root, "Core", "user_ux")
                    if os.path.exists(ux_path):
                        if ux_path not in sys.path:
                            sys.path.append(ux_path)
                        
                    # Try the import again
                    from sse_endpoint import send_event, broadcast_event
                    _send_event = send_event
                    _broadcast_event = broadcast_event
                    logger.info(f"[BOARDROOM] Successfully imported SSE functions from sse_endpoint")
                except ImportError:
                    logger.warning(f"[BOARDROOM] Could not import SSE functions from sse_endpoint - notification features will be limited")
                    return None, None
        
        return _send_event, _broadcast_event
    except Exception as e:
        logger.warning(f"[BOARDROOM] Error importing SSE functions: {e}")
        logger.debug(traceback.format_exc())
        return None, None

# Helper function to send a boardroom update
def send_boardroom_update(session_id, data):
    """
    Send a boardroom update to a specific client session
    
    Args:
        session_id: Client session ID
        data: Message data
    """
    send_event, _ = get_sse_functions()
    if send_event:
        try:
            send_event(session_id, 'boardroom_update', data)
            return True
        except Exception as e:
            logger.error(f"[BOARDROOM] Error sending boardroom update via SSE: {e}")
    return False

# Helper function to broadcast a boardroom update to all clients
def broadcast_boardroom_update(data):
    """
    Broadcast a boardroom update to all connected clients
    
    Args:
        data: Message data
    """
    _, broadcast_event = get_sse_functions()
    if broadcast_event:
        try:
            broadcast_event('boardroom_update', data)
            return True
        except Exception as e:
            logger.error(f"[BOARDROOM] Error broadcasting boardroom update via SSE: {e}")
    return False

# Helper function to send a chat message to a specific client
def send_chat_message(session_id, data):
    """
    Send a chat message to a specific client session
    
    Args:
        session_id: Client session ID
        data: Message data
    """
    send_event, _ = get_sse_functions()
    if send_event:
        try:
            send_event(session_id, 'message', data)
            return True
        except Exception as e:
            logger.error(f"[BOARDROOM] Error sending chat message via SSE: {e}")
    return False

# Helper function to broadcast a chat message to all clients
def broadcast_chat_message(data):
    """
    Broadcast a chat message to all connected clients
    
    Args:
        data: Message data
    """
    _, broadcast_event = get_sse_functions()
    if broadcast_event:
        try:
            broadcast_event('message', data)
            return True
        except Exception as e:
            logger.error(f"[BOARDROOM] Error broadcasting chat message via SSE: {e}")
    return False