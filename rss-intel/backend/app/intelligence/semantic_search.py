#!/usr/bin/env python3
"""
Semantic Search Engine for RSS Intelligence

Advanced semantic search using vector embeddings and similarity matching.
Provides intelligent query understanding and content matching beyond keyword-based search.

Features:
- Sentence transformer embeddings for semantic understanding
- Vector similarity search with FAISS indexing
- Query expansion and intent detection
- Multi-modal search (title + content + metadata)
- Real-time indexing and search
"""

import logging
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass
from datetime import datetime
import numpy as np
import json
from collections import defaultdict
import re

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    
try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)

@dataclass
class SemanticSearchResult:
    """A semantic search result with relevance scoring"""
    content_id: str
    title: str
    content_preview: str
    url: str
    relevance_score: float
    match_type: str  # 'semantic', 'hybrid', 'keyword'
    match_explanation: str
    embedding_similarity: float
    keyword_similarity: float
    metadata_match: bool = False

@dataclass
class SearchQuery:
    """Processed search query with intent and expansions"""
    original_query: str
    cleaned_query: str
    query_tokens: List[str]
    query_intent: str  # 'informational', 'navigational', 'transactional'
    expanded_terms: List[str]
    semantic_vector: Optional[np.ndarray] = None
    query_embedding: Optional[np.ndarray] = None

@dataclass
class ContentVector:
    """Vector representation of content for semantic search"""
    content_id: str
    title: str
    content_preview: str
    url: str
    source: str
    title_embedding: np.ndarray
    content_embedding: np.ndarray
    combined_embedding: np.ndarray
    metadata: Dict[str, Any]
    last_updated: datetime

