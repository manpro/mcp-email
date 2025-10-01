/**
 * Auto-RSVP Service
 *
 * Automatically responds to calendar invites based on:
 * - Calendar availability (conflict detection)
 * - User preferences and rules
 * - AI-based decision making
 * - Priority and importance scoring
 */

import { Pool } from 'pg'
import { GoogleCalendarProvider } from '../providers/google-calendar-provider'
import { GmailProvider } from '../providers/gmail-provider'
import { CalendarInviteParser } from './calendar-invite-parser'
import { OAuthCredentials } from '../providers/types'

interface AutoRSVPRule {
  id: number
  userId: string
  ruleType: 'R0' | 'R1' | 'R2'
  condition: {
    organizerPattern?: string
    subjectPattern?: string
    timeOfDay?: { start: string, end: string }
    dayOfWeek?: number[]
    duration?: { min: number, max: number }
    attendeeCount?: { min: number, max: number }
  }
  action: {
    response: 'accept' | 'decline' | 'tentative' | 'ask'
    autoArchive?: boolean
    addToCalendar?: boolean
    sendComment?: string
  }
  priority: number
  enabled: boolean
}

interface RSVPDecision {
  response: 'accepted' | 'declined' | 'tentative'
  confidence: number
  reason: string
  addToCalendar: boolean
  sendComment?: string
  archiveEmail: boolean
}

export class AutoRSVPService {
  private postgres: Pool
  private calendarParser: CalendarInviteParser
  private googleOAuthConfig: OAuthCredentials

  constructor(
    postgres: Pool,
    calendarParser: CalendarInviteParser,
    googleOAuthConfig: OAuthCredentials
  ) {
    this.postgres = postgres
    this.calendarParser = calendarParser
    this.googleOAuthConfig = googleOAuthConfig
  }

  /**
   * Process pending calendar invites and auto-RSVP
   */
  async processAutomatedRSVPs(userId: string): Promise<number> {
    try {
      // Get pending invites
      const pendingInvites = await this.calendarParser.getPendingInvites(userId)

      console.log(`Processing ${pendingInvites.length} pending invites for user ${userId}`)

      let processed = 0

      for (const invite of pendingInvites) {
        try {
          const decision = await this.makeRSVPDecision(userId, invite)

          if (decision.confidence >= 0.8) {
            // High confidence - auto-respond
            await this.executeRSVP(invite, decision)
            processed++

            console.log(`Auto-RSVP: ${decision.response} to "${invite.event_title}" (confidence: ${decision.confidence})`)
          } else {
            // Low confidence - mark for manual review
            console.log(`Manual review needed for "${invite.event_title}" (confidence: ${decision.confidence})`)
          }
        } catch (error: any) {
          console.error(`Failed to process invite ${invite.email_id}:`, error.message)
        }
      }

      return processed
    } catch (error: any) {
      console.error('Failed to process automated RSVPs:', error.message)
      return 0
    }
  }

  /**
   * Make RSVP decision based on rules, availability, and AI
   */
  private async makeRSVPDecision(userId: string, invite: any): Promise<RSVPDecision> {
    // Step 1: Check user rules (R0, R1, R2)
    const ruleDecision = await this.checkUserRules(userId, invite)
    if (ruleDecision) {
      return ruleDecision
    }

    // Step 2: Check calendar conflicts
    const hasConflict = await this.checkCalendarConflict(userId, invite)
    if (hasConflict) {
      return {
        response: 'declined',
        confidence: 0.95,
        reason: 'Calendar conflict detected',
        addToCalendar: false,
        sendComment: 'I have a conflict at this time.',
        archiveEmail: true
      }
    }

    // Step 3: Check availability preferences
    const availabilityDecision = await this.checkAvailabilityPreferences(userId, invite)
    if (availabilityDecision) {
      return availabilityDecision
    }

    // Step 4: AI-based decision (using GPT-OSS or similar)
    const aiDecision = await this.makeAIDecision(userId, invite)
    if (aiDecision) {
      return aiDecision
    }

    // Default: Low confidence, needs manual review
    return {
      response: 'tentative',
      confidence: 0.3,
      reason: 'No matching rules, needs manual review',
      addToCalendar: true,
      archiveEmail: false
    }
  }

