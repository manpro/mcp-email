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
export declare class ConnectionTester {
    static testConnection(email: string, provider?: string, customHost?: string, customPort?: number): Promise<ConnectionTestResult>;
    private static testTcpConnection;
    private static testTlsConnection;
    private static testImapGreeting;
    static suggestAlternatives(email: string): Promise<string[]>;
}
//# sourceMappingURL=connection-tester.d.ts.map