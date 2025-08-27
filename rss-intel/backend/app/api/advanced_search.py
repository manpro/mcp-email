"""
Advanced Search API endpoints
Provides comprehensive search functionality with filtering, facets, and analytics
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from pydantic import BaseModel, Field

from ..deps import get_db
from ..services.search_service import AdvancedSearchService, SearchFilter, SearchResponse
from ..services.search_analytics_service import SearchAnalyticsService
from ..store import Article
from ..models.search import SavedSearch as SavedSearchModel

router = APIRouter()

# Request/Response Models
class SearchRequest(BaseModel):
    query: str = ""
    sources: Optional[List[str]] = None
    categories: Optional[List[str]] = None
    min_score: Optional[int] = None
    max_score: Optional[int] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    has_image: Optional[bool] = None
    is_starred: Optional[bool] = None
    labels: Optional[List[str]] = None
    exclude_spam: bool = True
    content_quality_min: Optional[float] = None
    sentiment: Optional[str] = None
    word_count_min: Optional[int] = None
    word_count_max: Optional[int] = None
    language: Optional[str] = None
    
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)
    sort_by: str = Field("relevance", regex="^(relevance|date|score|title)$")
    sort_order: str = Field("desc", regex="^(asc|desc)$")
    enable_semantic: bool = True
    highlight: bool = True

class ArticleSearchResult(BaseModel):
    id: int
    title: str
    url: str
    source: str
    published_at: datetime
    score: Optional[int]
    content_preview: Optional[str]
    image_proxy_path: Optional[str]
    relevance_score: float
    match_highlights: List[str]
    match_reason: str
    has_image: bool
    is_starred: bool
    labels: List[str]
    spam_detected: Optional[bool]
    content_quality_score: Optional[float]

class SearchFacets(BaseModel):
    sources: Dict[str, int]
    score_ranges: Dict[str, int] 
    date_ranges: Dict[str, int]

class AdvancedSearchResponse(BaseModel):
    results: List[ArticleSearchResult]
    total_count: int
    search_time_ms: float
    page: int
    page_size: int
    total_pages: int
    filters_applied: Dict[str, Any]
    suggestions: List[str]
    facets: SearchFacets

class SavedSearch(BaseModel):
    id: Optional[int] = None
    name: str
    description: Optional[str] = None
    search_params: SearchRequest
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class SearchAnalytics(BaseModel):
    query: str
    result_count: int
    search_time_ms: float
    clicked_results: List[int] = []
    timestamp: datetime

# Search endpoints
@router.post("/search", response_model=AdvancedSearchResponse)
async def advanced_search(
    request: SearchRequest,
    db: Session = Depends(get_db)
):
    """
    Advanced search with comprehensive filtering and semantic capabilities
    """
    try:
        # Convert request to SearchFilter
        filters = SearchFilter(
            sources=request.sources,
            categories=request.categories,
            min_score=request.min_score,
            max_score=request.max_score,
            date_from=request.date_from,
            date_to=request.date_to,
            has_image=request.has_image,
            is_starred=request.is_starred,
            labels=request.labels,
            exclude_spam=request.exclude_spam,
            content_quality_min=request.content_quality_min,
            sentiment=request.sentiment,
            word_count_min=request.word_count_min,
            word_count_max=request.word_count_max,
            language=request.language
        )
        
        # Perform search
        search_service = AdvancedSearchService(db)
        analytics_service = SearchAnalyticsService(db)
        
        search_response = search_service.search(
            query=request.query,
            filters=filters,
            page=request.page,
            page_size=request.page_size,
            sort_by=request.sort_by,
            sort_order=request.sort_order,
            enable_semantic=request.enable_semantic,
            highlight=request.highlight
        )
        
        # Log search analytics (in background)
        try:
            search_type = "semantic" if request.enable_semantic else "keyword"
            if request.enable_semantic and len(request.query) <= 10:
                search_type = "hybrid"
                
            analytics_service.log_search(
                query=request.query,
                search_filters=filters.__dict__,
                search_type=search_type,
                result_count=search_response.total_count,
                search_time_ms=search_response.search_time_ms,
                page=request.page
            )
        except Exception as e:
            logger.warning(f"Failed to log search analytics: {e}")
        
        # Convert results to response format
        results = []
        for result in search_response.results:
            article = result.article
            
            # Extract labels from flags
            labels = []
            if article.flags:
                for key, value in article.flags.items():
                    if isinstance(value, bool) and value and key not in ['spam_detected', 'low_quality']:
                        labels.append(key)
            
            # Generate content preview
            content_preview = None
            if article.content:
                preview_length = 200
                content_preview = article.content[:preview_length]
                if len(article.content) > preview_length:
                    content_preview += "..."
            
            results.append(ArticleSearchResult(
                id=article.id,
                title=article.title,
                url=article.url,
                source=article.source,
                published_at=article.published_at,
                score=article.score,
                content_preview=content_preview,
                image_proxy_path=article.image_proxy_path,
                relevance_score=result.relevance_score,
                match_highlights=result.match_highlights,
                match_reason=result.match_reason,
                has_image=article.image_proxy_path is not None,
                is_starred=bool(article.flags and article.flags.get('starred', False)),
                labels=labels,
                spam_detected=getattr(article, 'spam_detected', None),
                content_quality_score=getattr(article, 'content_quality_score', None)
            ))
        
        # Calculate pagination
        total_pages = (search_response.total_count + request.page_size - 1) // request.page_size
        
        return AdvancedSearchResponse(
            results=results,
            total_count=search_response.total_count,
            search_time_ms=search_response.search_time_ms,
            page=request.page,
            page_size=request.page_size,
            total_pages=total_pages,
            filters_applied=search_response.filters_applied,
            suggestions=search_response.suggestions,
            facets=SearchFacets(**search_response.facets)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@router.get("/search/suggestions")
async def get_search_suggestions(
    query: str = Query(..., min_length=1),
    limit: int = Query(10, ge=1, le=20),
    db: Session = Depends(get_db)
):
    """Get search suggestions based on partial query"""
    try:
        analytics_service = SearchAnalyticsService(db)
        suggestions = analytics_service.get_search_suggestions(query, limit)
        
        return {
            "suggestions": suggestions,
            "query": query
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get suggestions: {str(e)}")

@router.get("/search/facets")
async def get_search_facets(
    query: str = Query("", description="Search query for facet calculation"),
    db: Session = Depends(get_db)
):
    """Get search facets (filters) with counts"""
    try:
        search_service = AdvancedSearchService(db)
        filters = SearchFilter()  # Empty filters to get all facets
        
        # Get facets
        facets = search_service._generate_facets(filters, query if query else None)
        
        return {
            "facets": facets,
            "query": query
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get facets: {str(e)}")

@router.get("/search/popular-terms")
async def get_popular_search_terms(
    limit: int = Query(20, ge=1, le=50),
    period_days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db)
):
    """Get popular search terms from the last N days"""
    try:
        # In a real implementation, this would come from search analytics
        # For now, return commonly searched terms
        popular_terms = [
            {"term": "artificial intelligence", "count": 150, "growth": 0.25},
            {"term": "payments", "count": 120, "growth": 0.15},
            {"term": "fintech", "count": 100, "growth": 0.10},
            {"term": "machine learning", "count": 95, "growth": 0.30},
            {"term": "blockchain", "count": 80, "growth": -0.05},
            {"term": "cryptocurrency", "count": 75, "growth": -0.10},
            {"term": "api", "count": 65, "growth": 0.20},
            {"term": "security", "count": 60, "growth": 0.18},
            {"term": "startups", "count": 55, "growth": 0.12},
            {"term": "funding", "count": 50, "growth": 0.08}
        ]
        
        return {
            "popular_terms": popular_terms[:limit],
            "period_days": period_days,
            "last_updated": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get popular terms: {str(e)}")

# Saved searches endpoints  
@router.post("/search/saved")
async def save_search(
    saved_search: SavedSearch,
    db: Session = Depends(get_db)
):
    """Save a search configuration for later use"""
    try:
        # Create database model
        db_saved_search = SavedSearchModel(
            name=saved_search.name,
            description=saved_search.description,
            search_query=saved_search.search_params.query,
            search_filters=saved_search.search_params.__dict__ if hasattr(saved_search.search_params, '__dict__') else {},
            search_settings={}
        )
        
        db.add(db_saved_search)
        db.commit()
        db.refresh(db_saved_search)
        
        return {
            "success": True,
            "saved_search": {
                "id": db_saved_search.id,
                "name": db_saved_search.name,
                "description": db_saved_search.description,
                "search_params": db_saved_search.search_params_dict,
                "created_at": db_saved_search.created_at.isoformat(),
                "usage_count": db_saved_search.usage_count
            },
            "message": "Search saved successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save search: {str(e)}")

@router.get("/search/saved")
async def get_saved_searches(
    db: Session = Depends(get_db)
):
    """Get all saved searches for the current user"""
    try:
        saved_searches = db.query(SavedSearchModel).order_by(
            SavedSearchModel.last_used.desc().nullslast(),
            SavedSearchModel.created_at.desc()
        ).limit(50).all()
        
        result = []
        for search in saved_searches:
            result.append({
                "id": search.id,
                "name": search.name,
                "description": search.description,
                "search_params": search.search_params_dict,
                "created_at": search.created_at.isoformat(),
                "last_used": search.last_used.isoformat() if search.last_used else None,
                "usage_count": search.usage_count
            })
        
        return {
            "saved_searches": result
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get saved searches: {str(e)}")

@router.delete("/search/saved/{search_id}")
async def delete_saved_search(
    search_id: int,
    db: Session = Depends(get_db)
):
    """Delete a saved search"""
    try:
        saved_search = db.query(SavedSearchModel).filter(
            SavedSearchModel.id == search_id
        ).first()
        
        if not saved_search:
            raise HTTPException(status_code=404, detail="Saved search not found")
        
        db.delete(saved_search)
        db.commit()
        
        return {
            "success": True,
            "message": f"Saved search {search_id} deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete saved search: {str(e)}")

@router.put("/search/saved/{search_id}/use")
async def use_saved_search(
    search_id: int,
    db: Session = Depends(get_db)
):
    """Mark a saved search as used (updates usage statistics)"""
    try:
        saved_search = db.query(SavedSearchModel).filter(
            SavedSearchModel.id == search_id
        ).first()
        
        if not saved_search:
            raise HTTPException(status_code=404, detail="Saved search not found")
        
        saved_search.update_usage()
        db.commit()
        
        return {
            "success": True,
            "message": "Usage updated successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update saved search usage: {str(e)}")

# Search analytics endpoints
@router.post("/search/analytics/click")
async def log_click_through(
    search_id: int,
    clicked_article_ids: List[int],
    db: Session = Depends(get_db)
):
    """Log click-through events for search analytics"""
    try:
        analytics_service = SearchAnalyticsService(db)
        success = analytics_service.log_click_through(search_id, clicked_article_ids)
        
        return {
            "success": success,
            "message": "Click-through logged successfully" if success else "Search not found"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to log click-through: {str(e)}")

@router.get("/search/analytics/summary")
async def get_search_analytics_summary(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db)
):
    """Get comprehensive search analytics summary"""
    try:
        analytics_service = SearchAnalyticsService(db)
        metrics = analytics_service.get_search_performance_metrics(days)
        
        # Convert to API response format
        summary = {
            "period_days": days,
            "total_searches": metrics.total_searches,
            "avg_search_time_ms": round(metrics.avg_search_time_ms, 1),
            "avg_results_per_search": round(metrics.avg_results_per_search, 1),
            "search_success_rate": round(metrics.search_success_rate, 3),
            "avg_click_through_rate": round(metrics.avg_click_through_rate, 3),
            "most_popular_queries": [
                {"term": query, "count": count} 
                for query, count in metrics.most_popular_queries
            ],
            "search_types_distribution": metrics.search_types_distribution,
            "performance_by_hour": {
                str(hour): round(avg_time, 1) 
                for hour, avg_time in metrics.performance_by_hour.items()
            },
            "zero_result_queries": metrics.zero_result_queries[:10],  # Limit for API
            "search_performance_distribution": {
                "fast_searches_pct": len([t for t in metrics.performance_by_hour.values() if t < 100]) / max(len(metrics.performance_by_hour), 1) * 100,
                "medium_searches_pct": len([t for t in metrics.performance_by_hour.values() if 100 <= t < 500]) / max(len(metrics.performance_by_hour), 1) * 100,
                "slow_searches_pct": len([t for t in metrics.performance_by_hour.values() if t >= 500]) / max(len(metrics.performance_by_hour), 1) * 100,
            }
        }
        
        return summary
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get analytics summary: {str(e)}")

@router.get("/search/analytics/insights")
async def get_search_insights(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db)
):
    """Get actionable search insights and recommendations"""
    try:
        analytics_service = SearchAnalyticsService(db)
        insights = analytics_service.get_search_insights(days)
        
        return {
            "insights": [
                {
                    "type": insight.insight_type,
                    "title": insight.title,
                    "description": insight.description,
                    "metric_value": insight.metric_value,
                    "recommendation": insight.recommendation,
                    "priority": insight.priority
                }
                for insight in insights
            ],
            "period_days": days
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get search insights: {str(e)}")

@router.get("/search/analytics/trending")
async def get_trending_queries(
    days: int = Query(7, ge=1, le=30),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """Get trending search queries"""
    try:
        analytics_service = SearchAnalyticsService(db)
        trending = analytics_service.get_trending_queries(days, limit)
        
        return {
            "trending_queries": [
                {
                    "query": item["query"],
                    "current_count": item["current_count"],
                    "previous_count": item["previous_count"],
                    "growth_rate": round(item["growth_rate"], 2) if item["growth_rate"] != float('inf') else "new",
                    "trending_score": round(item["trending_score"], 1)
                }
                for item in trending
            ],
            "period_days": days
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get trending queries: {str(e)}")

# Quick search endpoint for autocomplete
@router.get("/search/quick")
async def quick_search(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(5, ge=1, le=20),
    db: Session = Depends(get_db)
):
    """Quick search for autocomplete and instant results"""
    try:
        search_service = AdvancedSearchService(db)
        filters = SearchFilter(exclude_spam=True)
        
        # Quick search with limited results
        response = search_service.search(
            query=q,
            filters=filters,
            page=1,
            page_size=limit,
            sort_by="relevance",
            enable_semantic=False,  # Disable for speed
            highlight=False  # Disable for speed
        )
        
        # Return minimal result format for speed
        quick_results = []
        for result in response.results:
            article = result.article
            quick_results.append({
                "id": article.id,
                "title": article.title,
                "source": article.source,
                "score": article.score,
                "published_at": article.published_at.isoformat(),
                "relevance": result.relevance_score
            })
        
        return {
            "results": quick_results,
            "total_count": response.total_count,
            "search_time_ms": response.search_time_ms,
            "query": q
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Quick search failed: {str(e)}")