"""
Search-related database models
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean, ARRAY
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from datetime import datetime
from typing import Dict, List, Any, Optional

from ..store import Base

class SavedSearch(Base):
    """Saved search configurations for users"""
    __tablename__ = "saved_searches"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(100), nullable=True, index=True)  # For future user system
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    search_query = Column(Text, nullable=True)
    search_filters = Column(JSONB, nullable=True)
    search_settings = Column(JSONB, nullable=True)
    usage_count = Column(Integer, default=0, nullable=False)
    last_used = Column(DateTime(timezone=True), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    @property
    def search_params_dict(self) -> Dict[str, Any]:
        """Get complete search parameters as dict"""
        return {
            "query": self.search_query or "",
            "filters": self.search_filters or {},
            "settings": self.search_settings or {}
        }
    
    def update_usage(self) -> None:
        """Update usage statistics"""
        self.usage_count += 1
        self.last_used = datetime.now()

class SearchAnalytics(Base):
    """Search analytics and performance tracking"""
    __tablename__ = "search_analytics"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(100), nullable=True, index=True)
    search_query = Column(Text, nullable=False, index=True)
    search_filters = Column(JSONB, nullable=True)
    search_type = Column(String(50), nullable=False, index=True)  # 'semantic', 'keyword', 'hybrid'
    result_count = Column(Integer, nullable=False, index=True)
    search_time_ms = Column(Float, nullable=False)
    page_requested = Column(Integer, default=1, nullable=False)
    results_clicked = Column(ARRAY(Integer), nullable=True)
    session_id = Column(String(100), nullable=True)
    user_agent = Column(String(500), nullable=True)
    ip_address = Column(String(45), nullable=True)
    referer = Column(String(500), nullable=True)
    search_timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    
    @property
    def click_through_rate(self) -> float:
        """Calculate click-through rate"""
        if not self.results_clicked or self.result_count == 0:
            return 0.0
        return len(self.results_clicked) / self.result_count

class SearchSuggestion(Base):
    """Search suggestions for auto-complete"""
    __tablename__ = "search_suggestions"
    
    id = Column(Integer, primary_key=True, index=True)
    suggestion_text = Column(String(500), nullable=False, unique=True)
    search_count = Column(Integer, default=1, nullable=False, index=True)
    last_searched = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    avg_result_count = Column(Float, default=0.0, nullable=False)
    category = Column(String(100), nullable=True, index=True)  # 'manual', 'trending', 'popular'
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    def update_stats(self, result_count: int) -> None:
        """Update suggestion statistics"""
        # Calculate new average
        total_results = (self.avg_result_count * self.search_count) + result_count
        self.search_count += 1
        self.avg_result_count = total_results / self.search_count
        self.last_searched = datetime.now()
    
    @property
    def is_trending(self) -> bool:
        """Check if suggestion is trending (searched recently with good results)"""
        if not self.last_searched:
            return False
        
        days_since_search = (datetime.now() - self.last_searched).days
        return (days_since_search <= 7 and 
                self.search_count >= 5 and 
                self.avg_result_count >= 10)