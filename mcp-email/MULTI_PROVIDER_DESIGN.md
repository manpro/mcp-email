# Multi-Provider Email & Calendar Design
## Gmail, Exchange/Outlook & IMAP Support med Unified Backend

**Skapad:** 2025-10-01
**Status:** Design Phase
**Kritiska deadlines:**
- Gmail OAuth obligatoriskt från 14 mars 2025
- Exchange EWS deprecation: Oktober 2026

---

## EXECUTIVE SUMMARY

Systemet måste stödja tre email-providers med olika capabilities:

1. **IMAP/SMTP (Generic)** - Nuvarande implementation
2. **Gmail API** - OAuth-obligatoriskt från mars 2025, bättre labels/flags
3. **Microsoft Graph API** - Exchange/Outlook, EWS depreceras 2026

**Designprincip:** Unified abstraction layer som exponerar gemensamma operationer men tillåter provider-specifika features.

---

## 1. EMAIL STANDARDER & FLAGS ANALYS

### 1.1 IMAP System Flags (RFC 3501)

**Standardiserade flags som fungerar överallt:**

```
\Seen       - Läst/oläst (UNIVERSAL SUPPORT)
\Answered   - Besvarad (UNIVERSAL SUPPORT)
\Flagged    - Stjärna/viktigt (UNIVERSAL SUPPORT)
\Deleted    - Markerad för borttagning (UNIVERSAL SUPPORT)
\Draft      - Utkast (UNIVERSAL SUPPORT)
\Recent     - Nyligen anlänt (READ-ONLY, server-managed)
```

**Custom flags (provider-dependent):**
```
$Label1, $Label2, etc - Custom keywords
Keyword flags - Arbitrary text labels
```

### 1.2 Gmail-Specifika Funktioner

**Labels vs Folders:**
- Gmail använder **labels** (flat namespace)
- IMAP emulerar detta som **folders**
- En email kan ha flera labels samtidigt
- Speciella labels: INBOX, SENT, DRAFT, SPAM, TRASH, STARRED, IMPORTANT

**Gmail API Labels:**
```json
{
  "id": "Label_123",
  "name": "Work/Projects",
  "type": "user",
  "messageListVisibility": "show",
  "labelListVisibility": "labelShow"
}
```

**Skillnad IMAP vs Gmail API:**
| Feature | IMAP | Gmail API |
|---------|------|-----------|
| OAuth Support | ✅ XOAUTH2 | ✅ Native |
| Multiple Labels | ⚠️ Emuleras via folders | ✅ Native |
| Threading | ❌ Manuell | ✅ threadId |
| Search | ⚠️ Basic | ✅ Advanced (Gmail search syntax) |
| Rate Limits | Session-based | 250 req/user/sec |
| Session Validity | 1 hour (OAuth token) | Access token expires |

**Gmail API Fördelar:**
- Batch operations (upp till 1000 emails/request)
- Snabbare än IMAP för bulk operations
- Native support för drafts, send, attachments
- Push notifications (Cloud Pub/Sub)
- History API (delta sync)

### 1.3 Microsoft Exchange/Graph API

**Flag Mapping:**
```json
{
  "flag": {
    "flagStatus": "flagged" | "complete" | "notFlagged",
    "startDateTime": "2025-10-01T09:00:00Z",
    "dueDateTime": "2025-10-05T17:00:00Z",
    "completedDateTime": "2025-10-03T14:30:00Z"
  },
  "importance": "low" | "normal" | "high",
  "isRead": true,
  "categories": ["Red category", "Blue category"]
}
```

**Exchange Folders:**
- Hierarkisk struktur (lik IMAP)
- Well-known folders: Inbox, Sent Items, Drafts, Deleted Items
- Custom folders med `parentFolderId`

**Graph API vs EWS:**
| Feature | EWS (Legacy) | Graph API |
|---------|--------------|-----------|
| OAuth | ✅ | ✅ |
| REST API | ❌ SOAP | ✅ JSON |
| Calendar | ✅ | ✅ Enhanced |
| Support End | Oktober 2026 | ✅ Active |
| Rate Limits | Lower | 2000 req/sec/app |

**Graph API Fördelar:**
- Unified API för mail, calendar, contacts, files
- Delta queries (sync only changes)
- Webhooks för real-time updates
- Rich calendar features (findMeetingTimes, free/busy)

---

## 2. UNIFIED PROVIDER ABSTRACTION LAYER

### 2.1 Arkitektur-Diagram

```
┌─────────────────────────────────────────────────────────┐
│                   Frontend (React)                      │
│  - EmailList, CategoryFilter, ActionBar, Calendar      │
└────────────────────┬────────────────────────────────────┘
                     │ REST API
┌────────────────────▼────────────────────────────────────┐
│              Email API Service (Port 3018)              │
│  - Unified REST endpoints (/api/emails, /api/calendar) │
└────────────────────┬────────────────────────────────────┘
                     │
          ┌──────────┴──────────┐
          ▼                     ▼
┌─────────────────┐   ┌─────────────────────┐
│ EmailProvider   │   │  CalendarProvider   │
│  Interface      │   │    Interface        │
└────────┬────────┘   └──────────┬──────────┘
         │                       │
    ┌────┼─────┬────────┐   ┌────┼─────┬────────┐
    ▼    ▼     ▼        ▼   ▼    ▼     ▼        ▼
┌──────┐┌────┐┌──────┐┌────┐┌────┐┌────┐┌──────┐
│IMAP  ││Gmail││Graph││...  ││GCal││Ex  ││...   │
│Impl  ││Impl ││Impl ││     ││Impl││Impl││      │
└──────┘└────┘└──────┘└────┘└────┘└────┘└──────┘
```

### 2.2 Provider Interface Definition

