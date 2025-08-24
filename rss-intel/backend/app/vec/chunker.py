"""Text chunking for articles with overlap and language detection"""
import re
from typing import List, Dict, Any, Tuple
import logging
from dataclasses import dataclass
import tiktoken

logger = logging.getLogger(__name__)


@dataclass
class TextChunk:
    """Represents a text chunk with metadata"""
    text: str
    start_pos: int
    end_pos: int
    token_count: int
    chunk_index: int
    

class TextChunker:
    """Handles intelligent text chunking with overlap"""
    
    def __init__(
        self, 
        chunk_size: int = 800,
        overlap_size: int = 150,
        min_chunk_size: int = 100
    ):
        self.chunk_size = chunk_size
        self.overlap_size = overlap_size
        self.min_chunk_size = min_chunk_size
        
        # Initialize tokenizer for accurate token counting
        try:
            self.tokenizer = tiktoken.get_encoding("cl100k_base")  # GPT-4 tokenizer
        except Exception as e:
            logger.warning(f"Could not load tiktoken encoder: {e}")
            self.tokenizer = None
    
    def chunk_article(self, article_id: int, title: str, content: str) -> List[Dict[str, Any]]:
        """
        Chunk an article into overlapping segments
        
        Args:
            article_id: Database ID of article
            title: Article title
            content: Article content
            
        Returns:
            List of chunk dictionaries ready for embedding
        """
        if not content.strip():
            logger.warning(f"Empty content for article {article_id}")
            return []
        
        # Combine title and content
        full_text = f"{title}\n\n{content}" if title else content
        
        # Clean and normalize text
        full_text = self._clean_text(full_text)
        
        # Split into chunks
        chunks = self._split_text(full_text)
        
        # Convert to chunk dictionaries
        chunk_dicts = []
        for i, chunk in enumerate(chunks):
            chunk_dicts.append({
                'article_id': article_id,
                'chunk_ix': i,
                'text': chunk.text,
                'token_count': chunk.token_count,
                'start_pos': chunk.start_pos,
                'end_pos': chunk.end_pos
            })
        
        logger.info(f"Created {len(chunk_dicts)} chunks for article {article_id}")
        return chunk_dicts
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text content"""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove HTML entities that might have been missed
        text = re.sub(r'&[a-zA-Z0-9]+;', ' ', text)
        
        # Remove URLs (keep domain for context)
        text = re.sub(r'https?://[^\s]+', '[URL]', text)
        
        # Normalize quotes
        text = re.sub(r'[""]', '"', text)
        text = re.sub(r"['']", "'", text)
        
        # Remove excessive punctuation
        text = re.sub(r'[.]{3,}', '...', text)
        text = re.sub(r'[!]{2,}', '!', text)
        text = re.sub(r'[?]{2,}', '?', text)
        
        return text.strip()
    
    def _split_text(self, text: str) -> List[TextChunk]:
        """Split text into overlapping chunks"""
        if not text:
            return []
        
        chunks = []
        current_pos = 0
        chunk_index = 0
        
        while current_pos < len(text):
            # Determine chunk end position
            chunk_end = min(current_pos + self._estimate_char_length(self.chunk_size), len(text))
            
            # Find good break point (sentence or paragraph boundary)
            if chunk_end < len(text):
                chunk_end = self._find_break_point(text, chunk_end)
            
            # Extract chunk text
            chunk_text = text[current_pos:chunk_end].strip()
            
            # Skip if chunk is too small
            if len(chunk_text) < self.min_chunk_size and chunk_index > 0:
                break
            
            # Count tokens
            token_count = self._count_tokens(chunk_text)
            
            # Create chunk
            chunk = TextChunk(
                text=chunk_text,
                start_pos=current_pos,
                end_pos=chunk_end,
                token_count=token_count,
                chunk_index=chunk_index
            )
            chunks.append(chunk)
            
            # Calculate next position with overlap
            if chunk_end >= len(text):
                break
            
            overlap_chars = self._estimate_char_length(self.overlap_size)
            current_pos = max(current_pos + 1, chunk_end - overlap_chars)
            chunk_index += 1
        
        return chunks
    
    def _find_break_point(self, text: str, preferred_end: int) -> int:
        """Find good break point near preferred position"""
        # Look backwards for sentence end
        for i in range(preferred_end, max(0, preferred_end - 200), -1):
            if text[i] in '.!?':
                # Make sure it's not an abbreviation
                if i < len(text) - 1 and text[i + 1].isspace():
                    return i + 1
        
        # Look backwards for paragraph break
        for i in range(preferred_end, max(0, preferred_end - 200), -1):
            if text[i] == '\n':
                return i + 1
        
        # Look backwards for word boundary
        for i in range(preferred_end, max(0, preferred_end - 100), -1):
            if text[i].isspace():
                return i + 1
        
        # No good break found, use preferred end
        return preferred_end
    
    def _count_tokens(self, text: str) -> int:
        """Count tokens in text"""
        if self.tokenizer:
            try:
                return len(self.tokenizer.encode(text))
            except Exception as e:
                logger.debug(f"Tokenizer error: {e}")
        
        # Fallback: rough estimate
        return len(text.split()) * 1.3  # Average 1.3 tokens per word
    
    def _estimate_char_length(self, token_count: int) -> int:
        """Estimate character length for given token count"""
        # Rough estimate: 4 characters per token on average
        return int(token_count * 4)


def detect_language(text: str, title: str = "") -> str:
    """
    Simple language detection for articles
    
    Args:
        text: Article content
        title: Article title
        
    Returns:
        Language code ('en', 'sv', etc.)
    """
    # Combine title and beginning of content for analysis
    sample_text = (title + " " + text[:1000]).lower()
    
    # Swedish indicators
    swedish_words = [
        'och', 'att', 'är', 'med', 'för', 'på', 'av', 'en', 'som', 'till', 
        'från', 'det', 'har', 'kan', 'ska', 'kommer', 'blir', 'alla', 
        'eller', 'bara', 'efter', 'också', 'redan', 'inte', 'skulle', 'varit'
    ]
    
    # English indicators
    english_words = [
        'the', 'and', 'to', 'of', 'is', 'in', 'for', 'with', 'on', 'at', 
        'that', 'this', 'from', 'will', 'can', 'have', 'are', 'was', 'were',
        'been', 'has', 'had', 'would', 'could', 'should', 'about', 'also'
    ]
    
    # German indicators  
    german_words = [
        'der', 'die', 'und', 'ist', 'das', 'mit', 'für', 'auf', 'von',
        'ein', 'eine', 'sich', 'nicht', 'werden', 'haben', 'werden', 'dass'
    ]
    
    # French indicators
    french_words = [
        'le', 'de', 'et', 'dans', 'pour', 'avec', 'est', 'sur', 'par',
        'une', 'que', 'qui', 'pas', 'sont', 'tout', 'mais', 'cette'
    ]
    
    # Count occurrences
    swedish_count = sum(1 for word in swedish_words if word in sample_text)
    english_count = sum(1 for word in english_words if word in sample_text)
    german_count = sum(1 for word in german_words if word in sample_text)
    french_count = sum(1 for word in french_words if word in sample_text)
    
    # Find language with highest score
    language_scores = {
        'sv': swedish_count,
        'en': english_count,
        'de': german_count,
        'fr': french_count
    }
    
    detected_lang = max(language_scores, key=language_scores.get)
    
    # Require minimum confidence
    if language_scores[detected_lang] < 3:
        detected_lang = 'en'  # Default to English
    
    return detected_lang


def chunk_articles_batch(articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Batch process articles into chunks
    
    Args:
        articles: List of article dictionaries with keys: id, title, content
        
    Returns:
        List of chunk dictionaries ready for embedding
    """
    chunker = TextChunker()
    all_chunks = []
    
    for article in articles:
        try:
            article_chunks = chunker.chunk_article(
                article_id=article['id'],
                title=article.get('title', ''),
                content=article.get('content', '')
            )
            
            # Add additional metadata to chunks
            for chunk in article_chunks:
                chunk.update({
                    'title': article.get('title', ''),
                    'url': article.get('url', ''),
                    'source': article.get('source', ''),
                    'published_at': article.get('published_at'),
                    'score': article.get('score_total', 0),
                    'lang': article.get('lang') or detect_language(
                        article.get('content', ''), 
                        article.get('title', '')
                    ),
                    'near_dup_id': article.get('near_dup_id')
                })
            
            all_chunks.extend(article_chunks)
            
        except Exception as e:
            logger.error(f"Error chunking article {article.get('id', 'unknown')}: {e}")
            continue
    
    logger.info(f"Created {len(all_chunks)} total chunks from {len(articles)} articles")
    return all_chunks