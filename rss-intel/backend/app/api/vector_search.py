"""
Vector Search API Endpoints

API endpoints for semantic search, RAG capabilities, and vector index management
using Weaviate vector database.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, Field

from ..deps import get_db
from ..services.vector_search_service import get_vector_search_service, VectorSearchQuery
from ..store import Article

logger = logging.getLogger(__name__)
router = APIRouter()

class SemanticSearchRequest(BaseModel):
    """Request model for semantic search"""
    query: str = Field(..., min_length=1, max_length=500)
    limit: int = Field(10, ge=1, le=100)
    min_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    days_back: Optional[int] = Field(None, ge=1, le=365)
    sources: Optional[List[str]] = Field(None, max_items=20)
    semantic_weight: float = Field(0.7, ge=0.0, le=1.0)
    keyword_weight: float = Field(0.3, ge=0.0, le=1.0)
    include_explanation: bool = Field(True)

class SearchResultModel(BaseModel):
    """Search result model for API responses"""
    article_id: int
    title: str
    url: str
    content_preview: str
    source: str
    published_at: str
    score_total: float
    similarity_score: float
    combined_score: float
    explanation: str
    topics: List[str]

class IndexingRequest(BaseModel):
    """Request model for indexing operations"""
    article_ids: Optional[List[int]] = Field(None, max_items=1000)
    force_reindex: bool = Field(False)
    batch_size: int = Field(50, ge=1, le=100)

@router.post("/vector-search/search")
async def semantic_search(
    request: SemanticSearchRequest,
    db: Session = Depends(get_db)
):
    """Perform semantic search across articles"""
    try:
        service = get_vector_search_service(db)
        
        # Build date filter if specified
        date_filter = None
        if request.days_back:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=request.days_back)
            date_filter = (start_date, end_date)
        
        # Create vector search query
        vector_query = VectorSearchQuery(
            query=request.query,
            limit=request.limit,
            min_score=request.min_score,
            date_filter=date_filter,
            source_filter=request.sources,
            semantic_weight=request.semantic_weight,
            keyword_weight=request.keyword_weight,
            include_explanation=request.include_explanation
        )
        
        # Perform search
        results = await service.semantic_search(vector_query)
        
        # Convert to API response format
        search_results = []
        for result in results:
            article = result.article
            search_results.append(SearchResultModel(
                article_id=article.id,
                title=article.title or "Untitled",
                url=article.url or "",
                content_preview=(article.content or "")[:200] + "..." if len(article.content or "") > 200 else (article.content or ""),
                source=article.source or "",
                published_at=article.published_at.isoformat() if article.published_at else "",
                score_total=article.score_total or 0,
                similarity_score=result.similarity,
                combined_score=result.score,
                explanation=result.explanation,
                topics=article.topics or []
            ))
        
        return {
            "query": request.query,
            "results": search_results,
            "total_results": len(search_results),
            "search_params": {
                "semantic_weight": request.semantic_weight,
                "keyword_weight": request.keyword_weight,
                "min_score": request.min_score,
                "days_back": request.days_back,
                "sources": request.sources
            }
        }
        
    except Exception as e:
        logger.error(f"Semantic search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/vector-search/similar/{article_id}")
async def find_similar_articles(
    article_id: int,
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """Find articles similar to the specified article"""
    try:
        # Get the source article
        article = db.query(Article).filter(Article.id == article_id).first()
        if not article:
            raise HTTPException(status_code=404, detail="Article not found")
        
        service = get_vector_search_service(db)
        results = await service.get_similar_articles(article, limit)
        
        # Convert to response format
        similar_articles = []
        for result in results:
            similar_article = result.article
            similar_articles.append({
                "article_id": similar_article.id,
                "title": similar_article.title or "Untitled",
                "url": similar_article.url or "",
                "content_preview": (similar_article.content or "")[:150] + "..." if len(similar_article.content or "") > 150 else (similar_article.content or ""),
                "source": similar_article.source or "",
                "published_at": similar_article.published_at.isoformat() if similar_article.published_at else "",
                "similarity_score": result.similarity,
                "explanation": result.explanation
            })
        
        return {
            "source_article": {
                "id": article.id,
                "title": article.title or "Untitled",
                "source": article.source or ""
            },
            "similar_articles": similar_articles,
            "total_found": len(similar_articles)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Finding similar articles failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/vector-search/suggestions")
async def get_search_suggestions(
    q: str = Query(..., min_length=2, max_length=100),
    limit: int = Query(5, ge=1, le=20),
    db: Session = Depends(get_db)
):
    """Get search suggestions based on partial query"""
    try:
        service = get_vector_search_service(db)
        suggestions = await service.get_search_suggestions(q, limit)
        
        return {
            "query": q,
            "suggestions": suggestions
        }
        
    except Exception as e:
        logger.error(f"Getting search suggestions failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/vector-search/index")
async def index_articles(
    request: IndexingRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Index articles in the vector database"""
    try:
        service = get_vector_search_service(db)
        
        if request.article_ids:
            # Index specific articles
            articles = db.query(Article).filter(Article.id.in_(request.article_ids)).all()
            if not articles:
                return {"message": "No articles found with the specified IDs", "indexed": 0}
        else:
            # Index recent unindexed articles (default behavior)
            recent_date = datetime.now() - timedelta(days=7)
            articles = db.query(Article).filter(
                Article.created_at >= recent_date
            ).limit(request.batch_size * 10).all()  # Reasonable limit
        
        if not articles:
            return {"message": "No articles to index", "indexed": 0}
        
        # Start indexing in background
        background_tasks.add_task(
            index_articles_task,
            service,
            articles,
            request.batch_size,
            request.force_reindex
        )
        
        return {
            "message": "Article indexing started",
            "articles_to_index": len(articles),
            "batch_size": request.batch_size,
            "force_reindex": request.force_reindex,
            "status": "background_task_started"
        }
        
    except Exception as e:
        logger.error(f"Article indexing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/vector-search/reindex")
