# GPT-OSS Funktionalitets Gap-Analys
**Datum:** 2025-10-09
**System:** AI Email Manager med GPT-OSS 20B Integration

---

## Executive Summary

**Status:** GPT-OSS kan för närvarande endast skapa kategorier via chat-interface.
**Gap:** 70+ email-hanteringsfunktioner saknar GPT-OSS-styrning.
**Påverkan:** Användare måste fortfarande använda manuella knappar/formulär för majoriteten av funktionaliteten.

---

## 1. Nuvarande GPT-OSS Funktionalitet

### ✅ Implementerat (1 funktion)
| Funktion | Kommando | API Endpoint | Status |
|----------|----------|--------------|--------|
| Skapa kategori | "skapa en kategori som heter kivra" | `POST /api/categories/create-with-ai` | ✅ Fungerar |

**Implementation:** Text-baserad parsing av `[CREATE_CATEGORY...]` kommando från GPT-OSS svar.

---

## 2. Email Hantering Gap (17 funktioner)

### ❌ Saknas: Email Operations

| # | Funktion | Use Case | Förväntat Kommando | Saknad Endpoint Integration |
|---|----------|----------|-------------------|---------------------------|
| 1 | **Arkivera email** | "arkivera det här mailet" | `POST /api/emails/:id/archive` | ❌ |
| 2 | **Ta bort email** | "ta bort alla gamla mail från 2023" | `POST /api/emails/bulk/delete-old` | ❌ |
| 3 | **Markera som läst** | "markera alla mail från kivra som lästa" | `POST /api/emails/bulk/mark-read` | ❌ |
| 4 | **Snooze email** | "påminn mig om det här mailet imorgon kl 9" | `POST /api/emails/:id/snooze` | ❌ |
| 5 | **Unsnooze** | "väck upp snoozade mail" | `POST /api/emails/:id/unsnooze` | ❌ |
| 6 | **Bulk archive** | "arkivera alla mail i inbox" | `POST /api/emails/bulk/archive` | ❌ |
| 7 | **Bulk snooze** | "snooze alla olästa mail till på måndag" | `POST /api/emails/bulk/snooze` | ❌ |
| 8 | **Sök emails** | "hitta mail från maria om projektet" | `GET /api/search` | ❌ |
| 9 | **Räkna emails** | "hur många olästa mail har jag?" | `GET /api/emails/count` | ❌ |
| 10 | **Lista snoozade** | "visa mina snoozade mail" | `GET /api/emails/snoozed` | ❌ |
| 11 | **Email analys** | "analysera det här mailet" | `GET /api/emails/:uid/analysis` | ❌ |
| 12 | **Kategorisera batch** | "kategorisera alla nya mail" | `POST /api/emails/categorize-batch` | ❌ |
| 13 | **ML status** | "status på email-kategorisering" | `POST /api/emails/ml-status` | ❌ |
| 14 | **Email count verification** | "verifiera antal mail" | `GET /api/email-count-verification/:accountId` | ❌ |
| 15 | **Unarchive** | "ta fram arkiverade mail från förra veckan" | `POST /api/emails/:id/unarchive` | ❌ |
| 16 | **Get email details** | "visa hela mailet från maria" | `GET /api/emails/:id` | ❌ |
| 17 | **Get recent emails** | "visa senaste 10 mailen" | `GET /api/recent-emails/:accountId` | ❌ |

---

## 3. Kategori Hantering Gap (4 funktioner)

### ✅ Implementerat
- **Skapa kategori** med GPT-OSS ✅

### ❌ Saknas: Kategori Operations

| # | Funktion | Use Case | Förväntat Kommando | Saknad Endpoint |
|---|----------|----------|-------------------|----------------|
| 18 | **Lista kategorier** | "vilka kategorier har jag?" | `GET /api/categories` | ❌ |
| 19 | **Kategori-statistik** | "hur många mail har kategorin kivra?" | `GET /api/categories/stats/:accountId` | ❌ |
| 20 | **Byt kategori** | "flytta det här mailet till kivra-kategorin" | `POST /api/categories/override` | ❌ |
| 21 | **Ta bort kategori** | "ta bort kategorin spam" | `DELETE /api/custom-categories/:userId/:categoryId` | ❌ |

---

## 4. AI Regler & Automation Gap (9 funktioner)

### ❌ Saknas: AI Rules Operations

