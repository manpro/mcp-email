import { ImapConfig } from './imap-client.js';

export interface EmailProvider {
  name: string;
  getConfig(email: string, password: string): ImapConfig;
}

export const EmailProviders: Record<string, EmailProvider> = {
  outlook: {
    name: 'Microsoft Outlook/Exchange',
    getConfig: (email: string, password: string): ImapConfig => ({
      host: 'outlook.office365.com',
      port: 993,
      user: email,
      password: password,
      tls: true,
      tlsOptions: {
        servername: 'outlook.office365.com',
        rejectUnauthorized: true
      },
      authTimeout: 10000,
      connTimeout: 15000
    })
  },
  
  exchangeOnline: {
    name: 'Microsoft Exchange Online',
    getConfig: (email: string, password: string): ImapConfig => ({
      host: 'outlook.office365.com',
      port: 993,
      user: email,
      password: password,
      tls: true,
      tlsOptions: {
        servername: 'outlook.office365.com',
        rejectUnauthorized: true
      },
      authTimeout: 10000,
      connTimeout: 15000
    })
  },

  exchangeOnPremise: {
    name: 'Microsoft Exchange On-Premise',
    getConfig: (email: string, password: string): ImapConfig => {
      const domain = email.split('@')[1];
      return {
        host: `mail.${domain}`,
        port: 993,
        user: email,
        password: password,
        tls: true,
        tlsOptions: {
          rejectUnauthorized: false // Often needed for self-signed certs
        },
        authTimeout: 10000,
        connTimeout: 15000
      };
    }
  },

  gmail: {
    name: 'Gmail',
    getConfig: (email: string, password: string): ImapConfig => ({
      host: 'imap.gmail.com',
      port: 993,
      user: email,
      password: password,
      tls: true,
      tlsOptions: {
        servername: 'imap.gmail.com',
        rejectUnauthorized: true
      },
      authTimeout: 10000,
      connTimeout: 15000
    })
  },

  oneCom: {
    name: 'One.com',
    getConfig: (email: string, password: string): ImapConfig => ({
      host: 'imap.one.com',
      port: 993,
      user: email,
      password: password,
      tls: true,
      tlsOptions: {
        servername: 'imap.one.com',
        rejectUnauthorized: true
      },
      authTimeout: 15000,
      connTimeout: 20000
    })
  },

  generic: {
    name: 'Generic IMAP',
    getConfig: (email: string, password: string): ImapConfig => {
      const domain = email.split('@')[1];
      return {
        host: `imap.${domain}`,
        port: 993,
        user: email,
        password: password,
        tls: true,
        authTimeout: 10000,
        connTimeout: 15000
      };
    }
  }
};

export function detectProvider(email: string): string {
  const domain = email.split('@')[1]?.toLowerCase();
  
  if (domain?.includes('outlook.com') || domain?.includes('hotmail.com') || 
      domain?.includes('live.com') || domain?.includes('msn.com')) {
    return 'outlook';
  }
  
  if (domain?.includes('gmail.com')) {
    return 'gmail';
  }
  
  if (domain?.includes('one.com')) {
    return 'oneCom';
  }
  
  return 'generic';
}

export function createImapConfig(
  email: string, 
  password: string, 
  provider?: string,
  customHost?: string,
  customPort?: number
): ImapConfig {
  if (customHost) {
    return {
      host: customHost,
      port: customPort || 993,
      user: email,
      password: password,
      tls: true,
      authTimeout: 10000,
      connTimeout: 15000
    };
  }

  const detectedProvider = provider || detectProvider(email);
  const emailProvider = EmailProviders[detectedProvider] || EmailProviders.generic;
  
  return emailProvider.getConfig(email, password);
}