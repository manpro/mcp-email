#!/usr/bin/env python3
"""
WebSocket Hub for Real-time Communication
Handles WebSocket connections and real-time event broadcasting
"""

import json
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Set, Any, Optional
from dataclasses import dataclass
from enum import Enum

from fastapi import WebSocket, WebSocketDisconnect
from fastapi.websockets import WebSocketState

from .events import event_stream, Event, EventType

logger = logging.getLogger(__name__)


class MessageType(Enum):
    """WebSocket message types"""
    PING = "ping"
    PONG = "pong"
    SUBSCRIBE = "subscribe"
    UNSUBSCRIBE = "unsubscribe"
    EVENT = "event"
    ERROR = "error"
    STATUS = "status"


@dataclass
class WebSocketMessage:
    """WebSocket message structure"""
    type: MessageType
    data: Any = None
    timestamp: str = None
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'type': self.type.value,
            'data': self.data,
            'timestamp': self.timestamp
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WebSocketMessage':
        return cls(
            type=MessageType(data['type']),
            data=data.get('data'),
            timestamp=data.get('timestamp')
        )


class ConnectionManager:
    """Manage WebSocket connections and subscriptions"""
    
    def __init__(self):
        # Active connections by user_id
        self.connections: Dict[str, List[WebSocket]] = {}
        
        # Subscriptions by user_id to event types
        self.subscriptions: Dict[str, Set[EventType]] = {}
        
        # Connection metadata
        self.connection_info: Dict[WebSocket, Dict[str, Any]] = {}
        
        # Keep track of connection counts for monitoring
        self.stats = {
            'total_connections': 0,
            'active_connections': 0,
            'total_messages_sent': 0,
            'total_events_processed': 0
        }
    
    async def connect(self, websocket: WebSocket, user_id: str):
        """Accept WebSocket connection"""
        await websocket.accept()
        
        # Add to connections
        if user_id not in self.connections:
            self.connections[user_id] = []
        self.connections[user_id].append(websocket)
        
        # Add connection info
        self.connection_info[websocket] = {
            'user_id': user_id,
            'connected_at': datetime.utcnow(),
            'last_ping': datetime.utcnow()
        }
        
        # Initialize subscriptions
        if user_id not in self.subscriptions:
            self.subscriptions[user_id] = set()
        
        # Update stats
        self.stats['total_connections'] += 1
        self.stats['active_connections'] = len(self.connection_info)
        
        logger.info(f"WebSocket connected: user={user_id}, total_active={self.stats['active_connections']}")
        
        # Send welcome message
        await self.send_message(websocket, WebSocketMessage(
            type=MessageType.STATUS,
            data={'status': 'connected', 'user_id': user_id}
        ))
    
    def disconnect(self, websocket: WebSocket):
        """Remove WebSocket connection"""
        if websocket not in self.connection_info:
            return
        
        user_id = self.connection_info[websocket]['user_id']
        
        # Remove from connections
        if user_id in self.connections:
            if websocket in self.connections[user_id]:
                self.connections[user_id].remove(websocket)
            
            # Remove user if no more connections
            if not self.connections[user_id]:
                del self.connections[user_id]
                if user_id in self.subscriptions:
                    del self.subscriptions[user_id]
        
        # Remove connection info
        del self.connection_info[websocket]
        
        # Update stats
        self.stats['active_connections'] = len(self.connection_info)
        
        logger.info(f"WebSocket disconnected: user={user_id}, total_active={self.stats['active_connections']}")
    
    async def send_message(self, websocket: WebSocket, message: WebSocketMessage):
        """Send message to specific WebSocket"""
        try:
            if websocket.client_state == WebSocketState.CONNECTED:
                await websocket.send_text(json.dumps(message.to_dict()))
                self.stats['total_messages_sent'] += 1
                return True
        except Exception as e:
            logger.error(f"Error sending WebSocket message: {e}")
            return False
        return False
    
    async def send_to_user(self, user_id: str, message: WebSocketMessage):
        """Send message to all connections for a user"""
        if user_id not in self.connections:
            return 0
        
        sent_count = 0
        connections_to_remove = []
        
        for websocket in self.connections[user_id].copy():
            success = await self.send_message(websocket, message)
            if success:
                sent_count += 1
            else:
                connections_to_remove.append(websocket)
        
        # Clean up failed connections
        for websocket in connections_to_remove:
            self.disconnect(websocket)
        
        return sent_count
    
    async def broadcast(self, message: WebSocketMessage, event_type: EventType = None):
        """Broadcast message to all subscribed users"""
        sent_count = 0
        
        for user_id, subscriptions in self.subscriptions.items():
            # Check if user is subscribed to this event type
            if event_type and event_type not in subscriptions:
                continue
            
            count = await self.send_to_user(user_id, message)
            sent_count += count
        
        logger.debug(f"Broadcasted message to {sent_count} connections")
        return sent_count
    
    def subscribe(self, user_id: str, event_type: EventType):
        """Subscribe user to event type"""
        if user_id not in self.subscriptions:
            self.subscriptions[user_id] = set()
        
        self.subscriptions[user_id].add(event_type)
        logger.info(f"User {user_id} subscribed to {event_type.value}")
    
    def unsubscribe(self, user_id: str, event_type: EventType):
        """Unsubscribe user from event type"""
        if user_id in self.subscriptions:
            self.subscriptions[user_id].discard(event_type)
            logger.info(f"User {user_id} unsubscribed from {event_type.value}")
    
    async def handle_message(self, websocket: WebSocket, message_data: str):
        """Handle incoming WebSocket message"""
        try:
            data = json.loads(message_data)
            message = WebSocketMessage.from_dict(data)
            user_id = self.connection_info[websocket]['user_id']
            
            if message.type == MessageType.PING:
                # Respond with pong
                await self.send_message(websocket, WebSocketMessage(
                    type=MessageType.PONG,
                    data={'timestamp': datetime.utcnow().isoformat()}
                ))
                # Update last ping
                self.connection_info[websocket]['last_ping'] = datetime.utcnow()
            
            elif message.type == MessageType.SUBSCRIBE:
                # Subscribe to event type
                if message.data and 'event_type' in message.data:
                    try:
                        event_type = EventType(message.data['event_type'])
                        self.subscribe(user_id, event_type)
                        await self.send_message(websocket, WebSocketMessage(
                            type=MessageType.STATUS,
                            data={'status': 'subscribed', 'event_type': event_type.value}
                        ))
                    except ValueError:
                        await self.send_message(websocket, WebSocketMessage(
                            type=MessageType.ERROR,
                            data={'error': 'Invalid event type'}
                        ))
            
            elif message.type == MessageType.UNSUBSCRIBE:
                # Unsubscribe from event type
                if message.data and 'event_type' in message.data:
                    try:
                        event_type = EventType(message.data['event_type'])
                        self.unsubscribe(user_id, event_type)
                        await self.send_message(websocket, WebSocketMessage(
                            type=MessageType.STATUS,
                            data={'status': 'unsubscribed', 'event_type': event_type.value}
                        ))
                    except ValueError:
                        await self.send_message(websocket, WebSocketMessage(
                            type=MessageType.ERROR,
                            data={'error': 'Invalid event type'}
                        ))
            
            else:
                logger.warning(f"Unknown message type: {message.type}")
                
        except Exception as e:
            logger.error(f"Error handling WebSocket message: {e}")
            await self.send_message(websocket, WebSocketMessage(
                type=MessageType.ERROR,
                data={'error': 'Invalid message format'}
            ))
    
    def get_stats(self) -> Dict[str, Any]:
        """Get connection statistics"""
        return {
            **self.stats,
            'users_connected': len(self.connections),
            'subscriptions': {
                user_id: [et.value for et in subs] 
                for user_id, subs in self.subscriptions.items()
            }
        }


