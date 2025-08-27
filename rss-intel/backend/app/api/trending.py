"""
Trending Analysis API Endpoints

API endpoints for trending topic analysis, viral content detection,
and topic clustering functionality.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, or_
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, Field

from ..deps import get_db
from ..services.trending_analysis_service import get_trending_analysis_service
from ..models.trending import TrendingTopic, TopicCluster, ViralContent, TopicAnalysis
from ..store import Article

logger = logging.getLogger(__name__)
router = APIRouter()

class TrendingTopicModel(BaseModel):
    """Trending topic model for API responses"""
    id: int
    topic_name: str
    topic_type: str
    trend_score: float
    velocity: float
    article_count: int
    unique_sources: int
    engagement_score: float
    trend_direction: str
    confidence: float
    age_hours: float
    keywords: List[str]
    is_viral: bool

class TopicClusterModel(BaseModel):
    """Topic cluster model for API responses"""
    id: int
    cluster_name: str
    keywords: List[str]
    size: int
    coherence_score: float
    timespan_hours: float
    source_diversity: float
    unique_sources: int

class ViralContentModel(BaseModel):
    """Viral content model for API responses"""
    id: int
    article_id: int
    viral_score: float
    engagement_rate: float
    viral_intensity: str
    detected_at: str
    viral_duration_hours: Optional[float]
    viral_triggers: List[str]

class TrendAnalysisRequest(BaseModel):
    """Request model for trend analysis"""
    hours_back: int = Field(24, ge=1, le=168)
    min_articles: int = Field(3, ge=1, le=20)
    min_sources: int = Field(2, ge=1, le=10)
    include_predictions: bool = Field(True)
    save_results: bool = Field(True)

@router.get("/trending/topics")
async def get_trending_topics(
    limit: int = Query(20, ge=1, le=100),
    min_score: float = Query(0.3, ge=0.0, le=1.0),
    topic_type: Optional[str] = Query(None, regex="^(keyword|emerging|hashtag)$"),
    trend_direction: Optional[str] = Query(None, regex="^(rising|stable|declining)$"),
    hours_back: int = Query(24, ge=1, le=168),
    db: Session = Depends(get_db)
):
    """Get current trending topics"""
    try:
        # Build query
        cutoff_time = datetime.now() - timedelta(hours=hours_back)
        
        query = db.query(TrendingTopic).filter(
            TrendingTopic.is_active == True,
            TrendingTopic.trend_score >= min_score,
            TrendingTopic.first_detected_at >= cutoff_time
        )
        
        if topic_type:
            query = query.filter(TrendingTopic.topic_type == topic_type)
        
        if trend_direction:
            query = query.filter(TrendingTopic.trend_direction == trend_direction)
        
        trending_topics = query.order_by(
            desc(TrendingTopic.trend_score)
        ).limit(limit).all()
        
        # Convert to API format
        topics_response = []
        for topic in trending_topics:
            topics_response.append(TrendingTopicModel(
                id=topic.id,
                topic_name=topic.topic_name,
                topic_type=topic.topic_type,
                trend_score=topic.trend_score,
                velocity=topic.velocity,
                article_count=topic.article_count,
                unique_sources=topic.unique_sources,
                engagement_score=topic.engagement_score,
                trend_direction=topic.trend_direction,
                confidence=topic.confidence,
                age_hours=topic.age_hours,
                keywords=topic.keywords or [],
                is_viral=topic.is_viral
            ))
        
        return {
            "trending_topics": topics_response,
            "total_found": len(topics_response),
            "analysis_period_hours": hours_back,
            "filters": {
                "min_score": min_score,
                "topic_type": topic_type,
                "trend_direction": trend_direction
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get trending topics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/trending/clusters")
async def get_topic_clusters(
    limit: int = Query(10, ge=1, le=50),
    min_size: int = Query(3, ge=1, le=50),
    min_coherence: float = Query(0.3, ge=0.0, le=1.0),
    hours_back: int = Query(24, ge=1, le=168),
    db: Session = Depends(get_db)
):
    """Get topic clusters"""
    try:
        cutoff_time = datetime.now() - timedelta(hours=hours_back)
        
        clusters = db.query(TopicCluster).filter(
            TopicCluster.created_at >= cutoff_time,
            TopicCluster.size >= min_size,
            TopicCluster.coherence_score >= min_coherence
        ).order_by(
            desc(TopicCluster.coherence_score),
            desc(TopicCluster.size)
        ).limit(limit).all()
        
        # Convert to API format
        clusters_response = []
        for cluster in clusters:
            clusters_response.append(TopicClusterModel(
                id=cluster.id,
                cluster_name=cluster.cluster_name,
                keywords=cluster.keywords or [],
                size=cluster.size,
                coherence_score=cluster.coherence_score,
                timespan_hours=cluster.timespan_hours,
                source_diversity=cluster.source_diversity,
                unique_sources=cluster.unique_sources
            ))
        
        return {
            "topic_clusters": clusters_response,
            "total_found": len(clusters_response),
            "analysis_period_hours": hours_back,
            "filters": {
                "min_size": min_size,
                "min_coherence": min_coherence
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get topic clusters: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/trending/viral")
async def get_viral_content(
    limit: int = Query(20, ge=1, le=100),
    min_viral_score: float = Query(0.5, ge=0.0, le=1.0),
    hours_back: int = Query(24, ge=1, le=168),
    db: Session = Depends(get_db)
):
    """Get viral content"""
    try:
        cutoff_time = datetime.now() - timedelta(hours=hours_back)
        
        viral_content = db.query(ViralContent).filter(
            ViralContent.detected_at >= cutoff_time,
            ViralContent.viral_score >= min_viral_score,
            ViralContent.is_still_viral == True
        ).order_by(
            desc(ViralContent.viral_score)
        ).limit(limit).all()
        
        # Convert to API format
        viral_response = []
        for content in viral_content:
            viral_response.append(ViralContentModel(
                id=content.id,
                article_id=content.article_id,
                viral_score=content.viral_score,
                engagement_rate=content.engagement_rate,
                viral_intensity=content.viral_intensity,
                detected_at=content.detected_at.isoformat(),
                viral_duration_hours=content.viral_duration_hours,
                viral_triggers=content.viral_triggers or []
            ))
        
        return {
            "viral_content": viral_response,
            "total_found": len(viral_response),
            "analysis_period_hours": hours_back,
            "min_viral_score": min_viral_score
        }
        
    except Exception as e:
        logger.error(f"Failed to get viral content: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/trending/analyze")
async def run_trending_analysis(
    request: TrendAnalysisRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Run comprehensive trending analysis"""
    try:
        service = get_trending_analysis_service(db)
        
        # Start analysis in background
        background_tasks.add_task(
            run_trending_analysis_task,
            service,
            request.hours_back,
            request.min_articles,
            request.min_sources,
            request.include_predictions,
            request.save_results
        )
        
        return {
            "message": "Trending analysis started",
            "hours_back": request.hours_back,
            "parameters": {
                "min_articles": request.min_articles,
                "min_sources": request.min_sources,
                "include_predictions": request.include_predictions,
                "save_results": request.save_results
            },
            "status": "background_task_started"
        }
        
    except Exception as e:
        logger.error(f"Failed to start trending analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/trending/analysis/history")
