# RSS Intelligence Dashboard - Complete System Architecture

## Overview

RSS Intelligence Dashboard is a comprehensive AI-powered content intelligence platform that transforms traditional RSS reading into an advanced intelligence gathering system. The architecture is built on modern microservices principles with AI-first design, real-time capabilities, and enterprise-grade scalability.

## 🏗️ System Architecture Layers

### 1. Intelligence Core Layer
The heart of the system that orchestrates all AI operations and decision-making.

```
┌─────────────────────────────────────┐
│           AI ORCHESTRATOR           │
├─────────────────────────────────────┤
│  • Vector Search Engine             │
│  • Trending Analysis Engine         │  
│  • Source Health Monitor            │
│  • Quality Assessment System        │
│  • Fediverse Intelligence Hub       │
│  • ML Personalization Engine        │
└─────────────────────────────────────┘
```

### 2. Data Processing Layer
Handles all content ingestion, transformation, and storage operations.

```
┌─────────────────────────────────────┐
│        DATA PROCESSING LAYER        │
├─────────────────────────────────────┤
│  • Content Ingestion Service        │
│  • JSON Feed Parser                 │
│  • API Integration Service          │
│  • Text Processing Pipeline         │
│  • Image Extraction Service         │
│  • Database Management              │
└─────────────────────────────────────┘
```

### 3. Real-Time Communication Layer
Provides live updates and notifications across the platform.

```
┌─────────────────────────────────────┐
│    REAL-TIME COMMUNICATION LAYER    │
├─────────────────────────────────────┤
│  • WebSocket Hub                    │
│  • Event Streaming (Redis)          │
│  • Push Notification System         │
│  • Live Update Distributor          │
│  • Alert Management                 │
└─────────────────────────────────────┘
```

### 4. API & Integration Layer
Exposes functionality through REST APIs and integrates with external services.

```
┌─────────────────────────────────────┐
│       API & INTEGRATION LAYER       │
├─────────────────────────────────────┤
│  • FastAPI Backend                  │
│  • External API Connectors          │
│  • Authentication System            │
│  • Rate Limiting & Security         │
│  • OpenAPI Documentation            │
└─────────────────────────────────────┘
```

### 5. User Interface Layer
Modern web application with responsive design and real-time features.

```
┌─────────────────────────────────────┐
│        USER INTERFACE LAYER         │
├─────────────────────────────────────┤
│  • Next.js Frontend                 │
│  • React Components                 │
│  • Real-time Updates                │
│  • Mobile-Responsive Design         │
│  • Progressive Web App              │
└─────────────────────────────────────┘
```

## 🧠 Intelligence Services

### Vector Search Service
**Location**: `backend/app/services/vector_search_service.py`

Advanced semantic search powered by Weaviate vector database.

**Key Components:**
- Sentence transformer embeddings (all-MiniLM-L6-v2)
- Hybrid search combining vector similarity and BM25
- RAG (Retrieval-Augmented Generation) with OpenAI
- Query expansion and result re-ranking

**API Endpoints:**
- `POST /api/vector-search/search` - Semantic search
- `GET /api/vector-search/health` - Service health check
- `POST /api/vector-search/reindex` - Rebuild search index

### Trending Analysis Service
**Location**: `backend/app/services/trending_analysis_service.py`

Real-time trend detection using advanced machine learning techniques.

**Key Components:**
- LDA (Latent Dirichlet Allocation) topic modeling
- K-means clustering for content grouping
- Viral content detection algorithms
- Trend prediction and scoring

**Database Models:**
- `trending_topics` - Active trending topics with scores
- `topic_clusters` - Content clusters and analysis
- `viral_content` - Viral articles and engagement metrics
- `trend_predictions` - Future trend predictions

**API Endpoints:**
- `POST /api/trending/analyze` - Run trend analysis
- `GET /api/trending/topics` - Get trending topics
- `GET /api/trending/viral` - Get viral content

### Source Health Service
**Location**: `backend/app/services/source_health_service.py`

Monitors RSS sources for availability and content extraction issues.

**Key Features:**
- Cloudflare block detection
- Paywall identification
- Content extraction success tracking
- Automatic source quality scoring

