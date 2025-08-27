#!/usr/bin/env python3
"""
Push Notification System for RSS Intelligence
Handles real-time notifications via WebSocket, email, and future push services
"""

import json
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, asdict
from enum import Enum
try:
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    import smtplib
    # Alias for compatibility - the import name in the standard library is MIMEText, not MimeText
    MimeText = MIMEText
    MimeMultipart = MIMEMultipart
except ImportError:
    # Fallback if email modules not available in container
    MimeText = None
    MimeMultipart = None
    smtplib = None

from .config import settings
from .events import Event, EventType, publish_user_action
from .websocket_hub import connection_manager, WebSocketMessage, MessageType

logger = logging.getLogger(__name__)


class NotificationType(Enum):
    """Types of notifications"""
    BREAKING_NEWS = "breaking_news"
    HIGH_SCORE_ARTICLE = "high_score_article"
    TREND_ALERT = "trend_alert"
    PRICE_ALERT = "price_alert"
    KEYWORD_MATCH = "keyword_match"
    DAILY_DIGEST = "daily_digest"
    SYSTEM_ALERT = "system_alert"


class NotificationPriority(Enum):
    """Notification priority levels"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class Notification:
    """Base notification structure"""
    id: str
    user_id: str
    type: NotificationType
    priority: NotificationPriority
    title: str
    message: str
    data: Dict[str, Any]
    created_at: datetime
    expires_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    read_at: Optional[datetime] = None
    channels: Set[str] = None  # websocket, email, push
    
    def __post_init__(self):
        if self.channels is None:
            self.channels = {"websocket"}
        if self.expires_at is None:
            # Default expiry: 24 hours for normal, 7 days for digest
            hours = 24 if self.type != NotificationType.DAILY_DIGEST else 168
            self.expires_at = self.created_at + timedelta(hours=hours)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'user_id': self.user_id,
            'type': self.type.value,
            'priority': self.priority.value,
            'title': self.title,
            'message': self.message,
            'data': self.data,
            'created_at': self.created_at.isoformat(),
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'delivered_at': self.delivered_at.isoformat() if self.delivered_at else None,
            'read_at': self.read_at.isoformat() if self.read_at else None,
            'channels': list(self.channels)
        }


class NotificationManager:
    """Manages notification creation, delivery, and tracking"""
    
    def __init__(self):
        # In-memory store for recent notifications (Redis would be better in production)
        self.notifications: Dict[str, Notification] = {}
        
        # User preferences for notification types and channels
        self.user_preferences: Dict[str, Dict[str, Any]] = {}
        
        # Delivery statistics
        self.stats = {
            'total_sent': 0,
            'websocket_sent': 0,
            'email_sent': 0,
            'failed_deliveries': 0
        }
    
    def generate_notification_id(self) -> str:
        """Generate unique notification ID"""
        import uuid
        return f"notif_{uuid.uuid4().hex[:12]}"
    
    async def send_notification(
        self,
        user_id: str,
        notification_type: NotificationType,
        title: str,
        message: str,
        data: Dict[str, Any] = None,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        channels: Set[str] = None
    ) -> str:
        """Create and send notification"""
        
        # Check user preferences
        if not self._should_send_notification(user_id, notification_type, priority):
            logger.debug(f"Notification blocked by user preferences: {user_id}, {notification_type.value}")
            return None
        
        # Create notification
        notification = Notification(
            id=self.generate_notification_id(),
            user_id=user_id,
            type=notification_type,
            priority=priority,
            title=title,
            message=message,
            data=data or {},
            created_at=datetime.utcnow(),
            channels=channels or {"websocket"}
        )
        
        # Store notification
        self.notifications[notification.id] = notification
        
        # Send via different channels
        success = await self._deliver_notification(notification)
        
        if success:
            notification.delivered_at = datetime.utcnow()
            self.stats['total_sent'] += 1
            
            # Publish user action event
            await publish_user_action(
                user_id=user_id,
                action="notification_sent",
                data={
                    'notification_id': notification.id,
                    'type': notification_type.value,
                    'priority': priority.value
                }
            )
        
        return notification.id
    
    async def _deliver_notification(self, notification: Notification) -> bool:
        """Deliver notification via all specified channels"""
        success = True
        
        # WebSocket delivery
        if "websocket" in notification.channels:
            ws_success = await self._send_websocket_notification(notification)
            if ws_success:
                self.stats['websocket_sent'] += 1
            else:
                success = False
        
        # Email delivery
        if "email" in notification.channels:
            email_success = await self._send_email_notification(notification)
            if email_success:
                self.stats['email_sent'] += 1
            else:
                success = False
        
        # Future: Push notification delivery
        if "push" in notification.channels:
            # TODO: Implement push notifications (Firebase, APNS, etc.)
            logger.info(f"Push notifications not yet implemented for {notification.id}")
        
        if not success:
            self.stats['failed_deliveries'] += 1
        
        return success
    
    async def _send_websocket_notification(self, notification: Notification) -> bool:
        """Send notification via WebSocket"""
        try:
            ws_message = WebSocketMessage(
                type=MessageType.EVENT,
                data={
                    'event_type': 'notification',
                    'notification': notification.to_dict()
                }
            )
            
            sent_count = await connection_manager.send_to_user(
                notification.user_id, 
                ws_message
            )
            
            return sent_count > 0
        except Exception as e:
            logger.error(f"WebSocket notification error: {e}")
            return False
    
    async def _send_email_notification(self, notification: Notification) -> bool:
        """Send notification via email"""
        try:
            # Check if email modules are available
            if not MimeText or not MimeMultipart or not smtplib:
                logger.warning("Email modules not available, skipping email notification")
                return False
                
            # Get user email from preferences or database
            user_email = self._get_user_email(notification.user_id)
            if not user_email:
                logger.warning(f"No email found for user {notification.user_id}")
                return False
            
            # Create email
            msg = MimeMultipart('alternative')
            msg['Subject'] = f"[RSS Intel] {notification.title}"
            msg['From'] = getattr(settings, 'smtp_from', 'noreply@rss-intel.local')
            msg['To'] = user_email
            
            # HTML content
            html_content = self._generate_email_html(notification)
            html_part = MimeText(html_content, 'html')
            msg.attach(html_part)
            
            # Send email
            smtp_settings = getattr(settings, 'smtp', {})
            if not smtp_settings.get('enabled', False):
                logger.debug("SMTP not configured, skipping email notification")
                return False
            
            with smtplib.SMTP(smtp_settings.get('host'), smtp_settings.get('port', 587)) as server:
                if smtp_settings.get('tls', True):
                    server.starttls()
                if smtp_settings.get('username'):
                    server.login(smtp_settings['username'], smtp_settings['password'])
                
                server.send_message(msg)
            
            return True
            
        except Exception as e:
            logger.error(f"Email notification error: {e}")
            return False
    
    def _should_send_notification(
        self, 
        user_id: str, 
        notification_type: NotificationType, 
        priority: NotificationPriority
    ) -> bool:
        """Check if notification should be sent based on user preferences"""
        
        # Get user preferences
        prefs = self.user_preferences.get(user_id, {})
        
        # Check if notification type is enabled
        type_enabled = prefs.get('types', {}).get(notification_type.value, True)
        if not type_enabled:
            return False
        
        # Check priority threshold
        min_priority = prefs.get('min_priority', NotificationPriority.LOW.value)
        priority_levels = {
            NotificationPriority.LOW.value: 0,
            NotificationPriority.NORMAL.value: 1,
            NotificationPriority.HIGH.value: 2,
            NotificationPriority.URGENT.value: 3
        }
        
        if priority_levels.get(priority.value, 1) < priority_levels.get(min_priority, 0):
            return False
        
        # Check rate limiting
        if self._is_rate_limited(user_id, notification_type):
            return False
        
        return True
    
    def _is_rate_limited(self, user_id: str, notification_type: NotificationType) -> bool:
        """Check if user has exceeded rate limits for notification type"""
        now = datetime.utcnow()
        hour_ago = now - timedelta(hours=1)
        
        # Count notifications of this type sent in the last hour
        recent_count = sum(
            1 for notif in self.notifications.values()
            if (notif.user_id == user_id and 
                notif.type == notification_type and 
                notif.created_at > hour_ago)
        )
        
        # Rate limits by type
        limits = {
            NotificationType.BREAKING_NEWS: 5,
            NotificationType.HIGH_SCORE_ARTICLE: 10,
            NotificationType.TREND_ALERT: 3,
            NotificationType.PRICE_ALERT: 20,
            NotificationType.KEYWORD_MATCH: 15,
            NotificationType.DAILY_DIGEST: 1,
            NotificationType.SYSTEM_ALERT: 2
        }
        
        limit = limits.get(notification_type, 10)
        return recent_count >= limit
    
    def _get_user_email(self, user_id: str) -> Optional[str]:
        """Get user email address from preferences or database"""
        # TODO: Integrate with user database
        return self.user_preferences.get(user_id, {}).get('email')
    
    def _generate_email_html(self, notification: Notification) -> str:
        """Generate HTML email content"""
        return f"""
        <html>
        <body>
            <div style="max-width: 600px; margin: 0 auto; font-family: Arial, sans-serif;">
                <div style="background: #1a1a1a; color: white; padding: 20px; text-align: center;">
                    <h1>RSS Intelligence</h1>
                </div>
                <div style="padding: 20px;">
                    <h2>{notification.title}</h2>
                    <p>{notification.message}</p>
                    <div style="margin-top: 20px; padding: 15px; background: #f5f5f5; border-radius: 5px;">
                        <p><strong>Priority:</strong> {notification.priority.value.title()}</p>
                        <p><strong>Time:</strong> {notification.created_at.strftime('%Y-%m-%d %H:%M:%S')}</p>
                    </div>
                </div>
                <div style="background: #f0f0f0; padding: 10px; text-align: center; font-size: 12px;">
                    RSS Intelligence Dashboard
                </div>
            </div>
        </body>
        </html>
        """
    
    async def mark_read(self, notification_id: str, user_id: str) -> bool:
        """Mark notification as read"""
        if notification_id in self.notifications:
            notification = self.notifications[notification_id]
            if notification.user_id == user_id:
                notification.read_at = datetime.utcnow()
                return True
        return False
    
    def get_user_notifications(
        self, 
        user_id: str, 
        limit: int = 50,
        unread_only: bool = False
    ) -> List[Dict[str, Any]]:
        """Get notifications for user"""
        user_notifications = [
            notif for notif in self.notifications.values()
            if notif.user_id == user_id
        ]
        
        if unread_only:
            user_notifications = [
                notif for notif in user_notifications
                if notif.read_at is None
            ]
        
        # Sort by creation time (newest first)
        user_notifications.sort(key=lambda n: n.created_at, reverse=True)
        
        return [notif.to_dict() for notif in user_notifications[:limit]]
    
    def set_user_preferences(self, user_id: str, preferences: Dict[str, Any]):
        """Set user notification preferences"""
        self.user_preferences[user_id] = preferences
        logger.info(f"Updated notification preferences for user {user_id}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get notification statistics"""
        return {
            **self.stats,
            'total_notifications': len(self.notifications),
            'active_users': len(set(n.user_id for n in self.notifications.values()))
        }
    
    async def cleanup_expired(self):
        """Remove expired notifications"""
        now = datetime.utcnow()
        expired_ids = [
            notif_id for notif_id, notif in self.notifications.items()
            if notif.expires_at and notif.expires_at < now
        ]
        
        for notif_id in expired_ids:
            del self.notifications[notif_id]
        
        if expired_ids:
            logger.info(f"Cleaned up {len(expired_ids)} expired notifications")


