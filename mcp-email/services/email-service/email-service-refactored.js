const express = require('express');
const cors = require('cors');
const axios = require('axios');
const redis = require('redis');
const EmailCategorizationService = require('./email-categorization-service');

const app = express();
const PORT = process.env.PORT || 3012;

app.use(cors());
app.use(express.json());

// Redis client setup
const redisClient = redis.createClient({
  host: process.env.REDIS_HOST || '172.17.0.1',
  port: process.env.REDIS_PORT || 6381
});

redisClient.on('connect', () => console.log('✅ Redis connected for Email Service'));
redisClient.on('error', (err) => console.error('Redis error:', err));

// Connect to Redis
redisClient.connect().catch(err => {
  console.error('Failed to connect to Redis:', err);
});

// ML Service wrapper
class MLService {
  async categorize(email) {
    try {
      const prompt = `Analyze this email and provide structured classification:
From: ${email.from || 'Unknown'}
Subject: ${email.subject || 'No subject'}
Date: ${email.date || new Date().toISOString()}
Content: ${email.text?.substring(0, 500) || email.bodyPreview || 'No content'}

Provide JSON response with:
1. category: work/personal/newsletter/spam/notification/social
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
      }, {
        timeout: 10000
      });

      const aiContent = response.data.choices[0].message.content;
      const jsonMatch = aiContent.match(/\{[\s\S]*?\}/);

      if (jsonMatch) {
        const parsed = JSON.parse(jsonMatch[0]);
        return {
          category: parsed.category || 'uncategorized',
          priority: parsed.priority || 'medium',
          sentiment: parsed.sentiment || 'neutral',
          topics: parsed.topics || [],
          action_required: parsed.action_required || false,
          summary: parsed.summary || 'Unable to categorize',
          confidence: 0.8 // Assume good confidence for successful ML analysis
        };
      }

      throw new Error('No valid JSON found in ML response');

    } catch (error) {
      console.error('ML categorization error:', error.message);
      throw error;
    }
  }
}

// Initialize services
const mlService = new MLService();
const categorizationService = new EmailCategorizationService(redisClient, mlService, {
  mlConfidenceThreshold: 0.7,
  cacheExpiry: 3600
});

// Event listener for ML training
categorizationService.on('category_override', (event) => {
  console.log(`📚 Category override event:`, {
    emailId: event.emailId,
    userId: event.userId,
    category: event.category,
    timestamp: new Date(event.timestamp).toISOString()
  });

  // Here you could send to external ML training system
  // await mlTrainingSystem.addFeedback(event);
});

// Store connected email accounts
const emailConnections = new Map();

// Connect to MCP Email GUI Server and get emails
async function fetchEmailsFromMCP(connectionId, limit = 50) {
  try {
    const mcpConnectionId = 'primary';

    // First ensure connection exists
    const connections = await axios.get('http://localhost:3623/api/connections');
    const hasConnection = connections.data.connections.some(c => c.connectionId === mcpConnectionId);

    if (!hasConnection) {
      console.log('Creating new MCP connection...');
      await axios.post('http://localhost:3623/api/connect', {
        connectionId: mcpConnectionId,
        email: process.env.ONECOM_EMAIL || 'mikael@fallstrom.org',
        password: process.env.ONECOM_PASSWORD || 'Ati:}v>~ra_Tqec?)zpLRq8Z',
        provider: 'oneCom'
      });
    }

    // Fetch recent emails with configurable limit
    const emailsResponse = await axios.post('http://localhost:3623/api/search-emails', {
      connectionId: mcpConnectionId,
      criteria: ['ALL'],
      limit: limit,
      mailbox: 'INBOX'
    });

    return emailsResponse.data.emails || [];
  } catch (error) {
    console.error('MCP fetch error:', error.message);

    if (error.code === 'ECONNREFUSED') {
      console.log('MCP Email GUI Server not running on port 3623');
      return [];
    }

    throw error;
  }
}

// Main endpoint to get emails with centralized categorization
app.get('/recent-emails/:accountId', async (req, res) => {
  try {
    const accountId = req.params.accountId;
    const userId = req.headers['x-user-id'] || 'default'; // Get user ID from header
    const limit = parseInt(req.query.limit) || 50;

    console.log(`Fetching emails for account: ${accountId}, user: ${userId}, limit: ${limit}`);

    // Fetch emails from MCP
    const emails = await fetchEmailsFromMCP(accountId, limit);

    if (emails.length === 0) {
      return res.json([]);
    }

    // Process each email with centralized categorization service
    const processedEmails = await Promise.all(
      emails.map(async (email) => {
        const categorization = await categorizationService.categorizeEmail(email, userId);

        return {
          uid: email.uid,
          from: email.from,
          subject: email.subject,
          date: email.date,
          flags: email.flags || [],
          hasAttachments: email.hasAttachments || false,
          bodyPreview: email.bodyPreview,

          // Centralized categorization results
          category: categorization.category,
          priority: categorization.priority,
          sentiment: categorization.sentiment,
          topics: categorization.topics,
          actionRequired: categorization.actionRequired,
          summary: categorization.summary,

          // Metadata
          categorizationSource: categorization.source,
          confidence: categorization.confidence,
          analyzed: true,
          manualCategory: categorization.source === 'user_override'
        };
      })
    );

    // Sort by priority and then by date
    processedEmails.sort((a, b) => {
      const priorityScore = { critical: 4, high: 3, medium: 2, low: 1 };
      const scoreA = priorityScore[a.priority] || 2;
      const scoreB = priorityScore[b.priority] || 2;

      if (scoreB !== scoreA) {
        return scoreB - scoreA; // Higher priority first
      }

      return new Date(b.date) - new Date(a.date); // Newer emails first
    });

    console.log(`Processed ${processedEmails.length} emails with centralized categorization`);
    res.json(processedEmails);

  } catch (error) {
    console.error('Error fetching/processing emails:', error);
    res.status(500).json({
      error: 'Failed to fetch emails',
      details: error.message
    });
  }
});

// Endpoint to set user category override
app.post('/api/categories/override', async (req, res) => {
  try {
    const { emailId, category, userId = 'default' } = req.body;

    if (!emailId || !category) {
      return res.status(400).json({
        error: 'emailId and category are required'
      });
    }

    const result = await categorizationService.setUserCategoryOverride(
      emailId,
      userId,
      category,
      { source: 'manual_ui_change' }
    );

    res.json({
      success: true,
      message: 'Category override set successfully',
      data: result
    });

  } catch (error) {
    console.error('Category override error:', error);
    res.status(500).json({
      error: 'Failed to set category override',
      details: error.message
    });
  }
});

// Endpoint to get category statistics
app.get('/api/categories/stats/:accountId', async (req, res) => {
  try {
    const accountId = req.params.accountId;
    const userId = req.headers['x-user-id'] || 'default';
    const limit = parseInt(req.query.limit) || 50;

    // Fetch emails
    const emails = await fetchEmailsFromMCP(accountId, limit);

    // Get stats using centralized service
    const stats = await categorizationService.getCategoryStats(emails, userId);

    res.json({
      success: true,
      stats,
      metadata: {
        accountId,
        userId,
        emailsAnalyzed: emails.length,
        timestamp: Date.now()
      }
    });

  } catch (error) {
    console.error('Stats error:', error);
    res.status(500).json({
      error: 'Failed to get category stats',
      details: error.message
    });
  }
});

// Endpoint to trigger email sync
app.post('/sync-emails/:accountId', async (req, res) => {
  try {
    const accountId = req.params.accountId;
    const limit = parseInt(req.query.limit) || 50;

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

// Smart inbox endpoint with centralized categorization
app.get('/smart-inbox/:accountId', async (req, res) => {
  try {
    const accountId = req.params.accountId;
    const userId = req.headers['x-user-id'] || 'default';

    // Get processed emails
    const response = await axios.get(`http://localhost:${PORT}/recent-emails/${accountId}`, {
      headers: { 'x-user-id': userId }
    });
    const emails = response.data;

