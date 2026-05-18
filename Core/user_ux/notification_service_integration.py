#!/usr/bin/env python3
"""
Notification Service Integration for Unified Real-time System

This module integrates existing notification services with the unified real-time system,
routing notifications through both SSE and WebSocket as appropriate for optimal delivery.

Integrates:
- ConversationStatusNotifications
- BoardRoomConversationStreaming  
- AgentCommunicationNotifications
"""

import json
import logging
import asyncio
import time
from typing import Dict, Any, Optional
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NotificationServiceIntegration:
    """
    Integrates existing notification services with unified real-time system
    """
    
    def __init__(self, unified_realtime_system):
        """
        Initialize notification service integration
        
        Args:
            unified_realtime_system: Instance of UnifiedRealTimeSystem
        """
        self.unified_realtime = unified_realtime_system
        self.integrated_services = {}
        self.notification_stats = {
            'conversation_status_notifications': 0,
            'boardroom_streaming_notifications': 0,
            'agent_communication_notifications': 0,
            'total_notifications_routed': 0
        }
        
        logger.info("Notification Service Integration initialized")
    
    def integrate_conversation_status_notifications(self, conversation_status_service):
        """
        Integrate ConversationStatusNotifications with unified real-time system
        
        Args:
            conversation_status_service: ConversationStatusNotifications instance
        """
        try:
            # Store reference to the service
            self.integrated_services['conversation_status'] = conversation_status_service
            
            # Override the service's broadcast method to route through unified system
            original_broadcast = conversation_status_service._broadcast_status_change
            
            async def unified_broadcast_status_change(event):
                """Route conversation status notifications through unified system"""
                try:
                    # Convert the event to unified format
                    notification_data = {
                        'type': 'conversation_status_change',
                        'conversation_id': event.conversation_id,
                        'workspace_id': event.workspace_id,
                        'user_id': event.user_id,
                        'change_type': event.change_type.value,
                        'old_value': event.old_value,
                        'new_value': event.new_value,
                        'priority': event.priority.value,
                        'timestamp': event.timestamp.isoformat(),
                        'event_id': event.event_id,
                        'metadata': event.metadata
                    }
                    
                    # Route through unified real-time system
                    self.unified_realtime.send_status_update(
                        event.user_id,  # session_id 
                        notification_data
                    )
                    
                    self.notification_stats['conversation_status_notifications'] += 1
                    self.notification_stats['total_notifications_routed'] += 1
                    
                    logger.debug(f"Routed conversation status notification: {event.change_type.value}")
                    
                    # Still call original broadcast for backward compatibility if needed
                    # await original_broadcast(event)
                    
                except Exception as e:
                    logger.error(f"Error routing conversation status notification: {e}")
            
            # Replace the service's broadcast method
            conversation_status_service._broadcast_status_change = unified_broadcast_status_change
            
            logger.info("Successfully integrated ConversationStatusNotifications")
            
        except Exception as e:
            logger.error(f"Error integrating ConversationStatusNotifications: {e}")
    
    def integrate_boardroom_streaming(self, boardroom_streaming_service):
        """
        Integrate BoardRoomConversationStreaming with unified real-time system
        
        Args:
            boardroom_streaming_service: BoardRoomConversationStreaming instance
        """
        try:
            # Store reference to the service
            self.integrated_services['boardroom_streaming'] = boardroom_streaming_service
            
            # Override the service's broadcast method to route through unified system
            if hasattr(boardroom_streaming_service, '_broadcast_boardroom_event'):
                original_broadcast = boardroom_streaming_service._broadcast_boardroom_event
                
                async def unified_broadcast_boardroom_event(event):
                    """Route BoardRoom streaming notifications through unified system"""
                    try:
                        # Convert the event to unified format
                        notification_data = {
                            'type': 'boardroom_event',
                            'event_type': event.event_type.value,
                            'conversation_id': event.conversation_id,
                            'workspace_id': event.workspace_id,
                            'boardroom_state': event.boardroom_state.value,
                            'participants': event.participants,
                            'model_exchanges': event.model_exchanges,
                            'timestamp': event.timestamp.isoformat(),
                            'event_id': event.event_id,
                            'metadata': event.metadata
                        }
                        
                        # Route through unified real-time system - use WebSocket for real-time BoardRoom updates
                        self.unified_realtime.send_conversation_timeline_update(
                            event.participants[0] if event.participants else 'system',  # session_id
                            notification_data
                        )
                        
                        self.notification_stats['boardroom_streaming_notifications'] += 1
                        self.notification_stats['total_notifications_routed'] += 1
                        
                        logger.debug(f"Routed BoardRoom streaming notification: {event.event_type.value}")
                        
                    except Exception as e:
                        logger.error(f"Error routing BoardRoom streaming notification: {e}")
                
                # Replace the service's broadcast method
                boardroom_streaming_service._broadcast_boardroom_event = unified_broadcast_boardroom_event
            
            logger.info("Successfully integrated BoardRoomConversationStreaming")
            
        except Exception as e:
            logger.error(f"Error integrating BoardRoomConversationStreaming: {e}")
    
    def integrate_agent_communication_notifications(self, agent_communication_service):
        """
        Integrate AgentCommunicationNotifications with unified real-time system
        
        Args:
            agent_communication_service: AgentCommunicationNotifications instance
        """
        try:
            # Store reference to the service
            self.integrated_services['agent_communication'] = agent_communication_service
            
            # Override the service's broadcast method to route through unified system
            if hasattr(agent_communication_service, '_broadcast_agent_communication'):
                original_broadcast = agent_communication_service._broadcast_agent_communication
                
                async def unified_broadcast_agent_communication(communication):
                    """Route agent communication notifications through unified system"""
                    try:
                        # Convert the communication to unified format
                        notification_data = {
                            'type': 'agent_communication',
                            'communication_type': communication.communication_type.value,
                            'agent_id': communication.agent_id,
                            'target_agent_id': communication.target_agent_id,
                            'workspace_id': communication.workspace_id,
                            'priority': communication.priority.value,
                            'message': communication.message,
                            'status': communication.status.value,
                            'timestamp': communication.timestamp.isoformat(),
                            'communication_id': communication.communication_id,
                            'metadata': communication.metadata
                        }
                        
                        # Route through unified real-time system
                        # Use SSE for agent status updates, WebSocket for real-time coordination
                        if communication.communication_type.value in ['status_update', 'error_notification']:
                            self.unified_realtime.send_status_update(
                                communication.target_agent_id or 'system',  # session_id
                                notification_data
                            )
                        else:
                            self.unified_realtime.send_conversation_timeline_update(
                                communication.target_agent_id or 'system',  # session_id
                                notification_data
                            )
                        
                        self.notification_stats['agent_communication_notifications'] += 1
                        self.notification_stats['total_notifications_routed'] += 1
                        
                        logger.debug(f"Routed agent communication notification: {communication.communication_type.value}")
                        
                    except Exception as e:
                        logger.error(f"Error routing agent communication notification: {e}")
                
                # Replace the service's broadcast method
                agent_communication_service._broadcast_agent_communication = unified_broadcast_agent_communication
            
            logger.info("Successfully integrated AgentCommunicationNotifications")
            
        except Exception as e:
            logger.error(f"Error integrating AgentCommunicationNotifications: {e}")
    
    def integrate_all_notification_services(self):
        """
        Convenience method to integrate all available notification services
        """
        try:
            # Import and initialize notification services
            from conversation_status_notifications import ConversationStatusNotifications
            from boardroom_conversation_streaming import BoardRoomConversationStreaming  
            from agent_communication_notifications import AgentCommunicationNotifications
            from conversation_websocket_updates import ConversationWebSocketUpdates
            from conversation_aggregator import ConversationAggregator
            
            # Initialize dependencies
            websocket_updates = ConversationWebSocketUpdates()
            conversation_aggregator = ConversationAggregator()
            
            # Initialize notification services
            conversation_status_service = ConversationStatusNotifications(
                websocket_updates, conversation_aggregator
            )
            boardroom_streaming_service = BoardRoomConversationStreaming(
                websocket_updates, conversation_aggregator
            )
            agent_communication_service = AgentCommunicationNotifications(
                websocket_updates, conversation_aggregator
            )
            
            # Integrate each service
            self.integrate_conversation_status_notifications(conversation_status_service)
            self.integrate_boardroom_streaming(boardroom_streaming_service)
            self.integrate_agent_communication_notifications(agent_communication_service)
            
            logger.info("Successfully integrated all notification services")
            
        except ImportError as e:
            logger.warning(f"Could not import all notification services: {e}")
        except Exception as e:
            logger.error(f"Error integrating all notification services: {e}")
    
    def get_integration_stats(self) -> Dict[str, Any]:
        """
        Get statistics about notification service integration
        
        Returns:
            Dictionary with integration statistics
        """
        return {
            'integrated_services': list(self.integrated_services.keys()),
            'notification_stats': self.notification_stats.copy(),
            'unified_realtime_stats': self.unified_realtime.get_system_stats()
        }
    
    def test_notification_routing(self, test_session_id: str = "test_session", test_workspace_id: str = "test_workspace"):
        """
        Test notification routing through the unified system
        
        Args:
            test_session_id: Session ID for testing
            test_workspace_id: Workspace ID for testing
        """
        try:
            logger.info("Testing notification routing...")
            
            # Test conversation status notification
            test_status_data = {
                'type': 'conversation_status_change',
                'change_type': 'status_updated',
                'conversation_id': 'test_conv_1',
                'workspace_id': test_workspace_id,
                'old_value': 'active',
                'new_value': 'completed',
                'timestamp': datetime.now().isoformat()
            }
            
            self.unified_realtime.send_status_update(test_session_id, test_status_data)
            
            # Test BoardRoom streaming notification
            test_boardroom_data = {
                'type': 'boardroom_event',
                'event_type': 'consensus_reached',
                'conversation_id': 'test_boardroom_1',
                'workspace_id': test_workspace_id,
                'participants': ['claude', 'gpt'],
                'timestamp': datetime.now().isoformat()
            }
            
            self.unified_realtime.send_conversation_timeline_update(test_session_id, test_boardroom_data)
            
            # Test agent communication notification
            test_agent_data = {
                'type': 'agent_communication',
                'communication_type': 'handoff_completed',
                'agent_id': 'agent_1',
                'target_agent_id': 'agent_2',
                'workspace_id': test_workspace_id,
                'timestamp': datetime.now().isoformat()
            }
            
            self.unified_realtime.send_conversation_timeline_update(test_session_id, test_agent_data)
            
            logger.info("Notification routing test completed successfully")
            
        except Exception as e:
            logger.error(f"Error testing notification routing: {e}")

