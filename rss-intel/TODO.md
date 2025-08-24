# RSS Intelligence - Development TODO

## ✅ Completed Phases

### ✅ Phase 0 - Base System
- [x] FreshRSS + RSSHub setup
- [x] PostgreSQL database
- [x] Next.js frontend
- [x] Basic scoring system
- [x] Docker Compose infrastructure

### ✅ Phase 1 - Images & UI
- [x] Image proxy/cache system
- [x] Blurhash generation
- [x] List/Card view toggle
- [x] Virtual scrolling
- [x] Pagination with "Load More"

### ✅ Phase 2 - Story Clustering
- [x] URL canonicalization
- [x] Content hash deduplication
- [x] SimHash for near-duplicates
- [x] Stories table and relationships
- [x] Clustering API endpoints
- [x] Automatic clustering scheduler (every 30 min)

### ✅ Phase 3 - Personalization
- [x] Events tracking system (impression, open, click, star, dismiss)
- [x] ML feature extraction
- [x] Logistic Regression model for p(read)
- [x] Model versioning and A/B testing support
- [x] Predictions table and scoring
- [x] Daily training scheduler (4 AM)
- [x] Hourly scoring of new articles

### ✅ Phase 4 - Spotlight (Daily Digest) ✅ COMPLETED!

### Core Features ✅ 
- [x] Daily digest generation at 07:00 Europe/Stockholm
- [x] Select top 3 "Must Read" articles  
- [x] Select up to 5 "Also Worth Reading" articles
- [x] Weighted scoring algorithm (rule_norm + p_read + trend + freshness)
- [x] Diversity rules (max per source/topic)
- [x] Watchlist integration for priority content

### Technical Implementation ✅
- [x] Create `spotlight_issues` and `spotlight_items` tables
- [x] Implement SpotlightEngine class
- [x] Add summary generation (1-2 sentences, ~220 chars)
- [x] Cache summaries per story_hash
- [x] Create `/spotlight/today` endpoint
- [x] Create `/spotlight/{date}` endpoint
- [x] Add scheduler job for daily generation
- [x] Export as RSS/JSON feed
- [ ] Slack webhook integration (future enhancement)

### UI Components ✅
- [x] ✅ Spotlight view in dashboard - COMPLETED!
- [x] ✅ Daily digest card design with rank badges
- [x] ✅ Summary display with expand option  
- [x] ✅ Share/export buttons (RSS feed)

**Current Status**: ✅ FULLY IMPLEMENTED AND WORKING!
- ✅ Backend: All API endpoints functional (today, generate, stats, RSS feed)
- ✅ SpotlightEngine: Generating quality digests with 6 articles  
- ✅ Scheduling: Automatic generation at 07:00 Europe/Stockholm
- ✅ Database: Proper migrations and schema
- ✅ Frontend: Complete Spotlight tab integration with beautiful UI
- ✅ API Integration: Full proxy support and data fetching
- ✅ Export: RSS feed functional and accessible

## 📋 Phase 5 - Additional Data Sources

### JSON Feed Support
- [ ] JSON Feed adapter
- [ ] Auto-discovery from HTML pages
- [ ] Normalization to Article model

### Sitemap/HTML Scraping
- [ ] Sitemap parser
- [ ] Readability integration
- [ ] Rate limiting and robots.txt respect
- [ ] Scheduled crawling

### API Integrations
- [ ] GitHub (releases, trending)
- [ ] HackerNews (top stories, Show HN)
- [ ] Reddit (subreddit monitoring)
- [ ] YouTube (channel feeds)
- [ ] arXiv (paper feeds)

### IMAP Newsletter Integration
- [ ] IMAP client setup
- [ ] Whitelist management
- [ ] "View online" URL extraction
- [ ] Newsletter-to-articles parser

### ActivityPub/Fediverse
- [ ] Mastodon account following
- [ ] Hashtag monitoring
- [ ] Stream processing

## 📋 Phase 6 - RAG/Weaviate Integration

### Search Infrastructure
- [ ] Article chunking (700-1000 tokens, 150 overlap)
- [ ] Embedding generation (bge-m3 or e5-base-v2)
- [ ] Weaviate schema setup
- [ ] Hybrid retrieval (vector + BM25)
- [ ] Cross-encoder re-ranking

### API Endpoints
- [ ] `/search` - Full-text and semantic search
- [ ] `/ask` - Question answering with citations
- [ ] `/similar` - Find related articles
- [ ] Language and freshness filters

### UI Components
- [ ] Search bar with auto-complete
- [ ] Search results page
- [ ] Ask interface with streaming responses
- [ ] Citation display

## 📋 Phase 7 - GPT-OSS Integration

