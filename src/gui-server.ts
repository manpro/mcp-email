#!/usr/bin/env node

import express from 'express';
import cors from 'cors';
import path from 'path';
import { fileURLToPath } from 'url';
import { ImapEmailClient } from './imap-client.js';
import { createImapConfig } from './email-providers.js';
import { ConnectionTester } from './connection-tester.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

class EmailGUIServer {
  private app: express.Application;
  private clients: Map<string, ImapEmailClient> = new Map();
  private port: number;

  constructor(port: number = 3623) {
    this.port = port;
    this.app = express();
    this.setupMiddleware();
    this.setupRoutes();
    this.setupErrorHandling();
  }

  private setupMiddleware(): void {
    this.app.use(cors());
    this.app.use(express.json());
    this.app.use(express.static(path.join(__dirname, '../public')));
  }

  private setupRoutes(): void {
    // Serve static files
    this.app.get('/', (req, res) => {
      res.sendFile(path.join(__dirname, '../public/index.html'));
    });

    // API Routes
    this.app.post('/api/connect', async (req, res) => {
      try {
        const { connectionId, email, password, provider, customHost, customPort } = req.body;

        console.log(`Connection attempt: ${connectionId} - ${email} - Provider: ${provider || 'auto'}`);

        if (!connectionId || !email || !password) {
          return res.status(400).json({ error: 'connectionId, email och password krävs' });
        }

        if (this.clients.has(connectionId)) {
          return res.status(400).json({ error: `Anslutning med ID '${connectionId}' finns redan` });
        }

        const config = createImapConfig(email, password, provider, customHost, customPort);
        console.log(`Using config: ${config.host}:${config.port} for ${email}`);
        
        const client = new ImapEmailClient(config);
        
        // Test connection with timeout
        const connectPromise = client.connect();
        const timeoutPromise = new Promise((_, reject) => {
          setTimeout(() => reject(new Error('Anslutning tog för lång tid (40s timeout)')), 40000);
        });

        await Promise.race([connectPromise, timeoutPromise]);
        
        this.clients.set(connectionId, client);

        res.json({ 
          success: true, 
          message: `Ansluten till ${email} som ${connectionId}`,
          connectionId,
          email,
          provider: provider || 'automatisk',
          host: config.host,
          port: config.port
        });
      } catch (error) {
        console.error('Connection error:', error);
        
        let errorMessage = 'Okänt fel vid anslutning';
        if (error instanceof Error) {
          if (error.message.includes('timeout')) {
            errorMessage = 'Anslutningen tog för lång tid. Kontrollera värdnamn och port.';
          } else if (error.message.includes('ENOTFOUND')) {
            errorMessage = 'Servern hittades inte. Kontrollera värdnamnet.';
          } else if (error.message.includes('ECONNREFUSED')) {
            errorMessage = 'Anslutningen nekades. Kontrollera port och brandväggsinställningar.';
          } else if (error.message.includes('authentication')) {
            errorMessage = 'Autentiseringsfel. Kontrollera e-post och lösenord.';
          } else if (error.message.includes('certificate')) {
            errorMessage = 'SSL-certifikatfel. Försök med "Exchange On-Premise" för företagsmejl.';
          } else {
            errorMessage = error.message;
          }
        }
        
        res.status(500).json({ 
          error: errorMessage,
          details: error instanceof Error ? error.message : String(error)
        });
      }
    });

    this.app.post('/api/disconnect', async (req, res) => {
      try {
        const { connectionId } = req.body;

        if (!connectionId) {
          return res.status(400).json({ error: 'connectionId krävs' });
        }

        const client = this.clients.get(connectionId);
        if (!client) {
          return res.status(404).json({ error: `Anslutning '${connectionId}' hittades inte` });
        }

        await client.disconnect();
        this.clients.delete(connectionId);

        res.json({ 
          success: true, 
          message: `Frånkopplad från ${connectionId}` 
        });
      } catch (error) {
        console.error('Disconnect error:', error);
        res.status(500).json({ 
          error: error instanceof Error ? error.message : 'Okänt fel vid frånkoppling' 
        });
      }
    });

    this.app.post('/api/recent-emails', async (req, res) => {
      try {
        const { connectionId, count = 10, mailbox = 'INBOX' } = req.body;

        if (!connectionId) {
          return res.status(400).json({ error: 'connectionId krävs' });
        }

        const client = this.clients.get(connectionId);
        if (!client) {
          return res.status(404).json({ error: `Anslutning '${connectionId}' hittades inte` });
        }

        const emails = await client.getRecentEmails(count, mailbox);
        
        const emailSummary = emails.map(email => ({
          uid: email.uid,
          subject: email.subject,
          from: email.from,
          to: email.to,
          date: email.date,
          flags: email.flags,
          hasAttachments: (email.attachments?.length || 0) > 0,
          bodyPreview: email.bodyText?.substring(0, 200) + (email.bodyText && email.bodyText.length > 200 ? '...' : ''),
        }));

        res.json({ 
          success: true, 
          emails: emailSummary,
          count: emailSummary.length,
          mailbox 
        });
      } catch (error) {
        console.error('Get emails error:', error);
        res.status(500).json({ 
          error: error instanceof Error ? error.message : 'Okänt fel vid hämtning av e-post' 
        });
      }
    });

    this.app.post('/api/mailboxes', async (req, res) => {
      try {
        const { connectionId } = req.body;

        if (!connectionId) {
          return res.status(400).json({ error: 'connectionId krävs' });
        }

        const client = this.clients.get(connectionId);
        if (!client) {
          return res.status(404).json({ error: `Anslutning '${connectionId}' hittades inte` });
        }

        const mailboxes = await client.getMailboxes();

        res.json({ 
          success: true, 
          mailboxes 
        });
      } catch (error) {
        console.error('Get mailboxes error:', error);
        res.status(500).json({ 
          error: error instanceof Error ? error.message : 'Okänt fel vid hämtning av mappar' 
        });
      }
    });

    this.app.post('/api/search-emails', async (req, res) => {
      try {
        const { connectionId, criteria, limit = 20, mailbox = 'INBOX' } = req.body;

        if (!connectionId || !criteria) {
          return res.status(400).json({ error: 'connectionId och criteria krävs' });
        }

        const client = this.clients.get(connectionId);
        if (!client) {
          return res.status(404).json({ error: `Anslutning '${connectionId}' hittades inte` });
        }

        const uids = await client.searchEmails(criteria, mailbox);
        const limitedUids = uids.slice(-limit);
        const emails = await client.fetchEmails(limitedUids, mailbox);
        
        const emailSummary = emails.map(email => ({
          uid: email.uid,
          subject: email.subject,
          from: email.from,
          to: email.to,
          date: email.date,
          flags: email.flags,
          hasAttachments: (email.attachments?.length || 0) > 0,
          bodyPreview: email.bodyText?.substring(0, 200) + (email.bodyText && email.bodyText.length > 200 ? '...' : ''),
        }));

        res.json({ 
          success: true, 
          emails: emailSummary,
          count: emailSummary.length,
          totalFound: uids.length,
          criteria,
          mailbox 
        });
      } catch (error) {
        console.error('Search emails error:', error);
        res.status(500).json({ 
          error: error instanceof Error ? error.message : 'Okänt fel vid sökning av e-post' 
        });
      }
    });

    this.app.get('/api/connections', (req, res) => {
      const connectionsList = Array.from(this.clients.keys()).map(id => ({
        connectionId: id,
        connected: this.clients.get(id)?.isConnected() || false
      }));

      res.json({ 
        success: true, 
        connections: connectionsList,
        count: connectionsList.length 
      });
    });

    this.app.post('/api/test-connection', async (req, res) => {
      try {
        const { email, provider, customHost, customPort } = req.body;

        if (!email) {
          return res.status(400).json({ error: 'email krävs för test' });
        }

        console.log(`Testing connection for: ${email}`);
        const testResult = await ConnectionTester.testConnection(email, provider, customHost, customPort);
        
        if (!testResult.success) {
          const suggestions = await ConnectionTester.suggestAlternatives(email);
          res.json({
            ...testResult,
            suggestions
          });
        } else {
          res.json(testResult);
        }
      } catch (error) {
        console.error('Connection test error:', error);
        res.status(500).json({ 
          error: error instanceof Error ? error.message : 'Okänt fel vid test' 
        });
      }
    });

    this.app.post('/api/delete-emails', async (req, res) => {
      try {
        const { connectionId, uids, mailbox = 'INBOX', moveToTrash = true } = req.body;

        if (!connectionId || !uids || !Array.isArray(uids)) {
          return res.status(400).json({ error: 'connectionId och uids (array) krävs' });
        }

        const client = this.clients.get(connectionId);
        if (!client) {
          return res.status(404).json({ error: `Anslutning '${connectionId}' hittades inte` });
        }

        console.log(`Deleting ${uids.length} emails from ${connectionId}`);

        if (moveToTrash) {
          // Try to move to trash first, fall back to permanent deletion
          try {
            await client.moveEmailsToTrash(uids, 'Trash', mailbox);
            res.json({ 
              success: true, 
              message: `${uids.length} e-post flyttade till papperskorgen`,
              method: 'moved_to_trash',
              count: uids.length
            });
          } catch (trashError) {
            console.log('Failed to move to trash, trying permanent deletion...');
            await client.deleteEmails(uids, mailbox);
            res.json({ 
              success: true, 
              message: `${uids.length} e-post permanent raderade`,
              method: 'permanently_deleted',
              count: uids.length
            });
          }
        } else {
          await client.deleteEmails(uids, mailbox);
          res.json({ 
            success: true, 
            message: `${uids.length} e-post permanent raderade`,
            method: 'permanently_deleted',
            count: uids.length
          });
        }
      } catch (error) {
        console.error('Delete emails error:', error);
        res.status(500).json({ 
          error: error instanceof Error ? error.message : 'Okänt fel vid radering av e-post' 
        });
      }
    });

    this.app.get('/api/status', (req, res) => {
      res.json({ 
        success: true, 
        message: 'MCP Email GUI Server körs',
        activeConnections: this.clients.size,
        port: this.port
      });
    });
  }

