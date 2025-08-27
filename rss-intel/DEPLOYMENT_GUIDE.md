# RSS Intelligence Dashboard - Complete Deployment Guide

## Overview

This guide covers all deployment scenarios for the RSS Intelligence Dashboard, from local development to production deployment with full monitoring, SSL, and high availability.

## 🏗️ Architecture Requirements

### Minimum System Requirements

**Development Environment:**
- CPU: 4 cores
- RAM: 8GB
- Storage: 20GB SSD
- Docker & Docker Compose

**Production Environment:**
- CPU: 8+ cores
- RAM: 32GB+
- Storage: 100GB+ SSD
- Docker & Docker Compose
- Load balancer (Nginx/HAProxy)

### Service Dependencies

**Core Services:**
- PostgreSQL 16+ (Primary database)
- Redis 7+ (Cache & event streaming)
- Weaviate 1.26+ (Vector database)

**External Services:**
- OpenAI API (GPT models)
- GitHub API (optional)
- Reddit API (optional)
- Mastodon instances (optional)

## 🚀 Quick Start Deployment

### 1. Development Setup

```bash
# Clone repository
git clone <repository-url>
cd rss-intel

# Copy environment template
cp .env.example .env

# Configure environment variables
vim .env
```

**Basic .env Configuration:**
```env
# Database
DATABASE_URL=postgresql://rss:password@postgres:5432/rssintel
WEAVIATE_URL=http://weaviate:8080
REDIS_HOST=redis
REDIS_PORT=6379

# AI Services
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4o-mini

# System Features
VECTOR_SEARCH_ENABLED=true
TRENDING_ANALYSIS_ENABLED=true
FEDIVERSE_ENABLED=true
SOURCE_HEALTH_MONITORING=true
```

```bash
# Start development environment
docker-compose up -d

# Initialize database
docker-compose exec backend alembic upgrade head

# Access services
# Web UI: http://localhost:3000
# API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

### 2. Production Deployment

```bash
# Copy production environment template
cp .env.production .env

# Configure for production
vim .env
```

**Production .env Configuration:**
```env
# Domain & SSL
DOMAIN=your-domain.com
SSL_EMAIL=admin@your-domain.com

# Database (use managed service in production)
DATABASE_URL=postgresql://rss:secure_password@db_host:5432/rssintel

# Security
POSTGRES_PASSWORD=very_secure_database_password
REDIS_PASSWORD=very_secure_redis_password

# Performance
POSTGRES_MAX_CONNECTIONS=200
REDIS_MAXMEMORY=2gb

# Monitoring
PROMETHEUS_ENABLED=true
GRAFANA_ENABLED=true
GRAFANA_ADMIN_PASSWORD=secure_grafana_password
```

```bash
# Deploy with SSL and monitoring
sudo ./deploy.sh deploy
```

## 🔧 Environment Configuration

### Core Environment Variables

#### Database Configuration
```env
# Primary Database
DATABASE_URL=postgresql://user:password@host:port/database
POSTGRES_PASSWORD=secure_password
POSTGRES_MAX_CONNECTIONS=200

# Vector Database
WEAVIATE_URL=http://weaviate:8080
WEAVIATE_API_KEY=optional_api_key

# Cache & Events
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=secure_password
REDIS_MAXMEMORY=2gb
```

#### AI & ML Services
```env
# OpenAI Integration
OPENAI_API_KEY=sk-proj-your_key_here
OPENAI_MODEL=gpt-4o-mini
OPENAI_MAX_TOKENS=1000
OPENAI_TEMPERATURE=0.1

# Embedding Configuration
EMBEDDING_MODEL=all-MiniLM-L6-v2
EMBEDDING_DIMENSIONS=384
EMBEDDING_BATCH_SIZE=100
```

#### Feature Toggles
```env
# Intelligence Features
VECTOR_SEARCH_ENABLED=true
TRENDING_ANALYSIS_ENABLED=true
FEDIVERSE_ENABLED=true
SOURCE_HEALTH_MONITORING=true
ML_RECOMMENDATIONS_ENABLED=true

