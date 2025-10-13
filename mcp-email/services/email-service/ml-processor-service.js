/**
 * ML Processor Service - Separate process for ML categorization
 *
 * This service:
 * 1. Listens to ML processing queue
 * 2. Processes emails with controlled concurrency
 * 3. Handles retries and circuit breaking
 * 4. Updates results back to Redis/DB
 *
 * CPU Fix (2025-10-10):
 * - Fixed queue.count() Promise not being awaited (caused busy-wait loop)
 * - Added 100ms delay in processing to prevent CPU spinning
 * - Improved Redis reconnect with exponential backoff
 * - Added error handler to prevent Redis crashes
 * - Fixed retry stats counter
 */

const Bull = require('bull');
const redis = require('redis');
const axios = require('axios');
const EmailDatabase = require('./database');

// Configuration
const REDIS_HOST = process.env.REDIS_HOST || '172.17.0.1';
const REDIS_PORT = process.env.REDIS_PORT || 6381;
const WORKER_CONCURRENCY = parseInt(process.env.ML_WORKERS) || 2;
const ML_TIMEOUT = parseInt(process.env.ML_TIMEOUT) || 5000;

// ML Models configuration
const ML_MODELS = {
  primary: {
    name: 'GPT-OSS 20B',
    url: 'http://172.17.0.1:8085/v1/chat/completions',
    model: 'gpt-oss:20b',
    timeout: ML_TIMEOUT,
    retries: 2
  },
  fallback: {
    name: 'Qwen 2.5 7B',
    url: 'http://mini:1234/v1/chat/completions',
    model: 'qwen2.5:7b',
    timeout: ML_TIMEOUT,
    retries: 1
  }
};

// Circuit Breaker implementation
class CircuitBreaker {
  constructor(name, threshold = 5, timeout = 60000) {
    this.name = name;
    this.failureCount = 0;
    this.threshold = threshold;
    this.timeout = timeout;
    this.state = 'CLOSED'; // CLOSED, OPEN, HALF_OPEN
    this.nextAttempt = Date.now();
  }

  async execute(fn) {
    if (this.state === 'OPEN') {
      if (Date.now() < this.nextAttempt) {
        throw new Error(`Circuit breaker is OPEN for ${this.name}`);
      }
      this.state = 'HALF_OPEN';
    }

    try {
      const result = await fn();
      this.onSuccess();
      return result;
    } catch (error) {
      this.onFailure();
      throw error;
    }
  }

  onSuccess() {
    this.failureCount = 0;
    this.state = 'CLOSED';
    console.log(`✅ Circuit breaker ${this.name}: CLOSED`);
  }

  onFailure() {
    this.failureCount++;
    if (this.failureCount >= this.threshold) {
      this.state = 'OPEN';
      this.nextAttempt = Date.now() + this.timeout;
      console.log(`🔥 Circuit breaker ${this.name}: OPEN for ${this.timeout}ms`);
    }
  }
}

class MLProcessorService {
  constructor() {
    this.queue = null;
    this.redisClient = null;
    this.db = new EmailDatabase();
    this.circuitBreakers = {
      primary: new CircuitBreaker('GPT-OSS'),
      fallback: new CircuitBreaker('Qwen')
    };
    this.stats = {
      processed: 0,
      failed: 0,
      retried: 0,
      startTime: Date.now()
    };
  }

