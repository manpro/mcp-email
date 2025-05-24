import { execSync } from 'child_process';

interface ClaudeCodePromptRequest {
  input: string;
  timeout?: number;
}

interface ClaudeCodePromptResponse {
  output: string;
}

export class ClaudeCodePromptAgent {
  
  async processPrompt(request: ClaudeCodePromptRequest): Promise<ClaudeCodePromptResponse> {
    const { input, timeout = 60000 } = request;

    if (!input || typeof input !== 'string' || input.trim().length === 0) {
      return { output: 'ERROR: Invalid input. Expected non-empty string with prompt.' };
    }

    try {
      console.log(`[${new Date().toISOString()}] Claude Code prompt: "${input.substring(0, 100)}..."`);

      // Clean and prepare the prompt
      const cleanedPrompt = input.trim().replace(/"/g, '\\"');
      
      // Execute Claude Code with the prompt
      // Using npx to ensure we get the globally installed version
      const command = `npx @anthropic-ai/claude-code --print "${cleanedPrompt}"`;
      
      console.log(`[${new Date().toISOString()}] Executing: ${command}`);
      
      const output = execSync(command, {
        encoding: 'utf8',
        timeout: timeout,
        maxBuffer: 1024 * 1024 * 10, // 10MB buffer for large responses
        cwd: process.cwd(),
        env: {
          ...process.env,
          // Ensure non-interactive mode
          CI: 'true',
          TERM: 'dumb'
        }
      });

      // Clean the output - remove ANSI codes and extra whitespace
      const cleanedOutput = output
        .replace(/\x1b\[[0-9;]*m/g, '') // Remove ANSI color codes
        .replace(/\r\n/g, '\n')         // Normalize line endings
        .trim();

      if (!cleanedOutput) {
        return { output: 'ERROR: Claude Code returned empty response. Try rephrasing your prompt.' };
      }

      console.log(`[${new Date().toISOString()}] Claude Code response length: ${cleanedOutput.length} chars`);
      
      return { output: cleanedOutput };

    } catch (error: any) {
      console.error(`[${new Date().toISOString()}] Claude Code error:`, error);
      
      if (error.code === 'ETIMEDOUT') {
        return { output: 'ERROR: Claude Code request timed out. Try a simpler prompt or increase timeout.' };
      }
      
      if (error.status && error.stderr) {
        const stderrOutput = error.stderr.toString().trim();
        return { output: `ERROR: Claude Code failed with exit code ${error.status}: ${stderrOutput}` };
      }
      
      if (error.message) {
        return { output: `ERROR: Claude Code execution failed: ${error.message}` };
      }
      
      return { output: 'ERROR: Unknown error occurred while executing Claude Code.' };
    }
  }
}

// Export singleton instance
export const claudeCodePromptAgent = new ClaudeCodePromptAgent();