| # | Funktion | Use Case | Förväntat Kommando | Saknad Endpoint |
|---|----------|----------|-------------------|----------------|
| 22 | **Skapa AI-regel** | "skapa en regel: alla mail från maria ska markeras som viktiga" | `POST /api/ai-rules/:accountId` | ❌ |
| 23 | **Lista AI-regler** | "vilka regler har jag?" | `GET /api/ai-rules/:accountId` | ❌ |
| 24 | **Ta bort AI-regel** | "ta bort regeln för spam-mail" | `DELETE /api/ai-rules/:ruleId` | ❌ |
| 25 | **Uppdatera AI-regel** | "ändra regeln så att maria-mail går till work" | `PUT /api/ai-rules/:ruleId` | ❌ |
| 26 | **Regel-statistik** | "hur många mail har regeln spam matchat?" | `GET /api/ai-rules/:ruleId/stats` | ❌ |
| 27 | **Testa regel** | "testa regeln på det här mailet" | `POST /api/ai-rules/test` | ❌ |
| 28 | **Process email med regel** | "kör regler på det här mailet" | `POST /api/ai-rules/process/:emailId` | ❌ |
| 29 | **Batch process regler** | "kör alla regler på olästa mail" | `POST /api/ai-rules/batch-process` | ❌ |
| 30 | **Skapa enkel regel** | "skapa regel: arkivera nyhetsbrev automatiskt" | `POST /api/rules/create` | ❌ |

---

## 5. Mapphantering Gap (5 funktioner)

### ❌ Saknas: Folder Operations

| # | Funktion | Use Case | Förväntat Kommando | Saknad Endpoint |
|---|----------|----------|-------------------|----------------|
| 31 | **Lista mappar** | "vilka mappar har jag?" | `GET /api/folders` | ❌ |
| 32 | **Skapa mapp** | "skapa en mapp som heter projekt" | `POST /api/folders` | ❌ |
| 33 | **Flytta email till mapp** | "flytta det här mailet till projekt-mappen" | `POST /api/folders/move` | ❌ |
| 34 | **Mapp-förslag** | "föreslå mappar baserat på mina mail" | `GET /api/folders/suggestions/:accountId` | ❌ |
| 35 | **Lista mailboxes** | "vilka mailboxes har jag?" | `GET /api/accounts/:accountId/mailboxes` | ❌ |

---

## 6. Konto Hantering Gap (6 funktioner)

### ❌ Saknas: Account Operations

| # | Funktion | Use Case | Förväntat Kommando | Saknad Endpoint |
|---|----------|----------|-------------------|----------------|
| 36 | **Lista konton** | "vilka email-konton har jag?" | `GET /api/accounts` | ❌ |
| 37 | **Lägg till konto** | "lägg till mitt gmail-konto" | `POST /api/accounts` | ❌ |
| 38 | **Koppla konto** | "koppla konto 1 till IMAP" | `POST /api/accounts/:accountId/connect` | ❌ |
| 39 | **Aktivera/avaktivera konto** | "stäng av synkronisering för arbetsmail" | `POST /api/accounts/:accountId/toggle` | ❌ |
| 40 | **Ta bort konto** | "ta bort mitt gamla hotmail" | `DELETE /api/accounts/:accountId` | ❌ |
| 41 | **Synkronisera emails** | "synka mail från gmail nu" | `POST /sync-emails/:accountId` | ❌ |

---

## 7. Inbox Zero & Produktivitet Gap (6 funktioner)

### ❌ Saknas: Inbox Zero Operations

| # | Funktion | Use Case | Förväntat Kommando | Saknad Endpoint |
|---|----------|----------|-------------------|----------------|
| 42 | **Inbox Zero stats** | "visa mina inbox zero stats" | `GET /api/inbox-zero/stats/:accountId` | ❌ |
| 43 | **Achievements** | "vilka achievements har jag?" | `GET /api/inbox-zero/achievements/:accountId` | ❌ |
| 44 | **Weekly progress** | "visa min veckas framsteg" | `GET /api/inbox-zero/weekly-progress/:accountId` | ❌ |
| 45 | **Smart inbox** | "visa mitt smarta inbox" | `GET /smart-inbox/:accountId` | ❌ |
| 46 | **Predictive actions** | "föreslå nästa åtgärd" | *(Frontend PredictiveActionsPanel)* | ❌ |
| 47 | **Performance dashboard** | "visa prestanda-dashboard" | *(Frontend PerformanceDashboard)* | ❌ |

