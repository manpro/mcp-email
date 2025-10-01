/**
 * Calendar Invite Parser Service
 *
 * Detects and parses calendar invites (.ics attachments) in emails
 * Links emails to calendar events for auto-RSVP workflow
 */

import { Pool } from 'pg'
import * as ical from 'ical.js'
import { GoogleCalendarProvider } from '../providers/google-calendar-provider'
import { CalendarEvent, EventAttendee, OAuthCredentials } from '../providers/types'

interface ParsedInvite {
  method: 'REQUEST' | 'REPLY' | 'CANCEL'
  icalUid: string
  organizer: string
  attendees: EventAttendee[]
  event: {
    title: string
    description?: string
    location?: string
    startTime: Date
    endTime: Date
    isAllDay: boolean
    recurrence?: string[]
  }
}

export class CalendarInviteParser {
  private postgres: Pool
  private googleOAuthConfig: OAuthCredentials

  constructor(postgres: Pool, googleOAuthConfig: OAuthCredentials) {
    this.postgres = postgres
    this.googleOAuthConfig = googleOAuthConfig
  }

  /**
   * Process email to detect and parse calendar invites
   */
  async processEmail(emailId: number): Promise<boolean> {
    try {
      // Get email with attachments
      const emailResult = await this.postgres.query(
        `SELECT e.*, ea.account_id
         FROM emails e
         WHERE e.id = $1 AND e.has_attachments = true`,
        [emailId]
      )

      if (emailResult.rows.length === 0) {
        return false
      }

      const email = emailResult.rows[0]

      // Check for .ics attachments in body or as separate attachments
      const icsContent = await this.extractICSContent(email)

      if (!icsContent) {
        return false
      }

      // Parse ICS content
      const invite = await this.parseICS(icsContent)

      if (!invite) {
        return false
      }

      console.log('Parsed calendar invite:', {
        emailId,
        method: invite.method,
        title: invite.event.title,
        organizer: invite.organizer,
        attendees: invite.attendees.length
      })

      // Check if calendar event already exists
      const existingLink = await this.postgres.query(
        `SELECT id FROM email_calendar_links
         WHERE email_id = $1 OR ics_uid = $2`,
        [emailId, invite.icalUid]
      )

      if (existingLink.rows.length > 0) {
        console.log(`Calendar invite already processed for email ${emailId}`)
        return true
      }

      // Find user's calendar account
      const calendarAccount = await this.findCalendarAccount(email.account_id)

      if (!calendarAccount) {
        console.log('No calendar account found, creating link without calendar event')

        // Create email-calendar link without event (will be processed later)
        await this.createEmailCalendarLink(emailId, null, invite)
        return true
      }

      // Create or update calendar event
      const calendarEventId = await this.createCalendarEvent(
        calendarAccount,
        invite,
        email.account_id
      )

      // Create email-calendar link
      await this.createEmailCalendarLink(emailId, calendarEventId, invite)

      console.log(`Created calendar event and link for email ${emailId}`)

      return true
    } catch (error: any) {
      console.error(`Failed to process calendar invite for email ${emailId}:`, error.message)
      return false
    }
  }

  /**
   * Extract ICS content from email
   */
  private async extractICSContent(email: any): Promise<string | null> {
    try {
      // Check if there's an .ics attachment in the email metadata
      // In production, this would fetch actual attachment data

      // For now, look for ICS in body_text or headers
      const bodyText = email.body_text || ''
      const bodyHtml = email.body_html || ''

      // Look for BEGIN:VCALENDAR in body
      if (bodyText.includes('BEGIN:VCALENDAR')) {
        const start = bodyText.indexOf('BEGIN:VCALENDAR')
        const end = bodyText.indexOf('END:VCALENDAR')
        if (end > start) {
          return bodyText.substring(start, end + 'END:VCALENDAR'.length)
        }
      }

      if (bodyHtml.includes('BEGIN:VCALENDAR')) {
        const start = bodyHtml.indexOf('BEGIN:VCALENDAR')
        const end = bodyHtml.indexOf('END:VCALENDAR')
        if (end > start) {
          return bodyHtml.substring(start, end + 'END:VCALENDAR'.length)
        }
      }

      // TODO: In production, fetch actual .ics attachment from provider
      // const attachments = await provider.getAttachments(email.provider_message_id)
      // const icsAttachment = attachments.find(a => a.mimeType === 'text/calendar')

      return null
    } catch (error: any) {
      console.error('Failed to extract ICS content:', error.message)
      return null
    }
  }

