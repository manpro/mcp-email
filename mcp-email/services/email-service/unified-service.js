const express = require('express');
const cors = require('cors');
const axios = require('axios');
const EmailAIAnalyzer = require('./ai-analyzer');
const cache = require('./cache');
const accountsManager = require('./env-accounts-manager');
const envSaver = require('./env-saver');

const app = express();
const PORT = process.env.PORT || 3013;

app.use(cors());
app.use(express.json());

// AI Analyzer instance
const aiAnalyzer = new EmailAIAnalyzer();

// Email backend service (index.js)
const MCP_EMAIL_URL = process.env.EMAIL_SERVICE_URL || 'http://localhost:3012';

// Account Management Endpoints
app.get('/api/accounts', async (req, res) => {
  try {
    const accounts = accountsManager.getAllAccounts();
    res.json({ accounts });
  } catch (error) {
    console.error('Error fetching accounts:', error);
    res.status(500).json({ error: 'Failed to fetch accounts' });
  }
});

app.post('/api/accounts', async (req, res) => {
  try {
    const { email, password, provider } = req.body;

    // Save credentials to .env file if password is provided
    if (password) {
      envSaver.saveCredentials(email, password, provider);
    }

    const account = await accountsManager.addAccount(req.body);
    res.json({ success: true, account });
  } catch (error) {
    console.error('Error adding account:', error);
    res.status(500).json({ error: 'Failed to add account', details: error.message });
  }
});

app.put('/api/accounts/:accountId', async (req, res) => {
  try {
    const { accountId } = req.params;
    const account = await accountsManager.updateAccount(accountId, req.body);
    res.json({ success: true, account });
  } catch (error) {
    console.error('Error updating account:', error);
    res.status(500).json({ error: 'Failed to update account', details: error.message });
  }
});

app.delete('/api/accounts/:accountId', async (req, res) => {
  try {
    const { accountId } = req.params;
    const result = await accountsManager.removeAccount(accountId);
    res.json(result);
  } catch (error) {
    console.error('Error removing account:', error);
    res.status(500).json({ error: 'Failed to remove account', details: error.message });
  }
});

app.post('/api/accounts/:accountId/toggle', async (req, res) => {
  try {
    const { accountId } = req.params;
    const { active } = req.body;
    const account = await accountsManager.toggleAccount(accountId, active);
    res.json({ success: true, account });
  } catch (error) {
    console.error('Error toggling account:', error);
    res.status(500).json({ error: 'Failed to toggle account', details: error.message });
  }
});

// Connect to a specific account
app.post('/api/accounts/:accountId/connect', async (req, res) => {
  try {
    const { accountId } = req.params;
    const { password } = req.body;
    const account = accountsManager.getAccount(accountId);

    if (!account) {
      return res.status(404).json({ error: 'Account not found' });
    }

    // Try to get password from request body first, then from stored credentials
    let finalPassword = password || accountsManager.getCredentials(accountId);

    if (!finalPassword) {
      return res.status(400).json({ error: 'No password provided or stored for this account' });
    }

    // If password was provided in request, save it to .env
    if (password) {
      envSaver.saveCredentials(account.email, password, account.provider);
      accountsManager.storeCredentials(accountId, password);
    }

    // Connect via MCP-Email
    const response = await axios.post(`${MCP_EMAIL_URL}/connect`, {
      connectionId: accountId,
      email: account.email,
      password: finalPassword,
      imapHost: account.imapHost,
      imapPort: account.imapPort,
      imapSecure: true
    });

    // Store connection
    accountsManager.setConnection(accountId, response.data);

    res.json({
      success: true,
      message: 'Connected successfully',
      accountId,
      ...response.data
    });
  } catch (error) {
    console.error('Connection error:', error.message);
    res.status(500).json({
      error: 'Connection failed',
      details: error.response?.data || error.message
    });
  }
});

