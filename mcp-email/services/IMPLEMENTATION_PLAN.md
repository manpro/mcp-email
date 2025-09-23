# 🚀 Implementationsplan - Email AI System v2.0

## 📅 Översikt
**Mål:** Migrera från nuvarande fragmenterade arkitektur till förenklad 3-lagers arkitektur
**Tidsram:** 4-6 timmar
**Risk:** Låg (befintlig funktionalitet bevaras)
**Prioritet:** Hög

## 🎯 Målbild

### Före (Nuvarande)
```
Frontend (3623) → Proxy (3625) → MCP Server (3624) → IMAP
                ↘ Backend (3015) ↗
```
**Problem:** För många mellanled, komplext, svårt att debugga

### Efter (Målarkitektur)
```
Frontend (3623) → Backend (3015) → IMAP
```
**Fördelar:** Enkelt, direkt, lättunderhållet

## 📋 Fas 1: Förberedelse (30 min)

### 1.1 Stoppa onödiga tjänster
```bash
# Stoppa alla bakgrundsprocesser
- [ ] Kill MCP GUI Server (port 3624)
- [ ] Kill Email Proxy Server (port 3625)
- [ ] Kill Mock servers
- [ ] Stoppa Docker containers
```

### 1.2 Backup
```bash
# Säkerhetskopiera viktiga filer
- [ ] Backup SQLite database
- [ ] Backup .env filer
- [ ] Git commit nuvarande state
```

### 1.3 Dokumentation
```bash
- [ ] Dokumentera nuvarande portar och tjänster
- [ ] Notera IMAP credentials
- [ ] Lista beroenden
```

## 📋 Fas 2: Backend-refaktorering (2 timmar)

### 2.1 Skapa IMAP-modul
**Fil:** `email-service/imap-service.js`

```javascript
// Ny direkt IMAP-integration
class IMAPService {
  constructor(config) {
    this.config = {
      user: process.env.IMAP_USER,
      password: process.env.IMAP_PASSWORD,
      host: process.env.IMAP_HOST || 'imap.one.com',
      port: process.env.IMAP_PORT || 993,
      tls: true,
      authTimeout: 10000
    };
  }

  async connect() { /* ... */ }
  async fetchRecent(limit = 50) { /* ... */ }
  async search(criteria) { /* ... */ }
  async disconnect() { /* ... */ }
}
```

**Tasks:**
- [ ] Installera imap-bibliotek: `npm install imap mailparser`
- [ ] Skapa IMAPService klass
- [ ] Implementera connection pooling
- [ ] Lägg till error handling
- [ ] Skapa reconnect-logik

### 2.2 Uppdatera integrated-email-service.js
```javascript
// Ta bort MCP-beroenden
- [ ] Remove: MCP_GUI_HOST referenser
- [ ] Remove: axios calls till port 3624/3625
- [ ] Add: Direkt IMAP-integration
- [ ] Update: fetchEmailsFromSource() att använda IMAPService
```

### 2.3 Environment configuration
**Fil:** `.env`
```bash
# IMAP Configuration
IMAP_HOST=imap.one.com
IMAP_PORT=993
IMAP_USER=mikael@fallstrom.org
IMAP_PASSWORD=Ati:}v>~ra_Tqec?)zpLRq8Z
IMAP_TLS=true

# Redis Configuration
REDIS_HOST=172.17.0.1
REDIS_PORT=6381

# LLM Configuration
LLM_API_URL=http://localhost:8085
LLM_FALLBACK=rule-based

# Database
DATABASE_PATH=/app/data/email_cache.db
```

- [ ] Skapa .env.template
- [ ] Uppdatera docker-compose.yml
- [ ] Säkra credentials med secrets management

## 📋 Fas 3: Frontend-anpassning (1 timme)

### 3.1 Ta bort proxy-referenser
**Fil:** `frontend/vite.config.js`
```javascript
// Remove:
- [ ] '/api/mcp' proxy regel
- [ ] Port 3625 referenser

// Keep:
- [ ] '/api/email' → 3015
- [ ] '/api/ai' → 8085
```

### 3.2 Uppdatera API-anrop
**Fil:** `frontend/src/services/api.js`
```javascript
- [ ] Verifiera alla endpoints pekar på /api/email
- [ ] Ta bort MCP-specifika anrop
- [ ] Uppdatera error handling
```

