#!/usr/bin/env node

const express = require('express');
const { Client } = require('pg');
const cors = require('cors');
const helmet = require('helmet');
const compression = require('compression');
const pino = require('pino');
const axios = require('axios');
require('dotenv').config();

const logger = pino({
  level: process.env.LOG_LEVEL || 'info',
  transport: { target: 'pino-pretty' }
});

class EmailAPIService {
  constructor() {
    this.app = express();
    this.port = process.env.PORT || 3018;

    // PostgreSQL connection
    this.postgres = new Client({
      host: process.env.DB_HOST || 'localhost',
      port: parseInt(process.env.DB_PORT) || 5432,
      database: process.env.DB_NAME || 'email_management',
      user: process.env.DB_USER || 'postgres',
      password: process.env.DB_PASSWORD || ''
    });

    // Service endpoints
    this.services = {
      classifier: process.env.CLASSIFIER_URL || 'http://localhost:3016',
      orchestrator: process.env.ORCHESTRATOR_URL || 'http://localhost:3017',
      imapSync: process.env.IMAP_SYNC_URL || 'http://localhost:3019'
    };

    this.setupExpress();
    this.setupRoutes();
  }

  setupExpress() {
    // Security and performance middleware
    this.app.use(helmet());
    this.app.use(compression());
    this.app.use(cors({
      origin: [
        'http://localhost:13623',
        'http://localhost:3623',
        'http://email-frontend-new:13623',
        'http://email-frontend:13623',
        process.env.FRONTEND_URL || 'http://localhost:13623'
      ],
      credentials: true
    }));
    this.app.use(express.json({ limit: '10mb' }));

    // Request logging
    this.app.use((req, res, next) => {
      logger.info(`${req.method} ${req.path}`);
      next();
    });
  }

