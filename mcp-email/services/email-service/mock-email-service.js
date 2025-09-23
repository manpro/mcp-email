const express = require('express');
const cors = require('cors');

const app = express();
const PORT = process.env.PORT || 3012;

app.use(cors());
app.use(express.json());

// Enhanced mock emails with proper categories
const mockEmails = [
  // Work & Business
  {
    seqno: 180,
    uid: 180,
    flags: [],
    from: 'Sarah Johnson <sarah.johnson@techcorp.com>',
    to: 'mikael@fallstrom.org',
    subject: 'Q4 Project Status Update - Action Required',
    date: new Date('2025-09-21T14:30:00.000Z'),
    messageId: '<msg180>',
    category: 'Work',
    priority: 'high',
    categorizationSource: 'ai'
  },
  {
    seqno: 179,
    uid: 179,
    flags: ['\\Seen'],
    from: 'Meeting Scheduler <noreply@calendly.com>',
    to: 'mikael@fallstrom.org',
    subject: 'Tomorrow: Tech Review Meeting at 2 PM',
    date: new Date('2025-09-21T13:15:00.000Z'),
    messageId: '<msg179>',
    category: 'Meetings',
    priority: 'high',
    categorizationSource: 'ai'
  },
  {
    seqno: 178,
    uid: 178,
    flags: [],
    from: 'LinkedIn <notifications@linkedin.com>',
    to: 'mikael@fallstrom.org',
    subject: 'You have 5 new profile views this week',
    date: new Date('2025-09-21T12:00:00.000Z'),
    messageId: '<msg178>',
    category: 'Social',
    priority: 'low',
    categorizationSource: 'ai'
  },

  // Financial
  {
    seqno: 177,
    uid: 177,
    flags: [],
    from: 'Swedbank <noreply@swedbank.se>',
    to: 'mikael@fallstrom.org',
    subject: 'Kontoutdrag för september 2025',
    date: new Date('2025-09-21T09:00:00.000Z'),
    messageId: '<msg177>',
    category: 'Financial',
    priority: 'medium',
    categorizationSource: 'ai'
  },
  {
    seqno: 176,
    uid: 176,
    flags: ['\\Seen'],
    from: 'PayPal <service@paypal.com>',
    to: 'mikael@fallstrom.org',
    subject: 'Payment received from Client ABC',
    date: new Date('2025-09-20T18:45:00.000Z'),
    messageId: '<msg176>',
    category: 'Financial',
    priority: 'medium',
    categorizationSource: 'ai'
  },
  {
    seqno: 175,
    uid: 175,
    flags: [],
    from: 'Klarna <noreply@klarna.com>',
    to: 'mikael@fallstrom.org',
    subject: 'Din faktura förfaller om 3 dagar',
    date: new Date('2025-09-20T16:00:00.000Z'),
    messageId: '<msg175>',
    category: 'Bills',
    priority: 'high',
    categorizationSource: 'ai'
  },

  // Development & Tech
  {
    seqno: 174,
    uid: 174,
    flags: [],
    from: 'GitHub <noreply@github.com>',
    to: 'mikael@fallstrom.org',
    subject: '[PR] Review requested: Update Docker configuration',
    date: new Date('2025-09-20T15:30:00.000Z'),
    messageId: '<msg174>',
    category: 'Development',
    priority: 'high',
    categorizationSource: 'ai'
  },
  {
    seqno: 173,
    uid: 173,
    flags: ['\\Seen'],
    from: 'Stack Overflow <do-not-reply@stackoverflow.email>',
    to: 'mikael@fallstrom.org',
    subject: 'Your answer was accepted',
    date: new Date('2025-09-20T14:20:00.000Z'),
    messageId: '<msg173>',
    category: 'Development',
    priority: 'low',
    categorizationSource: 'ai'
  },
  {
    seqno: 172,
    uid: 172,
    flags: [],
    from: 'Docker Hub <noreply@hub.docker.com>',
    to: 'mikael@fallstrom.org',
    subject: 'Security update available for your images',
    date: new Date('2025-09-20T13:00:00.000Z'),
    messageId: '<msg172>',
    category: 'Security',
    priority: 'high',
    categorizationSource: 'ai'
  },

  // Personal
  {
    seqno: 171,
    uid: 171,
    flags: [],
    from: 'Anna Andersson <anna.andersson@gmail.com>',
    to: 'mikael@fallstrom.org',
    subject: 'Middag på lördag?',
    date: new Date('2025-09-20T12:30:00.000Z'),
    messageId: '<msg171>',
    category: 'Personal',
    priority: 'medium',
    categorizationSource: 'ai'
  },
  {
    seqno: 170,
    uid: 170,
    flags: ['\\Seen'],
    from: 'Boappa <no-reply@boappa.se>',
    to: 'mikael@fallstrom.org',
    subject: 'Nytt inlägg i Boappa',
    date: new Date('2025-09-20T10:27:41.000Z'),
    messageId: '<msg170>',
    category: 'Community',
    priority: 'low',
    categorizationSource: 'ai'
  },

  // Marketing & Promotions
  {
    seqno: 169,
    uid: 169,
    flags: [],
    from: 'Amazon <store-news@amazon.com>',
    to: 'mikael@fallstrom.org',
    subject: 'Your order has been shipped',
    date: new Date('2025-09-20T10:00:00.000Z'),
    messageId: '<msg169>',
    category: 'Shopping',
    priority: 'medium',
    categorizationSource: 'ai'
  },
  {
    seqno: 168,
    uid: 168,
    flags: [],
    from: 'Smakbox <kontakt@smakbox.se>',
    to: 'mikael@fallstrom.org',
    subject: 'Dubbel rabatt i september! 🎉',
    date: new Date('2025-09-20T09:34:15.000Z'),
    messageId: '<msg168>',
    category: 'Marketing',
    priority: 'low',
    categorizationSource: 'ai'
  },
  {
    seqno: 167,
    uid: 167,
    flags: ['\\Seen'],
    from: 'Netflix <info@netflix.com>',
    to: 'mikael@fallstrom.org',
    subject: 'New episodes of your favorite show available',
    date: new Date('2025-09-20T08:00:00.000Z'),
    messageId: '<msg167>',
    category: 'Entertainment',
    priority: 'low',
    categorizationSource: 'ai'
  },

  // News & Updates
  {
    seqno: 166,
    uid: 166,
    flags: [],
    from: 'TechCrunch <newsletter@techcrunch.com>',
    to: 'mikael@fallstrom.org',
    subject: 'Daily: AI breakthrough in medical research',
    date: new Date('2025-09-20T07:00:00.000Z'),
    messageId: '<msg166>',
    category: 'Newsletter',
    priority: 'low',
    categorizationSource: 'ai'
  },
  {
    seqno: 165,
    uid: 165,
    flags: ['\\Seen'],
    from: 'Medium Daily Digest <noreply@medium.com>',
    to: 'mikael@fallstrom.org',
    subject: 'Top stories in Technology today',
    date: new Date('2025-09-20T06:00:00.000Z'),
    messageId: '<msg165>',
    category: 'Newsletter',
    priority: 'low',
    categorizationSource: 'ai'
  },

  // Travel
  {
    seqno: 164,
    uid: 164,
    flags: [],
    from: 'SAS <noreply@flysas.com>',
    to: 'mikael@fallstrom.org',
    subject: 'Check-in öppnar nu för din resa till Copenhagen',
    date: new Date('2025-09-19T22:00:00.000Z'),
    messageId: '<msg164>',
    category: 'Travel',
    priority: 'high',
    categorizationSource: 'ai'
  },
  {
    seqno: 163,
    uid: 163,
    flags: [],
    from: 'Booking.com <customer.service@booking.com>',
    to: 'mikael@fallstrom.org',
    subject: 'Din bokning är bekräftad - Hotel Nordic',
    date: new Date('2025-09-19T20:00:00.000Z'),
    messageId: '<msg163>',
    category: 'Travel',
    priority: 'medium',
    categorizationSource: 'ai'
  },

  // Health & Fitness
  {
    seqno: 162,
    uid: 162,
    flags: [],
    from: 'Vårdcentral <noreply@1177.se>',
    to: 'mikael@fallstrom.org',
    subject: 'Påminnelse: Läkarbesök måndag 14:30',
    date: new Date('2025-09-19T18:00:00.000Z'),
    messageId: '<msg162>',
    category: 'Health',
    priority: 'high',
    categorizationSource: 'ai'
  },
  {
    seqno: 161,
    uid: 161,
    flags: ['\\Seen'],
    from: 'Strava <no-reply@strava.com>',
    to: 'mikael@fallstrom.org',
    subject: 'Your weekly fitness summary',
    date: new Date('2025-09-19T16:00:00.000Z'),
    messageId: '<msg161>',
    category: 'Fitness',
    priority: 'low',
    categorizationSource: 'ai'
  },

  // Education
  {
    seqno: 160,
    uid: 160,
    flags: [],
    from: 'Coursera <no-reply@coursera.org>',
    to: 'mikael@fallstrom.org',
    subject: 'Course deadline in 2 days: Machine Learning',
    date: new Date('2025-09-19T14:00:00.000Z'),
    messageId: '<msg160>',
    category: 'Education',
    priority: 'high',
    categorizationSource: 'ai'
  },

  // Support & Customer Service
  {
    seqno: 159,
    uid: 159,
    flags: [],
    from: 'Support Team <support@techservice.com>',
    to: 'mikael@fallstrom.org',
    subject: 'Re: Ticket #4523 - Issue resolved',
    date: new Date('2025-09-19T12:00:00.000Z'),
    messageId: '<msg159>',
    category: 'Support',
    priority: 'medium',
    categorizationSource: 'ai'
  },

  // Legal & Compliance
  {
    seqno: 158,
    uid: 158,
    flags: [],
    from: 'Legal Department <legal@company.com>',
    to: 'mikael@fallstrom.org',
    subject: 'Contract review required - Due Friday',
    date: new Date('2025-09-19T10:00:00.000Z'),
    messageId: '<msg158>',
    category: 'Legal',
    priority: 'high',
    categorizationSource: 'ai'
  },

  // Spam/Junk
  {
    seqno: 157,
    uid: 157,
    flags: [],
    from: 'Winner Notification <prize@fake-lottery.com>',
    to: 'mikael@fallstrom.org',
    subject: 'Congratulations! You won €1,000,000',
    date: new Date('2025-09-19T08:00:00.000Z'),
    messageId: '<msg157>',
    category: 'Spam',
    priority: 'low',
    categorizationSource: 'ai'
  }
];