// Legacy connect endpoint for backward compatibility
app.post('/connect', async (req, res) => {
  try {
    const { email, password, provider } = req.body;

    // Determine IMAP host and connection ID from email
    let imapHost = 'imap.gmail.com';
    let connectionId = 'main';
    const domain = email.split('@')[1];
    const username = email.split('@')[0];

    if (domain === 'fallstrom.org' || provider === 'oneCom') {
      imapHost = 'imap.one.com';
      connectionId = username; // Use username as connectionId
    } else if (domain.includes('outlook') || domain.includes('hotmail')) {
      imapHost = 'outlook.office365.com';
    } else if (provider === 'gmail' || domain.includes('gmail')) {
      imapHost = 'imap.gmail.com';
    }

    // Save credentials to .env file
    envSaver.saveCredentials(email, password, provider);

    // Add account to manager
    const account = await accountsManager.addAccount({
      email,
      password,
      provider,
      imapHost,
      imapPort: 993,
      displayName: username
    });

    // Connect via MCP-Email
    const response = await axios.post(`${MCP_EMAIL_URL}/connect`, {
      connectionId: account.id,
      email,
      password,
      imapHost,
      imapPort: 993,
      imapSecure: true
    });

    // Store connection
    accountsManager.setConnection(account.id, response.data);

    res.json({
      success: true,
      message: 'Connected successfully',
      connectionId: account.id,
      accountId: account.id,
      account,
      ...response.data
    });
  } catch (error) {
    console.error('Connection error:', error.message);
    res.status(500).json({
      error: 'Connection failed',
      details: error.response?.data || error.message
    });
  }
});

app.get('/api/accounts/:accountId/mailboxes', async (req, res) => {
  try {
    const { accountId } = req.params;
    const account = accountsManager.getAccount(accountId);

    if (!account) {
      return res.status(404).json({ error: 'Account not found' });
    }

    // Try to get real mailboxes from MCP-Email
    try {
      const response = await axios.post(`${MCP_EMAIL_URL}/api/mailboxes`, {
        connectionId: accountId
      });

      if (response.data.mailboxes) {
        // Update account with fetched folders
        await accountsManager.updateFolders(accountId, response.data.mailboxes);
        return res.json({ mailboxes: response.data.mailboxes, accountId });
      }
    } catch (err) {
      console.log('Could not fetch real mailboxes, using defaults');
    }

    // Return cached or standard mailboxes
    const mailboxes = account.folders.length > 0 ? account.folders : [
      { id: 1, name: 'INBOX', path: 'INBOX', count: 0, unread: 0 },
      { id: 2, name: 'Sent', path: 'Sent', count: 0, unread: 0 },
      { id: 3, name: 'Drafts', path: 'Drafts', count: 0, unread: 0 },
      { id: 4, name: 'Trash', path: 'Trash', count: 0, unread: 0 },
      { id: 5, name: 'Spam', path: 'Spam', count: 0, unread: 0 },
      { id: 6, name: 'Archive', path: 'Archive', count: 0, unread: 0 }
    ];

    res.json({ mailboxes, accountId });
  } catch (error) {
    console.error('Mailboxes error:', error.message);
    res.status(500).json({
      error: 'Failed to fetch mailboxes',
      requiresAuth: true,
      details: error.message
    });
  }
});

// Legacy mailboxes endpoint
app.get('/api/mailboxes', async (req, res) => {
  try {
    // GitHub mcp-email has circular structure issues with mailboxes
    // For now, return common IMAP folders
    const standardMailboxes = [
      { id: 1, name: 'INBOX', path: 'INBOX', count: 0, unread: 0 },
      { id: 2, name: 'Sent', path: 'Sent', count: 0, unread: 0 },
      { id: 3, name: 'Drafts', path: 'Drafts', count: 0, unread: 0 },
      { id: 4, name: 'Trash', path: 'Trash', count: 0, unread: 0 },
      { id: 5, name: 'Spam', path: 'Spam', count: 0, unread: 0 },
      { id: 6, name: 'Archive', path: 'Archive', count: 0, unread: 0 }
    ];

    res.json({ mailboxes: standardMailboxes });
  } catch (error) {
    console.error('Mailboxes error:', error.message);
    res.status(500).json({
      error: 'Failed to fetch mailboxes',
      requiresAuth: true,
      details: error.message
    });
  }
});

