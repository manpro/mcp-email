"""
Advanced feature engineering for improved ML personalization
"""
import logging
import numpy as np
import hashlib
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import text
import re
from collections import Counter

from .embedding import get_article_embedding, compute_similarity
from .features import extract_quality_features

logger = logging.getLogger(__name__)

class AdvancedFeatureExtractor:
    """Advanced feature extraction for better personalization"""
    
    def __init__(self, db: Session):
        self.db = db
        self.source_scores = None
        self.topic_popularity = None
        self.user_source_preferences = None
        self._cache_global_stats()
    
    def _cache_global_stats(self):
        """Cache global statistics for feature engineering"""
        try:
            # Source popularity and quality scores
            result = self.db.execute(text("""
                SELECT 
                    source, 
                    COUNT(*) as article_count,
                    AVG(score_total) as avg_score,
                    COUNT(CASE WHEN e.type IN ('star', 'external_click') THEN 1 END) as positive_interactions
                FROM articles a
                LEFT JOIN events e ON a.id = e.article_id
                WHERE a.published_at > NOW() - INTERVAL '30 days'
                GROUP BY source
                HAVING COUNT(*) >= 5
            """))
            
            self.source_scores = {}
            for row in result:
                self.source_scores[row.source] = {
                    'article_count': row.article_count,
                    'avg_score': float(row.avg_score or 0),
                    'positive_interactions': row.positive_interactions or 0,
                    'interaction_rate': (row.positive_interactions or 0) / max(1, row.article_count)
                }
            
            # Topic popularity
            result = self.db.execute(text("""
                SELECT 
                    unnest(topics) as topic, 
                    COUNT(*) as frequency,
                    AVG(score_total) as avg_score
                FROM articles 
                WHERE topics IS NOT NULL 
                AND published_at > NOW() - INTERVAL '30 days'
                GROUP BY unnest(topics)
                HAVING COUNT(*) >= 3
                ORDER BY frequency DESC
                LIMIT 100
            """))
            
            self.topic_popularity = {}
            for row in result:
                self.topic_popularity[row.topic] = {
                    'frequency': row.frequency,
                    'avg_score': float(row.avg_score or 0)
                }
            
            logger.info(f"Cached stats: {len(self.source_scores)} sources, {len(self.topic_popularity)} topics")
            
        except Exception as e:
            logger.error(f"Error caching global stats: {e}")
            self.source_scores = {}
            self.topic_popularity = {}
    
    def extract_advanced_content_features(
        self,
        article_id: int,
        title: str,
        content: Optional[str],
        source: str,
        topics: List[str],
        score_total: int,
        score_breakdown: Dict[str, Any],
        published_at: datetime,
        has_image: bool
    ) -> np.ndarray:
        """Extract advanced content features"""
        features = []
        
        # Title analysis
        title_words = len(title.split()) if title else 0
        title_chars = len(title) if title else 0
        title_has_numbers = bool(re.search(r'\d', title or ''))
        title_has_caps = bool(re.search(r'[A-Z]{2,}', title or ''))
        title_question = title.endswith('?') if title else False
        
        features.extend([
            float(title_words),
            float(title_chars),
            float(title_has_numbers),
            float(title_has_caps),
            float(title_question),
        ])
        
        # Content analysis
        if content:
            content_words = len(content.split())
            content_chars = len(content)
            content_sentences = len(re.split(r'[.!?]+', content))
            avg_sentence_length = content_words / max(1, content_sentences)
            content_has_links = bool(re.search(r'https?://', content))
        else:
            content_words = content_chars = content_sentences = avg_sentence_length = 0
            content_has_links = False
        
        features.extend([
            float(content_words),
            float(content_chars),
            float(content_sentences),
            float(avg_sentence_length),
            float(content_has_links),
        ])
        
        # Source features
        source_stats = self.source_scores.get(source, {})
        source_article_count = source_stats.get('article_count', 1)
        source_avg_score = source_stats.get('avg_score', 50)
        source_interaction_rate = source_stats.get('interaction_rate', 0)
        source_popularity = min(1.0, source_article_count / 100)  # Normalize
        
        features.extend([
            float(source_popularity),
            float(source_avg_score / 100),  # Normalize to 0-1
            float(source_interaction_rate),
        ])
        
        # Topic features
        if topics:
            topic_count = len(topics)
            topic_popularity_sum = sum(self.topic_popularity.get(topic, {}).get('frequency', 0) for topic in topics)
            topic_score_avg = sum(self.topic_popularity.get(topic, {}).get('avg_score', 0) for topic in topics) / max(1, len(topics))
            
            # Check for trending topics
            trending_topics = ['ai', 'crypto', 'blockchain', 'fintech', 'ml', 'defi', 'nft']
            has_trending = any(any(trend in topic.lower() for trend in trending_topics) for topic in topics)
        else:
            topic_count = topic_popularity_sum = topic_score_avg = 0
            has_trending = False
        
        features.extend([
            float(topic_count),
            float(min(1.0, topic_popularity_sum / 1000)),  # Normalize
            float(topic_score_avg / 100),  # Normalize
            float(has_trending),
        ])
        
        # Time-based features
        now = datetime.now(timezone.utc)
        if published_at.tzinfo is None:
            published_at = published_at.replace(tzinfo=timezone.utc)
        
        hours_old = (now - published_at).total_seconds() / 3600
        day_of_week = published_at.weekday()  # 0=Monday, 6=Sunday
        hour_of_day = published_at.hour
        
        # Time patterns
        is_weekend = day_of_week >= 5
        is_business_hours = 9 <= hour_of_day <= 17
        is_morning = 6 <= hour_of_day <= 12
        is_evening = 18 <= hour_of_day <= 23
        
        features.extend([
            float(min(1.0, hours_old / 168)),  # Normalize to weeks
            float(day_of_week / 7),  # Normalize
            float(hour_of_day / 24),  # Normalize
            float(is_weekend),
            float(is_business_hours),
            float(is_morning),
            float(is_evening),
        ])
        
        # Engagement prediction features
        features.extend([
            float(has_image),
            float(score_total / 200),  # Normalize rule score
            float(min(1.0, title_chars / 100)),  # Title length normalized
        ])
        
        # Quality features - add to ML features
        try:
            quality_feats = extract_quality_features(
                title, content or "", source, score_breakdown
            )
            features.extend(quality_feats.tolist())
        except Exception as e:
            logger.error(f"Error extracting quality features: {e}")
            # Add zeros if quality feature extraction fails
            features.extend([0.0] * 10)  # Match expected quality feature count
        
        return np.array(features, dtype=np.float32)
    
    def extract_user_context_features(
        self,
        user_id: str,
        article_source: str,
        article_topics: List[str],
        lookback_days: int = 30
    ) -> np.ndarray:
        """Extract user context and behavior features"""
        features = []
        
        cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)
        
        try:
            # User's source preferences
            result = self.db.execute(text("""
                SELECT 
                    a.source,
                    COUNT(*) as interactions,
                    COUNT(CASE WHEN e.type = 'star' THEN 1 END) as stars,
                    COUNT(CASE WHEN e.type = 'external_click' THEN 1 END) as clicks,
                    AVG(CASE WHEN e.type = 'open' AND e.duration_ms > 0 THEN e.duration_ms END) as avg_dwell
                FROM events e
                JOIN articles a ON e.article_id = a.id
                WHERE e.user_id = :user_id 
                AND e.created_at > :cutoff
                AND e.type IN ('star', 'external_click', 'open')
                GROUP BY a.source
            """), {"user_id": user_id, "cutoff": cutoff})
            
            user_source_prefs = {}
            total_interactions = 0
            for row in result:
                interactions = row.interactions
                total_interactions += interactions
                user_source_prefs[row.source] = {
                    'interactions': interactions,
                    'stars': row.stars or 0,
                    'clicks': row.clicks or 0,
                    'avg_dwell': row.avg_dwell or 0,
                    'star_rate': (row.stars or 0) / max(1, interactions),
                    'click_rate': (row.clicks or 0) / max(1, interactions)
                }
            
            # User's preference for this source
            source_prefs = user_source_prefs.get(article_source, {})
            source_interactions = source_prefs.get('interactions', 0)
            source_preference = source_interactions / max(1, total_interactions) if total_interactions > 0 else 0
            source_star_rate = source_prefs.get('star_rate', 0)
            source_click_rate = source_prefs.get('click_rate', 0)
            source_avg_dwell = source_prefs.get('avg_dwell', 0) / 1000  # Convert to seconds
            
            features.extend([
                float(source_preference),
                float(source_star_rate),
                float(source_click_rate),
                float(min(1.0, source_avg_dwell / 60)),  # Normalize to minutes
            ])
            
            # User's topic preferences
            topic_interactions = {}
            if article_topics:
                for topic in article_topics:
                    # Count interactions with articles containing this topic
                    result = self.db.execute(text("""
                        SELECT COUNT(*) as count
                        FROM events e
                        JOIN articles a ON e.article_id = a.id
                        WHERE e.user_id = :user_id 
                        AND e.created_at > :cutoff
                        AND e.type IN ('star', 'external_click')
                        AND :topic = ANY(a.topics)
                    """), {"user_id": user_id, "cutoff": cutoff, "topic": topic})
                    
                    count = result.scalar() or 0
                    topic_interactions[topic] = count
            
            # Topic preference score
            topic_pref_score = sum(topic_interactions.values()) / max(1, len(article_topics)) if article_topics else 0
            max_topic_interactions = max(topic_interactions.values()) if topic_interactions else 0
            
            features.extend([
                float(min(1.0, topic_pref_score / 10)),  # Normalize
                float(min(1.0, max_topic_interactions / 5)),  # Normalize
            ])
            
            # User activity patterns
            result = self.db.execute(text("""
                SELECT 
                    COUNT(*) as total_events,
                    COUNT(DISTINCT DATE(e.created_at)) as active_days,
                    AVG(CASE WHEN e.type = 'open' AND e.duration_ms > 0 THEN e.duration_ms END) as avg_dwell,
                    COUNT(CASE WHEN e.type = 'star' THEN 1 END) as total_stars,
                    COUNT(CASE WHEN e.type = 'external_click' THEN 1 END) as total_clicks
                FROM events e
                WHERE e.user_id = :user_id 
                AND e.created_at > :cutoff
            """), {"user_id": user_id, "cutoff": cutoff})
            
            row = result.fetchone()
            if row:
                total_events = row.total_events or 0
                active_days = row.active_days or 1
                avg_dwell = (row.avg_dwell or 0) / 1000  # Convert to seconds
                total_stars = row.total_stars or 0
                total_clicks = row.total_clicks or 0
                
                engagement_rate = (total_stars + total_clicks) / max(1, total_events)
                activity_frequency = active_days / lookback_days
            else:
                engagement_rate = activity_frequency = avg_dwell = 0
            
            features.extend([
                float(min(1.0, engagement_rate)),
                float(activity_frequency),
                float(min(1.0, avg_dwell / 60)),  # Normalize to minutes
            ])
            
        except Exception as e:
            logger.error(f"Error extracting user context features: {e}")
            # Return zeros if error
            features.extend([0.0] * 10)  # Match expected feature count
        
        return np.array(features, dtype=np.float32)
    
    def extract_all_features(
        self,
        article_id: int,
        title: str,
        content: Optional[str],
        source: str,
        topics: List[str],
        score_total: int,
        published_at: datetime,
        has_image: bool,
        user_id: str = "owner"
    ) -> np.ndarray:
        """Extract all advanced features for an article"""
        
        # Content features
        content_features = self.extract_advanced_content_features(
            article_id, title, content, source, topics, score_total, published_at, has_image
        )
        
        # User context features  
        user_features = self.extract_user_context_features(
            user_id, source, topics
        )
        
        # Combine all features
        all_features = np.concatenate([content_features, user_features])
        
        logger.debug(f"Extracted {len(all_features)} features for article {article_id}")
        return all_features

