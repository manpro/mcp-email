"""
DirectRSSClient - Direct RSS feed polling from ai_feed table
Fallback/replacement for FreshRSSClient when not available
"""
import feedparser
import hashlib
import logging
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any
from urllib.parse import urlparse, urljoin
import asyncio
import aiohttp
from sqlalchemy.orm import Session
from sqlalchemy import text

logger = logging.getLogger(__name__)


class DirectRSSClient:
    """Direct RSS client that polls feeds from ai_feed table"""
    
    def __init__(self, db: Session):
        self.db = db
        self.session = None
        self._setup_session()
    
    def _setup_session(self):
        """Setup aiohttp session for feed fetching"""
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        connector = aiohttp.TCPConnector(limit=10, limit_per_host=3)
        
        self.session = aiohttp.ClientSession(
            timeout=timeout,
            connector=connector,
            headers={
                'User-Agent': 'RSSIntelBot/1.0 (RSS Intelligence Dashboard)'
            }
        )
    
    async def close(self):
        """Close HTTP session"""
        if self.session:
            await self.session.close()
    
    def login(self) -> bool:
        """Mock login for compatibility with FreshRSSClient interface"""
        return True
    
    def get_feeds(self) -> List[Dict[str, Any]]:
        """Get all active feeds from ai_feed table"""
        try:
            result = self.db.execute(
                text("""
                    SELECT f.id, f.url, f.name, f.description, f.website, f.priority,
                           c.name as category_name
                    FROM ai_feed f
                    LEFT JOIN ai_category c ON f.category = c.id
                    WHERE f.error = 0
                    ORDER BY f.priority DESC, f.name
                """)
            )
            
            feeds = []
            for row in result:
                feeds.append({
                    'id': row.id,
                    'url': row.url,
                    'title': row.name,
                    'description': row.description or '',
                    'website': row.website or '',
                    'category': row.category_name or 'Uncategorized',
                    'priority': row.priority or 5
                })
            
            logger.info(f"Found {len(feeds)} active feeds in database")
            return feeds
            
        except Exception as e:
            logger.error(f"Error getting feeds: {e}")
            return []
    
    async def fetch_feed_entries(self, feed_url: str, feed_title: str = "") -> List[Dict[str, Any]]:
        """Fetch and parse entries from a single RSS feed"""
        try:
            logger.info(f"Fetching feed: {feed_title} ({feed_url})")
            
            # Fetch RSS content
            async with self.session.get(feed_url) as response:
                if response.status != 200:
                    logger.warning(f"HTTP {response.status} for {feed_url}")
                    return []
                
                content = await response.text()
            
            # Parse with feedparser
            feed = feedparser.parse(content)
            
            if feed.bozo:
                logger.warning(f"Feed parsing issues for {feed_url}: {feed.bozo_exception}")
            
            if not hasattr(feed, 'entries') or not feed.entries:
                logger.warning(f"No entries found in feed {feed_url}")
                return []
            
            # Convert to internal format
            entries = []
            feed_source = feed_title or feed.feed.get('title', urlparse(feed_url).netloc)
            
            for entry in feed.entries:
                try:
                    # Create unique ID from URL
                    entry_id = hashlib.md5(entry.link.encode('utf-8')).hexdigest()
                    
                    # Parse published date
                    published_at = None
                    if hasattr(entry, 'published_parsed') and entry.published_parsed:
                        date_parts = list(entry.published_parsed[:6])
                        published_at = datetime(*date_parts, tzinfo=timezone.utc)
                    elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                        date_parts = list(entry.updated_parsed[:6])
                        published_at = datetime(*date_parts, tzinfo=timezone.utc)
                    else:
                        published_at = datetime.now(timezone.utc)
                    
                    # Extract content
                    content = ""
                    if hasattr(entry, 'content') and entry.content:
                        content = entry.content[0].value if entry.content else ""
                    elif hasattr(entry, 'summary'):
                        content = entry.summary
                    elif hasattr(entry, 'description'):
                        content = entry.description
                    
                    # Clean and prepare entry
                    article_entry = {
                        'freshrss_entry_id': entry_id,
                        'title': entry.title if hasattr(entry, 'title') else 'No Title',
                        'url': entry.link if hasattr(entry, 'link') else feed_url,
                        'content': content,
                        'source': feed_source,
                        'published_at': published_at,
                        'author': entry.author if hasattr(entry, 'author') else None
                    }
                    
                    entries.append(article_entry)
                    
                except Exception as e:
                    logger.error(f"Error processing entry from {feed_url}: {e}")
                    continue
            
            logger.info(f"Parsed {len(entries)} entries from {feed_source}")
            return entries
            
        except Exception as e:
            logger.error(f"Error fetching feed {feed_url}: {e}")
            return []
    
    async def get_entries(self, since_timestamp: Optional[int] = None, limit: int = 200) -> List[Dict[str, Any]]:
        """
        Get entries from all feeds
        
        Args:
            since_timestamp: Only return entries newer than this (Unix timestamp)
            limit: Maximum number of entries to return
        """
        logger.info(f"Getting entries since {since_timestamp}, limit {limit}")
        
        # Get all feeds
        feeds = self.get_feeds()
        if not feeds:
            logger.warning("No feeds found")
            return []
        
        # Fetch entries from all feeds
        all_entries = []
        
        # Process feeds with higher priority first
        sorted_feeds = sorted(feeds, key=lambda f: f.get('priority', 5), reverse=True)
        
        for feed in sorted_feeds:
            try:
                feed_entries = await self.fetch_feed_entries(
                    feed['url'], 
                    feed['title']
                )
                
                # Filter by timestamp if provided
                if since_timestamp:
                    cutoff_time = datetime.fromtimestamp(since_timestamp, tz=timezone.utc)
                    feed_entries = [
                        entry for entry in feed_entries
                        if entry['published_at'] > cutoff_time
                    ]
                
                all_entries.extend(feed_entries)
                
                # Update last fetch time in database
                try:
                    self.db.execute(
                        text('UPDATE ai_feed SET "lastUpdate" = :timestamp WHERE id = :feed_id'),
                        {
                            'timestamp': int(datetime.now(timezone.utc).timestamp()),
                            'feed_id': feed['id']
                        }
                    )
                    self.db.commit()
                except Exception as e:
                    logger.warning(f"Could not update lastUpdate for feed {feed['id']}: {e}")
                
                # Add small delay to be nice to servers
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Error processing feed {feed['title']}: {e}")
                continue
        
        # Sort by published date (newest first) and limit
        all_entries.sort(key=lambda x: x['published_at'], reverse=True)
        
        if limit and len(all_entries) > limit:
            all_entries = all_entries[:limit]
        
        logger.info(f"Returning {len(all_entries)} total entries from {len(feeds)} feeds")
        return all_entries
    
    # Compatibility methods for FreshRSSClient interface
    def add_label(self, entry_id: str, label: str) -> bool:
        """Mock label addition (labels stored in articles table)"""
        logger.debug(f"Label {label} requested for entry {entry_id} (stored in articles table)")
        return True
    
    def star_entry(self, entry_id: str) -> bool:
        """Mock star entry (stars stored in articles table)"""
        logger.debug(f"Star requested for entry {entry_id} (stored in articles table)")
        return True
    
    def create_feed(self, feed_url: str) -> bool:
        """Mock feed creation (feeds managed via ai_feed table)"""
        logger.debug(f"Feed creation requested for {feed_url} (managed via ai_feed table)")
        return True