### Infrastructure
- [ ] ROCm container setup (7900XTX)
- [ ] Model selection and quantization (4-5 bit)
- [ ] Health checks (/live, /ready)
- [ ] VRAM monitoring
- [ ] Queue management with backpressure

### Summarization Service
- [ ] Model checkpoint verification (SHA256)
- [ ] Prompt templates for summaries
- [ ] Caching layer per story_hash
- [ ] Fallback to heuristic extraction
- [ ] Rate limiting

### Integration Points
- [ ] Spotlight summaries
- [ ] Article TL;DR generation
- [ ] Topic summarization
- [ ] Q&A augmentation

## 📋 Phase 8 - Pro Features

### Topic Hubs
- [ ] Topic detection and clustering
- [ ] Topic pages with timelines
- [ ] Topic trending analysis
- [ ] Topic subscription

### Trend Radar
- [ ] Spike detection algorithms
- [ ] Anomaly detection
- [ ] Alert system
- [ ] Trend visualization

### Consensus vs Contrarian
- [ ] Stance detection
- [ ] Source bias analysis
- [ ] Contrarian viewpoint discovery
- [ ] Balanced presentation

### Watchlist Features
- [ ] Enhanced watchlist management
- [ ] Heatmap visualization
- [ ] "Missed but relevant" notifications
- [ ] Custom alert rules

## 🎨 UI/UX Improvements

### Dashboard Enhancements
- [ ] Recommended tab using ML predictions
- [ ] "Why" chips explaining recommendations
- [ ] Keyboard shortcuts (j/k navigation, s star, l label)
- [ ] Batch actions for multiple articles
- [ ] Saved views/filters
- [ ] URL sync for shareable views

### Performance
- [ ] Handle 5000+ items lag-free (≥45 FPS)
- [ ] CLS score ≈ 0
- [ ] Optimistic UI updates
- [ ] Progressive image loading
- [ ] Service worker for offline support

### Curator Tools
- [ ] Story split/merge UI
- [ ] Pin important stories
- [ ] Mute source/topic
- [ ] Undo/redo actions
- [ ] Bulk operations

## 🔧 Technical Debt & Improvements

### Data Quality
- [ ] Fix arXiv RSS feed parsing issues
- [x] ✅ Fixed: Frontend hydration errors (ViewToggle SSR/client mismatch)
- [x] ✅ Fixed: Lodash import compilation error 
- [ ] Improve content extraction success rate (currently 60%)
- [ ] Better image extraction from articles
- [ ] Handle paywalled content gracefully

### Observability
- [ ] Prometheus metrics
- [ ] Grafana dashboards
- [ ] Error tracking (Sentry integration)
- [ ] Performance monitoring
- [ ] User analytics (privacy-respecting)

### Testing
- [ ] Unit tests for scoring engine
- [ ] Integration tests for API endpoints
- [ ] E2E tests for critical user flows
- [ ] Load testing for scalability

### Documentation
- [ ] API documentation (OpenAPI/Swagger)
- [ ] User guide
- [ ] Admin guide
- [ ] Development setup guide
- [ ] Architecture documentation

## 🚦 Updated Priority Order

1. **✅ Phase 4 - Spotlight** ✅ FULLY COMPLETED WITH UI! (High impact, builds on existing ML)
2. **UI Recommended Tab** (Quick win, uses existing personalization) 
3. **Phase 5 - More Sources** (Increases content variety)
4. **Phase 6 - RAG/Search** (Advanced discovery features)
5. **Phase 7 - GPT-OSS** (Enhanced summaries)  
6. **Phase 8 - Pro Features** (Advanced analytics)

🎯 **Next Focus**: Recommended Tab implementation or Phase 5 data sources

## 📅 Updated Timeline (August 2025)

- **✅ Week 1**: Phase 4 (Spotlight) - COMPLETED!
  - Database schema, SpotlightEngine, API endpoints, RSS export, scheduler integration
  - Successfully generating daily digests with 6 quality articles 
  - All core features working: scoring, diversity rules, summaries, publishing
- **Week 2**: UI improvements + Spotlight view in dashboard
- **Week 3-4**: Phase 5 (Additional sources) - JSON feeds, APIs, IMAP
- **Week 5-6**: Phase 6 (RAG/Weaviate) - Search infrastructure  
- **Week 7-8**: Phase 7 (GPT-OSS) - Enhanced summaries with local LLM
- **Week 9-10**: Phase 8 (Pro features) - Advanced analytics

## 🎯 Success Metrics

- [ ] Spotlight CTR +15-20% vs baseline
- [ ] ML model AUC ≥0.70
- [ ] Clustering reduces duplicates by ≥80%
- [ ] Content extraction success rate ≥80%
- [ ] Search latency <400ms (warm)
- [ ] UI handles 5000+ items smoothly
- [ ] Daily active users growth
- [ ] User engagement time increase