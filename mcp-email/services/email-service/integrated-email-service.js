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

// Helper function for getting recent emails (used by folder suggestions)
async function getRecentEmails(accountId, limit = 100) {
  try {
    console.log(`📬 Fetching ${limit} emails for account: ${accountId}`);

    if (!imapConnected) {
      console.log('⚠️ IMAP not connected, attempting to connect...');
      await imapService.connect();
      imapConnected = true;
    }

    const emails = await imapService.fetchRecent(limit);
    console.log(`✅ Fetched ${emails?.length || 0} emails from IMAP`);

    return emails || [];
  } catch (error) {
    console.error('❌ Error in getRecentEmails:', error.message);
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

// Category statistics endpoint - OPTIMIZED
app.get('/api/categories/stats/:accountId', async (req, res) => {
  try {
    const accountId = req.params.accountId;
    const limit = parseInt(req.query.limit) || 500;

    console.log(`📊 Getting category stats for ${accountId}, limit: ${limit}`);

    // Check Redis cache first
    const cacheKey = `stats:${accountId}:${limit}`;
    if (redisClient) {
      try {
        const cachedStats = await redisClient.get(cacheKey);
        if (cachedStats) {
          console.log('🎯 Using cached stats');
          return res.json({ stats: JSON.parse(cachedStats), cached: true });
        }
      } catch (cacheError) {
        console.log('Cache read error, proceeding with fresh calculation');
      }
    }

    // Fetch emails to calculate stats
    const emails = await fetchEmailsFromSource(accountId, limit);
    console.log(`📬 Processing ${emails.length} emails for stats`);

    // Initialize statistics
    const stats = {
      categories: {},
      priorities: {},
      sources: {},
      total: emails.length,
      unread: emails.filter(e => !e.flags?.includes('\\Seen')).length
    };

    // OPTIMIZED: Process emails in smaller batches to avoid overwhelming ML service
    const BATCH_SIZE = 20; // Process 20 emails at a time
    const processedEmails = [];

    for (let i = 0; i < emails.length; i += BATCH_SIZE) {
      const batch = emails.slice(i, i + BATCH_SIZE);
      console.log(`🔄 Processing batch ${Math.floor(i/BATCH_SIZE) + 1}/${Math.ceil(emails.length/BATCH_SIZE)}`);

      // Check cache for each email first
      const batchResults = await Promise.all(
        batch.map(async (email) => {
          const emailCacheKey = `ml:${email.uid || email.id}`;

          if (redisClient) {
            try {
              const cachedAnalysis = await redisClient.get(emailCacheKey);
              if (cachedAnalysis) {
                return JSON.parse(cachedAnalysis);
              }
            } catch (cacheError) {
              console.log(`Cache miss for email ${email.uid || email.id}`);
            }
          }

          // If not cached, use basic classification without ML
          return {
            category: classifyEmailBasic(email),
            priority: 'medium',
            sentiment: 'neutral'
          };
        })
      );

      processedEmails.push(...batchResults);

      // Small delay to prevent overwhelming the system
      await new Promise(resolve => setTimeout(resolve, 100));
    }

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

    // Cache the results for 5 minutes
    if (redisClient) {
      try {
        await redisClient.setex(cacheKey, 300, JSON.stringify(stats));
        console.log('📦 Stats cached for 5 minutes');
      } catch (cacheError) {
        console.log('Cache write error:', cacheError.message);
      }
    }

    console.log(`✅ Stats calculated: ${Object.keys(stats.categories).length} categories, ${stats.total} total emails`);
    res.json({ stats });

  } catch (error) {
    console.error('❌ Stats error:', error);
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

// ENHANCED CATEGORY MANAGEMENT APIs

// ML Training signal endpoint - learns from user feedback
app.post('/api/ml/training-signal', async (req, res) => {
  try {
    const {
      emailUid,
      fromCategory,
      toCategory,
      mlSuggestion,
      mlConfidence,
      userAction,
      timestamp
    } = req.body;

    console.log(`🎯 Training signal: ${userAction} - ${fromCategory} → ${toCategory} (ML suggested: ${mlSuggestion}, confidence: ${mlConfidence})`);

    // Store training data
    const trainingData = {
      emailUid,
      fromCategory,
      toCategory,
      mlSuggestion,
      mlConfidence,
      userAction,
      timestamp: new Date(timestamp || Date.now())
    };

    // Save to database for ML learning
    if (emailDb && emailDb.saveTrainingSignal) {
      await emailDb.saveTrainingSignal(trainingData);
    }

    // If user consistently corrects ML, adjust confidence
    if (mlPipeline && userAction === 'suggestion_reject') {
      await mlPipeline.adjustConfidenceForPattern(emailUid, -0.1);
    } else if (userAction === 'suggestion_accept') {
      await mlPipeline.adjustConfidenceForPattern(emailUid, 0.1);
    }

    res.json({ success: true, recorded: true });
  } catch (error) {
    console.error('Error recording training signal:', error);
    res.status(500).json({ error: 'Failed to record training signal' });
  }
});

// Auto-rule creation endpoint
app.post('/api/rules/create', async (req, res) => {
  try {
    const { trigger, action, confidence_required = 0.90 } = req.body;

    const rule = {
      id: `rule_${Date.now()}`,
      trigger,
      action,
      confidenceRequired: confidence_required,
      createdAt: new Date(),
      usageCount: 0,
      enabled: true
    };

    // Save rule to cache
    const rulesKey = 'auto_rules';
    if (redisConnected && redisClient) {
      try {
        const existing = await redisClient.get(rulesKey) || '[]';
        const rules = JSON.parse(existing);
        rules.push(rule);
        await redisClient.set(rulesKey, JSON.stringify(rules));
      } catch (error) {
        console.warn('Redis rule save error:', error.message);
      }
    }

    console.log(`📋 Auto-rule created: ${trigger.type}=${trigger.value} → ${action.category}`);
    res.json({ success: true, rule });
  } catch (error) {
    console.error('Error creating auto rule:', error);
    res.status(500).json({ error: 'Failed to create auto rule' });
  }
});

// === PHASE 2: SMART FOLDER MANAGEMENT APIs ===

// Get folder suggestions based on email patterns
app.get('/api/folders/suggestions', async (req, res) => {
  try {
    console.log('🎯 Getting smart folder suggestions...');

    // Get recent emails to analyze patterns
    const recentEmails = await getRecentEmails('primary', 100);

    const suggestions = [];
    const senderFolderMap = new Map();
    const categoryFolderMap = new Map();

    // Analyze email patterns
    for (const email of recentEmails) {
      const domain = email.from ? email.from.split('@')[1] : null;
      const category = email.mlAnalysis?.category || 'other';

      if (domain) {
        if (!senderFolderMap.has(domain)) {
          senderFolderMap.set(domain, []);
        }
        senderFolderMap.get(domain).push(email);
      }

      if (!categoryFolderMap.has(category)) {
        categoryFolderMap.set(category, []);
      }
      categoryFolderMap.get(category).push(email);
    }

    // Generate sender-based folder suggestions
    for (const [domain, emails] of senderFolderMap) {
      if (emails.length >= 5) {
        const companyName = domain.split('.')[0];
        const displayName = companyName.charAt(0).toUpperCase() + companyName.slice(1);

        suggestions.push({
          type: 'sender_folder',
          folderName: displayName,
          folderPath: `Senders/${displayName}`,
          reason: `${emails.length} emails från ${domain}`,
          emailIds: emails.map(e => e.uid),
          confidence: Math.min(emails.length / 10, 0.95),
          category: 'sender',
          estimatedEmails: emails.length
        });
      }
    }

    // Generate category-based folder suggestions
    for (const [category, emails] of categoryFolderMap) {
      if (emails.length >= 10 && category !== 'other') {
        const displayNames = {
          newsletter: 'Nyhetsbrev',
          work: 'Arbete',
          invoice: 'Fakturor',
          security: 'Säkerhet',
          meetings: 'Möten',
          social: 'Socialt',
          personal: 'Personligt'
        };

        const displayName = displayNames[category] || category;

        suggestions.push({
          type: 'category_folder',
          folderName: displayName,
          folderPath: `Categories/${displayName}`,
          reason: `${emails.length} emails i kategori ${category}`,
          emailIds: emails.map(e => e.uid),
          confidence: Math.min(emails.length / 20, 0.90),
          category: category,
          estimatedEmails: emails.length
        });
      }
    }

    // Sort by confidence and limit results
    const sortedSuggestions = suggestions
      .sort((a, b) => b.confidence - a.confidence)
      .slice(0, 8);

    console.log(`✅ Generated ${sortedSuggestions.length} folder suggestions`);
    res.json({ suggestions: sortedSuggestions });

  } catch (error) {
    console.error('❌ Error generating folder suggestions:', error);
    res.status(500).json({ error: error.message, suggestions: [] });
  }
});

// Get folder structure
app.get('/api/folders', async (req, res) => {
  try {
    console.log('📁 Getting folder structure...');

    // Mock folder structure - in production this would come from IMAP
    const folders = [
      {
        name: 'INBOX',
        path: 'INBOX',
        unreadCount: 156,
        children: []
      },
      {
        name: 'Sent',
        path: 'Sent',
        unreadCount: 0,
        children: []
      },
      {
        name: 'Archive',
        path: 'Archive',
        unreadCount: 0,
        children: []
      },
      {
        name: 'Categories',
        path: 'Categories',
        unreadCount: 0,
        children: [
          { name: 'Nyhetsbrev', path: 'Categories/Nyhetsbrev', unreadCount: 0 },
          { name: 'Arbete', path: 'Categories/Arbete', unreadCount: 0 },
          { name: 'Fakturor', path: 'Categories/Fakturor', unreadCount: 0 }
        ]
      },
      {
        name: 'Senders',
        path: 'Senders',
        unreadCount: 0,
        children: []
      }
    ];

    res.json({ folders });

  } catch (error) {
    console.error('❌ Error getting folders:', error);
    res.status(500).json({ error: error.message, folders: [] });
  }
});

// Create new folder
app.post('/api/folders', async (req, res) => {
  try {
    const { path, autoCreated = false, reason = '' } = req.body;
    console.log(`📁 Creating folder: ${path} (auto: ${autoCreated})`);

    // In production, this would create actual IMAP folder
    const folder = {
      name: path.split('/').pop(),
      path: path,
      unreadCount: 0,
      autoCreated: autoCreated,
      reason: reason,
      createdAt: new Date()
    };

    console.log(`✅ Folder created: ${path}`);
    res.json({ success: true, folder });

  } catch (error) {
    console.error('❌ Error creating folder:', error);
    res.status(500).json({ error: error.message, success: false });
  }
});

// Move emails to folder
app.post('/api/folders/move', async (req, res) => {
  try {
    const { emailIds, targetFolder } = req.body;
    console.log(`📁 Moving ${emailIds.length} emails to ${targetFolder}`);

    // In production, this would move actual emails via IMAP
    // For now, we'll just log the action and send ML feedback

    // Send learning signal
    for (const emailId of emailIds) {
      // Find the email to get context
      const emails = await getRecentEmails('primary', 500);
      const email = emails.find(e => e.uid === emailId);

      if (email) {
        // Record folder move for ML learning
        await recordMLTrainingSignal({
          emailUid: emailId,
          action: 'folder_move',
          targetFolder: targetFolder,
          category: email.mlAnalysis?.category,
          confidence: email.mlAnalysis?.confidence || 0.5,
          userAction: 'bulk_move',
          timestamp: Date.now()
        });
      }
    }

    console.log(`✅ Moved ${emailIds.length} emails to ${targetFolder}`);
    res.json({ success: true, movedCount: emailIds.length, targetFolder });

  } catch (error) {
    console.error('❌ Error moving emails:', error);
    res.status(500).json({ error: error.message, success: false });
  }
});

// === PHASE 3: INBOX ZERO DASHBOARD APIs ===

// Get inbox zero statistics
app.get('/api/inbox-zero/stats', async (req, res) => {
  try {
    console.log('📊 Getting inbox zero statistics...');

    const recentEmails = await getRecentEmails('primary', 500);
    const today = new Date();
    const todayStart = new Date(today.getFullYear(), today.getMonth(), today.getDate());

    // Calculate daily processed emails (emails with categories/actions)
    const dailyProcessed = recentEmails.filter(email => {
      const emailDate = new Date(email.date);
      return emailDate >= todayStart && (email.category || email.mlAnalysis?.category);
    }).length;

    // Calculate productivity metrics
    const categorizedEmails = recentEmails.filter(email => email.category || email.mlAnalysis?.category);
    const productivityScore = recentEmails.length > 0
      ? Math.round((categorizedEmails.length / recentEmails.length) * 100)
      : 0;

    // Calculate streak (simplified - days with processed emails)
    let streak = 0;
    for (let i = 0; i < 30; i++) {
      const checkDate = new Date(today.getTime() - (i * 24 * 60 * 60 * 1000));
      const dayStart = new Date(checkDate.getFullYear(), checkDate.getMonth(), checkDate.getDate());
      const dayEnd = new Date(dayStart.getTime() + 24 * 60 * 60 * 1000);

      const dayProcessed = recentEmails.filter(email => {
        const emailDate = new Date(email.date);
        return emailDate >= dayStart && emailDate < dayEnd && (email.category || email.mlAnalysis?.category);
      }).length;

      if (dayProcessed > 0) {
        streak++;
      } else {
        break;
      }
    }

    // Average response time (mock for now)
    const averageResponseTime = '2.3h';

    const stats = {
      dailyProcessed,
      weeklyGoal: 100,
      productivityScore,
      averageResponseTime,
      streak,
      inboxZeroAchievements: streak > 0 ? 1 : 0
    };

    console.log(`✅ Generated inbox zero stats: ${JSON.stringify(stats)}`);
    res.json({ stats });

  } catch (error) {
    console.error('❌ Error getting inbox zero stats:', error);
    res.status(500).json({ error: error.message, stats: {} });
  }
});

// Get achievements
app.get('/api/inbox-zero/achievements', async (req, res) => {
  try {
    console.log('🏆 Getting achievements...');

    const recentEmails = await getRecentEmails('primary', 500);
    const categorizedEmails = recentEmails.filter(email => email.category || email.mlAnalysis?.category);

    const achievements = [
      {
        id: 1,
        title: 'First Steps',
        description: 'Processed your first 10 emails with AI',
        unlocked: categorizedEmails.length >= 10,
        date: categorizedEmails.length >= 10 ? new Date().toISOString().split('T')[0] : null,
        icon: '🎯'
      },
      {
        id: 2,
        title: 'Category Master',
        description: 'Categorized 50 emails correctly',
        unlocked: categorizedEmails.length >= 50,
        date: categorizedEmails.length >= 50 ? new Date().toISOString().split('T')[0] : null,
        icon: '📁'
      },
      {
        id: 3,
        title: 'Inbox Zero Hero',
        description: 'Achieved inbox zero for 3 consecutive days',
        unlocked: false, // Would need more complex tracking
        icon: '🏆'
      },
      {
        id: 4,
        title: 'Speed Demon',
        description: 'Process 100 emails in under 1 hour',
        unlocked: categorizedEmails.length >= 100,
        date: categorizedEmails.length >= 100 ? new Date().toISOString().split('T')[0] : null,
        icon: '⚡'
      },
      {
        id: 5,
        title: 'ML Master',
        description: 'Achieved 90%+ ML accuracy through feedback',
        unlocked: false, // Would check ML pipeline stats
        icon: '🧠'
      },
      {
        id: 6,
        title: 'Folder Organizer',
        description: 'Created 5 smart folders',
        unlocked: false, // Would check folder creation history
        icon: '🗂️'
      }
    ];

    const unlockedCount = achievements.filter(a => a.unlocked).length;
    console.log(`✅ Generated ${achievements.length} achievements (${unlockedCount} unlocked)`);

    res.json({ achievements });

  } catch (error) {
    console.error('❌ Error getting achievements:', error);
    res.status(500).json({ error: error.message, achievements: [] });
  }
});

// Get weekly progress
app.get('/api/inbox-zero/weekly-progress', async (req, res) => {
  try {
    console.log('📈 Getting weekly progress...');

    const recentEmails = await getRecentEmails('primary', 500);
    const today = new Date();

    const progress = [];
    const dayNames = ['Sön', 'Mån', 'Tis', 'Ons', 'Tor', 'Fre', 'Lör'];

    for (let i = 6; i >= 0; i--) {
      const checkDate = new Date(today.getTime() - (i * 24 * 60 * 60 * 1000));
      const dayStart = new Date(checkDate.getFullYear(), checkDate.getMonth(), checkDate.getDate());
      const dayEnd = new Date(dayStart.getTime() + 24 * 60 * 60 * 1000);

      const dayProcessed = recentEmails.filter(email => {
        const emailDate = new Date(email.date);
        return emailDate >= dayStart && emailDate < dayEnd && (email.category || email.mlAnalysis?.category);
      }).length;

      // Weekend has lower goals
      const isWeekend = checkDate.getDay() === 0 || checkDate.getDay() === 6;
      const goal = isWeekend ? 10 : 20;

      progress.push({
        day: dayNames[checkDate.getDay()],
        processed: dayProcessed,
        goal: goal
      });
    }

    console.log(`✅ Generated weekly progress: ${JSON.stringify(progress)}`);
    res.json({ progress });

  } catch (error) {
    console.error('❌ Error getting weekly progress:', error);
    res.status(500).json({ error: error.message, progress: [] });
  }
});

// Get ML analysis with enhanced confidence data
app.get('/api/emails/:uid/analysis', async (req, res) => {
  try {
    const { uid } = req.params;

    // Find email in recent cache or database
    // Support both UID strings and numeric IDs for compatibility
    let email = null;
    try {
      const recentEmails = await fetchEmailsFromSource('primary', 500);

      // Try exact match first, then loose match for numeric IDs
      email = recentEmails.find(e => e.uid == uid) ||
              recentEmails.find(e => e.uid === String(uid)) ||
              recentEmails.find(e => String(e.uid) === String(uid));

      // If no match found, also check if uid is numeric and matches sequence ID
      if (!email && /^\d+$/.test(uid)) {
        email = recentEmails.find(e => e.sequenceID == uid || e.messageNumber == uid);
      }
    } catch (err) {
      console.log('Could not fetch email for analysis:', err);
      return res.status(404).json({
        error: 'Email not found',
        details: 'Service temporarily unavailable',
        uid: uid
      });
    }

    if (!email) {
      // Return structured error instead of generic 404 to help debug
      return res.status(404).json({
        error: 'Email not found',
        uid: uid,
        hint: 'Email may have been archived or deleted'
      });
    }

    // Get ML analysis with confidence scoring
    const mlAnalysis = await categorizeEmailWithML(email);

    // Calculate enhanced confidence factors
    const confidenceFactors = {
      modelAccuracy: mlPipeline.getStats().accuracy || 0.5,
      senderHistory: await calculateSenderConfidence(email.from),
      subjectPattern: calculateSubjectPatternConfidence(email.subject),
      contentLength: Math.min(email.text?.length / 500, 1) || 0.5,
      timeContext: calculateTimeConfidence(email.date)
    };

    // Overall confidence (weighted average)
    const overallConfidence = (
      confidenceFactors.modelAccuracy * 0.4 +
      confidenceFactors.senderHistory * 0.3 +
      confidenceFactors.subjectPattern * 0.2 +
      confidenceFactors.contentLength * 0.05 +
      confidenceFactors.timeContext * 0.05
    );

    // Determine if should auto-execute, suggest, or manual review
    const shouldAutoExecute = overallConfidence >= 0.95;
    const shouldSuggest = overallConfidence >= 0.80 && overallConfidence < 0.95;
    const needsManualReview = overallConfidence < 0.80;

    res.json({
      mlAnalysis,
      confidence: overallConfidence,
      confidenceFactors,
      shouldAutoExecute,
      shouldSuggest,
      needsManualReview,
      suggestedCategory: mlAnalysis.category,
      isAutoExecuted: shouldAutoExecute
    });

  } catch (error) {
    console.error('Error getting email analysis:', error);
    res.status(500).json({ error: 'Failed to get email analysis' });
  }
});

// Helper functions for confidence calculation
async function calculateSenderConfidence(sender) {
  // Check how many emails from this sender we've processed correctly
  const senderKey = `sender_confidence:${sender}`;

  if (redisConnected && redisClient) {
    try {
      const data = await redisClient.get(senderKey);
      if (data) {
        const parsed = JSON.parse(data);
        return Math.min(parsed.correctCount / (parsed.correctCount + parsed.incorrectCount), 0.95);
      }
    } catch (error) {
      console.warn('Redis sender confidence error:', error.message);
    }
  }

  return 0.7; // Default confidence for unknown senders
}

function calculateSubjectPatternConfidence(subject) {
  const highConfidencePatterns = [
    { pattern: /^RE:/, confidence: 0.9 },
    { pattern: /^FW:|^FWD:/, confidence: 0.85 },
    { pattern: /invoice|faktura/i, confidence: 0.95 },
    { pattern: /meeting|möte|calendar/i, confidence: 0.9 },
    { pattern: /newsletter|nyhetsbrev/i, confidence: 0.9 },
    { pattern: /security|säkerhet|alert/i, confidence: 0.95 }
  ];

  for (const { pattern, confidence } of highConfidencePatterns) {
    if (pattern.test(subject)) {
      return confidence;
    }
  }
  return 0.6;
}

function calculateTimeConfidence(dateStr) {
  const date = new Date(dateStr);
  const hour = date.getHours();
  const day = date.getDay();

  // Higher confidence during business hours and weekdays
  if (day >= 1 && day <= 5 && hour >= 8 && hour <= 18) {
    return 0.8;
  } else if (day >= 1 && day <= 5) {
    return 0.7;
  }
  return 0.6;
}

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
      'Enhanced category management',
      'Auto-rule creation',
      'Account management',
      'Category statistics',
      redisConnected ? '✅ Redis caching enabled' : '⚠️ Redis caching disabled'
    ]
  });
});

