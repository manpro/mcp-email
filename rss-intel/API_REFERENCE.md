# RSS Intelligence Dashboard - Complete API Reference

## Overview

This document provides comprehensive documentation for all API endpoints in the RSS Intelligence Dashboard. The API is built with FastAPI and follows RESTful principles with OpenAPI 3.0 specification.

**Base URL**: `http://localhost:8000` (development) / `https://your-domain.com` (production)  
**API Documentation**: `/docs` (Swagger UI) / `/redoc` (ReDoc)

## Authentication

Most endpoints require authentication using JWT tokens or session-based authentication.

```http
Authorization: Bearer <jwt_token>
```

## 🔍 Vector Search API

### Search Articles Semantically
**Endpoint**: `POST /api/vector-search/search`

Advanced semantic search using Weaviate vector database.

**Request Body**:
```json
{
  "query": "artificial intelligence trends",
  "limit": 20,
  "semantic_weight": 0.7,
  "keyword_weight": 0.3,
  "min_score": 0.5,
  "filters": {
    "category": "technology",
    "date_range": {
      "start": "2025-08-01T00:00:00Z",
      "end": "2025-08-27T23:59:59Z"
    }
  }
}
```

**Response**:
```json
{
  "results": [
    {
      "id": 123,
      "title": "AI Breakthrough in Language Models",
      "content": "Article content...",
      "url": "https://example.com/article",
      "score": 0.85,
      "similarity": 0.78,
      "published_at": "2025-08-27T10:00:00Z",
      "source": {
        "id": 1,
        "name": "Tech News",
        "url": "https://technews.com"
      }
    }
  ],
  "query_info": {
    "processed_query": "artificial intelligence trends",
    "total_results": 150,
    "search_time_ms": 45,
    "hybrid_search": true
  }
}
```

### Check Vector Search Health
**Endpoint**: `GET /api/vector-search/health`

Returns the health status of the vector search service.

**Response**:
```json
{
  "status": "healthy",
  "weaviate_connection": true,
  "indexed_articles": 5680,
  "embedding_model": "all-MiniLM-L6-v2",
  "last_index_update": "2025-08-27T12:00:00Z"
}
```

### Rebuild Search Index
**Endpoint**: `POST /api/vector-search/reindex`

Rebuilds the entire vector search index (admin only).

**Request Body**:
```json
{
  "force": true,
  "batch_size": 100
}
```

## 📊 Trending Analysis API

### Analyze Current Trends
**Endpoint**: `POST /api/trending/analyze`

Performs real-time trend analysis using LDA topic modeling.

**Request Body**:
```json
{
  "hours_back": 24,
  "min_articles": 3,
  "min_sources": 2,
  "include_predictions": true,
  "analysis_type": "lda_clustering"
}
```

**Response**:
```json
{
  "analysis_id": "trend_2025-08-27_001",
  "topics_found": [
    {
      "id": 1,
      "topic_name": "AI Model Releases",
      "trend_score": 0.85,
      "velocity": 12.5,
      "article_count": 15,
      "unique_sources": 8,
      "keywords": ["AI", "model", "release", "GPT", "OpenAI"],
      "trend_direction": "rising",
      "confidence": 0.92,
      "is_viral": true
    }
  ],
  "analysis_metadata": {
    "articles_analyzed": 1250,
    "sources_analyzed": 45,
    "execution_time_seconds": 8.3,
    "confidence_level": 0.89
  }
}
```

### Get Trending Topics
**Endpoint**: `GET /api/trending/topics`

Retrieves current trending topics with pagination.

**Query Parameters**:
- `limit` (int): Number of topics to return (default: 20)
- `min_score` (float): Minimum trend score (default: 0.6)
- `trend_direction` (string): "rising", "falling", or "stable"
- `is_viral` (boolean): Filter viral content only

**Response**:
```json
{
  "topics": [
    {
      "id": 1,
      "topic_name": "Cryptocurrency Regulation",
      "trend_score": 0.78,
      "article_count": 12,
      "first_detected_at": "2025-08-27T08:00:00Z",
      "related_articles": [123, 124, 125]
    }
  ],
  "pagination": {
    "total": 45,
    "page": 1,
    "per_page": 20
  }
}
```

### Get Viral Content
**Endpoint**: `GET /api/trending/viral`

Returns articles identified as viral content.

**Query Parameters**:
- `min_viral_score` (float): Minimum viral score (default: 0.8)
- `hours_back` (int): Time window in hours (default: 24)

