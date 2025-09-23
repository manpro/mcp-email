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

// Simple IMAP connection function
function connectImap(config) {
  return new Promise((resolve, reject) => {
    const imap = new Imap({
      user: config.email,
      password: config.password,
      host: config.host,
      port: config.port || 993,
      tls: true,
      tlsOptions: { rejectUnauthorized: false },
      connTimeout: 10000,
      authTimeout: 10000
    });

    imap.once('ready', () => {
      console.log('IMAP connection ready');
      resolve(imap);
    });

    imap.once('error', (err) => {
      console.error('IMAP error:', err);
      reject(err);
    });

    imap.connect();
  });
}

// Connect endpoint
app.post('/connect', async (req, res) => {
  try {
    const { userId, email, password, provider } = req.body;

    // Determine IMAP host
    let host = 'imap.one.com';
    if (provider === 'gmail') {
      host = 'imap.gmail.com';
    } else if (provider === 'outlook') {
      host = 'outlook.office365.com';
    }

    console.log(`Connecting to ${host} for ${email}`);

    const imap = await connectImap({
      email,
      password,
      host,
      port: 993
    });

    // Store connection
    connections.set(userId || email, imap);

    res.json({ success: true, message: 'Connected successfully' });
  } catch (error) {
    console.error('Connection error:', error);
    res.status(500).json({ error: error.message });
  }
});

// Get mailboxes
app.get('/mailboxes/:userId', async (req, res) => {
  try {
    const imap = connections.get(req.params.userId);

    if (!imap) {
      return res.status(404).json({ error: 'No active connection' });
    }

    imap.getBoxes((err, boxes) => {
      if (err) {
        console.error('Error getting boxes:', err);
        return res.status(500).json({ error: err.message });
      }

      // Convert boxes to array
      const mailboxes = [];
      function parseBoxes(obj, parent = '') {
        for (const [name, box] of Object.entries(obj)) {
          const path = parent ? `${parent}${box.delimiter}${name}` : name;
          mailboxes.push({
            name,
            path,
            delimiter: box.delimiter,
            children: box.children ? Object.keys(box.children) : [],
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
  } catch (error) {
    console.error('Mailboxes error:', error);
    res.status(500).json({ error: error.message });
  }
});

// Get emails
app.get('/emails/:userId', async (req, res) => {
  try {
    const imap = connections.get(req.params.userId);
    const { mailbox = 'INBOX', limit = 20 } = req.query;

    if (!imap) {
      return res.status(404).json({ error: 'No active connection' });
    }

    console.log(`Fetching emails from ${mailbox}, limit: ${limit}`);

    imap.openBox(mailbox, false, (err, box) => {
      if (err) {
        console.error('Error opening box:', err);
        return res.status(500).json({ error: err.message });
      }

      const emails = [];
      const totalMessages = box.messages.total;

      if (totalMessages === 0) {
        return res.json({ emails: [], total: 0, unread: 0 });
      }

      // Calculate range for latest emails
      const fetchLimit = Math.min(parseInt(limit), totalMessages);
      const start = Math.max(1, totalMessages - fetchLimit + 1);
      const range = `${start}:*`;

      console.log(`Fetching range ${range} from total ${totalMessages} messages`);

      const fetch = imap.seq.fetch(range, {
        bodies: '',
        struct: true,
        envelope: true
      });

      fetch.on('message', (msg, seqno) => {
        let emailData = { seqno, uid: null };

        msg.on('body', (stream, info) => {
          simpleParser(stream, (err, parsed) => {
            if (!err && parsed) {
              emailData = {
                ...emailData,
                from: parsed.from?.text || '',
                to: parsed.to?.text || '',
                subject: parsed.subject || '(no subject)',
                date: parsed.date || new Date(),
                text: parsed.text || '',
                html: parsed.html || '',
                attachments: parsed.attachments?.map(att => ({
                  filename: att.filename,
                  size: att.size,
                  contentType: att.contentType
                })) || []
              };
            }
          });
        });

        msg.on('attributes', (attrs) => {
          emailData.uid = attrs.uid;
          emailData.flags = attrs.flags || [];
          emailData.date = attrs.date;
          emailData.size = attrs.size;
        });

        msg.once('end', () => {
          // Use envelope data if body parsing failed
          if (!emailData.subject && msg.envelope) {
            emailData.subject = msg.envelope.subject || '(no subject)';
            emailData.from = msg.envelope.from?.[0]?.address || '';
            emailData.date = msg.envelope.date || new Date();
          }
          emails.push(emailData);
        });
      });

      fetch.once('error', (err) => {
        console.error('Fetch error:', err);
        res.status(500).json({ error: err.message });
      });

      fetch.once('end', () => {
        console.log(`Fetched ${emails.length} emails`);

        // Sort by date descending
        emails.sort((a, b) => new Date(b.date) - new Date(a.date));

        res.json({
          emails,
          total: totalMessages,
          unread: box.messages.new || 0
        });
      });
    });
  } catch (error) {
    console.error('Emails error:', error);
    res.status(500).json({ error: error.message });
  }
});

// Disconnect
app.post('/disconnect/:userId', (req, res) => {
  const imap = connections.get(req.params.userId);

  if (imap) {
    imap.end();
    connections.delete(req.params.userId);
    res.json({ success: true, message: 'Disconnected' });
  } else {
    res.status(404).json({ error: 'No active connection' });
  }
});

// Health check
app.get('/health', (req, res) => {
  res.json({ status: 'ok', connections: connections.size });
});

app.listen(PORT, () => {
  console.log(`Simple Email Service running on port ${PORT}`);
});