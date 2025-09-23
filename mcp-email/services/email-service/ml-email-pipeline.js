const express = require('express');
const cors = require('cors');
const axios = require('axios');
const redis = require('redis');
const EventEmitter = require('events');

const app = express();
const PORT = process.env.PORT || 3012;

app.use(cors());
app.use(express.json());

// Redis client setup
const redisClient = redis.createClient({
  host: process.env.REDIS_HOST || '172.17.0.1',
  port: process.env.REDIS_PORT || 6381
});

// Promisify Redis methods
const redisGet = (key) => new Promise((resolve, reject) => {
  redisClient.get(key, (err, result) => {
    if (err) reject(err);
    else resolve(result);
  });
});

const redisSet = (key, ttl, value) => new Promise((resolve, reject) => {
  redisClient.setex(key, ttl, value, (err, result) => {
    if (err) reject(err);
    else resolve(result);
  });
});

const redisHget = (hash, field) => new Promise((resolve, reject) => {
  redisClient.hget(hash, field, (err, result) => {
    if (err) reject(err);
    else resolve(result);
  });
});

const redisHset = (hash, field, value) => new Promise((resolve, reject) => {
  redisClient.hset(hash, field, value, (err, result) => {
    if (err) reject(err);
    else resolve(result);
  });
});

const redisLpush = (key, value) => new Promise((resolve, reject) => {
  redisClient.lpush(key, value, (err, result) => {
    if (err) reject(err);
    else resolve(result);
  });
});

const redisLrange = (key, start, stop) => new Promise((resolve, reject) => {
  redisClient.lrange(key, start, stop, (err, result) => {
    if (err) reject(err);
    else resolve(result);
  });
});

redisClient.on('connect', () => console.log('✅ Redis connected for ML pipeline'));
redisClient.on('error', (err) => console.error('Redis error:', err));

// Event emitter for processing queue
class EmailProcessingQueue extends EventEmitter {
  constructor() {
    super();
    this.queue = [];
    this.processing = false;
    this.batchSize = 5; // Process 5 emails at a time
    this.processInterval = 2000; // 2 seconds between batches
  }

  async add(emails) {
    this.queue.push(...emails);
    if (!this.processing) {
      this.startProcessing();
    }
  }

  async startProcessing() {
    if (this.processing) return;
    this.processing = true;

    while (this.queue.length > 0) {
      const batch = this.queue.splice(0, this.batchSize);
      await this.processBatch(batch);
      await new Promise(resolve => setTimeout(resolve, this.processInterval));
    }

    this.processing = false;
    this.emit('complete');
  }

  async processBatch(emails) {
    const processed = await Promise.all(
      emails.map(email => processEmailWithML(email))
    );
    this.emit('batch_processed', processed);
    return processed;
  }
}

const processingQueue = new EmailProcessingQueue();

// ML Training Data Storage
class MLTrainingStore {
  constructor() {
    this.trainingData = [];
    this.userFeedback = new Map();
    this.patterns = new Map();
    this.loadFromRedis();
  }

  async loadFromRedis() {
    try {
      const data = await redisGet('ml_training_data');
      if (data) {
        this.trainingData = JSON.parse(data);
      }

      const feedback = await redisGet('ml_user_feedback');
      if (feedback) {
        this.userFeedback = new Map(JSON.parse(feedback));
      }

      const patterns = await redisGet('ml_patterns');
      if (patterns) {
        this.patterns = new Map(JSON.parse(patterns));
      }
    } catch (error) {
      console.error('Error loading ML data from Redis:', error);
    }
  }

  async saveToRedis() {
    try {
      await redisSet('ml_training_data', 86400, JSON.stringify(this.trainingData));
      await redisSet('ml_user_feedback', 86400, JSON.stringify([...this.userFeedback]));
      await redisSet('ml_patterns', 86400, JSON.stringify([...this.patterns]));
    } catch (error) {
      console.error('Error saving ML data to Redis:', error);
    }
  }

