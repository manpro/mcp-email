/**
 * Google Calendar Provider Implementation
 *
 * Uses Google Calendar API v3 for calendar integration
 * Supports event creation, RSVP, meeting time suggestions, and iCalendar parsing
 */

import { google, calendar_v3, Auth } from 'googleapis'
import * as ical from 'ical.js'
import {
  ICalendarProvider,
  CalendarAccount,
  Calendar,
  CalendarEvent,
  EventAttendee,
  ConferenceData,
  EventDefinition,
  MeetingTimeSuggestion,
  ProviderCredentials,
  AuthToken,
  OAuthCredentials
} from './types'

export class GoogleCalendarProvider implements ICalendarProvider {
  private calendar: calendar_v3.Calendar | null = null
  private oauth2Client: Auth.OAuth2Client | null = null
  private account: CalendarAccount | null = null

  constructor(private oauthConfig: OAuthCredentials) {}

  async initialize(account: CalendarAccount): Promise<void> {
    this.account = account

    // Create OAuth2 client
    this.oauth2Client = new google.auth.OAuth2(
      this.oauthConfig.clientId,
      this.oauthConfig.clientSecret,
      this.oauthConfig.redirectUri
    )

    // Set credentials if we have tokens
    if (account.accessToken) {
      this.oauth2Client.setCredentials({
        access_token: account.accessToken,
        refresh_token: account.refreshToken,
        expiry_date: account.tokenExpiresAt?.getTime()
      })

      // Auto-refresh tokens
      this.oauth2Client.on('tokens', (tokens) => {
        console.log('Google Calendar tokens refreshed:', {
          accountId: account.id,
          expiresIn: tokens.expiry_date
        })
      })
    }

    // Initialize Calendar client
    this.calendar = google.calendar({ version: 'v3', auth: this.oauth2Client })
  }

  async authenticate(credentials: ProviderCredentials): Promise<AuthToken> {
    if (!this.oauth2Client) {
      throw new Error('OAuth2 client not initialized')
    }

    if (credentials.authCode) {
      const { tokens } = await this.oauth2Client.getToken(credentials.authCode)
      this.oauth2Client.setCredentials(tokens)

      return {
        accessToken: tokens.access_token!,
        refreshToken: tokens.refresh_token,
        expiresAt: new Date(tokens.expiry_date!),
        tokenType: tokens.token_type!,
        scope: tokens.scope
      }
    }

    throw new Error('Invalid credentials: authCode required')
  }

  async refreshToken(refreshToken: string): Promise<AuthToken> {
    if (!this.oauth2Client) {
      throw new Error('OAuth2 client not initialized')
    }

    this.oauth2Client.setCredentials({ refresh_token: refreshToken })
    const { credentials } = await this.oauth2Client.refreshAccessToken()

    return {
      accessToken: credentials.access_token!,
      refreshToken: credentials.refresh_token,
      expiresAt: new Date(credentials.expiry_date!),
      tokenType: credentials.token_type!
    }
  }

  async getCalendars(): Promise<Calendar[]> {
    if (!this.calendar) throw new Error('Calendar client not initialized')

    const response = await this.calendar.calendarList.list()
    const calendars = response.data.items || []

    return calendars.map(cal => ({
      id: 0, // Will be assigned by database
      accountId: this.account?.id || 0,
      providerCalendarId: cal.id || '',
      name: cal.summary || '',
      description: cal.description,
      color: cal.backgroundColor,
      isPrimary: cal.primary || false,
      isWritable: cal.accessRole === 'owner' || cal.accessRole === 'writer',
      timezone: cal.timeZone || 'UTC'
    }))
  }

  async getEvents(calendarId: string, startTime: Date, endTime: Date): Promise<CalendarEvent[]> {
    if (!this.calendar) throw new Error('Calendar client not initialized')

    const response = await this.calendar.events.list({
      calendarId,
      timeMin: startTime.toISOString(),
      timeMax: endTime.toISOString(),
      singleEvents: true,
      orderBy: 'startTime'
    })

    const events = response.data.items || []
    return events.map(event => this.transformEvent(event))
  }

