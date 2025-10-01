/**
 * Bi-Directional Flag Synchronization Service
 *
 * Syncs email flags between our database and email providers (IMAP, Gmail, Exchange)
 * Ensures that changes in the web client reflect in the original email client and vice versa
 */

import { Pool } from 'pg'
import { GmailProvider } from '../providers/gmail-provider'
import { EmailAccount, EmailFlag, IEmailProvider } from '../providers/types'

interface FlagChange {
  emailId: number
  providerMessageId: string
  flags: EmailFlag
  source: 'user' | 'provider' | 'ai'
  timestamp: Date
}

export class FlagSyncService {
  private postgres: Pool
  private providers: Map<number, IEmailProvider> = new Map()

  constructor(postgres: Pool) {
    this.postgres = postgres
  }

  /**
   * Sync flags from provider to our database
   * Called during delta sync or webhook handling
   */
  async syncFlagsFromProvider(accountId: number, emailId: number): Promise<void> {
    try {
      // Get email and account info
      const emailResult = await this.postgres.query(
        `SELECT e.id, e.provider_message_id, e.is_read, e.is_flagged, e.is_answered
         FROM emails e
         WHERE e.id = $1 AND e.account_id = $2`,
        [emailId, accountId]
      )

      if (emailResult.rows.length === 0) {
        console.log(`Email ${emailId} not found in account ${accountId}`)
        return
      }

      const email = emailResult.rows[0]
      const provider = await this.getProvider(accountId)

      if (!provider) {
        console.error(`No provider available for account ${accountId}`)
        return
      }

      // Fetch current flags from provider
      const providerEmail = await provider.getEmail(email.provider_message_id)

      // Compare flags
      const changed = {
        isRead: providerEmail.isRead !== email.is_read,
        isFlagged: providerEmail.isFlagged !== email.is_flagged,
        isAnswered: providerEmail.isAnswered !== email.is_answered
      }

      if (changed.isRead || changed.isFlagged || changed.isAnswered) {
        // Update database with provider flags
        await this.postgres.query(
          `UPDATE emails
           SET is_read = $1,
               is_flagged = $2,
               is_answered = $3,
               provider_flags = $4,
               updated_at = NOW()
           WHERE id = $5`,
          [
            providerEmail.isRead,
            providerEmail.isFlagged,
            providerEmail.isAnswered,
            JSON.stringify(providerEmail.providerFlags),
            emailId
          ]
        )

        console.log(`Synced flags from provider for email ${emailId}:`, {
          isRead: providerEmail.isRead,
          isFlagged: providerEmail.isFlagged,
          isAnswered: providerEmail.isAnswered
        })
      }
    } catch (error: any) {
      console.error(`Failed to sync flags from provider for email ${emailId}:`, error.message)
    }
  }

  /**
   * Sync flags from our database to provider
   * Called when user changes flags in web client
   */
  async syncFlagsToProvider(accountId: number, emailId: number, flags: EmailFlag): Promise<void> {
    try {
      // Get email info
      const emailResult = await this.postgres.query(
        `SELECT e.id, e.provider_message_id
         FROM emails e
         WHERE e.id = $1 AND e.account_id = $2`,
        [emailId, accountId]
      )

      if (emailResult.rows.length === 0) {
        console.log(`Email ${emailId} not found in account ${accountId}`)
        return
      }

      const email = emailResult.rows[0]
      const provider = await this.getProvider(accountId)

      if (!provider) {
        console.error(`No provider available for account ${accountId}`)
        return
      }

      // Update flags on provider
      await provider.setFlag(email.provider_message_id, flags)

      // Update database
      const updateFields: string[] = []
      const updateValues: any[] = []
      let paramIndex = 1

      if (flags.seen !== undefined) {
        updateFields.push(`is_read = $${paramIndex++}`)
        updateValues.push(flags.seen)
      }

      if (flags.flagged !== undefined) {
        updateFields.push(`is_flagged = $${paramIndex++}`)
        updateValues.push(flags.flagged)
      }

      if (flags.answered !== undefined) {
        updateFields.push(`is_answered = $${paramIndex++}`)
        updateValues.push(flags.answered)
      }

      if (updateFields.length > 0) {
        updateFields.push(`updated_at = NOW()`)
        updateValues.push(emailId)

        await this.postgres.query(
          `UPDATE emails SET ${updateFields.join(', ')} WHERE id = $${paramIndex}`,
          updateValues
        )

        // Log the flag change
        await this.logFlagChange({
          emailId,
          providerMessageId: email.provider_message_id,
          flags,
          source: 'user',
          timestamp: new Date()
        })

        console.log(`Synced flags to provider for email ${emailId}:`, flags)
      }
    } catch (error: any) {
      console.error(`Failed to sync flags to provider for email ${emailId}:`, error.message)
    }
  }

