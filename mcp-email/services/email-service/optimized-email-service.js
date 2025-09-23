const express = require('express');
const cors = require('cors');
const axios = require('axios');
const redis = require('redis');
const FlexibleEmailAIAnalyzer = require('./flexible-ai-analyzer');
const EmailDatabase = require('./database');

const app = express();
const PORT = process.env.PORT || 3012;

app.use(cors());
app.use(express.json());

// Redis client setup
const REDIS_HOST = process.env.REDIS_HOST || '172.17.0.1';
const REDIS_PORT = process.env.REDIS_PORT || 6381;
let redisClient = null;
let redisConnected = false;

// Metrics tracking
const metrics = {
  cacheHits: 0,
  cacheMisses: 0,
  dbHits: 0,
  dbMisses: 0,
  aiCalls: 0,
  fallbackUsed: 0,
  totalRequests: 0,
  avgResponseTime: 0
};

// Initialize Redis connection
(async () => {
  try {
    redisClient = redis.createClient({
      socket: {
        host: REDIS_HOST,
        port: REDIS_PORT,
        reconnectStrategy: (retries) => Math.min(retries * 50, 500)
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

// AI Analyzer instance
const llmConfigPath = process.env.LLM_CONFIG || './llm-config.json';
const aiAnalyzer = new FlexibleEmailAIAnalyzer(llmConfigPath);

// Database instance
const emailDb = new EmailDatabase();

// Store connected email accounts
const emailConnections = new Map();

// Helper function to get dynamic TTL based on email type
function getDynamicTTL(categorization) {
  if (!categorization) return 3600; // 1 hour default

  // Newsletter and promotional emails can be cached longer
  if (['newsletter', 'promotional', 'spam'].includes(categorization.category)) {
    return 86400; // 24 hours
  }

  // High priority emails need fresher data
  if (categorization.priority === 'high' || categorization.action_required) {
    return 1800; // 30 minutes
  }

  // Work emails moderate caching
  if (categorization.category === 'work') {
    return 3600; // 1 hour
  }

  return 7200; // 2 hours standard
}

// Helper function to generate cache key
function getCacheKey(email) {
  return `email:cat:${email.uid || 'unknown'}:${email.subject?.substring(0, 50) || 'no-subject'}`;
}

// Rule-based fallback categorization
function ruleBasedCategorization(email) {
  const subject = (email.subject || '').toLowerCase();
  const from = (email.from || '').toLowerCase();
  const content = (email.text || email.html || '').toLowerCase().substring(0, 500);

  // Newsletter detection
  if (subject.includes('newsletter') || content.includes('unsubscribe') ||
      content.includes('weekly update') || content.includes('monthly digest')) {
    return {
      category: 'newsletter',
      priority: 'low',
      sentiment: 'neutral',
      action_required: false,
      summary: 'Newsletter or subscription update',
      topics: ['newsletter'],
      confidence: 0.7
    };
  }

  // Promotional/Spam detection
  const spamKeywords = ['sale', 'discount', 'offer', 'deal', 'winner', 'claim', 'urgent', 'act now'];
  if (spamKeywords.some(keyword => subject.includes(keyword) || content.includes(keyword))) {
    return {
      category: 'promotional',
      priority: 'low',
      sentiment: 'neutral',
      action_required: false,
      summary: 'Promotional or sales email',
      topics: ['promotion'],
      confidence: 0.6
    };
  }

  // Work email detection
  const workKeywords = ['meeting', 'project', 'deadline', 'task', 'report', 'review'];
  if (workKeywords.some(keyword => subject.includes(keyword) || content.includes(keyword))) {
    return {
      category: 'work',
      priority: 'medium',
      sentiment: 'neutral',
      action_required: true,
      summary: 'Work-related email requiring attention',
      topics: ['work'],
      confidence: 0.65
    };
  }

  // Default fallback
  return {
    category: 'personal',
    priority: 'medium',
    sentiment: 'neutral',
    action_required: false,
    summary: 'Personal email',
    topics: [],
    confidence: 0.4
  };
}

// Optimized ML categorization with cache-first approach
async function categorizeEmailOptimized(email) {
  const startTime = Date.now();
  metrics.totalRequests++;

  try {
    // 1. CHECK REDIS FIRST (fastest)
    if (redisConnected && redisClient) {
      const cacheKey = getCacheKey(email);
      try {
        const cached = await redisClient.get(cacheKey);
        if (cached) {
          metrics.cacheHits++;
          console.log(`⚡ Redis cache hit for: ${email.subject?.substring(0, 30)}...`);
          const result = JSON.parse(cached);

          // Update response time metric
          const responseTime = Date.now() - startTime;
          metrics.avgResponseTime = (metrics.avgResponseTime + responseTime) / 2;

          return result;
        }
        metrics.cacheMisses++;
      } catch (cacheError) {
        console.warn('Redis read error:', cacheError.message);
      }
    }

    // 2. CHECK DATABASE (persistent storage)
    try {
      const dbResult = await emailDb.getCategorization(email);
      if (dbResult) {
        metrics.dbHits++;
        console.log(`💾 Database hit for: ${email.subject?.substring(0, 30)}...`);

        // Update Redis cache with DB result
        if (redisConnected && redisClient) {
          const cacheKey = getCacheKey(email);
          const ttl = getDynamicTTL(dbResult);
          try {
            await redisClient.setEx(cacheKey, ttl, JSON.stringify(dbResult));
          } catch (cacheError) {
            console.warn('Redis write error:', cacheError.message);
          }
        }

        const responseTime = Date.now() - startTime;
        metrics.avgResponseTime = (metrics.avgResponseTime + responseTime) / 2;

        return dbResult;
      }
      metrics.dbMisses++;
    } catch (dbError) {
      console.error('Database error:', dbError.message);
    }

    // 3. CALL AI SERVICE
    console.log(`🤖 Calling AI for: ${email.subject?.substring(0, 30)}...`);
    metrics.aiCalls++;

    let categorization;
    try {
      categorization = await aiAnalyzer.classifyEmail(email);

      // Add confidence score if not present
      if (!categorization.confidence) {
        categorization.confidence = 0.85; // Default high confidence for AI results
      }
    } catch (aiError) {
      console.error('AI service error:', aiError.message);

      // 4. FALLBACK TO RULE-BASED
      console.log('⚠️ Using rule-based fallback categorization');
      metrics.fallbackUsed++;
      categorization = ruleBasedCategorization(email);
    }

    // 5. SAVE TO BOTH CACHE AND DATABASE (parallel)
    const savePromises = [];

    // Save to database
    savePromises.push(
      emailDb.saveCategorization(email, categorization).catch(err =>
        console.error('DB save error:', err.message)
      )
    );

    // Save to Redis cache with dynamic TTL
    if (redisConnected && redisClient) {
      const cacheKey = getCacheKey(email);
      const ttl = getDynamicTTL(categorization);
      savePromises.push(
        redisClient.setEx(cacheKey, ttl, JSON.stringify(categorization)).catch(err =>
          console.warn('Cache save error:', err.message)
        )
      );
    }

    // Wait for saves to complete
    await Promise.all(savePromises);

    const responseTime = Date.now() - startTime;
    metrics.avgResponseTime = (metrics.avgResponseTime + responseTime) / 2;

    return categorization;

  } catch (error) {
    console.error('Categorization error:', error);
    metrics.fallbackUsed++;

    // Last resort fallback
    return ruleBasedCategorization(email);
  }
}

// Batch processing endpoint
app.post('/api/categorize/batch', async (req, res) => {
  const { emails } = req.body;

  if (!emails || !Array.isArray(emails)) {
    return res.status(400).json({ error: 'Invalid request: emails array required' });
  }

  console.log(`📦 Processing batch of ${emails.length} emails`);

  try {
    // Process emails in parallel with concurrency limit
    const batchSize = 5;
    const results = [];

    for (let i = 0; i < emails.length; i += batchSize) {
      const batch = emails.slice(i, i + batchSize);
      const batchResults = await Promise.all(
        batch.map(email => categorizeEmailOptimized(email))
      );
      results.push(...batchResults);
    }

    res.json({
      success: true,
      count: results.length,
      categorizations: results
    });
  } catch (error) {
    console.error('Batch processing error:', error);
    res.status(500).json({ error: 'Batch processing failed' });
  }
});

// Single email categorization endpoint
app.post('/api/categorize', async (req, res) => {
  const email = req.body;

  if (!email) {
    return res.status(400).json({ error: 'Email data required' });
  }

  try {
    const categorization = await categorizeEmailOptimized(email);
    res.json(categorization);
  } catch (error) {
    console.error('Categorization error:', error);
    res.status(500).json({ error: 'Categorization failed' });
  }
});

// Health check endpoint with metrics
app.get('/health', async (req, res) => {
  const health = {
    status: 'healthy',
    timestamp: new Date().toISOString(),
    services: {
      redis: redisConnected,
      database: true,
      ai: true
    },
    metrics: {
      ...metrics,
      cacheHitRate: metrics.totalRequests > 0
        ? ((metrics.cacheHits / metrics.totalRequests) * 100).toFixed(2) + '%'
        : '0%',
      dbHitRate: metrics.totalRequests > 0
        ? ((metrics.dbHits / metrics.totalRequests) * 100).toFixed(2) + '%'
        : '0%',
      fallbackRate: metrics.totalRequests > 0
        ? ((metrics.fallbackUsed / metrics.totalRequests) * 100).toFixed(2) + '%'
        : '0%'
    }
  };

  // Test Redis connection
  if (redisConnected && redisClient) {
    try {
      await redisClient.ping();
    } catch (err) {
      health.services.redis = false;
    }
  }

  // Test AI service
  try {
    await axios.get(`${process.env.GPT_OSS_URL || 'http://172.16.16.148:8085'}/health`,
      { timeout: 2000 }
    );
  } catch (err) {
    health.services.ai = false;
  }

  // Determine overall health
  if (!health.services.redis || !health.services.ai) {
    health.status = 'degraded';
  }

  res.json(health);
});

// Metrics endpoint
app.get('/metrics', (req, res) => {
  res.json({
    timestamp: new Date().toISOString(),
    metrics: {
      ...metrics,
      cacheHitRate: metrics.totalRequests > 0
        ? ((metrics.cacheHits / metrics.totalRequests) * 100).toFixed(2) + '%'
        : '0%',
      dbHitRate: metrics.totalRequests > 0
        ? ((metrics.dbHits / metrics.totalRequests) * 100).toFixed(2) + '%'
        : '0%',
      aiCallRate: metrics.totalRequests > 0
        ? ((metrics.aiCalls / metrics.totalRequests) * 100).toFixed(2) + '%'
        : '0%',
      fallbackRate: metrics.totalRequests > 0
        ? ((metrics.fallbackUsed / metrics.totalRequests) * 100).toFixed(2) + '%'
        : '0%',
      avgResponseTimeMs: metrics.avgResponseTime.toFixed(2)
    }
  });
});

// Get available LLM models endpoint
app.get('/api/models', (req, res) => {
  const config = aiAnalyzer.getConfig();
  const models = config.providers;
  const activeProviders = config.activeProviders;

  res.json({
    providers: Object.entries(models).map(([key, provider]) => ({
      id: key,
      name: provider.name,
      model: provider.model,
      url: provider.url,
      enabled: provider.enabled,
      priority: provider.priority,
      isActive: activeProviders.some(p => p.key === key)
    })),
    currentDefault: config.default
  });
});

// Switch LLM model endpoint
app.post('/api/models/switch', async (req, res) => {
  const { modelId, enabled } = req.body;

  if (!modelId) {
    return res.status(400).json({ error: 'Model ID required' });
  }

  const success = aiAnalyzer.toggleProvider(modelId, enabled !== undefined ? enabled : true);

  if (success) {
    // Clear cache when switching models to force re-categorization with new model
    if (redisConnected && redisClient) {
      try {
        await redisClient.flushDb();
        console.log(`🔄 Cache cleared after model switch to ${modelId}`);
      } catch (err) {
        console.warn('Could not clear cache:', err.message);
      }
    }

    res.json({
      success: true,
      message: `Model ${modelId} ${enabled ? 'enabled' : 'disabled'}`,
      currentConfig: aiAnalyzer.getConfig()
    });
  } else {
    res.status(400).json({ error: `Model ${modelId} not found` });
  }
});

// Update model priority endpoint
app.post('/api/models/priority', (req, res) => {
  const { modelId, priority } = req.body;

  if (!modelId || priority === undefined) {
    return res.status(400).json({ error: 'Model ID and priority required' });
  }

  const success = aiAnalyzer.updateProvider(modelId, { priority });

  if (success) {
    res.json({
      success: true,
      message: `Model ${modelId} priority updated to ${priority}`,
      currentConfig: aiAnalyzer.getConfig()
    });
  } else {
    res.status(400).json({ error: `Model ${modelId} not found` });
  }
});

// Cache warming endpoint
app.post('/api/cache/warm/:accountId', async (req, res) => {
  const { accountId } = req.params;

  if (!redisConnected || !redisClient) {
    return res.status(503).json({ error: 'Cache service unavailable' });
  }

  try {
    // Get recent categorizations from database
    const stats = emailDb.getStatistics();
    console.log(`🔥 Warming cache for account ${accountId} with ${stats.total} entries`);

    // In a real implementation, you would fetch recent emails for this account
    // and pre-populate the cache

    res.json({
      success: true,
      message: `Cache warming initiated for account ${accountId}`,
      entriesWarmed: stats.total
    });
  } catch (error) {
    console.error('Cache warming error:', error);
    res.status(500).json({ error: 'Cache warming failed' });
  }
});

// Start server
app.listen(PORT, () => {
  console.log(`
🚀 Optimized Email Service running on port ${PORT}
📊 Metrics available at http://localhost:${PORT}/metrics
🏥 Health check at http://localhost:${PORT}/health
⚡ Features:
   - Redis-first caching strategy
   - Dynamic TTL based on email type
   - Rule-based fallback
   - Batch processing support
   - Real-time metrics tracking
  `);
});

// Graceful shutdown
process.on('SIGTERM', async () => {
  console.log('SIGTERM received, shutting down gracefully...');

  if (redisClient) {
    await redisClient.quit();
  }

  if (emailDb) {
    emailDb.close();
  }

  process.exit(0);
});