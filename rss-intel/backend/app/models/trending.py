"""
Trending Analysis Database Models

Models for storing trending topics, topic analysis results, and viral content tracking.
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean, JSON, ARRAY
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from datetime import datetime
from typing import Dict, Any, List, Optional

from ..database import Base

class TrendingTopic(Base):
    """Trending topic detected by analysis"""
    __tablename__ = "trending_topics"
    
    id = Column(Integer, primary_key=True, index=True)
    topic_name = Column(String(200), nullable=False, index=True)
    topic_type = Column(String(50), nullable=False, index=True)  # 'keyword', 'emerging', 'hashtag'
    
    # Trend metrics
    trend_score = Column(Float, nullable=False, index=True)
    velocity = Column(Float, default=0.0, nullable=False)  # Rate of change
    article_count = Column(Integer, default=0, nullable=False)
    unique_sources = Column(Integer, default=0, nullable=False)
    engagement_score = Column(Float, default=0.0, nullable=False)
    
    # Content and keywords
    keywords = Column(JSONB, nullable=True)  # List of related keywords
    related_article_ids = Column(JSONB, nullable=True)  # List of article IDs
    
    # Trend analysis
    trend_direction = Column(String(20), nullable=False, index=True)  # 'rising', 'stable', 'declining'
    confidence = Column(Float, default=0.0, nullable=False)
    prediction_accuracy = Column(Float, nullable=True)  # Filled in retrospectively
    
    # Temporal data
    first_detected_at = Column(DateTime(timezone=True), nullable=False, index=True)
    peak_time = Column(DateTime(timezone=True), nullable=True)
    last_updated = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)  # When trend is expected to fade
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    is_viral = Column(Boolean, default=False, nullable=False, index=True)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    @property
    def age_hours(self) -> float:
        """Age of trend in hours"""
        return (datetime.now() - self.first_detected_at).total_seconds() / 3600
    
    @property
    def is_trending_up(self) -> bool:
        """Check if trend is currently rising"""
        return self.trend_direction == 'rising' and self.is_active
    
    @property
    def trend_strength(self) -> str:
        """Categorize trend strength"""
        if self.trend_score >= 0.8:
            return 'very_strong'
        elif self.trend_score >= 0.6:
            return 'strong'
        elif self.trend_score >= 0.4:
            return 'moderate'
        else:
            return 'weak'

class TopicCluster(Base):
    """Topic cluster from content analysis"""
    __tablename__ = "topic_clusters"
    
    id = Column(Integer, primary_key=True, index=True)
    cluster_name = Column(String(200), nullable=False)
    cluster_type = Column(String(50), nullable=False)  # 'lda', 'kmeans', 'manual'
    
    # Cluster characteristics
    keywords = Column(JSONB, nullable=False)  # Top keywords for cluster
    article_ids = Column(JSONB, nullable=False)  # Articles in cluster
    coherence_score = Column(Float, nullable=False)  # Quality of cluster
    size = Column(Integer, nullable=False)  # Number of articles
    
    # Temporal characteristics
    timespan_hours = Column(Float, default=0.0)  # Time span of articles in cluster
    first_article_at = Column(DateTime(timezone=True), nullable=True)
    last_article_at = Column(DateTime(timezone=True), nullable=True)
    
    # Geographic and source diversity
    geographic_spread = Column(JSONB, nullable=True)  # Countries/regions if detected
    source_diversity = Column(Float, default=0.0)  # Measure of source variety
    unique_sources = Column(Integer, default=0)
    
    # Analysis metadata
    analysis_method = Column(String(100), nullable=True)
    algorithm_version = Column(String(50), nullable=True)
    analysis_parameters = Column(JSONB, nullable=True)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    @property
    def cluster_quality(self) -> str:
        """Categorize cluster quality"""
        if self.coherence_score >= 0.8:
            return 'excellent'
        elif self.coherence_score >= 0.6:
            return 'good'
        elif self.coherence_score >= 0.4:
            return 'fair'
        else:
            return 'poor'
    
    @property
    def is_large_cluster(self) -> bool:
        """Check if this is a large, significant cluster"""
        return self.size >= 10 and self.coherence_score >= 0.5

class TopicAnalysis(Base):
    """Overall topic analysis session"""
    __tablename__ = "topic_analyses"
    
    id = Column(Integer, primary_key=True, index=True)
    analysis_type = Column(String(50), nullable=False, index=True)  # 'trending', 'clustering', 'comprehensive'
    
    # Analysis scope
    time_window_hours = Column(Integer, nullable=False)
    articles_analyzed = Column(Integer, default=0)
    sources_analyzed = Column(Integer, default=0)
    
    # Results summary
    topics_found = Column(Integer, default=0)
    clusters_found = Column(Integer, default=0)
    viral_articles = Column(Integer, default=0)
    emerging_topics = Column(Integer, default=0)
    
    # Quality metrics
    analysis_quality_score = Column(Float, default=0.0)
    confidence_level = Column(Float, default=0.0)
    
    # Detailed results
    analysis_metadata = Column(JSONB, nullable=True)  # Full analysis results and metadata
    trending_keywords = Column(JSONB, nullable=True)  # Top trending keywords found
    predictions = Column(JSONB, nullable=True)  # Trend predictions made
    
    # Performance metrics
    execution_time_seconds = Column(Float, nullable=True)
    memory_usage_mb = Column(Float, nullable=True)
    
    # Status
    status = Column(String(20), default='completed', nullable=False)  # 'running', 'completed', 'failed'
    error_message = Column(Text, nullable=True)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    @property
    def analysis_duration(self) -> Optional[float]:
        """Duration of analysis in seconds"""
        if self.completed_at:
            return (self.completed_at - self.created_at).total_seconds()
        return None
    
    @property
    def topics_per_hour(self) -> float:
        """Rate of topic discovery"""
        if self.time_window_hours > 0:
            return self.topics_found / self.time_window_hours
        return 0.0

class ViralContent(Base):
    """Viral content tracking"""
    __tablename__ = "viral_content"
    
    id = Column(Integer, primary_key=True, index=True)
    article_id = Column(Integer, nullable=False, index=True, unique=True)
    
    # Viral metrics
    viral_score = Column(Float, nullable=False, index=True)
    engagement_rate = Column(Float, default=0.0)
    share_velocity = Column(Float, default=0.0)  # Rate of sharing/engagement
    peak_engagement_time = Column(DateTime(timezone=True), nullable=True)
    
    # Viral characteristics
    viral_triggers = Column(JSONB, nullable=True)  # What made it viral
    viral_keywords = Column(JSONB, nullable=True)  # Keywords contributing to virality
    engagement_pattern = Column(String(50), nullable=True)  # 'explosive', 'gradual', 'sustained'
    
    # Geographic spread
    viral_regions = Column(JSONB, nullable=True)  # Regions where it went viral
    cross_platform = Column(Boolean, default=False)  # If viral across platforms
    
    # Detection details
    detected_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    detection_method = Column(String(100), nullable=True)
    confidence = Column(Float, default=0.0)
    
    # Tracking
    first_viral_indicator = Column(DateTime(timezone=True), nullable=True)
    viral_decay_started = Column(DateTime(timezone=True), nullable=True)
    is_still_viral = Column(Boolean, default=True, nullable=False)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    @property
    def viral_duration_hours(self) -> Optional[float]:
        """How long content has been viral"""
        if self.viral_decay_started:
            return (self.viral_decay_started - self.first_viral_indicator).total_seconds() / 3600
        elif self.first_viral_indicator:
            return (datetime.now() - self.first_viral_indicator).total_seconds() / 3600
        return None
    
    @property
    def viral_intensity(self) -> str:
        """Categorize viral intensity"""
        if self.viral_score >= 0.9:
            return 'explosive'
        elif self.viral_score >= 0.7:
            return 'high'
        elif self.viral_score >= 0.5:
            return 'moderate'
        else:
            return 'low'

class TrendPrediction(Base):
    """Trend predictions and their accuracy tracking"""
    __tablename__ = "trend_predictions"
    
    id = Column(Integer, primary_key=True, index=True)
    topic_name = Column(String(200), nullable=False, index=True)
    prediction_type = Column(String(50), nullable=False)  # 'emergence', 'growth', 'decline'
    
    # Prediction details
    predicted_score = Column(Float, nullable=False)
    confidence_level = Column(Float, nullable=False)
    prediction_horizon_hours = Column(Integer, nullable=False)  # How far ahead
    
    # Prediction basis
    based_on_articles = Column(Integer, default=0)
    based_on_sources = Column(Integer, default=0)
    algorithm_used = Column(String(100), nullable=True)
    input_features = Column(JSONB, nullable=True)
    
    # Actual outcomes (filled in later)
    actual_score = Column(Float, nullable=True)
    prediction_accuracy = Column(Float, nullable=True)  # 0-1 scale
    outcome_verified_at = Column(DateTime(timezone=True), nullable=True)
    
    # Status
    status = Column(String(20), default='active', nullable=False)  # 'active', 'verified', 'expired'
    notes = Column(Text, nullable=True)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    
    @property
    def is_expired(self) -> bool:
        """Check if prediction has expired"""
        return datetime.now() > self.expires_at
    
    @property
    def hours_remaining(self) -> float:
        """Hours until prediction expires"""
        if self.is_expired:
            return 0.0
        return (self.expires_at - datetime.now()).total_seconds() / 3600
    
    def verify_prediction(self, actual_score: float):
        """Verify prediction with actual outcome"""
        self.actual_score = actual_score
        
        # Calculate accuracy based on how close prediction was
        if self.predicted_score == 0:
            self.prediction_accuracy = 1.0 if actual_score == 0 else 0.0
        else:
            error = abs(actual_score - self.predicted_score) / self.predicted_score
            self.prediction_accuracy = max(0.0, 1.0 - error)
        
        self.outcome_verified_at = datetime.now()
        self.status = 'verified'