  private setupErrorHandling(): void {
    this.app.use((err: any, req: express.Request, res: express.Response, next: express.NextFunction) => {
      console.error('Express error:', err);
      res.status(500).json({ 
        error: 'Internt serverfel',
        details: err.message 
      });
    });

    this.app.use((req: express.Request, res: express.Response) => {
      res.status(404).json({ 
        error: 'Endpoint hittades inte',
        path: req.path 
      });
    });

    process.on('SIGINT', async () => {
      console.log('\nStänger ner servern...');
      await this.cleanup();
      process.exit(0);
    });
  }

  private async cleanup(): Promise<void> {
    console.log('Stänger alla e-postanslutningar...');
    for (const [id, client] of this.clients) {
      try {
        await client.disconnect();
        console.log(`Stängde anslutning: ${id}`);
      } catch (error) {
        console.error(`Fel vid stängning av ${id}:`, error);
      }
    }
    this.clients.clear();
  }

  public start(): void {
    this.app.listen(this.port, () => {
      console.log(`🚀 MCP Email GUI Server körs på http://localhost:${this.port}`);
      console.log(`📧 Hantera dina e-postanslutningar via webgränssnittet`);
      console.log(`🔗 Aktiva anslutningar: ${this.clients.size}`);
      console.log(`\n💡 Tryck Ctrl+C för att stoppa servern`);
    });
  }
}

// Start the server
const server = new EmailGUIServer(3623);
server.start();