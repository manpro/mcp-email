import axios from 'axios'
import { userProfile, getAIPromptForEmail } from '../config/userProfile'

// Get AI URL from environment variable, with fallback to GPT-OSS 20B
const AI_BASE_URL = import.meta.env.VITE_AI_URL || 'http://172.16.16.148:8085';
const GPT_OSS_API = `${AI_BASE_URL}/v1/chat/completions`;

// User patterns storage (would be in a database in production)
const userPatterns = JSON.parse(localStorage.getItem('emailPatterns') || '{}')

export const classifyEmail = async (email) => {
  // Check if email already has AI analysis from backend
  if (email.aiAnalysis) {
    return {
      priority: email.aiAnalysis.priority || 'medium',
      category: email.aiAnalysis.category || 'other',
      suggestedFolder: null,
      suggestedActions: [],
      summary: email.aiAnalysis.summary || email.subject
    }
  }

  // Return default classification without calling AI
  // The backend unified-service already provides AI analysis
  return {
    priority: 'medium',
    category: 'other',
    suggestedFolder: null,
    suggestedActions: [],
    summary: email.subject
  }
}

export const searchWithAI = async (naturalLanguageQuery, accountId) => {
  try {
    // First, use AI to extract search keywords from natural language
    const prompt = `Extrahera sökord från denna naturliga språkfråga:

Fråga: "${naturalLanguageQuery}"

Extrahera de viktigaste sökorden som kan användas för att hitta emails.
Fokusera på:
- Namn på personer eller företag
- Specifika ämnen eller projekt
- Tidsperioder (översätt till engelska datum)
- Viktiga termer

Returnera ENDAST sökorden separerade med mellanslag, inget annat:`

    const aiResponse = await axios.post(GPT_OSS_API, {
      model: 'gpt-oss:20b',
      messages: [
        {
          role: 'system',
          content: 'Du är expert på att extrahera sökord från naturliga språkfrågor för email-sökning.'
        },
        {
          role: 'user',
          content: prompt
        }
      ],
      temperature: 0.3
    })

    // Extract keywords from AI response, fallback to original query
    const aiKeywords = aiResponse.data.choices[0].message.content.trim()
    const searchQuery = aiKeywords || naturalLanguageQuery

    // Now use the backend search API with the extracted keywords
    const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:3013'
    const searchResponse = await axios.get(`${apiUrl}/api/search`, {
      params: {
        q: searchQuery,
        account: accountId
      }
    })

    // Add AI match reasoning to each result
    const resultsWithAI = searchResponse.data.emails.map(email => ({
      ...email,
      matchReason: `AI found relevant content for "${naturalLanguageQuery}": ${aiKeywords}`
    }))

    return resultsWithAI

  } catch (error) {
    console.error('AI search failed:', error)

    // Fallback to simple backend search without AI enhancement
    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:3013'
      const searchResponse = await axios.get(`${apiUrl}/api/search`, {
        params: {
          q: naturalLanguageQuery,
          account: accountId
        }
      })
      return searchResponse.data.emails || []
    } catch (fallbackError) {
      console.error('Fallback search also failed:', fallbackError)
      return []
    }
  }
}

export const getBulkSuggestions = async (emails) => {
  try {
    const emailSummaries = emails.map(e => ({
      from: e.from,
      subject: e.subject,
      preview: (e.text || e.html || '').slice(0, 100)
    }))

    const prompt = `Analysera dessa ${emails.length} valda emails och föreslå bulk-åtgärder:

${JSON.stringify(emailSummaries, null, 2)}

Returnera JSON med föreslagna åtgärder:
{
  "actions": [
    {
      "type": "move|delete|archive|mark",
      "value": "folder name or action value",
      "label": "Åtgärd på svenska",
      "reason": "Kort förklaring",
      "icon": "folder|delete|archive",
      "confidence": 0-100
    }
  ]
}`

    const response = await axios.post(GPT_OSS_API, {
      model: 'gpt-oss:20b',
      messages: [
        {
          role: 'system',
          content: 'Du är en email-hanteringsassistent. Föreslå smarta bulk-åtgärder baserat på email-innehåll.'
        },
        {
          role: 'user',
          content: prompt
        }
      ],
      temperature: 0.4
    })

    try {
      const content = response.data.choices[0].message.content
      const jsonMatch = content.match(/\{[\s\S]*\}/)
      if (jsonMatch) {
        return JSON.parse(jsonMatch[0])
      }
    } catch {
      // Fallback
    }

    return {
      actions: [
        {
          type: 'archive',
          value: 'archive',
          label: 'Arkivera alla',
          reason: 'Flytta till arkiv',
          icon: 'archive',
          confidence: 75
        }
      ]
    }
  } catch (error) {
    console.error('Bulk suggestions failed:', error)
    return { actions: [] }
  }
}

export const trainUserPattern = (email, action, value) => {
  const key = `${email.from}_${action}`

  if (!userPatterns[key]) {
    userPatterns[key] = {
      pattern: {
        from: email.from,
        subjectPattern: email.subject
      },
      action: action,
      value: value,
      count: 0,
      confidence: 0.5
    }
  }

  userPatterns[key].count++
  userPatterns[key].confidence = Math.min(0.95, userPatterns[key].confidence + 0.1)

  localStorage.setItem('emailPatterns', JSON.stringify(userPatterns))
}

export const getPredictedAction = (email) => {
  // Look for matching patterns
  for (const key in userPatterns) {
    const pattern = userPatterns[key]
    if (pattern.pattern.from === email.from && pattern.confidence > 0.7) {
      return {
        action: pattern.action,
        value: pattern.value,
        confidence: pattern.confidence
      }
    }
  }
  return null
}