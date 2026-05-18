#!/usr/bin/env python3
"""
Unified Real-time Communication System
Coordinates SSE (existing) + WebSocket (new) for optimal real-time experience

This system manages the coordination between:
- SSE: Claude feedback responses, export notifications, status updates  
- WebSocket: Live conversation timeline, real-time search, interactive features
"""

import json
import time
import logging
import asyncio
import websockets
from typing import Dict, Set, Optional, Any
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UnifiedRealTimeSystem:
    """
    Coordinates SSE and WebSocket for optimal real-time experience
    
    SSE is used for:
    - Claude feedback responses (existing)
    - Export notifications
    - Status updates
    - One-way server-to-client communication
    
    WebSocket is used for:
    - Live conversation timeline updates
    - Real-time search results
    - Interactive features requiring bidirectional communication
    - Low-latency updates
    """
    
    def __init__(self):
        self.sse_active = True  # Existing SSE system is always active
        self.websocket_active = False  # WebSocket system starts inactive
        self.websocket_server = None
        self.active_connections: Dict[str, Set[websockets.WebSocketServerProtocol]] = {}
        self.session_to_workspace: Dict[str, str] = {}
        self.connection_stats = {
            'sse_messages_sent': 0,
            'websocket_messages_sent': 0,
            'websocket_connections': 0,
            'start_time': time.time()
        }
        
        logger.info("Unified Real-time System initialized")
    
    # ========================== SSE INTEGRATION (EXISTING SYSTEM) ==========================
    
    def send_claude_feedback_update(self, session_id: str, response: str, workspace_id: str):
        """
        Use SSE for Claude feedback responses (EXISTING)
        This integrates with the existing send_to_persistent_workspace function
        """
        try:
            # Import here to avoid circular imports
            from .boardroom_api import send_to_persistent_workspace
            
            send_to_persistent_workspace(session_id, response, workspace_id)
            self.connection_stats['sse_messages_sent'] += 1
            logger.debug(f"Sent Claude feedback via SSE to session {session_id}")
            
        except Exception as e:
            logger.error(f"Error sending Claude feedback via SSE: {e}")
    
    def send_export_notification(self, session_id: str, notification_data: Dict[str, Any]):
        """
        Send export notifications via SSE (existing pattern)
        """
        try:
            from .boardroom_api import send_to_persistent_workspace
            
            message = json.dumps({
                'type': 'export_notification',
                'timestamp': time.time(),
                'data': notification_data
            })
            
            send_to_persistent_workspace(session_id, message, notification_data.get('workspace_id'))
            self.connection_stats['sse_messages_sent'] += 1
            logger.debug(f"Sent export notification via SSE to session {session_id}")
            
        except Exception as e:
            logger.error(f"Error sending export notification via SSE: {e}")
    
    def send_status_update(self, session_id: str, status_data: Dict[str, Any]):
        """
        Send status updates via SSE (existing pattern)
        """
        try:
            from .boardroom_api import send_to_persistent_workspace
            
            message = json.dumps({
                'type': 'status_update',
                'timestamp': time.time(),
                'data': status_data
            })
            
            send_to_persistent_workspace(session_id, message, status_data.get('workspace_id'))
            self.connection_stats['sse_messages_sent'] += 1
            logger.debug(f"Sent status update via SSE to session {session_id}")
            
        except Exception as e:
            logger.error(f"Error sending status update via SSE: {e}")
    
    # ========================== WEBSOCKET INTEGRATION (NEW SYSTEM) ==========================
    
    async def start_websocket_server(self, port: int = 8766):
        """
        Start the WebSocket server for real-time interactive features
        """
        try:
            self.websocket_server = await websockets.serve(
                self.handle_websocket_connection,
                "localhost",
                port
            )
            self.websocket_active = True
            logger.info(f"WebSocket server started on port {port}")
            
        except Exception as e:
            logger.error(f"Error starting WebSocket server: {e}")
            self.websocket_active = False
    
    async def stop_websocket_server(self):
        """
        Stop the WebSocket server
        """
        if self.websocket_server:
            self.websocket_server.close()
            await self.websocket_server.wait_closed()
            self.websocket_active = False
            logger.info("WebSocket server stopped")
    
    async def handle_websocket_connection(self, websocket, path):
        """
        Handle incoming WebSocket connections
        """
        session_id = None
        workspace_id = None
        
        try:
            # Extract session and workspace info from path or query params
            # Format: /workspace/{workspace_id}?session_id={session_id}
            path_parts = path.strip('/').split('/')
            if len(path_parts) >= 2 and path_parts[0] == 'workspace':
                workspace_id = path_parts[1]
            
            # Register connection
            if workspace_id not in self.active_connections:
                self.active_connections[workspace_id] = set()
            
            self.active_connections[workspace_id].add(websocket)
            self.connection_stats['websocket_connections'] += 1
            
            logger.info(f"WebSocket connected: workspace {workspace_id}")
            
            # Send welcome message
            await websocket.send(json.dumps({
                'type': 'connection_established',
                'workspace_id': workspace_id,
                'timestamp': time.time()
            }))
            
            # Listen for messages
            async for message in websocket:
                await self.handle_websocket_message(websocket, message, workspace_id)
                
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"WebSocket disconnected: workspace {workspace_id}")
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
        finally:
            # Clean up connection
            if workspace_id and workspace_id in self.active_connections:
                self.active_connections[workspace_id].discard(websocket)
                if not self.active_connections[workspace_id]:
                    del self.active_connections[workspace_id]
    
    async def handle_websocket_message(self, websocket, message: str, workspace_id: str):
        """
        Handle incoming WebSocket messages
        """
        try:
            data = json.loads(message)
            message_type = data.get('type')
            
            if message_type == 'timeline_filter_request':
                await self.handle_timeline_filter_request(websocket, data, workspace_id)
            elif message_type == 'search_live_request':
                await self.handle_live_search_request(websocket, data, workspace_id)
            elif message_type == 'presence_update':
                await self.handle_presence_update(websocket, data, workspace_id)
            else:
                logger.warning(f"Unknown WebSocket message type: {message_type}")
                
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in WebSocket message: {message}")
        except Exception as e:
            logger.error(f"Error handling WebSocket message: {e}")
    
    async def handle_timeline_filter_request(self, websocket, data: Dict[str, Any], workspace_id: str):
        """
        Handle real-time timeline filter requests
        """
        try:
            filter_criteria = data.get('filter', {})
            
            # Mock response for now - would integrate with actual timeline service
            response = {
                'type': 'timeline_filter_response',
                'workspace_id': workspace_id,
                'filter_applied': filter_criteria,
                'results': [
                    {
                        'id': 'conv_1',
                        'title': 'Filtered Conversation 1',
                        'date': datetime.now().isoformat(),
                        'participants': ['user1', 'user2']
                    }
                ],
                'timestamp': time.time()
            }
            
            await websocket.send(json.dumps(response))
            logger.debug(f"Sent timeline filter response to workspace {workspace_id}")
            
        except Exception as e:
            logger.error(f"Error handling timeline filter request: {e}")
    
    async def handle_live_search_request(self, websocket, data: Dict[str, Any], workspace_id: str):
        """
        Handle real-time search requests
        """
        try:
            query = data.get('query', '')
            
            # Mock response for now - would integrate with actual search service
            response = {
                'type': 'search_live_response',
                'workspace_id': workspace_id,
                'query': query,
                'results': [
                    {
                        'id': 'result_1',
                        'title': f'Search result for "{query}"',
                        'content': 'Mock search result content',
                        'relevance': 0.95
                    }
                ],
                'timestamp': time.time()
            }
            
            await websocket.send(json.dumps(response))
            logger.debug(f"Sent live search response to workspace {workspace_id}")
            
        except Exception as e:
            logger.error(f"Error handling live search request: {e}")
    
    async def handle_presence_update(self, websocket, data: Dict[str, Any], workspace_id: str):
        """
        Handle user presence updates
        """
        try:
            user_id = data.get('user_id')
            status = data.get('status')
            
            # Broadcast presence update to all connections in workspace
            presence_update = {
                'type': 'presence_update_broadcast',
                'workspace_id': workspace_id,
                'user_id': user_id,
                'status': status,
                'timestamp': time.time()
            }
            
            await self.broadcast_to_workspace(workspace_id, presence_update)
            logger.debug(f"Broadcasted presence update for user {user_id} in workspace {workspace_id}")
            
        except Exception as e:
            logger.error(f"Error handling presence update: {e}")
    
    # ========================== UNIFIED COMMUNICATION METHODS ==========================
    
    def send_conversation_timeline_update(self, session_id: str, timeline_data: Dict[str, Any]):
        """
        Use WebSocket for conversation timeline updates (NEW)
        Falls back to SSE if WebSocket unavailable
        """
        workspace_id = timeline_data.get('workspace_id')
        
        if self.websocket_active and workspace_id in self.active_connections:
            # Send via WebSocket for real-time updates
            asyncio.create_task(self.broadcast_to_workspace(workspace_id, {
                'type': 'timeline_update',
                'data': timeline_data,
                'timestamp': time.time()
            }))
            self.connection_stats['websocket_messages_sent'] += 1
            logger.debug(f"Sent timeline update via WebSocket to workspace {workspace_id}")
        else:
            # Fallback to SSE
            try:
                from .boardroom_api import send_to_persistent_workspace
                message = json.dumps({
                    'type': 'conversation_timeline_loaded',
                    'data': timeline_data,
                    'timestamp': time.time()
                })
                send_to_persistent_workspace(session_id, message, workspace_id)
                self.connection_stats['sse_messages_sent'] += 1
                logger.debug(f"Sent timeline update via SSE fallback to session {session_id}")
            except Exception as e:
                logger.error(f"Error sending timeline update via SSE fallback: {e}")
    
    def send_search_results_update(self, session_id: str, search_results: Dict[str, Any]):
        """
        Use WebSocket for live search results (NEW)
        Falls back to SSE if WebSocket unavailable
        """
        workspace_id = search_results.get('workspace_id')
        
        if self.websocket_active and workspace_id in self.active_connections:
            # Send via WebSocket for real-time search
            asyncio.create_task(self.broadcast_to_workspace(workspace_id, {
                'type': 'search_update',
                'data': search_results,
                'timestamp': time.time()
            }))
            self.connection_stats['websocket_messages_sent'] += 1
            logger.debug(f"Sent search update via WebSocket to workspace {workspace_id}")
        else:
            # Fallback to SSE
            try:
                from .boardroom_api import send_to_persistent_workspace
                message = json.dumps({
                    'type': 'conversation_search_results',
                    'data': search_results,
                    'timestamp': time.time()
                })
                send_to_persistent_workspace(session_id, message, workspace_id)
                self.connection_stats['sse_messages_sent'] += 1
                logger.debug(f"Sent search update via SSE fallback to session {session_id}")
            except Exception as e:
                logger.error(f"Error sending search update via SSE fallback: {e}")
    
    async def broadcast_to_workspace(self, workspace_id: str, message: Dict[str, Any]):
        """
        Broadcast message to all WebSocket connections in a workspace
        """
        if workspace_id not in self.active_connections:
            return
        
        connections_to_remove = set()
        message_str = json.dumps(message)
        
        for connection in self.active_connections[workspace_id]:
            try:
                await connection.send(message_str)
            except websockets.exceptions.ConnectionClosed:
                connections_to_remove.add(connection)
            except Exception as e:
                logger.error(f"Error broadcasting to connection: {e}")
                connections_to_remove.add(connection)
        
        # Clean up closed connections
        self.active_connections[workspace_id] -= connections_to_remove
    
    # ========================== SYSTEM MONITORING AND STATS ==========================
    
    def get_system_stats(self) -> Dict[str, Any]:
        """
        Get system statistics for monitoring
        """
        uptime = time.time() - self.connection_stats['start_time']
        
        return {
            'sse_active': self.sse_active,
            'websocket_active': self.websocket_active,
            'uptime_seconds': uptime,
            'sse_messages_sent': self.connection_stats['sse_messages_sent'],
            'websocket_messages_sent': self.connection_stats['websocket_messages_sent'],
            'active_websocket_connections': self.connection_stats['websocket_connections'],
            'active_workspaces': len(self.active_connections),
            'total_connections': sum(len(connections) for connections in self.active_connections.values())
        }
    
    def reset_stats(self):
        """
        Reset statistics counters
        """
        self.connection_stats = {
            'sse_messages_sent': 0,
            'websocket_messages_sent': 0,
            'websocket_connections': 0,
            'start_time': time.time()
        }
        logger.info("System statistics reset")

