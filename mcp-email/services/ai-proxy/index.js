const express = require('express');
const cors = require('cors');
const axios = require('axios');

const app = express();
const PORT = process.env.PORT || 3003;

// GPT-OSS external service URL
const GPT_OSS_URL = process.env.GPT_OSS_URL || 'http://localhost:8085';

app.use(cors());
app.use(express.json());

// Health check
app.get('/health', (req, res) => {
  res.json({
    status: 'healthy',
    service: 'ai-proxy',
    gptOssUrl: GPT_OSS_URL
  });
});

// Email classification
app.post('/classify', async (req, res) => {
  try {
    const { email } = req.body;

    // Call GPT-OSS for classification
    const response = await axios.post(`${GPT_OSS_URL}/v1/chat/completions`, {
      model: 'gpt-oss:20b',
      messages: [{
        role: 'system',
        content: 'You are an email classifier. Classify emails into categories: work, personal, newsletter, spam, important. Also assign priority: high, medium, low. Return JSON format: {"category": "...", "priority": "...", "confidence": 0.0-1.0}'
      }, {
        role: 'user',
        content: `Classify this email:\nFrom: ${email.from}\nSubject: ${email.subject}\nBody: ${email.body?.substring(0, 500)}`
      }],
      temperature: 0.3    });

    const classification = JSON.parse(response.data.choices[0].message.content);
    res.json({
      success: true,
      ...classification
    });
  } catch (error) {
    console.error('Classification error:', error.message);

    // Fallback classification if GPT-OSS is unavailable
    res.json({
      success: true,
      category: 'uncategorized',
      priority: 'medium',
      confidence: 0.5,
      fallback: true
    });
  }
});

// Email summarization
app.post('/summarize', async (req, res) => {
  try {
    const { text, maxLength = 150 } = req.body;

    const response = await axios.post(`${GPT_OSS_URL}/v1/chat/completions`, {
      model: 'gpt-oss:20b',
      messages: [{
        role: 'system',
        content: `Summarize the following text in maximum ${maxLength} characters. Be concise and capture the main points.`
      }, {
        role: 'user',
        content: text
      }],
      temperature: 0.5
    });

    res.json({
      success: true,
      summary: response.data.choices[0].message.content
    });
  } catch (error) {
    console.error('Summarization error:', error.message);

    // Fallback summarization
    res.json({
      success: true,
      summary: text.substring(0, maxLength) + '...',
      fallback: true
    });
  }
});

// Generate email response
app.post('/generate-response', async (req, res) => {
  try {
    const { originalEmail, responseType = 'professional' } = req.body;

    const toneInstructions = {
      professional: 'Write a professional and formal response',
      friendly: 'Write a warm and friendly response',
      brief: 'Write a very brief and concise response',
      detailed: 'Write a comprehensive and detailed response'
    };

    const response = await axios.post(`${GPT_OSS_URL}/v1/chat/completions`, {
      model: 'gpt-oss:20b',
      messages: [{
        role: 'system',
        content: `You are an email assistant. ${toneInstructions[responseType]}. Do not include subject line or signatures.`
      }, {
        role: 'user',
        content: `Generate a response to this email:\n\nFrom: ${originalEmail.from}\nSubject: ${originalEmail.subject}\n\n${originalEmail.body}`
      }],
      temperature: 0.7
    });

    res.json({
      success: true,
      response: response.data.choices[0].message.content
    });
  } catch (error) {
    console.error('Response generation error:', error.message);

    // Fallback response
    res.json({
      success: true,
      response: 'Thank you for your email. I will review it and get back to you shortly.',
      fallback: true
    });
  }
});

// Extract action items from email
app.post('/extract-actions', async (req, res) => {
  try {
    const { emailContent } = req.body;

    const response = await axios.post(`${GPT_OSS_URL}/v1/chat/completions`, {
      model: 'gpt-oss:20b',
      messages: [{
        role: 'system',
        content: 'Extract action items from the email. Return JSON format: {"actions": ["action1", "action2"], "deadlines": ["date1", "date2"]}'
      }, {
        role: 'user',
        content: emailContent
      }],
      temperature: 0.3    });

    const actions = JSON.parse(response.data.choices[0].message.content);
    res.json({
      success: true,
      ...actions
    });
  } catch (error) {
    console.error('Action extraction error:', error.message);

    res.json({
      success: true,
      actions: [],
      deadlines: [],
      fallback: true
    });
  }
});

// Sentiment analysis
app.post('/analyze-sentiment', async (req, res) => {
  try {
    const { text } = req.body;

    const response = await axios.post(`${GPT_OSS_URL}/v1/chat/completions`, {
      model: 'gpt-oss:20b',
      messages: [{
        role: 'system',
        content: 'Analyze the sentiment of the text. Return JSON: {"sentiment": "positive/negative/neutral", "score": 0.0-1.0, "emotions": ["emotion1", "emotion2"]}'
      }, {
        role: 'user',
        content: text
      }],
      temperature: 0.3    });

    const sentiment = JSON.parse(response.data.choices[0].message.content);
    res.json({
      success: true,
      ...sentiment
    });
  } catch (error) {
    console.error('Sentiment analysis error:', error.message);

    res.json({
      success: true,
      sentiment: 'neutral',
      score: 0.5,
      emotions: [],
      fallback: true
    });
  }
});

// OpenAI-compatible chat completions endpoint for frontend
app.post('/v1/chat/completions', async (req, res) => {
  try {
    const { model, messages, temperature = 0.3 } = req.body;

    const response = await axios.post(`${GPT_OSS_URL}/v1/chat/completions`, {
      model: model || 'gpt-oss:20b',
      messages,
      temperature
    });

    // GPT-OSS already returns OpenAI-compatible format
    res.json(response.data);
  } catch (error) {
    console.error('Chat completions error:', error.message);

    res.status(500).json({
      error: {
        message: 'AI service temporarily unavailable',
        type: 'service_error'
      }
    });
  }
});

// Check GPT-OSS status
app.get('/status', async (req, res) => {
  try {
    const response = await axios.get(`${GPT_OSS_URL}/health`, {
      timeout: 5000
    });

    res.json({
      success: true,
      gptOssStatus: 'online',
      gptOssUrl: GPT_OSS_URL,
      details: response.data
    });
  } catch (error) {
    res.json({
      success: false,
      gptOssStatus: 'offline',
      gptOssUrl: GPT_OSS_URL,
      error: error.message
    });
  }
});

app.listen(PORT, () => {
  console.log(`AI Proxy Service running on port ${PORT}`);
  console.log(`Connected to GPT-OSS at: ${GPT_OSS_URL}`);
  console.log('Endpoints:');
  console.log('  POST /v1/chat/completions - OpenAI-compatible chat API');
  console.log('  POST /classify - Classify emails');
  console.log('  POST /summarize - Summarize text');
  console.log('  POST /generate-response - Generate email responses');
  console.log('  POST /extract-actions - Extract action items');
  console.log('  POST /analyze-sentiment - Sentiment analysis');
  console.log('  GET /status - Check GPT-OSS connection status');
});