  async getEvent(calendarId: string, eventId: string): Promise<CalendarEvent> {
    if (!this.calendar) throw new Error('Calendar client not initialized')

    const response = await this.calendar.events.get({
      calendarId,
      eventId
    })

    return this.transformEvent(response.data)
  }

  async createEvent(calendarId: string, event: EventDefinition): Promise<CalendarEvent> {
    if (!this.calendar) throw new Error('Calendar client not initialized')

    const eventResource: calendar_v3.Schema$Event = {
      summary: event.title,
      description: event.description,
      location: event.location,
      start: event.isAllDay
        ? { date: event.startTime.toISOString().split('T')[0] }
        : { dateTime: event.startTime.toISOString() },
      end: event.isAllDay
        ? { date: event.endTime.toISOString().split('T')[0] }
        : { dateTime: event.endTime.toISOString() },
      attendees: event.attendees?.map(email => ({ email })),
      recurrence: event.recurrence,
      reminders: event.reminders
        ? {
            useDefault: false,
            overrides: event.reminders.map(r => ({
              method: r.method === 'email' ? 'email' : 'popup',
              minutes: r.minutes
            }))
          }
        : { useDefault: true }
    }

    // Add Google Meet if requested
    if (event.createMeeting) {
      eventResource.conferenceData = {
        createRequest: {
          requestId: `meet-${Date.now()}`,
          conferenceSolutionKey: { type: 'hangoutsMeet' }
        }
      }
    }

    const response = await this.calendar.events.insert({
      calendarId,
      conferenceDataVersion: event.createMeeting ? 1 : undefined,
      requestBody: eventResource,
      sendUpdates: 'all'
    })

    return this.transformEvent(response.data)
  }

  async updateEvent(
    calendarId: string,
    eventId: string,
    updates: Partial<EventDefinition>
  ): Promise<CalendarEvent> {
    if (!this.calendar) throw new Error('Calendar client not initialized')

    const eventResource: calendar_v3.Schema$Event = {}

    if (updates.title) eventResource.summary = updates.title
    if (updates.description) eventResource.description = updates.description
    if (updates.location) eventResource.location = updates.location
    if (updates.startTime) {
      eventResource.start = updates.isAllDay
        ? { date: updates.startTime.toISOString().split('T')[0] }
        : { dateTime: updates.startTime.toISOString() }
    }
    if (updates.endTime) {
      eventResource.end = updates.isAllDay
        ? { date: updates.endTime.toISOString().split('T')[0] }
        : { dateTime: updates.endTime.toISOString() }
    }

    const response = await this.calendar.events.patch({
      calendarId,
      eventId,
      requestBody: eventResource,
      sendUpdates: 'all'
    })

    return this.transformEvent(response.data)
  }

  async deleteEvent(calendarId: string, eventId: string): Promise<void> {
    if (!this.calendar) throw new Error('Calendar client not initialized')

    await this.calendar.events.delete({
      calendarId,
      eventId,
      sendUpdates: 'all'
    })
  }

  async respondToInvite(
    calendarId: string,
    eventId: string,
    response: 'accepted' | 'declined' | 'tentative',
    comment?: string
  ): Promise<void> {
    if (!this.calendar) throw new Error('Calendar client not initialized')

    // Get current event
    const event = await this.calendar.events.get({ calendarId, eventId })
    const attendees = event.data.attendees || []

    // Find current user's attendee entry
    const userEmail = await this.getUserEmail()
    const userAttendee = attendees.find(a => a.email === userEmail)

    if (userAttendee) {
      // Update response status
      userAttendee.responseStatus = response

      // Update event with new response
      await this.calendar.events.patch({
        calendarId,
        eventId,
        requestBody: {
          attendees
        },
        sendUpdates: 'all'
      })
    }
  }

