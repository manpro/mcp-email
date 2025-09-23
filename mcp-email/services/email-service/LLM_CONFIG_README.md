# Flexibel LLM-konfiguration för Email AI-kategorisering

## Översikt
Detta system stöder flera olika LLM-providers för email-kategorisering med automatisk fallback och regel-baserad backup.

## Konfiguration

### 1. Redigera `llm-config.json`

```json
{
  "providers": {
    "mistral": {
      "name": "Mistral 7B",
      "url": "http://localhost:1234",  // Ändra till din LLM-server
      "model": "mistral:7b",            // Modellnamn
      "endpoint": "/v1/chat/completions",
      "temperature": 0.4,
      "max_tokens": 250,
      "enabled": true,                  // Aktivera/avaktivera
      "priority": 1                     // Lägre nummer = högre prioritet
    }
  }
}
```

### 2. Starta din LLM-server

För Mistral 7B med Ollama:
```bash
# Installera Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Ladda ner Mistral 7B
ollama pull mistral

# Starta server på port 11434 (standard)
ollama serve
```

För LM Studio eller annan OpenAI-kompatibel server:
```bash
# Starta LM Studio och ladda Mistral 7B
# Sätt API-server till port 1234
```

### 3. Uppdatera konfiguration för din setup

Ändra i `llm-config.json`:

**För Ollama (port 11434):**
```json
"ollama": {
  "url": "http://localhost:11434",
  "model": "mistral",
  "endpoint": "/api/chat",
  "format": "ollama",
  "enabled": true,
  "priority": 1
}
```

**För LM Studio (port 1234):**
```json
"mistral": {
  "url": "http://localhost:1234",
  "model": "mistral-7b-instruct",
  "endpoint": "/v1/chat/completions",
  "enabled": true,
  "priority": 1
}
```

## Testning

### Testa LLM-konfiguration:
```bash
node test-llm-config.js
```

### Interaktivt läge:
```bash
node test-llm-config.js --interactive
```

## Funktioner

### Automatisk Fallback
- Försöker providers i prioritetsordning
- Om alla LLM:er misslyckas, använd regel-baserad klassificering
- Retry-logik med konfigurerbar delay

### Regel-baserad Backup
När ingen LLM är tillgänglig använder systemet intelligent pattern-matching för att:
- Kategorisera emails (work/personal/newsletter/spam/promotional)
- Bestämma prioritet (high/medium/low)
- Detektera sentiment (positive/neutral/negative)
- Identifiera action required

### Stöd för flera LLM-format
- **OpenAI-kompatibel** (GPT-OSS, LM Studio, etc.)
- **Ollama** format
- **Custom providers** (lägg till i config)

## Integration med Email-service

### Använd i optimized-email-service.js:

```javascript
const FlexibleEmailAIAnalyzer = require('./flexible-ai-analyzer');

// Initiera med config
const aiAnalyzer = new FlexibleEmailAIAnalyzer('./llm-config.json');

// Använd för kategorisering
const result = await aiAnalyzer.classifyEmail(email);
```

### Miljövariabler (alternativ):
```bash
# Överstyr config med miljövariabler
LLM_URL=http://localhost:1234 \
LLM_MODEL=mistral:7b \
node optimized-email-service.js
```

## Exempel på providers

### Mistral 7B (rekommenderad för lokal körning)
- Bra balans mellan prestanda och resurser
- ~4GB RAM-krav
- Snabb för email-kategorisering

### Llama 2 7B
```json
{
  "url": "http://localhost:1234",
  "model": "llama2:7b",
  "temperature": 0.3
}
```

### GPT4All
```json
{
  "url": "http://localhost:4891",
  "model": "gpt4all-j",
  "temperature": 0.2
}
```

## Felsökning

### LLM svarar inte:
1. Kontrollera att LLM-servern körs: `curl http://localhost:1234/v1/models`
2. Verifiera port och URL i config
3. Kör test: `node test-llm-config.js`

### Dålig kategorisering:
1. Justera temperature (lägre = mer deterministisk)
2. Öka max_tokens för längre svar
3. Byt till större modell (13B eller 30B)

### För långsam respons:
1. Använd mindre modell (3B eller 7B)
2. Minska max_tokens
3. Aktivera GPU-acceleration om möjligt

## Performance-tips

1. **Caching**: Systemet cachar redan kategoriseringar i Redis
2. **Batch-processing**: Använd batch-endpoints för flera emails
3. **Priority**: Sätt snabbaste LLM:en som priority 1
4. **Fallback**: Håll regel-baserad som backup för 100% uptime

## Exempel-output

```
🤖 Trying Mistral 7B...
✅ Success with Mistral 7B
Category: newsletter
Priority: low
Summary: Weekly tech newsletter with AI updates
Provider: Mistral 7B
```

När LLM inte är tillgänglig:
```
⚠️ All LLM providers failed, using rule-based classification
Category: newsletter (rule-based)
Priority: low
Summary: Email about: Weekly Tech Newsletter
Provider: rule-based
```