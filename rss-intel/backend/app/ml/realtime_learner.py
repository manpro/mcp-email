"""Real-time ML model learning and updates for RSS Intelligence"""
import logging
import pickle
import numpy as np
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
import joblib
import os

from .advanced_features import AdvancedFeatureExtractor
from .advanced_ranker import AdvancedArticleRanker

logger = logging.getLogger(__name__)

class RealtimeLearner:
    """Handles real-time model updates based on user feedback"""
    
    def __init__(self, db: Session):
        self.db = db
        self.feature_extractor = AdvancedFeatureExtractor(db)
        self.ranker = AdvancedArticleRanker(db)
        self.min_samples_for_update = 50  # Minimum new samples before model update
        self.update_frequency_hours = 6   # Update model every 6 hours
        
    def collect_recent_feedback(self, hours: int = 1) -> List[Dict[str, Any]]:
        """Collect recent user feedback for model updates"""
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
            
            # Get recent positive and negative events
            result = self.db.execute(text("""
                SELECT 
                    e.user_id,
                    e.article_id,
                    e.type,
                    e.duration_ms,
                    e.created_at,
                    a.title,
                    a.source,
                    a.published_at,
                    a.score_total,
                    a.topics,
                    a.has_image,
                    a.full_content IS NOT NULL as has_content
                FROM events e
                JOIN articles a ON e.article_id = a.id
                WHERE e.created_at >= :cutoff
                AND e.type IN ('star', 'external_click', 'dismiss', 'open')
                ORDER BY e.created_at DESC
                LIMIT 1000
            """), {"cutoff": cutoff})
            
            feedback_data = []
            for row in result:
                # Convert event type to binary label
                label = self._event_to_label(row.type, row.duration_ms)
                
                feedback_data.append({
                    'user_id': row.user_id,
                    'article_id': row.article_id,
                    'label': label,
                    'event_type': row.type,
                    'duration_ms': row.duration_ms or 0,
                    'timestamp': row.created_at,
                    'article_data': {
                        'title': row.title,
                        'source': row.source,
                        'published_at': row.published_at,
                        'score_total': row.score_total or 0,
                        'topics': row.topics or [],
                        'has_image': row.has_image or False,
                        'has_content': row.has_content
                    }
                })
            
            logger.info(f"Collected {len(feedback_data)} feedback samples from last {hours} hours")
            return feedback_data
            
        except Exception as e:
            logger.error(f"Error collecting recent feedback: {e}")
            return []
    
    def _event_to_label(self, event_type: str, duration_ms: Optional[int]) -> int:
        """Convert event type and duration to binary label (0=negative, 1=positive)"""
        if event_type in ['star', 'external_click']:
            return 1
        elif event_type == 'dismiss':
            return 0
        elif event_type == 'open':
            # Consider opens with duration > 10 seconds as positive
            return 1 if (duration_ms or 0) > 10000 else 0
        else:
            return 0
    
    def should_update_model(self) -> bool:
        """Check if model should be updated based on new data"""
        try:
            # Check when model was last updated
            result = self.db.execute(text("""
                SELECT created_at 
                FROM ml_models 
                WHERE is_active = true
                ORDER BY created_at DESC
                LIMIT 1
            """))
            
            row = result.fetchone()
            if not row:
                logger.info("No active model found, update recommended")
                return True
            
            last_update = row.created_at
            hours_since_update = (datetime.now(timezone.utc) - last_update).total_seconds() / 3600
            
            if hours_since_update >= self.update_frequency_hours:
                logger.info(f"Model last updated {hours_since_update:.1f} hours ago, update needed")
                return True
            
            # Check if we have enough new training samples
            recent_samples = self.collect_recent_feedback(int(hours_since_update))
            if len(recent_samples) >= self.min_samples_for_update:
                logger.info(f"Found {len(recent_samples)} new samples, triggering update")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking model update status: {e}")
            return False
    
    def prepare_incremental_training_data(self, hours_back: int = 24) -> Optional[Dict[str, Any]]:
        """Prepare training data for incremental model update"""
        try:
            feedback_data = self.collect_recent_feedback(hours_back)
            
            if len(feedback_data) < 10:
                logger.warning(f"Not enough samples ({len(feedback_data)}) for incremental training")
                return None
            
            # Extract features for each feedback sample
            features_list = []
            labels = []
            user_ids = []
            article_ids = []
            
            for feedback in feedback_data:
                try:
                    # Get user context for feature extraction
                    user_context = self._get_user_context(feedback['user_id'], feedback['timestamp'])
                    
                    # Extract features
                    features = self.feature_extractor.extract_features(
                        article_data=feedback['article_data'],
                        user_context=user_context
                    )
                    
                    if features is not None and len(features) > 0:
                        features_list.append(features)
                        labels.append(feedback['label'])
                        user_ids.append(feedback['user_id'])
                        article_ids.append(feedback['article_id'])
                        
                except Exception as e:
                    logger.error(f"Error extracting features for article {feedback['article_id']}: {e}")
                    continue
            
            if len(features_list) == 0:
                logger.warning("No valid features extracted from feedback data")
                return None
            
            features_array = np.array(features_list)
            labels_array = np.array(labels)
            
            logger.info(f"Prepared {len(features_array)} samples for incremental training")
            logger.info(f"Feature dimensions: {features_array.shape}")
            logger.info(f"Label distribution: {np.bincount(labels_array)}")
            
            return {
                'features': features_array,
                'labels': labels_array,
                'user_ids': user_ids,
                'article_ids': article_ids,
                'sample_count': len(features_array)
            }
            
        except Exception as e:
            logger.error(f"Error preparing incremental training data: {e}")
            return None
    
    def _get_user_context(self, user_id: str, timestamp: datetime) -> Dict[str, Any]:
        """Get user context for feature extraction at specific time"""
        try:
            # Get user activity before this timestamp
            cutoff = timestamp - timedelta(days=30)
            
            result = self.db.execute(text("""
                SELECT 
                    COUNT(*) as total_events,
                    COUNT(CASE WHEN type = 'star' THEN 1 END) as stars,
                    COUNT(CASE WHEN type = 'external_click' THEN 1 END) as clicks,
                    AVG(CASE WHEN type = 'open' AND duration_ms > 0 THEN duration_ms END) as avg_dwell_ms
                FROM events 
                WHERE user_id = :user_id 
                AND created_at BETWEEN :cutoff AND :timestamp
            """), {"user_id": user_id, "cutoff": cutoff, "timestamp": timestamp})
            
            row = result.fetchone()
            
            # Get top sources and topics for this user
            source_result = self.db.execute(text("""
                SELECT a.source, COUNT(*) as interactions
                FROM events e
                JOIN articles a ON e.article_id = a.id
                WHERE e.user_id = :user_id 
                AND e.created_at BETWEEN :cutoff AND :timestamp
                GROUP BY a.source
                ORDER BY interactions DESC
                LIMIT 5
            """), {"user_id": user_id, "cutoff": cutoff, "timestamp": timestamp})
            
            preferred_sources = [r.source for r in source_result]
            
            return {
                'total_events': row.total_events or 0,
                'stars': row.stars or 0,
                'clicks': row.clicks or 0,
                'avg_dwell_ms': row.avg_dwell_ms or 0,
                'preferred_sources': preferred_sources,
                'activity_level': min((row.total_events or 0) / 100, 1.0)  # Normalized
            }
            
        except Exception as e:
            logger.error(f"Error getting user context for {user_id}: {e}")
            return {
                'total_events': 0,
                'stars': 0,
                'clicks': 0,
                'avg_dwell_ms': 0,
                'preferred_sources': [],
                'activity_level': 0.0
            }
    
    def perform_incremental_update(self) -> bool:
        """Perform incremental model update with recent feedback"""
        try:
            logger.info("Starting incremental model update...")
            
            # Prepare training data
            training_data = self.prepare_incremental_training_data(24)  # Last 24 hours
            
            if not training_data:
                logger.warning("No training data available for incremental update")
                return False
            
            # Load current model
            if not self.ranker.model:
                logger.error("No active model loaded for incremental update")
                return False
            
            model = self.ranker.model
            features = training_data['features']
            labels = training_data['labels']
            
            # For Random Forest, we can't do true incremental learning
            # Instead, we'll retrain with a combination of old and new data
            # This is a simplified approach - in production, you might want to
            # maintain a sliding window of recent data
            
            logger.info(f"Performing model update with {len(features)} new samples")
            
            # Fit model with new data (partial_fit for algorithms that support it)
            if hasattr(model, 'partial_fit'):
                # For models that support incremental learning
                model.partial_fit(features, labels)
                logger.info("Applied partial_fit incremental update")
            else:
                # For Random Forest and other models, we'll need to retrain
                # In a production system, you'd maintain a buffer of recent samples
                logger.info("Model doesn't support partial_fit, skipping incremental update")
                logger.info("Consider implementing a full retrain with buffered samples")
                return False
            
            # Note: Model metadata update would require schema changes
            # For now, we just log the update
            logger.info(f"Model updated with {training_data['sample_count']} new samples")
            
            self.db.commit()
            
            # Reload model in ranker
            self.ranker.load_model()
            
            logger.info(f"Incremental model update completed with {training_data['sample_count']} samples")
            return True
            
        except Exception as e:
            logger.error(f"Error performing incremental update: {e}")
            self.db.rollback()
            return False
    
    def get_learning_stats(self) -> Dict[str, Any]:
        """Get statistics about real-time learning performance"""
        try:
            # Get recent model updates
            result = self.db.execute(text("""
                SELECT 
                    model_type,
                    created_at,
                    metrics,
                    model_path
                FROM ml_models 
                WHERE is_active = true
                ORDER BY created_at DESC
                LIMIT 1
            """))
            
            model_row = result.fetchone()
            
            # Get recent feedback volume
            cutoff_24h = datetime.now(timezone.utc) - timedelta(hours=24)
            cutoff_7d = datetime.now(timezone.utc) - timedelta(days=7)
            
            feedback_result = self.db.execute(text("""
                SELECT 
                    COUNT(CASE WHEN created_at >= :cutoff_24h THEN 1 END) as feedback_24h,
                    COUNT(CASE WHEN created_at >= :cutoff_7d THEN 1 END) as feedback_7d,
                    COUNT(*) as feedback_total,
                    COUNT(CASE WHEN type IN ('star', 'external_click') THEN 1 END) as positive_feedback,
                    COUNT(CASE WHEN type = 'dismiss' THEN 1 END) as negative_feedback
                FROM events
                WHERE type IN ('star', 'external_click', 'dismiss', 'open')
            """), {"cutoff_24h": cutoff_24h, "cutoff_7d": cutoff_7d})
            
            feedback_row = feedback_result.fetchone()
            
            # Calculate learning metrics
            total_feedback = feedback_row.feedback_total or 0
            positive_rate = (feedback_row.positive_feedback or 0) / max(1, total_feedback)
            
            # Extract metrics from JSON if available
            accuracy = None
            auc_score = None
            if model_row and model_row.metrics:
                try:
                    import json
                    metrics = json.loads(model_row.metrics) if isinstance(model_row.metrics, str) else model_row.metrics
                    accuracy = metrics.get('accuracy')
                    auc_score = metrics.get('auc_score')
                except:
                    pass
            
            return {
                'model_info': {
                    'name': model_row.model_type if model_row else 'No active model',
                    'created_at': model_row.created_at.isoformat() if model_row and model_row.created_at else None,
                    'model_path': model_row.model_path if model_row else None,
                    'accuracy': accuracy,
                    'auc_score': auc_score
                },
                'feedback_volume': {
                    'last_24h': feedback_row.feedback_24h or 0,
                    'last_7d': feedback_row.feedback_7d or 0,
                    'total': total_feedback,
                    'positive_rate': round(positive_rate, 3)
                },
                'learning_status': {
                    'auto_updates_enabled': True,
                    'update_frequency_hours': self.update_frequency_hours,
                    'min_samples_for_update': self.min_samples_for_update,
                    'ready_for_update': self.should_update_model()
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting learning stats: {e}")
            return {
                'error': str(e),
                'learning_status': {'auto_updates_enabled': False}
            }