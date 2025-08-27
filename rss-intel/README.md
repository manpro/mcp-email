# RSS Intelligence Dashboard

A production-ready intelligent RSS aggregation and analytics system with advanced AI features, real-time updates, and comprehensive monitoring capabilities.

## Overview

The RSS Intelligence Dashboard is a sophisticated content analysis platform that automatically discovers, analyzes, and categorizes articles from multiple RSS sources. Built with modern microservices architecture, it features advanced machine learning capabilities, real-time processing, and production-grade deployment infrastructure.

## Key Features

### 🤖 Advanced AI Intelligence
- **Smart Trend Detection**: Semantic clustering with DBSCAN to identify emerging trends across sources
- **Content Classification**: Ensemble ML approach with 10 major categories (Tech, Finance, Politics, etc.)
- **Sentiment Analysis**: Multi-layered pipeline with contextual domain adaptation and emotion detection
- **Keyword Extraction**: Advanced NLP combining TF-IDF, TextRank, pattern matching, and NER
- **Quality Assessment**: 6-dimensional scoring (readability, informativeness, credibility, etc.)
- **Duplicate Detection**: Real-time similarity detection with multiple algorithms

### 🔄 Real-time Foundation
- **Event-Driven Architecture**: Redis Streams for reliable event processing
- **WebSocket Hub**: Real-time notifications and live updates
- **Push Notifications**: Browser notifications for significant trends and alerts
- **Live Analytics**: Real-time content analysis and trend monitoring

### 🎯 Content Intelligence
- **Smart Scoring**: Multi-signal ranking with keyword matching, source reputation, and recency decay
- **Watchlist Tracking**: Monitor specific entities (companies, products, people) with custom weights
- **Image Extraction**: Automatic image discovery with caching and optimization
- **Automated Labeling**: Dynamic categorization with configurable thresholds

### 💻 Modern User Interface
- **Responsive Design**: Built with Next.js 14, TypeScript, and Tailwind CSS
- **Multiple View Modes**: Card view, list view, and spotlight mode for different use cases
- **Advanced Filtering**: Filter by score, sentiment, category, source, and custom criteria
- **Real-time Updates**: Live content updates without page refresh
- **Virtualization**: Handle thousands of articles with smooth performance

### 🚀 Production Infrastructure
- **Docker Containerization**: Complete production deployment with Docker Compose
- **SSL/TLS Support**: Automated Let's Encrypt certificate management
- **Load Balancing**: Nginx reverse proxy with rate limiting and caching
- **Health Monitoring**: Comprehensive health checks and metrics collection
- **Backup System**: Automated database backups with retention policies

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

## Architecture

### Core Services

- **PostgreSQL**: Primary database with optimized indexes for fast queries
- **Redis**: Caching layer and event streaming with Redis Streams
- **Weaviate**: Vector database for semantic search and similarity detection
- **Backend (FastAPI)**: AI engine with comprehensive REST API
- **Frontend (Next.js)**: Modern web application with real-time features
- **Nginx**: Reverse proxy with SSL termination and caching

### AI Intelligence Pipeline

```mermaid
graph TB
    A[RSS Sources] --> B[Content Ingestion]
    B --> C[Content Analysis]
    C --> D[Trend Detection]
    C --> E[Sentiment Analysis]
    C --> F[Classification]
    C --> G[Keyword Extraction]
    D --> H[Real-time Notifications]
    E --> H
    F --> H
    G --> H
    H --> I[WebSocket Hub]
    I --> J[Frontend Updates]
```

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

## API Reference

### Intelligence Endpoints

```bash
# Comprehensive content analysis
POST /api/intelligence/analyze
{
  "content": "Article content...",
  "title": "Article title",
  "source": "example.com"
}

# Trend detection
GET /api/intelligence/trends
POST /api/intelligence/detect-trends

# Content classification  
POST /api/intelligence/classify
{
  "content": "Article content...",
  "title": "Article title"
}

# Sentiment analysis
POST /api/intelligence/sentiment
{
  "content": "Article content..."
}

# Keyword extraction
POST /api/intelligence/keywords
{
  "content": "Article content...",
  "max_keywords": 10
}

# Quality assessment
POST /api/intelligence/quality
{
  "content": "Article content...",
  "title": "Article title"
}

# Similarity detection
POST /api/intelligence/similarity
{
  "content": "Article content...",
  "threshold": 0.8
}

# System status
GET /api/intelligence/status
```

### Real-time Features

```bash
# WebSocket connection for live updates
ws://localhost:8000/ws/live

# Push notification subscription
POST /api/notifications/subscribe
{
  "endpoint": "...",
  "keys": {...}
}
```

### Search and Analytics

