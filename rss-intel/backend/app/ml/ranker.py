"""Article ranking and scoring module"""
import os
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import numpy as np
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import text

from .trainer import load_latest_model
from .features import extract_candidate_features
from .uservec import get_user_embedding
from ..deps import SessionLocal

logger = logging.getLogger(__name__)

# Configuration
CANDIDATE_DAYS = int(os.getenv('ML_CANDIDATE_DAYS', '14'))
MIN_RULE_SCORE = int(os.getenv('ML_MIN_RULE_SCORE', '20'))

class ArticleRanker:
    """Article ranking using trained ML model"""
    
    def __init__(self, db: Session):
        self.db = db
        self.model = None
        self.scaler = None
        self.model_id = None
        self._load_model()
    
    def _load_model(self):
        """Load the latest trained model"""
        model_data = load_latest_model(self.db)
        if model_data:
            self.model, self.scaler, self.model_id = model_data
            logger.info(f"Loaded model ID: {self.model_id}")
        else:
            logger.warning("No model available - using fallback scoring")
    
    def get_candidates(
        self,
        user_id: str = "owner",
        days_back: int = CANDIDATE_DAYS,
        min_score: int = MIN_RULE_SCORE,
        limit: int = 1000
    ) -> List[int]:
        """
        Get candidate articles for ranking
        
        Returns:
            List of article IDs
        """
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
        """
        Score articles using ML model
        
        Returns:
            List of dicts with article_id, p_read, rule_score
        """
        if not article_ids:
            return []
        
        logger.info(f"Scoring {len(article_ids)} articles")
        
        # Get user embedding for features
        user_embedding = get_user_embedding(self.db, user_id, lookback_days=30)
        
        # Extract features
        features_df = extract_candidate_features(
            self.db, article_ids, user_embedding
        )
        
        if features_df.empty:
            logger.warning("No features available for scoring")
            return []
        
        scored_articles = []
        
        for _, row in features_df.iterrows():
            article_id = row['article_id']
            features = np.array(row['features']).reshape(1, -1)
            
            # Get ML prediction if model available
            if self.model and self.scaler:
                try:
                    features_scaled = self.scaler.transform(features)
                    p_read = float(self.model.predict_proba(features_scaled)[0, 1])
                except Exception as e:
                    logger.error(f"Error scoring article {article_id}: {e}")
                    p_read = 0.5  # Neutral prediction
            else:
                # Fallback: use rule score normalized to [0,1]
                rule_score = features[0, -6] if features.shape[1] > 6 else 50  # Assuming rule_score is 6th from end
                p_read = min(1.0, max(0.0, rule_score / 100.0))
            
            scored_articles.append({
                'article_id': article_id,
                'p_read': p_read,
                'rule_score': int(features[0, -6]) if features.shape[1] > 6 else 0
            })
        
        # Save predictions to database
        if self.model_id and scored_articles:
            self._save_predictions(scored_articles)
        
        # Sort by p_read descending
        scored_articles.sort(key=lambda x: x['p_read'], reverse=True)
        
        logger.info(f"Scored {len(scored_articles)} articles")
        return scored_articles
    
    def _save_predictions(self, scored_articles: List[Dict]):
        """Save predictions to database"""
        try:
            for item in scored_articles:
                self.db.execute(text("""
                    INSERT INTO predictions (article_id, model_id, p_read, created_at)
                    VALUES (:article_id, :model_id, :p_read, :created_at)
                    ON CONFLICT (article_id, model_id) 
                    DO UPDATE SET p_read = EXCLUDED.p_read, created_at = EXCLUDED.created_at
                """), {
                    "article_id": item['article_id'],
                    "model_id": self.model_id,
                    "p_read": item['p_read'],
                    "created_at": datetime.utcnow()
                })
            
            self.db.commit()
            logger.info(f"Saved {len(scored_articles)} predictions")
            
        except Exception as e:
            logger.error(f"Error saving predictions: {e}")
            self.db.rollback()
    
    def rank_for_user(
        self,
        user_id: str = "owner",
        limit: int = 50,
        days_back: int = CANDIDATE_DAYS
    ) -> List[Dict]:
        """
        Full ranking pipeline for user
        
        Returns:
            Ranked list of articles with scores
        """
        # Get candidates
        candidate_ids = self.get_candidates(
            user_id=user_id,
            days_back=days_back,
            limit=limit * 3  # Get more candidates than needed
        )
        
        if not candidate_ids:
            return []
        
        # Score candidates
        scored_articles = self.score_articles(candidate_ids, user_id)
        
        # Limit results
        return scored_articles[:limit]

def batch_score_articles(db: Session, limit: int = 1000) -> Dict:
    """Batch score articles for all users"""
    logger.info(f"Starting batch scoring, limit={limit}")
    
    ranker = ArticleRanker(db)
    
    # Get all users (for now just default user)
    users = ["owner"]  # TODO: get from database when multi-user
    
    total_scored = 0
    results = {}
    
    for user_id in users:
        try:
            candidates = ranker.get_candidates(user_id=user_id, limit=limit)
            if candidates:
                scored = ranker.score_articles(candidates, user_id)
                results[user_id] = len(scored)
                total_scored += len(scored)
            else:
                results[user_id] = 0
                
        except Exception as e:
            logger.error(f"Error scoring for user {user_id}: {e}")
            results[user_id] = {"error": str(e)}
    
    logger.info(f"Batch scoring completed: {total_scored} articles")
    return {
        "total_scored": total_scored,
        "per_user": results,
        "timestamp": datetime.utcnow().isoformat()
    }

if __name__ == "__main__":
    # CLI for batch scoring
    import sys
    import json
    
    db = SessionLocal()
    try:
        if len(sys.argv) > 1 and sys.argv[1] == "batch":
            limit = int(sys.argv[2]) if len(sys.argv) > 2 else 1000
            result = batch_score_articles(db, limit)
            print(json.dumps(result, indent=2))
        else:
            # Test single user ranking
            ranker = ArticleRanker(db)
            results = ranker.rank_for_user(limit=10)
            for item in results:
                print(f"Article {item['article_id']}: p_read={item['p_read']:.3f}, rule_score={item['rule_score']}")
    finally:
        db.close()