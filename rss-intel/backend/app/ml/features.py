"""Feature engineering for ML models"""
import logging
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import text

from .embedding import get_article_embedding, compute_similarity

logger = logging.getLogger(__name__)

def hash_trick_encode(text: str, n_features: int = 32) -> np.ndarray:
    """Hash trick encoding for categorical features"""
    if not text:
        return np.zeros(n_features)
    
    # Simple hash trick
    feature_vec = np.zeros(n_features)
    for word in text.lower().split():
        hash_val = int(hashlib.md5(word.encode()).hexdigest(), 16)
        idx = hash_val % n_features
        feature_vec[idx] = 1.0
    
    return feature_vec

def extract_content_features(
    article_embedding: np.ndarray,
    user_embedding: Optional[np.ndarray],
    title_len: int,
    has_image: bool,
    source: str,
    published_at: datetime
) -> np.ndarray:
    """
    Extract content-based features
    
    Returns:
        Feature vector with content signals
    """
    features = []
    
    # Content similarity features
    if user_embedding is not None:
        # Dot product and cosine similarity with user vector
        dot_product = float(np.dot(article_embedding, user_embedding))
        cos_similarity = compute_similarity(article_embedding, user_embedding)
        features.extend([dot_product, cos_similarity])
    else:
        # No user vector available
        features.extend([0.0, 0.0])
    
    # Article content features
    features.extend([
        float(title_len),
        float(title_len > 50),  # Long title indicator
        float(has_image),
    ])
    
    # Source encoding (hash trick)
    source_features = hash_trick_encode(source or "", n_features=32)
    features.extend(source_features.tolist())
    
    return np.array(features, dtype=np.float32)

def extract_recency_features(published_at: datetime, now: Optional[datetime] = None) -> np.ndarray:
    """Extract time-based features"""
    from datetime import timezone
    if now is None:
        now = datetime.now(timezone.utc)
    
    # Ensure both datetimes are timezone-aware or both are naive
    if published_at.tzinfo is None:
        published_at = published_at.replace(tzinfo=timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    
    age_hours = (now - published_at).total_seconds() / 3600
    
    features = [
        float(age_hours),
        float(age_hours < 24),  # Fresh article
        float(age_hours < 168),  # This week
        np.exp(-age_hours / 48),  # Exponential decay (48h half-life)
    ]
    
    return np.array(features, dtype=np.float32)

def extract_interaction_features(
    db: Session, 
    article_id: int, 
    user_id: str = "owner",
    lookback_days: int = 14
) -> np.ndarray:
    """Extract user interaction history features"""
    from datetime import timezone
    cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)
    
    # Get interaction stats for this user
    result = db.execute(text("""
        SELECT 
            COUNT(*) FILTER (WHERE type = 'open') as opens,
            AVG(duration_ms) FILTER (WHERE type = 'open' AND duration_ms > 0) as avg_dwell,
            COUNT(*) FILTER (WHERE type = 'star') as stars,
            COUNT(*) FILTER (WHERE type = 'external_click') as ext_clicks,
            COUNT(*) FILTER (WHERE type = 'dismiss') as dismisses
        FROM events 
        WHERE user_id = :user_id 
        AND created_at > :cutoff
    """), {"user_id": user_id, "cutoff": cutoff})
    
    row = result.fetchone()
    if row:
        features = [
            float(row.opens or 0),
            float(row.avg_dwell or 0) / 1000.0,  # Convert to seconds
            float(row.stars or 0),
            float(row.ext_clicks or 0),
            float(row.dismisses or 0),
        ]
    else:
        features = [0.0, 0.0, 0.0, 0.0, 0.0]
    
    return np.array(features, dtype=np.float32)