```typescript
// services/email-providers/interfaces/EmailProvider.ts

interface EmailProvider {
  // Authentication
  authenticate(credentials: ProviderCredentials): Promise<AuthToken>
  refreshToken(refreshToken: string): Promise<AuthToken>

  // Email Operations
  fetchEmails(options: FetchOptions): Promise<Email[]>
  getEmail(id: string): Promise<Email>
  sendEmail(draft: EmailDraft): Promise<SentEmail>

  // Flags & States
  setFlag(emailId: string, flag: EmailFlag): Promise<void>
  removeFlag(emailId: string, flag: EmailFlag): Promise<void>
  markAsRead(emailId: string, read: boolean): Promise<void>

  // Labels/Categories (provider-specific mapping)
  addLabel(emailId: string, label: string): Promise<void>
  removeLabel(emailId: string, label: string): Promise<void>
  createLabel(label: LabelDefinition): Promise<Label>

  // Folders/Mailboxes
  listFolders(): Promise<Folder[]>
  moveToFolder(emailId: string, folderId: string): Promise<void>

  // Batch Operations
  batchUpdate(updates: BatchUpdate[]): Promise<BatchResult>

  // Search
  search(query: SearchQuery): Promise<Email[]>

  // Sync & Deltas
  getDelta(lastSyncToken?: string): Promise<DeltaResponse>

  // Provider Capabilities
  getCapabilities(): ProviderCapabilities
}

interface CalendarProvider {
  // Authentication
  authenticate(credentials: ProviderCredentials): Promise<AuthToken>

  // Calendar Operations
  listCalendars(): Promise<Calendar[]>
  getEvents(calendarId: string, options: EventQuery): Promise<CalendarEvent[]>
  createEvent(event: EventDefinition): Promise<CalendarEvent>
  updateEvent(eventId: string, updates: Partial<EventDefinition>): Promise<CalendarEvent>
  deleteEvent(eventId: string): Promise<void>

  // RSVP & Responses
  respondToInvite(eventId: string, response: 'accepted' | 'declined' | 'tentative', comment?: string): Promise<void>

  // Scheduling
  findMeetingTimes(attendees: string[], duration: number, constraints: TimeConstraints): Promise<MeetingTimeSuggestion[]>
  checkAvailability(attendees: string[], timeRange: TimeRange): Promise<FreeBusyInfo[]>

  // Provider Capabilities
  getCapabilities(): CalendarCapabilities
}

// Shared Types
interface ProviderCapabilities {
  provider: 'imap' | 'gmail' | 'exchange'
  supportsMultipleLabels: boolean
  supportsThreading: boolean
  supportsSearch: boolean
  searchSyntax: 'basic' | 'gmail' | 'kql' // Exchange uses KQL
  supportsBatchOperations: boolean
  maxBatchSize: number
  supportsDeltaSync: boolean
  supportsWebhooks: boolean
  rateLimit: {
    requestsPerSecond: number
    requestsPerDay: number
  }
}

interface EmailFlag {
  type: 'system' | 'custom'
  name: string // \Seen, \Flagged, etc for system; custom for others
  value?: boolean | string
}

interface Email {
  id: string
  provider: string
  threadId?: string
  subject: string
  from: EmailAddress
  to: EmailAddress[]
  cc?: EmailAddress[]
  bcc?: EmailAddress[]
  date: Date
  bodyHtml?: string
  bodyText?: string
  flags: EmailFlag[]
  labels: string[]
  folderId?: string
  attachments: Attachment[]
  headers: Record<string, string>
  metadata: {
    isRead: boolean
    isFlagged: boolean
    isAnswered: boolean
    isDraft: boolean
  }
}
```

### 2.3 Provider Implementation Examples

#### A. IMAP Provider (Enhanced)

```javascript
// services/email-providers/impl/IMAPProvider.js

class IMAPProvider extends EmailProvider {
  constructor(config) {
    super()
    this.imap = new Imap({
      user: config.email,
      password: config.password, // eller OAuth token
      host: config.host,
      port: config.port || 993,
      tls: true,
      authTimeout: 10000
    })
  }

  async setFlag(emailId, flag) {
    const imapFlag = this.mapToIMAPFlag(flag)
    return new Promise((resolve, reject) => {
      this.imap.openBox('INBOX', false, (err) => {
        if (err) return reject(err)

        // IMAP uses UID or sequence number
        this.imap.addFlags(emailId, imapFlag, (err) => {
          if (err) return reject(err)
          resolve()
        })
      })
    })
  }

  mapToIMAPFlag(flag) {
    const mapping = {
      'flagged': '\\Flagged',
      'seen': '\\Seen',
      'answered': '\\Answered',
      'deleted': '\\Deleted',
      'draft': '\\Draft'
    }
    return mapping[flag.name] || flag.name
  }

  getCapabilities() {
    return {
      provider: 'imap',
      supportsMultipleLabels: false, // IMAP folders = one at a time
      supportsThreading: false,
      supportsSearch: true,
      searchSyntax: 'basic',
      supportsBatchOperations: false,
      maxBatchSize: 1,
      supportsDeltaSync: false,
      supportsWebhooks: false,
      rateLimit: {
        requestsPerSecond: 10,
        requestsPerDay: Infinity
      }
    }
  }
}
```

#### B. Gmail Provider

```javascript
// services/email-providers/impl/GmailProvider.js
const { google } = require('googleapis')

class GmailProvider extends EmailProvider {
  constructor(credentials) {
    super()
    this.oauth2Client = new google.auth.OAuth2(
      credentials.clientId,
      credentials.clientSecret,
      credentials.redirectUri
    )
    this.oauth2Client.setCredentials({
      access_token: credentials.accessToken,
      refresh_token: credentials.refreshToken
    })
    this.gmail = google.gmail({ version: 'v1', auth: this.oauth2Client })
  }

  async setFlag(emailId, flag) {
    if (flag.name === 'flagged') {
      // Gmail's STARRED label
      return this.gmail.users.messages.modify({
        userId: 'me',
        id: emailId,
        requestBody: {
          addLabelIds: ['STARRED']
        }
      })
    }

    if (flag.name === 'seen') {
      return this.gmail.users.messages.modify({
        userId: 'me',
        id: emailId,
        requestBody: {
          removeLabelIds: ['UNREAD']
        }
      })
    }
  }

  async batchUpdate(updates) {
    // Gmail supports batch requests up to 1000 items
    const batch = this.gmail.newBatch()

    updates.forEach(update => {
      batch.add(
        this.gmail.users.messages.modify({
          userId: 'me',
          id: update.emailId,
          requestBody: update.modifications
        })
      )
    })

    return batch.execute()
  }

  async getDelta(lastSyncToken) {
    // Gmail History API
    const response = await this.gmail.users.history.list({
      userId: 'me',
      startHistoryId: lastSyncToken,
      historyTypes: ['messageAdded', 'messageDeleted', 'labelAdded', 'labelRemoved']
    })

    return {
      changes: response.data.history || [],
      nextSyncToken: response.data.historyId
    }
  }

  getCapabilities() {
    return {
      provider: 'gmail',
      supportsMultipleLabels: true,
      supportsThreading: true,
      supportsSearch: true,
      searchSyntax: 'gmail', // from:user@example.com has:attachment
      supportsBatchOperations: true,
      maxBatchSize: 1000,
      supportsDeltaSync: true,
      supportsWebhooks: true,
      rateLimit: {
        requestsPerSecond: 250,
        requestsPerDay: 1000000000 // Practically unlimited with quota
      }
    }
  }
}
```

