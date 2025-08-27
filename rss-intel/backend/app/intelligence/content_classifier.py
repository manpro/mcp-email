#!/usr/bin/env python3
"""
Smart Content Categorization System for RSS Intelligence
Uses ML models and semantic analysis for automatic content classification
"""

import asyncio
import logging
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import json
import re
from collections import defaultdict, Counter

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.linear_model import LogisticRegression
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import LabelEncoder
import joblib

from ..config import settings
from ..store import Article
from ..deps import SessionLocal
from ..ml.embedding import batch_embed_articles

logger = logging.getLogger(__name__)


@dataclass
class ContentCategory:
    """Represents a content category with confidence"""
    name: str
    confidence: float
    subcategories: List[str] = None
    keywords: List[str] = None
    description: str = ""


@dataclass
class ClassificationResult:
    """Result of content classification"""
    article_id: int
    primary_category: ContentCategory
    secondary_categories: List[ContentCategory]
    tags: List[str]
    classification_timestamp: datetime
    processing_time_ms: float


class SmartContentClassifier:
    """Advanced content classification using multiple ML approaches"""
    
    def __init__(self):
        self.categories_config = {
            'Technology': {
                'keywords': ['ai', 'artificial intelligence', 'machine learning', 'blockchain', 'cryptocurrency', 
                           'software', 'hardware', 'programming', 'developer', 'tech', 'digital', 'cloud',
                           'cybersecurity', 'data science', 'automation', 'robotics', 'iot'],
                'subcategories': ['AI/ML', 'Blockchain', 'Software Development', 'Cybersecurity', 'Cloud Computing'],
                'patterns': [r'\b(AI|ML|API|SDK|SaaS|IoT|5G|VR|AR)\b', r'crypto\w*', r'tech\w*']
            },
            'Finance': {
                'keywords': ['finance', 'investment', 'trading', 'market', 'stock', 'crypto', 'bitcoin',
                           'ethereum', 'defi', 'bank', 'monetary', 'economic', 'financial', 'currency',
                           'portfolio', 'hedge fund', 'venture capital', 'ipo'],
                'subcategories': ['Cryptocurrency', 'Traditional Markets', 'DeFi', 'Banking', 'Investment'],
                'patterns': [r'\$[0-9,]+', r'\b(USD|EUR|BTC|ETH|DeFi)\b', r'financial\w*']
            },
            'Business': {
                'keywords': ['business', 'startup', 'company', 'corporate', 'enterprise', 'entrepreneur',
                           'market', 'industry', 'commerce', 'strategy', 'management', 'leadership',
                           'merger', 'acquisition', 'revenue', 'profit', 'growth'],
                'subcategories': ['Startups', 'Corporate News', 'M&A', 'Strategy', 'Leadership'],
                'patterns': [r'\b(CEO|CTO|CFO|IPO|M&A)\b', r'company\w*', r'business\w*']
            },
            'Science': {
                'keywords': ['science', 'research', 'study', 'discovery', 'breakthrough', 'experiment',
                           'scientific', 'technology', 'innovation', 'development', 'analysis',
                           'data', 'evidence', 'methodology', 'peer review'],
                'subcategories': ['Research', 'Medical', 'Environmental', 'Space', 'Physics'],
                'patterns': [r'\bresearch\w*', r'\bstudy\b', r'scientific\w*']
            },
            'Politics': {
                'keywords': ['politics', 'government', 'policy', 'election', 'politician', 'congress',
                           'parliament', 'legislation', 'regulation', 'political', 'democracy',
                           'republican', 'democrat', 'liberal', 'conservative'],
                'subcategories': ['Domestic Policy', 'International Relations', 'Elections', 'Regulation'],
                'patterns': [r'\b(govt|gov|political)\b', r'policy\w*', r'election\w*']
            },
            'Health': {
                'keywords': ['health', 'medical', 'healthcare', 'medicine', 'doctor', 'patient',
                           'disease', 'treatment', 'therapy', 'pharmaceutical', 'clinical',
                           'hospital', 'wellness', 'fitness', 'mental health'],
                'subcategories': ['Medical Research', 'Healthcare Policy', 'Wellness', 'Mental Health'],
                'patterns': [r'\bhealth\w*', r'medical\w*', r'\b(FDA|WHO|CDC)\b']
            },
            'Environment': {
                'keywords': ['environment', 'climate', 'sustainability', 'renewable', 'green',
                           'carbon', 'emission', 'pollution', 'conservation', 'ecosystem',
                           'biodiversity', 'global warming', 'clean energy'],
                'subcategories': ['Climate Change', 'Renewable Energy', 'Conservation', 'Pollution'],
                'patterns': [r'climate\w*', r'environment\w*', r'renewable\w*']
            },
            'Sports': {
                'keywords': ['sports', 'game', 'player', 'team', 'league', 'championship',
                           'football', 'basketball', 'baseball', 'soccer', 'olympics',
                           'athletic', 'competition', 'tournament'],
                'subcategories': ['Professional Sports', 'Olympics', 'College Sports', 'Esports'],
                'patterns': [r'\bsports?\b', r'game\w*', r'championship\w*']
            },
            'Entertainment': {
                'keywords': ['entertainment', 'movie', 'film', 'music', 'celebrity', 'hollywood',
                           'streaming', 'netflix', 'gaming', 'video game', 'culture',
                           'art', 'media', 'television', 'show'],
                'subcategories': ['Movies', 'Music', 'Gaming', 'Television', 'Celebrity'],
                'patterns': [r'entertainment\w*', r'movie\w*', r'gaming\w*']
            },
            'Education': {
                'keywords': ['education', 'school', 'university', 'student', 'teacher', 'learning',
                           'academic', 'curriculum', 'degree', 'scholarship', 'tuition',
                           'online learning', 'e-learning', 'educational'],
                'subcategories': ['Higher Education', 'K-12', 'Online Learning', 'Educational Technology'],
                'patterns': [r'education\w*', r'school\w*', r'university\w*']
            }
        }
        
        # ML models
        self.tfidf_vectorizer = None
        self.nb_classifier = None
        self.lr_classifier = None
        self.label_encoder = None
        self.is_trained = False
        
        # Performance tracking
        self.classification_stats = {
            'total_classified': 0,
            'avg_confidence': 0.0,
            'category_distribution': defaultdict(int),
            'processing_times': []
        }
    
    async def classify_content(self, article: Article) -> ClassificationResult:
        """Classify a single article"""
        start_time = datetime.utcnow()
        
        # Extract text features
        text_content = f"{article.title} {article.content or ''}"
        
        # Multi-approach classification
        rule_based_result = await self._rule_based_classification(text_content, article)
        
        if self.is_trained:
            ml_result = await self._ml_classification(text_content)
            # Combine results
            primary_category = self._combine_classification_results(rule_based_result, ml_result)
        else:
            primary_category = rule_based_result[0] if rule_based_result else ContentCategory("General", 0.5)
        
        # Generate additional tags
        tags = await self._generate_content_tags(text_content, article)
        
        # Calculate processing time
        processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        # Update stats
        self.classification_stats['total_classified'] += 1
        self.classification_stats['category_distribution'][primary_category.name] += 1
        self.classification_stats['processing_times'].append(processing_time)
        
        return ClassificationResult(
            article_id=article.id,
            primary_category=primary_category,
            secondary_categories=rule_based_result[1:3] if len(rule_based_result) > 1 else [],
            tags=tags,
            classification_timestamp=datetime.utcnow(),
            processing_time_ms=processing_time
        )
    
    async def _rule_based_classification(self, text: str, article: Article) -> List[ContentCategory]:
        """Rule-based classification using keywords and patterns"""
        text_lower = text.lower()
        category_scores = {}
        
        for category_name, config in self.categories_config.items():
            score = 0.0
            matched_keywords = []
            
            # Keyword matching
            for keyword in config['keywords']:
                if keyword.lower() in text_lower:
                    # Weight by keyword importance and frequency
                    count = text_lower.count(keyword.lower())
                    keyword_weight = 1.0 + (len(keyword.split()) - 1) * 0.5  # Multi-word bonus
                    score += count * keyword_weight
                    matched_keywords.append(keyword)
            
            # Pattern matching
            for pattern in config.get('patterns', []):
                matches = re.findall(pattern, text, re.IGNORECASE)
                score += len(matches) * 2.0  # Patterns get higher weight
            
            # Source-based hints
            if hasattr(article, 'source') and article.source:
                source_hints = self._get_source_category_hints(article.source)
                if category_name in source_hints:
                    score *= source_hints[category_name]
            
            # Score normalization
            text_length = len(text.split())
            normalized_score = score / max(text_length / 100, 1.0)  # Normalize by text length
            
            if normalized_score > 0:
                category_scores[category_name] = {
                    'score': normalized_score,
                    'keywords': matched_keywords
                }
        
        # Sort by score and create ContentCategory objects
        sorted_categories = sorted(category_scores.items(), key=lambda x: x[1]['score'], reverse=True)
        
        results = []
        for category_name, data in sorted_categories[:5]:  # Top 5
            confidence = min(data['score'] / 10.0, 1.0)  # Normalize confidence to 0-1
            
            category = ContentCategory(
                name=category_name,
                confidence=confidence,
                subcategories=self.categories_config[category_name]['subcategories'],
                keywords=data['keywords'][:5],  # Top 5 matched keywords
                description=f"Matched {len(data['keywords'])} keywords with confidence {confidence:.2f}"
            )
            results.append(category)
        
        return results
    
    async def _ml_classification(self, text: str) -> ContentCategory:
        """Machine learning based classification"""
        if not self.is_trained:
            return ContentCategory("General", 0.5)
        
        try:
            # Vectorize text
            text_vector = self.tfidf_vectorizer.transform([text])
            
            # Get predictions from both models
            nb_proba = self.nb_classifier.predict_proba(text_vector)[0]
            lr_proba = self.lr_classifier.predict_proba(text_vector)[0]
            
            # Ensemble prediction (average)
            ensemble_proba = (nb_proba + lr_proba) / 2
            
            # Get best prediction
            best_idx = np.argmax(ensemble_proba)
            best_category = self.label_encoder.inverse_transform([best_idx])[0]
            confidence = ensemble_proba[best_idx]
            
            return ContentCategory(
                name=best_category,
                confidence=float(confidence),
                description=f"ML classification with {confidence:.2f} confidence"
            )
            
        except Exception as e:
            logger.warning(f"ML classification failed: {e}")
            return ContentCategory("General", 0.5)
    
    def _combine_classification_results(self, rule_based: List[ContentCategory], ml_result: ContentCategory) -> ContentCategory:
        """Combine rule-based and ML classification results"""
        if not rule_based:
            return ml_result
        
        # Weight rule-based vs ML
        rule_weight = 0.7
        ml_weight = 0.3
        
        rule_top = rule_based[0]
        
        # If ML and rule-based agree, boost confidence
        if ml_result.name == rule_top.name:
            combined_confidence = min(rule_top.confidence * rule_weight + ml_result.confidence * ml_weight, 1.0)
            return ContentCategory(
                name=rule_top.name,
                confidence=combined_confidence,
                subcategories=rule_top.subcategories,
                keywords=rule_top.keywords,
                description=f"Rule-based + ML agreement with {combined_confidence:.2f} confidence"
            )
        
        # If they disagree, compare confidences
        if rule_top.confidence > ml_result.confidence:
            return rule_top
        else:
            return ml_result
    
    async def _generate_content_tags(self, text: str, article: Article) -> List[str]:
        """Generate additional content tags"""
        tags = []
        text_lower = text.lower()
        
        # Temporal tags
        if hasattr(article, 'published_at') and article.published_at:
            age_hours = (datetime.utcnow() - article.published_at).total_seconds() / 3600
            if age_hours < 1:
                tags.append("breaking")
            elif age_hours < 6:
                tags.append("recent")
        
        # Content characteristics
        if len(text) > 2000:
            tags.append("long-form")
        elif len(text) < 200:
            tags.append("brief")
        
        # Sentiment hints
        positive_words = ['breakthrough', 'success', 'growth', 'innovation', 'achievement', 'positive']
        negative_words = ['crisis', 'problem', 'decline', 'failure', 'negative', 'concern']
        
        pos_count = sum(1 for word in positive_words if word in text_lower)
        neg_count = sum(1 for word in negative_words if word in text_lower)
        
        if pos_count > neg_count and pos_count > 2:
            tags.append("positive")
        elif neg_count > pos_count and neg_count > 2:
            tags.append("negative")
        
        # Technical complexity
        technical_terms = ['algorithm', 'methodology', 'analysis', 'implementation', 'architecture']
        if sum(1 for term in technical_terms if term in text_lower) > 2:
            tags.append("technical")
        
        # Geographic hints
        regions = ['europe', 'asia', 'america', 'africa', 'global', 'international']
        for region in regions:
            if region in text_lower:
                tags.append(f"geo-{region}")
                break
        
        return tags[:10]  # Limit to 10 tags
    
    def _get_source_category_hints(self, source: str) -> Dict[str, float]:
        """Get category hints based on source domain"""
        source_hints = {
            'techcrunch': {'Technology': 1.5, 'Business': 1.2},
            'coindesk': {'Finance': 2.0, 'Technology': 1.3},
            'bloomberg': {'Finance': 1.8, 'Business': 1.5},
            'reuters': {'Politics': 1.3, 'Business': 1.2},
            'nature': {'Science': 2.0, 'Health': 1.3},
            'cnn': {'Politics': 1.3, 'General': 1.1},
            'bbc': {'Politics': 1.2, 'General': 1.1},
            'espn': {'Sports': 2.0},
            'variety': {'Entertainment': 2.0},
            'wired': {'Technology': 1.8, 'Science': 1.2}
        }
        
        source_lower = source.lower()
        for domain, hints in source_hints.items():
            if domain in source_lower:
                return hints
        
        return {}
    
    async def train_classifier(self, articles: List[Article], force_retrain: bool = False):
        """Train the ML classifier on labeled articles"""
        if self.is_trained and not force_retrain:
            logger.info("Classifier already trained. Use force_retrain=True to retrain.")
            return
        
        logger.info(f"Training content classifier on {len(articles)} articles...")
        
        # Prepare training data
        texts = []
        labels = []
        
        for article in articles:
            text = f"{article.title} {article.content or ''}"
            
            # Get rule-based classification as training label
            rule_result = await self._rule_based_classification(text, article)
            if rule_result and rule_result[0].confidence > 0.3:
                texts.append(text)
                labels.append(rule_result[0].name)
        
        if len(set(labels)) < 3:  # Need at least 3 categories
            logger.warning("Insufficient labeled data for training. Need at least 3 categories.")
            return
        
        logger.info(f"Training on {len(texts)} texts with {len(set(labels))} categories")
        
        # Vectorize texts
        self.tfidf_vectorizer = TfidfVectorizer(
            max_features=5000,
            stop_words='english',
            ngram_range=(1, 2),
            min_df=2,
            max_df=0.8
        )
        
        X = self.tfidf_vectorizer.fit_transform(texts)
        
        # Encode labels
        self.label_encoder = LabelEncoder()
        y = self.label_encoder.fit_transform(labels)
        
        # Train multiple models
        self.nb_classifier = MultinomialNB(alpha=0.1)
        self.lr_classifier = LogisticRegression(max_iter=1000, random_state=42)
        
        self.nb_classifier.fit(X, y)
        self.lr_classifier.fit(X, y)
        
        self.is_trained = True
        logger.info("Content classifier training completed")
    
    def save_model(self, model_path: str = "content_classifier_model.joblib"):
        """Save trained model to disk"""
        if not self.is_trained:
            logger.warning("No trained model to save")
            return
        
        model_data = {
            'tfidf_vectorizer': self.tfidf_vectorizer,
            'nb_classifier': self.nb_classifier,
            'lr_classifier': self.lr_classifier,
            'label_encoder': self.label_encoder,
            'categories_config': self.categories_config
        }
        
        joblib.dump(model_data, model_path)
        logger.info(f"Model saved to {model_path}")
    
    def load_model(self, model_path: str = "content_classifier_model.joblib"):
        """Load trained model from disk"""
        try:
            model_data = joblib.load(model_path)
            
            self.tfidf_vectorizer = model_data['tfidf_vectorizer']
            self.nb_classifier = model_data['nb_classifier']
            self.lr_classifier = model_data['lr_classifier']
            self.label_encoder = model_data['label_encoder']
            self.categories_config.update(model_data.get('categories_config', {}))
            
            self.is_trained = True
            logger.info(f"Model loaded from {model_path}")
            
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
    
    def get_classification_stats(self) -> Dict[str, Any]:
        """Get classification performance statistics"""
        avg_processing_time = np.mean(self.classification_stats['processing_times']) if self.classification_stats['processing_times'] else 0
        
        return {
            'total_classified': self.classification_stats['total_classified'],
            'avg_processing_time_ms': round(avg_processing_time, 2),
            'category_distribution': dict(self.classification_stats['category_distribution']),
            'is_trained': self.is_trained,
            'available_categories': list(self.categories_config.keys())
        }
    
    async def analyze_category_trends(self, hours_back: int = 24) -> Dict[str, Any]:
        """Analyze trending categories over time"""
        db = SessionLocal()
        try:
            since = datetime.utcnow() - timedelta(hours=hours_back)
            articles = db.query(Article).filter(
                Article.published_at >= since
            ).order_by(Article.published_at.desc()).limit(500).all()
            
            # Classify articles and track trends
            category_timeline = defaultdict(list)
            
            for article in articles:
                result = await self.classify_content(article)
                hour_key = article.published_at.strftime('%Y-%m-%d-%H')
                category_timeline[result.primary_category.name].append({
                    'hour': hour_key,
                    'confidence': result.primary_category.confidence,
                    'article_id': article.id
                })
            
            # Calculate trending categories
            trending_categories = []
            for category, timeline in category_timeline.items():
                if len(timeline) >= 3:  # Minimum articles for trend
                    avg_confidence = np.mean([item['confidence'] for item in timeline])
                    recent_activity = len([item for item in timeline 
                                         if item['hour'] >= (datetime.utcnow() - timedelta(hours=6)).strftime('%Y-%m-%d-%H')])
                    
                    trending_categories.append({
                        'category': category,
                        'article_count': len(timeline),
                        'avg_confidence': round(avg_confidence, 3),
                        'recent_activity': recent_activity,
                        'trend_score': len(timeline) * avg_confidence * (recent_activity + 1)
                    })
            
            # Sort by trend score
            trending_categories.sort(key=lambda x: x['trend_score'], reverse=True)
            
            return {
                'trending_categories': trending_categories[:10],
                'total_articles_analyzed': len(articles),
                'time_period_hours': hours_back,
                'category_distribution': {cat: len(timeline) for cat, timeline in category_timeline.items()}
            }
            
        except Exception as e:
            logger.error(f"Error analyzing category trends: {e}")
            return {}
        finally:
            db.close()


