#!/usr/bin/env python3
"""
Server-Sent Events (SSE) Endpoint for Trevor Desktop UI

This module adds SSE support to the boardroom_api.py server, replacing Socket.IO
with a simpler, more reliable real-time communication mechanism.

Key features:
- Real-time updates without WebSockets
- Standard HTTP streaming (works through proxies and firewalls)
- No ping/pong mechanism needed
- Support for multiple event types
- Session-based message queuing
"""

import time
import json
import queue
import threading
import logging
import traceback
from typing import Dict, Any, List, Optional
from flask import Response, request, stream_with_context, jsonify

# Configure logging
logger = logging.getLogger(__name__)

# Message queues for each client session
message_queues = {}
queue_lock = threading.Lock()

def get_message_queue(session_id):
    """Get or create a message queue for a client session"""
    with queue_lock:
        if session_id not in message_queues:
            message_queues[session_id] = queue.Queue()
        return message_queues[session_id]

def remove_message_queue(session_id):
    """Remove a message queue when client disconnects"""
    with queue_lock:
        if session_id in message_queues:
            del message_queues[session_id]
            logger.info(f"Removed message queue for session {session_id}")

def send_event(session_id, event_type, data):
    """
    Send an event to a specific client session
    
    Args:
        session_id: Client session ID
        event_type: Type of event (e.g., 'boardroom_update', 'message')
        data: Event data (will be JSON-encoded)
    """
    try:
        # Get the message queue for this session
        q = get_message_queue(session_id)
        
        # Format the event in SSE format
        event = {
            'event': event_type,
            'data': data
        }
        
        # Add to the queue
        q.put(event)
        logger.debug(f"Added event to queue for session {session_id}: {event_type}")
    except Exception as e:
        logger.error(f"Error sending event to session {session_id}: {e}")

def broadcast_event(event_type, data):
    """
    Broadcast an event to all connected clients
    
    Args:
        event_type: Type of event
        data: Event data
    """
    with queue_lock:
        for session_id in message_queues:
            send_event(session_id, event_type, data)

def format_sse_event(event_type, data):
    """Format data in SSE format"""
    if isinstance(data, dict) or isinstance(data, list):
        data = json.dumps(data)
    
    # Format according to SSE spec
    msg = f"event: {event_type}\ndata: {data}\n\n"
    return msg

def event_stream(session_id):
    """
    Generate SSE event stream for a client session
    
    This is the main function that creates the streaming response.
    """
    # Get queue for this session
    q = get_message_queue(session_id)
    
    # Send initial connection message
    yield format_sse_event("connection", {
        "status": "connected",
        "session_id": session_id,
        "timestamp": time.time()
    })
    
    # Keep connection alive
    try:
        while True:
            # Try to get message from queue with timeout
            try:
                event = q.get(timeout=1.0)
                if event:
                    yield format_sse_event(event['event'], event['data'])
            except queue.Empty:
                # No events, send comment to keep connection alive
                yield ": keepalive\n\n"
                time.sleep(20)  # Send keepalive every 20 seconds
    except GeneratorExit:
        # Client disconnected
        logger.info(f"Client disconnected: {session_id}")
        remove_message_queue(session_id)

def setup_sse_endpoint(app):
    """
    Set up SSE endpoint in Flask app
    
    Args:
        app: Flask application instance
    """
    @app.route('/events')
    def sse_request():
        """SSE endpoint handler"""
        # Get or generate session ID
        session_id = request.args.get('session_id')
        if not session_id:
            session_id = str(request.remote_addr) + "_" + str(int(time.time()))
        
        logger.info(f"New SSE connection from {request.remote_addr}, session ID: {session_id}")
        
        # Set up proper headers for SSE
        response = Response(
            stream_with_context(event_stream(session_id)),
            mimetype='text/event-stream'
        )
        
        # Important headers for SSE
        response.headers['Cache-Control'] = 'no-cache'
        response.headers['X-Accel-Buffering'] = 'no'  # For Nginx
        response.headers['Connection'] = 'keep-alive'
        response.headers['Access-Control-Allow-Origin'] = '*'
        
        return response
        
    @app.route('/api/client_ready', methods=['POST'])
    def handle_client_ready():
        """Handle client ready event from the frontend via HTTP POST"""
        try:
            data = request.json
            logger.info(f"Client ready event received: {data}")
            
            client_id = data.get('session_id')
            if not client_id:
                return jsonify({'status': 'error', 'message': 'session_id is required'}), 400
                
            # Record client information
            logger.info(f"Client {client_id} reports ready")
            
            # Send a connection confirmation with server info
            send_event(client_id, 'connection_confirmed', {
                'status': 'connected',
                'session_id': client_id,
                'server_time': time.time(),
                'timestamp': time.time()
            })
            
            # Send ready confirmation
            send_event(client_id, 'ready_confirmed', {
                'status': 'ready',
                'message': 'Server is ready to receive messages',
                'timestamp': time.time()
            })
            
            return jsonify({
                'status': 'success',
                'message': 'Client ready acknowledged',
                'session_id': client_id
            })
            
        except Exception as e:
            logger.error(f"Error in handle_client_ready: {str(e)}")
            logger.debug(traceback.format_exc())
            return jsonify({'status': 'error', 'message': str(e)}), 500
            
    @app.route('/api/test_message', methods=['POST'])
    def handle_test_message():
        """Handle test message from client via HTTP POST"""
        try:
            data = request.json
            logger.info(f"Test message received: {data}")
            
            session_id = data.get('session_id')
            if not session_id:
                return jsonify({'status': 'error', 'message': 'session_id is required'}), 400
                
            # Send message back to client
            send_event(session_id, 'message', {
                'id': str(time.time()),
                'type': 'system',
                'content': f"Test message received: {data.get('message', 'No message content')}",
                'timestamp': time.time(),
                'status': 'complete'
            })
            
            return jsonify({
                'status': 'success', 
                'message': 'Test message received and processed'
            })
            
        except Exception as e:
            logger.error(f"Error in handle_test_message: {str(e)}")
            logger.debug(traceback.format_exc())
            return jsonify({'status': 'error', 'message': str(e)}), 500