async def reindex_all_articles(
    background_tasks: BackgroundTasks,
    batch_size: int = Query(50, ge=1, le=100),
    days_back: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db)
):
    """Reindex articles from the specified time period"""
    try:
        service = get_vector_search_service(db)
        
        # Get articles from specified period
        cutoff_date = datetime.now() - timedelta(days=days_back)
        articles = db.query(Article).filter(
            Article.created_at >= cutoff_date
        ).all()
        
        if not articles:
            return {"message": "No articles found in the specified period", "reindexed": 0}
        
        # Start reindexing in background
        background_tasks.add_task(
            index_articles_task,
            service,
            articles,
            batch_size,
            True  # Force reindex
        )
        
        return {
            "message": "Article reindexing started",
            "articles_to_reindex": len(articles),
            "days_back": days_back,
            "batch_size": batch_size,
            "status": "background_task_started"
        }
        
    except Exception as e:
        logger.error(f"Article reindexing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/vector-search/stats")
async def get_vector_search_stats(
    db: Session = Depends(get_db)
):
    """Get vector search index statistics"""
    try:
        service = get_vector_search_service(db)
        stats = await service.get_index_stats()
        
        return stats
        
    except Exception as e:
        logger.error(f"Getting vector search stats failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/vector-search/cleanup")
async def cleanup_old_articles(
    background_tasks: BackgroundTasks,
    days_old: int = Query(90, ge=30, le=365),
    db: Session = Depends(get_db)
):
    """Remove old articles from the vector index"""
    try:
        service = get_vector_search_service(db)
        
        # Start cleanup in background
        background_tasks.add_task(
            cleanup_articles_task,
            service,
            days_old
        )
        
        return {
            "message": "Vector index cleanup started",
            "days_old": days_old,
            "status": "background_task_started"
        }
        
    except Exception as e:
        logger.error(f"Vector index cleanup failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/vector-search/initialize")
async def initialize_vector_search(
    db: Session = Depends(get_db)
):
    """Initialize the vector search service and create schema if needed"""
    try:
        service = get_vector_search_service(db)
        success = await service.initialize()
        
        if success:
            return {
                "message": "Vector search initialized successfully",
                "status": "ready"
            }
        else:
            raise HTTPException(status_code=503, detail="Failed to initialize vector search")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Vector search initialization failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/vector-search/health")
async def check_vector_search_health(
    db: Session = Depends(get_db)
):
    """Check the health of the vector search system"""
    try:
        service = get_vector_search_service(db)
        
        # Try to initialize if not already done
        if not service.client:
            await service.initialize()
        
        # Get basic stats to test connectivity
        stats = await service.get_index_stats()
        
        health_status = {
            "status": "healthy" if "error" not in stats else "unhealthy",
            "weaviate_connected": service.client is not None and service.client.is_ready() if service.client else False,
            "embedding_model_loaded": service.embedding_model is not None,
            "total_indexed_articles": stats.get("total_articles", 0),
            "last_checked": datetime.now().isoformat()
        }
        
        if "error" in stats:
            health_status["error"] = stats["error"]
        
        return health_status
        
    except Exception as e:
        logger.error(f"Vector search health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "last_checked": datetime.now().isoformat()
        }

# Background task functions
async def index_articles_task(service, articles: List[Article], batch_size: int, force_reindex: bool):
    """Background task for indexing articles"""
    try:
        stats = await service.index_articles_batch(articles, batch_size)
        logger.info(f"Article indexing completed: {stats}")
    except Exception as e:
        logger.error(f"Article indexing task failed: {e}")

async def cleanup_articles_task(service, days_old: int):
    """Background task for cleaning up old articles"""
    try:
        deleted_count = await service.cleanup_old_articles(days_old)
        logger.info(f"Vector index cleanup completed: {deleted_count} articles removed")
    except Exception as e:
        logger.error(f"Vector index cleanup task failed: {e}")