// QUICK FIX: API Compatibility Routes - Proxy missing /api endpoints
// This ensures frontend can call /api/recent-emails and /api/health

// ADDITIONAL API PROXIES for Enhanced Category Selector

// Proxy /api/emails/:uid/analysis (new endpoint)
app.get('/api/emails/:uid/analysis', async (req, res) => {
  try {
    const { uid } = req.params;

    // Find email in recent cache or database
    let email = null;
    try {
      const recentEmails = await fetchEmailsFromSource('primary', 100);
      email = recentEmails.find(e => e.uid == uid);
    } catch (err) {
      console.log('Could not fetch email for analysis:', err);
      return res.status(404).json({ error: 'Email not found' });
    }

    if (!email) {
      return res.status(404).json({ error: 'Email not found' });
    }

    // Get ML analysis with confidence scoring
    const mlAnalysis = await categorizeEmailWithML(email);

    // Calculate enhanced confidence factors
    const confidenceFactors = {
      modelAccuracy: mlPipeline.getStats().accuracy || 0.5,
      senderHistory: await calculateSenderConfidence(email.from),
      subjectPattern: calculateSubjectPatternConfidence(email.subject),
      contentLength: Math.min(email.text?.length / 500, 1) || 0.5,
      timeContext: calculateTimeConfidence(email.date)
    };

    // Overall confidence (weighted average)
    const overallConfidence = (
      confidenceFactors.modelAccuracy * 0.4 +
      confidenceFactors.senderHistory * 0.3 +
      confidenceFactors.subjectPattern * 0.2 +
      confidenceFactors.contentLength * 0.05 +
      confidenceFactors.timeContext * 0.05
    );

    // Determine if should auto-execute, suggest, or manual review
    const shouldAutoExecute = overallConfidence >= 0.95;
    const shouldSuggest = overallConfidence >= 0.80 && overallConfidence < 0.95;
    const needsManualReview = overallConfidence < 0.80;

    res.json({
      mlAnalysis,
      confidence: overallConfidence,
      confidenceFactors,
      shouldAutoExecute,
      shouldSuggest,
      needsManualReview,
      suggestedCategory: mlAnalysis.category,
      isAutoExecuted: shouldAutoExecute
    });

  } catch (error) {
    console.error('Error getting email analysis:', error);
    res.status(500).json({ error: 'Failed to get email analysis' });
  }
});

