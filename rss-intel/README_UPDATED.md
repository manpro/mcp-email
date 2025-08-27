# RSS Intelligence Dashboard - Complete Intelligence Platform

A comprehensive AI-powered content discovery and analysis platform that combines RSS aggregation, semantic search, social media monitoring, trending analysis, and advanced machine learning capabilities.

## 🚀 Overview

RSS Intelligence Dashboard is the most advanced open-source content intelligence platform available. It transforms traditional RSS reading into a comprehensive intelligence gathering system with AI-powered analysis, real-time monitoring, and predictive insights.

### What Makes This Special

✨ **Complete Intelligence Suite** - From basic RSS to advanced AI analysis  
🌐 **Multi-Platform Content** - RSS, Mastodon, GitHub, HackerNews, Reddit  
🧠 **Advanced AI Analysis** - Vector search, trending detection, quality scoring  
⚡ **Real-Time Monitoring** - Live updates, notifications, health monitoring  
🎯 **Production Ready** - Docker deployment, SSL, monitoring, backups  

## 🎯 Key Features

### 🤖 Advanced AI Intelligence
- **Vector Search & RAG**: Weaviate-powered semantic search with embeddings
- **Trending Analysis**: LDA topic modeling with viral content detection
- **ML Recommendations**: Personalized content discovery with explanation
- **Quality Assessment**: Advanced spam detection and content scoring
- **Sentiment Analysis**: Multi-layered emotional intelligence pipeline

### 🌐 Multi-Platform Content Discovery
- **Fediverse Integration**: Complete Mastodon/ActivityPub support
- **API Integrations**: GitHub releases, HackerNews stories, Reddit posts
- **JSON Feed Support**: Modern feed format with auto-discovery
- **RSS Enhancement**: Traditional feeds with AI-powered enhancement
- **Source Health**: Automatic detection of failing sources and blocks

### 📊 Real-Time Intelligence
- **Trending Detection**: Real-time topic emergence and viral content
- **Source Monitoring**: Cloudflare blocks, paywall detection, health alerts  
- **Live Updates**: WebSocket-powered real-time content streams
- **Smart Notifications**: Context-aware alerts and briefings
- **Performance Monitoring**: System health and optimization metrics

### 💻 Modern User Experience
- **Unified Dashboard**: All content sources in one interface
- **Multiple View Modes**: Browse, Search, Trending, Health, Fediverse
- **Mobile Responsive**: Touch-optimized interface design
- **Dark/Light Theme**: Adaptive UI with user preferences
- **Real-Time Updates**: Live content without page refreshes

## 🏗️ System Architecture

### Core Intelligence Stack

```mermaid
graph TB
    A[Content Sources] --> B[Ingestion Layer]
    B --> C[AI Processing Pipeline]
    C --> D[Vector Database]
    C --> E[Trending Analysis]
    C --> F[Quality Filtering]
    D --> G[Search Engine]
    E --> H[Real-Time Alerts]
    F --> I[Content Ranking]
    G --> J[User Interface]
    H --> J
    I --> J
```

### Service Architecture

#### **Intelligence Services**
- **Vector Search Service**: Weaviate integration with semantic embeddings
- **Trending Analysis Service**: LDA clustering and viral detection
- **Source Health Service**: Monitoring and failure detection
- **Fediverse Service**: Mastodon/ActivityPub integration
- **API Integration Service**: External platform connectors
- **JSON Feed Service**: Modern feed format support

#### **Core Platform**
- **FastAPI Backend**: High-performance Python API with async support
- **Next.js Frontend**: Modern React application with TypeScript
- **PostgreSQL Database**: Primary data store with optimization
- **Redis Cache**: High-performance caching and session management
- **Weaviate Vector DB**: Semantic search and similarity matching

#### **External Integrations**
- **OpenAI API**: Advanced language model capabilities
- **Mastodon Network**: Fediverse content discovery
- **GitHub API**: Developer content and releases
- **HackerNews API**: Tech community discussions
- **Reddit API**: Social media content extraction

## 🚀 Quick Start

### Development Setup

1. **Clone Repository**
   ```bash
   git clone <repository>
   cd rss-intel
   ```

