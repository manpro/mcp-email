"""
Enhanced Image Extraction Pipeline v2
Supports multiple sources, formats, lazy loading, diagnostics
"""

import asyncio
import hashlib
import json
import logging
import os
import re
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from urllib.parse import urljoin, urlparse, parse_qs, urlencode, urlunparse
from xml.etree import ElementTree as ET

import httpx
import yaml
from bs4 import BeautifulSoup
from PIL import Image, ExifTags, ImageOps
from sqlalchemy.orm import Session

try:
    import blurhash
except ImportError:
    blurhash = None

try:
    from playwright.async_api import async_playwright
except ImportError:
    async_playwright = None

from .config import settings

logger = logging.getLogger(__name__)


def safe_confidence(candidate) -> float:
    """Safely extract confidence as float, handle string values"""
    try:
        conf = getattr(candidate, 'confidence', 0.5)
        if isinstance(conf, str):
            return float(conf)
        return float(conf)
    except (ValueError, TypeError):
        return 0.5


@dataclass
class ImageCandidate:
    """Represents a potential image for an article"""
    url: str
    width: Optional[int] = None
    height: Optional[int] = None
    alt: Optional[str] = None
    source_type: str = "unknown"  # enclosure|media|content|og|jsonld|amp|newsletter|yt|fallback|playwright
    confidence: float = 0.5
    
    @property
    def area(self) -> int:
        """Calculate pixel area for comparison"""
        if self.width and self.height:
            return self.width * self.height
        return 0

@dataclass
class CachedImageMeta:
    """Metadata for cached image"""
    proxy_path: str
    width: int
    height: int
    blurhash: Optional[str]
    original_url: str
    cached_at: datetime
    etag: Optional[str] = None
    last_modified: Optional[str] = None
    file_size: int = 0

