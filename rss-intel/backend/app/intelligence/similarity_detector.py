#!/usr/bin/env python3
"""
Content Similarity Detector

Advanced real-time content similarity detection system for RSS Intelligence.
Detects duplicate, near-duplicate, and related content using multiple algorithms:
- TF-IDF cosine similarity
- N-gram similarity analysis
- Semantic similarity with word embeddings
- URL and title similarity detection
- Cross-source duplicate detection
"""

import re
import logging
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass
from datetime import datetime
import hashlib
import difflib
from collections import Counter
import math
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

logger = logging.getLogger(__name__)

@dataclass
class SimilarityMatch:
    """A similarity match between two content items."""
    content_id_1: str
    content_id_2: str
    similarity_score: float  # 0.0 to 1.0
    similarity_type: str  # 'duplicate', 'near_duplicate', 'related', 'semantic'
    matching_elements: List[str]
    confidence: float  # 0.0 to 1.0

@dataclass
class ContentFingerprint:
    """Content fingerprint for efficient similarity detection."""
    content_id: str
    title_hash: str
    content_hash: str
    url_hash: str
    title_words: Set[str]
    content_ngrams: Set[str]
    key_phrases: List[str]
    word_count: int
    creation_time: datetime

@dataclass
class SimilarityDetectionResult:
    """Result of similarity detection analysis."""
    query_content_id: str
    similar_matches: List[SimilarityMatch]
    duplicate_matches: List[SimilarityMatch]
    related_matches: List[SimilarityMatch]
    total_matches_found: int
    analysis_timestamp: datetime

