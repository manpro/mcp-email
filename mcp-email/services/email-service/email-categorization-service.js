const redis = require('redis');
const EventEmitter = require('events');

/**
 * Centralized Email Categorization Service
 * Single source of truth for all email categorization logic
 */
class EmailCategorizationService extends EventEmitter {
  constructor(redisClient, mlService, options = {}) {
    super();
    this.redis = redisClient;
    this.mlService = mlService;
    this.options = {
      mlConfidenceThreshold: 0.8,
      cacheExpiry: 3600, // 1 hour
      ...options
    };

    this.defaultCategories = [
      'newsletter', 'work', 'personal', 'invoice', 'security',
      'meetings', 'automated', 'social', 'spam', 'other'
    ];
  }

  /**
   * Main categorization method - single source of truth
   * Priority: User Override > ML Analysis > Rule-based
   */
  async categorizeEmail(email, userId = 'default') {
    try {
      // 1. Check user manual category override (highest priority)
      const userOverride = await this.getUserCategoryOverride(email.uid || email.id, userId);
      if (userOverride) {
        console.log(`📌 Using user override: ${userOverride.category} for email ${email.uid}`);
        return {
          category: userOverride.category,
          source: 'user_override',
          confidence: 1.0,
          timestamp: userOverride.timestamp
        };
      }

      // 2. Check cache first
      const cached = await this.getCachedCategory(email.uid || email.id);
      if (cached) {
        console.log(`💾 Using cached category: ${cached.category} for email ${email.uid}`);
        return cached;
      }

      // 3. ML Analysis (if available and confident)
      if (this.mlService) {
        try {
          const mlResult = await this.mlService.categorize(email);
          if (mlResult && mlResult.confidence >= this.options.mlConfidenceThreshold) {
            const result = {
              category: mlResult.category,
              source: 'ml_analysis',
              confidence: mlResult.confidence,
              priority: mlResult.priority || 'medium',
              sentiment: mlResult.sentiment || 'neutral',
              topics: mlResult.topics || [],
              actionRequired: mlResult.action_required || false,
              summary: mlResult.summary || `ML categorized as ${mlResult.category}`,
              timestamp: Date.now()
            };

            // Cache the result
            await this.setCachedCategory(email.uid || email.id, result);
            console.log(`🤖 ML categorized: ${result.category} (confidence: ${result.confidence}) for email ${email.uid}`);
            return result;
          }
        } catch (mlError) {
          console.warn('ML categorization failed, falling back to rules:', mlError.message);
        }
      }

      // 4. Rule-based categorization (fallback)
      const ruleResult = this.ruleBasedCategorize(email);
      const result = {
        category: ruleResult.category,
        source: 'rule_based',
        confidence: ruleResult.confidence,
        priority: ruleResult.priority || 'medium',
        sentiment: 'neutral',
        topics: ruleResult.topics || [],
        actionRequired: false,
        summary: `Rule-based categorization: ${ruleResult.category}`,
        timestamp: Date.now()
      };

      // Cache the result
      await this.setCachedCategory(email.uid || email.id, result);
      console.log(`📋 Rule-based categorized: ${result.category} for email ${email.uid}`);
      return result;

    } catch (error) {
      console.error('Categorization error:', error);
      return {
        category: 'other',
        source: 'error_fallback',
        confidence: 0.1,
        priority: 'medium',
        sentiment: 'neutral',
        topics: [],
        actionRequired: false,
        summary: 'Categorization failed',
        timestamp: Date.now()
      };
    }
  }

  /**
   * Set user manual category override
   */
  async setUserCategoryOverride(emailId, userId, category, metadata = {}) {
    const key = `user_category:${userId}:${emailId}`;
    const data = {
      category,
      timestamp: Date.now(),
      metadata
    };

    await this.redisSet(key, 86400 * 30, JSON.stringify(data)); // 30 days

    // Emit event for ML training
    this.emit('category_override', {
      emailId,
      userId,
      category,
      timestamp: data.timestamp,
      metadata
    });

    console.log(`✅ User category override set: ${category} for email ${emailId} by user ${userId}`);

    // Clear cache to force recategorization
    await this.clearCachedCategory(emailId);

    return data;
  }

  /**
   * Get user manual category override
   */
  async getUserCategoryOverride(emailId, userId) {
    const key = `user_category:${userId}:${emailId}`;
    try {
      const data = await this.redisGet(key);
      return data ? JSON.parse(data) : null;
    } catch (error) {
      console.error('Error getting user category override:', error);
      return null;
    }
  }