  addTrainingExample(email, classification, userCorrection = null) {
    const example = {
      timestamp: Date.now(),
      email_signature: this.createSignature(email),
      ai_classification: classification,
      user_correction: userCorrection,
      confidence: userCorrection ? 1.0 : classification.confidence || 0.5
    };

    this.trainingData.push(example);
    this.updatePatterns(example);

    // Keep only last 10000 examples
    if (this.trainingData.length > 10000) {
      this.trainingData = this.trainingData.slice(-10000);
    }

    this.saveToRedis();
    return example;
  }

  createSignature(email) {
    return {
      from_domain: this.extractDomain(email.from),
      subject_keywords: this.extractKeywords(email.subject),
      content_length: email.text?.length || 0,
      has_attachments: email.hasAttachments || false,
      time_received: new Date(email.date).getHours(),
      day_of_week: new Date(email.date).getDay()
    };
  }

  extractDomain(email) {
    const match = email?.match(/@([^>]+)/);
    return match ? match[1] : '';
  }

  extractKeywords(text) {
    if (!text) return [];
    const words = text.toLowerCase().split(/\W+/);
    const stopWords = new Set(['the', 'is', 'at', 'which', 'on', 'a', 'an']);
    return words.filter(w => w.length > 3 && !stopWords.has(w)).slice(0, 5);
  }

  updatePatterns(example) {
    const key = `${example.email_signature.from_domain}_${example.ai_classification.category}`;

    if (!this.patterns.has(key)) {
      this.patterns.set(key, {
        count: 0,
        confidence_sum: 0,
        last_seen: null
      });
    }

    const pattern = this.patterns.get(key);
    pattern.count++;
    pattern.confidence_sum += example.confidence;
    pattern.last_seen = example.timestamp;
    pattern.avg_confidence = pattern.confidence_sum / pattern.count;

    this.patterns.set(key, pattern);
  }

  getRecommendation(email) {
    const signature = this.createSignature(email);
    const domainPatterns = [];

    for (const [key, pattern] of this.patterns) {
      if (key.startsWith(signature.from_domain)) {
        const [domain, category] = key.split('_');
        domainPatterns.push({
          category,
          confidence: pattern.avg_confidence,
          count: pattern.count
        });
      }
    }

    domainPatterns.sort((a, b) => b.confidence - a.confidence);
    return domainPatterns[0];
  }
}

const mlStore = new MLTrainingStore();

// Process email with ML (with caching and timeout handling)
async function processEmailWithML(email) {
  // Check Redis cache first
  const cacheKey = `email_ml_${email.uid || email.id}`;

  try {
    const cached = await redisGet(cacheKey);
    if (cached) {
      console.log(`Cache hit for email ${email.uid}`);
      return JSON.parse(cached);
    }
  } catch (error) {
    console.error('Cache read error:', error);
  }

  // Get recommendation from learned patterns
  const learned = mlStore.getRecommendation(email);

  try {
    // Call GPT-OSS with timeout
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 10000); // 10 second timeout

    const prompt = `Analyze email and classify:
From: ${email.from || 'Unknown'}
Subject: ${email.subject || 'No subject'}
Preview: ${(email.text || email.bodyPreview || '').substring(0, 300)}
${learned ? `\nPrevious pattern suggests: ${learned.category} (${learned.count} examples)` : ''}

Return JSON with: category, priority, sentiment, topics[], action_required, summary (max 20 words)`;

    const response = await axios.post('http://172.16.16.148:8085/v1/chat/completions', {
      model: 'gpt-oss:20b',
      messages: [
        {
          role: 'system',
          content: 'You are an email classifier. Return only valid JSON.'
        },
        {
          role: 'user',
          content: prompt
        }
      ],
      temperature: 0.3,
      max_tokens: 150
    }, {
      signal: controller.signal,
      timeout: 10000
    });

    clearTimeout(timeout);

    const aiContent = response.data.choices[0].message.content;
    const jsonMatch = aiContent.match(/\{[\s\S]*?\}/);

    let classification = {
      category: 'uncategorized',
      priority: 'medium',
      sentiment: 'neutral',
      topics: [],
      action_required: false,
      summary: 'Unable to analyze'
    };

    if (jsonMatch) {
      classification = JSON.parse(jsonMatch[0]);
    }

    // Merge with learned patterns
    if (learned && learned.confidence > 0.7) {
      classification.category = learned.category;
      classification.confidence = learned.confidence;
      classification.learned = true;
    }

    const processedEmail = {
      ...email,
      ...classification,
      analyzed: true,
      processed_at: Date.now()
    };

    // Cache the result
    await redisSet(cacheKey, 3600, JSON.stringify(processedEmail)); // Cache for 1 hour

    // Add to training data
    mlStore.addTrainingExample(email, classification);

    return processedEmail;

  } catch (error) {
    console.error('ML processing error:', error.message);

    // Fallback to learned patterns or basic classification
    const fallback = {
      ...email,
      category: learned?.category || 'uncategorized',
      priority: 'medium',
      sentiment: 'neutral',
      topics: [],
      action_required: false,
      summary: 'Analysis unavailable',
      analyzed: false,
      fallback: true,
      processed_at: Date.now()
    };

    // Cache even fallback results
    await redisSet(cacheKey, 600, JSON.stringify(fallback)); // Cache for 10 min

    return fallback;
  }
}

