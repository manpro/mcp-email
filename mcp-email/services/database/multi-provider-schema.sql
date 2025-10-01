-- Multi-Provider Email & Calendar Database Schema
-- Supports: IMAP, Gmail API, Microsoft Graph (Exchange/Outlook)
-- Created: 2025-10-01

-- ============================================================================
-- PART 1: EMAIL ACCOUNTS & AUTHENTICATION
-- ============================================================================

-- Email Accounts (multi-provider support)
CREATE TABLE IF NOT EXISTS email_accounts (
  id SERIAL PRIMARY KEY,
  user_id VARCHAR(100) NOT NULL,
  provider VARCHAR(20) NOT NULL CHECK (provider IN ('imap', 'gmail', 'exchange')),
  email_address VARCHAR(255) NOT NULL,
  display_name VARCHAR(255),

  -- Authentication
  auth_type VARCHAR(20) NOT NULL CHECK (auth_type IN ('oauth', 'password', 'app_password')),
  credentials_encrypted TEXT, -- Encrypted JSON blob

  -- OAuth tokens (if applicable)
  access_token TEXT,
  refresh_token TEXT,
  token_expires_at TIMESTAMP,
  token_scopes TEXT[], -- Array of granted scopes

  -- Provider-specific config
  provider_config JSONB DEFAULT '{}'::jsonb,
  -- Example for IMAP: {"host": "imap.gmail.com", "port": 993, "tls": true}
  -- Example for Gmail: {"project_id": "...", "client_id": "..."}

  -- Sync state
  last_sync_at TIMESTAMP,
  sync_token VARCHAR(500), -- Delta sync token (Gmail historyId, Graph deltatoken)
  sync_enabled BOOLEAN DEFAULT true,
  sync_frequency_minutes INTEGER DEFAULT 15,

  -- Status
  is_active BOOLEAN DEFAULT true,
  is_primary BOOLEAN DEFAULT false, -- Primary account for user
  status VARCHAR(20) DEFAULT 'connected' CHECK (status IN ('connected', 'auth_failed', 'sync_error', 'disabled')),
  last_error TEXT,
  error_count INTEGER DEFAULT 0,

  -- Metadata
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),

  UNIQUE(user_id, email_address)
);

CREATE INDEX idx_email_accounts_user ON email_accounts(user_id);
CREATE INDEX idx_email_accounts_provider ON email_accounts(provider);
CREATE INDEX idx_email_accounts_status ON email_accounts(status) WHERE is_active = true;

-- Trigger to update updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_email_accounts_updated_at
  BEFORE UPDATE ON email_accounts
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- PART 2: EMAILS (UNIFIED STORAGE)
-- ============================================================================

-- Emails table (provider-agnostic)
CREATE TABLE IF NOT EXISTS emails (
  id SERIAL PRIMARY KEY,
  account_id INTEGER NOT NULL REFERENCES email_accounts(id) ON DELETE CASCADE,

  -- Provider identifiers
  provider_message_id VARCHAR(500) NOT NULL, -- Gmail message ID, Graph ID, IMAP UID
  provider_thread_id VARCHAR(500), -- For threading support
  provider_folder_id VARCHAR(255), -- Current folder/label ID

  -- Email headers
  subject TEXT,
  from_address VARCHAR(500),
  from_name VARCHAR(255),
  to_addresses JSONB DEFAULT '[]'::jsonb, -- [{address: "x@y.com", name: "X"}]
  cc_addresses JSONB DEFAULT '[]'::jsonb,
  bcc_addresses JSONB DEFAULT '[]'::jsonb,
  reply_to VARCHAR(500),

  -- Content
  body_text TEXT,
  body_html TEXT,
  body_preview VARCHAR(500), -- First 500 chars for list view

  -- Timestamps
  received_at TIMESTAMP NOT NULL,
  sent_at TIMESTAMP,
  internal_date TIMESTAMP, -- IMAP INTERNALDATE

  -- Flags (unified representation)
  is_read BOOLEAN DEFAULT false,
  is_flagged BOOLEAN DEFAULT false,
  is_answered BOOLEAN DEFAULT false,
  is_draft BOOLEAN DEFAULT false,
  is_deleted BOOLEAN DEFAULT false,

  -- Provider-specific flags (store raw for reference)
  provider_flags JSONB DEFAULT '{}'::jsonb,
  -- Example: {"gmail_labels": ["INBOX", "IMPORTANT"], "imap_flags": ["\\Seen"]}

  -- Attachments
  has_attachments BOOLEAN DEFAULT false,
  attachment_count INTEGER DEFAULT 0,
  attachments JSONB DEFAULT '[]'::jsonb,
  -- Example: [{"filename": "doc.pdf", "mimeType": "application/pdf", "size": 12345}]

  -- Headers (full raw headers for advanced features)
  raw_headers JSONB DEFAULT '{}'::jsonb,

  -- Folder/Path
  folder_path VARCHAR(500), -- Human-readable path like "INBOX" or "Work/Projects"

  -- Size
  size_bytes INTEGER,

  -- Spam/ML scores
  spam_score DECIMAL(3,2),
  importance_score DECIMAL(3,2),

  -- Metadata
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),

  UNIQUE(account_id, provider_message_id)
);

