# Gmail OAuth Setup Guide

## Overview

For att kunna integrera Gmail och Google Calendar behöver vi sätta upp OAuth 2.0 credentials i Google Cloud Console.

## Steg 1: Skapa Google Cloud Project

1. Gå till [Google Cloud Console](https://console.cloud.google.com/)
2. Klicka på "Select a project" → "New Project"
3. Namnge projektet: "AI Email Manager"
4. Klicka "Create"

## Steg 2: Aktivera APIs

1. Gå till "APIs & Services" → "Library"
2. Sök efter och aktivera följande APIs:
   - **Gmail API**
   - **Google Calendar API**
   - **Cloud Pub/Sub API** (för webhooks)

## Steg 3: Konfigurera OAuth Consent Screen

1. Gå till "APIs & Services" → "OAuth consent screen"
2. Välj **External** (om du vill tillåta alla Gmail-användare)
3. Fyll i:
   - App name: "AI Email Manager"
   - User support email: din email
   - Developer contact: din email
4. Klicka "Save and Continue"
5. **Scopes**: Lägg till följande scopes:
   ```
   https://www.googleapis.com/auth/gmail.modify
   https://www.googleapis.com/auth/gmail.send
   https://www.googleapis.com/auth/calendar
   https://www.googleapis.com/auth/calendar.events
   ```
6. Klicka "Save and Continue"
7. **Test users** (om appen är i Testing mode):
   - Lägg till din Gmail-adress
8. Klicka "Save and Continue"

## Steg 4: Skapa OAuth 2.0 Credentials

1. Gå till "APIs & Services" → "Credentials"
2. Klicka "+ CREATE CREDENTIALS" → "OAuth client ID"
3. Välj Application type: **Web application**
4. Name: "AI Email Manager Web Client"
5. **Authorized redirect URIs**: Lägg till:
   ```
   http://localhost:3015/api/accounts/oauth/gmail/callback
   http://localhost:3623/oauth/callback
   ```
   (Lägg även till production URL när du deployar)
6. Klicka "Create"
7. **Kopiera Client ID och Client Secret** - dessa behövs i `.env`

## Steg 5: Konfigurera Cloud Pub/Sub (för webhooks)

### Skapa Topic

1. Gå till "Cloud Pub/Sub" → "Topics"
2. Klicka "CREATE TOPIC"
3. Topic ID: `gmail-notifications`
4. Klicka "Create"

### Ge Gmail API rätt att publicera till topic

1. I topic-listan, klicka på `gmail-notifications`
2. Gå till "Permissions" tab
3. Klicka "ADD PRINCIPAL"
4. Principal: `gmail-api-push@system.gserviceaccount.com`
5. Role: **Pub/Sub Publisher**
6. Klicka "Save"

### Skapa Subscription

1. I topic `gmail-notifications`, klicka "CREATE SUBSCRIPTION"
2. Subscription ID: `gmail-notifications-sub`
3. Delivery type: **Push**
4. Endpoint URL: `https://yourdomain.com/api/webhooks/gmail`
   (Använd ngrok för lokal utveckling)
5. Klicka "Create"

## Steg 6: Uppdatera .env

Kopiera `.env.example` till `.env`:

```bash
cp services/email-service/.env.example services/email-service/.env
```

Fyll i följande värden:

```env
# Google OAuth Configuration
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=http://localhost:3015/api/accounts/oauth/gmail/callback

# Google Cloud Pub/Sub
GOOGLE_PROJECT_ID=your-project-id
GOOGLE_PUBSUB_TOPIC=projects/your-project-id/topics/gmail-notifications
```

## Steg 7: Installera Dependencies

```bash
cd services/email-service
npm install
```

Detta kommer installera:
- `googleapis` - Google API client
- `google-auth-library` - OAuth 2.0 authentication
- `ical.js` - iCalendar parsing för calendar invites
- `pg` - PostgreSQL driver

## Steg 8: Skapa Database Schema

```bash
psql -U your_user -d email_db -f database/multi-provider-schema.sql
```

## Steg 9: Testa OAuth Flow

1. Starta email-service:
   ```bash
   cd services/email-service
   npm start
   ```

2. Öppna i browser:
   ```
   http://localhost:3015/api/accounts/oauth/gmail/url?userId=default
   ```

3. Du får en JSON response med `authUrl`
4. Kopiera URL:en och öppna i browser
5. Logga in med ditt Gmail-konto
6. Godkänn permissions
7. Du redirectas tillbaka till callback URL

## Steg 10: Verifiera i Database

```sql
SELECT * FROM email_accounts WHERE provider = 'gmail';
SELECT * FROM calendar_accounts WHERE provider = 'google';
```

Du bör se ditt Gmail-konto med access/refresh tokens.

## Troubleshooting

### Error: "Access blocked: This app's request is invalid"

- Kontrollera att redirect URI i Google Cloud Console matchar exakt
- Lägg till din email som test user i OAuth consent screen

### Error: "invalid_grant"

- Refresh token kan vara expired
- Gå igenom OAuth flow igen med `prompt=consent`

### Error: "insufficient_permissions"

- Kontrollera att alla scopes är tillagda i OAuth consent screen
- Be användaren att godkänna igen

### Webhook inte working

- Kontrollera att Pub/Sub topic har rätt permissions
- Verifiera att endpoint URL är publicly accessible
- Använd ngrok för lokal utveckling:
  ```bash
  ngrok http 3015
  # Använd ngrok URL i Pub/Sub subscription
  ```

## Nästa Steg

1. Implementera frontend OAuth flow (React component)
2. Testa email sync med Gmail API
3. Testa calendar integration
4. Setup webhooks för real-time sync
5. Implementera auto-RSVP för calendar invites

## Säkerhet

- **Aldrig** committa `.env` till git
- Använd environment variables i production
- Rotera OAuth client secrets regelbundet
- Använd HTTPS i production
- Implementera rate limiting
- Logga alla OAuth-relaterade händelser

## Rate Limits

Gmail API:
- 250 quota units/user/second
- 1 billion quota units/day

Calendar API:
- 1000 requests/100 seconds/user
- 10000 requests/100 seconds/project

Se [Gmail API Quotas](https://developers.google.com/gmail/api/reference/quota) för detaljer.
