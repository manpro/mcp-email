const express = require('express');
const cors = require('cors');
const Imap = require('imap');
const { simpleParser } = require('mailparser');
const EventEmitter = require('events');

const app = express();
const PORT = process.env.PORT || 3002;

app.use(cors());
app.use(express.json());

// Connection pool for IMAP connections
class ImapConnectionPool extends EventEmitter {
  constructor() {
    super();
    this.connections = new Map();
  }

  async getConnection(userId, config) {
    if (this.connections.has(userId)) {
      return this.connections.get(userId);
    }

    const connection = new ImapConnection(config);
    await connection.connect();
    this.connections.set(userId, connection);
    return connection;
  }

  async closeConnection(userId) {
    if (this.connections.has(userId)) {
      const conn = this.connections.get(userId);
      await conn.disconnect();
      this.connections.delete(userId);
    }
  }
}

class ImapConnection {
  constructor(config) {
    this.config = config;
    this.imap = null;
    this.connected = false;
  }

  connect() {
    return new Promise((resolve, reject) => {
      this.imap = new Imap({
        user: this.config.email,
        password: this.config.password,
        host: this.config.host || 'imap.gmail.com',
        port: this.config.port || 993,
        tls: true,
        tlsOptions: { rejectUnauthorized: false },
        connTimeout: 10000, // 10 second connection timeout
        authTimeout: 10000  // 10 second auth timeout
      });

      this.imap.once('ready', () => {
        this.connected = true;
        resolve();
      });

      this.imap.once('error', (err) => {
        this.connected = false;
        reject(err);
      });

      this.imap.connect();
    });
  }

  disconnect() {
    return new Promise((resolve) => {
      if (this.imap && this.connected) {
        this.imap.once('end', resolve);
        this.imap.end();
      } else {
        resolve();
      }
    });
  }

  getMailboxes() {
    return new Promise((resolve, reject) => {
      this.imap.getBoxes((err, boxes) => {
        if (err) reject(err);
        else resolve(this.parseBoxes(boxes));
      });
    });
  }

  parseBoxes(boxes, parent = '') {
    const result = [];
    for (const [name, box] of Object.entries(boxes)) {
      const fullPath = parent ? `${parent}${box.delimiter}${name}` : name;
      result.push({
        name,
        path: fullPath,
        delimiter: box.delimiter,
        hasChildren: box.children != null
      });
      if (box.children) {
        result.push(...this.parseBoxes(box.children, fullPath));
      }
    }
    return result;
  }

  async fetchEmails(mailbox = 'INBOX', limit = 50) {
    return new Promise((resolve, reject) => {
      this.imap.openBox(mailbox, false, (err, box) => {
        if (err) return reject(err);

        const fetchRange = Math.max(1, box.messages.total - limit + 1) + ':*';
        const emails = [];

        const fetch = this.imap.seq.fetch(fetchRange, {
          bodies: '',
          struct: true,
          envelope: true
        });

        fetch.on('message', (msg) => {
          const email = { headers: {}, body: '' };

          msg.on('body', (stream) => {
            let buffer = '';
            stream.on('data', (chunk) => buffer += chunk);
            stream.on('end', () => {
              simpleParser(buffer).then((parsed) => {
                email.subject = parsed.subject;
                email.from = parsed.from?.text;
                email.to = parsed.to?.text;
                email.date = parsed.date;
                email.text = parsed.text;
                email.html = parsed.html;
                email.attachments = parsed.attachments?.map(a => ({
                  filename: a.filename,
                  size: a.size,
                  contentType: a.contentType
                }));
              }).catch(console.error);
            });
          });

          msg.on('attributes', (attrs) => {
            email.uid = attrs.uid;
            email.flags = attrs.flags;
          });

          msg.on('end', () => {
            emails.push(email);
          });
        });

        fetch.once('end', () => resolve(emails));
        fetch.once('error', reject);
      });
    });
  }

  searchEmails(criteria, mailbox = 'INBOX') {
    return new Promise((resolve, reject) => {
      this.imap.openBox(mailbox, false, (err) => {
        if (err) return reject(err);

        this.imap.search(criteria, (err, results) => {
          if (err) reject(err);
          else resolve(results);
        });
      });
    });
  }

  moveEmail(uid, targetMailbox, sourceMailbox = 'INBOX') {
    return new Promise((resolve, reject) => {
      this.imap.openBox(sourceMailbox, false, (err) => {
        if (err) return reject(err);

        this.imap.move(uid, targetMailbox, (err) => {
          if (err) reject(err);
          else resolve({ success: true });
        });
      });
    });
  }

