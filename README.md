# MCP Email Server

En MCP (Model Context Protocol) server för att läsa e-post via IMAP, med stöd för både vanlig IMAP och Microsoft Exchange/Outlook.

## Funktioner

- Anslut till vilken IMAP-server som helst
- Inbyggt stöd för Microsoft Outlook/Exchange Online
- Stöd för Microsoft Exchange On-Premise
- Läs senaste e-post från valfri mapp
- Sök e-post med IMAP-kriterier
- Hämta detaljerad information om specifika e-post
- Lista alla mappar i e-postkontot

## Installation

```bash
npm install
npm run build
```

## Användning

### Starta MCP-servern

```bash
npm start
```

### Tillgängliga Tools

#### 1. `connect_email`
Anslut till ett e-postkonto via IMAP.

**Parametrar:**
- `connectionId` (obligatorisk): Unik identifierare för anslutningen
- `email` (obligatorisk): E-postadress
- `password` (obligatorisk): Lösenord eller app-lösenord
- `provider` (valfri): E-postleverantör (`outlook`, `exchangeOnline`, `exchangeOnPremise`, `gmail`, `generic`)
- `customHost` (valfri): Anpassad IMAP-host
- `customPort` (valfri): Anpassad IMAP-port

#### 2. `list_mailboxes`
Lista alla mappar i e-postkontot.

#### 3. `get_recent_emails`
Hämta senaste e-post från en mapp.

**Parametrar:**
- `connectionId`: Anslutnings-ID
- `mailbox`: Mappnamn (standard: INBOX)
- `count`: Antal e-post att hämta (standard: 10)

#### 4. `search_emails`
Sök e-post baserat på kriterier.

**Parametrar:**
- `connectionId`: Anslutnings-ID
- `mailbox`: Mappnamn (standard: INBOX)
- `criteria`: IMAP-sökkriterier (t.ex. `["FROM", "example@email.com"]`)
- `limit`: Max antal e-post att returnera (standard: 20)

#### 5. `get_email_details`
Hämta detaljerad information om specifika e-post.

#### 6. `disconnect_email`
Koppla från ett e-postkonto.

#### 7. `list_providers`
Lista tillgängliga e-postleverantörer.

## Stödda E-postleverantörer

### Microsoft Outlook/Exchange Online
- Host: `outlook.office365.com`
- Port: `993`
- TLS: Aktiverad

### Microsoft Exchange On-Premise
- Automatisk detektion baserat på domän
- Port: `993`
- TLS: Aktiverad (accepterar självsignerade certifikat)

### Gmail
- Host: `imap.gmail.com`
- Port: `993`
- TLS: Aktiverad
- **OBS:** Kräver app-lösenord, inte vanligt lösenord

### One.com
- Host: `imap.one.com`
- Port: `993`
- TLS: Aktiverad
- **OBS:** Använd ditt vanliga lösenord eller app-lösenord

### Generisk IMAP
- Automatisk detektion: `imap.[domän]`
- Port: `993`
- TLS: Aktiverad

## Exempel på användning

### Ansluta till Outlook
```json
{
  "tool": "connect_email",
  "arguments": {
    "connectionId": "outlook1",
    "email": "din.email@outlook.com",
    "password": "ditt_lösenord",
    "provider": "outlook"
  }
}
```

### Ansluta till Exchange On-Premise
```json
{
  "tool": "connect_email",
  "arguments": {
    "connectionId": "exchange1",
    "email": "din.email@företag.se",
    "password": "ditt_lösenord",
    "provider": "exchangeOnPremise"
  }
}
```

### Ansluta till One.com
```json
{
  "tool": "connect_email",
  "arguments": {
    "connectionId": "onecom1",
    "email": "din.email@one.com",
    "password": "ditt_lösenord",
    "provider": "oneCom"
  }
}
```

### Hämta senaste e-post
```json
{
  "tool": "get_recent_emails",
  "arguments": {
    "connectionId": "outlook1",
    "count": 5
  }
}
```

### Sök e-post från specifik avsändare
```json
{
  "tool": "search_emails",
  "arguments": {
    "connectionId": "outlook1",
    "criteria": ["FROM", "exempel@email.com"],
    "limit": 10
  }
}
```

## IMAP-sökkriterier

Vanliga sökkriterier:
- `["ALL"]` - Alla e-post
- `["UNSEEN"]` - Olästa e-post
- `["FROM", "email@domain.com"]` - Från specifik avsändare
- `["TO", "email@domain.com"]` - Till specifik mottagare
- `["SUBJECT", "ämne"]` - Innehåller ämnestext
- `["SINCE", "1-Jan-2024"]` - Sedan specifikt datum
- `["BEFORE", "31-Dec-2023"]` - Före specifikt datum

## Säkerhet

- Lösenord skickas över säkra TLS-anslutningar
- Stöd för app-lösenord (rekommenderas för Gmail och Microsoft)
- Automatisk hantering av TLS-certifikat

## Utveckling

```bash
# Bygg projektet
npm run build

# Utvecklingsläge med watch
npm run dev
```

## Felsökning

### Vanliga problem

1. **Autentiseringsfel**: Kontrollera att du använder rätt lösenord. För Gmail och Microsoft, använd app-lösenord.

2. **Anslutningsfel**: Kontrollera att IMAP är aktiverat i ditt e-postkonto.

3. **TLS-fel**: För företagsmejl med självsignerade certifikat, använd `exchangeOnPremise` provider.

### Microsoft-specifika inställningar

För Microsoft Exchange/Outlook:
- IMAP måste vara aktiverat i Exchange Admin Center
- Användaren behöver IMAP-behörigheter
- Moderna autentisering kan kräva app-lösenord