class SemanticSearchEngine:
    """Advanced semantic search engine with vector embeddings"""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2", enable_faiss: bool = True):
        self.model_name = model_name
        self.enable_faiss = enable_faiss and FAISS_AVAILABLE
        
        # Initialize models
        if SENTENCE_TRANSFORMERS_AVAILABLE:
            try:
                self.sentence_model = SentenceTransformer(model_name)
                self.embedding_dimension = self.sentence_model.get_sentence_embedding_dimension()
                logger.info(f"Loaded sentence transformer: {model_name} (dim: {self.embedding_dimension})")
            except Exception as e:
                logger.warning(f"Failed to load sentence transformer: {e}")
                self.sentence_model = None
                self.embedding_dimension = 384  # Default dimension
        else:
            logger.warning("Sentence transformers not available, using TF-IDF fallback")
            self.sentence_model = None
            self.embedding_dimension = 384
        
        # Fallback TF-IDF for keyword matching
        self.tfidf_vectorizer = TfidfVectorizer(
            max_features=10000,
            stop_words='english',
            ngram_range=(1, 3),
            max_df=0.95,
            min_df=1
        )
        
        # Vector storage
        self.content_vectors: Dict[str, ContentVector] = {}
        self.content_embeddings = []
        self.content_ids_ordered = []
        
        # FAISS index for fast similarity search
        if self.enable_faiss:
            try:
                self.faiss_index = faiss.IndexFlatIP(self.embedding_dimension)  # Inner product for cosine similarity
                self.faiss_index_built = False
                logger.info("FAISS index initialized")
            except Exception as e:
                logger.warning(f"FAISS initialization failed: {e}")
                self.enable_faiss = False
        
        # Query processing patterns
        self.intent_patterns = {
            'informational': [
                r'\b(what|how|why|when|where|who|explain|define|describe)\b',
                r'\b(information|learn|understand|know|about)\b'
            ],
            'navigational': [
                r'\b(find|search|locate|show|list|get)\b',
                r'\b(page|article|post|content)\b'
            ],
            'transactional': [
                r'\b(buy|purchase|order|download|register|signup|login)\b',
                r'\b(price|cost|free|trial|demo)\b'
            ]
        }
        
        # Common query expansions
        self.query_expansions = {
            'ai': ['artificial intelligence', 'machine learning', 'deep learning', 'neural networks'],
            'ml': ['machine learning', 'artificial intelligence', 'data science', 'algorithms'],
            'api': ['application programming interface', 'web service', 'rest api', 'integration'],
            'fintech': ['financial technology', 'payments', 'banking', 'financial services'],
            'crypto': ['cryptocurrency', 'blockchain', 'bitcoin', 'ethereum', 'digital currency'],
        }

    def add_content(self, 
                   content_id: str,
                   title: str,
                   content: str,
                   url: str = "",
                   source: str = "",
                   metadata: Dict[str, Any] = None) -> bool:
        """
        Add content to the semantic search index
        
        Args:
            content_id: Unique identifier for the content
            title: Content title
            content: Full content text
            url: Content URL
            source: Content source/domain
            metadata: Additional metadata
            
        Returns:
            bool: True if successfully added
        """
        try:
            if metadata is None:
                metadata = {}
            
            # Generate embeddings
            title_embedding = self._get_embedding(title)
            content_preview = content[:500] if len(content) > 500 else content
            content_embedding = self._get_embedding(content_preview)
            
            # Create combined embedding (weighted average)
            combined_text = f"{title} {content_preview}"
            combined_embedding = self._get_embedding(combined_text)
            
            # Create content vector
            content_vector = ContentVector(
                content_id=content_id,
                title=title,
                content_preview=content_preview,
                url=url,
                source=source,
                title_embedding=title_embedding,
                content_embedding=content_embedding,
                combined_embedding=combined_embedding,
                metadata=metadata,
                last_updated=datetime.now()
            )
            
            # Store in memory
            self.content_vectors[content_id] = content_vector
            
            # Update FAISS index
            if self.enable_faiss:
                self._update_faiss_index()
            
            logger.info(f"Added content to semantic index: {content_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add content {content_id}: {e}")
            return False

    def semantic_search(self,
                       query: str,
                       top_k: int = 20,
                       similarity_threshold: float = 0.3,
                       search_type: str = "hybrid") -> List[SemanticSearchResult]:
        """
        Perform semantic search on indexed content
        
        Args:
            query: Search query
            top_k: Maximum number of results to return
            similarity_threshold: Minimum similarity score threshold
            search_type: 'semantic', 'keyword', 'hybrid'
            
        Returns:
            List of semantic search results
        """
        try:
            if not self.content_vectors:
                return []
            
            # Process query
            processed_query = self._process_query(query)
            
            # Perform search based on type
            if search_type == "semantic" and self.sentence_model:
                results = self._semantic_vector_search(processed_query, top_k)
            elif search_type == "keyword":
                results = self._keyword_search(processed_query, top_k)
            else:  # hybrid
                results = self._hybrid_search(processed_query, top_k)
            
            # Filter by threshold and sort
            results = [r for r in results if r.relevance_score >= similarity_threshold]
            results.sort(key=lambda x: x.relevance_score, reverse=True)
            
            return results[:top_k]
            
        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            return []

    def batch_search(self, queries: List[str], top_k: int = 10) -> Dict[str, List[SemanticSearchResult]]:
        """Perform batch semantic search for multiple queries"""
        results = {}
        for query in queries:
            results[query] = self.semantic_search(query, top_k=top_k)
        return results

    def update_content(self, content_id: str, **kwargs) -> bool:
        """Update existing content in the index"""
        if content_id not in self.content_vectors:
            return False
        
        content_vector = self.content_vectors[content_id]
        
        # Update fields
        if 'title' in kwargs:
            content_vector.title = kwargs['title']
            content_vector.title_embedding = self._get_embedding(kwargs['title'])
        
        if 'content' in kwargs:
            content_preview = kwargs['content'][:500] if len(kwargs['content']) > 500 else kwargs['content']
            content_vector.content_preview = content_preview
            content_vector.content_embedding = self._get_embedding(content_preview)
        
        if 'url' in kwargs:
            content_vector.url = kwargs['url']
        
        if 'metadata' in kwargs:
            content_vector.metadata.update(kwargs['metadata'])
        
        # Regenerate combined embedding
        combined_text = f"{content_vector.title} {content_vector.content_preview}"
        content_vector.combined_embedding = self._get_embedding(combined_text)
        content_vector.last_updated = datetime.now()
        
        # Update FAISS index
        if self.enable_faiss:
            self._update_faiss_index()
        
        return True

    def remove_content(self, content_id: str) -> bool:
        """Remove content from the search index"""
        if content_id in self.content_vectors:
            del self.content_vectors[content_id]
            
            # Rebuild FAISS index
            if self.enable_faiss:
                self._update_faiss_index()
            
            logger.info(f"Removed content from semantic index: {content_id}")
            return True
        return False

    def get_similar_content(self, content_id: str, top_k: int = 5) -> List[SemanticSearchResult]:
        """Find content similar to a given content item"""
        if content_id not in self.content_vectors:
            return []
        
        content_vector = self.content_vectors[content_id]
        query_text = f"{content_vector.title} {content_vector.content_preview}"
        
        # Use semantic search to find similar content
        results = self.semantic_search(query_text, top_k=top_k + 1, search_type="semantic")
        
        # Remove the original content from results
        results = [r for r in results if r.content_id != content_id]
        
        return results[:top_k]

    def _process_query(self, query: str) -> SearchQuery:
        """Process and analyze search query"""
        # Clean query
        cleaned_query = re.sub(r'[^\w\s]', ' ', query.lower())
        cleaned_query = re.sub(r'\s+', ' ', cleaned_query).strip()
        
        # Tokenize
        query_tokens = cleaned_query.split()
        
        # Detect intent
        query_intent = self._detect_query_intent(query)
        
        # Expand query terms
        expanded_terms = self._expand_query_terms(query_tokens)
        
        # Generate embeddings
        query_embedding = self._get_embedding(query) if self.sentence_model else None
        
        return SearchQuery(
            original_query=query,
            cleaned_query=cleaned_query,
            query_tokens=query_tokens,
            query_intent=query_intent,
            expanded_terms=expanded_terms,
            query_embedding=query_embedding
        )

    def _semantic_vector_search(self, processed_query: SearchQuery, top_k: int) -> List[SemanticSearchResult]:
        """Perform pure semantic vector search"""
        if not self.sentence_model or processed_query.query_embedding is None:
            return []
        
        results = []
        
        if self.enable_faiss and self.faiss_index_built:
            # Use FAISS for fast search
            query_vector = processed_query.query_embedding.reshape(1, -1).astype('float32')
            faiss.normalize_L2(query_vector)  # Normalize for cosine similarity
            
            scores, indices = self.faiss_index.search(query_vector, min(top_k * 2, len(self.content_vectors)))
            
            for i, (score, idx) in enumerate(zip(scores[0], indices[0])):
                if idx < len(self.content_ids_ordered):
                    content_id = self.content_ids_ordered[idx]
                    content_vector = self.content_vectors[content_id]
                    
                    result = SemanticSearchResult(
                        content_id=content_id,
                        title=content_vector.title,
                        content_preview=content_vector.content_preview[:200],
                        url=content_vector.url,
                        relevance_score=float(score),
                        match_type='semantic',
                        match_explanation='Semantic vector similarity',
                        embedding_similarity=float(score),
                        keyword_similarity=0.0
                    )
                    results.append(result)
        else:
            # Brute force search
            query_vector = processed_query.query_embedding
            
            for content_id, content_vector in self.content_vectors.items():
                # Calculate cosine similarity with combined embedding
                similarity = cosine_similarity(
                    query_vector.reshape(1, -1),
                    content_vector.combined_embedding.reshape(1, -1)
                )[0][0]
                
                result = SemanticSearchResult(
                    content_id=content_id,
                    title=content_vector.title,
                    content_preview=content_vector.content_preview[:200],
                    url=content_vector.url,
                    relevance_score=float(similarity),
                    match_type='semantic',
                    match_explanation='Semantic vector similarity',
                    embedding_similarity=float(similarity),
                    keyword_similarity=0.0
                )
                results.append(result)
        
        return results

    def _keyword_search(self, processed_query: SearchQuery, top_k: int) -> List[SemanticSearchResult]:
        """Perform keyword-based search using TF-IDF"""
        try:
            # Prepare content texts
            texts = []
            content_ids = []
            
            for content_id, content_vector in self.content_vectors.items():
                text = f"{content_vector.title} {content_vector.content_preview}"
                texts.append(text)
                content_ids.append(content_id)
            
            if not texts:
                return []
            
            # Fit TF-IDF if not already fitted
            tfidf_matrix = self.tfidf_vectorizer.fit_transform(texts)
            
            # Transform query
            query_vector = self.tfidf_vectorizer.transform([processed_query.cleaned_query])
            
            # Calculate similarities
            similarities = cosine_similarity(query_vector, tfidf_matrix)[0]
            
            # Create results
            results = []
            for i, similarity in enumerate(similarities):
                content_id = content_ids[i]
                content_vector = self.content_vectors[content_id]
                
                result = SemanticSearchResult(
                    content_id=content_id,
                    title=content_vector.title,
                    content_preview=content_vector.content_preview[:200],
                    url=content_vector.url,
                    relevance_score=float(similarity),
                    match_type='keyword',
                    match_explanation='TF-IDF keyword matching',
                    embedding_similarity=0.0,
                    keyword_similarity=float(similarity)
                )
                results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"Keyword search failed: {e}")
            return []

    def _hybrid_search(self, processed_query: SearchQuery, top_k: int) -> List[SemanticSearchResult]:
        """Perform hybrid search combining semantic and keyword approaches"""
        # Get results from both methods
        semantic_results = self._semantic_vector_search(processed_query, top_k * 2) if self.sentence_model else []
        keyword_results = self._keyword_search(processed_query, top_k * 2)
        
        # Combine and re-rank results
        combined_results = {}
        
        # Add semantic results
        for result in semantic_results:
            combined_results[result.content_id] = result
            result.match_type = 'hybrid'
        
        # Merge keyword results
        for result in keyword_results:
            if result.content_id in combined_results:
                # Combine scores (weighted average)
                existing = combined_results[result.content_id]
                existing.keyword_similarity = result.relevance_score
                existing.relevance_score = (existing.embedding_similarity * 0.7 + result.relevance_score * 0.3)
                existing.match_explanation = 'Hybrid semantic + keyword matching'
            else:
                combined_results[result.content_id] = result
                result.match_type = 'hybrid'
                result.keyword_similarity = result.relevance_score
                result.embedding_similarity = 0.0
        
        return list(combined_results.values())

    def _get_embedding(self, text: str) -> np.ndarray:
        """Get embedding for text"""
        if self.sentence_model and text.strip():
            try:
                embedding = self.sentence_model.encode(text, convert_to_numpy=True)
                return embedding
            except Exception as e:
                logger.error(f"Error generating embedding: {e}")
        
        # Fallback: return zero vector
        return np.zeros(self.embedding_dimension)

    def _detect_query_intent(self, query: str) -> str:
        """Detect query intent based on patterns"""
        query_lower = query.lower()
        
        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    return intent
        
        return 'informational'  # Default intent

    def _expand_query_terms(self, query_tokens: List[str]) -> List[str]:
        """Expand query terms with synonyms and related terms"""
        expanded = []
        
        for token in query_tokens:
            expanded.append(token)
            if token in self.query_expansions:
                expanded.extend(self.query_expansions[token])
        
        return list(set(expanded))  # Remove duplicates

    def _update_faiss_index(self):
        """Update FAISS index with current content vectors"""
        if not self.enable_faiss:
            return
        
        try:
            # Collect all embeddings
            embeddings = []
            content_ids = []
            
            for content_id, content_vector in self.content_vectors.items():
                embeddings.append(content_vector.combined_embedding)
                content_ids.append(content_id)
            
            if not embeddings:
                return
            
            # Convert to numpy array and normalize
            embeddings_array = np.array(embeddings).astype('float32')
            faiss.normalize_L2(embeddings_array)
            
            # Rebuild index
            self.faiss_index.reset()
            self.faiss_index.add(embeddings_array)
            self.content_ids_ordered = content_ids
            self.faiss_index_built = True
            
            logger.info(f"Updated FAISS index with {len(embeddings)} vectors")
            
        except Exception as e:
            logger.error(f"Error updating FAISS index: {e}")
            self.faiss_index_built = False

    def get_stats(self) -> Dict[str, Any]:
        """Get search engine statistics"""
        return {
            'total_content_items': len(self.content_vectors),
            'embedding_dimension': self.embedding_dimension,
            'faiss_enabled': self.enable_faiss,
            'sentence_transformer_available': SENTENCE_TRANSFORMERS_AVAILABLE,
            'model_name': self.model_name,
            'faiss_index_built': getattr(self, 'faiss_index_built', False),
            'last_updated': datetime.now().isoformat()
        }

# Global semantic search engine instance
semantic_search_engine = SemanticSearchEngine()

def initialize_semantic_search(model_name: str = "all-MiniLM-L6-v2") -> bool:
    """Initialize the global semantic search engine"""
    global semantic_search_engine
    try:
        semantic_search_engine = SemanticSearchEngine(model_name=model_name)
        logger.info("Semantic search engine initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize semantic search engine: {e}")
        return False

def add_content_to_index(content_id: str, title: str, content: str, **kwargs) -> bool:
    """Convenience function to add content to the global search index"""
    return semantic_search_engine.add_content(content_id, title, content, **kwargs)

def search_content(query: str, top_k: int = 10, **kwargs) -> List[SemanticSearchResult]:
    """Convenience function for semantic search"""
    return semantic_search_engine.semantic_search(query, top_k=top_k, **kwargs)