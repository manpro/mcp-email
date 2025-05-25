import { exec } from 'child_process';
import { promisify } from 'util';
import { existsSync } from 'fs';
import path from 'path';

const execAsync = promisify(exec);

interface MKDocsRequest {
  topic?: string;
  filename?: string;
  content?: string;
}

interface MKDocsStatusResult {
  status: string;
  version?: string;
  project_path: string;
  venv_active: boolean;
  config_exists: boolean;
  docs_dir_exists: boolean;
  site_dir_exists: boolean;
}

interface MKDocsBuildResult {
  status: string;
  duration: string;
  site_size?: string;
  file_count?: number;
  output?: string;
  error?: string;
}

interface MKDocsGenerateResult {
  status: string;
  filename: string;
  content_length: number;
  file_path: string;
  error?: string;
}

export class MKDocsAgent {
  private readonly PROJECT_PATH = '/home/micke/claude-env/docs-site';
  private readonly VENV_PATH = path.join(this.PROJECT_PATH, '.venv', 'bin');
  
  private async getMKDocsCommand(): Promise<string> {
    const venvMkdocs = path.join(this.VENV_PATH, 'mkdocs');
    
    if (existsSync(venvMkdocs)) {
      return venvMkdocs;
    }
    
    return 'mkdocs';
  }

  async getStatus(): Promise<MKDocsStatusResult> {
    try {
      const mkdocsCmd = await this.getMKDocsCommand();
      const { stdout } = await execAsync(`${mkdocsCmd} --version`, { 
        cwd: this.PROJECT_PATH,
        timeout: 10000 
      });
      
      const configExists = existsSync(path.join(this.PROJECT_PATH, 'mkdocs.yml'));
      const docsExists = existsSync(path.join(this.PROJECT_PATH, 'docs'));
      const siteExists = existsSync(path.join(this.PROJECT_PATH, 'site'));
      const venvActive = existsSync(this.VENV_PATH);
      
      return {
        status: 'healthy',
        version: stdout.trim(),
        project_path: this.PROJECT_PATH,
        venv_active: venvActive,
        config_exists: configExists,
        docs_dir_exists: docsExists,
        site_dir_exists: siteExists
      };
    } catch (error) {
      return {
        status: 'error',
        project_path: this.PROJECT_PATH,
        venv_active: existsSync(this.VENV_PATH),
        config_exists: existsSync(path.join(this.PROJECT_PATH, 'mkdocs.yml')),
        docs_dir_exists: existsSync(path.join(this.PROJECT_PATH, 'docs')),
        site_dir_exists: existsSync(path.join(this.PROJECT_PATH, 'site'))
      };
    }
  }

  async buildSite(): Promise<MKDocsBuildResult> {
    const startTime = Date.now();
    
    try {
      const mkdocsCmd = await this.getMKDocsCommand();
      const { stdout, stderr } = await execAsync(`${mkdocsCmd} build --clean`, {
        cwd: this.PROJECT_PATH,
        timeout: 60000
      });
      
      const duration = ((Date.now() - startTime) / 1000).toFixed(2);
      
      // Try to get site size
      let siteSize = '';
      let fileCount = 0;
      
      try {
        const siteDir = path.join(this.PROJECT_PATH, 'site');
        if (existsSync(siteDir)) {
          const { stdout: duOutput } = await execAsync(`du -sh "${siteDir}"`, { timeout: 5000 });
          siteSize = duOutput.split('\t')[0];
          
          const { stdout: countOutput } = await execAsync(`find "${siteDir}" -type f | wc -l`, { timeout: 5000 });
          fileCount = parseInt(countOutput.trim());
        }
      } catch {
        // Size calculation failed, continue without it
      }
      
      return {
        status: 'success',
        duration: `${duration}s`,
        site_size: siteSize,
        file_count: fileCount,
        output: stdout + stderr
      };
    } catch (error) {
      const duration = ((Date.now() - startTime) / 1000).toFixed(2);
      return {
        status: 'error',
        duration: `${duration}s`,
        error: error instanceof Error ? error.message : String(error)
      };
    }
  }

  async generateContent(request: MKDocsRequest): Promise<MKDocsGenerateResult> {
    const { topic = 'documentation', filename, content } = request;
    
    if (content) {
      // Use provided content
      const targetFilename = filename || `${topic.toLowerCase().replace(/\s+/g, '-')}.md`;
      const filePath = path.join(this.PROJECT_PATH, 'docs', targetFilename);
      
      try {
        const fs = require('fs').promises;
        await fs.writeFile(filePath, content, 'utf8');
        
        return {
          status: 'success',
          filename: targetFilename,
          content_length: content.length,
          file_path: filePath
        };
      } catch (error) {
        return {
          status: 'error',
          filename: targetFilename,
          content_length: 0,
          file_path: filePath,
          error: error instanceof Error ? error.message : String(error)
        };
      }
    }
    
    // Generate template content
    const targetFilename = filename || `${topic.toLowerCase().replace(/\s+/g, '-')}.md`;
    const templateContent = `# ${topic.charAt(0).toUpperCase() + topic.slice(1)}

## Overview

This section covers ${topic}.

## Getting Started

To get started with ${topic}:

1. First step
2. Second step
3. Third step

## Examples

Here are some examples:

\`\`\`bash
# Example command
echo "Hello ${topic}"
\`\`\`

## References

- [Documentation](https://example.com)
- [API Reference](https://example.com/api)

---
*Generated by MKDocs Agent on ${new Date().toISOString()}*
`;
    
    const filePath = path.join(this.PROJECT_PATH, 'docs', targetFilename);
    
    try {
      const fs = require('fs').promises;
      await fs.writeFile(filePath, templateContent, 'utf8');
      
      return {
        status: 'success',
        filename: targetFilename,
        content_length: templateContent.length,
        file_path: filePath
      };
    } catch (error) {
      return {
        status: 'error',
        filename: targetFilename,
        content_length: 0,
        file_path: filePath,
        error: error instanceof Error ? error.message : String(error)
      };
    }
  }
}

export const mkdocsAgent = new MKDocsAgent();