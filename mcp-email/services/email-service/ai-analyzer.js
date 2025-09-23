const axios = require('axios');

class EmailAIAnalyzer {
  constructor(gptOssUrl = 'http://172.16.16.148:8085') {
    this.gptOssUrl = gptOssUrl;
  }

  async classifyEmail(email) {
    const prompt = `Analyze this email and return JSON with classification:

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

    try {
      const response = await axios.post(`${this.gptOssUrl}/v1/chat/completions`, {
        model: 'gpt-oss:20b',
        messages: [
          {
            role: 'system',
            content: 'You are an email classifier. Always return valid JSON only.'
          },
          {
            role: 'user',
            content: prompt
          }
        ],
        temperature: 0.3,
        max_tokens: 200
      });

      const aiResponse = response.data.choices[0].message.content;

      // Extract JSON from response
      const jsonMatch = aiResponse.match(/\{[\s\S]*?\}/);
      if (jsonMatch) {
        return JSON.parse(jsonMatch[0]);
      }

      return {
        priority: 'medium',
        category: 'unknown',
        sentiment: 'neutral',
        actionRequired: false,
        summary: 'Could not analyze email',
        keyTopics: []
      };
    } catch (error) {
      console.error('AI Analysis error:', error.message);
      return {
        priority: 'medium',
        category: 'unknown',
        sentiment: 'neutral',
        actionRequired: false,
        summary: 'AI analysis unavailable',
        keyTopics: [],
        error: error.message
      };
    }
  }

  async generateReply(email, replyType = 'professional') {
    const prompt = `Generate a ${replyType} reply to this email:

Original Email:
From: ${email.from}
Subject: ${email.subject}
Content: ${(email.text || '').substring(0, 1000)}

Generate a concise, appropriate reply.`;

    try {
      const response = await axios.post(`${this.gptOssUrl}/v1/chat/completions`, {
        model: 'gpt-oss:20b',
        messages: [
          {
            role: 'system',
            content: `You are a helpful email assistant. Write ${replyType} email replies.`
          },
          {
            role: 'user',
            content: prompt
          }
        ],
        temperature: 0.7,
        max_tokens: 300
      });

      return response.data.choices[0].message.content;
    } catch (error) {
      console.error('Reply generation error:', error.message);
      return null;
    }
  }

  async summarizeThread(emails) {
    const threadContent = emails.map(e =>
      `From: ${e.from}\nDate: ${e.date}\nContent: ${(e.text || '').substring(0, 200)}`
    ).join('\n---\n');

    const prompt = `Summarize this email thread concisely:

${threadContent}

Provide:
1. Main topic
2. Key decisions/actions
3. Next steps`;

    try {
      const response = await axios.post(`${this.gptOssUrl}/v1/chat/completions`, {
        model: 'gpt-oss:20b',
        messages: [
          {
            role: 'system',
            content: 'You are an email thread summarizer. Be concise.'
          },
          {
            role: 'user',
            content: prompt
          }
        ],
        temperature: 0.3,
        max_tokens: 200
      });

      return response.data.choices[0].message.content;
    } catch (error) {
      console.error('Thread summary error:', error.message);
      return 'Summary unavailable';
    }
  }
}

module.exports = EmailAIAnalyzer;