  async initialize() {
    console.log('🚀 Starting ML Processor Service...');

    // Initialize Redis connection with better backoff strategy
    this.redisClient = redis.createClient({
      socket: {
        host: REDIS_HOST,
        port: REDIS_PORT,
        reconnectStrategy: (retries) => {
          // Exponential backoff: 100ms, 200ms, 400ms, 800ms, max 5s
          const delay = Math.min(retries * 100 * Math.pow(2, Math.min(retries, 5)), 5000);
          console.log(`⏳ Redis reconnect attempt ${retries}, waiting ${delay}ms`);
          return delay;
        }
      }
    });

    // Add error handler to prevent crash
    this.redisClient.on('error', (err) => {
      console.error('❌ Redis error:', err.message);
    });

    await this.redisClient.connect();
    console.log(`✅ Connected to Redis at ${REDIS_HOST}:${REDIS_PORT}`);

    // Initialize Bull queue
    this.queue = new Bull('ml-processing', {
      redis: {
        host: REDIS_HOST,
        port: REDIS_PORT
      }
    });

    // Set up queue event handlers
    this.setupQueueEvents();

    // Database is auto-initialized in constructor
    console.log('✅ Database initialized');

    // Start processing queue
    this.startProcessing();

    // Start metrics reporting
    this.startMetricsReporting();

    console.log(`🎯 ML Processor ready with ${WORKER_CONCURRENCY} workers`);
  }

  setupQueueEvents() {
    this.queue.on('completed', (job, result) => {
      this.stats.processed++;
      console.log(`✅ Job ${job.id} completed for email ${job.data.emailUid}`);
    });

    this.queue.on('failed', (job, error) => {
      this.stats.failed++;
      console.error(`❌ Job ${job.id} failed:`, error.message);
    });

    this.queue.on('stalled', (job) => {
      console.warn(`⚠️ Job ${job.id} stalled`);
    });
  }

  startProcessing() {
    // Process queue with controlled concurrency and CPU throttling
    this.queue.process(WORKER_CONCURRENCY, async (job) => {
      const { emailUid, emailData, priority } = job.data;

      try {
        console.log(`🔄 Processing email ${emailUid} (priority: ${priority})`);

        // Add small delay to prevent CPU spinning when queue is empty
        await new Promise(resolve => setTimeout(resolve, 100));

        // Try to get ML result (might be from retry)
        let result = await this.getCachedResult(emailUid);

        if (!result) {
          // Process with ML
          result = await this.processWithML(emailData);

          // Cache the result
          await this.cacheResult(emailUid, result);

          // Save to database
          await this.db.saveCategorization({ uid: emailUid }, result);

          // Publish completion event (for WebSocket notification)
          await this.publishCompletion(emailUid, result);
        }

        return result;

      } catch (error) {
        console.error(`❌ Failed to process ${emailUid}:`, error.message);

        // Check if we should retry
        if (job.attemptsMade < 3) {
          this.stats.retried++;
          throw error; // Bull will retry
        }

        // Final failure - use fallback
        const fallback = this.getFallbackCategorization(emailData);
        await this.cacheResult(emailUid, fallback);
        return fallback;
      }
    });
  }

  async processWithML(emailData) {
    // Try primary model with circuit breaker
    try {
      return await this.circuitBreakers.primary.execute(
        () => this.callMLModel(ML_MODELS.primary, emailData)
      );
    } catch (primaryError) {
      console.warn(`⚠️ Primary model failed: ${primaryError.message}`);

      // Try fallback model
      try {
        return await this.circuitBreakers.fallback.execute(
          () => this.callMLModel(ML_MODELS.fallback, emailData)
        );
      } catch (fallbackError) {
        console.error(`❌ Both models failed: ${fallbackError.message}`);
        throw fallbackError;
      }
    }
  }

