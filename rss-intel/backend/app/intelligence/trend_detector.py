#!/usr/bin/env python3
"""
Advanced Trend Detection System for RSS Intelligence
Uses semantic clustering and temporal analysis to detect emerging trends
"""

import asyncio
import logging
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from collections import defaultdict, Counter
import json

from sklearn.cluster import DBSCAN
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import networkx as nx

from ..config import settings
from ..store import Article, SessionLocal
from ..ml.embedding import get_embeddings_batch
from ..events import publish_trend_event, EventType
from ..notifications import send_trend_alert

logger = logging.getLogger(__name__)


@dataclass
class TrendCluster:
    """Represents a detected trend cluster"""
    id: str
    keywords: List[str]
    articles: List[int]  # article IDs
    strength: float  # trend strength score
    growth_rate: float  # how fast it's growing
    first_seen: datetime
    last_updated: datetime
    category: Optional[str] = None
    sentiment: Optional[float] = None
    geographic_focus: Optional[str] = None


@dataclass  
class TrendSignal:
    """Individual signal contributing to a trend"""
    type: str  # 'keyword', 'semantic', 'temporal', 'source'
    value: float
    confidence: float
    metadata: Dict[str, Any]


class SemanticTrendDetector:
    """Advanced trend detection using semantic analysis and clustering"""
    
    def __init__(self):
        self.min_articles_for_trend = 3
        self.trend_strength_threshold = 0.3
        self.semantic_similarity_threshold = 0.7
        self.temporal_window_hours = 24
        self.max_trends_to_track = 100
        
        # Cache for computational efficiency
        self.article_embeddings = {}
        self.trend_clusters = {}
        self.keyword_trends = defaultdict(list)
        self.last_analysis = None
        
        # ML models
        self.tfidf_vectorizer = TfidfVectorizer(
            max_features=1000,
            stop_words='english',
            ngram_range=(1, 3),
            min_df=2,
            max_df=0.8
        )
    
    async def detect_trends(self, hours_back: int = 24) -> List[TrendCluster]:
        """Main trend detection pipeline"""
        logger.info(f"Starting trend detection for last {hours_back} hours")
        
        db = SessionLocal()
        try:
            # Get recent articles
            since = datetime.utcnow() - timedelta(hours=hours_back)
            articles = db.query(Article).filter(
                Article.published_at >= since,
                Article.score_total >= 5.0  # Focus on quality content
            ).order_by(Article.published_at.desc()).limit(1000).all()
            
            if len(articles) < self.min_articles_for_trend:
                logger.warning(f"Insufficient articles for trend detection: {len(articles)}")
                return []
            
            logger.info(f"Analyzing {len(articles)} articles for trends")
            
            # Multi-stage trend detection
            trends = []
            
            # 1. Keyword-based trends
            keyword_trends = await self._detect_keyword_trends(articles)
            trends.extend(keyword_trends)
            
            # 2. Semantic clustering trends  
            semantic_trends = await self._detect_semantic_trends(articles)
            trends.extend(semantic_trends)
            
            # 3. Temporal pattern trends
            temporal_trends = await self._detect_temporal_trends(articles)
            trends.extend(temporal_trends)
            
            # 4. Source-based trends
            source_trends = await self._detect_source_trends(articles)
            trends.extend(source_trends)
            
            # Consolidate and rank trends
            consolidated_trends = await self._consolidate_trends(trends, articles)
            
            # Update trend tracking
            await self._update_trend_tracking(consolidated_trends)
            
            # Publish significant trends as events
            await self._publish_trend_events(consolidated_trends)
            
            logger.info(f"Detected {len(consolidated_trends)} significant trends")
            return consolidated_trends
            
        except Exception as e:
            logger.error(f"Trend detection error: {e}")
            return []
        finally:
            db.close()
    
    async def _detect_keyword_trends(self, articles: List[Article]) -> List[TrendCluster]:
        """Detect trends based on keyword frequency and growth"""
        logger.debug("Analyzing keyword trends...")
        
        # Extract keywords from titles and content
        texts = []
        article_times = []
        
        for article in articles:
            text = f"{article.title} {article.content or ''}"
            texts.append(text)
            article_times.append(article.published_at)
        
        if not texts:
            return []
        
        # TF-IDF analysis
        try:
            tfidf_matrix = self.tfidf_vectorizer.fit_transform(texts)
            feature_names = self.tfidf_vectorizer.get_feature_names_out()
        except Exception as e:
            logger.warning(f"TF-IDF analysis failed: {e}")
            return []
        
        # Calculate keyword trends over time
        time_buckets = self._create_time_buckets(article_times, bucket_hours=4)
        keyword_trends = []
        
        for i, keyword in enumerate(feature_names):
            keyword_scores = tfidf_matrix[:, i].toarray().flatten()
            
            # Calculate trend strength and growth
            trend_data = self._calculate_keyword_trend_strength(
                keyword, keyword_scores, article_times, time_buckets
            )
            
            if trend_data['strength'] > self.trend_strength_threshold:
                # Find articles strongly associated with this keyword
                article_indices = np.where(keyword_scores > np.percentile(keyword_scores, 80))[0]
                article_ids = [articles[idx].id for idx in article_indices]
                
                cluster = TrendCluster(
                    id=f"keyword_{keyword}_{int(datetime.utcnow().timestamp())}",
                    keywords=[keyword],
                    articles=article_ids,
                    strength=trend_data['strength'],
                    growth_rate=trend_data['growth_rate'],
                    first_seen=min(articles[idx].published_at for idx in article_indices),
                    last_updated=datetime.utcnow(),
                    category="keyword_trend"
                )
                keyword_trends.append(cluster)
        
        # Sort by strength and return top trends
        keyword_trends.sort(key=lambda x: x.strength, reverse=True)
        return keyword_trends[:20]
    
    async def _detect_semantic_trends(self, articles: List[Article]) -> List[TrendCluster]:
        """Detect trends using semantic similarity clustering"""
        logger.debug("Analyzing semantic trends...")
        
        if len(articles) < self.min_articles_for_trend:
            return []
        
        # Get embeddings for articles
        texts = [f"{article.title} {article.content or ''}" for article in articles]
        
        try:
            embeddings = await get_embeddings_batch(texts[:500])  # Limit for performance
            if not embeddings:
                logger.warning("No embeddings generated for semantic analysis")
                return []
            
            embeddings_array = np.array(embeddings)
            
        except Exception as e:
            logger.warning(f"Embedding generation failed: {e}")
            return []
        
        # DBSCAN clustering for trend detection
        clustering = DBSCAN(
            eps=1 - self.semantic_similarity_threshold,  # Convert similarity to distance
            min_samples=self.min_articles_for_trend,
            metric='cosine'
        )
        
        cluster_labels = clustering.fit_predict(embeddings_array)
        
        semantic_trends = []
        unique_labels = set(cluster_labels)
        
        for label in unique_labels:
            if label == -1:  # Noise cluster
                continue
                
            # Get articles in this cluster
            cluster_indices = np.where(cluster_labels == label)[0]
            cluster_articles = [articles[i] for i in cluster_indices[:len(articles)]]
            
            if len(cluster_articles) < self.min_articles_for_trend:
                continue
            
            # Extract representative keywords for this cluster
            cluster_texts = [f"{a.title} {a.content or ''}" for a in cluster_articles]
            cluster_keywords = self._extract_cluster_keywords(cluster_texts)
            
            # Calculate trend strength based on temporal distribution and scores
            trend_strength = self._calculate_semantic_trend_strength(cluster_articles)
            
            if trend_strength > self.trend_strength_threshold:
                cluster = TrendCluster(
                    id=f"semantic_{label}_{int(datetime.utcnow().timestamp())}",
                    keywords=cluster_keywords,
                    articles=[a.id for a in cluster_articles],
                    strength=trend_strength,
                    growth_rate=self._calculate_growth_rate(cluster_articles),
                    first_seen=min(a.published_at for a in cluster_articles),
                    last_updated=datetime.utcnow(),
                    category="semantic_trend"
                )
                semantic_trends.append(cluster)
        
        logger.debug(f"Found {len(semantic_trends)} semantic trends")
        return semantic_trends
    
    async def _detect_temporal_trends(self, articles: List[Article]) -> List[TrendCluster]:
        """Detect trends based on temporal patterns"""
        logger.debug("Analyzing temporal trends...")
        
        # Group articles by hour and analyze velocity
        time_buckets = defaultdict(list)
        for article in articles:
            hour_key = article.published_at.strftime('%Y-%m-%d-%H')
            time_buckets[hour_key].append(article)
        
        # Look for acceleration patterns
        temporal_trends = []
        
        # Analyze publication velocity
        bucket_counts = [(k, len(v)) for k, v in time_buckets.items()]
        bucket_counts.sort()
        
        if len(bucket_counts) > 3:
            # Calculate moving averages to detect acceleration
            counts = [c for _, c in bucket_counts]
            moving_avg = np.convolve(counts, np.ones(3)/3, mode='valid')
            
            # Find significant increases
            for i in range(1, len(moving_avg)):
                if moving_avg[i] > moving_avg[i-1] * 1.5:  # 50% increase
                    # This represents a surge in activity
                    surge_time = bucket_counts[i+2][0]  # Account for convolution offset
                    surge_articles = time_buckets[surge_time]
                    
                    if len(surge_articles) >= self.min_articles_for_trend:
                        # Extract keywords from surge articles
                        surge_texts = [f"{a.title} {a.content or ''}" for a in surge_articles]
                        surge_keywords = self._extract_cluster_keywords(surge_texts)
                        
                        cluster = TrendCluster(
                            id=f"temporal_{surge_time}_{int(datetime.utcnow().timestamp())}",
                            keywords=surge_keywords,
                            articles=[a.id for a in surge_articles],
                            strength=min(moving_avg[i] / moving_avg[i-1], 2.0),  # Cap at 2.0
                            growth_rate=moving_avg[i] - moving_avg[i-1],
                            first_seen=min(a.published_at for a in surge_articles),
                            last_updated=datetime.utcnow(),
                            category="temporal_surge"
                        )
                        temporal_trends.append(cluster)
        
        return temporal_trends
    
    async def _detect_source_trends(self, articles: List[Article]) -> List[TrendCluster]:
        """Detect trends based on source behavior and cross-source correlation"""
        logger.debug("Analyzing source trends...")
        
        # Group by source
        source_articles = defaultdict(list)
        for article in articles:
            source_articles[article.source].append(article)
        
        source_trends = []
        
        # Look for sources covering similar topics simultaneously
        sources_keywords = {}
        for source, articles_list in source_articles.items():
            if len(articles_list) >= 2:  # Minimum articles per source
                texts = [f"{a.title} {a.content or ''}" for a in articles_list]
                keywords = self._extract_cluster_keywords(texts)
                sources_keywords[source] = {
                    'keywords': keywords,
                    'articles': articles_list,
                    'avg_score': np.mean([a.score_total for a in articles_list])
                }
        
        # Find keyword overlaps across sources
        source_pairs = [(s1, s2) for s1 in sources_keywords.keys() for s2 in sources_keywords.keys() if s1 < s2]
        
        for source1, source2 in source_pairs:
            kw1 = set(sources_keywords[source1]['keywords'])
            kw2 = set(sources_keywords[source2]['keywords'])
            
            overlap = kw1.intersection(kw2)
            if len(overlap) >= 2:  # Significant keyword overlap
                # Combine articles from both sources
                combined_articles = sources_keywords[source1]['articles'] + sources_keywords[source2]['articles']
                combined_score = (sources_keywords[source1]['avg_score'] + sources_keywords[source2]['avg_score']) / 2
                
                if combined_score > 6.0:  # High quality threshold
                    cluster = TrendCluster(
                        id=f"source_{source1}_{source2}_{int(datetime.utcnow().timestamp())}",
                        keywords=list(overlap),
                        articles=[a.id for a in combined_articles],
                        strength=len(overlap) / 10.0,  # Normalize strength
                        growth_rate=combined_score / 10.0,
                        first_seen=min(a.published_at for a in combined_articles),
                        last_updated=datetime.utcnow(),
                        category="cross_source_trend"
                    )
                    source_trends.append(cluster)
        
        return source_trends
    
    async def _consolidate_trends(self, trends: List[TrendCluster], articles: List[Article]) -> List[TrendCluster]:
        """Consolidate similar trends and remove duplicates"""
        if not trends:
            return []
        
        logger.debug(f"Consolidating {len(trends)} preliminary trends...")
        
        # Group trends by keyword similarity
        consolidated = []
        used_trends = set()
        
        for i, trend1 in enumerate(trends):
            if i in used_trends:
                continue
                
            similar_trends = [trend1]
            
            for j, trend2 in enumerate(trends):
                if j <= i or j in used_trends:
                    continue
                
                # Calculate keyword overlap
                kw1 = set(trend1.keywords)
                kw2 = set(trend2.keywords)
                overlap = len(kw1.intersection(kw2)) / len(kw1.union(kw2)) if kw1.union(kw2) else 0
                
                if overlap > 0.5:  # 50% keyword similarity
                    similar_trends.append(trend2)
                    used_trends.add(j)
            
            # Merge similar trends
            if len(similar_trends) > 1:
                merged_trend = self._merge_trends(similar_trends)
                consolidated.append(merged_trend)
            else:
                consolidated.append(trend1)
            
            used_trends.add(i)
        
        # Sort by strength and return top trends
        consolidated.sort(key=lambda x: x.strength, reverse=True)
        return consolidated[:self.max_trends_to_track]
    
    def _merge_trends(self, trends: List[TrendCluster]) -> TrendCluster:
        """Merge multiple similar trends into one"""
        # Combine keywords (unique only)
        all_keywords = []
        for trend in trends:
            all_keywords.extend(trend.keywords)
        unique_keywords = list(set(all_keywords))
        
        # Combine articles
        all_articles = []
        for trend in trends:
            all_articles.extend(trend.articles)
        unique_articles = list(set(all_articles))
        
        # Calculate merged metrics
        avg_strength = np.mean([t.strength for t in trends])
        max_growth_rate = max([t.growth_rate for t in trends])
        earliest_seen = min([t.first_seen for t in trends])
        
        return TrendCluster(
            id=f"merged_{int(datetime.utcnow().timestamp())}",
            keywords=unique_keywords[:10],  # Limit to top keywords
            articles=unique_articles,
            strength=avg_strength,
            growth_rate=max_growth_rate,
            first_seen=earliest_seen,
            last_updated=datetime.utcnow(),
            category="merged_trend"
        )
    
    async def _update_trend_tracking(self, trends: List[TrendCluster]):
        """Update persistent trend tracking"""
        for trend in trends:
            self.trend_clusters[trend.id] = trend
        
        # Clean up old trends (older than 7 days)
        cutoff = datetime.utcnow() - timedelta(days=7)
        to_remove = [
            trend_id for trend_id, trend in self.trend_clusters.items()
            if trend.last_updated < cutoff
        ]
        
        for trend_id in to_remove:
            del self.trend_clusters[trend_id]
        
        logger.info(f"Updated trend tracking: {len(trends)} new trends, {len(to_remove)} removed")
    
    async def _publish_trend_events(self, trends: List[TrendCluster]):
        """Publish significant trends as events"""
        significant_trends = [t for t in trends if t.strength > 0.7]  # High significance threshold
        
        for trend in significant_trends:
            try:
                trend_data = {
                    'trend_id': trend.id,
                    'trend_name': ' + '.join(trend.keywords[:3]),
                    'keywords': trend.keywords,
                    'strength': trend.strength,
                    'growth_rate': trend.growth_rate,
                    'article_count': len(trend.articles),
                    'category': trend.category,
                    'confidence': min(trend.strength, 1.0)
                }
                
                # Publish as event
                await publish_trend_event(trend_data)
                
                # Send notifications to interested users
                # TODO: Implement user interest matching
                await send_trend_alert("test-user", trend_data)
                
                logger.info(f"Published trend event: {trend_data['trend_name']}")
                
            except Exception as e:
                logger.error(f"Error publishing trend event: {e}")
    
    # Helper methods
    def _create_time_buckets(self, times: List[datetime], bucket_hours: int = 4) -> Dict:
        """Create time buckets for temporal analysis"""
        buckets = defaultdict(list)
        for i, time in enumerate(times):
            bucket_key = time.replace(minute=0, second=0, microsecond=0)
            bucket_key = bucket_key.replace(hour=bucket_key.hour // bucket_hours * bucket_hours)
            buckets[bucket_key].append(i)
        return buckets
    
    def _calculate_keyword_trend_strength(self, keyword: str, scores: np.ndarray, times: List[datetime], time_buckets: Dict) -> Dict:
        """Calculate trend strength for a keyword"""
        if len(scores) == 0:
            return {'strength': 0.0, 'growth_rate': 0.0}
        
        # Basic strength metrics
        max_score = np.max(scores)
        avg_score = np.mean(scores)
        score_variance = np.var(scores)
        
        # Temporal distribution analysis
        recent_threshold = datetime.utcnow() - timedelta(hours=12)
        recent_count = sum(1 for t in times if t > recent_threshold)
        total_count = len(times)
        recency_factor = recent_count / total_count if total_count > 0 else 0
        
        # Calculate growth rate
        if len(time_buckets) > 1:
            bucket_keys = sorted(time_buckets.keys())
            early_buckets = bucket_keys[:len(bucket_keys)//2]
            late_buckets = bucket_keys[len(bucket_keys)//2:]
            
            early_avg = np.mean([len(time_buckets[k]) for k in early_buckets])
            late_avg = np.mean([len(time_buckets[k]) for k in late_buckets])
            
            growth_rate = (late_avg - early_avg) / max(early_avg, 1)
        else:
            growth_rate = 0.0
        
        # Combine factors for overall strength
        strength = (max_score * 0.3 + avg_score * 0.3 + recency_factor * 0.4) * min(score_variance + 0.1, 1.0)
        
        return {
            'strength': min(strength, 2.0),  # Cap at 2.0
            'growth_rate': growth_rate
        }
    
    def _calculate_semantic_trend_strength(self, articles: List[Article]) -> float:
        """Calculate trend strength for semantic clusters"""
        if not articles:
            return 0.0
        
        # Score-based strength
        scores = [a.score_total for a in articles]
        avg_score = np.mean(scores)
        score_factor = min(avg_score / 10.0, 1.0)  # Normalize to 0-1
        
        # Temporal concentration
        times = [a.published_at for a in articles]
        time_span = (max(times) - min(times)).total_seconds() / 3600  # hours
        concentration_factor = max(0.1, 1 / (time_span + 1))  # Higher if more concentrated
        
        # Article count factor
        count_factor = min(len(articles) / 20.0, 1.0)  # Normalize to 0-1
        
        return score_factor * 0.5 + concentration_factor * 0.3 + count_factor * 0.2
    
    def _calculate_growth_rate(self, articles: List[Article]) -> float:
        """Calculate growth rate for a trend"""
        if len(articles) < 2:
            return 0.0
        
        # Sort by time
        sorted_articles = sorted(articles, key=lambda a: a.published_at)
        
        # Calculate rate of publication
        time_span_hours = (sorted_articles[-1].published_at - sorted_articles[0].published_at).total_seconds() / 3600
        if time_span_hours == 0:
            return len(articles)  # All published at same time
        
        return len(articles) / time_span_hours  # Articles per hour
    
    def _extract_cluster_keywords(self, texts: List[str], max_keywords: int = 10) -> List[str]:
        """Extract representative keywords from a cluster of texts"""
        if not texts:
            return []
        
        try:
            # Use TF-IDF to find important terms
            vectorizer = TfidfVectorizer(
                max_features=50,
                stop_words='english',
                ngram_range=(1, 2),
                min_df=1
            )
            
            tfidf_matrix = vectorizer.fit_transform(texts)
            feature_names = vectorizer.get_feature_names_out()
            
            # Calculate mean TF-IDF scores
            mean_scores = np.array(tfidf_matrix.mean(axis=0)).flatten()
            
            # Get top keywords
            top_indices = mean_scores.argsort()[-max_keywords:][::-1]
            top_keywords = [feature_names[i] for i in top_indices if mean_scores[i] > 0]
            
            return top_keywords
            
        except Exception as e:
            logger.warning(f"Keyword extraction failed: {e}")
            # Fallback: simple word frequency
            all_words = ' '.join(texts).lower().split()
            word_freq = Counter(all_words)
            common_words = [word for word, count in word_freq.most_common(max_keywords)]
            return common_words
    
    def get_trend_summary(self) -> Dict[str, Any]:
        """Get current trend analysis summary"""
        active_trends = [t for t in self.trend_clusters.values() 
                        if (datetime.utcnow() - t.last_updated).total_seconds() < 86400]  # Last 24h
        
        return {
            'total_trends_tracked': len(self.trend_clusters),
            'active_trends_24h': len(active_trends),
            'top_trending_keywords': self._get_top_trending_keywords(active_trends),
            'trend_categories': self._get_trend_categories(active_trends),
            'last_analysis': self.last_analysis.isoformat() if self.last_analysis else None
        }
    
    def _get_top_trending_keywords(self, trends: List[TrendCluster], limit: int = 20) -> List[Dict]:
        """Get top trending keywords with their strength"""
        keyword_strength = defaultdict(float)
        
        for trend in trends:
            for keyword in trend.keywords:
                keyword_strength[keyword] += trend.strength
        
        sorted_keywords = sorted(keyword_strength.items(), key=lambda x: x[1], reverse=True)
        return [{'keyword': kw, 'strength': strength} for kw, strength in sorted_keywords[:limit]]
    
    def _get_trend_categories(self, trends: List[TrendCluster]) -> Dict[str, int]:
        """Get trend distribution by category"""
        categories = defaultdict(int)
        for trend in trends:
            categories[trend.category or 'unknown'] += 1
        return dict(categories)


# Global trend detector instance
trend_detector = SemanticTrendDetector()


# Background task for continuous trend detection
async def continuous_trend_detection():
    """Background task that runs trend detection periodically"""
    while True:
        try:
            logger.info("Starting periodic trend detection...")
            trends = await trend_detector.detect_trends(hours_back=24)
            trend_detector.last_analysis = datetime.utcnow()
            
            logger.info(f"Periodic trend detection completed: {len(trends)} trends detected")
            
            # Wait 30 minutes before next analysis
            await asyncio.sleep(1800)
            
        except Exception as e:
            logger.error(f"Error in continuous trend detection: {e}")
            # Wait 5 minutes before retrying on error
            await asyncio.sleep(300)


# API helper functions
async def get_current_trends(limit: int = 20) -> List[Dict[str, Any]]:
    """Get current trending topics"""
    trends = await trend_detector.detect_trends(hours_back=12)
    return [asdict(trend) for trend in trends[:limit]]


async def get_trend_by_keywords(keywords: List[str]) -> Optional[TrendCluster]:
    """Find trend matching specific keywords"""
    for trend in trend_detector.trend_clusters.values():
        if any(kw.lower() in [tk.lower() for tk in trend.keywords] for kw in keywords):
            return trend
    return None