---

## 8. Integrationer Gap (9 funktioner)

### ❌ Saknas: Integration Operations

| # | Funktion | Use Case | Förväntat Kommando | Saknad Endpoint |
|---|----------|----------|-------------------|----------------|
| 48 | **Lista integrationer** | "vilka integrationer har jag?" | `GET /api/integrations/:userId` | ❌ |
| 49 | **Koppla från integration** | "koppla från google calendar" | `POST /api/integrations/:userId/:provider/disconnect` | ❌ |
| 50 | **OAuth Google** | "koppla google calendar" | `GET /oauth/google/authorize` | ❌ |
| 51 | **OAuth Microsoft** | "koppla outlook calendar" | `GET /oauth/microsoft/authorize` | ❌ |
| 52 | **Calendar invites** | "visa mina kalender-inbjudningar" | *(CalendarInvitesPanel)* | ❌ |
| 53 | **Auto RSVP** | "svara automatiskt ja på alla teammöten" | *(AutoRSVPManager)* | ❌ |
| 54 | **Browser automation** | "automatisera webbläsaren för att..." | `POST /api/browser-automation/test` | ❌ |
| 55 | **Automation history** | "visa automationshistorik" | `GET /api/browser-automation/history/:userId` | ❌ |
| 56 | **Cleanup browser** | "rensa webbläsar-automation" | `DELETE /api/browser-automation/cleanup` | ❌ |

---

## 9. ML & Feedback Gap (3 funktioner)

### ❌ Saknas: ML Operations

| # | Funktion | Use Case | Förväntat Kommando | Saknad Endpoint |
|---|----------|----------|-------------------|----------------|
| 57 | **ML feedback** | "det här mailet borde vara i spam" | `POST /api/ml/feedback` | ❌ |
| 58 | **Training signal** | "lär dig från det här mailet" | `POST /api/ml/training-signal` | ❌ |
| 59 | **ML stats** | "visa ML-statistik" | `GET /ml-stats` | ❌ |

---

## 10. GDPR & Samtycke Gap (4 funktioner)

### ❌ Saknas: Consent Operations

| # | Funktion | Use Case | Förväntat Kommando | Saknad Endpoint |
|---|----------|----------|-------------------|----------------|
| 60 | **Pending consent** | "vilka samtycken väntar?" | `GET /api/consent/:userId/pending` | ❌ |
| 61 | **Grant consent** | "ge samtycke för email-analys" | `POST /api/consent/:userId/grant` | ❌ |
| 62 | **Revoke consent** | "återkalla samtycke" | `POST /api/consent/:userId/revoke` | ❌ |
| 63 | **Consent manager** | "hantera mina samtycken" | *(ConsentManager component)* | ❌ |

---

## 11. Avancerade Features Gap (10 funktioner)

### ❌ Saknas: Advanced Operations

| # | Funktion | Use Case | Förväntat Kommando | Saknad/Integration |
|---|----------|----------|-------------------|-------------------|
| 64 | **Drag & drop kategorisering** | "dra mailet till kivra" | *(Frontend DragFeedback)* | ❌ |
| 65 | **Undo/Redo** | "ångra senaste åtgärden" | *(UndoRedoBar)* | ❌ |
| 66 | **Bulk actions** | "välj flera mail och arkivera" | *(PerformanceOptimizedBulkActions)* | ❌ |
| 67 | **Email modal** | "öppna mailet i popup" | *(EmailModal)* | ❌ |
| 68 | **Search results** | "visa sökresultat" | *(SearchResults component)* | ❌ |
| 69 | **Sync status** | "visa synkroniseringsstatus" | *(SyncStatusBar)* | ❌ |
| 70 | **Icon picker** | "ändra ikon för kategorin" | *(IconPicker)* | ❌ |
| 71 | **Cache clear** | "rensa cache" | `POST /api/cache/clear` | ❌ |
| 72 | **Cache stats** | "visa cache-statistik" | `GET /api/cache/stats` | ❌ |
| 73 | **Health check** | "är systemet friskt?" | `GET /api/health` | ❌ |

---

## 12. Prioriterad Implementation Roadmap

### Fas 1: Email Basics (Högsta Prioritet)
**Estimat:** 2-3 timmar
**Impact:** Låter användare hantera emails via GPT-OSS

