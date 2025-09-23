const Database = require('better-sqlite3');
const path = require('path');
const crypto = require('crypto');

class EmailDatabase {
  constructor() {
    const dbPath = path.join(__dirname, 'email_categorizations.db');
    this.db = new Database(dbPath);
    this.initDatabase();
  }

  initDatabase() {
    // Create email_categories table if it doesn't exist
    this.db.exec(`
      CREATE TABLE IF NOT EXISTS email_categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email_uid TEXT NOT NULL,
        email_hash TEXT NOT NULL,
        subject TEXT,
        from_address TEXT,
        category TEXT,
        priority TEXT,
        sentiment TEXT,
        topics TEXT,
        action_required BOOLEAN,
        summary TEXT,
        raw_result TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(email_hash)
      );

      CREATE INDEX IF NOT EXISTS idx_email_uid ON email_categories(email_uid);
      CREATE INDEX IF NOT EXISTS idx_email_hash ON email_categories(email_hash);
      CREATE INDEX IF NOT EXISTS idx_category ON email_categories(category);
      CREATE INDEX IF NOT EXISTS idx_created_at ON email_categories(created_at);
    `);

    console.log('✅ SQLite database initialized at:', this.db.name);
  }

  // Generate a unique hash for an email based on UID and subject
  generateEmailHash(email) {
    const uid = email.uid || 'unknown';
    const subject = email.subject || '';
    const from = email.from || '';
    const content = `${uid}:${subject}:${from}`;
    return crypto.createHash('md5').update(content).digest('hex');
  }

  // Save email categorization to database
  async saveCategorization(email, categorization) {
    try {
      const emailHash = this.generateEmailHash(email);
      const topics = Array.isArray(categorization.topics)
        ? JSON.stringify(categorization.topics)
        : categorization.topics;

      const stmt = this.db.prepare(`
        INSERT OR REPLACE INTO email_categories (
          email_uid, email_hash, subject, from_address,
          category, priority, sentiment, topics,
          action_required, summary, raw_result, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
      `);

      const result = stmt.run(
        email.uid || 'unknown',
        emailHash,
        email.subject,
        email.from,
        categorization.category,
        categorization.priority,
        categorization.sentiment,
        topics,
        categorization.action_required ? 1 : 0,
        categorization.summary,
        JSON.stringify(categorization),
      );

      console.log(`💾 Saved categorization to DB for: ${email.subject?.substring(0, 30)}...`);
      return result;
    } catch (error) {
      console.error('Database save error:', error);
      throw error;
    }
  }

  // Get categorization from database
  async getCategorization(email) {
    try {
      const emailHash = this.generateEmailHash(email);

      const stmt = this.db.prepare(`
        SELECT * FROM email_categories
        WHERE email_hash = ?
        ORDER BY updated_at DESC
        LIMIT 1
      `);

      const row = stmt.get(emailHash);

      if (row) {
        console.log(`📚 Found categorization in DB for: ${email.subject?.substring(0, 30)}...`);
        // Parse the stored JSON data
        const categorization = JSON.parse(row.raw_result);
        return categorization;
      }

      return null;
    } catch (error) {
      console.error('Database fetch error:', error);
      return null;
    }
  }

  // Get categorization statistics
  getStatistics() {
    try {
      const stats = this.db.prepare(`
        SELECT
          COUNT(*) as total,
          COUNT(DISTINCT category) as categories,
          SUM(CASE WHEN action_required = 1 THEN 1 ELSE 0 END) as action_required,
          COUNT(DISTINCT DATE(created_at)) as days_active
        FROM email_categories
      `).get();

      const categoryBreakdown = this.db.prepare(`
        SELECT category, COUNT(*) as count
        FROM email_categories
        GROUP BY category
        ORDER BY count DESC
      `).all();

      return {
        ...stats,
        categoryBreakdown
      };
    } catch (error) {
      console.error('Statistics error:', error);
      return null;
    }
  }

  // Clean up old entries (optional, keeps last 30 days by default)
  cleanup(daysToKeep = 30) {
    try {
      const stmt = this.db.prepare(`
        DELETE FROM email_categories
        WHERE created_at < datetime('now', '-' || ? || ' days')
      `);

      const result = stmt.run(daysToKeep);
      console.log(`🧹 Cleaned up ${result.changes} old entries`);
      return result.changes;
    } catch (error) {
      console.error('Cleanup error:', error);
      return 0;
    }
  }

  // Close database connection
  close() {
    this.db.close();
    console.log('Database connection closed');
  }
}

module.exports = EmailDatabase;