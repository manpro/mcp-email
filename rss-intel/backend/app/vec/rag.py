"""RAG (Retrieval-Augmented Generation) functionality"""
from typing import List, Dict, Any, Optional, Tuple
import logging
from datetime import datetime
import json

from .weaviate_client import weaviate_manager
from .embedder import get_batch_embedder
from rank_bm25 import BM25Okapi
import numpy as np
from rapidfuzz import fuzz

logger = logging.getLogger(__name__)


class RAGSearchEngine:
    """Main RAG search engine combining vector and BM25 search"""
    
    def __init__(self):
        self.embedder = get_batch_embedder()
        self.reranker = ReRanker()
    
    def search(
        self,
        query: str,
        k: int = 30,
        lang: Optional[str] = None,
        freshness_days: Optional[int] = None,
        min_score: Optional[int] = None,
        hybrid: bool = True,
        alpha: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Perform semantic search with optional filters
        
        Args:
            query: Search query
            k: Number of results to return
            lang: Language filter ('en', 'sv', etc.)
            freshness_days: Only include articles from last N days
            min_score: Minimum article score
            hybrid: Use hybrid (vector + BM25) search
            alpha: Hybrid search balance (0=BM25 only, 1=vector only)
            
        Returns:
            List of search results with metadata
        """
        logger.info(f"Searching for: '{query}' (k={k}, lang={lang}, hybrid={hybrid})")
        
        try:
            if hybrid:
                # Hybrid search using Weaviate
                query_vector = self.embedder.embed_query(query)
                
                results = weaviate_manager.hybrid_search(
                    query=query,
                    vector=query_vector,
                    limit=min(k * 2, 100),  # Get more for re-ranking
                    alpha=alpha,
                    lang=lang,
                    freshness_days=freshness_days,
                    min_score=min_score
                )
            else:
                # Vector-only search
                query_vector = self.embedder.embed_query(query)
                
                results = weaviate_manager.hybrid_search(
                    query="",  # Empty query for vector-only
                    vector=query_vector,
                    limit=min(k * 2, 100),
                    alpha=1.0,  # Vector only
                    lang=lang,
                    freshness_days=freshness_days,
                    min_score=min_score
                )
            
            if not results:
                logger.info("No results found")
                return []
            
            # Re-rank results
            reranked_results = self.reranker.rerank(query, results)
            
            # Group by article and take best chunk per article
            grouped_results = self._group_by_article(reranked_results)
            
            # Apply final scoring and limit
            final_results = self._apply_final_scoring(query, grouped_results)
            
            # Limit results
            limited_results = final_results[:k]
            
            # Add search metadata
            for result in limited_results:
                result['search_metadata'] = {
                    'query': query,
                    'hybrid': hybrid,
                    'alpha': alpha,
                    'timestamp': datetime.utcnow().isoformat()
                }
            
            logger.info(f"Returning {len(limited_results)} search results")
            return limited_results
            
        except Exception as e:
            logger.error(f"Search error: {e}")
            return []
    
    def _group_by_article(self, results: List[Dict[str, Any]]) -> Dict[int, Dict[str, Any]]:
        """Group results by article ID, keeping best chunk per article"""
        grouped = {}
        
        for result in results:
            article_id = result['article_id']
            
            if article_id not in grouped:
                grouped[article_id] = result
            else:
                # Keep result with higher search score
                if result.get('final_score', 0) > grouped[article_id].get('final_score', 0):
                    grouped[article_id] = result
        
        return grouped
    
    def _apply_final_scoring(self, query: str, grouped_results: Dict[int, Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Apply final scoring combining multiple factors"""
        results = list(grouped_results.values())
        
        for result in results:
            # Base search score
            search_score = result.get('final_score', result.get('search_score', 0))
            
            # Recency boost
            recency_boost = self._calculate_recency_boost(result['published_at'])
            
            # Rule score normalization
            rule_score_norm = min(1.0, result.get('score', 0) / 100.0)
            
            # Title relevance boost
            title_boost = self._calculate_title_relevance(query, result['title'])
            
            # Combine scores
            final_score = (
                0.5 * search_score +
                0.2 * recency_boost + 
                0.2 * rule_score_norm +
                0.1 * title_boost
            )
            
            result['final_score'] = final_score
            result['score_components'] = {
                'search_score': search_score,
                'recency_boost': recency_boost,
                'rule_score_norm': rule_score_norm,
                'title_boost': title_boost
            }
        
        # Sort by final score
        results.sort(key=lambda x: x['final_score'], reverse=True)
        return results
    
    def _calculate_recency_boost(self, published_at: datetime) -> float:
        """Calculate recency boost factor"""
        if not published_at:
            return 0.0
        
        days_old = (datetime.now(published_at.tzinfo) - published_at).days
        # Exponential decay: newer articles get higher boost
        return np.exp(-days_old / 14.0)  # Half-life of 14 days
    
    def _calculate_title_relevance(self, query: str, title: str) -> float:
        """Calculate title relevance using fuzzy matching"""
        if not title:
            return 0.0
        
        # Use fuzzy string matching
        similarity = fuzz.partial_ratio(query.lower(), title.lower()) / 100.0
        return similarity


class ReRanker:
    """Re-ranks search results using cross-encoder model"""
    
    def __init__(self):
        # For now, use a simple scoring approach
        # Could be enhanced with actual cross-encoder model
        self.use_cross_encoder = False
    
    def rerank(self, query: str, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Re-rank results based on query-document relevance"""
        if not results:
            return results
        
        if self.use_cross_encoder:
            return self._cross_encoder_rerank(query, results)
        else:
            return self._simple_rerank(query, results)
    
    def _simple_rerank(self, query: str, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Simple re-ranking using text similarity metrics"""
        query_words = set(query.lower().split())
        
        for result in results:
            text = result.get('text', '')
            title = result.get('title', '')
            
            # Calculate keyword overlap
            text_words = set(text.lower().split())
            title_words = set(title.lower().split())
            
            text_overlap = len(query_words & text_words) / max(len(query_words), 1)
            title_overlap = len(query_words & title_words) / max(len(query_words), 1)
            
            # Combine with original search score
            search_score = result.get('search_score', 0)
            rerank_score = search_score + 0.2 * text_overlap + 0.3 * title_overlap
            
            result['final_score'] = rerank_score
            result['rerank_components'] = {
                'original_score': search_score,
                'text_overlap': text_overlap,
                'title_overlap': title_overlap
            }
        
        # Sort by re-ranked score
        results.sort(key=lambda x: x['final_score'], reverse=True)
        return results
    
    def _cross_encoder_rerank(self, query: str, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Re-rank using cross-encoder model (placeholder)"""
        # This would use a model like cross-encoder/ms-marco-MiniLM-L-6-v2
        # For now, just return original results
        return results


class AnswerGenerator:
    """Generates answers from retrieved context"""
    
    def __init__(self):
        self.max_context_tokens = 2000
    
    def generate_answer(
        self,
        question: str,
        search_results: List[Dict[str, Any]],
        lang: str = 'en'
    ) -> Dict[str, Any]:
        """
        Generate answer from search results
        
        Args:
            question: User question
            search_results: Results from search
            lang: Language for answer
            
        Returns:
            Dict with answer and citations
        """
        logger.info(f"Generating answer for: '{question}' (lang={lang})")
        
        if not search_results:
            return {
                'answer': 'Sorry, I could not find relevant information to answer your question.',
                'citations': [],
                'confidence': 0.0
            }
        
        # Build context from search results
        context = self._build_context(search_results)
        
        # Generate answer (simplified approach)
        answer = self._generate_simple_answer(question, context, search_results, lang)
        
        # Build citations
        citations = self._build_citations(search_results[:5])  # Top 5 sources
        
        return {
            'answer': answer,
            'citations': citations,
            'context_used': len(context),
            'sources_count': len(search_results),
            'confidence': self._estimate_confidence(search_results)
        }
    
    def _build_context(self, search_results: List[Dict[str, Any]]) -> str:
        """Build context string from search results"""
        context_parts = []
        total_length = 0
        
        for i, result in enumerate(search_results):
            text = result.get('text', '')
            title = result.get('title', '')
            source = result.get('source', '')
            
            # Create context snippet
            snippet = f"Source {i+1} - {title} ({source}):\n{text}\n"
            
            # Check token budget (rough estimate)
            if total_length + len(snippet) > self.max_context_tokens * 4:  # ~4 chars per token
                break
            
            context_parts.append(snippet)
            total_length += len(snippet)
        
        return '\n'.join(context_parts)
    
    def _generate_simple_answer(
        self, 
        question: str, 
        context: str, 
        search_results: List[Dict[str, Any]], 
        lang: str
    ) -> str:
        """Generate simple extractive answer"""
        # For now, provide a structured response based on search results
        # This could be enhanced with actual LLM integration
        
        if not search_results:
            return "No relevant information found."
        
        # Get top result
        top_result = search_results[0]
        
        # Create structured answer
        if lang == 'sv':
            answer = f"Baserat på informationen från {top_result['source']}:\n\n"
            answer += f"{top_result['text'][:300]}..."
            if len(search_results) > 1:
                answer += f"\n\nRelaterad information finns också från {search_results[1]['source']} och andra källor."
        else:
            answer = f"Based on information from {top_result['source']}:\n\n"
            answer += f"{top_result['text'][:300]}..."
            if len(search_results) > 1:
                answer += f"\n\nRelated information is also available from {search_results[1]['source']} and other sources."
        
        return answer
    
    def _build_citations(self, search_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Build citation list from search results"""
        citations = []
        
        for i, result in enumerate(search_results):
            citations.append({
                'id': i + 1,
                'article_id': result['article_id'],
                'title': result['title'],
                'url': result['url'],
                'source': result['source'],
                'published_at': result['published_at'].isoformat() if result['published_at'] else None,
                'relevance_score': result.get('final_score', 0)
            })
        
        return citations
    
    def _estimate_confidence(self, search_results: List[Dict[str, Any]]) -> float:
        """Estimate confidence in the answer"""
        if not search_results:
            return 0.0
        
        # Simple heuristic based on top result score and result count
        top_score = search_results[0].get('final_score', 0)
        result_count = len(search_results)
        
        # Normalize top score
        confidence = min(1.0, top_score)
        
        # Boost confidence if multiple relevant results
        if result_count >= 3 and top_score > 0.5:
            confidence = min(1.0, confidence * 1.2)
        
        return confidence


# Global instances
rag_search_engine = RAGSearchEngine()
answer_generator = AnswerGenerator()