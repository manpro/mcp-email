"""
Content extraction service with rate limiting, retry logic, and robots.txt compliance
"""
import asyncio
import logging
from typing import Dict, Optional, List, Any
from datetime import datetime, timedelta
from urllib.parse import urlparse
from collections import defaultdict
import time

from asyncio_throttle import Throttler
from sqlalchemy.orm import Session
import httpx
from urllib.robotparser import RobotFileParser

from .content_extractor import ContentExtractor, ArticleContent
from .store import Article, ArticleStore

logger = logging.getLogger(__name__)


class RobotsChecker:
    """Check robots.txt compliance for URLs"""
    
    def __init__(self):
        self.robots_cache: Dict[str, RobotFileParser] = {}
        self.cache_expiry: Dict[str, datetime] = {}
        self.cache_duration = timedelta(hours=24)
    
    async def can_fetch(self, url: str, user_agent: str = "*") -> bool:
        """Check if URL can be fetched according to robots.txt"""
        try:
            parsed = urlparse(url)
            domain = f"{parsed.scheme}://{parsed.netloc}"
            
            # Check cache
            if domain in self.robots_cache:
                if datetime.utcnow() < self.cache_expiry[domain]:
                    return self.robots_cache[domain].can_fetch(user_agent, url)
            
            # Fetch and parse robots.txt
            robots_url = f"{domain}/robots.txt"
            robot_parser = RobotFileParser()
            robot_parser.set_url(robots_url)
            
            # Fetch robots.txt asynchronously
            async with httpx.AsyncClient() as client:
                try:
                    response = await client.get(robots_url, timeout=5)
                    if response.status_code == 200:
                        robot_parser.parse(response.text.splitlines())
                    else:
                        # No robots.txt means everything is allowed
                        return True
                except:
                    # If we can't fetch robots.txt, assume allowed
                    return True
            
            # Cache the parser
            self.robots_cache[domain] = robot_parser
            self.cache_expiry[domain] = datetime.utcnow() + self.cache_duration
            
            return robot_parser.can_fetch(user_agent, url)
            
        except Exception as e:
            logger.error(f"Error checking robots.txt for {url}: {e}")
            # Default to allowing if error
            return True


