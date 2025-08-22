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

class ArticleCreate(ArticleBase):
    freshrss_entry_id: str

class Article(ArticleBase):
    id: int
    freshrss_entry_id: str
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