def build_training_features(
    db: Session,
    user_embedding: Optional[np.ndarray] = None,
    lookback_days: int = 30,
    min_interactions: int = 5
) -> pd.DataFrame:
    """
    Build training dataset with features and labels
    
    Args:
        db: Database session
        user_embedding: User's preference embedding
        lookback_days: How far back to look for training data
        min_interactions: Minimum interactions needed per article
        
    Returns:
        DataFrame with features and labels
    """
    from datetime import timezone
    cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)
    
    logger.info(f"Building training features, lookback={lookback_days} days")
    
    # Get articles with embeddings and sufficient interaction data
    result = db.execute(text("""
        SELECT DISTINCT
            a.id as article_id,
            a.title,
            a.content,
            a.score_total,
            a.published_at,
            av.emb,
            av.title_len,
            av.has_image,
            av.source
        FROM articles a
        JOIN article_vectors av ON a.id = av.article_id
        JOIN events e ON a.id = e.article_id
        WHERE a.created_at > :cutoff
        GROUP BY a.id, a.title, a.content, a.score_total, a.published_at,
                 av.emb, av.title_len, av.has_image, av.source
        HAVING COUNT(e.id) >= :min_interactions
        ORDER BY a.published_at DESC
        LIMIT 5000
    """), {"cutoff": cutoff, "min_interactions": min_interactions})
    
    articles = result.fetchall()
    logger.info(f"Found {len(articles)} articles with sufficient interactions")
    
    if len(articles) < 10:
        logger.warning("Not enough articles for training")
        return pd.DataFrame()
    
    # Build feature matrix
    feature_rows = []
    
    for article in articles:
        try:
            article_emb = np.array(article.emb, dtype=np.float32)
            
            # Content features
            content_features = extract_content_features(
                article_emb, user_embedding, article.title_len,
                article.has_image, article.source, article.published_at
            )
            
            # Recency features
            recency_features = extract_recency_features(article.published_at)
            
            # Rule score feature
            rule_score = float(article.score_total or 0)
            
            # Interaction features
            interaction_features = extract_interaction_features(
                db, article.article_id, lookback_days=14
            )
            
            # Combine all features
            all_features = np.concatenate([
                content_features,
                recency_features,
                [rule_score],
                interaction_features
            ])
            
            feature_rows.append({
                'article_id': article.article_id,
                'features': all_features.tolist(),
                'published_at': article.published_at
            })
            
        except Exception as e:
            logger.error(f"Error building features for article {article.article_id}: {e}")
            continue
    
    if not feature_rows:
        return pd.DataFrame()
    
    # Create DataFrame
    df = pd.DataFrame(feature_rows)
    logger.info(f"Built features for {len(df)} articles")
    
    return df

def extract_candidate_features(
    db: Session,
    article_ids: List[int],
    user_embedding: Optional[np.ndarray] = None
) -> pd.DataFrame:
    """Extract features for candidate articles (for scoring)"""
    if not article_ids:
        return pd.DataFrame()
    
    # Get article data
    placeholders = ','.join([':id%d' % i for i in range(len(article_ids))])
    params = {f'id{i}': article_id for i, article_id in enumerate(article_ids)}
    
    result = db.execute(text(f"""
        SELECT 
            a.id as article_id,
            a.score_total,
            a.published_at,
            av.emb,
            av.title_len,
            av.has_image,
            av.source
        FROM articles a
        JOIN article_vectors av ON a.id = av.article_id
        WHERE a.id IN ({placeholders})
    """), params)
    
    articles = result.fetchall()
    
    feature_rows = []
    for article in articles:
        try:
            article_emb = np.array(article.emb, dtype=np.float32)
            
            # Extract all feature types
            content_features = extract_content_features(
                article_emb, user_embedding, article.title_len,
                article.has_image, article.source, article.published_at
            )
            
            recency_features = extract_recency_features(article.published_at)
            rule_score = float(article.score_total or 0)
            
            interaction_features = extract_interaction_features(
                db, article.article_id, lookback_days=14
            )
            
            all_features = np.concatenate([
                content_features,
                recency_features,
                [rule_score],
                interaction_features
            ])
            
            feature_rows.append({
                'article_id': article.article_id,
                'features': all_features.tolist()
            })
            
        except Exception as e:
            logger.error(f"Error extracting features for article {article.article_id}: {e}")
            continue
    
    return pd.DataFrame(feature_rows)