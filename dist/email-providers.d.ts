import { ImapConfig } from './imap-client.js';
export interface EmailProvider {
    name: string;
    getConfig(email: string, password: string): ImapConfig;
}
export declare const EmailProviders: Record<string, EmailProvider>;
export declare function detectProvider(email: string): string;
export declare function createImapConfig(email: string, password: string, provider?: string, customHost?: string, customPort?: number): ImapConfig;
//# sourceMappingURL=email-providers.d.ts.map