class ImageExtractor:
    """Enhanced image extraction with multiple source support"""
    
    def __init__(self):
        self.rules = self._load_domain_rules()
        self.session = None
        self._playwright_semaphore = asyncio.Semaphore(settings.image_playwright_max_concurrency)
    
    def _load_domain_rules(self) -> Dict:
        """Load domain-specific extraction rules"""
        rules_path = Path(settings.image_domain_rules_path)
        if rules_path.exists():
            try:
                with open(rules_path) as f:
                    return yaml.safe_load(f) or {}
            except Exception as e:
                logger.error(f"Failed to load image rules: {e}")
        return {"domains": {}, "global": {}}
    
    async def get_session(self) -> httpx.AsyncClient:
        """Get or create HTTP session"""
        if not self.session:
            self.session = httpx.AsyncClient(
                timeout=float(settings.image_proxy_timeout_sec),
                headers={
                    "User-Agent": settings.image_proxy_user_agent
                },
                follow_redirects=True
            )
        return self.session
    
    async def close(self):
        """Close HTTP session"""
        if self.session:
            await self.session.aclose()
            self.session = None

    def normalize_candidate_url(self, base_url: str, candidate_url: str) -> str:
        """Convert to absolute URL and strip tracking parameters"""
        # Make absolute
        absolute_url = urljoin(base_url, candidate_url)
        
        # Parse URL
        parsed = urlparse(absolute_url)
        
        # Remove tracking parameters
        query_dict = parse_qs(parsed.query)
        tracking_params = self.rules.get("global", {}).get("tracking_params", [])
        
        filtered_query = {}
        for key, value in query_dict.items():
            # Remove if matches any tracking pattern
            is_tracking = any(key.startswith(pattern.rstrip("_")) for pattern in tracking_params)
            if not is_tracking:
                filtered_query[key] = value
        
        # Rebuild URL
        new_query = urlencode(filtered_query, doseq=True)
        clean_url = urlunparse((
            parsed.scheme, parsed.netloc, parsed.path,
            parsed.params, new_query, ""
        ))
        
        return clean_url
    
    def _extract_youtube_id(self, url: str) -> Optional[str]:
        """Extract YouTube video ID from various URL formats"""
        patterns = [
            r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]{11})',
            r'youtube\.com/v/([a-zA-Z0-9_-]{11})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None
    
    def _extract_from_rss_enclosures(self, entry: Dict) -> List[ImageCandidate]:
        """Extract images from RSS enclosures"""
        candidates = []
        
        # Check enclosures
        enclosures = entry.get('enclosures', [])
        for enclosure in enclosures:
            if enclosure.get('type', '').startswith('image/'):
                candidates.append(ImageCandidate(
                    url=enclosure['href'],
                    source_type="enclosure",
                    confidence=0.9
                ))
        
        return candidates
    
    def _extract_from_media_content(self, entry: Dict) -> List[ImageCandidate]:
        """Extract from media:content and media:thumbnail"""
        candidates = []
        
        # media:content
        media_content = entry.get('media_content', [])
        for media in media_content:
            if media.get('medium') == 'image' or media.get('type', '').startswith('image/'):
                width = media.get('width')
                height = media.get('height')
                candidates.append(ImageCandidate(
                    url=media['url'],
                    width=int(width) if width else None,
                    height=int(height) if height else None,
                    source_type="media",
                    confidence=0.85
                ))
        
        # media:thumbnail
        thumbnails = entry.get('media_thumbnail', [])
        for thumb in thumbnails:
            width = thumb.get('width')
            height = thumb.get('height')
            candidates.append(ImageCandidate(
                url=thumb['url'],
                width=int(width) if width else None,
                height=int(height) if height else None,
                source_type="media",
                confidence=0.7  # Lower confidence for thumbnails
            ))
        
        return candidates
    
    def _extract_from_content(self, content_html: str, base_url: str) -> List[ImageCandidate]:
        """Extract images from content HTML with srcset, lazy loading support"""
        if not content_html:
            return []
        
        candidates = []
        soup = BeautifulSoup(content_html, 'html.parser')
        
        # Find all img tags including those in noscript
        img_tags = soup.find_all('img')
        
        # Also check noscript blocks for lazy-loaded images
        noscript_tags = soup.find_all('noscript')
        for noscript in noscript_tags:
            noscript_soup = BeautifulSoup(str(noscript), 'html.parser')
            img_tags.extend(noscript_soup.find_all('img'))
        
        for img in img_tags:
            # Try different src attributes (lazy loading)
            src_candidates = [
                img.get('src'),
                img.get('data-src'),
                img.get('data-lazy-src'), 
                img.get('data-original'),
                img.get('data-srcset'),
            ]
            
            # Handle srcset
            srcset = img.get('srcset')
            if srcset:
                # Parse srcset and take largest image
                srcset_candidates = []
                for src_desc in srcset.split(','):
                    parts = src_desc.strip().split()
                    if parts:
                        url = parts[0]
                        # Extract width from descriptor like "800w"
                        width = None
                        if len(parts) > 1 and parts[1].endswith('w'):
                            try:
                                width = int(parts[1][:-1])
                            except ValueError:
                                pass
                        srcset_candidates.append((url, width))
                
                # Sort by width (largest first) 
                srcset_candidates.sort(key=lambda x: x[1] or 0, reverse=True)
                if srcset_candidates:
                    src_candidates.append(srcset_candidates[0][0])
            
            # Process each source candidate
            for src in src_candidates:
                if src and src.strip():
                    # Skip data URLs and very small images
                    if src.startswith('data:') or 'pixel' in src or '1x1' in src:
                        continue
                    
                    normalized_url = self.normalize_candidate_url(base_url, src.strip())
                    
                    # Extract dimensions from attributes
                    width = img.get('width')
                    height = img.get('height')
                    try:
                        width = int(width) if width else None
                        height = int(height) if height else None
                    except (ValueError, TypeError):
                        width = height = None
                    
                    candidates.append(ImageCandidate(
                        url=normalized_url,
                        width=width,
                        height=height,
                        alt=img.get('alt', ''),
                        source_type="content",
                        confidence=0.8
                    ))
                    break  # Take first valid source
        
        # Try domain-specific CSS selectors for better targeting
        domain = urlparse(base_url).netloc
        domain_rules = self.rules.get("domains", {}).get(domain, {})
        selectors = domain_rules.get("selectors", [])
        
        for selector in selectors:
            try:
                selected_imgs = soup.select(selector)
                for img in selected_imgs:
                    src = img.get('src') or img.get('data-src') or img.get('data-lazy-src')
                    if src:
                        normalized_url = self.normalize_candidate_url(base_url, src)
                        candidates.append(ImageCandidate(
                            url=normalized_url,
                            width=self._safe_int(img.get('width')),
                            height=self._safe_int(img.get('height')),
                            alt=img.get('alt', ''),
                            source_type="targeted",
                            confidence=0.85  # Higher confidence for targeted selectors
                        ))
            except Exception as e:
                logger.debug(f"Selector '{selector}' failed for {domain}: {e}")
                continue
        
        return candidates
    
    def _safe_int(self, value):
        """Safely convert value to int or return None"""
        if value is None:
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None
    
    def _extract_from_meta_tags(self, page_html: str, base_url: str) -> List[ImageCandidate]:
        """Extract from OpenGraph, Twitter Cards metadata"""
        if not page_html:
            return []
        
        candidates = []
        soup = BeautifulSoup(page_html, 'html.parser')
        
        # OpenGraph images
        og_images = soup.find_all('meta', property=re.compile(r'og:image'))
        for meta in og_images:
            content = meta.get('content')
            if content:
                candidates.append(ImageCandidate(
                    url=self.normalize_candidate_url(base_url, content),
                    source_type="og",
                    confidence=0.75
                ))
        
        # Twitter Card images
        twitter_images = soup.find_all('meta', attrs={'name': re.compile(r'twitter:image')})
        for meta in twitter_images:
            content = meta.get('content')
            if content:
                candidates.append(ImageCandidate(
                    url=self.normalize_candidate_url(base_url, content),
                    source_type="og", 
                    confidence=0.75
                ))
        
        return candidates
    
    def _extract_from_jsonld(self, page_html: str, base_url: str) -> List[ImageCandidate]:
        """Extract images from JSON-LD structured data"""
        if not page_html:
            return []
        
        candidates = []
        soup = BeautifulSoup(page_html, 'html.parser')
        
        # Find JSON-LD script tags
        jsonld_scripts = soup.find_all('script', type='application/ld+json')
        
        for script in jsonld_scripts:
            try:
                data = json.loads(script.string or '')
                
                # Handle array of objects
                if isinstance(data, list):
                    objects = data
                else:
                    objects = [data]
                
                for obj in objects:
                    if not isinstance(obj, dict):
                        continue
                    
                    # Look for Article or NewsArticle types
                    obj_type = obj.get('@type', '').lower()
                    if 'article' in obj_type or 'news' in obj_type:
                        image_data = obj.get('image')
                        
                        if isinstance(image_data, str):
                            # Simple string URL
                            candidates.append(ImageCandidate(
                                url=self.normalize_candidate_url(base_url, image_data),
                                source_type="jsonld",
                                confidence=0.8
                            ))
                        elif isinstance(image_data, list):
                            # Array of images
                            for img in image_data:
                                if isinstance(img, str):
                                    candidates.append(ImageCandidate(
                                        url=self.normalize_candidate_url(base_url, img),
                                        source_type="jsonld",
                                        confidence=0.8
                                    ))
                                elif isinstance(img, dict) and img.get('url'):
                                    candidates.append(ImageCandidate(
                                        url=self.normalize_candidate_url(base_url, img['url']),
                                        width=img.get('width'),
                                        height=img.get('height'),
                                        source_type="jsonld",
                                        confidence=0.8
                                    ))
                        elif isinstance(image_data, dict) and image_data.get('url'):
                            # Image object with metadata
                            candidates.append(ImageCandidate(
                                url=self.normalize_candidate_url(base_url, image_data['url']),
                                width=image_data.get('width'),
                                height=image_data.get('height'),
                                source_type="jsonld",
                                confidence=0.8
                            ))
                            
            except (json.JSONDecodeError, KeyError, AttributeError) as e:
                logger.debug(f"Failed to parse JSON-LD: {e}")
                continue
        
        return candidates
    
    async def _extract_from_amp(self, base_url: str) -> List[ImageCandidate]:
        """Try to fetch AMP version and extract hero image"""
        candidates = []
        
        # Get domain rules
        domain = urlparse(base_url).netloc
        domain_rules = self.rules.get("domains", {}).get(domain, {})
        
        amp_hint = domain_rules.get("amp_path_hint")
        amp_urls = []
        
        if amp_hint:
            # Use domain-specific hint
            if amp_hint.startswith('/'):
                parsed = urlparse(base_url)
                amp_url = f"{parsed.scheme}://{parsed.netloc}{amp_hint}"
            else:
                amp_url = base_url + amp_hint
            amp_urls.append(amp_url)
        else:
            # Try common AMP patterns
            amp_urls = [
                base_url + '/amp',
                base_url + '?amp=1',
                base_url.replace('//', '//amp.'),
            ]
        
        session = await self.get_session()
        
        for amp_url in amp_urls:
            try:
                resp = await session.get(amp_url)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, 'html.parser')
                    
                    # Look for amp-img tags
                    amp_imgs = soup.find_all('amp-img')
                    for amp_img in amp_imgs:
                        src = amp_img.get('src')
                        if src:
                            width = amp_img.get('width')
                            height = amp_img.get('height')
                            try:
                                width = int(width) if width else None
                                height = int(height) if height else None
                            except (ValueError, TypeError):
                                width = height = None
                            
                            candidates.append(ImageCandidate(
                                url=self.normalize_candidate_url(base_url, src),
                                width=width,
                                height=height,
                                source_type="amp",
                                confidence=0.85
                            ))
                    
                    if candidates:
                        break  # Found AMP images, stop trying other URLs
                        
            except Exception as e:
                logger.debug(f"AMP fetch failed for {amp_url}: {e}")
                continue
        
        return candidates
    
    def _extract_youtube_thumbnails(self, entry: Dict, base_url: str) -> List[ImageCandidate]:
        """Extract YouTube video thumbnails"""
        candidates = []
        
        # Check if this is a YouTube URL
        youtube_id = None
        
        # Try article URL first
        if 'youtube.com' in base_url or 'youtu.be' in base_url:
            youtube_id = self._extract_youtube_id(base_url)
        
        # Try content for embedded videos
        content = entry.get('content', [])
        if content and isinstance(content, list):
            content_html = content[0].get('value', '')
        else:
            content_html = str(content) if content else ''
        
        if not youtube_id and content_html:
            youtube_id = self._extract_youtube_id(content_html)
        
        if youtube_id:
            # Try different thumbnail qualities
            thumbnail_urls = [
                f"https://i.ytimg.com/vi/{youtube_id}/maxresdefault.jpg",  # 1280x720
                f"https://i.ytimg.com/vi/{youtube_id}/hqdefault.jpg",     # 480x360
                f"https://i.ytimg.com/vi/{youtube_id}/mqdefault.jpg",     # 320x180
            ]
            
            for i, thumb_url in enumerate(thumbnail_urls):
                candidates.append(ImageCandidate(
                    url=thumb_url,
                    width=1280 if i == 0 else (480 if i == 1 else 320),
                    height=720 if i == 0 else (360 if i == 1 else 180),
                    source_type="yt",
                    confidence=0.9 - (i * 0.1)  # Prefer higher quality
                ))
        
        return candidates
    
    def _is_blocked_by_patterns(self, url: str, domain: Optional[str] = None) -> bool:
        """Check if URL is blocked by global or domain-specific patterns"""
        # Get global blocked patterns
        global_blocked = self.rules.get("global", {}).get("blocked_patterns", [])
        
        # Get domain-specific patterns
        domain_blocked = []
        if domain:
            domain_rules = self.rules.get("domains", {}).get(domain, {})
            domain_blocked = domain_rules.get("blocked_patterns", [])
        
        all_blocked = global_blocked + domain_blocked
        
        url_lower = url.lower()
        for pattern in all_blocked:
            if pattern.lower() in url_lower:
                return True
        
        return False
    
    def _meets_size_requirements(self, candidate: ImageCandidate, domain: Optional[str] = None) -> bool:
        """Check if candidate meets minimum size requirements"""
        if not candidate.width or not candidate.height:
            return True  # Can't filter without dimensions
        
        # Get domain-specific minimums or use global
        min_width = settings.image_min_width
        min_height = settings.image_min_height
        
        if domain:
            domain_rules = self.rules.get("domains", {}).get(domain, {})
            min_width = domain_rules.get("min_width", min_width)
            min_height = domain_rules.get("min_height", min_height)
        
        if candidate.width < min_width or candidate.height < min_height:
            return False
        
        # Check aspect ratio
        aspect = candidate.width / candidate.height
        if aspect < settings.image_aspect_min or aspect > settings.image_aspect_max:
            return False
        
        return True
    
    def select_best_candidate(self, candidates: List[ImageCandidate]) -> Optional[ImageCandidate]:
        """Select the best image candidate from a list"""
        if not candidates:
            return None
        
        # Filter candidates
        valid_candidates = []
        
        for candidate in candidates:
            domain = urlparse(candidate.url).netloc
            
            # Skip if blocked by patterns
            if self._is_blocked_by_patterns(candidate.url, domain):
                continue
            
            # Skip if doesn't meet size requirements
            if not self._meets_size_requirements(candidate, domain):
                continue
            
            valid_candidates.append(candidate)
        
        if not valid_candidates:
            return None
        
        # Sort by confidence and area (larger images preferred)
        def score_candidate(c: ImageCandidate) -> Tuple[float, int]:
            return (c.confidence, c.area)
        
        valid_candidates.sort(key=score_candidate, reverse=True)
        return valid_candidates[0]
    
    async def extract_primary_image(
        self, 
        entry: Dict, 
        page_html: Optional[str] = None, 
        base_url: Optional[str] = None
    ) -> Optional[ImageCandidate]:
        """
        Extract primary image for an article using multiple strategies
        
        Priority order:
        1. RSS enclosure (image/*)
        2. media:content / media:thumbnail  
        3. First <img> in content (with srcset, noscript, lazy support)
        4. OG/Twitter meta tags
        5. JSON-LD structured data
        6. AMP version
        7. Newsletter cid: handling (if applicable)
        8. YouTube thumbnails
        9. Headless fallback (if enabled)
        """
        
        if not base_url:
            base_url = entry.get('link', '')
        
        all_candidates = []
        
        # 1. RSS enclosures
        all_candidates.extend(self._extract_from_rss_enclosures(entry))
        
        # 2. Media content
        all_candidates.extend(self._extract_from_media_content(entry))
        
        # 3. Content images
        content = entry.get('content', [])
        if content and isinstance(content, list):
            content_html = content[0].get('value', '')
        else:
            content_html = str(content) if content else ''
        
        if content_html:
            all_candidates.extend(self._extract_from_content(content_html, base_url))
        
        # 4-6. If no good candidates yet, try page HTML
        if not all_candidates or max(safe_confidence(c) for c in all_candidates) < 0.8:
            # Fetch page HTML if not provided
            if not page_html and base_url:
                try:
                    session = await self.get_session()
                    response = await session.get(base_url)
                    if response.status_code == 200:
                        page_html = response.text
                        logger.info(f"Fetched page HTML for image extraction: {len(page_html)} chars")
                except Exception as e:
                    logger.debug(f"Failed to fetch page HTML: {e}")
            
            if page_html:
                # OG/Twitter meta
                all_candidates.extend(self._extract_from_meta_tags(page_html, base_url))
                
                # JSON-LD
                all_candidates.extend(self._extract_from_jsonld(page_html, base_url))
                
                # Additional content images from full page
                all_candidates.extend(self._extract_from_content(page_html, base_url))
        
        # 5. AMP fallback (if still no high-confidence candidates)
        if not all_candidates or max(safe_confidence(c) for c in all_candidates) < 0.7:
            try:
                amp_candidates = await self._extract_from_amp(base_url)
                all_candidates.extend(amp_candidates)
            except Exception as e:
                logger.debug(f"AMP extraction failed: {e}")
        
        # 7. YouTube thumbnails  
        youtube_candidates = self._extract_youtube_thumbnails(entry, base_url)
        all_candidates.extend(youtube_candidates)
        
        # 8. Playwright headless fallback (if enabled and no good candidates yet)
        if (settings.image_playwright_enabled and 
            (not all_candidates or max(safe_confidence(c) for c in all_candidates) < 0.7)):
            try:
                playwright_candidates = await self._extract_with_playwright(base_url)
                all_candidates.extend(playwright_candidates)
                logger.info(f"Playwright fallback found {len(playwright_candidates)} candidates for {base_url}")
            except Exception as e:
                logger.debug(f"Playwright extraction failed for {base_url}: {e}")
        
        # Select best candidate
        return self.select_best_candidate(all_candidates)
    
    async def _extract_with_playwright(self, url: str) -> List[ImageCandidate]:
        """Extract images using Playwright for JavaScript-rendered pages"""
        if not async_playwright:
            return []
        
        candidates = []
        
        async with self._playwright_semaphore:
            try:
                async with async_playwright() as p:
                    # Launch browser
                    browser = await p.chromium.launch(
                        headless=True,
                        args=['--no-sandbox', '--disable-setuid-sandbox']
                    )
                    
                    context = await browser.new_context(
                        viewport={'width': 1920, 'height': 1080},
                        user_agent=settings.image_proxy_user_agent
                    )
                    
                    page = await context.new_page()
                    
                    # Navigate to page with timeout
                    await page.goto(url, wait_until='networkidle', timeout=15000)
                    
                    # Wait a bit for dynamic content
                    await page.wait_for_timeout(2000)
                    
                    # Extract OG meta tags (often populated by JS)
                    og_images = await page.query_selector_all('meta[property*="og:image"]')
                    for meta in og_images:
                        content = await meta.get_attribute('content')
                        if content:
                            candidates.append(ImageCandidate(
                                url=self.normalize_candidate_url(url, content),
                                source_type="playwright_og",
                                confidence=0.8
                            ))
                    
                    # Extract from high-confidence selectors
                    hero_selectors = [
                        'img[class*="hero"]', 'img[class*="featured"]', 'img[class*="banner"]',
                        '.hero-image img', '.featured-image img', '.article-image img',
                        '.post-thumbnail img', '.entry-image img'
                    ]
                    
                    for selector in hero_selectors:
                        try:
                            imgs = await page.query_selector_all(selector)
                            for img in imgs[:2]:  # Max 2 per selector
                                src = await img.get_attribute('src')
                                if src:
                                    width = await img.get_attribute('width')
                                    height = await img.get_attribute('height')
                                    alt = await img.get_attribute('alt') or ''
                                    
                                    candidates.append(ImageCandidate(
                                        url=self.normalize_candidate_url(url, src),
                                        width=self._safe_int(width),
                                        height=self._safe_int(height),
                                        alt=alt,
                                        source_type="playwright",
                                        confidence=0.75
                                    ))
                        except Exception:
                            continue
                    
                    # Domain-specific selectors
                    domain = urlparse(url).netloc
                    domain_rules = self.rules.get("domains", {}).get(domain, {})
                    selectors = domain_rules.get("selectors", [])
                    
                    for selector in selectors:
                        try:
                            imgs = await page.query_selector_all(selector)
                            for img in imgs[:1]:  # Just take the first from domain-specific
                                src = await img.get_attribute('src')
                                if src:
                                    candidates.append(ImageCandidate(
                                        url=self.normalize_candidate_url(url, src),
                                        width=self._safe_int(await img.get_attribute('width')),
                                        height=self._safe_int(await img.get_attribute('height')),
                                        alt=await img.get_attribute('alt') or '',
                                        source_type="playwright_targeted",
                                        confidence=0.85
                                    ))
                        except Exception:
                            continue
                    
                    await browser.close()
                    
            except Exception as e:
                logger.warning(f"Playwright extraction failed for {url}: {e}")
        
        return candidates
    
    def _generate_blurhash(self, image_path: Path) -> Optional[str]:
        """Generate blurhash for image"""
        if not blurhash:
            return None
        
        try:
            with Image.open(image_path) as img:
                # Resize to small size for blurhash
                img.thumbnail((32, 32), Image.Resampling.LANCZOS)
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Generate blurhash
                hash_str = blurhash.encode(img, x_components=4, y_components=3)
                return hash_str
        except Exception as e:
            logger.warning(f"Blurhash generation failed: {e}")
            return None
    
    def _get_cache_path(self, url: str) -> Tuple[Path, str]:
        """Get cache file path and proxy path for URL"""
        # Generate hash for URL
        url_hash = hashlib.sha256(url.encode()).hexdigest()
        
        # Create hierarchical path (first 2 chars, next 2 chars)
        h1, h2 = url_hash[:2], url_hash[2:4]
        
        # Cache directory structure
        cache_dir = Path(settings.image_proxy_cache_dir)
        file_dir = cache_dir / h1 / h2
        file_dir.mkdir(parents=True, exist_ok=True)
        
        # Determine file extension from URL
        parsed = urlparse(url)
        path = parsed.path.lower()
        if path.endswith('.png'):
            ext = '.png'
        elif path.endswith('.webp'):
            ext = '.webp'
        elif path.endswith('.gif'):
            ext = '.gif'
        else:
            ext = '.jpg'  # Default to JPEG
        
        filename = f"{url_hash}{ext}"
        file_path = file_dir / filename
        proxy_path = f"{h1}/{h2}/{filename}"
        
        return file_path, proxy_path
    
    async def fetch_and_cache_image(
        self, 
        url: str, 
        referer: Optional[str] = None
    ) -> Optional[CachedImageMeta]:
        """
        Fetch image from URL, validate, process and cache it
        Returns metadata about cached image
        """
        
        file_path, proxy_path = self._get_cache_path(url)
        sidecar_path = file_path.with_suffix('.json')
        
        # Check if we need to revalidate
        if file_path.exists() and sidecar_path.exists():
            try:
                with open(sidecar_path) as f:
                    meta = json.load(f)
                
                cached_at = datetime.fromisoformat(meta.get('cached_at', ''))
                
                # Check if revalidation is needed
                if settings.image_enable_revalidation:
                    revalidate_after = timedelta(hours=settings.image_revalidate_after_hours)
                    if datetime.now(timezone.utc) - cached_at.replace(tzinfo=timezone.utc) < revalidate_after:
                        # Still fresh, return cached metadata
                        return CachedImageMeta(
                            proxy_path=proxy_path,
                            width=meta.get('width', 0),
                            height=meta.get('height', 0),
                            blurhash=meta.get('blurhash'),
                            original_url=url,
                            cached_at=cached_at,
                            etag=meta.get('etag'),
                            last_modified=meta.get('last_modified'),
                            file_size=meta.get('file_size', 0)
                        )
                else:
                    # Revalidation disabled, return cached
                    return CachedImageMeta(
                        proxy_path=proxy_path,
                        width=meta.get('width', 0),
                        height=meta.get('height', 0),
                        blurhash=meta.get('blurhash'),
                        original_url=url,
                        cached_at=cached_at,
                        etag=meta.get('etag'),
                        last_modified=meta.get('last_modified'),
                        file_size=meta.get('file_size', 0)
                    )
            except Exception as e:
                logger.warning(f"Failed to read cache metadata: {e}")
        
        # Fetch image
        session = await self.get_session()
        
        headers = {}
        if referer and settings.image_proxy_send_referer:
            headers['Referer'] = referer
        
        # Add conditional headers for revalidation
        if sidecar_path.exists():
            try:
                with open(sidecar_path) as f:
                    old_meta = json.load(f)
                if old_meta.get('etag'):
                    headers['If-None-Match'] = old_meta['etag']
                if old_meta.get('last_modified'):
                    headers['If-Modified-Since'] = old_meta['last_modified']
            except:
                pass
        
        try:
            resp = await session.get(url, headers=headers)
            
            # Handle 304 Not Modified
            if resp.status_code == 304 and file_path.exists():
                # Update cached_at timestamp
                try:
                    with open(sidecar_path) as f:
                        meta = json.load(f)
                    meta['cached_at'] = datetime.now(timezone.utc).isoformat()
                    with open(sidecar_path, 'w') as f:
                        json.dump(meta, f)
                    
                    return CachedImageMeta(
                        proxy_path=proxy_path,
                        width=meta.get('width', 0),
                        height=meta.get('height', 0),
                        blurhash=meta.get('blurhash'),
                        original_url=url,
                        cached_at=datetime.fromisoformat(meta['cached_at']),
                        etag=meta.get('etag'),
                        last_modified=meta.get('last_modified'),
                        file_size=meta.get('file_size', 0)
                    )
                except:
                    pass
            
            if resp.status_code != 200:
                logger.warning(f"Image fetch failed: {resp.status_code} for {url}")
                return None
            
            # Check content type
            content_type = resp.headers.get('content-type', '').lower()
            allowed_types = self.rules.get("global", {}).get("mime_types", [
                "image/jpeg", "image/png", "image/webp", "image/gif"
            ])
            
            if not any(ct in content_type for ct in allowed_types):
                logger.warning(f"Invalid content type {content_type} for {url}")
                return None
            
            # Check file size
            content_length = len(resp.content)
            if content_length > settings.image_proxy_max_bytes:
                logger.warning(f"Image too large: {content_length} bytes for {url}")
                return None
            
            # Write to temporary file first
            temp_path = file_path.with_suffix('.tmp')
            with open(temp_path, 'wb') as f:
                f.write(resp.content)
            
            # Process with Pillow
            try:
                with Image.open(temp_path) as img:
                    # Auto-orient based on EXIF
                    if hasattr(img, '_getexif'):
                        exif = img._getexif()
                        if exif is not None:
                            for orientation_tag in [0x0112, 'Orientation']:
                                if orientation_tag in exif:
                                    img = ImageOps.exif_transpose(img)
                                    break
                    
                    # Get dimensions
                    width, height = img.size
                    
                    # Check minimum dimensions
                    if width < settings.image_min_width or height < settings.image_min_height:
                        logger.info(f"Image too small: {width}x{height} for {url}")
                        temp_path.unlink()
                        return None
                    
                    # Check aspect ratio
                    aspect = width / height
                    if aspect < settings.image_aspect_min or aspect > settings.image_aspect_max:
                        logger.info(f"Invalid aspect ratio {aspect:.2f} for {url}")
                        temp_path.unlink()
                        return None
                    
                    # Convert to RGB if necessary and save optimized version
                    if img.mode in ('RGBA', 'LA'):
                        # Create white background for transparency
                        background = Image.new('RGB', img.size, 'white')
                        if img.mode == 'RGBA':
                            background.paste(img, mask=img.split()[-1])
                        else:
                            background.paste(img, mask=img.split()[-1])
                        img = background
                    elif img.mode != 'RGB':
                        img = img.convert('RGB')
                    
                    # Save optimized image
                    if file_path.suffix.lower() == '.jpg':
                        img.save(file_path, 'JPEG', quality=85, optimize=True)
                    elif file_path.suffix.lower() == '.png':
                        img.save(file_path, 'PNG', optimize=True)
                    elif file_path.suffix.lower() == '.webp':
                        img.save(file_path, 'WEBP', quality=85, optimize=True)
                    else:
                        img.save(file_path, 'JPEG', quality=85, optimize=True)
                    
                    # Generate blurhash
                    blurhash_str = self._generate_blurhash(file_path)
                    
                    # Get final file size
                    final_size = file_path.stat().st_size
                    
                    # Save metadata
                    meta = {
                        'url': url,
                        'width': width,
                        'height': height,
                        'blurhash': blurhash_str,
                        'cached_at': datetime.now(timezone.utc).isoformat(),
                        'etag': resp.headers.get('etag'),
                        'last_modified': resp.headers.get('last-modified'),
                        'content_type': content_type,
                        'file_size': final_size
                    }
                    
                    with open(sidecar_path, 'w') as f:
                        json.dump(meta, f)
                    
                    # Remove temp file
                    temp_path.unlink(missing_ok=True)
                    
                    return CachedImageMeta(
                        proxy_path=proxy_path,
                        width=width,
                        height=height,
                        blurhash=blurhash_str,
                        original_url=url,
                        cached_at=datetime.now(timezone.utc),
                        etag=resp.headers.get('etag'),
                        last_modified=resp.headers.get('last-modified'),
                        file_size=final_size
                    )
                    
            except Exception as e:
                logger.error(f"Image processing failed for {url}: {e}")
                temp_path.unlink(missing_ok=True)
                return None
                
        except Exception as e:
            logger.error(f"Failed to fetch image {url}: {e}")
            return None
    
    def record_image_diag(
        self, 
        db: Session,
        article_id: int, 
        domain: str, 
        stage: str, 
        reason: str, 
        http_status: Optional[int] = None, 
        bytes: Optional[int] = None
    ):
        """Record image extraction diagnostics"""
        try:
            from .store import ImageDiagnostic
            
            # Create diagnostics record
            diagnostic = ImageDiagnostic(
                article_id=article_id,
                domain=domain,
                stage=stage,
                reason=reason,
                http_status=http_status,
                bytes=bytes,
                created_at=datetime.now(timezone.utc)
            )
            
            db.add(diagnostic)
            db.commit()
            
        except Exception as e:
            logger.error(f"Failed to record image diagnostic: {e}")

# Global instance
image_extractor = ImageExtractor()