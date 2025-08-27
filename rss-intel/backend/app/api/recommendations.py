"""
Personalized Recommendations API

Provides AI-powered content recommendations based on user behavior,
reading patterns, and ML predictions.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc, text
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, Field

from ..deps import get_db
from ..store import Article, Story, Prediction
from ..events import Event

logger = logging.getLogger(__name__)
router = APIRouter()

class RecommendationReason(BaseModel):
    """Reason why an article was recommended"""
    type: str  # 'ml_score', 'trending', 'topic_match', 'source_affinity', 'time_preference', 'similar_read'
    description: str
    confidence: float = Field(ge=0.0, le=1.0)

class RecommendedArticle(BaseModel):
    """Article with recommendation metadata"""
    id: int
    title: str
    url: str
    source: str
    published_at: datetime
    score: Optional[int]
    content: Optional[str]
    image_proxy_path: Optional[str]
    story_id: Optional[int]
    recommendation_score: float
    reasons: List[RecommendationReason]
    explanation: str

class RecommendationsResponse(BaseModel):
    """Response containing personalized recommendations"""
    articles: List[RecommendedArticle]
    generated_at: datetime
    user_preferences: Dict[str, Any]
    total_candidates: int
    filtering_stats: Dict[str, int]

@router.get("/recommendations", response_model=RecommendationsResponse)
async def get_recommendations(
    limit: int = Query(30, ge=1, le=100),
    min_confidence: float = Query(0.5, ge=0.0, le=1.0),
    include_reasons: bool = Query(True),
    hours_back: int = Query(48, ge=1, le=168),
    db: Session = Depends(get_db)
):
    """
    Get personalized article recommendations based on ML predictions and user behavior
    """
    try:
        since = datetime.now() - timedelta(hours=hours_back)
        user_preferences = await analyze_user_preferences(db)
        
        # Get ML predictions for recent articles
        predictions_query = db.query(
            Prediction.article_id,
            Prediction.p_read,
            Prediction.model_version,
            Article
        ).join(
            Article, Article.id == Prediction.article_id
        ).filter(
            and_(
                Article.published_at >= since,
                Prediction.p_read >= min_confidence,
                Article.spam_detected != True
            )
        ).order_by(
            desc(Prediction.p_read),
            desc(Article.published_at)
        )
        
        # Get trending articles
        trending_query = db.query(
            Article,
            func.count(Event.id).label('event_count')
        ).outerjoin(
            Event, Event.article_id == Article.id
        ).filter(
            and_(
                Article.published_at >= since,
                Article.spam_detected != True
            )
        ).group_by(Article.id).having(
            func.count(Event.id) > 0
        ).order_by(desc('event_count'))
        
        predictions = predictions_query.limit(limit * 3).all()
        trending = trending_query.limit(limit).all()
        
        # Build recommendation list
        recommendations = []
        seen_article_ids = set()
        
        # Add ML-predicted articles
        for pred in predictions:
            if pred.article_id not in seen_article_ids:
                article = pred.Article
                reasons = []
                
                # ML prediction reason
                reasons.append(RecommendationReason(
                    type="ml_score",
                    description=f"AI predicts {pred.p_read:.0%} chance you'll read this",
                    confidence=pred.p_read
                ))
                
                # Check for trending
                if any(t[0].id == article.id for t in trending[:10]):
                    reasons.append(RecommendationReason(
                        type="trending",
                        description="Currently trending in your network",
                        confidence=0.8
                    ))
                
                # Topic matching
                if user_preferences.get('favorite_topics'):
                    for topic in user_preferences['favorite_topics']:
                        if topic.lower() in (article.title or '').lower() or \
                           topic.lower() in (article.content or '')[:500].lower():
                            reasons.append(RecommendationReason(
                                type="topic_match",
                                description=f"Matches your interest in {topic}",
                                confidence=0.7
                            ))
                            break
                
                # Source affinity
                if article.source in user_preferences.get('favorite_sources', []):
                    reasons.append(RecommendationReason(
                        type="source_affinity",
                        description=f"From frequently read source: {article.source}",
                        confidence=0.6
                    ))
                
                # Time preference
                hour = article.published_at.hour
                if hour in user_preferences.get('preferred_reading_hours', []):
                    reasons.append(RecommendationReason(
                        type="time_preference",
                        description="Published during your typical reading time",
                        confidence=0.5
                    ))
                
                # Calculate combined recommendation score
                recommendation_score = calculate_recommendation_score(pred.p_read, reasons)
                
                # Generate explanation
                explanation = generate_explanation(article, reasons, user_preferences)
                
                recommendations.append(RecommendedArticle(
                    id=article.id,
                    title=article.title,
                    url=article.url,
                    source=article.source,
                    published_at=article.published_at,
                    score=article.score,
                    content=article.content[:500] if article.content else None,
                    image_proxy_path=article.image_proxy_path,
                    story_id=article.story_id,
                    recommendation_score=recommendation_score,
                    reasons=reasons if include_reasons else [],
                    explanation=explanation
                ))
                
                seen_article_ids.add(article.id)
                
                if len(recommendations) >= limit:
                    break
        
        # Add trending articles not in ML predictions
        for article, event_count in trending:
            if article.id not in seen_article_ids and len(recommendations) < limit:
                reasons = [
                    RecommendationReason(
                        type="trending",
                        description=f"Trending with {event_count} interactions",
                        confidence=min(0.9, event_count / 10)
                    )
                ]
                
                recommendation_score = 0.6 + min(0.3, event_count / 20)
                
                recommendations.append(RecommendedArticle(
                    id=article.id,
                    title=article.title,
                    url=article.url,
                    source=article.source,
                    published_at=article.published_at,
                    score=article.score,
                    content=article.content[:500] if article.content else None,
                    image_proxy_path=article.image_proxy_path,
                    story_id=article.story_id,
                    recommendation_score=recommendation_score,
                    reasons=reasons if include_reasons else [],
                    explanation="Trending in your network"
                ))
                
                seen_article_ids.add(article.id)
        
        # Sort by recommendation score
        recommendations.sort(key=lambda x: x.recommendation_score, reverse=True)
        
        return RecommendationsResponse(
            articles=recommendations,
            generated_at=datetime.now(),
            user_preferences=user_preferences,
            total_candidates=len(predictions) + len(trending),
            filtering_stats={
                'ml_predicted': len([r for r in recommendations if any(reason.type == 'ml_score' for reason in r.reasons)]),
                'trending': len([r for r in recommendations if any(reason.type == 'trending' for reason in r.reasons)]),
                'topic_matched': len([r for r in recommendations if any(reason.type == 'topic_match' for reason in r.reasons)]),
                'source_affinity': len([r for r in recommendations if any(reason.type == 'source_affinity' for reason in r.reasons)])
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to generate recommendations: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def analyze_user_preferences(db: Session) -> Dict[str, Any]:
    """Analyze user reading patterns to understand preferences"""
    try:
        # Get recent user events
        recent_events = db.query(Event).filter(
            Event.created_at >= datetime.now() - timedelta(days=30)
        ).all()
        
        # Analyze reading patterns
        source_counts = {}
        topic_keywords = {}
        reading_hours = []
        
        for event in recent_events:
            if event.event_type in ['open', 'star']:
                article = db.query(Article).filter(Article.id == event.article_id).first()
                if article:
                    # Track sources
                    source_counts[article.source] = source_counts.get(article.source, 0) + 1
                    
                    # Track reading hours
                    reading_hours.append(event.created_at.hour)
                    
                    # Extract topic keywords from starred articles
                    if event.event_type == 'star' and article.title:
                        words = article.title.lower().split()
                        for word in words:
                            if len(word) > 4:  # Skip short words
                                topic_keywords[word] = topic_keywords.get(word, 0) + 1
        
        # Identify preferences
        favorite_sources = sorted(source_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        favorite_topics = sorted(topic_keywords.items(), key=lambda x: x[1], reverse=True)[:10]
        
        # Identify preferred reading hours
        hour_counts = {}
        for hour in reading_hours:
            hour_counts[hour] = hour_counts.get(hour, 0) + 1
        preferred_hours = [h for h, c in hour_counts.items() if c >= 3]
        
        return {
            'favorite_sources': [s for s, _ in favorite_sources],
            'favorite_topics': [t for t, _ in favorite_topics],
            'preferred_reading_hours': preferred_hours,
            'total_events': len(recent_events),
            'analysis_period_days': 30
        }
        
    except Exception as e:
        logger.warning(f"Failed to analyze user preferences: {e}")
        return {
            'favorite_sources': [],
            'favorite_topics': [],
            'preferred_reading_hours': [],
            'total_events': 0,
            'analysis_period_days': 30
        }

def calculate_recommendation_score(ml_score: float, reasons: List[RecommendationReason]) -> float:
    """Calculate combined recommendation score from ML and other signals"""
    # Start with ML score as base
    score = ml_score * 0.6  # ML contributes 60%
    
    # Add bonuses for additional reasons
    for reason in reasons:
        if reason.type == 'trending':
            score += reason.confidence * 0.2
        elif reason.type == 'topic_match':
            score += reason.confidence * 0.15
        elif reason.type == 'source_affinity':
            score += reason.confidence * 0.1
        elif reason.type == 'time_preference':
            score += reason.confidence * 0.05
    
    return min(1.0, score)  # Cap at 1.0

def generate_explanation(article: Article, reasons: List[RecommendationReason], preferences: Dict[str, Any]) -> str:
    """Generate human-readable explanation for recommendation"""
    explanations = []
    
    # Find the strongest reason
    if reasons:
        strongest = max(reasons, key=lambda r: r.confidence)
        
        if strongest.type == 'ml_score':
            explanations.append("Our AI thinks you'll find this interesting")
        elif strongest.type == 'trending':
            explanations.append("This is trending right now")
        elif strongest.type == 'topic_match':
            topics = [t for t in preferences.get('favorite_topics', []) 
                     if t.lower() in (article.title or '').lower()]
            if topics:
                explanations.append(f"Related to your interest in {topics[0]}")
        elif strongest.type == 'source_affinity':
            explanations.append(f"From {article.source}, a source you read often")
    
    # Add secondary reasons
    if len(reasons) > 1:
        if any(r.type == 'trending' for r in reasons[1:]):
            explanations.append("and it's popular")
        if any(r.type == 'topic_match' for r in reasons[1:]):
            explanations.append("matching your interests")
    
    return " ".join(explanations) if explanations else "Recommended based on your reading patterns"

@router.get("/recommendations/feedback")
async def get_recommendation_feedback(
    days: int = Query(7, ge=1, le=30),
    db: Session = Depends(get_db)
):
    """Get feedback metrics on recommendation performance"""
    try:
        since = datetime.now() - timedelta(days=days)
        
        # Get events on recommended articles
        recommendation_events = db.query(Event).filter(
            and_(
                Event.created_at >= since,
                Event.event_metadata.has_key('from_recommendations')
            )
        ).all()
        
        # Calculate metrics
        total_recommendations = len(recommendation_events)
        opens = len([e for e in recommendation_events if e.event_type == 'open'])
        stars = len([e for e in recommendation_events if e.event_type == 'star'])
        dismissals = len([e for e in recommendation_events if e.event_type == 'dismiss'])
        
        engagement_rate = (opens + stars) / max(total_recommendations, 1)
        star_rate = stars / max(opens, 1) if opens > 0 else 0
        
        return {
            'period_days': days,
            'total_recommendations_interacted': total_recommendations,
            'opens': opens,
            'stars': stars,
            'dismissals': dismissals,
            'engagement_rate': round(engagement_rate, 3),
            'star_rate': round(star_rate, 3),
            'metrics': {
                'click_through_rate': round(opens / max(total_recommendations, 1), 3),
                'save_rate': round(stars / max(total_recommendations, 1), 3),
                'dismiss_rate': round(dismissals / max(total_recommendations, 1), 3)
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get recommendation feedback: {e}")
        raise HTTPException(status_code=500, detail=str(e))