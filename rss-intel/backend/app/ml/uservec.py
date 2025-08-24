"""User embedding and preference modeling"""
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict
import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy import text

from .embedding import get_article_embedding

logger = logging.getLogger(__name__)

def get_user_embedding(
    db: Session,
    user_id: str = "owner",
    lookback_days: int = 30,
    min_interactions: int = 3
) -> Optional[np.ndarray]:
    """
    Compute user preference embedding as weighted average of positive article embeddings
    
    Args:
        db: Database session
        user_id: User identifier
        lookback_days: How far back to look for interactions
        min_interactions: Minimum positive interactions needed
        
    Returns:
        384-dimensional user embedding or None if insufficient data
    """
    from datetime import timezone
    cutoff_date = datetime.utcnow().replace(tzinfo=timezone.utc) - timedelta(days=lookback_days)
    
    logger.info(f"Computing user embedding for {user_id}, lookback={lookback_days} days")
    
    # Get positive interactions (stars, long dwells, external clicks)
    result = db.execute(text("""
        SELECT DISTINCT
            e.article_id,
            a.score_total,
            e.created_at,
            av.emb
        FROM events e
        JOIN articles a ON e.article_id = a.id
        JOIN article_vectors av ON a.id = av.article_id
        WHERE e.user_id = :user_id
        AND e.created_at > :cutoff_date
        AND (
            e.type = 'star' 
            OR e.type = 'external_click'
            OR (e.type = 'open' AND e.duration_ms >= 15000)
        )
        ORDER BY e.created_at DESC
        LIMIT 100
    """), {
        "user_id": user_id,
        "cutoff_date": cutoff_date
    })
    
    interactions = result.fetchall()
    logger.info(f"Found {len(interactions)} positive interactions")
    
    if len(interactions) < min_interactions:
        logger.info(f"Not enough interactions ({len(interactions)} < {min_interactions}), using fallback")
        return get_fallback_user_embedding(db, user_id)
    
    # Compute weighted average embedding
    embeddings = []
    weights = []
    
    for interaction in interactions:
        if not interaction.emb:
            continue
            
        embedding = np.array(interaction.emb, dtype=np.float32)
        
        # Weight by log(1 + score) * recency decay
        score_weight = np.log(1 + max(0, interaction.score_total or 0))
        
        # Recency decay (2-week half-life)
        from datetime import timezone
        if interaction.created_at.tzinfo is not None:
            now = datetime.utcnow().replace(tzinfo=timezone.utc)
        else:
            now = datetime.utcnow().replace(tzinfo=None)
        age_hours = (now - interaction.created_at).total_seconds() / 3600
        recency_weight = np.exp(-age_hours / (14 * 24))  # 14-day half-life
        
        total_weight = score_weight * recency_weight
        
        embeddings.append(embedding)
        weights.append(total_weight)
    
    if not embeddings:
        logger.warning("No valid embeddings found")
        return get_fallback_user_embedding(db, user_id)
    
    # Weighted average
    embeddings_matrix = np.stack(embeddings)
    weights_array = np.array(weights)
    
    # Normalize weights
    weights_normalized = weights_array / weights_array.sum()
    
    user_embedding = np.average(embeddings_matrix, axis=0, weights=weights_normalized)
    
    # Normalize to unit vector
    user_embedding = user_embedding / np.linalg.norm(user_embedding)
    
    logger.info(f"Computed user embedding from {len(embeddings)} articles")
    return user_embedding.astype(np.float32)

def get_fallback_user_embedding(
    db: Session,
    user_id: str = "owner"
) -> Optional[np.ndarray]:
    """
    Fallback user embedding based on high-scoring articles from watchlisted sources
    """
    logger.info(f"Computing fallback user embedding for {user_id}")
    
    # Get high-scoring articles from the last 60 days
    cutoff_date = datetime.utcnow() - timedelta(days=60)
    
    result = db.execute(text("""
        SELECT av.emb, a.score_total
        FROM articles a
        JOIN article_vectors av ON a.id = av.article_id
        WHERE a.published_at > :cutoff_date
        AND a.score_total >= 60  -- High-scoring articles only
        ORDER BY a.score_total DESC
        LIMIT 50
    """), {"cutoff_date": cutoff_date})
    
    articles = result.fetchall()
    
    if not articles:
        logger.warning("No articles available for fallback embedding")
        return None
    
    # Weight by score
    embeddings = []
    weights = []
    
    for article in articles:
        if not article.emb:
            continue
            
        embedding = np.array(article.emb, dtype=np.float32)
        weight = float(article.score_total or 0)
        
        embeddings.append(embedding)
        weights.append(weight)
    
    if not embeddings:
        return None
    
    # Weighted average
    embeddings_matrix = np.stack(embeddings)
    weights_array = np.array(weights)
    weights_normalized = weights_array / weights_array.sum()
    
    fallback_embedding = np.average(embeddings_matrix, axis=0, weights=weights_normalized)
    fallback_embedding = fallback_embedding / np.linalg.norm(fallback_embedding)
    
    logger.info(f"Computed fallback embedding from {len(embeddings)} high-scoring articles")
    return fallback_embedding.astype(np.float32)

def update_user_embeddings(db: Session) -> Dict[str, int]:
    """Update embeddings for all users"""
    # For now, just handle default user
    # TODO: extend for multi-user when user management is implemented
    
    users = ["owner"]
    results = {}
    
    for user_id in users:
        try:
            embedding = get_user_embedding(db, user_id, lookback_days=30)
            if embedding is not None:
                # Store in cache/database if needed
                results[user_id] = 1
                logger.info(f"Updated embedding for user {user_id}")
            else:
                results[user_id] = 0
                logger.warning(f"No embedding computed for user {user_id}")
        except Exception as e:
            logger.error(f"Error updating embedding for user {user_id}: {e}")
            results[user_id] = -1
    
    return results

def compute_user_article_similarity(
    db: Session,
    user_id: str,
    article_id: int
) -> Optional[float]:
    """Compute similarity between user and specific article"""
    user_emb = get_user_embedding(db, user_id, lookback_days=30)
    if user_emb is None:
        return None
    
    article_emb = get_article_embedding(db, article_id)
    if article_emb is None:
        return None
    
    # Cosine similarity
    user_norm = user_emb / np.linalg.norm(user_emb)
    article_norm = article_emb / np.linalg.norm(article_emb)
    
    similarity = float(np.dot(user_norm, article_norm))
    return similarity