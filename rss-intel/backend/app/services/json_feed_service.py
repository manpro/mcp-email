"""
JSON Feed Service

Support for parsing JSON Feed format (https://jsonfeed.org/) as an alternative to RSS/Atom.
Many modern websites and services provide JSON feeds which are easier to parse and more structured.
"""

import logging
import aiohttp
import asyncio
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse
import json
import re
import hashlib
from sqlalchemy.orm import Session

from ..store import Article, Feed
from ..intelligence.content_extractor import extract_content

logger = logging.getLogger(__name__)

@dataclass
class JsonFeedItem:
    """Represents an item from a JSON Feed"""
    id: str
    title: Optional[str]
    content_html: Optional[str]
    content_text: Optional[str]
    url: Optional[str]
    external_url: Optional[str]
    summary: Optional[str]
    image: Optional[str]
    banner_image: Optional[str]
    date_published: Optional[datetime]
    date_modified: Optional[datetime]
    author: Optional[Dict[str, Any]]
    tags: List[str]
    attachments: List[Dict[str, Any]]
    
@dataclass
class JsonFeedInfo:
    """Represents JSON Feed metadata"""
    version: str
    title: str
    home_page_url: Optional[str]
    feed_url: Optional[str]
    description: Optional[str]
    user_comment: Optional[str]
    next_url: Optional[str]
    icon: Optional[str]
    favicon: Optional[str]
    author: Optional[Dict[str, Any]]
    language: Optional[str]
    expired: bool
    items: List[JsonFeedItem]