# Content Processing
CONTENT_EXTRACTION_ENABLED=true
IMAGE_EXTRACTION_ENABLED=true
AUTOMATIC_CATEGORIZATION=true
```

#### Performance Tuning
```env
# Trending Analysis
TRENDING_WINDOW_HOURS=24
MIN_ARTICLES_FOR_TREND=3
MIN_SOURCES_FOR_TREND=2
VIRAL_THRESHOLD=0.8
TREND_CONFIDENCE_THRESHOLD=0.7

# Vector Search
SEARCH_TIMEOUT=30
MAX_SEARCH_RESULTS=100
SEMANTIC_WEIGHT=0.7
KEYWORD_WEIGHT=0.3

# Source Health
HEALTH_CHECK_INTERVAL=3600
CLOUDFLARE_DETECTION=true
PAYWALL_DETECTION=true
ALERT_THRESHOLD=0.3
```

#### External API Configuration
```env
# GitHub Integration
GITHUB_API_KEY=github_pat_your_token
GITHUB_RATE_LIMIT=5000

# Reddit Integration
REDDIT_CLIENT_ID=your_reddit_client_id
REDDIT_CLIENT_SECRET=your_reddit_client_secret
REDDIT_USER_AGENT=RSS-Intelligence-Bot/1.0

# HackerNews
HACKERNEWS_ENABLED=true
HACKERNEWS_FETCH_INTERVAL=300
```

### Security Configuration

```env
# SSL/TLS
SSL_ENABLED=true
DOMAIN=your-domain.com
SSL_EMAIL=admin@your-domain.com
FORCE_HTTPS=true

# Authentication
JWT_SECRET=very_secure_jwt_secret_key
JWT_EXPIRATION=3600
SESSION_SECRET=very_secure_session_secret

# CORS
ALLOWED_ORIGINS=https://your-domain.com,https://www.your-domain.com
ALLOWED_METHODS=GET,POST,PUT,DELETE,OPTIONS

# Rate Limiting
RATE_LIMIT_REQUESTS_PER_MINUTE=100
RATE_LIMIT_BURST=20
```

### Monitoring Configuration

```env
# Prometheus
PROMETHEUS_ENABLED=true
PROMETHEUS_PORT=9090
PROMETHEUS_RETENTION_DAYS=15

# Grafana
GRAFANA_ENABLED=true
GRAFANA_PORT=3001
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=secure_password

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
LOG_TO_FILE=true
LOG_ROTATION=daily
```

## 📦 Docker Deployment

### Development Docker Compose

**File**: `docker-compose.yml`
```yaml
version: '3.8'

services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - WEAVIATE_URL=${WEAVIATE_URL}
      - REDIS_HOST=redis
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    depends_on:
      - postgres
      - weaviate
      - redis
    volumes:
      - ./backend:/app
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  web:
    build: ./web
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:8000
    volumes:
      - ./web:/app
    command: npm run dev

  postgres:
    image: postgres:16
    environment:
      - POSTGRES_DB=rssintel
      - POSTGRES_USER=rss
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-password}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  weaviate:
    image: semitechnologies/weaviate:1.26.3
    ports:
      - "8080:8080"
    environment:
      QUERY_DEFAULTS_LIMIT: 25
      AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED: 'true'
      PERSISTENCE_DATA_PATH: '/var/lib/weaviate'
      DEFAULT_VECTORIZER_MODULE: 'none'
    volumes:
      - weaviate_data:/var/lib/weaviate

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes

volumes:
  postgres_data:
  weaviate_data:
  redis_data:
```

### Production Docker Compose

**File**: `docker-compose.prod.yml`
```yaml
version: '3.8'

