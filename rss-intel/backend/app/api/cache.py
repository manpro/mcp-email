#!/usr/bin/env python3
"""
Cache management API endpoints
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import Dict, Any
import logging

from ..deps import get_db
from ..cache_service import cache_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/cache", tags=["cache"])

@router.get("/status")
async def get_cache_status() -> Dict[str, Any]:
    """Get cache service status and statistics"""
    try:
        stats = cache_service.get_cache_stats()
        return {
            "status": "success",
            "data": stats
        }
    except Exception as e:
        logger.error(f"Error getting cache status: {e}")
        raise HTTPException(status_code=500, detail=f"Cache status error: {str(e)}")

@router.post("/clear")
async def clear_cache(pattern: str = "*") -> Dict[str, Any]:
    """Clear cache entries matching pattern"""
    try:
        if pattern == "*":
            # Clear all cache
            success = cache_service.clear_all_cache()
            message = "All cache cleared" if success else "Failed to clear cache"
            cleared_count = "all"
        else:
            # Clear specific pattern
            cleared_count = cache_service.clear_pattern(pattern)
            message = f"Cleared {cleared_count} cache entries matching pattern: {pattern}"
            success = cleared_count >= 0
        
        return {
            "status": "success" if success else "error",
            "message": message,
            "cleared_count": cleared_count
        }
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        raise HTTPException(status_code=500, detail=f"Cache clear error: {str(e)}")

@router.post("/warm-up")
async def warm_up_cache(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Warm up cache with common queries"""
    try:
        result = cache_service.warm_up_cache(db)
        return {
            "status": "success",
            "data": result
        }
    except Exception as e:
        logger.error(f"Error warming up cache: {e}")
        raise HTTPException(status_code=500, detail=f"Cache warm-up error: {str(e)}")

@router.delete("/search")
async def clear_search_cache() -> Dict[str, Any]:
    """Clear only search-related cache"""
    try:
        cleared_count = cache_service.clear_pattern("search:*")
        return {
            "status": "success",
            "message": f"Cleared {cleared_count} search cache entries",
            "cleared_count": cleared_count
        }
    except Exception as e:
        logger.error(f"Error clearing search cache: {e}")
        raise HTTPException(status_code=500, detail=f"Search cache clear error: {str(e)}")

@router.delete("/ask")
async def clear_ask_cache() -> Dict[str, Any]:
    """Clear only ask/Q&A-related cache"""
    try:
        cleared_count = cache_service.clear_pattern("ask:*")
        return {
            "status": "success", 
            "message": f"Cleared {cleared_count} Q&A cache entries",
            "cleared_count": cleared_count
        }
    except Exception as e:
        logger.error(f"Error clearing Q&A cache: {e}")
        raise HTTPException(status_code=500, detail=f"Q&A cache clear error: {str(e)}")

@router.delete("/trends")
async def clear_trends_cache() -> Dict[str, Any]:
    """Clear only trends-related cache"""
    try:
        cleared_count = cache_service.clear_pattern("trends:*")
        return {
            "status": "success",
            "message": f"Cleared {cleared_count} trends cache entries", 
            "cleared_count": cleared_count
        }
    except Exception as e:
        logger.error(f"Error clearing trends cache: {e}")
        raise HTTPException(status_code=500, detail=f"Trends cache clear error: {str(e)}")

@router.get("/metrics")
async def get_cache_metrics() -> Dict[str, Any]:
    """Get detailed cache performance metrics"""
    try:
        stats = cache_service.get_cache_stats()
        
        if stats.get("status") != "active":
            return stats
        
        # Add computed metrics
        total_keys = stats.get("total_keys", 0)
        key_counts = stats.get("key_counts", {})
        
        metrics = {
            **stats,
            "cache_distribution": {
                "search_percentage": round((key_counts.get("search", 0) / max(total_keys, 1)) * 100, 2),
                "ask_percentage": round((key_counts.get("ask", 0) / max(total_keys, 1)) * 100, 2),
                "trends_percentage": round((key_counts.get("trends", 0) / max(total_keys, 1)) * 100, 2),
                "analysis_percentage": round((key_counts.get("analysis", 0) / max(total_keys, 1)) * 100, 2)
            },
            "performance_indicators": {
                "total_keys": total_keys,
                "hit_rate_percent": round(stats.get("hit_rate", 0) * 100, 2),
                "memory_efficiency": "good" if total_keys > 0 else "empty"
            }
        }
        
        return {
            "status": "success",
            "data": metrics
        }
    except Exception as e:
        logger.error(f"Error getting cache metrics: {e}")
        raise HTTPException(status_code=500, detail=f"Cache metrics error: {str(e)}")