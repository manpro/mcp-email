# MCP Agents Server

MCP (Model Context Protocol) server för Cursor IDE med stöd för Gitea och PostgreSQL-integrationer.

## Funktioner

### 🎯 Gitea Integration (`/agent/gitea-create-issue`)
- Skapa issues i Gitea repositories
- Input format: `"repo=owner/name, title=Issue Title, body=Issue Body"`
- Automatisk autentisering med personal access token

### 🗄️ PostgreSQL Integration (`/agent/pg-query`) 
- Kör SQL-queries mot flera databaser
- Stöd för flera databaser via environment variables
- Connection pooling och automatisk resurshantering

## Installation

```bash
npm install
cp .env.template .env
# Redigera .env med dina databasanslutningar
npm run dev
```

## Konfiguration

### Environment Variables (.env)
```
PG_FINANCE_URL=postgresql://user:pass@host:port/finance_db
PG_CRM_URL=postgresql://user:pass@host:port/crm_db  
PG_INTERNAL_URL=postgresql://user:pass@host:port/internal_db
```

## API Endpoints

### POST /agent/gitea-create-issue
```json
{
  "input": "repo=manpro/test, title=Bug i login, body=Det går inte att logga in."
}
```

### POST /agent/pg-query
```json
{
  "db": "finance",
  "query": "SELECT * FROM users WHERE active = true"
}
```

## Användning med Cursor IDE

1. Starta servern: `npm run dev`
2. Konfigurera Cursor att anropa `http://localhost:3111/agent/*`
3. Använd agenterna via HTTP-anrop från Cursor

## Teknologier

- **Express.js** - HTTP server
- **PostgreSQL** - Databasintegration med connection pooling
- **Axios** - HTTP client för Gitea API
- **TypeScript** - Type safety
- **dotenv** - Environment variable management