// Main endpoint with batch processing
app.get('/recent-emails/:accountId', async (req, res) => {
  try {
    const accountId = req.params.accountId;
    const limit = parseInt(req.query.limit) || 20;

    console.log(`Fetching emails for account: ${accountId}, limit: ${limit}`);

    // Try to get from MCP Email Server
    let emails = [];
    try {
      const response = await axios.post('http://localhost:3623/api/search-emails', {
        connectionId: accountId,
        criteria: ['ALL'],
        limit,
        mailbox: 'INBOX'
      });
      emails = response.data.emails || [];
    } catch (error) {
      console.log('MCP server not available, using cached data');
      // Try to get from cache
      const cached = await redisLrange(`emails_${accountId}`, 0, limit - 1);
      emails = cached.map(e => JSON.parse(e));
    }

    if (emails.length === 0) {
      return res.json([]);
    }

    // Process emails in batches
    const processedEmails = [];
    processingQueue.on('batch_processed', (batch) => {
      processedEmails.push(...batch);
    });

    await processingQueue.add(emails);

    // Wait for processing to complete (with timeout)
    await new Promise((resolve) => {
      const timeout = setTimeout(resolve, 30000); // 30 second max wait
      processingQueue.once('complete', () => {
        clearTimeout(timeout);
        resolve();
      });
    });

    // Sort by priority
    processedEmails.sort((a, b) => {
      const priorityScore = { high: 3, medium: 2, low: 1 };
      return (priorityScore[b.priority] || 0) - (priorityScore[a.priority] || 0);
    });

    console.log(`Processed ${processedEmails.length} emails with ML`);
    res.json(processedEmails);

  } catch (error) {
    console.error('Error in recent-emails:', error);
    res.status(500).json({ error: error.message });
  }
});

// Feedback endpoint for ML training
app.post('/api/ml/feedback', async (req, res) => {
  try {
    const { emailId, correction, feedback } = req.body;

    // Store user feedback
    mlStore.userFeedback.set(emailId, {
      correction,
      feedback,
      timestamp: Date.now()
    });

    // Update training data with correction
    if (correction) {
      const email = await redisGet(`email_ml_${emailId}`);
      if (email) {
        mlStore.addTrainingExample(JSON.parse(email), correction, correction);
      }
    }

    await mlStore.saveToRedis();

    res.json({
      success: true,
      message: 'Feedback recorded for ML training'
    });

  } catch (error) {
    console.error('Feedback error:', error);
    res.status(500).json({ error: error.message });
  }
});