services:
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./nginx/ssl:/etc/nginx/ssl
      - certbot_data:/var/www/certbot
    depends_on:
      - backend
      - web
    restart: unless-stopped

  certbot:
    image: certbot/certbot
    volumes:
      - certbot_data:/var/www/certbot
      - ./nginx/ssl:/etc/letsencrypt
    command: certonly --webroot -w /var/www/certbot --email ${SSL_EMAIL} --agree-tos --no-eff-email -d ${DOMAIN}

  backend:
    build: 
      context: ./backend
      dockerfile: Dockerfile.prod
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - WEAVIATE_URL=${WEAVIATE_URL}
      - REDIS_HOST=redis
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    depends_on:
      - postgres
      - weaviate
      - redis
    restart: unless-stopped
    deploy:
      replicas: 2
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G

  web:
    build:
      context: ./web
      dockerfile: Dockerfile.prod
    environment:
      - NEXT_PUBLIC_API_URL=https://${DOMAIN}
    restart: unless-stopped

  postgres:
    image: postgres:16
    environment:
      - POSTGRES_DB=rssintel
      - POSTGRES_USER=rss
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./backups:/backups
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 8G
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U rss"]
      interval: 30s
      timeout: 10s
      retries: 3

  weaviate:
    image: semitechnologies/weaviate:1.26.3
    environment:
      QUERY_DEFAULTS_LIMIT: 25
      AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED: 'true'
      PERSISTENCE_DATA_PATH: '/var/lib/weaviate'
      DEFAULT_VECTORIZER_MODULE: 'none'
    volumes:
      - weaviate_data:/var/lib/weaviate
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 16G
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/v1/.well-known/live"]
      interval: 30s
      timeout: 10s
      retries: 3

  redis:
    image: redis:7-alpine
    environment:
      - REDIS_PASSWORD=${REDIS_PASSWORD}
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes --requirepass ${REDIS_PASSWORD} --maxmemory ${REDIS_MAXMEMORY:-2gb} --maxmemory-policy allkeys-lru
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "--raw", "incr", "ping"]
      interval: 30s
      timeout: 3s
      retries: 5

  # Monitoring Stack
  prometheus:
    image: prom/prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'
      - '--storage.tsdb.retention.time=${PROMETHEUS_RETENTION_DAYS:-15}d'
      - '--web.enable-lifecycle'
    restart: unless-stopped

  grafana:
    image: grafana/grafana
    ports:
      - "${GRAFANA_PORT:-3001}:3000"
    environment:
      - GF_SECURITY_ADMIN_USER=${GRAFANA_ADMIN_USER:-admin}
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_ADMIN_PASSWORD}
    volumes:
      - grafana_data:/var/lib/grafana
      - ./monitoring/grafana/dashboards:/etc/grafana/provisioning/dashboards
      - ./monitoring/grafana/datasources:/etc/grafana/provisioning/datasources
    restart: unless-stopped

volumes:
  postgres_data:
  weaviate_data:
  redis_data:
  prometheus_data:
  grafana_data:
  certbot_data:
```

## 🌐 Nginx Configuration

**File**: `nginx/nginx.conf`
```nginx
events {
    worker_connections 1024;
}