  async callMLModel(modelConfig, emailData) {
    const prompt = `Analyze this email and provide JSON categorization:
From: ${emailData.from || 'Unknown'}
Subject: ${emailData.subject || 'No subject'}
Content: ${(emailData.text || emailData.bodyPreview || '').substring(0, 500)}

Return JSON with:
- category: work/personal/newsletter/spam/invoice/security/meetings/automated/social/other
- priority: high/medium/low
- sentiment: positive/neutral/negative
- summary: one sentence (max 20 words)
- topics: array of 3 main topics
- action_required: boolean`;

    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), modelConfig.timeout);

    try {
      const response = await axios.post(modelConfig.url, {
        model: modelConfig.model,
        messages: [
          {
            role: 'system',
            content: 'You are an email categorization AI. Always return valid JSON only.'
          },
          { role: 'user', content: prompt }
        ],
        temperature: 0.3,
        max_tokens: 200
      }, {
        signal: controller.signal,
        timeout: modelConfig.timeout
      });

      clearTimeout(timeout);

      const content = response.data.choices[0].message.content;
      const jsonMatch = content.match(/\{[\s\S]*?\}/);

      if (jsonMatch) {
        const result = JSON.parse(jsonMatch[0]);
        console.log(`✅ ${modelConfig.name} categorized as: ${result.category}`);
        return result;
      }

      throw new Error('Invalid JSON response from ML model');

    } catch (error) {
      clearTimeout(timeout);

      if (error.name === 'AbortError' || error.code === 'ECONNABORTED') {
        throw new Error(`${modelConfig.name} timeout after ${modelConfig.timeout}ms`);
      }

      throw error;
    }
  }

  getFallbackCategorization(emailData) {
    // Simple rule-based fallback
    const subject = (emailData.subject || '').toLowerCase();
    const from = (emailData.from || '').toLowerCase();

    let category = 'other';
    let priority = 'medium';

    // Simple rules
    if (subject.includes('invoice') || subject.includes('payment')) {
      category = 'invoice';
      priority = 'high';
    } else if (subject.includes('meeting') || subject.includes('calendar')) {
      category = 'meetings';
      priority = 'high';
    } else if (from.includes('noreply') || from.includes('newsletter')) {
      category = 'newsletter';
      priority = 'low';
    } else if (subject.includes('spam') || subject.includes('unsubscribe')) {
      category = 'spam';
      priority = 'low';
    }

    return {
      category,
      priority,
      sentiment: 'neutral',
      summary: `Email about: ${subject.substring(0, 50)}`,
      topics: [],
      action_required: priority === 'high',
      method: 'fallback'
    };
  }

  async getCachedResult(emailUid) {
    try {
      const cached = await this.redisClient.get(`email:${emailUid}:ml`);
      return cached ? JSON.parse(cached) : null;
    } catch (error) {
      console.warn('Cache read error:', error.message);
      return null;
    }
  }

  async cacheResult(emailUid, result) {
    try {
      await this.redisClient.setEx(
        `email:${emailUid}:ml`,
        86400, // 24 hours
        JSON.stringify(result)
      );
    } catch (error) {
      console.warn('Cache write error:', error.message);
    }
  }

  async publishCompletion(emailUid, result) {
    try {
      // Publish to Redis pub/sub for real-time updates
      await this.redisClient.publish('ml-completions', JSON.stringify({
        emailUid,
        result,
        timestamp: Date.now()
      }));
    } catch (error) {
      console.warn('Publish error:', error.message);
    }
  }

  startMetricsReporting() {
    setInterval(async () => {
      try {
        const uptime = Math.floor((Date.now() - this.stats.startTime) / 1000);
        const rate = this.stats.processed / (uptime / 60);

        // Fix: await queue.count() as it returns a Promise
        const queueSize = this.queue ? await this.queue.count() : 0;

        console.log(`📊 ML Processor Stats:
  - Processed: ${this.stats.processed}
  - Failed: ${this.stats.failed}
  - Retried: ${this.stats.retried}
  - Rate: ${rate.toFixed(2)}/min
  - Uptime: ${uptime}s
  - Queue size: ${queueSize}`);
      } catch (error) {
        console.warn('⚠️ Metrics reporting error:', error.message);
      }
    }, 30000); // Every 30 seconds
  }

  async shutdown() {
    console.log('🛑 Shutting down ML Processor...');

    if (this.queue) {
      await this.queue.close();
    }

    if (this.redisClient) {
      await this.redisClient.quit();
    }

    console.log('👋 ML Processor stopped');
  }
}

// Start the service
const processor = new MLProcessorService();

processor.initialize().catch(error => {
  console.error('Failed to start ML Processor:', error);
  process.exit(1);
});

// Handle graceful shutdown
process.on('SIGTERM', async () => {
  await processor.shutdown();
  process.exit(0);
});

process.on('SIGINT', async () => {
  await processor.shutdown();
  process.exit(0);
});