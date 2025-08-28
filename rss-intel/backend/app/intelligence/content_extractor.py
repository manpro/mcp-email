"""
Content extraction service for web articles and text processing.
"""

import logging
import re
import asyncio
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urljoin, urlparse
import hashlib

try:
    import httpx
    import aiohttp
    from bs4 import BeautifulSoup
    from readability import Document
except ImportError:
    httpx = None
    aiohttp = None
    BeautifulSoup = None
    Document = None

logger = logging.getLogger(__name__)

@dataclass
class ArticleContent:
    """Extracted article content"""
    title: str
    content: str
    summary: Optional[str] = None
    author: Optional[str] = None
    published_date: Optional[datetime] = None
    image_url: Optional[str] = None
    keywords: List[str] = None
    language: Optional[str] = None
    reading_time: Optional[int] = None  # minutes
    
    def __post_init__(self):
        if self.keywords is None:
            self.keywords = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert ArticleContent to dictionary for database storage"""
        return {
            'full_content': self.content,
            'content_html': self.content,  # For now, same as content
            'content_summary': self.summary,
            'authors': [self.author] if self.author else [],
            'top_image_url': self.image_url,
            'content_keywords': self.keywords,
            'extraction_status': 'success',
            'extracted_at': datetime.utcnow(),
            'extraction_error': None
        }

class ContentExtractor:
    """Web content extraction service"""
    
    def __init__(self):
        self.session_timeout = 30
        self.user_agent = 'RSS Intelligence Bot/1.0 (+https://example.com/bot)'
        
    async def extract_from_url(self, url: str) -> Optional[ArticleContent]:
        """Extract article content from URL"""
        try:
            if not httpx:
                logger.warning("httpx not available, content extraction disabled")
                return None
                
            async with httpx.AsyncClient(timeout=self.session_timeout) as client:
                response = await client.get(
                    url,
                    headers={'User-Agent': self.user_agent},
                    follow_redirects=True
                )
                
                if response.status_code != 200:
                    logger.warning(f"HTTP {response.status_code} for {url}")
                    return None
                
                return self._parse_html(response.text, url)
                
        except Exception as e:
            logger.error(f"Error extracting content from {url}: {e}")
            return None
    
    def _parse_html(self, html: str, url: str) -> Optional[ArticleContent]:
        """Parse HTML and extract article content"""
        try:
            if not BeautifulSoup:
                logger.warning("BeautifulSoup not available, using basic extraction")
                return self._basic_extraction(html, url)
            
            # Use readability for main content extraction
            if Document:
                doc = Document(html)
                readable_html = doc.summary()
                title = doc.title()
            else:
                readable_html = html
                title = self._extract_title_basic(html)
            
            # Parse with BeautifulSoup
            soup = BeautifulSoup(readable_html, 'html.parser')
            
            # Extract text content
            content = self._extract_text(soup)
            if not content:
                return None
            
            # Extract metadata
            metadata = self._extract_metadata(BeautifulSoup(html, 'html.parser'), url)
            
            # Extract keywords
            keywords = extract_keywords(content)
            
            return ArticleContent(
                title=title or metadata.get('title', 'Untitled'),
                content=content,
                summary=self._generate_summary(content),
                author=metadata.get('author'),
                published_date=metadata.get('published_date'),
                image_url=metadata.get('image_url'),
                keywords=keywords,
                language=metadata.get('language'),
                reading_time=self._estimate_reading_time(content)
            )
            
        except Exception as e:
            logger.error(f"Error parsing HTML: {e}")
            return None
    
    def _basic_extraction(self, html: str, url: str) -> Optional[ArticleContent]:
        """Basic text extraction without external libraries"""
        try:
            # Simple regex-based extraction
            title_match = re.search(r'<title[^>]*>([^<]+)</title>', html, re.IGNORECASE)
            title = title_match.group(1).strip() if title_match else 'Untitled'
            
            # Remove script and style tags
            clean_html = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', html, flags=re.DOTALL | re.IGNORECASE)
            
            # Extract text
            text_content = re.sub(r'<[^>]+>', ' ', clean_html)
            text_content = re.sub(r'\s+', ' ', text_content).strip()
            
            if len(text_content) < 100:
                return None
                
            return ArticleContent(
                title=title,
                content=text_content[:5000],  # Limit content
                summary=text_content[:500] if len(text_content) > 500 else text_content,
                keywords=self._basic_keyword_extraction(text_content),
                reading_time=len(text_content.split()) // 200  # Rough estimate
            )
            
        except Exception as e:
            logger.error(f"Error in basic extraction: {e}")
            return None
    
    def _extract_title_basic(self, html: str) -> str:
        """Extract title using regex"""
        title_match = re.search(r'<title[^>]*>([^<]+)</title>', html, re.IGNORECASE)
        return title_match.group(1).strip() if title_match else 'Untitled'
    
    def _extract_text(self, soup) -> str:
        """Extract clean text from BeautifulSoup object"""
        # Remove script and style elements
        for element in soup(['script', 'style', 'nav', 'header', 'footer']):
            element.decompose()
        
        # Get text
        text = soup.get_text()
        
        # Clean up whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ' '.join(chunk for chunk in chunks if chunk)
        
        return text
    
    def _extract_metadata(self, soup, url: str) -> Dict[str, Any]:
        """Extract metadata from HTML"""
        metadata = {}
        
        try:
            # Author
            author_selectors = [
                'meta[name="author"]',
                'meta[property="article:author"]',
                '.author',
                '.byline'
            ]
            for selector in author_selectors:
                element = soup.select_one(selector)
                if element:
                    if element.name == 'meta':
                        metadata['author'] = element.get('content')
                    else:
                        metadata['author'] = element.get_text().strip()
                    break
            
            # Published date
            date_selectors = [
                'meta[property="article:published_time"]',
                'meta[name="pubdate"]',
                'time[datetime]',
                '.date'
            ]
            for selector in date_selectors:
                element = soup.select_one(selector)
                if element:
                    date_str = element.get('content') or element.get('datetime') or element.get_text()
                    if date_str:
                        try:
                            # Basic date parsing
                            from dateutil.parser import parse
                            metadata['published_date'] = parse(date_str)
                        except:
                            pass
                    break
            
            # Image
            image_selectors = [
                'meta[property="og:image"]',
                'meta[name="twitter:image"]',
                'img'
            ]
            for selector in image_selectors:
                element = soup.select_one(selector)
                if element:
                    image_url = element.get('content') or element.get('src')
                    if image_url:
                        metadata['image_url'] = urljoin(url, image_url)
                        break
            
            # Language
            html_lang = soup.find('html', lang=True)
            if html_lang:
                metadata['language'] = html_lang['lang']
                
        except Exception as e:
            logger.debug(f"Error extracting metadata: {e}")
        
        return metadata
    
    def _generate_summary(self, content: str, max_length: int = 300) -> str:
        """Generate a summary of the content"""
        if len(content) <= max_length:
            return content
        
        # Find sentence boundaries
        sentences = re.split(r'[.!?]+', content)
        summary = ""
        
        for sentence in sentences:
            if len(summary + sentence) <= max_length:
                summary += sentence + ". "
            else:
                break
        
        return summary.strip()
    
    def _estimate_reading_time(self, content: str) -> int:
        """Estimate reading time in minutes (average 200 words per minute)"""
        word_count = len(content.split())
        return max(1, word_count // 200)
    
    def _basic_keyword_extraction(self, text: str, max_keywords: int = 10) -> List[str]:
        """Basic keyword extraction without external libraries"""
        # Simple word frequency analysis
        words = re.findall(r'\b[a-zA-Z]{4,}\b', text.lower())
        
        # Common stop words to filter out
        stop_words = {
            'this', 'that', 'with', 'have', 'will', 'from', 'they', 'know',
            'want', 'been', 'good', 'much', 'some', 'time', 'very', 'when',
            'come', 'here', 'just', 'like', 'long', 'make', 'many', 'over',
            'such', 'take', 'than', 'them', 'well', 'were', 'what'
        }
        
        # Count word frequencies
        word_freq = {}
        for word in words:
            if word not in stop_words and len(word) > 3:
                word_freq[word] = word_freq.get(word, 0) + 1
        
        # Return top keywords
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return [word for word, freq in sorted_words[:max_keywords]]

# Global instance
_content_extractor = None

def get_content_extractor() -> ContentExtractor:
    """Get or create content extractor instance"""
    global _content_extractor
    if _content_extractor is None:
        _content_extractor = ContentExtractor()
    return _content_extractor

async def extract_content(url: str) -> Optional[Dict[str, Any]]:
    """Extract content from URL (compatibility function)"""
    try:
        extractor = get_content_extractor()
        result = await extractor.extract_from_url(url)
        
        if result:
            return {
                'title': result.title,
                'content': result.content,
                'summary': result.summary,
                'author': result.author,
                'published_date': result.published_date,
                'image_url': result.image_url,
                'keywords': result.keywords,
                'language': result.language,
                'reading_time': result.reading_time
            }
        return None
        
    except Exception as e:
        logger.error(f"Error extracting content from {url}: {e}")
        return None

def extract_keywords(text: str, max_keywords: int = 10) -> List[str]:
    """Extract keywords from text"""
    try:
        extractor = get_content_extractor()
        return extractor._basic_keyword_extraction(text, max_keywords)
    except Exception as e:
        logger.error(f"Error extracting keywords: {e}")
        return []