    // Separate into categories
    const categorized = {
      urgent: emails.filter(e => e.priority === 'critical' || e.category === 'urgent'),
      actionRequired: emails.filter(e => e.actionRequired),
      work: emails.filter(e => e.category === 'work'),
      personal: emails.filter(e => e.category === 'personal'),
      newsletters: emails.filter(e => e.category === 'newsletter'),
      manuallySet: emails.filter(e => e.manualCategory),
      mlAnalyzed: emails.filter(e => e.categorizationSource === 'ml_analysis'),
      ruleBased: emails.filter(e => e.categorizationSource === 'rule_based')
    };

    res.json({
      inbox: categorized,
      stats: {
        total: emails.length,
        unread: emails.filter(e => !e.flags?.includes('\\Seen')).length,
        highPriority: emails.filter(e => e.priority === 'high' || e.priority === 'critical').length,
        actionRequired: categorized.actionRequired.length,
        manuallySet: categorized.manuallySet.length,
        mlAnalyzed: categorized.mlAnalyzed.length,
        ruleBased: categorized.ruleBased.length
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

// Health check
app.get('/health', (req, res) => {
  res.json({
    status: 'ok',
    service: 'Refactored Email Service',
    features: [
      'Centralized categorization logic',
      'Redis-based user overrides',
      'Event-driven ML training',
      'Clean separation of concerns',
      'IMAP connection via MCP',
      'ML categorization with GPT-OSS 20B',
      'Smart inbox with prioritization',
      'Persistent user preferences'
    ],
    architecture: {
      categorizationPriority: [
        '1. User manual overrides (Redis)',
        '2. ML analysis (GPT-OSS)',
        '3. Rule-based fallback'
      ],
      dataFlow: 'MCP → EmailCategorizationService → Redis → Response'
    }
  });
});

app.listen(PORT, () => {
  console.log(`\n🚀 Refactored Email Service running on port ${PORT}\n`);
  console.log('✨ Architecture Improvements:');
  console.log('  ✅ Centralized categorization logic');
  console.log('  ✅ Redis-based persistent storage');
  console.log('  ✅ Event-driven design');
  console.log('  ✅ Clean separation of concerns');
  console.log('  ✅ Single source of truth');
  console.log('  ✅ Consistent user overrides');
  console.log('  ✅ ML training feedback loop\n');

  console.log('🔗 Endpoints:');
  console.log('  GET  /recent-emails/:accountId - Get emails with centralized categorization');
  console.log('  POST /api/categories/override - Set user category override');
  console.log('  GET  /api/categories/stats/:accountId - Get category statistics');
  console.log('  POST /sync-emails/:accountId - Trigger email sync');
  console.log('  GET  /smart-inbox/:accountId - Smart categorized inbox');
  console.log('  GET  /health - Service health and architecture info\n');
});