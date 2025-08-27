"""
Vector Search Service using Weaviate

Implements semantic search, document embeddings, and RAG (Retrieval Augmented Generation)
capabilities for articles using Weaviate vector database.
"""

import logging
import weaviate
import asyncio
from typing import Dict, List, Optional, Any, Union, Tuple
from datetime import datetime, timedelta
import hashlib
import json
from dataclasses import dataclass
from sqlalchemy.orm import Session
import openai
from sentence_transformers import SentenceTransformer
import numpy as np

from ..store import Article, SearchQuery, UserProfile
from ..config import settings

logger = logging.getLogger(__name__)

@dataclass
class SearchResult:
    """Search result with semantic similarity"""
    article: Article
    score: float
    similarity: float
    distance: float
    explanation: str
    embedding_used: str

@dataclass
class VectorSearchQuery:
    """Vector search query configuration"""
    query: str
    limit: int = 10
    min_score: Optional[float] = None
    date_filter: Optional[Tuple[datetime, datetime]] = None
    source_filter: Optional[List[str]] = None
    semantic_weight: float = 0.7
    keyword_weight: float = 0.3
    include_explanation: bool = True

class WeaviateVectorSearch:
    """Weaviate-based vector search service"""
    
    def __init__(self, db: Session):
        self.db = db
        self.client = None
        self.embedding_model = None
        
        # Weaviate configuration
        self.weaviate_url = getattr(settings, 'weaviate_url', 'http://localhost:8080')
        self.weaviate_api_key = getattr(settings, 'weaviate_api_key', None)
        
        # Embedding model configuration
        self.embedding_model_name = getattr(settings, 'embedding_model', 'all-MiniLM-L6-v2')
        
        # Schema configuration
        self.article_class = "Article"
        self.embedding_dimensions = 384  # for all-MiniLM-L6-v2
        
        # Search parameters
        self.search_timeout = 30
        self.max_batch_size = 100
    
    async def initialize(self):
        """Initialize Weaviate client and embedding model"""
        try:
            # Initialize Weaviate client
            auth_config = None
            if self.weaviate_api_key:
                auth_config = weaviate.AuthApiKey(api_key=self.weaviate_api_key)
            
            self.client = weaviate.Client(
                url=self.weaviate_url,
                auth_client_secret=auth_config,
                timeout_config=weaviate.classes.config.Timeout(
                    init=30,
                    query=self.search_timeout,
                    insert=30
                )
            )
            
            # Test connection
            if not self.client.is_ready():
                raise Exception("Weaviate is not ready")
            
            # Initialize embedding model
            self.embedding_model = SentenceTransformer(self.embedding_model_name)
            
            # Create schema if it doesn't exist
            await self._ensure_schema()
            
            logger.info(f"Weaviate vector search initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Weaviate: {e}")
            return False
    
    async def _ensure_schema(self):
        """Ensure the Article schema exists in Weaviate"""
        try:
            # Check if class exists
            if self.client.schema.contains({'class': self.article_class}):
                return
            
            # Define article schema
            article_schema = {
                "class": self.article_class,
                "description": "RSS Intelligence article with semantic embeddings",
                "vectorizer": "none",  # We'll provide our own vectors
                "properties": [
                    {
                        "name": "articleId",
                        "dataType": ["int"],
                        "description": "Database article ID"
                    },
                    {
                        "name": "title",
                        "dataType": ["text"],
                        "description": "Article title"
                    },
                    {
                        "name": "content",
                        "dataType": ["text"],
                        "description": "Article content"
                    },
                    {
                        "name": "fullContent",
                        "dataType": ["text"],
                        "description": "Full extracted article content"
                    },
                    {
                        "name": "source",
                        "dataType": ["string"],
                        "description": "Article source"
                    },
                    {
                        "name": "url",
                        "dataType": ["string"],
                        "description": "Article URL"
                    },
                    {
                        "name": "publishedAt",
                        "dataType": ["date"],
                        "description": "Publication date"
                    },
                    {
                        "name": "scoreTotal",
                        "dataType": ["number"],
                        "description": "Total article score"
                    },
                    {
                        "name": "topics",
                        "dataType": ["string[]"],
                        "description": "Article topics"
                    },
                    {
                        "name": "contentHash",
                        "dataType": ["string"],
                        "description": "Content hash for deduplication"
                    },
                    {
                        "name": "embeddingMethod",
                        "dataType": ["string"],
                        "description": "Embedding generation method"
                    },
                    {
                        "name": "indexedAt",
                        "dataType": ["date"],
                        "description": "When article was indexed"
                    }
                ]
            }
            
            # Create schema
            self.client.schema.create_class(article_schema)
            logger.info(f"Created Weaviate schema for {self.article_class}")
            
        except Exception as e:
            logger.error(f"Failed to ensure schema: {e}")
            raise
    
    def _generate_embeddings(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings for a list of texts"""
        try:
            if not self.embedding_model:
                raise Exception("Embedding model not initialized")
            
            embeddings = self.embedding_model.encode(texts, convert_to_numpy=True)
            return embeddings
            
        except Exception as e:
            logger.error(f"Failed to generate embeddings: {e}")
            raise
    
    async def index_article(self, article: Article, force_reindex: bool = False) -> bool:
        """
        Index a single article in Weaviate
        
        Args:
            article: Article object to index
            force_reindex: Whether to reindex if already exists
            
        Returns:
            True if successfully indexed
        """
        try:
            if not self.client or not self.embedding_model:
                await self.initialize()
            
            # Check if already indexed
            if not force_reindex:
                existing = self._get_article_by_id(article.id)
                if existing:
                    logger.debug(f"Article {article.id} already indexed")
                    return True
            
            # Prepare content for embedding
            content_for_embedding = self._prepare_content_for_embedding(article)
            
            # Generate embedding
            embedding = self._generate_embeddings([content_for_embedding])[0]
            
            # Prepare data object
            data_object = {
                "articleId": article.id,
                "title": article.title or "",
                "content": article.content or "",
                "fullContent": article.full_content or "",
                "source": article.source or "",
                "url": article.url or "",
                "publishedAt": article.published_at.isoformat() if article.published_at else None,
                "scoreTotal": float(article.score_total or 0),
                "topics": article.topics or [],
                "contentHash": article.content_hash or "",
                "embeddingMethod": self.embedding_model_name,
                "indexedAt": datetime.now().isoformat()
            }
            
            # Add to Weaviate
            uuid = self.client.data_object.create(
                data_object=data_object,
                class_name=self.article_class,
                vector=embedding.tolist()
            )
            
            logger.debug(f"Indexed article {article.id} with UUID {uuid}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to index article {article.id}: {e}")
            return False
    
    async def index_articles_batch(self, articles: List[Article], batch_size: int = 50) -> Dict[str, int]:
        """
        Index multiple articles in batches
        
        Args:
            articles: List of articles to index
            batch_size: Number of articles to process at once
            
        Returns:
            Dictionary with indexing statistics
        """
        stats = {"indexed": 0, "skipped": 0, "failed": 0}
        
        try:
            if not self.client or not self.embedding_model:
                await self.initialize()
            
            # Process in batches
            for i in range(0, len(articles), batch_size):
                batch = articles[i:i + batch_size]
                
                with self.client.batch as batch_client:
                    batch_client.batch_size = len(batch)
                    
                    for article in batch:
                        try:
                            # Prepare content and generate embedding
                            content_for_embedding = self._prepare_content_for_embedding(article)
                            embedding = self._generate_embeddings([content_for_embedding])[0]
                            
                            # Prepare data object
                            data_object = {
                                "articleId": article.id,
                                "title": article.title or "",
                                "content": article.content or "",
                                "fullContent": article.full_content or "",
                                "source": article.source or "",
                                "url": article.url or "",
                                "publishedAt": article.published_at.isoformat() if article.published_at else None,
                                "scoreTotal": float(article.score_total or 0),
                                "topics": article.topics or [],
                                "contentHash": article.content_hash or "",
                                "embeddingMethod": self.embedding_model_name,
                                "indexedAt": datetime.now().isoformat()
                            }
                            
                            # Add to batch
                            batch_client.add_data_object(
                                data_object=data_object,
                                class_name=self.article_class,
                                vector=embedding.tolist()
                            )
                            
                            stats["indexed"] += 1
                            
                        except Exception as e:
                            logger.error(f"Failed to prepare article {article.id} for batch: {e}")
                            stats["failed"] += 1
                
                logger.info(f"Processed batch {i//batch_size + 1}, indexed {stats['indexed']} articles so far")
                
                # Small delay between batches to avoid overwhelming Weaviate
                await asyncio.sleep(0.1)
            
            logger.info(f"Batch indexing completed: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Batch indexing failed: {e}")
            stats["failed"] += len(articles) - stats["indexed"]
            return stats
    
    def _prepare_content_for_embedding(self, article: Article) -> str:
        """Prepare article content for embedding generation"""
        # Combine title and content for better semantic representation
        content_parts = []
        
        if article.title:
            content_parts.append(article.title)
        
        # Prefer full content if available, otherwise use summary
        if article.full_content and len(article.full_content) > 100:
            # Truncate very long content to avoid embedding limits
            content = article.full_content[:4000]
            content_parts.append(content)
        elif article.content:
            content_parts.append(article.content)
        
        # Add topics if available
        if article.topics:
            topics_str = " ".join(article.topics)
            content_parts.append(f"Topics: {topics_str}")
        
        return " | ".join(content_parts)
    
    async def semantic_search(self, query: VectorSearchQuery) -> List[SearchResult]:
        """
        Perform semantic search using vector similarity
        
        Args:
            query: Vector search query configuration
            
        Returns:
            List of search results with similarity scores
        """
        try:
            if not self.client or not self.embedding_model:
                await self.initialize()
            
            # Generate query embedding
            query_embedding = self._generate_embeddings([query.query])[0]
            
            # Build Weaviate query
            where_filter = self._build_where_filter(query)
            
            # Perform vector search
            result = (
                self.client.query
                .get(self.article_class, [
                    "articleId", "title", "content", "fullContent", "source", 
                    "url", "publishedAt", "scoreTotal", "topics", "contentHash"
                ])
                .with_near_vector({
                    "vector": query_embedding.tolist(),
                    "certainty": query.min_score or 0.5
                })
                .with_where(where_filter)
                .with_limit(query.limit)
                .with_additional(["certainty", "distance"])
                .do()
            )
            
            # Process results
            search_results = []
            articles_data = result.get("data", {}).get("Get", {}).get(self.article_class, [])
            
            for item in articles_data:
                try:
                    # Get article from database
                    article_id = item["articleId"]
                    article = self.db.query(Article).filter(Article.id == article_id).first()
                    
                    if not article:
                        continue
                    
                    # Extract similarity metrics
                    additional = item.get("_additional", {})
                    certainty = additional.get("certainty", 0.0)
                    distance = additional.get("distance", 1.0)
                    
                    # Calculate combined score
                    semantic_score = certainty * query.semantic_weight
                    keyword_score = self._calculate_keyword_score(query.query, article) * query.keyword_weight
                    combined_score = semantic_score + keyword_score
                    
                    # Generate explanation if requested
                    explanation = ""
                    if query.include_explanation:
                        explanation = self._generate_search_explanation(
                            query.query, article, certainty, keyword_score
                        )
                    
                    search_result = SearchResult(
                        article=article,
                        score=combined_score,
                        similarity=certainty,
                        distance=distance,
                        explanation=explanation,
                        embedding_used=self.embedding_model_name
                    )
                    
                    search_results.append(search_result)
                    
                except Exception as e:
                    logger.error(f"Error processing search result: {e}")
                    continue
            
            # Sort by combined score
            search_results.sort(key=lambda x: x.score, reverse=True)
            
            logger.info(f"Semantic search for '{query.query}' returned {len(search_results)} results")
            return search_results
            
        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            return []
    
    def _build_where_filter(self, query: VectorSearchQuery) -> Optional[Dict]:
        """Build Weaviate where filter from search query"""
        filters = []
        
        # Date filter
        if query.date_filter:
            start_date, end_date = query.date_filter
            filters.append({
                "path": ["publishedAt"],
                "operator": "GreaterThanEqual",
                "valueDate": start_date.isoformat()
            })
            filters.append({
                "path": ["publishedAt"],
                "operator": "LessThanEqual", 
                "valueDate": end_date.isoformat()
            })
        
        # Source filter
        if query.source_filter:
            source_conditions = []
            for source in query.source_filter:
                source_conditions.append({
                    "path": ["source"],
                    "operator": "Equal",
                    "valueString": source
                })
            
            if len(source_conditions) == 1:
                filters.append(source_conditions[0])
            else:
                filters.append({
                    "operator": "Or",
                    "operands": source_conditions
                })
        
        # Combine filters
        if not filters:
            return None
        elif len(filters) == 1:
            return filters[0]
        else:
            return {
                "operator": "And",
                "operands": filters
            }
    
    def _calculate_keyword_score(self, query: str, article: Article) -> float:
        """Calculate keyword-based relevance score"""
        try:
            query_lower = query.lower()
            query_words = set(query_lower.split())
            
            # Check title
            title_score = 0.0
            if article.title:
                title_lower = article.title.lower()
                title_words = set(title_lower.split())
                title_matches = len(query_words.intersection(title_words))
                title_score = title_matches / len(query_words) if query_words else 0.0
            
            # Check content
            content_score = 0.0
            content_text = article.full_content or article.content or ""
            if content_text:
                content_lower = content_text.lower()
                content_matches = sum(1 for word in query_words if word in content_lower)
                content_score = content_matches / len(query_words) if query_words else 0.0
            
            # Weighted combination
            return title_score * 0.6 + content_score * 0.4
            
        except Exception as e:
            logger.error(f"Error calculating keyword score: {e}")
            return 0.0
    
    def _generate_search_explanation(self, query: str, article: Article, 
                                   similarity: float, keyword_score: float) -> str:
        """Generate human-readable explanation for search result"""
        explanations = []
        
        if similarity > 0.8:
            explanations.append("Strong semantic similarity")
        elif similarity > 0.6:
            explanations.append("Good semantic match")
        else:
            explanations.append("Relevant content match")
        
        if keyword_score > 0.5:
            explanations.append("Contains query keywords")
        
        if article.score_total and article.score_total > 80:
            explanations.append("High-quality article")
        
        return " • ".join(explanations)
    
    def _get_article_by_id(self, article_id: int) -> Optional[Dict]:
        """Check if article is already indexed in Weaviate"""
        try:
            result = (
                self.client.query
                .get(self.article_class, ["articleId"])
                .with_where({
                    "path": ["articleId"],
                    "operator": "Equal",
                    "valueInt": article_id
                })
                .with_limit(1)
                .do()
            )
            
            articles = result.get("data", {}).get("Get", {}).get(self.article_class, [])
            return articles[0] if articles else None
            
        except Exception as e:
            logger.debug(f"Error checking existing article {article_id}: {e}")
            return None
    
    async def get_similar_articles(self, article: Article, limit: int = 10) -> List[SearchResult]:
        """Find articles similar to the given article"""
        try:
            # Use article content as query
            query_text = self._prepare_content_for_embedding(article)
            
            query = VectorSearchQuery(
                query=query_text,
                limit=limit + 1,  # +1 to exclude the original article
                include_explanation=True
            )
            
            results = await self.semantic_search(query)
            
            # Filter out the original article
            filtered_results = [r for r in results if r.article.id != article.id]
            
            return filtered_results[:limit]
            
        except Exception as e:
            logger.error(f"Error finding similar articles: {e}")
            return []
    
    async def get_search_suggestions(self, partial_query: str, limit: int = 5) -> List[str]:
        """Get search suggestions based on partial query"""
        try:
            if len(partial_query) < 2:
                return []
            
            # Simple implementation - could be enhanced with more sophisticated methods
            query = VectorSearchQuery(
                query=partial_query,
                limit=limit * 2,
                include_explanation=False
            )
            
            results = await self.semantic_search(query)
            
            # Extract unique topics and keywords
            suggestions = set()
            for result in results:
                if result.article.topics:
                    suggestions.update(result.article.topics)
                
                # Extract key phrases from titles
                if result.article.title:
                    title_words = result.article.title.split()
                    for i in range(len(title_words) - 1):
                        phrase = " ".join(title_words[i:i+2])
                        if partial_query.lower() in phrase.lower():
                            suggestions.add(phrase)
            
            return sorted(list(suggestions))[:limit]
            
        except Exception as e:
            logger.error(f"Error generating search suggestions: {e}")
            return []
    
    async def cleanup_old_articles(self, days_old: int = 90) -> int:
        """Remove old articles from Weaviate index"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_old)
            
            # Find old articles
            result = (
                self.client.query
                .get(self.article_class, ["articleId"])
                .with_where({
                    "path": ["publishedAt"],
                    "operator": "LessThan",
                    "valueDate": cutoff_date.isoformat()
                })
                .do()
            )
            
            articles_to_delete = result.get("data", {}).get("Get", {}).get(self.article_class, [])
            
            # Delete old articles
            deleted_count = 0
            for article_data in articles_to_delete:
                try:
                    self.client.data_object.delete(
                        class_name=self.article_class,
                        where={
                            "path": ["articleId"],
                            "operator": "Equal",
                            "valueInt": article_data["articleId"]
                        }
                    )
                    deleted_count += 1
                except Exception as e:
                    logger.error(f"Failed to delete article: {e}")
            
            logger.info(f"Cleaned up {deleted_count} old articles from Weaviate")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
            return 0
    
    async def get_index_stats(self) -> Dict[str, Any]:
        """Get statistics about the Weaviate index"""
        try:
            if not self.client:
                await self.initialize()
            
            # Get total count
            result = (
                self.client.query
                .aggregate(self.article_class)
                .with_meta_count()
                .do()
            )
            
            total_articles = result.get("data", {}).get("Aggregate", {}).get(self.article_class, [{}])[0].get("meta", {}).get("count", 0)
            
            # Get recent articles count (last 7 days)
            recent_date = datetime.now() - timedelta(days=7)
            recent_result = (
                self.client.query
                .aggregate(self.article_class)
                .with_meta_count()
                .with_where({
                    "path": ["indexedAt"],
                    "operator": "GreaterThan",
                    "valueDate": recent_date.isoformat()
                })
                .do()
            )
            
            recent_count = recent_result.get("data", {}).get("Aggregate", {}).get(self.article_class, [{}])[0].get("meta", {}).get("count", 0)
            
            return {
                "total_articles": total_articles,
                "recent_articles_7days": recent_count,
                "embedding_model": self.embedding_model_name,
                "embedding_dimensions": self.embedding_dimensions,
                "weaviate_url": self.weaviate_url,
                "index_status": "healthy" if self.client.is_ready() else "unhealthy"
            }
            
        except Exception as e:
            logger.error(f"Failed to get index stats: {e}")
            return {"error": str(e)}

# Global service instance
vector_search_service = None

def get_vector_search_service(db: Session) -> WeaviateVectorSearch:
    """Get or create vector search service"""
    global vector_search_service
    if not vector_search_service:
        vector_search_service = WeaviateVectorSearch(db)
    return vector_search_service