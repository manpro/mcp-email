# 📧 Email Kategoriseringsflöde - Komplett Arkitektur

## 🏗️ Systemöversikt

```
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│   IMAP Server   │◄──────│  MCP GUI Server │◄──────│    Backend API  │
│  (one.com:993)  │       │   (port 3624)   │       │   (port 3015)   │
└─────────────────┘       └─────────────────┘       └─────────────────┘
                                                              ▲
                                                              │
                                                     ┌─────────────────┐
                                                     │  Frontend GUI   │
                                                     │   (port 3623)   │
                                                     └─────────────────┘
```

## 📊 Detaljerat Dataflöde

### 1️⃣ **Email-hämtning från IMAP**

```
IMAP Server (one.com)
    ↓
MCP GUI Server (port 3624)
    - Ansluter via IMAP protokoll
    - Autentisering: mikael@fallstrom.org
    - Hämtar emails från INBOX
    - Returnerar rå email-data
```

**Loggexempel från MCP GUI Server:**
```
Successfully connected to imap.one.com
=> 'A5 UID SEARCH ALL'
<= '* SEARCH 126965 127158 127219...'
=> 'A7 UID FETCH 129394,129395,129396...'
```

### 2️⃣ **Backend Processing (port 3015)**

**Fil:** `integrated-email-service.js`

```javascript
// Steg 1: Hämta emails från MCP
const emails = await fetchEmailsFromMCP(accountId, limit)

// Steg 2: Processera varje email
emails.forEach(email => {
  // AI-kategorisering
  const mlAnalysis = await categorizeEmailWithML(email)

  // Spara i databas
  saveCategorizationToDB(email.uid, mlAnalysis)

  // Cacha i Redis
  cacheInRedis(email.uid, mlAnalysis)
})
```

### 3️⃣ **AI-Kategorisering**

**Process:**

```
Email Input
    ↓
FlexibleEmailAIAnalyzer
    ↓
┌──────────────────────────────┐
│  1. Försök LLM (8085)        │
│  2. Om fail → Regelbaserad   │
│     kategorisering           │
└──────────────────────────────┘
    ↓
Kategoriseringsresultat:
- category: 'personal/work/newsletter/spam/etc'
- priority: 'high/medium/low'
- sentiment: 'positive/neutral/negative'
- topics: ['meeting', 'invoice', etc]
- actionRequired: true/false
- summary: "AI-genererad sammanfattning"
- confidence: 0.0-1.0
```

### 4️⃣ **Datalagring**

```
┌─────────────────────────────────────────┐
│           LAGRINGSPUNKTER               │
├─────────────────────────────────────────┤
│                                         │
│  1. SQLite Database                    │
│     Fil: /app/email_categorizations.db │
│     Tabell: categorizations            │
│     - email_uid                        │
│     - category                         │
│     - priority                         │
│     - sentiment                        │
│     - topics (JSON)                    │
│     - created_at                       │
│                                         │
│  2. Redis Cache                        │
│     Host: 172.17.0.1:6381             │
│     Key: email:{uid}:ml               │
│     TTL: Dynamisk (1h - 7d)           │
│     - Hög prioritet: 1 timme          │
│     - Medium: 1 dag                    │
│     - Låg: 7 dagar                    │
│                                         │
└─────────────────────────────────────────┘
```

### 5️⃣ **API Endpoints**

```
Backend API (port 3015)
│
├── /recent-emails/:accountId
│   └── Returnerar emails MED kategorisering
│
├── /api/emails
│   └── Kompatibilitet endpoint
│
├── /smart-inbox/:accountId
│   └── AI-prioriterad inbox
│
└── /api/categories/stats/:accountId
    └── Kategoristatistik
```

### 6️⃣ **Frontend GUI (port 3623)**

**Dataflöde i React:**

```javascript
// 1. EmailList.jsx - Laddar emails
const loadEmails = async () => {
  const response = await fetch(
    'http://172.16.16.148:3015/recent-emails/primary'
  )
  const emails = await response.json()
  // Emails har redan kategorier från backend
}

// 2. SmartFilters.jsx - Analyserar och filtrerar
const categorizeEmail = (email) => {
  // Använder email.category från backend
  if (email.category) return email.category

  // Fallback om kategori saknas
  return ruleBasedCategorization(email)
}

// 3. Filtrering
const filteredEmails = emails.filter(email => {
  const category = email.category || categorizeEmail(email)
  return activeFilters.has(`category:${category}`)
})
```

## 🔄 Komplett Flöde - Steg för Steg

```
1. Användare öppnar GUI (port 3623)
       ↓
2. Frontend anropar Backend API
   GET http://172.16.16.148:3015/recent-emails/primary
       ↓
3. Backend kontrollerar cache
   - Om cachad → returnera direkt
   - Om inte → fortsätt
       ↓
4. Backend anropar MCP GUI Server
   POST http://172.16.16.148:3624/api/search-emails
       ↓
5. MCP hämtar från IMAP (one.com)
       ↓
6. Backend tar emot rå emails
       ↓
7. För varje email:
   a. Kör AI-kategorisering (LLM eller regelbaserad)
   b. Spara i SQLite databas
   c. Cacha i Redis med TTL
   d. Lägg till kategoriseringsdata till email-objektet
       ↓
8. Returnera kategoriserade emails till Frontend
       ↓
9. Frontend visar emails med filter
   - SmartFilters räknar kategorier
   - EmailList applicerar valda filter
       ↓
10. Användare kan filtrera på:
    - Kategori (personal, work, newsletter, etc)
    - Prioritet (high, medium, low)
    - Sentiment (positive, neutral, negative)
```

## 💾 Var sparas kategoriseringen?

1. **Permanent lagring:**
   - SQLite: `/app/email_categorizations.db`
   - Innehåller alla kategoriseringar permanent

2. **Cache-lagring:**
   - Redis: `172.17.0.1:6381`
   - Temporär med intelligent TTL baserat på prioritet

3. **Runtime-minne:**
   - Frontend state (Zustand store)
   - Lever så länge sessionen är aktiv

## 🎯 När görs kategoriseringen?

1. **Första gången:** När email hämtas från IMAP första gången
2. **Cache-miss:** När Redis-cache har gått ut
3. **Aldrig om cachad:** Om email finns i cache används den sparade kategoriseringen

## 🔗 Koppling till GUI

GUI får kategoriserad data direkt från backend:
- Backend lägger till `category`, `priority`, `sentiment` etc. till varje email
- Frontend behöver INTE kategorisera själv (har bara fallback)
- SmartFilters använder backend-kategorier för att räkna och filtrera
- EmailList visar emails baserat på aktiva filter

## ⚡ Prestandaoptimering

1. **Redis Cache:** Minskar databas-lookups
2. **TTL-strategi:** Kortare för viktiga emails
3. **Batch-processing:** Kategoriserar flera emails samtidigt
4. **Regelbaserad fallback:** När LLM inte är tillgänglig

## 🔍 Debug-punkter

För att följa flödet, kolla:
1. Docker logs: `docker-compose logs email-backend`
2. MCP GUI logs: Visar IMAP-kommunikation
3. Browser console: Visar frontend filter-operationer
4. Redis: `redis-cli -p 6381` för att se cachade värden

---

Detta är det kompletta flödet från IMAP till GUI med alla kategoriserings- och lagringspunkter!