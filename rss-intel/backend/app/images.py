"""
Image extraction and proxy caching for RSS articles
"""

import os
import json
import hashlib
import re
import io
from pathlib import Path
from typing import Optional, Dict, Any, List, NamedTuple
from urllib.parse import urljoin, urlparse, parse_qs
import httpx
from PIL import Image, ImageOps
from bs4 import BeautifulSoup
import blurhash
from datetime import datetime, timedelta
import asyncio
from .proxy_utils import create_httpx_client

class ImageCandidate(NamedTuple):
    url: str
    width: Optional[int] = None
    height: Optional[int] = None
    source: str = "unknown"

class CachedImageMeta(NamedTuple):
    proxy_path: str
    width: int
    height: int
    blurhash_value: str
    content_type: str
    file_size: int

class ImageProcessor:
    def __init__(self, 
                 cache_dir: str = "/data/image-cache",
                 max_bytes: int = 5 * 1024 * 1024,  # 5MB
                 timeout_sec: int = 8,
                 connect_sec: int = 3,
                 user_agent: str = "RSSIntelBot/1.0",
                 min_width: int = 320,
                 min_height: int = 180,
                 revalidate_after_hours: int = 168):  # 7 days
        self.cache_dir = Path(cache_dir)
        self.max_bytes = max_bytes
        self.timeout_sec = timeout_sec
        self.connect_sec = connect_sec
        self.user_agent = user_agent
        self.min_width = min_width
        self.min_height = min_height
        self.revalidate_after_hours = revalidate_after_hours
        
        # Create cache directory structure
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def normalize_url(self, base: str, candidate: str) -> str:
        """Convert relative URL to absolute and remove tracking parameters"""
        # Make absolute
        absolute_url = urljoin(base, candidate)
        
        # Parse URL components
        parsed = urlparse(absolute_url)
        
        # Remove common tracking parameters
        tracking_params = {
            'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
            'fbclid', 'gclid', 'ref', 'source'
        }
        
        if parsed.query:
            query_dict = parse_qs(parsed.query, keep_blank_values=True)
            cleaned_query = {
                k: v for k, v in query_dict.items() 
                if k.lower() not in tracking_params
            }
            
            # Rebuild query string
            if cleaned_query:
                query_parts = []
                for k, v_list in cleaned_query.items():
                    for v in v_list:
                        if v:
                            query_parts.append(f"{k}={v}")
                        else:
                            query_parts.append(k)
                new_query = "&".join(query_parts)
            else:
                new_query = ""
        else:
            new_query = ""
        
        # Reconstruct URL
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}" + (f"?{new_query}" if new_query else "")

    def pick_primary_image(self, entry: Dict[str, Any]) -> Optional[ImageCandidate]:
        """Extract best image candidate from RSS entry"""
        
        # 1. RSS enclosure (image/*)
        if hasattr(entry, 'enclosures'):
            for enclosure in entry.get('enclosures', []):
                if enclosure.get('type', '').startswith('image/'):
                    return ImageCandidate(
                        url=enclosure.get('href', ''),
                        source="enclosure"
                    )
        
        # 2. Media content/thumbnail
        if hasattr(entry, 'media_content'):
            for media in entry.get('media_content', []):
                if media.get('type', '').startswith('image/'):
                    return ImageCandidate(
                        url=media.get('url', ''),
                        width=media.get('width'),
                        height=media.get('height'),
                        source="media_content"
                    )
        
        if hasattr(entry, 'media_thumbnail'):
            for thumb in entry.get('media_thumbnail', []):
                return ImageCandidate(
                    url=thumb.get('url', ''),
                    width=thumb.get('width'),
                    height=thumb.get('height'),
                    source="media_thumbnail"
                )
        
        # 3. Parse content for <img> tags
        content_text = ""
        if hasattr(entry, 'content') and entry.content:
            content_text = entry.content[0].value if hasattr(entry.content[0], 'value') else str(entry.content[0])
        elif hasattr(entry, 'summary'):
            content_text = entry.get('summary', '')
        
        if content_text:
            img_candidate = self._extract_img_from_html(content_text)
            if img_candidate:
                return img_candidate
        
        # 4. Fetch page for og:image / twitter:image (if entry has link)
        if hasattr(entry, 'link') or 'link' in entry:
            link = entry.get('link', '')
            if link:
                og_image = self._fetch_og_image(link)
                if og_image:
                    return og_image
        
        return None

    def _extract_img_from_html(self, html_content: str) -> Optional[ImageCandidate]:
        """Extract largest <img> from HTML content"""
        try:
            soup = BeautifulSoup(html_content, 'lxml')
            images = soup.find_all('img')
            
            best_img = None
            best_size = 0
            
            for img in images:
                src = img.get('src') or img.get('data-src')
                if not src:
                    continue
                
                # Try to get dimensions
                width = self._parse_dimension(img.get('width'))
                height = self._parse_dimension(img.get('height'))
                
                # Calculate size score (width * height, or estimate if missing)
                if width and height:
                    size = width * height
                elif width:
                    size = width * 300  # Estimate height
                elif height:
                    size = height * 400  # Estimate width
                else:
                    size = 100000  # Default size for images without dimensions
                
                if size > best_size:
                    best_size = size
                    best_img = ImageCandidate(
                        url=src,
                        width=width,
                        height=height,
                        source="content_img"
                    )
            
            return best_img
        except Exception:
            return None

    def _parse_dimension(self, value: Optional[str]) -> Optional[int]:
        """Parse width/height attribute"""
        if not value:
            return None
        try:
            # Remove 'px' suffix if present
            if value.endswith('px'):
                value = value[:-2]
            return int(value)
        except (ValueError, TypeError):
            return None

    def _fetch_og_image(self, page_url: str) -> Optional[ImageCandidate]:
        """Fetch page and extract og:image or twitter:image"""
        try:
            with create_httpx_client(timeout=5) as client:
                response = client.get(page_url, headers={'User-Agent': self.user_agent})
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'lxml')
                    
                    # Try og:image first
                    og_img = soup.find('meta', property='og:image')
                    if og_img and og_img.get('content'):
                        return ImageCandidate(
                            url=og_img['content'],
                            source="og_image"
                        )
                    
                    # Try twitter:image
                    twitter_img = soup.find('meta', name='twitter:image') or soup.find('meta', property='twitter:image')
                    if twitter_img and twitter_img.get('content'):
                        return ImageCandidate(
                            url=twitter_img['content'],
                            source="twitter_image"
                        )
        except Exception:
            pass
        
        return None

    async def fetch_and_cache(self, url: str, base_url: str = "") -> Optional[CachedImageMeta]:
        """Fetch image and cache it with metadata"""
        try:
            # Normalize URL
            normalized_url = self.normalize_url(base_url or url, url)
            
            # Generate cache path based on URL hash
            url_hash = hashlib.sha256(normalized_url.encode()).hexdigest()
            cache_subdir = self.cache_dir / url_hash[:2] / url_hash[2:4]
            cache_subdir.mkdir(parents=True, exist_ok=True)
            
            # File paths
            image_file = cache_subdir / f"{url_hash}.jpg"
            meta_file = cache_subdir / f"{url_hash}.json"
            
            # Check if cached and still valid
            if await self._is_cache_valid(meta_file, normalized_url):
                return self._load_cache_meta(meta_file)
            
            # Fetch image
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(
                    connect=self.connect_sec,
                    read=self.timeout_sec
                )
            ) as client:
                response = await client.get(
                    normalized_url,
                    headers={'User-Agent': self.user_agent},
                    follow_redirects=True
                )
                
                if response.status_code != 200:
                    return None
                
                # Check content type
                content_type = response.headers.get('content-type', '').lower()
                if not any(mime in content_type for mime in ['image/jpeg', 'image/png', 'image/webp']):
                    return None
                
                # Check size
                content_length = int(response.headers.get('content-length', 0))
                if content_length > self.max_bytes:
                    return None
                
                image_data = response.content
                if len(image_data) > self.max_bytes:
                    return None
            
            # Process image with Pillow
            return await self._process_and_save_image(
                image_data, image_file, meta_file, normalized_url, response.headers
            )
        
        except Exception as e:
            print(f"Error fetching image {url}: {e}")
            return None

    async def _is_cache_valid(self, meta_file: Path, url: str) -> bool:
        """Check if cached image is still valid"""
        if not meta_file.exists():
            return False
        
        try:
            with open(meta_file, 'r') as f:
                meta = json.load(f)
            
            # Check age
            cached_at = datetime.fromisoformat(meta.get('cached_at', ''))
            if datetime.now() - cached_at > timedelta(hours=self.revalidate_after_hours):
                # Could implement HEAD request here for revalidation
                return False
            
            return True
        except Exception:
            return False

    def _load_cache_meta(self, meta_file: Path) -> Optional[CachedImageMeta]:
        """Load cached image metadata"""
        try:
            with open(meta_file, 'r') as f:
                meta = json.load(f)
            
            return CachedImageMeta(
                proxy_path=meta['proxy_path'],
                width=meta['width'],
                height=meta['height'],
                blurhash_value=meta['blurhash'],
                content_type=meta['content_type'],
                file_size=meta['file_size']
            )
        except Exception:
            return None

    async def _process_and_save_image(self, image_data: bytes, image_file: Path, 
                                    meta_file: Path, url: str, headers: Dict[str, str]) -> Optional[CachedImageMeta]:
        """Process image with Pillow and save"""
        try:
            # Open image with Pillow
            image = Image.open(io.BytesIO(image_data))
            
            # Auto-orient image
            image = ImageOps.exif_transpose(image)
            
            # Check minimum dimensions
            if image.width < self.min_width or image.height < self.min_height:
                return None
            
            # Convert to RGB if needed (for JPEG saving)
            if image.mode not in ('RGB', 'L'):
                image = image.convert('RGB')
            
            # Save as JPEG with good quality
            image.save(image_file, 'JPEG', quality=85, optimize=True)
            
            # Generate blurhash (resize to small size first for performance)
            thumb = image.copy()
            thumb.thumbnail((32, 32), Image.Resampling.LANCZOS)
            thumb = thumb.convert('RGB')
            
            # Convert to numpy-like array for blurhash
            import numpy as np
            thumb_array = np.array(thumb)
            blurhash_value = blurhash.encode(thumb_array, x_components=4, y_components=3)
            
            # Create proxy path
            url_hash = hashlib.sha256(url.encode()).hexdigest()
            proxy_path = f"{url_hash[:2]}/{url_hash[2:4]}/{url_hash}.jpg"
            
            # Save metadata
            meta = {
                'url': url,
                'proxy_path': proxy_path,
                'width': image.width,
                'height': image.height,
                'blurhash': blurhash_value,
                'content_type': 'image/jpeg',
                'file_size': image_file.stat().st_size,
                'cached_at': datetime.now().isoformat(),
                'etag': headers.get('etag'),
                'last_modified': headers.get('last-modified')
            }
            
            with open(meta_file, 'w') as f:
                json.dump(meta, f)
            
            return CachedImageMeta(
                proxy_path=proxy_path,
                width=image.width,
                height=image.height,
                blurhash_value=blurhash_value,
                content_type='image/jpeg',
                file_size=meta['file_size']
            )
        
        except Exception as e:
            print(f"Error processing image: {e}")
            return None