# Global integration instance
notification_integration = None

def get_notification_integration(unified_realtime_system):
    """
    Get or create the global notification integration instance
    
    Args:
        unified_realtime_system: UnifiedRealTimeSystem instance
        
    Returns:
        NotificationServiceIntegration instance
    """
    global notification_integration
    
    if notification_integration is None:
        notification_integration = NotificationServiceIntegration(unified_realtime_system)
    
    return notification_integration

def integrate_notification_services(unified_realtime_system):
    """
    Convenience function to integrate all notification services
    
    Args:
        unified_realtime_system: UnifiedRealTimeSystem instance
        
    Returns:
        NotificationServiceIntegration instance
    """
    integration = get_notification_integration(unified_realtime_system)
    integration.integrate_all_notification_services()
    return integration

if __name__ == "__main__":
    # Test the integration
    async def test_integration():
        """Test notification service integration"""
        logger.info("Testing Notification Service Integration")
        
        # Import unified real-time system
        from unified_realtime_system import unified_realtime
        
        # Create integration
        integration = integrate_notification_services(unified_realtime)
        
        # Test notification routing
        integration.test_notification_routing()
        
        # Show stats
        stats = integration.get_integration_stats()
        logger.info(f"Integration stats: {stats}")
    
    asyncio.run(test_integration())