class ContentExtractionService:
    """Service for managing content extraction with rate limiting and queue management"""
    
    def __init__(
        self,
        db: Session,
        max_concurrent: int = 5,
        rate_limit: float = 1.0,  # Requests per second per domain
        max_retries: int = 3
    ):
        self.db = db
        self.store = ArticleStore(db)
        self.extractor = ContentExtractor()
        self.robots_checker = RobotsChecker()
        
        # Rate limiting setup
        self.max_concurrent = max_concurrent
        self.rate_limit = rate_limit
        self.max_retries = max_retries
        
        # Domain-specific rate limiters
        self.domain_throttlers: Dict[str, Throttler] = {}
        self.domain_last_request: Dict[str, float] = defaultdict(float)
        
        # Global concurrent limit
        self.semaphore = asyncio.Semaphore(max_concurrent)
        
        # Statistics
        self.stats = {
            'total_processed': 0,
            'successful': 0,
            'failed': 0,
            'skipped_robots': 0,
            'retries': 0
        }
    
    def _get_domain(self, url: str) -> str:
        """Extract domain from URL"""
        parsed = urlparse(url)
        return parsed.netloc
    
    async def _get_throttler(self, domain: str) -> Throttler:
        """Get or create throttler for domain"""
        if domain not in self.domain_throttlers:
            self.domain_throttlers[domain] = Throttler(rate_limit=self.rate_limit)
        return self.domain_throttlers[domain]
    
    async def extract_article_content(
        self,
        article: Article,
        force: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Extract content for a single article with rate limiting
        
        Args:
            article: Article model instance
            force: Force re-extraction even if already extracted
        
        Returns:
            Updated article data or None if failed
        """
        # Skip if already extracted unless forced
        if not force and article.extraction_status == 'success':
            logger.info(f"Article {article.id} already extracted, skipping")
            return None
        
        # Check robots.txt
        if not article.robots_txt_checked:
            can_fetch = await self.robots_checker.can_fetch(article.url)
            article.robots_txt_checked = True
            
            if not can_fetch:
                logger.warning(f"Robots.txt disallows fetching {article.url}")
                article.extraction_status = 'robots_blocked'
                self.db.commit()
                self.stats['skipped_robots'] += 1
                return None
        
        domain = self._get_domain(article.url)
        
        # Rate limiting per domain
        throttler = await self._get_throttler(domain)
        
        # Global concurrent limit
        async with self.semaphore:
            async with throttler:
                # Add extra delay based on domain
                min_delay = 1.0 / self.rate_limit
                last_request = self.domain_last_request[domain]
                time_since_last = time.time() - last_request
                
                if time_since_last < min_delay:
                    await asyncio.sleep(min_delay - time_since_last)
                
                # Extract with retries
                content = await self._extract_with_retry(article.url)
                
                # Update last request time
                self.domain_last_request[domain] = time.time()
                
                if content:
                    # Update article with extracted content
                    update_data = content.to_dict()
                    for key, value in update_data.items():
                        setattr(article, key, value)
                    
                    self.db.commit()
                    self.stats['successful'] += 1
                    
                    logger.info(f"Successfully extracted content for article {article.id}")
                    return update_data
                else:
                    # Mark as failed
                    article.extraction_status = 'failed'
                    article.extraction_error = 'Failed to extract content after retries'
                    self.db.commit()
                    self.stats['failed'] += 1
                    
                    logger.error(f"Failed to extract content for article {article.id}")
                    return None
    
    async def _extract_with_retry(self, url: str) -> Optional[ArticleContent]:
        """Extract content with retry logic"""
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                if attempt > 0:
                    # Exponential backoff
                    wait_time = 2 ** attempt
                    logger.info(f"Retry {attempt} for {url}, waiting {wait_time}s")
                    await asyncio.sleep(wait_time)
                    self.stats['retries'] += 1
                
                content = await self.extractor.extract_article(url)
                if content:
                    return content
                    
            except Exception as e:
                last_error = e
                logger.warning(f"Attempt {attempt + 1} failed for {url}: {e}")
        
        logger.error(f"All retries exhausted for {url}. Last error: {last_error}")
        return None
    
    async def process_pending_articles(
        self,
        limit: Optional[int] = None,
        min_score: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Process all pending articles for content extraction
        
        Args:
            limit: Maximum number of articles to process
            min_score: Minimum score required for extraction
        
        Returns:
            Processing statistics
        """
        # Query pending articles
        query = self.db.query(Article).filter(
            Article.extraction_status == 'pending'
        )
        
        if min_score is not None:
            query = query.filter(Article.score_total >= min_score)
        
        # Order by score and date
        query = query.order_by(
            Article.score_total.desc(),
            Article.published_at.desc()
        )
        
        if limit:
            query = query.limit(limit)
        
        articles = query.all()
        
        logger.info(f"Processing {len(articles)} pending articles")
        
        # Process articles concurrently
        tasks = []
        for article in articles:
            task = self.extract_article_content(article)
            tasks.append(task)
            self.stats['total_processed'] += 1
        
        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Log any exceptions
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Error processing article {articles[i].id}: {result}")
        
        return self.get_stats()
    
    async def process_article_batch(
        self,
        article_ids: List[int],
        force: bool = False
    ) -> Dict[str, Any]:
        """
        Process specific articles by ID
        
        Args:
            article_ids: List of article IDs to process
            force: Force re-extraction
        
        Returns:
            Processing statistics
        """
        articles = self.db.query(Article).filter(
            Article.id.in_(article_ids)
        ).all()
        
        tasks = []
        for article in articles:
            task = self.extract_article_content(article, force=force)
            tasks.append(task)
            self.stats['total_processed'] += 1
        
        await asyncio.gather(*tasks, return_exceptions=True)
        
        return self.get_stats()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get extraction statistics"""
        return {
            **self.stats,
            'success_rate': (
                self.stats['successful'] / self.stats['total_processed'] * 100
                if self.stats['total_processed'] > 0 else 0
            )
        }
    
    def reset_stats(self):
        """Reset statistics"""
        self.stats = {
            'total_processed': 0,
            'successful': 0,
            'failed': 0,
            'skipped_robots': 0,
            'retries': 0
        }
    
    async def close(self):
        """Cleanup resources"""
        await self.extractor.close()