http {
    include       /etc/nginx/mime.types;
    default_type  application/octet-stream;

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=100r/m;
    limit_req_zone $binary_remote_addr zone=search:10m rate=20r/m;

    # SSL Configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-SHA384;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;

    # Gzip Configuration
    gzip on;
    gzip_vary on;
    gzip_min_length 1000;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types
        application/atom+xml
        application/geo+json
        application/javascript
        application/x-javascript
        application/json
        application/ld+json
        application/manifest+json
        application/rdf+xml
        application/rss+xml
        application/xhtml+xml
        application/xml
        font/eot
        font/otf
        font/ttf
        image/svg+xml
        text/css
        text/javascript
        text/plain
        text/xml;

    # Security Headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin";

    # HTTP to HTTPS redirect
    server {
        listen 80;
        server_name ${DOMAIN} www.${DOMAIN};
        
        location /.well-known/acme-challenge/ {
            root /var/www/certbot;
        }
        
        location / {
            return 301 https://$server_name$request_uri;
        }
    }

    # HTTPS Configuration
    server {
        listen 443 ssl http2;
        server_name ${DOMAIN} www.${DOMAIN};

        ssl_certificate /etc/letsencrypt/live/${DOMAIN}/fullchain.pem;
        ssl_certificate_key /etc/letsencrypt/live/${DOMAIN}/privkey.pem;

        # Frontend
        location / {
            proxy_pass http://web:3000;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection 'upgrade';
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_cache_bypass $http_upgrade;
            proxy_read_timeout 86400;
        }

        # API Backend
        location /api/ {
            limit_req zone=api burst=20 nodelay;
            proxy_pass http://backend:8000/api/;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection 'upgrade';
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_cache_bypass $http_upgrade;
        }

        # Search endpoints with stricter rate limiting
        location /api/vector-search/ {
            limit_req zone=search burst=5 nodelay;
            proxy_pass http://backend:8000/api/vector-search/;
            proxy_http_version 1.1;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # WebSocket support
        location /ws/ {
            proxy_pass http://backend:8000/ws/;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_read_timeout 86400;
        }

        # Health checks
        location /health {
            proxy_pass http://backend:8000/health;
            access_log off;
        }

        # Static files with caching
        location ~* \\.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
            proxy_pass http://web:3000;
        }
    }

    # Monitoring endpoints (optional)
    server {
        listen 9090;
        server_name ${DOMAIN};
        
        location / {
            proxy_pass http://prometheus:9090;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            
            # Basic auth for monitoring
            auth_basic "Monitoring";
            auth_basic_user_file /etc/nginx/monitoring.htpasswd;
        }
    }
}
```

## 📊 Monitoring Setup

### Prometheus Configuration

**File**: `monitoring/prometheus.yml`
```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "rules/*.yml"

scrape_configs:
  - job_name: 'rss-intelligence-backend'
    static_configs:
      - targets: ['backend:8000']
    metrics_path: '/metrics'
    scrape_interval: 30s

  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres-exporter:9187']

  - job_name: 'redis'
    static_configs:
      - targets: ['redis-exporter:9121']

  - job_name: 'node'
    static_configs:
      - targets: ['node-exporter:9100']

alerting:
  alertmanagers:
    - static_configs:
        - targets: ['alertmanager:9093']
```

### Grafana Dashboards

**File**: `monitoring/grafana/dashboards/dashboard.json`
```json
{
  "dashboard": {
    "title": "RSS Intelligence Dashboard",
    "panels": [
      {
        "title": "Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(http_requests_total[5m])",
            "legendFormat": "Requests/sec"
          }
        ]
      },
      {
        "title": "Response Time",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))",
            "legendFormat": "95th percentile"
          }
        ]
      },
      {
        "title": "Database Connections",
        "type": "singlestat",
        "targets": [
          {
            "expr": "pg_stat_database_numbackends",
            "legendFormat": "Active connections"
          }
        ]
      }
    ]
  }
}
```

## 🔄 Database Migrations

### Initialize Database

```bash
# Create initial migration
docker-compose exec backend alembic revision --autogenerate -m "Initial migration"

# Apply migration
docker-compose exec backend alembic upgrade head

# Check migration status
docker-compose exec backend alembic current
```

### Migration Best Practices

```bash
# Always backup before migrations
docker-compose exec postgres pg_dump rssintel > backup_$(date +%Y%m%d_%H%M%S).sql

# Test migrations on copy first
docker-compose exec postgres createdb rssintel_test
docker-compose exec postgres pg_restore -d rssintel_test backup_latest.sql