  markAsRead(uid, mailbox = 'INBOX') {
    return new Promise((resolve, reject) => {
      this.imap.openBox(mailbox, false, (err) => {
        if (err) return reject(err);

        this.imap.addFlags(uid, '\\Seen', (err) => {
          if (err) reject(err);
          else resolve({ success: true });
        });
      });
    });
  }

  deleteEmail(uid, mailbox = 'INBOX') {
    return new Promise((resolve, reject) => {
      this.imap.openBox(mailbox, false, (err) => {
        if (err) return reject(err);

        this.imap.addFlags(uid, '\\Deleted', (err) => {
          if (err) return reject(err);

          this.imap.expunge((err) => {
            if (err) reject(err);
            else resolve({ success: true });
          });
        });
      });
    });
  }
}

const connectionPool = new ImapConnectionPool();

// Health check
app.get('/health', (req, res) => {
  res.json({ status: 'healthy', service: 'email-service' });
});

// Real IMAP-based endpoints that require authentication
app.get('/api/mailboxes', async (req, res) => {
  try {
    const { userId } = req.query;
    if (!userId) {
      return res.status(400).json({
        error: 'userId required. Please connect to email account first.'
      });
    }

    const connection = connectionPool.connections.get(userId);
    if (!connection) {
      return res.status(404).json({
        error: 'No active connection. Please connect to email account first.',
        requiresAuth: true
      });
    }

    const mailboxes = await connection.getMailboxes();
    // Transform IMAP mailboxes to frontend format
    const formattedMailboxes = mailboxes.map((box, index) => ({
      id: index + 1,
      name: box.name,
      path: box.path,
      count: 0, // Will be updated when opened
      unread: 0 // Will be updated when opened
    }));

    res.json({ mailboxes: formattedMailboxes });
  } catch (error) {
    console.error('Mailboxes error:', error);
    res.status(500).json({
      error: 'Failed to fetch mailboxes. Please check your connection.',
      requiresAuth: true
    });
  }
});

app.get('/api/recent-emails', async (req, res) => {
  try {
    const { userId, mailbox = 'INBOX', limit = 20 } = req.query;
    if (!userId) {
      return res.status(400).json({
        error: 'userId required. Please connect to email account first.'
      });
    }

    const connection = connectionPool.connections.get(userId);
    if (!connection) {
      return res.status(404).json({
        error: 'No active connection. Please connect to email account first.',
        requiresAuth: true
      });
    }

    const emails = await connection.fetchEmails(mailbox, parseInt(limit));
    // Transform IMAP emails to frontend format
    const formattedEmails = emails.map((email, index) => ({
      id: email.uid || index + 1,
      subject: email.subject || 'No Subject',
      from: email.from || 'Unknown Sender',
      date: email.date ? new Date(email.date).toISOString() : new Date().toISOString(),
      preview: (email.text || email.html || '').slice(0, 150) + '...',
      read: !email.flags?.includes('\\Seen'),
      text: email.text,
      html: email.html,
      flags: email.flags || [],
      uid: email.uid
    }));

    res.json({ emails: formattedEmails });
  } catch (error) {
    console.error('Recent emails error:', error);
    res.status(500).json({
      error: 'Failed to fetch emails. Please check your connection.',
      requiresAuth: true
    });
  }
});

// Connect to email account
app.post('/connect', async (req, res) => {
  try {
    const { userId, email, password, provider } = req.body;

    // Map provider to correct IMAP host
    let host;
    if (provider === 'gmail') {
      host = 'imap.gmail.com';
    } else if (provider === 'outlook') {
      host = 'outlook.office365.com';
    } else if (provider === 'oneCom') {
      host = 'imap.one.com';
    } else if (provider === 'auto') {
      // Try to detect from email domain
      const domain = email.split('@')[1];
      if (domain.includes('gmail')) {
        host = 'imap.gmail.com';
      } else if (domain.includes('outlook') || domain.includes('hotmail') || domain.includes('live')) {
        host = 'outlook.office365.com';
      } else if (domain.includes('one.com')) {
        host = 'imap.one.com';
      } else if (domain === 'fallstrom.org') {
        // Special handling for fallstrom.org - hosted on One.com
        host = 'imap.one.com';
      } else {
        // Generic IMAP host
        host = `imap.${domain}`;
      }
    } else {
      host = req.body.host || provider;
    }

    const config = {
      email,
      password,
      host,
      port: req.body.port || 993
    };

    console.log(`Attempting to connect to ${host} for ${email}`);
    console.log('Port:', config.port);
    console.log('Starting connection attempt...');

    // Set a timeout for the entire connection attempt
    const timeoutPromise = new Promise((_, reject) => {
      setTimeout(() => reject(new Error('Connection timeout after 10 seconds')), 10000);
    });

    const connectionPromise = connectionPool.getConnection(userId, config);

    await Promise.race([connectionPromise, timeoutPromise]);

    console.log('Connection successful!');

    res.json({
      success: true,
      message: 'Connected successfully'
    });
  } catch (error) {
    console.error('Connection error:', error);
    console.error('Error stack:', error.stack);

    // Provide more helpful error messages
    let errorMessage = error.message;
    if (error.message.includes('timeout')) {
      errorMessage = 'Connection timeout. Please check your email settings and try again.';
    } else if (error.message.includes('AUTHENTICATIONFAILED')) {
      errorMessage = 'Authentication failed. Please check your email and password.';
    } else if (error.message.includes('ENOTFOUND')) {
      errorMessage = 'Could not find email server. Please check the server address.';
    }

    res.status(500).json({
      success: false,
      error: errorMessage,
      details: error.message
    });
  }
});