**Response**:
```json
{
  "viral_articles": [
    {
      "article_id": 123,
      "viral_score": 0.92,
      "engagement_rate": 15.7,
      "peak_engagement_time": "2025-08-27T14:30:00Z",
      "viral_triggers": ["breaking_news", "celebrity_mention"],
      "cross_platform": true
    }
  ]
}
```

## 🏥 Source Health Monitoring API

### Get Source Health Overview
**Endpoint**: `GET /api/source-health/overview`

Provides comprehensive health overview of all monitored sources.

**Query Parameters**:
- `days` (int): Analysis period in days (default: 7)
- `include_healthy` (boolean): Include healthy sources (default: true)

**Response**:
```json
{
  "summary": {
    "total_sources": 150,
    "healthy_sources": 142,
    "warning_sources": 6,
    "failing_sources": 2,
    "average_success_rate": 0.947
  },
  "source_health": [
    {
      "source_id": 1,
      "source_name": "Tech News",
      "health_status": "healthy",
      "success_rate": 0.98,
      "last_successful_fetch": "2025-08-27T12:00:00Z",
      "issues": []
    },
    {
      "source_id": 2,
      "source_name": "Blocked Site",
      "health_status": "failing",
      "success_rate": 0.12,
      "last_successful_fetch": "2025-08-25T08:00:00Z",
      "issues": ["cloudflare_block", "extraction_failure"]
    }
  ]
}
```

### Get Problematic Sources
**Endpoint**: `GET /api/source-health/problematic`

Returns sources with health issues.

**Query Parameters**:
- `min_severity` (string): "low", "medium", "high"
- `issue_type` (string): "cloudflare_block", "paywall", "extraction_failure"

**Response**:
```json
{
  "problematic_sources": [
    {
      "source_id": 5,
      "source_name": "Paywalled News",
      "issue_type": "paywall",
      "severity": "high",
      "first_detected": "2025-08-26T09:00:00Z",
      "failure_count": 15,
      "detection_patterns_matched": [
        "subscribe to continue reading",
        "premium content"
      ]
    }
  ]
}
```

### Run Source Health Analysis
**Endpoint**: `POST /api/source-health/analyze`

Triggers immediate health analysis for specific sources or all sources.

**Request Body**:
```json
{
  "source_ids": [1, 2, 3],
  "full_analysis": false,
  "update_patterns": true
}
```

## 🌐 Fediverse Integration API

### List Mastodon Instances
**Endpoint**: `GET /api/fediverse/instances`

Returns known Mastodon instances and their status.

**Response**:
```json
{
  "instances": [
    {
      "id": 1,
      "domain": "mastodon.social",
      "name": "Mastodon Social",
      "is_active": true,
      "api_version": "4.2.0",
      "user_count": 500000,
      "last_checked": "2025-08-27T12:00:00Z"
    }
  ]
}
```

### Add Fediverse Source
**Endpoint**: `POST /api/fediverse/sources`

Adds a new Mastodon account or hashtag to monitor.

**Request Body**:
```json
{
  "source_type": "account",
  "identifier": "username",
  "instance_domain": "mastodon.social",
  "fetch_frequency": 3600,
  "include_replies": false,
  "include_boosts": true
}
```

**Response**:
```json
{
  "source_id": 123,
  "status": "added",
  "next_fetch": "2025-08-27T13:00:00Z",
  "estimated_posts_per_day": 5
}
```

### Monitor Hashtag
**Endpoint**: `GET /api/fediverse/hashtag/{hashtag}`

Retrieves posts for a specific hashtag across monitored instances.