// Proxy /api/ml/training-signal (new endpoint)
app.post('/api/ml/training-signal', async (req, res) => {
  try {
    const {
      emailUid,
      fromCategory,
      toCategory,
      mlSuggestion,
      mlConfidence,
      userAction,
      timestamp
    } = req.body;

    console.log(`🎯 [PROXY] Training signal: ${userAction} - ${fromCategory} → ${toCategory} (ML suggested: ${mlSuggestion}, confidence: ${mlConfidence})`);

    // Store training data
    const trainingData = {
      emailUid,
      fromCategory,
      toCategory,
      mlSuggestion,
      mlConfidence,
      userAction,
      timestamp: new Date(timestamp || Date.now())
    };

    // Save to database for ML learning
    if (emailDb && emailDb.saveTrainingSignal) {
      await emailDb.saveTrainingSignal(trainingData);
    }

    // If user consistently corrects ML, adjust confidence
    if (mlPipeline && userAction === 'suggestion_reject') {
      await mlPipeline.adjustConfidenceForPattern(emailUid, -0.1);
    } else if (userAction === 'suggestion_accept') {
      await mlPipeline.adjustConfidenceForPattern(emailUid, 0.1);
    }

    res.json({ success: true, recorded: true });
  } catch (error) {
    console.error('Error recording training signal:', error);
    res.status(500).json({ error: 'Failed to record training signal' });
  }
});

