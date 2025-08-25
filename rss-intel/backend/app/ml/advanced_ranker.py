"""Advanced article ranking using the improved ML model"""
import os
import logging
import joblib
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import numpy as np
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import text

from .advanced_features import AdvancedFeatureExtractor
from ..deps import SessionLocal

logger = logging.getLogger(__name__)

class AdvancedArticleRanker:
    """Advanced article ranking using improved ML model with better features"""
    
    def __init__(self, db: Session):
        self.db = db
        self.model = None
        self.scaler = None
        self.feature_names = None
        self.model_type = None
        self.model_id = None
        self.feature_extractor = None
        self._load_model()
    
    def _load_model(self):
        """Load the latest active advanced model"""
        try:
            # Get active model from database
            result = self.db.execute(text("""
                SELECT id, model_path, params, version
                FROM ml_models 
                WHERE model_type = 'personalization' 
                AND is_active = true 
                ORDER BY id DESC 
                LIMIT 1
            """))
            
            model_record = result.fetchone()
            if not model_record:
                logger.warning("No active personalization model found")
                return
            
            model_path = model_record.model_path
            if not os.path.exists(model_path):
                logger.warning(f"Model file not found: {model_path}")
                return
            
            # Load model
            model_data = joblib.load(model_path)
            self.model = model_data['model']
            self.scaler = model_data.get('scaler')  # May be None for tree-based models
            self.feature_names = model_data['feature_names']
            self.model_type = model_data.get('model_type', 'unknown')
            self.model_id = model_record.id
            
            # Initialize feature extractor
            self.feature_extractor = AdvancedFeatureExtractor(self.db)
            
            logger.info(f"Loaded advanced model: {self.model_type} (ID: {self.model_id})")
            logger.info(f"Model features: {len(self.feature_names)}")
            
        except Exception as e:
            logger.error(f"Error loading advanced model: {e}")
            self.model = None
    
    def get_candidates(
        self,
        user_id: str = "owner",
        days_back: int = 14,
        min_score: int = 20,
        limit: int = 1000
    ) -> List[int]:
        """Get candidate articles for ranking"""
        cutoff_date = datetime.utcnow() - timedelta(days=days_back)
        
        # Get candidates: recent articles, not read/dismissed, above min score
        result = self.db.execute(text("""
            SELECT DISTINCT a.id, a.score_total, a.published_at
            FROM articles a
            LEFT JOIN events e ON a.id = e.article_id 
                AND e.user_id = :user_id 
                AND e.type IN ('open', 'dismiss', 'mark_read')
            WHERE a.published_at > :cutoff_date
            AND a.score_total >= :min_score
            AND e.article_id IS NULL  -- Not read/dismissed
            ORDER BY a.score_total DESC, a.published_at DESC
            LIMIT :limit
        """), {
            "user_id": user_id,
            "cutoff_date": cutoff_date,
            "min_score": min_score,
            "limit": limit
        })
        
        article_ids = [row[0] for row in result.fetchall()]
        logger.info(f"Found {len(article_ids)} candidate articles")
        return article_ids
    
    def score_articles(
        self,
        article_ids: List[int],
        user_id: str = "owner"
    ) -> List[Dict]:
        """Score articles using advanced ML model"""
        if not article_ids:
            return []
        
        if not self.model or not self.feature_extractor:
            logger.warning("No model available - using fallback scoring")
            return self._fallback_scoring(article_ids)
        
        logger.info(f"Scoring {len(article_ids)} articles with advanced model")
        
        # Get article data
        placeholders = ','.join([f':id{i}' for i in range(len(article_ids))])
        params = {f'id{i}': article_id for i, article_id in enumerate(article_ids)}
        
        result = self.db.execute(text(f"""
            SELECT 
                a.id, a.title, a.content, a.full_content, a.source, a.topics,
                a.score_total, a.published_at, a.has_image
            FROM articles a
            WHERE a.id IN ({placeholders})
        """), params)
        
        articles = result.fetchall()
        scored_articles = []
        
        for article in articles:
            try:
                # Extract advanced features
                topics = article.topics if article.topics else []
                content = article.full_content or article.content
                
                features = self.feature_extractor.extract_all_features(
                    article.id, article.title, content, article.source,
                    topics, article.score_total, article.published_at,
                    article.has_image, user_id
                )
                
                # Make prediction
                if self.scaler:
                    # Scale features for models that need it (like logistic regression)
                    features_scaled = self.scaler.transform(features.reshape(1, -1))
                    p_read = float(self.model.predict_proba(features_scaled)[0, 1])
                else:
                    # Use raw features for tree-based models
                    p_read = float(self.model.predict_proba(features.reshape(1, -1))[0, 1])
                
                scored_articles.append({
                    'article_id': article.id,
                    'p_read': p_read,
                    'rule_score': int(article.score_total or 0),
                    'features_used': len(features),
                    'model_type': self.model_type
                })
                
            except Exception as e:
                logger.error(f"Error scoring article {article.id}: {e}")
                # Fallback scoring
                scored_articles.append({
                    'article_id': article.id,
                    'p_read': 0.5,
                    'rule_score': int(article.score_total or 0),
                    'features_used': 0,
                    'model_type': 'fallback'
                })
        
        # Save predictions to database
        if self.model_id and scored_articles:
            self._save_predictions(scored_articles)
        
        # Sort by p_read descending
        scored_articles.sort(key=lambda x: x['p_read'], reverse=True)
        
        logger.info(f"Scored {len(scored_articles)} articles with advanced model")
        return scored_articles
    
    def _fallback_scoring(self, article_ids: List[int]) -> List[Dict]:
        """Fallback scoring when no model is available"""
        logger.info("Using fallback rule-based scoring")
        
        placeholders = ','.join([f':id{i}' for i in range(len(article_ids))])
        params = {f'id{i}': article_id for i, article_id in enumerate(article_ids)}
        
        result = self.db.execute(text(f"""
            SELECT id, score_total FROM articles WHERE id IN ({placeholders})
        """), params)
        
        scored_articles = []
        for row in result:
            rule_score = row.score_total or 0
            p_read = min(1.0, max(0.0, rule_score / 100.0))  # Normalize to 0-1
            
            scored_articles.append({
                'article_id': row.id,
                'p_read': p_read,
                'rule_score': rule_score,
                'features_used': 0,
                'model_type': 'rule_based_fallback'
            })
        
        scored_articles.sort(key=lambda x: x['p_read'], reverse=True)
        return scored_articles
    
    def _save_predictions(self, scored_articles: List[Dict]):
        """Save predictions to database"""
        try:
            for item in scored_articles:
                self.db.execute(text("""
                    INSERT INTO predictions (article_id, model_id, score, created_at)
                    VALUES (:article_id, :model_id, :score, :created_at)
                    ON CONFLICT (article_id, model_id) 
                    DO UPDATE SET score = EXCLUDED.score, created_at = EXCLUDED.created_at
                """), {
                    "article_id": item['article_id'],
                    "model_id": self.model_id,
                    "score": item['p_read'],
                    "created_at": datetime.utcnow()
                })
            
            self.db.commit()
            logger.info(f"Saved {len(scored_articles)} advanced predictions")
            
        except Exception as e:
            logger.error(f"Error saving predictions: {e}")
            self.db.rollback()
    
    def rank_for_user(
        self,
        user_id: str = "owner",
        limit: int = 50,
        days_back: int = 14
    ) -> List[Dict]:
        """Full ranking pipeline using advanced model"""
        # Get candidates
        candidate_ids = self.get_candidates(
            user_id=user_id,
            days_back=days_back,
            limit=limit * 3  # Get more candidates than needed
        )
        
        if not candidate_ids:
            return []
        
        # Score candidates with advanced model
        scored_articles = self.score_articles(candidate_ids, user_id)
        
        # Limit results
        return scored_articles[:limit]
    
    def get_model_info(self) -> Dict:
        """Get information about the loaded model"""
        return {
            'model_loaded': self.model is not None,
            'model_type': self.model_type,
            'model_id': self.model_id,
            'feature_count': len(self.feature_names) if self.feature_names else 0,
            'has_scaler': self.scaler is not None,
            'feature_extractor_available': self.feature_extractor is not None
        }