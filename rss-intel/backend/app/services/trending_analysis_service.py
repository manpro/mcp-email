"""
Trending Analysis Service

Advanced trending detection, topic modeling, and content analysis for discovering
emerging topics, viral content, and content patterns across RSS feeds.
"""

import logging
import asyncio
from typing import Dict, List, Optional, Any, Set, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from collections import defaultdict, Counter
import json
import re
import hashlib
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_, or_
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
from sklearn.decomposition import LatentDirichletAllocation
import networkx as nx

from ..store import Article, Event, TrendingTopic, TopicAnalysis
from ..intelligence.content_extractor import extract_keywords

logger = logging.getLogger(__name__)

@dataclass
class TrendingItem:
    """Represents a trending item (topic, keyword, or source)"""
    item_id: str
    item_type: str  # 'topic', 'keyword', 'source', 'domain'
    title: str
    description: str
    trend_score: float
    velocity: float  # Rate of change
    engagement_score: float
    article_count: int
    unique_sources: int
    first_seen: datetime
    peak_time: datetime
    related_articles: List[int]
    keywords: List[str]
    confidence: float
    trend_direction: str  # 'rising', 'stable', 'declining'

@dataclass
class TopicCluster:
    """Represents a cluster of related articles"""
    cluster_id: str
    topic_name: str
    keywords: List[str]
    article_ids: List[int]
    coherence_score: float
    size: int
    timespan_hours: float
    geographic_spread: List[str]
    source_diversity: float

@dataclass
class TrendAnalysisResult:
    """Complete trend analysis result"""
    trending_topics: List[TrendingItem]
    emerging_topics: List[TrendingItem]
    topic_clusters: List[TopicCluster]
    viral_articles: List[int]
    trend_predictions: Dict[str, float]
    analysis_metadata: Dict[str, Any]