2. **Environment Configuration**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and settings
   ```

3. **Start Development Stack**
   ```bash
   docker-compose up -d
   ```

4. **Initialize System**
   ```bash
   # Run database migrations
   docker-compose exec backend alembic upgrade head
   
   # Initialize vector database
   docker-compose exec backend python -c "
   from app.services.vector_search_service import get_vector_search_service
   from app.deps import get_db
   service = get_vector_search_service(next(get_db()))
   await service.initialize()
   "
   ```

5. **Access Services**
   - **Main Dashboard**: http://localhost:3000
   - **API Documentation**: http://localhost:8000/docs
   - **System Health**: http://localhost:8000/health
   - **Admin Interface**: http://localhost:8000/admin

### Production Deployment

```bash
# Quick production deployment
sudo ./deploy.sh deploy

# With SSL and monitoring
sudo SSL_ENABLED=true MONITORING_ENABLED=true ./deploy.sh deploy
```

## 🔧 Configuration

### Core Environment Variables

```env
# Database Configuration
DATABASE_URL=postgresql://rss:password@postgres:5432/rssintel
WEAVIATE_URL=http://weaviate:8080
REDIS_HOST=redis
REDIS_PORT=6379

# AI Services
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4o-mini

# External APIs
GITHUB_API_KEY=your_github_token
REDDIT_CLIENT_ID=your_reddit_client_id
REDDIT_CLIENT_SECRET=your_reddit_secret

# System Features
VECTOR_SEARCH_ENABLED=true
TRENDING_ANALYSIS_ENABLED=true
FEDIVERSE_ENABLED=true
SOURCE_HEALTH_MONITORING=true
```

### Advanced Configuration

**Vector Search Settings**
```env
EMBEDDING_MODEL=all-MiniLM-L6-v2
EMBEDDING_DIMENSIONS=384
SEARCH_TIMEOUT=30
MAX_SEARCH_RESULTS=100
```

**Trending Analysis**
```env
TRENDING_WINDOW_HOURS=24
MIN_ARTICLES_FOR_TREND=3
MIN_SOURCES_FOR_TREND=2
VIRAL_THRESHOLD=0.8
```

**Source Health Monitoring**
```env
HEALTH_CHECK_INTERVAL=3600
CLOUDFLARE_DETECTION=true
PAYWALL_DETECTION=true
ALERT_THRESHOLD=0.3
```

## 📱 User Interface

### Dashboard Tabs

1. **Browse** - Traditional article browsing with AI enhancement
2. **Recommended** - ML-powered personalized content discovery
3. **Search** - Semantic search with vector similarity
4. **Fediverse** - Mastodon content monitoring and discovery
5. **Health** - Source monitoring and failure detection
6. **Trending** - Real-time trend analysis and viral content
7. **Spotlight** - Featured content and important updates

### Key Features

- **Real-Time Updates**: Live content refresh without page reload
- **Advanced Filtering**: Multi-dimensional content filtering
- **Source Management**: Add/remove sources with health monitoring  
- **Quality Control**: Spam detection and content quality assessment
- **Export Capabilities**: Data export and API access

## 🔍 API Reference

### Intelligence APIs

#### Vector Search
```http
POST /api/vector-search/search
{
  "query": "artificial intelligence trends",
  "limit": 20,
  "semantic_weight": 0.7,
  "keyword_weight": 0.3
}
```

#### Trending Analysis
```http
POST /api/trending/analyze
{
  "hours_back": 24,
  "min_articles": 3,
  "include_predictions": true
}

GET /api/trending/topics?limit=20&min_score=0.6
```

#### Source Health Monitoring
```http
GET /api/source-health/overview?days=7
GET /api/source-health/problematic?min_severity=medium
POST /api/source-health/analyze
```

#### Fediverse Integration
```http
GET /api/fediverse/instances
POST /api/fediverse/sources
{
  "source_type": "account",
  "identifier": "username",
  "instance_domain": "mastodon.social"
}

GET /api/fediverse/hashtag/{hashtag}?instance_domain=mastodon.social
```

### Content Management

#### Article Operations
```http
GET /api/items?min_score=50&source=example.com&page=1
POST /api/items/{id}/decide
{
  "action": "star|archive|downvote",
  "label": "important"
}
```

#### Recommendations
```http
GET /api/recommendations?limit=20&explanation=true
POST /api/personalization/feedback
{
  "article_id": 123,
  "action": "like|dislike|share"
}
```

## 🛠️ Development

### Adding New Intelligence Features

1. **Create Service Class**
   ```python
   # backend/app/services/your_service.py
   class YourIntelligenceService:
       async def analyze_content(self, content: str):
           # Your analysis logic
           pass
   ```

2. **Add API Router**
   ```python
   # backend/app/api/your_api.py
   from fastapi import APIRouter
   router = APIRouter()
   
   @router.post("/analyze")
   async def analyze_endpoint(request: YourRequest):
       # Your API logic
       pass
   ```

3. **Register Router**
   ```python
   # backend/app/main.py
   from .api.your_api import router as your_router
   app.include_router(your_router, prefix="/api/your-feature")
   ```

4. **Add Frontend Component**
   ```typescript
   // web/src/components/YourTab.tsx
   const YourTab = () => {
     // Your React component
     return <div>Your Feature</div>
   }
   ```

### Testing

```bash
# Backend tests
docker-compose exec backend pytest tests/ -v

