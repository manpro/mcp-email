"""Sitemap adapter for fetching articles from XML sitemaps"""
import aiohttp
import asyncio
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Set
import xml.etree.ElementTree as ET
from urllib.parse import urljoin, urlparse
import logging
from dateutil.parser import parse as parse_date
from readability import Document
from bs4 import BeautifulSoup

from .base import BaseAdapter, RawItem, AdapterFactory

logger = logging.getLogger(__name__)


class SitemapAdapter(BaseAdapter):
    """Adapter for XML sitemaps - fetches new URLs and extracts content"""
    
    def __init__(self, source_config: Dict[str, Any]):
        super().__init__(source_config)
        self.processed_urls: Set[str] = set()
        self.max_age_days = source_config.get('max_age_days', 7)
        self.max_urls = source_config.get('max_urls', 100)
        self.url_patterns = source_config.get('url_patterns', [])
        self.exclude_patterns = source_config.get('exclude_patterns', [])
    
    async def fetch_new(self) -> List[RawItem]:
        """Fetch new URLs from sitemap and extract content"""
        sitemap_url = self.config.get('url')
        if not sitemap_url:
            logger.error(f"No sitemap URL configured for {self.source_name}")
            return []
        
        try:
            # Parse sitemap
            urls = await self._parse_sitemap(sitemap_url)
            
            # Filter URLs
            filtered_urls = self._filter_urls(urls)
            
            # Extract content from URLs
            items = await self._extract_content_from_urls(filtered_urls)
            
            return items
            
        except Exception as e:
            logger.error(f"Error processing sitemap {sitemap_url}: {e}")
            return []
    
    async def _parse_sitemap(self, sitemap_url: str) -> List[Dict[str, Any]]:
        """Parse XML sitemap and return list of URLs with metadata"""
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        
        async with aiohttp.ClientSession(timeout=timeout) as session:
            headers = {
                'User-Agent': 'RSSIntelBot/2.0 (RSS Intelligence Dashboard)'
            }
            
            async with session.get(sitemap_url, headers=headers) as response:
                if response.status != 200:
                    logger.warning(f"HTTP {response.status} for sitemap {sitemap_url}")
                    return []
                
                xml_content = await response.text()
                
        # Parse XML
        try:
            root = ET.fromstring(xml_content)
            urls = []
            
            # Handle both sitemap index and urlset
            if root.tag.endswith('sitemapindex'):
                # This is a sitemap index, fetch individual sitemaps
                for sitemap in root:
                    loc_elem = sitemap.find('.//{http://www.sitemaps.org/schemas/sitemap/0.9}loc')
                    if loc_elem is not None:
                        sub_urls = await self._parse_sitemap(loc_elem.text)
                        urls.extend(sub_urls)
            else:
                # This is a URL set
                for url_elem in root:
                    loc_elem = url_elem.find('.//{http://www.sitemaps.org/schemas/sitemap/0.9}loc')
                    lastmod_elem = url_elem.find('.//{http://www.sitemaps.org/schemas/sitemap/0.9}lastmod')
                    
                    if loc_elem is not None:
                        url_data = {'loc': loc_elem.text}
                        
                        if lastmod_elem is not None:
                            try:
                                url_data['lastmod'] = parse_date(lastmod_elem.text)
                            except Exception as e:
                                logger.debug(f"Could not parse lastmod {lastmod_elem.text}: {e}")
                        
                        urls.append(url_data)
            
            logger.info(f"Found {len(urls)} URLs in sitemap {sitemap_url}")
            return urls
            
        except ET.ParseError as e:
            logger.error(f"XML parse error for sitemap {sitemap_url}: {e}")
            return []
    
    def _filter_urls(self, urls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter URLs based on patterns and age"""
        filtered = []
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=self.max_age_days)
        
        for url_data in urls:
            url = url_data['loc']
            lastmod = url_data.get('lastmod')
            
            # Skip if already processed
            if url in self.processed_urls:
                continue
            
            # Check age if lastmod available
            if lastmod and lastmod < cutoff_date:
                continue
            
            # Check URL patterns (include)
            if self.url_patterns:
                if not any(pattern in url for pattern in self.url_patterns):
                    continue
            
            # Check exclude patterns
            if self.exclude_patterns:
                if any(pattern in url for pattern in self.exclude_patterns):
                    continue
            
            filtered.append(url_data)
        
        # Limit number of URLs
        if len(filtered) > self.max_urls:
            # Sort by lastmod if available, otherwise keep original order
            filtered.sort(key=lambda x: x.get('lastmod', datetime.min.replace(tzinfo=timezone.utc)), reverse=True)
            filtered = filtered[:self.max_urls]
        
        logger.info(f"Filtered to {len(filtered)} URLs for processing")
        return filtered
    
    async def _extract_content_from_urls(self, urls: List[Dict[str, Any]]) -> List[RawItem]:
        """Extract content from list of URLs using readability"""
        items = []
        
        # Process URLs in batches to avoid overwhelming the server
        batch_size = 5
        for i in range(0, len(urls), batch_size):
            batch = urls[i:i + batch_size]
            batch_tasks = [self._extract_single_url(url_data) for url_data in batch]
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            for result in batch_results:
                if isinstance(result, Exception):
                    logger.error(f"Batch extraction error: {result}")
                elif result is not None:
                    items.append(result)
            
            # Small delay between batches
            if i + batch_size < len(urls):
                await asyncio.sleep(1)
        
        logger.info(f"Extracted content from {len(items)} URLs")
        return items
    
    async def _extract_single_url(self, url_data: Dict[str, Any]) -> RawItem:
        """Extract content from a single URL"""
        url = url_data['loc']
        lastmod = url_data.get('lastmod')
        
        try:
            timeout = aiohttp.ClientTimeout(total=20, connect=10)
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                headers = {
                    'User-Agent': 'RSSIntelBot/2.0 (RSS Intelligence Dashboard)',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
                }
                
                async with session.get(url, headers=headers) as response:
                    if response.status != 200:
                        logger.warning(f"HTTP {response.status} for {url}")
                        return None
                    
                    html_content = await response.text()
            
            # Use readability to extract main content
            doc = Document(html_content)
            title = doc.title() or "No Title"
            content = doc.summary()
            
            # Extract additional metadata with BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Try to find published date in meta tags
            published_at = lastmod
            if not published_at:
                published_at = self._extract_published_date(soup)
            
            # Extract author
            author = self._extract_author(soup)
            
            # Extract image
            image_url = self._extract_image(soup, url)
            
            # Extract language
            lang = soup.get('lang') or self._detect_language(title, content)
            
            # Mark as processed
            self.processed_urls.add(url)
            
            return RawItem(
                title=title.strip(),
                url=url,
                content=content,
                published_at=published_at,
                source=self.source_name,
                image_url=image_url,
                author=author,
                lang=lang,
                metadata={
                    'extraction_method': 'readability',
                    'sitemap_lastmod': lastmod.isoformat() if lastmod else None
                }
            )
            
        except Exception as e:
            logger.error(f"Error extracting content from {url}: {e}")
            return None
    
    def _extract_published_date(self, soup: BeautifulSoup) -> datetime:
        """Try to extract published date from HTML meta tags"""
        # Common meta tag patterns for published date
        selectors = [
            'meta[property="article:published_time"]',
            'meta[name="article:published_time"]',
            'meta[property="og:published_time"]', 
            'meta[name="published_time"]',
            'meta[name="date"]',
            'meta[itemprop="datePublished"]',
            'time[itemprop="datePublished"]',
            'time[datetime]'
        ]
        
        for selector in selectors:
            elem = soup.select_one(selector)
            if elem:
                date_str = elem.get('content') or elem.get('datetime') or elem.text
                if date_str:
                    try:
                        return parse_date(date_str)
                    except Exception:
                        continue
        
        return datetime.now(timezone.utc)
    
    def _extract_author(self, soup: BeautifulSoup) -> str:
        """Try to extract author from HTML meta tags"""
        selectors = [
            'meta[name="author"]',
            'meta[property="article:author"]',
            'meta[name="article:author"]',
            'meta[itemprop="author"]',
            '[rel="author"]'
        ]
        
        for selector in selectors:
            elem = soup.select_one(selector)
            if elem:
                author = elem.get('content') or elem.text
                if author:
                    return author.strip()
        
        return None
    
    def _extract_image(self, soup: BeautifulSoup, base_url: str) -> str:
        """Try to extract main image from HTML"""
        selectors = [
            'meta[property="og:image"]',
            'meta[name="twitter:image"]',
            'meta[itemprop="image"]',
        ]
        
        for selector in selectors:
            elem = soup.select_one(selector)
            if elem:
                img_url = elem.get('content')
                if img_url:
                    return urljoin(base_url, img_url)
        
        # Fallback to first article image
        article_img = soup.select_one('article img, .content img, .post img')
        if article_img:
            img_url = article_img.get('src')
            if img_url:
                return urljoin(base_url, img_url)
        
        return None


# Register the adapter
AdapterFactory.register('sitemap', SitemapAdapter)