class ContentSimilarityDetector:
    """Advanced content similarity detection system."""
    
    def __init__(self):
        self.content_fingerprints: Dict[str, ContentFingerprint] = {}
        self.tfidf_vectorizer = TfidfVectorizer(
            max_features=5000,
            stop_words='english',
            ngram_range=(1, 2),
            max_df=0.95,
            min_df=2
        )
        self.content_vectors = {}
        
        # Similarity thresholds
        self.thresholds = {
            'duplicate': 0.95,      # Almost identical content
            'near_duplicate': 0.85, # Very similar content
            'related': 0.65,        # Related content
            'semantic': 0.70        # Semantically similar
        }
        
        # Common patterns for URL normalization
        self.url_patterns = [
            r'https?://',
            r'www\.',
            r'/\?.*$',  # Query parameters
            r'#.*$',    # Anchors
            r'/amp/?$', # AMP versions
            r'/m\./',   # Mobile versions
        ]

    def add_content(self, 
                   content_id: str, 
                   title: str, 
                   content: str, 
                   url: str = "") -> ContentFingerprint:
        """
        Add content to the similarity detection system.
        
        Args:
            content_id: Unique identifier for the content
            title: Content title
            content: Content text
            url: Content URL
            
        Returns:
            ContentFingerprint: Generated fingerprint for the content
        """
        try:
            # Create content fingerprint
            fingerprint = self._create_fingerprint(content_id, title, content, url)
            
            # Store fingerprint
            self.content_fingerprints[content_id] = fingerprint
            
            # Update TF-IDF vectors if we have enough content
            if len(self.content_fingerprints) >= 2:
                self._update_tfidf_vectors()
            
            logger.info(f"Added content fingerprint for: {content_id}")
            return fingerprint
            
        except Exception as e:
            logger.error(f"Error adding content {content_id}: {e}")
            raise

    def detect_similar_content(self, 
                             content_id: str,
                             similarity_types: List[str] = None) -> SimilarityDetectionResult:
        """
        Detect similar content for a given content item.
        
        Args:
            content_id: ID of content to check for similarities
            similarity_types: Types of similarity to check ('duplicate', 'near_duplicate', 'related', 'semantic')
            
        Returns:
            SimilarityDetectionResult: Detected similarities
        """
        try:
            if similarity_types is None:
                similarity_types = ['duplicate', 'near_duplicate', 'related', 'semantic']
            
            if content_id not in self.content_fingerprints:
                raise ValueError(f"Content {content_id} not found in fingerprints")
            
            query_fingerprint = self.content_fingerprints[content_id]
            all_matches = []
            
            # Check each similarity type
            for sim_type in similarity_types:
                matches = self._find_matches_by_type(query_fingerprint, sim_type)
                all_matches.extend(matches)
            
            # Organize matches by type
            duplicate_matches = [m for m in all_matches if m.similarity_type == 'duplicate']
            near_duplicate_matches = [m for m in all_matches if m.similarity_type == 'near_duplicate']
            related_matches = [m for m in all_matches if m.similarity_type in ['related', 'semantic']]
            
            # Sort by similarity score (descending)
            all_matches.sort(key=lambda x: x.similarity_score, reverse=True)
            duplicate_matches.sort(key=lambda x: x.similarity_score, reverse=True)
            near_duplicate_matches.sort(key=lambda x: x.similarity_score, reverse=True)
            related_matches.sort(key=lambda x: x.similarity_score, reverse=True)
            
            return SimilarityDetectionResult(
                query_content_id=content_id,
                similar_matches=all_matches[:20],  # Limit results
                duplicate_matches=duplicate_matches[:10],
                related_matches=related_matches[:10],
                total_matches_found=len(all_matches),
                analysis_timestamp=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Error detecting similar content for {content_id}: {e}")
            return self._create_empty_result(content_id)

    def batch_similarity_detection(self, 
                                 content_ids: List[str]) -> Dict[str, SimilarityDetectionResult]:
        """
        Run similarity detection for multiple content items.
        
        Args:
            content_ids: List of content IDs to analyze
            
        Returns:
            Dict mapping content IDs to their similarity results
        """
        results = {}
        
        for content_id in content_ids:
            try:
                results[content_id] = self.detect_similar_content(content_id)
            except Exception as e:
                logger.error(f"Error in batch detection for {content_id}: {e}")
                results[content_id] = self._create_empty_result(content_id)
        
        return results

    def remove_content(self, content_id: str) -> bool:
        """Remove content from similarity detection system."""
        try:
            if content_id in self.content_fingerprints:
                del self.content_fingerprints[content_id]
                
                # Remove from TF-IDF vectors
                if content_id in self.content_vectors:
                    del self.content_vectors[content_id]
                
                # Update TF-IDF if significant change
                if len(self.content_fingerprints) >= 2:
                    self._update_tfidf_vectors()
                
                logger.info(f"Removed content: {content_id}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error removing content {content_id}: {e}")
            return False

    def _create_fingerprint(self, 
                          content_id: str, 
                          title: str, 
                          content: str, 
                          url: str) -> ContentFingerprint:
        """Create a comprehensive content fingerprint."""
        # Generate hashes
        title_hash = hashlib.md5(title.lower().strip().encode()).hexdigest()
        content_hash = hashlib.md5(content.lower().strip().encode()).hexdigest()
        url_hash = hashlib.md5(self._normalize_url(url).encode()).hexdigest()
        
        # Extract title words (clean)
        title_words = set(self._clean_text(title).split())
        
        # Generate content n-grams
        content_ngrams = self._generate_ngrams(content, n=3)
        
        # Extract key phrases
        key_phrases = self._extract_key_phrases(f"{title} {content}")
        
        return ContentFingerprint(
            content_id=content_id,
            title_hash=title_hash,
            content_hash=content_hash,
            url_hash=url_hash,
            title_words=title_words,
            content_ngrams=content_ngrams,
            key_phrases=key_phrases,
            word_count=len(content.split()),
            creation_time=datetime.now()
        )

    def _find_matches_by_type(self, 
                            query_fingerprint: ContentFingerprint, 
                            similarity_type: str) -> List[SimilarityMatch]:
        """Find matches of a specific similarity type."""
        matches = []
        
        for content_id, fingerprint in self.content_fingerprints.items():
            if content_id == query_fingerprint.content_id:
                continue
            
            # Calculate similarity based on type
            if similarity_type == 'duplicate':
                match = self._check_duplicate_similarity(query_fingerprint, fingerprint)
            elif similarity_type == 'near_duplicate':
                match = self._check_near_duplicate_similarity(query_fingerprint, fingerprint)
            elif similarity_type == 'related':
                match = self._check_content_similarity(query_fingerprint, fingerprint)
            elif similarity_type == 'semantic':
                match = self._check_semantic_similarity(query_fingerprint, fingerprint)
            else:
                continue
            
            if match and match.similarity_score >= self.thresholds[similarity_type]:
                matches.append(match)
        
        return matches

    def _check_duplicate_similarity(self, 
                                  fp1: ContentFingerprint, 
                                  fp2: ContentFingerprint) -> Optional[SimilarityMatch]:
        """Check for duplicate content (exact or near-exact matches)."""
        matching_elements = []
        scores = []
        
        # Exact hash matches
        if fp1.title_hash == fp2.title_hash:
            matching_elements.append("Identical title")
            scores.append(1.0)
        
        if fp1.content_hash == fp2.content_hash:
            matching_elements.append("Identical content")
            scores.append(1.0)
        
        if fp1.url_hash == fp2.url_hash and fp1.url_hash != hashlib.md5(b'').hexdigest():
            matching_elements.append("Same URL")
            scores.append(1.0)
        
        # Title word overlap
        if fp1.title_words and fp2.title_words:
            title_overlap = len(fp1.title_words & fp2.title_words) / len(fp1.title_words | fp2.title_words)
            if title_overlap >= 0.8:
                matching_elements.append(f"Title overlap: {title_overlap:.2f}")
                scores.append(title_overlap)
        
        # N-gram similarity
        if fp1.content_ngrams and fp2.content_ngrams:
            ngram_overlap = len(fp1.content_ngrams & fp2.content_ngrams) / len(fp1.content_ngrams | fp2.content_ngrams)
            if ngram_overlap >= 0.7:
                matching_elements.append(f"Content n-gram overlap: {ngram_overlap:.2f}")
                scores.append(ngram_overlap)
        
        if not scores:
            return None
        
        similarity_score = max(scores)  # Use highest similarity
        confidence = min(0.9, len(matching_elements) / 3.0)  # More elements = higher confidence
        
        return SimilarityMatch(
            content_id_1=fp1.content_id,
            content_id_2=fp2.content_id,
            similarity_score=similarity_score,
            similarity_type='duplicate',
            matching_elements=matching_elements,
            confidence=confidence
        )

    def _check_near_duplicate_similarity(self, 
                                       fp1: ContentFingerprint, 
                                       fp2: ContentFingerprint) -> Optional[SimilarityMatch]:
        """Check for near-duplicate content."""
        matching_elements = []
        scores = []
        
        # Title similarity using difflib
        if fp1.title_words and fp2.title_words:
            title_text1 = " ".join(sorted(fp1.title_words))
            title_text2 = " ".join(sorted(fp2.title_words))
            title_sim = difflib.SequenceMatcher(None, title_text1, title_text2).ratio()
            if title_sim >= 0.7:
                matching_elements.append(f"Similar title: {title_sim:.2f}")
                scores.append(title_sim)
        
        # Content n-gram similarity
        if fp1.content_ngrams and fp2.content_ngrams:
            jaccard_sim = len(fp1.content_ngrams & fp2.content_ngrams) / len(fp1.content_ngrams | fp2.content_ngrams)
            if jaccard_sim >= 0.5:
                matching_elements.append(f"Content similarity: {jaccard_sim:.2f}")
                scores.append(jaccard_sim)
        
        # Key phrase overlap
        if fp1.key_phrases and fp2.key_phrases:
            phrase_overlap = len(set(fp1.key_phrases) & set(fp2.key_phrases))
            if phrase_overlap >= 2:
                matching_elements.append(f"Shared key phrases: {phrase_overlap}")
                phrase_score = min(1.0, phrase_overlap / 5.0)  # Normalize to 0-1
                scores.append(phrase_score)
        
        # Length similarity (similar articles often have similar length)
        if fp1.word_count > 0 and fp2.word_count > 0:
            length_ratio = min(fp1.word_count, fp2.word_count) / max(fp1.word_count, fp2.word_count)
            if length_ratio >= 0.8:
                matching_elements.append(f"Similar length: {length_ratio:.2f}")
                scores.append(length_ratio * 0.5)  # Lower weight for length
        
        if not scores:
            return None
        
        similarity_score = sum(scores) / len(scores)  # Average similarity
        confidence = min(0.8, len(matching_elements) / 4.0)
        
        return SimilarityMatch(
            content_id_1=fp1.content_id,
            content_id_2=fp2.content_id,
            similarity_score=similarity_score,
            similarity_type='near_duplicate',
            matching_elements=matching_elements,
            confidence=confidence
        )

    def _check_content_similarity(self, 
                                fp1: ContentFingerprint, 
                                fp2: ContentFingerprint) -> Optional[SimilarityMatch]:
        """Check for content similarity using TF-IDF."""
        try:
            if fp1.content_id not in self.content_vectors or fp2.content_id not in self.content_vectors:
                return None
            
            # Get TF-IDF vectors
            vec1 = self.content_vectors[fp1.content_id].reshape(1, -1)
            vec2 = self.content_vectors[fp2.content_id].reshape(1, -1)
            
            # Calculate cosine similarity
            similarity = cosine_similarity(vec1, vec2)[0][0]
            
            if similarity < self.thresholds['related']:
                return None
            
            matching_elements = [f"TF-IDF cosine similarity: {similarity:.3f}"]
            
            # Add additional context
            if fp1.key_phrases and fp2.key_phrases:
                shared_phrases = set(fp1.key_phrases) & set(fp2.key_phrases)
                if shared_phrases:
                    matching_elements.append(f"Shared phrases: {', '.join(list(shared_phrases)[:3])}")
            
            confidence = min(0.8, similarity)
            
            return SimilarityMatch(
                content_id_1=fp1.content_id,
                content_id_2=fp2.content_id,
                similarity_score=similarity,
                similarity_type='related',
                matching_elements=matching_elements,
                confidence=confidence
            )
            
        except Exception as e:
            logger.error(f"Error checking content similarity: {e}")
            return None

    def _check_semantic_similarity(self, 
                                 fp1: ContentFingerprint, 
                                 fp2: ContentFingerprint) -> Optional[SimilarityMatch]:
        """Check for semantic similarity (simplified version)."""
        # This is a simplified semantic similarity check
        # In a production system, you would use word embeddings or sentence transformers
        
        matching_elements = []
        scores = []
        
        # Key phrase semantic overlap
        if fp1.key_phrases and fp2.key_phrases:
            # Simple semantic overlap based on phrase matching
            semantic_overlap = 0
            for phrase1 in fp1.key_phrases[:10]:  # Limit for performance
                for phrase2 in fp2.key_phrases[:10]:
                    if self._phrases_semantically_similar(phrase1, phrase2):
                        semantic_overlap += 1
            
            if semantic_overlap >= 2:
                semantic_score = min(1.0, semantic_overlap / 5.0)
                matching_elements.append(f"Semantic phrase overlap: {semantic_overlap}")
                scores.append(semantic_score)
        
        # Word overlap with semantic weighting
        if fp1.title_words and fp2.title_words:
            semantic_words = self._get_semantic_word_overlap(fp1.title_words, fp2.title_words)
            if semantic_words:
                word_score = min(1.0, len(semantic_words) / 5.0)
                matching_elements.append(f"Semantic word overlap: {len(semantic_words)}")
                scores.append(word_score)
        
        if not scores:
            return None
        
        similarity_score = sum(scores) / len(scores)
        
        if similarity_score < self.thresholds['semantic']:
            return None
        
        confidence = min(0.7, similarity_score)
        
        return SimilarityMatch(
            content_id_1=fp1.content_id,
            content_id_2=fp2.content_id,
            similarity_score=similarity_score,
            similarity_type='semantic',
            matching_elements=matching_elements,
            confidence=confidence
        )

    def _update_tfidf_vectors(self):
        """Update TF-IDF vectors for all content."""
        try:
            # Collect all content texts
            contents = []
            content_ids = []
            
            for content_id, fingerprint in self.content_fingerprints.items():
                # Combine key phrases as representative text
                content_text = " ".join(fingerprint.key_phrases) if fingerprint.key_phrases else ""
                if content_text:
                    contents.append(content_text)
                    content_ids.append(content_id)
            
            if len(contents) < 2:
                return
            
            # Fit and transform TF-IDF
            vectors = self.tfidf_vectorizer.fit_transform(contents)
            
            # Store vectors
            self.content_vectors = {}
            for i, content_id in enumerate(content_ids):
                self.content_vectors[content_id] = vectors[i].toarray()[0]
            
            logger.info(f"Updated TF-IDF vectors for {len(content_ids)} contents")
            
        except Exception as e:
            logger.error(f"Error updating TF-IDF vectors: {e}")

    def _normalize_url(self, url: str) -> str:
        """Normalize URL for comparison."""
        if not url:
            return ""
        
        normalized = url.lower()
        for pattern in self.url_patterns:
            normalized = re.sub(pattern, "", normalized)
        
        return normalized.strip('/')

    def _clean_text(self, text: str) -> str:
        """Clean text for processing."""
        # Remove special characters, keep only alphanumeric and spaces
        cleaned = re.sub(r'[^a-zA-Z0-9\s]', ' ', text.lower())
        # Remove extra whitespace
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        return cleaned

    def _generate_ngrams(self, text: str, n: int = 3) -> Set[str]:
        """Generate n-grams from text."""
        words = self._clean_text(text).split()
        if len(words) < n:
            return set()
        
        ngrams = set()
        for i in range(len(words) - n + 1):
            ngram = " ".join(words[i:i+n])
            ngrams.add(ngram)
        
        return ngrams

    def _extract_key_phrases(self, text: str) -> List[str]:
        """Extract key phrases from text (simplified)."""
        # This is a simplified key phrase extraction
        # In production, you might use more sophisticated NLP techniques
        
        cleaned_text = self._clean_text(text)
        words = cleaned_text.split()
        
        # Extract 2-4 word phrases that might be important
        phrases = []
        
        # Extract noun phrases (simplified)
        for i in range(len(words) - 1):
            if len(words[i]) > 3 and len(words[i+1]) > 3:
                phrase = f"{words[i]} {words[i+1]}"
                phrases.append(phrase)
        
        # Get most common phrases
        phrase_counts = Counter(phrases)
        return [phrase for phrase, count in phrase_counts.most_common(20) if count >= 1]

    def _phrases_semantically_similar(self, phrase1: str, phrase2: str) -> bool:
        """Check if two phrases are semantically similar (simplified)."""
        # Simplified semantic similarity check
        words1 = set(phrase1.split())
        words2 = set(phrase2.split())
        
        # Check for word overlap
        overlap = len(words1 & words2)
        union = len(words1 | words2)
        
        if union == 0:
            return False
        
        similarity = overlap / union
        return similarity >= 0.5

    def _get_semantic_word_overlap(self, words1: Set[str], words2: Set[str]) -> Set[str]:
        """Get semantically similar words (simplified)."""
        # This is a very simplified approach
        # In production, you would use word embeddings
        return words1 & words2

    def _create_empty_result(self, content_id: str) -> SimilarityDetectionResult:
        """Create empty result for error cases."""
        return SimilarityDetectionResult(
            query_content_id=content_id,
            similar_matches=[],
            duplicate_matches=[],
            related_matches=[],
            total_matches_found=0,
            analysis_timestamp=datetime.now()
        )

# Create global detector instance
similarity_detector = ContentSimilarityDetector()

def detect_similar_content(content_id: str,
                         title: str = "",
                         content: str = "",
                         url: str = "",
                         similarity_types: List[str] = None) -> SimilarityDetectionResult:
    """
    Convenience function for content similarity detection.
    
    Args:
        content_id: Unique content identifier
        title: Content title (if adding new content)
        content: Content text (if adding new content)
        url: Content URL (if adding new content)
        similarity_types: Types of similarity to check
        
    Returns:
        SimilarityDetectionResult: Detected similarities
    """
    # Add content if not exists
    if content_id not in similarity_detector.content_fingerprints and title and content:
        similarity_detector.add_content(content_id, title, content, url)
    
    return similarity_detector.detect_similar_content(content_id, similarity_types)