  /**
   * Parse ICS content using ical.js
   */
  private async parseICS(icsContent: string): Promise<ParsedInvite | null> {
    try {
      const jcalData = ical.parse(icsContent)
      const comp = new ical.Component(jcalData)
      const vevent = comp.getFirstSubcomponent('vevent')

      if (!vevent) {
        console.log('No VEVENT found in ICS')
        return null
      }

      const method = (comp.getFirstPropertyValue('method') || 'REQUEST') as 'REQUEST' | 'REPLY' | 'CANCEL'
      const uid = vevent.getFirstPropertyValue('uid') || ''
      const summary = vevent.getFirstPropertyValue('summary') || 'Untitled Event'
      const description = vevent.getFirstPropertyValue('description')
      const location = vevent.getFirstPropertyValue('location')
      const dtstart = vevent.getFirstPropertyValue('dtstart')
      const dtend = vevent.getFirstPropertyValue('dtend')
      const organizer = vevent.getFirstPropertyValue('organizer')?.toString() || ''
      const rrule = vevent.getFirstPropertyValue('rrule')

      // Parse attendees
      const attendeeProps = vevent.getAllProperties('attendee')
      const attendees: EventAttendee[] = attendeeProps.map(prop => {
        const email = prop.getFirstValue().toString().replace('mailto:', '')
        const partstat = prop.getParameter('partstat') || 'NEEDS-ACTION'
        const cn = prop.getParameter('cn')

        return {
          email,
          displayName: cn,
          responseStatus: this.mapPartstatToResponseStatus(partstat),
          optional: prop.getParameter('role') === 'OPT-PARTICIPANT'
        }
      })

      // Build recurrence array if present
      const recurrence: string[] = []
      if (rrule) {
        recurrence.push(`RRULE:${rrule.toString()}`)
      }

      const invite: ParsedInvite = {
        method,
        icalUid: uid,
        organizer: organizer.replace('mailto:', ''),
        attendees,
        event: {
          title: summary,
          description,
          location,
          startTime: dtstart.toJSDate(),
          endTime: dtend.toJSDate(),
          isAllDay: dtstart.isDate,
          recurrence: recurrence.length > 0 ? recurrence : undefined
        }
      }

      return invite
    } catch (error: any) {
      console.error('Failed to parse ICS:', error.message)
      return null
    }
  }

  /**
   * Find calendar account for email account
   */
  private async findCalendarAccount(emailAccountId: number): Promise<any | null> {
    try {
      const result = await this.postgres.query(
        `SELECT ca.*, c.id as calendar_id, c.provider_calendar_id
         FROM calendar_accounts ca
         JOIN calendars c ON c.account_id = ca.id
         WHERE ca.email_account_id = $1
           AND ca.enabled = true
           AND c.is_primary = true
         LIMIT 1`,
        [emailAccountId]
      )

      return result.rows.length > 0 ? result.rows[0] : null
    } catch (error: any) {
      console.error('Failed to find calendar account:', error.message)
      return null
    }
  }

