from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, ARRAY, Index, func, Boolean, BigInteger, Float, ForeignKey, Date
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, relationship
from sqlalchemy.dialects.postgresql import JSONB
from typing import List, Optional, Dict, Any
from datetime import datetime
import hashlib

Base = declarative_base()

# Avoid circular imports by defining SpamReport here instead

class SpamReport(Base):
    """Spam detection reports for articles - matches existing database schema"""
    __tablename__ = 'spam_reports'

    id = Column(Integer, primary_key=True, index=True)
    article_id = Column(Integer, ForeignKey('articles.id', ondelete='CASCADE'), nullable=False, unique=True)
    reported_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    source = Column(String(50), nullable=False)  # Source of the spam report
    reason = Column(String(100), nullable=False)  # Reason for spam report
    report_count = Column(Integer, nullable=False)  # Number of reports
    metadata = Column(JSONB, nullable=True)  # Additional metadata
    
    # Relationship
    article = relationship("Article", back_populates="spam_reports")

class SpamDetectionStats(Base):
    """Daily statistics for spam detection performance"""
    __tablename__ = 'spam_detection_stats'

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False, unique=True, index=True)
    
    # Basic counts
    total_articles_checked = Column(Integer, nullable=False, default=0)
    spam_detected_count = Column(Integer, nullable=False, default=0)
    false_positives = Column(Integer, nullable=False, default=0)
    false_negatives = Column(Integer, nullable=False, default=0)
    
    # Quality metrics
    avg_spam_probability = Column(Float, nullable=True)
    avg_content_score = Column(Float, nullable=True)
    
    # Signal analysis
    signal_type_counts = Column(JSONB, nullable=True)  # Count of each signal type detected
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

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
    spam_reports = relationship("SpamReport", back_populates="article", cascade="all, delete-orphan")
    
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
    model_id = Column(Integer, ForeignKey('ml_models.id'), nullable=False, index=True)
    score = Column(Float, nullable=False)  # Predicted read probability
    features = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    article = relationship("Article")
    model = relationship("MLModel")


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
            # Create new
            article_data['content_hash'] = content_hash
            article = Article(**article_data)
            self.db.add(article)
        
        self.db.commit()
        self.db.refresh(article)
        return article
    
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
        q = self.db.query(Article)
        
        # Exclude spam-reported articles unless explicitly requested
        if not include_spam:
            q = q.outerjoin(SpamReport, Article.id == SpamReport.article_id)\
                 .filter(SpamReport.id.is_(None))
        
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