# Global connection manager
connection_manager = ConnectionManager()


class EventBroadcaster:
    """Broadcasts events to WebSocket clients"""
    
    def __init__(self, connection_manager: ConnectionManager):
        self.connection_manager = connection_manager
        self.is_running = False
    
    async def start(self):
        """Start the event broadcaster"""
        self.is_running = True
        logger.info("Starting WebSocket event broadcaster")
        
        # Start consuming events from Redis Streams
        await event_stream.consume("websocket-broadcaster", self.handle_event)
    
    def stop(self):
        """Stop the event broadcaster"""
        self.is_running = False
        logger.info("Stopping WebSocket event broadcaster")
    
    async def handle_event(self, event: Event):
        """Handle event and broadcast to subscribers"""
        if not self.is_running:
            return
        
        try:
            # Create WebSocket message from event
            ws_message = WebSocketMessage(
                type=MessageType.EVENT,
                data={
                    'event_type': event.event_type.value,
                    'data': event.data,
                    'timestamp': event.timestamp.isoformat(),
                    'source': event.source
                }
            )
            
            # Broadcast to subscribed users
            if event.user_id:
                # Send to specific user
                await self.connection_manager.send_to_user(event.user_id, ws_message)
            else:
                # Broadcast to all subscribers
                await self.connection_manager.broadcast(ws_message, event.event_type)
            
            self.connection_manager.stats['total_events_processed'] += 1
            
        except Exception as e:
            logger.error(f"Error broadcasting event: {e}")


# Global event broadcaster
event_broadcaster = EventBroadcaster(connection_manager)


# Health check function
async def cleanup_stale_connections():
    """Clean up stale connections (call periodically)"""
    stale_limit = 300  # 5 minutes
    now = datetime.utcnow()
    
    stale_connections = []
    for websocket, info in connection_manager.connection_info.items():
        if (now - info['last_ping']).seconds > stale_limit:
            stale_connections.append(websocket)
    
    for websocket in stale_connections:
        logger.info(f"Cleaning up stale connection for user {connection_manager.connection_info[websocket]['user_id']}")
        connection_manager.disconnect(websocket)
    
    return len(stale_connections)


# Utility functions
async def notify_user(user_id: str, notification_type: str, data: Dict[str, Any]):
    """Send notification to specific user"""
    message = WebSocketMessage(
        type=MessageType.EVENT,
        data={
            'event_type': 'notification',
            'notification_type': notification_type,
            'data': data
        }
    )
    await connection_manager.send_to_user(user_id, message)


async def broadcast_system_status(status: str, data: Dict[str, Any] = None):
    """Broadcast system status to all connected users"""
    message = WebSocketMessage(
        type=MessageType.STATUS,
        data={
            'status': status,
            'data': data or {}
        }
    )
    await connection_manager.broadcast(message)