  /**
   * Handle flag change from user action
   */
  async handleFlagChange(accountId: number, emailId: number, flags: EmailFlag): Promise<void> {
    await this.syncFlagsToProvider(accountId, emailId, flags)
  }

  /**
   * Batch sync flags for multiple emails
   * Used during initial sync or bulk operations
   */
  async batchSyncFlags(accountId: number, emailIds: number[]): Promise<void> {
    try {
      const provider = await this.getProvider(accountId)
      if (!provider) {
        console.error(`No provider available for account ${accountId}`)
        return
      }

      const capabilities = provider.getCapabilities()

      if (capabilities.supportsBatch) {
        // Use batch API if supported
        await this.batchSyncWithProvider(accountId, emailIds, provider)
      } else {
        // Sync one by one
        for (const emailId of emailIds) {
          await this.syncFlagsFromProvider(accountId, emailId)
        }
      }
    } catch (error: any) {
      console.error(`Failed to batch sync flags for account ${accountId}:`, error.message)
    }
  }

  /**
   * Handle webhook notification from provider
   * Provider detected flag changes, update our database
   */
  async handleWebhookNotification(accountId: number, changes: Array<{
    messageId: string
    flags: EmailFlag
  }>): Promise<void> {
    try {
      for (const change of changes) {
        // Find email by provider message ID
        const emailResult = await this.postgres.query(
          `SELECT id FROM emails
           WHERE account_id = $1 AND provider_message_id = $2`,
          [accountId, change.messageId]
        )

        if (emailResult.rows.length === 0) {
          console.log(`Email with provider ID ${change.messageId} not found`)
          continue
        }

        const emailId = emailResult.rows[0].id

        // Update flags in database
        const updateFields: string[] = []
        const updateValues: any[] = []
        let paramIndex = 1

        if (change.flags.seen !== undefined) {
          updateFields.push(`is_read = $${paramIndex++}`)
          updateValues.push(change.flags.seen)
        }

        if (change.flags.flagged !== undefined) {
          updateFields.push(`is_flagged = $${paramIndex++}`)
          updateValues.push(change.flags.flagged)
        }

        if (change.flags.answered !== undefined) {
          updateFields.push(`is_answered = $${paramIndex++}`)
          updateValues.push(change.flags.answered)
        }

        if (updateFields.length > 0) {
          updateFields.push(`updated_at = NOW()`)
          updateValues.push(emailId)

          await this.postgres.query(
            `UPDATE emails SET ${updateFields.join(', ')} WHERE id = $${paramIndex}`,
            updateValues
          )

          // Log the flag change
          await this.logFlagChange({
            emailId,
            providerMessageId: change.messageId,
            flags: change.flags,
            source: 'provider',
            timestamp: new Date()
          })

          console.log(`Updated flags from webhook for email ${emailId}:`, change.flags)
        }
      }
    } catch (error: any) {
      console.error(`Failed to handle webhook notification:`, error.message)
    }
  }

  /**
   * Periodic sync job - check for flag changes on provider
   * Runs every 5 minutes for accounts without webhooks
   */
  async periodicSync(accountId: number): Promise<void> {
    try {
      const provider = await this.getProvider(accountId)
      if (!provider) {
        console.error(`No provider available for account ${accountId}`)
        return
      }

      const capabilities = provider.getCapabilities()

      if (capabilities.supportsDeltaSync) {
        // Use delta sync if supported
        await this.deltaSyncFlags(accountId, provider)
      } else {
        // Fallback to checking recent emails
        await this.checkRecentEmails(accountId, provider)
      }
    } catch (error: any) {
      console.error(`Periodic sync failed for account ${accountId}:`, error.message)
    }
  }

  // ==========================================================================
  // Private Helper Methods
  // ==========================================================================

