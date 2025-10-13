/**
 * LLM Adapter - Provider-Agnostic Function Calling
 * Supports: OpenAI, Anthropic, Ollama, vLLM, LM Studio, etc.
 */

const axios = require('axios');

class LLMAdapter {
  constructor(provider, model, url) {
    this.provider = provider; // 'openai', 'anthropic', 'ollama', 'custom'
    this.model = model;
    this.url = url;
  }

  /**
   * Call LLM with tools (function calling)
   * Returns unified response format
   */
  async callWithTools(messages, tools, options = {}) {
    const { temperature = 0.1, maxTokens = 1000 } = options;

    console.log(`[LLM Adapter] Calling ${this.provider} (${this.model}) with ${tools.length} tools`);

    try {
      switch(this.provider) {
        case 'openai':
        case 'ollama':
        case 'vllm':
        case 'lmstudio':
          return await this.callOpenAIFormat(messages, tools, temperature, maxTokens);

        case 'anthropic':
          return await this.callClaudeFormat(messages, tools, temperature, maxTokens);

        default:
          // Try OpenAI format as default (most common)
          return await this.callOpenAIFormat(messages, tools, temperature, maxTokens);
      }
    } catch (error) {
      console.error(`[LLM Adapter] Error calling ${this.provider}:`, error.message);
      throw error;
    }
  }

  /**
   * OpenAI-compatible format (works with Ollama, vLLM, LM Studio, etc)
   */
  async callOpenAIFormat(messages, tools, temperature, maxTokens) {
    const requestBody = {
      model: this.model,
      messages,
      tools,
      temperature,
      max_tokens: maxTokens,
      stream: false
    };

    // GPT-OSS specific settings
    if (this.model.includes('gpt-oss')) {
      requestBody.tool_choice = "required"; // Force GPT-OSS to use tools
      requestBody.num_ctx = 8192; // Larger context for better tool understanding
    }

    console.log(`[LLM Adapter] Request body:`, JSON.stringify(requestBody, null, 2).substring(0, 500));

    const response = await axios.post(`${this.url}/v1/chat/completions`, requestBody, {
      timeout: 60000 // 60 second timeout
    });

    return this.parseOpenAIResponse(response.data);
  }

  /**
   * Anthropic Claude format
   */
  async callClaudeFormat(messages, tools, temperature, maxTokens) {
    // Convert OpenAI tools to Claude format
    const claudeTools = tools.map(t => ({
      name: t.function.name,
      description: t.function.description,
      input_schema: t.function.parameters
    }));

    const response = await axios.post(`${this.url}/v1/messages`, {
      model: this.model,
      messages,
      tools: claudeTools,
      temperature,
      max_tokens: maxTokens
    }, {
      headers: {
        'x-api-key': process.env.ANTHROPIC_API_KEY,
        'anthropic-version': '2023-06-01'
      },
      timeout: 60000
    });

    return this.parseClaudeResponse(response.data);
  }

  /**
   * Parse OpenAI-format response
   */
  parseOpenAIResponse(data) {
    const choice = data.choices[0];
    const message = choice.message;

    console.log('[LLM Adapter] Response:', JSON.stringify(message, null, 2));

    // Check if LLM called a tool
    if (message.tool_calls && message.tool_calls.length > 0) {
      const toolCall = message.tool_calls[0];

      // Extract reasoning content for GPT-OSS chain-of-thought
      const reasoning = message.reasoning_content || message.content || '';

      return {
        type: 'tool_call',
        toolCall: {
          name: toolCall.function.name,
          arguments: typeof toolCall.function.arguments === 'string'
            ? JSON.parse(toolCall.function.arguments)
            : toolCall.function.arguments
        },
        reasoning: reasoning,
        rawMessage: message.content || ''
      };
    }

    // GPT-OSS might put tool info in content
    // Try to extract tool call from reasoning_content
    if (message.reasoning_content) {
      console.log('[LLM Adapter] Found reasoning_content:', message.reasoning_content);
    }

    // No tool call, just text response
    return {
      type: 'text',
      content: message.content || message.reasoning_content || '',
      toolCall: null
    };
  }