CREATE INDEX idx_emails_account ON emails(account_id);
CREATE INDEX idx_emails_received ON emails(received_at DESC);
CREATE INDEX idx_emails_thread ON emails(provider_thread_id) WHERE provider_thread_id IS NOT NULL;
CREATE INDEX idx_emails_flags ON emails(is_read, is_flagged, is_deleted);
CREATE INDEX idx_emails_from ON emails(from_address);
CREATE INDEX idx_emails_subject ON emails USING gin(to_tsvector('english', subject));
CREATE INDEX idx_emails_body ON emails USING gin(to_tsvector('english', body_text));

CREATE TRIGGER update_emails_updated_at
  BEFORE UPDATE ON emails
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- PART 3: LABELS & FOLDERS (UNIFIED)
-- ============================================================================

-- Labels/Folders/Categories (unified across providers)
CREATE TABLE IF NOT EXISTS labels (
  id SERIAL PRIMARY KEY,
  account_id INTEGER NOT NULL REFERENCES email_accounts(id) ON DELETE CASCADE,

  -- Provider info
  provider_label_id VARCHAR(255), -- Gmail label ID, folder path, category name
  name VARCHAR(255) NOT NULL, -- Internal name (lowercase, no spaces)
  display_name VARCHAR(255) NOT NULL, -- User-facing name

  -- Type
  label_type VARCHAR(20) NOT NULL CHECK (label_type IN ('system', 'user', 'ai_generated')),
  is_system BOOLEAN DEFAULT false, -- INBOX, SENT, TRASH, etc

  -- Visual
  color VARCHAR(7), -- #RRGGBB hex color
  icon VARCHAR(50), -- Emoji or icon identifier

  -- Hierarchy (for folder-based providers like IMAP/Exchange)
  parent_id INTEGER REFERENCES labels(id) ON DELETE SET NULL,
  path VARCHAR(500), -- Full path like "Work/Projects/Q4"
  depth INTEGER DEFAULT 0, -- Tree depth

  -- Policy & Rules (for AI-generated labels)
  policy JSONB DEFAULT '{}'::jsonb,
  -- Example: {
  --   "icon": "📧",
  --   "rules": {"keywords": ["invoice"], "from_domains": ["stripe.com"]},
  --   "created_by": "ai",
  --   "confidence_threshold": 0.8
  -- }

  -- Stats (cached counts)
  email_count INTEGER DEFAULT 0,
  unread_count INTEGER DEFAULT 0,

  -- Settings
  enabled BOOLEAN DEFAULT true,
  show_in_ui BOOLEAN DEFAULT true,
  show_in_imap BOOLEAN DEFAULT true, -- Gmail-specific: show in IMAP clients

  -- Metadata
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),

  UNIQUE(account_id, provider_label_id),
  UNIQUE(account_id, name)
);

CREATE INDEX idx_labels_account ON labels(account_id);
CREATE INDEX idx_labels_type ON labels(label_type);
CREATE INDEX idx_labels_parent ON labels(parent_id) WHERE parent_id IS NOT NULL;
CREATE INDEX idx_labels_path ON labels USING gin(path gin_trgm_ops);