  /**
   * Rule-based categorization logic
   */
  ruleBasedCategorize(email) {
    const from = (email.from || '').toLowerCase();
    const subject = (email.subject || '').toLowerCase();
    const text = (email.text || email.bodyPreview || '').toLowerCase();

    // Urgent/Critical
    if (subject.includes('brådskande') || subject.includes('urgent') ||
        subject.includes('akut') || subject.includes('emergency')) {
      return { category: 'urgent', confidence: 0.9, priority: 'critical', topics: ['urgent'] };
    }

    // Security
    if (subject.includes('säkerhet') || subject.includes('verifiering') ||
        subject.includes('lösenord') || subject.includes('security') ||
        subject.includes('verification') || subject.includes('inloggning')) {
      return { category: 'security', confidence: 0.9, priority: 'high', topics: ['security'] };
    }

    // Meetings
    if (subject.includes('möte') || subject.includes('meeting') ||
        subject.includes('kallelse') || text.includes('zoom') ||
        text.includes('calendar') || subject.includes('invitation')) {
      return { category: 'meetings', confidence: 0.8, priority: 'medium', topics: ['meeting'] };
    }

    // Newsletters
    if (from.includes('newsletter') || from.includes('noreply') ||
        from.includes('marketing') || subject.includes('nyhetsbrev') ||
        text.includes('unsubscribe') || text.includes('avprenumerera')) {
      return { category: 'newsletter', confidence: 0.9, priority: 'low', topics: ['newsletter'] };
    }

    // Work
    if (from.includes('@company.') || from.includes('@work.') ||
        subject.includes('projekt') || subject.includes('rapport') ||
        subject.includes('deadline') || subject.includes('budget')) {
      return { category: 'work', confidence: 0.8, priority: 'medium', topics: ['work'] };
    }

    // Invoices/Financial
    if (subject.includes('faktura') || subject.includes('invoice') ||
        text.includes('betalning') || text.includes('payment')) {
      return { category: 'invoice', confidence: 0.9, priority: 'high', topics: ['financial'] };
    }

    // Social
    if (from.includes('facebook') || from.includes('twitter') ||
        from.includes('instagram') || from.includes('linkedin')) {
      return { category: 'social', confidence: 0.8, priority: 'low', topics: ['social'] };
    }

    // Spam
    if (subject.includes('spam') || subject.includes('winner') ||
        subject.includes('congratulations') || text.includes('click here now')) {
      return { category: 'spam', confidence: 0.9, priority: 'low', topics: ['spam'] };
    }

    // Automated
    if (from.includes('noreply') || from.includes('donotreply') ||
        from.includes('automated') || from.includes('system') ||
        subject.includes('bekräftelse') || subject.includes('confirmation')) {
      return { category: 'automated', confidence: 0.7, priority: 'low', topics: ['automated'] };
    }

    // Default to personal
    return { category: 'personal', confidence: 0.5, priority: 'medium', topics: ['personal'] };
  }

  /**
   * Get category statistics for a user
   */
  async getCategoryStats(emails, userId = 'default') {
    const stats = {
      categories: {},
      priorities: {},
      sources: {},
      total: emails.length,
      unread: 0
    };

    // Initialize categories
    this.defaultCategories.forEach(cat => {
      stats.categories[cat] = 0;
    });

    for (const email of emails) {
      // Count unread
      if (!email.seen) {
        stats.unread++;
      }

      // Get categorization
      const result = await this.categorizeEmail(email, userId);

      // Count categories
      if (stats.categories[result.category] !== undefined) {
        stats.categories[result.category]++;
      } else {
        stats.categories[result.category] = 1;
      }

      // Count priorities
      stats.priorities[result.priority] = (stats.priorities[result.priority] || 0) + 1;

      // Count sources
      stats.sources[result.source] = (stats.sources[result.source] || 0) + 1;
    }

    return stats;
  }

  /**
   * Cache methods
   */
  async getCachedCategory(emailId) {
    try {
      const data = await this.redisGet(`email_category:${emailId}`);
      return data ? JSON.parse(data) : null;
    } catch (error) {
      return null;
    }
  }

  async setCachedCategory(emailId, result) {
    try {
      await this.redisSet(`email_category:${emailId}`, this.options.cacheExpiry, JSON.stringify(result));
    } catch (error) {
      console.error('Cache set error:', error);
    }
  }

  async clearCachedCategory(emailId) {
    try {
      await this.redisDel(`email_category:${emailId}`);
    } catch (error) {
      console.error('Cache clear error:', error);
    }
  }

  /**
   * Redis helper methods
   */
  async redisGet(key) {
    try {
      return await this.redis.get(key);
    } catch (error) {
      console.error('Redis GET error:', error);
      return null;
    }
  }

  async redisSet(key, ttl, value) {
    try {
      return await this.redis.setEx(key, ttl, value);
    } catch (error) {
      console.error('Redis SET error:', error);
      return null;
    }
  }

  async redisDel(key) {
    try {
      return await this.redis.del(key);
    } catch (error) {
      console.error('Redis DEL error:', error);
      return null;
    }
  }
}

module.exports = EmailCategorizationService;