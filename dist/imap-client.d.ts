import { EventEmitter } from 'events';
export interface ImapConfig {
    host: string;
    port: number;
    user: string;
    password: string;
    tls?: boolean;
    tlsOptions?: any;
    authTimeout?: number;
    connTimeout?: number;
}
export interface EmailMessage {
    id: string;
    uid: number;
    subject: string;
    from: string;
    to: string[];
    date: Date;
    body: string;
    bodyText?: string;
    attachments?: Array<{
        filename: string;
        contentType: string;
        size: number;
    }>;
    flags: string[];
    folder: string;
}
export declare class ImapEmailClient extends EventEmitter {
    private imap;
    private config;
    private connected;
    constructor(config: ImapConfig);
    connect(): Promise<void>;
    disconnect(): Promise<void>;
    getMailboxes(): Promise<any>;
    openBox(boxName?: string, readOnly?: boolean): Promise<any>;
    deleteEmails(uids: number[], boxName?: string): Promise<void>;
    moveEmailsToTrash(uids: number[], trashFolder?: string, boxName?: string): Promise<void>;
    searchEmails(criteria?: any[], boxName?: string): Promise<number[]>;
    fetchEmails(uids: number[], boxName?: string): Promise<EmailMessage[]>;
    getRecentEmails(count?: number, boxName?: string): Promise<EmailMessage[]>;
    isConnected(): boolean;
}
//# sourceMappingURL=imap-client.d.ts.map