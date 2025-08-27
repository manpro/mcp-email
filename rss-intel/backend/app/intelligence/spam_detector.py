"""
Advanced spam and low-quality content detection system.
Identifies promotional content, future events spam, thin content, and title-content mismatches.
"""

import re
import logging
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass
from datetime import datetime, timedelta
import spacy
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import nltk
from textstat import flesch_reading_ease
import numpy as np

# Download required NLTK data
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')

logger = logging.getLogger(__name__)

@dataclass
class SpamSignal:
    """Individual spam detection signal"""
    type: str
    confidence: float  # 0.0 to 1.0
    reason: str
    evidence: List[str]

@dataclass
class QualityIssue:
    """Content quality issue detection"""
    issue_type: str
    severity: str  # low, medium, high, critical
    description: str
    confidence: float
    affected_sections: List[str]

@dataclass
class SpamDetectionResult:
    """Complete spam detection analysis"""
    is_spam: bool
    spam_probability: float
    spam_signals: List[SpamSignal]
    quality_issues: List[QualityIssue]
    content_score: float  # 0.0 to 1.0 (higher = better quality)
    title_content_coherence: float  # 0.0 to 1.0
    recommendation: str  # "accept", "review", "reject"

class AdvancedSpamDetector:
    """
    Advanced spam detection system that identifies:
    1. Promotional/advertising content
    2. Future events spam
    3. Thin/empty content
    4. Title-content mismatches
    5. Clickbait patterns
    """
    
    def __init__(self):
        # Load configuration
        from ..config.spam_config import get_spam_config
        self.config = get_spam_config()
        
        self.promotional_patterns = self._load_promotional_patterns()
        self.future_event_patterns = self._load_future_event_patterns()
        self.thin_content_indicators = self._load_thin_content_indicators()
        self.clickbait_patterns = self._load_clickbait_patterns()
        
        # Initialize NLP models
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except OSError:
            logger.warning("spaCy model not found, using basic text processing")
            self.nlp = None
            
        # TF-IDF for semantic similarity
        self.tfidf = TfidfVectorizer(
            max_features=1000,
            stop_words='english',
            ngram_range=(1, 2),
            lowercase=True
        )
        
        # Use configuration for thresholds
        self.quality_thresholds = {
            'min_word_count': self.config.thresholds.min_word_count,
            'min_sentence_count': self.config.thresholds.min_sentence_count,
            'max_promotional_ratio': self.config.thresholds.max_promotional_ratio,
            'min_title_coherence': self.config.thresholds.min_title_coherence,
            'min_readability_score': 20,  # Keep this hardcoded for now
            'max_future_event_ratio': 0.4  # Keep this hardcoded for now
        }
    
    def _load_promotional_patterns(self) -> List[Dict]:
        """Load promotional content detection patterns from config"""
        patterns = []
        base_weight = self.config.signal_weights.promotional_content
        
        # Convert config patterns to weighted patterns
        for i, pattern in enumerate(self.config.patterns.promotional_patterns):
            patterns.append({
                'pattern': pattern,
                'weight': base_weight,  # Use config weight
                'category': f'promotional_{i}'
            })
        
        # Add some additional hardcoded patterns with specific weights
        patterns.extend([
            {
                'pattern': r'www\.[a-zA-Z0-9\-\.]+\.com|https?://[^\s]+',
                'weight': base_weight * 0.6,  # Lower weight for links
                'category': 'external_links'
            }
        ])
        
        return patterns
    
    def _load_future_event_patterns(self) -> List[Dict]:
        """Load future events spam detection patterns from config"""
        patterns = []
        base_weight = self.config.signal_weights.future_events_spam
        
        # Convert config patterns to weighted patterns
        for i, pattern in enumerate(self.config.patterns.future_event_patterns):
            patterns.append({
                'pattern': pattern,
                'weight': base_weight,
                'category': f'future_event_{i}'
            })
        
        return patterns
    
    def _load_thin_content_indicators(self) -> List[Dict]:
        """Load thin content detection patterns"""
        return [
            {
                'pattern': r'\b(?:lorem ipsum|placeholder|sample text|test content)\b',
                'weight': 1.0,
                'category': 'placeholder_text'
            },
            {
                'pattern': r'^(.+?)\1{3,}',  # Repeated patterns
                'weight': 0.8,
                'category': 'repetitive_content'
            },
            {
                'pattern': r'\b(?:more information|read more|click here|see more|learn more)\b.*$',
                'weight': 0.6,
                'category': 'generic_endings'
            },
            {
                'pattern': r'^\s*\[.*?\]\s*$',  # Just placeholder brackets
                'weight': 0.9,
                'category': 'bracket_placeholders'
            }
        ]
    
    def _load_clickbait_patterns(self) -> List[Dict]:
        """Load clickbait detection patterns"""
        return [
            {
                'pattern': r'\b(?:you won\'t believe|shocking|amazing|incredible|unbelievable)\b',
                'weight': 0.8,
                'category': 'sensational_language'
            },
            {
                'pattern': r'\b(?:[0-9]+ reasons|[0-9]+ ways|[0-9]+ tips|[0-9]+ secrets)\b',
                'weight': 0.7,
                'category': 'numbered_lists'
            },
            {
                'pattern': r'\b(?:hate|love|secret|trick|hack|revealed|exposed)\b',
                'weight': 0.6,
                'category': 'emotional_triggers'
            },
            {
                'pattern': r'[\!\?]{2,}',  # Multiple exclamation/question marks
                'weight': 0.5,
                'category': 'excessive_punctuation'
            }
        ]
    
    def detect_spam(self, title: str, content: str, source: str = None) -> SpamDetectionResult:
        """
        Comprehensive spam detection analysis
        
        Args:
            title: Article title
            content: Article content
            source: Source domain (optional)
            
        Returns:
            SpamDetectionResult with detailed analysis
        """
        try:
            signals = []
            quality_issues = []
            
            # 1. Promotional content detection
            promo_signals = self._detect_promotional_content(title, content)
            signals.extend(promo_signals)
            
            # 2. Future events spam detection
            event_signals = self._detect_future_events_spam(title, content)
            signals.extend(event_signals)
            
            # 3. Thin content detection
            thin_signals = self._detect_thin_content(title, content)
            signals.extend(thin_signals)
            quality_issues.extend(self._assess_content_quality(content))
            
            # 4. Title-content coherence
            coherence_score = self._calculate_title_coherence(title, content)
            if coherence_score < self.quality_thresholds['min_title_coherence']:
                signals.append(SpamSignal(
                    type="title_mismatch",
                    confidence=1.0 - coherence_score,
                    reason=f"Title and content coherence too low: {coherence_score:.2f}",
                    evidence=[f"Title: {title[:100]}...", f"Content relevance score: {coherence_score:.2f}"]
                ))
            
            # 5. Clickbait detection
            clickbait_signals = self._detect_clickbait(title, content)
            signals.extend(clickbait_signals)
            
            # Calculate overall spam probability
            spam_probability = self._calculate_spam_probability(signals)
            
            # Calculate content quality score
            content_score = self._calculate_content_score(content, quality_issues)
            
            # Determine recommendation
            recommendation = self._determine_recommendation(spam_probability, content_score, coherence_score)
            
            return SpamDetectionResult(
                is_spam=spam_probability > 0.7,
                spam_probability=spam_probability,
                spam_signals=signals,
                quality_issues=quality_issues,
                content_score=content_score,
                title_content_coherence=coherence_score,
                recommendation=recommendation
            )
            
        except Exception as e:
            logger.error(f"Error in spam detection: {str(e)}")
            # Return safe default
            return SpamDetectionResult(
                is_spam=False,
                spam_probability=0.0,
                spam_signals=[],
                quality_issues=[],
                content_score=0.5,
                title_content_coherence=0.5,
                recommendation="review"
            )
    
    def _detect_promotional_content(self, title: str, content: str) -> List[SpamSignal]:
        """Detect promotional and advertising content"""
        signals = []
        text = f"{title} {content}".lower()
        
        promotional_score = 0
        evidence = []
        
        for pattern_info in self.promotional_patterns:
            matches = re.findall(pattern_info['pattern'], text, re.IGNORECASE)
            if matches:
                promotional_score += len(matches) * pattern_info['weight']
                evidence.extend(matches[:3])  # Limit evidence
        
        # Normalize score
        text_length = len(text.split())
        normalized_score = min(promotional_score / max(text_length, 100), 1.0)
        
        if normalized_score > 0.3:
            signals.append(SpamSignal(
                type="promotional_content",
                confidence=min(normalized_score, 1.0),
                reason=f"High promotional language density: {normalized_score:.2f}",
                evidence=evidence
            ))
        
        return signals
    
    def _detect_future_events_spam(self, title: str, content: str) -> List[SpamSignal]:
        """Detect future events spam patterns"""
        signals = []
        text = f"{title} {content}".lower()
        
        future_score = 0
        evidence = []
        
        for pattern_info in self.future_event_patterns:
            matches = re.findall(pattern_info['pattern'], text, re.IGNORECASE)
            if matches:
                future_score += len(matches) * pattern_info['weight']
                evidence.extend(matches[:3])
        
        # Normalize score
        text_length = len(text.split())
        normalized_score = min(future_score / max(text_length, 100), 1.0)
        
        if normalized_score > self.quality_thresholds['max_future_event_ratio']:
            signals.append(SpamSignal(
                type="future_events_spam",
                confidence=min(normalized_score, 1.0),
                reason=f"High future events language density: {normalized_score:.2f}",
                evidence=evidence
            ))
        
        return signals
    
    def _detect_thin_content(self, title: str, content: str) -> List[SpamSignal]:
        """Detect thin or low-quality content"""
        signals = []
        
        # Word count analysis
        words = content.split()
        if len(words) < self.quality_thresholds['min_word_count']:
            signals.append(SpamSignal(
                type="thin_content",
                confidence=1.0 - (len(words) / self.quality_thresholds['min_word_count']),
                reason=f"Content too short: {len(words)} words",
                evidence=[f"Word count: {len(words)}"]
            ))
        
        # Sentence count analysis
        sentences = re.split(r'[.!?]+', content)
        sentence_count = len([s for s in sentences if s.strip()])
        if sentence_count < self.quality_thresholds['min_sentence_count']:
            signals.append(SpamSignal(
                type="thin_content",
                confidence=0.8,
                reason=f"Too few sentences: {sentence_count}",
                evidence=[f"Sentence count: {sentence_count}"]
            ))
        
        # Thin content patterns
        text = content.lower()
        evidence = []
        
        for pattern_info in self.thin_content_indicators:
            matches = re.findall(pattern_info['pattern'], text, re.IGNORECASE)
            if matches:
                signals.append(SpamSignal(
                    type="thin_content",
                    confidence=pattern_info['weight'],
                    reason=f"Detected {pattern_info['category']} patterns",
                    evidence=matches[:3]
                ))
        
        return signals
    
    def _detect_clickbait(self, title: str, content: str) -> List[SpamSignal]:
        """Detect clickbait patterns"""
        signals = []
        text = title.lower()  # Focus on title for clickbait
        
        clickbait_score = 0
        evidence = []
        
        for pattern_info in self.clickbait_patterns:
            matches = re.findall(pattern_info['pattern'], text, re.IGNORECASE)
            if matches:
                clickbait_score += len(matches) * pattern_info['weight']
                evidence.extend(matches[:2])
        
        if clickbait_score > 0.5:
            signals.append(SpamSignal(
                type="clickbait",
                confidence=min(clickbait_score, 1.0),
                reason=f"Clickbait patterns detected: {clickbait_score:.2f}",
                evidence=evidence
            ))
        
        return signals
    
    def _calculate_title_coherence(self, title: str, content: str) -> float:
        """Calculate semantic coherence between title and content"""
        try:
            # Clean and prepare texts
            title_clean = re.sub(r'[^\w\s]', ' ', title.lower())
            content_clean = re.sub(r'[^\w\s]', ' ', content.lower())
            
            # Take first paragraph for content (avoid full article bias)
            content_sample = ' '.join(content_clean.split()[:100])
            
            if not title_clean.strip() or not content_sample.strip():
                return 0.0
            
            # Use TF-IDF similarity
            documents = [title_clean, content_sample]
            
            try:
                tfidf_matrix = self.tfidf.fit_transform(documents)
                similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
                return float(similarity)
            except Exception:
                # Fallback to simple word overlap
                title_words = set(title_clean.split())
                content_words = set(content_sample.split())
                
                if not title_words or not content_words:
                    return 0.0
                
                overlap = len(title_words.intersection(content_words))
                return overlap / len(title_words.union(content_words))
                
        except Exception as e:
            logger.error(f"Error calculating title coherence: {str(e)}")
            return 0.5
    
    def _assess_content_quality(self, content: str) -> List[QualityIssue]:
        """Assess overall content quality"""
        issues = []
        
        # Readability assessment
        try:
            readability = flesch_reading_ease(content)
            if readability < self.quality_thresholds['min_readability_score']:
                issues.append(QualityIssue(
                    issue_type="poor_readability",
                    severity="medium",
                    description=f"Low readability score: {readability:.1f}",
                    confidence=0.8,
                    affected_sections=["content"]
                ))
        except Exception:
            pass
        
        # Repetition analysis
        words = content.lower().split()
        if len(words) > 10:
            word_freq = {}
            for word in words:
                if len(word) > 3:  # Only check meaningful words
                    word_freq[word] = word_freq.get(word, 0) + 1
            
            total_words = len(words)
            max_freq = max(word_freq.values()) if word_freq else 0
            
            if max_freq > total_words * 0.1:  # More than 10% repetition
                issues.append(QualityIssue(
                    issue_type="excessive_repetition",
                    severity="medium",
                    description=f"High word repetition detected",
                    confidence=0.7,
                    affected_sections=["content"]
                ))
        
        return issues
    
    def _calculate_spam_probability(self, signals: List[SpamSignal]) -> float:
        """Calculate overall spam probability from signals"""
        if not signals:
            return 0.0
        
        # Weight different signal types
        signal_weights = {
            'promotional_content': 0.8,
            'future_events_spam': 0.7,
            'thin_content': 0.6,
            'title_mismatch': 0.9,
            'clickbait': 0.5
        }
        
        total_score = 0
        total_weight = 0
        
        for signal in signals:
            weight = signal_weights.get(signal.type, 0.5)
            total_score += signal.confidence * weight
            total_weight += weight
        
        if total_weight == 0:
            return 0.0
        
        return min(total_score / total_weight, 1.0)
    
    def _calculate_content_score(self, content: str, quality_issues: List[QualityIssue]) -> float:
        """Calculate overall content quality score"""
        base_score = 1.0
        
        # Penalize based on quality issues
        for issue in quality_issues:
            severity_penalties = {
                'low': 0.1,
                'medium': 0.2,
                'high': 0.4,
                'critical': 0.6
            }
            penalty = severity_penalties.get(issue.severity, 0.1) * issue.confidence
            base_score -= penalty
        
        # Basic content metrics
        word_count = len(content.split())
        if word_count < 50:
            base_score *= (word_count / 50)
        
        return max(base_score, 0.0)
    
    def _determine_recommendation(self, spam_prob: float, content_score: float, coherence: float) -> str:
        """Determine overall recommendation"""
        if spam_prob > 0.8 or content_score < 0.2:
            return "reject"
        elif spam_prob > 0.5 or content_score < 0.4 or coherence < 0.3:
            return "review"
        else:
            return "accept"
    
    def get_spam_summary(self, result: SpamDetectionResult) -> str:
        """Generate human-readable summary of spam detection results"""
        if result.is_spam:
            return f"SPAM DETECTED: {result.spam_probability:.1%} probability"
        
        issues = []
        if result.spam_probability > 0.5:
            issues.append(f"High spam risk ({result.spam_probability:.1%})")
        if result.content_score < 0.5:
            issues.append(f"Low content quality ({result.content_score:.1%})")
        if result.title_content_coherence < 0.3:
            issues.append(f"Title-content mismatch ({result.title_content_coherence:.1%})")
        
        if issues:
            return f"Quality issues: {', '.join(issues)}"
        else:
            return f"Good quality content (Score: {result.content_score:.1%})"