  /**
   * Check user-defined RSVP rules
   */
  private async checkUserRules(userId: string, invite: any): Promise<RSVPDecision | null> {
    try {
      const rules = await this.postgres.query(
        `SELECT * FROM user_rules
         WHERE user_id = $1
           AND rule_type IN ('R0', 'R1', 'R2')
           AND enabled = true
         ORDER BY priority DESC`,
        [userId]
      )

      for (const rule of rules.rows) {
        const condition = rule.condition as AutoRSVPRule['condition']
        const action = rule.action as AutoRSVPRule['action']

        if (this.matchesCondition(invite, condition)) {
          console.log(`Matched rule ${rule.id}: ${rule.rule_type}`)

          if (action.response === 'ask') {
            // User wants to manually decide
            return null
          }

          return {
            response: action.response as 'accepted' | 'declined' | 'tentative',
            confidence: 1.0,
            reason: `Matched user rule: ${rule.rule_type}`,
            addToCalendar: action.addToCalendar ?? true,
            sendComment: action.sendComment,
            archiveEmail: action.autoArchive ?? true
          }
        }
      }

      return null
    } catch (error: any) {
      console.error('Failed to check user rules:', error.message)
      return null
    }
  }

  /**
   * Check if invite matches rule condition
   */
  private matchesCondition(invite: any, condition: AutoRSVPRule['condition']): boolean {
    // Check organizer pattern
    if (condition.organizerPattern) {
      const regex = new RegExp(condition.organizerPattern, 'i')
      if (!regex.test(invite.organizer)) {
        return false
      }
    }

    // Check subject pattern
    if (condition.subjectPattern) {
      const regex = new RegExp(condition.subjectPattern, 'i')
      if (!regex.test(invite.subject || invite.event_title)) {
        return false
      }
    }

    // Check time of day
    if (condition.timeOfDay) {
      const startTime = new Date(invite.start_time)
      const hour = startTime.getHours()
      const minute = startTime.getMinutes()
      const timeString = `${hour.toString().padStart(2, '0')}:${minute.toString().padStart(2, '0')}`

      if (timeString < condition.timeOfDay.start || timeString > condition.timeOfDay.end) {
        return false
      }
    }

    // Check day of week
    if (condition.dayOfWeek && condition.dayOfWeek.length > 0) {
      const startTime = new Date(invite.start_time)
      const dayOfWeek = startTime.getDay()

      if (!condition.dayOfWeek.includes(dayOfWeek)) {
        return false
      }
    }

    // Check duration
    if (condition.duration) {
      const startTime = new Date(invite.start_time)
      const endTime = new Date(invite.end_time)
      const durationMinutes = (endTime.getTime() - startTime.getTime()) / (1000 * 60)

      if (durationMinutes < condition.duration.min || durationMinutes > condition.duration.max) {
        return false
      }
    }

    return true
  }

  /**
   * Check for calendar conflicts
   */
  private async checkCalendarConflict(userId: string, invite: any): Promise<boolean> {
    try {
      // Find user's calendar account
      const calendarResult = await this.postgres.query(
        `SELECT ca.*, c.id as calendar_id, c.provider_calendar_id
         FROM calendar_accounts ca
         JOIN calendars c ON c.account_id = ca.id
         JOIN email_accounts ea ON ca.email_account_id = ea.id
         WHERE ea.user_id = $1
           AND ca.enabled = true
           AND c.is_primary = true
         LIMIT 1`,
        [userId]
      )

      if (calendarResult.rows.length === 0) {
        return false
      }

      const calendarAccount = calendarResult.rows[0]

      // Initialize calendar provider
      const calendarProvider = new GoogleCalendarProvider(this.googleOAuthConfig)
      await calendarProvider.initialize(calendarAccount)

      // Get events in the same time range
      const startTime = new Date(invite.start_time)
      const endTime = new Date(invite.end_time)

      const events = await calendarProvider.getEvents(
        calendarAccount.provider_calendar_id,
        startTime,
        endTime
      )

      // Check for conflicts (events that overlap)
      for (const event of events) {
        if (
          event.startTime < endTime &&
          event.endTime > startTime &&
          event.responseStatus !== 'declined'
        ) {
          console.log(`Conflict detected with event: ${event.title}`)
          return true
        }
      }

      return false
    } catch (error: any) {
      console.error('Failed to check calendar conflict:', error.message)
      return false
    }
  }