# Apply migration to test database
DATABASE_URL=postgresql://rss:password@postgres:5432/rssintel_test \
docker-compose exec backend alembic upgrade head
```

## 🔐 SSL Certificate Setup

### Automatic SSL with Let's Encrypt

```bash
# Initial certificate request
docker-compose run --rm certbot certonly --webroot \
  -w /var/www/certbot \
  --email admin@your-domain.com \
  --agree-tos \
  --no-eff-email \
  -d your-domain.com

# Auto-renewal setup (add to crontab)
0 12 * * * docker-compose run --rm certbot renew --quiet && docker-compose exec nginx nginx -s reload
```

### Manual SSL Certificate

```bash
# Copy certificates to nginx/ssl/
cp fullchain.pem nginx/ssl/
cp privkey.pem nginx/ssl/

# Update nginx configuration
vim nginx/nginx.conf
# Update ssl_certificate and ssl_certificate_key paths
```

## 📋 Health Monitoring

### Health Check Endpoints

```bash
# System health
curl https://your-domain.com/health

# Database health
curl https://your-domain.com/api/health/database

# Vector database health
curl https://your-domain.com/api/vector-search/health

# Intelligence services health
curl https://your-domain.com/api/intelligence/status
```

### Automated Health Monitoring

**File**: `scripts/health-check.sh`
```bash
#!/bin/bash

DOMAIN="https://your-domain.com"
SLACK_WEBHOOK="https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK"

check_endpoint() {
    local endpoint=$1
    local name=$2
    
    if ! curl -sf "$DOMAIN$endpoint" > /dev/null; then
        curl -X POST -H 'Content-type: application/json' \
            --data "{\"text\":\"🚨 $name is DOWN: $DOMAIN$endpoint\"}" \
            $SLACK_WEBHOOK
        return 1
    fi
    return 0
}

# Check all critical endpoints
check_endpoint "/health" "System Health"
check_endpoint "/api/health/database" "Database"
check_endpoint "/api/vector-search/health" "Vector Search"

echo "Health check completed"
```

## 🔄 Backup & Recovery

### Database Backup

```bash
# Daily backup script
#!/bin/bash
BACKUP_DIR="/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup
docker-compose exec postgres pg_dump rssintel > $BACKUP_DIR/rssintel_$DATE.sql

# Compress backup
gzip $BACKUP_DIR/rssintel_$DATE.sql

# Keep only last 30 days
find $BACKUP_DIR -name "*.sql.gz" -mtime +30 -delete

# Upload to cloud storage (optional)
aws s3 cp $BACKUP_DIR/rssintel_$DATE.sql.gz s3://your-backup-bucket/
```

### Vector Database Backup

```bash
# Backup Weaviate data
docker-compose exec weaviate weaviate-tools export --scheme http --host localhost:8080 \
  --output /var/lib/weaviate/backup_$(date +%Y%m%d).json
```

### Recovery Process

```bash
# Stop services
docker-compose down

# Restore database
docker-compose up -d postgres
gunzip -c backup_20250827_120000.sql.gz | \
docker-compose exec -T postgres psql -U rss -d rssintel

# Restore vector database
docker-compose up -d weaviate
docker-compose exec weaviate weaviate-tools import --scheme http --host localhost:8080 \
  --input /var/lib/weaviate/backup_20250827.json

# Restart all services
docker-compose up -d
```

## 🚀 Performance Optimization

### Database Optimization

```sql
-- Add performance indexes
CREATE INDEX CONCURRENTLY idx_articles_published_at_desc ON articles(published_at DESC);
CREATE INDEX CONCURRENTLY idx_articles_score_desc ON articles(score DESC);
CREATE INDEX CONCURRENTLY idx_trending_topics_score ON trending_topics(trend_score DESC);

-- Analyze tables
ANALYZE articles;
ANALYZE trending_topics;
ANALYZE source_health_reports;

