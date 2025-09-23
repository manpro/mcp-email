const Redis = require('ioredis');

class CacheService {
  constructor() {
    // Connect to Redis (will use Docker container)
    this.redis = new Redis({
      host: process.env.REDIS_HOST || 'localhost',
      port: process.env.REDIS_PORT || 6381,  // Using 6381 to avoid conflict
      retryStrategy: (times) => {
        const delay = Math.min(times * 50, 2000);
        return delay;
      }
    });

    this.redis.on('error', (err) => {
      console.error('Redis Client Error:', err);
    });

    this.redis.on('connect', () => {
      console.log('Redis Client Connected');
    });

    // Default TTL values (in seconds)
    this.TTL = {
      EMAILS: 300,        // 5 minutes for email lists
      EMAIL_DETAIL: 600,  // 10 minutes for individual emails
      MAILBOXES: 1800,    // 30 minutes for mailbox structure
      AI_ANALYSIS: 3600, // 1 hour for AI analysis results
      CONNECTIONS: 900    // 15 minutes for connection status
    };
  }

  /**
   * Generate cache key with account namespace
   * @param {string} accountId - Unique identifier for the account (connectionId or userId)
   * @param {string} keyType - Type of data being cached
   * @param {string} identifier - Additional identifier (mailbox name, email uid, etc)
   */
  generateKey(accountId, keyType, identifier = '') {
    const parts = ['email', accountId, keyType];
    if (identifier) {
      parts.push(identifier);
    }
    return parts.join(':');
  }

  /**
   * Get cached data
   * @param {string} key - Cache key
   * @returns {Promise<any|null>} Cached data or null if not found
   */
  async get(key) {
    try {
      const data = await this.redis.get(key);
      if (data) {
        console.log(`Cache HIT: ${key}`);
        return JSON.parse(data);
      }
      console.log(`Cache MISS: ${key}`);
      return null;
    } catch (error) {
      console.error(`Cache GET error for ${key}:`, error);
      return null;
    }
  }

  /**
   * Set cache data with TTL
   * @param {string} key - Cache key
   * @param {any} value - Data to cache
   * @param {number} ttl - Time to live in seconds
   */
  async set(key, value, ttl) {
    try {
      await this.redis.set(key, JSON.stringify(value), 'EX', ttl);
      console.log(`Cache SET: ${key} (TTL: ${ttl}s)`);
    } catch (error) {
      console.error(`Cache SET error for ${key}:`, error);
    }
  }

  /**
   * Delete cached data
   * @param {string} key - Cache key
   */
  async del(key) {
    try {
      await this.redis.del(key);
      console.log(`Cache DEL: ${key}`);
    } catch (error) {
      console.error(`Cache DEL error for ${key}:`, error);
    }
  }

  /**
   * Clear all cache for a specific account
   * @param {string} accountId - Account identifier
   */
  async clearAccount(accountId) {
    try {
      const pattern = `email:${accountId}:*`;
      const keys = await this.redis.keys(pattern);
      if (keys.length > 0) {
        await this.redis.del(...keys);
        console.log(`Cleared ${keys.length} cache entries for account ${accountId}`);
      }
    } catch (error) {
      console.error(`Error clearing cache for account ${accountId}:`, error);
    }
  }

  /**
   * Cache email list
   */
  async cacheEmails(accountId, mailbox, emails, limit) {
    const key = this.generateKey(accountId, 'emails', `${mailbox}:${limit}`);
    await this.set(key, emails, this.TTL.EMAILS);
  }

  /**
   * Get cached email list
   */
  async getCachedEmails(accountId, mailbox, limit) {
    const key = this.generateKey(accountId, 'emails', `${mailbox}:${limit}`);
    return await this.get(key);
  }

  /**
   * Cache mailbox list
   */
  async cacheMailboxes(accountId, mailboxes) {
    const key = this.generateKey(accountId, 'mailboxes');
    await this.set(key, mailboxes, this.TTL.MAILBOXES);
  }

  /**
   * Get cached mailbox list
   */
  async getCachedMailboxes(accountId) {
    const key = this.generateKey(accountId, 'mailboxes');
    return await this.get(key);
  }

  /**
   * Cache AI analysis for an email
   */
  async cacheAIAnalysis(accountId, emailUid, analysis) {
    const key = this.generateKey(accountId, 'ai', emailUid);
    await this.set(key, analysis, this.TTL.AI_ANALYSIS);
  }

  /**
   * Get cached AI analysis
   */
  async getCachedAIAnalysis(accountId, emailUid) {
    const key = this.generateKey(accountId, 'ai', emailUid);
    return await this.get(key);
  }

  /**
   * Cache connection status
   */
  async cacheConnectionStatus(connectionId, status) {
    const key = this.generateKey('connections', connectionId);
    await this.set(key, status, this.TTL.CONNECTIONS);
  }

  /**
   * Get cached connection status
   */
  async getCachedConnectionStatus(connectionId) {
    const key = this.generateKey('connections', connectionId);
    return await this.get(key);
  }

  /**
   * Invalidate specific cache entries when emails are modified
   */
  async invalidateEmailCache(accountId, mailbox) {
    const pattern = this.generateKey(accountId, 'emails', `${mailbox}:*`);
    try {
      const keys = await this.redis.keys(pattern);
      if (keys.length > 0) {
        await this.redis.del(...keys);
        console.log(`Invalidated ${keys.length} email cache entries for ${accountId}/${mailbox}`);
      }
    } catch (error) {
      console.error(`Error invalidating email cache:`, error);
    }
  }

  /**
   * Get cache statistics
   */
  async getStats() {
    try {
      const info = await this.redis.info('stats');
      const dbSize = await this.redis.dbsize();
      return {
        connected: this.redis.status === 'ready',
        totalKeys: dbSize,
        info: info
      };
    } catch (error) {
      console.error('Error getting cache stats:', error);
      return { connected: false, error: error.message };
    }
  }

  /**
   * Close Redis connection
   */
  async close() {
    await this.redis.quit();
    console.log('Redis connection closed');
  }
}

// Export singleton instance
module.exports = new CacheService();