#### C. Microsoft Graph Provider

```javascript
// services/email-providers/impl/GraphProvider.js
const { Client } = require('@microsoft/microsoft-graph-client')

class GraphProvider extends EmailProvider {
  constructor(credentials) {
    super()
    this.client = Client.init({
      authProvider: async (done) => {
        done(null, credentials.accessToken)
      }
    })
  }

  async setFlag(emailId, flag) {
    if (flag.name === 'flagged') {
      return this.client
        .api(`/me/messages/${emailId}`)
        .patch({
          flag: {
            flagStatus: 'flagged'
          }
        })
    }

    if (flag.name === 'seen') {
      return this.client
        .api(`/me/messages/${emailId}`)
        .patch({
          isRead: true
        })
    }
  }

  async fetchEmails(options) {
    const response = await this.client
      .api('/me/messages')
      .top(options.limit || 50)
      .skip(options.offset || 0)
      .select('id,subject,from,receivedDateTime,bodyPreview,isRead,flag,categories')
      .orderby('receivedDateTime DESC')
      .get()

    return response.value.map(this.transformGraphEmail)
  }

  transformGraphEmail(graphEmail) {
    return {
      id: graphEmail.id,
      provider: 'exchange',
      subject: graphEmail.subject,
      from: {
        address: graphEmail.from.emailAddress.address,
        name: graphEmail.from.emailAddress.name
      },
      date: new Date(graphEmail.receivedDateTime),
      bodyText: graphEmail.bodyPreview,
      flags: this.extractFlags(graphEmail),
      labels: graphEmail.categories || [],
      metadata: {
        isRead: graphEmail.isRead,
        isFlagged: graphEmail.flag?.flagStatus === 'flagged',
        isAnswered: false, // Not directly available
        isDraft: false
      }
    }
  }

  async getDelta(lastSyncToken) {
    const endpoint = lastSyncToken
      ? `/me/messages/delta?$deltatoken=${lastSyncToken}`
      : '/me/messages/delta'

    const response = await this.client.api(endpoint).get()

    return {
      changes: response.value,
      nextSyncToken: response['@odata.deltaLink']?.match(/\$deltatoken=([^&]+)/)?.[1]
    }
  }

  getCapabilities() {
    return {
      provider: 'exchange',
      supportsMultipleLabels: true, // Categories
      supportsThreading: true, // conversationId
      supportsSearch: true,
      searchSyntax: 'kql', // Keyword Query Language
      supportsBatchOperations: true,
      maxBatchSize: 20, // Graph batch limit
      supportsDeltaSync: true,
      supportsWebhooks: true,
      rateLimit: {
        requestsPerSecond: 2000,
        requestsPerDay: Infinity
      }
    }
  }
}
```

---

## 3. CALENDAR INTEGRATION DESIGN

### 3.1 Unified Calendar Interface

```typescript
// Calendar Event Format (unified across providers)
interface CalendarEvent {
  id: string
  provider: 'google' | 'exchange'
  calendarId: string

  // Core fields
  title: string
  description?: string
  location?: string
  start: DateTime
  end: DateTime
  isAllDay: boolean

  // Attendees & RSVP
  organizer: Person
  attendees: Attendee[]
  responseStatus?: 'accepted' | 'declined' | 'tentative' | 'needsAction'

  // Recurrence
  recurrence?: RecurrenceRule

  // Metadata
  created: DateTime
  updated: DateTime
  status: 'confirmed' | 'tentative' | 'cancelled'

  // Provider-specific
  iCalUID?: string // For interoperability
  htmlLink?: string // Link to event in calendar UI
  conferenceData?: ConferenceInfo // Meet, Teams, etc
}

interface Attendee {
  email: string
  name?: string
  responseStatus: 'accepted' | 'declined' | 'tentative' | 'needsAction'
  optional: boolean
}

interface ConferenceInfo {
  type: 'googleMeet' | 'microsoftTeams' | 'zoom' | 'other'
  joinUrl: string
  conferenceId?: string
}
```

### 3.2 Google Calendar Provider

```javascript
// services/calendar-providers/impl/GoogleCalendarProvider.js
const { google } = require('googleapis')

class GoogleCalendarProvider extends CalendarProvider {
  constructor(credentials) {
    super()
    this.oauth2Client = new google.auth.OAuth2(
      credentials.clientId,
      credentials.clientSecret,
      credentials.redirectUri
    )
    this.oauth2Client.setCredentials(credentials.tokens)
    this.calendar = google.calendar({ version: 'v3', auth: this.oauth2Client })
  }

  async createEvent(event) {
    const response = await this.calendar.events.insert({
      calendarId: event.calendarId || 'primary',
      requestBody: {
        summary: event.title,
        description: event.description,
        location: event.location,
        start: {
          dateTime: event.start.toISOString(),
          timeZone: event.timezone || 'Europe/Stockholm'
        },
        end: {
          dateTime: event.end.toISOString(),
          timeZone: event.timezone || 'Europe/Stockholm'
        },
        attendees: event.attendees?.map(a => ({
          email: a.email,
          displayName: a.name,
          optional: a.optional
        })),
        conferenceData: event.createMeetLink ? {
          createRequest: {
            requestId: `meet-${Date.now()}`,
            conferenceSolutionKey: { type: 'hangoutsMeet' }
          }
        } : undefined
      },
      conferenceDataVersion: event.createMeetLink ? 1 : undefined
    })

    return this.transformGoogleEvent(response.data)
  }

  async respondToInvite(eventId, response, comment) {
    // Google Calendar doesn't have direct RSVP endpoint
    // Must update attendee status via PATCH
    const event = await this.calendar.events.get({
      calendarId: 'primary',
      eventId: eventId
    })

    const updatedAttendees = event.data.attendees?.map(attendee => {
      if (attendee.self) {
        return {
          ...attendee,
          responseStatus: response === 'accepted' ? 'accepted' :
                         response === 'declined' ? 'declined' : 'tentative',
          comment: comment
        }
      }
      return attendee
    })

    return this.calendar.events.patch({
      calendarId: 'primary',
      eventId: eventId,
      requestBody: {
        attendees: updatedAttendees
      },
      sendUpdates: 'all' // Notify organizer
    })
  }

  async findMeetingTimes(attendees, duration, constraints) {
    // Google Calendar doesn't have findMeetingTimes
    // Must use freebusy query + local logic
    const now = new Date()
    const weekFromNow = new Date(now.getTime() + 7 * 24 * 60 * 60 * 1000)

    const freebusyResponse = await this.calendar.freebusy.query({
      requestBody: {
        timeMin: constraints.earliestStart || now.toISOString(),
        timeMax: constraints.latestEnd || weekFromNow.toISOString(),
        items: attendees.map(email => ({ id: email }))
      }
    })

    // Process busy periods and find gaps
    return this.findAvailableSlots(freebusyResponse.data, duration, constraints)
  }

  getCapabilities() {
    return {
      provider: 'google',
      supportsMultipleCalendars: true,
      supportsRecurrence: true,
      supportsConferencing: true,
      conferenceTypes: ['googleMeet'],
      supportsFreeBusy: true,
      supportsSmartScheduling: false, // No native findMeetingTimes
      supportsWebhooks: true,
      maxAttendeesPerEvent: 200
    }
  }
}
```

