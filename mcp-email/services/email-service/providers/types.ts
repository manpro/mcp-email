/**
 * Multi-Provider Email & Calendar Abstractions
 *
 * Unified interfaces for IMAP, Gmail API, and Microsoft Graph API
 */

// ============================================================================
// Core Types
// ============================================================================

export type EmailProvider = 'imap' | 'gmail' | 'exchange'
export type CalendarProvider = 'google' | 'exchange'
export type AuthType = 'oauth' | 'password' | 'app_password'

export interface EmailAccount {
  id: number
  userId: string
  provider: EmailProvider
  emailAddress: string
  displayName?: string
  authType: AuthType
  accessToken?: string
  refreshToken?: string
  tokenExpiresAt?: Date
  syncToken?: string  // Gmail historyId or Graph deltaToken
  lastSyncAt?: Date
  enabled: boolean
  capabilities: ProviderCapabilities
  metadata?: Record<string, any>
}

export interface ProviderCapabilities {
  supportsThreading: boolean
  supportsLabels: boolean
  supportsFolders: boolean
  supportsFlags: boolean
  supportsSearch: boolean
  supportsBatch: boolean
  supportsWebhooks: boolean
  supportsDeltaSync: boolean
  supportsCalendar: boolean
  maxBatchSize: number
  rateLimitPerSecond: number
}

// ============================================================================
// Email Types
// ============================================================================

export interface Email {
  id: number
  accountId: number
  providerMessageId: string
  providerThreadId?: string
  subject: string
  fromAddress: string
  fromName?: string
  toAddresses: string[]
  ccAddresses?: string[]
  bccAddresses?: string[]
  bodyText?: string
  bodyHtml?: string
  receivedAt: Date
  isRead: boolean
  isFlagged: boolean
  isAnswered: boolean
  isDraft: boolean
  hasAttachments: boolean
  attachments?: EmailAttachment[]
  providerFlags?: Record<string, any>
  headers?: Record<string, string>
  metadata?: Record<string, any>
}

export interface EmailAttachment {
  id: string
  filename: string
  mimeType: string
  size: number
  contentId?: string
  isInline: boolean
  url?: string
}

export interface EmailLabel {
  id: number
  accountId: number
  providerLabelId?: string
  name: string
  displayName: string
  labelType: 'system' | 'user' | 'ai_generated'
  color?: string
  icon?: string
  parentId?: number
  policy?: Record<string, any>
}

export interface EmailFlag {
  seen?: boolean
  flagged?: boolean
  answered?: boolean
  deleted?: boolean
  draft?: boolean
  recent?: boolean
}

// ============================================================================
// Fetch Options
// ============================================================================

export interface FetchOptions {
  folderId?: string
  labelId?: string
  since?: Date
  limit?: number
  offset?: number
  includeBody?: boolean
  includeHeaders?: boolean
  threadId?: string
  query?: string
  deltaSyncToken?: string
}

export interface DeltaResponse {
  emails: Email[]
  syncToken: string
  hasMore: boolean
}

export interface BatchUpdate {
  emailId: string
  operation: 'flag' | 'unflag' | 'read' | 'unread' | 'archive' | 'delete' | 'addLabel' | 'removeLabel' | 'move'
  value?: any
}

export interface BatchResult {
  success: boolean
  results: Array<{
    emailId: string
    success: boolean
    error?: string
  }>
}

// ============================================================================
// OAuth Types
// ============================================================================

export interface OAuthCredentials {
  clientId: string
  clientSecret: string
  redirectUri: string
  scopes: string[]
}

export interface AuthToken {
  accessToken: string
  refreshToken?: string
  expiresAt: Date
  tokenType: string
  scope?: string
}

export interface ProviderCredentials {
  type: AuthType
  // OAuth
  authCode?: string
  accessToken?: string
  refreshToken?: string
  // Password-based
  username?: string
  password?: string
  host?: string
  port?: number
  tls?: boolean
}

// ============================================================================
// Calendar Types
// ============================================================================

export interface CalendarAccount {
  id: number
  emailAccountId: number
  provider: CalendarProvider
  accessToken: string
  refreshToken?: string
  tokenExpiresAt?: Date
  syncToken?: string
  enabled: boolean
}

