# MCP Email Server GUI

Ett webbaserat gränssnitt för att hantera e-postanslutningar via MCP Email Server.

## Snabbstart

1. **Bygg projektet:**
   ```bash
   npm run build
   ```

2. **Starta GUI-servern:**
   ```bash
   npm run gui
   ```

3. **Öppna webbläsaren:**
   ```
   http://localhost:3623
   ```

## Funktioner

### ✅ E-postanslutningar
- Lägg till nya e-postanslutningar med credentials
- Stöd för automatisk leverantörsdetektering
- Hantera flera anslutningar samtidigt
- Säker frånkoppling av anslutningar

### ✅ Stödda Leverantörer
- **Microsoft Outlook/Exchange Online** - `outlook.office365.com`
- **Microsoft Exchange On-Premise** - Automatisk domändetekning
- **Gmail** - `imap.gmail.com` (kräver app-lösenord)
- **Generisk IMAP** - Anpassade inställningar

### ✅ E-posthantering
- Hämta senaste e-post från valfri mapp
- Lista alla tillgängliga mappar
- Förhandsgranska e-postinnehåll
- Visa bilagor och metadata

## API Endpoints

### POST `/api/connect`
Anslut till ett e-postkonto.

**Body:**
```json
{
  "connectionId": "mitt-konto",
  "email": "din.email@exempel.se",
  "password": "ditt_lösenord",
  "provider": "outlook",
  "customHost": "imap.företag.se",
  "customPort": 993
}
```

### POST `/api/disconnect`
Koppla från ett e-postkonto.

**Body:**
```json
{
  "connectionId": "mitt-konto"
}
```

### POST `/api/recent-emails`
Hämta senaste e-post.

**Body:**
```json
{
  "connectionId": "mitt-konto",
  "count": 10,
  "mailbox": "INBOX"
}
```

### POST `/api/mailboxes`
Lista alla mappar.

**Body:**
```json
{
  "connectionId": "mitt-konto"
}
```

### GET `/api/status`
Kontrollera serverstatus.

### GET `/api/connections`
Lista aktiva anslutningar.

## Säkerhet

### 🔒 Lösenordshantering
- Lösenord lagras endast i minnet under aktiva sessioner
- Automatisk rensning vid serverstopp
- Stöd för app-lösenord (rekommenderas)

### 🔒 TLS/SSL
- Alla e-postanslutningar använder TLS
- Säker certifikatvalidering
- Stöd för självsignerade certifikat (On-Premise)

## Felsökning

### Vanliga Problem

**1. Anslutningsfel:**
```
Error: connect ECONNREFUSED
```
- Kontrollera att IMAP är aktiverat
- Verifiera värdnamn och port
- Testa med anpassade inställningar

**2. Autentiseringsfel:**
```
Error: Invalid credentials
```
- För Gmail: Använd app-lösenord
- För Microsoft: Kontrollera moderna autentisering
- Testa lösenordet i en e-postklient först

**3. TLS-fel:**
```
Error: unable to verify the first certificate
```
- Använd `exchangeOnPremise` för företagsmejl
- Kontrollera certifikatsinställningar

### Debug-läge

Starta servern med debug-information:
```bash
DEBUG=* npm run gui
```

## Utveckling

### Projektstruktur
```
src/
├── gui-server.ts      # Express-server för GUI
├── imap-client.ts     # IMAP-klient
├── email-providers.ts # Leverantörskonfigurationer
└── index.ts          # MCP-server

public/
└── index.html        # Webgränssnitt

dist/                 # Kompilerad TypeScript
```

### Lägg till ny leverantör

1. Uppdatera `email-providers.ts`:
```typescript
export const EmailProviders: Record<string, EmailProvider> = {
  // ... befintliga leverantörer
  minLeverantör: {
    name: 'Min E-postleverantör',
    getConfig: (email: string, password: string): ImapConfig => ({
      host: 'imap.minleverantör.se',
      port: 993,
      user: email,
      password: password,
      tls: true
    })
  }
};
```

2. Uppdatera dropdown i `public/index.html`:
```html
<option value="minLeverantör">Min E-postleverantör</option>
```

## Port-konfiguration

Standard port: `3623`

Ändra port:
```typescript
// I gui-server.ts
const server = new EmailGUIServer(8080); // Anpassad port
```

## Produktionsdrift

### 1. Reverse Proxy (Nginx)
```nginx
server {
    listen 80;
    server_name email-gui.företag.se;
    
    location / {
        proxy_pass http://localhost:3623;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 2. HTTPS-certifikat
```bash
certbot --nginx -d email-gui.företag.se
```

### 3. Process Manager (PM2)
```bash
npm install -g pm2
pm2 start dist/gui-server.js --name "email-gui"
pm2 save
pm2 startup
```

## Support

För problem eller frågor:
1. Kontrollera loggarna i terminalen
2. Testa API-endpoints direkt med curl
3. Verifiera nätverksanslutning till e-postservern