// Proxy /api/rules/create (new endpoint)
app.post('/api/rules/create', async (req, res) => {
  try {
    const { trigger, action, confidence_required = 0.90 } = req.body;

    const rule = {
      id: `rule_${Date.now()}`,
      trigger,
      action,
      confidenceRequired: confidence_required,
      createdAt: new Date(),
      usageCount: 0,
      enabled: true
    };

    // Save rule to cache
    const rulesKey = 'auto_rules';
    if (redisConnected && redisClient) {
      try {
        const existing = await redisClient.get(rulesKey) || '[]';
        const rules = JSON.parse(existing);
        rules.push(rule);
        await redisClient.set(rulesKey, JSON.stringify(rules));
      } catch (error) {
        console.warn('Redis rule save error:', error.message);
      }
    }

    console.log(`📋 [PROXY] Auto-rule created: ${trigger.type}=${trigger.value} → ${action.category}`);
    res.json({ success: true, rule });
  } catch (error) {
    console.error('Error creating auto rule:', error);
    res.status(500).json({ error: 'Failed to create auto rule' });
  }
});

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

// Proxy inbox zero endpoints with account parameter
app.get('/api/inbox-zero/stats/:accountId', async (req, res) => {
  console.log(`[API PROXY] /api/inbox-zero/stats/${req.params.accountId} -> /api/inbox-zero/stats`);
  try {
    const stats = await getInboxZeroStats(req.params.accountId);
    res.json({ stats });
  } catch (error) {
    console.error('Error getting inbox zero stats:', error);
    res.status(500).json({ error: error.message, stats: {} });
  }
});

