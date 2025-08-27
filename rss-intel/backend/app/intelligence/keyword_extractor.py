#!/usr/bin/env python3
"""
Automatic Keyword Extraction and Tagging System for RSS Intelligence
Advanced NLP-based keyword extraction with contextual understanding and smart tagging
"""

import asyncio
import logging
import numpy as np
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass
import json
from collections import defaultdict, Counter
import string

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import networkx as nx
from textstat import flesch_reading_ease, gunning_fog

from ..config import settings
from ..store import Article
from ..deps import SessionLocal

logger = logging.getLogger(__name__)


@dataclass
class ExtractedKeyword:
    """Represents an extracted keyword with metadata"""
    term: str
    score: float
    frequency: int
    context: str  # Where it appears most
    category: str  # Type of keyword (entity, concept, etc.)
    confidence: float
    related_terms: List[str] = None


@dataclass
class KeywordExtractionResult:
    """Result of keyword extraction for an article"""
    article_id: int
    keywords: List[ExtractedKeyword]
    named_entities: List[ExtractedKeyword]
    technical_terms: List[ExtractedKeyword]
    trending_keywords: List[ExtractedKeyword]
    content_tags: List[str]
    extraction_method: str
    extraction_timestamp: datetime
    processing_time_ms: float


class AdvancedKeywordExtractor:
    """Multi-method keyword extraction with contextual understanding"""
    
    def __init__(self):
        # Domain-specific keyword patterns
        self.domain_patterns = {
            'financial': {
                'currencies': r'\b(USD|EUR|GBP|JPY|CAD|AUD|CHF|BTC|ETH|ADA|DOGE|USDT)\b',
                'financial_terms': r'\b(IPO|M&A|PE|VC|ROI|EBITDA|GDP|inflation|recession|bullish|bearish)\b',
                'market_indicators': r'\b(S&P\s*500|NASDAQ|DOW|FTSE|DAX|Nikkei)\b',
                'amounts': r'\$\d{1,3}(?:,\d{3})*(?:\.\d{2})?(?:\s*(?:million|billion|trillion|M|B|T))?'
            },
            'technology': {
                'tech_companies': r'\b(Apple|Google|Microsoft|Amazon|Meta|Tesla|NVIDIA|AMD|Intel)\b',
                'programming': r'\b(Python|JavaScript|Java|C\+\+|React|Angular|Node\.js|API|SDK|ML|AI)\b',
                'protocols': r'\b(HTTP|HTTPS|TCP|UDP|JSON|XML|REST|GraphQL|WebRTC)\b',
                'platforms': r'\b(AWS|Azure|GCP|Docker|Kubernetes|GitHub|GitLab)\b'
            },
            'health': {
                'conditions': r'\b(COVID|cancer|diabetes|hypertension|depression|anxiety)\b',
                'treatments': r'\b(vaccine|medication|therapy|surgery|treatment|clinical\s+trial)\b',
                'organizations': r'\b(FDA|WHO|CDC|NIH|NHS)\b'
            },
            'science': {
                'fields': r'\b(physics|chemistry|biology|neuroscience|astronomy|geology)\b',
                'methods': r'\b(research|study|experiment|analysis|peer\s+review|publication)\b',
                'institutions': r'\b(NASA|CERN|MIT|Stanford|Harvard|Nature|Science)\b'
            }
        }
        
        # Common entity types
        self.entity_patterns = {
            'person': r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b',  # Simple name pattern
            'organization': r'\b(?:Inc\.|Corp\.|Ltd\.|LLC|Co\.)|\b[A-Z]{2,}(?:\s+[A-Z]{2,})*\b',
            'location': r'\b(?:USA|UK|EU|China|Japan|Germany|France|Italy|Spain|Canada|Australia)\b',
            'date': r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}|\d{1,2}/\d{1,2}/\d{4}|\d{4}-\d{2}-\d{2}\b',
            'time': r'\b\d{1,2}:\d{2}(?:\s*(?:AM|PM))?\b'
        }
        
        # Stop words (enhanced)
        self.stop_words = set([
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by',
            'from', 'up', 'about', 'into', 'through', 'during', 'before', 'after', 'above', 'below',
            'over', 'under', 'again', 'further', 'then', 'once', 'here', 'there', 'when', 'where',
            'why', 'how', 'all', 'any', 'both', 'each', 'few', 'more', 'most', 'other', 'some',
            'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very', 's',
            't', 'can', 'will', 'just', 'don', 'should', 'now', 'said', 'says', 'would', 'could',
            'also', 'new', 'first', 'last', 'long', 'great', 'little', 'own', 'other', 'old', 'right',
            'big', 'high', 'different', 'small', 'large', 'next', 'early', 'young', 'important', 'good'
        ])
        
        # Technical term indicators
        self.technical_indicators = {
            'acronyms': r'\b[A-Z]{2,}\b',
            'versions': r'v?\d+\.\d+(?:\.\d+)?',
            'protocols': r'\b\w+://\w+',
            'file_extensions': r'\.\w{2,4}\b',
            'technical_suffixes': ['API', 'SDK', 'OS', 'DB', 'AI', 'ML', 'IoT', 'VR', 'AR']
        }
        
        # Performance tracking
        self.extraction_stats = {
            'total_extracted': 0,
            'avg_keywords_per_article': 0.0,
            'avg_processing_time': 0.0,
            'method_distribution': defaultdict(int),
            'category_distribution': defaultdict(int)
        }
    
    async def extract_keywords(self, article: Article, max_keywords: int = 20) -> KeywordExtractionResult:
        """Extract keywords using multiple methods and combine results"""
        start_time = datetime.utcnow()
        
        title_text = article.title or ""
        content_text = article.content or ""
        combined_text = f"{title_text} {content_text}"
        
        if not combined_text.strip():
            return self._empty_result(article.id, start_time)
        
        # Apply multiple extraction methods
        tfidf_keywords = await self._tfidf_extraction(combined_text)
        textrank_keywords = await self._textrank_extraction(combined_text)
        pattern_keywords = await self._pattern_based_extraction(combined_text)
        entity_keywords = await self._entity_extraction(combined_text)
        
        # Combine and rank all keywords
        combined_keywords = self._combine_keyword_results([
            (tfidf_keywords, 'tfidf', 0.3),
            (textrank_keywords, 'textrank', 0.3),
            (pattern_keywords, 'pattern', 0.2),
            (entity_keywords, 'entity', 0.2)
        ])
        
        # Categorize keywords
        categorized_keywords = self._categorize_keywords(combined_keywords, combined_text)
        
        # Extract named entities
        named_entities = self._extract_named_entities(combined_text)
        
        # Identify technical terms
        technical_terms = self._extract_technical_terms(combined_text)
        
        # Detect trending keywords (requires historical data)
        trending_keywords = await self._detect_trending_keywords(combined_keywords, article)
        
        # Generate content tags
        content_tags = self._generate_content_tags(combined_text, categorized_keywords)
        
        # Calculate processing time
        processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        # Update stats
        self._update_stats(len(categorized_keywords), processing_time, 'combined')
        
        return KeywordExtractionResult(
            article_id=article.id,
            keywords=categorized_keywords[:max_keywords],
            named_entities=named_entities[:10],
            technical_terms=technical_terms[:10],
            trending_keywords=trending_keywords[:5],
            content_tags=content_tags[:15],
            extraction_method='combined',
            extraction_timestamp=datetime.utcnow(),
            processing_time_ms=processing_time
        )
    
    async def _tfidf_extraction(self, text: str, max_keywords: int = 20) -> List[ExtractedKeyword]:
        """Extract keywords using TF-IDF"""
        try:
            # Preprocess text
            processed_text = self._preprocess_text(text)
            
            if not processed_text.strip():
                return []
            
            # Create TF-IDF vectorizer
            vectorizer = TfidfVectorizer(
                max_features=500,
                stop_words='english',
                ngram_range=(1, 3),
                min_df=1,
                max_df=0.8,
                token_pattern=r'\b[a-zA-Z][a-zA-Z0-9]*\b'
            )
            
            # Handle single document case
            corpus = [processed_text]
            if len(processed_text.split()) < 10:
                # Too short for meaningful TF-IDF
                return []
            
            tfidf_matrix = vectorizer.fit_transform(corpus)
            feature_names = vectorizer.get_feature_names_out()
            
            # Get TF-IDF scores
            scores = tfidf_matrix.toarray()[0]
            
            # Create keyword objects
            keywords = []
            for i, score in enumerate(scores):
                if score > 0:
                    term = feature_names[i]
                    frequency = processed_text.lower().count(term.lower())
                    
                    keyword = ExtractedKeyword(
                        term=term,
                        score=float(score),
                        frequency=frequency,
                        context='tfidf',
                        category='tfidf_term',
                        confidence=min(score * 2, 1.0)  # Normalize confidence
                    )
                    keywords.append(keyword)
            
            # Sort by score and return top keywords
            keywords.sort(key=lambda x: x.score, reverse=True)
            return keywords[:max_keywords]
            
        except Exception as e:
            logger.warning(f"TF-IDF extraction failed: {e}")
            return []
    
    async def _textrank_extraction(self, text: str, max_keywords: int = 20) -> List[ExtractedKeyword]:
        """Extract keywords using TextRank algorithm"""
        try:
            # Split into sentences
            sentences = re.split(r'[.!?]+', text)
            sentences = [s.strip() for s in sentences if len(s.strip()) > 10]
            
            if len(sentences) < 2:
                return []
            
            # Extract candidate phrases (noun phrases, named entities, etc.)
            candidates = self._extract_candidate_phrases(text)
            
            if len(candidates) < 3:
                return []
            
            # Build similarity graph
            similarity_matrix = self._build_similarity_matrix(candidates)
            
            # Apply PageRank
            graph = nx.from_numpy_array(similarity_matrix)
            pagerank_scores = nx.pagerank(graph, alpha=0.85, max_iter=100)
            
            # Create keyword objects
            keywords = []
            for i, candidate in enumerate(candidates):
                score = pagerank_scores.get(i, 0.0)
                frequency = text.lower().count(candidate.lower())
                
                keyword = ExtractedKeyword(
                    term=candidate,
                    score=float(score),
                    frequency=frequency,
                    context='textrank',
                    category='ranked_phrase',
                    confidence=min(score * 10, 1.0)  # Scale confidence
                )
                keywords.append(keyword)
            
            # Sort by score
            keywords.sort(key=lambda x: x.score, reverse=True)
            return keywords[:max_keywords]
            
        except Exception as e:
            logger.warning(f"TextRank extraction failed: {e}")
            return []
    
    async def _pattern_based_extraction(self, text: str) -> List[ExtractedKeyword]:
        """Extract keywords using domain-specific patterns"""
        keywords = []
        
        for domain, patterns in self.domain_patterns.items():
            for pattern_name, pattern in patterns.items():
                matches = re.findall(pattern, text, re.IGNORECASE)
                
                for match in matches:
                    # Handle tuple matches from complex patterns
                    if isinstance(match, tuple):
                        match = ' '.join(match).strip()
                    
                    if match and len(match) > 1:
                        frequency = text.count(match)
                        
                        keyword = ExtractedKeyword(
                            term=match,
                            score=2.0,  # High score for pattern matches
                            frequency=frequency,
                            context=f'{domain}_{pattern_name}',
                            category=f'{domain}_entity',
                            confidence=0.9
                        )
                        keywords.append(keyword)
        
        return keywords
    
    async def _entity_extraction(self, text: str) -> List[ExtractedKeyword]:
        """Extract named entities using pattern matching"""
        keywords = []
        
        for entity_type, pattern in self.entity_patterns.items():
            matches = re.findall(pattern, text)
            
            for match in matches:
                if isinstance(match, tuple):
                    match = ' '.join(match).strip()
                
                if match and len(match) > 2:
                    frequency = text.count(match)
                    
                    keyword = ExtractedKeyword(
                        term=match,
                        score=1.5,
                        frequency=frequency,
                        context=entity_type,
                        category='named_entity',
                        confidence=0.8
                    )
                    keywords.append(keyword)
        
        return keywords
    
    def _extract_candidate_phrases(self, text: str, max_candidates: int = 50) -> List[str]:
        """Extract candidate phrases for TextRank"""
        candidates = []
        
        # Simple noun phrase extraction
        # Look for patterns like: [Adj]* [Noun]+ or [Noun]+ [Prep] [Noun]+
        
        # Split into words and clean
        words = re.findall(r'\b[a-zA-Z][a-zA-Z0-9]*\b', text.lower())
        words = [w for w in words if w not in self.stop_words and len(w) > 2]
        
        # Extract unigrams
        candidates.extend(words)
        
        # Extract bigrams
        for i in range(len(words) - 1):
            bigram = f"{words[i]} {words[i+1]}"
            candidates.append(bigram)
        
        # Extract trigrams (selective)
        for i in range(len(words) - 2):
            trigram = f"{words[i]} {words[i+1]} {words[i+2]}"
            if len(trigram) <= 30:  # Reasonable length
                candidates.append(trigram)
        
        # Remove duplicates and filter
        unique_candidates = list(set(candidates))
        
        # Filter out very common or very rare candidates
        filtered_candidates = []
        for candidate in unique_candidates:
            if 2 <= len(candidate.split()) <= 3:  # Multi-word phrases
                filtered_candidates.append(candidate)
            elif len(candidate) >= 4 and len(candidate.split()) == 1:  # Single meaningful words
                filtered_candidates.append(candidate)
        
        return filtered_candidates[:max_candidates]
    
    def _build_similarity_matrix(self, candidates: List[str]) -> np.ndarray:
        """Build similarity matrix for TextRank"""
        n = len(candidates)
        similarity_matrix = np.zeros((n, n))
        
        # Simple Jaccard similarity based on character n-grams
        for i in range(n):
            for j in range(i+1, n):
                # Convert to character bigrams
                bigrams_i = set([candidates[i][k:k+2] for k in range(len(candidates[i])-1)])
                bigrams_j = set([candidates[j][k:k+2] for k in range(len(candidates[j])-1)])
                
                # Jaccard similarity
                intersection = len(bigrams_i.intersection(bigrams_j))
                union = len(bigrams_i.union(bigrams_j))
                
                if union > 0:
                    similarity = intersection / union
                    similarity_matrix[i][j] = similarity
                    similarity_matrix[j][i] = similarity
        
        return similarity_matrix
    
    def _combine_keyword_results(self, results: List[Tuple[List[ExtractedKeyword], str, float]]) -> List[ExtractedKeyword]:
        """Combine results from different extraction methods"""
        combined = {}
        
        for keywords, method, weight in results:
            for keyword in keywords:
                term_lower = keyword.term.lower()
                
                if term_lower in combined:
                    # Merge with existing keyword
                    existing = combined[term_lower]
                    existing.score += keyword.score * weight
                    existing.frequency = max(existing.frequency, keyword.frequency)
                    existing.confidence = max(existing.confidence, keyword.confidence)
                    
                    # Update context
                    if existing.context != keyword.context:
                        existing.context = f"{existing.context},{keyword.context}"
                else:
                    # Add new keyword
                    new_keyword = ExtractedKeyword(
                        term=keyword.term,
                        score=keyword.score * weight,
                        frequency=keyword.frequency,
                        context=keyword.context,
                        category=keyword.category,
                        confidence=keyword.confidence
                    )
                    combined[term_lower] = new_keyword
        
        # Convert back to list and sort
        combined_list = list(combined.values())
        combined_list.sort(key=lambda x: x.score, reverse=True)
        
        return combined_list
    
    def _categorize_keywords(self, keywords: List[ExtractedKeyword], text: str) -> List[ExtractedKeyword]:
        """Categorize keywords into semantic categories"""
        for keyword in keywords:
            # Determine category based on term characteristics
            term = keyword.term.lower()
            
            # Technical terms
            if (any(indicator in term for indicator in ['api', 'sdk', 'ai', 'ml', 'iot']) or
                re.match(r'.*\d+\.\d+.*', term) or  # Version numbers
                term.isupper()):  # Acronyms
                keyword.category = 'technical'
            
            # Financial terms
            elif any(financial in term for financial in ['$', 'million', 'billion', 'investment', 'market', 'price']):
                keyword.category = 'financial'
            
            # Company/Organization names
            elif (term.istitle() and len(term.split()) <= 2 and 
                  any(indicator in term.lower() for indicator in ['inc', 'corp', 'ltd', 'co'])):
                keyword.category = 'organization'
            
            # Geographic terms
            elif any(geo in term for geo in ['usa', 'china', 'europe', 'asia', 'global']):
                keyword.category = 'geographic'
            
            # Temporal terms
            elif any(temporal in term for temporal in ['2024', '2025', 'january', 'february', 'march', 'april', 'may']):
                keyword.category = 'temporal'
            
            # Default to concept
            else:
                keyword.category = 'concept'
        
        return keywords
    
    def _extract_named_entities(self, text: str) -> List[ExtractedKeyword]:
        """Extract named entities with higher confidence"""
        entities = []
        
        # Look for capitalized sequences (potential proper nouns)
        capitalized_sequences = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', text)
        
        for entity in capitalized_sequences:
            if len(entity.split()) >= 2:  # Multi-word entities more likely to be names
                frequency = text.count(entity)
                
                extracted_entity = ExtractedKeyword(
                    term=entity,
                    score=2.0,
                    frequency=frequency,
                    context='named_entity',
                    category='named_entity',
                    confidence=0.8
                )
                entities.append(extracted_entity)
        
        # Remove duplicates
        seen = set()
        unique_entities = []
        for entity in entities:
            if entity.term.lower() not in seen:
                seen.add(entity.term.lower())
                unique_entities.append(entity)
        
        return unique_entities
    
    def _extract_technical_terms(self, text: str) -> List[ExtractedKeyword]:
        """Extract technical terms and jargon"""
        technical_terms = []
        
        # Acronyms
        acronyms = re.findall(self.technical_indicators['acronyms'], text)
        for acronym in set(acronyms):
            if len(acronym) >= 2 and acronym not in self.stop_words:
                frequency = text.count(acronym)
                
                term = ExtractedKeyword(
                    term=acronym,
                    score=1.5,
                    frequency=frequency,
                    context='acronym',
                    category='technical',
                    confidence=0.7
                )
                technical_terms.append(term)
        
        # Version numbers
        versions = re.findall(self.technical_indicators['versions'], text)
        for version in set(versions):
            frequency = text.count(version)
            
            term = ExtractedKeyword(
                term=version,
                score=1.2,
                frequency=frequency,
                context='version',
                category='technical',
                confidence=0.9
            )
            technical_terms.append(term)
        
        # Technical suffixes
        for suffix in self.technical_indicators['technical_suffixes']:
            if suffix in text:
                frequency = text.count(suffix)
                
                term = ExtractedKeyword(
                    term=suffix,
                    score=1.8,
                    frequency=frequency,
                    context='technical_suffix',
                    category='technical',
                    confidence=0.8
                )
                technical_terms.append(term)
        
        return technical_terms
    
    async def _detect_trending_keywords(self, keywords: List[ExtractedKeyword], 
                                       article: Article) -> List[ExtractedKeyword]:
        """Detect trending keywords (requires historical data)"""
        # This would require comparison with historical keyword data
        # For now, return keywords with high frequency as potentially trending
        
        trending = []
        for keyword in keywords:
            if keyword.frequency >= 3 and keyword.score > 1.0:
                trending_keyword = ExtractedKeyword(
                    term=keyword.term,
                    score=keyword.score * 1.2,  # Boost score for trending
                    frequency=keyword.frequency,
                    context='trending',
                    category='trending',
                    confidence=keyword.confidence
                )
                trending.append(trending_keyword)
        
        return trending[:5]
    
    def _generate_content_tags(self, text: str, keywords: List[ExtractedKeyword]) -> List[str]:
        """Generate additional content tags based on text analysis"""
        tags = []
        text_lower = text.lower()
        
        # Content type tags
        if len(text) > 2000:
            tags.append('long-form')
        elif len(text) < 300:
            tags.append('brief')
        
        # Reading complexity
        try:
            flesch_score = flesch_reading_ease(text)
            if flesch_score > 80:
                tags.append('easy-read')
            elif flesch_score < 30:
                tags.append('complex')
        except:
            pass
        
        # Domain tags based on keywords
        domain_indicators = {
            'technology': ['tech', 'ai', 'software', 'digital', 'algorithm', 'data'],
            'finance': ['money', 'investment', 'market', 'financial', 'economic', 'price'],
            'science': ['research', 'study', 'discovery', 'scientific', 'analysis'],
            'politics': ['government', 'policy', 'political', 'election', 'law'],
            'health': ['health', 'medical', 'doctor', 'patient', 'treatment', 'medicine']
        }
        
        for domain, indicators in domain_indicators.items():
            if any(indicator in text_lower for indicator in indicators):
                tags.append(domain)
        
        # Sentiment indicators
        positive_indicators = ['success', 'growth', 'improvement', 'breakthrough', 'achievement']
        negative_indicators = ['crisis', 'problem', 'decline', 'failure', 'concern']
        
        if any(indicator in text_lower for indicator in positive_indicators):
            tags.append('positive')
        elif any(indicator in text_lower for indicator in negative_indicators):
            tags.append('negative')
        
        # Time sensitivity
        urgent_indicators = ['breaking', 'urgent', 'immediate', 'emergency', 'alert']
        if any(indicator in text_lower for indicator in urgent_indicators):
            tags.append('urgent')
        
        return list(set(tags))  # Remove duplicates
    
    def _preprocess_text(self, text: str) -> str:
        """Preprocess text for keyword extraction"""
        # Remove URLs
        text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
        
        # Remove email addresses
        text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '', text)
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def _empty_result(self, article_id: int, start_time: datetime) -> KeywordExtractionResult:
        """Return empty result for articles with insufficient content"""
        processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        return KeywordExtractionResult(
            article_id=article_id,
            keywords=[],
            named_entities=[],
            technical_terms=[],
            trending_keywords=[],
            content_tags=[],
            extraction_method='empty',
            extraction_timestamp=datetime.utcnow(),
            processing_time_ms=processing_time
        )
    
    def _update_stats(self, keyword_count: int, processing_time: float, method: str):
        """Update extraction statistics"""
        self.extraction_stats['total_extracted'] += 1
        
        # Update average keywords per article
        total = self.extraction_stats['total_extracted']
        current_avg = self.extraction_stats['avg_keywords_per_article']
        self.extraction_stats['avg_keywords_per_article'] = ((current_avg * (total - 1)) + keyword_count) / total
        
        # Update average processing time
        current_time_avg = self.extraction_stats['avg_processing_time']
        self.extraction_stats['avg_processing_time'] = ((current_time_avg * (total - 1)) + processing_time) / total
        
        # Update method distribution
        self.extraction_stats['method_distribution'][method] += 1
    
    def get_extraction_stats(self) -> Dict[str, Any]:
        """Get keyword extraction performance statistics"""
        return {
            'total_extracted': self.extraction_stats['total_extracted'],
            'avg_keywords_per_article': round(self.extraction_stats['avg_keywords_per_article'], 2),
            'avg_processing_time_ms': round(self.extraction_stats['avg_processing_time'], 2),
            'method_distribution': dict(self.extraction_stats['method_distribution']),
            'supported_domains': list(self.domain_patterns.keys()),
            'supported_entities': list(self.entity_patterns.keys())
        }
    
    async def analyze_keyword_trends(self, hours_back: int = 24) -> Dict[str, Any]:
        """Analyze keyword trends across recent articles"""
        db = SessionLocal()
        try:
            since = datetime.utcnow() - timedelta(hours=hours_back)
            articles = db.query(Article).filter(
                Article.published_at >= since
            ).order_by(Article.published_at.desc()).limit(100).all()
            
            if not articles:
                return {}
            
            # Extract keywords from all articles
            all_keywords = defaultdict(int)
            category_keywords = defaultdict(lambda: defaultdict(int))
            
            for article in articles:
                try:
                    result = await self.extract_keywords(article, max_keywords=10)
                    
                    for keyword in result.keywords:
                        all_keywords[keyword.term.lower()] += keyword.frequency
                        category_keywords[keyword.category][keyword.term.lower()] += keyword.frequency
                        
                except Exception as e:
                    logger.error(f"Error extracting keywords for article {article.id}: {e}")
            
            # Get top keywords
            top_keywords = sorted(all_keywords.items(), key=lambda x: x[1], reverse=True)[:20]
            
            # Get top keywords by category
            top_by_category = {}
            for category, keywords in category_keywords.items():
                top_by_category[category] = sorted(keywords.items(), key=lambda x: x[1], reverse=True)[:10]
            
            return {
                'time_period_hours': hours_back,
                'total_articles': len(articles),
                'top_keywords': [{'keyword': kw, 'frequency': freq} for kw, freq in top_keywords],
                'keywords_by_category': {
                    category: [{'keyword': kw, 'frequency': freq} for kw, freq in keywords]
                    for category, keywords in top_by_category.items()
                },
                'total_unique_keywords': len(all_keywords)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing keyword trends: {e}")
            return {}
        finally:
            db.close()


# Global keyword extractor instance
keyword_extractor = AdvancedKeywordExtractor()


# Batch processing functions
async def extract_keywords_batch(articles: List[Article]) -> List[KeywordExtractionResult]:
    """Extract keywords for multiple articles in batch"""
    logger.info(f"Extracting keywords for {len(articles)} articles in batch...")
    
    results = []
    for article in articles:
        try:
            result = await keyword_extractor.extract_keywords(article)
            results.append(result)
        except Exception as e:
            logger.error(f"Error extracting keywords for article {article.id}: {e}")
    
    logger.info(f"Batch keyword extraction completed: {len(results)} results")
    return results


async def auto_extract_keywords_new_articles():
    """Background task to extract keywords from new articles"""
    db = SessionLocal()
    try:
        # Find recent articles without keyword extraction
        recent_articles = db.query(Article).filter(
            Article.published_at >= datetime.utcnow() - timedelta(hours=6)
        ).limit(50).all()
        
        extracted_count = 0
        for article in recent_articles:
            try:
                result = await keyword_extractor.extract_keywords(article)
                # TODO: Store keyword extraction results in database
                extracted_count += 1
            except Exception as e:
                logger.error(f"Auto-keyword extraction error for article {article.id}: {e}")
        
        logger.info(f"Auto-extracted keywords for {extracted_count} articles")
        
    except Exception as e:
        logger.error(f"Auto-keyword extraction batch error: {e}")
    finally:
        db.close()