// Connect endpoint
app.post('/connect', (req, res) => {
  console.log('Mock: Connected successfully');
  res.json({ success: true, message: 'Connected successfully' });
});

// Get emails
app.get('/emails/:userId', (req, res) => {
  const { mailbox = 'INBOX', limit = 20 } = req.query;
  console.log(`Mock: Returning ${limit} emails from ${mailbox}`);

  const emailsToReturn = mockEmails.slice(0, parseInt(limit));

  // Count actual unread emails
  const unreadCount = emailsToReturn.filter(e => !e.flags.includes('\\Seen')).length;

  res.json({
    emails: emailsToReturn,
    total: mockEmails.length,
    unread: unreadCount
  });
});

// Get mailboxes
app.get('/mailboxes/:userId', (req, res) => {
  console.log('Mock: Returning mailboxes');
  res.json([
    { name: 'INBOX', path: 'INBOX', delimiter: '.', special: null },
    { name: 'Sent', path: 'Sent', delimiter: '.', special: '\\Sent' },
    { name: 'Drafts', path: 'Drafts', delimiter: '.', special: '\\Drafts' },
    { name: 'Trash', path: 'Trash', delimiter: '.', special: '\\Trash' },
    { name: 'Spam', path: 'Spam', delimiter: '.', special: '\\Junk' }
  ]);
});

