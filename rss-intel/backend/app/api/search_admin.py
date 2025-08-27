"""
Search Administration API

Administrative endpoints for managing search performance, cache optimization,
and search system monitoring.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from datetime import datetime

from ..deps import get_db
from ..services.search_service import AdvancedSearchService
from ..services.search_analytics_service import SearchAnalyticsService
from ..services.search_cache_service import get_search_cache, initialize_search_cache

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin/search", tags=["Search Administration"])

@router.get("/stats")
async def get_search_system_stats(
    db: Session = Depends(get_db)
):
    """Get comprehensive search system statistics"""
    try:
        stats = {}
        
        # Search service stats
        search_service = AdvancedSearchService(db)
        stats['semantic_index'] = search_service.get_semantic_search_stats()
        
        # Analytics stats
        analytics_service = SearchAnalyticsService(db)
        stats['performance'] = analytics_service.get_search_performance_metrics(days=7).__dict__
        
        # Cache stats
        cache_service = get_search_cache()
        if cache_service:
            cache_stats = cache_service.get_cache_stats()
            stats['cache'] = {
                'total_entries': cache_stats.total_entries,
                'total_size_bytes': cache_stats.total_size_bytes,
                'total_size_mb': round(cache_stats.total_size_bytes / (1024 * 1024), 2),
                'hit_rate': round(cache_stats.hit_rate, 3),
                'miss_rate': round(cache_stats.miss_rate, 3),
                'avg_response_time_ms': round(cache_stats.avg_response_time_ms, 2),
                'popular_queries': dict(cache_stats.popular_queries[:10]),
                'expiry_distribution': cache_stats.expiry_distribution
            }
        else:
            stats['cache'] = {'status': 'disabled'}
        
        # System health
        stats['health'] = {
            'timestamp': datetime.now().isoformat(),
            'search_system_status': 'healthy',
            'semantic_search_enabled': bool(stats['semantic_index'].get('sentence_transformer_available', False)),
            'cache_enabled': cache_service is not None
        }
        
        return stats
        
    except Exception as e:
        logger.error(f"Failed to get search system stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/cache/clear")
async def clear_search_cache(
    pattern: str = Query("*", description="Pattern to clear (* for all)"),
    background_tasks: BackgroundTasks = None
):
    """Clear search cache entries"""
    try:
        cache_service = get_search_cache()
        if not cache_service:
            raise HTTPException(status_code=400, detail="Cache service not available")
        
        # Clear cache entries matching pattern
        cleared_count = cache_service.invalidate_pattern(pattern)
        
        # Clean up expired entries in background
        if background_tasks:
            background_tasks.add_task(cache_service.cleanup_expired_entries)
        
        return {
            'success': True,
            'cleared_entries': cleared_count,
            'pattern': pattern,
            'message': f'Cleared {cleared_count} cache entries matching "{pattern}"'
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to clear cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/cache/precompute")
async def precompute_popular_searches(
    background_tasks: BackgroundTasks,
    days: int = Query(7, ge=1, le=30, description="Days of analytics to use for popular queries"),
    limit: int = Query(20, ge=1, le=100, description="Number of popular queries to precompute"),
    db: Session = Depends(get_db)
):
    """Precompute cache for popular search queries"""
    try:
        cache_service = get_search_cache()
        if not cache_service:
            raise HTTPException(status_code=400, detail="Cache service not available")
        
        # Get popular queries from analytics
        analytics_service = SearchAnalyticsService(db)
        metrics = analytics_service.get_search_performance_metrics(days)
        popular_queries = [query for query, count in metrics.most_popular_queries[:limit]]
        
        # Schedule precomputation in background
        background_tasks.add_task(cache_service.precompute_popular_searches, popular_queries)
        
        return {
            'success': True,
            'message': f'Scheduled precomputation for {len(popular_queries)} popular queries',
            'queries': popular_queries
        }
        
    except Exception as e:
        logger.error(f"Failed to precompute searches: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/semantic-index/refresh")
async def refresh_semantic_index(
    background_tasks: BackgroundTasks,
    limit: int = Query(1000, ge=100, le=10000, description="Number of articles to reindex"),
    db: Session = Depends(get_db)
):
    """Refresh the semantic search index"""
    try:
        search_service = AdvancedSearchService(db)
        
        # Schedule refresh in background
        background_tasks.add_task(search_service.refresh_semantic_index, limit)
        
        return {
            'success': True,
            'message': f'Scheduled semantic index refresh for up to {limit} articles',
            'limit': limit
        }
        
    except Exception as e:
        logger.error(f"Failed to refresh semantic index: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/performance/analysis")
async def get_performance_analysis(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db)
):
    """Get detailed search performance analysis"""
    try:
        analytics_service = SearchAnalyticsService(db)
        
        # Get performance metrics
        metrics = analytics_service.get_search_performance_metrics(days)
        
        # Get insights
        insights = analytics_service.get_search_insights(days)
        
        # Get trending queries
        trending = analytics_service.get_trending_queries(days=min(days, 14), limit=15)
        
        analysis = {
            'period_days': days,
            'performance_metrics': {
                'total_searches': metrics.total_searches,
                'avg_search_time_ms': round(metrics.avg_search_time_ms, 1),
                'avg_results_per_search': round(metrics.avg_results_per_search, 1),
                'success_rate': round(metrics.search_success_rate, 3),
                'click_through_rate': round(metrics.avg_click_through_rate, 3)
            },
            'search_distribution': {
                'search_types': metrics.search_types_distribution,
                'hourly_performance': {
                    str(hour): round(avg_time, 1) 
                    for hour, avg_time in sorted(metrics.performance_by_hour.items())
                }
            },
            'problem_areas': {
                'zero_result_queries': metrics.zero_result_queries[:10],
                'slow_searches': [
                    hour for hour, time in metrics.performance_by_hour.items() 
                    if time > 1000
                ]
            },
            'insights': [
                {
                    'type': insight.insight_type,
                    'title': insight.title,
                    'description': insight.description,
                    'recommendation': insight.recommendation,
                    'priority': insight.priority
                }
                for insight in insights
            ],
            'trending_queries': [
                {
                    'query': item['query'],
                    'growth_rate': round(item['growth_rate'], 2) if item['growth_rate'] != float('inf') else 'new',
                    'current_searches': item['current_count']
                }
                for item in trending[:10]
            ]
        }
        
        return analysis
        
    except Exception as e:
        logger.error(f"Failed to get performance analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/optimize")
async def optimize_search_system(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Run comprehensive search system optimization"""
    try:
        optimizations = []
        
        # Get cache service
        cache_service = get_search_cache()
        
        # Cleanup expired cache entries
        if cache_service:
            background_tasks.add_task(cache_service.cleanup_expired_entries)
            optimizations.append("Scheduled cache cleanup")
        
        # Cleanup old analytics data (keep last 90 days)
        analytics_service = SearchAnalyticsService(db)
        background_tasks.add_task(analytics_service.cleanup_old_analytics, 90)
        optimizations.append("Scheduled analytics cleanup")
        
        # Refresh semantic index with recent articles
        search_service = AdvancedSearchService(db)
        background_tasks.add_task(search_service.refresh_semantic_index, 2000)
        optimizations.append("Scheduled semantic index refresh")
        
        # Precompute popular searches
        if cache_service:
            # Get popular queries
            metrics = analytics_service.get_search_performance_metrics(days=14)
            popular_queries = [query for query, count in metrics.most_popular_queries[:25]]
            
            if popular_queries:
                background_tasks.add_task(cache_service.precompute_popular_searches, popular_queries)
                optimizations.append(f"Scheduled precomputation for {len(popular_queries)} popular queries")
        
        return {
            'success': True,
            'message': 'Search system optimization started',
            'optimizations': optimizations,
            'estimated_duration_minutes': 5
        }
        
    except Exception as e:
        logger.error(f"Failed to optimize search system: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/config")
