"""Base adapter interface and common utilities for ingest sources"""
import hashlib
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class RawItem:
    """Raw item before normalization"""
    title: str
    url: str
    content: str
    published_at: Optional[datetime] = None
    source: str = ""
    image_url: Optional[str] = None
    author: Optional[str] = None
    lang: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass  
class NormalizedItem:
    """Normalized item ready for storage"""
    title: str
    url: str
    content: str
    published_at: datetime
    source: str
    image_url: Optional[str] = None
    author: Optional[str] = None
    lang: Optional[str] = None
    url_hash: str = ""
    content_hash: str = ""
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if not self.url_hash:
            self.url_hash = hashlib.md5(self.url.encode('utf-8')).hexdigest()
        if not self.content_hash:
            # Simple content fingerprint for dedup
            content_clean = self.title + " " + self.content[:1000]
            self.content_hash = hashlib.md5(content_clean.encode('utf-8')).hexdigest()


class BaseAdapter(ABC):
    """Base class for all ingest adapters"""
    
    def __init__(self, source_config: Dict[str, Any]):
        self.config = source_config
        self.source_name = source_config.get('name', 'Unknown')
    
    @abstractmethod
    async def fetch_new(self) -> List[RawItem]:
        """Fetch new items from the source"""
        pass
    
    def normalize_item(self, raw: RawItem) -> NormalizedItem:
        """Normalize a raw item"""
        # Default published_at if not set
        published_at = raw.published_at or datetime.now(timezone.utc)
        
        # Clean content
        content = self._clean_content(raw.content)
        
        # Detect language if not set
        lang = raw.lang or self._detect_language(raw.title, content)
        
        return NormalizedItem(
            title=raw.title.strip(),
            url=raw.url.strip(),
            content=content,
            published_at=published_at,
            source=raw.source or self.source_name,
            image_url=raw.image_url,
            author=raw.author,
            lang=lang,
            metadata=raw.metadata
        )
    
    def _clean_content(self, content: str) -> str:
        """Clean HTML and normalize content"""
        if not content:
            return ""
        
        # Basic HTML stripping - can be enhanced
        import re
        content = re.sub(r'<[^>]+>', '', content)
        content = re.sub(r'\s+', ' ', content)
        return content.strip()
    
    def _detect_language(self, title: str, content: str) -> str:
        """Simple language detection"""
        # Basic heuristic - can be enhanced with proper language detection
        text = (title + " " + content[:500]).lower()
        
        # Swedish indicators
        swedish_words = ['och', 'att', 'är', 'med', 'för', 'på', 'av', 'en', 'som', 'till', 'från', 'det', 'har', 'kan', 'ska', 'kommer']
        swedish_count = sum(1 for word in swedish_words if word in text)
        
        # English indicators  
        english_words = ['the', 'and', 'to', 'of', 'is', 'in', 'for', 'with', 'on', 'at', 'that', 'this', 'from', 'will', 'can']
        english_count = sum(1 for word in english_words if word in text)
        
        if swedish_count > english_count:
            return 'sv'
        elif english_count > 0:
            return 'en'
        else:
            return 'en'  # default


class AdapterFactory:
    """Factory to create adapters based on source type"""
    
    _adapters = {}
    
    @classmethod
    def register(cls, source_type: str, adapter_class):
        """Register an adapter class for a source type"""
        cls._adapters[source_type] = adapter_class
    
    @classmethod
    def create(cls, source_type: str, config: Dict[str, Any]) -> BaseAdapter:
        """Create an adapter instance"""
        if source_type not in cls._adapters:
            raise ValueError(f"Unknown source type: {source_type}")
        
        return cls._adapters[source_type](config)
    
    @classmethod
    def get_supported_types(cls) -> List[str]:
        """Get list of supported source types"""
        return list(cls._adapters.keys())