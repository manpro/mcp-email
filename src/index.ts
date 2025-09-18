#!/usr/bin/env node

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
  Tool,
} from '@modelcontextprotocol/sdk/types.js';

import { ImapEmailClient, EmailMessage } from './imap-client.js';
import { createImapConfig, EmailProviders, detectProvider } from './email-providers.js';

class EmailMCPServer {
  private server: Server;
  private clients: Map<string, ImapEmailClient> = new Map();

  constructor() {
    this.server = new Server(
      {
        name: 'email-server',
        version: '1.0.0',
      },
      {
        capabilities: {
          tools: {},
        },
      }
    );

    this.setupToolHandlers();
    this.setupErrorHandling();
  }

  private setupErrorHandling(): void {
    this.server.onerror = (error) => {
      console.error('[MCP Error]', error);
    };

    process.on('SIGINT', async () => {
      await this.cleanup();
      process.exit(0);
    });
  }

  private async cleanup(): Promise<void> {
    for (const client of this.clients.values()) {
      await client.disconnect();
    }
    this.clients.clear();
  }

  private setupToolHandlers(): void {
    this.server.setRequestHandler(ListToolsRequestSchema, async () => {
      return {
        tools: [
          {
            name: 'connect_email',
            description: 'Connect to an email account via IMAP',
            inputSchema: {
              type: 'object',
              properties: {
                connectionId: {
                  type: 'string',
                  description: 'Unique identifier for this connection',
                },
                email: {
                  type: 'string',
                  description: 'Email address',
                },
                password: {
                  type: 'string',
                  description: 'Email password or app password',
                },
                provider: {
                  type: 'string',
                  description: 'Email provider (outlook, exchangeOnline, exchangeOnPremise, gmail, generic)',
                  enum: Object.keys(EmailProviders),
                },
                customHost: {
                  type: 'string',
                  description: 'Custom IMAP host (optional)',
                },
                customPort: {
                  type: 'number',
                  description: 'Custom IMAP port (optional, default: 993)',
                },
              },
              required: ['connectionId', 'email', 'password'],
            },
          },
          {
            name: 'list_mailboxes',
            description: 'List all mailboxes/folders in the email account',
            inputSchema: {
              type: 'object',
              properties: {
                connectionId: {
                  type: 'string',
                  description: 'Connection identifier',
                },
              },
              required: ['connectionId'],
            },
          },
          {
            name: 'get_recent_emails',
            description: 'Get recent emails from a mailbox',
            inputSchema: {
              type: 'object',
              properties: {
                connectionId: {
                  type: 'string',
                  description: 'Connection identifier',
                },
                mailbox: {
                  type: 'string',
                  description: 'Mailbox name (default: INBOX)',
                  default: 'INBOX',
                },
                count: {
                  type: 'number',
                  description: 'Number of emails to retrieve (default: 10)',
                  default: 10,
                },
              },
              required: ['connectionId'],
            },
          },
          {
            name: 'search_emails',
            description: 'Search for emails based on criteria',
            inputSchema: {
              type: 'object',
              properties: {
                connectionId: {
                  type: 'string',
                  description: 'Connection identifier',
                },
                mailbox: {
                  type: 'string',
                  description: 'Mailbox name (default: INBOX)',
                  default: 'INBOX',
                },
                criteria: {
                  type: 'array',
                  description: 'IMAP search criteria (e.g., ["FROM", "example@email.com"])',
                  items: {
                    type: 'string',
                  },
                },
                limit: {
                  type: 'number',
                  description: 'Maximum number of emails to return (default: 20)',
                  default: 20,
                },
              },
              required: ['connectionId', 'criteria'],
            },
          },
          {
            name: 'get_email_details',
            description: 'Get detailed information about specific emails',
            inputSchema: {
              type: 'object',
              properties: {
                connectionId: {
                  type: 'string',
                  description: 'Connection identifier',
                },
                mailbox: {
                  type: 'string',
                  description: 'Mailbox name (default: INBOX)',
                  default: 'INBOX',
                },
                uids: {
                  type: 'array',
                  description: 'Array of email UIDs to fetch',
                  items: {
                    type: 'number',
                  },
                },
              },
              required: ['connectionId', 'uids'],
            },
          },
          {
            name: 'disconnect_email',
            description: 'Disconnect from an email account',
            inputSchema: {
              type: 'object',
              properties: {
                connectionId: {
                  type: 'string',
                  description: 'Connection identifier',
                },
              },
              required: ['connectionId'],
            },
          },
          {
            name: 'list_providers',
            description: 'List available email providers and their configurations',
            inputSchema: {
              type: 'object',
              properties: {},
            },
          },
        ] as Tool[],
      };
    });

    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      const { name, arguments: args } = request.params;

      try {
        switch (name) {
          case 'connect_email':
            return await this.handleConnectEmail(args);
          case 'list_mailboxes':
            return await this.handleListMailboxes(args);
          case 'get_recent_emails':
            return await this.handleGetRecentEmails(args);
          case 'search_emails':
            return await this.handleSearchEmails(args);
          case 'get_email_details':
            return await this.handleGetEmailDetails(args);
          case 'disconnect_email':
            return await this.handleDisconnectEmail(args);
          case 'list_providers':
            return await this.handleListProviders();
          default:
            throw new Error(`Unknown tool: ${name}`);
        }
      } catch (error) {
        return {
          content: [
            {
              type: 'text',
              text: `Error: ${error instanceof Error ? error.message : String(error)}`,
            },
          ],
        };
      }
    });
  }

  private async handleConnectEmail(args: any) {
    const { connectionId, email, password, provider, customHost, customPort } = args;

    try {
      const config = createImapConfig(email, password, provider, customHost, customPort);
      const client = new ImapEmailClient(config);
      
      await client.connect();
      this.clients.set(connectionId, client);

      const detectedProvider = provider || detectProvider(email);
      const providerInfo = EmailProviders[detectedProvider] || EmailProviders.generic;

      return {
        content: [
          {
            type: 'text',
            text: `Successfully connected to ${email} using ${providerInfo.name} (${config.host}:${config.port})`,
          },
        ],
      };
    } catch (error) {
      throw new Error(`Failed to connect: ${error instanceof Error ? error.message : String(error)}`);
    }
  }

  private async handleListMailboxes(args: any) {
    const { connectionId } = args;
    const client = this.clients.get(connectionId);

    if (!client) {
      throw new Error(`No connection found for ID: ${connectionId}`);
    }

    try {
      const mailboxes = await client.getMailboxes();
      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify(mailboxes, null, 2),
          },
        ],
      };
    } catch (error) {
      throw new Error(`Failed to list mailboxes: ${error instanceof Error ? error.message : String(error)}`);
    }
  }

  private async handleGetRecentEmails(args: any) {
    const { connectionId, mailbox = 'INBOX', count = 10 } = args;
    const client = this.clients.get(connectionId);

    if (!client) {
      throw new Error(`No connection found for ID: ${connectionId}`);
    }

    try {
      const emails = await client.getRecentEmails(count, mailbox);
      const emailSummary = emails.map(email => ({
        uid: email.uid,
        subject: email.subject,
        from: email.from,
        date: email.date,
        flags: email.flags,
        hasAttachments: (email.attachments?.length || 0) > 0,
        bodyPreview: email.bodyText?.substring(0, 200) + (email.bodyText && email.bodyText.length > 200 ? '...' : ''),
      }));

      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify(emailSummary, null, 2),
          },
        ],
      };
    } catch (error) {
      throw new Error(`Failed to get recent emails: ${error instanceof Error ? error.message : String(error)}`);
    }
  }

  private async handleSearchEmails(args: any) {
    const { connectionId, mailbox = 'INBOX', criteria, limit = 20 } = args;
    const client = this.clients.get(connectionId);

    if (!client) {
      throw new Error(`No connection found for ID: ${connectionId}`);
    }

    try {
      const uids = await client.searchEmails(criteria, mailbox);
      const limitedUids = uids.slice(-limit);
      const emails = await client.fetchEmails(limitedUids, mailbox);
      
      const emailSummary = emails.map(email => ({
        uid: email.uid,
        subject: email.subject,
        from: email.from,
        date: email.date,
        flags: email.flags,
        hasAttachments: (email.attachments?.length || 0) > 0,
        bodyPreview: email.bodyText?.substring(0, 200) + (email.bodyText && email.bodyText.length > 200 ? '...' : ''),
      }));

      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify(emailSummary, null, 2),
          },
        ],
      };
    } catch (error) {
      throw new Error(`Failed to search emails: ${error instanceof Error ? error.message : String(error)}`);
    }
  }

  private async handleGetEmailDetails(args: any) {
    const { connectionId, mailbox = 'INBOX', uids } = args;
    const client = this.clients.get(connectionId);

    if (!client) {
      throw new Error(`No connection found for ID: ${connectionId}`);
    }

    try {
      const emails = await client.fetchEmails(uids, mailbox);
      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify(emails, null, 2),
          },
        ],
      };
    } catch (error) {
      throw new Error(`Failed to get email details: ${error instanceof Error ? error.message : String(error)}`);
    }
  }

  private async handleDisconnectEmail(args: any) {
    const { connectionId } = args;
    const client = this.clients.get(connectionId);

    if (!client) {
      throw new Error(`No connection found for ID: ${connectionId}`);
    }

    try {
      await client.disconnect();
      this.clients.delete(connectionId);
      return {
        content: [
          {
            type: 'text',
            text: `Successfully disconnected connection: ${connectionId}`,
          },
        ],
      };
    } catch (error) {
      throw new Error(`Failed to disconnect: ${error instanceof Error ? error.message : String(error)}`);
    }
  }

  private async handleListProviders() {
    const providers = Object.entries(EmailProviders).map(([key, provider]) => ({
      key,
      name: provider.name,
    }));

    return {
      content: [
        {
          type: 'text',
          text: JSON.stringify(providers, null, 2),
        },
      ],
    };
  }

  async run(): Promise<void> {
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
    console.error('Email MCP server running on stdio');
  }
}

const server = new EmailMCPServer();
server.run().catch(console.error);