// Get emails for specific account
app.get('/api/accounts/:accountId/emails', async (req, res) => {
  try {
    const { accountId } = req.params;
    const { mailbox = 'INBOX', limit = 1000 } = req.query;

    const account = accountsManager.getAccount(accountId);
    if (!account) {
      return res.status(404).json({ error: 'Account not found' });
    }

    // Cache disabled for debugging
    // const cachedEmails = await cache.getCachedEmails(accountId, mailbox, limit);
    // if (cachedEmails) {
    //   console.log(`Serving emails from cache for ${accountId}/${mailbox}`);
    //   return res.json({ ...cachedEmails, accountId });
    // }

    // If not cached, fetch from MCP-Email
    const response = await axios.get(`${MCP_EMAIL_URL}/recent-emails/${accountId}`, {
      params: {
        limit: parseInt(limit),
        mailbox: mailbox
      }
    });

    // Integrated service returns array directly
    let emails = Array.isArray(response.data) ? response.data : (response.data.emails || []);

    // Sort emails by date, newest first
    emails.sort((a, b) => {
      const dateA = new Date(a.date || 0);
      const dateB = new Date(b.date || 0);
      return dateB - dateA; // Newest first
    });

    // Only analyze first 3 emails to avoid timeout
    const analyzedEmails = [];
    for (let i = 0; i < Math.min(3, emails.length); i++) {
      const email = emails[i];

      // Check if we have cached AI analysis for this email
      let analysis = await cache.getCachedAIAnalysis(accountId, email.uid);

      if (!analysis) {
        try {
          // No cached analysis, generate new one
          analysis = await aiAnalyzer.classifyEmail(email);
          // Cache the AI analysis
          await cache.cacheAIAnalysis(accountId, email.uid, analysis);
        } catch (err) {
          console.error(`AI analysis failed for email ${email.uid}:`, err.message);
          analysis = null;
        }
      }

      analyzedEmails.push({
        ...email,
        ...(analysis && { aiAnalysis: analysis })
      });
    }

    // Keep rest unanalyzed to avoid overload
    const finalEmails = [
      ...analyzedEmails,
      ...emails.slice(3)
    ];

    const result = {
      emails: finalEmails,
      analyzed: analyzedEmails.length,
      total: emails.length,
      accountId,
      account: {
        email: account.email,
        displayName: account.displayName,
        color: account.color
      }
    };

    // Update unread count
    const unreadCount = emails.filter(e => !e.seen).length;
    await accountsManager.updateCounts(accountId, unreadCount, emails.length);

    // Cache the result
    await cache.cacheEmails(accountId, mailbox, result, limit);

    res.json(result);
  } catch (error) {
    console.error('Recent emails error:', error.message);
    res.status(500).json({
      error: 'Failed to fetch emails',
      requiresAuth: true
    });
  }
});

// POST endpoint for frontend compatibility
app.post('/api/accounts/:accountId/emails', async (req, res) => {
  try {
    const { accountId } = req.params;
    const { mailbox = 'INBOX', limit = 50 } = req.body || {};

    console.log(`POST /api/accounts/${accountId}/emails - fetching emails from ${mailbox}, limit: ${limit}`);

    // Point to the refactored service on port 3015
    const response = await axios.get(`http://localhost:3015/recent-emails/${accountId}`, {
      params: {
        limit: parseInt(limit),
        mailbox
      }
    });

    const emails = Array.isArray(response.data) ? response.data : [];

    res.json({
      emails,
      accountId,
      total: emails.length
    });
  } catch (error) {
    console.error('Failed to fetch emails:', error.message);
    res.status(500).json({
      error: 'Failed to fetch emails',
      details: error.message
    });
  }
});

