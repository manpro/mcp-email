"""Search and RAG API endpoints"""
from fastapi import APIRouter, Query, HTTPException, Depends
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
import logging

from ..deps import get_db
from ..vec.rag import rag_search_engine, answer_generator
from sqlalchemy.orm import Session

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
    q: str = Query(..., min_length=1, max_length=200, description="Search query"),
    k: int = Query(default=30, ge=1, le=100, description="Number of results"),
    lang: Optional[str] = Query(default=None, regex="^(en|sv|de|fr)$", description="Language filter"),
    freshness_days: Optional[int] = Query(default=30, ge=1, le=365, description="Articles from last N days"),
    hybrid: bool = Query(default=True, description="Use hybrid vector+BM25 search"),
    alpha: float = Query(default=0.7, ge=0.0, le=1.0, description="Hybrid balance (0=BM25, 1=vector)")
) -> SearchResponse:
    """
    Semantic search across article content
    
    Returns relevant articles based on the query, with optional filters for language,
    recency, and search method. Results are re-ranked for relevance.
    """
    start_time = datetime.now()
    
    try:
        logger.info(f"Search request: q='{q}', k={k}, lang={lang}, hybrid={hybrid}")
        
        # Perform search
        results = rag_search_engine.search(
            query=q,
            k=k,
            lang=lang,
            freshness_days=freshness_days,
            hybrid=hybrid,
            alpha=alpha
        )
        
        # Calculate search time
        search_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
        
        # Format results for API response
        formatted_results = []
        for result in results:
            # Create snippet with highlighted matches (simple approach)
            snippet = result.get('text', '')[:300]
            if len(result.get('text', '')) > 300:
                snippet += '...'
            
            # Determine "why" chips for this result
            why_chips = []
            components = result.get('score_components', {})
            
            if components.get('title_boost', 0) > 0.3:
                why_chips.append('title_match')
            if components.get('recency_boost', 0) > 0.5:
                why_chips.append('fresh')
            if result.get('score', 0) >= 80:
                why_chips.append('high_score')
            if not why_chips:
                why_chips.append('semantic_match')
            
            formatted_results.append({
                'article_id': result['article_id'],
                'title': result['title'],
                'url': result['url'],
                'source': result['source'],
                'published_at': result['published_at'].isoformat() if result['published_at'] else None,
                'snippet': snippet,
                'relevance_score': round(result.get('final_score', 0), 3),
                'rule_score': result.get('score', 0),
                'lang': result.get('lang'),
                'why_chips': why_chips,
                'search_metadata': result.get('search_metadata', {})
            })
        
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
async def ask_question(request: AskRequest) -> AskResponse:
    """
    Ask a question and get an AI-generated answer with citations
    
    Uses semantic search to find relevant articles, then generates a contextual
    answer with proper source citations.
    """
    start_time = datetime.now()
    
    try:
        logger.info(f"Ask request: q='{request.q}', k={request.k}, lang={request.lang}")
        
        # First, search for relevant articles
        search_results = rag_search_engine.search(
            query=request.q,
            k=request.k,
            lang=request.lang,
            freshness_days=request.freshness_days,
            hybrid=True,  # Always use hybrid for Q&A
            alpha=0.7
        )
        
        # Generate answer from search results
        answer_data = answer_generator.generate_answer(
            question=request.q,
            search_results=search_results,
            lang=request.lang or 'en'
        )
        
        # Calculate generation time
        generation_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
        
        return AskResponse(
            answer=answer_data['answer'],
            citations=answer_data['citations'],
            question=request.q,
            confidence=answer_data.get('confidence', 0.0),
            sources_count=len(search_results),
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
        from ..vec.upsert_chunks import get_chunking_stats
        from ..vec.embedder import get_batch_embedder
        from ..vec.weaviate_client import weaviate_manager
        
        # Get chunking statistics
        chunk_stats = get_chunking_stats(db)
        
        # Get embedding model info
        embedder = get_batch_embedder()
        model_info = embedder.model_info
        
        # Get Weaviate collection stats
        weaviate_stats = weaviate_manager.get_collection_stats()
        
        return {
            'knowledge_base': chunk_stats,
            'embedding_model': model_info,
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
        from ..vec.upsert_chunks import upsert_chunks_for_articles
        
        logger.info(f"Refreshing search index: article_ids={article_ids}, limit={limit}")
        
        result = upsert_chunks_for_articles(
            db=db,
            article_ids=article_ids,
            limit=limit,
            overwrite_existing=article_ids is not None  # Only overwrite if specific articles requested
        )
        
        return {
            'success': True,
            'message': 'Search index refresh completed',
            'statistics': result
        }
        
    except Exception as e:
        logger.error(f"Index refresh error: {e}")
        raise HTTPException(status_code=500, detail=f"Index refresh failed: {str(e)}")