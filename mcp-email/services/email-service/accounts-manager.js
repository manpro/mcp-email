const fs = require('fs').promises;
const path = require('path');
const crypto = require('crypto');

class AccountsManager {
  constructor() {
    this.accountsFile = path.join(__dirname, 'accounts.json');
    this.accounts = new Map();
    this.connections = new Map(); // Active IMAP connections
    this.loadAccounts();
  }

  async loadAccounts() {
    try {
      const data = await fs.readFile(this.accountsFile, 'utf8');
      const accounts = JSON.parse(data);
      accounts.forEach(acc => {
        this.accounts.set(acc.id, acc);
      });
      console.log(`Loaded ${this.accounts.size} accounts`);
    } catch (error) {
      if (error.code === 'ENOENT') {
        // File doesn't exist, create it
        await this.saveAccounts();
        console.log('Created new accounts file');
      } else {
        console.error('Error loading accounts:', error);
      }
    }
  }

  async saveAccounts() {
    try {
      const accounts = Array.from(this.accounts.values()).map(acc => ({
        ...acc,
        password: undefined // Don't save passwords in plain text
      }));
      await fs.writeFile(this.accountsFile, JSON.stringify(accounts, null, 2));
    } catch (error) {
      console.error('Error saving accounts:', error);
    }
  }

  generateAccountId(email) {
    // Generate unique ID based on email
    return crypto.createHash('md5').update(email).digest('hex').substring(0, 8);
  }

  async addAccount(accountData) {
    const {
      email,
      password,
      provider,
      displayName,
      color,
      imapHost,
      imapPort = 993,
      smtpHost,
      smtpPort = 587
    } = accountData;

    // Auto-detect IMAP settings if not provided
    let finalImapHost = imapHost;
    let finalSmtpHost = smtpHost;

    if (!imapHost) {
      const domain = email.split('@')[1];
      if (domain === 'fallstrom.org') {
        finalImapHost = 'imap.one.com';
        finalSmtpHost = 'send.one.com';
      } else if (domain.includes('gmail')) {
        finalImapHost = 'imap.gmail.com';
        finalSmtpHost = 'smtp.gmail.com';
      } else if (domain.includes('outlook') || domain.includes('hotmail')) {
        finalImapHost = 'outlook.office365.com';
        finalSmtpHost = 'smtp-mail.outlook.com';
      } else if (domain.includes('yahoo')) {
        finalImapHost = 'imap.mail.yahoo.com';
        finalSmtpHost = 'smtp.mail.yahoo.com';
      }
    }

    const accountId = this.generateAccountId(email);

    const account = {
      id: accountId,
      email,
      displayName: displayName || email.split('@')[0],
      provider: provider || 'custom',
      color: color || this.generateColor(accountId),
      imapHost: finalImapHost,
      imapPort,
      smtpHost: finalSmtpHost,
      smtpPort,
      createdAt: new Date().toISOString(),
      lastSync: null,
      folders: [],
      active: true,
      unreadCount: 0,
      totalCount: 0
    };

    // Store account
    this.accounts.set(accountId, account);
    await this.saveAccounts();

    // Store password in memory only (should use secure storage in production)
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

    Object.assign(account, updates);
    await this.saveAccounts();
    return account;
  }

  async removeAccount(accountId) {
    // Disconnect if connected
    await this.disconnectAccount(accountId);

    // Remove from storage
    this.accounts.delete(accountId);
    await this.saveAccounts();

    // Clear credentials
    this.clearCredentials(accountId);

    return { success: true, accountId };
  }

  async toggleAccount(accountId, active) {
    const account = this.accounts.get(accountId);
    if (!account) {
      throw new Error(`Account ${accountId} not found`);
    }

    account.active = active;

    if (!active) {
      await this.disconnectAccount(accountId);
    }

    await this.saveAccounts();
    return account;
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

  // Credential management (in production, use keyring or secure storage)
  storeCredentials(accountId, password) {
    // This is temporary - in production use secure credential storage
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

  async disconnectAccount(accountId) {
    const connection = this.connections.get(accountId);
    if (connection) {
      try {
        // Call disconnect on the connection if it has that method
        if (connection.disconnect) {
          await connection.disconnect();
        }
      } catch (error) {
        console.error(`Error disconnecting account ${accountId}:`, error);
      }
      this.connections.delete(accountId);
    }
  }

  async disconnectAll() {
    for (const accountId of this.connections.keys()) {
      await this.disconnectAccount(accountId);
    }
  }

  // Helper to generate unique colors for accounts
  generateColor(seed) {
    const colors = [
      '#3B82F6', // blue
      '#10B981', // emerald
      '#8B5CF6', // violet
      '#F59E0B', // amber
      '#EF4444', // red
      '#EC4899', // pink
      '#14B8A6', // teal
      '#F97316', // orange
      '#6366F1', // indigo
      '#84CC16'  // lime
    ];

    const index = parseInt(seed.substring(0, 2), 16) % colors.length;
    return colors[index];
  }

  // Update folder structure for an account
  async updateFolders(accountId, folders) {
    const account = this.accounts.get(accountId);
    if (!account) {
      throw new Error(`Account ${accountId} not found`);
    }

    account.folders = folders;
    account.lastSync = new Date().toISOString();
    await this.saveAccounts();
    return account;
  }

  // Update unread/total counts
  async updateCounts(accountId, unreadCount, totalCount) {
    const account = this.accounts.get(accountId);
    if (!account) {
      throw new Error(`Account ${accountId} not found`);
    }

    account.unreadCount = unreadCount;
    account.totalCount = totalCount;
    await this.saveAccounts();
    return account;
  }
}

// Export singleton instance
module.exports = new AccountsManager();