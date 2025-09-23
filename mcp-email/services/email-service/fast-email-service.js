const express = require('express');
const cors = require('cors');
const Imap = require('imap');
const { simpleParser } = require('mailparser');

const app = express();
const PORT = process.env.PORT || 3012;

app.use(cors());
app.use(express.json());

// Store active connections
const connections = new Map();

// Connect endpoint
app.post('/connect', async (req, res) => {
  try {
    const { userId, email, password, provider } = req.body;

    // Determine IMAP host
    let host = 'imap.one.com';
    if (provider === 'gmail') {
      host = 'imap.gmail.com';
    }

    console.log(`Connecting to ${host} for ${email}`);

    const imap = new Imap({
      user: email,
      password: password,
      host: host,
      port: 993,
      tls: true,
      tlsOptions: { rejectUnauthorized: false },
      connTimeout: 10000,
      authTimeout: 10000
    });

    const promise = new Promise((resolve, reject) => {
      imap.once('ready', () => {
        console.log('IMAP connection ready');
        connections.set(userId || email, imap);
        resolve();
      });

      imap.once('error', (err) => {
        console.error('IMAP error:', err);
        reject(err);
      });

      imap.connect();
    });

    await promise;
    res.json({ success: true, message: 'Connected successfully' });
  } catch (error) {
    console.error('Connection error:', error);
    res.status(500).json({ error: error.message });
  }
});

// Get emails - fast version with only headers
app.get('/emails/:userId', (req, res) => {
  const imap = connections.get(req.params.userId);
  const { mailbox = 'INBOX', limit = 20 } = req.query;

  if (!imap) {
    return res.status(404).json({ error: 'No active connection' });
  }

  console.log(`Opening ${mailbox}...`);

  imap.openBox(mailbox, true, (err, box) => {
    if (err) {
      console.error('Error opening box:', err);
      return res.status(500).json({ error: err.message });
    }

    console.log(`Box opened. Total messages: ${box.messages.total}`);

    if (box.messages.total === 0) {
      return res.json({ emails: [], total: 0, unread: 0 });
    }

    const emails = [];
    const fetchLimit = Math.min(parseInt(limit), box.messages.total);
    const start = Math.max(1, box.messages.total - fetchLimit + 1);

    console.log(`Fetching ${start}:* (last ${fetchLimit} messages)`);

    // Fetch only headers for speed
    const f = imap.seq.fetch(`${start}:*`, {
      bodies: 'HEADER.FIELDS (FROM TO SUBJECT DATE MESSAGE-ID)',
      struct: false
    });

    f.on('message', (msg, seqno) => {
      let emailData = {
        seqno,
        uid: null,
        flags: [],
        from: '',
        to: '',
        subject: '',
        date: new Date()
      };

      msg.on('body', (stream, info) => {
        let buffer = '';
        stream.on('data', chunk => {
          buffer += chunk.toString('utf8');
        });
        stream.once('end', () => {
          const header = Imap.parseHeader(buffer);
          emailData.from = header.from ? header.from[0] : '';
          emailData.to = header.to ? header.to[0] : '';
          emailData.subject = header.subject ? header.subject[0] : '(no subject)';
          emailData.date = header.date ? new Date(header.date[0]) : new Date();
          emailData.messageId = header['message-id'] ? header['message-id'][0] : '';
        });
      });

      msg.once('attributes', (attrs) => {
        emailData.uid = attrs.uid;
        emailData.flags = attrs.flags || [];
      });

      msg.once('end', () => {
        emails.push(emailData);
      });
    });

    f.once('error', (err) => {
      console.error('Fetch error:', err);
      res.status(500).json({ error: err.message });
    });

    f.once('end', () => {
      console.log(`Fetched ${emails.length} emails successfully`);

      // Sort by date descending
      emails.sort((a, b) => new Date(b.date) - new Date(a.date));

      res.json({
        emails,
        total: box.messages.total,
        unread: box.messages.new || 0
      });
    });
  });
});

// Get mailboxes
app.get('/mailboxes/:userId', (req, res) => {
  const imap = connections.get(req.params.userId);

  if (!imap) {
    return res.status(404).json({ error: 'No active connection' });
  }

  imap.getBoxes((err, boxes) => {
    if (err) {
      return res.status(500).json({ error: err.message });
    }

    const mailboxes = [];
    function parseBoxes(obj, parent = '') {
      for (const [name, box] of Object.entries(obj)) {
        const path = parent ? `${parent}${box.delimiter}${name}` : name;
        mailboxes.push({
          name,
          path,
          delimiter: box.delimiter,
          special: box.special_use_attrib || null
        });
        if (box.children) {
          parseBoxes(box.children, path);
        }
      }
    }
    parseBoxes(boxes);

    res.json(mailboxes);
  });
});

// Health check
app.get('/health', (req, res) => {
  res.json({ status: 'ok', connections: connections.size });
});

app.listen(PORT, () => {
  console.log(`Fast Email Service running on port ${PORT}`);
});