  /**
   * Create calendar event in Google Calendar
   */
  private async createCalendarEvent(
    calendarAccount: any,
    invite: ParsedInvite,
    emailAccountId: number
  ): Promise<number | null> {
    try {
      // Check if event already exists by iCal UID
      const existingEvent = await this.postgres.query(
        `SELECT id FROM calendar_events WHERE ical_uid = $1`,
        [invite.icalUid]
      )

      if (existingEvent.rows.length > 0) {
        console.log(`Calendar event already exists: ${invite.icalUid}`)
        return existingEvent.rows[0].id
      }

      // Initialize Google Calendar provider
      const calendarProvider = new GoogleCalendarProvider(this.googleOAuthConfig)
      await calendarProvider.initialize(calendarAccount)

      // Create event in Google Calendar
      const calendarEvent = await calendarProvider.createEvent(
        calendarAccount.provider_calendar_id,
        {
          title: invite.event.title,
          description: invite.event.description,
          location: invite.event.location,
          startTime: invite.event.startTime,
          endTime: invite.event.endTime,
          isAllDay: invite.event.isAllDay,
          attendees: invite.attendees.map(a => a.email),
          recurrence: invite.event.recurrence
        }
      )

      // Store event in database
      const result = await this.postgres.query(
        `INSERT INTO calendar_events (
          calendar_id, provider_event_id, title, description, location,
          start_time, end_time, is_all_day, attendees, organizer,
          response_status, recurrence, ical_uid
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
        RETURNING id`,
        [
          calendarAccount.calendar_id,
          calendarEvent.providerEventId,
          invite.event.title,
          invite.event.description,
          invite.event.location,
          invite.event.startTime,
          invite.event.endTime,
          invite.event.isAllDay,
          JSON.stringify(invite.attendees),
          invite.organizer,
          'needsAction',
          JSON.stringify(invite.event.recurrence),
          invite.icalUid
        ]
      )

      return result.rows[0].id
    } catch (error: any) {
      console.error('Failed to create calendar event:', error.message)
      return null
    }
  }

  /**
   * Create email-calendar link
   */
  private async createEmailCalendarLink(
    emailId: number,
    calendarEventId: number | null,
    invite: ParsedInvite
  ): Promise<void> {
    try {
      await this.postgres.query(
        `INSERT INTO email_calendar_links (
          email_id, calendar_event_id, ics_method, ics_uid, processed
        ) VALUES ($1, $2, $3, $4, $5)`,
        [emailId, calendarEventId, invite.method, invite.icalUid, calendarEventId !== null]
      )

      console.log(`Created email-calendar link for email ${emailId}`)
    } catch (error: any) {
      console.error('Failed to create email-calendar link:', error.message)
    }
  }

  /**
   * Process all unprocessed emails with attachments
   */
  async processUnprocessedEmails(): Promise<number> {
    try {
      // Find emails with attachments that haven't been processed
      const result = await this.postgres.query(
        `SELECT e.id
         FROM emails e
         LEFT JOIN email_calendar_links ecl ON e.id = ecl.email_id
         WHERE e.has_attachments = true
           AND ecl.id IS NULL
         LIMIT 100`
      )

      let processed = 0

      for (const row of result.rows) {
        const success = await this.processEmail(row.id)
        if (success) {
          processed++
        }
      }

      console.log(`Processed ${processed} calendar invites`)

      return processed
    } catch (error: any) {
      console.error('Failed to process unprocessed emails:', error.message)
      return 0
    }
  }

  /**
   * Get pending invites that need RSVP
   */
  async getPendingInvites(userId: string): Promise<any[]> {
    try {
      const result = await this.postgres.query(
        `SELECT
          e.id as email_id,
          e.subject,
          e.from_address,
          e.received_at,
          ce.id as event_id,
          ce.title as event_title,
          ce.start_time,
          ce.end_time,
          ce.location,
          ce.organizer,
          ce.response_status,
          ecl.ics_method,
          ecl.auto_responded
         FROM emails e
         JOIN email_calendar_links ecl ON e.id = ecl.email_id
         LEFT JOIN calendar_events ce ON ecl.calendar_event_id = ce.id
         JOIN email_accounts ea ON e.account_id = ea.id
         WHERE ea.user_id = $1
           AND ecl.ics_method = 'REQUEST'
           AND ecl.auto_responded = false
           AND (ce.response_status = 'needsAction' OR ce.response_status IS NULL)
         ORDER BY e.received_at DESC`,
        [userId]
      )

      return result.rows
    } catch (error: any) {
      console.error('Failed to get pending invites:', error.message)
      return []
    }
  }

  // ==========================================================================
  // Helper Methods
  // ==========================================================================

  private mapPartstatToResponseStatus(partstat: string): 'accepted' | 'declined' | 'tentative' | 'needsAction' {
    switch (partstat.toUpperCase()) {
      case 'ACCEPTED':
        return 'accepted'
      case 'DECLINED':
        return 'declined'
      case 'TENTATIVE':
        return 'tentative'
      default:
        return 'needsAction'
    }
  }
}
