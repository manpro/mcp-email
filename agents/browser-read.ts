import { chromium, Browser, Page } from 'playwright';
import { exec } from 'child_process';
import { promisify } from 'util';

const execAsync = promisify(exec);

interface BrowserReadRequest {
  url: string;
  selector?: string;
  timeout?: number;
}

interface BrowserReadResponse {
  output: string;
}

export class BrowserReadAgent {
  async ensurePlaywrightInstalled(): Promise<void> {
    try {
      await import('playwright');
    } catch (error) {
      console.log('Installing Playwright...');
      await execAsync('npx playwright install chromium');
    }
  }

  async readPage(request: BrowserReadRequest): Promise<BrowserReadResponse> {
    const { url, selector = 'h1', timeout = 30000 } = request;

    if (!url || typeof url !== 'string') {
      throw new Error('Invalid URL provided');
    }

    if (!url.match(/^https?:\/\//)) {
      throw new Error('URL must start with http:// or https://');
    }

    await this.ensurePlaywrightInstalled();

    // Create browser instance for each request
    const browser = await chromium.launch({
      headless: true,
      args: [
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-dev-shm-usage',
        '--disable-accelerated-2d-canvas',
        '--no-first-run',
        '--no-zygote',
        '--single-process',
        '--disable-gpu'
      ]
    });

    const page: Page = await browser.newPage();
    
    try {
      // Set user agent to avoid bot detection
      await page.setExtraHTTPHeaders({
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
      });
      
      // Navigate to URL with timeout
      await page.goto(url, { 
        waitUntil: 'domcontentloaded',
        timeout: timeout 
      });

      // Wait for selector to be present
      await page.waitForSelector(selector, { timeout: 10000 });

      // Extract text content
      const elements = await page.$$(selector);
      
      if (elements.length === 0) {
        throw new Error(`No elements found with selector: ${selector}`);
      }

      const textContent = await Promise.all(
        elements.map(element => element.textContent())
      );

      const output = textContent
        .filter(text => text && text.trim().length > 0)
        .map(text => text!.trim())
        .join('\n');

      if (!output) {
        throw new Error(`No text content found in elements matching: ${selector}`);
      }

      return { output };

    } catch (error) {
      if (error instanceof Error) {
        throw new Error(`Browser read failed: ${error.message}`);
      }
      throw new Error('Unknown browser error occurred');
    } finally {
      await page.close();
      await browser.close();
    }
  }
}

// Export singleton instance
export const browserReadAgent = new BrowserReadAgent();