  /**
   * Parse Claude-format response
   */
  parseClaudeResponse(data) {
    const content = data.content;

    // Check if Claude called a tool
    const toolUse = content.find(c => c.type === 'tool_use');

    if (toolUse) {
      return {
        type: 'tool_call',
        toolCall: {
          name: toolUse.name,
          arguments: toolUse.input
        },
        rawMessage: content.find(c => c.type === 'text')?.text || ''
      };
    }

    // No tool call, just text
    const textContent = content.find(c => c.type === 'text');

    return {
      type: 'text',
      content: textContent?.text || '',
      toolCall: null
    };
  }

  /**
   * Simple chat without tools
   */
  async chat(messages, options = {}) {
    const { temperature = 0.7, maxTokens = 500 } = options;

    const response = await axios.post(`${this.url}/v1/chat/completions`, {
      model: this.model,
      messages,
      temperature,
      max_tokens: maxTokens,
      stream: false
    }, {
      timeout: 30000
    });

    const choice = response.data.choices[0];
    return choice.message.content;
  }
}

/**
 * Command Name Mapper
 * Maps OpenAI function names to our internal command format
 */
class CommandMapper {
  /**
   * Convert function call to legacy [COMMAND] format
   * For backwards compatibility with existing parsers
   */
  static toLegacyFormat(functionName, args) {
    // Convert snake_case to SCREAMING_SNAKE_CASE
    const commandName = functionName.toUpperCase();

    // Build parameter string
    const params = Object.entries(args)
      .map(([key, value]) => `${key}="${value}"`)
      .join(' ');

    if (params) {
      return `[${commandName} ${params}]`;
    } else {
      return `[${commandName}]`;
    }
  }

  /**
   * Convert legacy [COMMAND] to function call format
   */
  static fromLegacyFormat(commandString) {
    const match = commandString.match(/\[(\w+)(?:\s+(.+))?\]/);

    if (!match) {
      return null;
    }

    const [, commandName, paramsString] = match;

    // Parse parameters
    const args = {};
    if (paramsString) {
      const paramMatches = paramsString.matchAll(/(\w+)="([^"]*)"/g);
      for (const [, key, value] of paramMatches) {
        args[key] = value;
      }
    }

    return {
      name: commandName.toLowerCase(),
      arguments: args
    };
  }
}

/**
 * Factory function to create LLM adapter from env variables or config
 */
function createLLMAdapter() {
  // Try to load from llm-config.json first
  try {
    const fs = require('fs');
    const path = require('path');
    const configPath = path.resolve(__dirname, 'llm-config.json');

    if (fs.existsSync(configPath)) {
      const config = JSON.parse(fs.readFileSync(configPath, 'utf8'));

      // Find highest priority enabled provider
      const providers = Object.entries(config.providers)
        .filter(([_, p]) => p.enabled)
        .sort((a, b) => a[1].priority - b[1].priority);

      if (providers.length > 0) {
        const [providerName, providerConfig] = providers[0];

        // Determine provider type from URL or model
        let providerType = 'ollama'; // default
        if (providerConfig.url.includes('anthropic')) {
          providerType = 'anthropic';
        } else if (providerConfig.model.includes('gpt')) {
          providerType = 'openai';
        }

        console.log(`[LLM Factory] Creating adapter from config: ${providerType}/${providerConfig.model} at ${providerConfig.url}`);

        return new LLMAdapter(providerType, providerConfig.model, providerConfig.url);
      }
    }
  } catch (error) {
    console.log(`[LLM Factory] Config loading failed, using env vars:`, error.message);
  }

  // Fallback to environment variables
  const provider = process.env.LLM_PROVIDER || 'ollama';
  const model = process.env.LLM_MODEL || 'gpt-oss:20b';
  const url = process.env.LLM_URL || 'http://172.17.0.1:8085';

  console.log(`[LLM Factory] Creating adapter from env: ${provider}/${model} at ${url}`);

  return new LLMAdapter(provider, model, url);
}

// CommonJS export
module.exports = {
  LLMAdapter,
  CommandMapper,
  createLLMAdapter
};
