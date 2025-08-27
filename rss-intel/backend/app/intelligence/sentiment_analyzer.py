#!/usr/bin/env python3
"""
Advanced Sentiment Analysis Pipeline for RSS Intelligence
Multi-layered sentiment analysis with context awareness and emotion detection
"""

import asyncio
import logging
import numpy as np
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import json
from collections import defaultdict, Counter

from textblob import TextBlob
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from ..config import settings
from ..store import Article
from ..deps import SessionLocal

logger = logging.getLogger(__name__)


@dataclass
class SentimentScore:
    """Comprehensive sentiment analysis result"""
    polarity: float  # -1 (negative) to +1 (positive)
    subjectivity: float  # 0 (objective) to 1 (subjective)
    compound: float  # VADER compound score
    confidence: float  # Overall confidence in sentiment analysis
    emotions: Dict[str, float]  # Emotion scores
    context: str  # Context category (financial, political, etc.)
    intensity: str  # low, medium, high
    key_phrases: List[str]  # Phrases that influenced sentiment


@dataclass
class SentimentAnalysisResult:
    """Result of sentiment analysis for an article"""
    article_id: int
    title_sentiment: SentimentScore
    content_sentiment: SentimentScore
    overall_sentiment: SentimentScore
    sentiment_trend: Optional[str]  # improving, declining, stable
    analysis_timestamp: datetime
    processing_time_ms: float


