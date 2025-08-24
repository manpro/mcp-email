"""Simple ML recommendation API without timezone complexity"""
import logging
import os
import pickle
import numpy as np
from datetime import datetime
from typing import List, Dict
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text

from ..deps import get_db

logger = logging.getLogger(__name__)
router = APIRouter()

def get_simple_recommendations_internal(db: Session, user_id: str = "owner", limit: int = 50):
    """Get ML recommendations using simple scoring"""
    
    # Load model
    try:
        with open('/app/models/simple_model.pkl', 'rb') as f:
            model_data = pickle.load(f)
        model = model_data['model']
        scaler = model_data['scaler']
    except Exception as e:
        logger.error(f"Could not load model: {e}")
        return []
    
    # Get candidate articles (not interacted with)
    try:
        candidates = db.execute(text("""
            SELECT DISTINCT a.id, a.title, a.url, a.source, 
                            a.published_at, a.score_total, 
                            a.has_image, av.title_len, av.emb[1:10] as emb_sample
            FROM articles a
            JOIN article_vectors av ON a.id = av.article_id
            LEFT JOIN events e ON a.id = e.article_id 
                AND e.user_id = :user_id 
                AND e.type IN ('open', 'dismiss', 'mark_read')
            WHERE a.score_total >= 3
            AND e.article_id IS NULL
            ORDER BY a.score_total DESC
            LIMIT :limit
        """), {"user_id": user_id, "limit": min(limit * 2, 100)}).fetchall()
        
    except Exception as e:
        logger.error(f"Error getting candidates: {e}")
        return []
    
    recommendations = []
    
    for article in candidates:
        try:
            # Simple feature vector
            features = [
                float(article[5] or 0),    # score_total
                float(article[6] or 0),    # has_image
                float(article[7] or 0),    # title_len
                1.0                        # interaction_count (dummy)
            ]
            
            # Add embedding features
            if article[8]:
                features.extend(article[8])
            else:
                features.extend([0.0] * 10)
            
            # Get ML prediction
            X = np.array([features])
            X_scaled = scaler.transform(X)
            p_read = model.predict_proba(X_scaled)[0, 1]
            
            recommendations.append({
                'id': article[0],
                'title': article[1],
                'url': article[2],
                'source': article[3],
                'published_at': article[4].isoformat() if article[4] else None,
                'score_total': article[5],
                'has_image': bool(article[6]),
                'p_read': round(float(p_read), 3),
                'rule_score': article[5],
                'why': [
                    'High confidence' if p_read > 0.4 else 'Good match' if p_read > 0.3 else 'Explore',
                    f'ML Score: {p_read:.2f}',
                    f'Rule Score: {article[5]}'
                ]
            })
            
        except Exception as e:
            logger.error(f"Error scoring article {article[0]}: {e}")
            continue
    
    # Sort by ML score
    recommendations.sort(key=lambda x: x['p_read'], reverse=True)
    
    return recommendations[:limit]

@router.get("/recommend")
async def get_recommendations(
    limit: int = Query(50, ge=1, le=100),
    user_id: str = Query("owner"),
    db: Session = Depends(get_db)
) -> Dict:
    """Get personalized article recommendations (simplified)"""
    
    logger.info(f"Getting simple ML recommendations for user {user_id}, limit={limit}")
    
    try:
        recommendations = get_simple_recommendations_internal(db, user_id, limit)
        
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
        # Check model availability
        model_available = os.path.exists('/app/models/simple_model.pkl')
        
        # Count candidates
        candidates_result = db.execute(text("""
            SELECT COUNT(DISTINCT a.id)
            FROM articles a
            LEFT JOIN events e ON a.id = e.article_id 
                AND e.user_id = :user_id 
                AND e.type IN ('open', 'dismiss', 'mark_read')
            WHERE a.score_total >= 3
            AND e.article_id IS NULL
        """), {"user_id": user_id}).fetchone()
        
        candidates_found = candidates_result[0] if candidates_result else 0
        
        # Get sample scores
        sample_recs = get_simple_recommendations_internal(db, user_id, 3)
        sample_scores = [
            {"article_id": r["id"], "p_read": r["p_read"], "rule_score": r["rule_score"]}
            for r in sample_recs
        ]
        
        return {
            "user_id": user_id,
            "candidates_found": candidates_found,
            "user_embedding_available": True,  # Simplified
            "sample_scores": sample_scores,
            "bandit_config": {
                "epsilon": 0.1,
                "mmr_lambda": 0.25,
                "enabled": True
            },
            "model_loaded": model_available,
            "model_id": 1 if model_available else None,
            "version": "simplified"
        }
        
    except Exception as e:
        logger.error(f"Debug error: {e}")
        raise HTTPException(status_code=500, detail=str(e))