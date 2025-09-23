#!/usr/bin/env node

/**
 * Email Proxy Server - Integrates MCP email functionality into frontend
 * Runs alongside Vite dev server on port 3623
 */

const express = require('express');
const cors = require('cors');

// Use the compiled JavaScript from MCP email dist
let ImapEmailClient, createImapConfig;

try {
  // Try Docker path first
  ({ ImapEmailClient } = require('/mcp-email/dist/imap-client.js'));
  ({ createImapConfig } = require('/mcp-email/dist/email-providers.js'));
} catch (err) {
  // Fallback to local path
  ({ ImapEmailClient } = require('../../mcp-email/dist/imap-client.js'));
  ({ createImapConfig } = require('../../mcp-email/dist/email-providers.js'));
}

const app = express();
const port = 3625; // Proxy port, will be accessed via Vite proxy
const clients = new Map();

app.use(cors());
app.use(express.json());

// Connect to email account
app.post('/api/mcp/connect', async (req, res) => {
  try {
    const { connectionId, email, password, provider, customHost, customPort } = req.body;

    console.log(`Connection attempt: ${connectionId} - ${email} - Provider: ${provider || 'auto'}`);

    if (!connectionId || !email || !password) {
      return res.status(400).json({ error: 'connectionId, email and password required' });
    }

    if (clients.has(connectionId)) {
      return res.status(400).json({ error: `Connection with ID '${connectionId}' already exists` });
    }

    const config = createImapConfig(email, password, provider, customHost, customPort);
    console.log(`Using config: ${config.host}:${config.port} for ${email}`);

    const client = new ImapEmailClient(config);

    // Test connection with timeout
    const connectPromise = client.connect();
    const timeoutPromise = new Promise((_, reject) => {
      setTimeout(() => reject(new Error('Connection timeout (40s)')), 40000);
    });

    await Promise.race([connectPromise, timeoutPromise]);

    clients.set(connectionId, client);

    res.json({
      success: true,
      message: `Connected to ${email} as ${connectionId}`,
      connectionId,
      email,
      provider: provider || 'auto',
      host: config.host,
      port: config.port
    });
  } catch (error) {
    console.error('Connection error:', error);
    res.status(500).json({
      error: error instanceof Error ? error.message : 'Unknown error'
    });
  }
});

// Get recent emails
app.post('/api/mcp/recent-emails', async (req, res) => {
  try {
    let { connectionId, count = 50, mailbox = 'INBOX' } = req.body;

    // Fix for one.com IMAP which requires INBOX prefix
    if (mailbox === 'INBOX') {
      mailbox = 'INBOX';
    } else if (!mailbox.startsWith('INBOX.')) {
      mailbox = `INBOX.${mailbox}`;
    }

    if (!connectionId) {
      return res.status(400).json({ error: 'connectionId required' });
    }

    const client = clients.get(connectionId);
    if (!client) {
      return res.status(404).json({ error: `Connection '${connectionId}' not found` });
    }

    const emails = await client.getRecentEmails(count, mailbox);

    const emailSummary = emails.map(email => ({
      uid: email.uid,
      subject: email.subject,
      from: email.from,
      to: email.to,
      date: email.date,
      flags: email.flags,
      hasAttachments: (email.attachments?.length || 0) > 0,
      bodyPreview: email.bodyText?.substring(0, 200) + (email.bodyText && email.bodyText.length > 200 ? '...' : ''),
      text: email.bodyText,
      html: email.bodyHtml
    }));

    res.json({
      success: true,
      emails: emailSummary,
      count: emailSummary.length,
      mailbox
    });
  } catch (error) {
    console.error('Get emails error:', error);
    res.status(500).json({
      error: error instanceof Error ? error.message : 'Unknown error'
    });
  }
});

// Search emails
app.post('/api/mcp/search-emails', async (req, res) => {
  try {
    let { connectionId, criteria, count = 50, mailbox = 'INBOX' } = req.body;

    // Fix for one.com IMAP which requires INBOX prefix
    if (mailbox === 'INBOX') {
      mailbox = 'INBOX';
    } else if (!mailbox.startsWith('INBOX.')) {
      mailbox = `INBOX.${mailbox}`;
    }

    if (!connectionId) {
      return res.status(400).json({ error: 'connectionId required' });
    }

    const client = clients.get(connectionId);
    if (!client) {
      return res.status(404).json({ error: `Connection '${connectionId}' not found` });
    }

    const emails = await client.searchEmails(criteria, count, mailbox);

    const emailSummary = emails.map(email => ({
      uid: email.uid,
      subject: email.subject,
      from: email.from,
      to: email.to,
      date: email.date,
      flags: email.flags,
      hasAttachments: (email.attachments?.length || 0) > 0,
      bodyPreview: email.bodyText?.substring(0, 200) + (email.bodyText && email.bodyText.length > 200 ? '...' : ''),
      text: email.bodyText,
      html: email.bodyHtml
    }));

    res.json({
      success: true,
      emails: emailSummary,
      count: emailSummary.length,
      mailbox,
      criteria
    });
  } catch (error) {
    console.error('Search emails error:', error);
    res.status(500).json({
      error: error instanceof Error ? error.message : 'Unknown error'
    });
  }
});

// Get connections
app.get('/api/mcp/connections', (req, res) => {
  const connections = Array.from(clients.keys()).map(id => ({
    connectionId: id,
    email: id === 'primary' ? 'mikael@fallstrom.org' : id
  }));

  res.json({
    success: true,
    connections
  });
});

// Disconnect
app.post('/api/mcp/disconnect', async (req, res) => {
  try {
    const { connectionId } = req.body;

    if (!connectionId) {
      return res.status(400).json({ error: 'connectionId required' });
    }

    const client = clients.get(connectionId);
    if (!client) {
      return res.status(404).json({ error: `Connection '${connectionId}' not found` });
    }

    await client.disconnect();
    clients.delete(connectionId);

    res.json({
      success: true,
      message: `Disconnected from ${connectionId}`
    });
  } catch (error) {
    console.error('Disconnect error:', error);
    res.status(500).json({
      error: error instanceof Error ? error.message : 'Unknown error'
    });
  }
});

// Auto-connect to primary account on startup
async function autoConnect() {
  try {
    const config = createImapConfig('mikael@fallstrom.org', process.env.EMAIL_PASSWORD || 'Ati:}v>~ra_Tqec?)zpLRq8Z', 'one.com');
    const client = new ImapEmailClient(config);
    await client.connect();
    clients.set('primary', client);
    console.log('✅ Auto-connected to primary email account');
  } catch (error) {
    console.error('⚠️  Could not auto-connect to primary account:', error.message);
  }
}

app.listen(port, () => {
  console.log(`📧 Email proxy server running on port ${port}`);
  autoConnect();
});