### 3.3 Exchange Calendar Provider

```javascript
// services/calendar-providers/impl/ExchangeCalendarProvider.js
const { Client } = require('@microsoft/microsoft-graph-client')

class ExchangeCalendarProvider extends CalendarProvider {
  constructor(credentials) {
    super()
    this.client = Client.init({
      authProvider: (done) => done(null, credentials.accessToken)
    })
  }

  async createEvent(event) {
    const response = await this.client
      .api('/me/events')
      .post({
        subject: event.title,
        body: {
          contentType: 'HTML',
          content: event.description || ''
        },
        start: {
          dateTime: event.start.toISOString(),
          timeZone: event.timezone || 'Europe/Stockholm'
        },
        end: {
          dateTime: event.end.toISOString(),
          timeZone: event.timezone || 'Europe/Stockholm'
        },
        location: {
          displayName: event.location
        },
        attendees: event.attendees?.map(a => ({
          emailAddress: {
            address: a.email,
            name: a.name
          },
          type: a.optional ? 'optional' : 'required'
        })),
        isOnlineMeeting: event.createMeetLink,
        onlineMeetingProvider: event.createMeetLink ? 'teamsForBusiness' : undefined
      })

    return this.transformExchangeEvent(response)
  }

  async respondToInvite(eventId, response, comment) {
    const action = response === 'accepted' ? 'accept' :
                   response === 'declined' ? 'decline' : 'tentativelyAccept'

    return this.client
      .api(`/me/events/${eventId}/${action}`)
      .post({
        comment: comment,
        sendResponse: true
      })
  }

  async findMeetingTimes(attendees, duration, constraints) {
    // Graph API has native findMeetingTimes!
    const response = await this.client
      .api('/me/findMeetingTimes')
      .post({
        attendees: attendees.map(email => ({
          type: 'required',
          emailAddress: { address: email }
        })),
        timeConstraint: {
          timeslots: [{
            start: {
              dateTime: constraints.earliestStart.toISOString(),
              timeZone: 'Europe/Stockholm'
            },
            end: {
              dateTime: constraints.latestEnd.toISOString(),
              timeZone: 'Europe/Stockholm'
            }
          }]
        },
        meetingDuration: `PT${duration}M`, // ISO 8601 duration
        maxCandidates: 10
      })

    return response.meetingTimeSuggestions.map(suggestion => ({
      start: new Date(suggestion.meetingTimeSlot.start.dateTime),
      end: new Date(suggestion.meetingTimeSlot.end.dateTime),
      confidence: suggestion.confidence, // 0-100
      attendeeAvailability: suggestion.attendeeAvailability
    }))
  }

  getCapabilities() {
    return {
      provider: 'exchange',
      supportsMultipleCalendars: true,
      supportsRecurrence: true,
      supportsConferencing: true,
      conferenceTypes: ['microsoftTeams'],
      supportsFreeBusy: true,
      supportsSmartScheduling: true, // Native findMeetingTimes
      supportsWebhooks: true,
      maxAttendeesPerEvent: 500
    }
  }
}
```

---

## 4. DATABASE SCHEMA FÖR MULTI-PROVIDER

### 4.1 Account Management

```sql
-- Email Accounts (stöd för flera providers)
CREATE TABLE email_accounts (
  id SERIAL PRIMARY KEY,
  user_id VARCHAR(100) NOT NULL,
  provider VARCHAR(20) NOT NULL, -- 'imap', 'gmail', 'exchange'
  email_address VARCHAR(255) NOT NULL,
  display_name VARCHAR(255),

  -- Authentication
  auth_type VARCHAR(20) NOT NULL, -- 'oauth', 'password', 'app_password'
  credentials_encrypted TEXT, -- Encrypted JSON blob

  -- OAuth tokens (om applicable)
  access_token TEXT,
  refresh_token TEXT,
  token_expires_at TIMESTAMP,

  -- Provider-specific config
  provider_config JSONB, -- {host: "imap.gmail.com", port: 993, etc}

  -- Sync state
  last_sync_at TIMESTAMP,
  sync_token VARCHAR(500), -- Delta sync token (Gmail historyId, Graph deltatoken)
  sync_enabled BOOLEAN DEFAULT true,

  -- Status
  is_active BOOLEAN DEFAULT true,
  status VARCHAR(20) DEFAULT 'connected', -- connected, auth_failed, disabled
  last_error TEXT,

  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),

  UNIQUE(user_id, email_address)
);

CREATE INDEX idx_email_accounts_user ON email_accounts(user_id);
CREATE INDEX idx_email_accounts_provider ON email_accounts(provider);
```

### 4.2 Email Storage (Provider-Agnostic)

```sql
-- Emails (unified storage)
CREATE TABLE emails (
  id SERIAL PRIMARY KEY,
  account_id INTEGER REFERENCES email_accounts(id) ON DELETE CASCADE,

  -- Provider IDs
  provider_message_id VARCHAR(500) NOT NULL, -- Gmail message ID, Graph ID, IMAP UID
  provider_thread_id VARCHAR(500), -- For threading support

  -- Email Headers
  subject TEXT,
  from_address VARCHAR(500),
  from_name VARCHAR(255),
  to_addresses JSONB, -- [{address: "x@y.com", name: "X"}]
  cc_addresses JSONB,
  bcc_addresses JSONB,
  reply_to VARCHAR(500),

  -- Content
  body_text TEXT,
  body_html TEXT,
  body_preview VARCHAR(500), -- First 500 chars

  -- Metadata
  received_at TIMESTAMP NOT NULL,
  sent_at TIMESTAMP,

  -- Flags (unified representation)
  is_read BOOLEAN DEFAULT false,
  is_flagged BOOLEAN DEFAULT false,
  is_answered BOOLEAN DEFAULT false,
  is_draft BOOLEAN DEFAULT false,
  is_deleted BOOLEAN DEFAULT false,

  -- Provider-specific flags
  provider_flags JSONB, -- Store raw provider flags

  -- Attachments
  has_attachments BOOLEAN DEFAULT false,
  attachment_count INTEGER DEFAULT 0,

  -- Full headers (för advanced features)
  raw_headers JSONB,

  -- Folder/Labels
  folder_id VARCHAR(255), -- Provider folder ID
  folder_path VARCHAR(500), -- Human-readable path

  -- Size
  size_bytes INTEGER,

  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),

  UNIQUE(account_id, provider_message_id)
);

CREATE INDEX idx_emails_account ON emails(account_id);
CREATE INDEX idx_emails_received ON emails(received_at DESC);
CREATE INDEX idx_emails_thread ON emails(provider_thread_id);
CREATE INDEX idx_emails_flags ON emails(is_read, is_flagged, is_deleted);
```