# Frontend tests  
docker-compose exec web npm test

# Integration tests
docker-compose exec backend pytest tests/integration/ -v

# Load testing
docker-compose exec backend python tests/load_test.py
```

## 📊 Performance & Scaling

### Current Capabilities

- **Articles**: Handle millions of articles with efficient indexing
- **Search**: Sub-second semantic search response times
- **Real-Time**: WebSocket updates to thousands of concurrent users
- **AI Processing**: Parallel content analysis pipeline
- **Vector Database**: Scalable similarity search with Weaviate

### Optimization Features

- **Intelligent Caching**: Multi-layer caching strategy
- **Database Optimization**: Efficient queries and indexes
- **Content Processing**: Async pipeline with rate limiting  
- **Resource Management**: Docker resource limits and health checks
- **CDN Integration**: Static asset optimization

### Scaling Options

- **Horizontal Scaling**: Multi-instance deployment support
- **Database Clustering**: PostgreSQL read replicas
- **Vector Database**: Weaviate cluster configuration
- **Cache Scaling**: Redis cluster setup
- **Load Balancing**: Nginx upstream configuration

## 🔐 Security & Privacy

### Security Features

- **API Security**: Rate limiting, input validation, CORS protection
- **Authentication**: Secure session management and user isolation
- **Data Protection**: Environment-based secrets management
- **Network Security**: Internal service communication restrictions
- **SSL/TLS**: Automated certificate management with Let's Encrypt

### Privacy Controls

- **Data Minimization**: Only collect necessary user interaction data
- **Anonymization**: Pseudonymized user tracking for ML training
- **Opt-Out Options**: User control over data collection and processing
- **External Privacy**: No tracking on external link clicks
- **Local Processing**: Image caching respects user privacy

## 📈 Monitoring & Operations

### System Monitoring

```bash
# Health status
curl http://localhost:8000/health

# System metrics  
curl http://localhost:8000/system/metrics

# Service status
curl http://localhost:8000/api/intelligence/status
curl http://localhost:8000/api/vector-search/health
```

### Operational Commands

```bash
# Service management
docker-compose ps                    # Check service status
docker-compose logs -f backend      # Monitor logs
docker-compose restart backend      # Restart service

# Database operations
docker-compose exec backend alembic upgrade head    # Migrate
docker-compose exec postgres pg_dump rssintel > backup.sql  # Backup

# Cache operations
docker-compose exec backend python -c "
from app.cache_service import cache_service
print(cache_service.get_cache_stats())
"
```

### Production Monitoring

When deployed with monitoring enabled:

- **Prometheus**: http://localhost:9090 - Metrics collection
- **Grafana**: http://localhost:3001 - Visualization dashboards  
- **Alerting**: Email/Slack notifications for system issues
- **Log Aggregation**: Centralized logging with retention policies

## 🤝 Contributing

### Development Workflow

1. **Fork Repository** and create feature branch
2. **Set Up Environment** with development configuration  
3. **Write Tests** for new functionality
4. **Follow Code Style** - Python PEP 8, TypeScript ESLint
5. **Update Documentation** for API changes
6. **Submit Pull Request** with detailed description

### Code Standards

- **Backend**: FastAPI, async/await, type hints, comprehensive logging
- **Frontend**: React hooks, TypeScript, responsive design, accessibility
- **Database**: Alembic migrations, optimized queries, proper indexing
- **Testing**: Unit tests, integration tests, performance tests
- **Documentation**: Inline comments, API documentation, user guides

## 📄 License

MIT License - see LICENSE file for details.

## 🆘 Support & Community

- **Documentation**: Comprehensive guides in `/docs` directory
- **API Reference**: Interactive documentation at `/docs` endpoint  
- **GitHub Issues**: Bug reports and feature requests
- **Community Forum**: Discussions and user support
- **Professional Support**: Enterprise support available

---

**RSS Intelligence Dashboard** - Transform your content consumption into intelligent insights.

*Built with ❤️ using FastAPI, Next.js, PostgreSQL, Weaviate, and OpenAI*