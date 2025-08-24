from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class ActionType(str, Enum):
    STAR = "star"
    UNSTAR = "unstar"
    MARK_READ = "mark_read"
    ARCHIVE = "archive"
    LABEL_ADD = "label_add"
    LABEL_REMOVE = "label_remove"

class DecideRequest(BaseModel):
    action: ActionType
    label: Optional[str] = None

class ArticleBase(BaseModel):
    title: str
    url: str
    content: Optional[str] = None
    source: str
    published_at: datetime
    content_hash: str
    score_total: int = 0
    scores: Dict[str, Any] = Field(default_factory=dict)
    entities: Dict[str, Any] = Field(default_factory=dict)
    topics: List[str] = Field(default_factory=list)
    flags: Dict[str, Any] = Field(default_factory=dict)
    
    # Image fields
    image_src_url: Optional[str] = None
    image_proxy_path: Optional[str] = None
    image_width: Optional[int] = None
    image_height: Optional[int] = None
    image_blurhash: Optional[str] = None
    has_image: bool = False
    
    # Content extraction fields
    extraction_status: Optional[str] = None
    extracted_at: Optional[datetime] = None
    extraction_error: Optional[str] = None
    full_content: Optional[str] = None
    content_summary: Optional[str] = None
    has_extracted_content: bool = False

class ArticleCreate(ArticleBase):
    freshrss_entry_id: str

class Article(ArticleBase):
    id: int
    freshrss_entry_id: str
    story_id: Optional[int] = None
    canonical_url: Optional[str] = None
    simhash: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class ArticleList(BaseModel):
    items: List[Article]
    total: int
    page: int
    page_size: int

class HealthResponse(BaseModel):
    status: str
    timestamp: datetime
    services: Dict[str, str]

class RefreshResponse(BaseModel):
    status: str
    new_entries: int
    scored: int
    timestamp: datetime

class ConfigResponse(BaseModel):
    scoring: Dict[str, Any]
    thresholds: Dict[str, int]
    sources: List[str]
    imageEnabled: bool = True
    imageProxyBase: str = "/img"


class StoryBase(BaseModel):
    canonical_title: str
    best_image: Optional[str] = None
    sources: List[Dict[str, Any]] = Field(default_factory=list)
    first_seen: datetime
    last_seen: datetime
    confidence: float = 1.0


class StoryResponse(StoryBase):
    id: int
    article_count: int
    articles: Optional[List[Article]] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class StoryList(BaseModel):
    items: List[StoryResponse]
    total: int
    page: int
    page_size: int


class ClusteringStats(BaseModel):
    total_articles: int
    clustered_articles: int
    unclustered_articles: int
    clustering_rate: float
    total_stories: int
    stories_created_today: int
    story_size_distribution: List[Dict[str, Any]]