CREATE TRIGGER update_labels_updated_at
  BEFORE UPDATE ON labels
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- PART 4: EMAIL-LABEL RELATIONS (MANY-TO-MANY)
-- ============================================================================

-- Email <-> Label junction (supports multiple labels per email)
CREATE TABLE IF NOT EXISTS email_labels (
  id SERIAL PRIMARY KEY,
  email_id INTEGER NOT NULL REFERENCES emails(id) ON DELETE CASCADE,
  label_id INTEGER NOT NULL REFERENCES labels(id) ON DELETE CASCADE,

  -- ML/AI confidence
  score DECIMAL(3,2), -- 0.00 to 1.00
  confidence DECIMAL(3,2), -- 0.00 to 1.00
  source VARCHAR(50) CHECK (source IN ('ai', 'ml', 'user', 'rule', 'provider')),

  -- Timestamps
  decided_at TIMESTAMP DEFAULT NOW(),
  removed_at TIMESTAMP, -- Soft delete

  UNIQUE(email_id, label_id)
);

CREATE INDEX idx_email_labels_email ON email_labels(email_id);
CREATE INDEX idx_email_labels_label ON email_labels(label_id);
CREATE INDEX idx_email_labels_source ON email_labels(source);

-- ============================================================================
-- PART 5: CALENDAR INTEGRATION
-- ============================================================================

-- Calendar Accounts
CREATE TABLE IF NOT EXISTS calendar_accounts (
  id SERIAL PRIMARY KEY,
  email_account_id INTEGER REFERENCES email_accounts(id) ON DELETE CASCADE,
  user_id VARCHAR(100) NOT NULL,
  provider VARCHAR(20) NOT NULL CHECK (provider IN ('google', 'exchange')),

  -- Auth (usually shares tokens with email account)
  access_token TEXT,
  refresh_token TEXT,
  token_expires_at TIMESTAMP,

  -- Default calendar
  default_calendar_id VARCHAR(255),

  -- Status
  is_active BOOLEAN DEFAULT true,
  last_sync_at TIMESTAMP,
  sync_enabled BOOLEAN DEFAULT true,

  -- Metadata
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),

  UNIQUE(user_id, provider)
);

CREATE INDEX idx_calendar_accounts_user ON calendar_accounts(user_id);
CREATE INDEX idx_calendar_accounts_email ON calendar_accounts(email_account_id);

CREATE TRIGGER update_calendar_accounts_updated_at
  BEFORE UPDATE ON calendar_accounts
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

-- Calendars
CREATE TABLE IF NOT EXISTS calendars (
  id SERIAL PRIMARY KEY,
  calendar_account_id INTEGER NOT NULL REFERENCES calendar_accounts(id) ON DELETE CASCADE,
  provider_calendar_id VARCHAR(255) NOT NULL,

  -- Calendar info
  name VARCHAR(255) NOT NULL,
  description TEXT,
  timezone VARCHAR(100) DEFAULT 'Europe/Stockholm',
  color VARCHAR(7), -- #RRGGBB

  -- Permissions
  access_role VARCHAR(20) CHECK (access_role IN ('owner', 'writer', 'reader', 'freeBusyReader')),
  can_edit BOOLEAN DEFAULT false,

  -- Flags
  is_primary BOOLEAN DEFAULT false,
  is_selected BOOLEAN DEFAULT true, -- Show in UI

  -- Metadata
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),

  UNIQUE(calendar_account_id, provider_calendar_id)
);

CREATE INDEX idx_calendars_account ON calendars(calendar_account_id);
CREATE INDEX idx_calendars_primary ON calendars(is_primary) WHERE is_primary = true;

CREATE TRIGGER update_calendars_updated_at
  BEFORE UPDATE ON calendars
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

