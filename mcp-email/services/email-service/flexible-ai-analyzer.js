const axios = require('axios');
const fs = require('fs');
const path = require('path');

class FlexibleEmailAIAnalyzer {
  constructor(configPath = './llm-config.json') {
    this.loadConfig(configPath);
    this.initializeProviders();
  }

  loadConfig(configPath) {
    try {
      const configFile = path.resolve(configPath);
      if (fs.existsSync(configFile)) {
        const configData = fs.readFileSync(configFile, 'utf8');
        this.config = JSON.parse(configData);
        console.log('✅ LLM config loaded from:', configFile);
      } else {
        // Default fallback config
        this.config = {
          providers: {
            mistral: {
              name: "Mistral 7B",
              url: process.env.LLM_URL || "http://localhost:1234",
              model: process.env.LLM_MODEL || "mistral:7b",
              endpoint: "/v1/chat/completions",
              temperature: 0.4,
              max_tokens: 250,
              enabled: true,
              priority: 1
            }
          },
          default: "mistral",
          fallback: { enabled: true, maxRetries: 2, retryDelay: 1000 },
          ruleBasedFallback: { enabled: true, useWhenAllFail: true }
        };
        console.log('⚠️ Config file not found, using default config');
      }
    } catch (error) {
      console.error('Error loading config:', error);
      this.config = this.getDefaultConfig();
    }
  }

  initializeProviders() {
    // Sort providers by priority
    this.sortedProviders = Object.entries(this.config.providers)
      .filter(([_, provider]) => provider.enabled)
      .sort((a, b) => a[1].priority - b[1].priority)
      .map(([key, provider]) => ({ key, ...provider }));

    console.log('📊 Active LLM providers:');
    this.sortedProviders.forEach(p => {
      console.log(`  ${p.priority}. ${p.name} (${p.url})`);
    });
  }

  async classifyEmail(email) {
    const prompt = this.buildPrompt(email);

    // Try each provider in priority order
    for (const provider of this.sortedProviders) {
      try {
        console.log(`🤖 Trying ${provider.name}...`);
        const result = await this.callProvider(provider, prompt);
        if (result) {
          console.log(`✅ Success with ${provider.name}`);
          return { ...result, provider: provider.name };
        }
      } catch (error) {
        console.log(`❌ ${provider.name} failed:`, error.message);
        continue;
      }
    }

    // If all providers fail, use rule-based fallback
    if (this.config.ruleBasedFallback?.enabled) {
      console.log('⚠️ All LLM providers failed, using rule-based classification');
      return this.ruleBasedClassification(email);
    }

    throw new Error('All classification methods failed');
  }

  buildPrompt(email) {
    return `Analyze this email and return JSON with classification:

From: ${email.from || 'Unknown'}
Subject: ${email.subject || 'No Subject'}
Content: ${(email.text || email.html || '').substring(0, 500)}

Return JSON only:
{
  "priority": "high/medium/low",
  "category": "work/personal/newsletter/spam/promotional",
  "sentiment": "positive/neutral/negative",
  "actionRequired": true/false,
  "summary": "1-2 sentence summary",
  "keyTopics": ["topic1", "topic2"]
}`;
  }

  async callProvider(provider, prompt) {
    const timeout = provider.timeout || 10000;

    try {
      if (provider.format === 'ollama') {
        return await this.callOllama(provider, prompt, timeout);
      } else {
        return await this.callOpenAICompatible(provider, prompt, timeout);
      }
    } catch (error) {
      if (this.config.fallback?.enabled && this.config.fallback.maxRetries > 0) {
        console.log(`⏳ Retrying ${provider.name} after ${this.config.fallback.retryDelay}ms...`);
        await new Promise(resolve => setTimeout(resolve, this.config.fallback.retryDelay));

        // One retry attempt
        try {
          if (provider.format === 'ollama') {
            return await this.callOllama(provider, prompt, timeout);
          } else {
            return await this.callOpenAICompatible(provider, prompt, timeout);
          }
        } catch (retryError) {
          throw retryError;
        }
      }
      throw error;
    }
  }

  async callOpenAICompatible(provider, prompt, timeout) {
    const response = await axios.post(
      `${provider.url}${provider.endpoint}`,
      {
        model: provider.model,
        messages: [
          {
            role: 'system',
            content: 'You are an email classifier. Always return valid JSON only, no explanations.'
          },
          {
            role: 'user',
            content: prompt
          }
        ],
        temperature: provider.temperature,
        max_tokens: provider.max_tokens,
        stream: false
      },
      {
        timeout,
        headers: {
          'Content-Type': 'application/json'
        }
      }
    );

    const aiResponse = response.data.choices[0].message.content;
    return this.parseAIResponse(aiResponse);
  }

