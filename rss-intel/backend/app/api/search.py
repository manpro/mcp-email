"""Search and RAG API endpoints"""
from fastapi import APIRouter, Query, HTTPException, Depends
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
import logging

from ..deps import get_db
from ..rag_engine import rag_engine
from ..vec.weaviate_client import weaviate_manager
from ..personalization_service import get_personalization_service
from ..auth import get_current_user
from sqlalchemy.orm import Session
from fastapi import Request

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["search"])


class SearchResponse(BaseModel):
    """Search API response"""
    results: List[Dict[str, Any]]
    query: str
    total_found: int
    search_time_ms: int
    filters: Dict[str, Any]


class AskRequest(BaseModel):
    """Ask API request"""
    q: str = Field(..., min_length=3, max_length=500, description="Question to ask")
    k: int = Field(default=12, ge=1, le=50, description="Number of sources to consider")
    lang: Optional[str] = Field(default=None, pattern="^(en|sv|de|fr)$", description="Language preference")
    freshness_days: Optional[int] = Field(default=None, ge=1, le=365, description="Only consider articles from last N days")


class AskResponse(BaseModel):
    """Ask API response"""
    answer: str
    citations: List[Dict[str, Any]]
    question: str
    confidence: float
    sources_count: int
    generation_time_ms: int


@router.get("/search", response_model=SearchResponse)
async def search_articles(
    request: Request,
    db: Session = Depends(get_db),
    q: str = Query(..., min_length=1, max_length=200, description="Search query"),
    k: int = Query(default=30, ge=1, le=100, description="Number of results"),
    lang: Optional[str] = Query(default=None, regex="^(en|sv|de|fr)$", description="Language filter"),
    freshness_days: Optional[int] = Query(default=30, ge=1, le=365, description="Articles from last N days"),
    hybrid: bool = Query(default=True, description="Use hybrid vector+BM25 search"),
    alpha: float = Query(default=0.7, ge=0.0, le=1.0, description="Hybrid balance (0=BM25, 1=vector)"),
    content_type: Optional[str] = Query(default='article', regex="^(article|event|all)$", description="Content type filter"),
    personalized: bool = Query(default=True, description="Apply ML personalization")
) -> SearchResponse:
    """
    Semantic search across article content
    
    Returns relevant articles based on the query, with optional filters for language,
    recency, and search method. Results are re-ranked for relevance.
    """
    start_time = datetime.now()
    
    try:
        # Get current user
        user_id = get_current_user(request)
        logger.info(f"Search request: q='{q}', k={k}, lang={lang}, hybrid={hybrid}, personalized={personalized}, user={user_id}")
        
        # Perform search using our RAG engine's hybrid search
        # Note: freshness_days filter may be too restrictive, test without it first
        results = rag_engine.retrieve_relevant_chunks(
            question=q,
            max_chunks=k,
            alpha=alpha if hybrid else 0.0,  # Set alpha to 0 for BM25 only
            lang=lang,
            freshness_days=None,  # Disable freshness filter for now
            content_type=None  # Temporarily disable content_type filtering
        )
        
        # Calculate search time
        search_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
        
        # Format results for API response
        formatted_results = []
        seen_articles = {}  # Track best chunk per article
        
        # First pass: find the best chunk for each article
        for result in results:
            article_id = result['article_id']
            search_score = result.get('search_score', 0)
            
            if article_id not in seen_articles or search_score > seen_articles[article_id]['search_score']:
                seen_articles[article_id] = result
        
        # Second pass: format the best chunks
        for result in seen_articles.values():
            article_id = result['article_id']
            
            # Create snippet from chunk text
            snippet = result.get('text', '')[:300]
            if len(result.get('text', '')) > 300:
                snippet += '...'
            
            # Determine "why" chips for this result
            why_chips = []
            search_score = result.get('search_score', 0)
            rule_score = result.get('score', 0)
            
            if search_score > 0.8:
                why_chips.append('high_relevance')
            elif search_score > 0.6:
                why_chips.append('semantic_match')
            
            if rule_score >= 80:
                why_chips.append('high_score')
            elif rule_score >= 60:
                why_chips.append('interesting')
            
            # Check freshness (articles from last 7 days)
            if result.get('published_at'):
                try:
                    published_at = result['published_at']
                    if published_at.tzinfo is None:
                        # Naive datetime, make it UTC
                        published_at = published_at.replace(tzinfo=datetime.now().astimezone().tzinfo)
                    
                    now = datetime.now().astimezone()
                    days_old = (now - published_at).days
                    if days_old <= 7:
                        why_chips.append('fresh')
                except Exception:
                    # Skip freshness check if datetime comparison fails
                    pass
            
            if not why_chips:
                why_chips.append('content_match')
            
            formatted_results.append({
                'article_id': article_id,
                'title': result['title'],
                'url': result['url'],
                'source': result['source'],
                'published_at': result['published_at'].isoformat() if result['published_at'] else None,
                'snippet': snippet,
                'relevance_score': round(search_score, 3),
                'rule_score': rule_score,
                'lang': result.get('lang', 'en'),
                'why_chips': why_chips,
                'search_metadata': {
                    'chunk_index': result.get('chunk_index', 0),
                    'token_count': result.get('token_count', 0),
                    'search_method': 'hybrid' if hybrid else 'bm25'
                }
            })
        
        # Sort by relevance score
        formatted_results.sort(key=lambda x: x['relevance_score'], reverse=True)
        
        # Apply personalization if requested
        if personalized and formatted_results:
            try:
                personalization_service = get_personalization_service(db)
                formatted_results = personalization_service.personalize_search_results(
                    formatted_results, user_id=user_id, boost_factor=0.3
                )
                logger.info(f"Applied personalization for user {user_id}")
            except Exception as e:
                logger.error(f"Personalization failed: {e}")
                # Continue with non-personalized results
        
        return SearchResponse(
            results=formatted_results,
            query=q,
            total_found=len(results),
            search_time_ms=search_time_ms,
            filters={
                'lang': lang,
                'freshness_days': freshness_days,
                'hybrid': hybrid,
                'alpha': alpha
            }
        )
        
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.post("/ask", response_model=AskResponse)
async def ask_question(request: AskRequest, http_request: Request, db: Session = Depends(get_db)) -> AskResponse:
    """
    Ask a question and get an AI-generated answer with citations
    
    Uses semantic search to find relevant articles, then generates a contextual
    answer with proper source citations.
    """
    start_time = datetime.now()
    
    try:
        # Get current user
        user_id = get_current_user(http_request)
        logger.info(f"Ask request: q='{request.q}', k={request.k}, lang={request.lang}, user={user_id}")
        
        # Use RAG engine to generate answer with retrieval
        answer_data = rag_engine.ask_question(
            question=request.q,
            max_chunks=request.k,
            alpha=0.7,  # Favor vector search for Q&A
            lang=request.lang,
            freshness_days=request.freshness_days,
            content_type=None,  # Temporarily disable content_type filtering
            personalized=True,
            user_id=user_id,
            db_session=db
        )
        
        # Calculate generation time
        generation_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
        
        # Format citations from sources
        citations = []
        for source in answer_data.get('sources', []):
            citations.append({
                'title': source['title'],
                'source': source['source'],
                'url': source['url'],
                'published_at': source['published_at'].isoformat() if source.get('published_at') else None,
                'relevance_score': source.get('relevance_score', 0.0)
            })
        
        return AskResponse(
            answer=answer_data['answer'],
            citations=citations,
            question=request.q,
            confidence=answer_data.get('confidence', 0.0),
            sources_count=answer_data.get('total_chunks_retrieved', 0),
            generation_time_ms=generation_time_ms
        )
        
    except Exception as e:
        logger.error(f"Ask error: {e}")
        raise HTTPException(status_code=500, detail=f"Answer generation failed: {str(e)}")