**Detection Patterns:**
```python
{
    'cloudflare_block': [
        r'checking if the site connection is secure',
        r'cloudflare ray id',
        r'please enable cookies'
    ],
    'paywall': [
        r'subscribe to continue reading',
        r'premium content',
        r'sign up to read'
    ]
}
```

**Database Model:**
- `source_health_reports` - Health status and failure analysis

**API Endpoints:**
- `GET /api/source-health/overview` - Health dashboard
- `GET /api/source-health/problematic` - Failed sources
- `POST /api/source-health/analyze` - Run health check

### Fediverse Service
**Location**: `backend/app/services/fediverse_service.py`

Complete Mastodon/ActivityPub integration for social media monitoring.

**Key Features:**
- Mastodon instance discovery
- Account monitoring and post fetching
- Hashtag tracking across instances
- Public timeline monitoring
- ActivityPub protocol support

**Database Models:**
- `fediverse_instances` - Known Mastodon instances
- `fediverse_sources` - Monitored accounts and hashtags
- `fediverse_posts` - Fetched social media content

**API Endpoints:**
- `GET /api/fediverse/instances` - List available instances
- `POST /api/fediverse/sources` - Add monitoring source
- `GET /api/fediverse/hashtag/{tag}` - Monitor hashtag

### JSON Feed Service
**Location**: `backend/app/services/json_feed_service.py`

Modern feed format support with auto-discovery capabilities.

**Key Features:**
- JSON Feed 1.0/1.1 specification support
- Auto-discovery from HTML pages
- Fallback to common JSON feed paths
- Content normalization and validation

**Supported Formats:**
- JSON Feed 1.0 (`https://jsonfeed.org/version/1`)
- JSON Feed 1.1 (`https://jsonfeed.org/version/1.1`)

### API Integrations Service
**Location**: `backend/app/services/api_integrations_service.py`

External platform connectors for diverse content sources.

**Supported Platforms:**
- **GitHub**: Repository releases and important updates
- **HackerNews**: Top stories and trending discussions
- **Reddit**: Subreddit posts and community content

**Key Features:**
- Rate limiting and concurrent processing
- Content normalization across platforms
- Error handling and retry logic
- API key management

## 📊 Data Architecture

### Primary Database (PostgreSQL)
**Location**: Docker service `postgres`

**Core Tables:**
- `articles` - Main article storage
- `sources` - RSS feed sources
- `user_events` - User interaction tracking
- `ml_models` - Machine learning model storage

**Intelligence Tables:**
- `trending_topics` - Real-time trending analysis
- `topic_clusters` - Content clustering results
- `viral_content` - Viral article tracking
- `trend_predictions` - Future trend forecasts
- `source_health_reports` - Source monitoring data
- `fediverse_instances` - Mastodon instances
- `fediverse_sources` - Social media sources
- `fediverse_posts` - Social media content

### Vector Database (Weaviate)
**Location**: Docker service `weaviate`

**Schema:**
- `Article` class with vector embeddings
- Semantic search capabilities
- Cross-reference support
- Real-time indexing

### Cache Layer (Redis)
**Location**: Docker service `redis`

**Usage:**
- Search result caching
- Session management
- Rate limiting counters
- Real-time event streaming (Redis Streams)

## 🔄 Data Flow Architecture

### Content Ingestion Pipeline

```
RSS Feeds → Content Parser → Text Processing → Quality Assessment
     ↓              ↓              ↓              ↓
JSON Feeds → JSON Parser → Image Extraction → Vector Embedding
     ↓              ↓              ↓              ↓
API Sources → API Connector → ML Analysis → Database Storage
     ↓              ↓              ↓              ↓
Fediverse → Activity Parser → Trend Detection → Search Index
```

### Real-Time Processing Pipeline

```
Content Update → Event Generation → Redis Streams → WebSocket Hub
     ↓              ↓              ↓              ↓
Trend Analysis → Alert Generation → Push Notifications → UI Updates
     ↓              ↓              ↓              ↓
Health Check → Status Update → Dashboard Refresh → User Notification
```

### Search & Recommendation Pipeline

```
User Query → Query Processing → Vector Search → Result Ranking
     ↓              ↓              ↓              ↓
User Behavior → Feature Extraction → ML Training → Personalization
     ↓              ↓              ↓              ↓
Content Analysis → Quality Scoring → Recommendation → User Interface
```

## 🌐 API Architecture

### Router Structure

