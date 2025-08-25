"""Real-time learning API endpoints"""
import logging
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..deps import get_db
from ..ml.realtime_learner import RealtimeLearner
from ..auth import require_auth

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/learning", tags=["learning"])

@router.get("/stats")
async def get_learning_stats(
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get real-time learning statistics and status"""
    try:
        learner = RealtimeLearner(db)
        stats = learner.get_learning_stats()
        
        return stats
        
    except Exception as e:
        logger.error(f"Error getting learning stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/feedback")
async def get_recent_feedback(
    hours: int = Query(default=24, ge=1, le=168, description="Hours of feedback to retrieve"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get recent user feedback for learning analysis"""
    try:
        learner = RealtimeLearner(db)
        feedback_data = learner.collect_recent_feedback(hours)
        
        # Calculate feedback summary
        total_samples = len(feedback_data)
        positive_samples = sum(1 for f in feedback_data if f['label'] == 1)
        
        # Group by event type
        event_type_counts = {}
        for f in feedback_data:
            event_type = f['event_type']
            event_type_counts[event_type] = event_type_counts.get(event_type, 0) + 1
        
        # Group by user
        user_activity = {}
        for f in feedback_data:
            user_id = f['user_id']
            if user_id not in user_activity:
                user_activity[user_id] = {'total': 0, 'positive': 0}
            user_activity[user_id]['total'] += 1
            if f['label'] == 1:
                user_activity[user_id]['positive'] += 1
        
        return {
            'period_hours': hours,
            'summary': {
                'total_samples': total_samples,
                'positive_samples': positive_samples,
                'positive_rate': round(positive_samples / max(1, total_samples), 3),
                'unique_users': len(user_activity),
                'unique_articles': len(set(f['article_id'] for f in feedback_data))
            },
            'event_breakdown': event_type_counts,
            'user_activity': {
                user_id: {
                    **activity,
                    'engagement_rate': round(activity['positive'] / max(1, activity['total']), 3)
                }
                for user_id, activity in user_activity.items()
            },
            'recent_samples': feedback_data[:10]  # Show last 10 samples
        }
        
    except Exception as e:
        logger.error(f"Error getting recent feedback: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/update")
async def trigger_model_update(
    force: bool = Query(default=False, description="Force update even if not needed"),
    current_user: Dict[str, Any] = Depends(require_auth),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Trigger an incremental model update"""
    try:
        learner = RealtimeLearner(db)
        
        # Check if update is needed
        if not force and not learner.should_update_model():
            return {
                'status': 'skipped',
                'message': 'Model update not needed at this time',
                'should_update': False,
                'stats': learner.get_learning_stats()
            }
        
        # Perform incremental update
        success = learner.perform_incremental_update()
        
        if success:
            logger.info(f"Model update triggered by user {current_user['username']}")
            return {
                'status': 'success',
                'message': 'Model updated successfully',
                'updated_by': current_user['username'],
                'stats': learner.get_learning_stats()
            }
        else:
            return {
                'status': 'failed',
                'message': 'Model update failed or not supported',
                'error': 'See logs for details'
            }
        
    except Exception as e:
        logger.error(f"Error triggering model update: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def check_learning_health(
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Check health of the real-time learning system"""
    try:
        learner = RealtimeLearner(db)
        
        # Check if we have recent feedback
        recent_feedback = learner.collect_recent_feedback(24)
        feedback_health = len(recent_feedback) > 0
        
        # Check model status
        stats = learner.get_learning_stats()
        model_loaded = stats.get('model_info', {}).get('name') != 'No active model'
        
        # Check if update is overdue
        model_fresh = not learner.should_update_model()
        
        health_score = sum([feedback_health, model_loaded, model_fresh]) / 3
        
        status = 'healthy' if health_score >= 0.8 else 'degraded' if health_score >= 0.5 else 'unhealthy'
        
        return {
            'status': status,
            'health_score': round(health_score, 2),
            'checks': {
                'recent_feedback': {
                    'status': 'pass' if feedback_health else 'fail',
                    'message': f"Found {len(recent_feedback)} feedback samples in last 24h"
                },
                'model_loaded': {
                    'status': 'pass' if model_loaded else 'fail',
                    'message': 'Active ML model available' if model_loaded else 'No active model'
                },
                'model_freshness': {
                    'status': 'pass' if model_fresh else 'warn',
                    'message': 'Model is up to date' if model_fresh else 'Model update recommended'
                }
            },
            'recommendations': [
                'Model update recommended' if not model_fresh else None,
                'No recent feedback - check user engagement' if not feedback_health else None,
                'Load or train ML model' if not model_loaded else None
            ]
        }
        
    except Exception as e:
        logger.error(f"Error checking learning health: {e}")
        return {
            'status': 'unhealthy',
            'error': str(e),
            'health_score': 0.0
        }