# 🔒 RSS Intelligence HTTPS Setup Guide

## Automatisk SSL med Let's Encrypt

RSS Intelligence kommer nu med komplett HTTPS-support inklusive automatisk certifikatförnyelse via Let's Encrypt.

## 🚀 Snabbstart för Produktion

### 1. Förbered domän
```bash
# Se till att din domän pekar på serverns IP-adress
nslookup your-domain.com
```

### 2. Konfigurera miljövariabler
```bash
cp .env.ssl.example .env

# Redigera .env med dina uppgifter:
SSL_DOMAIN=your-domain.com
SSL_EMAIL=your-email@example.com
SSL_STAGING=0  # 0 för produktion, 1 för test
```

### 3. Starta med SSL
```bash
./start-with-ssl.sh
```

## 🔧 Konfiguration

### Miljövariabler

| Variabel | Beskrivning | Standard |
|----------|-------------|----------|
| `SSL_DOMAIN` | Din domän (krävs) | localhost |
| `SSL_EMAIL` | Email för Let's Encrypt | admin@example.com |
| `SSL_STAGING` | Använd staging server (1=ja, 0=nej) | 1 |

### Portinställningar

| Port | Tjänst | Beskrivning |
|------|--------|-------------|
| 80 | HTTP | Omdirigerar till HTTPS |
| 443 | HTTPS | Huvudtjänst med SSL |

## 📋 SSL-certifikat hantering

### Kontrollera certifikatstatus
```bash
docker-compose exec nginx certbot certificates
```

### Testa förnyelse (dry-run)
```bash
docker-compose exec nginx certbot renew --dry-run
```

### Manuell förnyelse
```bash
docker-compose exec nginx /usr/local/bin/renew-ssl.sh
```

## 🛡️ Säkerhetsfeatures

### Automatiskt aktiverat:

- **HTTPS-omdirigering**: All HTTP-trafik dirigeras till HTTPS
- **HSTS**: Strict-Transport-Security headers
- **Rate limiting**: 
  - API: 10 req/min per IP
  - Login: 5 req/min per IP
  - Allmänt: 30 req/min per IP
- **Säkra cookies**: HTTP-only, Secure, SameSite
- **Security headers**:
  - X-Frame-Options: DENY
  - X-Content-Type-Options: nosniff
  - X-XSS-Protection: 1; mode=block
  - Content-Security-Policy
- **SSL/TLS-konfiguration**:
  - Endast TLS 1.2 och 1.3
  - Starka cipher suites
  - OCSP Stapling

## 🔄 Automatisk förnyelse

Certifikat förnyas automatiskt via cron job som körs dagligen kl 03:00.

### Verifiera cron job
```bash
crontab -l | grep ssl
```

### Loggar för förnyelse
```bash
docker-compose logs nginx | grep -i ssl
```

## 📊 Övervakning

### Kontrollera tjänststatus
```bash
docker-compose ps
```

### Visa loggar
```bash
# Alla tjänster
docker-compose logs -f

# Endast nginx
docker-compose logs -f nginx

# Endast certbot
docker-compose logs certbot
```

### Health check
```bash
curl -k https://your-domain.com/health
```

## 🚧 Felsökning

### Vanliga problem:

#### 1. Certifikatgenerering misslyckas
```bash
# Kontrollera DNS
nslookup your-domain.com

# Testa med staging först
SSL_STAGING=1 ./start-with-ssl.sh

# Kontrollera brandvägg
sudo ufw status
sudo ufw allow 80
sudo ufw allow 443
```

#### 2. Nginx startar inte
```bash
# Kontrollera konfiguration
docker-compose exec nginx nginx -t

# Kontrollera loggar
docker-compose logs nginx
```

#### 3. Certifikat fungerar inte
```bash
# Kontrollera certifikat
openssl s_client -connect your-domain.com:443 -servername your-domain.com

# Förnya certifikat
docker-compose exec nginx certbot renew --force-renewal
```

## 🔄 Uppdatering från HTTP

Om du kör systemet utan HTTPS:

1. Stoppa befintliga tjänster:
   ```bash
   docker-compose down
   ```

2. Konfigurera SSL:
   ```bash
   cp .env.ssl.example .env
   # Redigera .env
   ```

3. Starta med SSL:
   ```bash
   ./start-with-ssl.sh
   ```

## ⚡ Development Mode

För utveckling (localhost):

```bash
# Kör utan riktig domän
SSL_DOMAIN=localhost ./start-with-ssl.sh
```

Detta använder self-signed certifikat för localhost.

## 📞 Support

Vid problem:
1. Kolla loggarna: `docker-compose logs -f`
2. Verifiera DNS-inställningar
3. Testa med SSL_STAGING=1 först
4. Kontrollera brandvägginställningar

---

**Säkerhetsnivå: 9/10** 🔒

Med denna setup har du:
- ✅ Automatisk HTTPS med Let's Encrypt
- ✅ Säkra cookies och headers
- ✅ Rate limiting
- ✅ Stark SSL/TLS-konfiguration
- ✅ Automatisk certifikatförnyelse