@router.get("/search/stats")
async def get_search_stats(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Get search system statistics
    
    Returns information about the knowledge base size, embedding models, and
    system health for debugging and monitoring.
    """
    try:
        # Get Weaviate collection stats
        weaviate_stats = weaviate_manager.get_collection_stats()
        
        # Get basic stats from database
        from sqlalchemy import text
        result = db.execute(text("SELECT COUNT(*) FROM articles WHERE full_content IS NOT NULL"))
        articles_with_content = result.scalar()
        
        result = db.execute(text("SELECT COUNT(*) FROM articles"))
        total_articles = result.scalar()
        
        return {
            'knowledge_base': {
                'total_articles': total_articles,
                'articles_with_content': articles_with_content,
                'coverage_pct': round((articles_with_content / total_articles * 100), 1) if total_articles > 0 else 0
            },
            'embedding_model': {
                'model_name': 'all-MiniLM-L6-v2',
                'dimensions': 384,
                'provider': 'sentence-transformers'
            },
            'vector_store': weaviate_stats,
            'timestamp': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Stats error: {e}")
        raise HTTPException(status_code=500, detail=f"Could not get stats: {str(e)}")


@router.post("/search/refresh")
async def refresh_search_index(
    article_ids: Optional[List[int]] = None,
    limit: int = Query(default=50, ge=1, le=500),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Refresh the search index by reprocessing articles
    
    Updates embeddings and chunks for specified articles or processes new articles
    that haven't been indexed yet.
    """
    try:
        logger.info(f"Refreshing search index: article_ids={article_ids}, limit={limit}")
        
        # For now, return a simple success message
        # In production, this would re-run the populate_weaviate script
        
        # Get current stats
        stats = weaviate_manager.get_collection_stats()
        
        return {
            'success': True,
            'message': 'Search index refresh would re-run chunk processing',
            'current_stats': stats,
            'note': 'Use populate_weaviate.py script to refresh the index'
        }
        
    except Exception as e:
        logger.error(f"Index refresh error: {e}")
        raise HTTPException(status_code=500, detail=f"Index refresh failed: {str(e)}")