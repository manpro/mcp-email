"""
Search Cache Service

High-performance caching layer for RSS Intelligence search system.
Provides intelligent caching, precomputation, and performance optimization.
"""

import logging
import json
import hashlib
from typing import Dict, List, Optional, Any, Union, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import pickle
import gzip
from collections import defaultdict, OrderedDict

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

logger = logging.getLogger(__name__)

@dataclass
class CacheEntry:
    """A cached search result entry"""
    key: str
    data: Any
    created_at: datetime
    expires_at: datetime
    hit_count: int = 0
    last_accessed: datetime = None
    size_bytes: int = 0

@dataclass
class CacheStats:
    """Cache performance statistics"""
    total_entries: int
    total_size_bytes: int
    hit_rate: float
    miss_rate: float
    avg_response_time_ms: float
    popular_queries: List[Tuple[str, int]]
    expiry_distribution: Dict[str, int]

class SearchCacheService:
    """High-performance search caching service"""
    
    def __init__(self, redis_url: str = None, max_memory_entries: int = 10000):
        self.max_memory_entries = max_memory_entries
        self.memory_cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.cache_stats = {
            'hits': 0,
            'misses': 0,
            'total_requests': 0,
            'response_times': []
        }
        
        # Redis setup
        self.redis_client = None
        if REDIS_AVAILABLE and redis_url:
            try:
                self.redis_client = redis.from_url(redis_url)
                self.redis_client.ping()  # Test connection
                logger.info("Redis cache backend initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Redis: {e}, falling back to memory cache")
                self.redis_client = None
        
        # Cache TTL settings (in seconds)
        self.cache_ttls = {
            'search_results': 300,      # 5 minutes for search results
            'facets': 1800,            # 30 minutes for facets
            'suggestions': 3600,        # 1 hour for suggestions
            'analytics': 900,          # 15 minutes for analytics
            'popular_queries': 1800,   # 30 minutes for popular queries
            'trending': 600,           # 10 minutes for trending
            'semantic_vectors': 7200,  # 2 hours for semantic vectors
        }
        
        # Precomputed cache for expensive operations
        self.precomputed_cache = {}
        
    def get_search_results(self, 
                          search_key: str,
                          cache_type: str = 'search_results') -> Optional[Any]:
        """
        Get cached search results
        
        Args:
            search_key: Unique search identifier
            cache_type: Type of cache entry
            
        Returns:
            Cached data or None if not found/expired
        """
        start_time = datetime.now()
        
        try:
            # Try Redis first if available
            if self.redis_client:
                result = self._get_from_redis(search_key, cache_type)
                if result is not None:
                    self._record_cache_hit(start_time)
                    return result
            
            # Try memory cache
            result = self._get_from_memory(search_key)
            if result is not None:
                self._record_cache_hit(start_time)
                return result
            
            # Cache miss
            self._record_cache_miss(start_time)
            return None
            
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            self._record_cache_miss(start_time)
            return None
    
    def set_search_results(self,
                          search_key: str,
                          data: Any,
                          cache_type: str = 'search_results',
                          custom_ttl: int = None) -> bool:
        """
        Cache search results
        
        Args:
            search_key: Unique search identifier
            data: Data to cache
            cache_type: Type of cache entry
            custom_ttl: Custom TTL in seconds
            
        Returns:
            True if successfully cached
        """
        try:
            ttl = custom_ttl or self.cache_ttls.get(cache_type, 300)
            expires_at = datetime.now() + timedelta(seconds=ttl)
            
            # Estimate size
            try:
                size_bytes = len(pickle.dumps(data))
            except:
                size_bytes = len(str(data))
            
            # Store in Redis if available
            if self.redis_client:
                success = self._set_in_redis(search_key, data, ttl, cache_type)
                if success:
                    logger.debug(f"Cached in Redis: {search_key} ({size_bytes} bytes, {ttl}s TTL)")
            
            # Always store in memory cache as backup
            self._set_in_memory(search_key, data, expires_at, size_bytes)
            
            return True
            
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False
    
    def invalidate_pattern(self, pattern: str) -> int:
        """
        Invalidate cache entries matching a pattern
        
        Args:
            pattern: Pattern to match (supports wildcards)
            
        Returns:
            Number of entries invalidated
        """
        invalidated = 0
        
        try:
            # Redis pattern invalidation
            if self.redis_client:
                keys = self.redis_client.keys(f"rss_search:{pattern}")
                if keys:
                    invalidated += self.redis_client.delete(*keys)
            
            # Memory cache pattern invalidation
            keys_to_remove = []
            for key in self.memory_cache.keys():
                if self._pattern_matches(key, pattern):
                    keys_to_remove.append(key)
            
            for key in keys_to_remove:
                del self.memory_cache[key]
                invalidated += 1
            
            logger.info(f"Invalidated {invalidated} cache entries matching pattern: {pattern}")
            return invalidated
            
        except Exception as e:
            logger.error(f"Cache invalidation error: {e}")
            return 0
    
    def precompute_popular_searches(self, popular_queries: List[str]) -> None:
        """
        Precompute results for popular search queries
        
        Args:
            popular_queries: List of popular search queries to precompute
        """
        logger.info(f"Precomputing {len(popular_queries)} popular searches...")
        
        for query in popular_queries:
            try:
                # This would typically trigger the actual search
                # to populate the cache in the background
                search_key = self.generate_search_key(query)
                
                # Check if already cached
                if self.get_search_results(search_key) is None:
                    # Trigger background precomputation
                    # In practice, this would queue a background task
                    logger.debug(f"Queuing precomputation for: {query}")
                    
            except Exception as e:
                logger.warning(f"Failed to precompute search for '{query}': {e}")
    
    def get_cache_stats(self) -> CacheStats:
        """Get comprehensive cache statistics"""
        try:
            total_requests = self.cache_stats['total_requests']
            hits = self.cache_stats['hits']
            misses = self.cache_stats['misses']
            
            hit_rate = hits / max(total_requests, 1)
            miss_rate = misses / max(total_requests, 1)
            
            avg_response_time = 0.0
            if self.cache_stats['response_times']:
                avg_response_time = sum(self.cache_stats['response_times']) / len(self.cache_stats['response_times'])
            
            # Memory cache stats
            total_entries = len(self.memory_cache)
            total_size = sum(entry.size_bytes for entry in self.memory_cache.values())
            
            # Popular queries from cache access patterns
            query_hits = defaultdict(int)
            for entry in self.memory_cache.values():
                if 'query' in entry.key:
                    query_hits[entry.key] += entry.hit_count
            
            popular_queries = sorted(query_hits.items(), key=lambda x: x[1], reverse=True)[:10]
            
            # Expiry distribution
            now = datetime.now()
            expiry_buckets = {'expired': 0, '1h': 0, '1d': 0, 'longer': 0}
            
            for entry in self.memory_cache.values():
                if entry.expires_at <= now:
                    expiry_buckets['expired'] += 1
                elif entry.expires_at <= now + timedelta(hours=1):
                    expiry_buckets['1h'] += 1
                elif entry.expires_at <= now + timedelta(days=1):
                    expiry_buckets['1d'] += 1
                else:
                    expiry_buckets['longer'] += 1
            
            return CacheStats(
                total_entries=total_entries,
                total_size_bytes=total_size,
                hit_rate=hit_rate,
                miss_rate=miss_rate,
                avg_response_time_ms=avg_response_time * 1000,
                popular_queries=popular_queries,
                expiry_distribution=expiry_buckets
            )
            
        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            return CacheStats(
                total_entries=0,
                total_size_bytes=0,
                hit_rate=0.0,
                miss_rate=0.0,
                avg_response_time_ms=0.0,
                popular_queries=[],
                expiry_distribution={}
            )
    
    def cleanup_expired_entries(self) -> int:
        """Clean up expired cache entries"""
        cleaned = 0
        now = datetime.now()
        
        try:
            # Clean memory cache
            expired_keys = []
            for key, entry in self.memory_cache.items():
                if entry.expires_at <= now:
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self.memory_cache[key]
                cleaned += 1
            
            logger.info(f"Cleaned up {cleaned} expired cache entries")
            return cleaned
            
        except Exception as e:
            logger.error(f"Cache cleanup error: {e}")
            return 0
    
    def generate_search_key(self, 
                           query: str = "",
                           filters: Dict[str, Any] = None,
                           settings: Dict[str, Any] = None,
                           search_type: str = "hybrid") -> str:
        """
        Generate a unique cache key for search parameters
        
        Args:
            query: Search query
            filters: Search filters
            settings: Search settings
            search_type: Type of search
            
        Returns:
            Unique cache key
        """
        # Create normalized parameters dict
        params = {
            'query': query.strip().lower() if query else "",
            'filters': self._normalize_filters(filters or {}),
            'settings': self._normalize_settings(settings or {}),
            'type': search_type
        }
        
        # Generate hash
        params_str = json.dumps(params, sort_keys=True)
        cache_key = hashlib.md5(params_str.encode()).hexdigest()
        
        return f"search:{cache_key}"
    
    def _get_from_redis(self, key: str, cache_type: str) -> Optional[Any]:
        """Get data from Redis cache"""
        try:
            redis_key = f"rss_search:{cache_type}:{key}"
            compressed_data = self.redis_client.get(redis_key)
            
            if compressed_data:
                # Decompress and deserialize
                data = pickle.loads(gzip.decompress(compressed_data))
                return data
            
            return None
            
        except Exception as e:
            logger.warning(f"Redis get error: {e}")
            return None
    
    def _set_in_redis(self, key: str, data: Any, ttl: int, cache_type: str) -> bool:
        """Set data in Redis cache"""
        try:
            redis_key = f"rss_search:{cache_type}:{key}"
            
            # Serialize and compress
            serialized = pickle.dumps(data)
            compressed = gzip.compress(serialized)
            
            # Set with TTL
            self.redis_client.setex(redis_key, ttl, compressed)
            return True
            
        except Exception as e:
            logger.warning(f"Redis set error: {e}")
            return False
    
    def _get_from_memory(self, key: str) -> Optional[Any]:
        """Get data from memory cache"""
        try:
            if key in self.memory_cache:
                entry = self.memory_cache[key]
                
                # Check expiry
                if entry.expires_at <= datetime.now():
                    del self.memory_cache[key]
                    return None
                
                # Update access stats
                entry.hit_count += 1
                entry.last_accessed = datetime.now()
                
                # Move to end (LRU)
                self.memory_cache.move_to_end(key)
                
                return entry.data
            
            return None
            
        except Exception as e:
            logger.warning(f"Memory cache get error: {e}")
            return None
    
    def _set_in_memory(self, key: str, data: Any, expires_at: datetime, size_bytes: int) -> None:
        """Set data in memory cache"""
        try:
            # Create cache entry
            entry = CacheEntry(
                key=key,
                data=data,
                created_at=datetime.now(),
                expires_at=expires_at,
                size_bytes=size_bytes,
                last_accessed=datetime.now()
            )
            
            # Add to cache
            self.memory_cache[key] = entry
            
            # Enforce size limit (LRU eviction)
            while len(self.memory_cache) > self.max_memory_entries:
                oldest_key = next(iter(self.memory_cache))
                del self.memory_cache[oldest_key]
            
        except Exception as e:
            logger.warning(f"Memory cache set error: {e}")
    
    def _record_cache_hit(self, start_time: datetime) -> None:
        """Record cache hit statistics"""
        response_time = (datetime.now() - start_time).total_seconds()
        self.cache_stats['hits'] += 1
        self.cache_stats['total_requests'] += 1
        self.cache_stats['response_times'].append(response_time)
        
        # Keep only recent response times
        if len(self.cache_stats['response_times']) > 1000:
            self.cache_stats['response_times'] = self.cache_stats['response_times'][-500:]
    
    def _record_cache_miss(self, start_time: datetime) -> None:
        """Record cache miss statistics"""
        response_time = (datetime.now() - start_time).total_seconds()
        self.cache_stats['misses'] += 1
        self.cache_stats['total_requests'] += 1
        self.cache_stats['response_times'].append(response_time)
    
    def _normalize_filters(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize filters for consistent caching"""
        normalized = {}
        
        for key, value in filters.items():
            if value is None or (isinstance(value, list) and len(value) == 0):
                continue
            
            if isinstance(value, list):
                normalized[key] = sorted(value)
            else:
                normalized[key] = value
        
        return normalized
    
    def _normalize_settings(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize settings for consistent caching"""
        # Only include settings that affect results
        relevant_settings = {
            'page', 'page_size', 'sort_by', 'sort_order', 
            'enable_semantic', 'highlight'
        }
        
        return {k: v for k, v in settings.items() if k in relevant_settings}
    
    def _pattern_matches(self, key: str, pattern: str) -> bool:
        """Check if key matches pattern (simple wildcard support)"""
        import fnmatch
        return fnmatch.fnmatch(key, pattern)

# Global cache service instance
search_cache_service = None

def initialize_search_cache(redis_url: str = None, max_memory_entries: int = 10000) -> SearchCacheService:
    """Initialize the global search cache service"""
    global search_cache_service
    search_cache_service = SearchCacheService(redis_url, max_memory_entries)
    logger.info("Search cache service initialized")
    return search_cache_service

def get_search_cache() -> Optional[SearchCacheService]:
    """Get the global search cache service"""
    return search_cache_service