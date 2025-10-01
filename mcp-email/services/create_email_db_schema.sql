-- Email Management System - PostgreSQL Schema
-- Clean 6-component architecture with Multi-Provider Support

-- Create database (run this first)
-- CREATE DATABASE email_management;

-- ============================================================================
-- MULTI-PROVIDER ACCOUNT MANAGEMENT
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
  credentials_encrypted TEXT,

  -- OAuth tokens (if applicable)
  access_token TEXT,
  refresh_token TEXT,
  token_expires_at TIMESTAMP,
  token_scopes TEXT[],

  -- Provider-specific config
  provider_config JSONB DEFAULT '{}'::jsonb,

  -- Sync state
  last_sync_at TIMESTAMP,
  sync_token VARCHAR(500),
  sync_enabled BOOLEAN DEFAULT true,
  sync_frequency_minutes INTEGER DEFAULT 15,

  -- Status
  is_active BOOLEAN DEFAULT true,
  is_primary BOOLEAN DEFAULT false,
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

-- Update trigger
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
-- CORE EMAIL STORAGE
-- ============================================================================

-- Core email storage (now with account_id reference)
CREATE TABLE emails (
    id BIGSERIAL PRIMARY KEY,
    uid VARCHAR(255) NOT NULL,
    account_id INTEGER REFERENCES email_accounts(id) ON DELETE CASCADE,
    thread_id VARCHAR(255),
    provider_message_id VARCHAR(500),
    provider_thread_id VARCHAR(500),
    from_address VARCHAR(500) NOT NULL,
    to_address TEXT,
    cc_address TEXT,
    bcc_address TEXT,
    subject TEXT,
    text_content TEXT,
    html_content TEXT,
    received_at TIMESTAMP WITH TIME ZONE NOT NULL,
    flags JSONB DEFAULT '{}',
    list_unsubscribe VARCHAR(1000),
    message_hash VARCHAR(64) UNIQUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- File attachments
CREATE TABLE attachments (
    id BIGSERIAL PRIMARY KEY,
    email_id BIGINT REFERENCES emails(id) ON DELETE CASCADE,
    filename VARCHAR(500) NOT NULL,
    file_path VARCHAR(1000) NOT NULL,
    mime_type VARCHAR(200),
    file_size BIGINT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Label definitions (categories)
CREATE TABLE labels (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    display_name VARCHAR(200) NOT NULL,
    color VARCHAR(7) DEFAULT '#3B82F6',
    policy JSONB DEFAULT '{}',
    thresholds JSONB DEFAULT '{"high": 0.85, "low": 0.3}',
    enabled BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Email-label relationships (final classifications)
CREATE TABLE email_labels (
    id BIGSERIAL PRIMARY KEY,
    email_id BIGINT REFERENCES emails(id) ON DELETE CASCADE,
    label_id INTEGER REFERENCES labels(id) ON DELETE CASCADE,
    score DECIMAL(5,4) NOT NULL,
    source VARCHAR(50) NOT NULL, -- 'rule', 'ml', 'gpt', 'user'
    model_version VARCHAR(100),
    confidence DECIMAL(5,4),
    decided_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(email_id, label_id)
);

-- Classification rules
CREATE TABLE rules (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    tier INTEGER NOT NULL, -- 0=blocker, 1=heuristic, 2=user
    expression JSONB NOT NULL, -- rule definition
    action JSONB NOT NULL, -- what to do
    label_id INTEGER REFERENCES labels(id),
    priority INTEGER DEFAULT 0,
    enabled BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ML model predictions (before final decision)
CREATE TABLE model_predictions (
    id BIGSERIAL PRIMARY KEY,
    email_id BIGINT REFERENCES emails(id) ON DELETE CASCADE,
    label_id INTEGER REFERENCES labels(id) ON DELETE CASCADE,
    score DECIMAL(5,4) NOT NULL,
    confidence DECIMAL(5,4),
    model_version VARCHAR(100) NOT NULL,
    features_json JSONB,
    reasoning TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- User feedback for learning
CREATE TABLE feedback (
    id BIGSERIAL PRIMARY KEY,
    email_id BIGINT REFERENCES emails(id) ON DELETE CASCADE,
    correct_label_id INTEGER REFERENCES labels(id),
    incorrect_label_id INTEGER REFERENCES labels(id),
    reason VARCHAR(500),
    user_id VARCHAR(100),
    feedback_type VARCHAR(50), -- 'correction', 'validation', 'priority'
    weight DECIMAL(3,2) DEFAULT 1.0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Background jobs queue
CREATE TABLE jobs (
    id BIGSERIAL PRIMARY KEY,
    type VARCHAR(100) NOT NULL, -- 'CLASSIFY', 'SYNC', 'ACTION', 'RETRAIN'
    status VARCHAR(50) DEFAULT 'PENDING', -- 'PENDING', 'RUNNING', 'COMPLETED', 'FAILED'
    payload JSONB,
    result JSONB,
    error_message TEXT,
    attempts INTEGER DEFAULT 0,
    max_attempts INTEGER DEFAULT 3,
    scheduled_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    unique_key VARCHAR(200) UNIQUE, -- for idempotency
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Action execution log
CREATE TABLE actions (
    id BIGSERIAL PRIMARY KEY,
    job_id BIGINT REFERENCES jobs(id),
    email_id BIGINT REFERENCES emails(id),
    action_type VARCHAR(100) NOT NULL, -- 'MOVE', 'DELETE', 'FLAG', 'UNSUB', 'DRAFT'
    target VARCHAR(500), -- folder name, flag value, etc.
    result VARCHAR(50), -- 'SUCCESS', 'FAILED', 'SKIPPED'
    error_message TEXT,
    executed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ML model versions tracking
CREATE TABLE model_versions (
    id SERIAL PRIMARY KEY,
    version VARCHAR(100) UNIQUE NOT NULL,
    model_type VARCHAR(100) NOT NULL, -- 'gpt-oss', 'local-ml', 'ensemble'
    metadata JSONB,
    performance_metrics JSONB,
    is_active BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Unsubscribe targets for bulk operations
CREATE TABLE unsubscribe_targets (
    id BIGSERIAL PRIMARY KEY,
    email_id BIGINT REFERENCES emails(id) ON DELETE CASCADE,
    unsubscribe_url VARCHAR(1000),
    sender_domain VARCHAR(255),
    list_id VARCHAR(500),
    status VARCHAR(50) DEFAULT 'PENDING', -- 'PENDING', 'PROCESSING', 'COMPLETED', 'FAILED'
    processed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================================
-- CALENDAR & AUTO-RSVP INTEGRATION
-- ============================================================================

-- Calendars
CREATE TABLE IF NOT EXISTS calendars (
  id SERIAL PRIMARY KEY,
  account_id INTEGER NOT NULL REFERENCES email_accounts(id) ON DELETE CASCADE,
  provider_calendar_id VARCHAR(500) NOT NULL,
  name VARCHAR(255),
  color VARCHAR(7),
  is_primary BOOLEAN DEFAULT false,
  timezone VARCHAR(100),
  created_at TIMESTAMP DEFAULT NOW(),
  UNIQUE(account_id, provider_calendar_id)
);

-- Calendar events
CREATE TABLE IF NOT EXISTS calendar_events (
  id SERIAL PRIMARY KEY,
  calendar_id INTEGER NOT NULL REFERENCES calendars(id) ON DELETE CASCADE,
  provider_event_id VARCHAR(500) NOT NULL,
  ical_uid VARCHAR(500),

  -- Event details
  summary TEXT,
  description TEXT,
  location TEXT,
  start_time TIMESTAMP NOT NULL,
  end_time TIMESTAMP NOT NULL,
  is_all_day BOOLEAN DEFAULT false,
  timezone VARCHAR(100),

  -- Meeting details
  organizer_email VARCHAR(500),
  organizer_name VARCHAR(255),

  -- Response status
  response_status VARCHAR(20) CHECK (response_status IN ('accepted', 'declined', 'tentative', 'needsAction')),
  response_comment TEXT,

  -- Auto-RSVP tracking
  auto_rsvp_applied BOOLEAN DEFAULT false,
  auto_rsvp_rule_id INTEGER,
  auto_rsvp_confidence DECIMAL(3,2),

  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  UNIQUE(calendar_id, provider_event_id)
);

CREATE INDEX idx_calendar_events_time ON calendar_events(start_time, end_time);
CREATE INDEX idx_calendar_events_response ON calendar_events(response_status);

-- Email-Calendar link (for meeting invites)
CREATE TABLE IF NOT EXISTS email_calendar_links (
  id SERIAL PRIMARY KEY,
  email_id BIGINT NOT NULL REFERENCES emails(id) ON DELETE CASCADE,
  calendar_event_id INTEGER REFERENCES calendar_events(id) ON DELETE SET NULL,
  ics_content TEXT,
  is_invite BOOLEAN DEFAULT true,
  processed BOOLEAN DEFAULT false,
  created_at TIMESTAMP DEFAULT NOW(),
  UNIQUE(email_id)
);

-- Auto-RSVP Rules
CREATE TABLE IF NOT EXISTS auto_rsvp_rules (
  id SERIAL PRIMARY KEY,
  user_id VARCHAR(100) NOT NULL,
  name VARCHAR(255) NOT NULL,
  rule_type VARCHAR(10) NOT NULL CHECK (rule_type IN ('R0', 'R1', 'R2')),
  priority INTEGER DEFAULT 50,
  enabled BOOLEAN DEFAULT true,

  -- Matching conditions
  condition JSONB NOT NULL,
  -- Example: {"organizerPattern": "@company\\.com$", "timeOfDay": {"start": 9, "end": 17}}

  -- Action
  action JSONB NOT NULL,
  -- Example: {"response": "accepted", "addToCalendar": true, "archiveEmail": true}

  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_auto_rsvp_rules_user ON auto_rsvp_rules(user_id, enabled);
CREATE INDEX idx_auto_rsvp_rules_priority ON auto_rsvp_rules(priority DESC);

-- Automation stats
CREATE TABLE IF NOT EXISTS automation_stats (
  id SERIAL PRIMARY KEY,
  user_id VARCHAR(100) NOT NULL,
  stat_date DATE NOT NULL,

  -- Action counts
  auto_rsvp_count INTEGER DEFAULT 0,
  email_archived_count INTEGER DEFAULT 0,
  flags_synced_count INTEGER DEFAULT 0,

  -- Time saved (estimated minutes)
  time_saved_minutes INTEGER DEFAULT 0,

  -- Inbox zero tracking
  inbox_zero_achieved BOOLEAN DEFAULT false,

  created_at TIMESTAMP DEFAULT NOW(),
  UNIQUE(user_id, stat_date)
);

CREATE INDEX idx_automation_stats_user_date ON automation_stats(user_id, stat_date DESC);

-- Performance indexes
CREATE INDEX idx_emails_received_at ON emails(received_at DESC);
CREATE INDEX idx_emails_from_domain ON emails((split_part(from_address, '@', 2)));
CREATE INDEX idx_emails_account_uid ON emails(account_id, uid);
CREATE INDEX idx_emails_hash ON emails(message_hash);
CREATE INDEX idx_email_labels_score ON email_labels(label_id, score DESC);
CREATE INDEX idx_email_labels_decided ON email_labels(decided_at DESC);
CREATE INDEX idx_jobs_status_type ON jobs(status, type, scheduled_at);
CREATE INDEX idx_jobs_unique_key ON jobs(unique_key) WHERE unique_key IS NOT NULL;
CREATE INDEX idx_model_predictions_email ON model_predictions(email_id, created_at DESC);
CREATE INDEX idx_feedback_created ON feedback(created_at DESC);
CREATE INDEX idx_actions_executed ON actions(executed_at DESC);

-- Insert default labels
INSERT INTO labels (name, display_name, color, thresholds) VALUES
('spam', 'Spam', '#EF4444', '{"high": 0.9, "low": 0.4}'),
('newsletter', 'Nyhetsbrev', '#8B5CF6', '{"high": 0.85, "low": 0.3}'),
('important', 'Viktiga', '#F59E0B', '{"high": 0.8, "low": 0.5}'),
('personal', 'Personliga', '#10B981', '{"high": 0.75, "low": 0.4}'),
('work', 'Arbete', '#3B82F6', '{"high": 0.8, "low": 0.4}'),
('promotions', 'Erbjudanden', '#EC4899', '{"high": 0.85, "low": 0.3}');

-- Insert initial model version
INSERT INTO model_versions (version, model_type, metadata, is_active) VALUES
('gpt-oss-20b-v1', 'gpt-oss', '{"endpoint": "http://172.16.16.148:8085", "model": "gpt-oss:20b"}', true);

-- Create trigger for updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_emails_updated_at BEFORE UPDATE ON emails
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();