  async findMeetingTimes(
    attendees: string[],
    duration: number,
    startDate: Date,
    endDate: Date
  ): Promise<MeetingTimeSuggestion[]> {
    if (!this.calendar) throw new Error('Calendar client not initialized')

    // Get free/busy information for all attendees
    const response = await this.calendar.freebusy.query({
      requestBody: {
        timeMin: startDate.toISOString(),
        timeMax: endDate.toISOString(),
        items: attendees.map(email => ({ id: email }))
      }
    })

    const calendars = response.data.calendars || {}
    const suggestions: MeetingTimeSuggestion[] = []

    // Find time slots where all attendees are available
    const workHours = { start: 9, end: 17 } // 9 AM to 5 PM
    let currentTime = new Date(startDate)

    while (currentTime < endDate) {
      // Only check during work hours
      if (currentTime.getHours() >= workHours.start && currentTime.getHours() < workHours.end) {
        const endTime = new Date(currentTime.getTime() + duration * 60000)

        // Check if all attendees are free
        const allFree = attendees.every(email => {
          const calendar = calendars[email]
          if (!calendar || !calendar.busy) return true

          return !calendar.busy.some(busy => {
            const busyStart = new Date(busy.start!)
            const busyEnd = new Date(busy.end!)
            return currentTime < busyEnd && endTime > busyStart
          })
        })

        if (allFree) {
          suggestions.push({
            startTime: new Date(currentTime),
            endTime: new Date(endTime),
            confidence: 1.0,
            attendeeAvailability: attendees.map(email => ({
              email,
              available: true
            }))
          })
        }
      }

      // Move to next 30-minute slot
      currentTime = new Date(currentTime.getTime() + 30 * 60000)
    }

    return suggestions.slice(0, 10) // Return top 10 suggestions
  }

  async parseICS(icsContent: string): Promise<{
    method: 'REQUEST' | 'REPLY' | 'CANCEL'
    event: CalendarEvent
    organizer: string
    attendees: EventAttendee[]
  }> {
    const jcalData = ical.parse(icsContent)
    const comp = new ical.Component(jcalData)
    const vevent = comp.getFirstSubcomponent('vevent')

    if (!vevent) {
      throw new Error('No VEVENT found in ICS')
    }

    const method = (comp.getFirstPropertyValue('method') || 'REQUEST') as 'REQUEST' | 'REPLY' | 'CANCEL'
    const summary = vevent.getFirstPropertyValue('summary') || ''
    const description = vevent.getFirstPropertyValue('description')
    const location = vevent.getFirstPropertyValue('location')
    const dtstart = vevent.getFirstPropertyValue('dtstart')
    const dtend = vevent.getFirstPropertyValue('dtend')
    const uid = vevent.getFirstPropertyValue('uid') || ''
    const organizer = vevent.getFirstPropertyValue('organizer')?.toString() || ''

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

    const event: CalendarEvent = {
      id: 0,
      calendarId: 0,
      providerEventId: uid,
      title: summary,
      description,
      location,
      startTime: dtstart.toJSDate(),
      endTime: dtend.toJSDate(),
      isAllDay: dtstart.isDate,
      attendees,
      organizer: organizer.replace('mailto:', ''),
      icalUid: uid,
      metadata: {}
    }

    return {
      method,
      event,
      organizer: organizer.replace('mailto:', ''),
      attendees
    }
  }