### 4.3 Labels/Folders (Unified)

```sql
-- Labels (works for both Gmail labels and IMAP/Exchange folders)
CREATE TABLE labels (
  id SERIAL PRIMARY KEY,
  account_id INTEGER REFERENCES email_accounts(id) ON DELETE CASCADE,

  -- Provider info
  provider_label_id VARCHAR(255), -- Gmail label ID, folder path, etc
  name VARCHAR(255) NOT NULL,
  display_name VARCHAR(255),

  -- Type
  label_type VARCHAR(20) NOT NULL, -- 'system', 'user', 'ai_generated'
  is_system BOOLEAN DEFAULT false,

  -- Visual
  color VARCHAR(7), -- #RRGGBB
  icon VARCHAR(50), -- Emoji or icon name

  -- Hierarchy (for folder-based providers)
  parent_id INTEGER REFERENCES labels(id),
  path VARCHAR(500), -- Full path like "Work/Projects/Q4"

  -- Policy & Rules
  policy JSONB, -- {icon: "📧", rules: {...}, created_by: "ai"}

  -- Stats
  email_count INTEGER DEFAULT 0,
  unread_count INTEGER DEFAULT 0,

  -- Settings
  enabled BOOLEAN DEFAULT true,
  show_in_ui BOOLEAN DEFAULT true,

  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),

  UNIQUE(account_id, provider_label_id)
);

CREATE INDEX idx_labels_account ON labels(account_id);
CREATE INDEX idx_labels_type ON labels(label_type);
```

### 4.4 Email-Label Relations (Many-to-Many)

```sql
-- Email <-> Label junction (supports multiple labels per email)
CREATE TABLE email_labels (
  id SERIAL PRIMARY KEY,
  email_id INTEGER REFERENCES emails(id) ON DELETE CASCADE,
  label_id INTEGER REFERENCES labels(id) ON DELETE CASCADE,

  -- ML/AI confidence
  score DECIMAL(3,2),
  confidence DECIMAL(3,2),
  source VARCHAR(50), -- 'ai', 'ml', 'user', 'rule'

  decided_at TIMESTAMP DEFAULT NOW(),

  UNIQUE(email_id, label_id)
);

CREATE INDEX idx_email_labels_email ON email_labels(email_id);
CREATE INDEX idx_email_labels_label ON email_labels(label_id);
```

### 4.5 Calendar Events (Multi-Provider)

```sql
-- Calendar Accounts
CREATE TABLE calendar_accounts (
  id SERIAL PRIMARY KEY,
  email_account_id INTEGER REFERENCES email_accounts(id),
  user_id VARCHAR(100) NOT NULL,
  provider VARCHAR(20) NOT NULL, -- 'google', 'exchange'

  -- Auth (usually same as email account)
  access_token TEXT,
  refresh_token TEXT,
  token_expires_at TIMESTAMP,

  -- Default calendar
  default_calendar_id VARCHAR(255),

  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMP DEFAULT NOW(),

  UNIQUE(user_id, provider)
);

-- Calendars
CREATE TABLE calendars (
  id SERIAL PRIMARY KEY,
  calendar_account_id INTEGER REFERENCES calendar_accounts(id),
  provider_calendar_id VARCHAR(255) NOT NULL,

  name VARCHAR(255) NOT NULL,
  description TEXT,
  timezone VARCHAR(100) DEFAULT 'Europe/Stockholm',
  color VARCHAR(7),

  -- Permissions
  access_role VARCHAR(20), -- owner, writer, reader
  can_edit BOOLEAN DEFAULT false,

  is_primary BOOLEAN DEFAULT false,

  created_at TIMESTAMP DEFAULT NOW(),

  UNIQUE(calendar_account_id, provider_calendar_id)
);

-- Calendar Events
CREATE TABLE calendar_events (
  id SERIAL PRIMARY KEY,
  calendar_id INTEGER REFERENCES calendars(id),
  provider_event_id VARCHAR(255) NOT NULL,

  -- Core fields
  title VARCHAR(500) NOT NULL,
  description TEXT,
  location VARCHAR(500),

  start_time TIMESTAMP NOT NULL,
  end_time TIMESTAMP NOT NULL,
  is_all_day BOOLEAN DEFAULT false,
  timezone VARCHAR(100) DEFAULT 'Europe/Stockholm',

  -- Organizer & Attendees
  organizer_email VARCHAR(255),
  organizer_name VARCHAR(255),
  attendees JSONB, -- [{email, name, responseStatus, optional}]

  -- User's response
  response_status VARCHAR(20), -- accepted, declined, tentative, needsAction

  -- Recurrence
  recurrence_rule TEXT, -- RRULE format
  is_recurring BOOLEAN DEFAULT false,
  recurring_event_id VARCHAR(255),

  -- Meeting info
  conference_data JSONB, -- {type: "googleMeet", joinUrl: "..."}

  -- Status
  status VARCHAR(20) DEFAULT 'confirmed', -- confirmed, tentative, cancelled

  -- iCal
  ical_uid VARCHAR(500), -- For interoperability

  -- Metadata
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  synced_at TIMESTAMP DEFAULT NOW(),

  UNIQUE(calendar_id, provider_event_id)
);

CREATE INDEX idx_calendar_events_time ON calendar_events(start_time, end_time);
CREATE INDEX idx_calendar_events_status ON calendar_events(response_status);
```

### 4.6 Email-Calendar Links