  /**
   * Check availability preferences (work hours, focus time, etc.)
   */
  private async checkAvailabilityPreferences(userId: string, invite: any): Promise<RSVPDecision | null> {
    try {
      const startTime = new Date(invite.start_time)
      const hour = startTime.getHours()
      const dayOfWeek = startTime.getDay()

      // Decline meetings outside work hours (9-17)
      if (hour < 9 || hour >= 17) {
        return {
          response: 'declined',
          confidence: 0.9,
          reason: 'Outside work hours',
          addToCalendar: false,
          sendComment: 'This is outside my normal work hours.',
          archiveEmail: true
        }
      }

      // Decline weekend meetings
      if (dayOfWeek === 0 || dayOfWeek === 6) {
        return {
          response: 'declined',
          confidence: 0.85,
          reason: 'Weekend meeting',
          addToCalendar: false,
          sendComment: 'I prefer not to schedule meetings on weekends.',
          archiveEmail: true
        }
      }

      // Decline very short meetings (< 15 min)
      const duration = (new Date(invite.end_time).getTime() - new Date(invite.start_time).getTime()) / (1000 * 60)
      if (duration < 15) {
        return {
          response: 'declined',
          confidence: 0.7,
          reason: 'Meeting too short',
          addToCalendar: false,
          sendComment: 'Could we handle this via email instead?',
          archiveEmail: true
        }
      }

      return null
    } catch (error: any) {
      console.error('Failed to check availability preferences:', error.message)
      return null
    }
  }

  /**
   * AI-based RSVP decision
   */
  private async makeAIDecision(userId: string, invite: any): Promise<RSVPDecision | null> {
    try {
      // TODO: Integrate with GPT-OSS or similar AI model
      // For now, return default tentative response

      // Example AI prompt:
      // "Should I accept this meeting invite?
      //  Subject: {invite.subject}
      //  Organizer: {invite.organizer}
      //  Time: {invite.start_time} - {invite.end_time}
      //  Location: {invite.location}
      //  My calendar: {calendar_context}
      //  My preferences: {user_preferences}"

      return {
        response: 'tentative',
        confidence: 0.5,
        reason: 'AI decision pending',
        addToCalendar: true,
        archiveEmail: false
      }
    } catch (error: any) {
      console.error('Failed to make AI decision:', error.message)
      return null
    }
  }

  /**
   * Execute RSVP decision
   */
  private async executeRSVP(invite: any, decision: RSVPDecision): Promise<void> {
    try {
      // Get email account
      const accountResult = await this.postgres.query(
        `SELECT ea.*, ca.id as calendar_account_id, c.provider_calendar_id
         FROM email_accounts ea
         JOIN emails e ON e.account_id = ea.id
         LEFT JOIN calendar_accounts ca ON ca.email_account_id = ea.id
         LEFT JOIN calendars c ON c.account_id = ca.id AND c.is_primary = true
         WHERE e.id = $1`,
        [invite.email_id]
      )

      if (accountResult.rows.length === 0) {
        throw new Error('Account not found')
      }

      const account = accountResult.rows[0]

      // Update calendar event response status
      if (invite.event_id) {
        await this.postgres.query(
          `UPDATE calendar_events
           SET response_status = $1, updated_at = NOW()
           WHERE id = $2`,
          [decision.response, invite.event_id]
        )

        // Send RSVP via calendar provider
        if (account.calendar_account_id && account.provider_calendar_id) {
          const calendarProvider = new GoogleCalendarProvider(this.googleOAuthConfig)
          await calendarProvider.initialize({
            id: account.calendar_account_id,
            emailAccountId: account.id,
            provider: 'google',
            accessToken: account.access_token,
            refreshToken: account.refresh_token,
            tokenExpiresAt: account.token_expires_at,
            enabled: true
          })

          await calendarProvider.respondToInvite(
            account.provider_calendar_id,
            invite.event_id,
            decision.response,
            decision.sendComment
          )
        }
      }

      // Update email-calendar link
      await this.postgres.query(
        `UPDATE email_calendar_links
         SET auto_responded = true,
             response_status = $1,
             updated_at = NOW()
         WHERE email_id = $2`,
        [decision.response, invite.email_id]
      )

      // Archive email if requested
      if (decision.archiveEmail && account.provider === 'gmail') {
        const gmailProvider = new GmailProvider(this.googleOAuthConfig)
        await gmailProvider.initialize(account)

        // Get provider message ID
        const emailResult = await this.postgres.query(
          `SELECT provider_message_id FROM emails WHERE id = $1`,
          [invite.email_id]
        )

        if (emailResult.rows.length > 0) {
          await gmailProvider.archive(emailResult.rows[0].provider_message_id)
        }
      }

      // Log action
      await this.postgres.query(
        `INSERT INTO email_actions
         (email_id, action_type, executed_by, metadata)
         VALUES ($1, $2, $3, $4)`,
        [
          invite.email_id,
          'auto_rsvp',
          'ai',
          JSON.stringify({
            response: decision.response,
            confidence: decision.confidence,
            reason: decision.reason
          })
        ]
      )

      // Update automation stats
      const today = new Date().toISOString().split('T')[0]
      await this.postgres.query(
        `INSERT INTO automation_stats
         (user_id, date, actions_automated, time_saved_seconds)
         VALUES ($1, $2, 1, 120)
         ON CONFLICT (user_id, date)
         DO UPDATE SET
           actions_automated = automation_stats.actions_automated + 1,
           time_saved_seconds = automation_stats.time_saved_seconds + 120`,
        [account.user_id, today]
      )

      console.log(`Executed RSVP for email ${invite.email_id}: ${decision.response}`)
    } catch (error: any) {
      console.error('Failed to execute RSVP:', error.message)
      throw error
    }
  }