# Global instance for use across the application
unified_realtime = UnifiedRealTimeSystem()

# ========================== CONVENIENCE FUNCTIONS ==========================

def send_claude_feedback(session_id: str, response: str, workspace_id: str):
    """Convenience function for sending Claude feedback"""
    unified_realtime.send_claude_feedback_update(session_id, response, workspace_id)

def send_timeline_update(session_id: str, timeline_data: Dict[str, Any]):
    """Convenience function for sending timeline updates"""
    unified_realtime.send_conversation_timeline_update(session_id, timeline_data)

def send_search_update(session_id: str, search_results: Dict[str, Any]):
    """Convenience function for sending search updates"""
    unified_realtime.send_search_results_update(session_id, search_results)

def send_export_notification(session_id: str, notification_data: Dict[str, Any]):
    """Convenience function for sending export notifications"""
    unified_realtime.send_export_notification(session_id, notification_data)

def send_status_update(session_id: str, status_data: Dict[str, Any]):
    """Convenience function for sending status updates"""
    unified_realtime.send_status_update(session_id, status_data)

def get_realtime_stats() -> Dict[str, Any]:
    """Convenience function for getting system statistics"""
    return unified_realtime.get_system_stats()

async def start_websocket_server(port: int = 8766):
    """Convenience function for starting WebSocket server"""
    await unified_realtime.start_websocket_server(port)

async def stop_websocket_server():
    """Convenience function for stopping WebSocket server"""
    await unified_realtime.stop_websocket_server()

if __name__ == "__main__":
    # Example usage and testing
    async def test_unified_system():
        """Test the unified real-time system"""
        logger.info("Testing Unified Real-time System")
        
        # Start WebSocket server
        await start_websocket_server()
        
        # Test SSE functionality
        send_claude_feedback("test_session", "Test Claude response", "test_workspace")
        
        # Test WebSocket functionality
        send_timeline_update("test_session", {
            'workspace_id': 'test_workspace',
            'conversations': [
                {'id': 'conv1', 'title': 'Test Conversation', 'date': datetime.now().isoformat()}
            ]
        })
        
        # Show stats
        stats = get_realtime_stats()
        logger.info(f"System stats: {stats}")
        
        # Keep server running for testing
        try:
            await asyncio.Future()  # Run forever
        except KeyboardInterrupt:
            logger.info("Shutting down...")
            await stop_websocket_server()
    
    asyncio.run(test_unified_system())