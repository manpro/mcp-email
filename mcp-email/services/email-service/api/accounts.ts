/**
 * Account Management API Endpoints
 *
 * Handles email account connections, OAuth flows, and account management
 * Supports IMAP, Gmail, and Exchange providers
 */

import { Router, Request, Response } from 'express'
import { Pool } from 'pg'
import { GmailProvider } from '../providers/gmail-provider'
import { GoogleCalendarProvider } from '../providers/google-calendar-provider'
import { OAuth2Client } from 'google-auth-library'
import {
  EmailAccount,
  CalendarAccount,
  EmailProvider,
  CalendarProvider,
  OAuthCredentials
} from '../providers/types'

export class AccountsAPI {
  private router: Router
  private postgres: Pool
  private gmailOAuthConfig: OAuthCredentials
  private googleOAuth2Client: OAuth2Client

  constructor(postgres: Pool, gmailOAuthConfig: OAuthCredentials) {
    this.router = Router()
    this.postgres = postgres
    this.gmailOAuthConfig = gmailOAuthConfig

    this.googleOAuth2Client = new OAuth2Client(
      gmailOAuthConfig.clientId,
      gmailOAuthConfig.clientSecret,
      gmailOAuthConfig.redirectUri
    )

    this.setupRoutes()
  }

  private setupRoutes() {
    // ========================================================================
    // OAuth Authorization URLs
    // ========================================================================

    /**
     * GET /api/accounts/oauth/gmail/url
     * Generate Gmail OAuth authorization URL
     */
    this.router.get('/oauth/gmail/url', this.getGmailAuthUrl.bind(this))

    /**
     * GET /api/accounts/oauth/exchange/url
     * Generate Microsoft Exchange OAuth authorization URL
     */
    this.router.get('/oauth/exchange/url', this.getExchangeAuthUrl.bind(this))

    // ========================================================================
    // OAuth Callbacks
    // ========================================================================

    /**
     * GET /api/accounts/oauth/gmail/callback
     * Handle Gmail OAuth callback
     */
    this.router.get('/oauth/gmail/callback', this.handleGmailCallback.bind(this))

    /**
     * GET /api/accounts/oauth/exchange/callback
     * Handle Exchange OAuth callback
     */
    this.router.get('/oauth/exchange/callback', this.handleExchangeCallback.bind(this))

    // ========================================================================
    // Account Management
    // ========================================================================

    /**
     * GET /api/accounts
     * List all email accounts for user
     */
    this.router.get('/', this.listAccounts.bind(this))

    /**
     * POST /api/accounts
     * Create new email account (IMAP with password)
     */
    this.router.post('/', this.createAccount.bind(this))

    /**
     * GET /api/accounts/:id
     * Get single account details
     */
    this.router.get('/:id', this.getAccount.bind(this))

    /**
     * PUT /api/accounts/:id
     * Update account settings
     */
    this.router.put('/:id', this.updateAccount.bind(this))

    /**
     * DELETE /api/accounts/:id
     * Remove email account
     */
    this.router.delete('/:id', this.removeAccount.bind(this))

    /**
     * POST /api/accounts/:id/sync
     * Manually trigger account sync
     */
    this.router.post('/:id/sync', this.syncAccount.bind(this))

    /**
     * GET /api/accounts/:id/status
     * Get account sync status
     */
    this.router.get('/:id/status', this.getAccountStatus.bind(this))

    // ========================================================================
    // Calendar Management
    // ========================================================================

    /**
     * GET /api/accounts/:id/calendars
     * List calendars for account
     */
    this.router.get('/:id/calendars', this.listCalendars.bind(this))

    /**
     * POST /api/accounts/:id/calendars/sync
     * Sync calendars for account
     */
    this.router.post('/:id/calendars/sync', this.syncCalendars.bind(this))
  }

  // ==========================================================================
  // OAuth Authorization URLs
  // ==========================================================================

  private async getGmailAuthUrl(req: Request, res: Response) {
    try {
      const state = this.generateState(req.query.userId as string)

      const authUrl = this.googleOAuth2Client.generateAuthUrl({
        access_type: 'offline',
        scope: [
          'https://www.googleapis.com/auth/gmail.modify',
          'https://www.googleapis.com/auth/gmail.send',
          'https://www.googleapis.com/auth/calendar',
          'https://www.googleapis.com/auth/calendar.events'
        ],
        state,
        prompt: 'consent' // Force consent to get refresh token
      })

      res.json({ authUrl, state })
    } catch (error: any) {
      console.error('Failed to generate Gmail auth URL:', error)
      res.status(500).json({ error: error.message })
    }
  }

