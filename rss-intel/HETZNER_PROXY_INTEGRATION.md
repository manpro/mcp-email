# 🚀 RSS Intelligence Dashboard - Hetzner Proxy Integration

**Version**: 1.0  
**Datum**: 2025-08-29  
**Syfte**: Dokumentation av WireGuard proxy-integration för RSS Intelligence Dashboard

---

## 📋 Översikt

RSS Intelligence Dashboard är nu konfigurerat att använda vår Hetzner Cloud proxy via WireGuard-tunnel för alla RSS-feeds och externa HTTP-anrop. Detta ger:

- **Anonymiserad RSS-hämtning** - Alla feeds hämtas från Hetzner IP (95.216.172.130)
- **Förbättrad tillgänglighet** - Bypass av geografiska blockeringar och rate limits
- **Säkerhet** - All trafik krypterad via WireGuard-tunnel
- **Prestanda** - Hetzner's snabba nätverk för feed-hämtning

---

## 🔧 Konfiguration

### Miljövariabler (.env)

RSS Intelligence är konfigurerat med följande proxy-inställningar i `.env`:

```bash
# Hetzner Proxy Configuration
HTTP_PROXY=http://10.8.0.1:3128
HTTPS_PROXY=http://10.8.0.1:3128
PROXY_ENABLED=true
```

### Automatisk Proxy-detektion

Systemet använder proxy automatiskt när:
- `PROXY_ENABLED=true` är satt
- `HTTP_PROXY` och `HTTPS_PROXY` är konfigurerade
- WireGuard-tunnel är aktiv (10.8.0.1 nåbar)

---

## 🏗️ Teknisk Implementation

### Proxy Utilities (`backend/app/proxy_utils.py`)

Centraliserad proxy-hantering för hela RSS Intelligence:

```python
from app.proxy_utils import create_httpx_client, test_proxy_connection

# Automatisk proxy-konfiguration
with create_httpx_client(timeout=30) as client:
    response = client.get('https://techcrunch.com/feed/')
    # Hämtas automatiskt via 95.216.172.130
```

### Integrerade Komponenter

**1. RSS Feed Fetching (`import_feeds_direct.py`)**
- Alla RSS-feeds hämtas via proxy
- Automatisk IP-verifiering vid start
- Fallback till direktanslutning om proxy ej tillgänglig

**2. Image Processing (`app/images.py`)**
- Artikelbilder hämtas via proxy
- OpenGraph images från externa sajter
- Säker caching med proxy-headers

**3. External API Calls**
- GitHub releases, HackerNews API
- Mastodon/Fediverse integration
- AI-tjänster för innehållsanalys

---

## 🧪 Verifiering och Test

### Automatisk Proxy-test

Kör vårt testscript för att verifiera proxy-integration:

```bash
cd /home/micke/claude-env/rss-intel/
python3 test_proxy_integration.py
```

**Förväntat resultat:**
```
🎉 ALLA TESTER LYCKADES!
✅ RSS Intelligence är redo att använda Hetzner proxy
```

### Manuell Verifiering

**1. Kontrollera proxy-status:**
```bash
# Från RSS Intelligence backend
python3 -c "from app.proxy_utils import test_proxy_connection; test_proxy_connection()"
```

**2. Verifiera RSS-hämtning:**
```bash
# Kör RSS import och kontrollera loggar
docker-compose exec backend python import_feeds_direct.py
```

**3. Kontrollera IP i loggar:**
Loggar ska visa: "RSS hämtad via IP: 95.216.172.130"

---

## 🐳 Docker Deployment

### Miljövariabler i Docker

RSS Intelligence Docker-containers får automatiskt proxy-konfiguration via `.env`:

```yaml
# docker-compose.yml (automatiskt konfigurerat)
services:
  backend:
    environment:
      - HTTP_PROXY=http://10.8.0.1:3128
      - HTTPS_PROXY=http://10.8.0.1:3128
      - PROXY_ENABLED=true
    network_mode: "host"  # För att nå WireGuard-interface
```

### Container Network Access

**Viktigt**: Containers måste kunna nå WireGuard-interface (10.8.0.1). Detta säkerställs genom:
- `network_mode: "host"` i docker-compose
- Eller custom bridge network med tillgång till host

