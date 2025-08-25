#!/usr/bin/env python3
"""
RAG (Retrieval-Augmented Generation) Engine for Q&A functionality
"""

import logging
from typing import List, Dict, Any, Optional
from sentence_transformers import SentenceTransformer
import re
from openai import OpenAI

from .vec.weaviate_client import weaviate_manager
from .config import settings

logger = logging.getLogger(__name__)

class RAGEngine:
    """RAG engine for answering questions using retrieved article chunks"""
    
    def __init__(self):
        self.model = None
        self.max_context_chunks = 10
        self.min_relevance_score = 0.3
        self.openai_client = None
        self._setup_openai()
    
    def ensure_model(self) -> SentenceTransformer:
        """Load sentence transformer model"""
        if self.model is None:
            logger.info("Loading sentence transformer model for RAG...")
            self.model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("RAG model loaded successfully")
        return self.model
    
    def _setup_openai(self):
        """Setup OpenAI client if API key is available"""
        if settings.openai_api_key:
            try:
                self.openai_client = OpenAI(api_key=settings.openai_api_key)
                logger.info("OpenAI client initialized")
            except Exception as e:
                logger.warning(f"Failed to setup OpenAI: {e}")
                self.openai_client = None
        else:
            logger.info("No OpenAI API key provided, using extractive approach")
    
    def retrieve_relevant_chunks(
        self,
        question: str,
        max_chunks: int = 10,
        alpha: float = 0.7,
        lang: Optional[str] = None,
        freshness_days: Optional[int] = None,
        min_score: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant chunks for a question using hybrid search
        
        Args:
            question: User question
            max_chunks: Maximum number of chunks to retrieve
            alpha: Hybrid search balance (0=BM25 only, 1=vector only)
            lang: Language filter
            freshness_days: Only articles from last N days
            min_score: Minimum article score filter
            
        Returns:
            List of relevant chunks with metadata
        """
        
        # Generate embedding for question
        model = self.ensure_model()
        question_vector = model.encode(question).astype('float32').tolist()
        
        # Perform hybrid search
        chunks = weaviate_manager.hybrid_search(
            query=question,
            vector=question_vector,
            limit=max_chunks,
            alpha=alpha,
            lang=lang,
            freshness_days=freshness_days,
            min_score=min_score
        )
        
        # Filter by relevance score
        relevant_chunks = [
            chunk for chunk in chunks 
            if chunk['search_score'] >= self.min_relevance_score
        ]
        
        logger.info(f"Retrieved {len(relevant_chunks)} relevant chunks for question: {question[:50]}...")
        return relevant_chunks
    
    def format_context(self, chunks: List[Dict[str, Any]]) -> str:
        """
        Format retrieved chunks into context for answer generation
        
        Args:
            chunks: List of retrieved chunks
            
        Returns:
            Formatted context string
        """
        if not chunks:
            return "No relevant context found."
        
        context_parts = []
        seen_articles = set()
        
        for i, chunk in enumerate(chunks):
            # Add source info only once per article
            article_id = chunk['article_id']
            if article_id not in seen_articles:
                context_parts.append(f"\nSource {len(seen_articles)+1}: [{chunk['source']}] {chunk['title']}")
                context_parts.append(f"Published: {chunk['published_at']}")
                context_parts.append(f"URL: {chunk['url']}")
                seen_articles.add(article_id)
            
            # Add chunk content
            context_parts.append(f"\nChunk {i+1}: {chunk['text']}")
        
        return "\n".join(context_parts)
    
    def generate_answer_with_openai(
        self,
        question: str,
        chunks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate answer using OpenAI GPT model
        
        Args:
            question: User question
            chunks: Retrieved context chunks
            
        Returns:
            Dictionary with answer and metadata
        """
        
        if not chunks:
            return {
                'answer': "I couldn't find any relevant information to answer your question.",
                'confidence': 0.0,
                'sources': [],
                'chunks_used': 0,
                'generation_method': 'none'
            }
        
        if not self.openai_client:
            # Fallback to extractive method
            return self._generate_extractive_answer(question, chunks)
        
        try:
            # Build context from chunks
            context_parts = []
            sources = []
            
            for i, chunk in enumerate(chunks[:self.max_context_chunks]):
                context_parts.append(f"Source {i+1}: [{chunk['source']}] {chunk['title']}")
                context_parts.append(f"Content: {chunk['text']}")
                
                source_info = {
                    'title': chunk['title'],
                    'source': chunk['source'],
                    'url': chunk['url'],
                    'published_at': chunk['published_at'],
                    'relevance_score': chunk['search_score']
                }
                if source_info not in sources:
                    sources.append(source_info)
            
            context = "\n\n".join(context_parts)
            
            # Create prompt for OpenAI
            prompt = f"""You are a helpful assistant that answers questions based on provided sources. 
Please answer the following question using only the information from the sources below. 
If the sources don't contain enough information to fully answer the question, say so.
Be concise but comprehensive, and cite relevant sources in your answer.

Question: {question}

Sources:
{context}

Answer:"""

            # Call OpenAI API
            response = self.openai_client.chat.completions.create(
                model=settings.openai_model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that answers questions based on provided sources. Always be factual and cite your sources."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=settings.openai_max_tokens,
                temperature=settings.openai_temperature,
            )
            
            answer = response.choices[0].message.content.strip()
            
            # Estimate confidence based on response length and source count
            confidence = min(0.95, 0.6 + (len(sources) * 0.1) + (len(answer) / 1000 * 0.2))
            
            return {
                'answer': answer,
                'confidence': round(confidence, 2),
                'sources': sources[:5],  # Limit to 5 sources
                'chunks_used': len(chunks[:self.max_context_chunks]),
                'generation_method': 'openai_gpt'
            }
            
        except Exception as e:
            logger.error(f"OpenAI generation error: {e}")
            # Fallback to extractive method
            return self._generate_extractive_answer(question, chunks)
    
    def _generate_extractive_answer(
        self,
        question: str,
        chunks: List[Dict[str, Any]],
        max_answer_length: int = 500
    ) -> Dict[str, Any]:
        """
        Generate answer using a simple extractive approach
        (In production, this would call an LLM like GPT-4 or Claude)
        
        Args:
            question: User question
            chunks: Retrieved context chunks
            max_answer_length: Maximum answer length
            
        Returns:
            Dictionary with answer and metadata
        """
        
        if not chunks:
            return {
                'answer': "I couldn't find any relevant information to answer your question.",
                'confidence': 0.0,
                'sources': [],
                'chunks_used': 0
            }
        
        # Simple extractive approach - find most relevant sentences
        question_lower = question.lower()
        question_words = set(re.findall(r'\w+', question_lower))
        
        relevant_sentences = []
        sources = []
        
        for chunk in chunks[:self.max_context_chunks]:
            sentences = self._split_into_sentences(chunk['text'])
            
            for sentence in sentences:
                if len(sentence) < 20:  # Skip very short sentences
                    continue
                    
                # Simple relevance scoring based on word overlap
                sentence_words = set(re.findall(r'\w+', sentence.lower()))
                overlap = len(question_words.intersection(sentence_words))
                
                if overlap > 0:
                    relevance_score = overlap / len(question_words)
                    relevant_sentences.append({
                        'text': sentence,
                        'score': relevance_score,
                        'chunk': chunk
                    })
        
        # Sort by relevance and take the best sentences
        relevant_sentences.sort(key=lambda x: x['score'], reverse=True)
        
        # Build answer from top sentences
        answer_parts = []
        current_length = 0
        used_chunks = set()
        
        for sentence_data in relevant_sentences:
            sentence = sentence_data['text']
            chunk = sentence_data['chunk']
            
            if current_length + len(sentence) > max_answer_length:
                break
                
            answer_parts.append(sentence)
            current_length += len(sentence)
            used_chunks.add(chunk['article_id'])
            
            # Add source info
            source_info = {
                'title': chunk['title'],
                'source': chunk['source'],
                'url': chunk['url'],
                'published_at': chunk['published_at'],
                'relevance_score': chunk['search_score']
            }
            if source_info not in sources:
                sources.append(source_info)
        
        # Generate final answer
        if not answer_parts:
            answer = "I found some relevant information but couldn't extract a clear answer. Please check the sources below for more details."
            confidence = 0.2
        else:
            answer = " ".join(answer_parts)
            confidence = min(0.9, len(used_chunks) * 0.2 + max(s['score'] for s in relevant_sentences[:3]))
        
        return {
            'answer': answer,
            'confidence': round(confidence, 2),
            'sources': sources[:5],  # Limit to 5 sources
            'chunks_used': len(used_chunks),
            'generation_method': 'extractive'
        }
    
    def generate_answer(
        self,
        question: str,
        chunks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Main answer generation method - uses OpenAI if available, else extractive
        
        Args:
            question: User question
            chunks: Retrieved context chunks
            
        Returns:
            Dictionary with answer and metadata
        """
        
        if self.openai_client and settings.openai_api_key:
            return self.generate_answer_with_openai(question, chunks)
        else:
            return self._generate_extractive_answer(question, chunks)
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences using simple regex"""
        # Simple sentence splitting
        sentences = re.split(r'[.!?]+', text)
        return [s.strip() for s in sentences if len(s.strip()) > 10]
    
    def ask_question(
        self,
        question: str,
        max_chunks: int = 10,
        alpha: float = 0.7,
        lang: Optional[str] = None,
        freshness_days: Optional[int] = None,
        min_score: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Main Q&A function - retrieve context and generate answer
        
        Args:
            question: User question
            max_chunks: Maximum chunks to retrieve
            alpha: Hybrid search balance
            lang: Language filter
            freshness_days: Freshness filter
            min_score: Score filter
            
        Returns:
            Complete Q&A response with answer, sources, and metadata
        """
        
        logger.info(f"Processing question: {question}")
        
        # Retrieve relevant chunks
        chunks = self.retrieve_relevant_chunks(
            question=question,
            max_chunks=max_chunks,
            alpha=alpha,
            lang=lang,
            freshness_days=freshness_days,
            min_score=min_score
        )
        
        # Generate answer
        result = self.generate_answer(question, chunks)
        
        # Add retrieval metadata
        result.update({
            'question': question,
            'retrieval_method': 'hybrid_search',
            'total_chunks_retrieved': len(chunks),
            'search_params': {
                'alpha': alpha,
                'lang': lang,
                'freshness_days': freshness_days,
                'min_score': min_score
            }
        })
        
        logger.info(f"Generated answer with confidence {result['confidence']} using {result['chunks_used']} chunks")
        return result

# Global RAG engine instance
rag_engine = RAGEngine()