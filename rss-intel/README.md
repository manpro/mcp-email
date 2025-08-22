# RSS Intelligence Dashboard

A self-hosted intelligent RSS aggregation and scoring system that automatically discovers, scores, and categorizes articles from multiple sources including RSS feeds and RSSHub routes.

## Features

- **Smart Scoring**: Articles are automatically scored based on keywords, source reputation, watchlist entities, and recency
- **FreshRSS Integration**: Uses FreshRSS as the RSS aggregator with full Reader API compatibility
- **RSSHub Support**: Automatically imports feeds from RSSHub for sites without native RSS
- **Intelligent Labeling**: Automatically applies labels and stars articles based on scoring thresholds
- **Web Interface**: Clean, responsive UI for browsing, filtering, and managing articles
- **Watchlist Tracking**: Track mentions of specific companies, products, or people
- **Real-time Updates**: Scheduled background processing with manual refresh capability

## Quick Start

1. **Clone and Setup**
   ```bash
   git clone <repository>
   cd rss-intel
   cp .env.example .env
   ```

2. **Start All Services**
   ```bash
   make up
   ```

3. **Initialize Database**
   ```bash
   make migrate
   make seed
   ```

4. **Access the Services**
   - Web UI: http://localhost:3001
   - FreshRSS UI: http://localhost:8081 (admin/adminadmin)
   - Backend API: http://localhost:8000
   - RSSHub: http://localhost:1200

## Architecture

### Services

- **PostgreSQL**: Main database for article storage and metadata
- **FreshRSS**: RSS aggregation with Google Reader API compatibility  
- **RSSHub**: RSS feeds for sites without native feeds
- **Backend (FastAPI)**: Scoring engine, FreshRSS integration, and API
- **Web (Next.js)**: User interface for browsing and managing articles

### Scoring Algorithm

Articles are scored using multiple signals:

1. **Keyword Matching** (0-50+ points)
   - Configurable keyword weights
   - Diminishing returns for repeated matches
   - Word boundary matching

2. **Watchlist Entities** (0-20+ points)
   - Track specific companies/people/products
   - Configurable weights per entity
   - Automatic label application

3. **Source Reputation** (0-15 points)
   - Domain-based scoring
   - Higher weights for trusted sources

4. **Recency Decay** (Multiplier: 0.1-1.0)
   - Exponential decay based on article age
   - Configurable half-life (default: 36 hours)

### Thresholds

- **Star** (default: 80+): Articles are starred in FreshRSS
- **Hot** (default: 80+): Applied "hot" label
- **Interesting** (default: 60+): Applied "interesting" label

## Configuration

### Environment Variables

Key settings in `.env`:

```env
# Scoring behavior
SCORING_HALF_LIFE_HOURS=36
SCORING_STAR_THRESHOLD=80
SCORING_INTEREST_THRESHOLD=60

# FreshRSS API user (must be created in FreshRSS)
FRESHRSS_API_USER=ai
FRESHRSS_API_PASS=strongpassword

# Scheduler
SCHEDULER_ENABLED=true
```

### Scoring Configuration

Edit `config/scoring.yml` to adjust keyword weights and thresholds:

```yaml
keywords:
  ai: 10
  payments: 12
  visa: 15

source_weights:
  finextra.com: 8
  bloomberg.com: 7

thresholds:
  star: 80
  interesting: 60
```

### Watchlist Configuration

Edit `config/watchlist.yml` to track entities:

```yaml
entities:
  - "Stripe"
  - "PayPal"
  - "Klarna"

weights:
  "Stripe": 14
  "PayPal": 13
```

### Feed Sources

Edit `config/sources.yml` to add RSS feeds and RSSHub routes:

```yaml
native_feeds:
  - "https://finextra.com/rss"
  - "https://techcrunch.com/feed"

rsshub:
  enabled: true
  routes:
    - "/github/trending/daily"
    - "/hackernews/best"
```

## Usage

### Web Interface

1. **Browse Articles**: View scored articles in a sortable table
2. **Filter & Search**: Filter by score, source, labels, or search text
3. **Quick Actions**: Star, label, or mark articles as read
4. **Manual Refresh**: Trigger immediate feed polling and scoring

### API Endpoints

```bash
# Get articles with filtering
curl "http://localhost:8000/items?min_score=70&source=finextra.com"

# Get single article
curl "http://localhost:8000/items/entry123"

# Star an article
curl -X POST "http://localhost:8000/items/entry123/decide" \
  -H "Content-Type: application/json" \
  -d '{"action": "star"}'

# Manual refresh
curl -X POST "http://localhost:8000/refresh"

# Get configuration
curl "http://localhost:8000/config"

# Health check
curl "http://localhost:8000/health"
```

### FreshRSS Integration

The system integrates with FreshRSS via the Google Reader API:

1. **Polling**: Fetches new entries every 10 minutes
2. **Scoring**: Calculates scores and applies labels
3. **Feedback**: Stars high-scoring articles and applies labels
4. **User Access**: Use FreshRSS interface for reading and OPML import

## Management Commands

```bash
# Start all services
make up

# Stop services
make down

# View logs
make logs

# Run database migrations
make migrate

# Seed initial data and config
make seed

# Manual refresh
make refresh

# Run tests
make test

# Reset everything
make reset

# Check status
make status
```

## Development

### Running Tests

```bash
# Backend tests only
docker compose run --rm backend pytest

# All tests
make test
```

### Adding New Features

1. **Scoring Signals**: Add new scoring logic in `backend/app/scoring.py`
2. **API Endpoints**: Extend `backend/app/main.py`
3. **UI Components**: Add React components in `web/src/components/`
4. **Configuration**: Update YAML configs in `config/`

### Database Changes

```bash
# Create new migration
docker compose exec backend alembic revision --autogenerate -m "description"

# Apply migrations
make migrate
```

## Monitoring

### Health Checks

```bash
# Overall system health
curl http://localhost:8000/health

# Scheduler status
curl http://localhost:8000/scheduler/status

# Service status
make status
```

### Logs

```bash
# All services
make logs

# Specific service
docker compose logs -f backend
docker compose logs -f freshrss
```

## Troubleshooting

### Common Issues

1. **FreshRSS API User Not Found**
   - Create API user in FreshRSS admin interface
   - Update credentials in `.env`

2. **No Articles Scoring High**
   - Check keyword configuration in `config/scoring.yml`
   - Verify feed sources are working
   - Lower thresholds temporarily

3. **RSSHub Feeds Not Working**
   - Check RSSHub service is running: `curl http://localhost:1200`
   - Verify routes in `config/sources.yml`
   - Check RSSHub documentation for route syntax

4. **Scoring Not Working**
   - Check scheduler status: `curl http://localhost:8000/scheduler/status`
   - Manually trigger refresh: `make refresh`
   - Check backend logs: `docker compose logs backend`

### Reset Data

```bash
# Reset everything including database
make reset

# Just reset articles (keep config)
docker compose exec postgres psql -U rss rssintel -c "TRUNCATE articles, runs;"
```

## Production Deployment

For production use:

1. **Environment Security**
   - Use strong passwords
   - Enable HTTPS with reverse proxy
   - Restrict database access

2. **Performance Tuning**
   - Adjust PostgreSQL settings for your hardware
   - Consider Redis for caching
   - Monitor memory usage

3. **Backup Strategy**
   - Regular PostgreSQL backups
   - Backup configuration files
   - Consider FreshRSS data export

4. **Monitoring**
   - Set up log aggregation
   - Monitor API response times
   - Alert on scoring failures

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## License

MIT License - see LICENSE file for details.