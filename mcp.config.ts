import express, { Request, Response } from 'express';
import { browserReadAgent } from './agents/browser-read';
import { claudeCodePromptAgent } from './agents/claude-code-prompt';
import { mkdocsAgent } from './agents/mkdocs-agent';

interface BrowserReadRequest {
  url: string;
  selector?: string;
  timeout?: number;
}

interface ClaudeCodePromptRequest {
  input: string;
  timeout?: number;
}

interface MKDocsRequest {
  topic?: string;
  filename?: string;
  content?: string;
}

export function registerBrowserReadAgent(app: express.Application): void {
  app.post('/agent/browser-read', async (req: Request, res: Response) => {
    const startTime = Date.now();
    
    try {
      const { url, selector = 'h1', timeout = 30000 }: BrowserReadRequest = req.body;
      
      console.log(`[${new Date().toISOString()}] Browser read request: ${url} (selector: ${selector})`);
      
      if (!url || typeof url !== 'string' || url.trim().length === 0) {
        console.log(`[${new Date().toISOString()}] Invalid URL: ${JSON.stringify(url)}`);
        return res.status(400).json({
          error: 'Invalid URL. Expected non-empty string starting with http:// or https://'
        });
      }

      const result = await browserReadAgent.readPage({
        url: url.trim(),
        selector: selector || 'h1',
        timeout: timeout || 30000
      });
      
      const duration = Date.now() - startTime;
      
      console.log(`[${new Date().toISOString()}] Browser read completed in ${duration}ms`);
      
      res.json({
        output: result.output,
        metadata: {
          url: url.trim(),
          selector: selector || 'h1',
          execution_time_ms: duration,
          timestamp: new Date().toISOString()
        }
      });
      
    } catch (error) {
      const duration = Date.now() - startTime;
      console.error(`[${new Date().toISOString()}] Browser read error after ${duration}ms:`, error);
      
      if (error instanceof Error) {
        return res.status(500).json({
          error: `Browser read failed: ${error.message}`
        });
      }
      
      res.status(500).json({
        error: 'Internal server error during browser read'
      });
    }
  });
}

export function registerClaudeCodePromptAgent(app: express.Application): void {
  app.post('/agent/claude-code-prompt', async (req: Request, res: Response) => {
    const startTime = Date.now();
    
    try {
      const { input, timeout = 60000 }: ClaudeCodePromptRequest = req.body;
      
      console.log(`[${new Date().toISOString()}] Claude Code prompt request: "${input?.substring(0, 100)}..."`);
      
      if (!input || typeof input !== 'string' || input.trim().length === 0) {
        console.log(`[${new Date().toISOString()}] Invalid input: ${JSON.stringify(input)}`);
        return res.status(400).json({
          error: 'Invalid input. Expected non-empty string with prompt for Claude Code'
        });
      }

      const result = await claudeCodePromptAgent.processPrompt({
        input: input.trim(),
        timeout: timeout || 60000
      });
      
      const duration = Date.now() - startTime;
      
      console.log(`[${new Date().toISOString()}] Claude Code prompt completed in ${duration}ms`);
      
      res.json({
        output: result.output,
        metadata: {
          prompt: input.trim().substring(0, 200) + (input.trim().length > 200 ? '...' : ''),
          execution_time_ms: duration,
          timestamp: new Date().toISOString()
        }
      });
      
    } catch (error) {
      const duration = Date.now() - startTime;
      console.error(`[${new Date().toISOString()}] Claude Code prompt error after ${duration}ms:`, error);
      
      if (error instanceof Error) {
        return res.status(500).json({
          error: `Claude Code prompt failed: ${error.message}`
        });
      }
      
      res.status(500).json({
        error: 'Internal server error during Claude Code prompt'
      });
    }
  });
}

export function registerMKDocsAgent(app: express.Application): void {
  // MKDocs Status endpoint
  app.get('/agent/mkdocs-status', async (req: Request, res: Response) => {
    const startTime = Date.now();
    
    try {
      console.log(`[${new Date().toISOString()}] MKDocs status request`);
      
      const result = await mkdocsAgent.getStatus();
      const duration = Date.now() - startTime;
      
      console.log(`[${new Date().toISOString()}] MKDocs status completed in ${duration}ms`);
      
      res.json({
        output: result,
        metadata: {
          execution_time_ms: duration,
          timestamp: new Date().toISOString()
        }
      });
      
    } catch (error) {
      const duration = Date.now() - startTime;
      console.error(`[${new Date().toISOString()}] MKDocs status error after ${duration}ms:`, error);
      
      res.status(500).json({
        error: error instanceof Error ? error.message : 'Internal server error'
      });
    }
  });

  // MKDocs Build endpoint
  app.post('/agent/mkdocs-build', async (req: Request, res: Response) => {
    const startTime = Date.now();
    
    try {
      console.log(`[${new Date().toISOString()}] MKDocs build request`);
      
      const result = await mkdocsAgent.buildSite();
      const duration = Date.now() - startTime;
      
      console.log(`[${new Date().toISOString()}] MKDocs build completed in ${duration}ms`);
      
      res.json({
        output: result,
        metadata: {
          execution_time_ms: duration,
          timestamp: new Date().toISOString()
        }
      });
      
    } catch (error) {
      const duration = Date.now() - startTime;
      console.error(`[${new Date().toISOString()}] MKDocs build error after ${duration}ms:`, error);
      
      res.status(500).json({
        error: error instanceof Error ? error.message : 'Internal server error'
      });
    }
  });

  // MKDocs Generate endpoint
  app.post('/agent/mkdocs-generate', async (req: Request, res: Response) => {
    const startTime = Date.now();
    
    try {
      const { topic, filename, content }: MKDocsRequest = req.body;
      
      console.log(`[${new Date().toISOString()}] MKDocs generate request: topic="${topic}", filename="${filename}"`);
      
      const result = await mkdocsAgent.generateContent({ topic, filename, content });
      const duration = Date.now() - startTime;
      
      console.log(`[${new Date().toISOString()}] MKDocs generate completed in ${duration}ms`);
      
      res.json({
        output: result,
        metadata: {
          topic: topic || 'documentation',
          filename: filename || 'auto-generated',
          execution_time_ms: duration,
          timestamp: new Date().toISOString()
        }
      });
      
    } catch (error) {
      const duration = Date.now() - startTime;
      console.error(`[${new Date().toISOString()}] MKDocs generate error after ${duration}ms:`, error);
      
      res.status(500).json({
        error: error instanceof Error ? error.message : 'Internal server error'
      });
    }
  });
}

// Health check endpoint
export function registerHealthCheck(app: express.Application): void {
  app.get('/health', (req: Request, res: Response) => {
    res.json({
      status: 'healthy',
      timestamp: new Date().toISOString(),
      agents: ['browser-read', 'gitea-create-issue', 'pg-query', 'weaviate-query', 'claude-code-prompt', 'mkdocs-status', 'mkdocs-build', 'mkdocs-generate']
    });
  });
}