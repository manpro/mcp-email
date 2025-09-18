import Imap from 'imap';
import { simpleParser } from 'mailparser';
import { EventEmitter } from 'events';
export class ImapEmailClient extends EventEmitter {
    imap = null;
    config;
    connected = false;
    constructor(config) {
        super();
        this.config = config;
    }
    async connect() {
        return new Promise((resolve, reject) => {
            console.log(`Attempting to connect to ${this.config.host}:${this.config.port}...`);
            this.imap = new Imap({
                host: this.config.host,
                port: this.config.port,
                user: this.config.user,
                password: this.config.password,
                tls: this.config.tls ?? true,
                tlsOptions: {
                    ...this.config.tlsOptions,
                    rejectUnauthorized: false // Allow self-signed certificates
                },
                authTimeout: this.config.authTimeout ?? 30000, // Increased timeout
                connTimeout: this.config.connTimeout ?? 30000, // Increased timeout
                keepalive: true,
                debug: console.log // Enable debug logging
            });
            // Set a custom timeout
            const timeoutId = setTimeout(() => {
                console.error('Connection timeout after 35 seconds');
                if (this.imap) {
                    this.imap.destroy();
                }
                reject(new Error(`Connection timeout to ${this.config.host}:${this.config.port}`));
            }, 35000);
            this.imap.once('ready', () => {
                clearTimeout(timeoutId);
                this.connected = true;
                console.log(`Successfully connected to ${this.config.host}`);
                resolve();
            });
            this.imap.once('error', (err) => {
                clearTimeout(timeoutId);
                this.connected = false;
                console.error(`IMAP connection error:`, err);
                reject(new Error(`IMAP Error: ${err.message || err}`));
            });
            this.imap.once('end', () => {
                clearTimeout(timeoutId);
                this.connected = false;
                console.log(`Connection ended to ${this.config.host}`);
                this.emit('disconnected');
            });
            this.imap.once('close', (hadError) => {
                clearTimeout(timeoutId);
                this.connected = false;
                console.log(`Connection closed to ${this.config.host}, hadError: ${hadError}`);
            });
            try {
                this.imap.connect();
            }
            catch (error) {
                clearTimeout(timeoutId);
                console.error('Failed to initiate connection:', error);
                reject(error);
            }
        });
    }
    async disconnect() {
        if (this.imap && this.connected) {
            this.imap.end();
            this.connected = false;
        }
    }
    async getMailboxes() {
        return new Promise((resolve, reject) => {
            if (!this.imap || !this.connected) {
                reject(new Error('Not connected to IMAP server'));
                return;
            }
            this.imap.getBoxes((err, boxes) => {
                if (err)
                    reject(err);
                else
                    resolve(boxes);
            });
        });
    }
    async openBox(boxName = 'INBOX', readOnly = true) {
        return new Promise((resolve, reject) => {
            if (!this.imap || !this.connected) {
                reject(new Error('Not connected to IMAP server'));
                return;
            }
            this.imap.openBox(boxName, readOnly, (err, box) => {
                if (err)
                    reject(err);
                else
                    resolve(box);
            });
        });
    }
    async deleteEmails(uids, boxName = 'INBOX') {
        return new Promise((resolve, reject) => {
            if (!this.imap || !this.connected) {
                reject(new Error('Not connected to IMAP server'));
                return;
            }
            // Open box in write mode
            this.openBox(boxName, false).then(() => {
                console.log(`Marking ${uids.length} emails for deletion...`);
                // Mark emails as deleted
                this.imap.addFlags(uids, '\\Deleted', (err) => {
                    if (err) {
                        reject(new Error(`Failed to mark emails as deleted: ${err.message}`));
                        return;
                    }
                    // Expunge to actually delete them
                    this.imap.expunge((expErr) => {
                        if (expErr) {
                            reject(new Error(`Failed to expunge deleted emails: ${expErr.message}`));
                            return;
                        }
                        console.log(`Successfully deleted ${uids.length} emails`);
                        resolve();
                    });
                });
            }).catch(reject);
        });
    }
    async moveEmailsToTrash(uids, trashFolder = 'Trash', boxName = 'INBOX') {
        return new Promise((resolve, reject) => {
            if (!this.imap || !this.connected) {
                reject(new Error('Not connected to IMAP server'));
                return;
            }
            // Open box in write mode
            this.openBox(boxName, false).then(() => {
                console.log(`Moving ${uids.length} emails to ${trashFolder}...`);
                // Move emails to trash folder
                this.imap.move(uids, trashFolder, (err) => {
                    if (err) {
                        reject(new Error(`Failed to move emails to trash: ${err.message}`));
                        return;
                    }
                    console.log(`Successfully moved ${uids.length} emails to ${trashFolder}`);
                    resolve();
                });
            }).catch(reject);
        });
    }
    async searchEmails(criteria = ['ALL'], boxName = 'INBOX') {
        return new Promise((resolve, reject) => {
            if (!this.imap || !this.connected) {
                reject(new Error('Not connected to IMAP server'));
                return;
            }
            this.openBox(boxName).then(() => {
                this.imap.search(criteria, (err, uids) => {
                    if (err)
                        reject(err);
                    else
                        resolve(uids);
                });
            }).catch(reject);
        });
    }
    async fetchEmails(uids, boxName = 'INBOX') {
        return new Promise((resolve, reject) => {
            if (!this.imap || !this.connected) {
                reject(new Error('Not connected to IMAP server'));
                return;
            }
            this.openBox(boxName).then(() => {
                const fetch = this.imap.fetch(uids, {
                    bodies: '',
                    struct: true,
                    markSeen: false
                });
                const emails = [];
                let processed = 0;
                fetch.on('message', (msg, seqno) => {
                    let buffer = '';
                    let attributes = null;
                    msg.on('body', (stream) => {
                        stream.on('data', (chunk) => {
                            buffer += chunk.toString('utf8');
                        });
                    });
                    msg.once('attributes', (attrs) => {
                        attributes = attrs;
                    });
                    msg.once('end', async () => {
                        try {
                            const parsed = await simpleParser(buffer);
                            const email = {
                                id: attributes.uid.toString(),
                                uid: attributes.uid,
                                subject: parsed.subject || '',
                                from: Array.isArray(parsed.from) ? parsed.from[0]?.text || '' : parsed.from?.text || '',
                                to: Array.isArray(parsed.to) ? parsed.to.map(addr => addr.text).filter(Boolean) : parsed.to?.text ? [parsed.to.text] : [],
                                date: parsed.date || new Date(),
                                body: parsed.html || parsed.text || '',
                                bodyText: parsed.text || '',
                                attachments: parsed.attachments?.map((att) => ({
                                    filename: att.filename || '',
                                    contentType: att.contentType || '',
                                    size: att.size || 0
                                })),
                                flags: attributes.flags || [],
                                folder: boxName
                            };
                            emails.push(email);
                            processed++;
                            if (processed === uids.length) {
                                resolve(emails);
                            }
                        }
                        catch (error) {
                            reject(error);
                        }
                    });
                });
                fetch.once('error', reject);
                fetch.once('end', () => {
                    if (processed === 0) {
                        resolve([]);
                    }
                });
            }).catch(reject);
        });
    }
    async getRecentEmails(count = 10, boxName = 'INBOX') {
        try {
            const uids = await this.searchEmails(['ALL'], boxName);
            const recentUids = uids.slice(-count);
            return await this.fetchEmails(recentUids, boxName);
        }
        catch (error) {
            throw error;
        }
    }
    isConnected() {
        return this.connected;
    }
}
//# sourceMappingURL=imap-client.js.map