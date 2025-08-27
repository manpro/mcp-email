"""
Search Analytics Service

Provides comprehensive search analytics, performance monitoring, and insights
for the RSS Intelligence advanced search system.
"""

import logging
from typing import Dict, List, Optional, Tuple, Any, Union
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc, asc, text
from sqlalchemy.dialects.postgresql import ARRAY
import json
from collections import defaultdict, Counter
from dataclasses import dataclass

from ..models.search import SearchAnalytics, SearchSuggestion, SavedSearch
from ..store import Article

logger = logging.getLogger(__name__)

@dataclass
class SearchPerformanceMetrics:
    """Search performance metrics"""
    avg_search_time_ms: float
    total_searches: int
    avg_results_per_search: float
    search_success_rate: float  # Searches with > 0 results
    avg_click_through_rate: float
    most_popular_queries: List[Tuple[str, int]]
    search_types_distribution: Dict[str, int]
    performance_by_hour: Dict[int, float]  # Hour -> avg search time
    zero_result_queries: List[str]

@dataclass
class SearchInsight:
    """A search insight or recommendation"""
    insight_type: str  # 'performance', 'content', 'user_behavior'
    title: str
    description: str
    metric_value: Union[float, int, str]
    recommendation: str
    priority: str  # 'low', 'medium', 'high', 'critical'