export interface Calendar {
  id: number
  accountId: number
  providerCalendarId: string
  name: string
  description?: string
  color?: string
  isPrimary: boolean
  isWritable: boolean
  timezone: string
}

export interface CalendarEvent {
  id: number
  calendarId: number
  providerEventId: string
  title: string
  description?: string
  location?: string
  startTime: Date
  endTime: Date
  isAllDay: boolean
  attendees?: EventAttendee[]
  organizer?: string
  responseStatus?: 'accepted' | 'declined' | 'tentative' | 'needsAction'
  conferenceData?: ConferenceData
  recurrence?: string[]
  icalUid?: string
  metadata?: Record<string, any>
}

export interface EventAttendee {
  email: string
  displayName?: string
  responseStatus?: 'accepted' | 'declined' | 'tentative' | 'needsAction'
  optional?: boolean
}

export interface ConferenceData {
  type: 'hangoutsMeet' | 'teams' | 'zoom' | 'other'
  url?: string
  conferenceId?: string
  dialIn?: string
  metadata?: Record<string, any>
}

export interface EventDefinition {
  title: string
  description?: string
  location?: string
  startTime: Date
  endTime: Date
  isAllDay?: boolean
  attendees?: string[]
  createMeeting?: boolean
  recurrence?: string[]
  reminders?: Array<{ method: 'email' | 'popup', minutes: number }>
}

export interface MeetingTimeSuggestion {
  startTime: Date
  endTime: Date
  confidence: number
  attendeeAvailability: Array<{
    email: string
    available: boolean
  }>
}

export interface EmailCalendarLink {
  id: number
  emailId: number
  calendarEventId?: number
  icsMethod?: 'REQUEST' | 'REPLY' | 'CANCEL'
  icsUid?: string
  processed: boolean
  autoResponded: boolean
  responseStatus?: 'accepted' | 'declined' | 'tentative'
}

// ============================================================================
// Provider Interfaces
// ============================================================================

export interface IEmailProvider {
  /**
   * Initialize the provider with account credentials
   */
  initialize(account: EmailAccount): Promise<void>

  /**
   * Authenticate and obtain access tokens
   */
  authenticate(credentials: ProviderCredentials): Promise<AuthToken>

  /**
   * Refresh expired access token
   */
  refreshToken(refreshToken: string): Promise<AuthToken>

  /**
   * Get provider capabilities
   */
  getCapabilities(): ProviderCapabilities

  /**
   * Fetch emails with optional filtering
   */
  fetchEmails(options: FetchOptions): Promise<Email[]>

  /**
   * Get delta changes since last sync
   */
  getDelta(syncToken?: string): Promise<DeltaResponse>

  /**
   * Get a single email by ID
   */
  getEmail(emailId: string): Promise<Email>

  /**
   * Set email flags (read, flagged, etc)
   */
  setFlag(emailId: string, flag: EmailFlag): Promise<void>

  /**
   * Add label/folder to email
   */
  addLabel(emailId: string, labelId: string): Promise<void>

  /**
   * Remove label/folder from email
   */
  removeLabel(emailId: string, labelId: string): Promise<void>

  /**
   * Move email to different folder
   */
  moveToFolder(emailId: string, folderId: string): Promise<void>

  /**
   * Archive email (Gmail: remove inbox label, IMAP: move to archive)
   */
  archive(emailId: string): Promise<void>

  /**
   * Delete email (move to trash)
   */
  delete(emailId: string): Promise<void>

  /**
   * Permanently delete email
   */
  permanentDelete(emailId: string): Promise<void>

  /**
   * Batch update multiple emails
   */
  batchUpdate(updates: BatchUpdate[]): Promise<BatchResult>

  /**
   * Search emails
   */
  search(query: string, options?: FetchOptions): Promise<Email[]>

  /**
   * Get all labels/folders
   */
  getLabels(): Promise<EmailLabel[]>

  /**
   * Create new label/folder
   */
  createLabel(name: string, parent?: string): Promise<EmailLabel>

  /**
   * Setup webhook for push notifications (if supported)
   */
  setupWebhook?(webhookUrl: string): Promise<{ webhookId: string }>

  /**
   * Stop webhook
   */
  stopWebhook?(webhookId: string): Promise<void>

  /**
   * Verify webhook signature
   */
  verifyWebhook?(payload: any, signature: string): boolean