1. **Arkivera email** - `POST /api/emails/:id/archive`
2. **Markera som läst** - `POST /api/emails/bulk/mark-read`
3. **Sök emails** - `GET /api/search`
4. **Lista emails** - `GET /api/emails`
5. **Email details** - `GET /api/emails/:id`

**Kommando-format:**
```
[ARCHIVE_EMAIL id="123"]
[MARK_READ ids="123,456,789"]
[SEARCH_EMAIL query="maria projekt"]
[LIST_EMAILS limit="10" unread="true"]
[GET_EMAIL id="123"]
```

---

### Fas 2: Kategorier & Regler (Hög Prioritet)
**Estimat:** 3-4 timmar
**Impact:** Automatisering av email-hantering

1. **Lista kategorier** - `GET /api/categories`
2. **Byt kategori** - `POST /api/categories/override`
3. **Skapa AI-regel** - `POST /api/ai-rules/:accountId`
4. **Lista AI-regler** - `GET /api/ai-rules/:accountId`
5. **Ta bort AI-regel** - `DELETE /api/ai-rules/:ruleId`

**Kommando-format:**
```
[LIST_CATEGORIES]
[CHANGE_CATEGORY emailId="123" category="kivra"]
[CREATE_RULE name="spam_filter" condition="from:spam.com" action="archive"]
[LIST_RULES]
[DELETE_RULE id="5"]
```

---

### Fas 3: Snooze & Bulk Operations (Medel Prioritet)
**Estimat:** 2-3 timmar
**Impact:** Produktivitets-features

1. **Snooze email** - `POST /api/emails/:id/snooze`
2. **Lista snoozade** - `GET /api/emails/snoozed`
3. **Bulk archive** - `POST /api/emails/bulk/archive`
4. **Bulk delete** - `POST /api/emails/bulk/delete-old`

**Kommando-format:**
```
[SNOOZE_EMAIL id="123" until="2025-10-10T09:00:00"]
[LIST_SNOOZED]
[BULK_ARCHIVE category="newsletters" older_than="30d"]
[BULK_DELETE older_than="2023-12-31"]
```

---

### Fas 4: Inbox Zero & Stats (Medel Prioritet)
**Estimat:** 2 timmar
**Impact:** Motivation & insikter

1. **Inbox Zero stats** - `GET /api/inbox-zero/stats/:accountId`
2. **Achievements** - `GET /api/inbox-zero/achievements/:accountId`
3. **Email count** - `GET /api/emails/count`
4. **Kategori-statistik** - `GET /api/categories/stats/:accountId`

**Kommando-format:**
```
[GET_INBOX_STATS]
[GET_ACHIEVEMENTS]
[COUNT_EMAILS unread="true"]
[CATEGORY_STATS]
```

---

### Fas 5: Konton & Mappar (Låg Prioritet)
**Estimat:** 2-3 timmar
**Impact:** System-administration

1. **Lista konton** - `GET /api/accounts`
2. **Lista mappar** - `GET /api/folders`
3. **Flytta till mapp** - `POST /api/folders/move`
4. **Synkronisera** - `POST /sync-emails/:accountId`

**Kommando-format:**
```
[LIST_ACCOUNTS]
[LIST_FOLDERS]
[MOVE_TO_FOLDER emailId="123" folder="project"]
[SYNC_ACCOUNT id="default"]
```

---

### Fas 6: Integrationer & Avancerat (Låg Prioritet)
**Estimat:** 4-5 timmar
**Impact:** Power users

1. **Lista integrationer** - `GET /api/integrations/:userId`
2. **ML feedback** - `POST /api/ml/feedback`
3. **Automation history** - `GET /api/browser-automation/history/:userId`
4. **Cache management** - `POST /api/cache/clear`

---

## 13. Implementation Strategi

### A. Text-Baserad Command Parsing (Nuvarande)
**Pros:** Fungerar med alla LLM:er
**Cons:** Kräver noggrann regex-parsing

**Format:**
```
[COMMAND_NAME param1="value" param2="value"]
```

**Example:**
```javascript
const archiveMatch = response.match(/\[ARCHIVE_EMAIL id="([^"]+)"\]/);
if (archiveMatch) {
  const emailId = archiveMatch[1];
  await archiveEmail(emailId);
}
```

### B. Structured JSON Response (Framtida)
**När GPT-OSS/Ollama stödjer tool calling:**