**Path Parameters**:
- `hashtag` (string): The hashtag to monitor (without #)

**Query Parameters**:
- `instance_domain` (string): Specific instance to search
- `limit` (int): Number of posts to return
- `since_id` (string): Return posts after this ID

**Response**:
```json
{
  "hashtag": "ai",
  "posts": [
    {
      "id": "110000000000000001",
      "content": "Exciting developments in #AI today...",
      "author": "@user@mastodon.social",
      "created_at": "2025-08-27T12:00:00Z",
      "url": "https://mastodon.social/@user/110000000000000001",
      "boosts_count": 15,
      "favourites_count": 32
    }
  ]
}
```

## 💡 Recommendations API

### Get Personalized Recommendations
**Endpoint**: `GET /api/recommendations`

Returns ML-powered personalized content recommendations.

**Query Parameters**:
- `limit` (int): Number of recommendations (default: 20)
- `explanation` (boolean): Include recommendation explanations (default: false)
- `categories` (array): Filter by specific categories
- `min_score` (float): Minimum recommendation score

**Response**:
```json
{
  "recommendations": [
    {
      "article_id": 123,
      "title": "AI Breakthrough in Healthcare",
      "recommendation_score": 0.87,
      "explanation": {
        "primary_reason": "matches_reading_history",
        "factors": [
          "user_likes_ai_content",
          "healthcare_interest",
          "similar_articles_read"
        ],
        "confidence": 0.82
      },
      "predicted_engagement": 0.73
    }
  ],
  "user_profile": {
    "top_categories": ["technology", "science", "business"],
    "reading_velocity": "high",
    "preferred_content_length": "medium"
  }
}
```

### Submit User Feedback
**Endpoint**: `POST /api/personalization/feedback`

Provides user feedback to improve recommendations.

**Request Body**:
```json
{
  "article_id": 123,
  "action": "like",
  "engagement_time": 45,
  "completion_rate": 0.8,
  "explicit_rating": 4
}
```

## 📡 JSON Feed API

### Discover JSON Feeds
**Endpoint**: `POST /api/json-feeds/discover`

Auto-discovers JSON feeds from URLs.

**Request Body**:
```json
{
  "url": "https://example.com",
  "check_common_paths": true
}
```

**Response**:
```json
{
  "feeds_found": [
    {
      "url": "https://example.com/feed.json",
      "title": "Example Blog",
      "version": "1.1",
      "discovery_method": "html_link"
    }
  ]
}
```

### Parse JSON Feed
**Endpoint**: `POST /api/json-feeds/parse`

Parses and validates JSON feed content.

**Request Body**:
```json
{
  "feed_url": "https://example.com/feed.json"
}
```

## 🔗 API Integrations

### GitHub Integration

#### Get Repository Releases
**Endpoint**: `GET /api/integrations/github/releases`

**Query Parameters**:
- `repo` (string): Repository in format "owner/repo"
- `limit` (int): Number of releases to fetch

#### Monitor Repository
**Endpoint**: `POST /api/integrations/github/monitor`

**Request Body**:
```json
{
  "repository": "microsoft/vscode",
  "events": ["release", "security_advisory"]
}
```

### Reddit Integration

#### Get Subreddit Posts
**Endpoint**: `GET /api/integrations/reddit/subreddit/{subreddit}`

**Path Parameters**:
- `subreddit` (string): Subreddit name

**Query Parameters**:
- `sort` (string): "hot", "new", "top"
- `limit` (int): Number of posts

### HackerNews Integration

#### Get Top Stories
**Endpoint**: `GET /api/integrations/hackernews/top`

**Query Parameters**:
- `limit` (int): Number of stories (default: 30)

**Response**:
```json
{
  "stories": [
    {
      "id": 38246420,
      "title": "Show HN: My AI Project",
      "url": "https://example.com",
      "score": 156,
      "comments": 42,
      "author": "username",
      "time": "2025-08-27T12:00:00Z"
    }
  ]
}
```

## 📊 Analytics & System APIs

### System Health Check
**Endpoint**: `GET /health`

Returns overall system health status.

**Response**:
```json
{
  "status": "healthy",
  "services": {
    "database": "healthy",
    "vector_db": "healthy",
    "redis": "healthy",
    "scheduler": "healthy"
  },
  "uptime_seconds": 86400,
  "version": "2.0.0"
}
```

### System Metrics
**Endpoint**: `GET /system/metrics`

Provides detailed system performance metrics.

**Response**:
```json
{
  "performance": {
    "avg_response_time_ms": 45,
    "requests_per_minute": 1250,
    "cache_hit_rate": 0.87,
    "error_rate": 0.001
  },
  "database": {
    "active_connections": 15,
    "query_avg_time_ms": 12,
    "total_articles": 125000,
    "indexed_articles": 98.5
  },
  "intelligence": {
    "trends_detected_today": 23,
    "viral_articles_found": 5,
    "ml_predictions_made": 1500
  }
}
```

### Intelligence Status
**Endpoint**: `GET /api/intelligence/status`

Returns status of all AI and ML services.

**Response**:
```json
{
  "services": {
    "vector_search": {
      "status": "active",
      "last_index_update": "2025-08-27T12:00:00Z",
      "articles_indexed": 5680
    },
    "trending_analysis": {
      "status": "active",
      "last_analysis": "2025-08-27T11:30:00Z",
      "topics_found": 15
    },
    "ml_personalization": {
      "status": "active",
      "model_accuracy": 0.847,
      "last_training": "2025-08-26T20:00:00Z"
    }
  }
}
```

## 🔐 Authentication Endpoints

### Login
**Endpoint**: `POST /api/auth/login`

**Request Body**:
```json
{
  "username": "user@example.com",
  "password": "secure_password"
}
```

**Response**:
```json
{
  "access_token": "jwt_token_here",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": {
    "id": 1,
    "username": "user",
    "email": "user@example.com"
  }
}
```

### Refresh Token
**Endpoint**: `POST /api/auth/refresh`

**Request Body**:
```json
{
  "refresh_token": "refresh_token_here"
}
```

## 📝 Content Management APIs

### Get Articles
**Endpoint**: `GET /api/items`

**Query Parameters**:
- `page` (int): Page number (default: 1)
- `limit` (int): Items per page (default: 50)
- `min_score` (float): Minimum quality score
- `category` (string): Filter by category
- `source` (string): Filter by source domain
- `starred` (boolean): Only starred articles
- `date_range` (object): Date range filter

**Response**:
```json
{
  "articles": [
    {
      "id": 123,
      "title": "Article Title",
      "content": "Article content...",
      "url": "https://example.com/article",
      "score": 75.5,
      "category": "technology",
      "sentiment": "positive",
      "published_at": "2025-08-27T10:00:00Z",
      "source": {
        "id": 1,
        "name": "Tech Blog",
        "url": "https://techblog.com"
      }
    }
  ],
  "pagination": {
    "total": 1250,
    "page": 1,
    "per_page": 50,
    "total_pages": 25
  }
}
```

### Article Action
**Endpoint**: `POST /api/items/{id}/decide`

**Path Parameters**:
- `id` (int): Article ID

**Request Body**:
```json
{
  "action": "star",
  "label": "important",
  "notes": "Interesting AI development"
}
```

## 🔍 Search APIs

### Enhanced Search
**Endpoint**: `GET /api/search`

**Query Parameters**:
- `q` (string): Search query
- `category` (string): Filter by category
- `sentiment` (string): "positive", "negative", "neutral"
- `min_score` (float): Minimum article score
- `date_range` (object): Date range filter

### Ask AI
**Endpoint**: `POST /api/ask`

**Request Body**:
```json
{
  "question": "What are the main AI trends this week?",
  "context": "technology",
  "include_sources": true,
  "max_results": 10
}
```

**Response**:
```json
{
  "answer": "The main AI trends this week include...",
  "confidence": 0.85,
  "sources": [
    {
      "article_id": 123,
      "title": "AI Breakthrough",
      "relevance": 0.92
    }
  ],
  "related_questions": [
    "How will this impact the industry?",
    "What companies are involved?"
  ]
}
```

## ⚠️ Error Responses

All API endpoints use standardized error responses:

```json
{
  "error": "validation_error",
  "message": "Invalid request parameters",
  "details": {
    "field": "limit",
    "issue": "must be between 1 and 100"
  },
  "timestamp": "2025-08-27T12:00:00Z",
  "request_id": "req_abc123"
}
```

### Common Error Codes

- `400` - Bad Request: Invalid parameters
- `401` - Unauthorized: Missing or invalid authentication
- `403` - Forbidden: Insufficient permissions
- `404` - Not Found: Resource doesn't exist
- `429` - Too Many Requests: Rate limit exceeded
- `500` - Internal Server Error: Server-side error
- `503` - Service Unavailable: Service temporarily down

## 🚀 Rate Limiting

API endpoints have the following rate limits:

- **Search endpoints**: 100 requests/minute
- **Content endpoints**: 200 requests/minute
- **Analytics endpoints**: 50 requests/minute
- **AI endpoints**: 20 requests/minute

Rate limit headers are included in responses:

```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1693123200
```

## 📋 Pagination

List endpoints use consistent pagination:

**Query Parameters**:
- `page` (int): Page number (default: 1)
- `limit` (int): Items per page (default: 50, max: 100)

**Response Format**:
```json
{
  "data": [...],
  "pagination": {
    "total": 1250,
    "page": 1,
    "per_page": 50,
    "total_pages": 25,
    "has_next": true,
    "has_prev": false
  }
}
```

## 🔧 WebSocket API

### Live Updates Connection
**Endpoint**: `ws://localhost:8000/ws/live`

**Message Types**:
- `article_update` - New articles available
- `trend_detected` - New trending topic found
- `health_alert` - Source health issue detected
- `viral_content` - Viral article identified

**Example Message**:
```json
{
  "type": "trend_detected",
  "data": {
    "topic_name": "AI Breakthrough",
    "trend_score": 0.85,
    "article_count": 12
  },
  "timestamp": "2025-08-27T12:00:00Z"
}
```

---

*API Reference Version: 2.0*  
*Last Updated: 2025-08-27*  
*For interactive documentation, visit `/docs` endpoint*