  async callOllama(provider, prompt, timeout) {
    const response = await axios.post(
      `${provider.url}${provider.endpoint}`,
      {
        model: provider.model,
        messages: [
          {
            role: 'system',
            content: 'You are an email classifier. Always return valid JSON only, no explanations.'
          },
          {
            role: 'user',
            content: prompt
          }
        ],
        stream: false,
        options: {
          temperature: provider.temperature,
          num_predict: provider.max_tokens
        }
      },
      {
        timeout,
        headers: {
          'Content-Type': 'application/json'
        }
      }
    );

    const aiResponse = response.data.message?.content || response.data.response;
    return this.parseAIResponse(aiResponse);
  }

  parseAIResponse(aiResponse) {
    try {
      // Try to extract JSON from the response
      const jsonMatch = aiResponse.match(/\{[\s\S]*?\}/);
      if (jsonMatch) {
        const parsed = JSON.parse(jsonMatch[0]);

        // Validate and normalize the response
        return {
          priority: parsed.priority || 'medium',
          category: parsed.category || 'other',
          sentiment: parsed.sentiment || 'neutral',
          actionRequired: parsed.actionRequired || false,
          summary: parsed.summary || 'Email processed',
          keyTopics: parsed.keyTopics || []
        };
      }
    } catch (error) {
      console.error('Failed to parse AI response:', error);
    }
    return null;
  }

  ruleBasedClassification(email) {
    const subject = (email.subject || '').toLowerCase();
    const from = (email.from || '').toLowerCase();
    const text = (email.text || email.html || '').toLowerCase();
    const combined = `${subject} ${from} ${text}`;

    // Priority detection
    let priority = 'low';
    if (combined.match(/urgent|asap|deadline|important|critical|emergency/)) {
      priority = 'high';
    } else if (combined.match(/meeting|review|feedback|project|task/)) {
      priority = 'medium';
    }

    // Category detection
    let category = 'other';
    if (combined.match(/newsletter|unsubscribe|weekly|monthly|digest/)) {
      category = 'newsletter';
    } else if (combined.match(/invoice|payment|order|receipt|shipping/)) {
      category = 'work';
    } else if (from.match(/noreply|no-reply|notification|automated/)) {
      category = 'promotional';
    } else if (combined.match(/spam|winner|claim|prize|viagra|casino/)) {
      category = 'spam';
    } else if (combined.match(/meeting|project|deadline|work|office|team/)) {
      category = 'work';
    } else if (combined.match(/family|friend|birthday|vacation|personal/)) {
      category = 'personal';
    }

    // Action required detection
    const actionRequired = combined.match(/please|review|approve|confirm|rsvp|respond|reply|action/i) !== null;

    // Simple sentiment
    let sentiment = 'neutral';
    if (combined.match(/thank|great|excellent|happy|pleased|congrat/)) {
      sentiment = 'positive';
    } else if (combined.match(/sorry|apologize|issue|problem|error|fail|wrong/)) {
      sentiment = 'negative';
    }

    // Generate summary
    const summary = subject ?
      `Email about: ${email.subject.substring(0, 100)}` :
      'Email content classified';

    return {
      priority,
      category,
      sentiment,
      actionRequired,
      summary,
      keyTopics: [],
      provider: 'rule-based'
    };
  }

  // Test connectivity to a specific provider
  async testProvider(providerKey) {
    const provider = this.config.providers[providerKey];
    if (!provider) {
      return { success: false, error: 'Provider not found' };
    }

    try {
      const testEmail = {
        from: 'test@example.com',
        subject: 'Test Email',
        text: 'This is a test email for connectivity check.'
      };

      const result = await this.callProvider(provider, this.buildPrompt(testEmail));
      return {
        success: true,
        provider: provider.name,
        url: provider.url,
        model: provider.model,
        result
      };
    } catch (error) {
      return {
        success: false,
        provider: provider.name,
        url: provider.url,
        error: error.message
      };
    }
  }

  // Test all configured providers
  async testAllProviders() {
    console.log('🧪 Testing all configured LLM providers...\n');
    const results = [];

    for (const [key, provider] of Object.entries(this.config.providers)) {
      console.log(`Testing ${provider.name}...`);
      const result = await this.testProvider(key);
      results.push(result);

      if (result.success) {
        console.log(`✅ ${provider.name}: OK`);
      } else {
        console.log(`❌ ${provider.name}: ${result.error}`);
      }
    }

    return results;
  }

  // Update provider configuration at runtime
  updateProvider(providerKey, updates) {
    if (this.config.providers[providerKey]) {
      Object.assign(this.config.providers[providerKey], updates);
      this.initializeProviders();
      console.log(`✅ Updated ${providerKey} configuration`);
      return true;
    }
    return false;
  }

  // Enable/disable a provider
  toggleProvider(providerKey, enabled) {
    if (this.config.providers[providerKey]) {
      this.config.providers[providerKey].enabled = enabled;
      this.initializeProviders();
      console.log(`${enabled ? '✅ Enabled' : '🚫 Disabled'} ${providerKey}`);
      return true;
    }
    return false;
  }

  // Get current configuration
  getConfig() {
    return {
      providers: this.config.providers,
      activeProviders: this.sortedProviders,
      default: this.config.default,
      fallback: this.config.fallback
    };
  }
}

module.exports = FlexibleEmailAIAnalyzer;