"""User interest profiling and personalization dashboard API"""
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text

from ..deps import get_db
from ..ml.advanced_ranker import AdvancedArticleRanker
from ..personalization_service import get_personalization_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/profile", tags=["user_profile"])

@router.get("/interests/{user_id}")
async def get_user_interests(
    user_id: str,
    days: int = Query(default=30, ge=1, le=365, description="Days to analyze"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get detailed user interest profile and behavior analysis
    """
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        
        # User activity summary
        activity_result = db.execute(text("""
            SELECT 
                COUNT(*) as total_events,
                COUNT(DISTINCT article_id) as unique_articles,
                COUNT(DISTINCT DATE(created_at)) as active_days,
                COUNT(CASE WHEN type = 'star' THEN 1 END) as stars,
                COUNT(CASE WHEN type = 'external_click' THEN 1 END) as clicks,
                COUNT(CASE WHEN type = 'open' THEN 1 END) as opens,
                COUNT(CASE WHEN type = 'dismiss' THEN 1 END) as dismisses,
                AVG(CASE WHEN type = 'open' AND duration_ms > 0 THEN duration_ms END) as avg_dwell_ms
            FROM events 
            WHERE user_id = :user_id 
            AND created_at > :cutoff
        """), {"user_id": user_id, "cutoff": cutoff})
        
        activity_row = activity_result.fetchone()
        
        if not activity_row or activity_row.total_events == 0:
            return {
                "user_id": user_id,
                "days_analyzed": days,
                "message": "No activity found for this user in the specified period"
            }
        
        # Source preferences
        source_result = db.execute(text("""
            SELECT 
                a.source,
                COUNT(*) as interactions,
                COUNT(CASE WHEN e.type = 'star' THEN 1 END) as stars,
                COUNT(CASE WHEN e.type = 'external_click' THEN 1 END) as clicks,
                AVG(a.score_total) as avg_article_score,
                AVG(CASE WHEN e.type = 'open' AND e.duration_ms > 0 THEN e.duration_ms END) as avg_dwell_ms
            FROM events e
            JOIN articles a ON e.article_id = a.id
            WHERE e.user_id = :user_id 
            AND e.created_at > :cutoff
            GROUP BY a.source
            ORDER BY interactions DESC
            LIMIT 15
        """), {"user_id": user_id, "cutoff": cutoff})
        
        source_preferences = []
        for row in source_result:
            engagement_rate = (row.stars + row.clicks) / max(1, row.interactions)
            source_preferences.append({
                "source": row.source,
                "interactions": row.interactions,
                "stars": row.stars or 0,
                "clicks": row.clicks or 0,
                "engagement_rate": round(engagement_rate, 3),
                "avg_article_score": round(float(row.avg_article_score or 0), 1),
                "avg_dwell_seconds": round((row.avg_dwell_ms or 0) / 1000, 1)
            })
        
        # Topic interests
        topic_result = db.execute(text("""
            SELECT 
                unnest(a.topics) as topic,
                COUNT(*) as interactions,
                COUNT(CASE WHEN e.type IN ('star', 'external_click') THEN 1 END) as positive_interactions,
                AVG(a.score_total) as avg_score
            FROM events e
            JOIN articles a ON e.article_id = a.id
            WHERE e.user_id = :user_id 
            AND e.created_at > :cutoff
            AND a.topics IS NOT NULL
            GROUP BY unnest(a.topics)
            HAVING COUNT(*) >= 2
            ORDER BY positive_interactions DESC, interactions DESC
            LIMIT 20
        """), {"user_id": user_id, "cutoff": cutoff})
        
        topic_interests = []
        for row in topic_result:
            interest_score = row.positive_interactions / max(1, row.interactions)
            topic_interests.append({
                "topic": row.topic,
                "interactions": row.interactions,
                "positive_interactions": row.positive_interactions,
                "interest_score": round(interest_score, 3),
                "avg_article_score": round(float(row.avg_score or 0), 1)
            })
        
        # Engagement patterns by time
        time_pattern_result = db.execute(text("""
            SELECT 
                EXTRACT(HOUR FROM created_at) as hour,
                COUNT(*) as events,
                COUNT(CASE WHEN type IN ('star', 'external_click') THEN 1 END) as engaged_events
            FROM events 
            WHERE user_id = :user_id 
            AND created_at > :cutoff
            GROUP BY EXTRACT(HOUR FROM created_at)
            ORDER BY hour
        """), {"user_id": user_id, "cutoff": cutoff})
        
        hourly_patterns = []
        for row in time_pattern_result:
            engagement_rate = row.engaged_events / max(1, row.events)
            hourly_patterns.append({
                "hour": int(row.hour),
                "events": row.events,
                "engagement_rate": round(engagement_rate, 3)
            })
        
        # ML model predictions for recent articles
        ranker = AdvancedArticleRanker(db)
        model_info = ranker.get_model_info()
        
        # Get some recent predictions
        prediction_result = db.execute(text("""
            SELECT 
                p.article_id,
                p.p_read,
                a.title,
                a.source,
                a.score_total,
                a.published_at
            FROM predictions p
            JOIN articles a ON p.article_id = a.id
            JOIN ml_models m ON p.model_id = m.id
            WHERE m.is_active = true
            AND p.created_at > :cutoff
            ORDER BY p.p_read DESC
            LIMIT 10
        """), {"cutoff": cutoff})
        
        recent_predictions = []
        for row in prediction_result:
            recent_predictions.append({
                "article_id": row.article_id,
                "title": row.title[:80] + "..." if len(row.title) > 80 else row.title,
                "source": row.source,
                "p_read": round(row.p_read, 3),
                "rule_score": row.score_total,
                "published_at": row.published_at.isoformat()
            })
        
        # Overall engagement metrics
        total_events = activity_row.total_events
        engagement_rate = (activity_row.stars + activity_row.clicks) / max(1, total_events)
        activity_frequency = activity_row.active_days / days
        
        return {
            "user_id": user_id,
            "analysis_period": {
                "days": days,
                "start_date": cutoff.isoformat(),
                "end_date": datetime.now(timezone.utc).isoformat()
            },
            "activity_summary": {
                "total_events": total_events,
                "unique_articles": activity_row.unique_articles,
                "active_days": activity_row.active_days,
                "activity_frequency": round(activity_frequency, 2),
                "engagement_rate": round(engagement_rate, 3),
                "avg_dwell_seconds": round((activity_row.avg_dwell_ms or 0) / 1000, 1),
                "breakdown": {
                    "stars": activity_row.stars or 0,
                    "clicks": activity_row.clicks or 0,
                    "opens": activity_row.opens or 0,
                    "dismisses": activity_row.dismisses or 0
                }
            },
            "source_preferences": source_preferences,
            "topic_interests": topic_interests,
            "hourly_engagement": hourly_patterns,
            "ml_personalization": {
                **model_info,
                "recent_predictions": recent_predictions,
                "prediction_quality": "High" if model_info['model_loaded'] else "Fallback"
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting user interests for {user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/recommendations/explain/{user_id}")
async def explain_recommendations(
    user_id: str,
    article_ids: str = Query(..., description="Comma-separated article IDs"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Explain why specific articles were recommended to a user
    """
    try:
        article_id_list = [int(id.strip()) for id in article_ids.split(',')]
        
        ranker = AdvancedArticleRanker(db)
        
        if not ranker.model:
            return {
                "user_id": user_id,
                "error": "No ML model available for explanations"
            }
        
        # Get article details and scores
        explanations = []
        
        for article_id in article_id_list:
            # Get article info
            article_result = db.execute(text("""
                SELECT title, source, topics, score_total, published_at, has_image
                FROM articles 
                WHERE id = :article_id
            """), {"article_id": article_id})
            
            article_row = article_result.fetchone()
            if not article_row:
                continue
            
            # Get ML prediction if available
            pred_result = db.execute(text("""
                SELECT p.p_read, p.created_at
                FROM predictions p
                JOIN ml_models m ON p.model_id = m.id
                WHERE p.article_id = :article_id
                AND m.is_active = true
                ORDER BY p.created_at DESC
                LIMIT 1
            """), {"article_id": article_id})
            
            pred_row = pred_result.fetchone()
            p_read = pred_row.p_read if pred_row else None
            
            # Get user's history with this source
            source_history = db.execute(text("""
                SELECT 
                    COUNT(*) as interactions,
                    COUNT(CASE WHEN type = 'star' THEN 1 END) as stars,
                    COUNT(CASE WHEN type = 'external_click' THEN 1 END) as clicks
                FROM events e
                JOIN articles a ON e.article_id = a.id
                WHERE e.user_id = :user_id
                AND a.source = :source
                AND e.created_at > NOW() - INTERVAL '30 days'
            """), {"user_id": user_id, "source": article_row.source})
            
            source_row = source_history.fetchone()
            
            # Generate explanation
            explanation_factors = []
            
            if p_read:
                if p_read > 0.7:
                    explanation_factors.append(f"High ML confidence ({p_read:.2f}) - strong match to your reading patterns")
                elif p_read > 0.5:
                    explanation_factors.append(f"Moderate ML confidence ({p_read:.2f}) - good match to your interests")
                else:
                    explanation_factors.append(f"Lower ML confidence ({p_read:.2f}) - exploratory recommendation")
            
            if source_row and source_row.interactions > 0:
                engagement_rate = (source_row.stars + source_row.clicks) / source_row.interactions
                if engagement_rate > 0.3:
                    explanation_factors.append(f"You actively engage with {article_row.source} articles")
                elif source_row.interactions >= 5:
                    explanation_factors.append(f"You frequently read {article_row.source}")
            
            if article_row.score_total > 80:
                explanation_factors.append("High trending score - popular article")
            elif article_row.score_total > 60:
                explanation_factors.append("Good trending score - interesting content")
            
            if article_row.topics:
                # Check topic preferences
                for topic in article_row.topics[:3]:  # Check first 3 topics
                    topic_pref = db.execute(text("""
                        SELECT COUNT(CASE WHEN e.type IN ('star', 'external_click') THEN 1 END) as positive
                        FROM events e
                        JOIN articles a ON e.article_id = a.id
                        WHERE e.user_id = :user_id
                        AND :topic = ANY(a.topics)
                        AND e.created_at > NOW() - INTERVAL '30 days'
                    """), {"user_id": user_id, "topic": topic})
                    
                    topic_row = topic_pref.fetchone()
                    if topic_row and topic_row.positive > 2:
                        explanation_factors.append(f"You show interest in '{topic}' topics")
            
            if not explanation_factors:
                explanation_factors.append("Recommended based on general content quality")
            
            explanations.append({
                "article_id": article_id,
                "title": article_row.title,
                "source": article_row.source,
                "p_read": p_read,
                "rule_score": article_row.score_total,
                "explanation_factors": explanation_factors,
                "topics": article_row.topics[:5] if article_row.topics else []
            })
        
        return {
            "user_id": user_id,
            "explanations": explanations,
            "model_info": ranker.get_model_info()
        }
        
    except Exception as e:
        logger.error(f"Error explaining recommendations: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/feedback/{user_id}")
async def record_user_feedback(
    user_id: str,
    article_id: int,
    feedback_type: str = Query(..., regex="^(like|dislike|not_interested|report)$"),
    reason: str = Query(None, max_length=200),
    db: Session = Depends(get_db)
) -> Dict[str, str]:
    """
    Record user feedback for improving personalization
    """
    try:
        # Map feedback to event types
        event_type_map = {
            "like": "star",
            "dislike": "dismiss", 
            "not_interested": "dismiss",
            "report": "dismiss"
        }
        
        event_type = event_type_map.get(feedback_type, "impression")
        
        # Insert event
        db.execute(text("""
            INSERT INTO events (user_id, article_id, type, created_at)
            VALUES (:user_id, :article_id, :event_type, :created_at)
        """), {
            "user_id": user_id,
            "article_id": article_id,
            "event_type": event_type,
            "created_at": datetime.now(timezone.utc)
        })
        
        db.commit()
        
        logger.info(f"Recorded feedback: {user_id} -> article {article_id}: {feedback_type}")
        
        return {
            "status": "success",
            "message": f"Feedback recorded: {feedback_type}",
            "user_id": user_id,
            "article_id": str(article_id)
        }
        
    except Exception as e:
        logger.error(f"Error recording feedback: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))