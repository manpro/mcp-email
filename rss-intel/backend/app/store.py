from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, ARRAY, Index, func, Boolean, BigInteger, Float, ForeignKey, Date, and_, or_
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, relationship
from sqlalchemy.dialects.postgresql import JSONB
from typing import List, Optional, Dict, Any
from datetime import datetime
import hashlib
import logging

logger = logging.getLogger(__name__)

Base = declarative_base()

# Spam detection temporarily disabled to resolve SQLAlchemy relationship conflicts

class Story(Base):
    __tablename__ = "stories"
    
    id = Column(Integer, primary_key=True, index=True)
    canonical_title = Column(Text, nullable=False)
    best_image = Column(Text, nullable=True)
    sources = Column(JSONB, default=[], nullable=True)
    first_seen = Column(DateTime(timezone=True), nullable=False, index=True)
    last_seen = Column(DateTime(timezone=True), nullable=False, index=True)
    confidence = Column(Float, default=1.0, nullable=False, index=True)
    stance = Column(ARRAY(Text), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationship
    articles = relationship("Article", back_populates="story")


class Article(Base):
    __tablename__ = "articles"
    
    id = Column(Integer, primary_key=True, index=True)
    freshrss_entry_id = Column(String, unique=True, index=True, nullable=False)
    title = Column(Text, nullable=False)
    url = Column(Text, nullable=False)
    content = Column(Text, nullable=True)  # Article content/summary
    source = Column(String, nullable=False)
    published_at = Column(DateTime(timezone=True), nullable=False, index=True)
    content_hash = Column(String, index=True, nullable=False)
    content_type = Column(String(20), default='article', nullable=False, index=True)  # 'article' or 'event'
    score_total = Column(Integer, default=0, index=True)
    scores = Column(JSON, default={})
    entities = Column(JSON, default={})
    topics = Column(ARRAY(Text), default=[])
    flags = Column(JSON, default={})
    
    # Image fields
    image_src_url = Column(Text, nullable=True)
    image_proxy_path = Column(Text, unique=True, nullable=True)
    image_width = Column(Integer, nullable=True)
    image_height = Column(Integer, nullable=True)
    image_blurhash = Column(String(120), nullable=True)
    has_image = Column(Boolean, default=False, index=True)
    image_stage = Column(String(50), nullable=True)  # Stage where image was found (enclosure, og, etc.)
    image_reason = Column(String(200), nullable=True)  # Reason for image status
    
    # Content extraction fields
    full_content = Column(Text, nullable=True)
    content_html = Column(Text, nullable=True)
    extracted_at = Column(DateTime(timezone=True), nullable=True)
    extraction_status = Column(String(20), default='pending', index=True)
    extraction_error = Column(Text, nullable=True)
    content_keywords = Column(ARRAY(String), nullable=True)
    content_summary = Column(Text, nullable=True)
    authors = Column(ARRAY(String), nullable=True)
    top_image_url = Column(Text, nullable=True)
    robots_txt_checked = Column(Boolean, default=False)
    
    # Story clustering fields
    story_id = Column(Integer, ForeignKey('stories.id'), nullable=True, index=True)
    canonical_url = Column(Text, nullable=True, index=True)
    content_hash = Column(String(40), nullable=True, index=True)
    simhash = Column(BigInteger, nullable=True, index=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    story = relationship("Story", back_populates="articles")
    # spam_reports relationship temporarily disabled
    
    __table_args__ = (
        Index('ix_article_score_published', 'score_total', 'published_at'),
        Index('ix_article_has_image_score', 'has_image', 'score_total', 'published_at'),
    )

class Run(Base):
    __tablename__ = "runs"
    
    id = Column(Integer, primary_key=True, index=True)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    finished_at = Column(DateTime(timezone=True))
    new_entries = Column(Integer, default=0)
    scored = Column(Integer, default=0)
    errors = Column(JSON, default=[])

class Event(Base):
    __tablename__ = "events"
    
    id = Column(Integer, primary_key=True, index=True)
    article_id = Column(Integer, ForeignKey('articles.id'), nullable=False, index=True)
    event_type = Column(String(50), nullable=False, index=True)  # impression, open, external_click, star, dismiss, mark_read, label_add
    duration_ms = Column(Integer, nullable=True)  # Time spent viewing
    visible_ms = Column(Integer, nullable=True)   # Time article was visible on screen
    scroll_pct = Column(Float, nullable=True)     # Percentage scrolled
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Relationship
    article = relationship("Article")


class ArticleVector(Base):
    __tablename__ = "article_vectors"
    
    id = Column(Integer, primary_key=True, index=True)
    article_id = Column(Integer, ForeignKey('articles.id'), nullable=False, index=True)
    embedding = Column(ARRAY(Float), nullable=True)
    title_len = Column(Integer, nullable=True)
    has_image = Column(Boolean, nullable=True)
    source_hash = Column(String(32), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationship
    article = relationship("Article")


class MLModel(Base):
    __tablename__ = "ml_models"
    
    id = Column(Integer, primary_key=True, index=True)
    model_type = Column(String(50), nullable=False, index=True)  # 'personalization', 'scoring', etc.
    version = Column(String(20), nullable=False)
    params = Column(JSONB, nullable=True)
    metrics = Column(JSONB, nullable=True)
    model_path = Column(Text, nullable=True)
    is_active = Column(Boolean, default=False, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Prediction(Base):
    __tablename__ = "predictions"
    
    id = Column(Integer, primary_key=True, index=True)
    article_id = Column(Integer, ForeignKey('articles.id'), nullable=False, index=True)
    model_id = Column(Integer, nullable=False, index=True)  # No FK constraint to ml_models
    p_read = Column(Float, nullable=False)  # Predicted read probability
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    article = relationship("Article")


class SpotlightIssue(Base):
    __tablename__ = "spotlight_issues"
    
    id = Column(Integer, primary_key=True, index=True)
    issue_date = Column(DateTime(timezone=True), nullable=False, unique=True, index=True)
    title = Column(String(200), nullable=False)
    subtitle = Column(String(500), nullable=True)
    generated_at = Column(DateTime(timezone=True), nullable=False)
    published = Column(Boolean, default=False, nullable=False, index=True)
    metrics = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationship
    items = relationship("SpotlightItem", back_populates="issue", cascade="all, delete-orphan")


class SpotlightItem(Base):
    __tablename__ = "spotlight_items"
    
    id = Column(Integer, primary_key=True, index=True)
    issue_id = Column(Integer, ForeignKey('spotlight_issues.id'), nullable=False, index=True)
    story_id = Column(Integer, ForeignKey('stories.id'), nullable=True)
    article_id = Column(Integer, ForeignKey('articles.id'), nullable=False)
    section = Column(String(50), nullable=False, index=True)  # 'must_read' or 'also_worth'
    position = Column(Integer, nullable=False)
    summary = Column(Text, nullable=True)
    summary_language = Column(String(10), default='en', nullable=False)
    recommendation_score = Column(Float, nullable=True)
    recommendation_reasons = Column(ARRAY(String), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    issue = relationship("SpotlightIssue", back_populates="items")
    story = relationship("Story")
    article = relationship("Article")


class SpotlightConfig(Base):
    __tablename__ = "spotlight_config"
    
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), nullable=False, unique=True)
    value = Column(JSONB, nullable=True)
    description = Column(Text, nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ImageDiagnostic(Base):
    __tablename__ = "image_diagnostics"
    
    id = Column(Integer, primary_key=True, index=True)
    article_id = Column(Integer, ForeignKey('articles.id'), nullable=False, index=True)
    domain = Column(String(255), nullable=False, index=True)
    stage = Column(String(50), nullable=False)
    reason = Column(String(200), nullable=False)
    http_status = Column(Integer, nullable=True)
    bytes = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Relationship
    article = relationship("Article")



class ArticleStore:
    def __init__(self, db: Session):
        self.db = db
    
    def upsert_article(self, article_data: Dict[str, Any]) -> Article:
        # Generate content hash
        content_hash = hashlib.sha1(
            f"{article_data['title']}{article_data['url']}".encode()
        ).hexdigest()
        
        article = self.db.query(Article).filter_by(
            freshrss_entry_id=article_data['freshrss_entry_id']
        ).first()
        
        if article:
            # Update existing
            for key, value in article_data.items():
                setattr(article, key, value)
            article.content_hash = content_hash
            article.updated_at = datetime.utcnow()
        else:
            # Create new - apply initial classification
            article_data['content_hash'] = content_hash
            article_data = self._apply_initial_classification(article_data)
            article = Article(**article_data)
            self.db.add(article)
        
        self.db.commit()
        self.db.refresh(article)
        return article
    
    def _apply_initial_classification(self, article_data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply initial spam/promotional classification when article is first ingested"""
        import re
        from datetime import datetime, timezone
        
        title = article_data.get('title', '').lower()
        url = article_data.get('url', '').lower()
        source = article_data.get('source', '').lower()
        content = article_data.get('content', '').lower()
        published_at = article_data.get('published_at')
        
        # Initialize flags if not present
        if 'flags' not in article_data:
            article_data['flags'] = {}
        
        # 1. Promotional domain detection
        promotional_domains = [
            'tradingview.com/chart/',
            'finextra.com/event-info/',
            '/press-releases/',
            '/webinar',
            '/events/'
        ]
        
        is_promotional_url = any(domain in url for domain in promotional_domains)
        
        # 2. Promotional source detection
        promotional_sources = [
            'tradingview ideas',
            'pr newswire',
            'business wire',
            'marketwatch press release'
        ]
        
        is_promotional_source = any(src in source for src in promotional_sources)
        
        # 3. Future event detection
        is_future_event = False
        if published_at and isinstance(published_at, datetime):
            now = datetime.now(timezone.utc)
            if published_at > now:
                is_future_event = True
        
        # 4. Event keyword detection in title/content
        event_keywords = [
            'webinar', 'register', 'sign up', 'join our', 'panel of experts',
            'hosted in association', 'event', 'conference', 'summit',
            'register for this', 'join this', 'attend', 'speakers include',
            'press release', 'announces', 'partnership with'
        ]
        
        full_text = f"{title} {content}"
        event_keyword_matches = sum(1 for keyword in event_keywords if keyword in full_text)
        has_event_keywords = event_keyword_matches >= 2
        
        # 5. Future date patterns in title (september, october, etc.)
        future_date_patterns = [
            r'\b(september|october|november|december)\b',
            r'\b202[5-9]\b',  # Years 2025-2029
            r'\b20[3-9][0-9]\b'  # Years 2030+
        ]
        
        has_future_dates = any(re.search(pattern, title) for pattern in future_date_patterns)
        
        # Apply classification
        spam_score = 0
        spam_reasons = []
        
        if is_promotional_url:
            spam_score -= 999
            spam_reasons.append("promotional_domain")
            
        if is_promotional_source:
            spam_score -= 999 
            spam_reasons.append("promotional_source")
            
        if is_future_event:
            spam_score -= 999
            spam_reasons.append("future_event")
            
        if has_event_keywords and (is_promotional_url or is_promotional_source):
            spam_score -= 500
            spam_reasons.append("promotional_event_content")
            
        if has_future_dates:
            spam_score -= 999
            spam_reasons.append("future_date_in_title")
        
        # Apply spam classification
        if spam_score < 0:
            article_data['score_total'] = spam_score
            article_data['flags']['spam'] = True
            article_data['flags']['spam_reasons'] = spam_reasons
            article_data['flags']['auto_classified'] = True
            article_data['flags']['classification_time'] = datetime.now(timezone.utc).isoformat()
            
            logger.info(f"Auto-classified article as spam: '{article_data.get('title')}' - Reasons: {spam_reasons}, Score: {spam_score}")
        
        return article_data
    
    def get_articles(
        self,
        min_score: Optional[int] = None,
        label: Optional[str] = None,
        source: Optional[str] = None,
        query: Optional[str] = None,
        has_image: Optional[bool] = None,
        page: int = 1,
        page_size: int = 50,
        include_spam: bool = False
    ) -> tuple[List[Article], int]:
        logger.warning(f"DEBUG: get_articles called with include_spam={include_spam}")
        q = self.db.query(Article)
        
        # Spam filtering based on score_total and flags
        if not include_spam:
            logger.warning(f"DEBUG: Applying spam filter - excluding articles with score < 0")
            q = q.filter(Article.score_total >= 0)  # Filter out articles with negative spam scores
        
        if min_score is not None:
            q = q.filter(Article.score_total >= min_score)
        
        if label:
            q = q.filter(Article.flags.op('->>')(label).isnot(None))
        
        if source:
            q = q.filter(Article.source == source)
        
        if has_image is not None:
            q = q.filter(Article.has_image == has_image)
        
        if query:
            search_term = f"%{query}%"
            q = q.filter(
                Article.title.ilike(search_term) |
                Article.url.ilike(search_term) |
                Article.source.ilike(search_term)
            )
        
        total = q.count()
        
        articles = q.order_by(Article.published_at.desc())\
            .offset((page - 1) * page_size)\
            .limit(page_size)\
            .all()
        
        return articles, total
    
    def get_article_by_entry_id(self, entry_id: str) -> Optional[Article]:
        return self.db.query(Article).filter_by(freshrss_entry_id=entry_id).first()
    
    def get_unique_sources(self) -> List[str]:
        return [row[0] for row in self.db.query(Article.source).distinct().all()]
    
    def check_duplicate(self, content_hash: str) -> bool:
        return self.db.query(Article).filter_by(content_hash=content_hash).first() is not None
    
    def create_run(self) -> Run:
        run = Run()
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        return run
    
    def finish_run(self, run_id: int, new_entries: int, scored: int, errors: List[str] = None):
        run = self.db.query(Run).filter_by(id=run_id).first()
        if run:
            run.finished_at = datetime.utcnow()
            run.new_entries = new_entries
            run.scored = scored
            run.errors = errors or []
            self.db.commit()