class TrendingAnalysisService:
    """Service for analyzing trending topics and content patterns"""
    
    def __init__(self, db: Session):
        self.db = db
        
        # Analysis parameters
        self.trending_window_hours = 24
        self.emerging_window_hours = 6
        self.min_articles_for_trend = 3
        self.min_sources_for_trend = 2
        self.topic_extraction_limit = 20
        
        # Text processing parameters
        self.max_features = 1000
        self.ngram_range = (1, 3)
        self.min_df = 2
        self.max_df = 0.8
        
        # Clustering parameters
        self.n_topic_clusters = 10
        self.min_cluster_size = 3
        
        # Trend detection thresholds
        self.viral_threshold = 0.8
        self.trending_threshold = 0.6
        self.emerging_threshold = 0.4
        
        # Stop words and filters
        self.stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 
            'of', 'with', 'by', 'this', 'that', 'these', 'those', 'is', 'are', 
            'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 
            'did', 'will', 'would', 'could', 'should', 'may', 'might', 'can', 
            'said', 'says', 'news', 'report', 'reports', 'article', 'story'
        }
    
    async def analyze_trending_topics(self, hours_back: int = 24) -> TrendAnalysisResult:
        """
        Comprehensive trending analysis
        
        Args:
            hours_back: Hours to look back for analysis
            
        Returns:
            Complete trend analysis results
        """
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours_back)
            
            # Get recent articles with engagement data
            articles_query = self.db.query(Article, func.count(Event.id).label('engagement_count')).outerjoin(
                Event, and_(Event.article_id == Article.id, Event.created_at >= cutoff_time)
            ).filter(
                Article.created_at >= cutoff_time,
                Article.score_total >= 30  # Minimum quality threshold
            ).group_by(Article.id).order_by(desc('engagement_count'), desc(Article.score_total))
            
            articles_with_engagement = articles_query.all()
            
            if not articles_with_engagement:
                return TrendAnalysisResult(
                    trending_topics=[], emerging_topics=[], topic_clusters=[],
                    viral_articles=[], trend_predictions={}, analysis_metadata={}
                )
            
            # Extract articles and engagement data
            articles = [item[0] for item in articles_with_engagement]
            engagement_counts = {item[0].id: item[1] for item in articles_with_engagement}
            
            logger.info(f"Analyzing {len(articles)} articles for trending topics")
            
            # Perform different types of analysis
            trending_topics = await self._detect_trending_topics(articles, engagement_counts)
            emerging_topics = await self._detect_emerging_topics(articles, engagement_counts)
            topic_clusters = await self._cluster_topics(articles)
            viral_articles = await self._identify_viral_content(articles, engagement_counts)
            trend_predictions = await self._predict_trends(articles, engagement_counts)
            
            # Generate metadata
            analysis_metadata = {
                'analysis_time': datetime.now().isoformat(),
                'hours_analyzed': hours_back,
                'articles_analyzed': len(articles),
                'total_engagement': sum(engagement_counts.values()),
                'unique_sources': len(set(a.source for a in articles if a.source)),
                'algorithm_version': '2.0'
            }
            
            return TrendAnalysisResult(
                trending_topics=trending_topics,
                emerging_topics=emerging_topics,
                topic_clusters=topic_clusters,
                viral_articles=viral_articles,
                trend_predictions=trend_predictions,
                analysis_metadata=analysis_metadata
            )
            
        except Exception as e:
            logger.error(f"Trending analysis failed: {e}")
            raise
    
    async def _detect_trending_topics(self, articles: List[Article], engagement_counts: Dict[int, int]) -> List[TrendingItem]:
        """Detect trending topics using keyword frequency and engagement"""
        try:
            # Extract keywords from all articles
            all_keywords = []
            keyword_articles = defaultdict(list)
            keyword_engagement = defaultdict(int)
            keyword_sources = defaultdict(set)
            keyword_timestamps = defaultdict(list)
            
            for article in articles:
                # Extract keywords from title and content
                text = f"{article.title or ''} {article.content or ''}"
                keywords = self._extract_keywords_from_text(text)
                
                for keyword in keywords:
                    all_keywords.append(keyword)
                    keyword_articles[keyword].append(article.id)
                    keyword_engagement[keyword] += engagement_counts.get(article.id, 0)
                    if article.source:
                        keyword_sources[keyword].add(article.source)
                    if article.published_at:
                        keyword_timestamps[keyword].append(article.published_at)
            
            # Calculate trend scores for keywords
            trending_items = []
            keyword_counts = Counter(all_keywords)
            
            for keyword, count in keyword_counts.most_common(self.topic_extraction_limit):
                if count < self.min_articles_for_trend:
                    continue
                
                sources = keyword_sources[keyword]
                if len(sources) < self.min_sources_for_trend:
                    continue
                
                # Calculate trend metrics
                engagement = keyword_engagement[keyword]
                velocity = self._calculate_velocity(keyword_timestamps[keyword])
                trend_score = self._calculate_trend_score(count, engagement, len(sources), velocity)
                
                if trend_score >= self.trending_threshold:
                    # Determine trend direction
                    direction = self._determine_trend_direction(keyword_timestamps[keyword])
                    
                    # Find peak time
                    timestamps = keyword_timestamps[keyword]
                    peak_time = max(timestamps, key=lambda x: x) if timestamps else datetime.now()
                    first_seen = min(timestamps) if timestamps else datetime.now()
                    
                    trending_item = TrendingItem(
                        item_id=f"keyword_{hashlib.md5(keyword.encode()).hexdigest()[:8]}",
                        item_type='keyword',
                        title=keyword,
                        description=f"Trending keyword with {count} articles from {len(sources)} sources",
                        trend_score=trend_score,
                        velocity=velocity,
                        engagement_score=engagement / max(count, 1),
                        article_count=count,
                        unique_sources=len(sources),
                        first_seen=first_seen,
                        peak_time=peak_time,
                        related_articles=keyword_articles[keyword],
                        keywords=[keyword],
                        confidence=min(trend_score, 1.0),
                        trend_direction=direction
                    )
                    
                    trending_items.append(trending_item)
            
            # Sort by trend score
            trending_items.sort(key=lambda x: x.trend_score, reverse=True)
            
            logger.info(f"Detected {len(trending_items)} trending topics")
            return trending_items[:20]  # Return top 20
            
        except Exception as e:
            logger.error(f"Trending topic detection failed: {e}")
            return []
    
    async def _detect_emerging_topics(self, articles: List[Article], engagement_counts: Dict[int, int]) -> List[TrendingItem]:
        """Detect emerging topics with recent acceleration"""
        try:
            recent_cutoff = datetime.now() - timedelta(hours=self.emerging_window_hours)
            recent_articles = [a for a in articles if a.created_at and a.created_at >= recent_cutoff]
            
            if not recent_articles:
                return []
            
            # Focus on very recent content
            emerging_keywords = []
            keyword_data = defaultdict(lambda: {'count': 0, 'engagement': 0, 'sources': set(), 'articles': []})
            
            for article in recent_articles:
                text = f"{article.title or ''} {article.content or ''}"
                keywords = self._extract_keywords_from_text(text)
                
                for keyword in keywords:
                    keyword_data[keyword]['count'] += 1
                    keyword_data[keyword]['engagement'] += engagement_counts.get(article.id, 0)
                    if article.source:
                        keyword_data[keyword]['sources'].add(article.source)
                    keyword_data[keyword]['articles'].append(article.id)
            
            # Calculate emerging scores
            emerging_items = []
            for keyword, data in keyword_data.items():
                if data['count'] < self.min_articles_for_trend:
                    continue
                
                # Emerging topics need diversity
                if len(data['sources']) < 2:
                    continue
                
                # Calculate emergence score (recent acceleration)
                recency_bonus = 2.0  # Boost for very recent content
                source_diversity = len(data['sources']) / max(data['count'], 1)
                engagement_rate = data['engagement'] / max(data['count'], 1)
                
                emerging_score = (data['count'] * recency_bonus * source_diversity * 
                                (1 + engagement_rate / 10)) / self.emerging_window_hours
                
                if emerging_score >= self.emerging_threshold:
                    emerging_item = TrendingItem(
                        item_id=f"emerging_{hashlib.md5(keyword.encode()).hexdigest()[:8]}",
                        item_type='emerging',
                        title=keyword,
                        description=f"Emerging topic with {data['count']} recent articles",
                        trend_score=emerging_score,
                        velocity=emerging_score,  # High velocity for emerging topics
                        engagement_score=engagement_rate,
                        article_count=data['count'],
                        unique_sources=len(data['sources']),
                        first_seen=recent_cutoff,
                        peak_time=datetime.now(),
                        related_articles=data['articles'],
                        keywords=[keyword],
                        confidence=min(emerging_score / 2, 1.0),
                        trend_direction='rising'
                    )
                    
                    emerging_items.append(emerging_item)
            
            # Sort by emerging score
            emerging_items.sort(key=lambda x: x.trend_score, reverse=True)
            
            logger.info(f"Detected {len(emerging_items)} emerging topics")
            return emerging_items[:10]  # Return top 10
            
        except Exception as e:
            logger.error(f"Emerging topic detection failed: {e}")
            return []
    
    async def _cluster_topics(self, articles: List[Article]) -> List[TopicCluster]:
        """Cluster articles into topic groups using LDA and k-means"""
        try:
            if len(articles) < self.min_cluster_size * 2:
                return []
            
            # Prepare text data
            documents = []
            article_metadata = []
            
            for article in articles:
                text = f"{article.title or ''} {article.content or ''}"
                if len(text.strip()) < 50:  # Skip very short content
                    continue
                    
                documents.append(text)
                article_metadata.append({
                    'id': article.id,
                    'source': article.source,
                    'published_at': article.published_at,
                    'score': article.score_total
                })
            
            if len(documents) < self.min_cluster_size:
                return []
            
            # TF-IDF vectorization
            vectorizer = TfidfVectorizer(
                max_features=self.max_features,
                ngram_range=self.ngram_range,
                min_df=self.min_df,
                max_df=self.max_df,
                stop_words='english'
            )
            
            doc_vectors = vectorizer.fit_transform(documents)
            feature_names = vectorizer.get_feature_names_out()
            
            # LDA topic modeling
            n_topics = min(self.n_topic_clusters, len(documents) // 2)
            lda = LatentDirichletAllocation(
                n_components=n_topics,
                random_state=42,
                max_iter=100
            )
            
            doc_topic_probs = lda.fit_transform(doc_vectors)
            
            # Create topic clusters
            topic_clusters = []
            
            for topic_idx in range(n_topics):
                # Get top keywords for this topic
                topic_keywords = []
                feature_weights = lda.components_[topic_idx]
                top_features = np.argsort(feature_weights)[-10:][::-1]
                
                for feature_idx in top_features:
                    topic_keywords.append(feature_names[feature_idx])
                
                # Find articles belonging to this topic (high probability)
                topic_articles = []
                for doc_idx, probs in enumerate(doc_topic_probs):
                    if probs[topic_idx] > 0.3:  # Threshold for topic membership
                        topic_articles.append(article_metadata[doc_idx])
                
                if len(topic_articles) >= self.min_cluster_size:
                    # Calculate cluster metrics
                    cluster_sources = set(a['source'] for a in topic_articles if a['source'])
                    cluster_timestamps = [a['published_at'] for a in topic_articles if a['published_at']]
                    
                    timespan_hours = 0
                    if cluster_timestamps:
                        timespan_hours = (max(cluster_timestamps) - min(cluster_timestamps)).total_seconds() / 3600
                    
                    coherence_score = np.mean([probs[topic_idx] for probs in doc_topic_probs if probs[topic_idx] > 0.3])
                    source_diversity = len(cluster_sources) / len(topic_articles)
                    
                    # Generate topic name from top keywords
                    topic_name = " ".join(topic_keywords[:3])
                    
                    cluster = TopicCluster(
                        cluster_id=f"cluster_{topic_idx}",
                        topic_name=topic_name.title(),
                        keywords=topic_keywords,
                        article_ids=[a['id'] for a in topic_articles],
                        coherence_score=coherence_score,
                        size=len(topic_articles),
                        timespan_hours=timespan_hours,
                        geographic_spread=[],  # Could be enhanced with location extraction
                        source_diversity=source_diversity
                    )
                    
                    topic_clusters.append(cluster)
            
            # Sort by cluster quality (coherence * size)
            topic_clusters.sort(key=lambda x: x.coherence_score * x.size, reverse=True)
            
            logger.info(f"Created {len(topic_clusters)} topic clusters")
            return topic_clusters
            
        except Exception as e:
            logger.error(f"Topic clustering failed: {e}")
            return []
    
    async def _identify_viral_content(self, articles: List[Article], engagement_counts: Dict[int, int]) -> List[int]:
        """Identify viral articles based on engagement patterns"""
        try:
            if not articles or not engagement_counts:
                return []
            
            # Calculate engagement statistics
            engagements = list(engagement_counts.values())
            if not engagements:
                return []
            
            mean_engagement = np.mean(engagements)
            std_engagement = np.std(engagements)
            
            if std_engagement == 0:
                return []
            
            # Find articles with exceptional engagement
            viral_articles = []
            
            for article in articles:
                engagement = engagement_counts.get(article.id, 0)
                
                if engagement == 0:
                    continue
                
                # Z-score for engagement
                z_score = (engagement - mean_engagement) / std_engagement
                
                # Additional viral indicators
                viral_score = 0.0
                
                # High engagement z-score
                if z_score >= 2.0:
                    viral_score += z_score / 3.0
                
                # High article quality score
                if article.score_total and article.score_total >= 80:
                    viral_score += 0.3
                
                # Recent publication (viral content spreads fast)
                if article.published_at:
                    hours_old = (datetime.now() - article.published_at).total_seconds() / 3600
                    if hours_old <= 6:
                        viral_score += 0.4
                    elif hours_old <= 12:
                        viral_score += 0.2
                
                # Check for viral keywords in title
                if article.title:
                    viral_keywords = ['breaking', 'urgent', 'exclusive', 'shocking', 'amazing', 'incredible']
                    title_lower = article.title.lower()
                    viral_keyword_count = sum(1 for kw in viral_keywords if kw in title_lower)
                    viral_score += viral_keyword_count * 0.1
                
                if viral_score >= self.viral_threshold:
                    viral_articles.append(article.id)
            
            logger.info(f"Identified {len(viral_articles)} viral articles")
            return viral_articles
            
        except Exception as e:
            logger.error(f"Viral content identification failed: {e}")
            return []
    
    async def _predict_trends(self, articles: List[Article], engagement_counts: Dict[int, int]) -> Dict[str, float]:
        """Predict future trending topics based on current patterns"""
        try:
            predictions = {}
            
            # Analyze keyword momentum
            current_time = datetime.now()
            recent_window = current_time - timedelta(hours=6)
            older_window = current_time - timedelta(hours=12)
            
            recent_keywords = Counter()
            older_keywords = Counter()
            
            for article in articles:
                if not article.published_at:
                    continue
                
                text = f"{article.title or ''} {article.content or ''}"
                keywords = self._extract_keywords_from_text(text)
                
                if article.published_at >= recent_window:
                    recent_keywords.update(keywords)
                elif article.published_at >= older_window:
                    older_keywords.update(keywords)
            
            # Calculate momentum for each keyword
            for keyword in recent_keywords:
                recent_count = recent_keywords[keyword]
                older_count = older_keywords.get(keyword, 0)
                
                if recent_count >= 2:  # Minimum threshold
                    # Calculate momentum (rate of change)
                    if older_count == 0:
                        momentum = recent_count * 2.0  # New keywords get boost
                    else:
                        momentum = (recent_count - older_count) / older_count
                    
                    # Predict future trend strength
                    prediction_score = min(momentum * 0.5, 1.0)
                    
                    if prediction_score > 0.2:
                        predictions[keyword] = prediction_score
            
            # Sort predictions by score
            predictions = dict(sorted(predictions.items(), key=lambda x: x[1], reverse=True)[:10])
            
            logger.info(f"Generated {len(predictions)} trend predictions")
            return predictions
            
        except Exception as e:
            logger.error(f"Trend prediction failed: {e}")
            return {}
    
    def _extract_keywords_from_text(self, text: str, max_keywords: int = 20) -> List[str]:
        """Extract relevant keywords from text"""
        if not text:
            return []
        
        # Basic preprocessing
        text = re.sub(r'[^\w\s]', ' ', text.lower())
        words = text.split()
        
        # Filter words
        keywords = []
        for word in words:
            if (len(word) >= 3 and 
                word not in self.stop_words and 
                not word.isdigit() and
                word.isalpha()):
                keywords.append(word)
        
        # Count and return most common
        keyword_counts = Counter(keywords)
        return [kw for kw, count in keyword_counts.most_common(max_keywords)]
    
    def _calculate_velocity(self, timestamps: List[datetime]) -> float:
        """Calculate velocity (rate of change) for timestamps"""
        if not timestamps or len(timestamps) < 2:
            return 0.0
        
        try:
            sorted_times = sorted(timestamps)
            time_diffs = [(sorted_times[i] - sorted_times[i-1]).total_seconds() 
                         for i in range(1, len(sorted_times))]
            
            if not time_diffs:
                return 0.0
            
            # Average time between articles (lower is higher velocity)
            avg_time_diff = sum(time_diffs) / len(time_diffs)
            
            # Convert to velocity score (higher is better)
            velocity = 3600 / max(avg_time_diff, 300)  # Max 1 per 5 minutes
            return min(velocity, 10.0)  # Cap at 10
            
        except Exception:
            return 0.0
    
    def _calculate_trend_score(self, count: int, engagement: int, sources: int, velocity: float) -> float:
        """Calculate overall trend score"""
        # Weighted combination of factors
        count_score = min(count / 10.0, 1.0)  # Normalize to 0-1
        engagement_score = min(engagement / 100.0, 1.0)  # Normalize to 0-1
        source_score = min(sources / 5.0, 1.0)  # Normalize to 0-1
        velocity_score = min(velocity / 5.0, 1.0)  # Normalize to 0-1
        
        # Weighted average
        trend_score = (count_score * 0.3 + 
                      engagement_score * 0.3 + 
                      source_score * 0.2 + 
                      velocity_score * 0.2)
        
        return trend_score
    
    def _determine_trend_direction(self, timestamps: List[datetime]) -> str:
        """Determine if trend is rising, stable, or declining"""
        if not timestamps or len(timestamps) < 3:
            return 'stable'
        
        try:
            sorted_times = sorted(timestamps)
            
            # Split into two halves and compare
            mid_point = len(sorted_times) // 2
            first_half = sorted_times[:mid_point]
            second_half = sorted_times[mid_point:]
            
            # Calculate rate in each half
            first_duration = (first_half[-1] - first_half[0]).total_seconds()
            second_duration = (second_half[-1] - second_half[0]).total_seconds()
            
            if first_duration == 0 or second_duration == 0:
                return 'stable'
            
            first_rate = len(first_half) / first_duration
            second_rate = len(second_half) / second_duration
            
            if second_rate > first_rate * 1.5:
                return 'rising'
            elif second_rate < first_rate * 0.5:
                return 'declining'
            else:
                return 'stable'
                
        except Exception:
            return 'stable'
    
    async def save_trending_analysis(self, analysis_result: TrendAnalysisResult) -> bool:
        """Save trending analysis results to database"""
        try:
            # Save trending topics
            for trending_item in analysis_result.trending_topics:
                existing = self.db.query(TrendingTopic).filter(
                    TrendingTopic.topic_name == trending_item.title
                ).first()
                
                if existing:
                    # Update existing
                    existing.trend_score = trending_item.trend_score
                    existing.article_count = trending_item.article_count
                    existing.engagement_score = trending_item.engagement_score
                    existing.updated_at = datetime.now()
                else:
                    # Create new
                    trending_topic = TrendingTopic(
                        topic_name=trending_item.title,
                        topic_type=trending_item.item_type,
                        trend_score=trending_item.trend_score,
                        velocity=trending_item.velocity,
                        article_count=trending_item.article_count,
                        unique_sources=trending_item.unique_sources,
                        engagement_score=trending_item.engagement_score,
                        keywords=trending_item.keywords,
                        related_article_ids=trending_item.related_articles,
                        trend_direction=trending_item.trend_direction,
                        confidence=trending_item.confidence,
                        first_detected_at=trending_item.first_seen,
                        peak_time=trending_item.peak_time
                    )
                    self.db.add(trending_topic)
            
            # Save topic analysis
            topic_analysis = TopicAnalysis(
                analysis_type='comprehensive',
                time_window_hours=self.trending_window_hours,
                topics_found=len(analysis_result.trending_topics),
                clusters_found=len(analysis_result.topic_clusters),
                viral_articles=len(analysis_result.viral_articles),
                analysis_metadata=analysis_result.analysis_metadata,
                created_at=datetime.now()
            )
            self.db.add(topic_analysis)
            
            self.db.commit()
            logger.info("Trending analysis results saved to database")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save trending analysis: {e}")
            self.db.rollback()
            return False

# Global service instance
trending_analysis_service = None

def get_trending_analysis_service(db: Session) -> TrendingAnalysisService:
    """Get or create trending analysis service"""
    global trending_analysis_service
    if not trending_analysis_service:
        trending_analysis_service = TrendingAnalysisService(db)
    return trending_analysis_service