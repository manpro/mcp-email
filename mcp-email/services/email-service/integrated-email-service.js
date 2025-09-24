const express = require('express');
const cors = require('cors');
const axios = require('axios'); // Still needed for AI/LLM API calls
const redis = require('redis');
const Bull = require('bull');
const { createServer } = require('http');
const { Server: SocketServer } = require('socket.io');
const EmailAIAnalyzer = require('./ai-analyzer');
const EmailDatabase = require('./database');
const IMAPService = require('./imap-service');
const FlexibleEmailAIAnalyzer = require('./flexible-ai-analyzer');
const MLTrainingPipeline = require('./ml-training-pipeline');
require('dotenv').config();

const app = express();
const PORT = process.env.PORT || 3012;

app.use(cors());
app.use(express.json());

// Create HTTP server and Socket.IO
const httpServer = createServer(app);
const io = new SocketServer(httpServer, {
  cors: {
    origin: "*",
    methods: ["GET", "POST"]
  }
});

// WebSocket connection handling
io.on('connection', (socket) => {
  console.log(`📡 WebSocket client connected: ${socket.id}`);

  socket.on('disconnect', () => {
    console.log(`📡 WebSocket client disconnected: ${socket.id}`);
  });
});

// Global WebSocket instance for sending updates
global.wsIo = io;

// Redis client setup
const REDIS_HOST = process.env.REDIS_HOST || '172.17.0.1';
const REDIS_PORT = process.env.REDIS_PORT || 6381;
let redisClient = null;
let redisConnected = false;

// IMAP service instance
const imapService = new IMAPService();
let imapConnected = false;

// Bull queue for ML processing
let mlProcessingQueue = null;

// Initialize Redis connection and Bull queue
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

    // Initialize Bull queue for ML processing
    mlProcessingQueue = new Bull('ml-processing', {
      redis: {
        host: REDIS_HOST,
        port: REDIS_PORT
      }
    });
    console.log('✅ Bull queue initialized for ML processing');

  } catch (error) {
    console.warn('⚠️ Redis connection failed, running without cache:', error.message);
    redisConnected = false;
  }
})();

// Initialize IMAP connection
(async () => {
  try {
    await imapService.connect();
    imapConnected = true;
    console.log('✅ IMAP service connected');
  } catch (error) {
    console.error('❌ IMAP connection failed:', error.message);
    imapConnected = false;
  }
})();

// AI Analyzer instance for GPT-OSS integration
const aiAnalyzer = new EmailAIAnalyzer();

// Flexible AI analyzer with multi-provider support
const flexibleAnalyzer = new FlexibleEmailAIAnalyzer('./llm-config.json');

// Database instance for persistent storage
const emailDb = new EmailDatabase();

// ML Training Pipeline - GPT-OSS teaches ML model
const mlPipeline = new MLTrainingPipeline(flexibleAnalyzer, emailDb);

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
    // Use ML Training Pipeline with GPT-OSS as teacher
    // This will:
    // 1. Make ML prediction
    // 2. Get GPT-OSS ground truth
    // 3. Learn from the difference
    // 4. Return best prediction based on confidence
    const result = await mlPipeline.processEmailWithLearning(email);

    // Save to database for persistence
    await emailDb.saveCategorization(email, result);

    // Cache in Redis for fast access
    if (redisConnected && redisClient) {
      const cacheKey = getCacheKey(email);
      try {
        await redisClient.setEx(cacheKey, 86400, JSON.stringify(result));
        console.log(`💾 Cached ML result for: ${email.subject?.substring(0, 30)}...`);
      } catch (cacheError) {
        console.warn('Cache write error:', cacheError.message);
      }
    }

    return result;
  } catch (error) {
    console.error('ML Pipeline error:', error.message);
    // Fallback to rule-based if ML pipeline fails
    return getRuleBasedCategorization(email);
  }
}