class SearchAnalyticsService:
    """Service for search analytics and performance monitoring"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def log_search(self,
                  query: str,
                  search_filters: Dict[str, Any],
                  search_type: str,
                  result_count: int,
                  search_time_ms: float,
                  page: int = 1,
                  user_id: str = None,
                  session_id: str = None,
                  user_agent: str = None,
                  ip_address: str = None,
                  referer: str = None) -> SearchAnalytics:
        """
        Log a search event for analytics
        
        Args:
            query: Search query string
            search_filters: Applied search filters
            search_type: Type of search ('semantic', 'keyword', 'hybrid')
            result_count: Number of results returned
            search_time_ms: Time taken for search in milliseconds
            page: Page number requested
            user_id: Optional user identifier
            session_id: Optional session identifier
            user_agent: Optional user agent string
            ip_address: Optional IP address
            referer: Optional referer URL
            
        Returns:
            SearchAnalytics: Created analytics record
        """
        try:
            analytics = SearchAnalytics(
                user_id=user_id,
                search_query=query,
                search_filters=search_filters,
                search_type=search_type,
                result_count=result_count,
                search_time_ms=search_time_ms,
                page_requested=page,
                session_id=session_id,
                user_agent=user_agent,
                ip_address=ip_address,
                referer=referer
            )
            
            self.db.add(analytics)
            self.db.commit()
            
            # Update search suggestions
            self._update_search_suggestions(query, result_count)
            
            logger.info(f"Logged search: '{query}' -> {result_count} results in {search_time_ms:.1f}ms")
            return analytics
            
        except Exception as e:
            logger.error(f"Failed to log search analytics: {e}")
            self.db.rollback()
            raise

    def log_click_through(self, search_id: int, clicked_article_ids: List[int]) -> bool:
        """
        Log click-through events for a search
        
        Args:
            search_id: ID of the search analytics record
            clicked_article_ids: List of article IDs that were clicked
            
        Returns:
            bool: True if successfully logged
        """
        try:
            analytics = self.db.query(SearchAnalytics).filter(
                SearchAnalytics.id == search_id
            ).first()
            
            if analytics:
                # Merge with existing clicks
                existing_clicks = analytics.results_clicked or []
                all_clicks = list(set(existing_clicks + clicked_article_ids))
                analytics.results_clicked = all_clicks
                
                self.db.commit()
                logger.info(f"Updated click-through for search {search_id}: {len(clicked_article_ids)} new clicks")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to log click-through: {e}")
            self.db.rollback()
            return False

    def get_search_performance_metrics(self,
                                     days: int = 30,
                                     user_id: str = None) -> SearchPerformanceMetrics:
        """
        Get comprehensive search performance metrics
        
        Args:
            days: Number of days to analyze
            user_id: Optional user ID to filter by
            
        Returns:
            SearchPerformanceMetrics: Performance metrics
        """
        try:
            since_date = datetime.now() - timedelta(days=days)
            
            # Base query
            query = self.db.query(SearchAnalytics).filter(
                SearchAnalytics.search_timestamp >= since_date
            )
            
            if user_id:
                query = query.filter(SearchAnalytics.user_id == user_id)
            
            all_searches = query.all()
            
            if not all_searches:
                return SearchPerformanceMetrics(
                    avg_search_time_ms=0.0,
                    total_searches=0,
                    avg_results_per_search=0.0,
                    search_success_rate=0.0,
                    avg_click_through_rate=0.0,
                    most_popular_queries=[],
                    search_types_distribution={},
                    performance_by_hour={},
                    zero_result_queries=[]
                )
            
            # Calculate metrics
            total_searches = len(all_searches)
            avg_search_time = sum(s.search_time_ms for s in all_searches) / total_searches
            avg_results = sum(s.result_count for s in all_searches) / total_searches
            
            # Success rate (searches with results)
            successful_searches = len([s for s in all_searches if s.result_count > 0])
            success_rate = successful_searches / total_searches if total_searches > 0 else 0.0
            
            # Click-through rate
            searches_with_clicks = [s for s in all_searches if s.results_clicked]
            avg_ctr = sum(s.click_through_rate for s in searches_with_clicks) / len(searches_with_clicks) if searches_with_clicks else 0.0
            
            # Popular queries
            query_counts = Counter(s.search_query for s in all_searches if s.search_query.strip())
            popular_queries = query_counts.most_common(10)
            
            # Search types distribution
            type_counts = Counter(s.search_type for s in all_searches)
            types_distribution = dict(type_counts)
            
            # Performance by hour
            hourly_performance = defaultdict(list)
            for search in all_searches:
                hour = search.search_timestamp.hour
                hourly_performance[hour].append(search.search_time_ms)
            
            performance_by_hour = {
                hour: sum(times) / len(times) 
                for hour, times in hourly_performance.items()
            }
            
            # Zero result queries
            zero_result_queries = list(set(
                s.search_query for s in all_searches 
                if s.result_count == 0 and s.search_query.strip()
            ))[:20]  # Limit to 20
            
            return SearchPerformanceMetrics(
                avg_search_time_ms=avg_search_time,
                total_searches=total_searches,
                avg_results_per_search=avg_results,
                search_success_rate=success_rate,
                avg_click_through_rate=avg_ctr,
                most_popular_queries=popular_queries,
                search_types_distribution=types_distribution,
                performance_by_hour=performance_by_hour,
                zero_result_queries=zero_result_queries
            )
            
        except Exception as e:
            logger.error(f"Failed to get search performance metrics: {e}")
            raise

    def get_search_insights(self, days: int = 30) -> List[SearchInsight]:
        """
        Generate actionable search insights and recommendations
        
        Args:
            days: Number of days to analyze
            
        Returns:
            List of search insights
        """
        insights = []
        
        try:
            metrics = self.get_search_performance_metrics(days)
            
            # Performance insights
            if metrics.avg_search_time_ms > 1000:  # > 1 second
                insights.append(SearchInsight(
                    insight_type='performance',
                    title='Slow Search Performance',
                    description=f'Average search time is {metrics.avg_search_time_ms:.0f}ms',
                    metric_value=metrics.avg_search_time_ms,
                    recommendation='Consider optimizing search indexes or enabling caching',
                    priority='high'
                ))
            
            # Search success rate insights
            if metrics.search_success_rate < 0.7:  # < 70% success rate
                insights.append(SearchInsight(
                    insight_type='content',
                    title='Low Search Success Rate',
                    description=f'Only {metrics.search_success_rate:.1%} of searches return results',
                    metric_value=metrics.search_success_rate,
                    recommendation='Review zero-result queries and improve content indexing',
                    priority='high'
                ))
            
            # Click-through rate insights
            if metrics.avg_click_through_rate < 0.3:  # < 30% CTR
                insights.append(SearchInsight(
                    insight_type='user_behavior',
                    title='Low Click-Through Rate',
                    description=f'Average click-through rate is {metrics.avg_click_through_rate:.1%}',
                    metric_value=metrics.avg_click_through_rate,
                    recommendation='Improve result relevance and snippet quality',
                    priority='medium'
                ))
            
            # Zero result queries insights
            if len(metrics.zero_result_queries) > 20:
                insights.append(SearchInsight(
                    insight_type='content',
                    title='High Number of Zero-Result Queries',
                    description=f'{len(metrics.zero_result_queries)} queries returned no results',
                    metric_value=len(metrics.zero_result_queries),
                    recommendation='Analyze zero-result queries to identify content gaps',
                    priority='medium'
                ))
            
            # Search type distribution insights
            semantic_pct = metrics.search_types_distribution.get('semantic', 0) / max(metrics.total_searches, 1)
            if semantic_pct < 0.2:  # < 20% semantic searches
                insights.append(SearchInsight(
                    insight_type='user_behavior',
                    title='Low Semantic Search Adoption',
                    description=f'Only {semantic_pct:.1%} of searches use semantic search',
                    metric_value=semantic_pct,
                    recommendation='Promote semantic search features to users',
                    priority='low'
                ))
            
            return insights
            
        except Exception as e:
            logger.error(f"Failed to generate search insights: {e}")
            return []

    def get_trending_queries(self, days: int = 7, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get trending search queries
        
        Args:
            days: Number of days to look back
            limit: Maximum number of queries to return
            
        Returns:
            List of trending queries with metadata
        """
        try:
            since_date = datetime.now() - timedelta(days=days)
            
            # Get queries from the last period
            current_queries = self.db.query(
                SearchAnalytics.search_query,
                func.count(SearchAnalytics.id).label('current_count')
            ).filter(
                and_(
                    SearchAnalytics.search_timestamp >= since_date,
                    SearchAnalytics.search_query.isnot(None),
                    SearchAnalytics.search_query != ''
                )
            ).group_by(SearchAnalytics.search_query).all()
            
            # Get queries from the previous period for comparison
            prev_since_date = since_date - timedelta(days=days)
            prev_queries = self.db.query(
                SearchAnalytics.search_query,
                func.count(SearchAnalytics.id).label('prev_count')
            ).filter(
                and_(
                    SearchAnalytics.search_timestamp >= prev_since_date,
                    SearchAnalytics.search_timestamp < since_date,
                    SearchAnalytics.search_query.isnot(None),
                    SearchAnalytics.search_query != ''
                )
            ).group_by(SearchAnalytics.search_query).all()
            
            # Convert to dicts for easier processing
            current_dict = {query: count for query, count in current_queries}
            prev_dict = {query: count for query, count in prev_queries}
            
            # Calculate trending scores
            trending_queries = []
            for query, current_count in current_dict.items():
                prev_count = prev_dict.get(query, 0)
                
                # Calculate growth rate
                if prev_count > 0:
                    growth_rate = (current_count - prev_count) / prev_count
                else:
                    growth_rate = float('inf') if current_count > 0 else 0
                
                # Calculate trending score (combination of current volume and growth)
                trending_score = current_count * (1 + min(growth_rate, 10))  # Cap growth rate
                
                trending_queries.append({
                    'query': query,
                    'current_count': current_count,
                    'previous_count': prev_count,
                    'growth_rate': growth_rate,
                    'trending_score': trending_score
                })
            
            # Sort by trending score and return top results
            trending_queries.sort(key=lambda x: x['trending_score'], reverse=True)
            return trending_queries[:limit]
            
        except Exception as e:
            logger.error(f"Failed to get trending queries: {e}")
            return []

    def get_search_suggestions(self, query_prefix: str, limit: int = 10) -> List[str]:
        """
        Get search suggestions based on query prefix
        
        Args:
            query_prefix: Partial query to match
            limit: Maximum number of suggestions
            
        Returns:
            List of suggestion strings
        """
        try:
            if len(query_prefix) < 2:
                return []
            
            # Get suggestions from the suggestions table
            suggestions = self.db.query(SearchSuggestion).filter(
                SearchSuggestion.suggestion_text.ilike(f"{query_prefix}%")
            ).order_by(
                desc(SearchSuggestion.search_count),
                desc(SearchSuggestion.last_searched)
            ).limit(limit).all()
            
            results = [s.suggestion_text for s in suggestions]
            
            # If we don't have enough suggestions, get from recent searches
            if len(results) < limit:
                recent_searches = self.db.query(SearchAnalytics.search_query).filter(
                    and_(
                        SearchAnalytics.search_query.ilike(f"{query_prefix}%"),
                        SearchAnalytics.result_count > 0,
                        SearchAnalytics.search_timestamp >= datetime.now() - timedelta(days=30)
                    )
                ).distinct().limit(limit - len(results)).all()
                
                for search_query, in recent_searches:
                    if search_query not in results:
                        results.append(search_query)
            
            return results[:limit]
            
        except Exception as e:
            logger.error(f"Failed to get search suggestions: {e}")
            return []

    def _update_search_suggestions(self, query: str, result_count: int):
        """Update search suggestions with new search data"""
        try:
            if not query or not query.strip():
                return
            
            query = query.strip()
            
            # Find or create suggestion
            suggestion = self.db.query(SearchSuggestion).filter(
                SearchSuggestion.suggestion_text == query
            ).first()
            
            if suggestion:
                suggestion.update_stats(result_count)
            else:
                suggestion = SearchSuggestion(
                    suggestion_text=query,
                    search_count=1,
                    avg_result_count=float(result_count),
                    category='auto'
                )
                self.db.add(suggestion)
            
            self.db.commit()
            
        except Exception as e:
            logger.warning(f"Failed to update search suggestions: {e}")
            self.db.rollback()

    def cleanup_old_analytics(self, days_to_keep: int = 90) -> int:
        """
        Clean up old search analytics data
        
        Args:
            days_to_keep: Number of days of data to keep
            
        Returns:
            Number of records deleted
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            
            deleted_count = self.db.query(SearchAnalytics).filter(
                SearchAnalytics.search_timestamp < cutoff_date
            ).delete()
            
            self.db.commit()
            logger.info(f"Cleaned up {deleted_count} old analytics records")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup old analytics: {e}")
            self.db.rollback()
            return 0