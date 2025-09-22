# GPT-OSS Bridge Setup & Lösning

## ✅ Status: Bridge körs nu!

- **Ollama**: Port 8080 (PID: 2585783)
- **OpenAI Bridge**: Port 8085 (PID: 2587626)
- **Modeller tillgängliga**: gpt-oss:20b, qwen2.5:7b

## 📍 Bridge-script lokalisering

```bash
/home/micke/claude-env/ollama-bridge.py
```

## 🚀 Starta tjänsterna (om de inte körs)

### 1. Starta Ollama
```bash
cd /home/micke/claude-env
OLLAMA_HOST=http://localhost:8080 nohup /home/micke/claude-env/ollama/bin/ollama serve > ollama.log 2>&1 &
```

### 2. Starta OpenAI Bridge
```bash
cd /home/micke/claude-env
nohup python3 ollama-bridge.py > ollama-bridge.log 2>&1 &
```

## ✅ Verifiera att allt fungerar

### Kontrollera processer
```bash
ps aux | grep -E "ollama|bridge"
```

### Kontrollera portar
```bash
netstat -tlnp | grep -E "8080|8085"
```

### Testa Bridge API
```bash
# Lista modeller
curl http://localhost:8085/v1/models

# Testa GPT-OSS
curl -X POST http://localhost:8085/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-oss:20b",
    "messages": [{"role": "user", "content": "Hello"}],
    "max_tokens": 50
  }'
```

## 🔧 Om tjänsterna måste startas om

```bash
# Stoppa allt
pkill -f ollama-bridge.py
pkill ollama

# Vänta 2 sekunder
sleep 2

# Starta igen
cd /home/micke/claude-env
OLLAMA_HOST=http://localhost:8080 nohup /home/micke/claude-env/ollama/bin/ollama serve > ollama.log 2>&1 &
sleep 3
nohup python3 ollama-bridge.py > ollama-bridge.log 2>&1 &
```

## 📝 Bridge-scriptets funktion

`ollama-bridge.py` konverterar OpenAI API-format till Ollama-format:
- Lyssnar på port 8085 (OpenAI-kompatibelt API)
- Vidarebefordrar till Ollama på port 8080
- Översätter mellan formaten

## 🎯 Integration med MCP-Email

MCP-Email använder Bridge på följande sätt:
```javascript
// Konfiguration
const BRIDGE_URL = "http://localhost:8085";

// Health check
const response = await axios.get(`${BRIDGE_URL}/v1/models`);

// Analysera e-post
const analysis = await axios.post(`${BRIDGE_URL}/v1/chat/completions`, {
  model: "gpt-oss:20b",
  messages: [...],
  max_tokens: 300
});
```

## ⚠️ Vanliga problem

### "Request timed out"
- GPT-OSS tar lång tid första gången (laddar modell)
- Vänta 30-60 sekunder och försök igen

### Port redan upptagen
```bash
lsof -i :8085
kill -9 [PID]
```

### Ollama svarar inte
```bash
# Kontrollera loggarna
tail -f /home/micke/claude-env/ollama.log
tail -f /home/micke/claude-env/ollama-bridge.log
```

## 📊 Aktuell status

```
Tjänst          Port    Status    PID
-------         ----    ------    ---
Ollama          8080    ✅ Kör    2585783
Bridge          8085    ✅ Kör    2587626
GPT-OSS 20B     -       ✅ Laddad -
```

Allt fungerar och är redo att användas!