// Mock accounts endpoint
app.get('/api/accounts', (req, res) => {
  console.log('Mock: Returning accounts');
  res.json({
    accounts: [
      {
        id: 'primary',
        email: 'mikael@fallstrom.org',
        displayName: 'Personal Email',
        provider: 'oneCom',
        active: true,
        color: '#3B82F6',
        unreadCount: 3
      }
    ]
  });
});

// Get mailboxes for specific account
app.get('/api/accounts/:accountId/mailboxes', (req, res) => {
  console.log('Mock: Returning mailboxes for account', req.params.accountId);
  res.json([
    { name: 'INBOX', path: 'INBOX', delimiter: '.', special: null },
    { name: 'Sent', path: 'Sent', delimiter: '.', special: '\\Sent' },
    { name: 'Drafts', path: 'Drafts', delimiter: '.', special: '\\Drafts' },
    { name: 'Trash', path: 'Trash', delimiter: '.', special: '\\Trash' },
    { name: 'Spam', path: 'Spam', delimiter: '.', special: '\\Junk' }
  ]);
});

// Add account
app.post('/api/accounts', (req, res) => {
  console.log('Mock: Adding account', req.body);
  res.json({
    account: {
      id: 'account-' + Date.now(),
      email: req.body.email,
      displayName: req.body.displayName || req.body.email,
      provider: req.body.provider || 'auto',
      active: true,
      color: '#10B981',
      unreadCount: 0
    }
  });
});

