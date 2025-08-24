"""
Content extraction module using newspaper3k for full article content extraction
"""
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from urllib.parse import urlparse
import hashlib

from newspaper import Article
from readability import Document as Readability
import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

class ArticleContent:
    """Data class for extracted article content"""
    def __init__(
        self,
        full_text: str,
        full_html: str,
        title: str,
        authors: List[str],
        publish_date: Optional[datetime],
        top_image: Optional[str],
        summary: Optional[str],
        keywords: List[str],
        extraction_method: str = "newspaper3k"
    ):
        self.full_text = full_text
        self.full_html = full_html
        self.title = title
        self.authors = authors
        self.publish_date = publish_date
        self.top_image = top_image
        self.summary = summary
        self.keywords = keywords
        self.extraction_method = extraction_method
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage"""
        return {
            'full_content': self.full_text,
            'content_html': self.full_html,
            'content_summary': self.summary,
            'content_keywords': self.keywords,
            'authors': self.authors,
            'top_image_url': self.top_image,
            'extracted_at': datetime.utcnow(),
            'extraction_status': 'success'
        }


class ContentExtractor:
    """Main content extraction class using newspaper3k with fallback methods"""
    
    # User agents to rotate
    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0'
    ]
    
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.current_ua_index = 0
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            follow_redirects=True,
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
        )
    
    def _get_user_agent(self) -> str:
        """Rotate user agents"""
        ua = self.USER_AGENTS[self.current_ua_index]
        self.current_ua_index = (self.current_ua_index + 1) % len(self.USER_AGENTS)
        return ua
    
    async def extract_article(self, url: str) -> Optional[ArticleContent]:
        """
        Extract article content from URL using newspaper3k
        Falls back to readability-lxml if newspaper fails
        """
        try:
            # First try with newspaper3k
            content = await self._extract_with_newspaper(url)
            if content and len(content.full_text) > 100:
                return content
            
            # Fallback to readability-lxml
            logger.info(f"Newspaper3k extraction insufficient for {url}, trying readability")
            content = await self._extract_with_readability(url)
            if content:
                return content
            
            logger.warning(f"All extraction methods failed for {url}")
            return None
            
        except Exception as e:
            logger.error(f"Error extracting content from {url}: {str(e)}")
            return None
    
    async def _extract_with_newspaper(self, url: str) -> Optional[ArticleContent]:
        """Extract using newspaper3k library"""
        try:
            # Create Article instance
            article = Article(url)
            article.config.browser_user_agent = self._get_user_agent()
            article.config.request_timeout = self.timeout
            
            # Download and parse
            article.download()
            article.parse()
            
            # Try NLP processing for keywords and summary
            try:
                article.nlp()
            except Exception as e:
                logger.warning(f"NLP processing failed: {e}")
            
            # Clean HTML
            clean_html = self._clean_html(article.html if article.html else "")
            
            return ArticleContent(
                full_text=article.text,
                full_html=clean_html,
                title=article.title,
                authors=article.authors if article.authors else [],
                publish_date=article.publish_date,
                top_image=article.top_image,
                summary=article.summary if hasattr(article, 'summary') else None,
                keywords=article.keywords if hasattr(article, 'keywords') else [],
                extraction_method="newspaper3k"
            )
            
        except Exception as e:
            logger.error(f"Newspaper extraction failed for {url}: {str(e)}")
            return None
    
    async def _extract_with_readability(self, url: str) -> Optional[ArticleContent]:
        """Fallback extraction using readability-lxml"""
        try:
            # Fetch content with httpx
            headers = {'User-Agent': self._get_user_agent()}
            response = await self.client.get(url, headers=headers)
            response.raise_for_status()
            
            # Parse with readability
            doc = Readability(response.text)
            result = doc.summary()
            title = doc.title()
            
            # Extract text from HTML
            soup = BeautifulSoup(result, 'html.parser')
            text = soup.get_text(separator='\n', strip=True)
            
            # Clean HTML
            clean_html = self._clean_html(result)
            
            return ArticleContent(
                full_text=text,
                full_html=clean_html,
                title=title,
                authors=[],  # Readability doesn't extract authors
                publish_date=None,
                top_image=self._extract_top_image(soup, url),
                summary=text[:500] if text else None,  # First 500 chars as summary
                keywords=[],
                extraction_method="readability"
            )
            
        except Exception as e:
            logger.error(f"Readability extraction failed for {url}: {str(e)}")
            return None
    
    def _clean_html(self, html: str) -> str:
        """Clean and sanitize HTML content"""
        if not html:
            return ""
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Remove script and style tags
            for tag in soup(['script', 'style', 'meta', 'link', 'noscript']):
                tag.decompose()
            
            # Remove comments
            for comment in soup.find_all(string=lambda text: isinstance(text, type(soup.new_string('')))):
                if '<!--' in str(comment):
                    comment.extract()
            
            # Remove ads and tracking elements
            for tag in soup.find_all(class_=lambda x: x and any(
                ad_word in x.lower() for ad_word in ['ad', 'banner', 'sponsor', 'promo', 'widget']
            )):
                tag.decompose()
            
            return str(soup)
            
        except Exception as e:
            logger.error(f"HTML cleaning failed: {e}")
            return html
    
    def _extract_top_image(self, soup: BeautifulSoup, base_url: str) -> Optional[str]:
        """Extract top image from HTML soup"""
        try:
            # Look for og:image meta tag first
            og_image = soup.find('meta', property='og:image')
            if og_image and og_image.get('content'):
                return self._make_absolute_url(og_image['content'], base_url)
            
            # Look for first significant image
            for img in soup.find_all('img'):
                src = img.get('src')
                if src and not any(skip in src.lower() for skip in ['icon', 'logo', 'avatar', 'ad']):
                    # Check if image is large enough
                    width = img.get('width')
                    height = img.get('height')
                    if width and height:
                        try:
                            if int(width) > 200 and int(height) > 200:
                                return self._make_absolute_url(src, base_url)
                        except:
                            pass
                    else:
                        # If no size info, return first image
                        return self._make_absolute_url(src, base_url)
            
            return None
            
        except Exception as e:
            logger.error(f"Image extraction failed: {e}")
            return None
    
    def _make_absolute_url(self, url: str, base_url: str) -> str:
        """Convert relative URLs to absolute"""
        if not url:
            return ""
        
        if url.startswith('http://') or url.startswith('https://'):
            return url
        
        if url.startswith('//'):
            return 'https:' + url
        
        if url.startswith('/'):
            parsed = urlparse(base_url)
            return f"{parsed.scheme}://{parsed.netloc}{url}"
        
        # Relative path
        base_parts = base_url.rsplit('/', 1)
        return f"{base_parts[0]}/{url}"
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()