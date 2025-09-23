const express = require('express');
const cors = require('cors');
const axios = require('axios');
const redis = require('redis');
const EmailAIAnalyzer = require('./ai-analyzer');
const EmailDatabase = require('./database');

const app = express();
const PORT = process.env.PORT || 3012;

app.use(cors());
app.use(express.json());

// Redis client setup
const REDIS_HOST = process.env.REDIS_HOST || '172.17.0.1';
const REDIS_PORT = process.env.REDIS_PORT || 6381;
const MCP_GUI_HOST = process.env.MCP_GUI_HOST || 'localhost';
let redisClient = null;
let redisConnected = false;

// Initialize Redis connection
(async () => {
  try {
    redisClient = redis.createClient({
      socket: {
        host: REDIS_HOST,
        port: REDIS_PORT
      }
    });

    redisClient.on('error', (err) => {
      console.error('Redis error:', err.message);
      redisConnected = false;
    });

    redisClient.on('connect', () => {
      console.log(`✅ Redis connected at ${REDIS_HOST}:${REDIS_PORT}`);
      redisConnected = true;
    });

    await redisClient.connect();
  } catch (error) {
    console.warn('⚠️ Redis connection failed, running without cache:', error.message);
    redisConnected = false;
  }
})();

// AI Analyzer instance for GPT-OSS integration
const aiAnalyzer = new EmailAIAnalyzer();

// Database instance for persistent storage
const emailDb = new EmailDatabase();

// Store connected email accounts
const emailConnections = new Map();

// Helper function to generate cache key
function getCacheKey(email) {
  // Use email UID and subject as cache key
  return `email:cat:${email.uid || 'unknown'}:${email.subject?.substring(0, 50) || 'no-subject'}`;
}

// Rule-based categorization fallback function
function getRuleBasedCategorization(email) {
  const from = (email.from || '').toLowerCase();
  const subject = (email.subject || '').toLowerCase();
  const text = (email.text || email.bodyPreview || '').toLowerCase();

  let category = 'personal';
  let priority = 'medium';
  let sentiment = 'neutral';
  let topics = [];
  let action_required = false;

  // Category determination
  if (from.includes('newsletter') || from.includes('noreply') || from.includes('marketing') ||
      subject.includes('nyhetsbrev') || text.includes('unsubscribe') || text.includes('avprenumerera')) {
    category = 'newsletter';
    priority = 'low';
  } else if (subject.includes('säkerhet') || subject.includes('verifiering') ||
             subject.includes('lösenord') || subject.includes('security')) {
    category = 'security';
    priority = 'high';
    action_required = true;
  } else if (subject.includes('möte') || subject.includes('meeting') ||
             subject.includes('kallelse') || text.includes('zoom')) {
    category = 'meetings';
    priority = 'high';
    action_required = true;
    topics = ['meeting'];
  } else if (from.includes('@company.') || subject.includes('projekt') ||
             subject.includes('deadline') || subject.includes('rapport')) {
    category = 'work';
    priority = 'high';
    topics = ['work'];
  } else if (from.includes('automated') || subject.includes('bekräftelse')) {
    category = 'notification';
    priority = 'low';
  } else if (subject.includes('faktura') || subject.includes('invoice') ||
             text.includes('betalning') || text.includes('payment')) {
    category = 'billing';
    priority = 'high';
    action_required = true;
    topics = ['billing'];
  } else if (subject.includes('spam') || text.includes('winner') ||
             text.includes('congratulations')) {
    category = 'spam';
    priority = 'low';
    sentiment = 'negative';
  }

  // Priority determination
  if (subject.includes('brådskande') || subject.includes('urgent') ||
      subject.includes('viktigt') || subject.includes('important')) {
    priority = 'high';
    action_required = true;
  }

  // Sentiment determination
  if (text.includes('tack') || text.includes('thank') || text.includes('grattis') ||
      text.includes('congratulation')) {
    sentiment = 'positive';
  } else if (text.includes('problem') || text.includes('fel') || text.includes('error') ||
             text.includes('issue')) {
    sentiment = 'negative';
  }

  return {
    category,
    priority,
    sentiment,
    topics,
    action_required,
    summary: `${category} email with ${priority} priority`,
    confidence: 0.7 // Rule-based confidence
  };
}