---

## 📊 Övervakning

### Proxy Health Check

RSS Intelligence kontrollerar automatiskt proxy-status:

```python
# Vid systemstart
proxy_working = test_proxy_connection()
if proxy_working:
    print("✅ Hetzner proxy fungerar - RSS-feeds hämtas via 95.216.172.130")
else:
    print("⚠️ Proxy fungerar inte - använder direktanslutning")
```

### Loggar och Debugging

**Proxy-loggar finns i:**
- **Backend logs**: `/var/log/rss-intel/backend.log`
- **Squid access log**: `ssh -i ~/server_key.pem root@95.216.172.130 "tail -f /var/log/squid/access.log"`
- **WireGuard stats**: `wg show`

**Viktiga logmeddelanden:**
```bash
🌐 Använder Hetzner proxy: http://10.8.0.1:3128    # Proxy aktiv
🔄 Proxy inaktiverad - använder direktanslutning    # Proxy inaktiv
✅ Proxy fungerar! Extern IP: 95.216.172.130       # Proxy-test OK
```

---

## 🚨 Felsökning

### Vanliga Problem

**1. "Proxy inte konfigurerad"**
```bash
# Kontrollera .env
grep -E "PROXY|HTTP_PROXY" /home/micke/claude-env/rss-intel/.env

# Säkerställ att miljövariabler är laddade
export $(grep -v '^#' .env | xargs)
```

**2. "WireGuard-tunnel nere"**
```bash
# Starta om WireGuard
sudo systemctl restart wg-quick@wg0
ping 10.8.0.1  # Ska svara
```

**3. "Squid proxy inte tillgänglig"**
```bash
# Starta om Squid på Hetzner
ssh -i ~/server_key.pem root@95.216.172.130 "systemctl restart squid"
```

**4. "Container kan inte nå proxy"**
```bash
# Kontrollera Docker network
docker-compose exec backend ping 10.8.0.1
```

### Debug-kommandon

```bash
# Test proxy från host
curl -x http://10.8.0.1:3128 http://httpbin.org/ip

# Test från RSS Intelligence container
docker-compose exec backend python -c "from app.proxy_utils import test_proxy_connection; test_proxy_connection()"

# Visa aktuella miljövariabler i container
docker-compose exec backend env | grep PROXY
```

---

## ⚡ Prestanda och Optimering

### Proxy Performance

**Fördelar med Hetzner proxy:**
- **Latency**: ~8-10ms från server3 till Hetzner
- **Bandwidth**: Obegränsad via WireGuard
- **Caching**: Squid cache för upprepade requests (inaktiverat för scraping)
- **Concurrent requests**: Squid hanterar flera samtidiga anslutningar

### RSS Intelligence Optimeringar

**1. Connection Pooling:**
```python
# Återanvänder connections via httpx.Client
with create_httpx_client(timeout=30) as client:
    for feed_url in feeds:
        response = client.get(feed_url)  # Samma connection pool
```

**2. Timeout-inställningar:**
- **Connect timeout**: 3 sekunder
- **Request timeout**: 30 sekunder
- **Total timeout**: 60 sekunder

**3. Concurrent RSS Fetching:**
```python
# Asynkron hämtning av multiple feeds
async with create_async_httpx_client() as client:
    tasks = [client.get(url) for url in feed_urls]
    responses = await asyncio.gather(*tasks)
```

---

## 🔒 Säkerhet

### Proxy Security

**Åtkomst:**
- Proxy endast tillgänglig från WireGuard-nätverk (10.8.0.0/24)
- Ingen publik exponering av proxy-tjänst
- Säker autentisering via IP-whitelisting

**Headers:**
```python
# Automatiska anonymitetsheaders
headers = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36...',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9...',
    'Accept-Language': 'en-US,en;q=0.5',
}
```

**Logging:**
- Squid loggar alla requests för audit
- Inga känsliga data lagras i loggar
- Automatisk logg-rotation

---

## 🎯 Use Cases

### 1. RSS Feed Aggregation
```python
# TechCrunch, HackerNews, ArsTechnica feeds
# Hämtas via Hetzner - sajter ser tysk/EU IP
feeds = [
    "https://techcrunch.com/feed/",
    "https://news.ycombinator.com/rss", 
    "https://arstechnica.com/feed/"
]
```

