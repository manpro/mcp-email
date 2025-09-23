const fs = require('fs');
const path = require('path');

class EnvSaver {
  constructor() {
    this.envPath = path.join(__dirname, '.env');
  }

  // Save or update credentials in .env file
  saveCredentials(email, password, provider) {
    try {
      let envContent = '';

      // Read existing .env file if it exists
      if (fs.existsSync(this.envPath)) {
        envContent = fs.readFileSync(this.envPath, 'utf8');
      }

      // Determine which provider to update
      let prefix = '';
      let imapHost = '';
      let imapPort = '993';
      let smtpHost = '';
      let smtpPort = '587';

      if (provider === 'oneCom' || email.includes('@fallstrom.org')) {
        prefix = 'ONECOM';
        imapHost = 'imap.one.com';
        smtpHost = 'send.one.com';
      } else if (provider === 'gmail' || email.includes('@gmail.com')) {
        prefix = 'GMAIL';
        imapHost = 'imap.gmail.com';
        smtpHost = 'smtp.gmail.com';
      } else {
        // Default to ONECOM for unknown providers
        prefix = 'ONECOM';
        imapHost = 'imap.one.com';
        smtpHost = 'send.one.com';
      }

      // Update or add credentials
      const updates = {
        [`${prefix}_EMAIL`]: email,
        [`${prefix}_PASSWORD`]: password,
        [`${prefix}_IMAP_HOST`]: imapHost,
        [`${prefix}_IMAP_PORT`]: imapPort,
        [`${prefix}_SMTP_HOST`]: smtpHost,
        [`${prefix}_SMTP_PORT`]: smtpPort
      };

      // Parse existing env content
      const lines = envContent.split('\n');
      const envVars = {};

      // Read existing variables
      lines.forEach(line => {
        if (line && !line.startsWith('#')) {
          const [key, ...valueParts] = line.split('=');
          if (key) {
            envVars[key.trim()] = valueParts.join('=').trim();
          }
        }
      });

      // Update with new values
      Object.assign(envVars, updates);

      // Build new env content
      let newEnvContent = `# Email Service Configuration
PORT=3012

# Redis Configuration
REDIS_HOST=172.17.0.1
REDIS_PORT=6381

# Email Accounts Configuration
`;

      // Add OneCom credentials if present
      if (envVars['ONECOM_EMAIL']) {
        newEnvContent += `
# OneCom Account
ONECOM_EMAIL=${envVars['ONECOM_EMAIL']}
ONECOM_PASSWORD=${envVars['ONECOM_PASSWORD'] || ''}
ONECOM_IMAP_HOST=${envVars['ONECOM_IMAP_HOST'] || 'imap.one.com'}
ONECOM_IMAP_PORT=${envVars['ONECOM_IMAP_PORT'] || '993'}
ONECOM_SMTP_HOST=${envVars['ONECOM_SMTP_HOST'] || 'send.one.com'}
ONECOM_SMTP_PORT=${envVars['ONECOM_SMTP_PORT'] || '587'}
`;
      }

      // Add Gmail credentials if present
      if (envVars['GMAIL_EMAIL']) {
        newEnvContent += `
# Gmail Account
GMAIL_EMAIL=${envVars['GMAIL_EMAIL']}
GMAIL_PASSWORD=${envVars['GMAIL_PASSWORD'] || ''}
GMAIL_IMAP_HOST=${envVars['GMAIL_IMAP_HOST'] || 'imap.gmail.com'}
GMAIL_IMAP_PORT=${envVars['GMAIL_IMAP_PORT'] || '993'}
GMAIL_SMTP_HOST=${envVars['GMAIL_SMTP_HOST'] || 'smtp.gmail.com'}
GMAIL_SMTP_PORT=${envVars['GMAIL_SMTP_PORT'] || '587'}
`;
      }

      // Write updated content to .env file
      fs.writeFileSync(this.envPath, newEnvContent.trim() + '\n');

      console.log(`✓ Credentials saved to .env for ${email}`);
      return true;
    } catch (error) {
      console.error('Error saving credentials to .env:', error);
      return false;
    }
  }

  // Load credentials from .env file
  loadCredentials() {
    const credentials = [];

    if (!fs.existsSync(this.envPath)) {
      return credentials;
    }

    try {
      const envContent = fs.readFileSync(this.envPath, 'utf8');
      const lines = envContent.split('\n');
      const envVars = {};

      lines.forEach(line => {
        if (line && !line.startsWith('#')) {
          const [key, ...valueParts] = line.split('=');
          if (key) {
            envVars[key.trim()] = valueParts.join('=').trim();
          }
        }
      });

      // Check for OneCom credentials
      if (envVars['ONECOM_EMAIL'] && envVars['ONECOM_PASSWORD']) {
        credentials.push({
          email: envVars['ONECOM_EMAIL'],
          password: envVars['ONECOM_PASSWORD'],
          provider: 'oneCom',
          imapHost: envVars['ONECOM_IMAP_HOST'] || 'imap.one.com',
          imapPort: parseInt(envVars['ONECOM_IMAP_PORT'] || '993')
        });
      }

      // Check for Gmail credentials
      if (envVars['GMAIL_EMAIL'] && envVars['GMAIL_PASSWORD']) {
        credentials.push({
          email: envVars['GMAIL_EMAIL'],
          password: envVars['GMAIL_PASSWORD'],
          provider: 'gmail',
          imapHost: envVars['GMAIL_IMAP_HOST'] || 'imap.gmail.com',
          imapPort: parseInt(envVars['GMAIL_IMAP_PORT'] || '993')
        });
      }

      return credentials;
    } catch (error) {
      console.error('Error loading credentials from .env:', error);
      return credentials;
    }
  }
}

module.exports = new EnvSaver();