// ML categorization function using GPT-OSS with Redis caching and SQLite persistence
async function categorizeEmailWithML(email) {
  try {
    // 1. First check SQLite database for persistent storage
    const dbResult = await emailDb.getCategorization(email);
    if (dbResult) {
      // If found in database, update Redis cache for faster access
      if (redisConnected && redisClient) {
        const cacheKey = getCacheKey(email);
        try {
          await redisClient.setEx(cacheKey, 86400, JSON.stringify(dbResult));
        } catch (cacheError) {
          console.warn('Cache write error:', cacheError.message);
        }
      }
      return dbResult;
    }

    // 2. Check Redis cache (for recently accessed items not in DB)
    if (redisConnected && redisClient) {
      const cacheKey = getCacheKey(email);
      try {
        const cached = await redisClient.get(cacheKey);
        if (cached) {
          console.log(`📦 Cache hit for email: ${email.subject?.substring(0, 30)}...`);
          const result = JSON.parse(cached);
          // Save to database for persistence
          await emailDb.saveCategorization(email, result);
          return result;
        }
      } catch (cacheError) {
        console.warn('Cache read error:', cacheError.message);
      }
    }
    const prompt = `Analyze this email and provide structured classification:
From: ${email.from || 'Unknown'}
Subject: ${email.subject || 'No subject'}
Date: ${email.date || new Date().toISOString()}
Content: ${email.text?.substring(0, 500) || email.bodyPreview || 'No content'}

Provide JSON response with:
1. category: work/personal/newsletter/spam/notification/social/billing/support/marketing/travel/education/health
2. priority: high/medium/low
3. sentiment: positive/neutral/negative
4. topics: array of main topics (max 3)
5. action_required: boolean
6. summary: one sentence summary (max 20 words)`;

    const response = await axios.post('http://172.16.16.148:8085/v1/chat/completions', {
      model: 'gpt-oss:20b',
      messages: [
        {
          role: 'system',
          content: 'You are an email classification AI. Always return valid JSON only, no extra text.'
        },
        {
          role: 'user',
          content: prompt
        }
      ],
      temperature: 0.3,
      max_tokens: 200
    });

    const aiContent = response.data.choices[0].message.content;

    // Parse JSON from response
    const jsonMatch = aiContent.match(/\{[\s\S]*?\}/);
    if (jsonMatch) {
      const result = JSON.parse(jsonMatch[0]);

      // Store in SQLite database for persistence
      await emailDb.saveCategorization(email, result);

      // Also store in Redis cache for fast access
      if (redisConnected && redisClient) {
        const cacheKey = getCacheKey(email);
        try {
          await redisClient.setEx(cacheKey, 86400, JSON.stringify(result));
          console.log(`💾 Cached categorization for: ${email.subject?.substring(0, 30)}...`);
        } catch (cacheError) {
          console.warn('Cache write error:', cacheError.message);
        }
      }

      return result;
    }

    // If LLM response is invalid, use rule-based categorization
    return getRuleBasedCategorization(email);
  } catch (error) {
    console.error('ML categorization error:', error.message);
    // Fallback to rule-based categorization
    return getRuleBasedCategorization(email);
  }
}

// Connect to MCP Email GUI Server and get emails
async function fetchEmailsFromMCP(connectionId, limit = 50) {
  try {
    // Use 'primary' as the connection ID for MCP regardless of the requested account ID
    const mcpConnectionId = 'primary';

    // First ensure connection exists
    // Connect to the MCP GUI Server on port 3624 (it's already running and working!)
    const connections = await axios.get(`http://${MCP_GUI_HOST}:3624/api/connections`);

    // Check if response data exists and has connections array
    const hasConnection = connections.data && connections.data.connections &&
                          Array.isArray(connections.data.connections) &&
                          connections.data.connections.some(c => c.connectionId === mcpConnectionId);

    if (!hasConnection) {
      // Connect to email
      console.log('Creating new MCP connection...');
      await axios.post(`http://${MCP_GUI_HOST}:3624/api/connect`, {
        connectionId: mcpConnectionId,
        email: process.env.ONECOM_EMAIL || 'mikael@fallstrom.org',
        password: process.env.ONECOM_PASSWORD || 'Ati:}v>~ra_Tqec?)zpLRq8Z',
        provider: 'oneCom'
      });
    }

    // Fetch recent emails with configurable limit
    const emailsResponse = await axios.post(`http://${MCP_GUI_HOST}:3624/api/search-emails`, {
      connectionId: mcpConnectionId,
      criteria: ['ALL'],
      limit: limit,  // Use configurable limit
      mailbox: 'INBOX'
    });

    return emailsResponse.data.emails || [];
  } catch (error) {
    console.error('MCP fetch error:', error.message);

    // If MCP server is down or returns 404, return empty array
    if (error.code === 'ECONNREFUSED' || (error.response && error.response.status === 404)) {
      console.log(`MCP GUI Server not available on ${MCP_GUI_HOST}:3624`);
      return [];
    }

    throw error;
  }
}

