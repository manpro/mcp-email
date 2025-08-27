"""
Source Health Database Models

Models for tracking RSS feed and source health, including content extraction
success rates, blocking issues, and quality metrics.
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean, JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from datetime import datetime
from typing import Dict, Any, Optional

from ..store import Base

class SourceHealthReport(Base):
    """Health report for a content source"""
    __tablename__ = "source_health_reports"
    
    id = Column(Integer, primary_key=True, index=True)
    source_name = Column(String(500), nullable=False, index=True)
    analysis_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    analysis_period_days = Column(Integer, default=7, nullable=False)
    
    # Metrics
    total_articles = Column(Integer, default=0, nullable=False)
    successful_extractions = Column(Integer, default=0, nullable=False)
    failed_extractions = Column(Integer, default=0, nullable=False)
    cloudflare_blocks = Column(Integer, default=0, nullable=False)
    paywall_hits = Column(Integer, default=0, nullable=False)
    low_content_articles = Column(Integer, default=0, nullable=False)
    spam_articles = Column(Integer, default=0, nullable=False)
    
    # Calculated scores
    extraction_success_rate = Column(Float, default=0.0, nullable=False)
    content_quality_score = Column(Float, default=0.0, nullable=False)
    health_score = Column(Float, default=0.0, nullable=False)  # Overall health 0-1
    
    # Status and timing
    health_status = Column(String(50), nullable=False, index=True)  # healthy, degraded, unhealthy, failing
    last_successful_extraction = Column(DateTime(timezone=True), nullable=True)
    
    # Detailed data
    issues = Column(JSONB, nullable=True)  # List of detected issues
    health_metrics = Column(JSONB, nullable=True)  # Detailed metrics
    recommendations = Column(JSONB, nullable=True)  # Actionable recommendations
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    @property
    def is_healthy(self) -> bool:
        """Check if source is considered healthy"""
        return self.health_status == 'healthy'
    
    @property 
    def needs_attention(self) -> bool:
        """Check if source needs attention"""
        return self.health_status in ['unhealthy', 'failing']
    
    @property
    def critical_issues_count(self) -> int:
        """Count of critical issues"""
        if not self.issues:
            return 0
        return len([issue for issue in self.issues if issue.get('severity') == 'critical'])

class ContentExtractionResult(Base):
    """Individual content extraction attempt result"""
    __tablename__ = "content_extraction_results"
    
    id = Column(Integer, primary_key=True, index=True)
    article_id = Column(Integer, nullable=False, index=True)  # References articles.id
    extraction_attempt_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    
    # URLs and metadata
    original_url = Column(Text, nullable=False)
    final_url = Column(Text, nullable=True)  # After redirects
    source_name = Column(String(500), nullable=False, index=True)
    
    # Extraction results
    success = Column(Boolean, default=False, nullable=False, index=True)
    http_status_code = Column(Integer, nullable=True)
    response_time_ms = Column(Integer, nullable=True)
    content_length = Column(Integer, nullable=True)
    extracted_content_length = Column(Integer, nullable=True)
    
    # Failure analysis
    failure_reason = Column(String(100), nullable=True, index=True)  # cloudflare_block, paywall, timeout, etc.
    error_message = Column(Text, nullable=True)
    blocked_by = Column(String(100), nullable=True)  # cloudflare, bot_protection, paywall, etc.
    
    # Content quality
    content_quality_score = Column(Float, nullable=True)
    title_content_coherence = Column(Float, nullable=True)
    spam_probability = Column(Float, nullable=True)
    
    # Technical details
    user_agent_used = Column(String(500), nullable=True)
    proxy_used = Column(String(100), nullable=True)
    extraction_method = Column(String(50), nullable=True)  # readability, custom, feed_content
    
    # Response analysis
    response_headers = Column(JSONB, nullable=True)
    response_indicators = Column(JSONB, nullable=True)  # Detected patterns, blocks, etc.
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    @property
    def extraction_success_rate_contribution(self) -> float:
        """How this result contributes to overall success rate"""
        return 1.0 if self.success else 0.0
    
    @property
    def is_blocked(self) -> bool:
        """Check if extraction was blocked"""
        return self.failure_reason in ['cloudflare_block', 'bot_protection', 'rate_limit']
    
    @property
    def is_paywall(self) -> bool:
        """Check if hit paywall"""
        return self.failure_reason == 'paywall'

class SourceQualityMetrics(Base):
    """Aggregated quality metrics for sources over time"""
    __tablename__ = "source_quality_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    source_name = Column(String(500), nullable=False, index=True)
    metric_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    
    # Daily metrics
    articles_published = Column(Integer, default=0, nullable=False)
    articles_successfully_extracted = Column(Integer, default=0, nullable=False)
    articles_failed_extraction = Column(Integer, default=0, nullable=False)
    articles_marked_spam = Column(Integer, default=0, nullable=False)
    
    # Quality scores (daily averages)
    avg_content_quality = Column(Float, default=0.0, nullable=False)
    avg_title_coherence = Column(Float, default=0.0, nullable=False)
    avg_content_length = Column(Integer, default=0, nullable=False)
    avg_extraction_time_ms = Column(Integer, default=0, nullable=False)
    
    # Issue counts
    cloudflare_blocks_count = Column(Integer, default=0, nullable=False)
    paywall_hits_count = Column(Integer, default=0, nullable=False)
    timeout_errors_count = Column(Integer, default=0, nullable=False)
    
    # Calculated rates
    extraction_success_rate = Column(Float, default=0.0, nullable=False)
    content_quality_rate = Column(Float, default=0.0, nullable=False)  # % of articles with quality > 0.5
    spam_rate = Column(Float, default=0.0, nullable=False)
    
    # Trend indicators
    trend_direction = Column(String(20), nullable=True)  # improving, stable, declining
    trend_confidence = Column(Float, default=0.0, nullable=False)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    @property
    def overall_health_score(self) -> float:
        """Calculate overall health score"""
        extraction_weight = 0.4
        quality_weight = 0.3
        spam_weight = 0.3
        
        extraction_score = self.extraction_success_rate
        quality_score = self.content_quality_rate
        spam_score = 1.0 - self.spam_rate
        
        return (extraction_score * extraction_weight + 
                quality_score * quality_weight + 
                spam_score * spam_weight)
    
    @property
    def needs_monitoring(self) -> bool:
        """Check if source needs closer monitoring"""
        return (self.extraction_success_rate < 0.7 or 
                self.content_quality_rate < 0.5 or
                self.spam_rate > 0.3)

class SourceHealthAlert(Base):
    """Health alerts for sources that need attention"""
    __tablename__ = "source_health_alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    source_name = Column(String(500), nullable=False, index=True)
    alert_type = Column(String(100), nullable=False, index=True)  # extraction_failure, quality_drop, etc.
    severity = Column(String(20), nullable=False, index=True)  # low, medium, high, critical
    
    # Alert details
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    metric_value = Column(Float, nullable=True)
    threshold_value = Column(Float, nullable=True)
    
    # Status
    status = Column(String(20), default='active', nullable=False, index=True)  # active, acknowledged, resolved
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    
    # Actions and notes
    recommended_actions = Column(JSONB, nullable=True)
    admin_notes = Column(Text, nullable=True)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    @property
    def age_hours(self) -> float:
        """Age of alert in hours"""
        return (datetime.now() - self.created_at).total_seconds() / 3600
    
    @property
    def is_stale(self) -> bool:
        """Check if alert is stale (active for too long)"""
        return self.status == 'active' and self.age_hours > 48
    
    def acknowledge(self, admin_notes: str = None):
        """Acknowledge the alert"""
        self.status = 'acknowledged'
        self.acknowledged_at = datetime.now()
        if admin_notes:
            self.admin_notes = admin_notes
    
    def resolve(self, admin_notes: str = None):
        """Resolve the alert"""
        self.status = 'resolved'
        self.resolved_at = datetime.now()
        if admin_notes:
            self.admin_notes = admin_notes