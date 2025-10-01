/**
 * Webhook Handlers for Email Provider Notifications
 *
 * Handles push notifications from Gmail (Cloud Pub/Sub) and Exchange (Graph API)
 * for real-time email and calendar synchronization
 */

import { Router, Request, Response } from 'express'
import { Pool } from 'pg'
import { GmailProvider } from '../providers/gmail-provider'
import { FlagSyncService } from '../services/flag-sync'
import { OAuthCredentials } from '../providers/types'

export class WebhooksAPI {
  private router: Router
  private postgres: Pool
  private flagSync: FlagSyncService
  private gmailOAuthConfig: OAuthCredentials

  constructor(postgres: Pool, gmailOAuthConfig: OAuthCredentials) {
    this.router = Router()
    this.postgres = postgres
    this.flagSync = new FlagSyncService(postgres)
    this.gmailOAuthConfig = gmailOAuthConfig

    this.setupRoutes()
  }

  private setupRoutes() {
    /**
     * POST /api/webhooks/gmail
     * Handle Gmail push notifications via Cloud Pub/Sub
     */
    this.router.post('/gmail', this.handleGmailWebhook.bind(this))

    /**
     * POST /api/webhooks/exchange
     * Handle Exchange/Outlook notifications via Microsoft Graph webhooks
     */
    this.router.post('/exchange', this.handleExchangeWebhook.bind(this))

    /**
     * GET /api/webhooks/exchange
     * Validation endpoint for Microsoft Graph subscription
     */
    this.router.get('/exchange', this.validateExchangeWebhook.bind(this))
  }

  // ==========================================================================
  // Gmail Webhook Handler
  // ==========================================================================

  private async handleGmailWebhook(req: Request, res: Response) {
    try {
      // Gmail sends notifications via Cloud Pub/Sub
      const pubsubMessage = req.body

      if (!pubsubMessage || !pubsubMessage.message) {
        return res.status(400).json({ error: 'Invalid Pub/Sub message' })
      }

      // Decode base64 data
      const messageData = pubsubMessage.message.data
      const decodedData = Buffer.from(messageData, 'base64').toString('utf-8')
      const notification = JSON.parse(decodedData)

      console.log('Gmail webhook notification:', notification)

      // Notification format:
      // {
      //   emailAddress: "user@gmail.com",
      //   historyId: "123456"
      // }

      const { emailAddress, historyId } = notification

      // Find account by email address
      const accountResult = await this.postgres.query(
        `SELECT id, sync_token FROM email_accounts
         WHERE provider = 'gmail' AND email_address = $1 AND enabled = true`,
        [emailAddress]
      )

      if (accountResult.rows.length === 0) {
        console.log(`No account found for Gmail address: ${emailAddress}`)
        return res.status(200).json({ message: 'Account not found, skipping' })
      }

      const account = accountResult.rows[0]
      const accountId = account.id
      const lastHistoryId = account.sync_token

      // Fetch history changes since last sync
      await this.syncGmailHistory(accountId, lastHistoryId, historyId)

      // Update sync token
      await this.postgres.query(
        `UPDATE email_accounts
         SET sync_token = $1, last_sync_at = NOW()
         WHERE id = $2`,
        [historyId, accountId]
      )

      // Acknowledge the message
      res.status(200).json({ success: true })
    } catch (error: any) {
      console.error('Gmail webhook error:', error)
      res.status(500).json({ error: error.message })
    }
  }

  // ==========================================================================
  // Exchange Webhook Handler
  // ==========================================================================

  private async handleExchangeWebhook(req: Request, res: Response) {
    try {
      // Microsoft Graph sends notification with changes
      const notifications = req.body.value || []

      for (const notification of notifications) {
        console.log('Exchange webhook notification:', notification)

        // Notification format:
        // {
        //   subscriptionId: "...",
        //   clientState: "...",
        //   changeType: "created" | "updated" | "deleted",
        //   resource: "Users/{userId}/Messages/{messageId}",
        //   resourceData: { ... }
        // }

        const { subscriptionId, changeType, resource } = notification

        // Extract userId and messageId from resource
        const resourceMatch = resource.match(/Users\/(.+?)\/Messages\/(.+)/)
        if (!resourceMatch) {
          console.log('Invalid resource format:', resource)
          continue
        }

        const [, userId, messageId] = resourceMatch

        // Find account by user ID (stored in metadata)
        const accountResult = await this.postgres.query(
          `SELECT id FROM email_accounts
           WHERE provider = 'exchange'
             AND metadata->>'userId' = $1
             AND enabled = true`,
          [userId]
        )

        if (accountResult.rows.length === 0) {
          console.log(`No account found for Exchange user: ${userId}`)
          continue
        }

        const accountId = accountResult.rows[0].id

        // Handle different change types
        switch (changeType) {
          case 'created':
            await this.handleExchangeEmailCreated(accountId, messageId)
            break
          case 'updated':
            await this.handleExchangeEmailUpdated(accountId, messageId)
            break
          case 'deleted':
            await this.handleExchangeEmailDeleted(accountId, messageId)
            break
        }
      }

      res.status(200).json({ success: true })
    } catch (error: any) {
      console.error('Exchange webhook error:', error)
      res.status(500).json({ error: error.message })
    }
  }

  private async validateExchangeWebhook(req: Request, res: Response) {
    try {
      // Microsoft Graph sends validation token on subscription creation
      const validationToken = req.query.validationToken as string

      if (validationToken) {
        // Respond with the validation token
        return res.status(200).send(validationToken)
      }

      res.status(400).json({ error: 'Missing validation token' })
    } catch (error: any) {
      console.error('Exchange webhook validation error:', error)
      res.status(500).json({ error: error.message })
    }
  }

