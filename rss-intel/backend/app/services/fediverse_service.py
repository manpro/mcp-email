"""
Fediverse/Mastodon Integration Service

Support for following Mastodon accounts, monitoring hashtags, and fetching posts
from across the Fediverse using ActivityPub protocol and Mastodon API.
"""

import logging
import aiohttp
import asyncio
from typing import Dict, List, Optional, Any, Set
from datetime import datetime, timedelta
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse
import json
import re
import hashlib
from sqlalchemy.orm import Session
from bs4 import BeautifulSoup

from ..store import Article
from ..intelligence.content_extractor import extract_content

logger = logging.getLogger(__name__)

@dataclass
class MastodonInstance:
    """Mastodon instance information"""
    domain: str
    name: str
    description: str
    version: str
    user_count: int
    status_count: int
    is_alive: bool
    api_base_url: str

@dataclass
class FediversePost:
    """Represents a post from the Fediverse"""
    id: str
    url: str
    content: str
    content_text: str
    author_username: str
    author_display_name: str
    author_avatar: Optional[str]
    published_at: datetime
    replies_count: int
    reblogs_count: int
    favourites_count: int
    tags: List[str]
    mentions: List[str]
    media_attachments: List[Dict[str, Any]]
    instance_domain: str
    language: Optional[str]
    sensitive: bool
    visibility: str
    in_reply_to: Optional[str]

@dataclass
class FediverseAccount:
    """Mastodon/Fediverse account to follow"""
    username: str
    domain: str
    display_name: str
    note: str
    avatar: Optional[str]
    followers_count: int
    following_count: int
    statuses_count: int
    last_status_at: Optional[datetime]
    bot: bool
    locked: bool