// Legacy function - direct LLM categorization without ML learning
async function categorizeEmailWithMLDirect(email) {
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

// Fetch emails directly from IMAP server
async function fetchEmailsFromSource(connectionId, limit = 50) {
  try {
    // Ensure IMAP is connected
    if (!imapConnected) {
      console.log('📧 Reconnecting to IMAP server...');
      await imapService.connect();
      imapConnected = true;
    }

    // Fetch recent emails directly from IMAP
    const emails = await imapService.fetchRecent(limit);

    console.log(`✅ Fetched ${emails.length} emails from IMAP`);
    return emails || [];

  } catch (error) {
    console.error('❌ IMAP fetch error:', error.message);

    // Try to reconnect once if connection was lost
    if (error.message.includes('Not connected') || error.message.includes('connection')) {
      try {
        console.log('🔄 Attempting to reconnect to IMAP...');
        await imapService.connect();
        imapConnected = true;
        const emails = await imapService.fetchRecent(limit);
        return emails || [];
      } catch (reconnectError) {
        console.error('❌ Reconnection failed:', reconnectError.message);
        imapConnected = false;
        return [];
      }
    }

    return [];
  }
}

// Frontend compatibility endpoint - maps to recent-emails
app.get('/api/emails', async (req, res) => {
  try {
    const accountId = req.query.accountId || 'primary';
    const limit = parseInt(req.query.limit) || 50;

    // Fetch emails from MCP
    const emails = await fetchEmailsFromSource(accountId, limit);

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
    const limit = parseInt(req.query.limit) || 500; // Get limit from query or default to 500
    console.log(`Fetching emails for account: ${accountId}, limit: ${limit}`);

    // Fetch emails from MCP with limit
    const emails = await fetchEmailsFromSource(accountId, limit);

    if (emails.length === 0) {
      return res.json([]);
    }

    // Return emails immediately with cached ML data (if available)
    // Process uncached emails in background
    const processedEmails = await Promise.all(
      emails.map(async (email) => {
        // Try to get cached ML analysis first
        let mlAnalysis = null;

        try {
          // Check database first
          mlAnalysis = await emailDb.getCategorization(email);

          // If not in database, check Redis cache
          if (!mlAnalysis && redisConnected && redisClient) {
            const cacheKey = getCacheKey(email);
            const cached = await redisClient.get(cacheKey);
            if (cached) {
              mlAnalysis = JSON.parse(cached);
            }
          }
        } catch (cacheError) {
          console.warn('Cache read error:', cacheError.message);
        }

        // If no cached data, use basic fallback and schedule ML processing
        if (!mlAnalysis) {
          mlAnalysis = getRuleBasedCategorization(email);
          // Schedule background ML processing (non-blocking)
          setImmediate(() => {
            categorizeEmailWithML(email).catch(error =>
              console.warn('Background ML processing failed:', error.message)
            );
          });
        }

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

          analyzed: !!mlAnalysis.category // true if ML analyzed, false if rule-based
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

    console.log(`Returned ${processedEmails.length} emails (${processedEmails.filter(e => e.analyzed).length} ML-analyzed)`);
    res.json(processedEmails);

  } catch (error) {
    console.error('Error fetching/processing emails:', error);
    // Return empty array when IMAP is not available
    console.log('⚠️ IMAP not available, returning empty array');
    res.json([]);
  }
});

// Endpoint to get ML analysis for specific emails
app.post('/api/emails/ml-status', async (req, res) => {
  try {
    const { uids } = req.body; // Array of email UIDs to check
    const results = {};

    for (const uid of uids) {
      // Check if we have ML analysis cached or in DB
      const cacheKey = `email:${uid}:ml`;

      if (redisConnected && redisClient) {
        try {
          const cached = await redisClient.get(cacheKey);
          if (cached) {
            results[uid] = JSON.parse(cached);
          }
        } catch (err) {
          console.warn(`Cache lookup failed for ${uid}:`, err.message);
        }
      }

      // Check database if not in cache
      if (!results[uid]) {
        const dbResult = await emailDb.getCategorization({ uid });
        if (dbResult) {
          results[uid] = dbResult;
        }
      }
    }

    res.json({ mlResults: results });
  } catch (error) {
    console.error('Error getting ML status:', error);
    res.status(500).json({ error: 'Failed to get ML status' });
  }
});

// Frontend-compatible endpoint at /api/recent-emails
app.get('/api/recent-emails', async (req, res) => {
  try {
    const accountId = 'default'; // Default account
    const limit = parseInt(req.query.limit) || 500;
    console.log(`Frontend API: Fetching emails, limit: ${limit}`);

    // Fetch emails from MCP
    const emails = await fetchEmailsFromSource(accountId, limit);

    if (emails.length === 0) {
      return res.json({ emails: [] });
    }

    // Return emails IMMEDIATELY with basic info
    const quickEmails = emails.map(email => ({
      uid: email.uid,
      from: email.from,
      subject: email.subject,
      date: email.date,
      text: email.text || email.bodyPreview || '',
      html: email.html || '',
      body: email.text || email.html || email.bodyPreview || '',
      bodyPreview: email.bodyPreview || (email.text ? email.text.substring(0, 200) : ''),
      flags: email.flags || [],
      hasAttachments: email.hasAttachments || false,
      attachments: email.attachments || [],
      // Default ML values - will be updated async
      category: 'other',
      priority: 'medium',
      sentiment: 'neutral',
      summary: `Email from: ${email.from?.substring(0, 30)}`,
      score: 50,
      analyzed: false  // Mark as not yet analyzed
    }));

    // Sort by date (newest first)
    quickEmails.sort((a, b) => {
      const dateA = new Date(a.date);
      const dateB = new Date(b.date);
      return dateB - dateA;
    });

    console.log(`Frontend API: Returning ${quickEmails.length} emails immediately`);
    res.json({ emails: quickEmails });

    // Send WebSocket notification for new emails
    if (global.wsIo) {
      global.wsIo.emit('emails-updated', {
        count: quickEmails.length,
        timestamp: Date.now()
      });
    }

    // Add emails to ML processing queue (non-blocking)
    if (mlProcessingQueue) {
      console.log('📋 Adding emails to ML processing queue...');

      // Add each email to the queue with priority
      for (const email of emails) {
        try {
          // Determine priority based on email characteristics
          let priority = 10; // Default priority

          // Higher priority for recent emails
          const emailAge = Date.now() - new Date(email.date).getTime();
          if (emailAge < 86400000) priority = 5; // Less than 24 hours old
          if (emailAge < 3600000) priority = 1; // Less than 1 hour old

          // Add to queue
          await mlProcessingQueue.add(
            {
              emailUid: email.uid,
              emailData: {
                uid: email.uid,
                from: email.from,
                subject: email.subject,
                text: email.text,
                html: email.html,
                bodyPreview: email.bodyPreview,
                date: email.date
              },
              priority
            },
            {
              priority,
              attempts: 3,
              backoff: {
                type: 'exponential',
                delay: 2000
              },
              removeOnComplete: true,
              removeOnFail: false
            }
          );
        } catch (error) {
          console.error(`Failed to queue email ${email.uid}:`, error.message);
        }
      }

      console.log(`✅ Added ${emails.length} emails to ML processing queue`);
    } else {
      console.warn('⚠️ ML processing queue not available - processing inline');

      // Fallback to inline processing if queue not available
      setImmediate(async () => {
        console.log('🤖 Starting background ML categorization...');
        const batchSize = 2;

        for (let i = 0; i < emails.length; i += batchSize) {
          const batch = emails.slice(i, Math.min(i + batchSize, emails.length));
          console.log(`Background: Processing batch ${Math.floor(i/batchSize) + 1}/${Math.ceil(emails.length/batchSize)}`);

          try {
            await Promise.all(
              batch.map(async (email) => {
                const mlAnalysis = await categorizeEmailWithML(email);
                console.log(`✅ ML categorized: ${email.subject?.substring(0, 30)}... as ${mlAnalysis.category}`);

                // Cache the ML result for the frontend to fetch later
                if (redisConnected && redisClient && email.uid) {
                  const cacheKey = `email:${email.uid}:ml`;
                  try {
                    await redisClient.setEx(cacheKey, 86400, JSON.stringify(mlAnalysis));
                  } catch (cacheErr) {
                    console.warn('Failed to cache ML result:', cacheErr.message);
                  }
                }
              })
            );
          } catch (err) {
            console.error('Background ML error:', err.message);
          }
        }
        console.log('✅ Background ML categorization completed');
      });
    }

  } catch (error) {
    console.error('Frontend API Error:', error);
    res.json({ emails: [] });
  }
});

// Endpoint to trigger email sync
app.post('/sync-emails/:accountId', async (req, res) => {
  try {
    const accountId = req.params.accountId;
    const limit = parseInt(req.query.limit) || 50;

    // Fetch fresh emails from MCP with limit
    const emails = await fetchEmailsFromSource(accountId, limit);

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

// Get single email with full content
app.get('/accounts/:accountId/emails/:uid', async (req, res) => {
  try {
    const { accountId, uid } = req.params;
    console.log(`📧 Fetching email ${uid} for account ${accountId}`);

    // Ensure IMAP is connected
    if (!imapConnected) {
      console.log('📧 Reconnecting to IMAP server...');
      await imapService.connect();
      imapConnected = true;
    }

    // Fetch the specific email by UID
    const email = await imapService.fetchEmailByUid(parseInt(uid));

    if (!email) {
      return res.status(404).json({ error: 'Email not found' });
    }

    // Add account ID to the email object
    email.accountId = accountId;

    console.log(`✅ Fetched email: ${email.subject}`);
    res.json(email);

  } catch (error) {
    console.error('❌ Error fetching email:', error.message);
    res.status(500).json({
      error: 'Failed to fetch email',
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
    await fetchEmailsFromSource(accountId, 10);
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
    const limit = parseInt(req.query.limit) || 500;

    // Fetch emails to calculate stats
    const emails = await fetchEmailsFromSource(accountId, limit);

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
    const { emailId, category, userId, priority = 'medium' } = req.body;

    console.log(`Category override: Email ${emailId} → ${category} by user ${userId}`);

    // Get the email from cache or recent emails
    let email = null;
    try {
      // Try to find the email in recent cache
      const recentEmails = await fetchEmailsFromSource(1, 50);
      email = recentEmails.find(e => e.uid == emailId);
    } catch (err) {
      console.log('Could not fetch email for training:', err);
    }

    if (email && mlPipeline) {
      // Create a "ground truth" from user's correction
      const userCorrection = {
        category: category,
        priority: priority || email.priority || 'medium',
        provider: 'User-Override',
        confidence: 1.0,  // User corrections are 100% confident
        sentiment: email.sentiment || 'neutral',
        actionRequired: email.actionRequired || false,
        summary: `User categorized as ${category}`
      };

      // Train ML with user's correction as ground truth
      // This teaches ML that the user's categorization is correct
      await mlPipeline.learnFromUserFeedback(email, userCorrection);

      console.log(`🎯 ML trained with user feedback: ${category}`);
    }

    // Save the override in database for future reference
    if (emailDb && emailDb.saveCategorization) {
      await emailDb.saveCategorization(
        { ...email, uid: emailId },
        {
          category,
          priority,
          overriddenBy: userId,
          overriddenAt: new Date().toISOString()
        }
      );
    }

    res.json({
      success: true,
      emailId,
      category,
      userId,
      mlTrained: true,
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

// ML Training statistics endpoint
app.get('/ml-stats', (req, res) => {
  const stats = mlPipeline.getStats();
  res.json({
    mlModel: {
      trainingCount: stats.trainingCount,
      accuracy: `${(stats.accuracy * 100).toFixed(1)}%`,
      lastTraining: stats.lastTraining ? new Date(stats.lastTraining).toISOString() : 'Never',
      canWorkIndependently: stats.canWorkIndependently,
      confidenceThreshold: `${(stats.confidenceThreshold * 100).toFixed(0)}%`,
      status: stats.canWorkIndependently ?
        '✅ ML can work independently' :
        `🧠 Learning mode (${stats.trainingCount}/100 samples)`
    },
    categories: stats.categoryConfidence,
    message: stats.trainingCount < 100 ?
      `GPT-OSS is teaching ML. ${100 - stats.trainingCount} more emails needed for independence.` :
      stats.accuracy >= 0.9 ?
        'ML is ready to work independently with GPT-OSS validation.' :
        `ML accuracy ${(stats.accuracy * 100).toFixed(1)}% - still learning from GPT-OSS.`
  });
});

// Custom Categories API Endpoints
app.get('/api/custom-categories/:userId', async (req, res) => {
  try {
    const userId = req.params.userId;
    const cacheKey = `custom_categories:${userId}`;

    // Try to get from Redis cache first
    if (redisConnected && redisClient) {
      try {
        const cached = await redisClient.get(cacheKey);
        if (cached) {
          return res.json(JSON.parse(cached));
        }
      } catch (error) {
        console.warn('Redis get error:', error.message);
      }
    }

    // Return empty array if no database connection (for now)
    // In the future, this could be stored in SQLite or other database
    const customCategories = [];

    // Cache the result
    if (redisConnected && redisClient) {
      try {
        await redisClient.setEx(cacheKey, 3600, JSON.stringify(customCategories));
      } catch (error) {
        console.warn('Redis set error:', error.message);
      }
    }

    res.json(customCategories);
  } catch (error) {
    console.error('Error fetching custom categories:', error);
    res.status(500).json({ error: 'Failed to fetch custom categories' });
  }
});

app.post('/api/custom-categories/:userId', async (req, res) => {
  try {
    const userId = req.params.userId;
    const category = req.body;
    const cacheKey = `custom_categories:${userId}`;

    // Validate category data
    if (!category.id || !category.name || !category.icon || !category.color) {
      return res.status(400).json({
        error: 'Invalid category data. Required: id, name, icon, color'
      });
    }

    // Get existing categories
    let categories = [];
    if (redisConnected && redisClient) {
      try {
        const cached = await redisClient.get(cacheKey);
        if (cached) {
          categories = JSON.parse(cached);
        }
      } catch (error) {
        console.warn('Redis get error:', error.message);
      }
    }

    // Add new category
    const newCategory = {
      ...category,
      createdAt: new Date().toISOString(),
      userId
    };

    // Check if category already exists
    const existingIndex = categories.findIndex(cat => cat.id === category.id);
    if (existingIndex >= 0) {
      categories[existingIndex] = newCategory;
    } else {
      categories.push(newCategory);
    }

    // Save back to cache
    if (redisConnected && redisClient) {
      try {
        await redisClient.setEx(cacheKey, 3600, JSON.stringify(categories));
      } catch (error) {
        console.warn('Redis set error:', error.message);
      }
    }

    console.log(`✅ Custom category saved: ${category.name} for user ${userId}`);
    res.json({ success: true, category: newCategory });
  } catch (error) {
    console.error('Error saving custom category:', error);
    res.status(500).json({ error: 'Failed to save custom category' });
  }
});

app.delete('/api/custom-categories/:userId/:categoryId', async (req, res) => {
  try {
    const { userId, categoryId } = req.params;
    const cacheKey = `custom_categories:${userId}`;

    // Get existing categories
    let categories = [];
    if (redisConnected && redisClient) {
      try {
        const cached = await redisClient.get(cacheKey);
        if (cached) {
          categories = JSON.parse(cached);
        }
      } catch (error) {
        console.warn('Redis get error:', error.message);
      }
    }

    // Remove category
    const filteredCategories = categories.filter(cat => cat.id !== categoryId);

    // Save back to cache
    if (redisConnected && redisClient) {
      try {
        await redisClient.setEx(cacheKey, 3600, JSON.stringify(filteredCategories));
      } catch (error) {
        console.warn('Redis set error:', error.message);
      }
    }

    console.log(`🗑️ Custom category deleted: ${categoryId} for user ${userId}`);
    res.json({ success: true, deletedId: categoryId });
  } catch (error) {
    console.error('Error deleting custom category:', error);
    res.status(500).json({ error: 'Failed to delete custom category' });
  }
});

// Health check
app.get('/health', (req, res) => {
  const mlStats = mlPipeline.getStats();
  res.json({
    status: 'ok',
    service: 'Integrated Email Service with ML Training',
    redis: redisConnected ? 'connected' : 'disconnected',
    mlStatus: {
      mode: mlStats.canWorkIndependently ? 'independent' : 'learning',
      accuracy: `${(mlStats.accuracy * 100).toFixed(1)}%`,
      samples: mlStats.trainingCount
    },
    features: [
      'IMAP connection via MCP',
      'ML categorization with GPT-OSS teacher',
      'Dual prediction system',
      'Real-time ML training',
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

// QUICK FIX: API Compatibility Routes - Proxy missing /api endpoints
// This ensures frontend can call /api/recent-emails and /api/health

// Proxy /api/recent-emails to existing /recent-emails
app.get('/api/recent-emails/:accountId', async (req, res) => {
  try {
    const accountId = req.params.accountId;
    const limit = parseInt(req.query.limit) || 500;
    console.log(`[API PROXY] /api/recent-emails/${accountId} -> /recent-emails/${accountId}`);

    // Fetch emails from MCP with limit
    const emails = await fetchEmailsFromSource(accountId, limit);

    if (emails.length === 0) {
      return res.json([]);
    }

    // Return emails immediately with cached ML data (if available)
    const processedEmails = await Promise.all(
      emails.map(async (email) => {
        let mlAnalysis = null;

        try {
          // Check database first
          mlAnalysis = await emailDb.getCategorization(email);

          // If not in database, check Redis cache
          if (!mlAnalysis && redisConnected && redisClient) {
            const cacheKey = getCacheKey(email);
            const cached = await redisClient.get(cacheKey);
            if (cached) {
              mlAnalysis = JSON.parse(cached);
            }
          }
        } catch (cacheError) {
          console.warn('Cache read error:', cacheError.message);
        }

        // If no cached data, use basic fallback and schedule ML processing
        if (!mlAnalysis) {
          mlAnalysis = getRuleBasedCategorization(email);
          // Schedule background ML processing (non-blocking)
          setImmediate(() => {
            categorizeEmailWithML(email).catch(error =>
              console.warn('Background ML processing failed:', error.message)
            );
          });
        }

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

          analyzed: !!mlAnalysis.category
        };
      })
    );

    // Sort by date (newest first), then by score/priority
    processedEmails.sort((a, b) => {
      const dateA = new Date(a.date);
      const dateB = new Date(b.date);
      const dateDiff = dateB - dateA;
      if (dateDiff !== 0) return dateDiff;
      return b.score - a.score;
    });

    console.log(`[API PROXY] Returned ${processedEmails.length} emails (${processedEmails.filter(e => e.analyzed).length} ML-analyzed)`);
    res.json(processedEmails);

  } catch (error) {
    console.error('[API PROXY] Error fetching/processing emails:', error);
    res.json([]);
  }
});

// Proxy /api/health to existing /health
app.get('/api/health', (req, res) => {
  console.log('[API PROXY] /api/health -> /health');
  const mlStats = mlPipeline.getStats();
  res.json({
    status: 'ok',
    service: 'Integrated Email Service with ML Training',
    redis: redisConnected ? 'connected' : 'disconnected',
    mlStatus: {
      mode: mlStats.canWorkIndependently ? 'independent' : 'learning',
      accuracy: `${(mlStats.accuracy * 100).toFixed(1)}%`,
      samples: mlStats.trainingCount
    },
    features: [
      'IMAP connection via MCP',
      'ML categorization with GPT-OSS teacher',
      'Dual prediction system',
      'Real-time ML training',
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

httpServer.listen(PORT, () => {
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
  GET  /api/custom-categories/:userId - Get custom categories
  POST /api/custom-categories/:userId - Create/update custom category
  DELETE /api/custom-categories/:userId/:categoryId - Delete custom category
  GET  /health - Service health check
  POST /api/cache/clear - Clear Redis cache
  GET  /api/cache/stats - Get cache statistics
  `);
});