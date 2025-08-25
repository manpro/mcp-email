"""Weaviate client and schema management"""
import weaviate
import weaviate.classes.config as wvc
import weaviate.classes.query as wvq
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import logging
import os

from ..config import settings

logger = logging.getLogger(__name__)


class WeaviateManager:
    """Manages Weaviate client and schema operations"""
    
    def __init__(self):
        self.client = None
        self.collection = None
        self._connect()
    
    def _connect(self):
        """Initialize Weaviate client connection"""
        try:
            weaviate_url = getattr(settings, 'weaviate_url', 'http://weaviate:8080')
            
            # Parse URL to get host and port
            from urllib.parse import urlparse
            parsed = urlparse(weaviate_url)
            host = parsed.hostname or 'weaviate'
            port = parsed.port or 8080
            
            self.client = weaviate.connect_to_custom(
                http_host=host,
                http_port=port,
                http_secure=False,
                grpc_host=host,
                grpc_port=50051,
                grpc_secure=False
            )
            
            # Create collection if it doesn't exist
            self._setup_collection()
            
            logger.info(f"Connected to Weaviate at {weaviate_url}")
            
        except Exception as e:
            logger.error(f"Failed to connect to Weaviate: {e}")
            raise
    
    def _setup_collection(self):
        """Setup ArticleChunk collection with proper schema"""
        collection_name = "ArticleChunk"
        
        try:
            # Check if collection exists
            if self.client.collections.exists(collection_name):
                self.collection = self.client.collections.get(collection_name)
                logger.info(f"Using existing collection: {collection_name}")
                return
            
            # Create collection with schema
            self.collection = self.client.collections.create(
                name=collection_name,
                description="Article chunks for semantic search",
                properties=[
                    wvc.Property(
                        name="articleId",
                        data_type=wvc.DataType.TEXT,
                        description="ID of the parent article"
                    ),
                    wvc.Property(
                        name="chunkIndex", 
                        data_type=wvc.DataType.INT,
                        description="Index of chunk within article"
                    ),
                    wvc.Property(
                        name="text",
                        data_type=wvc.DataType.TEXT,
                        description="Chunk text content"
                    ),
                    wvc.Property(
                        name="source",
                        data_type=wvc.DataType.TEXT,
                        description="Source of the article"
                    ),
                    wvc.Property(
                        name="lang",
                        data_type=wvc.DataType.TEXT,
                        description="Language code"
                    ),
                    wvc.Property(
                        name="publishedAt",
                        data_type=wvc.DataType.DATE,
                        description="Article publication date"
                    ),
                    wvc.Property(
                        name="score",
                        data_type=wvc.DataType.INT,
                        description="Article rule-based score"
                    ),
                    wvc.Property(
                        name="nearDupId",
                        data_type=wvc.DataType.TEXT,
                        description="Near-duplicate article ID (optional)"
                    ),
                    wvc.Property(
                        name="title",
                        data_type=wvc.DataType.TEXT,
                        description="Article title"
                    ),
                    wvc.Property(
                        name="url",
                        data_type=wvc.DataType.TEXT,
                        description="Article URL"
                    ),
                    wvc.Property(
                        name="tokenCount",
                        data_type=wvc.DataType.INT,
                        description="Number of tokens in chunk"
                    )
                ],
                vectorizer_config=wvc.Configure.Vectorizer.none(),  # Client-side vectorization
                vector_index_config=wvc.Configure.VectorIndex.hnsw(
                    ef_construction=128,
                    max_connections=64,
                    distance_metric=wvc.VectorDistances.COSINE
                )
            )
            
            logger.info(f"Created collection: {collection_name}")
            
        except Exception as e:
            logger.error(f"Error setting up Weaviate collection: {e}")
            raise
    
    def upsert_chunks(self, chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Upsert article chunks to Weaviate
        
        Args:
            chunks: List of chunk dictionaries with keys:
                - article_id: int
                - chunk_ix: int  
                - text: str
                - vector: List[float] (384-dimensional)
                - title: str
                - url: str
                - source: str
                - lang: str
                - published_at: datetime
                - score: int
                - near_dup_id: Optional[str]
                - token_count: int
        
        Returns:
            Dict with success count and errors
        """
        if not chunks:
            return {'inserted': 0, 'errors': []}
        
        success_count = 0
        errors = []
        
        try:
            with self.collection.batch.dynamic() as batch:
                for chunk in chunks:
                    try:
                        # Prepare properties
                        properties = {
                            "articleId": str(chunk['article_id']),
                            "chunkIndex": chunk['chunk_ix'],
                            "text": chunk['text'],
                            "title": chunk['title'],
                            "url": chunk['url'],
                            "source": chunk['source'],
                            "lang": chunk.get('lang', 'en'),
                            "publishedAt": chunk['published_at'],
                            "score": chunk.get('score', 0),
                            "tokenCount": chunk.get('token_count', 0)
                        }
                        
                        # Add nearDupId if present
                        if chunk.get('near_dup_id'):
                            properties["nearDupId"] = str(chunk['near_dup_id'])
                        
                        # Add to batch with vector
                        batch.add_object(
                            properties=properties,
                            vector=chunk['vector']
                        )
                        
                        success_count += 1
                        
                    except Exception as e:
                        error_msg = f"Error adding chunk {chunk.get('article_id', 'unknown')}:{chunk.get('chunk_ix', 'unknown')}: {e}"
                        errors.append(error_msg)
                        logger.error(error_msg)
            
            logger.info(f"Upserted {success_count} chunks to Weaviate")
            
        except Exception as e:
            error_msg = f"Batch upsert error: {e}"
            errors.append(error_msg)
            logger.error(error_msg)
        
        return {
            'inserted': success_count,
            'errors': errors
        }
    
    def hybrid_search(
        self,
        query: str,
        vector: List[float],
        limit: int = 30,
        alpha: float = 0.7,
        lang: Optional[str] = None,
        freshness_days: Optional[int] = None,
        min_score: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Perform hybrid search combining vector similarity and BM25
        
        Args:
            query: Text query
            vector: Query vector (384-dimensional)
            limit: Maximum results
            alpha: Hybrid search alpha (0=BM25 only, 1=vector only)
            lang: Language filter
            freshness_days: Only articles from last N days
            min_score: Minimum article score
        
        Returns:
            List of search results with scores and metadata
        """
        try:
            # Build where filter
            where_conditions = []
            
            if lang:
                where_conditions.append(
                    wvq.Filter.by_property("lang").equal(lang)
                )
            
            if freshness_days:
                cutoff_date = datetime.now(timezone.utc).replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
                cutoff_date = cutoff_date.replace(
                    day=cutoff_date.day - freshness_days
                )
                where_conditions.append(
                    wvq.Filter.by_property("publishedAt").greater_than(cutoff_date)
                )
            
            if min_score is not None:
                where_conditions.append(
                    wvq.Filter.by_property("score").greater_or_equal(min_score)
                )
            
            # Combine conditions
            where_filter = None
            if where_conditions:
                if len(where_conditions) == 1:
                    where_filter = where_conditions[0]
                else:
                    where_filter = wvq.Filter.all_of(where_conditions)
            
            # Perform hybrid search
            if where_filter:
                response = self.collection.query.hybrid(
                    query=query,
                    vector=vector,
                    alpha=alpha,
                    limit=limit,
                    return_metadata=wvq.MetadataQuery(score=True, explain_score=True)
                ).where(where_filter)
            else:
                response = self.collection.query.hybrid(
                    query=query,
                    vector=vector,
                    alpha=alpha,
                    limit=limit,
                    return_metadata=wvq.MetadataQuery(score=True, explain_score=True)
                )
            
            # Format results
            results = []
            for obj in response.objects:
                results.append({
                    'article_id': int(obj.properties['articleId']),
                    'chunk_index': obj.properties['chunkIndex'],
                    'text': obj.properties['text'],
                    'title': obj.properties['title'],
                    'url': obj.properties['url'],
                    'source': obj.properties['source'],
                    'lang': obj.properties.get('lang', 'en'),
                    'published_at': obj.properties['publishedAt'],
                    'score': obj.properties.get('score', 0),
                    'search_score': obj.metadata.score,
                    'near_dup_id': obj.properties.get('nearDupId'),
                    'token_count': obj.properties.get('tokenCount', 0)
                })
            
            logger.info(f"Hybrid search returned {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"Hybrid search error: {e}")
            return []
    
    def delete_chunks_for_article(self, article_id: int) -> bool:
        """Delete all chunks for a specific article"""
        try:
            # Delete by article ID
            self.collection.data.delete_many(
                where=wvq.Filter.by_property("articleId").equal(str(article_id))
            )
            
            logger.info(f"Deleted chunks for article {article_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting chunks for article {article_id}: {e}")
            return False
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the collection"""
        try:
            # Get object count
            response = self.collection.aggregate.over_all(
                total_count=True
            )
            
            total_count = response.total_count
            
            return {
                'total_chunks': total_count,
                'collection_name': self.collection.name
            }
            
        except Exception as e:
            logger.error(f"Error getting collection stats: {e}")
            return {'total_chunks': 0, 'error': str(e)}
    
    def close(self):
        """Close the Weaviate client connection"""
        if self.client:
            self.client.close()
            logger.info("Closed Weaviate connection")


# Global instance
weaviate_manager = WeaviateManager()