```sql
-- Link emails to calendar events (for tracking meeting invites)
CREATE TABLE email_calendar_links (
  id SERIAL PRIMARY KEY,
  email_id INTEGER REFERENCES emails(id) ON DELETE CASCADE,
  calendar_event_id INTEGER REFERENCES calendar_events(id) ON DELETE CASCADE,

  link_type VARCHAR(20), -- 'invite', 'update', 'cancellation', 'response'

  -- ICS attachment info
  ics_method VARCHAR(20), -- REQUEST, REPLY, CANCEL, etc
  ics_uid VARCHAR(500),

  processed BOOLEAN DEFAULT false,
  auto_responded BOOLEAN DEFAULT false,

  created_at TIMESTAMP DEFAULT NOW(),

  UNIQUE(email_id, calendar_event_id)
);
```

---

## 5. API ENDPOINTS (Multi-Provider)

### 5.1 Account Management

```javascript
// Email Accounts
POST   /api/accounts/email
  {
    "provider": "gmail" | "exchange" | "imap",
    "email": "user@example.com",
    "authType": "oauth" | "password",
    "credentials": {...}
  }

GET    /api/accounts/email
  // Returns all email accounts for user

PUT    /api/accounts/email/:id/sync
  // Trigger manual sync

POST   /api/accounts/email/:id/refresh-token
  // Refresh OAuth token

DELETE /api/accounts/email/:id

// Calendar Accounts
POST   /api/accounts/calendar
GET    /api/accounts/calendar
DELETE /api/accounts/calendar/:id
```

### 5.2 Unified Email Endpoints (Provider-Agnostic)

```javascript
// Same endpoints work across all providers
GET    /api/emails?account_id=123&label=inbox&limit=50
POST   /api/emails/:id/flag
DELETE /api/emails/:id/flag
PUT    /api/emails/:id/read
POST   /api/emails/:id/labels
  {
    "add": ["work", "important"],
    "remove": ["inbox"]
  }
POST   /api/emails/:id/move
  {
    "targetFolder": "Archive"
  }

// Batch operations (provider optimizes internally)
POST   /api/emails/batch
  {
    "emailIds": ["1", "2", "3"],
    "operations": [
      {"type": "flag", "value": true},
      {"type": "addLabel", "label": "processed"}
    ]
  }
```

### 5.3 Calendar Endpoints

```javascript
GET    /api/calendar/events?start=2025-10-01&end=2025-10-31
POST   /api/calendar/events
  {
    "calendarId": "primary",
    "title": "Meeting",
    "start": "2025-10-02T14:00:00Z",
    "end": "2025-10-02T15:00:00Z",
    "attendees": ["person@example.com"],
    "createMeetLink": true
  }

PUT    /api/calendar/events/:id
DELETE /api/calendar/events/:id

POST   /api/calendar/events/:id/respond
  {
    "response": "accepted" | "declined" | "tentative",
    "comment": "Looking forward to it!"
  }

// Smart scheduling (Exchange native, Google emulated)
POST   /api/calendar/find-meeting-times
  {
    "attendees": ["a@ex.com", "b@ex.com"],
    "duration": 60,
    "constraints": {
      "earliestStart": "2025-10-02T09:00:00Z",
      "latestEnd": "2025-10-05T17:00:00Z",
      "preferredTimes": ["morning", "afternoon"]
    }
  }

// Free/Busy
POST   /api/calendar/free-busy
  {
    "emails": ["user1@ex.com", "user2@ex.com"],
    "start": "2025-10-02T00:00:00Z",
    "end": "2025-10-02T23:59:59Z"
  }
```

### 5.4 Email-to-Calendar Integration

```javascript
// Parse calendar invite from email
POST   /api/emails/:id/parse-calendar-invite
  // Returns parsed event data from .ics attachment

// Auto-respond to meeting invite
POST   /api/emails/:id/respond-to-invite
  {
    "response": "accepted",
    "addToCalendar": true,
    "replyMessage": "See you there!"
  }
  // Steps:
  // 1. Parse .ics from email
  // 2. Create event in user's calendar
  // 3. Send RSVP email with proper iCal REPLY
  // 4. Archive original email with "processed" label
```

---

## 6. OAUTH AUTHENTICATION FLOWS

### 6.1 Gmail OAuth Setup

```javascript
// services/auth/GmailOAuthHandler.js

class GmailOAuthHandler {
  constructor() {
    this.oauth2Client = new google.auth.OAuth2(
      process.env.GMAIL_CLIENT_ID,
      process.env.GMAIL_CLIENT_SECRET,
      process.env.GMAIL_REDIRECT_URI
    )
  }

  getAuthUrl(userId) {
    const scopes = [
      'https://www.googleapis.com/auth/gmail.modify',
      'https://www.googleapis.com/auth/gmail.send',
      'https://www.googleapis.com/auth/calendar',
      'https://www.googleapis.com/auth/calendar.events'
    ]

    return this.oauth2Client.generateAuthUrl({
      access_type: 'offline', // Get refresh token
      scope: scopes,
      state: userId, // Pass user ID for callback
      prompt: 'consent' // Force consent to get refresh token
    })
  }

  async handleCallback(code) {
    const { tokens } = await this.oauth2Client.getToken(code)

    // tokens.access_token, tokens.refresh_token, tokens.expiry_date
    return {
      accessToken: tokens.access_token,
      refreshToken: tokens.refresh_token,
      expiresAt: new Date(tokens.expiry_date)
    }
  }

  async refreshAccessToken(refreshToken) {
    this.oauth2Client.setCredentials({
      refresh_token: refreshToken
    })

    const { credentials } = await this.oauth2Client.refreshAccessToken()

    return {
      accessToken: credentials.access_token,
      expiresAt: new Date(credentials.expiry_date)
    }
  }
}
```

### 6.2 Exchange/Microsoft Graph OAuth

```javascript
// services/auth/MicrosoftOAuthHandler.js
const msal = require('@azure/msal-node')

class MicrosoftOAuthHandler {
  constructor() {
    this.msalConfig = {
      auth: {
        clientId: process.env.MICROSOFT_CLIENT_ID,
        authority: 'https://login.microsoftonline.com/common',
        clientSecret: process.env.MICROSOFT_CLIENT_SECRET
      }
    }
    this.pca = new msal.ConfidentialClientApplication(this.msalConfig)
  }

  getAuthUrl(userId) {
    const authCodeUrlParameters = {
      scopes: [
        'https://graph.microsoft.com/Mail.ReadWrite',
        'https://graph.microsoft.com/Mail.Send',
        'https://graph.microsoft.com/Calendars.ReadWrite',
        'offline_access' // For refresh token
      ],
      redirectUri: process.env.MICROSOFT_REDIRECT_URI,
      state: userId
    }

    return this.pca.getAuthCodeUrl(authCodeUrlParameters)
  }

  async handleCallback(code) {
    const tokenRequest = {
      code: code,
      scopes: ['https://graph.microsoft.com/.default'],
      redirectUri: process.env.MICROSOFT_REDIRECT_URI
    }

    const response = await this.pca.acquireTokenByCode(tokenRequest)

    return {
      accessToken: response.accessToken,
      refreshToken: response.refreshToken,
      expiresAt: new Date(response.expiresOn)
    }
  }

  async refreshAccessToken(refreshToken) {
    const refreshTokenRequest = {
      refreshToken: refreshToken,
      scopes: ['https://graph.microsoft.com/.default']
    }

    const response = await this.pca.acquireTokenByRefreshToken(refreshTokenRequest)

    return {
      accessToken: response.accessToken,
      expiresAt: new Date(response.expiresOn)
    }
  }
}
```