  async generateICSReply(
    event: CalendarEvent,
    response: 'accepted' | 'declined' | 'tentative',
    comment?: string
  ): Promise<string> {
    const userEmail = await this.getUserEmail()

    const comp = new ical.Component(['vcalendar', [], []])
    comp.updatePropertyWithValue('prodid', '-//AI Email Manager//NONSGML v1.0//EN')
    comp.updatePropertyWithValue('version', '2.0')
    comp.updatePropertyWithValue('method', 'REPLY')

    const vevent = new ical.Component('vevent')
    vevent.updatePropertyWithValue('uid', event.icalUid || event.providerEventId)
    vevent.updatePropertyWithValue('summary', event.title)
    vevent.updatePropertyWithValue('dtstart', ical.Time.fromJSDate(event.startTime, false))
    vevent.updatePropertyWithValue('dtend', ical.Time.fromJSDate(event.endTime, false))

    if (event.organizer) {
      vevent.updatePropertyWithValue('organizer', `mailto:${event.organizer}`)
    }

    // Add attendee with response status
    const attendeeProp = vevent.updatePropertyWithValue('attendee', `mailto:${userEmail}`)
    attendeeProp.setParameter('partstat', this.mapResponseStatusToPartstat(response))
    attendeeProp.setParameter('cn', userEmail)

    if (comment) {
      vevent.updatePropertyWithValue('comment', comment)
    }

    comp.addSubcomponent(vevent)

    return comp.toString()
  }

  async setupWebhook(webhookUrl: string, calendarId: string): Promise<{ webhookId: string }> {
    if (!this.calendar) throw new Error('Calendar client not initialized')

    const response = await this.calendar.events.watch({
      calendarId,
      requestBody: {
        id: `webhook-${Date.now()}`,
        type: 'web_hook',
        address: webhookUrl
      }
    })

    return {
      webhookId: response.data.id || ''
    }
  }

  async stopWebhook(webhookId: string): Promise<void> {
    if (!this.calendar) throw new Error('Calendar client not initialized')

    await this.calendar.channels.stop({
      requestBody: {
        id: webhookId,
        resourceId: ''
      }
    })
  }

  async disconnect(): Promise<void> {
    this.calendar = null
    this.oauth2Client = null
  }

  // ============================================================================
  // Helper Methods
  // ============================================================================

  private transformEvent(event: calendar_v3.Schema$Event): CalendarEvent {
    const attendees: EventAttendee[] = (event.attendees || []).map(a => ({
      email: a.email || '',
      displayName: a.displayName,
      responseStatus: this.mapGoogleResponseStatus(a.responseStatus),
      optional: a.optional
    }))

    const conferenceData: ConferenceData | undefined = event.conferenceData
      ? {
          type: 'hangoutsMeet',
          url: event.conferenceData.entryPoints?.[0]?.uri,
          conferenceId: event.conferenceData.conferenceId,
          metadata: event.conferenceData
        }
      : undefined

    return {
      id: 0,
      calendarId: 0,
      providerEventId: event.id || '',
      title: event.summary || 'Untitled',
      description: event.description,
      location: event.location,
      startTime: event.start?.dateTime
        ? new Date(event.start.dateTime)
        : new Date(event.start?.date || ''),
      endTime: event.end?.dateTime ? new Date(event.end.dateTime) : new Date(event.end?.date || ''),
      isAllDay: !!event.start?.date,
      attendees,
      organizer: event.organizer?.email,
      responseStatus: this.mapGoogleResponseStatus(event.attendees?.find(a => a.self)?.responseStatus),
      conferenceData,
      recurrence: event.recurrence,
      icalUid: event.iCalUID,
      metadata: event
    }
  }

  private mapGoogleResponseStatus(
    status?: string
  ): 'accepted' | 'declined' | 'tentative' | 'needsAction' | undefined {
    switch (status) {
      case 'accepted':
        return 'accepted'
      case 'declined':
        return 'declined'
      case 'tentative':
        return 'tentative'
      case 'needsAction':
        return 'needsAction'
      default:
        return undefined
    }
  }

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

  private mapResponseStatusToPartstat(status: 'accepted' | 'declined' | 'tentative'): string {
    switch (status) {
      case 'accepted':
        return 'ACCEPTED'
      case 'declined':
        return 'DECLINED'
      case 'tentative':
        return 'TENTATIVE'
    }
  }

  private async getUserEmail(): Promise<string> {
    if (!this.calendar) throw new Error('Calendar client not initialized')

    const response = await this.calendar.calendarList.get({
      calendarId: 'primary'
    })

    return response.data.id || ''
  }
}
