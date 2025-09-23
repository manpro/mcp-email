const fs = require('fs').promises;
const path = require('path');
const crypto = require('crypto');
require('dotenv').config();
const envSaver = require('./env-saver');

class EnvAccountsManager {
  constructor() {
    this.accountsFile = path.join(__dirname, 'accounts.json');
    this.accounts = new Map();
    this.connections = new Map();
    this.loadAccounts();
    this.loadEnvCredentials();
  }

  async loadAccounts() {
    try {
      const data = await fs.readFile(this.accountsFile, 'utf8');
      const accounts = JSON.parse(data);
      accounts.forEach(acc => {
        this.accounts.set(acc.id, acc);
      });
      console.log(`Loaded ${this.accounts.size} accounts from file`);
    } catch (error) {
      if (error.code === 'ENOENT') {
        await this.saveAccounts();
        console.log('Created new accounts file');
      } else {
        console.error('Error loading accounts:', error);
      }
    }
  }

  loadEnvCredentials() {
    // Load credentials from .env file using envSaver
    const savedCredentials = envSaver.loadCredentials();

    savedCredentials.forEach(cred => {
      const accountId = this.generateAccountId(cred.email);

      // Store credentials in memory
      this.storeCredentials(accountId, cred.password);

      // Update or create account
      const existingAccount = this.findAccountByEmail(cred.email);
      if (existingAccount) {
        existingAccount.active = true;
        console.log(`Activated account from .env: ${cred.email}`);
      } else {
        // Create new account from env
        const account = {
          id: accountId,
          email: cred.email,
          displayName: cred.email.split('@')[0],
          provider: cred.provider,
          color: cred.provider === 'oneCom' ? '#3B82F6' : '#EA4335',
          imapHost: cred.imapHost,
          imapPort: cred.imapPort,
          smtpHost: cred.provider === 'oneCom' ? 'send.one.com' : 'smtp.gmail.com',
          smtpPort: 587,
          createdAt: new Date().toISOString(),
          lastSync: null,
          folders: [],
          active: true,
          unreadCount: 0,
          totalCount: 0
        };

        this.accounts.set(accountId, account);
        console.log(`Created account from .env: ${cred.email}`);
      }
    });

    // Save updated accounts if any were loaded
    if (savedCredentials.length > 0) {
      this.saveAccounts();
    }
  }

  async saveAccounts() {
    try {
      const accounts = Array.from(this.accounts.values()).map(acc => ({
        ...acc,
        password: undefined // Don't save passwords
      }));
      await fs.writeFile(this.accountsFile, JSON.stringify(accounts, null, 2));
    } catch (error) {
      console.error('Error saving accounts:', error);
    }
  }

  generateAccountId(email) {
    return crypto.createHash('md5').update(email).digest('hex').substring(0, 8);
  }

  findAccountByEmail(email) {
    for (const account of this.accounts.values()) {
      if (account.email === email) {
        return account;
      }
    }
    return null;
  }

  async addAccount(accountData) {
    const { email, password, provider } = accountData;

    // Determine provider settings from env or defaults
    let imapHost, imapPort, smtpHost, smtpPort;

    if (provider === 'oneCom') {
      imapHost = process.env.ONECOM_IMAP_HOST || 'imap.one.com';
      imapPort = parseInt(process.env.ONECOM_IMAP_PORT || '993');
      smtpHost = process.env.ONECOM_SMTP_HOST || 'send.one.com';
      smtpPort = parseInt(process.env.ONECOM_SMTP_PORT || '587');
    } else if (provider === 'gmail') {
      imapHost = process.env.GMAIL_IMAP_HOST || 'imap.gmail.com';
      imapPort = parseInt(process.env.GMAIL_IMAP_PORT || '993');
      smtpHost = process.env.GMAIL_SMTP_HOST || 'smtp.gmail.com';
      smtpPort = parseInt(process.env.GMAIL_SMTP_PORT || '587');
    }

    const accountId = this.generateAccountId(email);

    const account = {
      id: accountId,
      email,
      displayName: accountData.displayName || email.split('@')[0],
      provider,
      color: provider === 'oneCom' ? '#3B82F6' : '#EA4335',
      imapHost: accountData.imapHost || imapHost,
      imapPort: accountData.imapPort || imapPort,
      smtpHost: accountData.smtpHost || smtpHost,
      smtpPort: accountData.smtpPort || smtpPort,
      createdAt: new Date().toISOString(),
      lastSync: null,
      folders: [],
      active: true,
      unreadCount: 0,
      totalCount: 0
    };

    this.accounts.set(accountId, account);
    await this.saveAccounts();

    if (password) {
      this.storeCredentials(accountId, password);
    }

    return account;
  }

  async updateAccount(accountId, updates) {
    const account = this.accounts.get(accountId);
    if (!account) {
      throw new Error(`Account ${accountId} not found`);
    }

    Object.assign(account, updates, {
      lastUpdated: new Date().toISOString()
    });

    await this.saveAccounts();
    return account;
  }

  async removeAccount(accountId) {
    if (this.connections.has(accountId)) {
      const connection = this.connections.get(accountId);
      if (connection && connection.disconnect) {
        await connection.disconnect();
      }
      this.connections.delete(accountId);
    }

    this.accounts.delete(accountId);
    this.clearCredentials(accountId);
    await this.saveAccounts();
  }

  getAccount(accountId) {
    return this.accounts.get(accountId);
  }

  getAllAccounts() {
    return Array.from(this.accounts.values());
  }

  getActiveAccounts() {
    return Array.from(this.accounts.values()).filter(acc => acc.active);
  }

  updateCounts(accountId, counts) {
    const account = this.accounts.get(accountId);
    if (account) {
      account.totalEmails = counts.total || 0;
      account.unreadEmails = counts.unread || 0;
      account.lastSync = new Date().toISOString();
      this.saveAccounts();
      return account;
    }
    return null;
  }

  // Credential management
  storeCredentials(accountId, password) {
    if (!global.emailCredentials) {
      global.emailCredentials = new Map();
    }
    global.emailCredentials.set(accountId, password);
  }

  getCredentials(accountId) {
    if (!global.emailCredentials) {
      return null;
    }
    return global.emailCredentials.get(accountId);
  }

  clearCredentials(accountId) {
    if (global.emailCredentials) {
      global.emailCredentials.delete(accountId);
    }
  }

  // Connection management
  setConnection(accountId, connection) {
    this.connections.set(accountId, connection);
  }

  getConnection(accountId) {
    return this.connections.get(accountId);
  }

  async closeConnection(accountId) {
    if (this.connections.has(accountId)) {
      const connection = this.connections.get(accountId);
      if (connection && connection.disconnect) {
        await connection.disconnect();
      }
      this.connections.delete(accountId);
    }
  }

  async closeAllConnections() {
    for (const [accountId, connection] of this.connections) {
      if (connection && connection.disconnect) {
        await connection.disconnect();
      }
    }
    this.connections.clear();
  }
}

module.exports = new EnvAccountsManager();