### 3.3 Rensa onödiga filer
```bash
- [ ] Delete: email-proxy-server.cjs
- [ ] Delete: mock-mcp-server.js
- [ ] Delete: Gamla test-filer
```

## 📋 Fas 4: Docker & Deployment (1 timme)

### 4.1 Uppdatera Docker-filer
**Backend Dockerfile:**
```dockerfile
FROM node:20-slim
WORKDIR /app
COPY package*.json ./
RUN npm ci --omit=dev
COPY . .
EXPOSE 3015
CMD ["node", "integrated-email-service.js"]
```

**Frontend Dockerfile:**
```dockerfile
FROM node:20-slim
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
EXPOSE 3623
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
```

### 4.2 Docker Compose
```yaml
version: '3.8'
services:
  email-backend:
    build: ./email-service
    ports:
      - "3015:3015"
    env_file: .env
    volumes:
      - email-data:/app/data
    restart: unless-stopped

  email-frontend:
    build: ./frontend
    ports:
      - "3623:3623"
    environment:
      - VITE_API_URL=http://172.16.16.148:3015
    depends_on:
      - email-backend
    restart: unless-stopped

volumes:
  email-data:
```

- [ ] Uppdatera docker-compose.yml
- [ ] Build containers
- [ ] Test deployment lokalt

## 📋 Fas 5: Testing & Validering (30 min)

### 5.1 Funktionstester
```bash
# Backend
- [ ] GET /health - Returnerar 200
- [ ] GET /recent-emails/primary - Returnerar emails
- [ ] Verifiera AI-kategorisering fungerar
- [ ] Kontrollera Redis-caching

# Frontend
- [ ] Emails visas i UI
- [ ] Filter fungerar
- [ ] Sökning fungerar
- [ ] Kategorier visas korrekt
```

### 5.2 Integrationstester
```bash
- [ ] End-to-end: Frontend → Backend → IMAP
- [ ] Cache invalidering
- [ ] Error recovery
- [ ] Reconnect vid IMAP-avbrott
```

### 5.3 Prestandatester
```bash
- [ ] Response tid < 500ms för cachade requests
- [ ] Response tid < 2s för IMAP-hämtning
- [ ] Memory usage < 512MB
```

## 📋 Fas 6: Cleanup & Dokumentation (30 min)

### 6.1 Rensa gamla filer
```bash
# Ta bort
- [ ] /mcp-email/mcp-email/ (hela katalogen)
- [ ] Gamla proxy-filer
- [ ] Mock-servers
- [ ] Oanvända dependencies
```

### 6.2 Uppdatera dokumentation
```bash
- [ ] README.md - Installation & användning
- [ ] API.md - Endpoint-dokumentation
- [ ] TROUBLESHOOTING.md - Vanliga problem
```

### 6.3 Git & Versionering
```bash
git add .
git commit -m "Refactor: Simplified architecture v2.0 - Direct IMAP integration"
git tag -a v2.0.0 -m "Simplified 3-tier architecture"
```

## 🚨 Rollback-plan

Om något går fel:
```bash
# 1. Stoppa alla tjänster
docker-compose down

# 2. Återställ från backup
git checkout main
git reset --hard HEAD~1

# 3. Starta gamla tjänster
cd /home/micke/claude-env/mcp-email/mcp-email
npm run gui # Port 3624

# 4. Verifiera funktionalitet
```

## ✅ Definition of Done

- [ ] Alla tester passerar
- [ ] Inga onödiga processer körs
- [ ] Docker containers kör stabilt
- [ ] Emails hämtas och kategoriseras
- [ ] Frontend visar korrekt data
- [ ] Dokumentation uppdaterad
- [ ] Git repository städat

## 📊 Förväntade resultat

### Prestanda
- 50% färre nätverkshopp
- 30% snabbare response tid
- 60% mindre CPU-användning

### Underhåll
- 70% mindre kod att underhålla
- Enklare debugging
- Färre beroenden

### Stabilitet
- Färre points of failure
- Bättre error recovery
- Enklare monitoring

## 🎯 Nästa steg efter implementation

1. **Monitoring:** Sätt upp Prometheus/Grafana
2. **Skalning:** Implementera horizontal scaling
3. **Features:**
   - WebSocket för realtidsuppdateringar
   - Batch-processing för stora mailboxar
   - Machine learning för bättre kategorisering

---

**Start:** När du är redo
**Estimerad tid:** 4-6 timmar
**Support:** Jag guidar genom varje steg

Säg till när du vill börja implementationen!