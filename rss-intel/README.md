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

## 🌐 Hetzner Proxy Integration

RSS Intelligence använder nu automatiskt vår WireGuard proxy via Hetzner Cloud för:
- **Anonymiserad RSS-hämtning** via 95.216.172.130 
- **Geografiska bypass** för blockerade feeds
- **Förbättrad tillgänglighet** och prestanda

**Proxy är automatiskt aktiverat** när WireGuard-tunnel är igång. Se [HETZNER_PROXY_INTEGRATION.md](HETZNER_PROXY_INTEGRATION.md) för detaljer.

---

## Quick Start

### Development Setup

1. **Clone and Setup**
   ```bash
   git clone <repository>
   cd rss-intel
   cp .env.example .env
   ```

2. **Start Development Environment**
   ```bash
   docker-compose up -d
   ```

3. **Initialize Database**
   ```bash
   docker-compose exec backend alembic upgrade head
   make seed
   ```

4. **Access Services**
   - Web UI: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs
   - System Metrics: http://localhost:8000/system/metrics

### Production Deployment

1. **Prepare Environment**
   ```bash
   cp .env.production .env
   # Edit .env with your production settings
   ```

2. **Deploy with SSL**
   ```bash
   sudo ./deploy.sh deploy
   ```

3. **Enable Monitoring (Optional)**
   ```bash
   sudo PROMETHEUS_ENABLED=true ./deploy.sh deploy
   ```

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

### Intelligence Features

#### 1. Trend Detection (`/backend/app/intelligence/trend_detector.py`)
- **Semantic Clustering**: DBSCAN algorithm for identifying content clusters
- **Temporal Analysis**: Time-based pattern recognition
- **Cross-source Correlation**: Detect trends spanning multiple sources
- **Automated Notifications**: Real-time alerts for significant trends

#### 2. Content Classification (`/backend/app/intelligence/content_classifier.py`)
- **10 Major Categories**: Technology, Finance, Politics, Science, Business, etc.
- **Ensemble Approach**: Combines rule-based and ML methods
- **Confidence Scoring**: Classification certainty metrics
- **Custom Categories**: Support for domain-specific classification

#### 3. Sentiment Analysis (`/backend/app/intelligence/sentiment_analyzer.py`)
- **Multi-layered Pipeline**: VADER, TextBlob, and custom models
- **Domain Adaptation**: Context-aware sentiment for different content types
- **Emotion Detection**: 8 distinct emotions (joy, anger, fear, etc.)
- **Contextual Adjustment**: Sentiment modulation based on content domain

#### 4. Keyword Extraction (`/backend/app/intelligence/keyword_extractor.py`)
- **Multi-method Approach**: TF-IDF, TextRank, pattern matching, NER
- **Domain Patterns**: Specialized extraction for different content types
- **Named Entity Recognition**: Person, organization, location extraction
- **Technical Term Detection**: Automatic identification of technical terminology

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

## Monitoring and Operations

### Health Checks

```bash
# System health
curl http://localhost/health

# Component status
curl http://localhost/api/intelligence/status

# Cache statistics  
curl http://localhost/api/cache/status

# Database metrics
curl http://localhost/system/metrics
```

### Deployment Operations

```bash
# Full deployment
sudo ./deploy.sh deploy

# Update existing deployment
sudo ./deploy.sh update

# SSL certificate setup
sudo ./deploy.sh ssl

# Create manual backup
sudo ./deploy.sh backup

# View service logs
sudo ./deploy.sh logs backend

# Service status
sudo ./deploy.sh status
```

### Monitoring Stack (Optional)

When enabled with `PROMETHEUS_ENABLED=true`:

- **Prometheus**: Metrics collection and alerting
- **Grafana**: Visualization and dashboards (admin/password from env)
- **Node Exporter**: System metrics
- **Custom Metrics**: Application-specific monitoring

Access monitoring:
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3001

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

## Troubleshooting

### Common Issues

**AI Features Not Working**
- Check OpenAI API key configuration
- Verify vector database connectivity
- Monitor intelligence API endpoints

**Real-time Updates Not Working**
- Check WebSocket connection in browser dev tools
- Verify Redis connectivity
- Check scheduler status

**Performance Issues**
- Monitor cache hit rates
- Check database query performance
- Verify resource limits and scaling

**Deployment Issues**
- Check SSL certificate generation
- Verify domain DNS settings
- Monitor container health checks

### Debug Commands

```bash
# Check service dependencies
docker-compose ps

# Monitor logs in real-time
docker-compose logs -f backend

# Database connection test
docker-compose exec backend python -c "from app.deps import get_db_pool; print('DB OK')"

# Redis connectivity test
docker-compose exec backend python -c "import redis; r=redis.Redis(host='redis'); print(r.ping())"

# AI pipeline test
curl -X POST http://localhost:8000/api/intelligence/analyze \
  -H "Content-Type: application/json" \
  -d '{"content": "Test article content"}'
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Add tests for new functionality
4. Ensure all tests pass (`docker-compose exec backend pytest`)
5. Update documentation as needed
6. Submit a pull request

### Development Guidelines

- **Code Style**: Follow PEP 8 for Python, ESLint for JavaScript/TypeScript
- **Testing**: Maintain test coverage above 80%
- **Documentation**: Update README and API docs for new features
- **Security**: Never commit secrets or API keys
- **Performance**: Consider caching and optimization for new features

## License

MIT License - see LICENSE file for details.

## Support

- **Documentation**: Check this README and inline code comments
- **Issues**: Use GitHub Issues for bug reports and feature requests  
- **API Reference**: Access `/docs` endpoint for interactive API documentation
- **Health Checks**: Monitor `/health` and `/system/metrics` endpoints