// Get mailboxes
app.get('/mailboxes/:userId', async (req, res) => {
  try {
    const connection = connectionPool.connections.get(req.params.userId);
    if (!connection) {
      return res.status(404).json({ error: 'No active connection' });
    }

    const mailboxes = await connection.getMailboxes();
    res.json({ mailboxes });
  } catch (error) {
    console.error('Mailbox error:', error);
    res.status(500).json({ error: error.message });
  }
});

// Fetch emails
app.get('/emails/:userId', async (req, res) => {
  try {
    const connection = connectionPool.connections.get(req.params.userId);
    if (!connection) {
      return res.status(404).json({ error: 'No active connection' });
    }

    const { mailbox = 'INBOX', limit = 50 } = req.query;
    const emails = await connection.fetchEmails(mailbox, parseInt(limit));
    res.json({ emails });
  } catch (error) {
    console.error('Fetch error:', error);
    res.status(500).json({ error: error.message });
  }
});

// Search emails
app.post('/search/:userId', async (req, res) => {
  try {
    const connection = connectionPool.connections.get(req.params.userId);
    if (!connection) {
      return res.status(404).json({ error: 'No active connection' });
    }

    const { criteria, mailbox = 'INBOX' } = req.body;
    const results = await connection.searchEmails(criteria, mailbox);
    res.json({ results });
  } catch (error) {
    console.error('Search error:', error);
    res.status(500).json({ error: error.message });
  }
});

// Move email
app.post('/move/:userId', async (req, res) => {
  try {
    const connection = connectionPool.connections.get(req.params.userId);
    if (!connection) {
      return res.status(404).json({ error: 'No active connection' });
    }

    const { uid, targetMailbox, sourceMailbox } = req.body;
    const result = await connection.moveEmail(uid, targetMailbox, sourceMailbox);
    res.json(result);
  } catch (error) {
    console.error('Move error:', error);
    res.status(500).json({ error: error.message });
  }
});

// Mark as read
app.post('/mark-read/:userId', async (req, res) => {
  try {
    const connection = connectionPool.connections.get(req.params.userId);
    if (!connection) {
      return res.status(404).json({ error: 'No active connection' });
    }

    const { uid, mailbox } = req.body;
    const result = await connection.markAsRead(uid, mailbox);
    res.json(result);
  } catch (error) {
    console.error('Mark read error:', error);
    res.status(500).json({ error: error.message });
  }
});

// Delete email
app.delete('/email/:userId/:uid', async (req, res) => {
  try {
    const connection = connectionPool.connections.get(req.params.userId);
    if (!connection) {
      return res.status(404).json({ error: 'No active connection' });
    }

    const { mailbox = 'INBOX' } = req.query;
    const result = await connection.deleteEmail(req.params.uid, mailbox);
    res.json(result);
  } catch (error) {
    console.error('Delete error:', error);
    res.status(500).json({ error: error.message });
  }
});

// Disconnect
app.post('/disconnect/:userId', async (req, res) => {
  try {
    await connectionPool.closeConnection(req.params.userId);
    res.json({ success: true, message: 'Disconnected successfully' });
  } catch (error) {
    console.error('Disconnect error:', error);
    res.status(500).json({ error: error.message });
  }
});

app.listen(PORT, () => {
  console.log(`Email Service running on port ${PORT}`);
  console.log('Endpoints:');
  console.log('  POST /connect');
  console.log('  GET /mailboxes/:userId');
  console.log('  GET /emails/:userId');
  console.log('  POST /search/:userId');
  console.log('  POST /move/:userId');
  console.log('  POST /mark-read/:userId');
  console.log('  DELETE /email/:userId/:uid');
  console.log('  POST /disconnect/:userId');
});