---

## 7. FLAG SYNCHRONIZATION STRATEGY

### 7.1 Bi-directional Flag Sync

**Problem:** Användaren ändrar flagga i Gmail web UI → Måste synkas till vår DB

**Solution:** Delta sync + Webhooks

```javascript
// services/sync/FlagSyncService.js

class FlagSyncService {
  async syncFlags(accountId) {
    const account = await db.getEmailAccount(accountId)
    const provider = this.getProvider(account)

    // Get changes since last sync
    const delta = await provider.getDelta(account.sync_token)

    for (const change of delta.changes) {
      if (change.type === 'flagChanged') {
        await this.updateLocalFlags(change.emailId, change.newFlags)
      }
    }

    // Update sync token
    await db.updateSyncToken(accountId, delta.nextSyncToken)
  }

  async updateLocalFlags(emailId, providerFlags) {
    const localEmail = await db.getEmailByProviderId(emailId)

    // Map provider flags to our unified format
    const unifiedFlags = {
      is_read: this.hasFlag(providerFlags, 'seen'),
      is_flagged: this.hasFlag(providerFlags, 'flagged'),
      is_answered: this.hasFlag(providerFlags, 'answered'),
      provider_flags: providerFlags // Store raw for reference
    }

    await db.updateEmailFlags(localEmail.id, unifiedFlags)
  }

  async setFlagRemote(emailId, flag, value) {
    const email = await db.getEmail(emailId)
    const account = await db.getEmailAccount(email.account_id)
    const provider = this.getProvider(account)

    // Update on provider
    if (value) {
      await provider.setFlag(email.provider_message_id, flag)
    } else {
      await provider.removeFlag(email.provider_message_id, flag)
    }

    // Update locally
    await this.updateLocalFlags(email.provider_message_id, {...})
  }
}
```

### 7.2 Webhook Setup (Gmail & Graph)

```javascript
// Gmail Push Notifications
async function setupGmailWebhook(accountId) {
  const gmail = getGmailClient(accountId)

  await gmail.users.watch({
    userId: 'me',
    requestBody: {
      topicName: 'projects/my-project/topics/gmail-notifications',
      labelIds: ['INBOX', 'SENT'],
      labelFilterAction: 'include'
    }
  })
}

// Webhook receiver
app.post('/webhooks/gmail', async (req, res) => {
  const message = Buffer.from(req.body.message.data, 'base64').toString()
  const notification = JSON.parse(message)

  const accountId = notification.emailAddress // Map to our account

  // Trigger delta sync
  await flagSyncService.syncFlags(accountId)

  res.status(200).send('OK')
})

// Microsoft Graph Subscriptions
async function setupGraphWebhook(accountId) {
  const client = getGraphClient(accountId)

  await client.api('/subscriptions').post({
    changeType: 'updated',
    notificationUrl: 'https://my-server.com/webhooks/graph',
    resource: '/me/messages',
    expirationDateTime: new Date(Date.now() + 3 * 24 * 60 * 60 * 1000).toISOString(), // 3 days
    clientState: accountId // For verification
  })
}
```

---

## 8. IMPLEMENTATION ROADMAP

### Phase 1: Gmail Integration (3-4 veckor)
**Priority: CRITICAL** (OAuth mandatory från 14 mars 2025)

**Week 1-2:**
1. Setup Gmail OAuth flow (GmailOAuthHandler)
2. Implement GmailProvider med alla EmailProvider methods
3. Database schema för email_accounts, multi-provider support
4. Frontend: OAuth connection UI

**Week 3:**
5. Gmail flag sync (bi-directional)
6. Gmail webhook setup för real-time updates
7. Batch operations med Gmail API

**Week 4:**
8. Google Calendar integration (GoogleCalendarProvider)
9. Calendar OAuth setup
10. Meeting invite parsing + auto-response

### Phase 2: Exchange/Outlook Integration (3-4 veckor)

**Week 1-2:**
1. Setup Microsoft Graph OAuth (MicrosoftOAuthHandler)
2. Implement GraphProvider för email operations
3. Flag/category mapping Exchange ↔ unified format

**Week 3:**
4. ExchangeCalendarProvider implementation
5. findMeetingTimes integration
6. Teams meeting link support

**Week 4:**
7. Graph API webhooks
8. Delta sync optimization
9. Testing med Exchange mailboxes

### Phase 3: Unified Provider Abstraction (2 veckor)

**Week 1:**
1. Finalize EmailProvider interface
2. Provider capability detection
3. Provider selection logic (auto-detect från email domain)

**Week 2:**
4. Provider health monitoring
5. Error handling & retry logic
6. Migration guide för IMAP → OAuth

### Phase 4: Enhanced Features (2-3 veckor)

**Week 1:**
1. Multi-account support i UI
2. Account switching
3. Unified inbox (aggregate across accounts)

**Week 2:**
4. Smart scheduling UI (findMeetingTimes)
5. Calendar conflict detection
6. Auto-RSVP rules

**Week 3:**
7. Performance optimization (caching, batching)
8. Load testing
9. Documentation

---

## 9. MIGRATION STRATEGY

### 9.1 Från Nuvarande IMAP till Multi-Provider

```sql
-- Migration script
-- Step 1: Create new schema
-- (Run all CREATE TABLE statements from section 4)

-- Step 2: Migrate existing emails
INSERT INTO email_accounts (user_id, provider, email_address, auth_type, credentials_encrypted)
SELECT
  'default' as user_id,
  'imap' as provider,
  'user@example.com' as email_address, -- From env/config
  'password' as auth_type,
  pgp_sym_encrypt(json_build_object(
    'host', 'imap.gmail.com',
    'port', 993,
    'username', 'user@example.com',
    'password', 'app_password'
  )::text, 'encryption_key') as credentials_encrypted;

-- Step 3: Migrate emails
INSERT INTO emails (
  account_id,
  provider_message_id,
  subject,
  from_address,
  from_name,
  received_at,
  body_text,
  body_html,
  is_read,
  is_flagged
)
SELECT
  (SELECT id FROM email_accounts WHERE provider = 'imap' LIMIT 1) as account_id,
  uid::text as provider_message_id,
  subject,
  from_address,
  from_name,
  received_at,
  text_content,
  html_content,
  flags ? '\\Seen' as is_read,
  flags ? '\\Flagged' as is_flagged
FROM old_emails_table;

-- Step 4: Migrate labels
-- (Similar mapping from old schema)
```