-- Calendar Events
CREATE TABLE IF NOT EXISTS calendar_events (
  id SERIAL PRIMARY KEY,
  calendar_id INTEGER NOT NULL REFERENCES calendars(id) ON DELETE CASCADE,
  provider_event_id VARCHAR(255) NOT NULL,

  -- Core fields
  title VARCHAR(500) NOT NULL,
  description TEXT,
  location VARCHAR(500),

  -- Time
  start_time TIMESTAMP NOT NULL,
  end_time TIMESTAMP NOT NULL,
  is_all_day BOOLEAN DEFAULT false,
  timezone VARCHAR(100) DEFAULT 'Europe/Stockholm',

  -- Organizer
  organizer_email VARCHAR(255),
  organizer_name VARCHAR(255),
  is_organizer BOOLEAN DEFAULT false, -- Is current user the organizer?

  -- Attendees
  attendees JSONB DEFAULT '[]'::jsonb,
  -- [{email: "x@y.com", name: "X", responseStatus: "accepted", optional: false}]

  -- User's response
  response_status VARCHAR(20) CHECK (response_status IN ('accepted', 'declined', 'tentative', 'needsAction')),

  -- Recurrence
  recurrence_rule TEXT, -- RRULE format (RFC 5545)
  is_recurring BOOLEAN DEFAULT false,
  recurring_event_id VARCHAR(255), -- Parent event for recurring instances

  -- Meeting/Conference
  conference_data JSONB,
  -- {type: "googleMeet", joinUrl: "...", conferenceId: "...", dialIn: {...}}

  -- Status
  status VARCHAR(20) DEFAULT 'confirmed' CHECK (status IN ('confirmed', 'tentative', 'cancelled')),

  -- iCal interoperability
  ical_uid VARCHAR(500), -- Unique across providers
  sequence INTEGER DEFAULT 0, -- iCal SEQUENCE for updates

  -- Visibility
  visibility VARCHAR(20) DEFAULT 'default' CHECK (visibility IN ('default', 'public', 'private', 'confidential')),

  -- Reminders
  reminders JSONB DEFAULT '[]'::jsonb,
  -- [{method: "email", minutes: 30}, {method: "popup", minutes: 10}]

  -- Metadata
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  synced_at TIMESTAMP DEFAULT NOW(),

  UNIQUE(calendar_id, provider_event_id)
);

CREATE INDEX idx_calendar_events_calendar ON calendar_events(calendar_id);
CREATE INDEX idx_calendar_events_time ON calendar_events(start_time, end_time);
CREATE INDEX idx_calendar_events_status ON calendar_events(response_status);
CREATE INDEX idx_calendar_events_ical ON calendar_events(ical_uid);
CREATE INDEX idx_calendar_events_organizer ON calendar_events(organizer_email);

CREATE TRIGGER update_calendar_events_updated_at
  BEFORE UPDATE ON calendar_events
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- PART 6: EMAIL-CALENDAR LINKS
-- ============================================================================

-- Link emails to calendar events (meeting invites)
CREATE TABLE IF NOT EXISTS email_calendar_links (
  id SERIAL PRIMARY KEY,
  email_id INTEGER NOT NULL REFERENCES emails(id) ON DELETE CASCADE,
  calendar_event_id INTEGER REFERENCES calendar_events(id) ON DELETE SET NULL,

  -- Link metadata
  link_type VARCHAR(20) CHECK (link_type IN ('invite', 'update', 'cancellation', 'response')),

  -- ICS attachment info
  ics_method VARCHAR(20), -- REQUEST, REPLY, CANCEL, PUBLISH, etc (RFC 5546)
  ics_uid VARCHAR(500), -- iCal UID from attachment
  ics_sequence INTEGER, -- SEQUENCE number

  -- Processing status
  processed BOOLEAN DEFAULT false,
  auto_responded BOOLEAN DEFAULT false,
  response_sent_at TIMESTAMP,

  -- Metadata
  created_at TIMESTAMP DEFAULT NOW(),

  UNIQUE(email_id, calendar_event_id)
);

CREATE INDEX idx_email_calendar_links_email ON email_calendar_links(email_id);
CREATE INDEX idx_email_calendar_links_event ON email_calendar_links(calendar_event_id);
CREATE INDEX idx_email_calendar_links_ics ON email_calendar_links(ics_uid);
CREATE INDEX idx_email_calendar_links_processed ON email_calendar_links(processed) WHERE processed = false;