async def get_analysis_history(
    limit: int = Query(10, ge=1, le=50),
    analysis_type: Optional[str] = Query(None, regex="^(trending|clustering|comprehensive)$"),
    db: Session = Depends(get_db)
):
    """Get history of trending analyses"""
    try:
        query = db.query(TopicAnalysis).filter(TopicAnalysis.status == 'completed')
        
        if analysis_type:
            query = query.filter(TopicAnalysis.analysis_type == analysis_type)
        
        analyses = query.order_by(desc(TopicAnalysis.created_at)).limit(limit).all()
        
        # Convert to API format
        history_response = []
        for analysis in analyses:
            history_response.append({
                "id": analysis.id,
                "analysis_type": analysis.analysis_type,
                "time_window_hours": analysis.time_window_hours,
                "articles_analyzed": analysis.articles_analyzed,
                "topics_found": analysis.topics_found,
                "clusters_found": analysis.clusters_found,
                "viral_articles": analysis.viral_articles,
                "analysis_quality_score": analysis.analysis_quality_score,
                "execution_time_seconds": analysis.execution_time_seconds,
                "created_at": analysis.created_at.isoformat(),
                "completed_at": analysis.completed_at.isoformat() if analysis.completed_at else None
            })
        
        return {
            "analyses": history_response,
            "total_found": len(history_response)
        }
        
    except Exception as e:
        logger.error(f"Failed to get analysis history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/trending/stats")
async def get_trending_statistics(
    days_back: int = Query(7, ge=1, le=30),
    db: Session = Depends(get_db)
):
    """Get trending analysis statistics"""
    try:
        cutoff_date = datetime.now() - timedelta(days=days_back)
        
        # Count trending topics by type
        trending_stats = db.query(
            TrendingTopic.topic_type,
            db.func.count(TrendingTopic.id).label('count'),
            db.func.avg(TrendingTopic.trend_score).label('avg_score')
        ).filter(
            TrendingTopic.first_detected_at >= cutoff_date
        ).group_by(TrendingTopic.topic_type).all()
        
        # Count viral content
        viral_count = db.query(ViralContent).filter(
            ViralContent.detected_at >= cutoff_date
        ).count()
        
        # Count topic clusters
        cluster_count = db.query(TopicCluster).filter(
            TopicCluster.created_at >= cutoff_date
        ).count()
        
        # Analysis frequency
        analysis_count = db.query(TopicAnalysis).filter(
            TopicAnalysis.created_at >= cutoff_date,
            TopicAnalysis.status == 'completed'
        ).count()
        
        # Top trending topics
        top_topics = db.query(TrendingTopic).filter(
            TrendingTopic.first_detected_at >= cutoff_date,
            TrendingTopic.is_active == True
        ).order_by(desc(TrendingTopic.trend_score)).limit(5).all()
        
        return {
            "period_days": days_back,
            "trending_topics_by_type": {
                item.topic_type: {
                    "count": item.count,
                    "average_score": round(float(item.avg_score or 0), 3)
                }
                for item in trending_stats
            },
            "viral_articles_detected": viral_count,
            "topic_clusters_created": cluster_count,
            "analyses_completed": analysis_count,
            "top_trending_topics": [
                {
                    "name": topic.topic_name,
                    "score": topic.trend_score,
                    "type": topic.topic_type,
                    "articles": topic.article_count
                }
                for topic in top_topics
            ],
            "generated_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get trending statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/trending/topics/{topic_id}")
