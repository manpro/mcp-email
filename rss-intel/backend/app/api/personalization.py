"""
Personalization API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from ..deps import get_db
from ..ml.personalization import PersonalizationEngine
from ..store import Article, Prediction, MLModel

router = APIRouter()


class TrainingResult(BaseModel):
    success: bool
    auc: Optional[float] = None
    training_samples: Optional[int] = None
    positive_samples: Optional[int] = None
    error: Optional[str] = None


class RecommendationResponse(BaseModel):
    article_id: int
    title: str
    url: str
    source: str
    published_at: datetime
    score_total: int
    read_probability: float
    recommendation_reason: List[str]
    has_image: bool
    image_proxy_path: Optional[str]


@router.post("/personalization/train", response_model=TrainingResult)
async def train_personalization_model(
    lookback_days: int = Query(30, ge=7, le=90, description="Days of data to use for training"),
    db: Session = Depends(get_db)
):
    """Train the personalization model"""
    
    engine = PersonalizationEngine(db)
    result = engine.train_model(lookback_days=lookback_days)
    
    return TrainingResult(**result)


@router.get("/personalization/recommendations")
async def get_personalized_recommendations(
    limit: int = Query(20, ge=1, le=100, description="Number of recommendations"),
    min_score: Optional[int] = Query(None, description="Minimum article score"),
    days_back: int = Query(7, ge=1, le=30, description="Days to look back for articles"),
    db: Session = Depends(get_db)
):
    """Get personalized article recommendations"""
    
    from datetime import timedelta
    from sqlalchemy import text
    
    # Get articles with predictions from recent days
    since_date = datetime.utcnow() - timedelta(days=days_back)
    
    # Query for articles with predictions, ordered by read probability
    query = """
        SELECT DISTINCT a.id, a.title, a.url, a.source, a.published_at, 
               a.score_total, a.has_image, a.image_proxy_path,
               p.score as read_probability,
               p.features
        FROM articles a
        JOIN predictions p ON p.article_id = a.id
        JOIN ml_models m ON m.id = p.model_id
        WHERE m.model_type = 'personalization' 
        AND m.is_active = true
        AND a.published_at >= :since_date
        AND (:min_score IS NULL OR a.score_total >= :min_score)
        ORDER BY p.score DESC, a.score_total DESC, a.published_at DESC
        LIMIT :limit
    """
    
    results = db.execute(text(query), {
        "since_date": since_date,
        "min_score": min_score,
        "limit": limit
    }).fetchall()
    
    recommendations = []
    for row in results:
        # Generate recommendation reasons based on features
        reasons = []
        features = row.features or {}
        
        if features.get('score_total', 0) > 50:
            reasons.append("High relevance score")
        if features.get('has_image'):
            reasons.append("Has image")
        if features.get('recency_score', 0) > 0.8:
            reasons.append("Recently published")
        if features.get('keyword_score', 0) > 20:
            reasons.append("Matches your interests")
        if features.get('watchlist_score', 0) > 0:
            reasons.append("From watchlisted source")
        if features.get('extraction_success'):
            reasons.append("Full content available")
            
        # Add topic reasons
        for topic in ['ai', 'crypto', 'blockchain', 'fintech', 'tech', 'ml']:
            if features.get(f'topic_{topic}', 0) > 0:
                reasons.append(f"Tagged as {topic.upper()}")
                break  # Only show one topic reason
        
        if not reasons:
            reasons.append("Recommended for you")
        
        recommendation = RecommendationResponse(
            article_id=row.id,
            title=row.title,
            url=row.url,
            source=row.source,
            published_at=row.published_at,
            score_total=row.score_total,
            read_probability=float(row.read_probability),
            recommendation_reason=reasons[:3],  # Limit to top 3 reasons
            has_image=bool(row.has_image),
            image_proxy_path=row.image_proxy_path
        )
        
        recommendations.append(recommendation)
    
    return {
        "recommendations": recommendations,
        "total": len(recommendations),
        "generated_at": datetime.utcnow(),
        "parameters": {
            "limit": limit,
            "min_score": min_score,
            "days_back": days_back
        }
    }


@router.post("/personalization/score-batch")
async def score_articles_batch(
    article_ids: List[int],
    db: Session = Depends(get_db)
):
    """Score a batch of articles with personalization model"""
    
    if len(article_ids) > 500:
        raise HTTPException(status_code=400, detail="Maximum 500 articles per batch")
    
    engine = PersonalizationEngine(db)
    result = engine.score_articles_batch(article_ids)
    
    if 'error' in result:
        raise HTTPException(status_code=500, detail=result['error'])
    
    return result


@router.get("/personalization/status")
async def get_personalization_status(db: Session = Depends(get_db)):
    """Get personalization system status"""
    
    from sqlalchemy import func
    from ..store import Event
    
    # Get active model info
    active_model = db.query(MLModel).filter_by(
        model_type='personalization',
        is_active=True
    ).first()
    
    # Count events and predictions
    total_events = db.query(func.count(Event.id)).scalar() or 0
    total_predictions = db.query(func.count(Prediction.id)).scalar() or 0
    
    # Count articles with predictions
    articles_with_predictions = db.execute(text("""
        SELECT COUNT(DISTINCT p.article_id) 
        FROM predictions p 
        JOIN ml_models m ON m.id = p.model_id 
        WHERE m.model_type = 'personalization' AND m.is_active = true
    """)).scalar() or 0
    
    status = {
        "model_active": active_model is not None,
        "total_events": total_events,
        "total_predictions": total_predictions,
        "articles_with_predictions": articles_with_predictions
    }
    
    if active_model:
        status.update({
            "model_version": active_model.version,
            "model_created": active_model.created_at,
            "model_metrics": active_model.metrics,
            "model_params": active_model.params
        })
    
    return status