**Main Application**: `backend/app/main.py`
- Includes all service routers with proper prefixes
- Middleware for CORS, authentication, rate limiting
- Health checks and system monitoring endpoints

**Service Routers:**
- `api/vector_search.py` - Semantic search endpoints
- `api/trending.py` - Trend analysis and viral content
- `api/source_health.py` - Source monitoring and health
- `api/fediverse.py` - Social media integration
- `api/recommendations.py` - ML-powered suggestions
- `api/json_feeds.py` - JSON feed management
- `api/api_integrations.py` - External platform connectors

### Authentication & Security

**Features:**
- JWT token-based authentication
- Role-based access control
- API rate limiting per user/IP
- Request validation and sanitization
- CORS configuration for frontend

### Error Handling

**Standardized Responses:**
```python
{
    "error": "error_code",
    "message": "Human readable message",
    "details": {}, # Optional additional context
    "timestamp": "2025-08-27T12:00:00Z"
}
```

## 💻 Frontend Architecture

### Component Structure
**Location**: `web/src/components/`

**Main Components:**
- `Dashboard.tsx` - Main application container
- `ArticleCard.tsx` - Article display component
- `SearchTab.tsx` - Vector search interface
- `TrendingTab.tsx` - Trending analysis dashboard
- `FediverseTab.tsx` - Social media monitoring
- `SourceHealthTab.tsx` - Source health monitoring
- `RecommendedTab.tsx` - ML recommendations

### State Management

**Approach:**
- React hooks for local state
- Context API for global state
- Real-time updates via WebSocket
- Optimistic updates for better UX

### Real-Time Features

**WebSocket Integration:**
```typescript
const ws = new WebSocket('ws://localhost:8000/ws/live');
ws.onmessage = (event) => {
  const update = JSON.parse(event.data);
  // Handle real-time updates
};
```

## 🔧 Configuration Architecture

### Environment-Based Configuration

**Development** (`.env.development`):
```env
DATABASE_URL=postgresql://rss:password@postgres:5432/rssintel
WEAVIATE_URL=http://weaviate:8080
REDIS_HOST=redis
OPENAI_API_KEY=your_dev_key
```

**Production** (`.env.production`):
```env
DATABASE_URL=postgresql://rss:secure_password@db_host:5432/rssintel
WEAVIATE_URL=https://weaviate.example.com
REDIS_HOST=redis.example.com
OPENAI_API_KEY=your_prod_key
SSL_ENABLED=true
DOMAIN=your-domain.com
```

### Service Configuration

**Intelligence Services:**
```env
VECTOR_SEARCH_ENABLED=true
TRENDING_ANALYSIS_ENABLED=true
FEDIVERSE_ENABLED=true
SOURCE_HEALTH_MONITORING=true
```

**Performance Tuning:**
```env
TRENDING_WINDOW_HOURS=24
MIN_ARTICLES_FOR_TREND=3
VIRAL_THRESHOLD=0.8
HEALTH_CHECK_INTERVAL=3600
```

## 📈 Monitoring & Observability

### Health Check System

**Endpoint**: `/health`
**Components Monitored:**
- Database connectivity
- Vector database status
- Redis availability
- External API connectivity
- Service-specific health checks

### Metrics Collection

**System Metrics** (`/system/metrics`):
- Request/response times
- Error rates
- Database query performance
- Cache hit rates
- Memory and CPU usage

**Intelligence Metrics** (`/api/intelligence/status`):
- Trend detection performance
- Vector search response times
- ML model accuracy
- Content processing rates

### Logging Architecture

**Structured Logging:**
```python
logger.info("trend_analysis_completed", {
    "analysis_id": analysis_id,
    "topics_found": len(topics),
    "execution_time": execution_time,
    "confidence_score": avg_confidence
})
```

## 🚀 Deployment Architecture

### Docker Compose Stack

**Core Services:**
```yaml
services:
  backend:          # FastAPI application
    build: ./backend
    environment:
      - DATABASE_URL=postgresql://...
    
  web:              # Next.js frontend
    build: ./web
    environment:
      - NEXT_PUBLIC_API_URL=http://backend:8000
    
  postgres:         # Primary database
    image: postgres:16
    
  weaviate:         # Vector database
    image: semitechnologies/weaviate:1.26.3
    
  redis:            # Cache and events
    image: redis:7-alpine
```

