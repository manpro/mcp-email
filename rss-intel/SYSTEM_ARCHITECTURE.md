# RSS Intelligence Dashboard - Complete System Architecture

## Overview

RSS Intelligence Dashboard är ett AI-drivet innehållshanteringssystem som kombinerar traditionell RSS-aggregering med avancerad semantisk sökning, maskininlärning och OpenAI-förstärkt Q&A-funktionalitet.

## System Components

### 🗄️ Data Layer
- **PostgreSQL Database**: Primär datalagring för artiklar, användarhändelser och ML-modeller
- **Weaviate Vector Database**: Semantisk sökning med 5,680 chunks från 707 artiklar (86.9% coverage)
- **Content Extraction**: Full-text extraction med Readability och Newspaper3k
- **Image Processing**: Proxy-cache med Playwright-stöd för dynamiska bilder

### 🧠 AI & ML Stack
- **OpenAI GPT-4o-mini**: Q&A-generering med källhänvisningar
- **Sentence Transformers**: all-MiniLM-L6-v2 (384 dimensioner) för embeddings
- **Hybrid Search**: BM25 + semantisk sökning med Weaviate
- **ML Personalization**: Logistic Regression för läsannolikhetsprediktering
- **User Embeddings**: Personliga profiler baserade på läsbeteende

### 🔍 Search & Q&A Engine
- **RAG (Retrieval-Augmented Generation)**: Kombinerar semantisk sökning med OpenAI
- **Hybrid Search**: α-parameter för balans mellan BM25 och vektor-sökning
- **Fallback Mechanism**: Extraktiv metod när OpenAI inte tillgänglig
- **Confidence Scoring**: Automatisk bedömning av svarskvalitet

### 📊 Content Processing Pipeline
1. **RSS Ingestion**: FreshRSS integration för feeds
2. **Content Extraction**: Full-text med kvalitetsbedömning
3. **Text Chunking**: Överlappande segment för optimal sökning
4. **Vector Embedding**: Sentence Transformers processing
5. **ML Feature Extraction**: Artikel-metadata för personalisering

### 🖥️ Frontend Architecture
- **React/Next.js**: Modern SPA med server-side rendering
- **API Proxy**: Transparent backend-kommunikation
- **Multiple Views**: Browse, Search, Ask AI, Recommendations, Spotlight
- **Real-time Updates**: Auto-refresh med WebSocket-stöd

## API Endpoints

### Search & Q&A
- `GET /api/search` - Hybrid semantisk sökning
- `POST /api/ask` - AI-förstärkt Q&A med källor
- `GET /api/search/stats` - System-statistik
- `POST /api/search/refresh` - Index-uppdatering

### ML & Personalization
- `POST /api/personalization/train` - Träna ML-modeller
- `GET /api/recommend` - Personliga rekommendationer
- `POST /api/events` - Spåra användarhändelser
- `GET /api/ml/status` - ML-systemstatus

### Content Management
- `GET /api/articles` - Lista artiklar med filter
- `POST /api/articles/{id}/decide` - Märk artikel (stjärna/dölja)
- `GET /api/articles/{id}/content` - Full artikelinnehåll

## Performance Metrics

### Current System Status
- **Articles**: 1,304 totalt, 707 med extraherat innehåll
- **Vector Database**: 5,680 chunks, 86.9% coverage
- **Search Response**: <100ms för hybrid search
- **Q&A Generation**: 6-10 sekunder med OpenAI
- **ML Training**: ~30 dagar data för personalisering

### Scaling Capabilities
- **Database**: PostgreSQL med optimerade index
- **Vector Search**: Weaviate cluster-ready
- **Content Processing**: Parallell pipeline
- **API Rate Limits**: Konfigurerbar throttling

## Configuration

### Environment Variables
```bash
# Database
DATABASE_URL=postgresql://rss:password@postgres:5432/rssintel
WEAVIATE_URL=http://weaviate:8080

# AI Services
OPENAI_API_KEY=sk-proj-...
OPENAI_MODEL=gpt-4o-mini
OPENAI_MAX_TOKENS=1000
OPENAI_TEMPERATURE=0.1

# ML Settings
ML_CANDIDATE_DAYS=14
ML_MIN_RULE_SCORE=20
SCORING_HALF_LIFE_HOURS=36

# Content Processing
CONTENT_EXTRACTION_ENABLED=true
CONTENT_EXTRACTION_BATCH_SIZE=50
IMAGE_PROXY_ENABLED=true
```

### Docker Services
- `backend` - FastAPI application (Python 3.11)
- `web` - Next.js frontend (Node.js)
- `postgres` - Primary database (PostgreSQL 16)
- `weaviate` - Vector database (Weaviate 1.26.3)
- `freshrss` - RSS aggregation (FreshRSS latest)
- `rsshub` - RSS proxy service (RSSHub)

## Security & Privacy

### Data Protection
- Environment variables för API-nycklar
- Database-kryptering för känslig data
- Rate limiting för API-endpoints
- CORS-konfiguration för frontend

### User Privacy
- Pseudonymiserade användarhändelser
- Opt-out för ML-spårning
- Lokal image-cache för privacy
- No-tracking för externa länkar

## Monitoring & Observability

### Logging
- Structured logging med Python logging
- Request/response tracking
- ML model performance metrics
- Error aggregation och alerting

### Health Checks
- Database connectivity
- Vector database status
- OpenAI API availability
- Content extraction pipeline

## Deployment Architecture

### Production Stack
```yaml
services:
  - backend: FastAPI med Gunicorn
  - web: Next.js med nginx proxy
  - postgres: Managed PostgreSQL
  - weaviate: Dedicated vector cluster
  - redis: Caching och sessions
  - nginx: Load balancer och SSL
```

### Development Stack
```yaml
services:
  - Hot reload för backend/frontend
  - Local PostgreSQL med test data
  - Weaviate single-node
  - Mock OpenAI för testing
```

## Integration Points

### External Services
- **OpenAI API**: Q&A generation
- **FreshRSS**: RSS feed management
- **RSSHub**: RSS proxy och transformation
- **Image CDNs**: Extern bildhantering

### Data Flows
1. **Ingestion**: RSS → FreshRSS → Content Extraction → Vector Embedding
2. **Search**: Query → Hybrid Search → Weaviate → Results Ranking
3. **Q&A**: Question → RAG Pipeline → OpenAI → Formatted Response
4. **ML**: User Events → Feature Extraction → Model Training → Predictions

## Future Roadmap

### Phase 4: ML-Enhanced Search (Planned)
- Personalized search results baserad på användarbeteende
- Kontextuell förståelse av sökintention
- Adaptive ranking baserat på feedback
- Multi-modal search (text + bilder)

### Phase 5: Advanced AI Features
- Multi-språkstöd för Q&A
- Dokument-summarization
- Trend analysis och insights
- Automated content kategorisering

---

*Senast uppdaterad: 2025-08-25*
*System Version: 2.0*
*Status: Production Ready*