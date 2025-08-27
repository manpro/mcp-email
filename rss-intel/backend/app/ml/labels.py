"""Label generation for ML training"""
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import text

logger = logging.getLogger(__name__)

# Configuration
MIN_DWELL_MS = int(os.getenv('ML_MIN_DWELL_MS', '15000'))
IMPRESSION_TIMEOUT_HOURS = 24

def extract_labels(db: Session, article_ids: List[int], user_id: str = "owner") -> pd.DataFrame:
    """
    Extract positive/negative labels for articles based on user behavior
    
    Label rules:
    - Positive: star OR (open & dwell_ms >= MIN_DWELL_MS) OR external_click
    - Negative: impression without open within 24h OR dismiss
    
    Args:
        db: Database session
        article_ids: List of article IDs to generate labels for
        user_id: User identifier
        
    Returns:
        DataFrame with article_id and label (0/1)
    """
    if not article_ids:
        return pd.DataFrame()
    
    logger.info(f"Extracting labels for {len(article_ids)} articles, user={user_id}")
    
    # Build query with parameterized IN clause
    placeholders = ','.join([f':id{i}' for i in range(len(article_ids))])
    params = {f'id{i}': article_id for i, article_id in enumerate(article_ids)}
    params['user_id'] = user_id
    params['min_dwell'] = MIN_DWELL_MS
    params['timeout_hours'] = IMPRESSION_TIMEOUT_HOURS
    
    # Get all events for these articles
    result = db.execute(text(f"""
        SELECT 
            article_id,
            type,
            duration_ms,
            created_at,
            LAG(created_at) OVER (PARTITION BY article_id ORDER BY created_at) as prev_event_time
        FROM events 
        WHERE article_id IN ({placeholders})
        AND user_id = :user_id
        ORDER BY article_id, created_at
    """), params)
    
    events = result.fetchall()
    logger.info(f"Found {len(events)} events for labeling")
    
    # Process events to determine labels
    article_labels = {}
    article_events = {}
    
    # Group events by article
    for event in events:
        article_id = event.article_id
        if article_id not in article_events:
            article_events[article_id] = []
        article_events[article_id].append(event)
    
    for article_id in article_ids:
        events_for_article = article_events.get(article_id, [])
        label = determine_label(events_for_article)
        article_labels[article_id] = label
    
    # Create DataFrame
    label_data = [
        {'article_id': article_id, 'label': label}
        for article_id, label in article_labels.items()
    ]
    
    df = pd.DataFrame(label_data)
    
    if not df.empty:
        positive_count = (df['label'] == 1).sum()
        negative_count = (df['label'] == 0).sum()
        unlabeled_count = df['label'].isna().sum()
        
        logger.info(f"Labels: {positive_count} positive, {negative_count} negative, {unlabeled_count} unlabeled")
    
    return df

def determine_label(events: List) -> int:
    """
    Determine label for a single article based on its events
    
    Returns:
        1 for positive, 0 for negative, None for unlabeled
    """
    if not events:
        return None
    
    has_impression = False
    has_open = False
    has_long_dwell = False
    has_star = False
    has_external_click = False
    has_dismiss = False
    
    impression_time = None
    open_time = None
    
    for event in events:
        event_type = event.type
        
        if event_type == 'impression':
            has_impression = True
            impression_time = event.created_at
            
        elif event_type == 'open':
            has_open = True
            open_time = event.created_at
            
            # Check dwell time
            if event.duration_ms and event.duration_ms >= MIN_DWELL_MS:
                has_long_dwell = True
                
        elif event_type == 'star':
            has_star = True
            
        elif event_type == 'external_click':
            has_external_click = True
            
        elif event_type == 'dismiss':
            has_dismiss = True
            
        elif event_type == 'downvote':
            has_dismiss = True  # Treat downvote as strong negative signal
    
    # Apply labeling rules
    
    # Positive signals (in order of strength)
    if has_star:
        return 1
    
    if has_external_click:
        return 1
    
    if has_open and has_long_dwell:
        return 1
    
    # Negative signals
    if has_dismiss:
        return 0
    
    # Impression without open within timeout
    if has_impression and not has_open and impression_time:
        # Check if enough time has passed since impression
        now = datetime.utcnow()
        if impression_time.tzinfo is None:
            impression_time = impression_time.replace(tzinfo=None)
        if now.tzinfo is not None:
            now = now.replace(tzinfo=None)
            
        hours_since_impression = (now - impression_time).total_seconds() / 3600
        if hours_since_impression >= IMPRESSION_TIMEOUT_HOURS:
            return 0
    
    # No clear signal - unlabeled
    return None

def get_training_labels(
    db: Session,
    lookback_days: int = 30,
    min_events_per_article: int = 2,
    user_id: str = "owner"
) -> pd.DataFrame:
    """
    Get labels for training dataset
    
    Args:
        db: Database session
        lookback_days: How far back to look for training data
        min_events_per_article: Minimum events required per article
        user_id: User identifier
        
    Returns:
        DataFrame with article_id and label
    """
    cutoff = datetime.utcnow() - timedelta(days=lookback_days)
    
    # Get articles with sufficient events
    result = db.execute(text("""
        SELECT article_id, COUNT(*) as event_count
        FROM events
        WHERE user_id = :user_id
        AND created_at > :cutoff
        GROUP BY article_id
        HAVING COUNT(*) >= :min_events
        ORDER BY event_count DESC
        LIMIT 5000
    """), {
        "user_id": user_id,
        "cutoff": cutoff,
        "min_events": min_events_per_article
    })
    
    articles_with_events = result.fetchall()
    article_ids = [row.article_id for row in articles_with_events]
    
    logger.info(f"Found {len(article_ids)} articles with sufficient events for labeling")
    
    if not article_ids:
        return pd.DataFrame()
    
    return extract_labels(db, article_ids, user_id)

def compute_label_stats(df: pd.DataFrame) -> Dict:
    """Compute statistics about labels"""
    if df.empty or 'label' not in df.columns:
        return {}
    
    total = len(df)
    positive = (df['label'] == 1).sum()
    negative = (df['label'] == 0).sum()
    unlabeled = df['label'].isna().sum()
    
    stats = {
        'total_articles': total,
        'positive': int(positive),
        'negative': int(negative), 
        'unlabeled': int(unlabeled),
        'positive_rate': float(positive / total) if total > 0 else 0.0,
        'negative_rate': float(negative / total) if total > 0 else 0.0,
        'labeled_rate': float((positive + negative) / total) if total > 0 else 0.0
    }
    
    return stats