def build_advanced_training_dataset(
    db: Session,
    lookback_days: int = 45,
    min_interactions: int = 2
) -> Tuple[np.ndarray, np.ndarray, List[str]]:
    """Build advanced training dataset with improved features"""
    
    extractor = AdvancedFeatureExtractor(db)
    cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)
    
    logger.info(f"Building advanced training dataset, lookback={lookback_days} days")
    
    # Get articles with events and enough data
    result = db.execute(text("""
        SELECT DISTINCT
            a.id, a.title, a.content, a.full_content, a.source, a.topics,
            a.score_total, a.published_at, a.has_image,
            CASE 
                WHEN COUNT(CASE WHEN e.type IN ('star', 'external_click', 'open') THEN 1 END) > 0 THEN 1
                ELSE 0 
            END as is_positive
        FROM articles a
        JOIN events e ON a.id = e.article_id
        WHERE e.created_at > :cutoff
        AND a.published_at > :cutoff - INTERVAL '7 days'
        GROUP BY a.id, a.title, a.content, a.full_content, a.source, a.topics,
                 a.score_total, a.published_at, a.has_image
        HAVING COUNT(e.id) >= :min_interactions
        ORDER BY a.published_at DESC
        LIMIT 1000
    """), {"cutoff": cutoff, "min_interactions": min_interactions})
    
    articles = result.fetchall()
    logger.info(f"Found {len(articles)} articles for advanced training")
    
    if len(articles) < 10:
        raise ValueError(f"Not enough articles for training: {len(articles)}")
    
    X_data = []
    y_data = []
    feature_names = None
    
    for article in articles:
        try:
            topics = article.topics if article.topics else []
            content = article.full_content or article.content
            
            features = extractor.extract_all_features(
                article.id, article.title, content, article.source,
                topics, article.score_total, article.published_at,
                article.has_image
            )
            
            if feature_names is None:
                feature_names = [f"feature_{i}" for i in range(len(features))]
            
            X_data.append(features)
            y_data.append(article.is_positive)
            
        except Exception as e:
            logger.error(f"Error processing article {article.id}: {e}")
            continue
    
    if not X_data:
        raise ValueError("No valid training samples created")
    
    X = np.array(X_data)
    y = np.array(y_data)
    
    logger.info(f"Created advanced training dataset: {X.shape[0]} samples, {X.shape[1]} features")
    logger.info(f"Positive samples: {sum(y)}, Negative samples: {len(y) - sum(y)}")
    
    return X, y, feature_names