// Frontend-compatible endpoint for account-specific emails
app.get('/api/accounts/:accountId/emails', async (req, res) => {
  try {
    const { accountId } = req.params;
    const { mailbox = 'INBOX', limit = 1000 } = req.query;

    // Check cache first - disabled for debugging
    // const cachedEmails = await cache.getCachedEmails(accountId, mailbox, limit);
    // if (cachedEmails) {
    //   console.log(`Serving emails from cache for ${accountId}/${mailbox}`);
    //   return res.json(cachedEmails);
    // }

    // If not cached, fetch from MCP-Email
    console.log(`Fetching from ${MCP_EMAIL_URL}/recent-emails/${accountId}`);

    let emails = [];
    try {
      const response = await axios.get(`${MCP_EMAIL_URL}/recent-emails/${accountId}`, {
        params: {
          limit: parseInt(limit),
          mailbox: mailbox
        }
      });

      console.log(`Response type: ${typeof response.data}, length: ${Array.isArray(response.data) ? response.data.length : 'N/A'}`);
      emails = Array.isArray(response.data) ? response.data : [];
    } catch (fetchError) {
      console.error('Failed to fetch from integrated service:', fetchError.message);
      emails = [];
    }

    const account = accountsManager.getAccount(accountId);
    if (!account) {
      return res.status(404).json({ error: 'Account not found' });
    }

    // Apply AI analysis to first 3 emails to avoid overload
    const analyzedEmails = [];
    for (let i = 0; i < Math.min(3, emails.length); i++) {
      const email = emails[i];
      let analysis = null;

      try {
        // Only analyze if AI service is available
        if (process.env.AI_SERVICE_URL) {
          const aiResponse = await axios.post(`${process.env.AI_SERVICE_URL}/classify`, {
            subject: email.subject || '',
            body: email.text || email.html || '',
            from: email.from?.text || ''
          }, { timeout: 5000 });
          analysis = aiResponse.data;
        }
      } catch (aiError) {
        console.warn(`AI analysis failed for email ${email.uid}:`, aiError.message);
        analysis = null;
      }

      analyzedEmails.push({
        ...email,
        ...(analysis && { aiAnalysis: analysis })
      });
    }

    // Keep rest unanalyzed to avoid overload
    const finalEmails = [
      ...analyzedEmails,
      ...emails.slice(3)
    ];

    const result = {
      emails: finalEmails,
      analyzed: analyzedEmails.length,
      total: emails.length,
      accountId,
      account: {
        email: account.email,
        displayName: account.displayName,
        color: account.color
      }
    };

    // Update unread count
    const unreadCount = emails.filter(e => !e.seen).length;
    await accountsManager.updateCounts(accountId, unreadCount, emails.length);

    // Cache the result
    await cache.cacheEmails(accountId, mailbox, result, limit);

    res.json(result);
  } catch (error) {
    console.error('Account emails error:', error.message);
    console.error('Full error:', error.response?.status, error.response?.data);

    // Check if this is an authentication error
    if (error.response && error.response.status === 404) {
      // Account not connected - return empty result
      console.log('Returning empty due to 404');
      return res.json({
        emails: [],
        analyzed: 0,
        total: 0,
        accountId: req.params.accountId,
        requiresAuth: true,
        message: 'Email account not connected. Please connect your email account first.'
      });
    }

    // Other errors
    res.status(500).json({
      error: 'Failed to fetch emails',
      details: error.message
    });
  }
});

// Get combined emails from all active accounts
app.get('/api/emails/unified', async (req, res) => {
  try {
    const { mailbox = 'INBOX', limit = 1000 } = req.query;
    const activeAccounts = accountsManager.getActiveAccounts();

    if (activeAccounts.length === 0) {
      return res.json({
        emails: [],
        total: 0,
        accounts: []
      });
    }

    // Fetch emails from all active accounts in parallel
    const emailPromises = activeAccounts.map(async (account) => {
      try {
        const cachedEmails = await cache.getCachedEmails(account.id, mailbox, limit);
        if (cachedEmails) {
          return {
            ...cachedEmails,
            accountId: account.id,
            account: {
              email: account.email,
              displayName: account.displayName,
              color: account.color
            }
          };
        }

        const response = await axios.get(`${MCP_EMAIL_URL}/emails/${account.id}`, {
          params: {
            limit: parseInt(limit),
            mailbox
          }
        });

        const emails = (response.data.emails || []).map(email => ({
          ...email,
          accountId: account.id,
          accountEmail: account.email,
          accountColor: account.color
        }));

        return {
          emails,
          accountId: account.id,
          account: {
            email: account.email,
            displayName: account.displayName,
            color: account.color
          }
        };
      } catch (error) {
        console.error(`Failed to fetch emails for account ${account.id}:`, error.message);
        return {
          emails: [],
          accountId: account.id,
          error: error.message
        };
      }
    });

    const results = await Promise.all(emailPromises);

    // Combine and sort all emails by date
    const allEmails = [];
    const accountSummaries = [];

    results.forEach(result => {
      if (result.emails && result.emails.length > 0) {
        allEmails.push(...result.emails);
      }
      accountSummaries.push({
        accountId: result.accountId,
        account: result.account,
        emailCount: result.emails ? result.emails.length : 0,
        error: result.error
      });
    });

    // Sort all emails by date, newest first
    allEmails.sort((a, b) => {
      const dateA = new Date(a.date || 0);
      const dateB = new Date(b.date || 0);
      return dateB - dateA;
    });

    res.json({
      emails: allEmails,
      total: allEmails.length,
      accounts: accountSummaries
    });
  } catch (error) {
    console.error('Unified emails error:', error.message);
    res.status(500).json({
      error: 'Failed to fetch unified emails',
      details: error.message
    });
  }
});