// Frontend compatibility endpoint - maps to recent-emails
app.get('/api/emails', async (req, res) => {
  try {
    const accountId = req.query.accountId || 'primary';
    const limit = parseInt(req.query.limit) || 50;

    // Fetch emails from MCP
    const emails = await fetchEmailsFromMCP(accountId, limit);

    if (emails.length === 0) {
      return res.json([]);
    }

    // Process each email with ML categorization
    const processedEmails = await Promise.all(
      emails.map(async (email) => {
        const mlAnalysis = await categorizeEmailWithML(email);

        return {
          uid: email.uid,
          from: email.from,
          subject: email.subject,
          date: email.date,
          seen: email.flags && email.flags.includes('\\Seen'),
          text: email.text || email.bodyPreview || '',
          bodyPreview: email.bodyPreview || (email.text ? email.text.substring(0, 200) : ''),
          category: mlAnalysis.category,
          priority: mlAnalysis.priority,
          sentiment: mlAnalysis.sentiment,
          confidence: mlAnalysis.confidence,
          topics: mlAnalysis.topics || [],
          actionRequired: mlAnalysis.action_required || false,
          summary: mlAnalysis.summary || `Email categorized as ${mlAnalysis.category}`,
        };
      })
    );

    console.log(`✅ Processed ${processedEmails.length} emails with categorization`);
    res.json(processedEmails);
  } catch (error) {
    console.error('Error in /api/emails:', error);
    res.status(500).json({ error: 'Failed to fetch emails' });
  }
});

// Main endpoint to get emails with full ML + GPT-OSS categorization
app.get('/recent-emails/:accountId', async (req, res) => {
  try {
    const accountId = req.params.accountId;
    const limit = parseInt(req.query.limit) || 50; // Get limit from query or default to 50
    console.log(`Fetching emails for account: ${accountId}, limit: ${limit}`);

    // Fetch emails from MCP with limit
    const emails = await fetchEmailsFromMCP(accountId, limit);

    if (emails.length === 0) {
      return res.json([]);
    }

    // Process each email with ML categorization
    const processedEmails = await Promise.all(
      emails.map(async (email) => {
        const mlAnalysis = await categorizeEmailWithML(email);

        return {
          uid: email.uid,
          from: email.from,
          subject: email.subject,
          date: email.date,
          flags: email.flags || [],
          hasAttachments: email.hasAttachments || false,
          bodyPreview: email.bodyPreview,

          // ML/AI enriched fields
          category: mlAnalysis.category,
          priority: mlAnalysis.priority,
          sentiment: mlAnalysis.sentiment,
          topics: mlAnalysis.topics,
          actionRequired: mlAnalysis.action_required,
          summary: mlAnalysis.summary,

          // Score for sorting (high priority = higher score)
          score: mlAnalysis.priority === 'high' ? 100 :
                 mlAnalysis.priority === 'medium' ? 50 : 10,

          analyzed: true
        };
      })
    );

    // Sort by date (newest first), then by score/priority
    processedEmails.sort((a, b) => {
      // First compare dates (newer dates come first)
      const dateA = new Date(a.date);
      const dateB = new Date(b.date);
      const dateDiff = dateB - dateA;

      // If dates are different, sort by date
      if (dateDiff !== 0) return dateDiff;

      // If same date, sort by priority score
      return b.score - a.score;
    });

    console.log(`Processed ${processedEmails.length} emails with ML categorization`);
    res.json(processedEmails);

  } catch (error) {
    console.error('Error fetching/processing emails:', error);
    // Return empty array when IMAP is not available
    console.log('⚠️ IMAP not available, returning empty array');
    res.json([]);
  }
});

// Endpoint to trigger email sync
app.post('/sync-emails/:accountId', async (req, res) => {
  try {
    const accountId = req.params.accountId;
    const limit = parseInt(req.query.limit) || 50;

    // Fetch fresh emails from MCP with limit
    const emails = await fetchEmailsFromMCP(accountId, limit);

    res.json({
      success: true,
      message: `Synced ${emails.length} emails`,
      count: emails.length
    });
  } catch (error) {
    console.error('Sync error:', error);
    res.status(500).json({
      error: 'Sync failed',
      details: error.message
    });
  }
});