class FediverseService:
    """Service for Fediverse/Mastodon integration"""
    
    def __init__(self, db: Session):
        self.db = db
        self.session_timeout = aiohttp.ClientTimeout(total=30)
        
        # User agent for requests
        self.user_agent = 'RSS Intelligence Fediverse Bot (+https://example.com/bot)'
        
        # Known Mastodon instances
        self.known_instances = [
            'mastodon.social',
            'mastodon.online', 
            'mstdn.social',
            'fosstodon.org',
            'mas.to',
            'hachyderm.io',
            'techhub.social',
            'journa.host',
            'fediscience.org'
        ]
        
        # Hashtags to monitor
        self.monitored_hashtags = [
            'technology', 'ai', 'programming', 'opensource', 'security',
            'privacy', 'science', 'climate', 'news', 'breaking'
        ]
        
        # Content filtering patterns
        self.spam_patterns = [
            r'follow me for', r'check out my', r'buy now', r'limited time',
            r'crypto', r'nft', r'investment opportunity'
        ]
    
    async def discover_mastodon_instances(self) -> List[MastodonInstance]:
        """
        Discover and validate Mastodon instances
        
        Returns:
            List of active Mastodon instances
        """
        instances = []
        
        # Check known instances
        async with aiohttp.ClientSession(timeout=self.session_timeout) as session:
            for domain in self.known_instances:
                try:
                    instance = await self._check_mastodon_instance(session, domain)
                    if instance:
                        instances.append(instance)
                        logger.info(f"Discovered Mastodon instance: {domain}")
                except Exception as e:
                    logger.warning(f"Failed to check instance {domain}: {e}")
                    
                # Rate limiting
                await asyncio.sleep(0.5)
        
        return instances
    
    async def _check_mastodon_instance(self, session: aiohttp.ClientSession, domain: str) -> Optional[MastodonInstance]:
        """Check if domain is a valid Mastodon instance"""
        try:
            # Check instance API endpoint
            api_url = f"https://{domain}/api/v1/instance"
            
            async with session.get(
                api_url,
                headers={'User-Agent': self.user_agent}
            ) as response:
                if response.status != 200:
                    return None
                
                data = await response.json()
                
                # Validate it's actually Mastodon
                if 'version' not in data or 'stats' not in data:
                    return None
                
                return MastodonInstance(
                    domain=domain,
                    name=data.get('title', domain),
                    description=data.get('description', ''),
                    version=data.get('version', ''),
                    user_count=data.get('stats', {}).get('user_count', 0),
                    status_count=data.get('stats', {}).get('status_count', 0),
                    is_alive=True,
                    api_base_url=f"https://{domain}/api/v1"
                )
                
        except Exception as e:
            logger.debug(f"Instance check failed for {domain}: {e}")
            return None
    
    async def fetch_account_posts(self, username: str, domain: str, limit: int = 20) -> List[FediversePost]:
        """
        Fetch posts from a specific Mastodon account
        
        Args:
            username: Account username (without @)
            domain: Instance domain
            limit: Number of posts to fetch
            
        Returns:
            List of posts from the account
        """
        posts = []
        
        try:
            async with aiohttp.ClientSession(timeout=self.session_timeout) as session:
                # First, resolve the account ID
                account = await self._resolve_account(session, username, domain)
                if not account:
                    logger.warning(f"Could not resolve account @{username}@{domain}")
                    return posts
                
                # Fetch account statuses
                statuses_url = f"https://{domain}/api/v1/accounts/{account['id']}/statuses"
                
                async with session.get(
                    statuses_url,
                    headers={'User-Agent': self.user_agent},
                    params={'limit': limit, 'exclude_replies': True}
                ) as response:
                    if response.status != 200:
                        logger.warning(f"HTTP {response.status} fetching posts from @{username}@{domain}")
                        return posts
                    
                    statuses_data = await response.json()
                    
                    for status in statuses_data:
                        post = await self._parse_mastodon_status(status, domain)
                        if post and not self._is_spam_post(post):
                            posts.append(post)
                
                logger.info(f"Fetched {len(posts)} posts from @{username}@{domain}")
                
        except Exception as e:
            logger.error(f"Error fetching posts from @{username}@{domain}: {e}")
        
        return posts
    
    async def fetch_hashtag_posts(self, hashtag: str, instance_domain: str, limit: int = 30) -> List[FediversePost]:
        """
        Fetch posts for a specific hashtag from an instance
        
        Args:
            hashtag: Hashtag to search (without #)
            instance_domain: Mastodon instance to search
            limit: Number of posts to fetch
            
        Returns:
            List of posts with the hashtag
        """
        posts = []
        
        try:
            async with aiohttp.ClientSession(timeout=self.session_timeout) as session:
                # Hashtag timeline endpoint
                hashtag_url = f"https://{instance_domain}/api/v1/timelines/tag/{hashtag}"
                
                async with session.get(
                    hashtag_url,
                    headers={'User-Agent': self.user_agent},
                    params={'limit': limit}
                ) as response:
                    if response.status != 200:
                        logger.warning(f"HTTP {response.status} fetching #{hashtag} from {instance_domain}")
                        return posts
                    
                    statuses_data = await response.json()
                    
                    for status in statuses_data:
                        post = await self._parse_mastodon_status(status, instance_domain)
                        if post and not self._is_spam_post(post):
                            posts.append(post)
                
                logger.info(f"Fetched {len(posts)} posts for #{hashtag} from {instance_domain}")
                
        except Exception as e:
            logger.error(f"Error fetching #{hashtag} from {instance_domain}: {e}")
        
        return posts
    
    async def fetch_public_timeline(self, instance_domain: str, limit: int = 20) -> List[FediversePost]:
        """
        Fetch posts from public timeline of an instance
        
        Args:
            instance_domain: Mastodon instance domain
            limit: Number of posts to fetch
            
        Returns:
            List of public posts
        """
        posts = []
        
        try:
            async with aiohttp.ClientSession(timeout=self.session_timeout) as session:
                # Public timeline endpoint
                timeline_url = f"https://{instance_domain}/api/v1/timelines/public"
                
                async with session.get(
                    timeline_url,
                    headers={'User-Agent': self.user_agent},
                    params={'limit': limit, 'local': False}
                ) as response:
                    if response.status != 200:
                        logger.warning(f"HTTP {response.status} fetching public timeline from {instance_domain}")
                        return posts
                    
                    statuses_data = await response.json()
                    
                    for status in statuses_data:
                        post = await self._parse_mastodon_status(status, instance_domain)
                        if post and not self._is_spam_post(post):
                            posts.append(post)
                
                logger.info(f"Fetched {len(posts)} posts from {instance_domain} public timeline")
                
        except Exception as e:
            logger.error(f"Error fetching public timeline from {instance_domain}: {e}")
        
        return posts
    
    async def _resolve_account(self, session: aiohttp.ClientSession, username: str, domain: str) -> Optional[Dict[str, Any]]:
        """Resolve account information by username"""
        try:
            # Account lookup endpoint
            lookup_url = f"https://{domain}/api/v1/accounts/lookup"
            
            async with session.get(
                lookup_url,
                headers={'User-Agent': self.user_agent},
                params={'acct': f"{username}@{domain}"}
            ) as response:
                if response.status == 200:
                    return await response.json()
                
                # Try alternative format
                async with session.get(
                    lookup_url,
                    headers={'User-Agent': self.user_agent},
                    params={'acct': username}
                ) as alt_response:
                    if alt_response.status == 200:
                        return await alt_response.json()
                        
        except Exception as e:
            logger.debug(f"Account resolution failed for @{username}@{domain}: {e}")
            
        return None
    
    async def _parse_mastodon_status(self, status: Dict[str, Any], instance_domain: str) -> Optional[FediversePost]:
        """Parse a Mastodon status into FediversePost"""
        try:
            # Skip if reblog - process original instead
            if status.get('reblog'):
                status = status['reblog']
            
            # Parse timestamps
            published_at = datetime.fromisoformat(status['created_at'].replace('Z', '+00:00'))
            
            # Extract content
            content_html = status.get('content', '')
            content_text = self._html_to_text(content_html)
            
            # Extract hashtags
            tags = [tag['name'] for tag in status.get('tags', [])]
            
            # Extract mentions
            mentions = [mention['username'] for mention in status.get('mentions', [])]
            
            # Account info
            account = status['account']
            
            return FediversePost(
                id=status['id'],
                url=status['url'] or status['uri'],
                content=content_html,
                content_text=content_text,
                author_username=account['username'],
                author_display_name=account['display_name'] or account['username'],
                author_avatar=account.get('avatar'),
                published_at=published_at,
                replies_count=status.get('replies_count', 0),
                reblogs_count=status.get('reblogs_count', 0),
                favourites_count=status.get('favourites_count', 0),
                tags=tags,
                mentions=mentions,
                media_attachments=status.get('media_attachments', []),
                instance_domain=instance_domain,
                language=status.get('language'),
                sensitive=status.get('sensitive', False),
                visibility=status.get('visibility', 'public'),
                in_reply_to=status.get('in_reply_to_id')
            )
            
        except Exception as e:
            logger.warning(f"Error parsing Mastodon status: {e}")
            return None
    
    def _html_to_text(self, html_content: str) -> str:
        """Convert HTML content to plain text"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Convert <br> to newlines
            for br in soup.find_all("br"):
                br.replace_with("\n")
            
            # Convert <p> tags to paragraphs
            for p in soup.find_all("p"):
                p.insert_before("\n")
                p.insert_after("\n")
            
            return soup.get_text().strip()
            
        except Exception:
            # Fallback: remove HTML tags with regex
            return re.sub(r'<[^>]+>', '', html_content).strip()
    
    def _is_spam_post(self, post: FediversePost) -> bool:
        """Check if post appears to be spam"""
        content_lower = post.content_text.lower()
        
        for pattern in self.spam_patterns:
            if re.search(pattern, content_lower):
                return True
        
        # Check for excessive hashtags (possible spam)
        if len(post.tags) > 10:
            return True
        
        # Check for very short content with links (possible spam)
        if len(post.content_text) < 50 and ('http' in content_lower):
            return True
        
        return False
    
    async def convert_posts_to_articles(self, posts: List[FediversePost], source_name: str) -> List[Article]:
        """
        Convert Fediverse posts to Article objects
        
        Args:
            posts: List of Fediverse posts
            source_name: Source identifier for these posts
            
        Returns:
            List of Article objects
        """
        articles = []
        
        for post in posts:
            try:
                # Skip very short posts or replies
                if len(post.content_text) < 100 or post.in_reply_to:
                    continue
                
                # Generate title from content
                title = self._generate_title_from_content(post.content_text, post.author_display_name)
                
                # Create content with author attribution
                full_content = f"{post.content_text}\n\n---\nBy {post.author_display_name} (@{post.author_username}@{post.instance_domain})"
                
                # Add media if present
                if post.media_attachments:
                    media_urls = [media.get('url', '') for media in post.media_attachments if media.get('url')]
                    if media_urls:
                        full_content += f"\n\nMedia: {', '.join(media_urls)}"
                
                # Generate content hash for deduplication
                content_for_hash = f"{title}{full_content}{post.url}"
                content_hash = hashlib.sha256(content_for_hash.encode()).hexdigest()
                
                # Create Article object
                article = Article(
                    title=title,
                    url=post.url,
                    content=full_content,
                    source=source_name,
                    published_at=post.published_at,
                    content_hash=content_hash,
                    author=f"{post.author_display_name} (@{post.author_username})",
                    external_id=post.id
                )
                
                # Add Fediverse-specific flags
                article.flags = {
                    'fediverse': True,
                    'instance': post.instance_domain,
                    'tags': post.tags,
                    'replies_count': post.replies_count,
                    'reblogs_count': post.reblogs_count,
                    'favourites_count': post.favourites_count,
                    'language': post.language,
                    'sensitive': post.sensitive
                }
                
                articles.append(article)
                
            except Exception as e:
                logger.warning(f"Error converting Fediverse post to article: {e}")
                continue
        
        return articles
    
    def _generate_title_from_content(self, content: str, author: str) -> str:
        """Generate article title from post content"""
        # Clean content
        content = re.sub(r'https?://\S+', '', content)  # Remove URLs
        content = re.sub(r'#\w+', '', content)  # Remove hashtags
        content = content.strip()
        
        # Get first sentence or first 60 characters
        sentences = re.split(r'[.!?]+', content)
        if sentences and len(sentences[0].strip()) > 10:
            title = sentences[0].strip()[:100]
        else:
            title = content[:100]
        
        # Add ellipsis if truncated
        if len(title) == 100:
            title += "..."
        
        # Fallback title
        if len(title) < 10:
            title = f"Post by {author}"
        
        return title
    
    async def monitor_hashtags_across_instances(self, hashtags: List[str], instances: List[str]) -> List[Article]:
        """
        Monitor multiple hashtags across multiple instances
        
        Args:
            hashtags: List of hashtags to monitor
            instances: List of instance domains
            
        Returns:
            List of articles from all hashtags and instances
        """
        all_articles = []
        
        # Create tasks for concurrent processing
        tasks = []
        for hashtag in hashtags:
            for instance in instances:
                task = self.fetch_hashtag_posts(hashtag, instance, limit=10)
                tasks.append(task)
        
        # Execute concurrently with limit
        semaphore = asyncio.Semaphore(5)  # Max 5 concurrent requests
        
        async def limited_fetch(task):
            async with semaphore:
                return await task
        
        results = await asyncio.gather(
            *[limited_fetch(task) for task in tasks],
            return_exceptions=True
        )
        
        # Process results
        all_posts = []
        for result in results:
            if isinstance(result, list):
                all_posts.extend(result)
            elif isinstance(result, Exception):
                logger.warning(f"Task failed: {result}")
        
        # Convert to articles
        if all_posts:
            articles = await self.convert_posts_to_articles(all_posts, "fediverse_hashtags")
            all_articles.extend(articles)
        
        logger.info(f"Collected {len(all_articles)} articles from {len(hashtags)} hashtags across {len(instances)} instances")
        return all_articles
    
    def add_fediverse_source(self, source_type: str, identifier: str, instance_domain: str, 
                            description: str = '') -> bool:
        """
        Add a Fediverse source to the database
        
        Args:
            source_type: 'account', 'hashtag', or 'instance'
            identifier: Account name, hashtag, or instance domain
            instance_domain: Mastodon instance domain
            description: Optional description
            
        Returns:
            True if successfully added
        """
        try:
            # Construct feed URL based on type
            if source_type == 'account':
                feed_url = f"fediverse://account/{identifier}@{instance_domain}"
                title = f"@{identifier}@{instance_domain}"
            elif source_type == 'hashtag':
                feed_url = f"fediverse://hashtag/{identifier}@{instance_domain}"
                title = f"#{identifier} on {instance_domain}"
            elif source_type == 'instance':
                feed_url = f"fediverse://instance/{instance_domain}/public"
                title = f"{instance_domain} public timeline"
            else:
                raise ValueError(f"Invalid source type: {source_type}")
            
            # Check if already exists
            existing = self.db.query(Feed).filter(Feed.url == feed_url).first()
            if existing:
                logger.info(f"Fediverse source already exists: {feed_url}")
                return False
            
            # Create new feed entry
            feed = Feed(
                url=feed_url,
                title=title,
                description=description,
                feed_type='fediverse',
                is_active=True
            )
            
            self.db.add(feed)
            self.db.commit()
            
            logger.info(f"Added Fediverse source: {feed_url}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding Fediverse source {source_type}:{identifier}: {e}")
            self.db.rollback()
            return False

# Global instance
fediverse_service = None

def get_fediverse_service(db: Session) -> FediverseService:
    """Get or create Fediverse service"""
    return FediverseService(db)