# Global notification manager
notification_manager = NotificationManager()


# Convenience functions for common notification types
async def send_breaking_news_alert(user_id: str, article_data: Dict[str, Any]):
    """Send breaking news notification"""
    await notification_manager.send_notification(
        user_id=user_id,
        notification_type=NotificationType.BREAKING_NEWS,
        title="🚨 Breaking News Alert",
        message=f"High-impact story: {article_data.get('title', 'Unknown')}",
        data=article_data,
        priority=NotificationPriority.HIGH,
        channels={"websocket", "email"}
    )


async def send_high_score_alert(user_id: str, article_data: Dict[str, Any]):
    """Send high score article notification"""
    score = article_data.get('score', 0)
    await notification_manager.send_notification(
        user_id=user_id,
        notification_type=NotificationType.HIGH_SCORE_ARTICLE,
        title=f"⭐ High Score Article ({score:.1f})",
        message=f"New high-scoring article: {article_data.get('title', 'Unknown')}",
        data=article_data,
        priority=NotificationPriority.NORMAL,
        channels={"websocket"}
    )


async def send_trend_alert(user_id: str, trend_data: Dict[str, Any]):
    """Send trend detection notification"""
    await notification_manager.send_notification(
        user_id=user_id,
        notification_type=NotificationType.TREND_ALERT,
        title="📈 Trending Topic Detected",
        message=f"New trend: {trend_data.get('trend_name', 'Unknown')}",
        data=trend_data,
        priority=NotificationPriority.HIGH,
        channels={"websocket", "email"}
    )