// Legacy recent-emails endpoint
app.get('/emails', async (req, res) => {
  try {
    const { mailbox = 'INBOX', limit = 1000 } = req.query;

    // Try to use the first active account or mikael_one for backward compatibility
    const activeAccounts = accountsManager.getActiveAccounts();
    const accountId = activeAccounts.length > 0 ? activeAccounts[0].id : 'mikael_one';

    // Check cache first - disabled for debugging
    // const cachedEmails = await cache.getCachedEmails(accountId, mailbox, limit);
    // if (cachedEmails) {
    //   console.log(`Serving emails from cache for ${accountId}/${mailbox}`);
    //   return res.json(cachedEmails);
    // }

    // If not cached, fetch from MCP-Email
    const response = await axios.get(`${MCP_EMAIL_URL}/recent-emails/${accountId}`, {
      params: {
        limit: parseInt(limit),
        mailbox: mailbox
      }
    });

    // Integrated service returns array directly
    let emails = Array.isArray(response.data) ? response.data : (response.data.emails || []);

    // Sort emails by date, newest first
    emails.sort((a, b) => {
      const dateA = new Date(a.date || 0);
      const dateB = new Date(b.date || 0);
      return dateB - dateA; // Newest first
    });

    // Only analyze first 3 emails to avoid timeout
    // Check AI cache first for each email
    const analyzedEmails = [];
    for (let i = 0; i < Math.min(3, emails.length); i++) {
      const email = emails[i];

      // Check if we have cached AI analysis for this email
      let analysis = await cache.getCachedAIAnalysis(accountId, email.uid);

      if (!analysis) {
        try {
          // No cached analysis, generate new one
          analysis = await aiAnalyzer.classifyEmail(email);
          // Cache the AI analysis
          await cache.cacheAIAnalysis(accountId, email.uid, analysis);
        } catch (err) {
          console.error(`AI analysis failed for email ${email.uid}:`, err.message);
          analysis = null;
        }
      }

      analyzedEmails.push({
        ...email,
        ...(analysis && { aiAnalysis: analysis })
      });
    }

    // Keep rest unanalyzed to avoid overload
    const finalEmails = [
      ...analyzedEmails,
      ...emails.slice(3)
    ];

    const result = {
      emails: finalEmails,
      analyzed: analyzedEmails.length,
      total: emails.length
    };

    // Cache the result
    await cache.cacheEmails(accountId, mailbox, result, limit);

    res.json(result);
  } catch (error) {
    console.error('Recent emails error:', error.message);
    res.status(500).json({
      error: 'Failed to fetch emails',
      requiresAuth: true
    });
  }
});

// Email management endpoints
app.delete('/api/accounts/:accountId/emails/:uid', async (req, res) => {
  try {
    const { accountId, uid } = req.params;
    console.log(`Deleting email ${uid} from account ${accountId}`);

    // For now, just return success - would need IMAP integration for real deletion
    res.json({
      success: true,
      message: `Email ${uid} deleted`,
      accountId,
      uid
    });
  } catch (error) {
    console.error('Delete email error:', error);
    res.status(500).json({ error: 'Failed to delete email' });
  }
});

