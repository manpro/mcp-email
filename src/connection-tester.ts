import { createImapConfig, EmailProviders } from './email-providers.js';
import net from 'net';
import tls from 'tls';

export interface ConnectionTestResult {
  success: boolean;
  message: string;
  details: {
    host: string;
    port: number;
    tcpConnect: boolean;
    tlsConnect: boolean;
    imapResponse?: string;
    error?: string;
  };
}

export class ConnectionTester {
  static async testConnection(
    email: string,
    provider?: string,
    customHost?: string,
    customPort?: number
  ): Promise<ConnectionTestResult> {
    const config = createImapConfig(email, '', provider, customHost, customPort);
    
    const result: ConnectionTestResult = {
      success: false,
      message: '',
      details: {
        host: config.host,
        port: config.port,
        tcpConnect: false,
        tlsConnect: false
      }
    };

    try {
      // Test 1: TCP Connection
      console.log(`Testing TCP connection to ${config.host}:${config.port}...`);
      const tcpTest = await this.testTcpConnection(config.host, config.port);
      result.details.tcpConnect = tcpTest.success;
      
      if (!tcpTest.success) {
        result.message = `TCP-anslutning misslyckades: ${tcpTest.error}`;
        return result;
      }

      // Test 2: TLS Connection (if using TLS)
      if (config.tls) {
        console.log(`Testing TLS connection to ${config.host}:${config.port}...`);
        const tlsTest = await this.testTlsConnection(config.host, config.port);
        result.details.tlsConnect = tlsTest.success;
        
        if (!tlsTest.success) {
          result.message = `TLS-anslutning misslyckades: ${tlsTest.error}`;
          return result;
        }
      }

      // Test 3: IMAP Greeting
      console.log(`Testing IMAP greeting from ${config.host}:${config.port}...`);
      const imapTest = await this.testImapGreeting(config.host, config.port, config.tls ?? true);
      result.details.imapResponse = imapTest.response;
      
      if (!imapTest.success) {
        result.message = `IMAP-server svarar inte korrekt: ${imapTest.error}`;
        return result;
      }

      result.success = true;
      result.message = `Anslutning till ${config.host}:${config.port} fungerar!`;
      
    } catch (error) {
      result.message = `Testfel: ${error instanceof Error ? error.message : String(error)}`;
      result.details.error = error instanceof Error ? error.message : String(error);
    }

    return result;
  }

  private static testTcpConnection(host: string, port: number): Promise<{success: boolean; error?: string}> {
    return new Promise((resolve) => {
      const socket = net.createConnection({ host, port, timeout: 10000 });
      
      socket.on('connect', () => {
        socket.destroy();
        resolve({ success: true });
      });
      
      socket.on('error', (err) => {
        resolve({ success: false, error: err.message });
      });
      
      socket.on('timeout', () => {
        socket.destroy();
        resolve({ success: false, error: 'Timeout' });
      });
    });
  }

  private static testTlsConnection(host: string, port: number): Promise<{success: boolean; error?: string}> {
    return new Promise((resolve) => {
      const options = {
        host,
        port,
        timeout: 10000,
        rejectUnauthorized: false
      };
      
      const socket = tls.connect(options, () => {
        socket.destroy();
        resolve({ success: true });
      });
      
      socket.on('error', (err) => {
        resolve({ success: false, error: err.message });
      });
      
      socket.on('timeout', () => {
        socket.destroy();
        resolve({ success: false, error: 'TLS Timeout' });
      });
    });
  }

  private static testImapGreeting(host: string, port: number, useTls: boolean): Promise<{success: boolean; response?: string; error?: string}> {
    return new Promise((resolve) => {
      let socket: net.Socket | tls.TLSSocket;
      
      if (useTls) {
        socket = tls.connect({ host, port, rejectUnauthorized: false });
      } else {
        socket = net.createConnection({ host, port });
      }

      let response = '';
      let resolved = false;

      const timeout = setTimeout(() => {
        if (!resolved) {
          resolved = true;
          socket.destroy();
          resolve({ success: false, error: 'IMAP greeting timeout' });
        }
      }, 10000);

      socket.on('data', (data) => {
        response += data.toString();
        if (response.includes('OK') && !resolved) {
          resolved = true;
          clearTimeout(timeout);
          socket.destroy();
          resolve({ success: true, response: response.trim() });
        }
      });

      socket.on('error', (err) => {
        if (!resolved) {
          resolved = true;
          clearTimeout(timeout);
          resolve({ success: false, error: err.message });
        }
      });

      socket.on('connect', () => {
        console.log('Socket connected, waiting for IMAP greeting...');
      });
    });
  }

  static async suggestAlternatives(email: string): Promise<string[]> {
    const domain = email.split('@')[1];
    const suggestions: string[] = [];

    // Common IMAP server patterns
    const patterns = [
      `imap.${domain}`,
      `mail.${domain}`,
      `${domain}`,
      `imap.gmail.com`, // If it's a gmail domain variant
      `outlook.office365.com` // If it's a microsoft domain
    ];

    // Add provider-specific suggestions
    if (domain?.includes('gmail') || domain?.includes('googlemail')) {
      suggestions.push('imap.gmail.com:993 (Gmail)');
    }
    
    if (domain?.includes('outlook') || domain?.includes('hotmail') || domain?.includes('live')) {
      suggestions.push('outlook.office365.com:993 (Outlook)');
    }
    
    if (domain?.includes('one.com')) {
      suggestions.push('imap.one.com:993 (One.com)');
    }

    // Add generic patterns
    patterns.forEach(pattern => {
      if (pattern !== domain) {
        suggestions.push(`${pattern}:993`);
        suggestions.push(`${pattern}:143`);
      }
    });

    return suggestions.slice(0, 5); // Return top 5 suggestions
  }
}