  private async getExchangeAuthUrl(req: Request, res: Response) {
    try {
      // Microsoft Identity Platform OAuth 2.0
      const tenantId = process.env.AZURE_TENANT_ID || 'common'
      const clientId = process.env.AZURE_CLIENT_ID
      const redirectUri = process.env.AZURE_REDIRECT_URI
      const state = this.generateState(req.query.userId as string)

      const authUrl = `https://login.microsoftonline.com/${tenantId}/oauth2/v2.0/authorize?` +
        `client_id=${clientId}&` +
        `response_type=code&` +
        `redirect_uri=${encodeURIComponent(redirectUri!)}&` +
        `response_mode=query&` +
        `scope=${encodeURIComponent('https://graph.microsoft.com/Mail.ReadWrite https://graph.microsoft.com/Calendars.ReadWrite offline_access')}&` +
        `state=${state}`

      res.json({ authUrl, state })
    } catch (error: any) {
      console.error('Failed to generate Exchange auth URL:', error)
      res.status(500).json({ error: error.message })
    }
  }

  // ==========================================================================
  // OAuth Callbacks
  // ==========================================================================

  private async handleGmailCallback(req: Request, res: Response) {
    try {
      const { code, state } = req.query

      if (!code || !state) {
        return res.status(400).json({ error: 'Missing code or state' })
      }

      const userId = this.verifyState(state as string)
      if (!userId) {
        return res.status(400).json({ error: 'Invalid state' })
      }

      // Exchange code for tokens
      const { tokens } = await this.googleOAuth2Client.getToken(code as string)

      // Get user email address
      this.googleOAuth2Client.setCredentials(tokens)
      const gmail = new GmailProvider(this.gmailOAuthConfig)
      await gmail.initialize({
        id: 0,
        userId,
        provider: 'gmail',
        emailAddress: '',
        authType: 'oauth',
        accessToken: tokens.access_token!,
        refreshToken: tokens.refresh_token,
        tokenExpiresAt: new Date(tokens.expiry_date!),
        enabled: true,
        capabilities: gmail.getCapabilities()
      })

      const profile = await this.googleOAuth2Client.request({
        url: 'https://www.googleapis.com/gmail/v1/users/me/profile'
      })
      const emailAddress = (profile.data as any).emailAddress

      // Create email account in database
      const accountResult = await this.postgres.query(
        `INSERT INTO email_accounts
         (user_id, provider, email_address, auth_type, access_token, refresh_token, token_expires_at, enabled)
         VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
         RETURNING id`,
        [userId, 'gmail', emailAddress, 'oauth', tokens.access_token, tokens.refresh_token, new Date(tokens.expiry_date!), true]
      )

      const accountId = accountResult.rows[0].id

      // Create calendar account
      await this.postgres.query(
        `INSERT INTO calendar_accounts
         (email_account_id, provider, access_token, refresh_token, token_expires_at, enabled)
         VALUES ($1, $2, $3, $4, $5, $6)`,
        [accountId, 'google', tokens.access_token, tokens.refresh_token, new Date(tokens.expiry_date!), true]
      )

      // Redirect to success page
      res.redirect(`/settings/accounts?success=gmail&accountId=${accountId}`)
    } catch (error: any) {
      console.error('Gmail OAuth callback error:', error)
      res.redirect(`/settings/accounts?error=${encodeURIComponent(error.message)}`)
    }
  }

