"""
Enhanced Content Extraction Service with Image Pipeline v2
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List
from urllib.parse import urlparse
from datetime import datetime, timezone

from sqlalchemy.orm import Session
import httpx
from readability import Document

from .config import settings
from .images2 import image_extractor, ImageCandidate, CachedImageMeta
from .store import Article

logger = logging.getLogger(__name__)

class ContentExtractionServiceV2:
    """Enhanced content extraction with integrated image pipeline"""
    
    def __init__(self, db: Session):
        self.db = db
        self.session = None
    
    async def get_session(self) -> httpx.AsyncClient:
        """Get or create HTTP session"""
        if not self.session:
            self.session = httpx.AsyncClient(
                timeout=httpx.Timeout(connect=10.0, read=30.0, write=10.0, pool=10.0),
                headers={
                    'User-Agent': settings.image_proxy_user_agent
                },
                follow_redirects=True
            )
        return self.session
    
    async def close(self):
        """Close HTTP session"""
        if self.session:
            await self.session.aclose()
            self.session = None
        await image_extractor.close()
    
    async def fetch_page_content(self, url: str) -> Optional[str]:
        """Fetch full page HTML for extraction"""
        session = await self.get_session()
        
        try:
            resp = await session.get(url)
            if resp.status_code == 200:
                return resp.text
        except Exception as e:
            logger.error(f"Failed to fetch page content for {url}: {e}")
        
        return None
    
    def create_rss_entry_dict(self, article: Article) -> Dict[str, Any]:
        """Convert Article model to RSS entry-like dict for image extraction"""
        return {
            'link': article.url,
            'title': article.title,
            'content': [{'value': article.content or ''}] if article.content else [],
            'enclosures': [],  # Would need to be populated from RSS data if available
            'media_content': [],
            'media_thumbnail': []
        }
    
    async def extract_article_content_and_image(
        self, 
        article: Article, 
        force: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Extract both article content and images in one pass
        """
        logger.info(f"INFO: Starting extract_article_content_and_image for {article.url}")
        
        # Skip if already extracted and not forcing
        if not force and article.extraction_status == 'success':
            return {
                'full_content': article.full_content,
                'content_html': article.content_html,
                'content_summary': article.content_summary,
                'has_image': article.has_image,
                'image_proxy_path': article.image_proxy_path
            }
        
        domain = urlparse(article.url).netloc
        
        try:
            # Mark as processing
            article.extraction_status = 'processing'
            article.extracted_at = datetime.now(timezone.utc)
            self.db.commit()
            
            # Fetch page HTML
            page_html = await self.fetch_page_content(article.url)
            
            if not page_html:
                article.extraction_status = 'failed'
                article.extraction_error = 'Failed to fetch page'
                image_extractor.record_image_diag(
                    self.db, article.id, domain, 'fetch', 
                    'page_fetch_failed', None, None
                )
                self.db.commit()
                return None
            
            # Extract content using readability
            doc = Document(page_html)
            content_html = doc.content()
            full_content = doc.summary()
            title = doc.short_title() or article.title
            
            # Update article content
            article.content_html = content_html
            article.full_content = full_content
            article.extraction_status = 'success'
            article.extraction_error = None
            
            # Extract images using enhanced pipeline
            rss_entry = self.create_rss_entry_dict(article)
            
            # Try to extract primary image
            best_candidate = await image_extractor.extract_primary_image(
                rss_entry, page_html, article.url
            )
            
            if best_candidate:
                logger.info(f"Found image candidate: {best_candidate.url} ({best_candidate.source_type})")
                
                # Cache the image
                cached_meta = await image_extractor.fetch_and_cache_image(
                    best_candidate.url, 
                    referer=article.url
                )
                
                if cached_meta:
                    # Update article with image data
                    article.image_src_url = best_candidate.url
                    article.image_proxy_path = cached_meta.proxy_path
                    article.image_width = cached_meta.width
                    article.image_height = cached_meta.height
                    article.image_blurhash = cached_meta.blurhash
                    article.has_image = True
                    article.image_stage = best_candidate.source_type
                    article.image_reason = f"success_{best_candidate.confidence:.2f}"
                    
                    logger.info(f"Cached image: {cached_meta.proxy_path} ({cached_meta.width}x{cached_meta.height})")
                else:
                    # Image fetch/cache failed
                    article.image_stage = best_candidate.source_type
                    article.image_reason = "cache_failed"
                    
                    image_extractor.record_image_diag(
                        self.db, article.id, domain, best_candidate.source_type,
                        'cache_failed', None, None
                    )
                    
                    logger.warning(f"Failed to cache image: {best_candidate.url}")
            else:
                # No image candidates found
                article.image_stage = "none"
                article.image_reason = "no_candidates"
                
                image_extractor.record_image_diag(
                    self.db, article.id, domain, 'search',
                    'no_candidates', None, None
                )
                
                logger.debug(f"No image candidates found for: {article.url}")
            
            # Update scoring with image bonus
            if article.has_image and 'image_bonus' not in (article.scores or {}):
                scores = article.scores or {}
                scores['image_bonus'] = 3
                article.scores = scores
                
                # Recalculate total score
                article.score_total = sum(
                    v for v in scores.values() 
                    if isinstance(v, (int, float)) and v != scores.get('recency_factor', 0)
                )
            
            self.db.commit()
            
            return {
                'full_content': article.full_content,
                'content_html': article.content_html, 
                'content_summary': article.content_summary,
                'has_image': article.has_image,
                'image_proxy_path': article.image_proxy_path,
                'image_width': article.image_width,
                'image_height': article.image_height,
                'image_blurhash': article.image_blurhash
            }
            
        except Exception as e:
            logger.error(f"Content extraction failed for {article.url}: {e}")
            
            article.extraction_status = 'failed'
            article.extraction_error = str(e)
            
            image_extractor.record_image_diag(
                self.db, article.id, domain, 'error',
                f'extraction_error: {str(e)[:100]}', None, None
            )
            
            self.db.commit()
            return None
    
    async def process_articles_batch(
        self, 
        articles: List[Article], 
        force: bool = False
    ) -> Dict[str, int]:
        """Process multiple articles for content and image extraction"""
        logger.info(f"INFO: process_articles_batch called with {len(articles)} articles, force={force}")
        
        stats = {
            'total_processed': 0,
            'successful': 0,
            'failed': 0,
            'images_found': 0,
            'images_cached': 0
        }
        
        # Process articles with some concurrency but not too much
        semaphore = asyncio.Semaphore(3)  # Max 3 concurrent extractions
        
        async def process_single(article: Article) -> bool:
            async with semaphore:
                result = await self.extract_article_content_and_image(article, force)
                stats['total_processed'] += 1
                
                if result:
                    stats['successful'] += 1
                    if result.get('has_image'):
                        stats['images_found'] += 1
                        if result.get('image_proxy_path'):
                            stats['images_cached'] += 1
                    return True
                else:
                    stats['failed'] += 1
                    return False
        
        # Process all articles
        tasks = [process_single(article) for article in articles]
        await asyncio.gather(*tasks, return_exceptions=True)
        
        logger.info(f"Batch processing complete: {stats}")
        return stats