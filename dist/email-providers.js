export const EmailProviders = {
    outlook: {
        name: 'Microsoft Outlook/Exchange',
        getConfig: (email, password) => ({
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
        getConfig: (email, password) => ({
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
        getConfig: (email, password) => {
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
        getConfig: (email, password) => ({
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
        getConfig: (email, password) => ({
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
        getConfig: (email, password) => {
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
export function detectProvider(email) {
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
export function createImapConfig(email, password, provider, customHost, customPort) {
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
//# sourceMappingURL=email-providers.js.map