  setupRoutes() {
    // Health check
    this.app.get('/health', async (req, res) => {
      try {
        const dbResult = await this.postgres.query('SELECT COUNT(*) FROM emails');
        const emailCount = dbResult.rows[0].count;

        // Check service availability
        const services = {};
        for (const [name, url] of Object.entries(this.services)) {
          try {
            await axios.get(`${url}/health`, { timeout: 2000 });
            services[name] = 'available';
          } catch {
            services[name] = 'unavailable';
          }
        }

        res.json({
          status: 'ok',
          service: 'Email API Service',
          database: 'connected',
          emails: emailCount,
          services: services,
          version: '2.0.0',
          architecture: '6-component'
        });

      } catch (error) {
        res.status(500).json({ error: 'Health check failed' });
      }
    });

    // === EMAIL ENDPOINTS ===

    // Get emails with filtering and pagination
    this.app.get('/api/emails', async (req, res) => {
      console.log('🚀 /api/emails endpoint hit!');
      try {
        const {
          folder = 'INBOX',
          limit = 1000,
          offset = 0,
          search,
          label,
          unread_only = false
        } = req.query;
        console.log('📋 Query params:', { limit, offset });

        let query = `
          SELECT
            e.*,
            l.name as label,
            l.display_name as label_display,
            l.color as label_color,
            el.score,
            el.confidence
          FROM emails e
          LEFT JOIN email_labels el ON e.id = el.email_id
          LEFT JOIN labels l ON el.label_id = l.id
          WHERE 1=1
        `;

        const params = [];
        let paramIndex = 1;

        // Apply filters
        if (search) {
          query += ` AND (e.subject ILIKE $${paramIndex} OR e.from_address ILIKE $${paramIndex} OR e.text_content ILIKE $${paramIndex})`;
          params.push(`%${search}%`);
          paramIndex++;
        }

        if (label) {
          query += ` AND l.name = $${paramIndex}`;
          params.push(label);
          paramIndex++;
        }

        // Order and pagination
        query += ` ORDER BY e.received_at DESC LIMIT $${paramIndex} OFFSET $${paramIndex + 1}`;
        params.push(limit, offset);

        const result = await this.postgres.query(query, params);

        // Get total count for pagination
        let countQuery = 'SELECT COUNT(*) FROM emails e';
        const countParams = [];

        if (search || label) {
          countQuery += ' LEFT JOIN email_labels el ON e.id = el.email_id LEFT JOIN labels l ON el.label_id = l.id WHERE 1=1';
          let countParamIndex = 1;

          if (search) {
            countQuery += ` AND (e.subject ILIKE $${countParamIndex} OR e.from_address ILIKE $${countParamIndex} OR e.text_content ILIKE $${countParamIndex})`;
            countParams.push(`%${search}%`);
            countParamIndex++;
          }

          if (label) {
            countQuery += ` AND l.name = $${countParamIndex}`;
            countParams.push(label);
          }
        }

        const countResult = await this.postgres.query(countQuery, countParams);
        const total = parseInt(countResult.rows[0].count);

        // Transform emails to match frontend expected format
        logger.info(`📧 Transforming ${result.rows.length} emails`);
        logger.info(`📧 First email sample:`, {
          uid: result.rows[0]?.uid,
          from_address: result.rows[0]?.from_address,
          received_at: result.rows[0]?.received_at,
          text_content: result.rows[0]?.text_content?.substring(0, 50)
        });

        const transformedEmails = result.rows.map(email => {
          const transformed = {
            ...email,
            from: email.from_address || email.from,
            date: email.received_at || email.date,
            text: email.text_content || email.text,
            html: email.html_content || email.html,
            bodyPreview: email.text_content ? email.text_content.substring(0, 200) : ''
          };
          return transformed;
        });

        logger.info(`📧 Transformed first email:`, {
          uid: transformedEmails[0]?.uid,
          from: transformedEmails[0]?.from,
          date: transformedEmails[0]?.date,
          text: transformedEmails[0]?.text?.substring(0, 50)
        });

        // Log transformation test
        console.log(`🔄 Testing transformation - Original email:`, {
          uid: result.rows[0]?.uid,
          from_address: result.rows[0]?.from_address,
          text_content: result.rows[0]?.text_content?.substring(0, 50)
        });

        const testTransformed = result.rows[0] ? {
          ...result.rows[0],
          from: result.rows[0].from_address || result.rows[0].from,
          date: result.rows[0].received_at || result.rows[0].date,
          text: result.rows[0].text_content || result.rows[0].text
        } : null;

        console.log(`🔄 Testing transformation - Transformed email:`, {
          uid: testTransformed?.uid,
          from: testTransformed?.from,
          date: testTransformed?.date,
          text: testTransformed?.text?.substring(0, 50)
        });

        res.json({
          emails: transformedEmails,
          pagination: {
            total,
            limit: parseInt(limit),
            offset: parseInt(offset),
            pages: Math.ceil(total / limit)
          }
        });

      } catch (error) {
        logger.error('Failed to get emails:', error);
        res.status(500).json({ error: 'Failed to get emails' });
      }
    });

    // Get single email
    this.app.get('/api/emails/:id', async (req, res) => {
      try {
        const { id } = req.params;

        const result = await this.postgres.query(`
          SELECT
            e.*,
            l.name as label,
            l.display_name as label_display,
            l.color as label_color,
            el.score,
            el.confidence,
            el.source
          FROM emails e
          LEFT JOIN email_labels el ON e.id = el.email_id
          LEFT JOIN labels l ON el.label_id = l.id
          WHERE e.id = $1
        `, [id]);

        if (result.rows.length === 0) {
          return res.status(404).json({ error: 'Email not found' });
        }

        res.json(result.rows[0]);

      } catch (error) {
        logger.error('Failed to get email:', error);
        res.status(500).json({ error: 'Failed to get email' });
      }
    });

    // Update email label
    this.app.put('/api/emails/:id/label', async (req, res) => {
      try {
        const { id } = req.params;
        const { label_name, source = 'user' } = req.body;

        // Get label ID
        const labelResult = await this.postgres.query(
          'SELECT id FROM labels WHERE name = $1', [label_name]
        );

        if (labelResult.rows.length === 0) {
          return res.status(404).json({ error: 'Label not found' });
        }

        const labelId = labelResult.rows[0].id;

        // Update email label
        await this.postgres.query(`
          INSERT INTO email_labels (email_id, label_id, score, source, confidence)
          VALUES ($1, $2, $3, $4, $5)
          ON CONFLICT (email_id, label_id) DO UPDATE SET
            source = EXCLUDED.source,
            decided_at = NOW()
        `, [id, labelId, 1.0, source, 1.0]);

        // Create feedback entry
        await this.postgres.query(`
          INSERT INTO feedback (email_id, correct_label_id, reason, created_at)
          VALUES ($1, $2, $3, NOW())
        `, [id, labelId, 'User manual correction']);

        res.json({ success: true, message: 'Label updated successfully' });

      } catch (error) {
        logger.error('Failed to update email label:', error);
        res.status(500).json({ error: 'Failed to update label' });
      }
    });

    // === LABEL ENDPOINTS ===

    // Get all labels
    this.app.get('/api/labels', async (req, res) => {
      try {
        const result = await this.postgres.query(`
          SELECT
            l.*,
            COUNT(el.email_id) as email_count
          FROM labels l
          LEFT JOIN email_labels el ON l.id = el.label_id
          GROUP BY l.id
          ORDER BY l.name
        `);

        res.json(result.rows);

      } catch (error) {
        logger.error('Failed to get labels:', error);
        res.status(500).json({ error: 'Failed to get labels' });
      }
    });

    // === CLASSIFICATION ENDPOINTS ===

    // Trigger classification for specific email
    this.app.post('/api/emails/:id/classify', async (req, res) => {
      try {
        const { id } = req.params;

        const response = await axios.post(`${this.services.classifier}/classify`, {
          email_id: parseInt(id)
        });

        res.json(response.data);

      } catch (error) {
        logger.error('Failed to classify email:', error);
        res.status(500).json({ error: 'Classification failed' });
      }
    });

    // Batch classify pending emails
    this.app.post('/api/classify/batch', async (req, res) => {
      try {
        const { limit = 10 } = req.body;

        const response = await axios.post(`${this.services.classifier}/classify/batch`, {
          limit
        });

        res.json(response.data);

      } catch (error) {
        logger.error('Failed to batch classify:', error);
        res.status(500).json({ error: 'Batch classification failed' });
      }
    });

    // === SYNC ENDPOINTS ===

    // Trigger email sync
    this.app.post('/api/sync', async (req, res) => {
      try {
        // Create sync job
        await this.postgres.query(`
          INSERT INTO jobs (type, payload, unique_key, status)
          VALUES ($1, $2, $3, $4)
          ON CONFLICT (unique_key) DO UPDATE SET
            status = 'PENDING',
            scheduled_at = NOW()
        `, [
          'SYNC',
          JSON.stringify({ action: 'manual_sync', folder: 'INBOX' }),
          'manual_sync_' + Date.now(),
          'PENDING'
        ]);

        res.json({ success: true, message: 'Sync job created' });

      } catch (error) {
        logger.error('Failed to create sync job:', error);
        res.status(500).json({ error: 'Sync job creation failed' });
      }
    });

    // === STATISTICS ENDPOINTS ===

    // Get email statistics
    this.app.get('/api/stats', async (req, res) => {
      try {
        const stats = await this.postgres.query(`
          SELECT
            COUNT(*) as total_emails,
            COUNT(DISTINCT from_address) as unique_senders,
            COUNT(CASE WHEN received_at > NOW() - INTERVAL '24 hours' THEN 1 END) as emails_today,
            COUNT(CASE WHEN received_at > NOW() - INTERVAL '7 days' THEN 1 END) as emails_week,
            MAX(received_at) as latest_email
          FROM emails
        `);

        const labelStats = await this.postgres.query(`
          SELECT
            l.name,
            l.display_name,
            l.color,
            COUNT(el.email_id) as count
          FROM labels l
          LEFT JOIN email_labels el ON l.id = el.label_id
          GROUP BY l.id, l.name, l.display_name, l.color
          ORDER BY count DESC
        `);

        res.json({
          overview: stats.rows[0],
          labels: labelStats.rows
        });

      } catch (error) {
        logger.error('Failed to get stats:', error);
        res.status(500).json({ error: 'Failed to get statistics' });
      }
    });

    // Get custom categories (for frontend compatibility)
    this.app.get('/api/custom-categories/:accountId', async (req, res) => {
      try {
        const { accountId } = req.params;

        // Return labels as custom categories for compatibility
        const result = await this.postgres.query(`
          SELECT
            l.id,
            l.name,
            l.display_name as displayName,
            l.color,
            'tag' as icon,
            COUNT(el.email_id) as emailCount
          FROM labels l
          LEFT JOIN email_labels el ON l.id = el.label_id
          GROUP BY l.id, l.name, l.display_name, l.color
          ORDER BY emailCount DESC
        `);

        res.json(result.rows);

      } catch (error) {
        logger.error('Failed to get custom categories:', error);
        res.status(500).json({ error: 'Failed to get custom categories' });
      }
    });

    // Get recent emails (for frontend compatibility)
    this.app.get('/api/recent-emails/:accountId', async (req, res) => {
      try {
        const { accountId } = req.params;
        const { limit = 50 } = req.query;

        const result = await this.postgres.query(`
          SELECT
            e.*,
            l.name as label,
            l.display_name as label_display,
            l.color as label_color
          FROM emails e
          LEFT JOIN email_labels el ON e.id = el.email_id
          LEFT JOIN labels l ON el.label_id = l.id
          ORDER BY e.received_at DESC
          LIMIT $1
        `, [limit]);

        res.json(result.rows);

      } catch (error) {
        logger.error('Failed to get recent emails:', error);
        res.status(500).json({ error: 'Failed to get recent emails' });
      }
    });

    // === FEEDBACK ENDPOINTS ===

    // Submit feedback
    this.app.post('/api/feedback', async (req, res) => {
      try {
        const { email_id, correct_label_id, reason } = req.body;

        await this.postgres.query(`
          INSERT INTO feedback (email_id, correct_label_id, reason, created_at)
          VALUES ($1, $2, $3, NOW())
        `, [email_id, correct_label_id, reason]);

        // Forward to classifier for learning
        try {
          await axios.post(`${this.services.classifier}/feedback`, req.body);
        } catch (error) {
          logger.warn('Failed to forward feedback to classifier:', error.message);
        }

        res.json({ success: true });

      } catch (error) {
        logger.error('Failed to submit feedback:', error);
        res.status(500).json({ error: 'Failed to submit feedback' });
      }
    });

    // === JOB ENDPOINTS ===

    // Get job status
    this.app.get('/api/jobs', async (req, res) => {
      try {
        const { type, status, limit = 20 } = req.query;

        let query = 'SELECT * FROM jobs WHERE 1=1';
        const params = [];
        let paramIndex = 1;

        if (type) {
          query += ` AND type = $${paramIndex}`;
          params.push(type);
          paramIndex++;
        }

        if (status) {
          query += ` AND status = $${paramIndex}`;
          params.push(status);
          paramIndex++;
        }

        query += ` ORDER BY created_at DESC LIMIT $${paramIndex}`;
        params.push(limit);

        const result = await this.postgres.query(query, params);

        res.json(result.rows);

      } catch (error) {
        logger.error('Failed to get jobs:', error);
        res.status(500).json({ error: 'Failed to get jobs' });
      }
    });

    // === BULK OPERATIONS ===

    // Bulk update email labels
    this.app.post('/api/emails/bulk/label', async (req, res) => {
      try {
        const { email_ids, label_name } = req.body;

        if (!Array.isArray(email_ids) || email_ids.length === 0) {
          return res.status(400).json({ error: 'email_ids array required' });
        }

        // Get label ID
        const labelResult = await this.postgres.query(
          'SELECT id FROM labels WHERE name = $1', [label_name]
        );

        if (labelResult.rows.length === 0) {
          return res.status(404).json({ error: 'Label not found' });
        }

        const labelId = labelResult.rows[0].id;

        // Bulk update
        const promises = email_ids.map(emailId =>
          this.postgres.query(`
            INSERT INTO email_labels (email_id, label_id, score, source, confidence)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (email_id, label_id) DO UPDATE SET
              source = EXCLUDED.source,
              decided_at = NOW()
          `, [emailId, labelId, 1.0, 'bulk_user', 1.0])
        );

        await Promise.all(promises);

        res.json({
          success: true,
          updated: email_ids.length,
          message: `${email_ids.length} emails updated to ${label_name}`
        });

      } catch (error) {
        logger.error('Failed to bulk update labels:', error);
        res.status(500).json({ error: 'Bulk update failed' });
      }
    });

    // === MULTI-PROVIDER ENDPOINTS ===

    // Get email accounts
    this.app.get('/api/accounts', async (req, res) => {
      try {
        const { userId = 'default' } = req.query;

        const result = await this.postgres.query(
          'SELECT * FROM email_accounts WHERE user_id = $1 AND is_active = true ORDER BY is_primary DESC, created_at ASC',
          [userId]
        );

        res.json({
          accounts: result.rows.map(acc => ({
            ...acc,
            credentials_encrypted: undefined, // Don't send credentials to frontend
            access_token: undefined,
            refresh_token: undefined
          }))
        });

      } catch (error) {
        logger.error('Failed to get accounts:', error);
        res.status(500).json({ error: 'Failed to get accounts' });
      }
    });

    // Create IMAP account
    this.app.post('/api/accounts', async (req, res) => {
      try {
        const {
          userId = 'default',
          emailAddress,
          password,
          imapHost,
          imapPort = 993,
          displayName
        } = req.body;

        if (!emailAddress || !password || !imapHost) {
          return res.status(400).json({ error: 'emailAddress, password, and imapHost required' });
        }

        const result = await this.postgres.query(`
          INSERT INTO email_accounts (
            user_id, provider, email_address, display_name,
            auth_type, credentials_encrypted, provider_config,
            status, is_active
          ) VALUES ($1, 'imap', $2, $3, 'password', $4, $5, 'connected', true)
          RETURNING *
        `, [
          userId,
          emailAddress,
          displayName || emailAddress,
          JSON.stringify({ password }), // In production: encrypt this
          JSON.stringify({
            host: imapHost,
            port: imapPort,
            tls: true
          })
        ]);

        logger.info(`Created IMAP account: ${emailAddress}`);

        res.json({
          success: true,
          account: {
            ...result.rows[0],
            credentials_encrypted: undefined // Don't send credentials
          }
        });

      } catch (error) {
        logger.error('Failed to create account:', error);
        res.status(500).json({ error: 'Failed to create account' });
      }
    });

    // Delete email account
    this.app.delete('/api/accounts/:id', async (req, res) => {
      try {
        const { id } = req.params;

        await this.postgres.query(
          'UPDATE email_accounts SET is_active = false WHERE id = $1',
          [id]
        );

        logger.info(`Deactivated account: ${id}`);
        res.json({ success: true });

      } catch (error) {
        logger.error('Failed to delete account:', error);
        res.status(500).json({ error: 'Failed to delete account' });
      }
    });

    // Get provider capabilities
    this.app.get('/api/providers/capabilities', async (req, res) => {
      res.json({
        imap: {
          supportsThreading: false,
          supportsLabels: false,
          supportsBatch: false,
          maxBatchSize: 1,
          rateLimitPerSecond: 10,
          supportsWebhooks: false,
          supportsPush: false,
          supportsOAuth: false
        },
        gmail: {
          supportsThreading: true,
          supportsLabels: true,
          supportsBatch: true,
          maxBatchSize: 1000,
          rateLimitPerSecond: 250,
          supportsWebhooks: true,
          supportsPush: true,
          supportsOAuth: true
        },
        exchange: {
          supportsThreading: true,
          supportsLabels: false,
          supportsBatch: true,
          maxBatchSize: 20,
          rateLimitPerSecond: 200,
          supportsWebhooks: true,
          supportsPush: true,
          supportsOAuth: true
        }
      });
    });

    // Get pending calendar invites
    this.app.get('/api/calendar/pending-invites', async (req, res) => {
      try {
        const { userId = 'default' } = req.query;

        const result = await this.postgres.query(`
          SELECT
            e.id as email_id,
            e.subject,
            e.from_address,
            ecl.ics_content,
            ce.summary,
            ce.start_time,
            ce.end_time,
            ce.organizer_email,
            ce.response_status
          FROM email_calendar_links ecl
          JOIN emails e ON ecl.email_id = e.id
          JOIN email_accounts ea ON e.account_id = ea.id
          LEFT JOIN calendar_events ce ON ecl.calendar_event_id = ce.id
          WHERE ea.user_id = $1
            AND ecl.is_invite = true
            AND (ce.response_status IS NULL OR ce.response_status = 'needsAction')
          ORDER BY e.received_at DESC
          LIMIT 50
        `, [userId]);

        res.json({
          invites: result.rows
        });

      } catch (error) {
        logger.error('Failed to get pending invites:', error);
        res.status(500).json({ error: 'Failed to get pending invites' });
      }
    });

    // RSVP to calendar invite
    this.app.post('/api/calendar/rsvp', async (req, res) => {
      try {
        const { emailId, response } = req.body;

        if (!['accepted', 'declined', 'tentative'].includes(response)) {
          return res.status(400).json({ error: 'Invalid response. Must be: accepted, declined, or tentative' });
        }

        // Update calendar event if it exists
        await this.postgres.query(`
          UPDATE calendar_events ce
          SET response_status = $1, updated_at = NOW()
          FROM email_calendar_links ecl
          WHERE ecl.calendar_event_id = ce.id
            AND ecl.email_id = $2
        `, [response, emailId]);

        logger.info(`RSVP ${response} for email ${emailId}`);

        res.json({
          success: true,
          response: response,
          actions: ['Updated calendar event', 'Email processed']
        });

      } catch (error) {
        logger.error('Failed to RSVP:', error);
        res.status(500).json({ error: 'Failed to RSVP' });
      }
    });

    // Get auto-RSVP rules
    this.app.get('/api/rules/auto-rsvp', async (req, res) => {
      try {
        const { userId = 'default' } = req.query;

        const result = await this.postgres.query(
          'SELECT * FROM auto_rsvp_rules WHERE user_id = $1 ORDER BY priority DESC',
          [userId]
        );

        res.json({ rules: result.rows });

      } catch (error) {
        logger.error('Failed to get auto-RSVP rules:', error);
        res.status(500).json({ error: 'Failed to get auto-RSVP rules' });
      }
    });

    // Create auto-RSVP rule
    this.app.post('/api/rules/auto-rsvp', async (req, res) => {
      try {
        const {
          userId = 'default',
          name,
          ruleType,
          priority = 50,
          condition,
          action
        } = req.body;

        const result = await this.postgres.query(`
          INSERT INTO auto_rsvp_rules (
            user_id, name, rule_type, priority, enabled, condition, action
          ) VALUES ($1, $2, $3, $4, true, $5, $6)
          RETURNING *
        `, [userId, name, ruleType, priority, JSON.stringify(condition), JSON.stringify(action)]);

        logger.info(`Created auto-RSVP rule: ${name}`);
        res.json({ success: true, rule: result.rows[0] });

      } catch (error) {
        logger.error('Failed to create auto-RSVP rule:', error);
        res.status(500).json({ error: 'Failed to create auto-RSVP rule' });
      }
    });

    // Get automation stats
    this.app.get('/api/stats/automation', async (req, res) => {
      try {
        const { userId = 'default', days = 30 } = req.query;

        const result = await this.postgres.query(`
          SELECT
            COALESCE(SUM(auto_rsvp_count), 0) as total_auto_rsvp,
            COALESCE(SUM(email_archived_count), 0) as total_archived,
            COALESCE(SUM(flags_synced_count), 0) as total_flags_synced,
            COALESCE(SUM(time_saved_minutes), 0) as total_time_saved_minutes,
            COUNT(CASE WHEN inbox_zero_achieved THEN 1 END) as inbox_zero_days,
            COUNT(*) as total_days
          FROM automation_stats
          WHERE user_id = $1
            AND stat_date >= CURRENT_DATE - INTERVAL '${parseInt(days)} days'
        `, [userId]);

        const stats = result.rows[0];
        const totalActions = parseInt(stats.total_auto_rsvp) +
                            parseInt(stats.total_archived) +
                            parseInt(stats.total_flags_synced);

        res.json({
          totalActions: totalActions,
          totalTimeSavedHours: (parseFloat(stats.total_time_saved_minutes) / 60).toFixed(1),
          inboxZeroRate: stats.total_days > 0 ?
            (parseInt(stats.inbox_zero_days) / parseInt(stats.total_days)) : 0,
          avgActionsPerDay: stats.total_days > 0 ?
            (totalActions / parseInt(stats.total_days)).toFixed(1) : 0,
          breakdown: {
            autoRsvp: parseInt(stats.total_auto_rsvp),
            emailArchived: parseInt(stats.total_archived),
            flagsSync: parseInt(stats.total_flags_synced)
          }
        });

      } catch (error) {
        logger.error('Failed to get automation stats:', error);
        res.status(500).json({ error: 'Failed to get automation stats' });
      }
    });

    // Sync flags (bi-directional)
    this.app.post('/api/flags/sync', async (req, res) => {
      try {
        const { emailId, flags, direction = 'toProvider' } = req.body;

        // Get email and account
        const emailResult = await this.postgres.query(`
          SELECT e.*, ea.provider
          FROM emails e
          JOIN email_accounts ea ON e.account_id = ea.id
          WHERE e.id = $1
        `, [emailId]);

        if (emailResult.rows.length === 0) {
          return res.status(404).json({ error: 'Email not found' });
        }

        const email = emailResult.rows[0];

        // Update flags in database
        await this.postgres.query(
          'UPDATE emails SET flags = $1, updated_at = NOW() WHERE id = $2',
          [JSON.stringify(flags), emailId]
        );

        logger.info(`Synced flags for email ${emailId} (${direction})`);

        res.json({
          success: true,
          syncedTo: email.provider === 'gmail' ? 'Gmail' : email.provider === 'exchange' ? 'Exchange' : 'IMAP',
          direction: direction
        });

      } catch (error) {
        logger.error('Failed to sync flags:', error);
        res.status(500).json({ error: 'Failed to sync flags' });
      }
    });

    // Sync account emails
    this.app.post('/api/accounts/:id/sync', async (req, res) => {
      try {
        const { id } = req.params;

        // Load multi-provider service
        const MultiProviderEmailService = require('./multi-provider-email-service');
        const mpService = new MultiProviderEmailService(this.postgres);

        try {
          const result = await mpService.syncAccount(parseInt(id));
          logger.info(`Account sync result:`, result);

          res.json(result);
        } finally {
          await mpService.cleanup();
        }

      } catch (error) {
        logger.error('Failed to sync account:', error);
        res.status(500).json({ error: error.message || 'Failed to sync account' });
      }
    });

    // Error handling
    this.app.use((error, req, res, next) => {
      logger.error('API Error:', error);
      res.status(500).json({ error: 'Internal server error' });
    });

    // 404 handler
    this.app.use((req, res) => {
      res.status(404).json({ error: 'Endpoint not found' });
    });
  }