  private async getProvider(accountId: number): Promise<IEmailProvider | null> {
    // Check cache
    if (this.providers.has(accountId)) {
      return this.providers.get(accountId)!
    }

    // Load account from database
    const result = await this.postgres.query(
      `SELECT * FROM email_accounts WHERE id = $1 AND enabled = true`,
      [accountId]
    )

    if (result.rows.length === 0) {
      return null
    }

    const account: EmailAccount = {
      id: result.rows[0].id,
      userId: result.rows[0].user_id,
      provider: result.rows[0].provider,
      emailAddress: result.rows[0].email_address,
      displayName: result.rows[0].display_name,
      authType: result.rows[0].auth_type,
      accessToken: result.rows[0].access_token,
      refreshToken: result.rows[0].refresh_token,
      tokenExpiresAt: result.rows[0].token_expires_at,
      syncToken: result.rows[0].sync_token,
      lastSyncAt: result.rows[0].last_sync_at,
      enabled: result.rows[0].enabled,
      capabilities: {} as any, // Will be set by provider
      metadata: result.rows[0].metadata
    }

    // Create provider instance
    let provider: IEmailProvider | null = null

    if (account.provider === 'gmail') {
      const gmailProvider = new GmailProvider({
        clientId: process.env.GOOGLE_CLIENT_ID!,
        clientSecret: process.env.GOOGLE_CLIENT_SECRET!,
        redirectUri: process.env.GOOGLE_REDIRECT_URI!,
        scopes: ['https://www.googleapis.com/auth/gmail.modify']
      })

      await gmailProvider.initialize(account)
      provider = gmailProvider
    }
    // TODO: Add IMAP and Exchange providers

    if (provider) {
      this.providers.set(accountId, provider)
    }

    return provider
  }

  private async batchSyncWithProvider(
    accountId: number,
    emailIds: number[],
    provider: IEmailProvider
  ): Promise<void> {
    // Get emails
    const emailsResult = await this.postgres.query(
      `SELECT id, provider_message_id, is_read, is_flagged, is_answered
       FROM emails
       WHERE id = ANY($1) AND account_id = $2`,
      [emailIds, accountId]
    )

    const emails = emailsResult.rows

    // Fetch current state from provider
    for (const email of emails) {
      try {
        const providerEmail = await provider.getEmail(email.provider_message_id)

        // Check for changes
        if (
          providerEmail.isRead !== email.is_read ||
          providerEmail.isFlagged !== email.is_flagged ||
          providerEmail.isAnswered !== email.is_answered
        ) {
          await this.postgres.query(
            `UPDATE emails
             SET is_read = $1, is_flagged = $2, is_answered = $3, updated_at = NOW()
             WHERE id = $4`,
            [providerEmail.isRead, providerEmail.isFlagged, providerEmail.isAnswered, email.id]
          )
        }
      } catch (error: any) {
        console.error(`Failed to sync email ${email.id}:`, error.message)
      }
    }
  }

  private async deltaSyncFlags(accountId: number, provider: IEmailProvider): Promise<void> {
    // Get last sync token
    const accountResult = await this.postgres.query(
      `SELECT sync_token FROM email_accounts WHERE id = $1`,
      [accountId]
    )

    const syncToken = accountResult.rows[0]?.sync_token

    // Fetch delta
    const delta = await provider.getDelta(syncToken)

    // Update emails
    for (const email of delta.emails) {
      // Find corresponding email in database
      const dbEmailResult = await this.postgres.query(
        `SELECT id FROM emails
         WHERE account_id = $1 AND provider_message_id = $2`,
        [accountId, email.providerMessageId]
      )

      if (dbEmailResult.rows.length > 0) {
        const emailId = dbEmailResult.rows[0].id

        await this.postgres.query(
          `UPDATE emails
           SET is_read = $1, is_flagged = $2, is_answered = $3, updated_at = NOW()
           WHERE id = $4`,
          [email.isRead, email.isFlagged, email.isAnswered, emailId]
        )
      }
    }

    // Update sync token
    await this.postgres.query(
      `UPDATE email_accounts SET sync_token = $1, last_sync_at = NOW() WHERE id = $2`,
      [delta.syncToken, accountId]
    )
  }

  private async checkRecentEmails(accountId: number, provider: IEmailProvider): Promise<void> {
    // Get emails modified in last 15 minutes
    const recentResult = await this.postgres.query(
      `SELECT id, provider_message_id
       FROM emails
       WHERE account_id = $1
         AND updated_at > NOW() - INTERVAL '15 minutes'
       LIMIT 100`,
      [accountId]
    )

    for (const email of recentResult.rows) {
      await this.syncFlagsFromProvider(accountId, email.id)
    }
  }

  private async logFlagChange(change: FlagChange): Promise<void> {
    try {
      await this.postgres.query(
        `INSERT INTO email_actions
         (email_id, action_type, executed_by, metadata, created_at)
         VALUES ($1, $2, $3, $4, $5)`,
        [
          change.emailId,
          'flag_change',
          change.source,
          JSON.stringify({
            flags: change.flags,
            providerMessageId: change.providerMessageId
          }),
          change.timestamp
        ]
      )
    } catch (error: any) {
      console.error('Failed to log flag change:', error.message)
    }
  }
}
