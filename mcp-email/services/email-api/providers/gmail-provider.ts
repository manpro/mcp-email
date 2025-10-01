/**
 * Gmail API Provider Implementation
 *
 * Uses Google APIs client library for Gmail and Calendar integration
 * Supports OAuth 2.0, delta sync, batch operations, and webhooks
 */

import { google, gmail_v1, Auth } from 'googleapis'
import {
  IEmailProvider,
  EmailAccount,
  Email,
  EmailAttachment,
  EmailLabel,
  EmailFlag,
  FetchOptions,
  DeltaResponse,
  BatchUpdate,
  BatchResult,
  ProviderCredentials,
  AuthToken,
  ProviderCapabilities,
  OAuthCredentials
} from './types'

export class GmailProvider implements IEmailProvider {
  private gmail: gmail_v1.Gmail | null = null
  private oauth2Client: Auth.OAuth2Client | null = null
  private account: EmailAccount | null = null

  constructor(private oauthConfig: OAuthCredentials) {}

  async initialize(account: EmailAccount): Promise<void> {
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
        console.log('Gmail tokens refreshed:', {
          accountId: account.id,
          expiresIn: tokens.expiry_date
        })
        // TODO: Update database with new tokens
      })
    }

    // Initialize Gmail client
    this.gmail = google.gmail({ version: 'v1', auth: this.oauth2Client })
  }

  async authenticate(credentials: ProviderCredentials): Promise<AuthToken> {
    if (!this.oauth2Client) {
      throw new Error('OAuth2 client not initialized')
    }

    if (credentials.authCode) {
      // Exchange authorization code for tokens
      const { tokens } = await this.oauth2Client.getToken(credentials.authCode)
      this.oauth2Client.setCredentials(tokens)

      return {
        accessToken: tokens.access_token!,
        refreshToken: tokens.refresh_token,
        expiresAt: new Date(tokens.expiry_date!),
        tokenType: tokens.token_type!,
        scope: tokens.scope
      }
    } else if (credentials.accessToken && credentials.refreshToken) {
      // Use existing tokens
      this.oauth2Client.setCredentials({
        access_token: credentials.accessToken,
        refresh_token: credentials.refreshToken
      })

      return {
        accessToken: credentials.accessToken,
        refreshToken: credentials.refreshToken,
        expiresAt: new Date(Date.now() + 3600 * 1000), // Assume 1 hour
        tokenType: 'Bearer'
      }
    }

    throw new Error('Invalid credentials: authCode or tokens required')
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

  getCapabilities(): ProviderCapabilities {
    return {
      supportsThreading: true,
      supportsLabels: true,
      supportsFolders: false,
      supportsFlags: true,
      supportsSearch: true,
      supportsBatch: true,
      supportsWebhooks: true,
      supportsDeltaSync: true,
      supportsCalendar: true,
      maxBatchSize: 1000,
      rateLimitPerSecond: 250
    }
  }

  async fetchEmails(options: FetchOptions): Promise<Email[]> {
    if (!this.gmail) throw new Error('Gmail client not initialized')

    const query = this.buildQuery(options)
    const response = await this.gmail.users.messages.list({
      userId: 'me',
      q: query,
      maxResults: options.limit || 100,
      labelIds: options.labelId ? [options.labelId] : undefined
    })

    const messages = response.data.messages || []
    const emails: Email[] = []

    // Batch fetch full message details
    for (const msg of messages) {
      if (!msg.id) continue

      try {
        const email = await this.getEmail(msg.id)
        emails.push(email)
      } catch (error) {
        console.error(`Failed to fetch message ${msg.id}:`, error)
      }
    }

    return emails
  }

  async getDelta(syncToken?: string): Promise<DeltaResponse> {
    if (!this.gmail) throw new Error('Gmail client not initialized')

    if (syncToken) {
      // Use History API for delta sync
      const historyId = syncToken
      const response = await this.gmail.users.history.list({
        userId: 'me',
        startHistoryId: historyId,
        historyTypes: ['messageAdded', 'messageDeleted', 'labelAdded', 'labelRemoved']
      })

      const emails: Email[] = []
      const history = response.data.history || []

      for (const item of history) {
        // Process added messages
        if (item.messagesAdded) {
          for (const added of item.messagesAdded) {
            if (added.message?.id) {
              try {
                const email = await this.getEmail(added.message.id)
                emails.push(email)
              } catch (error) {
                console.error(`Failed to fetch added message ${added.message.id}:`, error)
              }
            }
          }
        }
      }

      return {
        emails,
        syncToken: response.data.historyId?.toString() || syncToken,
        hasMore: false
      }
    } else {
      // Initial sync - fetch recent emails
      const emails = await this.fetchEmails({ limit: 100 })

      // Get current historyId
      const profile = await this.gmail.users.getProfile({ userId: 'me' })

      return {
        emails,
        syncToken: profile.data.historyId?.toString() || '',
        hasMore: emails.length === 100
      }
    }
  }

  async getEmail(emailId: string): Promise<Email> {
    if (!this.gmail) throw new Error('Gmail client not initialized')

    const response = await this.gmail.users.messages.get({
      userId: 'me',
      id: emailId,
      format: 'full'
    })

    const msg = response.data
    return this.transformMessage(msg)
  }

  async setFlag(emailId: string, flag: EmailFlag): Promise<void> {
    if (!this.gmail) throw new Error('Gmail client not initialized')

    const addLabels: string[] = []
    const removeLabels: string[] = []

    if (flag.seen !== undefined) {
      if (flag.seen) {
        removeLabels.push('UNREAD')
      } else {
        addLabels.push('UNREAD')
      }
    }

    if (flag.flagged !== undefined) {
      if (flag.flagged) {
        addLabels.push('STARRED')
      } else {
        removeLabels.push('STARRED')
      }
    }

    if (addLabels.length > 0 || removeLabels.length > 0) {
      await this.gmail.users.messages.modify({
        userId: 'me',
        id: emailId,
        requestBody: {
          addLabelIds: addLabels.length > 0 ? addLabels : undefined,
          removeLabelIds: removeLabels.length > 0 ? removeLabels : undefined
        }
      })
    }
  }

  async addLabel(emailId: string, labelId: string): Promise<void> {
    if (!this.gmail) throw new Error('Gmail client not initialized')

    await this.gmail.users.messages.modify({
      userId: 'me',
      id: emailId,
      requestBody: {
        addLabelIds: [labelId]
      }
    })
  }

  async removeLabel(emailId: string, labelId: string): Promise<void> {
    if (!this.gmail) throw new Error('Gmail client not initialized')

    await this.gmail.users.messages.modify({
      userId: 'me',
      id: emailId,
      requestBody: {
        removeLabelIds: [labelId]
      }
    })
  }

  async moveToFolder(emailId: string, folderId: string): Promise<void> {
    // Gmail doesn't have folders, treat as label
    await this.addLabel(emailId, folderId)
  }

  async archive(emailId: string): Promise<void> {
    await this.removeLabel(emailId, 'INBOX')
  }

  async delete(emailId: string): Promise<void> {
    await this.addLabel(emailId, 'TRASH')
  }

  async permanentDelete(emailId: string): Promise<void> {
    if (!this.gmail) throw new Error('Gmail client not initialized')

    await this.gmail.users.messages.delete({
      userId: 'me',
      id: emailId
    })
  }

  async batchUpdate(updates: BatchUpdate[]): Promise<BatchResult> {
    if (!this.gmail) throw new Error('Gmail client not initialized')

    const results: BatchResult['results'] = []

    // Gmail supports batch modify
    const batchRequests = new Map<string, { add: string[], remove: string[] }>()

    for (const update of updates) {
      const batch = batchRequests.get(update.emailId) || { add: [], remove: [] }

      switch (update.operation) {
        case 'read':
          batch.remove.push('UNREAD')
          break
        case 'unread':
          batch.add.push('UNREAD')
          break
        case 'flag':
          batch.add.push('STARRED')
          break
        case 'unflag':
          batch.remove.push('STARRED')
          break
        case 'archive':
          batch.remove.push('INBOX')
          break
        case 'delete':
          batch.add.push('TRASH')
          break
        case 'addLabel':
          if (update.value) batch.add.push(update.value)
          break
        case 'removeLabel':
          if (update.value) batch.remove.push(update.value)
          break
      }

      batchRequests.set(update.emailId, batch)
    }

    // Execute batch modifications
    for (const [emailId, { add, remove }] of batchRequests) {
      try {
        await this.gmail.users.messages.modify({
          userId: 'me',
          id: emailId,
          requestBody: {
            addLabelIds: add.length > 0 ? add : undefined,
            removeLabelIds: remove.length > 0 ? remove : undefined
          }
        })
        results.push({ emailId, success: true })
      } catch (error: any) {
        results.push({ emailId, success: false, error: error.message })
      }
    }

    return {
      success: results.every(r => r.success),
      results
    }
  }

  async search(query: string, options?: FetchOptions): Promise<Email[]> {
    return this.fetchEmails({ ...options, query })
  }

  async getLabels(): Promise<EmailLabel[]> {
    if (!this.gmail) throw new Error('Gmail client not initialized')

    const response = await this.gmail.users.labels.list({
      userId: 'me'
    })

    const labels = response.data.labels || []
    return labels.map(label => ({
      id: 0, // Will be assigned by database
      accountId: this.account?.id || 0,
      providerLabelId: label.id,
      name: label.name || '',
      displayName: label.name || '',
      labelType: label.type === 'system' ? 'system' : 'user',
      color: label.color?.backgroundColor,
      icon: this.getLabelIcon(label.name || ''),
      policy: {}
    }))
  }

  async createLabel(name: string, parent?: string): Promise<EmailLabel> {
    if (!this.gmail) throw new Error('Gmail client not initialized')

    const response = await this.gmail.users.labels.create({
      userId: 'me',
      requestBody: {
        name,
        labelListVisibility: 'labelShow',
        messageListVisibility: 'show'
      }
    })

    return {
      id: 0,
      accountId: this.account?.id || 0,
      providerLabelId: response.data.id,
      name: response.data.name || '',
      displayName: response.data.name || '',
      labelType: 'user',
      policy: {}
    }
  }

  async setupWebhook(webhookUrl: string): Promise<{ webhookId: string }> {
    if (!this.gmail) throw new Error('Gmail client not initialized')

    // Gmail uses Cloud Pub/Sub for push notifications
    // This requires a GCP project with Pub/Sub enabled
    const response = await this.gmail.users.watch({
      userId: 'me',
      requestBody: {
        topicName: 'projects/YOUR_PROJECT_ID/topics/gmail-notifications',
        labelIds: ['INBOX']
      }
    })

    return {
      webhookId: response.data.historyId?.toString() || ''
    }
  }

  async stopWebhook(webhookId: string): Promise<void> {
    if (!this.gmail) throw new Error('Gmail client not initialized')

    await this.gmail.users.stop({
      userId: 'me'
    })
  }

  verifyWebhook(payload: any, signature: string): boolean {
    // Gmail webhooks are authenticated via GCP Pub/Sub
    // Signature verification happens at Pub/Sub level
    return true
  }

  async sendEmail(email: {
    to: string[]
    cc?: string[]
    bcc?: string[]
    subject: string
    bodyText?: string
    bodyHtml?: string
    attachments?: Array<{ filename: string, content: Buffer, mimeType: string }>
    inReplyTo?: string
    threadId?: string
  }): Promise<{ messageId: string }> {
    if (!this.gmail) throw new Error('Gmail client not initialized')

    const rawMessage = this.createMimeMessage(email)
    const encodedMessage = Buffer.from(rawMessage).toString('base64url')

    const response = await this.gmail.users.messages.send({
      userId: 'me',
      requestBody: {
        raw: encodedMessage,
        threadId: email.threadId
      }
    })

    return { messageId: response.data.id || '' }
  }

  async reply(emailId: string, bodyText: string, bodyHtml?: string): Promise<{ messageId: string }> {
    const original = await this.getEmail(emailId)

    return this.sendEmail({
      to: [original.fromAddress],
      subject: `Re: ${original.subject}`,
      bodyText,
      bodyHtml,
      inReplyTo: original.providerMessageId,
      threadId: original.providerThreadId
    })
  }

  async forward(emailId: string, to: string[], bodyText?: string): Promise<{ messageId: string }> {
    const original = await this.getEmail(emailId)

    return this.sendEmail({
      to,
      subject: `Fwd: ${original.subject}`,
      bodyText: bodyText || original.bodyText || '',
      bodyHtml: original.bodyHtml
    })
  }

  async createDraft(email: {
    to: string[]
    subject: string
    bodyText?: string
    bodyHtml?: string
  }): Promise<{ draftId: string }> {
    if (!this.gmail) throw new Error('Gmail client not initialized')

    const rawMessage = this.createMimeMessage(email)
    const encodedMessage = Buffer.from(rawMessage).toString('base64url')

    const response = await this.gmail.users.drafts.create({
      userId: 'me',
      requestBody: {
        message: {
          raw: encodedMessage
        }
      }
    })

    return { draftId: response.data.id || '' }
  }

  async updateDraft(draftId: string, email: any): Promise<void> {
    if (!this.gmail) throw new Error('Gmail client not initialized')

    const rawMessage = this.createMimeMessage(email)
    const encodedMessage = Buffer.from(rawMessage).toString('base64url')

    await this.gmail.users.drafts.update({
      userId: 'me',
      id: draftId,
      requestBody: {
        message: {
          raw: encodedMessage
        }
      }
    })
  }

  async sendDraft(draftId: string): Promise<{ messageId: string }> {
    if (!this.gmail) throw new Error('Gmail client not initialized')

    const response = await this.gmail.users.drafts.send({
      userId: 'me',
      requestBody: {
        id: draftId
      }
    })

    return { messageId: response.data.id || '' }
  }

  async disconnect(): Promise<void> {
    this.gmail = null
    this.oauth2Client = null
  }

  // ============================================================================
  // Helper Methods
  // ============================================================================

  private transformMessage(msg: gmail_v1.Schema$Message): Email {
    const headers = msg.payload?.headers || []
    const getHeader = (name: string) => headers.find(h => h.name?.toLowerCase() === name.toLowerCase())?.value || ''

    const email: Email = {
      id: 0, // Will be assigned by database
      accountId: this.account?.id || 0,
      providerMessageId: msg.id || '',
      providerThreadId: msg.threadId,
      subject: getHeader('subject'),
      fromAddress: this.extractEmail(getHeader('from')),
      fromName: this.extractName(getHeader('from')),
      toAddresses: this.parseAddresses(getHeader('to')),
      ccAddresses: this.parseAddresses(getHeader('cc')),
      bccAddresses: this.parseAddresses(getHeader('bcc')),
      bodyText: this.extractBody(msg, 'text/plain'),
      bodyHtml: this.extractBody(msg, 'text/html'),
      receivedAt: new Date(parseInt(msg.internalDate || '0')),
      isRead: !msg.labelIds?.includes('UNREAD'),
      isFlagged: msg.labelIds?.includes('STARRED') || false,
      isAnswered: false, // Gmail doesn't have answered flag in labelIds
      isDraft: msg.labelIds?.includes('DRAFT') || false,
      hasAttachments: this.hasAttachments(msg),
      attachments: this.extractAttachments(msg),
      providerFlags: { labelIds: msg.labelIds },
      headers: Object.fromEntries(headers.map(h => [h.name || '', h.value || '']))
    }

    return email
  }

  private buildQuery(options: FetchOptions): string {
    const parts: string[] = []

    if (options.query) {
      parts.push(options.query)
    }

    if (options.since) {
      const timestamp = Math.floor(options.since.getTime() / 1000)
      parts.push(`after:${timestamp}`)
    }

    return parts.join(' ')
  }

  private extractBody(msg: gmail_v1.Schema$Message, mimeType: string): string | undefined {
    const findPart = (parts: gmail_v1.Schema$MessagePart[] | undefined): string | undefined => {
      if (!parts) return undefined

      for (const part of parts) {
        if (part.mimeType === mimeType && part.body?.data) {
          return Buffer.from(part.body.data, 'base64').toString('utf-8')
        }
        if (part.parts) {
          const result = findPart(part.parts)
          if (result) return result
        }
      }
      return undefined
    }

    return findPart([msg.payload!])
  }

  private hasAttachments(msg: gmail_v1.Schema$Message): boolean {
    const checkParts = (parts: gmail_v1.Schema$MessagePart[] | undefined): boolean => {
      if (!parts) return false
      return parts.some(part => part.filename && part.filename.length > 0)
    }
    return checkParts([msg.payload!])
  }

  private extractAttachments(msg: gmail_v1.Schema$Message): EmailAttachment[] {
    const attachments: EmailAttachment[] = []

    const extractFromParts = (parts: gmail_v1.Schema$MessagePart[] | undefined) => {
      if (!parts) return

      for (const part of parts) {
        if (part.filename && part.filename.length > 0 && part.body?.attachmentId) {
          attachments.push({
            id: part.body.attachmentId,
            filename: part.filename,
            mimeType: part.mimeType || 'application/octet-stream',
            size: part.body.size || 0,
            isInline: false
          })
        }
        if (part.parts) {
          extractFromParts(part.parts)
        }
      }
    }

    extractFromParts([msg.payload!])
    return attachments
  }

  private extractEmail(address: string): string {
    const match = address.match(/<(.+?)>/)
    return match ? match[1] : address
  }

  private extractName(address: string): string | undefined {
    const match = address.match(/^(.+?)\s*</)
    return match ? match[1].replace(/"/g, '') : undefined
  }

  private parseAddresses(addressString: string): string[] {
    if (!addressString) return []
    return addressString.split(',').map(addr => this.extractEmail(addr.trim()))
  }

  private getLabelIcon(labelName: string): string {
    const iconMap: Record<string, string> = {
      'INBOX': '📥',
      'SENT': '📤',
      'DRAFT': '✏️',
      'TRASH': '🗑️',
      'SPAM': '⚠️',
      'STARRED': '⭐',
      'IMPORTANT': '🔴'
    }
    return iconMap[labelName] || '🏷️'
  }

  private createMimeMessage(email: {
    to: string[]
    cc?: string[]
    bcc?: string[]
    subject: string
    bodyText?: string
    bodyHtml?: string
    inReplyTo?: string
  }): string {
    const lines: string[] = []

    lines.push(`To: ${email.to.join(', ')}`)
    if (email.cc && email.cc.length > 0) {
      lines.push(`Cc: ${email.cc.join(', ')}`)
    }
    if (email.bcc && email.bcc.length > 0) {
      lines.push(`Bcc: ${email.bcc.join(', ')}`)
    }
    lines.push(`Subject: ${email.subject}`)
    if (email.inReplyTo) {
      lines.push(`In-Reply-To: ${email.inReplyTo}`)
    }
    lines.push('MIME-Version: 1.0')

    if (email.bodyHtml) {
      lines.push('Content-Type: multipart/alternative; boundary="boundary123"')
      lines.push('')
      lines.push('--boundary123')
      lines.push('Content-Type: text/plain; charset="UTF-8"')
      lines.push('')
      lines.push(email.bodyText || '')
      lines.push('')
      lines.push('--boundary123')
      lines.push('Content-Type: text/html; charset="UTF-8"')
      lines.push('')
      lines.push(email.bodyHtml)
      lines.push('')
      lines.push('--boundary123--')
    } else {
      lines.push('Content-Type: text/plain; charset="UTF-8"')
      lines.push('')
      lines.push(email.bodyText || '')
    }

    return lines.join('\r\n')
  }
}