async def get_search_configuration():
    """Get current search system configuration"""
    try:
        cache_service = get_search_cache()
        
        config = {
            'semantic_search': {
                'enabled': True,
                'model_info': 'Sentence transformer with TF-IDF fallback',
                'embedding_dimension': 384
            },
            'cache': {
                'enabled': cache_service is not None,
                'type': 'Redis + Memory' if cache_service and hasattr(cache_service, 'redis_client') and cache_service.redis_client else 'Memory only',
                'ttl_settings': cache_service.cache_ttls if cache_service else {}
            },
            'search_features': {
                'advanced_filters': True,
                'saved_searches': True,
                'search_analytics': True,
                'faceted_search': True,
                'auto_suggestions': True
            },
            'performance': {
                'pagination_default': 20,
                'max_page_size': 100,
                'default_cache_ttl': 300,
                'semantic_threshold_chars': 10
            }
        }
        
        return config
        
    except Exception as e:
        logger.error(f"Failed to get search configuration: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/test-performance")
async def test_search_performance(
    test_queries: List[str] = [
        "artificial intelligence machine learning",
        "fintech payments blockchain", 
        "startup funding venture capital",
        "api security authentication",
        "mobile development react native"
    ],
    iterations: int = Query(3, ge=1, le=10),
    db: Session = Depends(get_db)
):
    """Run search performance tests"""
    try:
        search_service = AdvancedSearchService(db)
        results = []
        
        for query in test_queries:
            query_results = []
            
            for i in range(iterations):
                start_time = datetime.now()
                
                try:
                    response = search_service.search(
                        query=query,
                        page_size=20,
                        enable_semantic=True
                    )
                    
                    duration_ms = (datetime.now() - start_time).total_seconds() * 1000
                    
                    query_results.append({
                        'iteration': i + 1,
                        'duration_ms': round(duration_ms, 1),
                        'result_count': response.total_count,
                        'cached': duration_ms < 50  # Assume cached if very fast
                    })
                    
                except Exception as e:
                    query_results.append({
                        'iteration': i + 1,
                        'error': str(e)
                    })
            
            # Calculate statistics
            successful_runs = [r for r in query_results if 'error' not in r]
            if successful_runs:
                durations = [r['duration_ms'] for r in successful_runs]
                avg_duration = sum(durations) / len(durations)
                min_duration = min(durations)
                max_duration = max(durations)
                avg_results = sum(r['result_count'] for r in successful_runs) / len(successful_runs)
                cache_hits = sum(1 for r in successful_runs if r.get('cached', False))
            else:
                avg_duration = min_duration = max_duration = avg_results = cache_hits = 0
            
            results.append({
                'query': query,
                'runs': query_results,
                'statistics': {
                    'avg_duration_ms': round(avg_duration, 1),
                    'min_duration_ms': round(min_duration, 1),
                    'max_duration_ms': round(max_duration, 1),
                    'avg_result_count': round(avg_results, 1),
                    'cache_hit_rate': round(cache_hits / len(successful_runs), 2) if successful_runs else 0,
                    'success_rate': len(successful_runs) / iterations
                }
            })
        
        # Overall statistics
        all_successful = [r for result in results for r in result['runs'] if 'error' not in r]
        overall_avg = sum(r['duration_ms'] for r in all_successful) / len(all_successful) if all_successful else 0
        
        return {
            'test_summary': {
                'total_queries_tested': len(test_queries),
                'iterations_per_query': iterations,
                'overall_avg_duration_ms': round(overall_avg, 1),
                'total_successful_runs': len(all_successful),
                'total_runs': len(test_queries) * iterations
            },
            'query_results': results
        }
        
    except Exception as e:
        logger.error(f"Failed to run performance tests: {e}")
        raise HTTPException(status_code=500, detail=str(e))