// Connect account
app.post('/api/accounts/:id/connect', (req, res) => {
  console.log('Mock: Connecting to account', req.params.id);
  res.json({ success: true, message: 'Connected successfully' });
});

// Toggle account
app.post('/api/accounts/:id/toggle', (req, res) => {
  console.log('Mock: Toggling account', req.params.id, req.body);
  res.json({ success: true, active: req.body.active });
});

// Remove account
app.delete('/api/accounts/:id', (req, res) => {
  console.log('Mock: Removing account', req.params.id);
  res.json({ success: true });
});

// Category stats endpoint
app.get('/api/categories/stats/:accountId', (req, res) => {
  console.log('Mock: Returning category stats for', req.params.accountId);

  // Calculate actual stats from mock emails
  const categories = {};
  const priorities = { high: 0, medium: 0, low: 0 };
  let unreadCount = 0;

  mockEmails.forEach(email => {
    // Count categories
    if (email.category) {
      categories[email.category] = (categories[email.category] || 0) + 1;
    }
    // Count priorities
    if (email.priority) {
      priorities[email.priority]++;
    }
    // Count unread
    if (!email.flags.includes('\\Seen')) {
      unreadCount++;
    }
  });

  res.json({
    stats: {
      categories,
      priorities,
      sources: {
        'ai': mockEmails.length,
        'user_override': 0,
        'default': 0
      },
      total: mockEmails.length,
      unread: unreadCount
    }
  });
});

// Recent emails with categorization
app.get('/recent-emails/:accountId', (req, res) => {
  const { limit = 100 } = req.query;
  console.log(`Mock: Returning ${limit} recent emails for ${req.params.accountId}`);

  // Return emails that already have categories defined
  const emailsToReturn = mockEmails.slice(0, parseInt(limit));
  res.json(emailsToReturn);
});

// Smart inbox endpoint
app.get('/smart-inbox/:accountId', (req, res) => {
  console.log('Mock: Returning smart inbox for', req.params.accountId);

  const importantEmails = mockEmails.filter(e => e.priority === 'high');
  const unreadEmails = mockEmails.filter(e => !e.flags.includes('\\Seen'));
  const recentEmails = mockEmails.slice(0, 5);

  res.json({
    inbox: {
      important: importantEmails,
      unread: unreadEmails,
      recent: recentEmails
    },
    stats: {
      total: mockEmails.length,
      unread: unreadEmails.length,
      important: importantEmails.length
    }
  });
});

// Category override endpoint
app.post('/api/categories/override', (req, res) => {
  console.log('Mock: Setting category override', req.body);
  res.json({
    success: true,
    emailId: req.body.emailId,
    category: req.body.category,
    source: 'user_override'
  });
});

// Sync emails endpoint
app.post('/sync-emails/:accountId', (req, res) => {
  console.log('Mock: Syncing emails for', req.params.accountId);
  res.json({
    success: true,
    message: 'Sync completed',
    newEmails: 0,
    updatedEmails: 0
  });
});

// Health check
app.get('/health', (req, res) => {
  res.json({ status: 'ok', type: 'mock' });
});

app.listen(PORT, () => {
  console.log(`Mock Email Service running on port ${PORT}`);
  console.log('This is a MOCK service returning static data for testing');
  console.log('Available endpoints:');
  console.log('  GET  /health');
  console.log('  GET  /api/accounts');
  console.log('  POST /api/accounts');
  console.log('  POST /api/accounts/:id/connect');
  console.log('  POST /api/accounts/:id/toggle');
  console.log('  DELETE /api/accounts/:id');
  console.log('  GET  /api/categories/stats/:accountId');
  console.log('  POST /api/categories/override');
  console.log('  GET  /recent-emails/:accountId');
  console.log('  GET  /smart-inbox/:accountId');
  console.log('  POST /sync-emails/:accountId');
  console.log('  GET  /emails/:userId');
  console.log('  GET  /mailboxes/:userId');
  console.log('  POST /connect');
});