app.get('/api/inbox-zero/achievements/:accountId', async (req, res) => {
  console.log(`[API PROXY] /api/inbox-zero/achievements/${req.params.accountId} -> /api/inbox-zero/achievements`);
  try {
    const achievements = await getInboxZeroAchievements(req.params.accountId);
    res.json({ achievements });
  } catch (error) {
    console.error('Error getting achievements:', error);
    res.status(500).json({ error: error.message, achievements: [] });
  }
});

app.get('/api/inbox-zero/weekly-progress/:accountId', async (req, res) => {
  console.log(`[API PROXY] /api/inbox-zero/weekly-progress/${req.params.accountId} -> /api/inbox-zero/weekly-progress`);
  try {
    const progress = await getWeeklyProgress(req.params.accountId);
    res.json({ progress });
  } catch (error) {
    console.error('Error getting weekly progress:', error);
    res.status(500).json({ error: error.message, progress: [] });
  }
});

app.get('/api/folders/suggestions/:accountId', async (req, res) => {
  console.log(`[API PROXY] /api/folders/suggestions/${req.params.accountId} -> smart folder suggestions`);
  try {
    const suggestions = await getSmartFolderSuggestions(req.params.accountId);
    res.json({ suggestions });
  } catch (error) {
    console.error('Error getting folder suggestions:', error);
    res.status(500).json({ error: error.message, suggestions: [] });
  }
});