class JsonFeedService:
    """Service for handling JSON Feed parsing and discovery"""
    
    def __init__(self, db: Session):
        self.db = db
        self.session_timeout = aiohttp.ClientTimeout(total=30)
        
        # User agent for requests
        self.user_agent = 'RSS Intelligence JSON Feed Parser (+https://example.com/bot)'
        
        # JSON Feed MIME types
        self.json_feed_mime_types = [
            'application/feed+json',
            'application/json',
            'text/json'
        ]
    
    async def discover_json_feeds(self, url: str) -> List[str]:
        """
        Discover JSON feeds from a website URL
        
        Args:
            url: Website URL to check for JSON feeds
            
        Returns:
            List of discovered JSON feed URLs
        """
        discovered_feeds = []
        
        try:
            async with aiohttp.ClientSession(timeout=self.session_timeout) as session:
                async with session.get(
                    url,
                    headers={'User-Agent': self.user_agent}
                ) as response:
                    if response.status != 200:
                        return discovered_feeds
                    
                    content_type = response.headers.get('content-type', '').lower()
                    
                    # Check if this URL itself is a JSON feed
                    if any(mime in content_type for mime in self.json_feed_mime_types):
                        try:
                            feed_data = await response.json()
                            if self._is_valid_json_feed(feed_data):
                                discovered_feeds.append(url)
                                return discovered_feeds
                        except:
                            pass
                    
                    # Parse HTML to find JSON feed links
                    if 'text/html' in content_type:
                        html_content = await response.text()
                        feed_links = self._extract_json_feed_links(html_content, url)
                        discovered_feeds.extend(feed_links)
            
        except Exception as e:
            logger.warning(f"Failed to discover JSON feeds from {url}: {e}")
        
        return discovered_feeds
    
    async def parse_json_feed(self, feed_url: str) -> Optional[JsonFeedInfo]:
        """
        Parse a JSON Feed from URL
        
        Args:
            feed_url: URL of the JSON feed
            
        Returns:
            JsonFeedInfo object or None if parsing failed
        """
        try:
            async with aiohttp.ClientSession(timeout=self.session_timeout) as session:
                async with session.get(
                    feed_url,
                    headers={
                        'User-Agent': self.user_agent,
                        'Accept': 'application/feed+json, application/json, */*'
                    }
                ) as response:
                    if response.status != 200:
                        logger.warning(f"HTTP {response.status} when fetching {feed_url}")
                        return None
                    
                    try:
                        feed_data = await response.json()
                    except json.JSONDecodeError as e:
                        logger.error(f"Invalid JSON in feed {feed_url}: {e}")
                        return None
                    
                    return self._parse_feed_data(feed_data, feed_url)
                    
        except asyncio.TimeoutError:
            logger.warning(f"Timeout fetching JSON feed: {feed_url}")
            return None
        except Exception as e:
            logger.error(f"Error parsing JSON feed {feed_url}: {e}")
            return None
    
    def _is_valid_json_feed(self, data: Dict[str, Any]) -> bool:
        """Check if data represents a valid JSON Feed"""
        return (
            isinstance(data, dict) and
            'version' in data and
            data['version'].startswith('https://jsonfeed.org/version/') and
            'items' in data and
            isinstance(data['items'], list)
        )
    
    def _extract_json_feed_links(self, html_content: str, base_url: str) -> List[str]:
        """Extract JSON feed links from HTML content"""
        feed_links = []
        
        # Look for <link> tags with JSON feed references
        link_patterns = [
            r'<link[^>]+rel=["\']alternate["\'][^>]+type=["\']application/feed\+json["\'][^>]*href=["\']([^"\']+)["\']',
            r'<link[^>]+type=["\']application/feed\+json["\'][^>]+rel=["\']alternate["\'][^>]*href=["\']([^"\']+)["\']',
            r'<link[^>]+href=["\']([^"\']+)["\'][^>]+type=["\']application/feed\+json["\']',
            r'<link[^>]+type=["\']application/feed\+json["\'][^>]*href=["\']([^"\']+)["\']'
        ]
        
        for pattern in link_patterns:
            matches = re.findall(pattern, html_content, re.IGNORECASE)
            for match in matches:
                feed_url = urljoin(base_url, match)
                if feed_url not in feed_links:
                    feed_links.append(feed_url)
        
        # Look for common JSON feed paths
        base_domain = f"{urlparse(base_url).scheme}://{urlparse(base_url).netloc}"
        common_paths = [
            '/feed.json',
            '/feeds/all.json',
            '/index.json',
            '/api/feed.json',
            '/.well-known/feed.json'
        ]
        
        for path in common_paths:
            potential_feed = base_domain + path
            if potential_feed not in feed_links:
                feed_links.append(potential_feed)
        
        return feed_links
    
    def _parse_feed_data(self, data: Dict[str, Any], feed_url: str) -> Optional[JsonFeedInfo]:
        """Parse JSON feed data into JsonFeedInfo object"""
        try:
            if not self._is_valid_json_feed(data):
                logger.warning(f"Invalid JSON Feed format: {feed_url}")
                return None
            
            # Parse feed metadata
            feed_info = JsonFeedInfo(
                version=data.get('version', ''),
                title=data.get('title', ''),
                home_page_url=data.get('home_page_url'),
                feed_url=data.get('feed_url', feed_url),
                description=data.get('description'),
                user_comment=data.get('user_comment'),
                next_url=data.get('next_url'),
                icon=data.get('icon'),
                favicon=data.get('favicon'),
                author=data.get('author'),
                language=data.get('language'),
                expired=data.get('expired', False),
                items=[]
            )
            
            # Parse items
            for item_data in data.get('items', []):
                item = self._parse_feed_item(item_data)
                if item:
                    feed_info.items.append(item)
            
            return feed_info
            
        except Exception as e:
            logger.error(f"Error parsing feed data from {feed_url}: {e}")
            return None
    
    def _parse_feed_item(self, item_data: Dict[str, Any]) -> Optional[JsonFeedItem]:
        """Parse a single JSON feed item"""
        try:
            # Parse dates
            date_published = None
            if item_data.get('date_published'):
                try:
                    date_published = datetime.fromisoformat(item_data['date_published'].replace('Z', '+00:00'))
                except:
                    pass
            
            date_modified = None
            if item_data.get('date_modified'):
                try:
                    date_modified = datetime.fromisoformat(item_data['date_modified'].replace('Z', '+00:00'))
                except:
                    pass
            
            return JsonFeedItem(
                id=item_data.get('id', ''),
                title=item_data.get('title'),
                content_html=item_data.get('content_html'),
                content_text=item_data.get('content_text'),
                url=item_data.get('url'),
                external_url=item_data.get('external_url'),
                summary=item_data.get('summary'),
                image=item_data.get('image'),
                banner_image=item_data.get('banner_image'),
                date_published=date_published,
                date_modified=date_modified,
                author=item_data.get('author'),
                tags=item_data.get('tags', []),
                attachments=item_data.get('attachments', [])
            )
            
        except Exception as e:
            logger.warning(f"Error parsing JSON feed item: {e}")
            return None
    
    async def convert_to_articles(self, feed_info: JsonFeedInfo, source_name: str) -> List[Article]:
        """
        Convert JSON feed items to Article objects
        
        Args:
            feed_info: Parsed JSON feed information
            source_name: Name/identifier for this feed source
            
        Returns:
            List of Article objects
        """
        articles = []
        
        for item in feed_info.items:
            try:
                # Generate URL - prefer external_url, then url, then construct from id
                article_url = item.external_url or item.url
                if not article_url and item.id:
                    # If id looks like a URL, use it
                    if item.id.startswith(('http://', 'https://')):
                        article_url = item.id
                    elif feed_info.home_page_url:
                        # Construct URL from home page + id
                        article_url = urljoin(feed_info.home_page_url, item.id)
                
                if not article_url:
                    logger.warning(f"No URL found for item {item.id}")
                    continue
                
                # Use content_html if available, otherwise content_text
                content = item.content_html or item.content_text or ''
                
                # If no content in feed, try to extract from URL
                if not content and article_url:
                    try:
                        extracted = await extract_content(article_url)
                        if extracted and extracted.get('content'):
                            content = extracted['content']
                    except Exception as e:
                        logger.debug(f"Failed to extract content for {article_url}: {e}")
                
                # Generate content hash for deduplication
                content_for_hash = f"{item.title}{content}{article_url}"
                content_hash = hashlib.sha256(content_for_hash.encode()).hexdigest()
                
                # Create Article object
                article = Article(
                    title=item.title or 'Untitled',
                    url=article_url,
                    content=content,
                    source=source_name,
                    published_at=item.date_published or datetime.now(),
                    content_hash=content_hash,
                    image_url=item.image or item.banner_image,
                    summary=item.summary,
                    external_id=item.id
                )
                
                # Add author information if available
                if item.author:
                    article.author = item.author.get('name') or json.dumps(item.author)
                
                # Add tags as flags
                if item.tags:
                    article.flags = {'tags': item.tags}
                
                articles.append(article)
                
            except Exception as e:
                logger.warning(f"Error converting JSON feed item to article: {e}")
                continue
        
        return articles
    
    async def fetch_and_parse_feed(self, feed_url: str, source_name: str) -> List[Article]:
        """
        Fetch and parse a JSON feed, returning Article objects
        
        Args:
            feed_url: URL of the JSON feed
            source_name: Name for this feed source
            
        Returns:
            List of Article objects
        """
        try:
            # Parse the feed
            feed_info = await self.parse_json_feed(feed_url)
            if not feed_info:
                return []
            
            # Convert to articles
            articles = await self.convert_to_articles(feed_info, source_name)
            
            logger.info(f"Parsed {len(articles)} articles from JSON feed {feed_url}")
            return articles
            
        except Exception as e:
            logger.error(f"Error fetching and parsing JSON feed {feed_url}: {e}")
            return []
    
    def add_json_feed(self, feed_url: str, source_name: str, description: str = '') -> bool:
        """
        Add a JSON feed to the database
        
        Args:
            feed_url: URL of the JSON feed
            source_name: Name for this feed
            description: Optional description
            
        Returns:
            True if successfully added
        """
        try:
            # Check if feed already exists
            existing = self.db.query(Feed).filter(Feed.url == feed_url).first()
            if existing:
                logger.info(f"JSON feed already exists: {feed_url}")
                return False
            
            # Create new feed entry
            feed = Feed(
                url=feed_url,
                title=source_name,
                description=description,
                feed_type='json',  # Mark as JSON feed
                is_active=True
            )
            
            self.db.add(feed)
            self.db.commit()
            
            logger.info(f"Added JSON feed: {feed_url}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding JSON feed {feed_url}: {e}")
            self.db.rollback()
            return False
    
    async def test_json_feed(self, feed_url: str) -> Dict[str, Any]:
        """
        Test a JSON feed URL and return information about it
        
        Args:
            feed_url: URL to test
            
        Returns:
            Dictionary with test results
        """
        result = {
            'url': feed_url,
            'is_valid': False,
            'error': None,
            'feed_info': None,
            'item_count': 0,
            'sample_items': []
        }
        
        try:
            feed_info = await self.parse_json_feed(feed_url)
            
            if feed_info:
                result['is_valid'] = True
                result['feed_info'] = {
                    'title': feed_info.title,
                    'description': feed_info.description,
                    'version': feed_info.version,
                    'home_page_url': feed_info.home_page_url,
                    'language': feed_info.language,
                    'author': feed_info.author,
                    'expired': feed_info.expired
                }
                result['item_count'] = len(feed_info.items)
                
                # Include sample items (first 3)
                for item in feed_info.items[:3]:
                    sample_item = {
                        'id': item.id,
                        'title': item.title,
                        'url': item.url or item.external_url,
                        'date_published': item.date_published.isoformat() if item.date_published else None,
                        'has_content': bool(item.content_html or item.content_text),
                        'tags': item.tags
                    }
                    result['sample_items'].append(sample_item)
            else:
                result['error'] = 'Invalid or empty JSON feed'
                
        except Exception as e:
            result['error'] = str(e)
        
        return result

# Global instance
json_feed_service = None

def get_json_feed_service(db: Session) -> JsonFeedService:
    """Get or create JSON feed service"""
    return JsonFeedService(db)