app.post('/api/accounts/:accountId/emails/:uid/move', async (req, res) => {
  try {
    const { accountId, uid } = req.params;
    const { targetFolder } = req.body;
    console.log(`Moving email ${uid} to ${targetFolder} in account ${accountId}`);

    // For now, just return success - would need IMAP integration for real move
    res.json({
      success: true,
      message: `Email ${uid} moved to ${targetFolder}`,
      accountId,
      uid,
      targetFolder
    });
  } catch (error) {
    console.error('Move email error:', error);
    res.status(500).json({ error: 'Failed to move email' });
  }
});

app.post('/api/accounts/:accountId/emails/:uid/read', async (req, res) => {
  try {
    const { accountId, uid } = req.params;
    console.log(`Marking email ${uid} as read in account ${accountId}`);

    // For now, just return success - would need IMAP integration for real marking
    res.json({
      success: true,
      message: `Email ${uid} marked as read`,
      accountId,
      uid
    });
  } catch (error) {
    console.error('Mark as read error:', error);
    res.status(500).json({ error: 'Failed to mark email as read' });
  }
});

app.post('/api/accounts/:accountId/emails/:uid/unread', async (req, res) => {
  try {
    const { accountId, uid } = req.params;
    console.log(`Marking email ${uid} as unread in account ${accountId}`);

    // For now, just return success - would need IMAP integration for real marking
    res.json({
      success: true,
      message: `Email ${uid} marked as unread`,
      accountId,
      uid
    });
  } catch (error) {
    console.error('Mark as unread error:', error);
    res.status(500).json({ error: 'Failed to mark email as unread' });
  }
});

// AI-specific endpoints
app.post('/api/ai/classify', async (req, res) => {
  try {
    const { email } = req.body;
    const analysis = await aiAnalyzer.classifyEmail(email);
    res.json(analysis);
  } catch (error) {
    res.status(500).json({ error: 'Classification failed', details: error.message });
  }
});

app.post('/api/ai/generate-reply', async (req, res) => {
  try {
    const { email, replyType = 'professional' } = req.body;
    const reply = await aiAnalyzer.generateReply(email, replyType);
    res.json({ reply });
  } catch (error) {
    res.status(500).json({ error: 'Reply generation failed', details: error.message });
  }
});

app.post('/api/ai/summarize-thread', async (req, res) => {
  try {
    const { emails } = req.body;
    const summary = await aiAnalyzer.summarizeThread(emails);
    res.json({ summary });
  } catch (error) {
    res.status(500).json({ error: 'Thread summary failed', details: error.message });
  }
});

// Smart inbox - combines email fetching with AI prioritization
app.get('/api/smart-inbox', async (req, res) => {
  try {
    // Fetch recent emails
    const emailsResponse = await axios.get(`${MCP_EMAIL_URL}/emails/mikael_one`, {
      params: {
        limit: 50,
        mailbox: 'INBOX'
      }
    });

    const emails = emailsResponse.data.emails || [];

    // Analyze and prioritize
    const analyzed = await Promise.all(
      emails.map(async (email) => {
        const analysis = await aiAnalyzer.classifyEmail(email);
        return {
          ...email,
          aiAnalysis: analysis,
          score: calculatePriorityScore(analysis)
        };
      })
    );

    // Sort by priority score
    analyzed.sort((a, b) => b.score - a.score);

    // Group by category
    const grouped = {
      urgent: analyzed.filter(e => e.aiAnalysis.priority === 'high' && e.aiAnalysis.actionRequired),
      important: analyzed.filter(e => e.aiAnalysis.priority === 'high' && !e.aiAnalysis.actionRequired),
      regular: analyzed.filter(e => e.aiAnalysis.priority === 'medium'),
      low: analyzed.filter(e => e.aiAnalysis.priority === 'low'),
      newsletters: analyzed.filter(e => e.aiAnalysis.category === 'newsletter'),
      promotional: analyzed.filter(e => e.aiAnalysis.category === 'promotional')
    };

    res.json({
      inbox: grouped,
      total: emails.length,
      analyzed: analyzed.length
    });
  } catch (error) {
    console.error('Smart inbox error:', error.message);
    res.status(500).json({
      error: 'Failed to load smart inbox',
      details: error.message
    });
  }
});