  /**
   * Send email
   */
  sendEmail(email: {
    to: string[]
    cc?: string[]
    bcc?: string[]
    subject: string
    bodyText?: string
    bodyHtml?: string
    attachments?: Array<{ filename: string, content: Buffer, mimeType: string }>
    inReplyTo?: string
    threadId?: string
  }): Promise<{ messageId: string }>

  /**
   * Send reply to email
   */
  reply(emailId: string, bodyText: string, bodyHtml?: string): Promise<{ messageId: string }>

  /**
   * Forward email
   */
  forward(emailId: string, to: string[], bodyText?: string): Promise<{ messageId: string }>

  /**
   * Create draft
   */
  createDraft(email: {
    to: string[]
    subject: string
    bodyText?: string
    bodyHtml?: string
  }): Promise<{ draftId: string }>

  /**
   * Update draft
   */
  updateDraft(draftId: string, email: any): Promise<void>

  /**
   * Send draft
   */
  sendDraft(draftId: string): Promise<{ messageId: string }>

  /**
   * Clean up resources
   */
  disconnect(): Promise<void>
}

export interface ICalendarProvider {
  /**
   * Initialize the provider with account credentials
   */
  initialize(account: CalendarAccount): Promise<void>

  /**
   * Authenticate and obtain access tokens
   */
  authenticate(credentials: ProviderCredentials): Promise<AuthToken>

  /**
   * Refresh expired access token
   */
  refreshToken(refreshToken: string): Promise<AuthToken>

  /**
   * Get all calendars
   */
  getCalendars(): Promise<Calendar[]>

  /**
   * Get events from a calendar
   */
  getEvents(calendarId: string, startTime: Date, endTime: Date): Promise<CalendarEvent[]>

  /**
   * Get a single event
   */
  getEvent(calendarId: string, eventId: string): Promise<CalendarEvent>

  /**
   * Create calendar event
   */
  createEvent(calendarId: string, event: EventDefinition): Promise<CalendarEvent>

  /**
   * Update calendar event
   */
  updateEvent(calendarId: string, eventId: string, updates: Partial<EventDefinition>): Promise<CalendarEvent>

  /**
   * Delete calendar event
   */
  deleteEvent(calendarId: string, eventId: string): Promise<void>

  /**
   * Respond to meeting invite
   */
  respondToInvite(
    calendarId: string,
    eventId: string,
    response: 'accepted' | 'declined' | 'tentative',
    comment?: string
  ): Promise<void>

  /**
   * Find available meeting times
   */
  findMeetingTimes(
    attendees: string[],
    duration: number,
    startDate: Date,
    endDate: Date
  ): Promise<MeetingTimeSuggestion[]>

  /**
   * Parse iCalendar (.ics) content
   */
  parseICS(icsContent: string): Promise<{
    method: 'REQUEST' | 'REPLY' | 'CANCEL'
    event: CalendarEvent
    organizer: string
    attendees: EventAttendee[]
  }>

  /**
   * Generate iCalendar REPLY
   */
  generateICSReply(
    event: CalendarEvent,
    response: 'accepted' | 'declined' | 'tentative',
    comment?: string
  ): Promise<string>

  /**
   * Setup webhook for calendar changes
   */
  setupWebhook?(webhookUrl: string, calendarId: string): Promise<{ webhookId: string }>

  /**
   * Stop webhook
   */
  stopWebhook?(webhookId: string): Promise<void>

  /**
   * Clean up resources
   */
  disconnect(): Promise<void>
}

// ============================================================================
// Service Types
// ============================================================================

export interface IProviderFactory {
  createEmailProvider(provider: EmailProvider, account: EmailAccount): IEmailProvider
  createCalendarProvider(provider: CalendarProvider, account: CalendarAccount): ICalendarProvider
}

export interface ISyncService {
  syncAccount(accountId: number): Promise<{ emailsAdded: number, emailsUpdated: number }>
  syncAllAccounts(userId: string): Promise<void>
  handleWebhook(provider: EmailProvider, payload: any): Promise<void>
}

export interface IFlagSyncService {
  syncFlags(accountId: number, emailId: number): Promise<void>
  handleFlagChange(accountId: number, emailId: number, flags: EmailFlag): Promise<void>
}