// Helper functions for the new endpoints
function classifyEmailBasic(email) {
  // Basic rule-based classification for performance optimization
  const subject = (email.subject || '').toLowerCase();
  const from = (email.from || '').toLowerCase();

  // Newsletter/Marketing detection
  if (subject.includes('newsletter') || subject.includes('unsubscribe') ||
      from.includes('noreply') || from.includes('marketing') ||
      from.includes('newsletter') || subject.includes('offer') ||
      subject.includes('sale') || subject.includes('discount')) {
    return 'marketing';
  }

  // Social notifications
  if (from.includes('notification') || from.includes('facebook') ||
      from.includes('twitter') || from.includes('linkedin') ||
      from.includes('instagram') || subject.includes('mentioned you') ||
      subject.includes('tagged you') || subject.includes('liked your')) {
    return 'social';
  }

  // Financial/Banking
  if (from.includes('bank') || from.includes('paypal') ||
      from.includes('stripe') || from.includes('invoice') ||
      subject.includes('payment') || subject.includes('receipt') ||
      subject.includes('transaction') || subject.includes('bill')) {
    return 'financial';
  }

  // Work/Professional
  if (from.includes('calendar') || from.includes('meeting') ||
      subject.includes('meeting') || subject.includes('calendar') ||
      subject.includes('schedule') || subject.includes('call') ||
      from.includes('jira') || from.includes('github') || from.includes('gitlab')) {
    return 'work';
  }

  // Travel
  if (from.includes('booking') || from.includes('hotel') ||
      from.includes('flight') || from.includes('trip') ||
      subject.includes('booking') || subject.includes('reservation') ||
      subject.includes('travel') || subject.includes('flight')) {
    return 'travel';
  }

  // Default to personal for everything else
  return 'personal';
}