```json
{
  "tool_calls": [{
    "name": "archive_email",
    "arguments": {"id": "123"}
  }]
}
```

---

## 14. Exempel på Fullständig Implementation

### Email Archiving via GPT-OSS

**1. Uppdatera System Prompt:**
```javascript
systemPrompt += `
När användaren ber dig arkivera ett email, svara med:
[ARCHIVE_EMAIL id="email_id"]

Exempel:
Användare: "arkivera mailet från maria"
Du: "[ARCHIVE_EMAIL id="123"]"
`;
```

**2. Lägg till Parsing:**
```javascript
// I /api/assistant/chat endpoint
const archiveMatch = assistantMessage.match(/\[ARCHIVE_EMAIL id="([^"]+)"\]/);

if (archiveMatch) {
  const emailId = archiveMatch[1];

  try {
    await emailDb.pool.query(`
      UPDATE emails SET archived = true WHERE id = $1
    `, [emailId]);

    return res.json({
      success: true,
      message: `✅ Arkiverade email ${emailId}`,
      model: usedModel
    });
  } catch (error) {
    return res.json({
      success: true,
      message: `❌ Kunde inte arkivera: ${error.message}`,
      model: usedModel
    });
  }
}
```

---

## 15. Risker & Utmaningar

### Tekniska Utmaningar
1. **Email ID Lookup** - GPT-OSS känner inte till email IDs
   - **Lösning:** Inkludera recent emails i context
2. **Bulk Operations** - Komplexa queries
   - **Lösning:** Steg-för-steg guided execution
3. **Multi-step Operations** - "arkivera alla mail från maria äldre än 30 dagar"
   - **Lösning:** Conversation memory + confirmation steps

### UX Utmaningar
1. **Fel email** - GPT-OSS arkiverar fel mail
   - **Lösning:** Confirmation prompts för destructive operations
2. **Otydliga kommandon** - "fixa mina mail"
   - **Lösning:** Ask for clarification
3. **Context window** - För många emails i prompt
   - **Lösning:** Paginated context med summaries

---

## 16. Rekommendationer

### Immediate Actions (Denna Sprint)
1. ✅ Implementera Fas 1 (Email Basics) - 5 commands
2. ✅ Lägg till error handling för alla commands
3. ✅ Skapa test suite för GPT-OSS commands

### Short-term (Nästa Sprint)
1. Implementera Fas 2 (Kategorier & Regler) - 5 commands
2. Lägg till conversation memory för multi-step operations
3. Implementera confirmation prompts för destructive operations

### Long-term (Q1 2026)
1. Migrera till proper tool calling när Ollama stödjer det
2. Implementera MCP Email Server för strukturerade operations
3. Lägg till voice command support

---

## 17. Metrics & Success Criteria

### KPIs to Track
- **Command Success Rate** - % av GPT-OSS kommandon som lyckas
- **User Adoption** - % av operationer via GPT-OSS vs UI
- **Error Rate** - % av misslyckade commands
- **Average Commands per Session** - Engagement metric

### Success Targets (3 månader)
- 80% command success rate
- 40% av email operations via GPT-OSS
- <5% error rate
- 10+ commands per user session

---

## 18. Totalt Gap Summary

| Kategori | Total Funktioner | GPT-OSS Support | Gap | % Klar |
|----------|------------------|-----------------|-----|--------|
| Email Operations | 17 | 0 | 17 | 0% |
| Kategori Hantering | 4 | 1 | 3 | 25% |
| AI Regler | 9 | 0 | 9 | 0% |
| Mapphantering | 5 | 0 | 5 | 0% |
| Konto Hantering | 6 | 0 | 6 | 0% |
| Inbox Zero | 6 | 0 | 6 | 0% |
| Integrationer | 9 | 0 | 9 | 0% |
| ML & Feedback | 3 | 0 | 3 | 0% |
| GDPR & Samtycke | 4 | 0 | 4 | 0% |
| Avancerade Features | 10 | 0 | 10 | 0% |
| **TOTALT** | **73** | **1** | **72** | **1.4%** |

---

## Slutsats

**Nuvarande situation:** Endast 1.4% av systemets funktionalitet är styrbar via GPT-OSS.

**Rekommendation:** Prioritera implementation av Fas 1-3 (15 kommandon) för att nå 21% coverage och ge användare grundläggande email-hantering via AI.

**Estimerad tid för 80% coverage:** 15-20 timmar development + testing.