### 2. Social Media API Integration
```python
# Mastodon instances, Reddit API
# Bypass rate limits och geographical restrictions
mastodon_api = "https://mastodon.social/api/v1/timelines/public"
```

### 3. Image Scraping
```python
# OpenGraph images från externa sajter
# Hetzner IP för att undvika bot-detection
og_image = fetch_og_image("https://news-site.com/article")
```

### 4. AI Content Analysis
```python
# Externa AI APIs för content enhancement
# Professionell IP-adress för business APIs
openai_response = analyze_content_sentiment(article_text)
```

---

## 📈 Metrics och Analytics

### Proxy Usage Stats

**Tillgängliga metrics:**
- Total requests via proxy per dag
- Response times för RSS feeds
- Success/failure rates
- Most accessed feeds/domains

**Squid statistik:**
```bash
# På Hetzner-server
ssh -i ~/server_key.pem root@95.216.172.130 "
  grep $(date +%d/%b/%Y) /var/log/squid/access.log | wc -l  # Requests idag
  grep 'TCP_MISS' /var/log/squid/access.log | tail -10     # Senaste requests
"
```

**RSS Intelligence Dashboard:**
- Proxy status visas i system health
- Response time metrics per feed
- Geographic distribution av content

---

## 🔄 Underhåll

### Regelbundna Kontroller

**Dagligen:**
```bash
# Automatisk health check i RSS Intelligence
# Loggas i system health dashboard
```

**Veckovis:**
```bash
# Kontrollera Squid logs storlek
ssh -i ~/server_key.pem root@95.216.172.130 "du -sh /var/log/squid/"

# Rensa gamla loggar om nödvändigt
ssh -i ~/server_key.pem root@95.216.172.130 "logrotate -f /etc/logrotate.conf"
```

**Månadsvis:**
```bash
# Uppdatera Squid på Hetzner
ssh -i ~/server_key.pem root@95.216.172.130 "apt update && apt upgrade squid"
```

### Backup och Disaster Recovery

**Proxy-konfiguration backup:**
```bash
# Local backup av RSS Intelligence config
cp /home/micke/claude-env/rss-intel/.env /home/micke/claude-env/rss-intel/.env.backup

# Hetzner proxy config backup
ssh -i ~/server_key.pem root@95.216.172.130 "cp /etc/squid/squid.conf /etc/squid/squid.conf.backup"
```

**Failover-strategi:**
1. RSS Intelligence detekterar proxy-problem
2. Automatisk fallback till direktanslutning
3. Health check var 5:e minut
4. Automatisk återanslutning när proxy blir tillgänglig

---

## ✅ Verifieringschecklist

- [x] ✅ Proxy-konfiguration i .env aktiv
- [x] ✅ WireGuard-tunnel fungerar (10.8.0.1 nåbar)
- [x] ✅ Squid proxy lyssnar på Hetzner (10.8.0.1:3128)
- [x] ✅ RSS Intelligence använder proxy automatiskt
- [x] ✅ HTTP/HTTPS requests via 95.216.172.130
- [x] ✅ Image fetching via proxy
- [x] ✅ Docker containers kan nå WireGuard
- [x] ✅ Proxy health check implementerat
- [x] ✅ Fallback till direktanslutning fungerar
- [x] ✅ Loggar och monitoring konfigurerat

---

## 🚀 Resultat

**RSS Intelligence Dashboard kör nu alla externa anrop via vår Hetzner proxy:**

- **RSS feeds** hämtas från `95.216.172.130`
- **Artikelbilder** laddas via proxy
- **API-anrop** anonymiserade
- **Geografiska begränsningar** omgås
- **Rate limits** fördelade över Hetzner IP

**Performance improvement:**
- Stabil tyskbaserad IP för alla requests
- Professionell hosting-IP (inte residential)
- Bättre success rate för content scraping
- Minskad risk för IP-blacklisting

---

**END OF DOCUMENTATION**

*RSS Intelligence Dashboard är nu fullständigt integrerat med vår WireGuard proxy-lösning via Hetzner Cloud!*