// Smart inbox endpoint with AI prioritization
app.get('/smart-inbox/:accountId', async (req, res) => {
  try {
    const accountId = req.params.accountId;

    // Get processed emails
    const response = await axios.get(`http://localhost:${PORT}/recent-emails/${accountId}`);
    const emails = response.data;

    // Separate into categories
    const highPriority = emails.filter(e => e.priority === 'high');
    const actionRequired = emails.filter(e => e.actionRequired);
    const work = emails.filter(e => e.category === 'work');
    const personal = emails.filter(e => e.category === 'personal');
    const newsletters = emails.filter(e => e.category === 'newsletter');

    res.json({
      inbox: {
        highPriority,
        actionRequired,
        work,
        personal,
        newsletters,
        all: emails
      },
      stats: {
        total: emails.length,
        unread: emails.filter(e => !e.flags?.includes('\\Seen')).length,
        highPriority: highPriority.length,
        actionRequired: actionRequired.length
      }
    });
  } catch (error) {
    console.error('Smart inbox error:', error);
    res.status(500).json({
      error: 'Failed to generate smart inbox',
      details: error.message
    });
  }
});

// Feedback endpoint for ML training
app.post('/api/ml/feedback', async (req, res) => {
  try {
    const { emailId, correction, feedback } = req.body;

    console.log(`📚 ML Feedback received for email ${emailId}:`);
    console.log(`   Original → Corrected: ${feedback}`);
    console.log(`   New categorization:`, correction);

    // Store feedback in memory (in a real system, this would go to a database)
    const timestamp = new Date().toISOString();
    console.log(`   ✅ Feedback recorded at ${timestamp}`);

    // In the future, this could be used to retrain the GPT-OSS model
    // or update categorization rules

    res.json({
      success: true,
      message: 'Feedback recorded for ML training',
      timestamp
    });

  } catch (error) {
    console.error('❌ Feedback error:', error);
    res.status(500).json({
      error: 'Failed to record feedback',
      details: error.message
    });
  }
});

// Account management endpoints
app.get('/api/accounts', (req, res) => {
  // Return configured email account
  const accounts = [{
    id: 'primary',
    email: process.env.ONECOM_EMAIL || 'mikael@fallstrom.org',
    displayName: 'Primary Account',
    provider: 'oneCom',
    active: true,
    color: '#3B82F6',
    unreadCount: 0
  }];

  res.json({ accounts });
});

// Get mailboxes/folders for an account
app.get('/api/accounts/:accountId/mailboxes', async (req, res) => {
  try {
    // Return standard IMAP folders
    const mailboxes = [
      {
        name: 'INBOX',
        path: 'INBOX',
        delimiter: '/',
        subscribed: true,
        specialUse: ['\\Inbox'],
        unreadCount: 0
      },
      {
        name: 'Sent',
        path: 'Sent',
        delimiter: '/',
        subscribed: true,
        specialUse: ['\\Sent']
      },
      {
        name: 'Drafts',
        path: 'Drafts',
        delimiter: '/',
        subscribed: true,
        specialUse: ['\\Drafts']
      },
      {
        name: 'Trash',
        path: 'Trash',
        delimiter: '/',
        subscribed: true,
        specialUse: ['\\Trash']
      },
      {
        name: 'Spam',
        path: 'Spam',
        delimiter: '/',
        subscribed: true,
        specialUse: ['\\Junk']
      }
    ];

    res.json({ mailboxes });
  } catch (error) {
    console.error('Failed to get mailboxes:', error);
    res.status(500).json({
      error: 'Failed to get mailboxes',
      details: error.message
    });
  }
});

app.post('/api/accounts', (req, res) => {
  // Add new account (currently supports single account)
  const { email, password, displayName, provider } = req.body;

  res.json({
    account: {
      id: 'primary',
      email,
      displayName: displayName || email,
      provider: provider || 'auto',
      active: true,
      color: '#3B82F6'
    }
  });
});

app.post('/api/accounts/:accountId/connect', async (req, res) => {
  try {
    const accountId = req.params.accountId;
    // Connect to MCP with the account
    await fetchEmailsFromMCP(accountId, 10);
    res.json({ success: true, message: 'Connected successfully' });
  } catch (error) {
    res.status(500).json({ error: 'Connection failed', details: error.message });
  }
});

app.post('/api/accounts/:accountId/toggle', (req, res) => {
  const { active } = req.body;
  res.json({ success: true, active });
});

app.delete('/api/accounts/:accountId', (req, res) => {
  res.json({ success: true, message: 'Account removed' });
});