### 9.2 User Migration Path

**Option 1: Gradual Migration (Rekommenderat)**
1. Användare fortsätter med IMAP
2. Vi visar banner: "Upgrade to Gmail OAuth for better performance"
3. User klickar → OAuth flow → new account skapas
4. Emails synkas från Gmail API (snabbare)
5. Old IMAP account kan deaktiveras

**Option 2: Forced Migration (Efter 14 mars 2025)**
1. Detektera Gmail-konton via IMAP
2. Force OAuth-setup vid nästa login
3. Disable IMAP access automatiskt

---

## 10. SÄKERHET & COMPLIANCE

### 10.1 Token Storage

```javascript
// Encrypt OAuth tokens before storing
const crypto = require('crypto')

function encryptToken(token, secretKey) {
  const iv = crypto.randomBytes(16)
  const cipher = crypto.createCipheriv('aes-256-cbc', Buffer.from(secretKey), iv)
  let encrypted = cipher.update(token, 'utf8', 'hex')
  encrypted += cipher.final('hex')
  return iv.toString('hex') + ':' + encrypted
}

function decryptToken(encryptedToken, secretKey) {
  const parts = encryptedToken.split(':')
  const iv = Buffer.from(parts[0], 'hex')
  const encrypted = parts[1]
  const decipher = crypto.createDecipheriv('aes-256-cbc', Buffer.from(secretKey), iv)
  let decrypted = decipher.update(encrypted, 'hex', 'utf8')
  decrypted += decipher.final('utf8')
  return decrypted
}

// Använd PostgreSQL pgcrypto för encryption at rest
```

### 10.2 GDPR Compliance

```sql
-- User data export
CREATE FUNCTION export_user_data(p_user_id VARCHAR)
RETURNS JSON AS $$
  SELECT json_build_object(
    'email_accounts', (SELECT json_agg(row_to_json(ea.*)) FROM email_accounts ea WHERE user_id = p_user_id),
    'emails', (SELECT json_agg(row_to_json(e.*)) FROM emails e JOIN email_accounts ea ON e.account_id = ea.id WHERE ea.user_id = p_user_id),
    'calendar_events', (...)
  );
$$ LANGUAGE SQL;

-- User data deletion
CREATE FUNCTION delete_user_data(p_user_id VARCHAR)
RETURNS VOID AS $$
BEGIN
  DELETE FROM email_accounts WHERE user_id = p_user_id;
  -- Cascade deletes emails, labels, calendar events
END;
$$ LANGUAGE plpgsql;
```

---

## 11. TESTING STRATEGY

### 11.1 Provider Mocking

```javascript
// tests/mocks/MockGmailProvider.js
class MockGmailProvider extends EmailProvider {
  async fetchEmails(options) {
    return [
      {
        id: 'mock-1',
        subject: 'Test Email',
        from: { address: 'test@example.com' },
        flags: [{ type: 'system', name: 'seen', value: true }]
      }
    ]
  }

  async setFlag(emailId, flag) {
    // Mock implementation - store in memory
    this.flags = this.flags || {}
    this.flags[emailId] = this.flags[emailId] || []
    this.flags[emailId].push(flag)
  }
}
```

### 11.2 Integration Tests

```javascript
// tests/integration/gmail-provider.test.js
describe('GmailProvider', () => {
  let provider

  beforeAll(async () => {
    // Use test account credentials
    provider = new GmailProvider({
      accessToken: process.env.GMAIL_TEST_ACCESS_TOKEN,
      refreshToken: process.env.GMAIL_TEST_REFRESH_TOKEN
    })
  })

  test('should fetch emails', async () => {
    const emails = await provider.fetchEmails({ limit: 10 })
    expect(emails).toHaveLength(10)
    expect(emails[0]).toHaveProperty('id')
  })

  test('should set flag', async () => {
    const email = await provider.getEmail('test-message-id')
    await provider.setFlag(email.id, { type: 'system', name: 'flagged' })

    const updated = await provider.getEmail(email.id)
    expect(updated.metadata.isFlagged).toBe(true)
  })
})
```

---

## 12. SLUTSATS

### Sammanfattning

Denna design ger en komplett multi-provider email & calendar-lösning som:

✅ **Stödjer alla major providers:** IMAP, Gmail API, Microsoft Graph
✅ **Unified abstraction:** Single API för frontend, provider-agnostic
✅ **Standards-compliant:** RFC 3501 IMAP flags, iCal/ICS support
✅ **OAuth-ready:** Gmail från mars 2025, Exchange Graph API
✅ **Bi-directional sync:** Flags synkas mellan vår app och original client
✅ **Calendar integration:** Mötesbokningar, auto-RSVP, smart scheduling
✅ **Future-proof:** Lätt att lägga till nya providers (Yahoo, iCloud, etc)

### Nyckelfunktioner

**Email Operations:**
- ✅ Flagga emails (synkas till Gmail/Exchange/IMAP)
- ✅ Multiple labels per email (Gmail native, emulerat för andra)
- ✅ Batch operations (optimerat per provider)
- ✅ Real-time sync via webhooks
- ✅ Delta sync (endast hämta ändringar)

**Calendar Operations:**
- ✅ Parse meeting invites från .ics attachments
- ✅ Auto-respond till meetings (RSVP)
- ✅ Create events med Meet/Teams links
- ✅ Find meeting times (native i Exchange, emulerat i Google)
- ✅ Free/busy queries
- ✅ Conflict detection

### Total Implementation Tid

**10-13 veckor** för full multi-provider support:
- Phase 1 (Gmail): 3-4 veckor
- Phase 2 (Exchange): 3-4 veckor
- Phase 3 (Abstraction): 2 veckor
- Phase 4 (Enhanced): 2-3 veckor

### Kritiska Milestones

📅 **14 mars 2025:** Gmail OAuth mandatory → Gmail integration MÅSTE vara klar
📅 **Oktober 2026:** Exchange EWS deprecation → Graph API migration kan vänta

**Rekommendation:** Börja med Gmail integration (Phase 1) omedelbart p.g.a. mars 2025 deadline.