-- ============================================================================
-- PART 7: EMAIL ACTIONS LOG (AUDIT TRAIL & UNDO)
-- ============================================================================

CREATE TABLE IF NOT EXISTS email_actions (
  id SERIAL PRIMARY KEY,
  email_id INTEGER NOT NULL REFERENCES emails(id) ON DELETE CASCADE,
  account_id INTEGER NOT NULL REFERENCES email_accounts(id) ON DELETE CASCADE,

  -- Action details
  action_type VARCHAR(50) NOT NULL,
  -- archive, snooze, flag, unflag, move, delete, label, send_reply, etc

  -- Execution context
  executed_at TIMESTAMP DEFAULT NOW(),
  executed_by VARCHAR(20) CHECK (executed_by IN ('user', 'ai', 'ml', 'automation', 'rule')),
  confidence DECIMAL(3,2), -- For AI/ML actions

  -- Undo capability
  reversible BOOLEAN DEFAULT true,
  reversed BOOLEAN DEFAULT false,
  reversed_at TIMESTAMP,
  undo_action_id INTEGER REFERENCES email_actions(id), -- Link to undo action

  -- Action-specific metadata
  metadata JSONB DEFAULT '{}'::jsonb,
  -- Example for snooze: {snooze_until: "2025-10-05T09:00:00Z", reason: "follow_up"}
  -- Example for move: {from_folder: "INBOX", to_folder: "Archive"}

  -- Error handling
  success BOOLEAN DEFAULT true,
  error_message TEXT
);

CREATE INDEX idx_email_actions_email ON email_actions(email_id);
CREATE INDEX idx_email_actions_account ON email_actions(account_id);
CREATE INDEX idx_email_actions_type ON email_actions(action_type);
CREATE INDEX idx_email_actions_executed ON email_actions(executed_at DESC);
CREATE INDEX idx_email_actions_reversible ON email_actions(reversible, reversed) WHERE reversible = true AND reversed = false;

-- ============================================================================
-- PART 8: SNOOZE/REMINDERS
-- ============================================================================

CREATE TABLE IF NOT EXISTS email_snoozes (
  id SERIAL PRIMARY KEY,
  email_id INTEGER NOT NULL REFERENCES emails(id) ON DELETE CASCADE,
  account_id INTEGER NOT NULL REFERENCES email_accounts(id) ON DELETE CASCADE,

  -- Snooze config
  snooze_until TIMESTAMP NOT NULL,
  reason VARCHAR(100),
  -- waiting_for_response, follow_up, review_later, custom

  -- Original folder (for restoration)
  original_folder_id VARCHAR(255),
  original_folder_path VARCHAR(500),

  -- Reminder status
  reminded BOOLEAN DEFAULT false,
  reminder_sent_at TIMESTAMP,

  -- Metadata
  created_at TIMESTAMP DEFAULT NOW(),

  UNIQUE(email_id) -- One active snooze per email
);

CREATE INDEX idx_email_snoozes_email ON email_snoozes(email_id);
CREATE INDEX idx_email_snoozes_account ON email_snoozes(account_id);
CREATE INDEX idx_email_snoozes_until ON email_snoozes(snooze_until) WHERE reminded = false;

-- ============================================================================
-- PART 9: USER RULES
-- ============================================================================

