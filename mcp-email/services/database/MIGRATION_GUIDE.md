# Database Migration Guide

## Översikt

Denna guide hjälper dig att migrera från befintlig SQLite-databas till nya PostgreSQL multi-provider schema.

## Förutsättningar

1. **PostgreSQL installerat och igång**
   ```bash
   # Ubuntu/Debian
   sudo apt install postgresql postgresql-contrib

   # macOS
   brew install postgresql
   brew services start postgresql
   ```

2. **Database skapat**
   ```bash
   # Skapa database
   createdb email_db

   # Eller med psql
   psql -U postgres
   CREATE DATABASE email_db;
   ```

3. **Environment variables konfigurerade**
   ```bash
   # I .env filen
   DATABASE_URL=postgresql://user:password@localhost:5432/email_db
   SQLITE_DB_PATH=./email_categorizations.db
   ```

## Migrationssteg

### Steg 1: Skapa PostgreSQL Schema

Kör schema-filen för att skapa alla tabeller:

```bash
psql -U your_user -d email_db -f multi-provider-schema.sql
```

Verifiera att tabellerna skapades:

```bash
psql -U your_user -d email_db -c "\dt"
```

Du bör se följande tabeller:
- email_accounts
- emails
- labels
- email_labels
- calendar_accounts
- calendars
- calendar_events
- email_calendar_links
- email_actions
- email_snoozes
- user_rules
- automation_stats
- unsubscribe_log
- sync_history

### Steg 2: Kör Migration Script

```bash
cd services/database
node migrate-to-postgres.js
```

Expected output:
```
Starting SQLite → PostgreSQL migration...

Step 1: Creating IMAP account...
✓ Created account ID: 1

Step 2: Migrating labels...
✓ Migrated 12 labels

Step 3: Migrating emails...
  Found 1523 emails to migrate
✓ Migrated 1523 emails

Step 4: Migrating email-label relationships...
✓ Migrated 3847 email-label relations

Step 5: Migrating user preferences...
✓ User preferences migrated

Step 6: Verifying migration...
  Emails: 1523
  Labels: 12
  Relations: 3847
✓ Migration verified

✅ Migration completed successfully!

Summary:
  - Account ID: 1
  - Labels: 12
  - Emails: 1523
  - Relations: 3847
```

### Steg 3: Verifiera Migration

#### Kontrollera account

```sql
SELECT * FROM email_accounts;
```

Expected:
```
 id | user_id | provider | email_address      | display_name
----+---------+----------+--------------------+-------------------------
  1 | default | imap     | you@example.com    | IMAP Account (Migrated)
```

#### Kontrollera emails

```sql
SELECT COUNT(*) FROM emails;
SELECT subject, from_address, received_at
FROM emails
ORDER BY received_at DESC
LIMIT 5;
```

#### Kontrollera labels

```sql
SELECT id, name, display_name, icon
FROM labels
ORDER BY id;
```

#### Kontrollera email-label relationer

```sql
SELECT
  l.display_name,
  COUNT(*) as email_count
FROM labels l
JOIN email_labels el ON l.id = el.label_id
GROUP BY l.id, l.display_name
ORDER BY email_count DESC;
```

### Steg 4: Uppdatera Backend för PostgreSQL

#### Installera pg driver

```bash
cd services/email-service
npm install pg
```

#### Uppdatera .env

```bash
# Lägg till PostgreSQL connection
DATABASE_URL=postgresql://user:password@localhost:5432/email_db

# Kommentera ut eller ta bort SQLite
# SQLITE_DB_PATH=./email_categorizations.db
```

#### Uppdatera index.js

```javascript
// Gamla SQLite koden
// const sqlite3 = require('sqlite3').verbose()
// const db = new sqlite3.Database('./email_categorizations.db')

// Nya PostgreSQL koden
const { Pool } = require('pg')
const postgres = new Pool({
  connectionString: process.env.DATABASE_URL
})

// Uppdatera alla queries till PostgreSQL syntax
// SQLite: INSERT ... RETURNING *
// PostgreSQL: INSERT ... RETURNING id
```

### Steg 5: Testa Backend

```bash
cd services/email-service
npm start
```

Verifiera att:
1. Backend startar utan fel
2. `/api/emails` returnerar emails från PostgreSQL
3. `/api/labels` returnerar labels från PostgreSQL
4. Kategorisering fungerar