  private async handleExchangeCallback(req: Request, res: Response) {
    try {
      const { code, state } = req.query

      if (!code || !state) {
        return res.status(400).json({ error: 'Missing code or state' })
      }

      const userId = this.verifyState(state as string)
      if (!userId) {
        return res.status(400).json({ error: 'Invalid state' })
      }

      // Exchange code for tokens (using Microsoft Identity Platform)
      const tokenResponse = await fetch('https://login.microsoftonline.com/common/oauth2/v2.0/token', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: new URLSearchParams({
          client_id: process.env.AZURE_CLIENT_ID!,
          client_secret: process.env.AZURE_CLIENT_SECRET!,
          code: code as string,
          redirect_uri: process.env.AZURE_REDIRECT_URI!,
          grant_type: 'authorization_code'
        })
      })

      const tokens = await tokenResponse.json()

      if (!tokens.access_token) {
        throw new Error('Failed to obtain access token')
      }

      // Get user email from Microsoft Graph
      const graphResponse = await fetch('https://graph.microsoft.com/v1.0/me', {
        headers: { Authorization: `Bearer ${tokens.access_token}` }
      })
      const userInfo = await graphResponse.json()
      const emailAddress = userInfo.mail || userInfo.userPrincipalName

      // Create email account in database
      const expiresAt = new Date(Date.now() + tokens.expires_in * 1000)

      const accountResult = await this.postgres.query(
        `INSERT INTO email_accounts
         (user_id, provider, email_address, auth_type, access_token, refresh_token, token_expires_at, enabled)
         VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
         RETURNING id`,
        [userId, 'exchange', emailAddress, 'oauth', tokens.access_token, tokens.refresh_token, expiresAt, true]
      )

      const accountId = accountResult.rows[0].id

      // Create calendar account
      await this.postgres.query(
        `INSERT INTO calendar_accounts
         (email_account_id, provider, access_token, refresh_token, token_expires_at, enabled)
         VALUES ($1, $2, $3, $4, $5, $6)`,
        [accountId, 'exchange', tokens.access_token, tokens.refresh_token, expiresAt, true]
      )

      res.redirect(`/settings/accounts?success=exchange&accountId=${accountId}`)
    } catch (error: any) {
      console.error('Exchange OAuth callback error:', error)
      res.redirect(`/settings/accounts?error=${encodeURIComponent(error.message)}`)
    }
  }

  // ==========================================================================
  // Account Management
  // ==========================================================================

  private async listAccounts(req: Request, res: Response) {
    try {
      const userId = req.query.userId as string

      const result = await this.postgres.query(
        `SELECT
          id, user_id, provider, email_address, display_name,
          auth_type, enabled, last_sync_at, sync_status,
          created_at, updated_at
         FROM email_accounts
         WHERE user_id = $1
         ORDER BY created_at DESC`,
        [userId]
      )

      res.json({ accounts: result.rows })
    } catch (error: any) {
      console.error('Failed to list accounts:', error)
      res.status(500).json({ error: error.message })
    }
  }

  private async createAccount(req: Request, res: Response) {
    try {
      const { userId, provider, emailAddress, host, port, username, password, tls } = req.body

      // Only IMAP accounts can be created via password
      if (provider !== 'imap') {
        return res.status(400).json({ error: 'Only IMAP accounts can be created with password' })
      }

      // Encrypt password (in production, use proper encryption)
      const encryptedPassword = Buffer.from(password).toString('base64')

      const result = await this.postgres.query(
        `INSERT INTO email_accounts
         (user_id, provider, email_address, auth_type, imap_host, imap_port, imap_username,
          imap_password, imap_tls, enabled)
         VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
         RETURNING id, email_address, provider`,
        [userId, 'imap', emailAddress, 'password', host, port, username, encryptedPassword, tls, true]
      )

      res.json({ account: result.rows[0] })
    } catch (error: any) {
      console.error('Failed to create account:', error)
      res.status(500).json({ error: error.message })
    }
  }

  private async getAccount(req: Request, res: Response) {
    try {
      const { id } = req.params
      const userId = req.query.userId as string

      const result = await this.postgres.query(
        `SELECT
          id, user_id, provider, email_address, display_name,
          auth_type, enabled, last_sync_at, sync_status,
          imap_host, imap_port, imap_username, imap_tls,
          created_at, updated_at
         FROM email_accounts
         WHERE id = $1 AND user_id = $2`,
        [id, userId]
      )

      if (result.rows.length === 0) {
        return res.status(404).json({ error: 'Account not found' })
      }

      res.json({ account: result.rows[0] })
    } catch (error: any) {
      console.error('Failed to get account:', error)
      res.status(500).json({ error: error.message })
    }
  }

  private async updateAccount(req: Request, res: Response) {
    try {
      const { id } = req.params
      const { displayName, enabled } = req.body
      const userId = req.query.userId as string

      const result = await this.postgres.query(
        `UPDATE email_accounts
         SET display_name = COALESCE($1, display_name),
             enabled = COALESCE($2, enabled),
             updated_at = NOW()
         WHERE id = $3 AND user_id = $4
         RETURNING id, email_address, display_name, enabled`,
        [displayName, enabled, id, userId]
      )

      if (result.rows.length === 0) {
        return res.status(404).json({ error: 'Account not found' })
      }

      res.json({ account: result.rows[0] })
    } catch (error: any) {
      console.error('Failed to update account:', error)
      res.status(500).json({ error: error.message })
    }
  }

  private async removeAccount(req: Request, res: Response) {
    try {
      const { id } = req.params
      const userId = req.query.userId as string

      // Delete account and all associated data (cascade)
      const result = await this.postgres.query(
        `DELETE FROM email_accounts
         WHERE id = $1 AND user_id = $2
         RETURNING id`,
        [id, userId]
      )

      if (result.rows.length === 0) {
        return res.status(404).json({ error: 'Account not found' })
      }

      res.json({ success: true, accountId: id })
    } catch (error: any) {
      console.error('Failed to remove account:', error)
      res.status(500).json({ error: error.message })
    }
  }

  private async syncAccount(req: Request, res: Response) {
    try {
      const { id } = req.params
      const userId = req.query.userId as string

      // Update sync status
      await this.postgres.query(
        `UPDATE email_accounts
         SET sync_status = 'syncing', updated_at = NOW()
         WHERE id = $1 AND user_id = $2`,
        [id, userId]
      )

      // Trigger sync in background (TODO: implement sync service)
      // For now, just return success
      res.json({ success: true, message: 'Sync started' })
    } catch (error: any) {
      console.error('Failed to sync account:', error)
      res.status(500).json({ error: error.message })
    }
  }

  private async getAccountStatus(req: Request, res: Response) {
    try {
      const { id } = req.params
      const userId = req.query.userId as string

      const result = await this.postgres.query(
        `SELECT sync_status, last_sync_at, sync_error
         FROM email_accounts
         WHERE id = $1 AND user_id = $2`,
        [id, userId]
      )

      if (result.rows.length === 0) {
        return res.status(404).json({ error: 'Account not found' })
      }

      // Get email counts
      const countsResult = await this.postgres.query(
        `SELECT
          COUNT(*) as total,
          COUNT(*) FILTER (WHERE is_read = false) as unread
         FROM emails
         WHERE account_id = $1`,
        [id]
      )

      res.json({
        status: result.rows[0],
        counts: countsResult.rows[0]
      })
    } catch (error: any) {
      console.error('Failed to get account status:', error)
      res.status(500).json({ error: error.message })
    }
  }

  // ==========================================================================
  // Calendar Management
  // ==========================================================================

  private async listCalendars(req: Request, res: Response) {
    try {
      const { id } = req.params
      const userId = req.query.userId as string

      // Verify account ownership
      const accountResult = await this.postgres.query(
        `SELECT id, provider FROM email_accounts WHERE id = $1 AND user_id = $2`,
        [id, userId]
      )

      if (accountResult.rows.length === 0) {
        return res.status(404).json({ error: 'Account not found' })
      }

      // Get calendars
      const result = await this.postgres.query(
        `SELECT
          c.id, c.provider_calendar_id, c.name, c.description,
          c.color, c.is_primary, c.is_writable, c.timezone
         FROM calendars c
         JOIN calendar_accounts ca ON c.account_id = ca.id
         WHERE ca.email_account_id = $1
         ORDER BY c.is_primary DESC, c.name`,
        [id]
      )

      res.json({ calendars: result.rows })
    } catch (error: any) {
      console.error('Failed to list calendars:', error)
      res.status(500).json({ error: error.message })
    }
  }

  private async syncCalendars(req: Request, res: Response) {
    try {
      const { id } = req.params
      const userId = req.query.userId as string

      // TODO: Implement calendar sync
      res.json({ success: true, message: 'Calendar sync not yet implemented' })
    } catch (error: any) {
      console.error('Failed to sync calendars:', error)
      res.status(500).json({ error: error.message })
    }
  }

  // ==========================================================================
  // Helper Methods
  // ==========================================================================

  private generateState(userId: string): string {
    // In production, use cryptographically secure random and store in Redis
    const state = Buffer.from(JSON.stringify({ userId, timestamp: Date.now() })).toString('base64')
    return state
  }

  private verifyState(state: string): string | null {
    try {
      const decoded = JSON.parse(Buffer.from(state, 'base64').toString())

      // Verify timestamp (max 10 minutes)
      if (Date.now() - decoded.timestamp > 10 * 60 * 1000) {
        return null
      }

      return decoded.userId
    } catch {
      return null
    }
  }

  getRouter(): Router {
    return this.router
  }
}
