#!/usr/bin/env python3
"""
Real-time Event Streaming System for RSS Intelligence
Handles event publishing and consumption via Redis Streams
"""

import json
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, AsyncGenerator, Callable
from dataclasses import dataclass, asdict
from enum import Enum

import redis.asyncio as redis
from redis.asyncio.client import Redis

from .config import settings

logger = logging.getLogger(__name__)


class EventType(Enum):
    """Event types for the streaming system"""
    ARTICLE_NEW = "article.new"
    ARTICLE_UPDATED = "article.updated"
    ARTICLE_SCORED = "article.scored"
    TREND_DETECTED = "trend.detected"
    ALERT_TRIGGERED = "alert.triggered"
    USER_ACTION = "user.action"
    SYSTEM_STATUS = "system.status"
    SPOTLIGHT_UPDATED = "spotlight.updated"


@dataclass
class Event:
    """Base event structure"""
    event_type: EventType
    data: Dict[str, Any]
    timestamp: datetime
    user_id: Optional[str] = None
    source: str = "rss-intelligence"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for Redis"""
        return {
            'event_type': self.event_type.value,
            'data': json.dumps(self.data),
            'timestamp': self.timestamp.isoformat(),
            'user_id': self.user_id,
            'source': self.source
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Event':
        """Create event from Redis dictionary"""
        return cls(
            event_type=EventType(data['event_type']),
            data=json.loads(data['data']),
            timestamp=datetime.fromisoformat(data['timestamp']),
            user_id=data.get('user_id'),
            source=data.get('source', 'rss-intelligence')
        )


class EventStream:
    """Redis Streams based event streaming system"""
    
    def __init__(self, redis_url: str = None):
        self.redis_url = redis_url or getattr(settings, 'redis_url', 'redis://redis:6379')
        self.redis: Optional[Redis] = None
        self.stream_name = "rss:events"
        self.consumer_group = "rss-processors"
        
    async def connect(self):
        """Connect to Redis"""
        if not self.redis:
            self.redis = redis.from_url(self.redis_url, decode_responses=True)
            
            # Create consumer group if it doesn't exist
            try:
                await self.redis.xgroup_create(
                    self.stream_name, 
                    self.consumer_group, 
                    id="0", 
                    mkstream=True
                )
                logger.info(f"Created consumer group '{self.consumer_group}'")
            except Exception as e:
                if "BUSYGROUP" not in str(e):
                    logger.warning(f"Error creating consumer group: {e}")
    
    async def disconnect(self):
        """Disconnect from Redis"""
        if self.redis:
            await self.redis.close()
            self.redis = None
    
    async def publish(self, event: Event) -> str:
        """Publish event to stream"""
        await self.connect()
        
        event_id = await self.redis.xadd(
            self.stream_name,
            event.to_dict(),
            maxlen=10000  # Keep last 10k events
        )
        
        logger.debug(f"Published event {event.event_type.value} with ID {event_id}")
        return event_id
    
    async def consume(
        self, 
        consumer_name: str,
        handler: Callable[[Event], None],
        count: int = 10
    ):
        """Consume events from stream"""
        await self.connect()
        
        logger.info(f"Starting consumer '{consumer_name}' for stream '{self.stream_name}'")
        
        while True:
            try:
                # Read new messages
                messages = await self.redis.xreadgroup(
                    self.consumer_group,
                    consumer_name,
                    {self.stream_name: ">"},
                    count=count,
                    block=1000  # Block for 1 second
                )
                
                for stream, msgs in messages:
                    for msg_id, fields in msgs:
                        try:
                            event = Event.from_dict(fields)
                            await handler(event)
                            
                            # Acknowledge message
                            await self.redis.xack(self.stream_name, self.consumer_group, msg_id)
                            
                        except Exception as e:
                            logger.error(f"Error processing event {msg_id}: {e}")
                            # Could implement dead letter queue here
                            
            except Exception as e:
                logger.error(f"Error in event consumer: {e}")
                await asyncio.sleep(5)  # Wait before retrying
    
    async def get_pending(self, consumer_name: str) -> List[Dict[str, Any]]:
        """Get pending messages for consumer"""
        await self.connect()
        
        pending = await self.redis.xpending_range(
            self.stream_name,
            self.consumer_group,
            min="-",
            max="+",
            count=100
        )
        
        return [
            {
                'id': msg_id,
                'consumer': consumer,
                'idle_time': idle_time
            }
            for msg_id, consumer, idle_time, delivery_count in pending
        ]
    
    async def get_stream_info(self) -> Dict[str, Any]:
        """Get stream information"""
        await self.connect()
        
        try:
            info = await self.redis.xinfo_stream(self.stream_name)
            groups = await self.redis.xinfo_groups(self.stream_name)
            
            return {
                'stream': info,
                'groups': groups,
                'length': info.get('length', 0),
                'last_generated_id': info.get('last-generated-id', '0-0')
            }
        except Exception as e:
            logger.warning(f"Could not get stream info: {e}")
            return {}


# Global event stream instance
event_stream = EventStream()


# Event Publishing Helper Functions
async def publish_article_event(article_id: int, event_type: EventType, data: Dict[str, Any]):
    """Publish article-related event"""
    event = Event(
        event_type=event_type,
        data={'article_id': article_id, **data},
        timestamp=datetime.utcnow()
    )
    await event_stream.publish(event)


async def publish_trend_event(trend_data: Dict[str, Any]):
    """Publish trend detection event"""
    event = Event(
        event_type=EventType.TREND_DETECTED,
        data=trend_data,
        timestamp=datetime.utcnow()
    )
    await event_stream.publish(event)


async def publish_alert_event(user_id: str, alert_data: Dict[str, Any]):
    """Publish user alert event"""
    event = Event(
        event_type=EventType.ALERT_TRIGGERED,
        data=alert_data,
        timestamp=datetime.utcnow(),
        user_id=user_id
    )
    await event_stream.publish(event)


async def publish_user_action(user_id: str, action: str, data: Dict[str, Any]):
    """Publish user action event"""
    event = Event(
        event_type=EventType.USER_ACTION,
        data={'action': action, **data},
        timestamp=datetime.utcnow(),
        user_id=user_id
    )
    await event_stream.publish(event)


# Event Consumers
class ArticleProcessor:
    """Process article events"""
    
    async def handle_new_article(self, event: Event):
        """Handle new article event"""
        article_id = event.data.get('article_id')
        logger.info(f"Processing new article: {article_id}")
        
        # Trigger scoring, trend detection, etc.
        # This will be implemented in the next phase
        
    async def handle_article_update(self, event: Event):
        """Handle article update event"""
        article_id = event.data.get('article_id')
        logger.info(f"Processing article update: {article_id}")


class TrendProcessor:
    """Process trend events"""
    
    async def handle_trend_detection(self, event: Event):
        """Handle trend detection event"""
        trend_data = event.data
        logger.info(f"Processing trend: {trend_data.get('trend_name')}")
        
        # Check if this should trigger alerts
        # Update spotlight content
        # Notify interested users


class AlertProcessor:
    """Process alert events"""
    
    async def handle_alert_trigger(self, event: Event):
        """Handle alert trigger event"""
        user_id = event.user_id
        alert_data = event.data
        
        logger.info(f"Processing alert for user {user_id}: {alert_data.get('alert_type')}")
        
        # Send push notification
        # Send email if configured
        # Update user's alert dashboard


# Event Router - routes events to appropriate processors
async def route_event(event: Event):
    """Route events to appropriate processors"""
    processors = {
        EventType.ARTICLE_NEW: ArticleProcessor().handle_new_article,
        EventType.ARTICLE_UPDATED: ArticleProcessor().handle_article_update,
        EventType.TREND_DETECTED: TrendProcessor().handle_trend_detection,
        EventType.ALERT_TRIGGERED: AlertProcessor().handle_alert_trigger,
    }
    
    handler = processors.get(event.event_type)
    if handler:
        try:
            await handler(event)
        except Exception as e:
            logger.error(f"Error processing {event.event_type.value}: {e}")
    else:
        logger.warning(f"No handler for event type: {event.event_type.value}")


# Main event consumer
async def start_event_consumer(consumer_name: str = "main-processor"):
    """Start the main event consumer"""
    logger.info(f"Starting event consumer: {consumer_name}")
    await event_stream.consume(consumer_name, route_event)


# Cleanup
async def cleanup_events():
    """Cleanup event stream connections"""
    await event_stream.disconnect()