async function getInboxZeroStats(accountId) {
  const recentEmails = await getRecentEmails(accountId, 500);
  const today = new Date();
  const todayStart = new Date(today.getFullYear(), today.getMonth(), today.getDate());

  const dailyProcessed = recentEmails.filter(email => {
    const emailDate = new Date(email.date);
    return emailDate >= todayStart && (email.category || email.mlAnalysis?.category);
  }).length;

  const categorizedEmails = recentEmails.filter(email => email.category || email.mlAnalysis?.category);
  const productivityScore = recentEmails.length > 0
    ? Math.round((categorizedEmails.length / recentEmails.length) * 100)
    : 0;

  let streak = 0;
  for (let i = 0; i < 30; i++) {
    const checkDate = new Date(today.getTime() - (i * 24 * 60 * 60 * 1000));
    const dayStart = new Date(checkDate.getFullYear(), checkDate.getMonth(), checkDate.getDate());
    const dayEnd = new Date(dayStart.getTime() + 24 * 60 * 60 * 1000);

    const dayProcessed = recentEmails.filter(email => {
      const emailDate = new Date(email.date);
      return emailDate >= dayStart && emailDate < dayEnd && (email.category || email.mlAnalysis?.category);
    }).length;

    if (dayProcessed > 0) {
      streak++;
    } else {
      break;
    }
  }

  return {
    dailyProcessed,
    weeklyGoal: 100,
    productivityScore,
    averageResponseTime: '2.3h',
    streak,
    inboxZeroAchievements: streak > 0 ? 1 : 0
  };
}