  /**
   * Create or update user RSVP rule
   */
  async createRule(userId: string, rule: Omit<AutoRSVPRule, 'id'>): Promise<number> {
    try {
      const result = await this.postgres.query(
        `INSERT INTO user_rules
         (user_id, rule_type, condition, action, priority, enabled)
         VALUES ($1, $2, $3, $4, $5, $6)
         RETURNING id`,
        [
          userId,
          rule.ruleType,
          JSON.stringify(rule.condition),
          JSON.stringify(rule.action),
          rule.priority,
          rule.enabled
        ]
      )

      return result.rows[0].id
    } catch (error: any) {
      console.error('Failed to create rule:', error.message)
      throw error
    }
  }

  /**
   * Get user's RSVP rules
   */
  async getRules(userId: string): Promise<AutoRSVPRule[]> {
    try {
      const result = await this.postgres.query(
        `SELECT * FROM user_rules
         WHERE user_id = $1
           AND rule_type IN ('R0', 'R1', 'R2')
         ORDER BY priority DESC`,
        [userId]
      )

      return result.rows.map(row => ({
        id: row.id,
        userId: row.user_id,
        ruleType: row.rule_type,
        condition: row.condition,
        action: row.action,
        priority: row.priority,
        enabled: row.enabled
      }))
    } catch (error: any) {
      console.error('Failed to get rules:', error.message)
      return []
    }
  }

  /**
   * Get automation statistics
   */
  async getStats(userId: string, days: number = 30): Promise<any> {
    try {
      const result = await this.postgres.query(
        `SELECT
          SUM(actions_automated) as total_actions,
          SUM(time_saved_seconds) as total_time_saved,
          COUNT(DISTINCT date) as active_days,
          AVG(actions_automated) as avg_actions_per_day
         FROM automation_stats
         WHERE user_id = $1
           AND date >= CURRENT_DATE - $2::interval
         GROUP BY user_id`,
        [userId, `${days} days`]
      )

      if (result.rows.length === 0) {
        return {
          totalActions: 0,
          totalTimeSaved: 0,
          activeDays: 0,
          avgActionsPerDay: 0
        }
      }

      const stats = result.rows[0]

      return {
        totalActions: parseInt(stats.total_actions) || 0,
        totalTimeSaved: parseInt(stats.total_time_saved) || 0,
        totalTimeSavedHours: Math.round((parseInt(stats.total_time_saved) || 0) / 3600 * 10) / 10,
        activeDays: parseInt(stats.active_days) || 0,
        avgActionsPerDay: Math.round((parseFloat(stats.avg_actions_per_day) || 0) * 10) / 10
      }
    } catch (error: any) {
      console.error('Failed to get stats:', error.message)
      return {
        totalActions: 0,
        totalTimeSaved: 0,
        activeDays: 0,
        avgActionsPerDay: 0
      }
    }
  }
}