```bash
# Enhanced search with AI features
GET /api/search?q=artificial+intelligence&category=technology&sentiment=positive

# Ask AI about content
POST /api/ask
{
  "question": "What are the main trends in AI this week?",
  "context": "technology"
}

# Cache management
GET /api/cache/status
POST /api/cache/warm-up
DELETE /api/cache/clear
```

## Configuration

### Environment Variables

**Core Settings**
```env
# Database
DATABASE_URL=postgresql://rss:password@postgres:5432/rssintel

# Vector Database  
WEAVIATE_URL=http://weaviate:8080

# Cache
REDIS_HOST=redis
REDIS_PORT=6379

# AI Features
OPENAI_API_KEY=your_api_key_here

# Real-time Features
SCHEDULER_ENABLED=true
WEBSOCKET_ENABLED=true
NOTIFICATIONS_ENABLED=true
```

**Production Settings**
```env
# Domain and SSL
DOMAIN=your-domain.com
SSL_EMAIL=admin@your-domain.com

# Security
POSTGRES_PASSWORD=strong_database_password
REDIS_PASSWORD=strong_redis_password

# Performance
POSTGRES_MAX_CONNECTIONS=200
REDIS_MAXMEMORY=512mb

# Monitoring
PROMETHEUS_ENABLED=true
GRAFANA_ENABLED=true
```

### Intelligence Configuration

**Trend Detection** (`config/trends.yml`)
```yaml
detection:
  min_cluster_size: 3
  similarity_threshold: 0.7
  time_window_hours: 24
  
notification_thresholds:
  significant_trend: 10
  breaking_trend: 20
```

**Classification** (`config/classification.yml`)
```yaml
categories:
  technology:
    keywords: ["AI", "machine learning", "blockchain"]
    weight: 1.2
  finance:
    keywords: ["payment", "fintech", "banking"]
    weight: 1.1
```

**Sentiment Analysis** (`config/sentiment.yml`)
```yaml
domain_adjustments:
  finance:
    positive_boost: 0.1
    negative_penalty: 0.05
  technology:
    neutral_threshold: 0.6
```

## Performance Optimization

### Caching Strategy

- **Search Results**: 10-minute TTL with intelligent invalidation
- **AI Analysis**: 30-minute TTL for expensive operations
- **Trends**: 1-hour TTL with background refresh
- **Images**: 30-day TTL with CDN-style headers

### Database Optimization

- **Strategic Indexes**: GIN indexes for full-text and JSON operations
- **Connection Pooling**: Optimized pool size (20) with overflow (30)
- **Query Optimization**: Efficient queries for common operations
- **Concurrent Operations**: Safe concurrent index creation

### Frontend Performance

- **Code Splitting**: Separate bundles for vendor libraries
- **Bundle Optimization**: Advanced webpack configuration
- **Image Optimization**: Next.js Image component with lazy loading
- **Virtual Scrolling**: Handle large datasets efficiently

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

## Development

### Local Development

```bash
# Start development environment
docker-compose -f docker-compose.dev.yml up -d

# Run tests
docker-compose exec backend pytest -v

# Watch frontend changes
docker-compose exec web npm run dev

# Database migrations
docker-compose exec backend alembic revision --autogenerate -m "description"
docker-compose exec backend alembic upgrade head
```

### Adding Intelligence Features

1. **Create new analyzer** in `backend/app/intelligence/`
2. **Add API endpoint** in `backend/app/api/intelligence.py`
3. **Update scheduler** in `backend/app/scheduler.py` if needed
4. **Add frontend components** in `web/src/components/`
5. **Write tests** in `backend/tests/`

### Testing

```bash
# Backend unit tests
docker-compose exec backend pytest tests/

# Integration tests
docker-compose exec backend pytest tests/integration/

# Frontend tests
docker-compose exec web npm test

# E2E tests
docker-compose exec web npm run test:e2e
```

## Production Considerations

### Security

- **SSL/TLS**: Automatic Let's Encrypt certificates
- **Rate Limiting**: API endpoint protection
- **Security Headers**: Comprehensive HTTP security headers
- **Input Validation**: Strict request validation
- **Access Control**: Network-level restrictions for internal services

### Scalability

- **Horizontal Scaling**: Services designed for multi-instance deployment
- **Database Optimization**: Efficient queries and indexing
- **Caching Strategy**: Multi-layer caching for performance
- **Resource Management**: Docker resource limits and health checks

### Backup and Recovery

- **Automated Backups**: Daily PostgreSQL dumps with retention
- **Configuration Backup**: Version-controlled configuration files
- **Disaster Recovery**: Complete deployment automation
- **Data Migration**: Safe upgrade and rollback procedures

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