  // ==========================================================================
  // Gmail Sync Methods
  // ==========================================================================

  private async syncGmailHistory(
    accountId: number,
    startHistoryId: string,
    endHistoryId: string
  ): Promise<void> {
    try {
      // Get account details
      const accountResult = await this.postgres.query(
        `SELECT * FROM email_accounts WHERE id = $1`,
        [accountId]
      )

      if (accountResult.rows.length === 0) {
        throw new Error(`Account ${accountId} not found`)
      }

      const account = accountResult.rows[0]

      // Initialize Gmail provider
      const gmailProvider = new GmailProvider(this.gmailOAuthConfig)
      await gmailProvider.initialize({
        id: account.id,
        userId: account.user_id,
        provider: 'gmail',
        emailAddress: account.email_address,
        authType: 'oauth',
        accessToken: account.access_token,
        refreshToken: account.refresh_token,
        tokenExpiresAt: account.token_expires_at,
        syncToken: startHistoryId,
        enabled: true,
        capabilities: gmailProvider.getCapabilities()
      })

      // Fetch delta changes
      const delta = await gmailProvider.getDelta(startHistoryId)

      console.log(`Gmail history sync: ${delta.emails.length} changes detected`)

      // Process each email change
      for (const email of delta.emails) {
        // Check if email exists
        const existingEmail = await this.postgres.query(
          `SELECT id FROM emails
           WHERE account_id = $1 AND provider_message_id = $2`,
          [accountId, email.providerMessageId]
        )

        if (existingEmail.rows.length > 0) {
          // Update existing email
          const emailId = existingEmail.rows[0].id

          await this.postgres.query(
            `UPDATE emails
             SET is_read = $1,
                 is_flagged = $2,
                 is_answered = $3,
                 provider_flags = $4,
                 updated_at = NOW()
             WHERE id = $5`,
            [
              email.isRead,
              email.isFlagged,
              email.isAnswered,
              JSON.stringify(email.providerFlags),
              emailId
            ]
          )

          console.log(`Updated email ${emailId} from Gmail history`)
        } else {
          // Insert new email
          await this.insertEmail(accountId, email)
        }
      }
    } catch (error: any) {
      console.error('Failed to sync Gmail history:', error)
      throw error
    }
  }

  // ==========================================================================
  // Exchange Sync Methods
  // ==========================================================================

  private async handleExchangeEmailCreated(accountId: number, messageId: string): Promise<void> {
    try {
      console.log(`Exchange email created: ${messageId}`)

      // TODO: Fetch email from Exchange API and insert into database
      // This requires ExchangeProvider implementation
    } catch (error: any) {
      console.error('Failed to handle Exchange email created:', error)
    }
  }

  private async handleExchangeEmailUpdated(accountId: number, messageId: string): Promise<void> {
    try {
      console.log(`Exchange email updated: ${messageId}`)

      // Find email in database
      const emailResult = await this.postgres.query(
        `SELECT id FROM emails
         WHERE account_id = $1 AND provider_message_id = $2`,
        [accountId, messageId]
      )

      if (emailResult.rows.length === 0) {
        console.log(`Email ${messageId} not found, skipping update`)
        return
      }

      const emailId = emailResult.rows[0].id

      // TODO: Fetch updated email from Exchange API and update database
      // For now, just trigger flag sync
      await this.flagSync.syncFlagsFromProvider(accountId, emailId)
    } catch (error: any) {
      console.error('Failed to handle Exchange email updated:', error)
    }
  }

  private async handleExchangeEmailDeleted(accountId: number, messageId: string): Promise<void> {
    try {
      console.log(`Exchange email deleted: ${messageId}`)

      // Soft delete in database
      await this.postgres.query(
        `UPDATE emails
         SET is_deleted = true, updated_at = NOW()
         WHERE account_id = $1 AND provider_message_id = $2`,
        [accountId, messageId]
      )
    } catch (error: any) {
      console.error('Failed to handle Exchange email deleted:', error)
    }
  }

  // ==========================================================================
  // Helper Methods
  // ==========================================================================

  private async insertEmail(accountId: number, email: any): Promise<void> {
    try {
      const result = await this.postgres.query(
        `INSERT INTO emails (
          account_id, provider_message_id, provider_thread_id,
          subject, from_address, from_name,
          to_addresses, cc_addresses, bcc_addresses,
          body_text, body_html, received_at,
          is_read, is_flagged, is_answered, is_draft,
          has_attachments, provider_flags, headers
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19)
        RETURNING id`,
        [
          accountId,
          email.providerMessageId,
          email.providerThreadId,
          email.subject,
          email.fromAddress,
          email.fromName,
          JSON.stringify(email.toAddresses),
          JSON.stringify(email.ccAddresses || []),
          JSON.stringify(email.bccAddresses || []),
          email.bodyText,
          email.bodyHtml,
          email.receivedAt,
          email.isRead,
          email.isFlagged,
          email.isAnswered,
          email.isDraft,
          email.hasAttachments,
          JSON.stringify(email.providerFlags),
          JSON.stringify(email.headers)
        ]
      )

      console.log(`Inserted new email ${result.rows[0].id}`)
    } catch (error: any) {
      console.error('Failed to insert email:', error)
      throw error
    }
  }

  getRouter(): Router {
    return this.router
  }
}