function calculatePriorityScore(analysis) {
  let score = 0;

  if (analysis.priority === 'high') score += 10;
  if (analysis.priority === 'medium') score += 5;
  if (analysis.actionRequired) score += 8;
  if (analysis.sentiment === 'negative') score += 3;
  if (analysis.category === 'work') score += 4;
  if (analysis.category === 'personal') score += 2;
  if (analysis.category === 'newsletter') score -= 5;
  if (analysis.category === 'promotional') score -= 7;
  if (analysis.category === 'spam') score -= 10;

  return score;
}

// Health check
app.get('/health', (req, res) => {
  res.json({
    status: 'healthy',
    service: 'unified-email-service',
    features: ['email', 'ai-analysis', 'smart-inbox'],
    backends: {
      mcp_email: MCP_EMAIL_URL,
      gpt_oss: 'http://172.16.16.148:8085'
    }
  });
});

// Search Endpoint
app.get('/api/search', async (req, res) => {
  try {
    const { q: query, account: accountId } = req.query;

    if (!query) {
      return res.status(400).json({ error: 'Search query is required' });
    }

    const cacheKey = `search_${accountId || 'all'}_${query}`;
    const cached = await cache.get(cacheKey);
    if (cached) {
      return res.json({ emails: cached, source: 'cache' });
    }

    // First get emails from the specified account or all accounts
    let emails = [];

    if (accountId) {
      // Search specific account
      const account = accountsManager.getAccount(accountId);
      if (!account) {
        return res.status(404).json({ error: 'Account not found' });
      }

      try {
        const response = await axios.post(`${MCP_EMAIL_URL}/api/emails`, {
          connectionId: accountId,
          mailbox: 'INBOX',
          limit: 50
        });
        emails = response.data.emails || [];
      } catch (error) {
        console.log('Could not fetch emails for search, using empty array');
      }
    } else {
      // Search all accounts
      const allAccounts = accountsManager.getAllAccounts();
      for (const account of allAccounts.filter(a => a.active)) {
        try {
          const response = await axios.post(`${MCP_EMAIL_URL}/api/emails`, {
            connectionId: account.id,
            mailbox: 'INBOX',
            limit: 25
          });
          emails = emails.concat(response.data.emails || []);
        } catch (error) {
          console.log(`Could not fetch emails from account ${account.id}`);
        }
      }
    }

    // Simple text-based search
    const searchTerms = query.toLowerCase().split(' ');
    const searchResults = emails.filter(email => {
      const searchText = [
        email.subject || '',
        email.from || '',
        email.text || '',
        email.bodyPreview || ''
      ].join(' ').toLowerCase();

      return searchTerms.some(term => searchText.includes(term));
    }).map(email => ({
      ...email,
      matchReason: `Found "${query}" in email content`
    }));

    // Cache results for 5 minutes
    await cache.set(cacheKey, searchResults, 300);

    res.json({
      emails: searchResults,
      query,
      totalResults: searchResults.length,
      source: 'search'
    });
  } catch (error) {
    console.error('Search error:', error);
    res.status(500).json({ error: 'Search failed', details: error.message });
  }
});

app.listen(PORT, () => {
  console.log(`\n🚀 Unified Email Service running on port ${PORT}`);
  console.log('\nFeatures:');
  console.log('  ✅ Email connection & fetching (via MCP-Email)');
  console.log('  ✅ AI-powered email classification (GPT-OSS 20B)');
  console.log('  ✅ Smart inbox with prioritization');
  console.log('  ✅ Reply generation');
  console.log('  ✅ Thread summarization');
  console.log('\nEndpoints:');
  console.log('  POST /connect - Connect to email');
  console.log('  GET  /api/mailboxes - Get mailboxes');
  console.log('  GET  /emails - Get emails with AI analysis');
  console.log('  GET  /api/smart-inbox - AI-prioritized inbox');
  console.log('  POST /api/ai/classify - Classify single email');
  console.log('  POST /api/ai/generate-reply - Generate reply');
  console.log('  POST /api/ai/summarize-thread - Summarize thread');
});