### Steg 6: Testa Frontend

```bash
cd services/frontend
npm run dev
```

Verifiera att:
1. Emails laddas korrekt
2. Kategorier visas
3. Filter fungerar
4. Email detail view fungerar

## Rollback Plan

Om något går fel, du kan enkelt gå tillbaka till SQLite:

### 1. Stoppa backend

```bash
# Stoppa alla Node.js processer
pkill -f "node.*email-service"
```

### 2. Återställ .env

```bash
# Kommentera ut PostgreSQL
# DATABASE_URL=postgresql://...

# Aktivera SQLite
SQLITE_DB_PATH=./email_categorizations.db
```

### 3. Återställ kod till SQLite version

```bash
git checkout HEAD -- services/email-service/index.js
```

### 4. Starta om backend

```bash
cd services/email-service
npm start
```

## Backup Strategi

### Backup SQLite (innan migration)

```bash
cp email_categorizations.db email_categorizations.db.backup
```

### Backup PostgreSQL (efter migration)

```bash
pg_dump email_db > email_db_backup.sql
```

### Restore från backup

```bash
# SQLite
cp email_categorizations.db.backup email_categorizations.db

# PostgreSQL
dropdb email_db
createdb email_db
psql email_db < email_db_backup.sql
```

## Performance Optimization

Efter migration, skapa indexes för bättre performance:

```sql
-- Additional indexes (utöver de i schema)
CREATE INDEX idx_emails_account_received
  ON emails(account_id, received_at DESC);

CREATE INDEX idx_emails_search
  ON emails USING gin(to_tsvector('english', subject || ' ' || COALESCE(body_text, '')));

CREATE INDEX idx_email_labels_label
  ON email_labels(label_id, score DESC);

-- Analyze tables
ANALYZE emails;
ANALYZE labels;
ANALYZE email_labels;
```

## Troubleshooting

### Problem: "relation does not exist"

**Lösning**: Schema har inte körts korrekt.

```bash
psql -U your_user -d email_db -f multi-provider-schema.sql
```

### Problem: "connection refused"

**Lösning**: PostgreSQL är inte igång.

```bash
# Ubuntu
sudo systemctl start postgresql

# macOS
brew services start postgresql
```

### Problem: "password authentication failed"

**Lösning**: Uppdatera DATABASE_URL med rätt credentials.

```bash
# Skapa user om det inte finns
psql -U postgres
CREATE USER your_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE email_db TO your_user;
```

### Problem: "duplicate key value"

**Lösning**: Migration kördes flera gånger.

```bash
# Rensa PostgreSQL och kör om
psql -U your_user -d email_db -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
psql -U your_user -d email_db -f multi-provider-schema.sql
node migrate-to-postgres.js
```

## Data Validation

Efter migration, kör dessa queries för att validera data:

```sql
-- Kontrollera att inga emails förlorats
SELECT COUNT(*) FROM emails;

-- Kontrollera att alla emails har korrekt account_id
SELECT COUNT(*) FROM emails WHERE account_id IS NULL;
-- Förväntat: 0

-- Kontrollera att alla labels finns
SELECT COUNT(*) FROM labels;

-- Kontrollera att alla email_labels har giltiga references
SELECT COUNT(*)
FROM email_labels el
LEFT JOIN emails e ON el.email_id = e.id
LEFT JOIN labels l ON el.label_id = l.id
WHERE e.id IS NULL OR l.id IS NULL;
-- Förväntat: 0

-- Kontrollera unread count
SELECT
  COUNT(*) FILTER (WHERE is_read = false) as unread,
  COUNT(*) FILTER (WHERE is_flagged = true) as flagged,
  COUNT(*) as total
FROM emails;
```

## Nästa Steg

Efter lyckad migration:

1. ✅ Testa alla API endpoints
2. ✅ Verifiera frontend funktionalitet
3. ✅ Setup Gmail OAuth (se GMAIL_OAUTH_SETUP.md)
4. ✅ Konfigurera webhooks
5. ✅ Deploy till production

## Support

Om du stöter på problem:

1. Kontrollera PostgreSQL logs: `tail -f /var/log/postgresql/postgresql-*.log`
2. Kontrollera backend logs: `journalctl -u email-service -f`
3. Kör validation queries ovan
4. Se TROUBLESHOOTING.md för vanliga problem
