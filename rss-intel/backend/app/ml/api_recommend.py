"""Recommendation API endpoints"""
import logging
from datetime import datetime
from typing import List, Dict, Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from ..deps import get_db
from .ranker import ArticleRanker
from .bandit import BanditRecommender
from .uservec import get_user_embedding, compute_user_article_similarity

logger = logging.getLogger(__name__)

router = APIRouter()

def get_article_details(db: Session, article_ids: List[int]) -> Dict[int, Dict]:
    """Get article details for recommendation display"""
    from sqlalchemy import text
    
    placeholders = ','.join([f':id{i}' for i in range(len(article_ids))])
    params = {f'id{i}': article_id for i, article_id in enumerate(article_ids)}
    
    result = db.execute(text(f"""
        SELECT 
            a.id,
            a.title,
            a.url,
            a.source,
            a.published_at,
            a.score_total,
            COALESCE(a.has_image, false) as has_image,
            av.source as vector_source
        FROM articles a
        LEFT JOIN article_vectors av ON a.id = av.article_id
        WHERE a.id IN ({placeholders})
    """), params)
    
    articles = {}
    for row in result:
        articles[row.id] = {
            'id': row.id,
            'title': row.title,
            'url': row.url,
            'source': row.source,
            'published_at': row.published_at.isoformat() if row.published_at else None,
            'score_total': row.score_total,
            'has_image': row.has_image
        }
    
    return articles

def generate_why_chips(
    db: Session,
    article_id: int,
    p_read: float,
    rule_score: int,
    user_id: str = "owner"
) -> List[str]:
    """Generate explanation chips for why article was recommended"""
    chips = []
    
    # High ML confidence
    if p_read > 0.8:
        chips.append("High confidence")
    elif p_read > 0.6:
        chips.append("Good match")
    
    # High rule score
    if rule_score > 80:
        chips.append("Trending")
    elif rule_score > 60:
        chips.append("Popular")
    
    # Source-based
    from sqlalchemy import text
    source_result = db.execute(text("""
        SELECT source FROM articles WHERE id = :article_id
    """), {"article_id": article_id})
    
    source_row = source_result.fetchone()
    if source_row and source_row.source:
        # Check if user has positive interactions with this source
        source_check = db.execute(text("""
            SELECT COUNT(*) 
            FROM events e
            JOIN articles a ON e.article_id = a.id
            WHERE e.user_id = :user_id
            AND a.source = :source
            AND e.type IN ('star', 'external_click')
            AND e.created_at > NOW() - INTERVAL '30 days'
        """), {"user_id": user_id, "source": source_row.source})
        
        if source_check.fetchone()[0] > 0:
            chips.append(f"source:{source_row.source}")
    
    # Similarity to starred articles
    similarity = compute_user_article_similarity(db, user_id, article_id)
    if similarity and similarity > 0.7:
        chips.append("similar to ⭐ you read")
    
    # Limit to top 3 chips
    return chips[:3]

@router.get("/recommend")
async def get_recommendations(
    limit: int = Query(50, ge=1, le=100),
    user_id: str = Query("owner"),
    db: Session = Depends(get_db)
) -> Dict:
    """
    Get personalized article recommendations
    
    Returns list of articles with p_read scores and explanation chips
    """
    logger.info(f"Getting recommendations for user {user_id}, limit={limit}")
    
    try:
        # Get ranked articles
        ranker = ArticleRanker(db)
        scored_articles = ranker.rank_for_user(
            user_id=user_id,
            limit=limit * 2,  # Get more for diversification
            days_back=14
        )
        
        if not scored_articles:
            return {
                "articles": [],
                "total": 0,
                "user_id": user_id,
                "timestamp": datetime.utcnow().isoformat()
            }
        
        # Apply bandit algorithm
        bandit = BanditRecommender(db)
        bandit_articles = bandit.apply_bandit(scored_articles, user_id)
        
        # Apply MMR diversification
        diversified_articles = bandit.apply_mmr_diversification(
            bandit_articles, user_id, final_count=limit
        )
        
        # Get article details
        article_ids = [a['article_id'] for a in diversified_articles]
        article_details = get_article_details(db, article_ids)
        
        # Build response
        recommendations = []
        for item in diversified_articles:
            article_id = item['article_id']
            if article_id not in article_details:
                continue
                
            article = article_details[article_id]
            
            # Generate explanation chips
            why_chips = generate_why_chips(
                db, article_id, item['p_read'], item['rule_score'], user_id
            )
            
            recommendations.append({
                **article,
                'p_read': round(item['p_read'], 3),
                'rule_score': item['rule_score'],
                'why': why_chips,
                'exploration': item.get('exploration', False)
            })
        
        logger.info(f"Returning {len(recommendations)} recommendations")
        
        return {
            "articles": recommendations,
            "total": len(recommendations),
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error generating recommendations: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/recommend/debug")
async def debug_recommendations(
    user_id: str = Query("owner"),
    db: Session = Depends(get_db)
) -> Dict:
    """Debug endpoint showing recommendation pipeline details"""
    
    try:
        ranker = ArticleRanker(db)
        bandit = BanditRecommender(db)
        
        # Get candidates
        candidates = ranker.get_candidates(user_id=user_id, limit=100)
        
        # Get user embedding info
        user_emb = get_user_embedding(db, user_id, lookback_days=30)
        user_emb_available = user_emb is not None
        
        # Score a few candidates
        sample_candidates = candidates[:10] if candidates else []
        scored_sample = ranker.score_articles(sample_candidates, user_id)
        
        return {
            "user_id": user_id,
            "candidates_found": len(candidates),
            "user_embedding_available": user_emb_available,
            "sample_scores": scored_sample,
            "bandit_config": {
                "epsilon": bandit.epsilon,
                "mmr_lambda": bandit.mmr_lambda,
                "enabled": bandit.enabled
            },
            "model_loaded": ranker.model is not None,
            "model_id": ranker.model_id
        }
        
    except Exception as e:
        logger.error(f"Debug error: {e}")
        raise HTTPException(status_code=500, detail=str(e))