class AdvancedSentimentAnalyzer:
    """Multi-layered sentiment analysis with contextual understanding"""
    
    def __init__(self):
        # Initialize sentiment analyzers
        self.vader_analyzer = SentimentIntensityAnalyzer()
        
        # Emotion lexicons
        self.emotion_lexicon = {
            'joy': ['happy', 'excited', 'thrilled', 'delighted', 'pleased', 'optimistic', 'cheerful', 'elated'],
            'anger': ['angry', 'furious', 'outraged', 'irritated', 'annoyed', 'hostile', 'rage', 'mad'],
            'fear': ['afraid', 'scared', 'terrified', 'worried', 'anxious', 'concerned', 'panic', 'nervous'],
            'sadness': ['sad', 'depressed', 'disappointed', 'upset', 'gloomy', 'melancholy', 'grief', 'sorrow'],
            'surprise': ['surprised', 'shocked', 'amazed', 'astonished', 'stunned', 'bewildered'],
            'trust': ['trust', 'confidence', 'reliable', 'dependable', 'faith', 'belief'],
            'disgust': ['disgusted', 'revolted', 'repulsed', 'appalled', 'sickened'],
            'anticipation': ['expecting', 'hopeful', 'eager', 'anticipating', 'excited', 'looking forward']
        }
        
        # Context-specific sentiment modifiers
        self.context_modifiers = {
            'financial': {
                'positive': ['profit', 'growth', 'bull', 'gain', 'surge', 'rally', 'breakthrough', 'success'],
                'negative': ['loss', 'crash', 'bear', 'decline', 'drop', 'recession', 'failure', 'crisis'],
                'neutral': ['trading', 'market', 'analysis', 'report', 'data', 'forecast']
            },
            'technology': {
                'positive': ['innovation', 'breakthrough', 'advancement', 'upgrade', 'revolutionary', 'cutting-edge'],
                'negative': ['bug', 'crash', 'vulnerability', 'hack', 'failure', 'obsolete', 'deprecated'],
                'neutral': ['update', 'release', 'version', 'feature', 'algorithm', 'development']
            },
            'political': {
                'positive': ['unity', 'cooperation', 'agreement', 'progress', 'victory', 'success', 'reform'],
                'negative': ['conflict', 'crisis', 'scandal', 'controversy', 'opposition', 'protest', 'failure'],
                'neutral': ['policy', 'legislation', 'government', 'official', 'statement', 'meeting']
            },
            'health': {
                'positive': ['recovery', 'cure', 'breakthrough', 'improvement', 'healing', 'prevention', 'wellness'],
                'negative': ['disease', 'outbreak', 'pandemic', 'illness', 'death', 'emergency', 'crisis'],
                'neutral': ['treatment', 'study', 'research', 'medical', 'health', 'clinical']
            }
        }
        
        # Intensity indicators
        self.intensity_amplifiers = ['very', 'extremely', 'incredibly', 'tremendously', 'absolutely', 'completely']
        self.intensity_diminishers = ['somewhat', 'rather', 'fairly', 'slightly', 'moderately', 'quite']
        
        # Performance tracking
        self.analysis_stats = {
            'total_analyzed': 0,
            'avg_processing_time': 0.0,
            'sentiment_distribution': defaultdict(int),
            'context_distribution': defaultdict(int)
        }
    
    async def analyze_sentiment(self, article: Article) -> SentimentAnalysisResult:
        """Perform comprehensive sentiment analysis on an article"""
        start_time = datetime.utcnow()
        
        title_text = article.title or ""
        content_text = article.content or ""
        
        # Analyze title and content separately
        title_sentiment = await self._analyze_text_sentiment(title_text, is_title=True)
        content_sentiment = await self._analyze_text_sentiment(content_text, is_title=False)
        
        # Combine for overall sentiment
        overall_sentiment = self._combine_sentiment_scores(title_sentiment, content_sentiment)
        
        # Detect sentiment trend (requires historical data)
        sentiment_trend = await self._detect_sentiment_trend(article, overall_sentiment)
        
        # Calculate processing time
        processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        # Update stats
        self._update_stats(overall_sentiment, processing_time)
        
        return SentimentAnalysisResult(
            article_id=article.id,
            title_sentiment=title_sentiment,
            content_sentiment=content_sentiment,
            overall_sentiment=overall_sentiment,
            sentiment_trend=sentiment_trend,
            analysis_timestamp=datetime.utcnow(),
            processing_time_ms=processing_time
        )
    
    async def _analyze_text_sentiment(self, text: str, is_title: bool = False) -> SentimentScore:
        """Analyze sentiment of a text using multiple approaches"""
        if not text.strip():
            return SentimentScore(
                polarity=0.0, subjectivity=0.5, compound=0.0, confidence=0.0,
                emotions={}, context="unknown", intensity="low", key_phrases=[]
            )
        
        # TextBlob analysis
        blob = TextBlob(text)
        tb_polarity = blob.sentiment.polarity
        tb_subjectivity = blob.sentiment.subjectivity
        
        # VADER analysis
        vader_scores = self.vader_analyzer.polarity_scores(text)
        vader_compound = vader_scores['compound']
        
        # Emotion analysis
        emotions = self._analyze_emotions(text)
        
        # Context detection
        context = self._detect_context(text)
        
        # Key phrase extraction
        key_phrases = self._extract_sentiment_phrases(text)
        
        # Intensity analysis
        intensity = self._analyze_intensity(text)
        
        # Context-aware sentiment adjustment
        adjusted_polarity, confidence = self._adjust_sentiment_for_context(
            tb_polarity, vader_compound, context, text
        )
        
        # Combine scores with weighting
        if is_title:
            # Titles often have stronger sentiment indicators
            final_polarity = adjusted_polarity * 1.2
            final_compound = vader_compound * 1.1
        else:
            final_polarity = adjusted_polarity
            final_compound = vader_compound
        
        # Ensure bounds
        final_polarity = max(-1.0, min(1.0, final_polarity))
        final_compound = max(-1.0, min(1.0, final_compound))
        
        return SentimentScore(
            polarity=final_polarity,
            subjectivity=tb_subjectivity,
            compound=final_compound,
            confidence=confidence,
            emotions=emotions,
            context=context,
            intensity=intensity,
            key_phrases=key_phrases
        )
    
    def _analyze_emotions(self, text: str) -> Dict[str, float]:
        """Analyze emotional content of text"""
        text_lower = text.lower()
        emotions = {}
        
        for emotion, words in self.emotion_lexicon.items():
            score = 0.0
            for word in words:
                # Count occurrences with context
                pattern = r'\b' + re.escape(word) + r'\b'
                matches = len(re.findall(pattern, text_lower))
                score += matches
            
            # Normalize by text length
            text_length = len(text_lower.split())
            normalized_score = score / max(text_length / 100, 1.0)
            emotions[emotion] = min(normalized_score, 1.0)
        
        return emotions
    
    def _detect_context(self, text: str) -> str:
        """Detect the contextual domain of the text"""
        text_lower = text.lower()
        context_scores = {}
        
        for context, modifiers in self.context_modifiers.items():
            score = 0
            for category, words in modifiers.items():
                for word in words:
                    if word in text_lower:
                        score += 1
            
            if score > 0:
                context_scores[context] = score
        
        # Return the context with highest score
        if context_scores:
            return max(context_scores, key=context_scores.get)
        else:
            return "general"
    
    def _extract_sentiment_phrases(self, text: str, max_phrases: int = 5) -> List[str]:
        """Extract key phrases that influence sentiment"""
        # Simple approach: look for adjective-noun or adverb-adjective patterns
        # This could be enhanced with more sophisticated NLP
        
        sentences = text.split('.')
        sentiment_phrases = []
        
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 10:  # Skip very short sentences
                continue
                
            # Look for strong sentiment indicators
            strong_indicators = [
                'very good', 'extremely bad', 'absolutely terrible', 'incredibly successful',
                'major breakthrough', 'significant decline', 'outstanding performance',
                'devastating impact', 'remarkable achievement', 'serious concerns'
            ]
            
            for indicator in strong_indicators:
                if indicator in sentence.lower():
                    sentiment_phrases.append(sentence)
                    break
        
        return sentiment_phrases[:max_phrases]
    
    def _analyze_intensity(self, text: str) -> str:
        """Analyze the intensity of sentiment expression"""
        text_lower = text.lower()
        
        amplifier_count = sum(1 for amp in self.intensity_amplifiers if amp in text_lower)
        diminisher_count = sum(1 for dim in self.intensity_diminishers if dim in text_lower)
        
        # Look for exclamation marks and caps
        exclamation_count = text.count('!')
        caps_words = len(re.findall(r'\b[A-Z]{2,}\b', text))
        
        # Calculate intensity score
        intensity_score = amplifier_count + exclamation_count * 0.5 + caps_words * 0.3 - diminisher_count * 0.5
        
        if intensity_score > 2:
            return "high"
        elif intensity_score > 0.5:
            return "medium"
        else:
            return "low"
    
    def _adjust_sentiment_for_context(self, tb_polarity: float, vader_compound: float, 
                                    context: str, text: str) -> Tuple[float, float]:
        """Adjust sentiment score based on contextual understanding"""
        
        # Base sentiment (weighted combination)
        base_sentiment = (tb_polarity * 0.6 + vader_compound * 0.4)
        
        # Context-specific adjustments
        if context in self.context_modifiers:
            modifiers = self.context_modifiers[context]
            text_lower = text.lower()
            
            positive_count = sum(1 for word in modifiers['positive'] if word in text_lower)
            negative_count = sum(1 for word in modifiers['negative'] if word in text_lower)
            neutral_count = sum(1 for word in modifiers['neutral'] if word in text_lower)
            
            total_context_words = positive_count + negative_count + neutral_count
            
            if total_context_words > 0:
                # Adjust based on context-specific sentiment
                context_sentiment = (positive_count - negative_count) / total_context_words
                adjusted_sentiment = base_sentiment * 0.7 + context_sentiment * 0.3
                confidence = min(0.9, 0.5 + total_context_words * 0.1)
            else:
                adjusted_sentiment = base_sentiment
                confidence = 0.5
        else:
            adjusted_sentiment = base_sentiment
            confidence = 0.6
        
        # Check for negation patterns
        negation_patterns = [
            r"not\s+\w+", r"never\s+\w+", r"no\s+\w+", r"don't\s+\w+", r"doesn't\s+\w+",
            r"won't\s+\w+", r"can't\s+\w+", r"shouldn't\s+\w+"
        ]
        
        for pattern in negation_patterns:
            if re.search(pattern, text.lower()):
                adjusted_sentiment *= 0.8  # Reduce sentiment intensity
                break
        
        return adjusted_sentiment, confidence
    
    def _combine_sentiment_scores(self, title_sentiment: SentimentScore, 
                                 content_sentiment: SentimentScore) -> SentimentScore:
        """Combine title and content sentiment for overall score"""
        
        # Weight title more heavily as it's usually more indicative
        title_weight = 0.6
        content_weight = 0.4
        
        combined_polarity = (title_sentiment.polarity * title_weight + 
                           content_sentiment.polarity * content_weight)
        
        combined_subjectivity = (title_sentiment.subjectivity * title_weight + 
                               content_sentiment.subjectivity * content_weight)
        
        combined_compound = (title_sentiment.compound * title_weight + 
                           content_sentiment.compound * content_weight)
        
        # Average confidence
        combined_confidence = (title_sentiment.confidence + content_sentiment.confidence) / 2
        
        # Combine emotions (take maximum)
        combined_emotions = {}
        all_emotions = set(title_sentiment.emotions.keys()) | set(content_sentiment.emotions.keys())
        for emotion in all_emotions:
            title_score = title_sentiment.emotions.get(emotion, 0)
            content_score = content_sentiment.emotions.get(emotion, 0)
            combined_emotions[emotion] = max(title_score, content_score)
        
        # Use content context if title context is general
        context = content_sentiment.context if title_sentiment.context == "general" else title_sentiment.context
        
        # Use higher intensity
        intensity_levels = {"low": 0, "medium": 1, "high": 2}
        title_intensity_level = intensity_levels.get(title_sentiment.intensity, 0)
        content_intensity_level = intensity_levels.get(content_sentiment.intensity, 0)
        
        if title_intensity_level >= content_intensity_level:
            intensity = title_sentiment.intensity
        else:
            intensity = content_sentiment.intensity
        
        # Combine key phrases
        combined_phrases = title_sentiment.key_phrases + content_sentiment.key_phrases
        unique_phrases = list(dict.fromkeys(combined_phrases))  # Remove duplicates while preserving order
        
        return SentimentScore(
            polarity=combined_polarity,
            subjectivity=combined_subjectivity,
            compound=combined_compound,
            confidence=combined_confidence,
            emotions=combined_emotions,
            context=context,
            intensity=intensity,
            key_phrases=unique_phrases[:10]  # Limit to 10 phrases
        )
    
    async def _detect_sentiment_trend(self, article: Article, current_sentiment: SentimentScore) -> Optional[str]:
        """Detect sentiment trend by comparing with historical data"""
        # This would require storing historical sentiment data
        # For now, return None - can be implemented with database storage
        return None
    
    def _update_stats(self, sentiment: SentimentScore, processing_time: float):
        """Update analysis statistics"""
        self.analysis_stats['total_analyzed'] += 1
        
        # Update average processing time
        total_time = (self.analysis_stats['avg_processing_time'] * 
                     (self.analysis_stats['total_analyzed'] - 1) + processing_time)
        self.analysis_stats['avg_processing_time'] = total_time / self.analysis_stats['total_analyzed']
        
        # Update sentiment distribution
        if sentiment.polarity > 0.1:
            self.analysis_stats['sentiment_distribution']['positive'] += 1
        elif sentiment.polarity < -0.1:
            self.analysis_stats['sentiment_distribution']['negative'] += 1
        else:
            self.analysis_stats['sentiment_distribution']['neutral'] += 1
        
        # Update context distribution
        self.analysis_stats['context_distribution'][sentiment.context] += 1
    
    def get_sentiment_label(self, sentiment_score: SentimentScore) -> str:
        """Get human-readable sentiment label"""
        polarity = sentiment_score.polarity
        intensity = sentiment_score.intensity
        
        if polarity > 0.6:
            return f"very positive ({intensity} intensity)"
        elif polarity > 0.1:
            return f"positive ({intensity} intensity)"
        elif polarity > -0.1:
            return f"neutral ({intensity} intensity)"
        elif polarity > -0.6:
            return f"negative ({intensity} intensity)"
        else:
            return f"very negative ({intensity} intensity)"
    
    def get_dominant_emotion(self, sentiment_score: SentimentScore) -> Tuple[str, float]:
        """Get the dominant emotion from sentiment analysis"""
        if not sentiment_score.emotions:
            return "none", 0.0
        
        dominant_emotion = max(sentiment_score.emotions.items(), key=lambda x: x[1])
        return dominant_emotion
    
    async def analyze_sentiment_trends(self, hours_back: int = 24) -> Dict[str, Any]:
        """Analyze sentiment trends across recent articles"""
        db = SessionLocal()
        try:
            since = datetime.utcnow() - timedelta(hours=hours_back)
            articles = db.query(Article).filter(
                Article.published_at >= since
            ).order_by(Article.published_at.desc()).limit(200).all()
            
            if not articles:
                return {}
            
            # Analyze all articles
            sentiment_data = []
            context_sentiments = defaultdict(list)
            
            for article in articles:
                try:
                    result = await self.analyze_sentiment(article)
                    sentiment_data.append({
                        'timestamp': article.published_at,
                        'polarity': result.overall_sentiment.polarity,
                        'context': result.overall_sentiment.context,
                        'intensity': result.overall_sentiment.intensity
                    })
                    context_sentiments[result.overall_sentiment.context].append(result.overall_sentiment.polarity)
                except Exception as e:
                    logger.error(f"Error analyzing sentiment for article {article.id}: {e}")
            
            # Calculate trends
            trends = {
                'total_articles': len(sentiment_data),
                'avg_sentiment': np.mean([item['polarity'] for item in sentiment_data]),
                'sentiment_distribution': {
                    'positive': len([item for item in sentiment_data if item['polarity'] > 0.1]),
                    'neutral': len([item for item in sentiment_data if -0.1 <= item['polarity'] <= 0.1]),
                    'negative': len([item for item in sentiment_data if item['polarity'] < -0.1])
                },
                'context_sentiment': {
                    context: {
                        'avg_sentiment': np.mean(sentiments),
                        'count': len(sentiments)
                    }
                    for context, sentiments in context_sentiments.items()
                },
                'intensity_distribution': Counter([item['intensity'] for item in sentiment_data]),
                'time_period_hours': hours_back
            }
            
            return trends
            
        except Exception as e:
            logger.error(f"Error analyzing sentiment trends: {e}")
            return {}
        finally:
            db.close()
    
    def get_analysis_stats(self) -> Dict[str, Any]:
        """Get sentiment analysis performance statistics"""
        return {
            'total_analyzed': self.analysis_stats['total_analyzed'],
            'avg_processing_time_ms': round(self.analysis_stats['avg_processing_time'], 2),
            'sentiment_distribution': dict(self.analysis_stats['sentiment_distribution']),
            'context_distribution': dict(self.analysis_stats['context_distribution']),
            'supported_emotions': list(self.emotion_lexicon.keys()),
            'supported_contexts': list(self.context_modifiers.keys())
        }


