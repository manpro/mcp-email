# 📧 Email AI System - Arkitekturdokumentation

## 📋 Innehållsförteckning
1. [Systemöversikt](#systemöversikt)
2. [Arkitekturprinciper](#arkitekturprinciper)
3. [Komponenter](#komponenter)
4. [Dataflöde](#dataflöde)
5. [API Specifikation](#api-specifikation)
6. [Databaser & Cache](#databaser--cache)
7. [Säkerhet](#säkerhet)
8. [Deployment](#deployment)

## Systemöversikt

### Vision
Ett intelligent email-hanteringssystem som automatiskt kategoriserar, prioriterar och organiserar emails med hjälp av AI och maskininlärning.

### Arkitektur
```
┌─────────────────────────────────────────┐
│         Frontend (Port 3623)            │
│   React + Vite + Zustand + TailwindCSS  │
│      - UI/UX                            │
│      - Filtrering & Sortering           │
│      - Realtidsuppdateringar            │
└─────────────────────────────────────────┘
                    ↓ REST API
┌─────────────────────────────────────────┐
│         Backend API (Port 3015)         │
│          Node.js + Express              │
│      - Business Logic                   │
│      - AI Kategorisering                │
│      - Cache Management                 │
│      - Data Aggregering                 │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│        Data & Externa Tjänster          │
├─────────────────────────────────────────┤
│ IMAP Server │ Redis │ SQLite │ LLM API  │
│  (one.com)  │ Cache │  DB    │ (8085)   │
└─────────────────────────────────────────┘
```

## Arkitekturprinciper

### 1. **Separation of Concerns**
- Varje lager har tydligt definierat ansvar
- Ingen överlappning av funktionalitet mellan lager
- Tydliga gränssnitt mellan komponenter

### 2. **Simplicity First**
- Minsta möjliga antal komponenter
- Ingen onödig komplexitet
- Direkta kopplingar utan mellanhänder

### 3. **Security by Design**
- Credentials endast i backend
- Ingen känslig data i frontend
- Alla API-anrop valideras

### 4. **Resilience**
- Fallback-mekanismer för alla externa tjänster
- Graceful degradation vid fel
- Cache för prestanda och tillgänglighet

## Komponenter

### Frontend (Port 3623)
**Teknologi:** React, Vite, Zustand, TailwindCSS, Lucide Icons

**Ansvar:**
- ✅ Användargränssnitt
- ✅ Visualisering av emails
- ✅ Interaktiv filtrering och sökning
- ✅ Responsiv design
- ✅ Realtidsuppdateringar

**Komponenter:**
```
frontend/
├── src/
│   ├── components/
│   │   ├── EmailList.jsx       # Email-lista med kort
│   │   ├── SmartFilters.jsx    # Kategorifitrering
│   │   ├── SearchBar.jsx       # Sökfunktionalitet
│   │   └── EmailDetail.jsx     # Detaljvy för email
│   ├── stores/
│   │   └── emailStore.js       # Zustand state management
│   └── services/
│       └── api.js              # Backend API-kommunikation
```

### Backend API (Port 3015)
**Teknologi:** Node.js, Express, Axios, Better-SQLite3, Redis

**Ansvar:**
- ✅ IMAP-integration
- ✅ AI-kategorisering
- ✅ Business logic
- ✅ Cache-hantering
- ✅ Data persistens

**Moduler:**
```javascript
// Core Modules
integrated-email-service.js  // Huvudtjänst
ai-analyzer.js              // AI-kategorisering
database.js                 // SQLite-hantering
imap-client.js             // IMAP-kommunikation

// API Endpoints
/recent-emails/:accountId   // Hämta kategoriserade emails
/smart-inbox/:accountId     // AI-prioriterad inbox
/api/categories/stats       // Kategoristatistik
/health                     // Hälsokontroll
```

### Data & Externa Tjänster

#### IMAP Server (one.com)
- **Host:** imap.one.com
- **Port:** 993 (SSL/TLS)
- **Protokoll:** IMAP4rev1
- **Funktionalitet:** Email-hämtning

#### Redis Cache
- **Host:** 172.17.0.1
- **Port:** 6381
- **TTL-strategi:**
  - High priority: 1 timme
  - Medium priority: 1 dag
  - Low priority: 7 dagar

#### SQLite Database
- **Fil:** /app/data/email_categorizations.db
- **Tabeller:**
  - `categorizations` - AI-kategoriseringar
  - `email_cache` - Email metadata
  - `user_preferences` - Användarinställningar

#### LLM API (Optional)
- **Host:** localhost
- **Port:** 8085
- **Model:** GPT-OSS 20B eller liknande
- **Fallback:** Regelbaserad kategorisering

## Dataflöde

### Email-hämtning och kategorisering
```
1. Frontend: GET /recent-emails/primary
        ↓
2. Backend: Kontrollera Redis cache
        ↓ (cache miss)
3. Backend: Hämta från IMAP
        ↓
4. Backend: AI-kategorisering
        ↓
5. Backend: Spara i SQLite & Redis
        ↓
6. Backend: Returnera till Frontend
        ↓
7. Frontend: Visa kategoriserade emails
```

### Kategoriseringsprocess
```javascript
{
  input: {
    subject: "Meeting tomorrow",
    from: "boss@company.com",
    body: "Let's discuss the Q4 report..."
  },

  processing: {
    ai_analysis: "LLM eller regelbaserad",
    features_extracted: ["meeting", "report", "business"]
  },

  output: {
    category: "work",
    priority: "high",
    sentiment: "neutral",
    topics: ["meeting", "report"],
    action_required: true,
    summary: "Meeting request for Q4 report discussion",
    confidence: 0.92
  }
}
```

## API Specifikation

### GET /recent-emails/:accountId
**Beskrivning:** Hämtar senaste emails med AI-kategorisering

**Parameters:**
- `accountId`: string (required) - Konto-ID
- `limit`: number (optional, default: 50) - Antal emails

**Response:**
```json
[
  {
    "uid": "129398",
    "subject": "Q4 Report Meeting",
    "from": "boss@company.com",
    "date": "2025-09-23T10:00:00Z",
    "category": "work",
    "priority": "high",
    "sentiment": "neutral",
    "topics": ["meeting", "report"],
    "action_required": true,
    "summary": "Meeting request for Q4 report",
    "confidence": 0.92
  }
]
```

### GET /smart-inbox/:accountId
**Beskrivning:** AI-prioriterad inbox med viktigaste emails först

### GET /api/categories/stats/:accountId
**Beskrivning:** Statistik över email-kategorier

## Databaser & Cache

### Redis Cache Schema
```
Key: email:{accountId}:{uid}:ml
Value: {
  category: string,
  priority: string,
  sentiment: string,
  topics: array,
  cached_at: timestamp,
  ttl: number
}
```

### SQLite Schema
```sql
CREATE TABLE categorizations (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  email_uid TEXT UNIQUE NOT NULL,
  account_id TEXT NOT NULL,
  category TEXT NOT NULL,
  priority TEXT NOT NULL,
  sentiment TEXT,
  topics TEXT, -- JSON array
  action_required BOOLEAN DEFAULT 0,
  summary TEXT,
  confidence REAL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_account_uid (account_id, email_uid)
);
```

## Säkerhet

### Autentisering & Authorization
- IMAP-credentials lagras endast i backend environment variables
- Ingen känslig data exponeras till frontend
- API rate limiting implementerat

### Environment Variables
```bash
# Backend (.env)
IMAP_HOST=imap.one.com
IMAP_PORT=993
IMAP_USER=mikael@fallstrom.org
IMAP_PASSWORD=<encrypted>
REDIS_HOST=172.17.0.1
REDIS_PORT=6381
LLM_API_URL=http://localhost:8085
DATABASE_PATH=/app/data/email_cache.db
```

## Deployment

### Docker Compose
```yaml
version: '3.8'

services:
  email-backend:
    build: ./email-service
    ports:
      - "3015:3015"
    environment:
      - NODE_ENV=production
    volumes:
      - email-data:/app/data

  email-frontend:
    build: ./frontend
    ports:
      - "3623:3623"
    environment:
      - VITE_API_URL=http://172.16.16.148:3015
    depends_on:
      - email-backend

volumes:
  email-data:
```

### Produktionskrav
- Node.js 20+
- Redis 6+
- Docker & Docker Compose
- 2GB RAM minimum
- 10GB diskutrymme för cache/databas

## Monitoring & Logging

### Health Checks
- Backend: `/health` endpoint
- Frontend: Vite dev server health
- Redis: Connection monitoring
- IMAP: Connection status

### Metrics
- Email processing rate
- Categorization accuracy
- Cache hit rate
- API response times
- Error rates

## Underhåll

### Backup
- SQLite database: Daglig backup
- Redis: Persistent snapshot var 6:e timme
- Configuration: Version control (Git)

### Uppdateringar
- Zero-downtime deployment med Docker
- Database migrations med version control
- Feature flags för gradvis utrullning

---

*Version 2.0 - September 2025*
*Arkitekt: Claude Assistant*
*Status: Godkänd för implementation*