# Global content classifier instance
content_classifier = SmartContentClassifier()


# Batch processing functions
async def classify_content_batch(articles: List[Article]) -> List[ClassificationResult]:
    """Classify multiple articles in batch"""
    logger.info(f"Classifying {len(articles)} articles in batch...")
    
    results = []
    for article in articles:
        try:
            result = await content_classifier.classify_content(article)
            results.append(result)
        except Exception as e:
            logger.error(f"Error classifying article {article.id}: {e}")
    
    logger.info(f"Batch classification completed: {len(results)} results")
    return results


async def auto_classify_new_articles():
    """Background task to classify new articles"""
    db = SessionLocal()
    try:
        # Find articles without categories (assuming we add a categories field)
        recent_articles = db.query(Article).filter(
            Article.published_at >= datetime.utcnow() - timedelta(hours=24)
        ).limit(100).all()
        
        classified_count = 0
        for article in recent_articles:
            try:
                result = await content_classifier.classify_content(article)
                # TODO: Store classification results in database
                classified_count += 1
            except Exception as e:
                logger.error(f"Auto-classification error for article {article.id}: {e}")
        
        logger.info(f"Auto-classified {classified_count} articles")
        
    except Exception as e:
        logger.error(f"Auto-classification batch error: {e}")
    finally:
        db.close()