CREATE TABLE IF NOT EXISTS user_rules (
  id SERIAL PRIMARY KEY,
  user_id VARCHAR(100) NOT NULL,
  account_id INTEGER REFERENCES email_accounts(id) ON DELETE CASCADE, -- NULL = applies to all accounts

  -- Rule metadata
  name VARCHAR(255) NOT NULL,
  description TEXT,
  rule_type VARCHAR(20) CHECK (rule_type IN ('R0', 'R1', 'R2')),
  -- R0: Hard blockers (spam, domains)
  -- R1: Heuristic rules (metadata-based)
  -- R2: User-defined rules

  -- Condition (JSON query)
  condition JSONB NOT NULL,
  -- Example: {
  --   "from_contains": "noreply",
  --   "subject_regex": ".*invoice.*",
  --   "has_attachments": true,
  --   "from_domain": "stripe.com"
  -- }

  -- Action (JSON definition)
  action JSONB NOT NULL,
  -- Example: {
  --   "type": "move",
  --   "target": "Archive",
  --   "mark_as_read": true,
  --   "add_label": "receipts"
  -- }

  -- ML integration
  confidence_threshold DECIMAL(3,2), -- Minimum confidence to apply rule
  ml_category VARCHAR(100), -- Link to ML category

  -- Status
  enabled BOOLEAN DEFAULT true,
  priority INTEGER DEFAULT 100, -- Lower = higher priority

  -- Stats
  match_count INTEGER DEFAULT 0,
  execution_count INTEGER DEFAULT 0,
  last_matched_at TIMESTAMP,

  -- Metadata
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_user_rules_user ON user_rules(user_id);
CREATE INDEX idx_user_rules_account ON user_rules(account_id);
CREATE INDEX idx_user_rules_type ON user_rules(rule_type);
CREATE INDEX idx_user_rules_enabled ON user_rules(enabled, priority) WHERE enabled = true;

CREATE TRIGGER update_user_rules_updated_at
  BEFORE UPDATE ON user_rules
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- PART 10: AUTOMATION STATS
-- ============================================================================

CREATE TABLE IF NOT EXISTS automation_stats (
  id SERIAL PRIMARY KEY,
  user_id VARCHAR(100) NOT NULL,
  account_id INTEGER REFERENCES email_accounts(id) ON DELETE CASCADE,
  date DATE NOT NULL,

  -- Counts
  actions_automated INTEGER DEFAULT 0,
  emails_processed INTEGER DEFAULT 0,
  rules_triggered INTEGER DEFAULT 0,

  -- Time savings (estimated seconds)
  time_saved_seconds INTEGER DEFAULT 0,

  -- Achievements
  inbox_zero_achieved BOOLEAN DEFAULT false,
  inbox_zero_duration_seconds INTEGER, -- How long it took

  -- Breakdown by action type
  actions_by_type JSONB DEFAULT '{}'::jsonb,
  -- {"archive": 45, "label": 23, "snooze": 12, ...}

  -- Metadata
  created_at TIMESTAMP DEFAULT NOW(),

  UNIQUE(user_id, account_id, date)
);

CREATE INDEX idx_automation_stats_user ON automation_stats(user_id, date DESC);
CREATE INDEX idx_automation_stats_account ON automation_stats(account_id, date DESC);
CREATE INDEX idx_automation_stats_inbox_zero ON automation_stats(inbox_zero_achieved) WHERE inbox_zero_achieved = true;

-- ============================================================================
-- PART 11: UNSUBSCRIBE LOG
-- ============================================================================

CREATE TABLE IF NOT EXISTS unsubscribe_log (
  id SERIAL PRIMARY KEY,
  email_id INTEGER REFERENCES emails(id) ON DELETE SET NULL,
  account_id INTEGER NOT NULL REFERENCES email_accounts(id) ON DELETE CASCADE,

  -- Sender info
  sender_email VARCHAR(255),
  sender_domain VARCHAR(255),

  -- Unsubscribe method
  unsubscribe_method VARCHAR(50) CHECK (unsubscribe_method IN ('link', 'list_unsubscribe_header', 'mailto', 'manual', 'browser_automation')),
  unsubscribe_url TEXT,

  -- Execution
  unsubscribed_at TIMESTAMP DEFAULT NOW(),
  success BOOLEAN,
  error_message TEXT,

  -- Follow-up
  blocked_future_emails BOOLEAN DEFAULT true, -- Add sender to blocklist

  -- Metadata
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_unsubscribe_log_email ON unsubscribe_log(email_id);
CREATE INDEX idx_unsubscribe_log_account ON unsubscribe_log(account_id);
CREATE INDEX idx_unsubscribe_log_domain ON unsubscribe_log(sender_domain);
CREATE INDEX idx_unsubscribe_log_success ON unsubscribe_log(success, unsubscribed_at DESC);

-- ============================================================================
-- PART 12: PROVIDER SYNC HISTORY (DEBUGGING)
-- ============================================================================

CREATE TABLE IF NOT EXISTS sync_history (
  id SERIAL PRIMARY KEY,
  account_id INTEGER NOT NULL REFERENCES email_accounts(id) ON DELETE CASCADE,

  -- Sync details
  sync_type VARCHAR(20) CHECK (sync_type IN ('full', 'delta', 'webhook')),
  started_at TIMESTAMP NOT NULL,
  completed_at TIMESTAMP,
  duration_seconds INTEGER,

  -- Results
  emails_added INTEGER DEFAULT 0,
  emails_updated INTEGER DEFAULT 0,
  emails_deleted INTEGER DEFAULT 0,
  labels_synced INTEGER DEFAULT 0,

  -- Sync token progression
  previous_sync_token VARCHAR(500),
  new_sync_token VARCHAR(500),

  -- Status
  success BOOLEAN DEFAULT true,
  error_message TEXT,

  -- Metadata
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_sync_history_account ON sync_history(account_id, started_at DESC);
CREATE INDEX idx_sync_history_success ON sync_history(success) WHERE success = false;

-- ============================================================================
-- HELPER VIEWS
-- ============================================================================

-- View: Unread emails per account
CREATE OR REPLACE VIEW vw_unread_counts AS
SELECT
  ea.id AS account_id,
  ea.email_address,
  ea.provider,
  COUNT(*) AS unread_count
FROM email_accounts ea
JOIN emails e ON ea.id = e.account_id
WHERE e.is_read = false AND e.is_deleted = false
GROUP BY ea.id, ea.email_address, ea.provider;

-- View: Today's inbox zero stats
CREATE OR REPLACE VIEW vw_inbox_zero_today AS
SELECT
  user_id,
  COUNT(DISTINCT account_id) AS accounts_inbox_zero,
  SUM(time_saved_seconds) AS total_time_saved_seconds,
  SUM(actions_automated) AS total_actions_automated
FROM automation_stats
WHERE date = CURRENT_DATE AND inbox_zero_achieved = true
GROUP BY user_id;

-- View: Active calendar events this week
CREATE OR REPLACE VIEW vw_calendar_week AS
SELECT
  ca.user_id,
  c.name AS calendar_name,
  ce.title,
  ce.start_time,
  ce.end_time,
  ce.location,
  ce.response_status,
  ce.conference_data->>'joinUrl' AS meeting_link
FROM calendar_events ce
JOIN calendars c ON ce.calendar_id = c.id
JOIN calendar_accounts ca ON c.calendar_account_id = ca.id
WHERE ce.start_time >= date_trunc('week', CURRENT_DATE)
  AND ce.start_time < date_trunc('week', CURRENT_DATE) + INTERVAL '7 days'
  AND ce.status != 'cancelled'
ORDER BY ce.start_time;

-- ============================================================================
-- GRANT PERMISSIONS (adjust as needed)
-- ============================================================================

-- Example: Grant to application user
-- GRANT ALL ON ALL TABLES IN SCHEMA public TO email_app_user;
-- GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO email_app_user;

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE email_accounts IS 'Multi-provider email accounts with OAuth support';
COMMENT ON TABLE emails IS 'Unified email storage across all providers';
COMMENT ON TABLE labels IS 'Gmail labels, IMAP folders, Exchange categories - unified';
COMMENT ON TABLE email_labels IS 'Many-to-many relationship: one email can have multiple labels';
COMMENT ON TABLE calendar_accounts IS 'Google Calendar and Exchange calendar authentication';
COMMENT ON TABLE calendar_events IS 'Unified calendar events from all providers';
COMMENT ON TABLE email_calendar_links IS 'Links emails to calendar events (meeting invites)';
COMMENT ON TABLE email_actions IS 'Audit trail of all email actions for undo/analytics';
COMMENT ON TABLE email_snoozes IS 'Snoozed emails with reminder scheduling';
COMMENT ON TABLE user_rules IS 'User-defined automation rules (R0/R1/R2)';
COMMENT ON TABLE automation_stats IS 'Daily stats for inbox zero tracking and gamification';
COMMENT ON TABLE unsubscribe_log IS 'Track unsubscribe actions and blocklist';
COMMENT ON TABLE sync_history IS 'Debug log of sync operations per account';