async def send_keyword_match(user_id: str, article_data: Dict[str, Any], keywords: List[str]):
    """Send keyword match notification"""
    await notification_manager.send_notification(
        user_id=user_id,
        notification_type=NotificationType.KEYWORD_MATCH,
        title=f"🔍 Keyword Match: {', '.join(keywords)}",
        message=f"Article matches your keywords: {article_data.get('title', 'Unknown')}",
        data={**article_data, 'matched_keywords': keywords},
        priority=NotificationPriority.NORMAL,
        channels={"websocket"}
    )


async def send_daily_digest(user_id: str, digest_data: Dict[str, Any]):
    """Send daily digest notification"""
    await notification_manager.send_notification(
        user_id=user_id,
        notification_type=NotificationType.DAILY_DIGEST,
        title="📊 Your Daily News Digest",
        message=f"Today's summary: {digest_data.get('summary', 'No summary available')}",
        data=digest_data,
        priority=NotificationPriority.LOW,
        channels={"websocket", "email"}
    )


# Event handlers for automatic notifications
async def handle_article_event(event: Event):
    """Handle article events and send relevant notifications"""
    article_data = event.data
    score = article_data.get('score', 0)
    
    # High score articles (for all users or based on preferences)
    if score >= 8.0:  # High threshold for general alerts
        # TODO: Get list of users who want high score alerts
        # For now, we'd need to integrate with user management
        pass
    
    # Breaking news detection (based on flags or score + recency)
    flags = article_data.get('flags', {})
    if flags.get('breaking') or (score >= 9.0 and 'urgent' in flags):
        # TODO: Send to users who want breaking news alerts
        pass


async def handle_trend_event(event: Event):
    """Handle trend events and send notifications"""
    trend_data = event.data
    
    # TODO: Send trend alerts to interested users
    # This would involve checking user preferences for trend categories
    pass


# Integration with event system
async def start_notification_event_consumer():
    """Start consuming events for notifications"""
    from .events import event_stream
    
    async def notification_event_handler(event: Event):
        """Handle events for notifications"""
        try:
            if event.event_type in [EventType.ARTICLE_NEW, EventType.ARTICLE_SCORED]:
                await handle_article_event(event)
            elif event.event_type == EventType.TREND_DETECTED:
                await handle_trend_event(event)
        except Exception as e:
            logger.error(f"Error in notification event handler: {e}")
    
    await event_stream.consume("notification-processor", notification_event_handler)


# Periodic cleanup task
async def periodic_notification_cleanup():
    """Periodic task to clean up expired notifications"""
    while True:
        try:
            await notification_manager.cleanup_expired()
            await asyncio.sleep(3600)  # Run every hour
        except Exception as e:
            logger.error(f"Notification cleanup error: {e}")
            await asyncio.sleep(300)  # Wait 5 minutes on error