async function getInboxZeroAchievements(accountId) {
  const recentEmails = await getRecentEmails(accountId, 500);
  const categorizedEmails = recentEmails.filter(email => email.category || email.mlAnalysis?.category);

  return [
    {
      id: 1,
      title: 'First Steps',
      description: 'Processed your first 10 emails with AI',
      unlocked: categorizedEmails.length >= 10,
      date: categorizedEmails.length >= 10 ? new Date().toISOString().split('T')[0] : null,
      icon: '🎯'
    },
    {
      id: 2,
      title: 'Category Master',
      description: 'Categorized 50 emails correctly',
      unlocked: categorizedEmails.length >= 50,
      date: categorizedEmails.length >= 50 ? new Date().toISOString().split('T')[0] : null,
      icon: '📁'
    },
    {
      id: 3,
      title: 'Inbox Zero Hero',
      description: 'Achieved inbox zero for 3 consecutive days',
      unlocked: false,
      icon: '🏆'
    },
    {
      id: 4,
      title: 'Speed Demon',
      description: 'Process 100 emails in under 1 hour',
      unlocked: categorizedEmails.length >= 100,
      date: categorizedEmails.length >= 100 ? new Date().toISOString().split('T')[0] : null,
      icon: '⚡'
    },
    {
      id: 5,
      title: 'ML Master',
      description: 'Achieved 90%+ ML accuracy through feedback',
      unlocked: false,
      icon: '🧠'
    },
    {
      id: 6,
      title: 'Folder Organizer',
      description: 'Created 5 smart folders',
      unlocked: false,
      icon: '🗂️'
    }
  ];
}

async function getWeeklyProgress(accountId) {
  const recentEmails = await getRecentEmails(accountId, 500);
  const today = new Date();
  const progress = [];
  const dayNames = ['Sön', 'Mån', 'Tis', 'Ons', 'Tor', 'Fre', 'Lör'];

  for (let i = 6; i >= 0; i--) {
    const checkDate = new Date(today.getTime() - (i * 24 * 60 * 60 * 1000));
    const dayStart = new Date(checkDate.getFullYear(), checkDate.getMonth(), checkDate.getDate());
    const dayEnd = new Date(dayStart.getTime() + 24 * 60 * 60 * 1000);

    const dayProcessed = recentEmails.filter(email => {
      const emailDate = new Date(email.date);
      return emailDate >= dayStart && emailDate < dayEnd && (email.category || email.mlAnalysis?.category);
    }).length;

    const isWeekend = checkDate.getDay() === 0 || checkDate.getDay() === 6;
    const goal = isWeekend ? 10 : 20;

    progress.push({
      day: dayNames[checkDate.getDay()],
      processed: dayProcessed,
      goal: goal
    });
  }

  return progress;
}

async function getSmartFolderSuggestions(accountId) {
  console.log('🎯 Getting smart folder suggestions...');

  const recentEmails = await getRecentEmails(accountId, 100);

  // Analyze email patterns to suggest folders
  const senderMap = {};
  const categoryMap = {};

  recentEmails.forEach(email => {
    const domain = email.from.split('@')[1];
    if (domain) {
      senderMap[domain] = (senderMap[domain] || 0) + 1;
    }

    if (email.category || email.mlAnalysis?.category) {
      const cat = email.category || email.mlAnalysis?.category;
      categoryMap[cat] = (categoryMap[cat] || 0) + 1;
    }
  });

  const suggestions = [];

  // Top senders (domains with >3 emails)
  Object.entries(senderMap)
    .filter(([domain, count]) => count >= 3)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 2)
    .forEach(([domain, count]) => {
      suggestions.push({
        name: domain.charAt(0).toUpperCase() + domain.slice(1),
        path: `Senders/${domain}`,
        reason: `${count} emails from ${domain}`,
        confidence: Math.min(count / 10, 0.9),
        autoCreated: false
      });
    });

  // High-volume categories
  Object.entries(categoryMap)
    .filter(([cat, count]) => count >= 5)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 1)
    .forEach(([cat, count]) => {
      suggestions.push({
        name: cat.charAt(0).toUpperCase() + cat.slice(1),
        path: `Categories/${cat}`,
        reason: `${count} emails kategoriserade som ${cat}`,
        confidence: Math.min(count / 20, 0.95),
        autoCreated: false
      });
    });

  console.log(`✅ Generated ${suggestions.length} folder suggestions`);
  return suggestions;
}

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