async def get_trending_topic_details(
    topic_id: int,
    db: Session = Depends(get_db)
):
    """Get detailed information about a specific trending topic"""
    try:
        topic = db.query(TrendingTopic).filter(TrendingTopic.id == topic_id).first()
        
        if not topic:
            raise HTTPException(status_code=404, detail="Trending topic not found")
        
        # Get related articles
        related_articles = []
        if topic.related_article_ids:
            articles = db.query(Article).filter(
                Article.id.in_(topic.related_article_ids)
            ).all()
            
            for article in articles:
                related_articles.append({
                    "id": article.id,
                    "title": article.title or "Untitled",
                    "url": article.url or "",
                    "source": article.source or "",
                    "published_at": article.published_at.isoformat() if article.published_at else "",
                    "score_total": article.score_total or 0
                })
        
        return {
            "topic": TrendingTopicModel(
                id=topic.id,
                topic_name=topic.topic_name,
                topic_type=topic.topic_type,
                trend_score=topic.trend_score,
                velocity=topic.velocity,
                article_count=topic.article_count,
                unique_sources=topic.unique_sources,
                engagement_score=topic.engagement_score,
                trend_direction=topic.trend_direction,
                confidence=topic.confidence,
                age_hours=topic.age_hours,
                keywords=topic.keywords or [],
                is_viral=topic.is_viral
            ),
            "related_articles": related_articles,
            "first_detected": topic.first_detected_at.isoformat(),
            "peak_time": topic.peak_time.isoformat() if topic.peak_time else None,
            "trend_strength": topic.trend_strength
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get trending topic details: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/trending/topics/{topic_id}")
async def deactivate_trending_topic(
    topic_id: int,
    reason: str = Query(..., description="Reason for deactivation"),
    db: Session = Depends(get_db)
):
    """Deactivate a trending topic"""
    try:
        topic = db.query(TrendingTopic).filter(TrendingTopic.id == topic_id).first()
        
        if not topic:
            raise HTTPException(status_code=404, detail="Trending topic not found")
        
        topic.is_active = False
        topic.updated_at = datetime.now()
        db.commit()
        
        return {
            "message": "Trending topic deactivated",
            "topic_id": topic_id,
            "topic_name": topic.topic_name,
            "reason": reason
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to deactivate trending topic: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/trending/predictions")
async def get_trend_predictions(
    limit: int = Query(10, ge=1, le=50),
    min_confidence: float = Query(0.3, ge=0.0, le=1.0),
    db: Session = Depends(get_db)
):
    """Get active trend predictions"""
    try:
        from ..models.trending import TrendPrediction
        
        predictions = db.query(TrendPrediction).filter(
            TrendPrediction.status == 'active',
            TrendPrediction.confidence_level >= min_confidence,
            TrendPrediction.expires_at > datetime.now()
        ).order_by(
            desc(TrendPrediction.confidence_level)
        ).limit(limit).all()
        
        predictions_response = []
        for pred in predictions:
            predictions_response.append({
                "id": pred.id,
                "topic_name": pred.topic_name,
                "prediction_type": pred.prediction_type,
                "predicted_score": pred.predicted_score,
                "confidence_level": pred.confidence_level,
                "hours_remaining": pred.hours_remaining,
                "based_on_articles": pred.based_on_articles,
                "algorithm_used": pred.algorithm_used,
                "created_at": pred.created_at.isoformat()
            })
        
        return {
            "predictions": predictions_response,
            "total_active": len(predictions_response),
            "min_confidence": min_confidence
        }
        
    except Exception as e:
        logger.error(f"Failed to get trend predictions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Background task functions
async def run_trending_analysis_task(service, hours_back: int, min_articles: int, 
                                    min_sources: int, include_predictions: bool, save_results: bool):
    """Background task for running trending analysis"""
    try:
        # Update service parameters
        service.min_articles_for_trend = min_articles
        service.min_sources_for_trend = min_sources
        
        # Run analysis
        analysis_result = await service.analyze_trending_topics(hours_back)
        
        # Save results if requested
        if save_results:
            await service.save_trending_analysis(analysis_result)
        
        logger.info(f"Trending analysis completed: {len(analysis_result.trending_topics)} topics, "
                   f"{len(analysis_result.topic_clusters)} clusters, {len(analysis_result.viral_articles)} viral articles")
        
    except Exception as e:
        logger.error(f"Trending analysis task failed: {e}")