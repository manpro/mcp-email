#!/usr/bin/env python3
"""
Redis caching service for RSS Intelligence Dashboard
Provides caching for search results, ask responses, and other expensive operations
"""

import redis
import json
import hashlib
import logging
from typing import Any, Optional, Dict, List
from datetime import datetime, timedelta
from .config import settings

logger = logging.getLogger(__name__)

class CacheService:
    """Redis-based caching service"""
    
    def __init__(self):
        self.redis_client = None
        self.default_ttl = 300  # 5 minutes default TTL
        self.search_ttl = 600   # 10 minutes for search results
        self.ask_ttl = 1800     # 30 minutes for Q&A responses
        self.trends_ttl = 3600  # 1 hour for trends
        self._connect()
    
    def _connect(self):
        """Connect to Redis"""
        try:
            self.redis_client = redis.Redis(
                host=settings.redis_host,
                port=settings.redis_port,
                db=settings.redis_db,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            # Test connection
            self.redis_client.ping()
            logger.info("Redis cache service connected successfully")
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}. Caching disabled.")
            self.redis_client = None
    
    def _generate_key(self, prefix: str, data: Dict[str, Any]) -> str:
        """Generate cache key from data"""
        # Create deterministic key from sorted data
        sorted_data = json.dumps(data, sort_keys=True, ensure_ascii=True)
        hash_obj = hashlib.md5(sorted_data.encode())
        return f"{prefix}:{hash_obj.hexdigest()}"
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if not self.redis_client:
            return None
        
        try:
            value = self.redis_client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache"""
        if not self.redis_client:
            return False
        
        try:
            ttl = ttl or self.default_ttl
            serialized_value = json.dumps(value, default=str, ensure_ascii=False)
            self.redis_client.setex(key, ttl, serialized_value)
            return True
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete key from cache"""
        if not self.redis_client:
            return False
        
        try:
            self.redis_client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            return False
    
    def clear_pattern(self, pattern: str) -> int:
        """Clear keys matching pattern"""
        if not self.redis_client:
            return 0
        
        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                return self.redis_client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Cache clear pattern error: {e}")
            return 0
    
    # Search-specific caching methods
    def get_search_result(self, query: str, filters: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get cached search result"""
        key = self._generate_key("search", {"query": query, "filters": filters})
        result = self.get(key)
        if result:
            logger.info(f"Cache hit for search: {query[:30]}...")
        return result
    
    def cache_search_result(self, query: str, filters: Dict[str, Any], result: Dict[str, Any]) -> bool:
        """Cache search result"""
        key = self._generate_key("search", {"query": query, "filters": filters})
        
        # Add cache metadata
        cache_data = {
            **result,
            "_cached_at": datetime.now().isoformat(),
            "_cache_ttl": self.search_ttl
        }
        
        success = self.set(key, cache_data, self.search_ttl)
        if success:
            logger.info(f"Cached search result: {query[:30]}...")
        return success
    
    # Ask/Q&A-specific caching methods
    def get_ask_result(self, question: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get cached ask result"""
        key = self._generate_key("ask", {"question": question, "params": params})
        result = self.get(key)
        if result:
            logger.info(f"Cache hit for ask: {question[:30]}...")
        return result
    
    def cache_ask_result(self, question: str, params: Dict[str, Any], result: Dict[str, Any]) -> bool:
        """Cache ask result"""
        key = self._generate_key("ask", {"question": question, "params": params})
        
        # Add cache metadata
        cache_data = {
            **result,
            "_cached_at": datetime.now().isoformat(),
            "_cache_ttl": self.ask_ttl
        }
        
        success = self.set(key, cache_data, self.ask_ttl)
        if success:
            logger.info(f"Cached ask result: {question[:30]}...")
        return success
    
    # Intelligence-specific caching methods
    def get_trends(self, params: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
        """Get cached trends"""
        key = self._generate_key("trends", params)
        result = self.get(key)
        if result:
            logger.info("Cache hit for trends")
        return result
    
    def cache_trends(self, params: Dict[str, Any], trends: List[Dict[str, Any]]) -> bool:
        """Cache trends result"""
        key = self._generate_key("trends", params)
        
        cache_data = {
            "trends": trends,
            "total": len(trends),
            "_cached_at": datetime.now().isoformat(),
            "_cache_ttl": self.trends_ttl
        }
        
        success = self.set(key, cache_data, self.trends_ttl)
        if success:
            logger.info(f"Cached {len(trends)} trends")
        return success
    
    # Intelligence analysis caching
    def get_analysis_result(self, article_id: int, analysis_type: str) -> Optional[Dict[str, Any]]:
        """Get cached analysis result"""
        key = f"analysis:{analysis_type}:{article_id}"
        return self.get(key)
    
    def cache_analysis_result(self, article_id: int, analysis_type: str, result: Dict[str, Any]) -> bool:
        """Cache analysis result"""
        key = f"analysis:{analysis_type}:{article_id}"
        
        cache_data = {
            **result,
            "_cached_at": datetime.now().isoformat(),
            "_cache_ttl": self.default_ttl
        }
        
        return self.set(key, cache_data, self.default_ttl)
    
    # Cache management
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        if not self.redis_client:
            return {"status": "disabled", "error": "Redis not available"}
        
        try:
            info = self.redis_client.info()
            
            # Get key counts by pattern
            search_keys = len(self.redis_client.keys("search:*"))
            ask_keys = len(self.redis_client.keys("ask:*"))
            trends_keys = len(self.redis_client.keys("trends:*"))
            analysis_keys = len(self.redis_client.keys("analysis:*"))
            
            return {
                "status": "active",
                "total_keys": info.get('db0', {}).get('keys', 0),
                "memory_used": info.get('used_memory_human', 'N/A'),
                "memory_peak": info.get('used_memory_peak_human', 'N/A'),
                "hit_rate": info.get('keyspace_hit_rate', 0),
                "key_counts": {
                    "search": search_keys,
                    "ask": ask_keys,
                    "trends": trends_keys,
                    "analysis": analysis_keys
                },
                "connected_clients": info.get('connected_clients', 0),
                "uptime_seconds": info.get('uptime_in_seconds', 0)
            }
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {"status": "error", "error": str(e)}
    
    def clear_all_cache(self) -> bool:
        """Clear all cache (use with caution)"""
        if not self.redis_client:
            return False
        
        try:
            self.redis_client.flushdb()
            logger.info("All cache cleared")
            return True
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            return False
    
    def warm_up_cache(self, db_session) -> Dict[str, Any]:
        """Warm up cache with common queries"""
        if not self.redis_client:
            return {"status": "disabled"}
        
        warming_results = {
            "search_queries": 0,
            "trends_cached": 0,
            "errors": 0
        }
        
        try:
            # Common search queries to pre-cache
            common_queries = [
                "artificial intelligence",
                "blockchain technology", 
                "machine learning",
                "cryptocurrency",
                "data science",
                "cybersecurity"
            ]
            
            from .api.search import SearchResponse
            from .rag_engine import rag_engine
            
            for query in common_queries:
                try:
                    # Pre-cache search results
                    filters = {"hybrid": True, "alpha": 0.7}
                    
                    results = rag_engine.retrieve_relevant_chunks(
                        question=query,
                        max_chunks=30,
                        alpha=0.7
                    )
                    
                    if results:
                        search_result = {
                            "results": results[:10],  # Cache top 10 results
                            "query": query,
                            "total_found": len(results),
                            "search_time_ms": 150,  # Estimated
                            "filters": filters
                        }
                        
                        self.cache_search_result(query, filters, search_result)
                        warming_results["search_queries"] += 1
                
                except Exception as e:
                    logger.error(f"Error warming up query '{query}': {e}")
                    warming_results["errors"] += 1
            
            logger.info(f"Cache warm-up completed: {warming_results}")
            return {"status": "completed", **warming_results}
            
        except Exception as e:
            logger.error(f"Cache warm-up failed: {e}")
            return {"status": "error", "error": str(e)}

# Global cache service instance
cache_service = CacheService()