# Global sentiment analyzer instance
sentiment_analyzer = AdvancedSentimentAnalyzer()


# Batch processing functions
async def analyze_sentiment_batch(articles: List[Article]) -> List[SentimentAnalysisResult]:
    """Analyze sentiment for multiple articles in batch"""
    logger.info(f"Analyzing sentiment for {len(articles)} articles in batch...")
    
    results = []
    for article in articles:
        try:
            result = await sentiment_analyzer.analyze_sentiment(article)
            results.append(result)
        except Exception as e:
            logger.error(f"Error analyzing sentiment for article {article.id}: {e}")
    
    logger.info(f"Batch sentiment analysis completed: {len(results)} results")
    return results


async def auto_analyze_sentiment_new_articles():
    """Background task to analyze sentiment for new articles"""
    db = SessionLocal()
    try:
        # Find recent articles without sentiment analysis
        recent_articles = db.query(Article).filter(
            Article.published_at >= datetime.utcnow() - timedelta(hours=6)
        ).limit(50).all()
        
        analyzed_count = 0
        for article in recent_articles:
            try:
                result = await sentiment_analyzer.analyze_sentiment(article)
                # TODO: Store sentiment results in database
                analyzed_count += 1
            except Exception as e:
                logger.error(f"Auto-sentiment analysis error for article {article.id}: {e}")
        
        logger.info(f"Auto-analyzed sentiment for {analyzed_count} articles")
        
    except Exception as e:
        logger.error(f"Auto-sentiment analysis batch error: {e}")
    finally:
        db.close()