"""
Spam Detection Database Models
"""

from sqlalchemy import Column, Integer, String, Float, Boolean, Text, DateTime, Date, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
from typing import Optional, Dict, List, Any

from ..store import Base


class SpamReport(Base):
    """
    Spam detection reports for articles
    """
    __tablename__ = 'spam_reports'

    id = Column(Integer, primary_key=True, index=True)
    article_id = Column(Integer, ForeignKey('articles.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Detection results
    report_type = Column(String(50), nullable=False, index=True)  # 'auto_detected', 'user_reported', 'manual_review'
    spam_probability = Column(Float, nullable=False, index=True)
    content_score = Column(Float, nullable=False)
    title_coherence = Column(Float, nullable=False)
    recommendation = Column(String(20), nullable=False, index=True)  # 'accept', 'review', 'reject'
    
    # Detailed analysis
    spam_signals = Column(JSONB, nullable=True)  # List of detected spam signals
    quality_issues = Column(JSONB, nullable=True)  # List of quality issues
    detection_summary = Column(Text, nullable=True)
    
    # Review tracking
    reported_by = Column(String(100), nullable=True)  # 'system' or user ID
    reviewed_by = Column(String(100), nullable=True)
    review_status = Column(String(20), nullable=True, index=True)  # 'pending', 'confirmed', 'false_positive'
    review_notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationship
    article = relationship("Article", back_populates="spam_reports")
    
    def __repr__(self):
        return f"<SpamReport(id={self.id}, article_id={self.article_id}, recommendation='{self.recommendation}')>"
    
    @property
    def is_spam(self) -> bool:
        """Check if this report indicates spam"""
        return self.spam_probability > 0.7 or self.recommendation == 'reject'
    
    @property
    def signal_types(self) -> List[str]:
        """Get list of detected signal types"""
        if not self.spam_signals:
            return []
        return [signal.get('type', 'unknown') for signal in self.spam_signals]
    
    @property
    def high_confidence_signals(self) -> List[Dict]:
        """Get signals with high confidence (>0.7)"""
        if not self.spam_signals:
            return []
        return [signal for signal in self.spam_signals if signal.get('confidence', 0) > 0.7]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'article_id': self.article_id,
            'report_type': self.report_type,
            'spam_probability': self.spam_probability,
            'content_score': self.content_score,
            'title_coherence': self.title_coherence,
            'recommendation': self.recommendation,
            'spam_signals': self.spam_signals,
            'quality_issues': self.quality_issues,
            'detection_summary': self.detection_summary,
            'reported_by': self.reported_by,
            'reviewed_by': self.reviewed_by,
            'review_status': self.review_status,
            'review_notes': self.review_notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_spam': self.is_spam,
            'signal_types': self.signal_types
        }


class SpamDetectionStats(Base):
    """
    Daily statistics for spam detection performance
    """
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
    
    def __repr__(self):
        return f"<SpamDetectionStats(date={self.date}, spam_rate={self.spam_rate:.2%})>"
    
    @property
    def spam_rate(self) -> float:
        """Calculate spam detection rate"""
        if self.total_articles_checked == 0:
            return 0.0
        return self.spam_detected_count / self.total_articles_checked
    
    @property
    def precision(self) -> Optional[float]:
        """Calculate precision (true positives / (true positives + false positives))"""
        if self.spam_detected_count == 0:
            return None
        true_positives = self.spam_detected_count - self.false_positives
        return true_positives / self.spam_detected_count if self.spam_detected_count > 0 else 0.0
    
    @property
    def accuracy_metrics(self) -> Dict[str, Optional[float]]:
        """Get accuracy metrics"""
        return {
            'spam_rate': self.spam_rate,
            'precision': self.precision,
            'false_positive_rate': self.false_positives / self.spam_detected_count if self.spam_detected_count > 0 else 0.0,
            'articles_per_day': self.total_articles_checked
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'date': self.date.isoformat() if self.date else None,
            'total_articles_checked': self.total_articles_checked,
            'spam_detected_count': self.spam_detected_count,
            'false_positives': self.false_positives,
            'false_negatives': self.false_negatives,
            'avg_spam_probability': self.avg_spam_probability,
            'avg_content_score': self.avg_content_score,
            'signal_type_counts': self.signal_type_counts,
            'spam_rate': self.spam_rate,
            'precision': self.precision,
            'accuracy_metrics': self.accuracy_metrics,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


# Add spam reports relationship to Article model
def add_spam_relationship_to_article():
    """
    This function should be called after Article model is imported
    to add the spam_reports relationship
    """
    from ..store import Article
    if not hasattr(Article, 'spam_reports'):
        Article.spam_reports = relationship("SpamReport", back_populates="article", cascade="all, delete-orphan")
        
        # Add spam detection columns if not already present
        if not hasattr(Article, 'spam_detected'):
            Article.spam_detected = Column(Boolean, default=False, nullable=False, index=True)
            Article.spam_probability = Column(Float, nullable=True, index=True)
            Article.content_quality_score = Column(Float, nullable=True, index=True)
            Article.title_coherence_score = Column(Float, nullable=True)
            Article.spam_signals = Column(JSONB, nullable=True)
            Article.last_spam_check = Column(DateTime(timezone=True), nullable=True, index=True)