**Production Additions:**
```yaml
  nginx:            # Reverse proxy
    image: nginx:alpine
    
  prometheus:       # Metrics collection
    image: prom/prometheus
    
  grafana:          # Monitoring dashboards
    image: grafana/grafana
```

### Scaling Considerations

**Horizontal Scaling:**
- Multiple backend instances behind load balancer
- Database read replicas for search queries
- Redis cluster for distributed caching
- Weaviate cluster for vector search scaling

**Vertical Scaling:**
- CPU-intensive: Trend analysis and ML training
- Memory-intensive: Vector search and embeddings
- I/O-intensive: Content fetching and processing

## 🔒 Security Architecture

### Data Protection

**Encryption:**
- Environment variables for API keys
- Database connection encryption
- Redis AUTH for cache access
- SSL/TLS for all external communications

**Input Validation:**
- Pydantic models for API request validation
- SQL injection prevention via ORM
- XSS protection in frontend
- Rate limiting for abuse prevention

### Network Security

**Internal Communication:**
- Services communicate via Docker network
- Database not exposed externally
- Redis cluster access restricted
- Admin interfaces behind authentication

## 📋 Performance Architecture

### Caching Strategy

**Multi-Layer Caching:**
1. **Application Cache**: In-memory Python dictionaries
2. **Redis Cache**: Shared cache across instances
3. **Database Cache**: PostgreSQL query result caching
4. **CDN Cache**: Static asset delivery (production)

**Cache Keys:**
```python
search_results:{query_hash}:{filters_hash}  # TTL: 10 minutes
trending_topics:{window_hours}              # TTL: 1 hour
source_health:{source_id}                   # TTL: 30 minutes
user_recommendations:{user_id}              # TTL: 2 hours
```

### Database Optimization

**Indexes:**
```sql
-- Full-text search
CREATE INDEX idx_articles_content_fts ON articles USING GIN(to_tsvector('english', content));

-- Trending analysis
CREATE INDEX idx_articles_published_at_desc ON articles(published_at DESC);
CREATE INDEX idx_trending_topics_score_desc ON trending_topics(trend_score DESC);

-- Source health
CREATE INDEX idx_source_health_created_at ON source_health_reports(created_at DESC);
```

**Query Optimization:**
- Prepared statements for common queries
- Connection pooling (20 connections, 30 overflow)
- Query result pagination
- Async database operations

### Async Processing

**Background Tasks:**
- Content ingestion pipeline
- Trend analysis jobs
- Source health monitoring
- ML model training

**Task Queue** (Redis-based):
```python
@app.task
async def analyze_trending_topics(hours_back: int):
    # Background trend analysis
    pass
```

## 🔄 Integration Architecture

### External Service Integration

**APIs Integrated:**
- **OpenAI**: GPT models for content analysis
- **GitHub**: Repository and release monitoring
- **Reddit**: Subreddit content aggregation
- **HackerNews**: Tech discussion monitoring
- **Mastodon**: Fediverse social content

**Integration Patterns:**
- Circuit breaker for fault tolerance
- Exponential backoff for retries
- Rate limiting respect for external APIs
- Webhook support for real-time updates

### Data Synchronization

**Real-Time Sync:**
- WebSocket connections for UI updates
- Redis Streams for event propagation
- Database triggers for critical updates
- Push notifications for important events

**Batch Sync:**
- Scheduled content ingestion jobs
- ML model training pipelines
- Historical data analysis
- Backup and archival processes

---

## 🎯 Architecture Benefits

### Scalability
- Microservices can scale independently
- Database read replicas for search queries
- Vector database clustering support
- Horizontal scaling of web services

### Reliability
- Health monitoring at every level
- Circuit breakers for external dependencies
- Graceful degradation when services fail
- Automated recovery mechanisms

### Performance
- Multi-layer caching strategy
- Async processing for heavy operations
- Optimized database queries and indexes
- CDN for static asset delivery

### Maintainability
- Clear separation of concerns
- Comprehensive logging and monitoring
- Type safety with TypeScript/Python hints
- Automated testing and deployment

### Intelligence
- AI-first architecture design
- Real-time trend detection
- Personalized content recommendations
- Continuous learning from user behavior

---

*System Architecture Version: 2.0*  
*Last Updated: 2025-08-27*  
*Status: Production Ready*