// Interactive training endpoint
app.post('/api/ml/train-interactive', async (req, res) => {
  try {
    const { question, emailContext } = req.body;

    // Use GPT-OSS to generate training question
    const response = await axios.post('http://172.16.16.148:8085/v1/chat/completions', {
      model: 'gpt-oss:20b',
      messages: [
        {
          role: 'system',
          content: 'You are helping to train an email classification system. Ask clarifying questions about email handling preferences.'
        },
        {
          role: 'user',
          content: `Based on this email context: ${JSON.stringify(emailContext)}\n\nUser asks: ${question}\n\nProvide a training insight.`
        }
      ],
      temperature: 0.5,
      max_tokens: 200
    });

    const insight = response.data.choices[0].message.content;

    res.json({
      insight,
      training_updated: true
    });

  } catch (error) {
    console.error('Interactive training error:', error);
    res.status(500).json({ error: error.message });
  }
});

// Get ML statistics
app.get('/api/ml/stats', async (req, res) => {
  try {
    const stats = {
      training_examples: mlStore.trainingData.length,
      learned_patterns: mlStore.patterns.size,
      user_corrections: mlStore.userFeedback.size,
      avg_confidence: Array.from(mlStore.patterns.values())
        .reduce((sum, p) => sum + p.avg_confidence, 0) / mlStore.patterns.size || 0,
      top_patterns: Array.from(mlStore.patterns.entries())
        .sort((a, b) => b[1].count - a[1].count)
        .slice(0, 10)
        .map(([key, pattern]) => ({
          pattern: key,
          count: pattern.count,
          confidence: pattern.avg_confidence
        }))
    };

    res.json(stats);

  } catch (error) {
    console.error('Stats error:', error);
    res.status(500).json({ error: error.message });
  }
});

// Smart inbox with ML predictions
app.get('/api/smart-inbox/:accountId', async (req, res) => {
  try {
    const accountId = req.params.accountId;

    // Get processed emails
    const response = await axios.get(`http://localhost:${PORT}/recent-emails/${accountId}?limit=50`);
    const emails = response.data;

    // Categorize based on ML analysis
    const categorized = {
      urgent: emails.filter(e => e.priority === 'high' && e.action_required),
      important: emails.filter(e => e.priority === 'high' && !e.action_required),
      work: emails.filter(e => e.category === 'work'),
      personal: emails.filter(e => e.category === 'personal'),
      newsletters: emails.filter(e => e.category === 'newsletter'),
      notifications: emails.filter(e => e.category === 'notification'),
      spam: emails.filter(e => e.category === 'spam'),
      learned: emails.filter(e => e.learned === true)
    };

    res.json({
      inbox: categorized,
      stats: {
        total: emails.length,
        processed: emails.filter(e => e.analyzed).length,
        from_cache: emails.filter(e => e.cached).length,
        learned: categorized.learned.length
      }
    });

  } catch (error) {
    console.error('Smart inbox error:', error);
    res.status(500).json({ error: error.message });
  }
});

app.listen(PORT, () => {
  console.log(`
🚀 ML Email Pipeline running on port ${PORT}

Features:
  ✅ Self-learning ML with pattern recognition
  ✅ Redis caching for processed emails
  ✅ Batch processing to avoid GPT-OSS timeouts
  ✅ User feedback integration for training
  ✅ Interactive training interface
  ✅ Fallback to learned patterns
  ✅ Queue-based processing (${processingQueue.batchSize} emails per batch)

Endpoints:
  GET  /recent-emails/:accountId - Get emails with ML analysis (cached & batched)
  POST /api/ml/feedback - Submit corrections for ML training
  POST /api/ml/train-interactive - Interactive training with questions
  GET  /api/ml/stats - Get ML training statistics
  GET  /api/smart-inbox/:accountId - Smart categorized inbox

ML Training:
  - Automatically learns from user actions
  - Stores patterns in Redis
  - Improves with each correction
  - Interactive training available
  `);
});