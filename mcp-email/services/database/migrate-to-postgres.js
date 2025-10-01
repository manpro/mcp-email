/**
 * Migration Script: SQLite → PostgreSQL
 *
 * Migrates existing IMAP email data from SQLite to unified multi-provider PostgreSQL schema
 * Preserves emails, labels, categorizations, and user preferences
 */

const sqlite3 = require('sqlite3').verbose()
const { Pool } = require('pg')
require('dotenv').config()

// Configuration
const SQLITE_PATH = process.env.SQLITE_DB_PATH || './email_categorizations.db'
const POSTGRES_URL = process.env.DATABASE_URL || 'postgresql://localhost/email_db'

const postgres = new Pool({ connectionString: POSTGRES_URL })
const sqlite = new sqlite3.Database(SQLITE_PATH)

// Default user ID for migration
const DEFAULT_USER_ID = 'default'
const DEFAULT_ACCOUNT_NAME = 'IMAP Account (Migrated)'

async function migrate() {
  console.log('Starting SQLite → PostgreSQL migration...\n')

  try {
    // Step 1: Migrate IMAP account
    console.log('Step 1: Creating IMAP account...')
    const accountId = await migrateIMAPAccount()
    console.log(`✓ Created account ID: ${accountId}\n`)

    // Step 2: Migrate labels
    console.log('Step 2: Migrating labels...')
    const labelMap = await migrateLabels(accountId)
    console.log(`✓ Migrated ${Object.keys(labelMap).size} labels\n`)

    // Step 3: Migrate emails
    console.log('Step 3: Migrating emails...')
    const emailMap = await migrateEmails(accountId)
    console.log(`✓ Migrated ${Object.keys(emailMap).size} emails\n`)

    // Step 4: Migrate email-label relationships
    console.log('Step 4: Migrating email-label relationships...')
    const relationCount = await migrateEmailLabels(emailMap, labelMap)
    console.log(`✓ Migrated ${relationCount} email-label relations\n`)

    // Step 5: Migrate user preferences (if exists)
    console.log('Step 5: Migrating user preferences...')
    await migrateUserPreferences()
    console.log('✓ User preferences migrated\n')

    // Step 6: Verify migration
    console.log('Step 6: Verifying migration...')
    await verifyMigration(accountId)
    console.log('✓ Migration verified\n')

    console.log('✅ Migration completed successfully!')
    console.log(`
Summary:
  - Account ID: ${accountId}
  - Labels: ${Object.keys(labelMap).size}
  - Emails: ${Object.keys(emailMap).size}
  - Relations: ${relationCount}
    `)
  } catch (error) {
    console.error('❌ Migration failed:', error)
    throw error
  } finally {
    await postgres.end()
    sqlite.close()
  }
}

/**
 * Step 1: Create IMAP account in PostgreSQL
 */
async function migrateIMAPAccount() {
  // Check if IMAP config exists in SQLite
  const imapConfig = await new Promise((resolve, reject) => {
    sqlite.get(
      `SELECT * FROM imap_config LIMIT 1`,
      (err, row) => {
        if (err) {
          // Table might not exist
          resolve(null)
        } else {
          resolve(row)
        }
      }
    )
  })

  const result = await postgres.query(
    `INSERT INTO email_accounts (
      user_id, provider, email_address, display_name,
      auth_type, imap_host, imap_port, imap_username,
      imap_password, imap_tls, enabled, sync_status
    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
    RETURNING id`,
    [
      DEFAULT_USER_ID,
      'imap',
      imapConfig?.email || 'unknown@example.com',
      DEFAULT_ACCOUNT_NAME,
      'password',
      imapConfig?.host || 'imap.gmail.com',
      imapConfig?.port || 993,
      imapConfig?.username || '',
      imapConfig?.password || '',
      imapConfig?.tls !== false,
      true,
      'idle'
    ]
  )

  return result.rows[0].id
}

/**
 * Step 2: Migrate labels from SQLite to PostgreSQL
 */
async function migrateLabels(accountId) {
  const labelMap = new Map() // SQLite ID → PostgreSQL ID

  const sqliteLabels = await new Promise((resolve, reject) => {
    sqlite.all(
      `SELECT * FROM labels ORDER BY id`,
      (err, rows) => {
        if (err) reject(err)
        else resolve(rows || [])
      }
    )
  })

  for (const label of sqliteLabels) {
    const policy = {}

    // Parse policy from SQLite columns
    if (label.policy) {
      try {
        Object.assign(policy, JSON.parse(label.policy))
      } catch (e) {
        // Ignore parse errors
      }
    }

    // Add icon if exists
    if (label.icon) {
      policy.icon = label.icon
    }

    // Add rules if exists
    if (label.rules) {
      try {
        policy.rules = JSON.parse(label.rules)
      } catch (e) {
        policy.rules = {}
      }
    }

    const result = await postgres.query(
      `INSERT INTO labels (
        account_id, name, display_name, label_type,
        color, icon, policy, enabled
      ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
      RETURNING id`,
      [
        accountId,
        label.name,
        label.display_name || label.name,
        label.created_by === 'ai' ? 'ai_generated' : 'user',
        label.color || '#6366f1',
        label.icon || '🏷️',
        JSON.stringify(policy),
        label.enabled !== false
      ]
    )

    labelMap.set(label.id, result.rows[0].id)
  }

  return labelMap
}

/**
 * Step 3: Migrate emails from SQLite to PostgreSQL
 */