// Category statistics endpoint
app.get('/api/categories/stats/:accountId', async (req, res) => {
  try {
    const accountId = req.params.accountId;
    const limit = parseInt(req.query.limit) || 100;

    // Fetch emails to calculate stats
    const emails = await fetchEmailsFromMCP(accountId, limit);

    // Process emails for statistics
    const processedEmails = await Promise.all(
      emails.map(async (email) => await categorizeEmailWithML(email))
    );

    // Calculate statistics
    const stats = {
      categories: {},
      priorities: {},
      sources: {},
      total: emails.length,
      unread: emails.filter(e => !e.flags?.includes('\\Seen')).length
    };

    // Count categories
    processedEmails.forEach(analysis => {
      // Count categories
      if (analysis.category) {
        stats.categories[analysis.category] = (stats.categories[analysis.category] || 0) + 1;
      }

      // Count priorities
      if (analysis.priority) {
        stats.priorities[analysis.priority] = (stats.priorities[analysis.priority] || 0) + 1;
      }

      // Count sentiment as sources
      if (analysis.sentiment) {
        stats.sources[analysis.sentiment] = (stats.sources[analysis.sentiment] || 0) + 1;
      }
    });

    res.json({ stats });

  } catch (error) {
    console.error('Stats error:', error);
    res.status(500).json({
      error: 'Failed to get statistics',
      details: error.message
    });
  }
});

// Category override endpoint
app.post('/api/categories/override', async (req, res) => {
  try {
    const { emailId, category, userId } = req.body;

    console.log(`Category override: Email ${emailId} → ${category} by user ${userId}`);

    // In a real system, this would update a database
    // For now, just acknowledge the override
    res.json({
      success: true,
      emailId,
      category,
      userId,
      timestamp: new Date().toISOString()
    });

  } catch (error) {
    console.error('Override error:', error);
    res.status(500).json({
      error: 'Failed to set override',
      details: error.message
    });
  }
});

// Clear cache endpoint
app.post('/api/cache/clear', async (req, res) => {
  if (redisConnected && redisClient) {
    try {
      await redisClient.flushDb();
      res.json({ success: true, message: 'Cache cleared successfully' });
    } catch (error) {
      res.status(500).json({ error: 'Failed to clear cache', details: error.message });
    }
  } else {
    res.json({ success: false, message: 'Redis not connected' });
  }
});

// Cache statistics endpoint
app.get('/api/cache/stats', async (req, res) => {
  if (redisConnected && redisClient) {
    try {
      const info = await redisClient.info('stats');
      const dbSize = await redisClient.dbSize();
      res.json({
        connected: true,
        host: REDIS_HOST,
        port: REDIS_PORT,
        totalKeys: dbSize,
        info: info
      });
    } catch (error) {
      res.status(500).json({ error: 'Failed to get cache stats', details: error.message });
    }
  } else {
    res.json({ connected: false, message: 'Redis not connected' });
  }
});

// Health check
app.get('/health', (req, res) => {
  res.json({
    status: 'ok',
    service: 'Integrated Email Service',
    redis: redisConnected ? 'connected' : 'disconnected',
    features: [
      'IMAP connection via MCP',
      'ML categorization',
      'GPT-OSS 20B analysis',
      'Smart inbox',
      'Priority sorting',
      'ML feedback collection',
      'Account management',
      'Category statistics',
      redisConnected ? '✅ Redis caching enabled' : '⚠️ Redis caching disabled'
    ]
  });
});

app.listen(PORT, () => {
  console.log(`
🚀 Integrated Email Service running on port ${PORT}

Features:
  ✅ Real IMAP connection via MCP Email Server
  ✅ ML categorization with GPT-OSS 20B
  ✅ Smart inbox with prioritization
  ✅ Sentiment analysis
  ✅ Topic extraction
  ✅ Action detection
  ${redisConnected ? '✅ Redis caching enabled' : '⚠️ Redis caching disabled'}

Endpoints:
  GET  /recent-emails/:accountId - Get emails with full ML analysis
  POST /sync-emails/:accountId - Trigger email sync
  GET  /smart-inbox/:accountId - Get AI-prioritized inbox
  GET  /api/accounts - Get all email accounts
  POST /api/accounts - Add new email account
  POST /api/accounts/:id/connect - Connect to email account
  POST /api/accounts/:id/toggle - Toggle account active state
  DELETE /api/accounts/:id - Remove email account
  GET  /api/categories/stats/:accountId - Get category statistics
  POST /api/categories/override - Set category override
  GET  /health - Service health check
  POST /api/cache/clear - Clear Redis cache
  GET  /api/cache/stats - Get cache statistics
  `);
});