"""ActivityPub adapter for Mastodon and other fediverse platforms"""
import aiohttp
import asyncio
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional, Set
import logging
from dateutil.parser import parse as parse_date
from urllib.parse import urljoin, urlparse
import json

from .base import BaseAdapter, RawItem, AdapterFactory

logger = logging.getLogger(__name__)


class ActivityPubAdapter(BaseAdapter):
    """Adapter for ActivityPub/Mastodon instances"""
    
    def __init__(self, source_config: Dict[str, Any]):
        super().__init__(source_config)
        self.processed_ids: Set[str] = set()
    
    async def fetch_new(self) -> List[RawItem]:
        """Fetch new posts from ActivityPub instances"""
        instance_url = self.config.get('instance_url')
        if not instance_url:
            logger.error(f"No instance URL configured for {self.source_name}")
            return []
        
        items = []
        
        try:
            timeout = aiohttp.ClientTimeout(total=30, connect=10)
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                # Fetch from different sources based on configuration
                if 'accounts' in self.config:
                    for account in self.config['accounts']:
                        account_items = await self._fetch_account_posts(session, instance_url, account)
                        items.extend(account_items)
                
                if 'hashtags' in self.config:
                    for hashtag in self.config['hashtags']:
                        hashtag_items = await self._fetch_hashtag_posts(session, instance_url, hashtag)
                        items.extend(hashtag_items)
                
                if 'local_timeline' in self.config and self.config['local_timeline']:
                    timeline_items = await self._fetch_local_timeline(session, instance_url)
                    items.extend(timeline_items)
                
                if 'federated_timeline' in self.config and self.config['federated_timeline']:
                    federated_items = await self._fetch_federated_timeline(session, instance_url)
                    items.extend(federated_items)
        
        except Exception as e:
            logger.error(f"Error fetching from ActivityPub instance {instance_url}: {e}")
            return []
        
        logger.info(f"Fetched {len(items)} items from ActivityPub {self.source_name}")
        return items
    
    async def _fetch_account_posts(self, session: aiohttp.ClientSession, instance_url: str, account: str) -> List[RawItem]:
        """Fetch posts from a specific account"""
        items = []
        
        try:
            # Resolve account ID if needed
            account_id = await self._resolve_account_id(session, instance_url, account)
            if not account_id:
                logger.warning(f"Could not resolve account {account}")
                return []
            
            # Fetch account statuses
            url = f"{instance_url}/api/v1/accounts/{account_id}/statuses"
            params = {
                'limit': 40,
                'exclude_replies': self.config.get('exclude_replies', True),
                'exclude_reblogs': self.config.get('exclude_reblogs', True)
            }
            
            headers = self._get_headers()
            
            async with session.get(url, params=params, headers=headers) as response:
                if response.status != 200:
                    logger.warning(f"HTTP {response.status} for account {account}")
                    return []
                
                posts = await response.json()
                
                for post in posts:
                    item = self._parse_mastodon_post(post, f"@{account}")
                    if item and item.metadata['post_id'] not in self.processed_ids:
                        items.append(item)
                        self.processed_ids.add(item.metadata['post_id'])
            
            await asyncio.sleep(0.5)  # Rate limiting
            
        except Exception as e:
            logger.error(f"Error fetching posts from account {account}: {e}")
        
        return items
    
    async def _fetch_hashtag_posts(self, session: aiohttp.ClientSession, instance_url: str, hashtag: str) -> List[RawItem]:
        """Fetch posts for a hashtag"""
        items = []
        
        try:
            url = f"{instance_url}/api/v1/timelines/tag/{hashtag.lstrip('#')}"
            params = {
                'limit': 40,
                'local': self.config.get('local_only', False)
            }
            
            headers = self._get_headers()
            
            async with session.get(url, params=params, headers=headers) as response:
                if response.status != 200:
                    logger.warning(f"HTTP {response.status} for hashtag {hashtag}")
                    return []
                
                posts = await response.json()
                
                for post in posts:
                    item = self._parse_mastodon_post(post, f"#{hashtag}")
                    if item and item.metadata['post_id'] not in self.processed_ids:
                        # Filter by age
                        max_age_hours = self.config.get('max_age_hours', 24)
                        if (datetime.now(timezone.utc) - item.published_at).total_seconds() > max_age_hours * 3600:
                            continue
                            
                        items.append(item)
                        self.processed_ids.add(item.metadata['post_id'])
            
            await asyncio.sleep(0.5)  # Rate limiting
            
        except Exception as e:
            logger.error(f"Error fetching hashtag {hashtag}: {e}")
        
        return items
    
    async def _fetch_local_timeline(self, session: aiohttp.ClientSession, instance_url: str) -> List[RawItem]:
        """Fetch from local timeline"""
        return await self._fetch_timeline(session, instance_url, 'public', local=True, source_name="Local Timeline")
    
    async def _fetch_federated_timeline(self, session: aiohttp.ClientSession, instance_url: str) -> List[RawItem]:
        """Fetch from federated timeline"""
        return await self._fetch_timeline(session, instance_url, 'public', local=False, source_name="Federated Timeline")
    
    async def _fetch_timeline(self, session: aiohttp.ClientSession, instance_url: str, 
                             timeline: str, local: bool, source_name: str) -> List[RawItem]:
        """Generic timeline fetching"""
        items = []
        
        try:
            url = f"{instance_url}/api/v1/timelines/{timeline}"
            params = {
                'limit': 20,  # Smaller limit for timelines
                'local': local
            }
            
            headers = self._get_headers()
            
            async with session.get(url, params=params, headers=headers) as response:
                if response.status != 200:
                    logger.warning(f"HTTP {response.status} for {timeline} timeline")
                    return []
                
                posts = await response.json()
                
                for post in posts:
                    item = self._parse_mastodon_post(post, source_name)
                    if item and item.metadata['post_id'] not in self.processed_ids:
                        # More restrictive age filter for timelines
                        max_age_hours = self.config.get('timeline_max_age_hours', 6)
                        if (datetime.now(timezone.utc) - item.published_at).total_seconds() > max_age_hours * 3600:
                            continue
                        
                        # Apply minimum engagement filter for timelines
                        min_boosts = self.config.get('min_boosts', 0)
                        min_favourites = self.config.get('min_favourites', 0)
                        
                        if (post.get('reblogs_count', 0) >= min_boosts and 
                            post.get('favourites_count', 0) >= min_favourites):
                            items.append(item)
                            self.processed_ids.add(item.metadata['post_id'])
            
            await asyncio.sleep(1)  # More conservative rate limiting for timelines
            
        except Exception as e:
            logger.error(f"Error fetching {timeline} timeline: {e}")
        
        return items
    
    async def _resolve_account_id(self, session: aiohttp.ClientSession, instance_url: str, account: str) -> Optional[str]:
        """Resolve account username to ID"""
        try:
            # If account is already an ID, return it
            if account.isdigit():
                return account
            
            # Clean account name
            clean_account = account.lstrip('@')
            
            # Search for account
            url = f"{instance_url}/api/v1/accounts/search"
            params = {'q': clean_account, 'limit': 1}
            headers = self._get_headers()
            
            async with session.get(url, params=params, headers=headers) as response:
                if response.status == 200:
                    results = await response.json()
                    if results:
                        return str(results[0]['id'])
            
            return None
            
        except Exception as e:
            logger.error(f"Error resolving account {account}: {e}")
            return None
    
    def _parse_mastodon_post(self, post: Dict[str, Any], source_suffix: str) -> Optional[RawItem]:
        """Parse a Mastodon post into RawItem"""
        try:
            # Skip reblogs unless explicitly configured
            if post.get('reblog') and not self.config.get('include_reblogs', False):
                return None
            
            post_id = post['id']
            content = post.get('content', '')
            
            # Clean HTML content
            import re
            clean_content = re.sub(r'<[^>]+>', '', content)
            clean_content = re.sub(r'&[^;]+;', ' ', clean_content)  # Basic HTML entity removal
            clean_content = re.sub(r'\s+', ' ', clean_content).strip()
            
            # Skip if content too short
            if len(clean_content) < self.config.get('min_content_length', 20):
                return None
            
            # Parse date
            created_at = parse_date(post['created_at'])
            
            # Account info
            account = post.get('account', {})
            author = account.get('display_name') or account.get('username', 'Unknown')
            
            # Media attachments
            media_attachments = post.get('media_attachments', [])
            image_url = None
            if media_attachments:
                for attachment in media_attachments:
                    if attachment.get('type') == 'image':
                        image_url = attachment.get('preview_url') or attachment.get('url')
                        break
            
            # Language
            lang = post.get('language')
            
            # Build title from content preview
            title = clean_content[:100] + '...' if len(clean_content) > 100 else clean_content
            if not title:
                title = f"Post by {author}"
            
            return RawItem(
                title=title,
                url=post['url'] or post.get('uri', ''),
                content=clean_content,
                published_at=created_at,
                source=f"{self.source_name} {source_suffix}",
                author=author,
                lang=lang,
                image_url=image_url,
                metadata={
                    'type': 'activitypub',
                    'post_id': post_id,
                    'account_username': account.get('username'),
                    'account_display_name': account.get('display_name'),
                    'reblogs_count': post.get('reblogs_count', 0),
                    'favourites_count': post.get('favourites_count', 0),
                    'replies_count': post.get('replies_count', 0),
                    'hashtags': [tag['name'] for tag in post.get('tags', [])],
                    'mentions': [mention['username'] for mention in post.get('mentions', [])],
                    'is_reblog': bool(post.get('reblog'))
                }
            )
            
        except Exception as e:
            logger.error(f"Error parsing Mastodon post: {e}")
            return None
    
    def _get_headers(self) -> Dict[str, str]:
        """Get headers for API requests"""
        headers = {
            'User-Agent': 'RSSIntelBot/2.0 (RSS Intelligence Dashboard)',
            'Accept': 'application/json'
        }
        
        # Add authorization if access token provided
        access_token = self.config.get('access_token')
        if access_token:
            headers['Authorization'] = f'Bearer {access_token}'
        
        return headers


# Register the adapter
AdapterFactory.register('activitypub', ActivityPubAdapter)