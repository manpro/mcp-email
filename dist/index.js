#!/usr/bin/env node
import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { CallToolRequestSchema, ListToolsRequestSchema, } from '@modelcontextprotocol/sdk/types.js';
import { ImapEmailClient } from './imap-client.js';
import { createImapConfig, EmailProviders, detectProvider } from './email-providers.js';
import axios from 'axios';
class EmailMCPServer {
    server;
    clients = new Map();
    constructor() {
        this.server = new Server({
            name: 'email-server',
            version: '1.0.0',
        }, {
            capabilities: {
                tools: {},
            },
        });
        this.setupToolHandlers();
        this.setupErrorHandling();
    }
    setupErrorHandling() {
        this.server.onerror = (error) => {
            console.error('[MCP Error]', error);
        };
        process.on('SIGINT', async () => {
            await this.cleanup();
            process.exit(0);
        });
    }
    async cleanup() {
        for (const client of this.clients.values()) {
            await client.disconnect();
        }
        this.clients.clear();
    }
    setupToolHandlers() {
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
                        name: 'check_ai_status',
                        description: 'Check if GPT-OSS 20B AI service is available for email analysis',
                        inputSchema: {
                            type: 'object',
                            properties: {},
                        },
                    },
                    {
                        name: 'analyze_email_with_ai',
                        description: 'Analyze email content using GPT-OSS 20B AI',
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
                                uid: {
                                    type: 'number',
                                    description: 'Email UID to analyze',
                                },
                            },
                            required: ['connectionId', 'uid'],
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
                ],
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
                    case 'check_ai_status':
                        return await this.handleCheckAIStatus();
                    case 'analyze_email_with_ai':
                        return await this.handleAnalyzeEmailWithAI(args);
                    case 'list_providers':
                        return await this.handleListProviders();
                    default:
                        throw new Error(`Unknown tool: ${name}`);
                }
            }
            catch (error) {
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
    async handleConnectEmail(args) {
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
        }
        catch (error) {
            throw new Error(`Failed to connect: ${error instanceof Error ? error.message : String(error)}`);
        }
    }
    async handleListMailboxes(args) {
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
        }
        catch (error) {
            throw new Error(`Failed to list mailboxes: ${error instanceof Error ? error.message : String(error)}`);
        }
    }
    async handleGetRecentEmails(args) {
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
        }
        catch (error) {
            throw new Error(`Failed to get recent emails: ${error instanceof Error ? error.message : String(error)}`);
        }
    }
    async handleSearchEmails(args) {
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
        }
        catch (error) {
            throw new Error(`Failed to search emails: ${error instanceof Error ? error.message : String(error)}`);
        }
    }
    async handleGetEmailDetails(args) {
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
        }
        catch (error) {
            throw new Error(`Failed to get email details: ${error instanceof Error ? error.message : String(error)}`);
        }
    }
    async handleDisconnectEmail(args) {
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
        }
        catch (error) {
            throw new Error(`Failed to disconnect: ${error instanceof Error ? error.message : String(error)}`);
        }
    }
    async checkGPTOSSAvailability() {
        try {
            // First check if the bridge is responding
            const response = await axios.get('http://localhost:8085/v1/models', {
                timeout: 5000
            });
            // Check if GPT-OSS 20B model is available
            const hasGPTOSS = response.data.data?.some((model) => model.id === 'gpt-oss:20b');
            if (!hasGPTOSS) {
                return {
                    status: 'model_unavailable',
                    message: 'GPT-OSS 20B model not available in Ollama'
                };
            }
            return {
                status: 'available',
                message: 'GPT-OSS 20B ready for email analysis'
            };
        }
        catch (error) {
            if (error.code === 'ECONNREFUSED') {
                return {
                    status: 'bridge_down',
                    message: 'OpenAI Bridge (port 8085) is not responding - check if ollama-bridge.py is running'
                };
            }
            else if (error.code === 'ETIMEDOUT') {
                return {
                    status: 'timeout',
                    message: 'GPT-OSS service timeout (>5s) - service may be overloaded or starting up'
                };
            }
            else {
                return {
                    status: 'error',
                    message: `GPT-OSS unavailable: ${error.message}`
                };
            }
        }
    }
    async handleCheckAIStatus() {
        const status = await this.checkGPTOSSAvailability();
        const statusEmoji = {
            'available': '✅',
            'bridge_down': '🔴',
            'timeout': '⏱️',
            'model_unavailable': '❌',
            'error': '⚠️'
        };
        return {
            content: [{
                    type: 'text',
                    text: `${statusEmoji[status.status]} AI Service Status: ${status.status.toUpperCase()}\n${status.message}`
                }]
        };
    }
    async handleAnalyzeEmailWithAI(args) {
        const { connectionId, mailbox = 'INBOX', uid } = args;
        const client = this.clients.get(connectionId);
        if (!client) {
            throw new Error(`No connection found for ID: ${connectionId}`);
        }
        // Check AI service availability first
        const healthCheck = await this.checkGPTOSSAvailability();
        if (healthCheck.status !== 'available') {
            return {
                content: [{
                        type: 'text',
                        text: `❌ Cannot analyze email - ${healthCheck.message}\n💡 Suggestion: Run 'check_ai_status' to verify service status or try again later`
                    }]
            };
        }
        try {
            // Fetch the email
            const emails = await client.fetchEmails([uid], mailbox);
            if (emails.length === 0) {
                throw new Error(`Email with UID ${uid} not found in ${mailbox}`);
            }
            const email = emails[0];
            // Prepare prompt for AI analysis
            const prompt = `Analyze this email and provide a structured assessment:

From: ${email.from}
Subject: ${email.subject}
Date: ${email.date}
Content: ${email.bodyText?.substring(0, 1000) || 'No text content available'}

Please provide:
1. Category (work/personal/newsletter/spam/notification/urgent)
2. Priority (high/medium/low)
3. Brief summary (max 50 words)
4. Suggested action (respond/archive/read-later/delete/forward)
5. Key information extracted

Return as JSON format.`;
            // Call GPT-OSS API
            const response = await axios.post('http://localhost:8085/v1/chat/completions', {
                model: 'gpt-oss:20b',
                messages: [
                    {
                        role: 'system',
                        content: 'You are an intelligent email analyst. Analyze emails and return structured JSON responses with accurate categorization and actionable insights.'
                    },
                    {
                        role: 'user',
                        content: prompt
                    }
                ],
                temperature: 0.3,
                max_tokens: 300
            }, { timeout: 30000 }); // 30 second timeout
            const aiContent = response.data.choices[0].message.content;
            // Try to extract and format JSON
            let analysis = aiContent;
            try {
                const jsonMatch = aiContent.match(/\{[\s\S]*?\}/);
                if (jsonMatch) {
                    const parsed = JSON.parse(jsonMatch[0]);
                    analysis = JSON.stringify(parsed, null, 2);
                }
            }
            catch (e) {
                // Keep original content if JSON parsing fails
            }
            return {
                content: [{
                        type: 'text',
                        text: `🤖 AI Analysis for Email UID ${uid}:\n\n📧 Email Info:\n- From: ${email.from}\n- Subject: ${email.subject}\n- Date: ${email.date}\n\n🧠 AI Assessment:\n${analysis}`
                    }]
            };
        }
        catch (error) {
            if (error.code === 'ETIMEDOUT') {
                return {
                    content: [{
                            type: 'text',
                            text: `⏱️ GPT-OSS analysis timeout (>30s) - service may be overloaded\n💡 Suggestion: Try with a shorter email or retry later`
                        }]
                };
            }
            else if (error.response?.status === 503) {
                return {
                    content: [{
                            type: 'text',
                            text: `🔄 GPT-OSS service temporarily unavailable (HTTP 503)\n💡 Suggestion: Model may be loading, try again in a few minutes`
                        }]
                };
            }
            else {
                return {
                    content: [{
                            type: 'text',
                            text: `❌ Analysis failed: ${error.message}\n💡 Suggestion: Check AI service status with 'check_ai_status'`
                        }]
                };
            }
        }
    }
    async handleListProviders() {
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
    async run() {
        const transport = new StdioServerTransport();
        await this.server.connect(transport);
        console.error('Email MCP server running on stdio');
    }
}
const server = new EmailMCPServer();
server.run().catch(console.error);
//# sourceMappingURL=index.js.map