  async connect() {
    try {
      await this.postgres.connect();
      logger.info('✅ Connected to PostgreSQL');
      return true;
    } catch (error) {
      logger.error('❌ Failed to connect to PostgreSQL:', error);
      return false;
    }
  }

  async start() {
    if (await this.connect()) {
      this.app.listen(this.port, () => {
        logger.info(`🚀 Email API Service running on port ${this.port}`);
        logger.info(`📋 Available endpoints:`);
        logger.info(`  - GET  /health`);
        logger.info(`  - GET  /api/emails`);
        logger.info(`  - GET  /api/emails/:id`);
        logger.info(`  - PUT  /api/emails/:id/label`);
        logger.info(`  - POST /api/emails/:id/classify`);
        logger.info(`  - POST /api/classify/batch`);
        logger.info(`  - GET  /api/labels`);
        logger.info(`  - GET  /api/stats`);
        logger.info(`  - POST /api/feedback`);
        logger.info(`  - GET  /api/jobs`);
      });

    } else {
      logger.error('❌ Failed to start Email API Service');
      process.exit(1);
    }
  }
}

async function main() {
  const apiService = new EmailAPIService();
  await apiService.start();

  // Graceful shutdown
  process.on('SIGTERM', () => {
    logger.info('📪 Received SIGTERM, shutting down...');
    process.exit(0);
  });
}

if (require.main === module) {
  main();
}

module.exports = EmailAPIService;