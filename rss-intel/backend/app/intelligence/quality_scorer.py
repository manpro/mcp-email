#!/usr/bin/env python3
"""
Content Quality Scorer

Advanced NLP-based content quality assessment system for RSS Intelligence.
Evaluates content across multiple quality dimensions:
- Readability and writing quality
- Informativeness and content depth
- Credibility indicators
- Technical accuracy
- Engagement potential
- Source reliability
"""

import re
import logging
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass
from datetime import datetime
import textstat
from collections import Counter
import math

logger = logging.getLogger(__name__)

@dataclass
class QualityScore:
    """Individual quality score for a specific dimension."""
    score: float  # 0.0 to 1.0
    dimension: str
    indicators: List[str]
    confidence: float  # 0.0 to 1.0

@dataclass 
class ContentQualityResult:
    """Complete quality assessment result."""
    overall_score: float  # 0.0 to 1.0
    quality_scores: List[QualityScore]
    quality_grade: str  # A, B, C, D, F
    strengths: List[str]
    weaknesses: List[str]
    recommendations: List[str]
    analysis_timestamp: datetime

class ContentQualityScorer:
    """Advanced content quality assessment system."""
    
    def __init__(self):
        self.quality_weights = {
            'readability': 0.20,
            'informativeness': 0.25,
            'credibility': 0.20,
            'engagement': 0.15,
            'technical_accuracy': 0.10,
            'source_reliability': 0.10
        }
        
        # Quality indicators patterns
        self.credibility_indicators = {
            'positive': [
                r'\b(study|research|data|statistics|analysis|report|survey|investigation)\b',
                r'\b(according to|based on|research shows|study finds|data indicates)\b',
                r'\b(expert|professor|researcher|analyst|scientist|doctor)\b',
                r'\b(university|institution|organization|agency|bureau)\b',
                r'\b(peer.reviewed|published|journal|conference|white paper)\b'
            ],
            'negative': [
                r'\b(allegedly|reportedly|rumors|gossip|unconfirmed|speculation)\b',
                r'\b(click here|amazing|shocking|unbelievable|miracle)\b',
                r'\b(secret|hidden|they don\'t want you to know|conspiracy)\b',
                r'!{2,}|\?{2,}|ALL CAPS WORDS{5,}'
            ]
        }
        
        self.engagement_patterns = {
            'positive': [
                r'\b(question|how|why|what|when|where|discover|learn|understand)\b',
                r'\b(example|case study|story|experience|lesson|insight)\b',
                r'\b(tips|guide|tutorial|step|method|approach|strategy)\b',
                r'\b(benefits|advantages|results|outcomes|impact|effects)\b'
            ],
            'negative': [
                r'\b(boring|technical jargon|complex terminology)\b',
                r'^[A-Z\s]{20,}$',  # All caps sections
                r'\b(furthermore|moreover|additionally|consequently){2,}'  # Too formal
            ]
        }
        
        self.technical_patterns = {
            'accuracy_indicators': [
                r'\b(version|model|specification|parameter|configuration)\b',
                r'\b(\d+(?:\.\d+)?%|\d+(?:,\d{3})*(?:\.\d+)?)\b',  # Numbers and percentages
                r'\b(API|SDK|framework|library|protocol|algorithm)\b',
                r'\b(benchmark|performance|metric|measurement|test)\b'
            ],
            'vague_language': [
                r'\b(some|many|most|various|several|numerous|plenty)\b',
                r'\b(approximately|roughly|about|around|nearly|almost)\b{2,}',
                r'\b(thing|stuff|item|element|aspect|factor){2,}\b'
            ]
        }

    def score_content_quality(self, 
                            title: str, 
                            content: str, 
                            source_url: str = "", 
                            author: str = "",
                            publish_date: Optional[datetime] = None) -> ContentQualityResult:
        """
        Comprehensive content quality assessment.
        
        Args:
            title: Article title
            content: Article content
            source_url: Source URL for reliability assessment
            author: Author information
            publish_date: Publication date
            
        Returns:
            ContentQualityResult: Complete quality assessment
        """
        try:
            full_text = f"{title} {content}"
            
            # Calculate individual quality scores
            quality_scores = []
            
            # 1. Readability Assessment
            readability_score = self._assess_readability(full_text)
            quality_scores.append(readability_score)
            
            # 2. Informativeness Assessment
            informativeness_score = self._assess_informativeness(title, content)
            quality_scores.append(informativeness_score)
            
            # 3. Credibility Assessment
            credibility_score = self._assess_credibility(full_text, source_url, author)
            quality_scores.append(credibility_score)
            
            # 4. Engagement Assessment
            engagement_score = self._assess_engagement(full_text)
            quality_scores.append(engagement_score)
            
            # 5. Technical Accuracy Assessment
            technical_score = self._assess_technical_accuracy(full_text)
            quality_scores.append(technical_score)
            
            # 6. Source Reliability Assessment
            source_score = self._assess_source_reliability(source_url, author, publish_date)
            quality_scores.append(source_score)
            
            # Calculate weighted overall score
            overall_score = sum(
                score.score * self.quality_weights[score.dimension] 
                for score in quality_scores
            )
            
            # Determine quality grade
            quality_grade = self._calculate_grade(overall_score)
            
            # Generate insights
            strengths, weaknesses, recommendations = self._generate_insights(quality_scores, overall_score)
            
            return ContentQualityResult(
                overall_score=overall_score,
                quality_scores=quality_scores,
                quality_grade=quality_grade,
                strengths=strengths,
                weaknesses=weaknesses,
                recommendations=recommendations,
                analysis_timestamp=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Error assessing content quality: {e}")
            return self._create_default_result()

    def _assess_readability(self, text: str) -> QualityScore:
        """Assess readability using multiple metrics."""
        try:
            indicators = []
            scores = []
            
            # Flesch Reading Ease
            flesch_score = textstat.flesch_reading_ease(text)
            if flesch_score >= 70:
                indicators.append("High readability (Flesch score)")
                scores.append(0.9)
            elif flesch_score >= 50:
                indicators.append("Moderate readability")
                scores.append(0.7)
            else:
                indicators.append("Low readability - complex text")
                scores.append(0.4)
            
            # Sentence length analysis
            sentences = re.split(r'[.!?]+', text)
            avg_sentence_length = sum(len(s.split()) for s in sentences if s.strip()) / max(len(sentences), 1)
            
            if avg_sentence_length <= 20:
                indicators.append("Good sentence length")
                scores.append(0.8)
            elif avg_sentence_length <= 30:
                indicators.append("Moderate sentence complexity")
                scores.append(0.6)
            else:
                indicators.append("Long, complex sentences")
                scores.append(0.3)
            
            # Syllable complexity
            syllable_count = textstat.syllable_count(text)
            word_count = len(text.split())
            avg_syllables = syllable_count / max(word_count, 1)
            
            if avg_syllables <= 1.5:
                indicators.append("Simple vocabulary")
                scores.append(0.8)
            elif avg_syllables <= 2.0:
                indicators.append("Moderate vocabulary complexity")
                scores.append(0.6)
            else:
                indicators.append("Complex vocabulary")
                scores.append(0.4)
            
            final_score = sum(scores) / len(scores) if scores else 0.5
            confidence = 0.8 if len(text) > 100 else 0.6
            
            return QualityScore(
                score=final_score,
                dimension="readability",
                indicators=indicators,
                confidence=confidence
            )
            
        except Exception as e:
            logger.error(f"Error assessing readability: {e}")
            return QualityScore(0.5, "readability", ["Assessment error"], 0.3)

    def _assess_informativeness(self, title: str, content: str) -> QualityScore:
        """Assess informativeness and content depth."""
        try:
            indicators = []
            scores = []
            
            # Content length assessment
            word_count = len(content.split())
            if word_count >= 500:
                indicators.append("Comprehensive content length")
                scores.append(0.9)
            elif word_count >= 200:
                indicators.append("Moderate content depth")
                scores.append(0.7)
            else:
                indicators.append("Brief content")
                scores.append(0.4)
            
            # Information density
            unique_words = len(set(content.lower().split()))
            total_words = len(content.split())
            word_diversity = unique_words / max(total_words, 1)
            
            if word_diversity >= 0.6:
                indicators.append("High vocabulary diversity")
                scores.append(0.8)
            elif word_diversity >= 0.4:
                indicators.append("Moderate vocabulary diversity")
                scores.append(0.6)
            else:
                indicators.append("Limited vocabulary diversity")
                scores.append(0.3)
            
            # Specific details and examples
            detail_patterns = [
                r'\b\d+(?:,\d{3})*(?:\.\d+)?\s*(?:percent|%|dollars?|\$|years?|months?|days?)\b',
                r'\b(?:for example|such as|including|specifically|namely)\b',
                r'\b(?:according to|based on|research shows|study found)\b'
            ]
            
            detail_count = sum(len(re.findall(pattern, content, re.IGNORECASE)) for pattern in detail_patterns)
            if detail_count >= 5:
                indicators.append("Rich in specific details")
                scores.append(0.9)
            elif detail_count >= 2:
                indicators.append("Some specific details")
                scores.append(0.6)
            else:
                indicators.append("Limited specific details")
                scores.append(0.3)
            
            # Title-content alignment
            title_words = set(title.lower().split())
            content_words = set(content.lower().split())
            overlap_ratio = len(title_words & content_words) / max(len(title_words), 1)
            
            if overlap_ratio >= 0.5:
                indicators.append("Good title-content alignment")
                scores.append(0.8)
            else:
                indicators.append("Weak title-content alignment")
                scores.append(0.4)
            
            final_score = sum(scores) / len(scores) if scores else 0.5
            
            return QualityScore(
                score=final_score,
                dimension="informativeness",
                indicators=indicators,
                confidence=0.8
            )
            
        except Exception as e:
            logger.error(f"Error assessing informativeness: {e}")
            return QualityScore(0.5, "informativeness", ["Assessment error"], 0.3)

    def _assess_credibility(self, text: str, source_url: str, author: str) -> QualityScore:
        """Assess content credibility indicators."""
        try:
            indicators = []
            scores = []
            
            # Positive credibility indicators
            positive_matches = 0
            for pattern in self.credibility_indicators['positive']:
                matches = len(re.findall(pattern, text, re.IGNORECASE))
                positive_matches += matches
            
            if positive_matches >= 3:
                indicators.append("Strong credibility signals")
                scores.append(0.9)
            elif positive_matches >= 1:
                indicators.append("Some credibility signals")
                scores.append(0.7)
            else:
                indicators.append("Limited credibility signals")
                scores.append(0.4)
            
            # Negative credibility indicators
            negative_matches = 0
            for pattern in self.credibility_indicators['negative']:
                matches = len(re.findall(pattern, text, re.IGNORECASE))
                negative_matches += matches
            
            if negative_matches == 0:
                indicators.append("No red flags detected")
                scores.append(0.8)
            elif negative_matches <= 2:
                indicators.append("Minor credibility concerns")
                scores.append(0.5)
            else:
                indicators.append("Multiple credibility red flags")
                scores.append(0.2)
            
            # Source domain assessment
            if source_url:
                domain_score = self._assess_domain_credibility(source_url)
                if domain_score >= 0.8:
                    indicators.append("Reputable source domain")
                    scores.append(0.9)
                elif domain_score >= 0.6:
                    indicators.append("Moderate source reputation")
                    scores.append(0.6)
                else:
                    indicators.append("Unknown source reputation")
                    scores.append(0.4)
            
            # Author information
            if author and len(author.strip()) > 0:
                indicators.append("Author attribution provided")
                scores.append(0.7)
            else:
                indicators.append("No author attribution")
                scores.append(0.3)
            
            final_score = sum(scores) / len(scores) if scores else 0.5
            
            return QualityScore(
                score=final_score,
                dimension="credibility",
                indicators=indicators,
                confidence=0.7
            )
            
        except Exception as e:
            logger.error(f"Error assessing credibility: {e}")
            return QualityScore(0.5, "credibility", ["Assessment error"], 0.3)

    def _assess_engagement(self, text: str) -> QualityScore:
        """Assess content engagement potential."""
        try:
            indicators = []
            scores = []
            
            # Positive engagement patterns
            positive_matches = 0
            for pattern in self.engagement_patterns['positive']:
                matches = len(re.findall(pattern, text, re.IGNORECASE))
                positive_matches += matches
            
            if positive_matches >= 5:
                indicators.append("High engagement potential")
                scores.append(0.9)
            elif positive_matches >= 2:
                indicators.append("Moderate engagement potential")
                scores.append(0.7)
            else:
                indicators.append("Limited engagement elements")
                scores.append(0.4)
            
            # Question usage (drives engagement)
            question_count = len(re.findall(r'\?', text))
            if question_count >= 3:
                indicators.append("Good use of questions")
                scores.append(0.8)
            elif question_count >= 1:
                indicators.append("Some questions present")
                scores.append(0.6)
            else:
                indicators.append("No engaging questions")
                scores.append(0.3)
            
            # Narrative elements
            narrative_patterns = [
                r'\b(?:story|experience|journey|adventure|challenge)\b',
                r'\b(?:suddenly|then|next|finally|meanwhile|however)\b',
                r'\b(?:imagine|picture|consider|think about)\b'
            ]
            
            narrative_count = sum(len(re.findall(pattern, text, re.IGNORECASE)) for pattern in narrative_patterns)
            if narrative_count >= 3:
                indicators.append("Strong narrative elements")
                scores.append(0.8)
            elif narrative_count >= 1:
                indicators.append("Some narrative elements")
                scores.append(0.6)
            else:
                indicators.append("Limited narrative appeal")
                scores.append(0.4)
            
            # Actionable content
            action_patterns = [
                r'\b(?:learn|discover|find out|explore|try|use|apply)\b',
                r'\b(?:tip|guide|how to|step|method|approach)\b',
                r'\b(?:can|will|should|must|need to|able to)\b'
            ]
            
            action_count = sum(len(re.findall(pattern, text, re.IGNORECASE)) for pattern in action_patterns)
            if action_count >= 5:
                indicators.append("Highly actionable content")
                scores.append(0.9)
            elif action_count >= 2:
                indicators.append("Some actionable elements")
                scores.append(0.6)
            else:
                indicators.append("Limited actionable content")
                scores.append(0.3)
            
            final_score = sum(scores) / len(scores) if scores else 0.5
            
            return QualityScore(
                score=final_score,
                dimension="engagement",
                indicators=indicators,
                confidence=0.7
            )
            
        except Exception as e:
            logger.error(f"Error assessing engagement: {e}")
            return QualityScore(0.5, "engagement", ["Assessment error"], 0.3)

    def _assess_technical_accuracy(self, text: str) -> QualityScore:
        """Assess technical accuracy and precision."""
        try:
            indicators = []
            scores = []
            
            # Technical accuracy indicators
            accuracy_matches = 0
            for pattern in self.technical_patterns['accuracy_indicators']:
                matches = len(re.findall(pattern, text, re.IGNORECASE))
                accuracy_matches += matches
            
            if accuracy_matches >= 5:
                indicators.append("High technical precision")
                scores.append(0.9)
            elif accuracy_matches >= 2:
                indicators.append("Moderate technical detail")
                scores.append(0.7)
            else:
                indicators.append("Limited technical precision")
                scores.append(0.5)
            
            # Vague language detection
            vague_matches = 0
            for pattern in self.technical_patterns['vague_language']:
                matches = len(re.findall(pattern, text, re.IGNORECASE))
                vague_matches += matches
            
            if vague_matches <= 2:
                indicators.append("Precise language use")
                scores.append(0.8)
            elif vague_matches <= 5:
                indicators.append("Some vague language")
                scores.append(0.6)
            else:
                indicators.append("Frequent vague language")
                scores.append(0.3)
            
            # Data and evidence
            data_patterns = [
                r'\b\d+(?:,\d{3})*(?:\.\d+)?\s*(?:percent|%)\b',
                r'\b\d{4}\b',  # Years
                r'\b(?:study|research|survey|poll|analysis)\b'
            ]
            
            data_count = sum(len(re.findall(pattern, text, re.IGNORECASE)) for pattern in data_patterns)
            if data_count >= 3:
                indicators.append("Evidence-based content")
                scores.append(0.8)
            elif data_count >= 1:
                indicators.append("Some supporting data")
                scores.append(0.6)
            else:
                indicators.append("Limited supporting evidence")
                scores.append(0.4)
            
            final_score = sum(scores) / len(scores) if scores else 0.5
            
            return QualityScore(
                score=final_score,
                dimension="technical_accuracy",
                indicators=indicators,
                confidence=0.6
            )
            
        except Exception as e:
            logger.error(f"Error assessing technical accuracy: {e}")
            return QualityScore(0.5, "technical_accuracy", ["Assessment error"], 0.3)

    def _assess_source_reliability(self, source_url: str, author: str, publish_date: Optional[datetime]) -> QualityScore:
        """Assess source and publication reliability."""
        try:
            indicators = []
            scores = []
            
            # Domain credibility
            if source_url:
                domain_score = self._assess_domain_credibility(source_url)
                if domain_score >= 0.8:
                    indicators.append("Highly reputable source")
                    scores.append(0.9)
                elif domain_score >= 0.6:
                    indicators.append("Moderately reputable source")
                    scores.append(0.7)
                else:
                    indicators.append("Unknown source reputation")
                    scores.append(0.5)
            else:
                indicators.append("No source URL provided")
                scores.append(0.3)
            
            # Author credibility
            if author and len(author.strip()) > 0:
                if any(title in author.lower() for title in ['dr.', 'prof.', 'phd', 'md', 'ceo', 'editor']):
                    indicators.append("Credentialed author")
                    scores.append(0.8)
                else:
                    indicators.append("Author identified")
                    scores.append(0.6)
            else:
                indicators.append("No author attribution")
                scores.append(0.3)
            
            # Recency assessment
            if publish_date:
                days_old = (datetime.now() - publish_date).days
                if days_old <= 7:
                    indicators.append("Recent publication")
                    scores.append(0.8)
                elif days_old <= 30:
                    indicators.append("Moderately recent")
                    scores.append(0.6)
                elif days_old <= 365:
                    indicators.append("Somewhat dated")
                    scores.append(0.4)
                else:
                    indicators.append("Outdated content")
                    scores.append(0.2)
            else:
                indicators.append("No publication date")
                scores.append(0.4)
            
            final_score = sum(scores) / len(scores) if scores else 0.5
            
            return QualityScore(
                score=final_score,
                dimension="source_reliability",
                indicators=indicators,
                confidence=0.7
            )
            
        except Exception as e:
            logger.error(f"Error assessing source reliability: {e}")
            return QualityScore(0.5, "source_reliability", ["Assessment error"], 0.3)

    def _assess_domain_credibility(self, source_url: str) -> float:
        """Assess domain credibility based on known patterns."""
        try:
            domain = re.search(r'https?://(?:www\.)?([^/]+)', source_url.lower())
            if not domain:
                return 0.5
                
            domain_name = domain.group(1)
            
            # High credibility domains
            high_cred_patterns = [
                r'\.edu$', r'\.gov$', r'\.org$',
                r'reuters\.com$', r'bloomberg\.com$', r'ap\.org$',
                r'bbc\.com$', r'nytimes\.com$', r'wsj\.com$',
                r'nature\.com$', r'science\.org$', r'ieee\.org$'
            ]
            
            for pattern in high_cred_patterns:
                if re.search(pattern, domain_name):
                    return 0.9
            
            # Medium credibility domains
            med_cred_patterns = [
                r'\.com$', r'cnn\.com$', r'techcrunch\.com$',
                r'forbes\.com$', r'guardian\.com$', r'wired\.com$'
            ]
            
            for pattern in med_cred_patterns:
                if re.search(pattern, domain_name):
                    return 0.6
            
            return 0.4  # Unknown domains
            
        except Exception as e:
            logger.error(f"Error assessing domain credibility: {e}")
            return 0.5

    def _calculate_grade(self, score: float) -> str:
        """Convert numeric score to letter grade."""
        if score >= 0.9:
            return "A"
        elif score >= 0.8:
            return "B"
        elif score >= 0.7:
            return "C"
        elif score >= 0.6:
            return "D"
        else:
            return "F"

    def _generate_insights(self, quality_scores: List[QualityScore], overall_score: float) -> Tuple[List[str], List[str], List[str]]:
        """Generate strengths, weaknesses, and recommendations."""
        strengths = []
        weaknesses = []
        recommendations = []
        
        # Analyze scores
        for score in quality_scores:
            if score.score >= 0.8:
                strengths.extend(score.indicators[:2])  # Top indicators
            elif score.score <= 0.4:
                weaknesses.extend(score.indicators[:2])
        
        # Generate recommendations based on weaknesses
        dimension_scores = {score.dimension: score.score for score in quality_scores}
        
        if dimension_scores.get('readability', 0) < 0.6:
            recommendations.append("Simplify sentence structure and vocabulary")
        
        if dimension_scores.get('informativeness', 0) < 0.6:
            recommendations.append("Add more specific details and examples")
        
        if dimension_scores.get('credibility', 0) < 0.6:
            recommendations.append("Include more authoritative sources and data")
        
        if dimension_scores.get('engagement', 0) < 0.6:
            recommendations.append("Add questions and actionable elements")
        
        if dimension_scores.get('technical_accuracy', 0) < 0.6:
            recommendations.append("Provide more precise technical details")
        
        if dimension_scores.get('source_reliability', 0) < 0.6:
            recommendations.append("Improve source attribution and author credentials")
        
        # Limit results
        return strengths[:5], weaknesses[:5], recommendations[:5]

    def _create_default_result(self) -> ContentQualityResult:
        """Create default result for error cases."""
        return ContentQualityResult(
            overall_score=0.5,
            quality_scores=[],
            quality_grade="C",
            strengths=[],
            weaknesses=["Analysis error occurred"],
            recommendations=["Retry content analysis"],
            analysis_timestamp=datetime.now()
        )

# Create global scorer instance
quality_scorer = ContentQualityScorer()

def score_content_quality(title: str, 
                         content: str, 
                         source_url: str = "", 
                         author: str = "",
                         publish_date: Optional[datetime] = None) -> ContentQualityResult:
    """
    Convenience function for content quality assessment.
    
    Args:
        title: Article title
        content: Article content  
        source_url: Source URL for reliability assessment
        author: Author information
        publish_date: Publication date
        
    Returns:
        ContentQualityResult: Complete quality assessment
    """
    return quality_scorer.score_content_quality(title, content, source_url, author, publish_date)