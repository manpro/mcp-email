#!/usr/bin/env python3
"""
RSS Intelligence - Advanced AI & Intelligence Features

This module contains advanced AI capabilities for intelligent content analysis:
- Trend detection with semantic clustering
- Content categorization with ML models  
- Sentiment analysis pipeline
- Automatic keyword extraction
- Content quality scoring
- Real-time similarity detection
- Advanced spam and quality control detection
"""

from .trend_detector import trend_detector, continuous_trend_detection, get_current_trends
from .content_classifier import content_classifier, classify_content_batch
from .sentiment_analyzer import sentiment_analyzer, analyze_sentiment_batch
from .keyword_extractor import keyword_extractor, extract_keywords_batch
from .quality_scorer import quality_scorer, score_content_quality
from .similarity_detector import similarity_detector, detect_similar_content
from .spam_detector import AdvancedSpamDetector

# Initialize spam detector instance
spam_detector = AdvancedSpamDetector()

__all__ = [
    'trend_detector',
    'continuous_trend_detection', 
    'get_current_trends',
    'content_classifier',
    'classify_content_batch',
    'sentiment_analyzer',
    'analyze_sentiment_batch',
    'keyword_extractor', 
    'extract_keywords_batch',
    'quality_scorer',
    'score_content_quality',
    'similarity_detector',
    'detect_similar_content',
    'spam_detector'
]