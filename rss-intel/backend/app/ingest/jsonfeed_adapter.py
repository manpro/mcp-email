"""JSON Feed adapter"""
import aiohttp
import asyncio
from datetime import datetime, timezone
from typing import List, Dict, Any
import logging
from dateutil.parser import parse as parse_date

from .base import BaseAdapter, RawItem, AdapterFactory

logger = logging.getLogger(__name__)


class JsonFeedAdapter(BaseAdapter):
    """Adapter for JSON Feed format (https://jsonfeed.org/)"""
    
    async def fetch_new(self) -> List[RawItem]:
        """Fetch items from JSON Feed"""
        feed_url = self.config.get('url')
        if not feed_url:
            logger.error(f"No URL configured for JSON Feed source {self.source_name}")
            return []
        
        try:
            timeout = aiohttp.ClientTimeout(total=30, connect=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                headers = {
                    'User-Agent': 'RSSIntelBot/2.0 (RSS Intelligence Dashboard)',
                    'Accept': 'application/json, application/feed+json'
                }
                
                async with session.get(feed_url, headers=headers) as response:
                    if response.status != 200:
                        logger.warning(f"HTTP {response.status} for {feed_url}")
                        return []
                    
                    data = await response.json()
                    return self._parse_json_feed(data)
                    
        except Exception as e:
            logger.error(f"Error fetching JSON Feed {feed_url}: {e}")
            return []
    
    def _parse_json_feed(self, data: Dict[str, Any]) -> List[RawItem]:
        """Parse JSON Feed data into RawItems"""
        items = []
        
        feed_title = data.get('title', self.source_name)
        feed_home_page = data.get('home_page_url', '')
        
        for item_data in data.get('items', []):
            try:
                # Required fields
                item_id = item_data.get('id')
                if not item_id:
                    continue
                
                title = item_data.get('title', 'No Title')
                url = item_data.get('url') or item_data.get('external_url') or item_id
                
                # Content - prefer content_html, fallback to content_text
                content = ''
                if 'content_html' in item_data:
                    content = item_data['content_html']
                elif 'content_text' in item_data:
                    content = item_data['content_text']
                elif 'summary' in item_data:
                    content = item_data['summary']
                
                # Parse published date
                published_at = None
                if 'date_published' in item_data:
                    try:
                        published_at = parse_date(item_data['date_published'])
                        if published_at.tzinfo is None:
                            published_at = published_at.replace(tzinfo=timezone.utc)
                    except Exception as e:
                        logger.warning(f"Could not parse date {item_data['date_published']}: {e}")
                
                # Author info
                author = None
                if 'author' in item_data:
                    author_data = item_data['author']
                    if isinstance(author_data, dict):
                        author = author_data.get('name')
                    else:
                        author = str(author_data)
                elif 'authors' in item_data and item_data['authors']:
                    first_author = item_data['authors'][0]
                    if isinstance(first_author, dict):
                        author = first_author.get('name')
                    else:
                        author = str(first_author)
                
                # Image
                image_url = item_data.get('image')
                if not image_url and 'attachments' in item_data:
                    # Look for image attachments
                    for attachment in item_data['attachments']:
                        if attachment.get('mime_type', '').startswith('image/'):
                            image_url = attachment.get('url')
                            break
                
                # Language
                lang = item_data.get('language') or data.get('language')
                
                # Metadata
                metadata = {
                    'feed_title': feed_title,
                    'feed_home_page': feed_home_page,
                    'item_id': item_id,
                    'tags': item_data.get('tags', [])
                }
                
                items.append(RawItem(
                    title=title,
                    url=url,
                    content=content,
                    published_at=published_at,
                    source=feed_title,
                    image_url=image_url,
                    author=author,
                    lang=lang,
                    metadata=metadata
                ))
                
            except Exception as e:
                logger.error(f"Error parsing JSON Feed item: {e}")
                continue
        
        logger.info(f"Parsed {len(items)} items from JSON Feed {self.source_name}")
        return items


# Register the adapter
AdapterFactory.register('json', JsonFeedAdapter)