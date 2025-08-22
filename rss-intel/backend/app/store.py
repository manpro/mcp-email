from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, ARRAY, Index, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime
import hashlib

Base = declarative_base()

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
    score_total = Column(Integer, default=0, index=True)
    scores = Column(JSON, default={})
    entities = Column(JSON, default={})
    topics = Column(ARRAY(Text), default=[])
    flags = Column(JSON, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        Index('ix_article_score_published', 'score_total', 'published_at'),
    )

class Run(Base):
    __tablename__ = "runs"
    
    id = Column(Integer, primary_key=True, index=True)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    finished_at = Column(DateTime(timezone=True))
    new_entries = Column(Integer, default=0)
    scored = Column(Integer, default=0)
    errors = Column(JSON, default=[])

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
        page: int = 1,
        page_size: int = 50
    ) -> tuple[List[Article], int]:
        q = self.db.query(Article)
        
        if min_score is not None:
            q = q.filter(Article.score_total >= min_score)
        
        if label:
            q = q.filter(Article.flags.op('->>')(label).isnot(None))
        
        if source:
            q = q.filter(Article.source == source)
        
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