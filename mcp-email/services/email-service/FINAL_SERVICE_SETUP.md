# Email AI Categorization Service - Final Setup

## Overview
After cleanup, we now have a streamlined email categorization system with only the essential services running.

## Active Services

### 1. Backend - Optimized Email Service (Port 3016)
**File:** `/home/micke/claude-env/mcp-email/services/email-service/optimized-email-service.js`
**Shell ID:** 98088b
**Command:**
```bash
REDIS_HOST=172.17.0.1 REDIS_PORT=6381 LLM_CONFIG=./llm-config.json PORT=3016 node optimized-email-service.js
```

**Features:**
- AI-powered email categorization using multiple LLM providers
- Redis caching (first layer) with dynamic TTL
- SQLite persistent storage (second layer)
- Rule-based fallback for resilience
- Real-time metrics tracking
- Model switching capability

**API Endpoints:**
- `POST /api/categorize` - Categorize single email
- `POST /api/categorize/batch` - Batch categorization
- `GET /api/models` - List available AI models
- `POST /api/models/switch` - Switch active model
- `POST /api/models/priority` - Update model priority
- `GET /health` - Service health check
- `GET /metrics` - Performance metrics

### 2. Frontend - React/Vite Application (Port 3623)
**Path:** `/home/micke/claude-env/mcp-email/services/frontend`
**Shell ID:** 482f3f
**Command:**
```bash
VITE_API_URL=http://172.16.16.148:3016 VITE_EMAIL_API_URL=http://172.16.16.148:3016 npm run dev -- --host 0.0.0.0 --port 3623
```

**Features:**
- Email dashboard interface
- IMAP email account connection
- Real-time categorization display
- Model selection UI component
- Performance metrics visualization

## AI Model Configuration

### Available Models (llm-config.json)
```json
{
  "providers": {
    "qwen": {
      "name": "Qwen 2.5 7B",
      "url": "http://mini:1234",
      "model": "qwen2.5-7b-instruct-1m",
      "enabled": true,
      "priority": 1
    },
    "gpt-oss": {
      "name": "GPT-OSS 20B",
      "url": "http://localhost:8085",
      "model": "gpt-oss:20b",
      "enabled": true,
      "priority": 2
    },
    "ollama-qwen": {
      "name": "Ollama Qwen 2.5 7B",
      "url": "http://localhost:11434",
      "model": "qwen2.5:7b",
      "enabled": false,
      "priority": 3
    }
  },
  "default": "qwen"
}
```

## Architecture

```
┌─────────────────────┐
│   Frontend (3623)   │
│   React + Vite      │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Backend API (3016) │
│  optimized-email-   │
│     service.js      │
└──────────┬──────────┘
           │
     ┌─────┴─────┐
     ▼           ▼
┌─────────┐ ┌─────────┐
│  Redis  │ │ SQLite  │
│  Cache  │ │   DB    │
└─────────┘ └─────────┘
     │
     ▼
┌─────────────────────┐
│   LLM Providers     │
├─────────────────────┤
│ • Qwen 2.5 7B       │
│ • GPT-OSS 20B       │
│ • Ollama (disabled) │
└─────────────────────┘
```

## Testing

### Test Email Categorization
```bash
cd /home/micke/claude-env/mcp-email/services/email-service
node test-categorization.js
```

### View Model Selection UI
Open: http://172.16.16.148:3623
Or use the standalone model selector:
```bash
open model-selector-demo.html
```

## Startup Commands

If services need to be restarted:

### Backend
```bash
cd /home/micke/claude-env/mcp-email/services/email-service
REDIS_HOST=172.17.0.1 REDIS_PORT=6381 LLM_CONFIG=./llm-config.json PORT=3016 node optimized-email-service.js
```

### Frontend
```bash
cd /home/micke/claude-env/mcp-email/services/frontend
VITE_API_URL=http://172.16.16.148:3016 VITE_EMAIL_API_URL=http://172.16.16.148:3016 npm run dev -- --host 0.0.0.0 --port 3623
```

## Key Files

- `optimized-email-service.js` - Main backend service
- `flexible-ai-analyzer.js` - Multi-provider AI integration
- `database.js` - SQLite persistence layer
- `llm-config.json` - AI model configuration
- `ModelSelector.jsx` - React component for model switching
- `model-selector-demo.html` - Standalone model selector UI
- `test-categorization.js` - Testing script

## Performance Metrics

The system tracks:
- Cache hit/miss rates
- Database hit/miss rates
- AI service calls
- Fallback usage
- Average response times

Access metrics at: http://localhost:3016/metrics

## Notes

- All old/redundant services on ports 3012-3015, 3024-3025 have been stopped
- Redis cache uses dynamic TTL based on email type
- System falls back to rule-based categorization if AI services fail
- Model switching clears cache to ensure fresh categorizations