-- Update statistics
SELECT pg_stat_reset();
```

### Redis Configuration

```bash
# Optimize Redis for production
redis-cli CONFIG SET save "900 1 300 10 60 10000"
redis-cli CONFIG SET maxmemory 4gb
redis-cli CONFIG SET maxmemory-policy allkeys-lru
redis-cli CONFIG SET timeout 0
redis-cli CONFIG SET tcp-keepalive 300
```

### Application Performance

```bash
# Backend optimization
export WORKERS=4
export MAX_REQUESTS=1000
export MAX_REQUESTS_JITTER=100

# Frontend optimization
export NODE_ENV=production
export NEXT_TELEMETRY_DISABLED=1
```

## 🔍 Troubleshooting

### Common Issues

**Services Not Starting:**
```bash
# Check service logs
docker-compose logs backend
docker-compose logs postgres
docker-compose logs weaviate

# Check port conflicts
netstat -tulpn | grep :8000
netstat -tulpn | grep :3000
```

**Database Connection Issues:**
```bash
# Test database connection
docker-compose exec backend python -c "
from app.database import engine
try:
    engine.connect()
    print('Database connection successful')
except Exception as e:
    print(f'Database connection failed: {e}')
"
```

**Vector Database Issues:**
```bash
# Check Weaviate status
curl http://localhost:8080/v1/.well-known/live
curl http://localhost:8080/v1/.well-known/ready

# Reset Weaviate schema
curl -X DELETE http://localhost:8080/v1/schema
```

**Performance Issues:**
```bash
# Check resource usage
docker stats

# Check database performance
docker-compose exec postgres psql -U rss -d rssintel -c "
SELECT query, mean_time, calls
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;"
```

### Log Analysis

```bash
# View logs in real-time
docker-compose logs -f backend | grep ERROR
docker-compose logs -f backend | grep -E "(trend|viral|health)"

# Export logs for analysis
docker-compose logs backend > backend_logs.txt
docker-compose logs postgres > postgres_logs.txt
```

## 📈 Scaling Strategies

### Horizontal Scaling

**Load Balancer Configuration:**
```yaml
# docker-compose.scale.yml
services:
  backend:
    deploy:
      replicas: 3
    
  nginx:
    depends_on:
      - backend
    # Update upstream configuration for multiple backends
```

**Database Read Replicas:**
```yaml
services:
  postgres-replica:
    image: postgres:16
    environment:
      - PGUSER=replicator
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
      - POSTGRES_MASTER_SERVICE=postgres
```

### Vertical Scaling

```yaml
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 8G
        reservations:
          cpus: '2'
          memory: 4G
```

## 🔒 Security Hardening

### Container Security

```dockerfile
# Use non-root user
FROM python:3.11-slim
RUN groupadd -r appuser && useradd -r -g appuser appuser
USER appuser

# Read-only filesystem
docker run --read-only --tmpfs /tmp rss-intelligence
```

### Network Security

```yaml
# Isolate services
networks:
  frontend:
    driver: bridge
  backend:
    driver: bridge
    internal: true
```

### Secrets Management

```bash
# Use Docker secrets for production
echo "secure_database_password" | docker secret create postgres_password -
echo "secure_openai_key" | docker secret create openai_api_key -
```

---

## 📞 Support & Maintenance

### Regular Maintenance Tasks

**Weekly:**
- Check service logs for errors
- Verify backup integrity
- Update dependency security patches
- Monitor resource usage trends

**Monthly:**
- Update container images
- Optimize database performance
- Review and update SSL certificates
- Analyze system performance metrics

**Quarterly:**
- Full system backup and recovery test
- Security audit and updates
- Performance optimization review
- Capacity planning assessment

### Emergency Response

**Service Down:**
1. Check health endpoints
2. Review recent logs
3. Restart affected services
4. Escalate if persistence

**Data Loss:**
1. Stop all services immediately
2. Assess damage scope
3. Restore from latest backup
4. Verify data integrity
5. Resume services gradually

---

*Deployment Guide Version: 2.0*  
*Last Updated: 2025-08-27*  
*For support, check logs at `/var/log/rss-intelligence/`*