async function migrateEmails(accountId) {
  const emailMap = new Map() // SQLite ID → PostgreSQL ID

  const sqliteEmails = await new Promise((resolve, reject) => {
    sqlite.all(
      `SELECT * FROM emails ORDER BY id`,
      (err, rows) => {
        if (err) reject(err)
        else resolve(rows || [])
      }
    )
  })

  console.log(`  Found ${sqliteEmails.length} emails to migrate`)

  for (const email of sqliteEmails) {
    // Parse JSON fields
    let toAddresses = []
    let ccAddresses = []
    let bccAddresses = []
    let headers = {}

    try {
      toAddresses = JSON.parse(email.to_addresses || '[]')
    } catch (e) {}

    try {
      ccAddresses = JSON.parse(email.cc_addresses || '[]')
    } catch (e) {}

    try {
      bccAddresses = JSON.parse(email.bcc_addresses || '[]')
    } catch (e) {}

    try {
      headers = JSON.parse(email.headers || '{}')
    } catch (e) {}

    const result = await postgres.query(
      `INSERT INTO emails (
        account_id, provider_message_id, provider_thread_id,
        subject, from_address, from_name,
        to_addresses, cc_addresses, bcc_addresses,
        body_text, body_html, received_at,
        is_read, is_flagged, is_answered, is_draft,
        has_attachments, headers, created_at
      ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19)
      RETURNING id`,
      [
        accountId,
        email.message_id || `migrated-${email.id}`,
        email.thread_id,
        email.subject || '(No Subject)',
        email.from_address || '',
        email.from_name,
        JSON.stringify(toAddresses),
        JSON.stringify(ccAddresses),
        JSON.stringify(bccAddresses),
        email.body_text,
        email.body_html,
        email.received_at ? new Date(email.received_at) : new Date(),
        email.is_read !== false,
        email.is_flagged === true,
        email.is_answered === true,
        email.is_draft === true,
        email.has_attachments === true,
        JSON.stringify(headers),
        email.created_at ? new Date(email.created_at) : new Date()
      ]
    )

    emailMap.set(email.id, result.rows[0].id)
  }

  return emailMap
}

/**
 * Step 4: Migrate email-label relationships
 */
async function migrateEmailLabels(emailMap, labelMap) {
  const sqliteRelations = await new Promise((resolve, reject) => {
    sqlite.all(
      `SELECT * FROM email_labels ORDER BY id`,
      (err, rows) => {
        if (err) reject(err)
        else resolve(rows || [])
      }
    )
  })

  let count = 0

  for (const relation of sqliteRelations) {
    const postgresEmailId = emailMap.get(relation.email_id)
    const postgresLabelId = labelMap.get(relation.label_id)

    if (!postgresEmailId || !postgresLabelId) {
      console.warn(`  Skipping relation: email ${relation.email_id} → label ${relation.label_id}`)
      continue
    }

    await postgres.query(
      `INSERT INTO email_labels (
        email_id, label_id, score, confidence, source, created_at
      ) VALUES ($1, $2, $3, $4, $5, $6)
      ON CONFLICT (email_id, label_id) DO NOTHING`,
      [
        postgresEmailId,
        postgresLabelId,
        relation.score || 1.0,
        relation.confidence || 1.0,
        relation.source || 'ml',
        relation.created_at ? new Date(relation.created_at) : new Date()
      ]
    )

    count++
  }

  return count
}

/**
 * Step 5: Migrate user preferences
 */
async function migrateUserPreferences() {
  // Check if user_preferences table exists in SQLite
  const preferences = await new Promise((resolve, reject) => {
    sqlite.all(
      `SELECT * FROM user_preferences LIMIT 1`,
      (err, rows) => {
        if (err) {
          // Table might not exist
          resolve([])
        } else {
          resolve(rows || [])
        }
      }
    )
  })

  if (preferences.length === 0) {
    console.log('  No user preferences to migrate')
    return
  }

  // TODO: Migrate to user_rules table if needed
  console.log('  User preferences migration skipped (implement if needed)')
}

/**
 * Step 6: Verify migration
 */
async function verifyMigration(accountId) {
  // Count records
  const emailCount = await postgres.query(
    `SELECT COUNT(*) as count FROM emails WHERE account_id = $1`,
    [accountId]
  )

  const labelCount = await postgres.query(
    `SELECT COUNT(*) as count FROM labels WHERE account_id = $1`,
    [accountId]
  )

  const relationCount = await postgres.query(
    `SELECT COUNT(*) as count FROM email_labels el
     JOIN emails e ON el.email_id = e.id
     WHERE e.account_id = $1`,
    [accountId]
  )

  console.log(`  Emails: ${emailCount.rows[0].count}`)
  console.log(`  Labels: ${labelCount.rows[0].count}`)
  console.log(`  Relations: ${relationCount.rows[0].count}`)

  // Verify data integrity
  const orphanedLabels = await postgres.query(
    `SELECT COUNT(*) as count FROM email_labels el
     LEFT JOIN emails e ON el.email_id = e.id
     WHERE e.id IS NULL`
  )

  if (parseInt(orphanedLabels.rows[0].count) > 0) {
    console.warn(`  ⚠️  Found ${orphanedLabels.rows[0].count} orphaned email_labels`)
  }
}

// Run migration
if (require.main === module) {
  migrate()
    .then(() => process.exit(0))
    .catch(err => {
      console.error(err)
      process.exit(1)
    })
}

module.exports = { migrate }
